# E28 — The WebAttacks band after the E26 fix

**Verdict: PASS** · 2026-09-28 · commit `4ab2313`

## Aim

Close the loop on the project's worst number. WebAttacks went 0.813 ± 0.091
(E21) → 0.900 ± 0.017 with the val-epoch fix, and that claim needed a full
4-seed band rather than the two-seed spot check E26 ran.

## What was done

WebAttacks AUC on clean Thursday for all four val-picked checkpoints
(`gnn_improved_s{0,1,2,3}.pt`, best epochs 215/17/78/77), within-window rank,
same protocol as every other clean-data measurement.

## Results

| Seed | Before (fixed 200 ep) | **After (val-picked)** |
|---|---|---|
| 0 | 0.931 | 0.9195 |
| 1 | 0.849 | 0.8765 |
| 2 | 0.790 | 0.9130 |
| 3 | 0.682 | 0.8906 |
| **Band** | **0.813 ± 0.091** | **0.900 ± 0.017** |

## What we understood

**The 0.68 tail is gone and the band is 5× tighter** (0.091 → 0.017). The two
seeds that were undertrained (2, 3) gained +0.123 and +0.209; the two that were
already fine (0, 1) changed little (−0.012, +0.028). That asymmetry is the
signature of a targeted fix — it moves exactly the cases the diagnosis
identified and leaves the rest alone, which is what you want to see and would
not see if the improvement were noise.

**WebAttacks is now a normal family in the table**, which changes what the
project can claim. Before, the honest summary was "six families ≥0.9, one
fragile at 0.813 ± 0.091". Now: seven families at 0.90–0.97 on clean data,
with the sole exception of Botnet, whose 0.42 is a *structural* floor rather
than a tuning failure (E19/E21).

**The transferable lesson, and the reason this experiment is more than a
number.** A ±0.09 band on one family out of seven does not read as "WebAttacks
is hard" — it reads as "something is wrong with the training". It took a
per-seed diagnostic (E21's train-loss table plus E22's rank distributions) to
see that the variance tracked *convergence*, not the family. Had the band been
reported as a property of web attacks, the fix would never have been found, and
the same defect would have been sitting in every other family's number
unnoticed — it was only visible here because the attack was marginal enough to
be sensitive to it.

This is the same discipline as gotcha #11 (always pass `--seed`) taken one step
further: **bands are not just error bars, they are a diagnostic instrument.**
A wide band is a question about your training, not a fact about your data.

## Files

- `exp_e28_web_valband.json` — the four post-fix numbers
- `../E26_val_epochs/` — the fix, and the superseded checkpoints
- `../../detection/gnn_improved_s{0,1,2,3}.pt` — the band now served
