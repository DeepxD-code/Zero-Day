# E36 — The decisive multi-window ablation (RC-26) and the production decision

**Verdict: PASS** · 2026-08-25 · commits `7220d474`, `a1479f1c`, `9164d1d5`, `f319055`, `80e8699`, `5f3e55b`

## Aim

This is the experiment that decided the production recipe, and it ran over
several days because the first result was not trustworthy. Its job: pick one
fusion configuration, prove it beats the alternatives over 4 seeds on the full
files, and hand the winner to `alert_pipeline`.

The specific controversy it settled: CLAUDE.md gotcha #20 recorded that the
**shipped** M5a saturates in fusion (its percentile is 0.999–1.000 on 100% of
alerts, so `max` lets it overwrite everything), and gotcha #22 recorded that
with `m5a_calibration="rolling"` it becomes un-saturated and WebAttacks
collapses to 0.1714. So "should M5a be in the fusion" was an open question
with evidence on both sides, and the revived 87-dim model was a candidate
replacement.

## What was done

`detection/eval_mw_ablation_4seed.py --seeds 0 1 2 3 --epochs 60` on full files,
GPU, CUDA-deterministic (`set_seed`), with a 20% Monday calibration holdout.
Six fusion configs, then four new arms adding the revived M5a:

`w60`, `w300`, `m5a_multi` (control), `three_way_rm`, `pure_rank_mean`,
`rev_multi`, `three_way_rev_rm`, `pure_noisyor_rev`, `pure_rmax_rev`.

The rule that had to survive: **best-or-tied on all 7 families, all 4 seeds, no
regressions.** Anything with a family regression was disqualified.

## Results — the 4-seed band on the fixed stack

| Config | Mean ± std |
|---|---|
| **pure_noisyor_rev** (revived M5a + within-window rank noisyor) | **0.9996 ± 0.0001** |
| rev_multi / three_way_rev_rm | 0.9996 ± 0.0000/0.0001 |
| pure_rank_mean (previous headline) | 0.9990 ± 0.0003 |
| m5a_multi (shipped M5a control) | 0.9482 ± 0.0032 |

`m5a_multi` landing on its published 0.9482 *exactly* was the determinism
check: the same seed on a rebuilt stack reproduced a number to four decimals,
which is the evidence that `set_seed` actually works here.

**Per-seed, the winner beats the runner-up in all four:** 0.9996, 0.9994,
0.9996, 0.9996 against 0.9994, 0.9990, 0.9992, 0.9980. That is the bar gotcha
#11 sets — a difference under ~6 points is noise until it holds across seeds —
and 0.9996 vs 0.9990 is exactly the kind of difference that only counts because
it reproduced 4/4.

## What we understood

**The shipped M5a and the revived M5a are different models, and conflating them
was the source of two years of confusion.** The plain shipped M5a *hurts*
fusion everywhere (0.9482, the worst config). The revived 87-dim context M5a
*helps* everywhere (0.9996, the best). Same "M5a" label, opposite sign, because
they were trained on different features and calibrated differently. Every
CLAUDE.md gotcha that reads "M5a hurts" is about the shipped one; every claim
that fusion reaches 0.999 is about the revived one. The project adopted the
revived model and marked the shipped one STALE, kept only for the Checkpoint-1
contract and ablations.

**Noisyor, not rank_max, is the defensible rule.** An earlier commit message
claimed rank_MAX was "7/7×4" and a later one corrected it to 5/7 on seed 3.
The 4-seed band is what settled it: `pure_noisyor_rev` is the only arm that is
strictly best in all four seeds. Per commit `9daece4`, rank_max halved DoS
dilution; per commit `2925813`, noisyor is the non-regression rule. This is the
same discipline as E26 six weeks later — a claim about a fusion rule requires
seeds, not a single good-looking run.

**The caveats that came with the decision, kept in the same commit.** Noisyor is
batch-only (needs a window population to rank against, so it cannot score a
single alert — gotcha #17). Both checkpoints must ship together; a missing one
warns and falls back to pure relational, and `model_source` records which
fired. And the v2-feature variant of this exact recipe was untested at the time,
so it was explicitly flagged as the next candidate rather than a bonus.

**Where this experiment stands now.** The recipe it chose (noisyor on
within-window ranks) was later *superseded* by causal reputation
([E21](../E21_band/)) once clean data exposed that the band was measuring the
testbed. But the decision procedure it established — 4 seeds, all families,
no-regression rule, exact-match determinism check — is still the standard every
later experiment is held to.

## Files

- `mw_ablation_4seed.json` — the 4-seed band, all configs
- `eval_mw_ablation_4seed.log`, `eval_mw_4seed.log`, `eval_mw_4seed_gpu.log`
- `decisive_mw_rev_4seed.log` — the run that added the revived arms
- `confirm_v2_noisyor_4seed.log` — the band confirmation
- `exp_promote_7_7.py`, `exp_grid_no_exceptions.py` — promotion gate + sweep driver
- `exp1_*.{json,md}`, `exp2_*.{json,md}` — earlier smoke/tiny protocol checks
- `smoke_ablation.json`, `smoke_v2rev.json` — smoke stages
- `overnight_mw_4seed_60ep.log`, `verify_ensembler_full_seed0.log` — overnight + verification
- `run_ablation_gpu.cmd`, `summarize_4seed.py` — launcher + aggregator
