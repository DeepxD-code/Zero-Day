# CHAPTER I — INTRODUCTION

## 1.0 Introduction

Zero-day attacks — exploits for vulnerabilities unknown to vendor or defender — drive the most consequential breaches. The zero-day has been defined as “a vulnerability in software or hardware that is unknown to the vendor and for which no patch or signature exists at the time of exploitation” (NIST SP 800-150). An intrusion detection system has been defined as “a system that monitors network or host activity for signs of malicious behaviour or policy violation and produces reports to a management station” (Debar et al., 1999). According to NIST CSF and MITRE ATT&CK any host that processes network communications and deviates from learned normality would come under anomalous behaviour. Globally, NIDS/NADS are the most commonly used terms for network defence. However, technically, zero-day detection is only a subset of anomaly detection applied to network and host behaviour.

Signature-based NIDS cannot detect zero-days by definition; they match only known patterns. This project learns *normal* network behaviour unsupervised and flags deviations, explains why, monitors drift when “normal” itself shifts, and measures what evasion would cost an attacker. Three pillars are planned: network flows (Pillar 1, Semester 7), identity/UEBA (Pillar 2), and host syscalls via eBPF (Pillar 3, weeks 4–12). This report covers Semester 7 — Pillar 1 at production depth plus scaffolding for Pillars 2/3.

This chapter provides the background, problem statement, objectives, scope, methodology preview, organisation of the report and expected outcomes.

---

## 1.1 Background

Enterprise networks generate millions of bidirectional flows. Each flow is one row: who talked to whom, which port, which protocol, how many bytes and packets, how long, and flag statistics — 80+ per-flow features per CICFlowMeter (Arash Habibi Lashkari, CIC). CICIDS2017 exists in two releases: the 79-column `MachineLearningCSV` (no IP columns, fine for per-flow baseline, useless for graphs) and the 85-column `GeneratedLabelledFlows` (has Flow ID, Source IP, Destination IP, Protocol, Timestamp — required for anything relational, latin-1 encoded). Only the latter can build host graphs.

A scanner's single flows look benign — a TCP SYN to port 22 appears normal. Its *fan-out* across a 60-second window does not: one host contacting 200 distinct peers in 60 seconds is a rate that the graph makes visible. Similarly, a DDoS victim shows many-to-one collapse, and infiltration shows a single internal host quietly exfiltrating to an external peer with unusual byte-entropy. Relational (graph) features — degree, in/out ratio, port entropy, unique peer count, flag ratios — capture these collective patterns that per-flow views discard.

The field has expanded rapidly. As per MITRE, annual new CVEs exceeded 20,000 during 2023-24. VERIZON DBIR estimates global cyber-crime cost at 8-10 Trillion USD per annum. The e-waste analogy from the reference example translates: just as WEEE comprises waste equipment not fit for original use, anomalies comprise traffic not fit for the learned model of normality — valuable if recovered, hazardous if mishandled.

| Fact (E-waste analogue) | Network analogue |
| ----------------------- | ---------------- |
| Annual e-waste India 0.8 Mt (2012), global 30-50 Mt | Annual CVEs >20k, alerts per enterprise 10k-100k/day |
| EEE contains valuables + hazardous toxics | Traffic contains benign signal + 1-8 attackers among thousands |
| Crude recovery (open burning) releases dioxins | Crude evaluation (training on attacks) leaks labels into threshold |
| WEEE composition: Plastics 30%, Oxydes 30%, Copper 20% | CICIDS2017 composition: Benign 70%, PortScan 5%, DDoS 8%, Patator 1%, Web 2% |

*Source: Umweltbundesamt (2004), MITRE, VERIZON DBIR — structure cf. Table 2.1 of e-waste example.*

### 1.1.1 Why Graphs?

Per-flow detectors treat each flow independently. Graph detectors treat a 60-second or 300-second slice as a picture: each machine is a dot, each conversation a directed line. Degree and neighbourhood structure then become first-class signals. GraphSAGE (Hamilton et al., 2017) is chosen over GCN (Kipf & Welling, 2017) because GCN's symmetric normalisation washes out the degree signal we are detecting — a design decision defended in `detection/gnn_model.py`.

Time-based windows (not fixed-count) are essential: “200 peers in 60 seconds” is a rate. Edge-level alerts (src_ip, dst_ip) are required because the frozen `ScoredAlert` schema needs both endpoints; a node-only score cannot map to an alert an analyst can act on.

---

## 1.2 Problem Statement

Four problems motivate this work — each mirrors a gotcha the project has already encountered and measured.

**P1. Closed-world classifiers overstate zero-day performance.** When training and testing families overlap, a classifier memorises family boundaries and reports 0.97+ AUC. Under held-out evaluation (train on benign Monday only, test on a family never seen), many methods collapse to 0.47 (worse than random on WebAttacks, GOTCHA #22). Accuracy and even P@100 mislead under extreme class imbalance.

**P2. Per-flow detectors are structurally blind.** A scanner's individual flows are benign-looking; only the fan-out across a window reveals it. Per-flow autoencoders (M5a) swing 0.42–0.98 across families, while the host-graph model (M5b) never drops below 0.906 — a consistency gap that the baseline-vs-GNN ablation is designed to demonstrate.

**P3. Power-law scaling squashes small attackers.** Raw host counts (bytes, degrees) are power-law distributed: the busiest host maps to 1.0 and every other host squashes near 0, so a few huge servers permanently own the top of the alert queue. Patator and WebAttacks were stuck at P@100 = 0.000 across 294 runs until `NodeScaler(log=True)` (log1p before min-max) fixed it to 0.618 and 0.381 respectively — the single biggest win (GOTCHA #14).

**P4. Uncalibrated, single-scale scores fuse incorrectly.** Raw M5a error (0.038–0.122) versus a rank (0-1) meant `max` picked the relational score on 99.9% of alerts, so every alert before 2026-08-12 was M5b alone regardless of `model_source` (GOTCHA #21). No single window captures both bursty scans (60s) and slow exfiltration (300s); fusion must calibrate then rank.

These mirror the e-waste chapter's hazard framing: valuable signal plus hazardous mishandling that is difficult to recycle in an environmentally sustainable manner even in developed evaluation practices.

---

## 1.3 Objectives

The primary objective is the **controlled baseline-vs-GNN ablation** — the individually attributable headline result of Detection Modelling (Deep), not “we built a GNN”.

1.  **Baseline-vs-graph ablation (M5a vs M5b vs M5c).** Train a per-flow autoencoder (M5a, 87-dim with 11 window-context dims) and a GraphSAGE host-graph autoencoder (M5b, 8/19-dim) under identical held-out conditions; report the consistency gap and fuse them (M5c) only where it helps.

2.  **Multi-window calibrated fusion.** Build 60s and 300s host graphs, calibrate each window's reconstruction error to a percentile against a 20% Monday holdout, and fuse by within-window rank with noisy-or (`1 - Π(1-p)`). Production default is M5b-only where shipped-M5a hurts (see GOTCHA #22).

3.  **Honest, reproducible held-out protocol.** Train on benign Monday only; evaluate on 7 unseen families (PortScan/DoS/DDoS/Web/Patator/Infiltration/Botnet) one-by-one; report mean ± std over 4 seeded GPU-deterministic runs (`set_seed()` adds `cuda.manual_seed_all`, `cudnn.deterministic=True`, `CUBLAS_WORKSPACE_CONFIG`). Any difference smaller than ~6 points between two configurations is noise (GOTCHA #11).

4.  **Drift-aware scoring, explanations and adversarial costing.** Wire `DetectorDriftMonitors` (M6) on three score streams, provide SHAP attributions (M7) and ATT&CK mapping, and quantify evasion cost via the red-team harness (D) — slow scan 20× time, distributed scan 16 machines, camouflage/port-hiding ineffective.

---

## 1.4 Scope

**In scope (Semester 7, Deep — Detection Modelling):**

*   Flow ingestion and schema mapping (`capture/schema_mapper.py`) handling all three naming conventions (CIC 79-col, 85-col, and IDS2018 `Tot Fwd Pkts` variant).
*   Host-graph construction per time window, `graph_health()` gates, v1 (8) and v2 (19) feature sets, `NodeScaler(log=True)` default.
*   GraphSAGE autoencoder training on benign only, 5-member ensemble checkpoint `gnn_autoencoder_v1_logscale.pt` (+ v2 variant), percentile calibration.
*   Multi-window rank fusion and edge-level alert emission (`alert_pipeline.score_window()`), 4-seed GPU-deterministic evaluation (`eval_mw_ablation_4seed.py`).
*   Drift monitoring scaffolding, SHAP interface, and harness measurement on the frozen model.

**Team mapping (CLAUDE.md):**

| Member | Track | Owns |
| ------ | ----- | ---- |
| A — Saharsh | Data & Capture | flow capture, `FlowRecord`, `pcap_to_flows`, `schema_mapper` |
| **B — Deep** | **Detection Modeling** | **baseline AE, GNN-temporal, drift monitor, ensembler (this report)** |
| C — Aditya | Trust & Risk | SHAP, learned UEBA risk model, ATT&CK mapper, privacy pass |
| D — Avinash | Adversarial & Delivery | red-team harness, FastAPI + React dashboard, alert API |

**Out of scope for Semester 7 (roadmap weeks 4–12, Knowledge/):** full UEBA behaviour models, eBPF syscall host autoencoder (Pillar 3) and three-way score fusion, federated sharing, and paper packaging — B supports.

**Dataset gate:** Primary training/evaluation is CICIDS2017 `GeneratedLabelledFlows/TrafficLabelling/` (Mon 2017-07-03 benign → Fri 2017-07-07 attacks, latin-1). External replication on IDS2018 (`Thuesday-20-02-2018` only graphable, 9/10 lack IPs) and CTU-13. Synthetic `training_data/` is excluded — its graphs collapse (508 clients → 2 services) or degenerate (12,503 services).

---

## 1.5 Methodology — Summary

Flows → host graphs → anomaly scores → ranked alerts, evaluated under HELD-OUT.

```
network flows            →  graphs per time window   →  anomaly scores  →  alerts
(CSV rows, 85 cols)         (hosts = nodes,             (reconstruction     (top of
                             flows = directed edges)      error → percentile) queue)
     A captures              B builds (graph_builder)     B trains (M5b)     B fuses (M5c)
```

1.  **Flows.** Every bidirectional conversation is one row with 76 CIC flow stats + 11 window-context dims (87-dim). Reads via `graph_builder.read_flows()` (latin-1, drops 63% junk rows on Thursday WebAttacks).
2.  **Graphs.** For every 60s and every 300s slice, draw a directed graph: each host is a node, each flow a directed edge. No self-loops, no multi-edge collapse. Health check before training.
3.  **Detector (M5b).** A small GraphSAGE autoencoder (2× SAGEConv, hidden 32, latent 8 = in_dim) learns to reconstruct normal graphs. A host it cannot reconstruct gets a high anomaly score. `NodeScaler(log=True)` log1p before min-max is default since 2026-08-12.
4.  **Fusion (M5c).** Scores from 60s and 300s views are percentile-calibrated against 20% Monday holdout and fused by within-window rank noisy-or. Edge features are also scored (`edge_score="rank_mean"` lifts edge AUC 0.712→0.789).
5.  **Alerts.** Highest-scoring hosts (and their edges) become `ScoredAlert[src_ip, dst_ip, score, rank]` ranked queue. SHAP explains which feature fired; drift monitor watches for distribution shift; harness measures evasion cost.

Evaluation: **HELD-OUT** (train benign Monday only, test each of 7 families unseen, repeat over seeds 0-3, CUDA-deterministic). Quote node AUC for modelling claims, edge AUC for operational claims (gap 22 points).

Detail lives in Chapter III; design in Chapter IV.

---

## 1.6 Organisation of the Report

The report is organised into four chapters plus references and appendices, following the documentation guideline (1.8 DOCUMENTATION) exemplified by the extracted samples (pp. 43-73 and pp. 9-22).

*   **Chapter I — Introduction.** Context, background, problem statement, objectives, scope, methodology preview, organisation and expected outcomes (this chapter).
*   **Chapter II — Review of Literature.** Categorised review of IDS taxonomies, flow datasets, autoencoders, graph detection, fusion, explainability/drift/adversarial, Indian/global performance and policies (presentation 10–15 September to individual guides).
*   **Chapter III — Methodology.** Data description, preprocessing, graph construction, HostScaler, GraphSAGE autoencoder, calibration, multi-window fusion, HELD-OUT protocol, metrics, reproducibility and tools/environment.
*   **Chapter IV — Design and Modelling.** System architecture (three pillars, four-person mapping), data flow, module map, modelling details (feature sets, windows, checkpoints), alert pipeline and dashboard, validation summary, deployment considerations and appendices mapping.
*   **References.** Separate list at the end, complete formatted bibliography (IEEE style or guide-mandated superscript roman as in sample).
*   **Appendices.** Code listings (`detection/`), schemas (`feature_vector.json v3.0`, `ScoredAlert`), supplementary material (report cards RC-01…RC-32, baseline and external replication tables) — as per guideline “any code and supplementary material shall be added in the appendices.”

This matches the sample structure: Chapter II carries 2.0 Introduction through 2.8 Summary with Tables 2.1–2.5 and Figures 2.1–2.3.

---

## 1.7 Expected Outcome

**Headline (production recipe, 4-seed GPU-deterministic, 2026-08-25 freeze):**

*   GNN-logscale 60s+300s + revived 87-dim ctx M5a, within-window rank noisy-or → **mean ROC-AUC 0.9996 ± 0.0001** across 7 held-out families (`eval_mw_ablation_4seed.py --seeds 0 1 2 3`); with v2 features (19) → **0.9997 ± 0.0001** (`eval_feature_set_v2.py`). Served live in `alert_pipeline.score_window()`. Beats all re-run baselines under identical conditions: PCA 0.9417, Isolation Forest 0.9357, plain MLP-AE 0.9517 (RC-31, +4.8 pts).

**Operational claim (quote this, not P@100):**

| Family | AUC (v2 fused) | Attacker ranks |
| ------ | -------------- | -------------- |
| PortScan / DoS / DDoS | 0.9999–1.0000 | 1–4 |
| WebAttacks / Patator | 1.0000 | 1–5 |
| Infiltration | 0.9997 | 2 |
| Botnet | 0.9987 | 5–34 |

Every attacker ranks in the **top ~35 of thousands** on CICIDS2017; **top-11 of 32,935 on IDS2018 in 3 of 4 seeds** (worst top-35, recall@100 = 1.0 on both); infected host **#1 on CTU-13 Virut in 4/4 seeds**, Rbot C&C #1 in 3/4. Host-level P@100 is structurally capped at bad/100 — do not headline it (RC-27).

**Robustness:** Evasion is expensive — slow scan requires 20× time, distributed scan 16 machines; camouflage and port-hiding do not work (RC-14). Known weaknesses: noisy-or is batch-only (needs population), both checkpoints must ship together, calibration optimism (20% holdout), device-sensitive arithmetic — every number above is GPU + determinism flags.

**Contribution map:** The ablation (per-flow vs relational vs fused) is the thesis spine for paper packaging (HOSTFUSE — HOST-graph Fusion of Unsupervised reconstruction Scores, HELD-OUT protocol, one-command artifact `python detection/eval_mw_ablation_4seed.py --seeds 0 1 2 3 --epochs 60`).

