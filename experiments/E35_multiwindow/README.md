# E35 — Multi-window fusion (60s + 300s)

**Verdict: PASS** · 2026-08-13 / 2026-08-20 · commits `9af7e96`, `a44494f`

## Aim

CLAUDE.md gotcha #8 records the central metric trade: raising the window from
60s to 1800s lifts mean ROC-AUC 0.9173 → 0.9832 but drops P@100 0.244 →
0.093, measured over 294 runs. The two views are good at *different* things —
short windows preserve alert-queue precision, long windows give a cleaner
global picture. Neither dominates.

If that trade is real, fusing them should get both, and the fusion rule has to
compare score *positions* rather than values, because the two windows do not
share a scale (gotcha #17).

## What was done

Two LogScaler `GraphAutoencoder`s trained on Monday benign: one at 60s, one at
300s. Host-level fusion for hosts appearing in both windows, with four rules —
`max`, `mean`, `rank_max`, `rank_mean` — then the 7 held-out families, full
files. Seed 0 first, then a 4-seed band.

## Results — single seed, host-window AUC

| Family | 60s | 300s | multi_max | multi_mean | multi_rank_max | **multi_rank_mean** |
|---|---|---|---|---|---|---|
| PortScan | 0.9681 | 0.9807 | 0.9984 | 0.9998 | 0.9991 | **1.0000** |
| DDoS | 0.9729 | 0.9890 | 0.9984 | 0.9988 | 0.9984 | **1.0000** |
| Botnet | 0.9691 | 0.9696 | 0.9936 | 0.9906 | 0.9935 | **0.9989** |
| Infiltration | 0.9652 | 0.9808 | 0.9992 | 0.9977 | 0.9975 | **1.0000** |
| WebAttacks | 0.9621 | 0.9867 | 0.7485 | 0.9994 | 0.9990 | 0.9605 |
| Patator | 0.9728 | 0.9635 | 0.9973 | 0.9838 | 0.9984 | 0.9828 |
| DoS | 0.9639 | 0.9829 | 0.9989 | 0.9997 | 0.9987 | **0.9999** |
| **Mean** | 0.9681 | 0.9807 | 0.9263 | 0.9602 | 0.9620 | **0.9925** |

4-seed band (`multiwindow_4seed_band.json`): PortScan 1.000, DoS 1.000,
Infiltration 0.9994, DDoS 0.9993, WebAttacks 0.9948, Botnet 0.9359,
Patator 0.9854.

## What we understood

**Rank-mean is the only rule that beats both parents, and the reason is
scale.** `max` and `mean` fuse *values*, so a 300s score and a 60s score are
averaged as if they were the same quantity — they are not, and the result
collapses to 0.9263, *below both singles*. `multi_max`'s 0.7485 on WebAttacks
is the pathological case: one window's absolute score dominates the pair purely
because of its scale. Converting both to within-window *rank positions* before
combining removes the scale problem entirely, which is gotcha #17 restated
in one table.

**The value of fusion here is variance, not just mean.** The 4-seed band shows
the worst-seed single window at 0.9929/0.9930 while fused is 0.9978 — fusion
buys robustness to the seed, consistent with what RC-26 later found. That is a
different benefit than "higher average" and it is the one that survives
contact with reality.

**The PIKACHU comparison attached to this experiment was later withdrawn**, and
that correction matters more than the number. The 0.9925 result was reported
as "beats PIKACHU 0.977 by +0.0155". A web verification on 2026-09-16
established that PIKACHU is Paudel & Huang, NOMS 2022 — a temporal-walk
embedding for **provenance graphs** (DARPA OpTC/LANL, recall 0.987), evaluated
on a different task and different data. The 0.977-CICIDS2017 figure has no
traceable source. The claim was removed. The multi-window *mechanism* stands;
the comparison to a published bar does not.

**What survived into the current system:** the 60s + 300s pair and the
rank-based fusion logic. The scores themselves are now 0.94–0.97 rather than
0.99 (see [E16](../E16_card_clean/) on why), and the fusion rule was later
upgraded from rank-mean to causal reputation ([E21](../E21_band/)).

## Files

- `multiwindow_fusion_results.json` — the 4-rule × 7-family table
- `multiwindow_4seed_band.json` — the 4-seed band
- `exp_gnn_fused_ensemble.py`, `exp_fused_improve.py` — ensemble builders
- `eval_mw_fusion.log`, `eval_multiwindow.log` — run logs
