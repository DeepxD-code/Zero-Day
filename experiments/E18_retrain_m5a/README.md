# E18 — Retrain the revived M5a flow model on clean Monday

**Verdict: PASS** · 2026-09-27 · commit `3760ffa`

## Aim

E17 fixed the graph pillar. The flow pillar (M5a-R, 87-dim context AE) had the
same problem for a sharper reason: **its checkpoint could not even run on clean
data.** `m5a_revived_ctx.pt` was missing 20 of its 76 canonical columns on the
fixed extractor's naming (`Tot Fwd Pkts`, `Min Packet Length`,
`Fwd Header Length.1`, …). The production code's instinct was right — it
raises `ValueError` naming the missing columns rather than silently scoring
garbage — but that meant the flow pillar was unusable on clean data.

## What was done

Same recipe as `detection/train_m5a_revived.py` (RevivedAE, 60 epochs, seed 0,
LR 1e-3), with one necessary change: **pin 82 canonical columns instead of 76.**

`pin_canonical()` in `experiments/exp_m5a_revival.py` hard-asserts
`EXPECTED_FEATURES == 76` and trips on the fixed extractor's 82 numeric
columns. Rather than loosen that assertion (it protects the original
checkpoint's contract), this script pins locally and lets `RevivedAE` size
itself to the resulting matrix: **82 flow + 11 context = 93 dims**.

Training: 371,624 × 93, loss 0.0422 → 0.00009 over 60 epochs.

## Results

- Checkpoint: `detection/m5a_revived_improved.pt` (93-dim, seed 0)
- Fixed data compatibility: **0 missing columns** (was 20/76)
- 4-seed band for the WebAttacks family: **0.8953 ± 0.0257**
  (0.8783 / 0.9065 / 0.8650 / 0.9306)

## What we understood

**Two findings, one expected and one that changed the fusion story.**

1. *Expected:* the 93-dim model runs on clean data where the 87-dim one
   could not. The schema-mapper discipline (`detection/README.md`, gotcha #13)
   predicted exactly this — a new extractor names things differently, and
   pinned column lists are a contract that must be re-pinned per dataset.

2. *The important one:* the flow model's WebAttacks band (0.895 ± 0.026) is
   **tight where the graph model's was not** (±0.091 in E21, and it flipped to
   0.68 on seed 3). Seed 3 specifically is the graph model's *worst* case
   (0.68) and the flow model's *best* (0.93). The two pillars fail on
   different seeds, which is the textbook condition for fusion to help — and
   it is what made [E24](../E24_dilate_reputation/)'s fused Web band (0.867 ±
   0.057) beat both graph-only and flow-only.

**Why the flow model is stable where the graph model flips:** a port scan is
topological (degree spike) and disappears under timing dilution — E12. A web
attack is a payload/packet-size pattern, and packet sizes survive in the flow
features regardless of how the graph aggregates them. Different representation,
different failure mode. That is the whole argument for the two-pillar design,
now measured rather than asserted.

**Note on seeds:** only seed 0's checkpoint is kept. The band numbers are in
[E22](../E22_web_m5a/)'s JSON and the seed-1/2/3 checkpoints are in
[E21](../E21_band/) — E22 shows the flow model is seed-stable enough that
serving one is defensible, unlike the graph model.

## Files

- `exp_e18_retrain_m5a_improved.py` — the trainer (`--epochs`, `--seed`, `--out`)
- output: `detection/m5a_revived_improved.pt` (93-dim)
