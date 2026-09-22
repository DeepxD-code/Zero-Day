# Fresh Verification Lookups — 22 Items (2026-09-21)

Sub-agent verification via live web search + Crossref/OpenAlex/arXiv APIs.
Verdicts are strict (IEEE-reviewer bar). Do not cite UNVERIFIABLE items.

## Batch A — graph / provenance / datasets

| # | Item | Verdict | Citation |
|---|------|---------|----------|
| 1 | GraphIDS (NeurIPS'25) | UNVERIFIABLE, likely hallucination | None. Closest real: X-GraphIDS, Bommy et al., IEEE ICDCA 2026, doi 10.1109/icdca69396.2026.11620243 |
| 2 | ARGUS (S&P'24) | UNVERIFIABLE, name collision | "Argus" is Carter Bullard's flow tool, not an S&P paper. No proceedings record found |
| 3 | EULER | REAL | King & Huang, NDSS 2022, doi 10.14722/ndss.2022.24107; journal ACM TOPS 2023, doi 10.1145/3588771 |
| 4 | REAL-IoT drift | REAL (preprint only) | Zhan, Zhou & Haddadi, arXiv:2507.10836 (2025) |
| 5 | Mvula ADFA-LD | UNVERIFIABLE, likely hallucinated surname | None. ADFA-LD itself is real (Creech & Hu 2013) |
| 6a | MAGIC | REAL | Jia et al., arXiv:2310.09831 (2023), listed NDSS'24 — confirm venue before citing |
| 6b | Unicorn | REAL | Han et al., NDSS 2020, doi 10.14722/ndss.2020.24046 |
| 6c | ThreaTrace | REAL | Wang et al., IEEE TIFS 2022, doi 10.1109/tifs.2022.3208815; arXiv:2111.04333 |
| 7 | LID-DS SOTA + benign-only IF | SPLIT: dataset REAL, IF-SOTA claim UNVERIFIABLE | Dataset: Grimmer/Röhling et al., Univ. Hamburg (2019) — confirm proceedings before citing |

## Batch B — adversarial / drift / explain

| # | Item | Verdict | Citation |
|---|------|---------|----------|
| 8 | CERT r6.2 | REAL | CMU SEI dataset, doi 10.1184/R1/12841247.v1; generator Glasser & Lindauer, IEEE SPW 2013, doi 10.1109/SPW.2013.37 |
| 9 | TANTRA | REAL | Sharon et al., IEEE TIFS vol.17 (2022), doi 10.1109/TIFS.2022.3201377; arXiv:2103.06297 |
| 10 | Galli adv. training | REAL, DOI confirmed | Galli et al., 23rd IEEE NCA 2025, doi 10.1109/NCA67271.2025.00043; arXiv:2608.24454 |
| 11 | A2PM realism | REAL | Vitorino et al., Future Internet 14(4):108 (2022), doi 10.3390/fi14040108; arXiv:2203.04234 |
| 12a | MARS | UNVERIFIABLE, likely hallucination | None. Use CertTA (Yan et al., USENIX Security 2025, pp.7349–7368) as certified anchor |
| 12b | TA-RS | REAL (preprint, provisional) | Li, arXiv:2607.13801 (Jul 2026), single author, no venue — verify code before citing |
| 13 | SSF replay | REAL, confirmed | Zhang et al., IEEE INFOCOM 2025, arXiv:2412.16264; code github.com/xinchen930/SSF-Strategic-Selection-and-Forgetting |
| 14 | Ha & Kim tail-risk | UNVERIFIABLE, do not cite | None found |
| 15 | Slack XAI attacks | REAL, venue corrected | Slack et al., AIES 2020 (NOT FAT*), doi 10.1145/3375627.3375830; arXiv:1911.02508 |

## Batch C — industry (all REAL, docs linked)

16. Darktrace Behavioral Defense Platform — https://www.darktrace.com/products/network
17. Vectra AI Attack Signal Intelligence — https://www.vectra.ai/platform
18. ExtraHop RevealX NDR — https://docs.extrahop.com/25.2/detections-overview/
19. Cisco Encrypted Traffic Analytics — Cisco Catalyst config guide (NetFlow/IPFIX SPLT+IDP)
20. Microsoft Defender XDR + ATT&CK — https://learn.microsoft.com/en-us/defender-xdr/threat-analytics
21. IBM QRadar SaaS → Palo Alto XSIAM ($500M, closed 4 Sep 2024) — Palo Alto press release
22. SANS 2024 Detection & Response Survey (n≈400) — https://www.sans.org/white-papers/sans-2024-detection-response-survey

## Do-not-cite list (5)

GraphIDS (NeurIPS'25), ARGUS (S&P'24), Mvula, MARS, Ha & Kim.
Plus corrections: Slack venue FAT*→AIES 2020; TA-RS preprint-only; REAL-IoT preprint-only.

## Reconciliation — 2026-09-21 re-verification (3 parallel batches) vs table above

Re-ran all batches live; conflicts resolved on strict IEEE bar. References.md now [1]–[73] ([23] venue corrected, [61]–[73] appended). Batch C (industry, all 7 REAL) stays OUT of archival References — URLs above are the citation; deployment lesson only.

* GraphIDS: was UNVERIFIABLE above; fresh search claims Guerra et al., NeurIPS 2025, arXiv:2509.16625 ("GraphIDS" = system name, paper title differs, NetFlow-v2/v3 not CICIDS). HELD provisional — NOT added until proceedings/DOI confirmed.
* ARGUS: was UNVERIFIABLE (name collision) above; fresh search claims Xu/Shu/Li, S&P 2024 paper118 ("ARGUS" = system name, paper title is *Understanding and Bridging the Gap…*). Accepted REAL-with-title-rule but NOT added — cite via Wang repro [30] which covers it until proceedings page checked.
* MARS: was UNVERIFIABLE/use-CertTA above; fresh search gives Huang et al., TrustCom 2024, doi 10.1109/TrustCom63139.2024.00117. Accepted REAL, added [70] with no-transfer-to-AE caveat.
* Ha & Kim: was UNVERIFIABLE above; fresh search found Ha & Kim, Appl. Sci. 16(5):2284, 2026. Accepted REAL low-weight, added [72] for eval-practice only.
* Apruzzese [23]: venue was USENIX Sec 2023 — CORRECTED to IEEE SaTML 2023, doi 10.1109/SaTML54575.2023.00031. Propagates to IEEE-draft [28].
* Mvula: confirmed mistaken-identity (real paper is 2023 Discover word-embedding leakage study, not ADFA SOTA). NOT added — caution only.
* LID-DS IF-SOTA: confirmed nonexistent. Dataset only added [66]; do not invent an IF number.

## IEEE-30 impact

IEEE draft (`Chapter2_Literature_Review_IEEE.md`, 30 refs) is FROZEN for submission — no renumbering. If the committee allows swaps: EULER [61] (temporal baseline), ThreaTrace [65] (host GraphSAGE analogue), TANTRA [68] (timing-evasion threat) are the three candidates; venue fix [23]→IEEE [28] applies regardless. Preprints [62]/[71], dataset-only [66]/[67], low-weight [72], certified-supervised [70], XAI-attack [73] stay in the full list only.
