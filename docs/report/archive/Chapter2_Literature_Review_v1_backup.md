# CHAPTER II
## REVIEW OF LITERATURE

### 2.0 Introduction

This chapter presents a review of related literature relevant to the present study — **drift-aware explainable anomaly detection for zero-day behavioral threat hunting**. The review provides an overview of theory and research literature with special emphasis on literature specific to network intrusion detection, unsupervised anomaly detection, graph representation of network flows, and evaluation protocols for unseen attack families.

The sources consulted include primary periodicals (IEEE S&P, CCS, NDSS, TDSC, TIFS), secondary databases (IEEE Xplore, Scopus, Web of Science), conference proceedings, technical reports (CIC, UNSW), and benchmark datasets. The review is categorized under the following headings:

1. Intrusion Detection Systems: Taxonomy and Evolution
2. Flow-based Features and Benchmark Datasets
3. Reconstruction-based Anomaly Detection: Autoencoders and Baselines
4. Graph-based and Relational Detection
5. Multi-scale Fusion, Calibration and Ensemble Methods
6. Explainability, Drift Monitoring and Adversarial Evaluation
7. Research Gaps and Summary

The grouping is broader with fuzzy boundaries, categorized based on major findings projected by investigators.

---

### 2.1 Intrusion Detection Systems: Taxonomy and Evolution

The field of intrusion detection has been subjected to systematic taxonomies since early 2000s.

**Debar et al. (2000)** and **Axelsson (2000)** distinguished misuse (signature-based) from anomaly-based detection. Signature systems match known patterns with high precision but by definition cannot detect zero-day families absent from training labels — a limitation that motivates the present work's unsupervised premise.

**Chandola et al. (2009)** surveyed anomaly detection across domains, formalizing point, contextual and collective anomalies. Network intrusions are collective: a single flow rarely defines an attack; the *pattern* of flows from a host within a time window does. This justifies host-window as the unit of scoring (cf. `graph_builder.py` design decision — nodes = hosts, edges = directed flows, time-based windows).

**Garcia-Teodoro et al. (2009)** and **Bhuyan et al. (2014)** reviewed anomaly NIDS, noting chronic evaluation flaws: training and testing on overlapping attack families, reporting accuracy on imbalanced data, and ignoring drift. Our HELD-OUT protocol (train benign Monday only, evaluate 7 unseen families) directly addresses this.

**Sommer & Paxson (2010)** warned that "outside the closed world" performance collapses when lab assumptions meet operational traffic — a finding mirrored in our result that LODO training on 2,209 graphs (vs Monday's 487) dropped mean ROC-AUC 0.9300 → 0.8405: an attack day's "benign" half is not clean normality (GOTCHA #10, `CHANGELOG.md`).

*Gap addressed:* classifier-based NIDS learns closed-world label boundaries; we adopt autoencoding of normality, so unseen families are detectable without retraining.

---

### 2.2 Flow-based Features and Benchmark Datasets

**2.2.1 Feature Engineering**

Early flow exporters (NetFlow, IPFIX) defined 5-tuple plus counters. **Moore et al. (2005)** catalogued 249 discriminators; **Williams et al. (2006)** showed that port and protocol alone are brittle under evasion (ephemeral ports, tunnelling).

**CICFlowMeter (Arash Habibi Lashkari, CIC)** extracts 80+ statistics per bidirectional flow (packet lengths, inter-arrival times, flag counts). CICIDS2017 exists in two releases — 79 columns without IPs (`MachineLearningCSV/`) and 85 columns with Flow ID/Source IP/Destination IP/Protocol/Timestamp (`GeneratedLabelledFlows/`, latin-1 encoded) — only the latter can build host graphs (GOTCHA #3, `capture/schema_mapper.py`). Our `Feature catalogue` freezes 87-dim flow vectors (76 CIC + 11 window-context) and 8/19-dim host aggregates.

**2.2.2 Datasets**

- **CICIDS2017 (Sharafaldin et al., 2018):** Monday benign + 7 attack days (Tuesday–Friday). De facto standard for held-out-family studies, but single-lab, single benign day — calibration optimism noted (20% Monday holdout, RC-26).
- **CSE-CIC-IDS2018 (Sharafaldin et al., 2018):** 10 CSVs, 9 without IPs; only `Thuesday-20-02-2018` builds graphs; column naming drifts (`Tot Fwd Pkts` vs `Total Fwd Packets`, bytes_sent silently zero — GOTCHA #13).
- **CTU-13 (Garcia et al., 2014):** 13 botnet captures, host-level ground truth, used for external replication (Virut host #1 in 4/4 seeds).
- **UNSW-NB15 (Moustafa & Slay, 2015):** hybrid real-synthetic, planned third replication (pseudo-timestamps required).

**Heng et al. (2024)** and **Ring et al. (2019)** critiqued dataset realism (synthetic benign, artefactual port distributions) — we verify graph health before training (`graph_health()` rejects collapsed or degenerate topologies, GOTCHA #6).

---

### 2.3 Reconstruction-based Anomaly Detection: Autoencoders and Baselines

**Hodge & Austin (2004)** and **Patcha & Park (2007)** surveyed statistical and ML anomaly detectors. Reconstruction error as anomaly score — train to rebuild normal, flag high error — became dominant.

**Sakurada & Yairi (2014)** demonstrated autoencoders for novelty detection; **An & Cho (2015)** variational variant. Principle: if the encoder bottleneck is narrow, identity mapping is impossible; normal data reconstructs well, anomalies do not.

Our **M5a per-flow AE** (76/87-dim) instantiates this. Its weakness is contextual blindness: a benign-looking flow from a scanner is individually normal.

<p style="text-align:center;"><strong>Table 2.1. Baseline comparison under identical features and held-out protocol.</strong></p>

| Model | Mean AUC | Note |
|:------|:--------:|:-----|
| PCA | 0.9417 | linear subspace |
| Isolation Forest | 0.9357 | tree isolation |
| Plain MLP-AE | 0.9517 | no graph context |
| **Ours (HOSTFUSE)** | **0.9996 ±0.0001** | graph + fusion |

<p style="font-size:10pt;"><em>Source: eval_baselines_4seed.py (RC-31), GPU, CUDA-deterministic, 4 seeds (0–3), 87-dim flow features, 19-dim host features.</em></p>

Isolation Forest (**Liu et al., 2008**) and One-Class SVM (**Schölkopf et al., 1999**) remain common baselines but ignore relational structure.

*Calibration note:* raw reconstruction distances (0.038–0.122) are uncalibrated; percentile calibration against benign holdout is required before fusion (GOTCHAs #18, #21). `DEFAULT_THRESHOLD=0.5` is uncalibrated (benign max ~0.278).

---

### 2.4 Graph-based and Relational Detection

Traffic is naturally relational: hosts are nodes, flows are directed edges. Per-flow models discard degree, fan-out and neighbourhood structure that define scan, DDoS and infiltration.

**Graph Neural Networks:** **Kipf & Welling (2017)** GCN uses symmetric normalisation that washes out degree signal; we use **Hamilton et al. (2017)** GraphSAGE with mean aggregation that preserves it (design decision, `gnn_model.py`).

**Network security adaptations:**

- **Kitsune (Mirsky et al., 2018):** ensemble of small AEs per feature cluster, packet-level, no graph — strong online baseline but per-flow.
- **PIKACHU (Alsham et al., 2022):** host-graph AE, reported 0.977 mean AUC on CICIDS2017 but grid-searched window/threshold *on* attack families (evaluation contamination). Our HELD-OUT protocol forbids this; we exceed PIKACHU (0.9996) without seeing attacks.
- **E-GraphSAGE (Lo et al., 2022):** edge-featured GraphSAGE for supervised classification — shares architecture, differs in objective (classifier vs autoencoder; we deliberately avoid supervised scoring to preserve ablation comparability).
- **Anomal-E (Cavanaugh et al., 2022):** self-supervised edge embeddings.
- **Euler / ARGUS:** temporal GNNs adding RNN layers.

**Node features (our HostScaler):** 8-dim base (degree, bytes, duration, etc.) or 19-dim v2 (adds entropy, port diversity, flag ratios). `NodeScaler(log=True)` applies log1p before min-max — single biggest win (P@100 0.250→0.413, Patator 0.000→0.618) because raw power-law counts squash all but the busiest host near zero (GOTCHA #14). Temporal variant `gnn_temporal_fused.py` (GNN+LSTM) was measured negative at edge-level (RC-20) and retained for ablation only.

*Graph construction:* 60s and 300s time windows (rate vs volume trade-off; 60s maximises P@100, `CHANGELOG.md` RC-02), directed, no self-loops, no multi-edge collapse. Flow IDs and timestamps required — synthetic datasets with identical services or incrementing dst_port fail health checks.

---

### 2.5 Multi-scale Fusion, Calibration and Ensemble Methods

No single window captures both bursty scans (60s) and slow exfiltration (300s). Multi-scale fusion is needed but naive score averaging fails: raw errors and ranks live on incomparable scales (GOTCHA #21: fusing uncalibrated M5a 0.038–0.122 vs rank 0–1 meant max picked M5b on 99.9% alerts).

**Calibration:** Per-window percentile against Monday holdout (80/20 split) maps errors to [0,1] uniformly under normality. Checkpoint carries calibrator; missing checkpoint falls back with `RuntimeWarning` (RC-26).

**Fusion rules evaluated (6 configs, 4 seeds, `eval_mw_ablation_4seed.py`):**

- `mean` / `max` on calibrated scores — `max` lets saturated M5a overwrite M5b (M5a saturates at 0.999–1.000 on every attack day, GOTCHA #20).
- `rank_mean` — ranking within window population before averaging; only window-local.
- `fused_rank_max` — rank positions vs values; beats both detectors (+0.0398 AUC) but costs P@100 and is batch-only (needs population).
- `noisyor` — `1 - Π(1-p)` under independence; best headline: **GNN-logscale 60s+300s + revived 87-dim ctx M5a, within-window rank noisyor → 0.9996±0.0001** (v2: 0.9997±0.0001). Production `alert_pipeline.score_window()` serves this.

**Ensembling:** `gnn_autoencoder_v1.pt` is a 5-member ensemble; scores emitted are percentiles, not raw errors. Thresholds tuned on single-model checkpoints are invalid (GOTCHA #18).

---

### 2.6 Explainability, Drift Monitoring and Adversarial Evaluation

**2.6.1 Explainability**

Operational SOCs require *why* an alert fired. **Lundberg & Lee (2017)** SHAP provides additive feature attributions. Person C's `shap_explainer.py` attributes host-window scores to input dimensions (e.g., out_degree spike for PortScan). ATT&CK mapping translates features to tactics (Reconnaissance, Resource Development).

**2.6.2 Concept Drift**

Normal drifts (new services, diurnal shifts). Score distributions shift; a fixed threshold either floods or blinds. **Gama et al. (2014)** taxonomy of drift detectors; unsupervised score drift is hardest.

Our **M6 `drift_monitor.py`** (`DetectorDriftMonitors` wired via `alert_pipeline.init_drift_monitors()`) watches three streams (M5a error, M5b error, fused rank) with rolling windows, flagging when benign drift would push queue noise above signal (RC-28: small-window filtering changes nothing — queue noise is drift, not variance). Weeks 4–12 roadmap extends to Pillar 3 (eBPF syscall host model) and three-way fusion.

**2.6.3 Adversarial Robustness**

Attackers adapt. **Grosse et al. (2017)** and **Apruzzese et al. (2023)** showed NIDS evasion via traffic shaping.

Person D's harness (`harness/graph_techniques.py`, `harness/run_graph_harness.py`, RC-14) tests four techniques against M5b:

<p style="text-align:center;"><strong>Table 2.2. Adversarial evasion techniques against M5b and attacker cost (RC-14).</strong></p>

| S.No. | Technique | Effect |
|:-----:|-----------|:------:|
| 1 | Port-hiding / camouflage | No effect |
| 2 | Slow scan (rate ↓ 20×) | Evasion succeeds but cost = 20× time |
| 3 | 16-way distributed scan | Succeeds but cost = 16 machines |

<p style="font-size:10pt;"><em>Source: harness/run_graph_harness.py; evasion measured as attacker rank drop below detection threshold on CICIDS2017.</em></p>

Result: evasion is *expensive*, not impossible — a defensible operational claim.

**Privacy:** federated or anonymised sharing is out-of-scope for semester 7; `Trust & Risk` track implements k-anonymity pass on exported features.

---

### 2.7 Research Gaps and Summary

<p style="text-align:center;"><strong>Table 2.3. Research gaps in literature and how this project fills them.</strong></p>

| S.No. | Gap in literature | How this project fills it |
|:-----:|-------------------|---------------------------|
| 1 | Evaluation on overlapping families overstates zero-day performance | **HELD-OUT protocol** — 7 families held-out one-by-one, mean±std over 4 seeded GPU-deterministic runs (`set_seed()` adds `cuda.manual_seed_all`, `cudnn.deterministic=True`, `CUBLAS_WORKSPACE_CONFIG`, GOTCHA #24) |
| 2 | Single-window, single-scale views | **Multi-window rank noisyor** (60s+300s) |
| 3 | Power-law feature squashing hides small attackers | **LogScaler** (log1p before scaling) |
| 4 | Scores reported at node-level inflate claims | **Edge-level alerts** (`ScoredAlert` with src_ip/dst_ip; node 0.8965 vs edge 0.6740 gap documented, `alert_pipeline` default `edge_score="rank_mean"` lifts edge AUC 0.7124→0.7892) |
| 5 | No reproducibility band; device variance ignored | **4-seed bands, device-annotated numbers** (single-seed differences <6 pts are noise, GOTCHA #11) |
| 6 | Explainability and drift treated separately | **Joint SHAP + drift monitors** per stream |

<p style="font-size:10pt;"><em>Source: Synthesis from report cards RC-02, RC-11, RC-14, RC-16, RC-24, RC-27, RC-28; see experiments/report_cards.md.</em></p>

**Summary.** Literature establishes that unsupervised reconstruction excels for unknown families, that graph context captures collective behaviours invisible per-flow, and that careful calibration/fusion and honest held-out evaluation are indispensable. This project synthesises those threads into HOSTFUSE and evaluates it under a protocol designed to survive the critiques of Sommer & Paxson and Bhuyan et al.

*Operational claim to quote:* attackers rank in top ~35 of thousands on CICIDS2017 and top-11 of 32,935 on IDS2018 (3/4 seeds); infected host #1 on CTU-13 Virut (4/4 seeds) — host-level P@100 is structurally capped at `bad/100` and is not a headline metric (RC-27).

---

**References (selected — full list in `References.md`)**

- Axelsson, S. (2000). Intrusion detection systems: A survey. *TR.*
- Bhuyan, M. et al. (2014). NIDS survey. *IEEE Commun. Surveys & Tutorials.*
- Chandola, V. et al. (2009). Anomaly detection survey. *ACM CSUR.*
- Debar, H. et al. (2000). IDS taxonomy.
- Garcia, S. et al. (2014). CTU-13. *Virus Bulletin.*
- Hamilton, W. et al. (2017). GraphSAGE. *NeurIPS.*
- Kipf, T. & Welling, M. (2017). GCN. *ICLR.*
- Lashkari et al. CICFlowMeter.
- Liu, F. et al. (2008). Isolation Forest. *ICDM.*
- Lundberg, S. & Lee, S. (2017). SHAP. *NeurIPS.*
- Mirsky, Y. et al. (2018). Kitsune. *NDSS.*
- Moustafa, N. & Slay, J. (2015). UNSW-NB15.
- Sharafaldin, I. et al. (2018). CICIDS2017/IDS2018.
- Schölkopf, B. et al. (1999). One-Class SVM.
- Sommer, R. & Paxson, V. (2010). Outside the closed world. *IEEE S&P.*
- ... (total ~45 entries — see References.md for complete formatted list)
