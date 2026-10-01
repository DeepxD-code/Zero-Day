# E33 — Non-relational baselines under identical conditions (RC-31)

**Verdict: CONTROL** · 2026-08-21 · commits `80675c5`, `dc6be7e`

## Aim

The single most common reviewer objection to a graph-NIDS paper is *"the
baselines were cited, not run"*. Every comparison in the literature places a
GNN against a non-relational model trained and scored by a different group, on
different splits, with different preprocessing. If the gap is an artefact of
protocol rather than architecture, the whole thesis is hollow.

This experiment closes that objection by training three non-relational
baselines on **exactly our features, exactly our splits, exactly our metric**.

## What was done

Same v2 host-window feature matrices the graph model consumes, same Monday
benign training, same 7 held-out families, same full files, same seeds:

- **PCA** — reconstruction error onto the principal subspace
- **Isolation Forest** — isolation-based, no density assumption
- **MLP-AE** — plain multilayer autoencoder, the non-graph equivalent of ours

Control: our `GraphAutoencoder` on the identical matrices.

## Results

| Model | Mean AUC (7 families, 4 seeds) |
|---|---|
| Isolation Forest | 0.9357 |
| PCA | 0.9417 |
| plain MLP-AE | **0.9517** |
| **ours (GraphAutoencoder)** | **0.9987 ± 0.0008** |

Per-family (seed 0, PortScan): PCA 0.952 with 29 attacker ranks spanning
1 → 12,045; Isolation Forest 0.8849 with best rank 7.

## What we understood

**The relational layer is worth +4.7 points, and the gain is concentrated
exactly where the thesis predicts.** Comparing the per-family deltas, the
largest gains are in the topology families — PortScan, DDoS, Botnet, DoS — and
the smallest in the ones where a single flow already looks anomalous
(Patator, WebAttacks). That is the mechanism, not a coincidence: a
"one host talked to 200 distinct peers in 60 seconds" fact is arithmetically
absent from a per-flow feature vector, so no per-flow model of any capacity can
recover it. That sentence is the entire justification for the graph half of
M5b, and this experiment is the measurement of it.

**The honest corollary, which the report must carry:** the 19-dim v2 features
alone are already strong — they carry plain models to ~0.95. Our claim is
therefore **"aggregation and relations"**, not "we invented better features".
Overclaiming here is the easiest way to lose an examiner.

**Isolation Forest at 0.9357 is the useful outlier.** It is the only baseline
with a genuinely different inductive bias, and it is the weakest. A defensible
"diverse model" claim would have needed it to be *complementary*; it is not,
it is just worse. This is the same finding as [E08](../E08_diverse_fusion/) —
diversity of algorithm is not diversity of assumption when the input
representation is shared.

**Why this is a CONTROL.** Nothing in the project changed because of it. It
exists to make the "we beat the baselines" claim falsifiable, and it is the
experiment that turns a literature comparison into a controlled one.

## Files

- `baselines_4seed.json` — per-family, per-seed AUCs and attacker ranks
- `eval_baselines_4seed.log`, `verify_baselines_4seed.log` — run + exact-match verification
- `summarize_baselines.py` — the summary aggregation
