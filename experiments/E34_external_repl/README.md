# E34 — External replication: IDS2018 and CTU-13 (RC-29, RC-32)

**Verdict: PASS** · 2026-08-21 / 2026-08-25 · commits `80675c5`, `9e11646`, `c4926df`

## Aim

Every result to this point was on CIC-IDS2017 — one lab, one capture stack, one
year, one benign population. A model that only works there is a benchmark
artifact. The aim was replication on genuinely different data, and the specific
claim under test was the project's *operational* one: **attackers rank in the
top handful out of tens of thousands of hosts**, on data the model has never
seen.

Protocol: train on the benign slice **before the first attack timestamp**,
evaluate everything after. Fully unsupervised, no attack labels used.

## What was done

**CSE-CIC-IDS2018** — `Thursday-20-02-2018_TrafficForML_CICFlowMeter.csv`, the
only one of ten files that has IP columns (the "typo is official" note in
`data/README.md`). LOIC-HTTP DDoS, 10 attacker hosts.

**CTU-13 (Stratosphere Lab)** — three real botnet captures, adapted via column
map: `s1_neris`, `s13_virut`, `s3_rbot`. Different lab, different country,
different decade, Argus NetFlow rather than CICFlowMeter.

## Results

**IDS2018** — 32,935 hosts, 10 attackers:

| Seed | Attacker ranks | Best-rank percentile |
|---|---|---|
| 0 | 1 – 10 | 3e-05 |
| 1 | 1 – 10 | 3e-05 |
| 2 | 1 – 11 | — |
| 3 | 23 – 34 (worst) | — |

Top-11 of 32,935 in 3 of 4 seeds, top-35 worst case.

**CTU-13:**

| Scenario | Result |
|---|---|
| s13 Virut | infected host **rank 1 in all 4 seeds** (314,177 hosts) |
| s3 Rbot | C&C host rank 1 in 3 of 4 seeds (434,730 hosts) |
| s1 Neris | worst seed 112 / 522,167 = top 0.02% |

## What we understood

**The operational claim replicated on a third dataset family — and the most
convincing detail is the training set size.** Virut's infected host ranked
first out of 314,177 hosts having trained on **4 benign graphs**; Rbot's C&C
host ranked first out of 434,730 having trained on **2**. Minutes of benign
traffic is enough, because the signal is relational and a scanner/beacon looks
relational from the first few windows. That is a strong, specific claim, and
much more interesting than the AUC.

**Two caveats that the archive records rather than hides, both about labels.**

1. **CTU-13 inflates the malicious class.** Every *destination* that an
   infected host touches gets labelled botnet, which is semantically true and
   operationally useless — recall@100 is therefore near zero on CTU-13 and
   **must not be quoted**. The right metric there is the infected-host rank
   percentile, which is why the table above reports ranks and not recall.
2. **Host-window P@100 has huge variance on tiny families** (std up to 0.48
   with ~5 malicious hosts). It is not a stable number and is not quoted.

Both are the same lesson as [E15](../E15_card_original/)'s Botnet row, arriving
from a completely different dataset. **Label inflation is the norm in NIDS
benchmarks, which is why rank beats AUC for operational claims** — the rank
question ("is the real attacker at the top?") survives contamination that the
classification question does not.

**Why this matters for the archive's later direction.** This experiment is the
strongest existing evidence that the detector's skill is *relational*, not
dataset-specific — which is the exact property that
[E29](../E29_transfer/) later showed does **not** transfer across *extraction
pipelines*. Replication on a new dataset succeeded; transfer to a new
extractor failed. Those are different axes and the project needed both.

## Files

- `external_ids2018_multiseed.json`, `external_ids2018_results.json`
- `external_ctu13_multiseed.json` (2.3 MB), `external_ctu13_results.json` (1.0 MB)
- `eval_ctu13_s1.log`, `eval_ctu13_s3.log`, `ctu13_multiseed.log`, `eval_external_ids2018.log`
- `overnight_ids2018_4seed.log`, `overnight_ctu13_4seed.log` — the overnight band runs
- `exp_m5a_fusion_external.py`, `m5a_fusion_external.json` — M5a on the same externals
- `run_externals_multiseed.cmd` — launcher
