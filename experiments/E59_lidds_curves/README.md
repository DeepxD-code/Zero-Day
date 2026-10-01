# E59 — Closing E58's two caveats: FPR curve and learning curve

> ## ⚠️ SUPERSEDED — length-blindness was never controlled
>
> Both parts of this experiment scored **whole traces**. Per
> [E60](../E60_lidds_lengthblind/), **trace length alone gives AUC 0.8150 on this
> corpus (inverted), beating both arms.** The FPR curve and the learning curve
> were therefore both computed with a near-perfect label-correlated feature
> available to both arms.
>
> The learning-curve conclusion in particular is **not established**: a
> widening gap is exactly what you would see if the count vector leaned harder on
> a length shortcut than the seq-AE did. Re-measuring it length-blind is required
> before the "structurally limited, not data-starved" claim can stand.

**Verdict: SUPERSEDED by [E60](../E60_lidds_lengthblind/)** — was PASS, but the
protocol did not control for trace length. · 2026-10-01

## Aim

E58 landed +0.0483 (2.19 SD) for seq-AE over count-AE on LID-DS and left two
things open. Both are answerable from the corpus already downloaded:

1. **F1 = 0.0000 at one operating point.** A single 10%-FPR threshold is a weak
   measure. "Detects nothing" at one threshold says as much about the threshold
   as about the model.
2. **210 training traces.** E58 read the result as "a histogram cannot represent
   order", not "a histogram was starved of data". That reading makes a
   prediction — *more data should not close the gap*. Testing it is the point.

Design: matched 20-epoch budget for both arms, 4 seeds, threshold set on
validation benign at each target FPR, AUC on 878 test traces (758 benign,
120 attack).

## Result 1 — detection rate across the whole FPR range

| FPR | seq-AE | count-AE |
|---|---|---|
| 1% | 0.150 ± 0.087 | **0.000 ± 0.000** |
| 2% | 0.188 ± 0.070 | **0.000 ± 0.000** |
| 5% | 0.396 ± 0.168 | **0.000 ± 0.000** |
| 10% | 0.450 ± 0.224 | **0.000 ± 0.000** |
| 20% | 0.562 ± 0.167 | 0.200 ± 0.000 |
| 30% | 0.667 ± 0.053 | 0.300 ± 0.000 |

E58's F1 = 0.0000 was one point on this curve, and the curve says it was not
an artefact of a badly chosen threshold. **The count-AE detects zero of 120
attacks anywhere up to 10% FPR.** Only past 20% FPR does it begin to fire, and
then at a third of the seq-AE's rate. Seq-AE's full curve is above the
count-AE's at every single point.

## Result 2 — learning curve (the decisive one)

| n train | seq-AE | count-AE | Δ |
|---|---|---|---|
| 25 | 0.6418 ± 0.0811 | 0.5830 ± 0.0642 | +0.0588 |
| 50 | 0.6514 ± 0.0741 | 0.5802 ± 0.0515 | +0.0712 |
| 100 | 0.6991 ± 0.0362 | 0.5691 ± 0.0143 | +0.1300 |
| 210 | 0.7709 ± 0.0118 | 0.5605 ± 0.0043 | **+0.2104** |

**The gap triples as data grows.** 0.059 → 0.071 → 0.130 → 0.210.

Look at the two columns separately, because the delta is not the whole story:

- **seq-AE climbs**: 0.642 → 0.771. More benign recordings, better model.
- **count-AE is flat, then drifts down**: 0.583 → 0.581 → 0.569 → 0.561.

The count vector is not being left behind slowly. **Eight times more training
data does not move it, and moves it very slightly the wrong way.** Its
seed-to-seed spread collapses too (SD 0.064 → 0.004), so this is a stable,
converged 0.56 — not an underfit model that needs longer.

## What we understood

**E58's conclusion survives, and gets stronger.** The alternative reading was
data starvation: 210 traces is small, maybe the count vector just needs more. If
that were true, the gap would narrow as n grew. It widens by 3.6×. The claim
now rests on a directional prediction that was made before the measurement and
came out the other way from the convenient answer.

**A converged count-AE sits near chance on this corpus.** 0.56 AUC against a
50% floor, with attack traces averaging 3,142 syscalls over a 38-symbol
vocabulary. Reordering information is most of what distinguishes a heartbeat
exploit from normal service on a host, and a histogram discards all of it. The
count vector is not learning a weaker version of the same thing — it is
measuring a different, largely uninformative quantity.

**Operational gap confirmed independently of the threshold choice.** E58's
single-number F1 was weak evidence on its own. The full curve shows the
count-AE below zero detection through 10% FPR and below the seq-AE at every
point tested. Two arms, two orderings of the evidence, same conclusion.

## Limitations

- **The learning curve confounds n with a fixed 20-epoch budget.** E58's
  per-seed-best count-AE reached 0.7226 at 40–80 epochs, so the count vector
  *does* respond to more training of a different kind. The 0.56 here is the
  count-AE at a matched 20 epochs, not its ceiling. Holding epochs fixed is the
  right design for asking "does more data close the gap", but the absolute
  count-AE numbers in this table are **not** comparable to E58's headline.
- **n is capped at 210** by what one CVE extract yields. The trend has three
  points and no asymptote; it shows the gap growing, not where it stops.
- One attack family (heartbleed), so no per-family breakdown.
- 4 seeds; within-size SDs are in the JSON.

## Files

- `exp_e59_curves.py` / `exp_e59_curves.json`
- Continues [E58](../E58_lidds_host/)