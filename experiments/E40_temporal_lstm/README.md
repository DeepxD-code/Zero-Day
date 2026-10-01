# E40 — The temporal/LSTM half (RC-20)

**Verdict: NEGATIVE** · 2026-08-11 / 2026-09-26 · commits `f218639`, `22231d7`, `7fe9d5b`

## Aim

The PDF's M5b is described as a *GNN + LSTM* model: graph autoencoder for
topology, recurrent model for the sequence of hosts over time. The branch
delivered the graph half and this file is the sequence half. The honest question
before shipping it: does it earn its place, or is it architecture for
architecture's sake?

## What was done

`gnn_temporal.py` — the standalone LSTM half (later folded into
`detection/gnn_temporal_fused.py` as `GraphTemporalAutoencoder`). Evaluated
under the held-out-family protocol, and reproduced at edge level in
[E02](../E02_edge_fusion/) across two seed groupings.

## Results

- Edge-level: the temporal half alone scores **0.568** against the graph half's
  **0.706** — decisively worse.
- Fused with the graph half: no family improves; several regress.
- Reproduced at both seed groupings (0–1, 2–3), so it is not a seed artifact.

## What we understood

**The sequence a graph autoencoder already sees is the sequence that matters.**
Per-window host graphs already encode *which* hosts talk to which, and fusing
adjacent windows (the 60s + 300s pair in [E35](../E35_multiwindow/)) already
captures the cross-window structure an LSTM would model explicitly. The LSTM
adds a modelling assumption — smooth temporal continuation — that the data does
not reward, and a large number of parameters to fit on the same 487 training
graphs.

This is a well-motivated negative, not a shrug. It is also the *second*
independent finding of the same shape: **[E08](../E08_diverse_fusion/) showed
extra model families do not help when the representation is shared.** The
project has now twice concluded that the win comes from a genuinely different
*view* of the data (relational vs per-flow), never from a different algorithm
over the same view.

**Status in the tree.** `detection/gnn_temporal_fused.py` and
`gnn_temporal_fused_v1.pt` are retained — not because the model is used, but
because the report's architecture comparison needs the honest negative, and the
dashboard's import path (`from gnn_temporal_fused import
GraphTemporalAutoencoder`, Person D's) must keep working. Nothing in
`alert_pipeline.py` imports it.

**The one place a temporal model does earn its keep is the host pillar**,
where the count vector is order-blind by construction and E06/E23 showed the
order-reading HMM beats the count-AE on the one family where order is
diagnostic. The idea was right; it was aimed at the wrong pillar.

## Files

- `gnn_temporal.py` — the standalone sequence half
- Reproduction and per-seed detail: [E02_edge_fusion](../E02_edge_fusion/)
- Shipped-but-unused: `detection/gnn_temporal_fused.py`, `detection/gnn_temporal_fused_v1.pt`
