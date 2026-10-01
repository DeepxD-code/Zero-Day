# E13 — Port-conditioned TLS evaluation (the fix for E11)

**Verdict: PASS** · 2026-09-26 · commits `c54490e`, `d51a9c3`, `cc557ec`

## Aim

E11 concluded "our detector is blind to encrypted traffic" (443-AUC 0.21 vs
0.66). That conclusion came from a broken measurement. This experiment rebuilds
the evaluation correctly and answers the real reviewer question: **does the
detector work on encrypted traffic?**

## What was done

The fix is one change in the order of operations:

```
E11 (wrong):   split df by port  ->  build graphs  ->  score  ->  filter edges
E13 (right):   build graphs (full)  ->  score  ->  filter edges by port
```

Topology is now intact during scoring, because the port filter applies to
**edges after** the graph is built and scored — the attacker's other edges are
still there inflating `out_degree`, exactly as in production.

Arms, all on the shipped v2 checkpoint:

- **A_split** — E11's procedure, kept as the control
- **B_cond** — the fix, port-conditioned on the dominant port per (src, dst)
- **C_multi** — B_cond on 60s + 300s with rank fusion
- **D_fused** — reputation-fused host score across windows

## Results

| Arm | PortScan 443 | PortScan rest | ALL edges |
|---|---|---|---|
| A_split (E11 method) | 0.2139 | 0.6604 | — |
| **B_cond (fix)** | **0.8935** (n=11,054) | 0.8600 (n=19,559) | — |
| D_fused (host reputation) | **1.0000** | 0.9907 | 0.9946 |

Risk verification, same run:

| Check | Result |
|---|---|
| R1 Monday threshold → Friday | AUC 0.9998, **precision 0.037** — ranking transfers, operating point does not |
| R2 443-slice 95% CI (5 positives) | **0.708 – 1.000** — the 0.89→1.0 "lift" is inside the noise of 5 samples |
| R3 causal vs transductive fusion | transductive 1.000, **causal running-mean 0.9997** — no hindsight needed |

## What we understood

**The encrypted-traffic "weakness" was never a model weakness. E11 was
measuring the wrong population, twice over** (fragmented topology, and attackers
who barely use 443). Scored correctly, port-443 edges are *easier* than the
rest — 0.893 vs 0.860 — which is what you would expect if anything, because
443 traffic has fewer distinct services to spread across.

**The static audit from E11 survives and is the report-grade claim:** zero of
the 87 features require decryption. That is the real answer to "most traffic is
encrypted", and it was true from the start.

Three sub-findings that outlived this experiment:

1. **R1 is now production behaviour** — frozen raw thresholds were retired in
   [E14](../E14_risk_controls/) in favour of rank cuts, precisely because a
   threshold fit on Monday gives 1 true positive per 27 alerts on Friday.
2. **R2 is why `eval_utils.slice_verdict()` exists** — a 5-positive slice
   cannot carry a headline, whatever its point estimate.
3. **R3 validated the deployable form of the fix** — the whole-day mean scores
   1.000 but peeks at the future; the causal running mean scores 0.9997 and
   *can* run live. That difference became `detection/host_reputation.py`.

## What remains genuinely open

The honest gap is not "TLS is opaque to us" — it is that **our testbeds
predate TLS 1.3 / QUIC / ECH, and no testbed here contains a confirmed-TLS
ground-truth label.** The port-443 subset is a *proxy* for encryption, not
proof of it. Closing this properly needs an encrypted-traffic dataset
(ISCX VPN/nonVPN, USTC-TFC2016, or CSTNET-TLS1.3) and the TLS-metadata
features (cipher suite, JA3, cert age, SPLT, byte distribution) that
Encrypted Traffic Analytics work uses. That is a Week-6+ item, not a code fix,
and it should be written into the report as future work rather than implied
away.

## Files

- `exp_e13_tls_fix.py` — both the flawed and fixed procedures, data-gated
- `exp_e13_tls_fix.json` — all four arms plus R1/R2/R3 verification
