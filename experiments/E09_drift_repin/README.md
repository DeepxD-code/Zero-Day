# E09 — Threshold re-pinning under synthetic drift

**Verdict: NEGATIVE** · 2026-09-26 · commit `451a7b4`

## Aim

E03 killed the distributional drift alarm. This tested the *other* drift
response: the one thing we know changes when the environment drifts is the
**score distribution**, so the threshold calibrated on clean data goes stale.
M6-style adaptation says: re-pin the threshold on a drifted validation set,
then serve.

If re-pinning recovers F1 under injected noise, drift handling is a solved
operational problem. If it doesn't, the project has a real, disclosed
limitation: benign drift degrades the alert queue and no cheap fix exists.

## What was done

Host AE on ADFA-LD. Inject Gaussian noise into the benign **validation**
stream at σ ∈ {0.0, 0.05, 0.1, 0.2}, then:

- **frozen** — threshold from the clean run (0.1324)
- **repin** — threshold re-tuned on the *drifted* validation set, applied to
  the drifted test set

Metric: test F1 per σ per arm. Disclosed limitation: re-pinning uses labelled
drifted validation data, i.e. a supervised touch in an unsupervised system —
only acceptable if it actually works.

## Results

Clean threshold 0.1324.

| σ | F1 frozen | F1 repin | Re-pinned threshold |
|---|---|---|---|
| 0.0 | 0.4745 | 0.4745 | 0.1324 |
| 0.05 | 0.2549 | 0.2559 | 0.1645 |
| 0.1 | 0.2549 | 0.2521 | 0.1834 |
| 0.2 | 0.2549 | 0.2538 | 0.1877 |

## What we understood

**Re-pinning does nothing, and the frozen number is suspiciously flat.**
F1 drops 0.4745 → 0.2549 at σ=0.05 and then *stays* at 0.2549 through σ=0.2.
A detector that loses half its F1 on 5% noise and then degrades no further for
another 15% of noise is not experiencing gradual degradation — it is
**collapsing to a fixed degenerate operating point** (roughly "predict
everything" or "predict nothing", pick one; the flatness means the score
ordering is destroyed immediately and further noise is irrelevant).

The re-pinned thresholds do move correctly (0.1324 → 0.1877, tracking the
drifted distribution), which proves the mechanism works as designed. It just
cannot recover what was lost: re-pinning restores the *cut point*, but the
*ranking* underneath is already gone, and no threshold can repair a destroyed
ordering.

**This is the experiment that killed the "handle drift by re-pinning" idea and
pointed at the real answer.** Ranking is what we care about operationally —
which is exactly why E14 retired frozen thresholds in favour of rank cuts, and
why E24's causal reputation tracker beats a global threshold. If a score
distribution is not comparable across time, cut by *position within the current
population*, never by a remembered number.

## Files

- `exp_e9_drift_repin.py` — procedure
- `exp_e9_drift_repin.json` — per-σ F1 and thresholds
