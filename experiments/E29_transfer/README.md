# E29 — Cross-testbed transfer: three attempts, one accepted

**Verdict: PASS** · 2026-09-28 · commit `74a6d64`

## Aim

Close [E27](../E27_combined_monday/). The project's remaining structural
liability: a checkpoint trained on one collection pipeline does not work on
the other, in either direction, and pooling the data was rejected. A SOC
deploying this cannot retrain from scratch at every site, so the question is:
**how much work is it to adapt one trained model to a new site?**

## What was done — three routes, in order

### Attempt 1: dual-checkpoint ensemble (rejected)

Score every window with *both* specialists and take the element-wise maximum —
OR-logic at score level, no retraining at all.

| PortScan | dual-max |
|---|---|
| original testbed | **0.4749** |
| clean testbed | **0.6169** |

Worse than either parent (0.871 original / 0.971 clean). Obvious in hindsight,
and worth stating: **max keeps the higher score, and a false alarm from either
parent survives.** OR-logic over uncalibrated scores is just alarm-union.

### Attempt 2: plain fine-tune (partial — catastrophic forgetting)

Improved model + 20 epochs at LR 1e-4 on original Monday benign. Loss
converged 0.100 → 0.0012.

| | plain fine-tune |
|---|---|
| original testbed | 0.8685 (was 0.4749 dual-max, 0.5477 improved-only) |
| clean testbed | **0.8308** (was 0.9708 improved-only) |

Transfer works — and the source model is forgotten. Textbook catastrophic
forgetting in 20 epochs: the target domain is learned by overwriting the source.

### Attempt 3: replay-tuned fine-tune (accepted)

Identical recipe, one change: every batch mixes original Monday with **20% of
the improved Monday graphs** (487 + 97). The old distribution stays on life
support while the new one is learned. 20 epochs, LR 1e-4, seed 1. Loss
0.081 → 0.0015.

| | **replay-tune** |
|---|---|
| original testbed | **0.9056** |
| clean testbed | **0.9033** |

## Results

| Approach | Original testbed | Clean testbed | Verdict |
|---|---|---|---|
| improved-only (no transfer) | 0.5477 | 0.9708 | one site only |
| original-only (no transfer) | 0.8714 | 0.4734 | one site only |
| dual-max ensemble | 0.4749 | 0.6169 | rejected — union of false alarms |
| plain fine-tune | 0.8685 | 0.8308 | rejected — forgets the source |
| E27 combined training | 0.578–0.861 | 0.731–0.993 | rejected — learns neither |
| **replay-tune** | **0.9056** | **0.9033** | **accepted** |

## What we understood

**Forgetting needs a reminder, not equal billing.** E27 failed by training
both domains from scratch and landing in a compromise (best val epoch 17). The
plain fine-tune failed by training on one domain and overwriting the other.
Replay-tune does neither: start from a model that already knows domain A, and
train on domain B *with domain A in the batch*. The old distribution never
leaves the training set, so it cannot be forgotten — and because only 20% of
each batch is A, learning B costs roughly nothing.

**The deployment story this produces is honest and cheap:** ship one base
checkpoint, then a **20-epoch replay-tune against the new site's own benign
traffic**. That is a bounded, unsupervised (benign-only) operation with a
reproducible recipe and a checkpoint (`gnn_improved_replay.pt`) that holds
both sites at ≥0.90. It is not zero-touch, and the report should not claim it
is.

**The remaining caveat, stated plainly: this is proven on PortScan only.** One
family, the easiest case (scans are the most topologically distinctive signal
in the suite). The recipe is principled and cheap to run, but "transfer works"
as a general claim needs the other six families, and cross-testbed is still
open item #3 in the root README. The checkpoints `gnn_finetuned_orig20.pt` (the
partial that forgot) and `gnn_improved_replay.pt` (the one that works) are both
kept here so the comparison stays reproducible.

**One more thing this experiment taught, which generalises past transfer:**
every "combine the two models" instinct failed here (E27 pooling, dual-max),
while every "adapt one model" approach that respected the other distribution
succeeded. E08's result is the same lesson in a different place — diversity of
*algorithm* is not diversity of *assumption*. When two things genuinely
disagree about what normal is, the answer is not to average them.

## Files

- `exp_e29_transfer.json` — all three attempts, both testbeds
- `gnn_finetuned_orig20.pt` — plain fine-tune (forgot the source)
- `gnn_improved_replay.pt` — **the accepted checkpoint** (also in `detection/`)
- recipe: `../E17_retrain_improved/exp_e17_retrain_improved.py` + 20% replay mix
