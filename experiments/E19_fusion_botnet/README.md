# E19 — Fusion rules against Botnet (the hard family)

**Verdict: PARTIAL** · 2026-09-27 · commit `3760ffa`

## Aim

Botnet is the family where the graph pillar fails, so it is where fusion has to
prove itself. The question: which combination of the two pillars surfaces
command-and-control traffic, and does combining them help or dilute?

## What was done

Clean Friday (Botnet day), retrained improved models
(`gnn_improved_monday_v2.pt` + `m5a_revived_improved.pt`), 60s v2 graphs,
within-window-rank metric, PortScan and DDoS as controls on the same day.

Per-flow scores are aggregated to hosts by max, then:

- **m5b / m5a** — each pillar alone
- **noisyor** — `1 − (1−r_m5b)(1−r_m5a)` on within-window ranks (OR-logic)
- **rank_max** — `max(r_m5b, r_m5a)` (the gotcha #17 rule)
- **repfuse** — 50/50 on *causal running-mean host reputation*, not ranks

## Results

| Arm | Botnet | PortScan | DDoS |
|---|---|---|---|
| m5b (graph) | 0.3505 | 0.9790 | 0.9974 |
| m5a (flow) | **0.6606** | 0.9186 | 0.9955 |
| noisyor | 0.5053 | 0.9704 | 0.9795 |
| rank_max | — | — | — |
| repfuse | 0.6670 | 0.9515 | 0.9813 |

## What we understood

**Fusion *diluted* Botnet — 0.66 down to 0.51 — and that was the useful
result.** The instinct "combine the pillars for the weak family" is wrong when
one pillar is not merely uninformative but *anti-informative*. M5b's Botnet
AUC of 0.35 is below chance: its rankings on that day are close to inverted. OR-logic then does the worst possible thing — it keeps whichever arm is higher, and M5b's noise is high, so noise gets OR'd into every alert.

The fix came from asking *why* the graph pillar fails on C2. Not because the
graph is noisy but because **C2 conversations look like ordinary
client-server traffic** — there is no topology anomaly to find, so M5b is
fitting noise. A noise arm cannot be fused away; it has to be removed or
replaced by a mechanism that has information M5b lacks.

That is exactly what **reputation** is: 0.6670, the best Botnet number measured
anywhere, and it comes from accumulation across windows rather than from a
better graph. PortScan and DDoS confirm it costs nothing (0.9515 / 0.9813,
tied-top). [E21](../E21_band/) then confirmed repfuse as best-or-tied across
all three families over 4 seeds and promoted it to the fusion default.

**The honest ceiling:** 0.667 is where the *network* pillar ends. Botnet's C2
is normal-looking on the wire by construction. The remaining lift requires the
malware process's own behaviour — Pillar 3, `host_autoencoder_adfa.pt`, which
needs LID-DS (Person A's loader) to evaluate against botnet scenarios. That
dependency is why Botnet is the top open item in the root README rather than a
solved line.

## Files

- `exp_e19_fusion_botnet.json` — the arms above
