# E53 — Where we actually stand against published work

**Verdict: POSITIONING ANALYSIS. A defensible numeric comparison could not be
established, and the reason is the evaluation protocol, not the model.** · 2026-09-30

## The honest headline

**We do not currently win on headline accuracy, and any table claiming otherwise
would be built on a protocol mismatch.** This document states our numbers
exactly, explains why they cannot be placed next to published CIC-IDS2017
numbers, and specifies the experiment that would fix that.

## What our numbers actually are

| Setting | Number | Protocol |
|---|---|---|
| Host seq-AE (E01, 4 seeds) | **0.8340 ± 0.0037** | ADFA-LD, train benign only, val-picked |
| Host count-AE (E23 incumbent) | 0.7756 ± 0.0059 | same |
| Host HMM-16 | 0.7217 | same |
| Network fused (E43 band) | Botnet 0.709±0.025 · Web 0.950±0.008 · PortScan/DDoS 0.969±0.004 · Infiltration 0.668±0.028 | clean data, per-day, within-window rank |
| Network edge-level (E52) | PortScan/DDoS 0.961 · Infiltration 0.633 · Botnet 0.442 | same |

**Our weakest headline is edge-level Botnet at 0.442 — chance.** Our strongest is
WebAttacks fused at 0.950. The spread across families is larger than the gap to
any published baseline, which is itself the finding.

## Why no comparison table appears here

**Published CIC-IDS2017 results are not measured on our protocol, and the
difference is not cosmetic.** Three specific, checkable mismatches:

1. **Same-day train and test.** A large share of the literature trains and
   evaluates on the *same* day-file. Monday-trained models tested on Monday
   attacks are not a detection result. This archive trains on **Monday benign
   only** and tests on **Tuesday–Friday**, so our numbers are strictly harder
   than a same-day figure and are not comparable to one.
2. **`- Attempted` handling.** Our protocol excludes `- Attempted` rows
   everywhere. Papers that retain them report on a different population; the
   archive has already been bitten by this class of mismatch twice (E11's
   5-positive slice, E45's encrypted-port count).
3. **Label set and granularity.** Most published tables report a single
   multiclass F1 over all attacks pooled. Ours is **per-family ROC-AUC, pooled
   only after within-window ranking**. F1 and AUC are not interchangeable, and
   a pooled multiclass F1 is not per-family AUC.

Lining those up would produce a number that looks like a comparison and is not
one. **That is the error this archive has made repeatedly in other forms
(E43's Botnet 0.723-vs-0.681, E48's label strings), so it is worth refusing
explicitly rather than quietly producing a table.**

## Where the defensible claim actually lies

Not "better accuracy". Two claims that survive scrutiny:

**1. The unsupervised setting is real and rarely held to the same rigour.**
Training benign-only and reporting per-family results on held-out days is a
stricter protocol than most of the 0.95+ literature uses — and that literature
is largely *supervised* (trained with attack labels), so it is not a
like-for-like category at all. On a strict-protocol comparison our absolute
numbers are respectable but not exceptional.

**2. The representation result is a genuine contribution independent of the
headline.** E01's count-vector → sequence-AE change bought **+0.058 AUC
(11.9 SD)** with **zero added capacity**, and moved the M3 reorder probe
**0.545 → 0.832**. That is a statement about what the features can express, not
about who tops a table. E52 then showed the *same lesson holds in reverse* at
the edge layer: the aggregator is not the bottleneck, the node representation
is. Two independent experiments, one principle — **the representation is the
constraint, not the readout.** That principle is portable and is the thing
worth writing up.

## The experiment that would make this defensible

Not a literature table. A **head-to-head reimplementation under one protocol**:

- Take 2–3 published unsupervised baselines (AE, VAE, and one graph-based
  method — the AlignAD-VAE and masked-context-reconstruction lines are the
  current unsupervised references)
- Reimplement them on **our** data with **our** E16 protocol: Monday benign
  only, per-day files, `- Attempted` excluded, within-window rank → pool
- Report per-family AUC with 4-seed bands
- **The comparison is only valid if every arm uses the identical split.** That
  is the entire point, and it is why the numbers can be trusted.

**Predicted outcome, stated in advance so it can be falsified:** our graph arm
loses to a well-tuned VAE on the saturated families (PortScan/DDoS, where
everything reaches ~0.96) and the seq-AE arm wins on the families nobody else
reports separately. If a VAE beats us broadly, the honest conclusion is that
our architecture is not the contribution — the protocol rigour and the
representation finding are.

## What I could not do

I did not find a citable, protocol-matched benchmark table, and I have not
constructed one from numbers I could not verify. **Any "we beat published
SOTA" claim in this document would be unfounded, and its absence is the
finding.**

## Files

- This document. No numbers from external papers are quoted, because none could
  be matched to this protocol.
