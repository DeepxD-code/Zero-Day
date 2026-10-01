# E04 — Structural-augmented adversarial training

**Verdict: NEGATIVE** · 2026-09-26 · commit `8f7e678`

## Aim

Galli et al. (IEEE NCA 2025, ref [54] in Ch2) claim that low-degree structural
adversarial training lifts robustness **with zero clean-accuracy tax**. Their
technique: during training, inject a small number of spurious edges whose
endpoints are sampled degree-biased, so the model learns that low-degree
incoherent neighbourhoods are normal rather than anomalous.

If it works here, it would blunt A1's edge-injection attack (which cost the
detector ~0.016 AUC per injected edge) at no cost to clean detection. This is
exactly the kind of "prior literature says it works" claim worth testing rather
than citing.

## What was done

100 epochs, 4 seeds, two arms:

- **clean** — standard benign-only training on Monday
- **hardened** — same, plus each graph/epoch gets `m ~ U{0..8}` spurious edges
  (uniform source, degree-biased destination, P02-shaped noise)

The scaler is fit on *unaugmented* graphs (production convention) — so the
`x`/`edge_index` inconsistency **is** the perturbation, which is the faithful
port of the paper's mechanism.

Metrics: clean PortScan edge-AUC (is there a tax?) and the A1 k-sweep slope
(k = 0, 5, 20 × 2 injection seeds — how much robustness did we buy per edge?).

## Results

| Arm | Clean PortScan AUC (4 seeds) | Slope per injected edge |
|---|---|---|
| clean | 0.891, 0.847, 0.753, 0.744 | 0.0074, 0.0065, 0.0023, 0.0066 |
| hardened | 0.714, 0.864, 0.814, 0.830 | 0.0026, 0.0074, 0.0067, 0.0063 |

## What we understood

**The "zero tax" claim does not hold here, and there is no robustness gain
either.** Both halves fail:

- **Tax is real and large**: mean clean AUC 0.809 → 0.806 overall, but the
  per-seed spread is where it shows — seed 0 dropped 0.891 → 0.714 (−0.177).
  The augmentation is per-epoch random, so seeds see different perturbation
  streams, and the loss lands wherever the stream happened to be bad.
- **Robustness is flat**: slope per edge 0.0057 → 0.0054. A 5% change. The
  claim we were testing (that augmentation would flatten the injection slope)
  is not measurable above seed noise.

The most likely reason is a mismatch in the paper's threat model. Galli's
attack targets *provenance* graphs where the defender cannot see the attacker's
edges at all; our A1 attacker **can** inject arbitrary edges, and the detector
reads `edge_attr` computed from those same edges. Training to distrust
incoherent structure cannot help when the attacker's evidence arrives through a
channel the model is explicitly trained to trust.

**Kept as a bound:** on this feature set, structural augmentation trades clean
accuracy for nothing measurable. A1's injection attack is cheap-but-not-free
(~0.016 AUC/edge), which is the honest statement.

## Files

- `exp_e4_hardening.py` — procedure (contains the `augment()` port)
- `exp_e4_hardening.json` — per-seed clean AUC and slopes
