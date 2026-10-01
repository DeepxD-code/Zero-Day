# E47 — Back-filling checkpoint provenance (the E46 gap, closed)

**Verdict: PASS (9 of 9 checkable, up from 3 of 9)** · 2026-09-29

## Aim

[E46](../E46_guard_regression/) shipped the pairing guards and left one gap:
**6 of the 9 checkpoints in `detection/` carried no `train` provenance field**,
so `require_dataset` was silent on them — including
`gnn_autoencoder_v1_logscale_v2.pt`, which is exactly the checkpoint
[E44](../E44_residual_evasion/) paired against the wrong day. E44's mistake was
caught at the time only by the scaler binding, by luck of file layout.

This closes it, with one rule: **a provenance value is written only if evidence
supports it.** Anything else is marked UNKNOWN, which makes the guard *warn* on
use rather than silently pass.

## What was done

Three scripts, run in order:

| Script | Job |
|---|---|
| `exp_e47_provenance_audit.py` | For each checkpoint, gather the evidence for a value. Writes nothing. Flags what it cannot support. |
| `exp_e47_scaler_forensics.py` | Settle undocumented checkpoints **empirically**, from the scaler. |
| `exp_e47_backfill.py` | Write the values, with a `--dry-run` and a per-file evidence trail. |

### The forensic method

`NodeScaler.fit` sets `lo`/`hi` to the **per-feature min and max of the
training graphs**. Those are data fingerprints, not free parameters — so a
scaler records the corpus it was fitted on. The method: fit a reference scaler
on each candidate corpus, then measure which reference the checkpoint's stored
bounds actually match.

Judged on the **margin** between corpora, not on absolute error — the reference
is fitted on a bounded slice of Monday, so even the right corpus will not match
to 1e-6. What matters is which corpus is orders of magnitude closer.

## Results

| Checkpoint | Evidence | Verdict |
|---|---|---|
| `gnn_improved_s0.pt` | already correct; forensics confirm | clean Monday, margin **167×** |
| `m5a_revived_improved.pt` | already correct | clean Monday |
| `host_autoencoder_adfa.pt` | already correct | ADFA-LD |
| `gnn_improved_replay.pt` | forensics (err 0.0) + E29/E42 record | clean + original replay mix |
| `gnn_autoencoder_v1_logscale_v2.pt` | forensics, margin **14.2×** | **original Monday** |
| `gnn_autoencoder_v1_logscale.pt` | forensics, margin **12.0×** | **original Monday** |
| `m5a_revived_ctx.pt` | **trainer source**, `train_m5a_revived.py:30` | **original Monday** |
| `gnn_autoencoder_v1.pt` | none | **UNKNOWN** |
| `gnn_temporal_fused_v1.pt` | none | **UNKNOWN** |

**Forensics, all six M5b checkpoints:**

```
gnn_improved_s0.pt               -> clean_monday/v2    err=0.0019  margin=167.2
gnn_improved_replay.pt           -> clean_monday/v2    err=0.0     margin=3.2e8
gnn_autoencoder_v1_logscale_v2.pt-> original_monday/v2 err=0.0587  margin=14.2
gnn_autoencoder_v1_logscale.pt   -> original_monday/v1 err=0.0815  margin=12.0
gnn_autoencoder_v1.pt            -> AMBIGUOUS          err=0.644   margin=1.5
gnn_temporal_fused_v1.pt         -> AMBIGUOUS          err=0.644   margin=1.5
```

**`provenance_report()` before: 3 checkable, 6 silent. After: 9 checkable, 0
silent** (10 including the seed trained during this session).

## What we understood

**The scaler is evidence, and nobody had used it as such.** The three legacy
checkpoints whose training command was never written down are now identified
from the artifact itself. The one that matters most is
`gnn_autoencoder_v1_logscale_v2.pt` — the checkpoint E12's control anchor is
measured on, and the one E44 mispaired. It matches **original Monday at 14.2×
margin**, which retroactively confirms E12's pairing was correct and shows E44
run 1 used a model trained on a different corpus than the day it was scored on.
That was a real error, and it is now structurally impossible to repeat.

**The two UNKNOWNs are the same fact, and honesty beats a plausible guess.**
`gnn_autoencoder_v1.pt` and `gnn_temporal_fused_v1.pt` have a **byte-identical
scaler** (fingerprint `ad2aafe47c2d8a1c`) — so the identical 0.644 error is one
measurement, not two. CHANGELOG 2026-08-25 records the first as *"saved by
smoke"*, a smoke run rather than a documented Monday train, and its hi-vector
sits between the two corpora (margin 1.5×). Its corpus genuinely cannot be
called. Marking it UNKNOWN makes `require_dataset` warn on any use, which is
the correct behaviour: a warning is recoverable, a confident wrong value is
not.

**Rewriting a checkpoint had to be provably lossless.** Every file was verified
bit-identical afterwards — all model weights and both scaler vectors unchanged,
`train` and `provenance` the only added keys. A provenance backfill that
quietly perturbed a model would be worse than the gap it closed.

**The self-test now fails on regression.** `t22` asserts *no* checkpoint lacks
provenance, so a new checkpoint arriving without it is a test failure rather
than a neutral state. `t24` pins the specific E44 case: the mispairing must
warn, and the home testbed must not.

## Files

- `exp_e47_provenance_audit.py` / `.json` — evidence per checkpoint
- `exp_e47_scaler_forensics.py` / `.json` — the scaler-bound measurements
- `exp_e47_backfill.py` / `.json` — what was written, with per-file basis
- `../../detection/eval_guards_selftest.py` — `t22`, `t24`

## Run it

```
python experiments/E47_provenance_audit/exp_e47_scaler_forensics.py
python experiments/E47_provenance_audit/exp_e47_backfill.py --dry-run
python detection/eval_guards_selftest.py
```
