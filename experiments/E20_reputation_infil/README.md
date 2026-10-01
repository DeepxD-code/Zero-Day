# E20 — Causal reputation vs single-window scoring (Infiltration)

**Verdict: PASS** · 2026-09-27 · commit `a2be3f7`

## Aim

[E14](../E14_risk_controls/) shipped `HostReputation` after E13 verified that
causal running-mean fusion works (0.9997 on PortScan). Infiltration was the
family where the mechanism was most needed: its AUC of 0.760 is 0.2 below
every other family except Botnet, and the diagnosis was specific — **hammered
victim servers outrank the attacker within each window**, so per-window
rankings are dominated by whoever is loudest, not by who is persistent.

If reputation works as theorised, Infiltration should rise, and the rise should
be causally available (no future windows).

## What was done

Clean Thursday, retrained improved M5b, 60s v2 graphs, attacker = source host
of `Infiltration` or `Infiltration - Portscan` (866 attacker edges across
55,202 scored edges).

Three scoring methods on identical edges:

| Method | What it sees |
|---|---|
| **single-window rank** | this window only, ranked within it |
| **transductive mean** | mean over the *whole day*, including windows after the edge |
| **causal running mean** | mean over windows *up to and including* this one |

## Results

| Method | AUC |
|---|---|
| single-window rank | 0.760 |
| transductive mean (whole day) | 0.9735 |
| **causal running mean** | **0.9082** |

## What we understood

**The mechanism does exactly what it was designed to do, and the 0.97→0.91 gap
is the price of causality, quantified.**

The walk-through that makes it obvious: suppose the attacker acts across 10
windows at 0.5 each (slightly odd, persistently). A victim server gets hammered
in window 3 only, at 0.9 there and 0.1 elsewhere.

- **Single-window (0.760):** in window 3 the victim (0.9) outranks the attacker
  (0.5), and rankings reset every window — the attacker's consistency across 10
  windows counts for nothing. Each window judges in isolation, so being loud
  beats being persistent.
- **Transductive (0.9735):** attacker averages 0.5; victim averages
  (0.9 + 9×0.1)/10 ≈ 0.18. The attacker wins easily. But at window 3 in real
  life you do not have windows 4–10 yet — the score peeks at the future. Great
  for analysis, undeployable.
- **Causal (0.9082):** at each window, average only what has been seen. Window
  1, the attacker is flagged immediately. By window 3 the victim spikes, but the
  attacker's history (0.5, 0.5, 0.5) still beats the victim's running average.
  Early windows cost a little accuracy versus hindsight; that is the 0.065 gap.

**Why this generalises beyond Infiltration.** The same argument killed E12's
slow-drip evasion (×5 → 0.979 at ×5 in E24). Both are the same property:
**windows see moments, accumulators see histories, and evasion that works
against the former is defeated by the latter.** A scanner that dials its rate
down or a victim that gets hammered once cannot avoid being persistently odd.

**Production consequence:** `HostReputation.update()` is fed each window's host
scores and `edge(src, dst)` is the fused score for an alert. Infiltration is
one of the two families where the *deployable* number (0.908) is the number to
quote — the 0.974 is not available to a live system.

## Files

- `exp_e20_reputation_infiltration.json` — the three numbers
- `../../detection/host_reputation.py` — the shipped mechanism
