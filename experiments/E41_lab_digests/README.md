# E41 — Lab digests, training logs, shared harness

**Verdict: CONTROL** · 2026-07 → 2026-08 · assorted commits

## What this folder is

Not an experiment. This is the lab notebook layer — the running documents and
raw console output that the RC-numbered experiments produced but that are not
themselves single experiments. It is kept numbered and documented for exactly
that reason: it is where you look to see *how the work was actually run*, not
*what it concluded*.

## Files and what they are

### Digests (the human-written layer)

- **`report_cards.md` (47 KB)** — the RC-01 … RC-32 experiment cards. One card
  per experiment with hypothesis, protocol, numbers and verdict. This is the
  historical index that predates the numbered folders; it remains the
  authoritative record of the pre-branch experiments, and the RC numbers it
  assigns are cited in CHANGELOG.md and in the READMEs throughout this archive
  (E33 = RC-31, E34 = RC-29/RC-32, E36 = RC-26, E37 = RC-27/28, E38 = RC-30,
  E40 = RC-20).
- **`OVERNIGHT_DIGEST.md`** — the session summary for the 2026-08-13 PIKACHU
  breakthrough, including the LogScaler result and the twelve-experiment list.

### Training logs (raw console output)

- `train_v1_logscale.log`, `train_60s_logscale.log`, `train_v2_checkpoint.log`
  (+ `.err.log`) — the three original checkpoint trainings. Kept because
  CLAUDE.md gotcha #24 makes device and build part of every number: these logs
  are the only record of what hardware produced the shipped checkpoints.

### Housekeeping

- `harness_restore.log` — record of restoring the red-team harness outputs
  after the week-4 clean slate quarantined stale implementations. Relevant to
  CLAUDE.md's RC-25-DUPLICATE-NOTE about output ownership.

### Dormant / stale

- **`seed_protocol.py`** — the shared 4-seed deterministic harness. **This file
  is currently broken and nothing imports it.** It does
  `from gnn_model import EdgeScaler, ScoreCalibrator, train_edge_model`, and
  the current `detection/gnn_model.py` no longer defines `EdgeScaler` — the
  edge-scaling path was folded into the host model when the edge/graph split
  was consolidated. The file was already unimportable before this archive was
  organised (verified against commit `ba286ca`); it is not collateral damage
  from the move.

  It is kept rather than deleted because it records the seeding discipline the
  project relies on everywhere else — `set_seed` with
  `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `cuda.manual_seed_all`,
  `cudnn.deterministic`, and the 4-seed band convention — which is now carried
  by `detection/gnn_model.py:set_seed()` and documented in CLAUDE.md gotcha #11
  and #24. Anyone reviving it should port the seeding logic forward, not the
  `EdgeScaler` import.

## Why these are here and not at the `experiments/` root

Two files *are* at the root, deliberately, and they are not evidence:

- **`exp_m5a_revival.py`** — still at the `experiments/` root, because it is
  imported by **production** code (`detection/alert_pipeline.py`,
  `detection/shap_revived_ctx.py`, `detection/train_m5a_revived.py`). It is a
  shared module, not an experiment script, and moving it would mean touching
  four production import paths for no benefit. It resolves its one
  experiment-local dependency (`exp_v2b_temporal_aug`, now in
  [E38](../E38_feature_set_v2/)) through an explicit `sys.path` insert.

Everything else that was loose in `experiments/` is now inside a numbered
folder. If you are wondering "where did experiment X go", the archive README's
table of contents answers it in one lookup.

## What we understood

Nothing here changed a decision. Its value is entirely in reproducibility and
in provenance: when an examiner asks "how do you know this number", the answer
is a numbered experiment, a script, a JSON, and a commit — and for the older
results, the raw log that shows the run actually happened on hardware rather
than being transcribed from a claim.
