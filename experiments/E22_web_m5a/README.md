# E22 — Is the flow pillar stable where the graph pillar flips?

**Verdict: PASS** · 2026-09-27 · commit `4e3a15f`

## Aim

[E21](../E21_band/) diagnosed WebAttacks' 0.813 ± 0.091 as undertraining and
pointed at E26. But before spending a retrain, a cheaper question: **is the
graph pillar even the right tool for this family?**

E6 and E12 explain why not. A port scan is topological — `out_degree` spikes,
and dilating the timeline destroys the per-window anomaly entirely. A web
attack is a payload pattern: packet-size distributions, IAT structure, header
costs. Those survive in the per-flow features regardless of how the graph
aggregates them. If that intuition is right, the flow pillar should be stable
across seeds exactly where the graph pillar is not.

## What was done

Per-seed WebAttacks AUC on clean Thursday from the flow pillar
(`m5a_revived_improved{,_s1,_s2,_s3}.pt`), flow-level scoring (not
edge-aggregated), same split/attempted-exclusion as E16.

Then a diagnostic on the *graph* pillar to locate where the web attacker
actually sits in the queue per seed:

| Seed | Graph train loss | Attacker median rank | Fraction in top 10% |
|---|---|---|---|
| 0 | 0.000084 | 0.961 | 0.79 |
| 1 | 0.000081 | 0.912 | 0.55 |
| 2 | 0.000184 | 0.789 | 0.18 |
| 3 | 0.000188 | 0.701 | 0.11 |

## Results

| Pillar | s0 | s1 | s2 | s3 | Band |
|---|---|---|---|---|---|
| graph (edge) | 0.931 | 0.849 | 0.790 | 0.682 | 0.813 ± 0.091 |
| **flow** | **0.878** | **0.907** | **0.865** | **0.931** | **0.895 ± 0.026** |

Also measured: the web attacker scores ~100× below the benign top-1% on
*every* seed (overlap fraction 1.000 for all four) — he is a small fish in a
shark pond (104 web flows against 71,767 infiltration-scan flows and 288k
benign). His rank therefore depends entirely on window company plus seed
geometry, which is exactly the ±0.091 spread.

## What we understood

**The two pillars fail on different seeds, which is the precondition for
fusion to work.** Seed 3 is the graph pillar's *worst* case (0.682) and the
flow pillar's *best* (0.931). That is not a coincidence to be averaged away —
it is the structural claim of the two-pillar design, now measured:

- graph pillar = relational topology, fragile under timing evasion (E12) and
  undertraining (E21)
- flow pillar = per-flow payload statistics, immune to both, but blind to
  anything spread across many individually-normal flows (the port scan)

Neither dominates. [E24](../E24_dilate_reputation/) then measured the fused
Web band at 0.867 ± 0.057 — better than the graph band, and crucially the
**worst seed (0.784) beats the graph pillar's mean (0.813)**.

**The flow pillar's stability is what makes one M5a checkpoint shippable.**
±0.026 across four seeds justifies serving seed 0 only, which is why
`detection/` holds one `m5a_revived_improved.pt` and not four.

**E26 was still the right call.** The graph pillar is the one in production
default, so undertraining there had to be fixed rather than routed around;
val-picked epochs took it to 0.900 ± 0.017 ([E28](../E28_web_valband/)). But
E22 is why that fix is an improvement rather than a rescue.

## Files

- `exp_e22_web_m5a_band.json` — flow band + graph rank diagnostics
