# CHAPTER IV — DESIGN AND MODELLING

## 4.0 Introduction

This chapter presents the system architecture, component design, data flow, and modelling choices that implement the methodology of Chapter III. Design decisions are defended, not revisited: autoencoder never classifier, SAGEConv over GCNConv, nodes=hosts / edges=directed, time-based windows (not fixed-count), edge-level alerts, and M5a lifted up to host-window for comparison (not M5b pushed down to flows) — all recorded in `CLAUDE.md` and justified in RC-02…RC-32.

The system is a three-pillar design: network flows (Pillar 1, Semester 7, this report), identity/UEBA (Pillar 2, Aditya), and host syscalls via eBPF (Pillar 3, weeks 4–6, roadmap in `Knowledge/`). The individually attributable headline is the **baseline-vs-GNN ablation** (B — Deep), not “we built a GNN”.

---

## 4.1 System Architecture — Three Pillars and Four Persons

```
                        ┌─────────────────────────────────┐
                        │  Pillar 1: Network (Semester 7) │
   Raw traffic →  capture/schema_mapper → pcap_to_flows ──→ graph_builder ──→ gnn_model (M5b GraphSAGE AE, LogScaler)
                        │                              ↘ ensembler (M5c: 60s+300s rank noisy-or) → alert_pipeline → dashboard  │
                        └─────────────────┬───────────────┘                                │
                                          │                                              │
   Identity logs → UEBA risk model (C) ───┼──────────────────────────────────────────────┤  Fusion (future: three-way)
                                          │                                              │
   Syscalls via eBPF → ebpf_syscall_watcher (capture/ebpf_syscall_watcher.py) ───────────┼→ Host AE (Pillar 3, HMM vs AE ablation)
                                          │                                              │
                              ┌───────────┴───────────┐                     ┌────────────┴──────────┐
                              │  M6 drift_monitor.py  │                     │ M7 shap_explainer.py  │
                              │  (score drift, 3 streams)               │  (SHAP + ATT&CK mapper) │
                              └───────────────────────┘                     └───────────────────────┘
                                          │                                              │
                              ┌───────────┴──────────────────────────────────────────────┴──────────┐
                              │  Harness D: graph_techniques.py → run_graph_harness.py (costs evasion) │
                              └───────────────────────────────────────────────────────────────────────┘
```

**Four-person mapping (CLAUDE.md):**

| Member | Track | Owns (freeze 2026-08-25) |
| ------ | ----- | ------------------------ |
| A — Saharsh | Data & Capture | flow capture (`FlowRecord`), feature engineering, dataset prep, `pcap_to_flows`, `schema_mapper` |
| **B — Deep** | **Detection Modeling** | **baseline AE (M5a revived 87-dim), GNN-temporal (ablated), drift monitor (M6), ensembler (M5c)** |
| C — Aditya | Trust & Risk | SHAP, learned UEBA risk model, ATT&CK mapper, privacy pass (k-anonymity) |
| D — Avinash | Adversarial & Delivery | red-team harness (4 techniques), FastAPI + React dashboard, alert API `/alerts` |

“HOSTFUSE + HELD-OUT” is the named method and protocol: HOST-graph Fusion of Unsupervised reconstruction Scores evaluated under held-out-family (see `docs/PAPER_OUTLINE.md`).

---

## 4.2 Data Flow and Module Map (`detection/`)

| S.No. | Stage | Module | Input → Output | Status |
| :---: | ----- | ------ | -------------- | ------ |
| 1 | Ingest — schema | `capture/schema_mapper.py` | CSV (79/85/IDS2018 naming) → canonical `FlowRecord` | Content-based detection; run on any new source |
| 2 | Ingest — capture | `capture/pcap_to_flows.py` , `capture/ebpf_syscall_watcher.py` (new) | pcap / eBPF → flows / syscall streams | `ebpf_syscall_watcher.py` added 2026-09 (week 4) |
| 3 | Build — graph | `detection/graph_builder.py` | flows → `List[Data]` per window (`x=[N,8/19]`, `edge_index=[2,E]`, `edge_attr=[E,4]`, `y`) | `read_flows()` latin-1, `drop_unusable_rows()`, `graph_health()` gates |
| 4 | Scale | `detection/gnn_model.py:NodeScaler(log=True)` | raw host feats → log1p → min-max (fit benign only) | Single biggest win (RC-28); default since 2026-08-12 |
| 5 | Train — baseline | `detection/train_m5a_revived.py` / `exp_m5a_revival.py` | 87-dim flows → `m5a_revived_ctx.pt` | Not in prod defaults — decision pending |
| 6 | Train — GNN | `detection/gnn_model.py:GraphAutoencoder` | benign host graphs → `gnn_autoencoder_v1_logscale.pt` (ensemble v1) + `_v2.pt` variant | Latent 8 (=in_dim), hidden 32 |
| 7 | Score — fuse | `detection/ensembler.py` | 60s+300s (+M5a ctx) errors → percentiles → noisy-or ranks | 80/20 cal holdout, `pin_canonical` |
| 8 | Serve — alerts | `detection/alert_pipeline.py` | window → `ScoredAlert[src_ip,dst_ip,score,rank,model_source]` (edge-level) | `score_window(feature_columns=None)` = M5b-only default (RC-26), guards v2 dim |
| 9 | Evaluate — lab | `detection/eval_mw_ablation_4seed.py` (reference), `eval_feature_set_v2.py`, `eval_baselines_4seed.py`, `eval_external_*` | held-out loop → mean±std tables | Every number is 4-seed banded |
| 10 | Monitor | `detection/drift_monitor.py:DetectorDriftMonitors` | 3 score streams → drift flag | Wired via `init_drift_monitors()` |
| 11 | Explain | `detection/shap_explainer.py` (C) | host embedding → SHAP values + ATT&CK tag | Per-alert drawer in dashboard |
| 12 | Adv — harness | `harness/graph_techniques.py` + `run_graph_harness.py` (D) | 4 evasion attacks → attacker cost | RC-14 |

*Source: Compiled from `detection/README.md`, `experiments/report_cards.md`; structure cf. Ex-2 Table 2.5.*

**Health gate (call before any training):**

```
python -c "from detection.graph_builder import graph_health; graph_health(flows)"
# synthetic 10k_normal → 508 clients → 2 services → REJECT (collapsed)
# live_capture → dst_port counter → 12,503 services → REJECT (degenerate)
# CICIDS2017 GeneratedLabelledFlows 85-col → ACCEPT
```

---

## 4.3 Modelling Details

### 4.3.1 GraphAutoencoder — Architecture

Two SAGEConv layers, ReLU, latent equal in_dim (8 for v1, 8 effective for v2 with larger input but same latent pattern — capacity via features, not width). GOTCHA #9: latent 2→12 moves mean 0.003; hidden 32→64 moves 0.0002 — do not tune width.

```
Input: Data(x=[N,8/19], edge_index=[2,E], edge_attr=[E,4])
SAGE-1: N×8/19 → N×32   (MEAN aggregation, no symmetric norm)
ReLU
SAGE-2: N×32 → N×8      (latent)
Decoder:
  x̂_v = MLP_node(z_v)                  ∈ R^{8/19}
  â_{u,v} = MLP_edge([z_u ; z_v])       ∈ R^{4}
Loss:  MSE(x, x̂) + MSE(edge_attr, â)   benign only, no labels
Score(v) = ||x - x̂||² + λ·||a - â||²   λ via edge_score rule (mean/src/rank_mean)
```

`NodeScaler(log=True)` is applied **before** encoding (log1p, then min-max fit on Monday benign). Checkpoints before 2026-08-12 carry no `log` key → loaded as `False` for correct scoring (GOTCHA #18 compat).

### 4.3.2 Feature Sets — v1 vs v2

| Version | Dims | Features (stable indices 0-7) | Added in v2 (8-18) | Checkpoint |
| ------- | ---- | ----------------------------- | ------------------ | ---------- |
| v1 | 8 | out_degree, in_degree, flow_count, bytes_out, bytes_in, duration_sum, unique_ports, degree_ratio | — | `gnn_autoencoder_v1_logscale.pt` (production) |
| v2 | 19 | same 0-7 | port_entropy, peer_entropy, flag_SYN_ratio, flag_ACK_ratio, IAT_mean/var, pkt_len_var, bytes_per_flow, etc. (11 more) | `gnn_autoencoder_v1_logscale_v2.pt` (shipped; flip pending team sign-off) |

Dimension guard: `feature_set="v2"` request without 19-dim checkpoint refuses loudly (RC-30). Never unpack positionally: `indices 0–7 guaranteed stable across v1/v2` (GOTCHA #23).

### 4.3.3 Windows, Calibration, Fusion — Reference Implementation

**Windows:** 60s (bursty: PortScan) + 300s (sustained: DDoS, infiltration). Both built per window in `graph_builder`.

**Calibration:** per-window percentile vs 20% Monday holdout (80 train /20 cal). Ensemble checkpoint stores calibrator; missing one falls back with `RuntimeWarning` (RC-26). `m5a_revived_ctx.pt` carries `m5a_calibrator`; uncalibrated fuse until 2026-08-12 was M5b alone (GOTCHA #21).

**Fusion (reference = `eval_mw_ablation_4seed.py`):**

```
p60 = percentile( reconstruction_error_60, cal_pop_60 )
p300 = percentile( error_300, cal_pop_300 )
pM5a = percentile( error_M5a_max_pooled_to_host, cal_pop_M5a )   # lifted up
rank_pX = rank(pX within window population) / |window|
fused = 1 - (1 - rank_p60)*(1 - rank_p300)*(1 - rank_pM5a)   # noisy-or
       # production M5b-only: omit pM5a → 0.8322 edge AUC (best consistent)
```

`fused_rank_max` also beats both detectors (+0.0398 AUC over M5b) but costs P@100 (0.277→0.193) and is batch-only — needs population to rank against (GOTCHA #17). `alert_pipeline` cannot use it for a single alert; documented as negative.

### 4.3.4 Checkpoints and Thresholds

Two checkpoints must ship together (`gnn_autoencoder_v1_logscale.pt` + `m5a_revived_ctx.pt`); missing one falls back to M5b-only with warning. Scores are **percentiles (0–1)**, not raw errors; thresholds tuned against old single-model `gnn_autoencoder_v1.pt` (raw) are meaningless. `model_source` records which was used. `DEFAULT_THRESHOLD=0.5` in legacy shim is uncalibrated (benign max ~0.278, GOTCHA #7).

---

## 4.4 Alert Pipeline and Dashboard (Person D — Delivery)

```
ScoredAlert ┐  score_window()   ┌→ FastAPI GET /alerts?window=60s
            ├──→ alert_pipeline ─┤→ WebSocket tail
            │  (rank_mean edge)  └→ React dashboard: filters, pagination, severity
SHAP drawer ←┘  shap_explainer.py  rank trend + ATT&CK tag
Drift banner ← drift_monitor.py (flag when cal population drifts)
```

Run: `run_detector.bat` or `powershell -ExecutionPolicy Bypass -File .\run_detector.ps1` or VS Code Run `Python: Stub Detector` on `detection/stub_detector.py` (kept as deprecated shim for dashboard import path; real code in `legacy/`). Paths are `Path(__file__).resolve().parent...` — never hardcode.

**Appended note (as in Ex-2 Fig 2.3 source):** Photo 1 analogue is a dashboard screenshot of top-35 rank queue; Fig 2.3 Total e-waste analogue is the alert rank distribution per family (see RC-27 diagnostic).

---

## 4.5 Validation and Results Summary — Week-4 Freeze (as of 2026-08-25, GPU, CUDA-deterministic, 4 seeds)

Current best is **HOSTFUSE (M5b) 60s+300s rank noisy-or + revived 87-dim M5a ctx** — heterogeneous multi-window fusion. Reproduces with one command:

```
python detection/eval_mw_ablation_4seed.py --seeds 0 1 2 3 --epochs 60
python detection/eval_feature_set_v2.py   # v2 variant
```

Requires only `data/GeneratedLabelledFlows/` (public download). Every number below is banded; nothing smaller than ~6 points is trusted until multi-seed (GOTCHA #11).

| Claim | Number | Source |
| ----- | ------ | ------ |
| Detection, CICIDS2017, v1 feats | **0.9996 ± 0.0001** | `mw_ablation_4seed.json` (reference) |
| Detection, CICIDS2017, v2 feats | **0.9997 ± 0.0001** | `feature_set_v2_results.json` (RC-30) |
| vs re-run baselines (same features) | PCA 0.9417 / IF 0.9357 / MLP-AE 0.9517 → +4.8 pts | `baselines_4seed.json` (RC-31) |
| IDS2018 attackers (external) | top-11 / 32,935 in 3 of 4 seeds (worst top-35) | `external_ids2018_multiseed.json` (RC-29) |
| CTU-13 Virut infected host | rank #1 in 4/4 seeds | `external_ctu13_multiseed.json` (RC-32) |
| CTU-13 Rbot C&C | #1 in 3/4 seeds | same |

Per-family v2 fused AUC (RC-26): PortScan/DoS/DDoS 0.9999-1.0000 (ranks 1-4), Web/Patator 1.0000 (1-5), Infiltration 0.9997 (2), Botnet 0.9987 (5-34). Recall@100 = 1.0 on both CIC datasets. P@100 structurally capped (bad/100) — do not headline (RC-27).

Closed negatives verified (do not revisit): shipped-M5a poison, temporal/LSTM neutral, LODO, k=5 sim edges, small-window filter (Ch. III §3.6.3).

---

## 4.6 Deployment Considerations — Known Weaknesses First

State weaknesses before an examiner does (as in `docs/PROJECT_GUIDE.md`):

*   **Noisy-or is batch-only** (needs window population to rank; `alert_pipeline` single-alert uses `rank_mean` edge rule, not noisy-or) — GOTCHA #17.
*   **Calibration optimism:** 20% Monday holdout; real deployments need drift-monitored re-calibration (M6 built, not yet wired into production threshold).
*   **Device sensitivity:** every number is GPU + `CUBLAS_WORKSPACE_CONFIG=:4096:8` + `cudnn.deterministic`; CPU retrain gave divergent WebAttacks (0.5048 vs 0.9948, GOTCHA #24). Record device on every number.
*   **Both checkpoints must ship** (`gnn_autoencoder_v1_logscale.pt` + `m5a_revived_ctx.pt`); one missing falls back gracefully but changes `model_source`.
*   **Near-ceiling dataset:** few attackers per day; future work replicates on UNSW-NB15 and uses pseudo-timestamps.

Failure modes and mitigations (as in Ex-2 Table 2.3):

| Component | Failure | Mitigation | Where |
| --------- | ------- | ---------- | ----- |
| CSV ingest | latin-1 vs UTF-8, junk NaN IPs | `read_flows()` + `drop_unusable_rows()` (GOTCHA #12) | `graph_builder.py` |
| Feature scaling | power-law squash | `NodeScaler(log=True)` (0.250→0.413) | `gnn_model.py` |
| Reproducibility | unseeded vs GPU nondeterminism | `set_seed()` + CUBLAS flag (GOTCHA #24) | all eval scripts |
| Portability | hard-coded `D:\Test OD\` | `Path(__file__).resolve().parent` (GOTCHA #2) | every script |
| Portability | `venv/` absolute paths | Per-machine `venv`, never copy | README |

---

## 4.7 Appendices Mapping

Per guideline: “Any code and supplementary material shall be added in the appendices.”

| Appendix | Content | Pointer |
| -------- | ------- | ------- |
| A — Schemas | `schemas/feature_vector.json v3.0` (87-dim catalogue), `ScoredAlert` dataclass, `HostScaler` params | code mirror of `detection/training_features/README.md` |
| B — Evidence (RC cards) | `experiments/report_cards.md` RC-01…RC-32 — one card per experiment with numbers + caveats | Detail behind every CHANGELOG entry |
| C — Code listing | `detection/graph_builder.py`, `gnn_model.py`, `ensembler.py`, `alert_pipeline.py`, `drift_monitor.py`, `shap_explainer.py`, eval scripts | Prod path; `experiments/` excluded from prod imports |
| D — Supplementary tables | Baselines (RC-31), external IDS2018/CTU-13 (RC-29/32), ablation 4-seed bands (RC-26), feature v2 (RC-30), harness costs (RC-14) | Reproducible JSONs listed in `docs/PAPER_OUTLINE.md` |

`CHANGELOG.md` is append-only (newest top; never edit past entries) with commit trailer `Assisted-by:`; `Knowledge/` is local-only gitignored and never pushed; `data/` and `venv/` are gitignored — each machine downloads/builds its own.

---

*Next: weeks 4–12 roadmap (`Knowledge/`): Pillar 3 host-syscall autoencoder via eBPF, AE-vs-HMM ablation, three-way score fusion — team work, B supports. Paper packaging when results freeze (`docs/PROJECT_GUIDE.md` §6) names method HOSTFUSE and protocol HELD-OUT with one-command public artifact.*

