# E55 — A working VAE baseline, and the honest competitive position

**Verdict: the numbers claim is now defensible as "competitive, not leading."**
· 2026-09-30

## Why this experiment existed

Two flaws in the previous numbers claim, both mine:

1. **I compared a single arm to published *systems*.** Quoting our graph arm
   alone (Botnet 0.442, Infiltration 0.633, Web 0.893) against a 0.95+ literature
   is arm-vs-system. Our **fused system** on the same families is PortScan
   **0.969**, DDoS **0.969**, WebAttacks **0.950** — already in the published band.
2. **E54's VAE arm was a broken straw man**, and refusing to cite it was right,
   but it left the strongest baseline unanswered.

## The VAE now trains

KL-weight sweep, selected on validation reconstruction against the plain AE's
3.3e-05 reference:

| config | val reconstruction |
|---|---|
| β=1.0, 600 ep | 1.748e-02 ← this is E54's collapse, reproduced |
| β=0.1, 600 ep | 2.992e-03 |
| **β=0.01, 600 ep** | **7.759e-04** ← selected |

**23× better than the collapsed arm**, and the diagnosis is confirmed: with
z=8 on a 19-dim input, β=1 from step 0 makes the posterior collapse toward the
prior and the decoder stops reading `x`. E54 was not measuring a VAE.

Even at β=0.01 the VAE reconstructs 23× worse than the deterministic AE. On
19 well-separated benign dims a stochastic bottleneck costs reconstruction
without buying anything — worth knowing about this feature set.

## Results — fixed VAE vs the graph autoencoder, one protocol, 4 seeds

| Family | vae (fixed) | **gnn_ae** | Δ (gnn − vae) |
|---|---|---|---|
| Botnet | 0.4182 ± 0.007 | **0.4421** ± 0.017 | +0.024 |
| PortScan | 0.9509 ± 0.004 | **0.9612** ± 0.002 | +0.010 |
| DDoS | 0.9509 ± 0.004 | **0.9612** ± 0.002 | +0.010 |
| Infiltration | 0.5855 ± 0.003 | **0.6333** ± 0.004 | **+0.048** |
| WebAttacks | **0.9353** ± 0.006 | 0.8931 ± 0.009 | **−0.042** |

## The defensible position

**Competitive, not leading — and now that statement is evidence-backed.**

1. **On the saturated families we are at parity-plus.** PortScan and DDoS:
   0.9612 vs a working VAE's 0.9509, a **+0.010** margin. Published numbers
   cluster at 0.95–0.99, so we sit inside that range. **This is the single
   most important correction: a well-tuned per-node VAE on our strict protocol
   already reaches 0.951, so our advantage there is ~0.01, not a step change.**

2. **The graph's real win is Infiltration: +0.048** — nearly 0.05, and the
   largest architectural margin measured anywhere. E52 localised the bottleneck
   to the node encoder; this quantifies it.

3. **We lose WebAttacks by 0.042 to a VAE.** Reported because it is real, and
   because a comparison that only lists wins is not a comparison. WebAttacks is
   where a per-node reconstruction can exploit distributional shape that message
   passing smooths away.

4. **Botnet is nobody's win.** VAE 0.418, graph 0.442, every arm 0.42–0.54,
   all chance. Fused reputation gets 0.709 (E43) — the *fusion* rescues this
   family, not the encoder.

### What may be quoted, and what may not

| Claim | Status |
|---|---|
| "0.961 on PortScan/DDoS, 0.950 WebAttacks fused — competitive with 0.95–0.99 published" | **Defensible** |
| "graph beats a matched per-node AE by +0.048 on Infiltration" | **Defensible, matched conditions** |
| "we beat a VAE by 0.45" | **False** — that was E54's collapsed arm. Real margin is +0.010 |
| "we lead unsupervised SOTA" | **Not supported.** A per-node VAE reaches 0.951 here |
| "benign-only + held-out days + per-family bands is a stricter protocol than most of the 0.95+ literature" | **Defensible** and the honest differentiator |

**The category claim is the defensible one; the numbers claim reduces to parity
plus a targeted architectural win.** Anyone claiming otherwise from this branch
is reading E54's broken table, which is now explicitly retracted.

## Files

- `exp_e55_vae.py`
- `exp_e55_vae.json` — β sweep, per-seed, bands
