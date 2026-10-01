# E46 — Pairing guards: making the project's dominant error mode impossible to repeat

**Verdict: PASS (24 self-tests + 8 real-bug regressions)** · 2026-09-29

## Aim

Six experiments in this archive produced a wrong number for the same reason:
**a model was evaluated against something it was not trained with.**

| Exp | The mistake | What it cost |
|---|---|---|
| E11 | split the frame by port *before* graphing | graphs were fragments; the attacker's degree signal did not exist |
| E16 | keyed each day-file separately, then concatenated | window 5 of Monday aliased window 5 of Tuesday |
| E42 | scored the base checkpoint with the replay-mix scaler | every "base" column handicapped; improvement inflated |
| E43 | ranked within 5000-row chunks, not 60s windows | Botnet `repfuse` read 0.789 vs the true 0.667 |
| E44 | paired the clean-data checkpoint with an original-testbed day | run 1's "control" was the cross-testbed gap |
| E07 / A3 | wrong population or wrong edge set | numbers that did not mean what the text said |

Every one was caught by the same accident: a number came out that disagreed
with a number already known. That is a luck-based defence. E21 caught two of
them only because it happened to reproduce E12's control.

This experiment builds the explicit version.

## What was done

Two files, both shipped in `detection/`:

- **`detection/eval_guards.py`** — the guards
- **`detection/eval_guards_selftest.py`** — 24 unit tests
- **`exp_e46_guard_regression.py`** (here) — 8 tests that reintroduce each
  *real* bug and assert the guard refuses it

### The four checks

| Guard | Catches | Behaviour |
|---|---|---|
| `require_scaler_match` | E42, and any refit-scaler mixup | **raises** |
| `require_window_groups` | E43, E16 | **raises** |
| `require_dataset` | E44, cross-testbed presented as in-domain | **warns** (see below) |
| `check_anchor` | any control that moves for no stated reason | **raises** |

Every anchor value was verified against the archive's own result JSON, not
from memory: 0.8714 in `E12_slowdrip/exp_e12_slowdrip.json`, 0.9483 in
`E21_band/exp_e21_band.json`, 0.7768 in `E23_host_ae_hmm/ablation_host.json`,
0.9789 in `E24_dilate_reputation/exp_e24_results.json`, plus the E44 control
that E12 also pins at 0.8714.

`require_dataset` deliberately **warns rather than raises**: E42 and E43 exist
precisely to score a checkpoint on a second testbed, and that is legitimate
work. The guard labels the result so it is quoted correctly; it does not stop
the run. Everything else raises.

## Results — the guards fire on the actual bugs

```
PASS  E42 base scored with replay-mix scaler
        -> scaler does not match the checkpoint (max |dlo| = 0, max |dhi| = 1).
           The scaler was refit on different data.
PASS  E42 base scored with its own scaler
PASS  E43 ranks within row-count chunks
        -> all 10 groups hold exactly 5000 rows. Fixed-size groups are a
           row-count chunk, not a time window.
PASS  E43 ranks within real time windows
        -> 180 groups, 64-1194 rows each
PASS  E44 clean ckpt on original-testbed day
        -> WARNED: trained on 'CICIDS2017_improved/monday benign-only' but
           scored on 'original CIC-IDS2017'
PASS  E44 clean ckpt on improved-testbed day
        -> same-testbed pairing is silent
PASS  E16 per-day keying then concat aliases windows
        -> 2 days aliased 600/600 window ids into 10 groups (should be 20)
PASS  E16 aliased window groups are refused
        -> group ids are not non-decreasing -- they are not in time order

8/8 cases behaved as required
```

## The guards were then wired into the live experiments, and all three reproduced

A guard that stops valid runs is worse than no guard, so each script was
re-run with the checks active and the published numbers compared.

| Script | Guard added | Reproduced? |
|---|---|---|
| [E44](../E44_residual_evasion/) | `require_scaler_match`, `require_window_groups`, `check_anchor` | **yes** — control 0.8714 hits the E12 anchor exactly; R1 0.9536 vs 0.9689 control; R2 ×10 → 0.0976; combined → 0.5009 |
| [E43](../E43_fusion_rule/) | `require_window_groups` on the rank groups | **yes** — all 5 families identical to the published table, including Botnet `repfuse` 0.723 and WebAttacks OPT3 0.957 |
| [E42](../E42_replay_all_families/) | `require_scaler_match` on every checkpoint load, `require_dataset` on both testbeds | **yes — all 7 families bit-identical** (Patator 0.9168831813, DoS 0.6380796751, Web 0.5191439631, PortScan 0.4084708480) |

E42's run also demonstrates the intended split behaviour: the scaler guard
passed silently on all four seeds (correct pairing), while the dataset guard
**warned once and continued** on the deliberate clean→original transfer — which
is exactly the E42 design, now labelled in the output instead of implied.

**E43's unresolved 0.723-vs-0.681 discrepancy did not reproduce as an error.**
The guards pass on E43 as written and the number is stable across two full
runs, so whatever differs from E21 is a difference in *method* between the two
scripts, not a pairing mistake in E43. That is a smaller, more tractable
question than the one the E43 README currently records, and it is worth
labelling as such rather than leaving it as a suspected bug.

## What we understood

**The discriminating signal is occupancy, not structure.** My first window
guard checked length, monotonicity and a group-count heuristic — and it did
*not* catch E43, because `np.arange(n) // 5000` satisfies all three. The check
that works is that real 60s windows over real traffic are **bursty** (64–1194
rows in the regression fixture) while a fixed-row chunk is exactly uniform.
Structural properties cannot distinguish the two; occupancy can.

**E16's mechanism was the opposite of what the archive assumed.** The summary
said `_window_key` is frame-relative, so concatenating days collides. Tested,
that is backwards: **concat-then-key is safe** (the global `ts.min()` anchors
both days to distinct ids — 0…9 and 1440…1449). The dangerous order is
**key-each-day-then-concatenate**, which restarts each day at 0 and merges
window 5 of Monday with window 5 of Tuesday. Same conclusion, opposite cause,
and only one of the two is the thing to avoid.

**"Same dataset" is not a substring test.** The first version of the dataset
guard compared token overlap and treated `CICIDS2017_improved` and
`original CIC-IDS2017` as *the same testbed*, because they share a corpus
name. That is precisely the distinction this project is built on, and the
guard would have gone silent on exactly the cross-testbed case it exists for.
Identity now requires the same corpus **and** the same variant. A recognised
corpus with no explicit variant token is the raw capture, so
`GeneratedLabelledFlows/TrafficLabelling` — how this repo spells the original
extraction — correctly matches `original CIC-IDS2017`.

### The gap the guards cannot close

`provenance_report()` exists because a guard that quietly does nothing is
worse than no guard. **6 of the 9 checkpoints in `detection/` carry no
`train` provenance field**, so `require_dataset` is silent on all of them —
including `gnn_autoencoder_v1_logscale_v2.pt`, which is exactly the
checkpoint E44 paired against the wrong day and the one E12's control anchor
is measured on. `require_scaler_match` still holds for those (the scaler is
inside the file), so the E44 mistake is caught by the binding even where the
provenance check is inert. **Back-filling provenance on the legacy checkpoints
is the outstanding follow-up**, and the self-test reports the count so it
cannot be forgotten.

## Files

- `exp_e46_guard_regression.py` — the 8 real-bug regressions
- `exp_e46_guard_regression.json` — per-case outcomes
- `../../detection/eval_guards.py` — the guards
- `../../detection/eval_guards_selftest.py` — 24 unit tests

## Run it

```
python detection/eval_guards_selftest.py
python experiments/E46_guard_regression/exp_e46_guard_regression.py
```
