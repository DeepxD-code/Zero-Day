# CHAPTER IV
## DESIGN AND MODELLING

### 4.0 Introduction
System architecture, component design, data flow, and modelling choices.

### 4.1 System Architecture (Pillars)
```
[Pillar 1: Network]  capture/schema_mapper → pcap_to_flows → graph_builder → gnn_model → ensembler/alert_pipeline → dashboard (FastAPI+React)
[Pillar 2: UEBA]     identity logs → risk model (Aditya, aux)
[Pillar 3: Host]     eBPF syscall watcher (capture/ebpf_syscall_watcher.py) → host AE (weeks 4-12)
                              ↓
                 drift_monitor (M6) + shap_explainer (M7) + harness (D)
```
Four-person mapping (CLAUDE.md): A Data/Capture, B Detection Modelling, C Trust/Risk, D Adversarial/Delivery.

### 4.2 Data Flow & Module Map

<p style="text-align:center;"><strong>Table 4.1. System module map — stage, implementation module and I/O.</strong></p>

| S.No. | Stage | Module | I/O |
|:-----:|-------|--------|-----|
| 1 | Ingest | `capture/schema_mapper.py` | CSV → canonical schema (handles 79/85-col + IDS2018 naming) |
| 2 | Ingest | `capture/pcap_to_flows.py`, `capture/ebpf_syscall_watcher.py` | pcap / eBPF → flows / syscall streams |
| 3 | Build | `detection/graph_builder.py` | flows → List[Data] per window (x=[N,8/19], edge_index, edge_attr, y) |
| 4 | Scale | `detection/gnn_model.py:NodeScaler` | log1p → min-max fitted on benign only |
| 5 | Train | `detection/gnn_model.py` | benign graphs → `gnn_autoencoder_v1_logscale.pt` (ensemble v1, v2 variant) |
| 6 | Score | `detection/alert_pipeline.py` | window → ScoredAlert[src_ip,dst_ip,score,rank] (edge_score="rank_mean") |
| 7 | Fuse | `detection/ensembler.py` | 60s+300s (+M5a ctx) → noisyor fused rank |
| 8 | Eval | `detection/eval_mw_ablation_4seed.py` | 6-config × 4-seed ablation → headline table |
| 9 | Monitor | `detection/drift_monitor.py` | score streams → drift flag |
| 10 | Explain | `detection/shap_explainer.py` | host embedding → SHAP values + ATT&CK tag |

<p style="font-size:10pt;"><em>Source: Compiled from detection/ module implementations; cf. detection/README.md.</em></p>

### 4.3 Modelling Details
- **GraphAutoencoder:** 2× SAGEConv (hidden 32, default), latent 8, ReLU, decoder = inner-product / MLP reconstruction of x and edge_attr. Loss = MSE (node) + MSE (edge). Latent 2→12 moves mean 0.003 (GOTCHA #9) — do not tune width.
- **Feature sets:** v1 (8): degree in/out, bytes in/out, flow count, duration stats; v2 (19): + port entropy, unique peers, flag ratios, IAT stats. `feature_set` guard refuses v2 scoring without 19-dim checkpoint.
- **Windows:** 60s (burst) + 300s (sustained) fused after calibration. Extending to 1800s raises AUC 0.917→0.983 but halves P@100 (GOTCHA #8).
- **Checkpoints:** `gnn_autoencoder_v1_logscale.pt` + `m5a_revived_ctx.pt` must ship together; single-model vs ensemble auto-detected.

### 4.4 Alert Pipeline & Dashboard (Person D)
`alert_pipeline.score_window()` → ranked `ScoredAlert` list → FastAPI `/alerts` → React dashboard (filter, explain drawer). Baseline `stub_detector.py` kept as shim import path (deprecated).

### 4.5 Validation & Results Summary (Week-4 Freeze)
Production: v1 HOSTFUSE 0.9996±0.0001; v2 0.9997±0.0001 (`eval_feature_set_v2.py`). External: IDS2018 top-11/32,935 (3/4 seeds), CTU-13 Virut #1 (4/4). Ablations confirm negatives listed in Ch 3.6.

### 4.6 Deployment Considerations
- Seeded determinism flags on every eval; device recorded.
- Thresholding on percentiles; drift monitor governs re-calibration.
- Failure modes: missing IPs → health reject; naive scaling → LogScaler; portable venv → per-machine build.

### 4.7 Appendices Mapping
A: Schemas (`schemas/feature_vector.json v3.0`, `ScoredAlert`) · B: RC cards (`experiments/report_cards.md` RC-01…RC-32) · C: Code listing (detection/*.py) · D: Supplementary (baselines, external replications).
