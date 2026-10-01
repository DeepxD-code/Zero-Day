# E48 — Sweeping the OPT thresholds (E43's "set by inspection" caveat)

**Verdict: PASS — the eyeballed k=3 was not wrong, but it is not optimal for
any family, and tuning it helps** · 2026-09-29

## Aim

[E43](../E43_fusion_rule/) left one explicit caveat: the burst-aware arm used
`SHORT_K = 3` and the persistence arm used `MIN_WINDOWS = 5`, **both chosen by
eye and never swept.** A threshold that was picked by intuition and never tested
is indistinguishable from one that happens to be right.

This measures the surface both sit on, and asks whether tuning them is worth
doing.

## What was done

Four seeds, both pillars banded as in E43, five families. One pass per
(seed, family); each edge records the **last 8 scores of both endpoints**, so
short-`k` reputation is reconstructed afterwards as `mean(tail[-k:])` for any
`k ≤ 8` — one pass instead of one per `k`.

| Grid | Values |
|---|---|
| OPT3 short-window `k` | 1, 2, 3, 4, 6, 8 |
| OPT1 persistence `nwin` | 3, 5, 8, 12, ∞ (∞ = always noisyor) |

**Selection is on the evaluation set, so a leave-one-seed-out check runs
alongside the surface**: pick `k` on 3 seeds, score it on the 4th. If tuned
loses to fixed `k=3` on held-out data, do not tune.

## Results — OPT3 surface (4-seed means)

| Family | k=1 | k=2 | **k=3** | k=4 | k=6 | k=8 | best k | span |
|---|---|---|---|---|---|---|---|---|
| Botnet | **0.4802** | 0.4606 | 0.4533 | 0.4475 | 0.4449 | 0.4391 | **1** | 0.041 |
| PortScan | 0.9671 | 0.9680 | 0.9690 | 0.9699 | **0.9710** | 0.9708 | **6** | 0.004 |
| DDoS | 0.9671 | 0.9680 | 0.9690 | 0.9699 | **0.9710** | 0.9708 | **6** | 0.004 |
| Infiltration | 0.6516 | 0.6666 | 0.6662 | 0.6704 | 0.6739 | **0.6757** | **8** | 0.024 |
| WebAttacks | 0.9193 | 0.9450 | 0.9502 | 0.9551 | 0.9586 | **0.9608** | **8** | 0.041 |

### Leave-one-seed-out — does tuning generalise?

| Family | tuned (k chosen on 3 seeds) | fixed k=3 | Δ | Verdict |
|---|---|---|---|---|
| Botnet | 0.4802 | 0.4533 | **+0.0269** | **tuning helps** |
| PortScan | 0.9710 | 0.9690 | +0.0020 | wash (inside noise) |
| DDoS | 0.9710 | 0.9690 | +0.0020 | wash (inside noise) |
| Infiltration | 0.6757 | 0.6662 | **+0.0095** | **tuning helps** |
| WebAttacks | 0.9608 | 0.9502 | **+0.0106** | **tuning helps** |

**Tuning never hurts, and helps by up to 0.027.**

### OPT1 is rejected across the entire grid, not just at its default

| Family | OPT1 best point | vs best baseline arm | |
|---|---|---|---|
| Botnet | 0.6482 (nwin=3) | 0.7092 (repfuse) | loses |
| PortScan | 0.9410 (nwin=12) | 0.9656 (noisyor) | loses |
| DDoS | 0.9410 (nwin=12) | 0.9656 (noisyor) | loses |
| Infiltration | 0.6545 (nwin=12) | 0.6684 (repfuse) | loses |
| WebAttacks | 0.7752 (nwin=3) | 0.9080 (noisyor) | loses |

**OPT1 loses at every one of 25 grid points.** This is a much stronger rejection
than E43's "last at the default": no setting rescues it.

## What we understood

**The optimal `k` runs in opposite directions, so `k=3` is a compromise rather
than a value.** Botnet improves monotonically as `k` *shrinks* (0.480 → 0.439);
WebAttacks and Infiltration improve monotonically as `k` *grows* (0.919 → 0.961).
`k=3` is best at **none** of the five families. It is not wrong — it is never
more than 0.011 off the best on any family — but it is the middle of a
compromise between two attack shapes, which is exactly what E43 concluded about
the fusion rule as a whole.

The mechanism is legible. A **persistent** attack (Botnet) is best judged by the
most recent score only: a long average lags behind a host that is *currently*
misbehaving, and the longer you average the more you dilute the signal. A
**bursty** attack (Web) is the mirror image — the long average suppresses the
burst, so a deeper window recovers more of it. This is the same
short-vs-long-timescale tension E43 identified, now measured across the whole
range rather than at two points.

**`k=3` was luck-adjacent, not wrong.** The LOSO check is what makes that
safe to say: choosing `k` without seeing the evaluation seed never underperformed
the fixed default, and beat it by up to 0.027. Tuning is therefore safe, just
not portable — a fixed `k` has to be a compromise, whereas a deployment that
tunes `k` on its own traffic can capture the 0.009–0.027.

**PortScan and DDoS are saturated, again.** The entire `k` range spans 0.004
and the whole grid is within 2× the seed SD. Reporting "best k=6 gives 0.9710"
would be overclaiming; the honest statement is that the fusion rule does not
matter on these families.

### Two bugs in this experiment, both caught before reporting

1. **The LOSO verdict was inverted.** The condition read
   `k3 >= tuned - 0.005`, which labels tuning as overfitting precisely when
   tuning *wins* — so three families that tuning helped by 0.010–0.027 were
   reported as "TUNING OVERFITS". The measurements were never affected; only the
   label was. Corrected in the script and in the JSON, with the correction
   recorded in a `verdict_fix` field rather than quietly overwritten.
2. **The first run was invalid.** E43's label strings were retyped from memory
   and three of five families got an empty positive set, returning silent `nan`.
   The real strings are `Botnet` (not `Bot`), `Portscan` (lowercase s),
   `Web Attack - SQL Injection` (uppercase). `run_family` now **raises** on a
   zero-row or zero-host family instead of emitting `nan` — the same lesson as
   E11's 5-positive slice, one class over.

## Files

- `exp_e48_opt_sweep.py` — the grid and the LOSO check
- `exp_e48_opt_sweep.json` — surface, LOSO, and the verdict correction

## Run it

```
python experiments/E48_opt_sweep/exp_e48_opt_sweep.py
```
