# E15 — 7-family report card, ORIGINAL data

**Verdict: CONTROL** · 2026-09-27 · commit `8f8756c`

## Aim

Everything before E15 measured PortScan, or a family at a time, or a single
seed. The report needs one table covering all seven held-out attack families
on the shipped production artifact, with error bars and ranks. E15 is that
table — and it turned out to be the baseline that E16 destroyed.

## What was done

Shipped `gnn_autoencoder_v1_logscale_v2.pt`, original
`data/GeneratedLabelledFlows/` (one file per attack day, file-per-family
labelling), v2 60s graphs. Per family: edge AUC (within-window rank), 95% CI,
**best attacker rank**, and the port-443 slice with its verdict.

Attackers are identified by the file's own labelling
(`evaluate_gnn.malicious_hosts`); the scored edge is positive if its *source*
host is an attacker host.

## Results

| Family | AUC | 95% CI | Best rank | Attacker edges | 443 AUC |
|---|---|---|---|---|---|
| Patator | 0.9629 | 0.941–0.985 | 5 | 144 | null (diag) |
| DoS | 0.8832 | 0.855–0.912 | 27 | 231 | null (diag) |
| WebAttacks | 0.9299 | 0.890–0.970 | 4 | 76 | null (diag) |
| Infiltration | 0.5768 | 0.566–0.587 | **1** | 3,330 | 0.625 (quotable) |
| Botnet | 0.4597 | 0.454–0.465 | **1** | 21,060 | 0.548 (quotable) |
| PortScan | 0.8714 | 0.788–0.955 | 16 | 29 | 0.893 (diag) |
| DDoS | 0.8988 | 0.881–0.916 | 2 | 554 | null (diag) |

## What we understood

**Read down the "Best rank" column before the AUC column, because that is
where the real story is.** Every single family ranks its attacker in the top
27 of tens of thousands. Botnet has AUC 0.460 — *below chance* — and still
puts the attacker at **rank 1**.

That gap is not a paradox, it is label inflation. Botnet's 21,060 "attacker
edges" come from 2,376 positive edges; the CTU-style contamination pattern is
the reverse of Botnet's own problem here — on CIC-IDS2017 every destination
the infected host touches gets labelled malicious, so the positive class is
mostly benign-looking traffic, and AUC against it is meaningless while the
*rank* of the true source is still perfect. The same mechanism inflates
Infiltration's 3,330.

**This is why CLAUDE.md says to quote attacker rank and recall@100, never
host-level P@100.** P@100 is capped at bad/100 (1–8 attackers among thousands);
AUC is destroyed by label inflation; rank survives both because it asks a
different question — not "can you classify every positive" but "is the actual
attacker at the top".

**And the caveat that E16 then confirmed:** these numbers are good *on this
data*, and this data turned out to be polluted. E15's real value was being a
clean control that made the contamination measurable.

## Files

- `exp_e15_report_card.py` — procedure (`--ckpt` / `--out` for reuse)
- `exp_e15_report_card.json` — the table above
