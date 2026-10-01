# E39 — Revived M5a + the LODO negative (RC-25, gotcha #10)

**Verdict: PASS (revival) / NEGATIVE (LODO, kept with data)** · 2026-08-13 / 2026-08-25 · commits `2925813`, `f222f44`, `f319055`

## Aim — two aims, opposite outcomes

**Aim 1: build a per-flow model that actually helps fusion.** The original M5a
is a 76-dim AE that saturates and hurts fusion (gotcha #20). The hypothesis:
a per-flow model is *supposed* to contribute per-flow evidence the graph cannot
see (payload sizes, header costs, IAT structure) — the problem is the feature
set and the training, not the idea.

**Aim 2: use more benign data.** LODO (leave-one-day-out) trains on benign rows
from all five weekdays — 2.27M flows / 2,454 graphs versus Monday's 487. On
paper that is strictly better data. CLAUDE.md gotcha #10 said it made things
much worse, and this experiment was the confirmation run after the fix stack
landed.

## What was done

**Aim 1:** 87 dims = the pinned 76 flow features + 11 window-context dims
(`ws_flows`, `ws_dst`, `ws_ports`, …) computed per 60s window, log1p + MinMax.
RevivedAE 87→256→128→32→128→256→87, 60 epochs, seeded, CUDA-deterministic.
Then evaluated inside the E36 multi-window fusion protocol, per seed, as the
`rev_*` arms.

**Aim 2:** `lodo_train.py --seed 0 --epochs 60`, identical evaluation protocol.

## Results

**Aim 1 — the revival worked.**

| Config | Mean AUC (7 families, 4 seeds) |
|---|---|
| shipped M5a in fusion | 0.9482 ± 0.0032 |
| **revived 87-dim M5a in fusion** | **0.9996 ± 0.0001** |
| revived M5a alone (edge) | 0.8322 — the most consistent single configuration measured |

**Aim 2 — LODO confirmed the negative, hard.**

| Config | Monday-only | LODO (5 days) | Δ |
|---|---|---|---|
| fused | 0.9534 | 0.9197 | −0.034 |
| M5b alone | 0.9160 | 0.8089 | **−0.107** |
| M5a | 0.8417 | 0.8524 | +0.011 |

Every M5b family AUC dropped. 5× the training data made the graph model
substantially worse.

## What we understood

**On the revival: the feature set was the whole problem.** The 11 context dims
are the difference. `ws_dst` (distinct destinations *this host* hit in the
window) is the same fact as the graph's `out_degree` but attached to a *flow*
row rather than a node — so a per-flow model can finally see scan-shaped
evidence, which is why the revived model scores 0.8322 alone where the shipped
one was useless in fusion. This is the cleanest statement of why M5a exists at
all in a graph-based system.

**On LODO: "more benign data" is a category error when the benign data is
contaminated.** CIC-IDS2017's attack days contain attack traffic, and the
"benign" half of those days is not clean — an attacker's reconnaissance sits in
the rows labelled benign. Training on them teaches the model that scan-shaped
traffic is normal, which is exactly backwards. Note the asymmetry in the table:
M5a is *unaffected* (+0.011) because a per-flow model does not aggregate
across hosts and so cannot absorb the cross-flow pattern, while M5b loses
0.107 because the graph is precisely where that pattern lives.

**Both halves are still active decisions in the project.** The revival became
production M5a (shipped as `m5a_revived_ctx.pt`, then retrained on clean data
in [E18](../E18_retrain_m5a/)). LODO stays closed: Monday-only benign training
remains the protocol, and the *reason* is now understood rather than merely
observed. It also prefigures [E27](../E27_combined_monday/)'s failure — pooling
data across conditions fails for the same underlying reason.

**The `loop2_*` and `loop3_*` files** are the same family's later arms: 1800s
window (fails, −0.09), and auxiliary-edge counts K=8/12/16. K=8 gained +0.054
and K=16 +0.05 in one configuration but the production architecture rejected
sim-edges outright (−0.0193, per CHANGELOG 2026-08-13) — another instance of a
lever that does not transfer between architectures.

## Files

- `m5a_revival_v2_full4seed.json` — the 87-dim revival, 4 seeds
- `m5a_revival_full4seed.json`, `m5a_revival_smoke.json` — earlier stages
- `loop2_edge300.json` — 300s-window arm
- `loop3_{K8,K12,K12b,K16,1800s}_final.json` — auxiliary-edge and window-count arms
- `lodo_train.py` — the LODO procedure (the gotcha #10 reproduction)
- `exp_m5a_revival.py` — **note: this module is imported by PRODUCTION**
  (`alert_pipeline.py`, `shap_revived_ctx.py`, `train_m5a_revived.py`), so it
  lives at `experiments/exp_m5a_revival.py` rather than in this folder
