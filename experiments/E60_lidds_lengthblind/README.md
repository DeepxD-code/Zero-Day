# E60 — Length-blind host detection on two LID-DS families

**Verdict: PARTLY RETRACTED by [E61](../E61_lidds_grid_ext/).** · 2026-10-01

> ## ⚠️ Two retractions — read E61 before quoting anything here
>
> **1. Length confound (this experiment fixed it).** Both [E58](../E58_lidds_host/)
> and [E59](../E59_lidds_curves/) scored whole traces, and on LID-DS trace length
> is a near-perfect label proxy: **length alone, inverted, gives AUC 0.8150 on
> CVE-2014-0160 — beating both arms**. Their absolute numbers are contaminated.
>
> **2. Truncated grid (found by E61).** The CVE-2012-2122 result below is
> **retracted**. On E60's grid {10,20,40,80} seq-AE led by +0.0954 (z = +4.50);
> on {5…320} the gap is **+0.0001 (z = +0.06) — inside noise**, and the count-AE
> reaches 100% detection. 80 epochs was simply undertrained for a 31-feature MLP.
>
> **What survives here:** the length-blind protocol itself, the guard that proves
> the shortcut is dead (1.0000 → 0.5000), and the **CVE-2014-0160** result, which
> E61 did not finish — so it remains **edge-pinned and unresolved**, not confirmed.
>
> The representation finding is currently supported by **E01 alone**.

## Why this protocol exists

Downloading a second CVE (CVE-2012-2122) to attack E58's 210-trace training cap
exposed a confound nobody had checked: **trace length alone separates the
classes**, with the direction depending on the family.

| Family | normal median | attack median | length-only AUC | inverted |
|---|---|---|---|---|
| CVE-2014-0160 | 3,396 | 1,399 | 0.1850 | **0.8150** |
| CVE-2012-2122 | 15,934 | 72,446 | **1.0000** | 1.0000 |

Two separate problems:

1. **CVE-2012-2122 is perfectly separable by duration alone.** Every attack
   trace (min 61,210 syscalls) is longer than every benign one (max 36,590). Any
   raw AUC there measures recording length, not behaviour.
2. **CVE-2014-0160 was already contaminated, less obviously.** Length alone,
   inverted, gives **0.8150 — which beats both host arms** (seq-AE 0.7709,
   count-AE 0.7226). E58 reported 0.771 for the seq-AE without ever checking
   whether a one-line length feature did better. It did.

## The fix

Every sample is a fixed **W = 1024**-token window, so no sample ever encodes its
own duration. Traces shorter than W are **dropped, never padded** — padding would
leak length back in through the PAD count.

W was set by a rule fixed before results were seen: the largest window retaining
the majority of every (family, label) cell.

| W | 2014 normal | 2014 attack | 2012 normal | 2012 attack |
|---|---|---|---|---|
| 256 | 97% | 82% | 100% | 100% |
| 1024 | 93% | 62% | 97% | 100% |
| 3000 | 57% | **18%** | 97% | 100% |

**No W retains 90% of the heartbleed attacks** — 18% are under 256 syscalls,
because heartbleed is a single request/response and is simply short. The rule was
relaxed to "majority of every cell" and the cost is stated below.

### The guard actually fires

| Family | raw length-only AUC | windowed |
|---|---|---|
| CVE-2012-2122 | 1.0000 | **0.5000** |
| CVE-2014-0160 | 0.1850 | **0.5000** |

The shortcut is dead by construction, and `all_windows_exactly_W` is True for
every family.

## Results — length-blind, 4 seeds, AUC per trace

| Family | Arm | AUC (max agg) | AUC (mean agg) | det@10%FPR |
|---|---|---|---|---|
| **CVE-2012-2122** | **seq-AE** | **0.9731 ± 0.0117** | 0.9754 ± 0.0098 | 0.992 |
| | count-AE | 0.8777 ± 0.0276 | 0.8548 ± 0.1435 | 0.867 |
| | **Δ** | **+0.0954 (z = +4.50)** | | separated |
| **CVE-2014-0160** | **seq-AE** | **0.6419 ± 0.0086** | 0.6884 ± 0.0083 | 0.360 |
| | count-AE | 0.5269 ± 0.0035 | 0.5372 ± 0.0074 | 0.209 |
| | **Δ** | **+0.1150 (z = +17.52)** | | separated |

## What we understood

**The representation finding survives, and is bigger than E58 claimed.** E58
reported +0.048 on CVE-2014-0160. Length-blind, that family gives **+0.115
(z = 17.5)**, and a second family gives **+0.095 (z = 4.5)**. The contamination
was not inflating the seq-AE's advantage — it was masking it, because length was
helping the count vector along with everything else.

**The count-AE is at chance on heartbleed once length is removed: 0.527 ± 0.004.**
Twenty-two attack windows against 600 benign, and a histogram ranks them barely
better than a coin flip. Combined with E59's finding that the count vector was
flat across an 8× increase in training data, the picture is consistent: on this
corpus the count vector was largely reading duration.

**The win is not an artefact of the aggregation choice.** This mattered more
than usual, because `max` is the natural detector semantics for an attack
occurring *somewhere* in a long trace, so it could manufacture a result. seq-AE
wins under **both** max (+0.095 / +0.115) and mean (+0.121 / +0.151), and mean is
actually the *higher* of the two on CVE-2014-0160. The aggregation is not doing
the work.

**CVE-2014-0160 is a genuinely hard family, and that is informative.** 0.642 with
length removed, against 0.771 with it available. Two-thirds of heartbleed's
signal on a host *was* duration — a request that takes 1,400 syscalls instead of
3,400. Order-aware modelling recovers real signal but recovers a minority of what
the shortcut gave away.

## Limitations

- **The epoch grid was truncated on both edges — all eight cells.** Picks were
  80 (top edge) on CVE-2012-2122 seq-AE and both count-AEs, and 10 (bottom edge)
  on CVE-2014-0160 seq-AE. Per the standing rule, those numbers are not results
  yet; [E61](../E61_lidds_grid_ext/) re-runs on {5…320}.
- **Dropping short traces selects on length**, the variable being neutralised.
  Equal-length windows remove length as a *feature* but do not make the trace
  *population* length-matched: on CVE-2014-0160, 45 of 120 attack traces were
  dropped as too short, and the 129 surviving windows come from the longer
  attacks. The surviving population is not E58's population.
- **Absolute AUCs are not comparable to E58** — the unit of modelling is a
  window, not a recording. The seq-vs-count comparison inside E60 is like-for-like
  because both arms get byte-identical windows.
- **Window caps:** 500 train and 600 test-benign windows per family, applied
  identically to both arms. Every attack window kept. 1,656 benign test windows
  were dropped on CVE-2012-2122 and 1,123 on CVE-2014-0160.
- K=3 windows per trace, evenly spaced — an attack confined to a narrow span
  could be missed by sampling. Mitigated for memcached amplification (a repeating
  flood), untested for sparse exploits.
- One attack family per CVE; no within-family breakdown.

## Files

- `exp_e60_lengthblind.py` / `exp_e60_lengthblind.json`
- Loader: `../../detection/lid_ds_loader.py` (adds `family`)
- Extractor: `../../detection/lid_ds_extract.py`
- Supersedes the absolute numbers in [E58](../E58_lidds_host/) and
  [E59](../E59_lidds_curves/)