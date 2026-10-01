# E38 — Feature set v2 (19 host dims) + the latent control (RC-30)

**Verdict: PASS** · 2026-08-21 / 2026-08-25 · commits `f222f44`, `115ff25`, `ca25e89`, `f9a5239`

## Aim

v1 gave each host 8 features: out-degree, in-degree, flow counts, byte totals,
unique ports, mean duration. Those are *magnitudes*, and CLAUDE.md's comment on
them was already the hypothesis — "many peers, many flows, many ports"
describes both a scanner and a busy file server, so magnitudes alone may not
separate them.

v2 appends 11 **shape** features: ratios, entropies, fractions. The aim was to
test whether the relational claim strengthens when the node representation
carries shape as well as scale.

The experiment also had a control obligation. Raising the bottleneck from 8 to
19 to match the wider input would confound "more features" with "more capacity",
so a `latent=19` arm was run to separate them.

## What was done

`detection/eval_feature_set_v2.py --seeds 0 1 2 3 --epochs 60`, full files. Arms:
v1 8-dim, v2 19-dim, and v2 with `latent=19` (capacity control). Indices 0–7 are
identical across v1 and v2 by construction, so old checkpoints and SHAP
mappings stay valid.

## Results (seed 0, host-window AUC)

| Family | v1 | **v2** | v2, latent=19 |
|---|---|---|---|
| PortScan | 0.9067 | **0.9998** | — |
| DDoS | 0.9785 | **0.9998** | — |
| Botnet | 0.9328 | **0.9983** | — |
| Infiltration | 0.9761 | **0.9998** | — |
| Patator | 0.9926 | **1.0000** | — |
| DoS | 0.9907 | **0.9998** | — |

4-seed band, v2 fused: **0.9997 ± 0.0001** (reproduced as 0.9997 ± 0.0001 on
the fixed stack).

Latent control: `latent=19` ≈ identical (0.9996) to the v2 default.

## What we understood

**The gain is features, not capacity.** Botnet is the diagnostic: 0.9328 → 0.9983,
a +6.6 point move, and the `latent=19` control shows the same result without
extra width. So the 11 shape features carry the signal, and the bottleneck
contributed nothing. This matters because CLAUDE.md gotcha #15 records that
*raising* `latent` makes the autoencoder **worse** — the model has no bottleneck
at all by default, which is a known weakness, and the temptation to fix it by
widening is exactly the wrong move. Confirmed here: widening did not help, and
the fix was on the input side.

**Why shape features work on Botnet specifically.** v1's 8 features are
dominated by scale, and a botnet's infected host has modest scale — it is not
scanning, it is beaconing to a few C2 hosts. What distinguishes it is
*regularity*: `duration_std` (beacon periodicity), `dst_port_entropy` (a few
repeating ports, not a spread), `bytes_ratio` (small uploads, large downloads).
Entropy and ratio features see regularity; magnitude features cannot.

**The engineering work around it, which is the part that bit.** Three fixes
were needed to make v2 usable, and each is a trap for the next person:

1. `train()` crashed on v2 because it inferred `in_dim` from the first graph
   before the checkpoint existed. Fixed by inferring from the graphs.
2. `score_window(feature_set="v2")` **crashed on the scaler** when a v1
   checkpoint was present — a confusing error far from its cause. Fixed with a
   dimension guard that refuses loudly and names the missing 19-dim checkpoint.
3. The guard exists precisely because gotcha #25 records that v2 was once
   built, documented as shipped, and then **lost** — no trace in git, stashes,
   or the working tree, and had to be rebuilt from scratch. A silent dimension
   mismatch is how that happens again.

**What survived.** `feature_set="v2"` is production; the frozen 19-name
catalogue is in `detection/training_features/README.md` and
`schemas/feature_vector.json` v3.0. The numbers themselves, like every other
in this archive, were later re-measured on clean data
([E21](../E21_band/)) and came back at 0.94–0.97 rather than 0.9997 — the
architecture claim held, the dataset was flattering it.

## Files

- `feature_set_v2_results.json` — 4-seed v1/v2 comparison
- `feature_set_v2_latent19_control.json` — the capacity control
- `eval_v2_4seed.log`, `eval_v2_latent19.log` — run logs
- `exp_v2_eval.py` — the evaluator
- `exp_v2b_temporal_aug.py`, `exp_v2b_ensemble.py` — temporal-augmentation and ensemble arms
- `exp_v2b_{smoke,60s_smoke,full60,full60b,full60_4seed,ensemble}.json` — the arm ladder
- `exp_v2_smoke.json`, `overnight_v2_4seed_60ep.log` — smoke + overnight band
