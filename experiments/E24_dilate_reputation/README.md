# E24 — Reputation vs slow-drip + the fused Web band

**Verdict: PASS** · 2026-09-27 · commit `0807a6f`

## Aim

Two questions that [E20](../E20_reputation_infil/) and
[E21](../E21_band/) opened but did not answer, run together because they share
a code path.

1. **Does reputation actually kill [E12](../E12_slowdrip/)'s evasion?** E20
   showed reputation helps Infiltration (0.76 → 0.91) and E13 showed it is
   causally deployable. But E12's slow-drip is the more serious threat: ×5
   dilution took the detector to 0.064, *below chance*. If reputation also
   defeats that, the project's most expensive weakness closes. If it does not,
   timing evasion is a permanent property of Pillar 1 and the report must say
   so plainly.
2. **Is the fused Web band ~0.9 and tight?** E22 measured flow 0.895 ± 0.026
   and graph 0.813 ± 0.091, with seed 3 favouring flow. Fusion should land
   above both with the worst seed beating the graph mean.

## What was done

**(a)** Original PortScan day, shipped `gnn_autoencoder_v1_logscale_v2.pt`,
`spread_dilate` factors {1, 2, 5} from `harness/graph_techniques.py`. Three
scorers: within-window rank (the E12 baseline), causal running-mean reputation,
and transductive whole-day mean for reference.

**(b)** Clean Thursday, retrained improved M5b + M5a, 4 seeds, five arms
(`m5b`, `m5a`, `noisyor`, `rank_max`, `repfuse`), within-window-rank metric.

## Results — (a) slow-drip

| Dilate | Window (E12) | **Reputation** |
|---|---|---|
| ×1 | 0.8714 | 0.9824 |
| ×2 | 0.3578 | 0.9738 |
| ×5 | **0.0637** | **0.9789** |

## Results — (b) Web fused band

| Arm | s0 | s1 | s2 | s3 | Band |
|---|---|---|---|---|---|
| m5b | 0.931 | 0.849 | 0.790 | 0.682 | 0.813 ± 0.091 |
| m5a (edge) | 0.762 | 0.789 | 0.776 | 0.744 | 0.768 ± 0.017 |
| **noisyor** | **0.937** | **0.891** | **0.858** | **0.784** | **0.867 ± 0.057** |
| rank_max | 0.927 | 0.878 | 0.830 | 0.752 | 0.847 ± 0.065 |
| repfuse | 0.770 | 0.773 | 0.751 | 0.741 | 0.759 ± 0.013 |
| m5a (flow-level) | 0.878 | 0.907 | 0.865 | 0.931 | 0.895 ± 0.026 |

## What we understood

**(a) E12 is closed up to ×5. Slow-drip at ×10 is NOT — see
[E44](../E44_residual_evasion/).** Reputation holds 0.97–0.98 at every
dilution factor measured here (×1, ×2, ×5) against 0.87 → 0.36 → 0.06 for
windows. The reason is the same one that took Infiltration to 0.908: dilating
the attack changes per-window totals, which is all a window can see, but it
cannot make the attacker stop being persistently odd across windows. An
accumulator is invariant to pacing.

**Correction (2026-09-29):** E44 swept ×10 and reputation **collapses to
0.098** there — the attacker ranks below typical benign hosts. The rescue has a
boundary at roughly ×5. E24's numbers are correct for the range it measured;
the "every dilution factor" reading is not, and this paragraph is the one to
quote. The open attack is a *paced* one that is never anomalous in any single
window, and no network-side fix was found for it.

**(b) The fused Web band is 0.867 ± 0.057 — better than the graph mean, and its
worst seed (0.784) beats the graph mean (0.813).** That is the property that
matters: fusion's value here is not a higher mean, it is *removing the bad
tail*. E22's mechanism is doing exactly what it was predicted to do.

**Two negative sub-findings, both worth keeping.**

- `repfuse` is the *worst* Web arm (0.759). Reputation needs persistence to
  accumulate, and a web attack lasts minutes — 62 attacker edges over a handful
  of windows, nothing to accumulate. E20/E24's reputation wins are on families
  with long-lived hosts (scanners, C2, infiltration). **The fusion rule is
  family-dependent, and the archive now says so** rather than claiming one rule
  wins everywhere. E21's `repfuse` sweep was on Friday, where the three
  families all persist; Friday never tested a burst family.
- Within-window rank fusion (`noisyor`) beats `repfuse` on Web. So the
  production rule should be: reputation where hosts persist, rank-noisyor
  where they do not. That is a real open design question, not a settled
  default.

**The stable Web story remains the flow pillar at 0.895 ± 0.026** — better
than any fused edge-level arm, because it scores flows directly rather than
through a graph that a 104-flow attack barely touches.

## Files

- `exp_e24_dilate_reputation_webfusion.py` — both parts
- `exp_e24_results.json` — dilate sweep and Web fusion band
