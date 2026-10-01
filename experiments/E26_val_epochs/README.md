# E26 — Val-picked epochs for M5b (fixes WebAttacks undertraining)

**Verdict: PASS** · 2026-09-28 · commit `07f475a`, band in `4ab2313`

## Aim

[E21](../E21_band/) found the cause of WebAttacks' 0.813 ± 0.091 band: seeds
2 and 3 converged to **2× worse final loss** at the fixed 200-epoch budget
(0.000184, 0.000188 versus 0.000084, 0.000081). Fixed-epoch training rewards
lucky starts.

The host pillar had solved this exact problem two weeks earlier and *told us*:
[E23](../E23_host_ae_hmm/)'s 60-epoch cliff (val AUC collapsing to 0.43–0.49
while test AUC held) is why the host trainer picks epochs from {10, 20, 40} on
validation. M5b had no such discipline — it just ran 200 epochs and kept
whatever fell out. This ports the host discipline to the network pillar.

## What was done

Added `--val-frac` to `experiments/E17_retrain_improved/exp_e17_retrain_improved.py`:

- Hold out the **last 20% of Monday windows** as validation, time-ordered so
  there is no shuffle leak
- Track validation loss each epoch, keep the best state
- Budget raised 200 → 400 epochs, because the val optimum may sit later
- **`--val-frac` now defaults to 0.2** (was 0.0) — this is now the default
  training protocol, not an opt-in

Retrained seeds 2 and 3 (seeds 0 and 1 followed in the band run), then scored
WebAttacks fixed-vs-val-picked head to head, then the full 4-seed band.

## Results — fixed-200 vs val-picked

| Seed | Fixed 200 ep | **Val-picked** | Best epoch | Val loss |
|---|---|---|---|---|
| 0 | 0.931 | **0.9195** | 215 | 0.000048 |
| 1 | 0.849 | **0.8765** | **17** | 0.000050 |
| 2 | 0.790 | **0.9130** | 78 | 0.000041 |
| 3 | 0.682 | **0.8906** | 77 | 0.000034 |

**Band: 0.813 ± 0.091 → 0.900 ± 0.017.** The seed-3 tail (0.68) is closed.

## What we understood

**Seed 1's best epoch is 17.** That single number is the whole argument. At a
fixed 200 epochs, seed 1 was graded on its epoch-200 husk — 199 epochs of
overtraining past its own best moment. Val-picking evaluates it at epoch 17 and
recovers 0.028 AUC. The fixed budget was not just noisy; for some seeds it was
measuring a model that had already overfit.

**Why the val optimum is so early (17–215, mostly 77–78):** the network
detector's benign training set is small (486 graphs from one quiet Monday) and
the model has a narrow bottleneck. It fits Monday quickly and then starts
memorising. That is a *data limitation*, not an architecture one — more benign
days (a full week, or several sites) is the real fix, and it is the same
underlying need as cross-testbed training in [E29](../E29_transfer/).

**The canary logic, which generalises.** The families with tight bands
(DDoS ±0.001, Infiltration ±0.012) did not care about undertraining because
their attacker signal is large relative to the model's error. The families
that flip are the marginal cases where the attacker's edge barely clears the
benign distribution — web attacks, 62 edges among 71,767 scan flows. **The
seed variance of a graph autoencoder is a canary for undertraining, and
marginal families are where you read it.**

**This is now policy, not a fix.** No checkpoint should ship without a
val-picked epoch. The training script defaults to it, and the old path
(`--val-frac 0`) is documented as legacy. The checkpoints `fixed200_s{0..3}.pt`
are kept in this folder precisely so the before/after comparison stays
reproducible.

## Files

- `exp_e26_val_epochs.json` — before/after per seed
- `fixed200_s{0,1,2,3}.pt` — the superseded fixed-epoch checkpoints (evidence)
- `../../detection/gnn_improved_s{0,1,2,3}.pt` — the val-picked band now served
- trainer: `../E17_retrain_improved/exp_e17_retrain_improved.py` (`--val-frac`)
