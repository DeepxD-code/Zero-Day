# E03 — Drift detection statistic (MMD) + detection delay

**Verdict: NEGATIVE** · 2026-09-26 · commit `8f7e678`

## Aim

The project ships a drift monitor (M6, `detection/drift_monitor.py`) that
tracks score drift, but nobody had ever tested whether it can actually *tell*
drift from an attack. An unsupervised detector needs one thing above all else:
a way to know when "normal" has changed, because every threshold it owns was
calibrated on the old normal.

MMD (maximum mean discrepancy) is the standard distribution-shift statistic, so
the question was: if we compute MMD between Monday's score distribution and an
attack day's, can we (a) rank attack-day blocks above Monday blocks, and (b)
raise an alarm before the attack detector does?

## What was done

Both the original (`data/GeneratedLabelledFlows/`) and clean
(`data/CICIDS2017_improved/`) datasets, per attack family, per 60s window:

1. Score every window with the shipped M5b checkpoint.
2. Chunk each day into sliding blocks of 10 windows (10 minutes).
3. Two statistics per block: MMD on the **embedding** (`conv2` output) and MMD
   on the **score** itself.
4. Calibrate a threshold on Monday blocks at a matched false-alarm rate.
5. Report, per family: **detection delay** (blocks until the statistic first
   crosses) and **AUC** of the statistic separating day-blocks from
   Monday-blocks.

## Results

AUC of the statistic for "is this block from an attack day?":

| Family | AUC (embedding) | AUC (score) | Blocks |
|---|---|---|---|
| Patator | **1.00** | 0.31 | 9 |
| DoS | 0.05 | 0.08 | 10 |
| WebAttacks | 0.00 | 0.19 | 4 |
| Infiltration | 0.00 | 0.00 | 4 |
| Botnet | 0.00 | 0.31 | 4 |
| DDoS | 0.00 | 0.25 | 1 |
| PortScan | 0.00 | 0.00 | 3 |

Thresholds: `thr_emb` 0.00970, `thr_score` 0.00048.

## What we understood

**This does not work, and the failure is informative.** Three families score
*below* 0.5 AUC — the statistic is worse than useless there, actively
anti-correlated. The reason is the same thing E16 later proved at scale: the
MMD is measuring the *dataset difference* between two collection pipelines,
not drift in the operating environment. An attack day from the original
extractor and Monday from the same extractor still differ hugely, because the
attack traffic is different traffic — so "attack day looks drifted" is
guaranteed, and "a quiet day looks drifted" is equally likely. Patator is the
only family where the attack traffic is *statistically* distinct enough that
MMD separates cleanly (1.00), which is the tell: the statistic is detecting
"unusual traffic volume", not "unusual environment".

**Consequence for the project:** MMD-on-scores cannot be the drift alarm. The
shipped `detection/drift_monitor.py` (score-percentile movement, which E24's
reputation tracker supersedes) is the right family of mechanism, but a
distribution-level test is the wrong tool. Kept as a bound: we now know the
alarm has to be *causal and local* (per-host running statistics), not global
and distributional.

## Files

- `exp_e3_drift_mmd.py` — procedure
- `exp_e3_drift_mmd.json` — per-family results
