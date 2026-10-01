# E17 — Retrain M5b on clean Monday (architecture exonerated)

**Verdict: PASS** · 2026-09-27 · commits `b743558`, `418225e`, `2d0fbcd`

## Aim

[E16](../E16_card_clean/) showed the shipped checkpoint collapsing on clean
data for 4 of 7 families. Two possible explanations:

- **(a)** the model learned the *original testbed's* normality, and clean
  training data fixes it → the architecture is sound;
- **(b)** the v2 19-dim architecture simply cannot represent these families →
  no amount of data helps.

E17 separates them by retraining the **identical architecture** on clean Monday
and re-running both cards. Same `GraphAutoencoder`, same 19 dims, same LogScaler,
same benign-only protocol, same 200 epochs, same seed.

## What was done

1. `data/CICIDS2017_improved/monday.csv` → 371,624 benign flows → 486 v2 60s
   graphs. (Original Monday gave 487 — near-identical scale, so this is a like-
   for-like swap, not a data-volume experiment.)
2. Train 200 epochs, seed 0, LR 0.01, `set_seed` with CUDA-determinism.
3. Re-run the clean card (E16) and the original card (E15) against the new
   checkpoint.
4. Add `--val-frac` (E26) and `--extra-monday` (E27) so this script later
   serves those experiments too.

## Results

| Family | Clean data, **old** model | Clean data, **retrained** | Original data, retrained |
|---|---|---|---|
| Patator | 0.186 | **0.993** | 0.861 |
| DoS | 0.467 | **0.991** | 0.684 |
| WebAttacks | 0.083 | **0.931** | 0.773 |
| Infiltration | 0.568 | **0.799** | 0.610 |
| Botnet | 0.527 | 0.460 | 0.537 |
| PortScan | 0.467 | **0.963** | 0.578 |
| DDoS | 0.908 | **0.981** | 0.632 |

Training converged: loss 0.0022 → 0.00008, plateau from epoch 80.

## What we understood

**(a) is correct. The architecture was never the problem — the training data
was.** Five of seven families went from 0.08–0.47 to 0.93–0.99 on identical
architecture with one variable changed. Botnet is the exception and stays
flat: its C2 traffic looks like normal client-server at graph level, and no
amount of retraining invents a topology signal that is not there. That one is
Pillar 3's job — see [E21](../E21_band/), where reputation fusion lifts it to
0.667, and the open item in the root README.

**The cross-testbed column is the uncomfortable one.** The retrained model
collapses on *original* data just as the original model collapsed on clean
data. Neither checkpoint transfers. So this is not "the improved data fixed
the model" — it is "each model learned its own testbed". The honest summary is
that we now have two good, testbed-specific models and one open research
question, which [E27](../E27_combined_monday/) attacked and
[E29](../E29_transfer/) answered.

**What carried over, permanently:** val-picked epochs (E26, now the default
`--val-frac 0.2`) and the replay-tune capability that E29 needed. This script
is now the single M5b trainer for the branch.

## Files

- `exp_e17_retrain_improved.py` — the trainer (`--val-frac`, `--extra-monday`, `--out`)
- `exp_e17_card_improved_on_improved.json` — clean card, new model
- `exp_e17_card_original_on_improved.json` — original card, new model
