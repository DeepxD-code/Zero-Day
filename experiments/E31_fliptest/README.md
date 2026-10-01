<!-- Renumbered from the A2-series on 2026-09-29 so every experiment uses one scheme. The original ID is preserved in the archive README's Historic ID column and in git history. -->

# E31 — Top-k attribution flip test (can camouflage change the explanation?)

**Verdict: NEGATIVE** · 2026-09-26

## Aim

Companion to E06. E06 asked whether mimicry attacks shift SHAP attribution.
A2 asks a cruder, SOC-relevant version: does the **top-k feature list** an
analyst actually reads change when the attack is camouflaged?

If the top-5 features are stable under mimicry, the explanation layer is
robust to the attacks we can synthesise. If they flip, an analyst reading
"top feature: setuid" on a camouflaged attack is being actively misled, and
the dashboard needs an uncertainty indicator on the explanation.

## What was done

Host AE (ADFA-LD, count features). Apply three mimicry probes to flagged
attacks, then measure how often each of the top-k contributing features
**flips** relative to the clean attack's ranking. Control: the same flip rate
under a random permutation, which is the chance rate.

## Results

Threshold 0.1324, 228 true positives.

| k | Top-k flip rate | Random (chance) flip rate | Ratio |
|---|---|---|---|
| 1 | 0.0658 | 0.0053 | 12.4× |
| 3 | 0.0789 | 0.0219 | 3.6× |
| 5 | 0.3509 | 0.0333 | 10.5× |
| 10 | 0.3246 | 0.0132 | 24.6× |

Top attributed dimensions: `extra_151`, `semtimedop`, `nr_265`, `setxattr`,
`shmdt`, `io_cancel`, `lsetxattr`, `getcpu`, `setuid`,
`sched_get_priority_max`.

## What we understood

**Attribution is measurably unstable — 3.6× to 24.6× the chance rate.** So
yes, camouflage can mislead the explanation. But the negative verdict rests on
a second observation: at k=1 the flip rate is only 6.6%, meaning **94% of the
time the single most-attributed feature survives the attack**. The headline
feature is stable; the tail is not.

The k=5/k=10 numbers (0.32–0.35) are large in absolute terms but they describe
the *5th through 10th* features, which is information an analyst rarely acts
on — SHAP explanations in the dashboard show the top 3–5, where flip rates are
0.066–0.079.

**Practical consequence, not a code change:** the explanation layer is
trustworthy for "why did this fire" and untrustworthy for "what is the 7th
reason". C's dashboard should show top-3 only and must not claim the tail is
meaningful. The instability is worth disclosing in the report as a known limit
of post-hoc attribution under adversarial input.

## Files

- `exp_a2_fliptest.py` — procedure
- `exp_a2_fliptest.json` — flip rates and top dimensions
