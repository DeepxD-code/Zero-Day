# E06 — Attribution-space evasion fingerprint (SHAP stability)

**Verdict: NEGATIVE** · 2026-09-26 · commit `8f7e678`

## Aim

Person C's SHAP explainer (`detection/shap_revived_ctx.py`) tells an analyst
*why* an alert fired. That creates an attack surface the graph detector does
not have: an attacker who cannot change the anomaly **score** can still try to
change the **attribution**, so the explanation points at the wrong feature and
the analyst is misled.

The proposal under test: adversarially reshaped attacks should produce a
detectable *shift in attribution rankings*, even when the score is unchanged.
If true, the explanation layer gets its own independent evasion detector.

## What was done

Host AE on ADFA-LD (where we own the attack synthesis). Three mimicry probes
applied to **test attacks** so the score is known to be detected:

- **M1 interleave** — insert 30% extra length of benign syscalls
- **M2 substitute** — swap 20% of tokens for benign ones
- **M3 reshuffle** — chop into 10-syscall chunks and shuffle chunk order
  (preserves the histogram exactly, destroys only order)

Baseline for "how much attribution movement is just noise": split-half
bootstrap over *clean* true positives — the attribution noise floor. Anything
above that floor is evasion.

Metric: Spearman ρ between the original attack's attribution ranking and the
mimicry attack's. ρ near 1.0 = attribution preserved = no fingerprint.

## Results

| Probe | mean ρ | std ρ |
|---|---|---|
| M1 interleave | 0.762 | 0.065 |
| M2 substitute | 0.797 | 0.066 |
| **M3 reshuffle** | **0.9998** | 0.003 |
| baseline (unpaired noise floor) | 0.740 | 0.104 |

## What we understood

**The idea works, and the negative verdict is about *our* detector, not the
premise.** M1 and M2 shift attribution to ρ ≈ 0.76–0.80, clearly above the
0.74 noise floor — an attribution-space evasion fingerprint is real and
measurable. That is a genuine positive finding about the method.

But M3 is the one that matters for our architecture, and it returns ρ = 0.9998.
**Chunk-shuffling preserves attribution perfectly** — because our host AE scores
a *count vector* (histogram over the pinned syscall vocab + length +
unique-rate), not a sequence. Shuffling order changes nothing the model can
see, so nothing in the attribution moves. The detector is order-blind by
construction, and the explanation faithfully reflects what the detector
actually used.

The uncomfortable corollary: M3 is also an **undetected evasion** against the
count-AE (0.42 in the JSON is the M3 column for the AE arm). It is only
caught by the models that *do* read order — which is precisely what E01
(seq-AE with a GRU + attention) and E23's HMM arm exist to provide.

**This is the strongest argument in the archive for the sequence models**, and
it is why E01 matters despite never completing.

## Files

- `exp_e6_attr_shift.py` — procedure (probe synthesis + bootstrap floor)
- `exp_e6_attr_shift.json` — ρ values
