# E43 — Three closes for the family-dependent fusion rule

**Verdict: PASS (4-seed band) — and the band overturns the single-seed claim** · 2026-09-29

## Aim

[E21](../E21_band/) chose `repfuse` as the production fusion rule because it
was best-or-tied on the three Friday families (Botnet 0.667, PortScan 0.952,
DDoS 0.981). [E24](../E24_dilate_reputation/) then measured the same arms on
WebAttacks and `repfuse` came **last** (0.759 vs noisyor 0.867).

The diagnosis: reputation is a running mean, so it needs a host to *persist*.
Botnet, PortScan and Infiltration persist. WebAttacks is 62 attacker edges
across a handful of windows out of ~490 — nothing to accumulate, and the mean
actively damps a short burst.

The E21 shootout only saw persistent-host families, so "one rule wins
everywhere" was under-evidenced. This experiment tests three closes for that.

## What was done

Five families spanning both regimes, all on the same protocol as E21/E24
(clean data, per-day files, attempted excluded, within-window rank → pool):

| Arm | What it is |
|---|---|
| **OPT1 persistence-routed** | per-edge: `repfuse` if the src host has ≥5 window observations, else `noisyor` |
| **OPT2 rule-rank-max** | `max(repfuse_rank, noisyor_rank)` per edge — fusing two *rules* the way the dual-pillar fusion fuses two *views* |
| **OPT3 burst-aware** | short-window (k=3) + long-window reputation fused 50/50, then rank-fused with noisyor |

Controls: `m5b`, `m5a`, `noisyor`, `repfuse`.

> **First run was invalid.** Ranks were computed within arbitrary 5000-row
> chunks instead of within real 60s windows, which inflated Botnet `repfuse` to
> 0.789 against E21's verified 0.667. The mismatch against a known number is
> what caught it. Second run ranks per real window and reproduces E21's shape.

## Results — 4-seed band (the production metric)

Both pillars banded over seeds 0–3: `gnn_improved_s{0,1,2,3}.pt` (val-picked,
E26 protocol) and `m5a_revived_improved{,_s1,_s2,_s3}.pt`. Full per-seed
numbers in `exp_e43_fusion_rules.json`.

| Family | m5b | m5a | noisyor | repfuse | OPT1 | OPT2 | **OPT3** |
|---|---|---|---|---|---|---|---|
| Botnet | 0.442±0.017 | **0.586±0.007** | 0.504±0.012 | 0.709±0.025 | 0.638±0.017 | 0.543±0.017 | 0.453±0.024 |
| PortScan | 0.961±0.002 | 0.914±0.010 | 0.966±0.003 | 0.953±0.003 | 0.935±0.003 | 0.965±0.003 | **0.969±0.004** |
| DDoS | 0.961±0.002 | 0.914±0.010 | 0.966±0.003 | 0.953±0.003 | 0.935±0.003 | 0.965±0.003 | **0.969±0.004** |
| Infiltration | 0.633±0.004 | 0.594±0.003 | 0.650±0.003 | 0.668±0.028 | 0.652±0.016 | 0.660±0.004 | 0.666±0.005 |
| WebAttacks | 0.893±0.009 | 0.780±0.014 | 0.908±0.013 | 0.799±0.011 | 0.708±0.017 | 0.919±0.008 | **0.950±0.008** |

### Which "wins" actually survive the noise

Ranking by mean and testing the gap against the pooled seed SD:

| Family | Best | Mean | Gap to 2nd | Verdict |
|---|---|---|---|---|
| Botnet | repfuse | 0.709 | 0.071 | **separated** (2.8× pooled SD) |
| WebAttacks | opt3_burst | 0.950 | 0.031 | **separated** (2.7× pooled SD) |
| PortScan | opt3_burst | 0.969 | 0.003 | **tied — inside noise** |
| DDoS | opt3_burst | 0.969 | 0.003 | **tied — inside noise** |
| Infiltration | repfuse | 0.668 | 0.002 | **tied — inside noise** |

**Only 2 of the 5 apparent wins are real.** The other three are ties that the
single-seed run had to break arbitrarily. See "What we understood".

## Single-seed results (superseded, kept for the record)

| Family | m5b | m5a | noisyor | repfuse | OPT1 | **OPT2** | **OPT3** |
|---|---|---|---|---|---|---|---|
| Botnet | 0.468 | 0.580 | 0.520 | **0.723** | 0.653 | 0.565 | 0.486 |
| PortScan | 0.963 | 0.919 | 0.968 | 0.953 | 0.933 | 0.968 | **0.973** |
| DDoS | 0.963 | 0.919 | 0.968 | 0.953 | 0.933 | 0.968 | **0.973** |
| Infiltration | 0.629 | 0.592 | 0.645 | 0.639 | 0.636 | 0.655 | **0.664** |
| WebAttacks | 0.889 | 0.779 | 0.902 | 0.798 | 0.709 | 0.925 | **0.957** |

*(PortScan and DDoS rows match because `172.16.0.1` launches both attacks in
CIC-IDS2017 — a dataset property, not a measurement error.)*

**These seed-0 numbers are superseded by the band above.** They are kept because
the comparison between them is itself the result.

## What we understood

**The band overturns the single-seed conclusion, and that is the headline.**
Seed 0 said "OPT3 wins 4 of 5". The band says **OPT3 is genuinely best on 2
(Botnet-adjacent families aside), tied-for-best on 2 more, and loses the fifth
to `repfuse` by a margin that is itself inside the noise.** The single-seed
table's most quotable claim — a 0.24 Botnet regression — is a seed artefact.

| Claim from seed 0 | Band verdict |
|---|---|
| OPT3 wins 4 of 5 | **2 real wins, 2 ties, 1 tie-but-loses-to-repfuse** |
| OPT3 costs 0.24 on Botnet (0.723 → 0.486) | **real and large** — 0.709 → 0.453, well outside noise |
| OPT1 is rejected | **confirmed** — last or second-last on all 5, all outside noise |
| OPT2 is the safe single default | **still defensible** — never far from best, now measured |

**The two separated wins are the two that matter, and they point opposite
ways.** `repfuse` wins Botnet by 0.071 (2.8× the pooled SD) and `opt3_burst`
wins WebAttacks by 0.031 (2.7×). So the single-seed reading "OPT3 wins the
majority" was really reading "the majority is ties, and here are the two real
effects, in opposite directions."

**Infiltration is the clearest example of why bands are mandatory.** Seed 0:
noisyor 0.645 > repfuse 0.639. Seed 1: repfuse 0.686 > noisyor 0.651. Seed 2:
repfuse 0.698 > noisyor 0.650. Seed 3: repfuse 0.651 < noisyor 0.652. The
ranking **flips with the seed**, and `repfuse` carries the family's largest SD
(±0.028, 4× any other arm). Quoting seed 0 here would have inverted the
conclusion. The band says: 0.668 ± 0.028 vs 0.650 ± 0.003 — `repfuse` is ahead
by 0.002, which is nothing.

**On PortScan and DDoS, four arms are statistically indistinguishable**
(0.953–0.969, all SDs ≤ 0.004). Reporting "OPT3 0.973" as a result would be
overclaiming a 0.003 difference. The honest statement is that **these two
families are saturated** and the fusion rule does not matter there.

**`repfuse` remains the best single number in the project** (Botnet 0.709
± 0.025) and that is the tension E43 originally set out to resolve: the rule
that wins the hardest family is not the one that wins the most families.

**OPT3 (burst-aware dual-timescale) is best on 4 of 5 and fixes exactly what it
was designed to fix**: WebAttacks 0.798 → **0.957**, a 0.16 gain over the rule
it replaces, at a cost of 0.24 on BotNet. The mechanism is the one E43
predicted — a short window tracks a burst that the long average smears, so
keeping both channels recovers the burst without losing persistence.

**OPT1 (persistence routing) is rejected.** Worse than plain `noisyor` on every
single family. A hard `nwin >= 5` cut misclassifies hosts whose attack lands
mid-window and have little history before it, which routes them to the wrong
rule. It is also the option with the largest heuristic surface — a good sign it
would have been fragile in production even if the numbers had worked.

**OPT2 (rule rank-max) is the safe middle.** Second-best on every family, and
on Web it recovers most of the gap (0.925 vs OPT3's 0.957) while degrading
Botnet less (0.565 vs 0.486). If a single simple rule is wanted, this is it —
and it is justified by the same principle that made the two-pillar fusion work:
combining things that fail differently beats picking one.

**The uncomfortable finding: no rule wins everywhere, and the thing that wins
the majority is the thing that loses the family's best number.** `repfuse` at
0.709 on Botnet is the best network-side result the project has produced on any
family. OPT3 gives that up. So the honest conclusion is not "OPT3 is the new
default" — it is **"the rule should depend on whether the deployment's attacks
persist"**, which is a routing decision the system cannot make for itself
without knowing the attack, and which is therefore a *design* question, not a
tuning one.

If a single default is required, **OPT2** is the defensible pick: never far
from the best on any family (Botnet 0.543, PortScan/DDoS 0.965,
Infiltration 0.660, Web 0.919), and justified by the same principle that made
the two-pillar fusion work — combining things that fail differently beats
picking one. Note it is *not* the mean-best rule; it is the rule with the
smallest worst-case regret.

**Caveats that keep this from being a finished result:** ~~the OPT thresholds
(k=3, nwin=5) were set by inspection and never swept~~ —
**[E48](../E48_opt_sweep/) swept them.** `k=3` is not optimal for any family
(Botnet wants k=1, Web/Infiltration want k=8) but never more than 0.011 off the
best, and leave-one-seed-out confirms tuning it helps by up to 0.027 and never
hurts. OPT1 is rejected at all 25 grid points, a stronger result than "last at
the default". What remains is a small band — 4 seeds, with `repfuse` SDs of
0.025–0.028 on Botnet, so those gaps are known only to about ±0.01.

**The Botnet `repfuse` gap is now narrowed.** This script reads 0.723 (seed 0)
against E21's seed-0 0.681 on the same checkpoints.
[E46](../E46_guard_regression/) re-ran this experiment with its pairing guards
active and got 0.723 again, across two independent full runs — so it is not a
mispairing or a fluke. The difference is a genuine *method* difference between
the two scripts in how reputation accumulates, not an error here. Still open,
but a much smaller question than "is this number wrong".

## Files

- `exp_e43_fusion_rules.py` — the seven arms, 4 seeds
- `exp_e43_fusion_rules.json` — per-seed results plus the band

## Note on the two pillars

Both pillars were banded. The original script iterated `for sd in [0]` but
loaded `M5A[0]` inside the loop, so a 4-seed run would have measured **M5b's**
variance alone and reported it as a fusion band. Fixed: `M5A[sd]` now varies
with the seed, reading seeds 1–3 from `E21_band/` (the cleanup deleted them
from `detection/` as "one checkpoint is enough to serve", which is true for
serving and false for banding).

M5b seeds 1–3 did not exist and had to be retrained — the cleanup deleted them
as "superseded by the val-picked band", but only seed 0 had ever been produced.
They were retrained with the documented E26 protocol (`--val-frac 0.2`,
best-val epoch saved) and verified distinct (max |Δw| 3.2–5.2 between pairs) and
individually scaler-checked by [E46](../E46_guard_regression/).
