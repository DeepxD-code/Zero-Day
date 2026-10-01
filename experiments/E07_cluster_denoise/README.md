# E07 — Cluster denoising of the alert queue

**Verdict: NEGATIVE (as intended) / informative** · 2026-09-26 · commit `8f7e678`

## Aim

RC-27/RC-28 established that host-level P@100 is *structurally* capped (most
days have 1–8 attackers among thousands of hosts) and that the false-positive
queue is mostly queue noise, not junk windows. Small-window filtering was
already tried and failed.

The remaining idea: instead of filtering windows, denoise the **queue** —
cluster the top-scoring hosts by embedding and either replace each cluster with
its centroid (consensus) or drop the smallest cluster. If a scanner's targets
form a coherent cluster, denoising should help; if the FP noise is diffuse,
it should not.

## What was done

KMeans over node embeddings in each window, k = 2 and k = 3, two strategies:

- **centroid** — replace every node's features with its cluster centroid
  (x ← centroid)
- **drop-small** — remove the smallest cluster's nodes and score the induced
  subgraph

Score = relational-mean endpoint reconstruction error → within-window rank01
→ PortScan edge AUC. Baseline (no denoise) = 0.8714.

## Results

| Strategy | AUC | Edges scored |
|---|---|---|
| **none (baseline)** | **0.8714** | 30613 |
| centroid k=2 | 0.5951 | 30613 |
| centroid k=3 | 0.6833 | 30613 |
| drop-small k=2 | 0.9143 | 15801 |
| drop-small k=3 | 0.9763 | 1729 |

## What we understood

**Two distinct results that must not be conflated.**

*Centroid replacement is actively harmful* (0.87 → 0.60/0.68). Averaging
features within a cluster destroys exactly what the detector measures: the
attacker's *outlier* degree is the signal, and centroids are by construction
the most average thing in the cluster. This is a clean illustration of why
"denoise" and "anomaly detection" are usually in tension.

*Drop-small looks great and is a trap.* 0.9763 at k=3 sounds like a win, but
look at the denominator: 30613 edges → **1729**. The attacker contributes 29 of
them. We deleted 94% of the graph, most of it the benign hosts we needed as
negatives, and the AUC went up because the sample got easier, not because
detection improved. This is precisely the RC-27/RC-28 trap: an AUC gain
bought by shrinking the evaluation population is a measurement artefact.

**Killed as a method; kept as a lesson.** Any future "our filter improves AUC"
claim must report the edge count next to the number, or it is meaningless.

## Files

- `exp_e7_cluster_denoise.py` — procedure
- `exp_e7_cluster_denoise.json` — per-arm AUC and edge counts
