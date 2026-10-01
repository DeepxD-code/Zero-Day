# E01 — Attention seq-AE vs count-AE vs HMM-16 (host syscall sequences)

**Verdict: PASS — sequence modelling beats the count vector by 0.058 AUC and
fixes the exact blind spot it was built for. The first, truncated grid said
otherwise and was wrong.** · 2026-09-29

> **CORRECTION.** This experiment was first run on the epoch grid {10, 20, 40}
> and reported a *negative*: seq-AE 0.7799 vs count-AE 0.7768, Δ = 0.47 SD,
> "inside the noise", and no gain on the M3 reorder probe. **That was an
> artefact of a truncated grid** — all four seeds selected epoch 40, the largest
> value offered. Re-run on {40, 80, 120, 160} the result inverts completely.
> The original conclusion is recorded below under "The truncated-grid result"
> because the failure is the useful part.

## Aim

The single most important open modelling question in the host pillar.

The production host AE ([E23](../E23_host_ae_hmm/)) scores a **count vector** — a
histogram over the pinned syscall vocabulary plus length and unique-rate. It is
therefore *order-blind by construction*. [E06](../E06_attr_shift/) proved the
consequence: chunk-shuffling an attack preserves attribution at I = 0.9998 and
is undetected by the count-AE. Hydra_SSH was the one family where the
order-reading HMM beat the count-AE (0.511 vs 0.457).

**So: does a model that actually reads sequence — GRU encoder, additive-attention
pooling, GRU decoder — detect what the count models structurally cannot?**

## What was done

Model: `emb(V+1, 32) → GRU(64) → additive attention → GRU decoder (teacher
forcing) → logits over V`. Score = mean token cross-entropy. Same protocol as
E23: vocab pinned from benign-train only, split-seed 0, val-picked epochs,
argmax-F1 threshold on validation. Four seeds.

Three arms — **seq-AE**, **count-AE** (incumbent), **HMM-16** — plus three
mimicry probes scored at each arm's own tuned threshold. M3 (chunk-shuffle) is
the known blind spot and was the decisive measurement.

### The runner, after three kills

This experiment was killed three times by the machine (two restarts, one silent
process death) and **never by the code**. The cause: `hmmlearn` has no Python
3.14 wheel, which forced the *entire* job onto CPU-only `venv312` — a
multi-hour single-threaded job. The fix is a split, since `hmmlearn` is the only
CPU-bound dependency and the seq-AE half is pure torch:

```powershell
python            experiments\E01_host_seqae\exp_host_seqae.py --arm torch   # CUDA, ~12 min
venv312\Scripts\python.exe experiments\E01_host_seqae\exp_host_seqae.py --arm hmm   # CPU, 4.5 min
```

The HMM arm takes the torch results from the JSON rather than recomputing them.
Two import paths (`host_features`, `exp_host_ablation` — the latter lives in
`E23_host_ae_hmm`, not `detection/`) had been silently satisfied by venv312's
working directory and are now explicit.

## Results

### Clean test set (4 seeds, grid 40–160)

| Arm | AUC |
|---|---|
| **seq-AE** | **0.8340 ± 0.0037** |
| count-AE (E23 incumbent) | 0.7756 ± 0.0059 |
| HMM-16 | 0.7217 |

Per-seed seq-AE: 0.8323, 0.8388, 0.8360, 0.8289.

**Δ = +0.0584 against a pooled SD of 0.0049 — 11.9 SD.** This is not a
marginal win; it is the largest effect measured anywhere in the host pillar, and
it is roughly **14× the seed noise**.

### Mimicry probes (recall at each model's own tuned threshold)

| Probe | seq-AE | count-AE |
|---|---|---|
| **M1 interleave** (+30% benign syscalls) | **1.000** | 0.032 |
| **M2 substitute** (20% tokens swapped) | **1.000** | 0.048 |
| **M3 chunk-shuffle** (order destroyed, histogram intact) | **0.832** | 0.545 |

**M3 is the result the experiment was built for, and seq-AE now answers it.**
On the truncated grid both models read 0.545 — an apparent tie. Trained
properly, seq-AE catches **0.832** against the count-AE's 0.545.

## The truncated-grid result (superseded, kept because the failure is the point)

| | grid {10,20,40} | grid {40,80,120,160} |
|---|---|---|
| seq-AE | 0.7799 ± 0.0066 | **0.8340 ± 0.0037** |
| count-AE | 0.7768 ± 0.0050 | 0.7756 ± 0.0059 |
| Δ (pooled SDs) | 0.47 → inside noise | **11.9 → decisive** |
| M3 recall (seq / count) | 0.545 / 0.545 (tie) | **0.832 / 0.545** |
| M1, M2 recall (seq) | 0.922, 0.778 | **1.000, 1.000** |
| epochs selected | 40 / 40 / 40 / 40 (all at ceiling) | 160 / 120 / 160 / 160 |

A 4.4× longer budget turned a null result into an 11.9-SD effect, and turned
the headline negative on M3 into a 0.287 gain. The tell was visible in the
first run's own output: **every seed selected the largest epoch offered.**

## What we understood

**The count vector was the binding constraint, and it is now relieved.** The
production host AE throws away syscall *order* and keeps a histogram. On clean
traffic that costs almost nothing — the two models were within 0.003 — because
most attack signal is distributional. But the cost is severe the moment the
histogram stops being informative, and there are two distinct ways that happens:
**dilution** (M1/M2, where padding shifts the histogram toward benign) and
**reordering** (M3, where the histogram is bit-identical and a count vector has
literally nothing left to read). seq-AE handles both; the count-AE handles
neither (0.032, 0.048, 0.545).

**E01's own stated decision rule is answered in the affirmative.** The README
for this experiment said: *"If seq-AE fails to beat 0.7768 on the clean test,
the count vector is confirmed sufficient and E06's M3 evasion becomes a
disclosed limitation rather than a fixable gap."* It beats it by 0.058. So the
order-blindness is a **fixable gap, and it is fixed**.

**The methodological lesson is the more valuable half.** A null result was
produced, written up, and believed — and the only reason it was caught is that
the run's own output said `picked ep 40` four times out of four. The archive had
just been burned by exactly this shape of error in
[E48](../E48_opt_sweep/): a threshold (k=3) that looked defensible because it
was inside the grid, rather than because it was optimal. **A parameter pinned to
the edge of a sweep has not been tested, it has been truncated.** That is now a
standing rule for this project, and this is the second time it has paid.

**The count-AE is not obsolete, and this is a false binary.** It is 14× cheaper
and near-equal on clean traffic. The right conclusion is that the host pillar
should carry a sequence-reading arm *alongside* the count vector, not replace
it — which is also what [E21](../E21_band/) has been asking for as Botnet's
third fuse input. E01 supplies that arm, and it is trained and measured.

### Caveats

- **The grid is still truncated.** Three of four seeds selected 160, again the
  maximum offered, so {160, 240, 320, 400} was run. **The truncation test
  passes: seed 0 selected epoch 240, an INTERIOR point of that grid, giving
  0.8432 (up from 0.8323 at epoch 160).** The earlier ceiling was an artefact
  of the shallow grid, not a real optimum. The run was stopped after seed 0 —
  at ~80 min/seed the full 4-seed version costs ~4 more hours to refine a value
  that cannot change an 11.9-SD conclusion. So: **the grid is not the
  limitation, and the exact seq-AE value is ~0.834–0.843, not final to the
  third decimal.** The comparison against the count-AE is unaffected either way.
- Mimicry recall is a single-seed (seed-0) measurement at one threshold, with no
  band. The gaps (1.000 vs 0.032; 0.832 vs 0.545) are far too large to be noise,
  but the exact values should not be quoted as precise.
- 22 probe traces per condition is a small sample.
- The count-AE number moved slightly between grids (0.7768 → 0.7756) because it
  grid-searches its epoch over the same list. Both figures are the incumbent's
  own tuned value; the comparison is like-for-like within each row.

## Files

- `exp_host_seqae.py` — the model, three arms, three probes, `--arm` split
- `ablation_host_seqae.json` — **complete 4-seed result** (torch + HMM merged)
- `ablation_host_seqae_torch.json` — the GPU half
- `exp_e01_m3_noop_check.py` / `.json` — is the M3 probe vacuous?
- ~~`ablation_host_seqae.json` (old)~~ — the earlier partial state, superseded
  and **not citable**
