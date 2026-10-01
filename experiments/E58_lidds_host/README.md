# E58 — First LID-DS 2021 host-pillar result

> ## ⚠️ SUPERSEDED — absolute numbers are contaminated
>
> This experiment scored **whole traces**, and on LID-DS trace length is a
> near-perfect label proxy. Measured in
> [E60](../E60_lidds_lengthblind/): **length alone, inverted, gives AUC 0.8150 on
> this very corpus — higher than either arm reported here** (seq-AE 0.7709,
> count-AE 0.7226).
>
> The seq-AE-beats-count-AE *conclusion* survives and is larger under a
> length-blind protocol (+0.115, z = 17.5). **The absolute AUCs and the F1 = 0.0000
> finding below are contaminated and must not be quoted.**

**Verdict: SUPERSEDED by [E60](../E60_lidds_lengthblind/)** — was PASS
(seq-AE +0.0483, 2.19 SD) on a contaminated protocol. · 2026-10-01

## Aim

LID-DS 2021 unblocks the host pillar's third corpus. [E01](../E01_host_seqae/)
found the count vector→sequence change worth **+0.058 (11.9 SD)** on ADFA-LD and
fixed its M3 reorder blind spot (0.545 → 0.832). **The open question is whether
that replicates** on a different attack family, a different capture method, and
traces 10× longer.

## The corpus

Downloaded `CVE-2014-0160` (392 MB), extracted 1,148 `.sc` syscall traces
(skipping `.pcap`), loaded by `detection/lid_ds_loader.py`.

| | |
|---|---|
| Benign train / val | 210 / 60 |
| Test | 878 (758 benign + 120 attack) |
| Vocab (pinned from train) | 38 |
| Trace length | min 112, **median 3,142**, max 9,727 |

Labels come from each recording's JSON sidecar (`exploit: true|false`,
container roles) — 1,148/1,148, zero path fallbacks.

**The training set is small (210) and that is a real limitation.** In a
single-CVE extract most benign recordings sit under `test/normal/` and are
correctly held out. A split bug that swept those 758 into training was found
and fixed first; the honest corpus is the small one.

## Results — 4 seeds, epochs picked per seed, one-class benign-quantile threshold

| Arm | AUC | F1 |
|---|---|---|
| **seq-AE** | **0.7709 ± 0.0114** | 0.3743 ± 0.0820 |
| count-AE | 0.7226 ± 0.0291 | 0.0000 ± 0.0000 |

**Δ = +0.0483, pooled SD 0.0221, z = +2.19 → separated.** Epochs picked: 20/20
(interior), and 40/40/80 for the count-AE.

## What we understood

**E01's representation finding replicates across corpora.** +0.058 on ADFA,
**+0.0483 on LID-DS** — same direction, similar magnitude, 2.19 SD, on an
entirely different attack family, a different recording framework, and traces
**10× longer** (median 3,142 vs 296 syscalls). That is the strongest form of this
claim available: it is not an ADFA artefact. A different dataset, a different
capture, the same sign and a similar size.

**The count-AE's F1 of exactly 0.0000 is real, and worth stating precisely.**
It is not a bug. Thresholds were 0.295–0.321 (count-AE) against 0.813–0.966
(seq-AE). An AUC of 0.723 means the count-AE's attack scores *do* rank above
benign overall — but none of the 120 attacks clears the 90th percentile of
validation benign. So at a **10% false-positive operating point the count-AE
detects zero of 120 attacks on LID-DS, while the seq-AE detects 25–43%.**

**Caveat that keeps this from being "the count vector cannot detect anything":**
F1 at one fixed operating point is not a capability measure. A lower threshold
would trade false positives for detection and the count-AE would find some. The
AUC comparison — which is threshold-free — is the load-bearing result, and it is
separated. The F1 column shows the *operational* gap at a fixed FPR, and it is
large.

**The longer traces did not rescue the count representation.** One plausible
hope was that with 3,142-syscall traces there is far more sequence information
available, so a better representation should pay more. It paid slightly less
(+0.048 vs +0.058). That is weak evidence against "the count vector was merely
starved of data" as the explanation for E01's result — the gap is about what a
histogram can represent at all, not how much it is given.

## Limitations

- **210 training traces.** Small. The seq-AE picked epoch 20 on all four seeds,
  which is early — consistent with fast saturation on little data, and it means
  the count could plausibly improve with a larger training split. A
  multi-CVE extract would test that properly.
- **One attack family** (heartbleed). No per-family breakdown is possible.
- **F1 at a single 10% FPR operating point**, as above.

## Files

- `exp_e58_lidds_host.py` / `.json`
- Loader: `../../detection/lid_ds_loader.py`
- Data: `data/practice/LID-DS_SyscallRecords/` (gitignored)
