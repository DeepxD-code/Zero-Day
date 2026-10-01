# E27 — Combined-Monday training (cross-testbed, attempt 1)

**Verdict: NEGATIVE** · 2026-09-28 · commit `a114d24`

## Aim

[E17](../E17_retrain_improved/) left the project's worst remaining structural
problem: the retrained model is excellent on clean data and **collapses on
original data**, and the original-trained model collapses on clean data. Neither
checkpoint transfers. That is a serious deployment liability — a detector that
only works on the testbed it was trained on is a demo, not a product.

The most obvious fix, and the one everyone tries first: **train on both.**
Concatenate the two Monday files and learn a normality that covers both
testbeds. If that works, one checkpoint ships everywhere.

## What was done

`--extra-monday` flag added to the E17 trainer: concatenate original Monday
(529,918 flows) with improved Monday (371,624) → 901,542 flows → 974 v2 60s
graphs. Val-picked epoch, 400-epoch budget, seed 0. Then both cards against the
single combined checkpoint.

## Results

| Family | Improved-only → clean | **Combined → clean** | Original-only → orig | **Combined → orig** |
|---|---|---|---|---|
| Patator | 0.983 | **0.993** | 0.963 | 0.861 |
| DoS | 0.991 | 0.935 | 0.883 | 0.684 |
| WebAttacks | 0.931 | **0.731** | 0.930 | 0.773 |
| Infiltration | 0.760 | 0.799 | 0.577 | 0.610 |
| Botnet | 0.418 | 0.460 | 0.460 | 0.537 |
| PortScan | 0.971 | 0.963 | 0.871 | **0.578** |
| DDoS | 0.973 | 0.981 | 0.899 | 0.632 |

Val loss trace: best 0.000063 at **epoch 17**.

## What we understood

**Naive pooling learns neither testbed.** Two patterns, and both are
informative:

*On clean data* the combined model is fine on four families (Patator 0.993,
DDoS 0.981, Infiltration 0.799, PortScan 0.963) and badly degraded on two
(WebAttacks 0.931 → 0.731, DoS 0.991 → 0.935). *On original data* it improves
on the weak families (Infiltration 0.577 → 0.610, Botnet 0.460 → 0.537) while
collapsing the strong ones (PortScan 0.871 → 0.578, DDoS 0.899 → 0.632).

The mechanism is visible in the val trace: **best epoch 17.** With roughly half
the data from each of two distributions, the joint validation loss bottoms out
almost immediately — the model reaches a compromise that fits neither
distribution well. Learning a single "normality" from two testbeds' benign
traffic assumes they share one, and they demonstrably do not: the original
release's benign traffic is drawn from a narrower internal network (90 source
hosts, 3 external) than the corrected extraction's.

This is a real, general lesson rather than a quirk: **dataset pooling is not
domain adaptation.** It works when the domains are samples of one population.
Two collection pipelines with different benign populations are two domains, and
averaging them yields the mean of two incompatible notions of normal.

**This killed the naive approach and set the agenda for what worked.**
[E29](../E29_transfer/) then tried the two non-naive routes — dual-checkpoint
ensembling (also rejected) and replay-tuned fine-tuning (**accepted**, holding
both testbeds at 0.906/0.903) — with the right lesson carried in: adapt a
trained model to a new site, do not train one model for all sites.

The checkpoint `gnn_combined_s0.pt` is kept in this folder as the evidence of
the failure. It should never be served.

## Files

- `exp_e27_card_clean_on_combined.json` — clean card
- `exp_e27_card_original_on_combined.json` — original card
- `gnn_combined_s0.pt` — the rejected checkpoint (kept, not served)
