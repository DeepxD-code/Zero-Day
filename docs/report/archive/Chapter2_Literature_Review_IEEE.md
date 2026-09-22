# Chapter 2 — Literature Review (IEEE Condensed)

> Standalone IEEE-style condensation of `Chapter2_Literature_Review.md` (60-study draft).
> 30 archival references only. Team-internal papers and low-tier venues removed.
> Full 60-entry list remains in `References.md`. Numbering below is local to this file; mapping to `References.md` is given in brackets, e.g. IEEE [4] = repo [4].

## 2.1 IDS taxonomies and evaluation protocol

Signature systems match stored rules and miss unseen families by definition [1], [2]. Anomaly detection models normality and flags deviation, at the cost of threshold setting and false alarms [3]–[5]. Network intrusions are collective anomalies: a single flow from a scanner looks benign; the fan-out across a window does not [3].

The closed-world critique applies directly: training and testing on the same capture with overlapping families and tuned thresholds reports memorisation, not detection [4]. Controls adopted here follow [4]: train on benign traffic only, hold out each attack family in turn, fix the alert unit before quoting any metric, and report bands over multiple seeds. Drift surveys add the second control: monitor score distributions, not labels, and recalibrate on flags rather than on schedule [6].

## 2.2 Datasets and flow features

CICIDS2017 is the primary benchmark: five days, benign background plus seven attack families, ~2.8M flows [7]. Only the 85-column `GeneratedLabelledFlows` release (Flow ID, Source/Destination IP, Protocol, Timestamp, latin-1) can build host graphs; the 79-column `MachineLearningCSV` release has no IP columns and feeds per-flow models only [7]. CSE-CIC-IDS2018 repeats this pattern: 1 of 10 processed files is graph-usable and column names change a third time [8]. CTU-13 (13 botnet scenarios) and UNSW-NB15 (hybrid synthetic-plus-real, nine families) supply external replication [9], [10].

Flow vocabulary follows CICFlowMeter: 80+ per-flow statistics over packet lengths, inter-arrival times, flags, and segment sizes [11]. Ports alone fail as keys once ephemeral randomisation appears [7], [11]. Two preprocessing constraints matter more than any architecture: (i) NaN-address rows (notably Thursday WebAttacks, ~63% unusable) must be dropped explicitly before host-set construction; (ii) byte/packet counts are power-law, so plain min-max lets a few busy hosts own the alert queue and log-compression before scaling is required.

| Capture | Scale | Graph-usable |
|---|---|---|
| CICIDS2017 [7] | ~2.8M flows, 7 families | 85-col release only |
| CSE-CIC-IDS2018 [8] | ~16M flows | 1 of 10 files |
| CTU-13 [9] | 13 scenarios | Yes, with column map |
| UNSW-NB15 [10] | ~2.5M flows, 9 families | Yes |

## 2.3 Reconstruction-based detection

Isolation Forest (path length), one-class SVM (kernel boundary distance), and PCA (linear subspace residual) are the shallow references [12]–[14]. They capture global structure and miss nonlinear interactions between timing, flag, and volume features. Deterministic autoencoders (bottleneck reconstruction error) and variational autoencoders (latent-distribution deviation) beat them on network data while remaining per-flow [15], [16]. Stacked autoencoders on CICFlowMeter features confirmed the same pattern at larger scale [17]. Kitsune distributes capacity across per-cluster experts for online packet scoring but still scores flows, not neighbourhoods [18].

The shared limit is scope, not capacity: a benign-looking flow from an attacker is individually normal under all of the above. The graph section keeps the reconstruction objective and changes only the aggregation scope from flows to host neighbourhoods.

## 2.4 Graph and relational detection

GraphSAGE uses mean neighbourhood aggregation and preserves degree signal; GCN uses symmetric normalisation and smooths it away [19], [20]. For degree-defined behaviours (one-to-many scan, many-to-one flood) the former keeps the attack signal intact.

Three systems define the design space. Temporal-walk embeddings learn unsupervised dynamic representations and report recall 0.987 on provenance captures (DARPA OpTC/LANL), but on labelled APT replays rather than held-out families [21]. E-GraphSAGE shares the GraphSAGE backbone with edge features but trains supervised, so unseen families fall outside its decision regions by construction [22]. Anomal-E learns edge embeddings self-supervised and is closest in framing, leaving alert granularity open [23]. Few-shot pre-training retains most of supervised graph performance on under 4% of labels, which supports small-benign training regimes [24]. Cross-dataset audits report the caution: several graph detectors that lead on CICIDS2017 degrade on second captures with different background mixes [25].

Node scores describe the model; alerts must be emitted per edge (source, destination). The two levels differ substantially and must be quoted separately.

| System | Backbone | Objective | Standing |
|---|---|---|---|
| GraphSAGE [19] | Mean aggregation | Inductive embeddings | Preserves degree |
| GCN [20] | Symmetric norm. | Semi-supervised classification | Washes out degree |
| Temporal-walk [21] | Dynamic walks | Unsupervised temporal representation | Recall 0.987, APT eval |
| E-GraphSAGE [22] | Edge SAGE | Supervised classification | No zero-day coverage |
| Anomal-E [23] | Self-supervised GNN | Edge embeddings | Granularity open |

## 2.5 Drift, adversarial cost, and explanations

Drift adaptation surveys distinguish supervised detectors that watch labels from unsupervised ones that watch score streams; only the latter applies to zero-day deployment [6]. Traffic-shaping moves malicious flows toward benign regions [2], [5]; gradient-free problem-space rewrites are the realistic threat model [28]. Fixed-threat benchmarks rank robustness across models and captures instead of reporting single headlines [29]. Structural attacks target neighbourhood surgery rather than feature noise [21]–[23], [25]; hardened training against edge injection recovers part of the loss [30]. SHAP gives per-alert additive attributions for triage [26]; LIME/SHAP agreement on IDS models holds within correlation limits [27].

Evaluation hazards and the controls used in this project:

| Hazard | Control |
|---|---|
| Overlapping families [4] | Held-out-family protocol, benign-only training |
| Uncalibrated fusion | Per-window percentile vs benign holdout |
| Node numbers quoted as alerts | Edge-level alerts, separate node/edge reporting |
| Single-seed wins | Multi-seed bands, device + determinism flags |
| Evasion assumed free | Red-team harness reporting attacker cost |

## 2.6 Summary and gap

Unsupervised reconstruction handles unseen families, graph context captures collective behaviours invisible per-flow, and calibration plus held-out evaluation decide whether numbers transfer. The gap addressed here is narrow: unsupervised host-graph reconstruction with benign-only training, edge-level alerts, calibrated multi-window fusion, and held-out-family bands — evaluated on CICIDS2017 with IDS2018/CTU-13 replication.

## References (local IEEE numbering; repo mapping in brackets)

[1] H. Debar, M. Dacier, and A. Wespi, “Towards a taxonomy of intrusion-detection systems,” *Comput. Networks*, vol. 31, no. 8, pp. 805–822, 1999. [repo 2]

[2] S. Axelsson, “Intrusion detection systems: A survey and taxonomy,” Chalmers Univ., Tech. Rep. 99-15, 2000. [repo 1]

[3] V. Chandola, A. Banerjee, and V. Kumar, “Anomaly detection: A survey,” *ACM Comput. Surv.*, vol. 41, no. 3, pp. 1–58, 2009. [repo 3]

[4] R. Sommer and V. Paxson, “Outside the closed world: On using machine learning for network intrusion detection,” in *Proc. IEEE Symp. Security and Privacy*, 2010, pp. 305–316. [repo 4]

[5] M. Bhuyan, D. Bhattacharyya, and J. Kalita, “Network anomaly detection: Methods, systems and tools,” *IEEE Commun. Surveys Tuts.*, vol. 16, no. 1, pp. 303–336, 2014. [repo 5]

[6] J. Gama et al., “A survey on concept drift adaptation,” *ACM Comput. Surv.*, vol. 46, no. 4, 2014. [repo 22]

[7] I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, “Toward generating a new intrusion detection dataset and intrusion traffic characterization,” in *Proc. Int. Conf. Information Systems Security and Privacy (ICISSP)*, 2018. [repo 7]

[8] Canadian Institute for Cybersecurity, “CSE-CIC-IDS2018 dataset,” 2018. [repo 8]

[9] S. Garcia, M. Grill, J. Stiborek, and A. Zunino, “An empirical comparison of botnet detection methods,” *Comput. Secur.*, vol. 45, pp. 100–123, 2014. [repo 9]

[10] N. Moustafa and J. Slay, “UNSW-NB15: A comprehensive data set for network intrusion detection systems,” in *Proc. MilCIS*, 2015. [repo 10]

[11] A. H. Lashkari, “CICFlowMeter,” Canadian Institute for Cybersecurity, 2017. [repo 24]

[12] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation forest,” in *Proc. IEEE ICDM*, 2008. [repo 13]

[13] B. Schölkopf et al., “Support vector method for novelty detection,” in *Proc. NeurIPS*, 1999. [repo 14]

[14] A. Hodge and J. Austin, “A survey of outlier detection methodologies,” *Artif. Intell. Rev.*, vol. 22, pp. 85–126, 2004. [repo 6]

[15] M. Sakurada and T. Yairi, “Anomaly detection using autoencoders with nonlinear dimensionality reduction,” in *Proc. MLSDA*, 2014. [repo 15]

[16] J. An and S. Cho, “Variational autoencoder based anomaly detection using reconstruction probability,” 2015. [repo 16]

[17] N. Shone et al., “A deep learning approach to network intrusion detection,” *IEEE Trans. Emerg. Topics Comput. Intell.*, 2018. [repo 25]

[18] Y. Mirsky et al., “Kitsune: An ensemble of autoencoders for online network intrusion detection,” in *Proc. NDSS*, 2018. [repo 18]

[19] W. Hamilton, R. Ying, and J. Leskovec, “Inductive representation learning on large graphs,” in *Proc. NeurIPS*, 2017. [repo 11]

[20] T. Kipf and M. Welling, “Semi-supervised classification with graph convolutional networks,” in *Proc. ICLR*, 2017. [repo 12]

[21] R. Paudel and H. Huang, “PIKACHU: Temporal walk based dynamic graph embedding for network anomaly detection,” in *Proc. IEEE/IFIP NOMS*, 2022. [repo 19]

[22] W. Lo et al., “E-GraphSAGE: A graph neural network based intrusion detection system,” *IEEE Trans. Dependable Secure Comput.*, 2022. [repo 20]

[23] E. Caville et al., “Anomal-E: A self-supervised network intrusion detection system based on graph neural networks,” *Knowl.-Based Syst.*, vol. 258, p. 110030, 2022. [repo 21]

[24] Z. Gu et al., “Always be pre-training: Representation learning for network intrusion detection with GNNs,” in *Proc. ISQED*, 2024. [repo 29]

[25] C. Wang et al., “Are we there yet? Unraveling the state-of-the-art graph network intrusion detection systems,” *arXiv:2503.20281*, 2025. [repo 30]

[26] S. Lundberg and S.-I. Lee, “A unified approach to interpreting model predictions,” in *Proc. NeurIPS*, 2017. [repo 17]

[27] D. Gaspar, P. Silva, and C. Silva, “Explainable AI for intrusion detection systems: LIME and SHAP applicability on multi-layer perceptron,” *IEEE Access*, 2024. [repo 36]

[28] D. Apruzzese et al., “Real attackers don’t compute gradients: Bridging the gap between adversarial ML research and practice,” in *Proc. USENIX Security*, 2023. [repo 23]

[29] J. Vitorino et al., “An adversarial robustness benchmark for enterprise network intrusion detection,” in *Proc. Int. Symp. Foundations and Practice of Security (FPS)*, 2023. [repo 44]

[30] D. Galli et al., “Defending network intrusion detection systems based on graph neural networks against structural adversarial attacks,” in *Proc. 23rd IEEE Int. Symp. Network Computing and Applications (NCA)*, 2025. [repo 54]
