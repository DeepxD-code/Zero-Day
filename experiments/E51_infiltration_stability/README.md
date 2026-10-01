# E51 — Can Infiltration's seed-flip be fixed at the estimator?

**Verdict: NEGATIVE — the hypothesis was wrong, and the negative is
diagnostic.** · 2026-09-29

## Aim

[E43](../E43_fusion_rule/) banded the fusion arms and found Infiltration's
ranking flips with the seed. The user-facing question is the right one: *fixing
the instability is worth more than any single-seed high.*

| seed | noisyor | repfuse | winner |
|---|---|---|---|
| 0 | 0.645 | 0.639 | noisyor |
| 1 | 0.651 | 0.686 | repfuse |
| 2 | 0.650 | 0.698 | repfuse |
| 3 | 0.652 | 0.651 | tie |

Band: repfuse 0.668 ± 0.028, noisyor 0.650 ± 0.003. The instability is entirely
in `repfuse`; `noisyor` is rock-stable.

## The hypothesis, and why it was reasonable

`repfuse` is the mean of two **per-host running means**. Infiltration has only
**three attacker hosts** on Thursday, so for the windows that matter each host's
running mean is built from very few observations and its value depends
sensitively on *when* that host first appears. A thin-history mean is a
high-variance estimator, so the natural fix is variance reduction, not tuning —
empirical-Bayes shrinkage toward the causal population mean:

```
shrunk = (n * mean_h + k * mu) / (n + k)
```

`k=0` recovers the raw running mean; large `k` collapses a host toward the
global. Fully causal, no labels, no future information. This is the textbook
response to a thin-history estimator, and it is the right tool *if* the
diagnosis is right.

## Result — it does nothing

| k | repfuse (mean ± SD) | vs noisyor | seed agreement |
|---|---|---|---|
| **0 (raw)** | 0.6743 ± 0.0324 | 2/4 | **FLIPS** |
| 1 | 0.6745 ± 0.0325 | 2/4 | FLIPS |
| 2 | 0.6748 ± 0.0327 | 3/4 | FLIPS |
| 4 | 0.6751 ± 0.0327 | 3/4 | FLIPS |
| 8 | 0.6751 ± 0.0326 | 3/4 | FLIPS |
| 16 | 0.6754 ± 0.0327 | 3/4 | FLIPS |

**SD changed by −0.3%** (0.0324 → 0.0325). Across a 16× range of prior
strength, the estimator is essentially invariant. **The variance is not in the
reputation estimator.**

The same holds on every family — Botnet SD 0.0290 at k=0 and 0.0292 at k=16;
WebAttacks 0.1115 → 0.1041. Shrinkage is a no-op everywhere.

## What we understood

**The variance is bimodal model variance, not estimator noise.** The per-seed
values are not scattered — they are in two clusters:

```
Infiltration repfuse:  0.6421  0.6954  0.7081  0.6515
                        └─ low ─┘         └─ low ─┘
seeds 0 and 3 sit near 0.645 (below noisyor's 0.6496); seeds 1 and 2 sit near
0.70 (well above it).
```

The flip is those two clusters straddling `noisyor`. A shrinkage prior cannot
help, because shrinking moves a host toward the *global* mean — and the global
mean is itself computed from models whose Infiltration behaviour differs by
seed. **The instability lives in what the per-seed models learn, not in how
their outputs are aggregated.** Those are different problems, and I picked the
wrong one.

**This retroactively validates the archive's decision to band.** A single seed
is not a noisy estimate of the truth here — it is a coin-flip between two
qualitatively different model behaviours. Seed 0 says "noisyor wins", seed 2
says "repfuse wins by 0.058", and both are honest readings of their own model.
**The band is not a convenience here; it is the only valid summary.** Quoting
Infiltration at any single seed would be a category error, and this experiment
is the proof of that rather than an assumption.

**What would actually fix it** is a change at the model level, not the fusion
level — more training data, a different host representation, or an ensemble.
[E22](../E22_web_m5a/) already tested a Web seed-ensemble and found it
"stabilizes only" (0.808), so the cheap version of that fix is not obviously
available either. The honest current position: Infiltration is a ±0.03 family,
quote the band, and stop trying to fuse it better.

**The value of this experiment is that it closed a wrong hypothesis cheaply.**
Twenty minutes of compute eliminated a whole class of fix (estimator
regularisation) and redirected the search to model variance. Had the flip been
quoted around — as the archive previously did — the next person would
plausibly have tried exactly this and wasted longer.

## Files

- `exp_e51_stability.py` — the shrinkage grid, 4 seeds × 5 families
- `exp_e51_stability.json` — per-seed values at every `k`
