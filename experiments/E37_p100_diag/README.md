# E37 — P@100 structural-cap diagnosis (RC-27, RC-28)

**Verdict: CONTROL (and a retired metric)** · 2026-08-21 · commits `f222f44`, `d041223`

## Aim

P@100 is the metric most IDS papers report, and it had been in this project's
headline tables for a month without anyone checking whether it could possibly
mean anything. This experiment asked that directly, and the answer retired the
metric.

## What was done

Two diagnostics on the full PortScan/attack days:

1. **The cap.** What is P@100 even when a day has 1–8 attackers among
   thousands of hosts? Measured directly rather than assumed.
2. **The small-window filter.** RC-28's claim that filtering out low-traffic
   windows would clean the queue. The filter was implemented and run.

## Results

- Host-level P@100 sits at exactly **bad/100** — 0.01–0.08 across families,
  i.e. the detector flags every attacker in the top 100 and the number is
  *arithmetically* capped by attacker rarity, not limited by model quality.
- **Attackers rank 1–35; recall@100 = 1.0.**
- Small-window filter: **NEGATIVE.** False-positive queue median 128–175
  hosts; filtering changed nothing. The queue noise is drift, not junk windows.

## What we understood

**P@100 was measuring the dataset's class ratio, not the detector.** This is
the clearest instance of a recurring theme in this archive (see also
[E07](../E07_cluster_denoise/)'s edge-count collapse and
[E32](../E32_perfamily_thr/)'s base-rate problem). When a metric's ceiling is
set by how many positives exist, the metric carries no information about the
model. Reporting P@100 = 0.08 as a performance figure is reporting the dataset.

**The replacement metrics are strictly better and were adopted:**
`recall@100` (did the attacker make the top 100 at all) and **attacker rank**
(where exactly did they land). Both are meaningful because they ask about the
*specific* attacker rather than about every labelled positive. Recall@100 = 1.0
with top-35 ranks is a far stronger statement than P@100 = 0.08, and it is a
true one.

**The negative filter result is worth keeping precisely because it looked
sensible.** The intuition — "drop tiny windows, remove junk" — was reasonable
and wrong. The FP queue is not made of small windows; it is made of *drift*,
the phenomenon [E09](../E09_drift_repin/) later showed re-pinning cannot fix
and that motivated the rank-cut alerting in [E14](../E14_risk_controls/). One
experiment's negative result set up the next experiment's positive one.

**Consequence for every later experiment:** the archive README's rule that a
claimed AUC improvement must be reported next to its edge/population count
comes directly from this. A metric that improves because you shrank the
population is this failure wearing a different hat.

## Files

- `diag_p100.log`, `diag_p100b.log` — the two diagnostics
- `exp_edge_full40.json`, `exp_edge_full40.log` — the edge-level full run, 40 epochs
  (its findings on the temporal/LSTM half were reproduced in
  [E02](../E02_edge_fusion/))
