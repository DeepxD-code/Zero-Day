# E45 — How much of our testbed is actually encrypted? (the item-5 answer)

**Verdict: NEGATIVE for the empirical claim / PASS for the structural one** · 2026-09-29

## Aim

Item 5 of the open-issues list asked for a confirmed-TLS testbed to replace
port-443-as-a-proxy. Before downloading one, this experiment measures what the
existing data actually contains, because the whole E11/E13 "encryption" line
rests on that proxy and nobody had checked whether it had anything behind it.

## What was done

For all 8 original day-files and all 5 improved day-files: classify every flow
as encrypted-port (443, 8443, 993, 995, 465, 636, 5061, 5222, 5223) or not, and
cross-tabulate against the attack label. `- Attempted` excluded as everywhere
else in the archive.

## Results

**Corpus totals: 5,219,321 flows, 1,351,679 attack flows.**

| | Value |
|---|---|
| Flows on encrypted ports | **17.33%** |
| Attack flows on encrypted ports | **3,256** |
| **Share of attack traffic that is encrypted-port** | **0.24%** |

Per file, the share of *attack* traffic on encrypted ports:

| File | Encrypted (all) | **Encrypted (attacks)** |
|---|---|---|
| orig / Monday | 26.74% | **0.00%** |
| orig / Tuesday | 21.98% | **0.00%** |
| orig / Wednesday | 14.57% | **0.00%** |
| orig / Thursday-WebAttacks | 7.89% | **0.00%** |
| orig / Thursday-Infiltration | 18.22% | **0.00%** |
| orig / Friday-Botnet | 20.72% | **0.00%** |
| orig / Friday-PortScan | 9.86% | 0.85% |
| orig / Friday-DDoS | 6.04% | **0.00%** |
| clean / monday…friday | 11.6–28.9% | 0.00–0.77% |

## What we understood

**There is no encrypted attack traffic in these datasets to evaluate on.** Six
of the eight original day-files contain **zero** attack flows on any encrypted
port. 0.24% of attack traffic corpus-wide, concentrated in PortScan's 0.85%.

This reframes E11 and E13 completely:

- **E13's headline** ("port-443 AUC 0.89, fused 1.0") was computed on a slice
  with **5 attacker edges out of 11,054** — a population I already flagged as
  diagnostic-only via `eval_utils.slice_verdict`, but whose true size is now
  known: 0.24% of all attack traffic in the entire corpus.
- **E11's "gap STAYS OPEN"** was not measuring blindness to encryption. It was
  measuring an almost-empty set, which E11's own README already suspected
  ("absence of attack being read as blindness") and E13's correction confirmed.
- So the TLS thread through the archive is **methodologically correct and
  empirically unsupported**. The port-conditioning fix in E13 was still the
  right fix — splitting before graphing genuinely does fragment topology, and
  that bug is real regardless of label counts — but neither result is evidence
  about encryption.

**The available public alternatives are not IDS datasets.** Checked for item 5:

| Dataset | What it actually is | Usable? |
|---|---|---|
| CSTNET-TLS 1.3 (ET-BERT) | Real TLS 1.3, but **10 application classes** — app classification, no attacks | No |
| CESNET-TLS22 / QUIC22 / TLS-Year22 | 191 apps over 2 weeks / 1 year, flow records, Zenodo | No — no attack labels |
| USTC-TFC2016 | VPN/Tor/BT + normal, tiny, no clean attack families | Marginal at best |
| ISCX VPN-nonVPN | VPN/Tor/SSH/SMB + web attacks, 2015 vintage | Marginal, and the encryption is via VPN not TLS |

There is no widely-available benchmark with **confirmed TLS/QUIC attack traffic
and IDS-grade labels**. The field's encrypted-traffic datasets (ET-BERT, FS-Net,
BLOCK-BERT) are app-identification problems — a different task, like
PIKACHU was.

**So the report's encryption claim must be the structural one, stated
explicitly.** It is a legitimate argument, and a strong one:

> None of the 87 frozen flow features requires payload content. They are L3/L4
> header and flow statistics — lengths, inter-arrival times, flags, window
> sizes, bulk rates, active/idle duty cycle. TLS conceals the payload; it does
> not alter the metadata this detector scores. No decryption is performed, and
> none would help an attacker who wants to stay hidden, because the features
> they would need to forge (packet lengths, timing) are exactly the ones we read.

That is verifiable by inspection of the frozen catalogue
(`detection/training_features/README.md`, `schemas/feature_vector.json` v3.0)
and it does not depend on a dataset. What the project **cannot** claim is
"evaluated on encrypted traffic", because it was not — and now that number is
measured rather than assumed.

**Future work, honestly scoped:** obtaining or generating genuinely encrypted
attack traces (a TLS-terminating testbed re-encrypting CIC-IDS flows, or the
LID-DS/ADFA host traces which are unaffected by network encryption at all) is a
Week-6+ item. It is not a code change.

## Files

- `exp_e45_encrypted_share.py` — the measurement
- `exp_e45_encrypted_share.json` — per-file breakdown
