# E61 — Extend E60's epoch grid (PARTIAL: CVE-2012-2122 done, CVE-2014-0160 lost)

**Verdict: RETRACTS E60's CVE-2012-2122 result. CVE-2014-0160 unresolved.**
· 2026-10-01

> **Status: partial.** The CVE-2012-2122 family completed. The CVE-2014-0160 family
> was killed on seed 0 when the **opencode server restarted mid-run** and the
> results file (written only at the end) never appeared. The machine did **not**
> reboot — uptime was 27 hours — so this is not a repeat of the E01 restarts.
> Recovered numbers live in `exp_e61_grid_ext.PARTIAL.json`.

## Why this experiment existed

E60's epoch picks, all eight cells, were pinned to a grid edge:

| Cell | Picks | Edge |
|---|---|---|
| CVE-2012-2122 seq-AE | 80, 80, 80, 80 | top of {10,20,40,80} |
| CVE-2012-2122 count-AE | 80, 80, 80, 20 | top on 3 of 4 |
| CVE-2014-0160 seq-AE | 10, 10, 10, 10 | **bottom** |
| CVE-2014-0160 count-AE | 80, 80, 80, 80 | top |

Standing rule, earned at E01 (epoch 40) and E48 (`k=3`): a parameter pinned to
the edge of a sweep has not been tested, it has been truncated. E60 was therefore
re-run on **{5, 10, 20, 40, 80, 160, 320}**. Everything else — W=1024 windows,
K=3, caps, 4 seeds, both arms — is byte-identical to E60.

## Result 1 — CVE-2012-2122: E60's gap was a grid artefact

| | seq-AE | count-AE | Δ | verdict |
|---|---|---|---|---|
| **E60**, grid {10…80} | 0.9731 ± 0.0117 | 0.8777 ± 0.0276 | **+0.0954** (z = +4.50) | separated |
| **E61**, grid {5…320} | 0.9927 ± 0.0015 | 0.9926 ± 0.0017 | **+0.0001** (z = +0.06) | **inside noise** |

**E60's +0.0954 is retracted.** With a budget long enough to matter, the count
vector catches up completely — and its detection rate at a 10% FPR goes from
0.867 to **1.000**, while the seq-AE's goes 0.992 → 0.996. Neither arm has an
advantage on this family at all.

This is the **third** time the edge-of-grid trap has fired in this project, and
the second time I introduced it myself after E01 documented it.

### Why it happened, stated plainly

E60 gave count-AE 80 epochs. The count vector is a small MLP over 31 features;
80 epochs is nowhere near convergence. It was not "worse at counting", it was
**undertrained**, and the gap I reported was the training budget showing through.

## Still not a ceiling

| Arm | Picks | Status |
|---|---|---|
| seq-AE | 80, 320, 320, 320 | **truncated at 320** |
| count-AE | 320, 320, 320, 320 | **truncated at 320** |

Six of eight picks sit on the top edge. **0.993 is a lower bound on both arms,
not a converged value.** And seed 0's seq-AE choosing 80 while the other three
chose 320 means that arm is not stable at this budget either — 0.9927 ± 0.0015
understates the seed-to-seed spread at a genuinely converged setting.

## Result 2 — CVE-2014-0160: lost, and still unresolved in both directions

Killed on seed 0. The two cells that did print:

| Arm | Pick | Edge? |
|---|---|---|
| seq-AE | **5** | bottom edge of {5…320} |
| count-AE | **320** | top edge |

So even on the wide grid this family wants **fewer** epochs for the seq-AE and
**more** for the count-AE — the opposite of CVE-2012-2122, where the count-AE
needed 320 to catch up. Two families pulling in opposite directions means there
is **no single defensible epoch budget**, and a paper quoting one grid is
quoting whichever family flatters it.

## Where this leaves the host pillar

| Claim | Status |
|---|---|
| E01 +0.058 on ADFA-LD | **stands** — pick was interior to the grid |
| E58 absolutes | retracted (length confound) |
| E59 learning curve | retracted (length confound, not re-measured) |
| E60 CVE-2012-2122 +0.0954 | **retracted here** (truncated grid) |
| E60 CVE-2014-0160 +0.1150 | **unresolved** — still edge-pinned in both directions |

The representation finding is now supported by **E01 alone**. The two LID-DS
families have both failed to confirm it under scrutiny, each for a different and
recorded reason. That is the honest state, and it is weaker than it was two hours
ago.

## What E62 has to do

1. Extend past 320 on CVE-2012-2122 — both arms are still climbing.
2. Grid CVE-2014-0160 in **both** directions: {2, 5, 10, 20, 40} for the seq-AE,
   {160, 320, 640} for the count-AE. They want opposite things.
3. Report the **converged** value, or state explicitly that no budget converges.
4. Make the script write results **incrementally**, so a server restart cannot
   destroy a multi-hour run again. This is the fix for what just happened.

## Files

- `exp_e61_grid_ext.py`
- `exp_e61_grid_ext.PARTIAL.json` — recovered CVE-2012-2122 results
- Supersedes the CVE-2012-2122 half of [E60](../E60_lidds_lengthblind/)