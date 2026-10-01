# E14 — R1/R2/R3 risk elimination in production code

**Verdict: PASS** · 2026-09-26 · commit `53d5dd3`

## Aim

E13 verified three risks. This experiment **fixed them in shipped code** rather
than leaving them as caveats in a report. Each risk maps to exactly one defect,
and each defect maps to one module.

## The three risks, and what each became

### R1 — Frozen thresholds do not transfer across days

**Measured (E13):** Monday's p95 threshold applied to Friday gives ROC-AUC
0.9998 with **precision 0.037** and F1 0.071 — 27 hosts flagged, 1 real
attacker. Recall 1.0, so the attacker is never missed, but the queue is
garbage.

**Diagnosed:** the score *scale* drifts between days; the score *ranking* does
not. A threshold is an absolute value (scale-dependent) where the information
lives in the order (scale-free).

**Fixed by `detection/thresholds.py`:**

```python
topk_mask(scores, k)          # cut the top k — transfers by construction
class RollingPercentile:      # causal adaptive threshold
    update(scores)            # feed each window
    threshold()               # percentile over recent history only
```

and wired into `detection/alert_pipeline.py:167` as
`score_window(..., top_k=N)`. Verified live: 7,374 alerts, exactly 10 flagged;
the `threshold=None` default path is unchanged, so no existing caller breaks.

**Kept, because it is still true:** a raw threshold, if anyone passes one,
still cannot transfer. The fix is to stop using them, not to trust them.

### R2 — Small slices produce confident nonsense

**Measured (E13):** the 443 slice has 5 attacker edges. Its AUC of 0.8935 has
a 95% CI of **0.708 – 1.000**; the pooled ALL-edges number of 0.9946 (29
positives) has CI 0.976 – 1.000.

**Fixed by `detection/eval_utils.py`:**

```python
auc_ci(auc, n_pos, n_neg)         # Hanley-McNeil 95% CI, no bootstrap cost
slice_verdict(n_pos, floor=30)    # "DIAGNOSTIC-ONLY: 5 positives < 30"
```

Every eval script in this archive now prints the CI and the verdict alongside
the point estimate. A slice under 30 positives cannot be quoted as a headline.

### R3 — Transductive fusion cannot ship

**Measured (E13):** whole-day mean fusion scores 1.000; causal running-mean
scores 0.9997. The 0.0003 gap is the price of not seeing the future.

**Fixed by `detection/host_reputation.py`:**

```python
class HostReputation:
    update(scores60, scores300)   # history only, never future
    host(h) -> running mean
    edge(src, dst) -> fused reputation
```

Validated twice after shipping: Infiltration 0.760 → **0.908** (E20), and
slow-drip ×5 0.064 → **0.979** (E24).

## What we understood

**The general lesson, which is larger than the three fixes.** Every bad number
in this archive — E07's 0.976, A3's 0.173, E11's 0.21, E13's own 0.89 — came
from the same mistake: measuring on a population that is not the population
the claim is about. The three modules here are the structural guard against it:
a CI forces you to state how much you know, a slice verdict forces you to
admit how little, and a rank cut forces you to stop depending on a scale that
moves.

This is also why they are in `detection/` and not here. They are not
experiments; they are the defaults that stop the archive's mistakes from
reaching production.

## Files

- `../../detection/thresholds.py` — top-k + rolling percentile
- `../../detection/eval_utils.py` — AUC CI + slice verdict
- `../../detection/host_reputation.py` — causal reputation tracker
- `../../detection/alert_pipeline.py` — the `top_k` wiring

Verified after shipping: production pipeline smoke test (7,374 alerts, top-5
flagging), all three modules unit-tested.
