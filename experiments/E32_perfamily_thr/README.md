<!-- Renumbered from the A3-series on 2026-09-29 so every experiment uses one scheme. The original ID is preserved in the archive README's Historic ID column and in git history. -->

# E32 — Per-family thresholds on the host AE

**Verdict: NEGATIVE** · 2026-09-26

## Aim

The host AE uses one global threshold (argmax-F1 on validation, 0.1324). Six
attack families share it. If each family has a naturally different score
distribution, per-family thresholds should raise macro recall.

This was the natural fix for the one family where the AE loses to the HMM
(Hydra_SSH) — give that family its own cut.

## What was done

Host AE on ADFA-LD, split-seed 0. For each of the 6 attack families, tune a
threshold on that family's validation rows and apply it to that family's test
rows. Compare macro-averaged recall/F1 against the single global threshold.

## Results

Global: thr 0.1324, F1 0.4745, precision 0.3884, recall 0.6096.

| Family | Threshold | F1 | Recall | n |
|---|---|---|---|---|
| Adduser | 0.1360 | 0.1773 | 0.3913 | 46 |
| Hydra_FTP | 0.1336 | 0.2211 | 0.5185 | 81 |
| Hydra_SSH | 0.1337 | 0.1685 | 0.3523 | 88 |
| Java_Meterpreter | 0.1345 | 0.1931 | 0.4516 | 62 |
| Meterpreter | 0.1323 | 0.1144 | 0.6579 | 38 |
| Web_Shell | 0.1336 | 0.1662 | 0.4915 | 59 |

**Macro: recall 0.4772, F1 0.1734** — versus global recall 0.6096, F1 0.4745.

## What we understood

**Per-family thresholds make things worse, and the tuned values explain why.**
Every family's optimum lands within 0.1323–0.1360 of the global 0.1324 — a
±0.4% spread. The score distributions are not different enough for per-family
cuts to find, so the tuning is fitting noise, and macro-F1 collapses from
0.4745 to 0.1734.

The collapse is not a tuning failure, it is an accounting artefact worth
stating precisely: the "global F1" of 0.4745 is computed over the **pooled**
test set where benign outnumbers attack 6:1, so a single threshold operating
on the pooled distribution is optimising the pooled problem. Per-family F1 is
computed on **within-family** sets where the ratio is near 1:1, so the same
operating point is scored against a completely different base rate. The
numbers are not comparable, and the honest comparison is recall-on-attacks:
global 0.6096 beats per-family 0.4772 even after per-family optimisation.

**Consequences:**
1. One global threshold stays. Splitting it buys nothing.
2. **Never compare F1 across differently-composed test sets** — we nearly
   reported a 2.7× regression that was pure base-rate change. This is the same
   trap as E07's edge-count collapse and the same guard E14 added
   (`eval_utils.slice_verdict`) addresses.
3. Per-family thresholds would additionally require knowing the family at
   inference time, which a zero-day unsupervised detector by definition does
   not have.

## Files

- `exp_a3_perfamily_thr.py` — procedure
- `exp_a3_perfamily_thr.json` — per-family thresholds and scores
