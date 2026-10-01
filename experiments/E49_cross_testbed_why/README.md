# E49 — Why do the two extractors learn different notions of normal?

**Verdict: PASS — mechanism identified. The improved extractor drops ~52% of
TCP flow records, so the same hosts produce a structurally different graph.**
· 2026-09-29

## Aim

The cross-testbed gap has been handled methodologically but never *explained*.
E17 exonerated the architecture (same network, clean data, 4 of 7 families
fixed). E27 ruled out pooling (it learns neither testbed). E29/E42 found
replay-tuning works on 5 of 7. **Nothing said why.**

This measures the mechanism directly from the data, before any training.

## What was done

Two measurements, both pure diagnostics — no model is trained, so neither can
be accused of a training artefact.

1. `exp_e49_feature_divergence.py` — per-feature distribution divergence
   (Kolmogorov–Smirnov on the empirical CDFs, distribution-free) between the two
   benign Mondays, plus dead-feature and host-overlap checks.
2. `exp_e49b_node_dim_divergence.py` — the same comparison on the **19 graph
   node dimensions** the model actually reads, per 60s window.

## Result — the mechanism

### The two Mondays are the same network

| | Original | Improved |
|---|---|---|
| Distinct hosts | 9,709 | 9,710 |
| **Host Jaccard** | **0.9999** | |

**The same hosts, on the same day.** So this is not two different network
segments — it is two extraction pipelines over one capture.

### The improved extractor drops 52% of TCP flows

| Protocol | Original | Improved | Difference |
|---|---|---|---|
| **UDP (17)** | **224,178** | **224,023** | **−155 (−0.07%)** |
| **TCP (6)** | **305,423** | **147,204** | **−158,219 (−51.8%)** |
| Total | 529,918 | 371,624 | −30% |

**This is the whole story.** The two extractors agree on UDP to within seven
hundredths of a percent, and disagree on TCP by a factor of two. Whatever the
improved pipeline changed — flow segmentation boundaries, handling of
bidirectional TCP records, retransmission or keepalive accounting — it changed
it *only for TCP*.

### The consequence, measured on the 19 node dims

Because the graph is built from TCP edges, losing half of them changes the
per-node statistics the model was fitted on:

| | Original | Improved |
|---|---|---|
| Nodes / window | 170.8 | 136.7 |
| Edges / window | 252.8 | **148.8** |
| **Edges per node** | **1.480** | **1.088** |
| `tcp_frac` (mean) | 0.516 | **0.036** |

**`tcp_frac` collapses from 0.52 to 0.036.** That single dimension is shifted by
1.32 within-corpus standard deviations — the only one of the 19 that exceeds
1 SD, and the largest outlier by a wide margin.

## What we understood

**The model did not learn the wrong thing. It learned the truth about a
pipeline it never sees at inference time.** A `GraphAutoencoder` fitted on
original Monday learns that a normal host has ~1.48 edges per node and ~52% TCP
neighbours. Scored on improved data, the same hosts show 1.08 edges and 3.6% TCP
— not because the hosts changed, but because the *flow records* changed. The
reconstruction error rises for every host, benign or not, and the ranking that
separates them collapses. That is exactly the failure E16 measured and E17
fixed by retraining.

**The feature-divergence hypothesis was wrong, and testing it mattered.** The
raw CSVs do contain near-total divergences — `Subflow Fwd Packets` at KS 0.986
(median 2 vs 0), `Fwd Header Length` at KS 0.552 (64 vs 16 bytes). Those look
like the answer. But **none of them feed the graph.** The 19 node dimensions are
degrees, byte totals, port counts, entropies and fractions, and the features
they *do* read are among the least divergent in the file (ECE Flag Count KS
0.000, Active/Idle stats 0.04–0.10, Flow Bytes/s 0.087). Chasing the biggest
CSV-level divergence would have been a dead end; the answer was one dimension
over, in a dimension nobody would have guessed to look at.

**This is why replay-tuning works and pooling does not.** Pooling (E27)
averages two incompatible flow densities into one "normal" that is right for
neither — its validation loss bottomed out at **epoch 17 of 400**, a model that
gives up almost immediately because it cannot reconcile them. Replay-tuning
(E29/E42) keeps the source distribution on life support at 20% while learning
the target, which is the standard remedy for exactly this: a covariate shift
that is systematic, one-sided, and not reducible by interpolation.

### Causal confirmation (E49c) — CONFIRMED, with a residual

`exp_e49c_causal_confirm.py` runs the falsifiable prediction. If the mechanism
is the TCP flow deficit, then **UDP-only graphs must agree and TCP-only graphs
must diverge** — and no synthetic manipulation is needed to test it.

| Arm | KS median | edges/node (orig → clean) |
|---|---|---|
| **UDP only** | **0.003** | **1.027 → 1.028** |
| TCP only | 0.427 | 1.470 → 1.032 |
| TCP downsampled to the clean count | 0.373 | 1.292 → 1.032 |

**UDP is a dead heat: KS 0.003, and edges-per-node matches to 0.001** (1.027 vs
1.028). If the two pipelines differed *in general*, UDP would diverge too. It
does not diverge at all. So the pipelines are identical for UDP and different
for TCP, which is exactly the mechanism E49 proposed — now established causally
rather than by correlation.

**The residual is real and worth stating.** Downsampling the original's TCP flows
to the improved extractor's count moves the divergence only part of the way
(KS 0.427 → 0.373, edges/node 1.470 → 1.292, against a target of 1.032). So the
deficit is the dominant term but **not the whole story**: at matched flow count
the two TCP streams still produce different graphs. The improved extractor
segments TCP flows differently, not merely more coarsely.

That changes the fix. It is not enough to normalise per-protocol flow density —
that would close most of the gap, not all of it. A real solution also has to
align TCP flow segmentation, which is a property of the *extractor*, not
something a detector can correct downstream.

## What this means for the fix

| Step | Effect | Status |
|---|---|---|
| Normalise per-protocol flow density before graphing | closes the dominant term | now justified by measurement |
| Align TCP flow segmentation | closes the residual | needs extractor-level work |
| Replay-tune 20% (E29/E42) | works today, 5 of 7 families | remains the pragmatic answer |

## Files

- `exp_e49_feature_divergence.py` / `.json` — CSV-level divergence, dead
  features, host overlap
- `exp_e49b_node_dim_divergence.py` / `.json` — the 19 node dims, and the
  TCP/UDP split that explains them
- `exp_e49c_causal_confirm.py` / `.json` — the UDP-agrees / TCP-diverges test,
  plus the downsampling arm
