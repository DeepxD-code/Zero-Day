# E08 — Diverse-arm fusion (AE + IF + PCA + HMM)

**Verdict: NEGATIVE** · 2026-09-26 · commit `99b1a77`

## Aim

The network pillar's fusion (M5c) works because the two arms fail
*differently* — M5a swings 0.48–0.99 across families while M5b never drops
below 0.906, so rank-fusing them beats both. The obvious extrapolation: add
more model families and let diversity do the work. Four arms with genuinely
different inductive biases:

- **AE** — count autoencoder (the incumbent, 0.7768)
- **Isolation Forest** — no density assumption, isolation-based
- **PCA** — linear subspace distance
- **HMM** — sequence model, reads order

All trained benign-only, all with val-tuned F1 thresholds, fused by rank_mean
(batch protocol, disclosed per gotcha #17 — needs a population to rank
against, cannot serve a single alert).

## What was done

Host pillar, ADFA-LD, split-seed 0, identical splits for every arm. Fusion =
rank_mean across the four arms. Question: does diversity + rank fusion beat
the best single arm?

## Results

| Arm | AUC | F1 |
|---|---|---|
| AE (incumbent) | 0.7852 | **0.4745** |
| HMM-16 | 0.7217 | 0.3683 |
| PCA | 0.7538 | 0.4176 |
| Isolation Forest | 0.4916 | 0.2685 |
| **rank_mean (all 4)** | **0.7943** | 0.4252 |

## What we understood

**Fusion wins on AUC by +0.009 and loses on F1 by −0.049 — and the F1 loss is
the honest signal.** Against a band of ±0.005 (E23's 4-seed AE std), +0.009 on
AUC is marginal; −0.049 on F1 is ten times the noise. The fusion is not a
better detector, it is a differently-calibrated one: rank_mean compresses
scores toward their positions, which flattens the extremes that F1's
threshold depends on.

The deeper reason is **correlated failure, not diverse failure**. All four arms
read the same count vector. IF's 0.4916 is the tell — a genuinely different
inductive bias that scores *worse than chance* means it is reading the same
structure and getting it inverted, not that it is orthogonal. Diversity of
algorithm is not diversity of assumption when the input representation is
shared.

**Consequence:** the diversity argument that justifies M5a+M5b fusion (two
representations: per-flow vs relational) does not extend to swapping
algorithms over one representation. E21 later confirmed the positive version of
this — fusing across *representations* (graph + flow) does work.

## Files

- `exp_e8_diverse_fusion.py` — procedure
- `exp_e8_diverse_fusion.json` — per-arm AUC/F1
