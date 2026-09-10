# CHAPTER III — METHODOLOGY

## 3.0 Introduction

This chapter details the data, graph construction, HostScaler, GraphSAGE autoencoder, calibration, multi-window fusion, HELD-OUT evaluation protocol, metrics, reproducibility constraints, and tools/environment. Every design choice is traceable to a gotcha or report card (RC) that measured its impact. Time-based windows, directed edges, SAGEConv over GCN, log1p before scaling, and edge-level alerts are not preferences — they are defended decisions recorded in `CLAUDE.md` and `experiments/report_cards.md`.

The methodology follows the principle established in Chapter I: learn what *normal* looks like (benign Monday only), reconstruct it, flag deviations, and evaluate on families never seen during training — the closest honest proxy for a zero-day. The chapter mirrors the sample's documentation structure where methodology follows literature review and precedes design.

---

## 3.1 Datasets and Preprocessing

### 3.1.1 Primary Dataset — CICIDS2017

CICIDS2017 is the Canadian Institute for Cybersecurity's labelled flow dataset captured 2017-07-03 to 2017-07-07. Monday 2017-07-03 is benign (-normal) and is the **only training source**; Tuesday–Friday contain 7 attack families held-out one-by-one.

Two releases exist and only one can build a graph (GOTCHA #3, `capture/schema_mapper.py`):

| Release | Path | Columns | Has IPs? | Use |
| ------- | ---- | ------- | -------- | --- |
| ML-CSV | `data/MachineLearningCSV/` | 79 | **No** — no IP columns at all | Fine for per-flow baseline M5a, useless for graphs |
| GeneratedLabelledFlows | `data/GeneratedLabelledFlows/TrafficLabelling/` | 85 | **Yes** — Flow ID, Source IP, Destination IP, Protocol, Timestamp | Required for anything relational (M5b) — **production gate** |

All GeneratedLabelledFlows files are **latin-1, not UTF-8** — use `graph_builder.read_flows()` (not `pd.read_csv` default). The Thursday WebAttacks CSV is 63% junk rows: 458,968 rows, only 170,366 labelled; the rest have NaN IPs. One NaN host makes `sorted(set(src)|set(dst))` raise `TypeError` and kills the whole family mid-sweep, leaving a silent mean across 6 not 7 (GOTCHA #12). `graph_builder.drop_unusable_rows()` handles it and prints what it drops.

**Naming conventions:** The 85-col release names `Destination Port` as a model feature; A's CICFlowMeter output treats it as metadata (GOTCHA #4). Both are handled; `capture/schema_mapper.py` identifies content-based columns without hard-coding names — run it on any new dataset before training (see GOTCHA #13: IDS2018's `Tot Fwd Pkts` / `TotLen Fwd Pkts` breaks `bytes_sent`).

### 3.1.2 External Replication Datasets

| Dataset | Size | Can build graph? | Note |
| ------- | ---- | ---------------- | ---- |
| CSE-CIC-IDS2018 | 10 CSVs, ~16M flows | Only `Thuesday-20-02-2018` (typo official) — 9/10 have **no IP columns** | Third naming convention unfixed, `bytes_sent` silently zero (GOTCHA #13) |
| CTU-13 | 13 botnet captures | Yes (host-level ground truth) | Virut, Rbot, Neris |
| UNSW-NB15 | 2.5M hybrid | Planned third replication — needs pseudo-timestamps | Not yet in production |

Synthetic datasets provided by A (`dataset_10k_normal.csv` — 508 clients touching identical 2 services, collapsed neighbourhoods → embeddings collapse; `live_capture.csv` — dst_port as incrementing counter → 12,503 services across 12,504 flows) **cannot form graphs** (GOTCHA #6). Use `graph_builder.graph_health()` before training on any new source — it rejects collapsed/degenerate topologies.

### 3.1.3 Schema Pinning and Column Alignment

Never derive feature columns per-file with `dropna(axis=1)` — it drops different columns on different attack days and hands the model misaligned features; scores look plausible and mean nothing (GOTCHA #5). Pin the column list once from the training file (`ensembler.pin_canonical()`). Feature catalogue (frozen):

*   **Flow features (87-dim for revived M5a):** 76 CIC flow stats + 11 window-context dims (degree, bytes, duration aggregates in window). `schemas/feature_vector.json v3.0` (76→87, flow+ctx).
*   **Host features:** v1 = 8 dims (degree in/out, flow count, bytes in/out, duration), v2 = 19 dims (adds port entropy, unique peers, flag ratios, IAT stats). Indices 0–7 stable across feature sets; never unpack positionally `a,b,c,d,e,f,g,h = node.tolist()` (GOTCHA #23; breaks at 19).

---

## 3.2 Host-Graph Construction (`detection/graph_builder.py`)

### 3.2.1 Time Windows

We draw a graph for every **time-based** window — 60-second and 300-second slices — not fixed-count windows. “200 peers in 60 seconds” is a rate; 200 peers in any count-window is not. Window size is a metric trade, not an upgrade: 60s → 1800s raises mean ROC-AUC 0.9173→0.9832 and drops P@100 0.244→0.093 (294 runs, RC-02). **60s maximises P@100 and is the right default** unless AUC is the chosen metric; we fuse both.

### 3.2.2 Nodes, Edges, Direction

**Nodes = hosts (IP), Edges = directed flows (src → dst).** One-to-many (scan) and many-to-one (DDoS) must not collapse into one undirected edge — a design decision defended in `graph_builder.py:directed=True`, no self-loops, no multi-edge collapse. Flow ID and Timestamp required; missing IPs → health reject.

**SAGEConv over GCNConv:** GCN's symmetric normalisation (`D^{-1/2}AD^{-1/2}`) washes out the degree signal we are detecting; GraphSAGE mean aggregation preserves it (Hamilton et al., 2017).

### 3.2.3 Node and Edge Features

Per-flow stats are aggregated to host level per window:

*Equation 1 — Host feature (example):*
```
out_degree(v) = |{ u : (v→u) ∈ E_window }|
port_entropy(v) = - Σ p(port) log p(port)   over dst ports of v
bytes_sent(v) = Σ bytes(f)                 over flows f from v
```

Edge features (`edge_attr`, 4-dim: bytes, packets, duration, protocol one-hot) were computed and discarded for the whole project until RC-26; ranking the source-host score together with the edge's own reconstruction error (`edge_score="rank_mean"` default) lifts edge-level AUC 0.712→0.789 and P@100 0.207→0.349 — the only change measured that improves both (GOTCHA #19). Edge features alone (0.7359) beat the node-derived score.

### 3.2.4 HostScaler — log1p Before Scaling

**Plain min-max on power-law counts** maps the busiest host to 1.0 and squashes every other host near 0, so a few huge servers permanently own the top of the alert queue. This was the reason Patator and WebAttacks were stuck at P@100 = 0.000 across 294 earlier runs, not “unobservable structure”.

Fix: `NodeScaler(log=True)` (default since 2026-08-12, GOTCHA #14) applies `x' = log1p(x) = log(1+x)` before min-max:

```
x_log = log(1 + x)
x_scaled = (x_log - min_log) / (max_log - min_log)   fitted on benign only
```

Mean P@100 0.250→0.413 at 60s, Patator 0.000→0.618, WebAttacks 0.000→0.381. Pass `--no-log-scale` only to reproduce pre-2026-08-12 numbers. Checkpoints saved before that date carry no `log` key and are loaded as `log=False`, so they still score correctly.

---

## 3.3 Models

### 3.3.1 M5a — Revived Per-Flow Autoencoder (87-dim)

Plain M5a (76-dim flow AE) is the legacy baseline `legacy/autoencoder.py` (now shim `stub_detector.py`, `DEFAULT_THRESHOLD=0.5` uncalibrated, benign max ~0.278 — GOTCHA #7). The **revived** variant (`train_m5a_revived.py` / `exp_m5a_revival.py`) adds 11 window-context dims (local degree, window bytes, etc.) → 87-dim, `m5a_revived_ctx.pt`. It is **not in production defaults — decision pending RC-26** — but when fused with M5b via rank noisy-or it contributes the headline 0.9996 (plain shipped M5a alone hurts everywhere: 0.9499±0.0021 in MW fusion).

Architecture: MLP encoder 87→64→32→16 (latent), decoder 16→32→64→87, ReLU, MSE loss trained on benign Monday only.

### 3.3.2 M5b — GraphSAGE Host Autoencoder (`detection/gnn_model.py`)

**GraphAutoencoder** — 2× SAGEConv (hidden 32, default), ReLU, latent **8 = in_dim** (no bottleneck by width). `GraphAutoencoder has no bottleneck` (GOTCHA #15): a host has 8 features and latent=8, so encoder is wide enough to pass input through unchanged — and an AE that can learn identity reconstructs attacks as well. Message passing means it is not literally an identity map, so this is a weakness not fatal. **Raising latent makes it worse**; if you want capacity, add node features (`feature_set="v2"` 19-dim, not width). GOTCHA #9: latent 2→12 moves mean only 0.003; hidden 32→64 moves 0.0002 — architecture does not matter here; do not tune width.

Decoder: inner-product for structure + MLP for features; loss = MSE(node) + MSE(edge). Formal:

```
h_v^{(k)} = ReLU( W_k · MEAN({h_v^{(k-1)} } ∪ { h_u^{(k-1)} : u ∈ N(v) }) )   SAGE
z_v = h_v^{(K)}   ∈ R^{latent}
x̂_v, â_{uv} = Decoder(z_v, z_u)
L = Σ_v ||x_v - x̂_v||² + Σ_{(u,v)∈E} ||a_{uv} - â_{uv}||²
```

*Equation 2 — Anomaly score:*
```
score(v) = ||x_v - x̂_v||² + λ·||a_{src,dst} - â||²    λ weighted by edge_score rule
```

### 3.3.3 Determinism and Device Sensitivity

Results are device-sensitive — same seed gave WebAttacks 0.5048 on CPU retrain and 0.9948 on GPU (2026-08-21): cuBLAS/cuDNN reduction order changes training trajectories on knife-edge families (GOTCHA #24). `torch.manual_seed` alone does NOT pin CUDA.

Every eval script must call the `set_seed()` helper:

```python
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
```

and every published number must state device + torch build. Never mix devices inside one comparison table. Always pass `--seed`; nothing was seeded until 2026-08-11, where two identical sweeps gave mean 0.8997 vs 0.9251 and PortScan moved 6.5 points on initialisation alone (GOTCHA #11).

---

## 3.4 Fusion and Scoring (`detection/ensembler.py`, `detection/alert_pipeline.py`)

### 3.4.1 Calibration

Raw reconstruction distances (0.038–0.122) and percentiles (0–1) live on incomparable scales; `alert_pipeline` fused uncalibrated scores until 2026-08-12 and thereby was M5b alone (99.9% max picks M5b, GOTCHA #21). Fix: per-window **percentile calibration** against a 20% Monday holdout (80/20 `ensembler.py`): for a score s in window W,

```
p(s) = rank(s) / |W_cal|    where rank is against benign calibration population
```

Checkpoints now carry `m5a_calibrator` and `gnn_calibrator`; `gnn_autoencoder_v1.pt` is a **5-member ensemble** whose scores are already percentiles, not raw errors — any threshold tuned against the old single-model checkpoint is meaningless (GOTCHA #18). Missing calibrator falls back with `RuntimeWarning` (RC-26).

### 3.4.2 Fusion Rules (6 configs, 4 seeds — `eval_mw_ablation_4seed.py` reference)

| Rule | Description | Property | Result (RC-26) |
| ---- | ----------- | -------- | -------------- |
| `mean` (calibrated) | ` (p60 + p300)/2` | Preserves ranking | Baseline fusion |
| `max` (calibrated) | `max(p60,p300,pM5a)` | Lets saturated M5a overwrite M5b (GOTCHA #20) | `fused_max` hurts (M5a saturates 0.999-1.000 on 100% attack alerts) |
| `rank_mean` | Rank within window population before averaging | Window-local, operationally usable | Lifts edge AUC 0.712→0.789 (GOTCHA #19) |
| `fused_rank_max` | Compare score POSITIONS rather than values | Only fusion that beats both detectors (+0.0398 AUC) but costs P@100 0.277→0.193 and is batch-only (GOTCHA #17) | Best but not streamable |
| **`noisyor` (production)** | `1 - Π(1 - p_i)` under independence | Within-window rank first | **0.9996±0.0001 (v1), 0.9997±0.0001 (v2)** best headline |
| `edge_score="src"` vs `rank_mean` | `mean` vs `src` vs `rank_mean` for `ScoredAlert` | `rank_mean` (node+edge) best | 0.7892 edge AUC |

**Production default (`alert_pipeline.score_window()`):** within-window rank noisy-or over 60s+300s host graphs (plus revived M5a ctx where enabled) → `rank_mean` edge scoring. `fusion="mean"` is default so M5b ranking survives; omitting `feature_columns` gives M5b only — the most consistent config measured (0.8322 edge-level, GOTCHA #22).

### 3.4.3 Alert Emission

`alert_pipeline.score_window(feature_columns=None, threshold=None)` → list of `ScoredAlert[src_ip, dst_ip, score, rank, model_source]` sorted by fused rank. `feature_set="v2"` requests refuse loudly without a 19-dim checkpoint (dimension guard). `model_source` records single vs ensemble (RC-18).

We report **node AUC for modelling claims** and **edge AUC for operational claims**; the gap is 22 points (node 0.8965 vs edge 0.6740, GOTCHA #16). Every published figure describes the model, not the queue, unless stated as edge-level.

---

## 3.5 Drift, Explainability, Adversarial Evaluation

### 3.5.1 M6 — Drift Monitoring (`detection/drift_monitor.py`)

Score distributions drift when “normal” shifts (new services, diurnal, patch days). Score drift is unsupervised — hardest. `DetectorDriftMonitors` watches all three streams (M5a error, M5b error, fused rank) via `alert_pipeline.init_drift_monitors()`. Wired but not yet governing threshold automatically (RC-28: small-window filtering changes nothing — queue noise is drift, not variance; fix is drift-aware threshold, not smaller windows).

### 3.5.2 M7 — SHAP Explainability (`detection/shap_explainer.py`, C's seam)

For each alert, SHAP (Lundberg & Lee, 2017) attributes the score to input dims: e.g., PortScan flagged by `out_degree` spike, DDoS by `in_degree` collapse. ATT&CK mapper translates features → tactics (Reconnaissance, Resource Development). Never unpack positionally: `a,b,c,d,e,f,g,h = node.tolist()` breaks under v2 (GOTCHA #23); index by position (0–7 stable).

### 3.5.3 Red-Team Harness (Person D)

`harness/graph_techniques.py` implements 4 evasion attacks aimed at M5b's structure; `harness/run_graph_harness.py` measures what evasion *costs* the attacker (RC-14):

| Technique | Success | Cost to attacker |
| --------- | ------- | ---------------- |
| Port-hiding / camouflage | No | — |
| Slow scan (rate ↓ 20×) | Yes | 20× time |
| 16-way distributed scan | Yes | 16 machines |
| Infiltration mimicry | Partial | — |

Result: evasion is **expensive**, not impossible — a defensible operational claim.

### 3.5.4 Privacy Pass (C)

k-anonymity on exported features; federated sharing out-of-scope for Semester 7.

---

## 3.6 Evaluation Protocol (HELD-OUT) and Metrics

### 3.6.1 HELD-OUT Definition

**HELD-OUT = held-out attack family.** Train on benign Monday only (80% train / 20% calibration holdout from Monday), evaluate on each of 7 families (Tuesday–Friday) **one family held-out at a time**, never trained on that family. This is the closest honest proxy for a zero-day. Report mean ± std over seeds 0–3 (`eval_mw_ablation_4seed.py --seeds 0 1 2 3 --epochs 60` is reference implementation, RC-26). One-command artifact quoted in `docs/PAPER_OUTLINE.md`.

### 3.6.2 Metrics — What to Quote and What Not To

*   **ROC-AUC (ranking quality, 0.5–1.0):** primary modelling metric. “0.9987 means: pick any attacker and any normal host — attacker scores higher 99.87% of the time.” Quote node AUC for modelling, edge AUC for operational.
*   **Attacker rank & recall@100:** operational headline — “attackers in top ~11–35 of thousands, recall@100 = 1.0”. Honest under extreme imbalance.
*   **P@100 (precision at 100):** diagnostic only — structurally capped at `bad/100` (1 attacker → max 0.01, 8 attackers → 0.08, RC-27). 60s vs 1800s trade: P@100 0.244→0.093 while AUC 0.917→0.983 (RC-02). Do not headline P@100.
*   **Calibration holdout optimism:** 20% Monday holdout is still optimism (still quote it; RC-26 caveat).

### 3.6.3 Closed Negatives — Do Not Revisit

Every result below was measured under identical HELD-OUT conditions and showed no or negative effect; report cards record the proof (RC-15…RC-32):

*   Shipped-M5a uniform fusion hurts (0.9499±0.0021 MW, GOTCHA #20).
*   Temporal/LSTM half alone adds nothing at edge level (RC-20, `gnn_temporal_fused.py` kept for ablation only).
*   LODO (5× training data, 2,209 graphs) worse (0.930→0.8405, RC-22, GOTCHA #10).
*   k=5 sim edges hurt on production architecture.
*   Small-window filtering null (RC-28).
*   Latent width tuning null (GOTCHA #9).

These are closed.

---

## 3.7 Tools and Environment

*   **Language/pkgs:** Python 3.11, PyTorch 2.5.1+cu121, PyG (GraphSAGE), scikit-learn, SHAP, FastAPI.
*   **Venv:** `venv/` is machine-specific, never portable, never committed (GOTCHA #1). Build per machine:
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    ```
    On CPU-only machines: drop `--extra-index-url` and use `torch==2.5.1` (README).
*   **Paths:** All scripts resolve via `Path(__file__).resolve().parent...` (GOTCHA #2) — never hardcode absolute paths (`D:\Test OD\...` broke 4 scripts).
*   **Datasets:** `data/` is gitignored; each machine downloads `GeneratedLabelledFlows` (CIC gates behind registration http://cicresearch.ca/CICDataset/CIC-IDS-2017/, skip ~50GB PCAPs). Model binaries `*.pt` **are** tracked for demo.
*   **Related scripts:** `experiments/` + `exp_*.py` are evidence behind `CHANGELOG.md` numbers; nothing in prod imports them.

One-command reproducibility (GPU, deterministic):
```
python detection/eval_mw_ablation_4seed.py --seeds 0 1 2 3 --epochs 60
```

---

*This chapter's protocol is the paper's HOSTFUSE + HELD-OUT spine; Chapter IV implements it as a system. Caveats (batch-only noisy-or, calibration holdout, device sensitivity) are stated before an examiner does — see §4.6.*

