# E62 — Resumable re-run, grid extended to {2…640}

**Verdict: CVE-2014-0160 CONFIRMED (+0.1079, nothing pinned). CVE-2012-2122 still
truncated — unresolved.** · 2026-10-01

## Why this experiment exists

E61 retracted E60's CVE-2012-2122 result (+0.0954 → +0.0001 on a wider grid) and
then **lost its CVE-2014-0160 half** when the opencode server restarted mid-run —
its results file was written only at the end, so 64 minutes of work left no
artifact. (The machine did not reboot; uptime was 27 hours.)

Two things were fixed. **Restart-proofing came first**, before the long run:

1. **Results are checkpointed after every single (family, arm, seed) cell**, via
   atomic `os.replace` on a temp file so a kill mid-write cannot corrupt the
   checkpoint. A restart resumes from the last completed cell. Verified with
   `--smoke` before the real run: 4 cells written, a second invocation reported
   *"4 cell(s) already done, 0 to run"* and reproduced identical numbers, exit 0.
   **This was then tested for real** — the server restarted again mid-run and the
   checkpoint preserved completed cells instead of losing everything.
2. **The grid extends past E61's own edge in both directions:** {2, 5, 10, 20, 40,
   80, 160, 320, 640}. E61 left both arms pinned at 320 on one family and left
   the other wanting *fewer* epochs for seq-AE (5) and *more* for count-AE (320).
   A grid bracketing neither is not a measurement.

A pick landing on 2 or 640 sets `truncated_top`/`truncated_bottom` and prints
`TOP-EDGE-TRUNCATED`. The edge-of-grid trap has fired three times; the fourth
occurrence is now self-reporting rather than silent.

## Result 1 — CVE-2014-0160: confirmed, and clean

4 seeds, W=1024 windows, K=3. **Every cell is interior to the grid.**

| Arm | Epochs picked | AUC (max) | AUC (mean) | det@10%FPR |
|---|---|---|---|---|
| **seq-AE** | 5, 5, 5, 5 | **0.6714 ± 0.0073** | 0.7036 ± 0.0109 | 0.273 |
| count-AE | 320, 160, 80, 160 | 0.5635 ± 0.0298 | 0.5647 ± 0.0240 | 0.285 |
| **Δ** | | **+0.1079**, pooled SD 0.0217, **z = +4.97** | +0.1390 | |

**No cell pinned to any edge, top or bottom.** The first fully-trusted LID-DS
result in this project.

### The gap held while both arms improved

| | seq-AE | count-AE | Δ |
|---|---|---|---|
| E60 — both arms pinned | 0.6419 | 0.5269 | +0.1150 |
| **E62 — nothing pinned** | **0.6714** | **0.5635** | **+0.1079** |

E60's count-AE was **starved** at 80 epochs; given 80–320 it improves 0.5269 →
0.5635. The seq-AE improves 0.6419 → 0.6714. **Δ essentially unchanged.**

So E60's heartbleed number was **right by accident** — the right magnitude from a
configuration that could not justify it. It is now right for the right reason.
That is the strongest form of this result available: the effect survived removing
the confound, and the confound had been *inflating both arms unequally*.

### A narrower claim, stated deliberately

**det@10%FPR is a tie: seq-AE 0.273, count-AE 0.285.**

The seq-AE **ranks** attacks better (AUC 0.671 vs 0.564, z = +4.97) but at a 10%
false-positive threshold the count-AE catches the same fraction. The claim this
supports is *"the seq-AE ranks anomalous traces better"*, **not** *"the seq-AE
detects more of them."* Those are different claims and only the first is measured
here.

## Result 2 — CVE-2012-2122: still truncated, reported as unresolved

| Seed | Epoch picked | AUC (max) | Edge? |
|---|---|---|---|
| 0 | 320 | 0.9957 | interior |
| 1 | **640** | 0.9986 | **TOP EDGE** |
| 2, 3 | *pending* | | climbing |

**This family does not converge at any budget tried.** At 80 it was underfit (the
E61 retraction); at 320 both arms pinned; at 640 seed 1 *still* pins. The seq-AE
keeps improving and has not plateaued.

**Consequence, stated plainly:** the memcached numbers are a **lower bound on both
arms**, not a result, and this family is **not evidence in either direction** until
it plateaus. Extending the grid indefinitely is not a fix — the honest options are
to keep going until the curve flattens, or to report the family as unconverged and
drop it from the comparison.

## What we understood

**There is no single defensible epoch budget across families.** Three convergence
points, all different, measured rather than suspected:

| | seq-AE | count-AE |
|---|---|---|
| heartbleed | **5** | 80–320 |
| memcached | 320–640+ | 320+ |

Heartbleed's seq-AE saturates after **five** epochs; memcached's needs **more than
640**. A paper quoting one grid is quoting whichever family flatters it. This is
now a measured property of the two corpora, not a worry.

**The count vector is the slower-converging arm everywhere.** It needed 80–320
epochs on heartbleed while the seq-AE needed 5 — roughly 20–60× more budget to
reach a *worse* optimum. That asymmetry is a property of the representation, not
of the grid, and it is the same finding E01 reported from the other direction.

## Where the host pillar actually stands

| Claim | Status |
|---|---|
| **E01 +0.058 on ADFA-LD** | **stands** — pick was interior to its grid |
| **E62 CVE-2014-0160 +0.1079** | **stands** — nothing pinned, confound removed |
| E60 CVE-2012-2122 +0.0954 | retracted (E61, truncated grid) |
| CVE-2012-2122 E62 | **unresolved** — unconverged, lower bound only |
| E58 absolutes / E59 learning curve | retracted (length confound) |

**The representation finding now has two independent supports:** ADFA-LD (E01)
and LID-DS CVE-2014-0160 (E62) — two corpora, two attack families, and in the
LID-DS case with the length shortcut removed by construction. The count-AE sits
at 0.5635 against a 0.50 floor.

## Limitations

- **det@10%FPR is a tie on heartbleed** — see above. Ranking, not detection rate.
- **W=1024 windowing, not whole traces** — absolutes are not comparable to E01's
  ADFA numbers or E58's. Short traces are dropped, which selects on length; 45 of
  120 heartbleed attack traces were dropped as too short, so the population is not
  the whole-trace population.
- **K=3 evenly-spaced windows per trace** — a sparse exploit confined to a narrow
  span could be missed.
- **Caps of 500 train / 600 test-benign windows**, applied identically to both
  arms. Every attack window kept.
- One attack family per CVE; no within-family breakdown.
- 4 seeds.

## Files

- `exp_e62_rerun.py` / `exp_e62_rerun.json` (checkpoint, resumes automatically)
- Supersedes both families in [E60](../E60_lidds_lengthblind/) and the
  CVE-2012-2122 half of [E61](../E61_lidds_grid_ext/)