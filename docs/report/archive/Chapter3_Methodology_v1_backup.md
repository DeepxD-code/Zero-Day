# CHAPTER III
## METHODOLOGY

### 3.0 Introduction
This chapter details data, graph construction, model, fusion and evaluation methodology, with reproducibility constraints.

### 3.1 Datasets and Preprocessing
- **Primary:** CICIDS2017 `GeneratedLabelledFlows/TrafficLabelling/` (Mon 2017-07-03 benign → Fri 2017-07-07). Only release with IPs; latin-1; `graph_builder.read_flows()` handles it. Thursday WebAttacks CSV 63% junk (458k rows, 170k labelled) → `drop_unusable_rows()` (GOTCHA #12).
- **Schema mapping:** `capture/schema_mapper.py` identifies 76 CIC flow cols vs A's CICFlowMeter convention (Destination Port as metadata — both handled GOTCHA #4). Never `dropna(axis=1)` per file (GOTCHA #5) — pin column list via `ensembler.pin_canonical()`.
- **Health gate:** `graph_health()` rejects collapsed graphs (synthetic 508 clients → 2 services, or `dst_port` as counter → 12,503 services, GOTCHA #6).
- **External:** IDS2018 `Thuesday-20-02-2018` only graphable (GOTCHA #13); CTU-13 flows.

### 3.2 Host-Graph Construction (`graph_builder.py`)
- **Window:** time-based 60s and 300s (not fixed-count — "200 peers in 60s" is a rate). Overlapping families measured RC-02: 60s maximises P@100; we fuse both.
- **Nodes = hosts, Edges = directed** (scan vs DDoS distinct; GCN symmetric norm would wash out degree → SAGEConv chosen).
- **Node features:** v1=8, v2=19 (`feature_set="v2"` adds entropy, diversity, flags). Indices 0–7 stable; never unpack positionally (GOTCHA #23). Edge features (bytes, pkts, duration) are also scored now — biggest operational win (GOTCHA #19: edge alone 0.7359 > node-derived).
- **Scaler:** `NodeScaler(log=True)` log1p before min-max (default since 2026-08-12; checkpoints before carry no `log` key → loaded as False).

### 3.3 Models
- **M5a per-flow AE:** 87-dim (76 flow + 11 window-context), revived `m5a_revived_ctx.pt`. M5a-L (`stub_detector.py`/`legacy/autoencoder.py`) deprecated.
- **M5b GNN AE:** `GraphAutoencoder` (GraphSAGE encoder, latent default 8 = in_dim — no bottleneck by width, so capacity via features not latent, GOTCHAs #9/#15). Trained benign-only, unsupervised reconstruction loss.
- **Determinism:** `set_seed(seed)` sets `torch.manual_seed`, `cuda.manual_seed_all`, `cudnn.deterministic=True`, `benchmark=False`, `CUBLAS_WORKSPACE_CONFIG=:4096:8` (GOTCHA #24). Always pass `--seed`.

### 3.4 Fusion and Scoring (`ensembler.py`, `alert_pipeline.py`)
- Calibration: per-window percentile vs 20% Monday holdout (80/20). Ensemble checkpoint emits percentiles.
- Fusion: within-window rank → noisyor `1-Π(1-p)`. `fused_rank_max` also evaluated (batch-only, GOTCHA #17). Edge score default `rank_mean` (node + edge error ranking lifts edge AUC 0.7124→0.7892).
- Alert: `score_window(feature_columns=None, threshold=None)` — RC-26 default M5b-only (omitting feature_columns) gives highest edge AUC 0.8322; uniform M5a fusion hurts (WebAttacks 0.476→0.171 with rolling cal, GOTCHA #22). `model_source` records single vs ensemble.

### 3.5 Drift, Explainability, Harness
- **M6 Drift:** `DetectorDriftMonitors` on three streams, wired via `alert_pipeline.init_drift_monitors()` (queue noise is drift, RC-28).
- **M7 SHAP:** `shap_explainer.py` (Person C) — host-window attributions.
- **Harness D:** `harness/graph_techniques.py` 4 evasion attacks; `run_graph_harness.py` measures attacker cost (RC-14).

### 3.6 Evaluation Protocol (HELD-OUT)
- **HELD-OUT:** held-out-family; train Monday benign only → test each attack day family unseen. Report mean±std over seeds 0–3 (`eval_mw_ablation_4seed.py` reference, `epochs 60`). Quote node AUC for modelling claims, edge AUC for operational claims (gap 22 pts, GOTCHA #16).
- **Metrics:** ROC-AUC (ranking), attacker rank & recall@100 (operational), P@100 diagnostic only (structurally capped at bad/100, RC-27; 60s vs 1800s trade 0.244→0.093).
- **Closed negatives documented:** LODO worse, k=5 sim edges hurt, temporal half negative, small-window filtering null — do not revisit (see `experiments/report_cards.md` RC-20…RC-32).

### 3.7 Tools and Environment
Python 3.11, PyTorch 2.5.1+cu121, PyG, `venv` per-machine (never portable, never committed). Paths via `Path(__file__).resolve().parent`. Requirements: `requirements.txt`. One-command artifact: `python detection/eval_mw_ablation_4seed.py --seeds 0 1 2 3 --epochs 60` (GPU, deterministic).
