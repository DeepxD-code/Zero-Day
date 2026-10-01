# E11 — Encrypted-traffic ablation (port 443)

**Verdict: BUG (in our own method)** · 2026-09-26 · commit `a9cb8c3`

## Aim

The report's reviewer objection, stated plainly: **most real traffic is
encrypted.** ~94% of Google's web traffic and ~70% of sites run TLS 1.3 by
mid-2024, plus QUIC and ECH which hide even the SNI. If our detector only works
on plaintext, the whole system is a 2017 artifact.

The static audit came back clean and is the important half of this experiment:
**all 76 flow features are L3/L4 header statistics** — lengths, IATs, flags,
window sizes, bulk rates, active/idle. Not one requires payload content, DPI
strings, SNI, or certificates. TLS hides the payload; it does not hide the
metadata this detector scores. This is the same principle as Cisco's
Encrypted Traffic Analytics / Joy (SPLT, byte distribution, TLS metadata).

So the empirical question: does the detector actually work on the encrypted
portion of traffic?

## What was done

Per family (PortScan, WebAttacks, DoS): split the day's flows into
`dst_port == 443` and everything else, build v2 60s graphs **separately**,
score with the shipped checkpoint, compute edge AUC for each subset.

## Results

| Family | n (443) | n (rest) | attack share of 443 | **443 AUC** | rest AUC |
|---|---|---|---|---|---|
| PortScan | 26,935 | 259,532 | 0.0089 | **0.2139** | 0.6604 |
| WebAttacks | 35,833 | 134,533 | **0.0000** | **null** (0 edges) | 0.8417 |
| DoS | 100,229 | 592,474 | **0.0000** | **0.2329** | 0.7571 |

The commit message at the time said "gap STAYS OPEN, documented". That was
honest reporting of a bad number — and the number was wrong.

## What we understood

**The measurement was broken in two ways, and neither was the model's fault.**

1. **Topology fragmentation.** Splitting the dataframe *before* building graphs
   means each port-443 graph is built from a disconnected fragment. `out_degree`
   — the exact feature that catches a port scan — collapses, because the
   attacker's non-443 edges no longer exist to inflate it. We destroyed the
   signal and then measured the wreckage.
2. **The attackers barely use 443.** `attack share` is 0.0000 for WebAttacks
   and DoS. For those families the 443 subset contains **no attacks at all**,
   so the AUC is either null (0 positive edges) or measuring the ranking of
   benign-vs-benign (0.23 on PortScan's 5 attacker edges, which E14 later
   showed has a 95% CI of 0.71–1.00). Absence of attack was being read as
   blindness to encryption.

None of this is exotic. It is the same family of error as E07 (edge count) and
A3 (base rate): a number measured on a different population than the one it is
compared against. The fix was verified in E13, which closed the gap completely.

**What survives from E11 and stays true:** the static audit. No feature in the
frozen 87-dim catalogue needs decryption. That claim is independent of the
measurement error and is the one worth putting in the report.

## Files

- `exp_e11_tls_split.py` — the flawed procedure, kept deliberately
- `exp_e11_tls_split.json` — the flawed numbers, kept deliberately

Superseded by [E13](../E13_tls_fix/).
