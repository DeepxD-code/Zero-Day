# E52 — Edge-level granularity: is the fixed symmetric mean the bottleneck?

**Verdict: NEGATIVE (valid). The edge aggregator is not the constraint; the node
representation is.** · 2026-09-30

## Aim

The per-flow gap is not a capacity problem — widths move thousandths. The user's
framing is right: the binding constraint is **granularity**.

`GraphAutoencoder.edge_scores` is a hand-fixed symmetric mean:

```
edge = (node_err[src] + node_err[dst]) / 2
```

which discards edge asymmetry for free. A flow whose client is anomalous and
server is not scores identically to one where both ends are equally anomalous.
No parameter tuning recovers a distinction that was never represented.

The test keeps the node autoencoder **exactly as trained** — no retraining, no
added capacity — and learns two ~150-param heads over the edge's own features:

```
phi(e) = [n_src, n_dst, |n_src - n_dst|, min, max,
          log1p(deg_src), log1p(deg_dst), mean]
```

`head_mean` predicts the mean edge error `phi[7]`; `head_asym` predicts the
asymmetry `phi[2]`. Both trained on benign edges only (Monday), val-picked,
4 seeds, scored with the same within-window-rank → pool metric as everywhere
else.

## The first attempt was INVALID, and how it was fixed

The initial run scored an edge by `head(phi)` directly. That is a category
error: a regressor trained on benign edges learns *what the value usually is
for this edge shape*, so its output measures **familiarity, not anomaly**. It
scored −0.001 to −0.023 across families and **−0.167 on WebAttacks** — the
expected signature of that bug, not evidence about granularity. That run is
retained below and explicitly not cited.

**Corrected scorer — the residual:**

```
score = | z(observed) - head(phi) |
```

i.e. "is this edge's error level unusual *for its shape*?" A second bug was also
fixed: `best_state` was computed by val-picking and then **never loaded**, so
the last epoch was shipping. Both defects are in the first version's history.

## Results (corrected arm, 4 seeds)

| Family | fixed mean | residual | Δ | residual + asym | Δ |
|---|---|---|---|---|---|
| Botnet | 0.442 ± 0.017 | 0.444 | **+0.002** | 0.439 | −0.003 |
| PortScan | 0.961 ± 0.002 | 0.822 | **−0.139** | 0.898 | −0.063 |
| DDoS | 0.961 ± 0.002 | 0.795 | **−0.166** | 0.900 | −0.061 |
| Infiltration | 0.633 | 0.511 (s0) | −0.117 | 0.545 (s0) | −0.084 |

(Botnet and PortScan/DDoS complete over 4 seeds; Infiltration stopped at seed 0
once the pattern was unambiguous and clearly wrong.)

## What we understood

**The residual subtracts exactly the part that carries the signal.** On
PortScan and DDoS the fixed mean already reaches 0.961 — and it reaches it
because the **level** of node error is itself discriminative. Asking "is this
value surprising for an edge of this shape?" removes the predictable component,
and on these families the predictable component *is* the attack signal. So the
residual is not a noisier version of the mean; it is a different quantity, and
a worse one. The −0.32 on PortScan seed 1 is that subtraction failing badly on a
single graph, not noise around a small effect.

**The one family where the aggregator could plausibly matter is the one where
it doesn't help either.** Botnet's fixed mean sits at 0.442 — chance. If edge
aggregation were the bottleneck, this is where a better aggregator would show
itself. The residual gives **+0.002**, i.e. nothing. Two of the three signals
are therefore consistent: the edge score is already extracting what the node
scores contain.

**This localises the bottleneck, which is the useful part.** The edge aggregator
is a lossy *downstream* step. The information that is missing was already
missing one level up, in what the node autoencoder encodes. And E01 has
independently shown that this is exactly where the leverage is: replacing a
count-vector *representation* with a sequence one bought **+0.058 AUC (11.9
SD)** with no change in capacity. Same lesson, different layer — **the
representation is the constraint, not the readout.**

**So the per-flow gap is not closable at the edge level**, and the next thing to
try is upstream: better node scores (which E01's seq-AE arm now provides for
the host pillar, and for the network pillar would mean a richer node
representation than 19 aggregated dims). A `mean + λ·residual` blend is the
obvious cheap variant still untested, but the mechanism above predicts it
cannot beat the mean by much, so it is low priority.

## Files

- `exp_e52_edge_head.py` — both arms, corrected scorer
- `exp_e52_edge_head.json` — per-seed results
- History: the INVALID first run's numbers are quoted above for the record and
  are not a result
