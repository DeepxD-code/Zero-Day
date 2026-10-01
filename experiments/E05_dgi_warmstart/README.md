# E05 — DGI contrastive warm-start before reconstruction

**Verdict: NEGATIVE** · 2026-09-26 · commit `8f7e678`

## Aim

Deep Graph Infometrics (DGI, Veličković et al.) is the standard
self-supervised pretraining for graph encoders: corrupt a graph, discriminate
real from corrupted node embeddings with a bilinear readout, and use that
representation as the init for a downstream task. It costs no labels, so it
sits naturally beside a benign-only autoencoder.

The specific hope: E04 showed a single 100-epoch reconstruction model is
high-variance on PortScan (0.744–0.891 across seeds). A contrastive objective
has a much richer per-batch signal than reconstruction-to-itself, so
pretraining should (a) lower that variance and (b) give a better starting
point than random init.

## What was done

100 epochs of reconstruction in both arms (so the only difference is the init),
4 seeds, shipped architecture (SAGEConv):

- **scratch** — random init → 100 epochs reconstruction
- **dgi** — 50 epochs DGI pretraining → 100 epochs reconstruction

Metric: PortScan clean edge-AUC, mean ± std over seeds. Reference point: E04's
clean arm spans 0.744–0.891.

## Results

| Arm | Per-seed PortScan AUC | Mean |
|---|---|---|
| scratch | 0.838, 0.813, 0.807, 0.883 | 0.835 |
| dgi | 0.816, 0.798, 0.799, 0.807 | 0.805 |

## What we understood

**DGI is slightly worse and, more damningly, less variable** — which is the
opposite of the stated goal. The variance we were trying to fix went *down*
(std 0.033 → 0.009), but so did the mean (−0.030). Pretraining pulled every
seed toward the same mediocre solution.

The likely reason is that DGI's discrimination task is **too easy on our
data**. Our graphs are small (tens of nodes, ~400 edges) with strongly
distinct degree profiles; telling a real graph from a corrupted one is close
to trivial, so the contrastive loss saturates and supplies almost no
information about *what normal looks like* — which is the only thing the
downstream autoencoder needs to learn. DGI rewards structural discriminability;
our downstream task requires a precise reconstruction of benign feature
magnitudes. These are different objectives, and the second one is not
derivable from the first.

**Kept as a bound:** self-supervised contrastive pretraining does not help this
detector. The zero-label argument still holds in principle; the objective
simply does not match the task at this graph scale.

## Files

- `exp_e5_dgi_warmstart.py` — procedure
- `exp_e5_dgi_warmstart.json` — per-seed AUCs
