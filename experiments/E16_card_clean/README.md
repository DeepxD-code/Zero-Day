# E16 — 7-family report card, CLEAN data (the contamination proof)

**Verdict: PASS (methodology) / the most important experiment in the archive** · 2026-09-27 · commits `b63783d`, `418225e`, `edd0746`

## Aim

E15's numbers were strong but all from one dataset — the original CIC-IDS2017
release. The literature is explicit that release is broken: Liu/Engelen et al.
(CNS 2022, "Error Prevalence in NIDS Datasets") found documented errors in both
CIC-IDS-2017 and CSE-CIC-IDS2018 and published a regenerated, relabelled
version. Our own repo already encoded the lesson twice (gotcha #12: Thursday
WebAttacks is 63% junk rows; CLAUDE.md's PIKACHU correction).

So: score the *same shipped checkpoint* on the *fixed* dataset, same protocol,
and see whether the model is real or the testbed was flattering it.

## What was done

Downloaded `CICIDS2017_improved` (CNS2022, 328 MB) from
`intrusion-detection.distrinet-research.be`. Schema differs from the original:
91 columns, one file per weekday with **mixed** families, explicit
`- Attempted` sub-labels, and a fixed feature extractor (82 numeric flow
columns, not 76).

Protocol:
- **Attempted attacks excluded** — 11,979 flows. This *is* the pollution fix:
  in the original release, "attempted" attacks (failed logins, partial scans)
  are labelled as full attacks.
- Families cut by **label**, not by file: `FTP-Patator` + `SSH-Patator`,
  `DoS Hulk/GoldenEye/Slowloris/Slowhttptest` + `Heartbleed`, the three `Web
  Attack` variants, `Infiltration` + `Infiltration - Portscan` (71,767 flows
  that the original release folds into Infiltration), `Botnet`, `Portscan`,
  `DDoS`.
- Per-**day-file** scoring, then pool edges. (See "the two bugs" below.)

## Results — the contamination proof

Same shipped checkpoint, original data vs clean data:

| Family | E15 original | **E16 clean** | Δ |
|---|---|---|---|
| Patator | 0.963 | **0.186** | −0.777 |
| DoS | 0.883 | **0.467** | −0.416 |
| WebAttacks | 0.930 | **0.083** | −0.847 |
| Infiltration | 0.577 | 0.568 | −0.009 |
| Botnet | 0.460 | 0.527 | +0.067 |
| PortScan | 0.871 | **0.467** | −0.404 |
| DDoS | 0.899 | **0.908** | +0.009 |

After the per-day fix and the M5b retrain ([E17](../E17_retrain_improved/)),
the clean-data card reads: Patator 0.983, DoS 0.991, Web 0.931, Infiltration
0.760, Botnet 0.418, PortScan 0.971, DDoS 0.973.

## What we understood

**Four of seven families collapsed — and that is the finding, not a failure.**
The original release's headline numbers were measuring the dataset's
construction, not the detector. Once the relabelled data exposed the real
attack topology, the original-trained model turned out to have learned *that
testbed's* normality: on Thursday it flags hammered internal servers and
external internet clients above the actual attacker.

Only DDoS (pure volume, 0.899 → 0.908) and Infiltration/Botnet (whose labels
the fix barely touched) survived unchanged. Those two are the families whose
signal is volume or persistence rather than fine label boundaries.

**Then [E17](../E17_retrain_improved/) retrained on clean Monday and the
0.95–0.99 numbers came back** — for the improved-trained model. The
architecture was always fine; the training data was the variable. And the
failure is symmetric: the improved-trained model collapses on original data
too. Neither checkpoint generalises across testbeds, which is why
[E29](../E29_transfer/) exists.

## Two bugs of my own, both instructive

1. **Relative window buckets collided days.** `_window_key()`
   (`graph_builder.py:207`) buckets time *relative to the frame's start*, so
   concatenating four day-files merged Tuesday-Thursday into shared windows and
   the graphs were nonsense. Caught because Infiltration read 0.76 by
   mean-rule but 0.93 by src-rule on the "same" data — a 0.17 gap that could
   only be a measurement bug. Fixed by scoring each day-file separately
   (`418225e`).
2. **Pooling edges across days diluted AUC.** Inf 0.76 pooled vs 0.93
   per-day. Fixed the same way.

Both are the E07/A3/E11 error class again: measuring on a population that is
not the population the claim is about. Three occurrences in two days is what
finally made the guard rails in [E14](../E14_risk_controls/) non-optional.

## Files

- `exp_e16_report_card_improved.py` — procedure (per-day, label-cut, attempted-excluded)
- `exp_e16_report_card_improved.json` — the clean card
