# E21 — 4-seed bands + fusion-rule shootout

**Verdict: PASS** · 2026-09-27 · commit `fdc96cf`

## Aim

Every number so far was one seed. CLAUDE.md's most important methodological
fact is that two identical *unseeded* full-file sweeps once gave mean ROC-AUC
0.8997 and 0.9251, and that any difference under ~6 points between two
configurations is noise until shown over multiple seeds. Two things were owed:

1. **Bands** for every family, so the headline is a band.
2. **A fusion rule chosen on evidence**, not on a hunch — and the rule had to
   win as one rule across families, not be cherry-picked per family.

## What was done

Four seeds of both pillars, trained on clean Monday:

- M5b: `gnn_improved_s{0,1,2,3}.pt` (200 epochs, seed 0–3)
- M5a: `m5a_revived_improved{,_s1,_s2,_s3}.pt` (60 epochs, seed 0–3)

Then per seed, per family (label-cut, attempted-excluded, **per-day** scoring
per E16's fix), under one consistent metric: within-window rank → pool.

On Friday, five fusion arms: `m5b`, `m5a`, `noisyor`, `rank_max`, `repfuse`.

## Results — the bands

| Family | s0 | s1 | s2 | s3 | Mean ± std |
|---|---|---|---|---|---|
| Patator | 0.983 | 0.914 | 0.957 | 0.917 | **0.943 ± 0.029** |
| DoS | 0.991 | 0.970 | 0.955 | 0.936 | **0.963 ± 0.020** |
| WebAttacks | 0.931 | 0.849 | 0.790 | 0.682 | **0.813 ± 0.091** |
| Infiltration | 0.760 | 0.772 | 0.746 | 0.742 | **0.755 ± 0.012** |
| Botnet | 0.418 | 0.453 | 0.477 | 0.477 | **0.456 ± 0.024** |
| PortScan | 0.971 | 0.973 | 0.925 | 0.925 | **0.948 ± 0.024** |
| DDoS | 0.973 | 0.973 | 0.972 | 0.970 | **0.972 ± 0.001** |

## Results — the fusion shootout (Friday, 4 seeds)

| Arm | Botnet | PortScan | DDoS |
|---|---|---|---|
| m5b | 0.456 ± 0.024 | 0.948 ± 0.024 | 0.972 ± 0.001 |
| m5a | 0.590 ± 0.006 | 0.948 ± 0.012 | 0.980 ± 0.001 |
| noisyor | 0.523 ± 0.021 | 0.960 ± 0.011 | 0.978 ± 0.001 |
| rank_max | 0.518 ± 0.021 | 0.961 ± 0.014 | 0.976 ± 0.002 |
| **repfuse** | **0.667 ± 0.012** | 0.952 ± 0.017 | **0.981 ± 0.000** |

## What we understood

**One rule, all families, no cherry-picking: `repfuse` wins.** It is
best-or-tied everywhere — outright winner on Botnet (+0.077 over the next
best), top on DDoS with a zero-variance band, tied-top on PortScan within
noise. That is the test that was set in advance, and it passed.

The reason it beats within-window rank fusion is the E19/E20 mechanism applied
uniformly: **fusing across *representations* (graph + flow) works; fusing across
*algorithms* over one representation does not** (E08 showed IF/PCA/HMM add
nothing but noise). `repfuse` also operates on the right quantity —
accumulated host history rather than a window snapshot — which is why it is the
only arm that helps Botnet at all.

**WebAttacks' ±0.091 is the finding that mattered most,** because it looked
like a property of the family and turned out to be a property of the
*training*. Seed 0's final loss was 0.000084, seed 1's 0.000081, seeds 2 and 3
were 0.000184 and 0.000188 — **2× worse convergence at a fixed 200-epoch
budget**. And the families with tight bands (DDoS ±0.001) do not care. The
web attacker, 62 edges buried under 71,767 scan flows, is the most marginal
case in the whole suite, so it is the canary for undertraining. That diagnosis
became [E26](../E26_val_epochs/) and lifted Web to 0.900 ± 0.017.

**The honest table is the banded one.** A single seed would have let us quote
0.931 for Web. The band says 0.813 ± 0.091, and the band is what the report
must carry.

## Files

- `exp_e21_band.py` — procedure (both pillars, all 7 families, 5 arms)
- `exp_e21_band.json` — per-seed cards and per-arm fusion results
- `m5a_revived_improved_s{1,2,3}.pt` — band evidence (not served; E22 showed
  the flow model is seed-stable)
