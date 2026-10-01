# E25 — Seed-ensemble for WebAttacks

**Verdict: NEGATIVE** · 2026-09-28 · commit `110fbd1`

## Aim

[E21](../E21_band/) left two candidate fixes for WebAttacks' 0.813 ± 0.091
band: E26 (val-picked epochs — retraining) and **averaging the four
checkpoints' scores** (no retraining at all, just an inference-time change).

The ensemble hypothesis is well-founded and cheap: four independently-seeded
models make partly independent errors, so their mean should cancel the
per-seed variance. If it works, the ±0.091 collapses without spending GPU
hours, and the same trick generalises to every family.

It is worth knowing which of the two fixes is actually needed *before* running
the expensive one.

## What was done

Clean Thursday. Load all four `gnn_improved_s{0..3}.pt` checkpoints, score each
window with each, take the **mean node score** across the four, then the
standard within-window rank → edge AUC. WebAttacks and Infiltration (the latter
as a control, since it was never seed-fragile).

## Results

| Family | Single-model band (E21) | **4-seed ensemble** |
|---|---|---|
| WebAttacks | 0.813 ± 0.091 | **0.808** (62 attacker edges) |
| Infiltration | 0.755 ± 0.012 | 0.753 |

## What we understood

**The ensemble does exactly what it says — it stabilises — and stabilisation
is not the goal.** Infiltration, whose single-model band is already ±0.012,
lands within 0.002 of its mean. So the mechanism works: averaging kills
seed-to-seed variance.

But Web's mean is **0.808 versus 0.813** — the consensus of four seeds is the
average of those seeds, not the best of them. Averaging cannot manufacture a
signal that individual models lack; it can only stop you from inheriting a bad
draw. Seed 3's 0.682 is a real deficiency in *that model's* learned geometry,
and averaging with three models that do not have it does not repair it.

**The decisive comparison, though, is against the per-seed number rather than
the mean.** A single model at 0.813 ± 0.091 means a 1-in-4 chance of serving
something around 0.68 on any given day. An ensemble delivers 0.808 *every*
day. If WebAttacks is going to be served from the graph pillar, the ensemble is
strictly better than picking a seed and hoping. It just is not better than
retraining properly.

**Which is why E26 was run next, and why it was the right call.** The ensemble
answers "how do I stop rolling dice?" for free. It does not answer "why is one
seed's geometry worse than the others?" — and that question had an answer
waiting: seeds 2 and 3 converged to 2× worse final loss at a fixed 200-epoch
budget. Val-picked epochs ([E26](../E26_val_epochs/)) fixed the cause and took
Web to 0.900 ± 0.017, which beats the ensemble's 0.808 outright.

**Kept as a negative because it is a genuinely useful cheap fallback.** For any
future family where retraining is expensive or the cause of variance is not
understood, a 4-checkpoint ensemble is a ~zero-cost variance floor. It is just
not a substitute for understanding *why* the variance exists.

## Files

- `exp_e25_ensemble.py` — procedure
- `exp_e25_ensemble.json` — ensemble vs single-model bands
