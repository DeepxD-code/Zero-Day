# CHAPTER I
## INTRODUCTION

### 1.0 Introduction
Zero-day attacks — exploits for vulnerabilities unknown to vendor or defender — drive the most consequential breaches. Signature-based NIDS cannot detect them by definition; they match only known patterns. This project learns *normal* network behaviour unsupervised and flags deviations, explains why, monitors drift, and measures evasion cost. Three pillars are planned: network flows (Semester 7), identity/UEBA (P2), and host syscalls via eBPF (P3, weeks 4–6). This report covers Semester 7, Pillars 1 + scaffolding for 2/3.

### 1.1 Background
Enterprise networks generate millions of bidirectional flows (5-tuple + statistics per CICFlowMeter). A scanner's single flows look benign; its *fan-out* across a 60s window does not. Similarly, a DDoS victim shows many-to-one collapse. Relational (graph) features — degree, entropy, port diversity — capture these collective patterns.

### 1.2 Problem Statement
- Closed-world classifiers overstate zero-day performance when trained/tested on overlapping families.
- Per-flow detectors miss structurally defined attacks (PortScan, DDoS, Infiltration topologies).
- Power-law scaling squashes small attackers; uncalibrated multi-scale scores fuse incorrectly.
- Operational metrics (accuracy, P@100) mislead under extreme class imbalance (1–8 attackers among thousands).

### 1.3 Objectives
1. Baseline vs graph ablation: controlled comparison (M5a per-flow AE vs M5b GraphSAGE host AE vs fusion M5c).
2. Multi-window fusion (60s+300s) with percentile calibration and rank-based noisyor.
3. Honest held-out-family protocol with 4-seed GPU-deterministic bands.
4. Drift-aware scoring and SHAP explanations; adversarial harness to quantify evasion cost.

### 1.4 Scope
Semester 7: Detection Modelling (Deep). Data & Capture owned by A, Trust & Risk by C, Adversarial & Delivery by D. Dataset gate: CICIDS2017 `GeneratedLabelledFlows` (85 cols, has IPs). Holdings: `gnn_autoencoder_v1_logscale.pt` + `m5a_revived_ctx.pt` (ensemble + revived checkpoints). Out of scope for Sem 7: full UEBA and eBPF host models (roadmap weeks 4–12).

### 1.5 Methodology (summary)
Flows → host graphs per time window (nodes=hosts, edges=directed, `graph_builder.py`) → GraphSAGE autoencoder trained benign-only (M5b, `gnn_model.py`, LogScaler) → multi-window rank noisyor fusion (M5c, `eval_mw_ablation_4seed.py`) → edge-level `ScoredAlert` queue (`alert_pipeline.py`) with SHAP + drift monitors (M6/M7). Evaluation: HELD-OUT, 7 families, 4 seeds.

### 1.6 Organisation of Report
Ch 2 Literature Review; Ch 3 Methodology; Ch 4 Design & Modelling; References; Appendices (code, schemas, RC cards).

### 1.7 Expected Outcome
Mean ROC-AUC 0.9996±0.0001 (v2: 0.9997) across 7 unseen families, attackers in top ~35 of thousands (recall@100=1.0), replicated on IDS2018 and CTU-13, with quantified evasion cost (slow scan 20×, distributed 16×).
