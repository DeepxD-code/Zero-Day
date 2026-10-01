# E56 — Fusing the VAE as a third view

**Verdict: PARTIAL. The prediction was met (WebAttacks 0.9525 > 0.950) but the
gain over the existing E43 system is +0.002 — inside noise.** · 2026-09-30

## Aim

[E55](../E55_vae_baseline/) found a working per-node VAE that beats the graph
autoencoder on exactly one family (WebAttacks 0.935 vs 0.893). [E43](../E43_fusion_rule/)
showed fusion works by combining views that fail differently. So: fuse it in.

**Prediction, stated before running:** WebAttacks fused > 0.950; everything else
within noise.

## Results — 4 seeds, one protocol, VAE (β=0.01, 600 ep) checkpointed

| Family | gnn alone | vae alone | **noisyor** | **rank-max** | E43 system |
|---|---|---|---|---|---|
| Botnet | **0.4421** ± 0.017 | 0.4115 ± 0.006 | 0.4154 ± 0.006 | 0.4158 ± 0.008 | **0.7092** |
| PortScan | 0.9612 ± 0.002 | 0.9525 ± 0.004 | **0.9659** ± 0.002 | 0.9559 ± 0.006 | 0.9690 |
| DDoS | 0.9612 ± 0.002 | 0.9525 ± 0.004 | **0.9659** ± 0.002 | 0.9559 ± 0.006 | 0.9690 |
| Infiltration | **0.6333** ± 0.004 | 0.5909 ± 0.004 | 0.6240 ± 0.002 | 0.6182 ± 0.001 | **0.6684** |
| WebAttacks | 0.8931 ± 0.009 | 0.9390 ± 0.005 | 0.9513 ± 0.004 | **0.9525** ± 0.004 | 0.9502 |

## What we understood

**The prediction held, and the mechanism is exactly the one E43 proposed.** The
one family where the two views fail differently is WebAttacks, and that is the
one family where fusion pays: **0.8931 → 0.9525, a +0.059 gain** — by far the
largest fusion gain in the archive, and it comes from adding a *weaker
everywhere-else* model. On PortScan/DDoS noisyor adds a further +0.005 over the
graph alone (0.9612 → 0.9659).

**But it does not beat the system we already have.** E43's two-pillar +
reputation system scores 0.9502 on WebAttacks; this VAE fusion scores 0.9525.
**That is +0.0023 against E43's ±0.008 band — inside noise.** Read plainly: the
VAE is a viable *substitute* for the M5a flow pillar on bursty families, not an
*improvement* to the full system. Anyone quoting "+0.059" as a new system result
would be quoting a comparison against a single arm, which is the same
arm-vs-system mistake E55 caught me making.

**Fusion actively hurts on the persistent families.** Botnet 0.4421 → 0.4158
and Infiltration 0.6333 → 0.6182, both *down*. The VAE is at or below chance
on Botnet (0.4115), so averaging it in drags the graph arm down. This is the
cleanest instance yet of the E43/E48 pattern: **views help only where they are
complementary, and dilute where one is weak.** No single fusion rule wins
everywhere, and the two rules disagree here too — noisyor wins PortScan/DDoS,
rank-max wins WebAttacks.

**E43's reputation component remains the load-bearing element and is not
replaceable by a third encoder.** Botnet 0.7092 vs 0.4158 here, a 0.29 gap
that no amount of view-fusing touches. Whatever rescues Botnet is *temporal
persistence across windows*, not a better within-window encoder — which is
consistent with E48's short-vs-long finding and with Botnet being a Pillar-3
problem.

## What to do with this

- **Keep the VAE checkpoints** (`detection/vae_improved_s{0..3}.pt`, β=0.01,
  val 6.1–7.4e-4) — they are a legitimate third view and a legitimate
  substitute for M5a on bursty families.
- **Do not replace the system.** The fused VAE ties E43 on WebAttacks and loses
  badly on Botnet and Infiltration.
- **The real target remains the node representation** (E01's lever, +0.058 in
  the host pillar, never pulled in the network pillar), not a fourth encoder.

## Files

- `exp_e56_vae_fusion.py` / `.json`
- `detection/vae_improved_s{0,1,2,3}.pt` — the fixed VAE, 4 seeds
