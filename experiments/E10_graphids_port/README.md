# E10 — GraphIDS port vs our SAGE-MLP under the held-out protocol

**Verdict: CONTROL** · 2026-09-26 · commit `77e3afe`

## Aim

A port of **GraphIDS** (a published graph-based IDS design) was available for
comparison. Two questions:

1. Does it reproduce its published numbers under *our* protocol (7 held-out
   families, full files, 4 seeds, CUDA-deterministic)?
2. Is our SAGE-MLP actually better, or are we comparing our model against a
   weaker one?

Without this, every "we beat X" claim in the report is unfalsifiable — we would
not know whether X was implemented correctly.

## What was done

Same held-out-family protocol as the production evaluation. Both models
retrained per seed on Monday benign only, evaluated on all 7 attack families:

- **port** — GraphIDS architecture as published
- **ours** — `GraphAutoencoder` (SAGEConv, 19-dim, LogScaler)

4 seeds each. Determinism flag split so the screening pass is fast but the
recorded run is reproducible.

## Results

| Seed | port — worst family | ours — worst family | port mean | ours mean |
|---|---|---|---|---|
| 0 | Botnet 0.9923 | Botnet 0.9981 | ~0.9985 | ~0.9996 |
| 1 | Botnet 0.9407 | Botnet 0.9973 | ~0.9974 | ~0.9995 |
| 2 | **Botnet 0.9582** | Botnet 0.9983 | ~0.9986 | ~0.9996 |
| 3 | Botnet 0.9960 | Botnet 0.9984 | ~0.9991 | ~0.9996 |

Per-family (seed 0): PortScan 1.0000/1.0000, DDoS 1.0000/1.0000, Infiltration
0.9983/0.9997, WebAttacks 0.9996/0.9994, Patator 0.9987/0.9998, DoS
0.9990/1.0000, Botnet 0.9923/0.9981.

## What we understood

**The port works, and the honest comparison is much closer than expected.**
GraphIDS is *not* a strawman — it clears 0.997 on this protocol, and on five of
seven families it is statistically indistinguishable from ours (both at
ceiling). The entire gap lives in **Botnet**: GraphIDS swings 0.9407–0.9960
across seeds, ours holds 0.9973–0.9984.

Two conclusions:

1. **We should not claim to beat GraphIDS overall.** Claiming a win on a
   benchmark where both models sit at 0.999 is noise-chasing. The defensible
   claim is narrow and specific: *our model is more consistent on the one
   family where graph topology carries no signal.*
2. **The seed-swing pattern repeats.** GraphIDS's Botnet band (±0.028) looks
   exactly like the WebAttacks variance E26 later diagnosed as undertraining
   (0.813±0.091 pre-fix). It is the same phenomenon, in a different model,
   which strengthens the E26 diagnosis considerably: this is a property of
   graph autoencoders on near-ceiling families, not of our implementation.

## Files

- `exp_e10_graphids_port.py` — procedure (both architectures)
- `exp_e10_graphids_port.json` — per-seed per-family AUCs
