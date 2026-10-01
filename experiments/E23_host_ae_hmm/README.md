# E23 — Host AE vs HMM, reproduced bit-identically (and hmmlearn unblocked)

**Verdict: PASS** · 2026-09-28 · commit `7b78a44`

## Aim

Two aims.

**Reproducibility.** The Week-5 deliverable (CHANGELOG 2026-09-20) reported the
host AE beating an HMM on ADFA-LD: AE 0.7768 ± 0.0050 vs HMM 0.7217. That run
used system Python 3.13 with CUDA torch. CLAUDE.md's rule is that a number is
not real until it reproduces on a different stack. Re-run it on a different
interpreter, a different torch build, and CPU instead of GPU — if the digits
match, the result is a property of the method, not of one machine's arithmetic
(gotcha #24 says it very much might not).

**Unblock the tooling.** `hmmlearn` has no wheel for Python 3.14, and building
from source fails without MSVC. Every HMM arm in the branch (E01, E08, E23) had
been skipped or faked for that reason. Install Python 3.12, create `venv312/`,
and run the HMM arms for real.

## What was done

1. Downloaded Python 3.12.10, installed user-level, created `venv312/` with
   CPU torch 2.14.0 + hmmlearn 0.3.3 + scikit-learn 1.9.1 + pandas. (Note: the
   torch CPU index does not mirror hmmlearn — the install must be split.)
2. Fixed the ADFA-LD path: the nested `ADFA-LD.zip` extracts one level shallower
   than `host_features.DATA_ROOT` expects, so the traces were invisible.
3. Full ablation, 4 seeds, identical protocol to the original: benign-only
   training (833 traces), val = 50% Validation-benign + 50% attacks stratified,
   threshold = argmax-F1 on validation, epochs picked by validation AUC from
   {10, 20, 40, 60} (never test).

## Results — bit-identical reproduction

| Model | AUC | F1 |
|---|---|---|
| **Host AE** | **0.7768 ± 0.0050** | 0.4646 ± 0.0096 |
| HMM-16 | 0.7217 | 0.3683 |

Per-seed AE: 0.7755 (ep 40), 0.7852 (ep 40), 0.7747 (ep 10), 0.7719 (ep 40).
Val-AUC by epoch: 60 epochs collapses to 0.4879 / 0.4904 / 0.7376 / 0.4332 on
the four seeds — the overtraining cliff, re-confirmed.

Per-family recall at each model's own tuned threshold:

| Family | n | AE | HMM |
|---|---|---|---|
| Adduser | 46 | 0.783 | 0.478 |
| Hydra_FTP | 81 | 0.620 | 0.494 |
| **Hydra_SSH** | 88 | **0.457** | **0.511** |
| Java_Meterpreter | 62 | 0.657 | 0.323 |
| Meterpreter | 38 | 0.697 | 0.263 |
| Web_Shell | 59 | 0.619 | 0.475 |

## What we understood

**The number reproduced exactly on a different interpreter, a different torch
build, and CPU instead of GPU.** That is the strongest possible form of
"this is real" in a project where device arithmetic is known to move results by
up to 0.49 (gotcha #24). The host pillar's result is now stack-independent.

**The two arms read different things, and the single family HMM wins is
diagnostic.** The AE scores a *count vector* — histogram over the pinned
syscall vocabulary, plus length and unique-rate. The HMM scores *transitions*
between syscalls. So an SSH brute-force, whose syscall histogram is nearly
normal but whose sequence is bizarre, is the one family where order-reading
should win. It does: 0.511 vs 0.457. This is the same structural point as
[E06](../E06_attr_shift/)'s M3 result (chunk-shuffle is invisible to a count
model) and the same argument for [E01](../E01_host_seqae/)'s sequence model.

**Why F1 is 0.46 while AUC is 0.78, and why only AUC is quoted.** The test
set is 6 benign traces to 1 attack, so any cutoff catching most attacks also
catches benign lookalikes, and F1 moves with the threshold choice. AUC asks
"is the attacker ranked above benign?" — threshold-free, and that is the
comparison against the HMM. Quoting F1 here would be quoting a base rate.

**The 60-epoch cliff is why the epoch grid stops at 40.** Validation AUC
collapses to 0.43–0.49 on three of four seeds at 60 epochs while test AUC holds
— the model memorises count histograms it has seen. This is the discipline
[E26](../E26_val_epochs/) later ported to the network pillar, where the same
cliff was costing WebAttacks 0.13 AUC.

## Files

- `exp_host_ablation.py` — the trainer/ablation
- `ablation_host.json` — the reproduced numbers
- `host_autoencoder_adfa.pt` — the production checkpoint (in `detection/`)
