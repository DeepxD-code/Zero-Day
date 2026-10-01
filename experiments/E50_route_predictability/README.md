# E50 — Can the fusion rule route itself? (is best-`k` predictable without labels)

**Verdict: NEGATIVE — no label-free observable predicts the best `k`. Routing is
not implementable; tune per site instead.** · 2026-09-29

## Aim

[E48](../E48_opt_sweep/) found the best short-window depth `k` runs in opposite
directions across families — Botnet wants k=1, WebAttacks and Infiltration want
k=8. That is only a *design* problem for the deployment if the regime can be
identified **without knowing the attack**. If detecting the regime requires the
label you are trying to detect, routing is circular and "tune per site" is the
honest recommendation.

So the question is not "which family wants which k" — that is n=5 with 4
agreeing, far too weak to route on. It is:

> Is there an observable, computable at inference time with no labels, that
> predicts whether a short or a long window is currently the better judge?

## What was done

Seed 0. Each day cut into contiguous blocks of 40 windows. Within each block,
sweep `k` and record which one maximises AUC. Then test whether either
observable predicts the winner.

Two label-free candidates:

| Observable | Definition |
|---|---|
| **persistence** | median window-observations-so-far (`nwin`) of the top-decile-scoring edges in the block |
| **clustering** | distinct windows in the block's top decile ÷ window span — do high scores arrive in clumps? |

## Results — the best `k` genuinely moves within a family

| Family | best `k` per block |
|---|---|
| Botnet | 4, 1, 8, 1, 1, 4, 3, 1, 1, 1, 1, 4, 1 |
| PortScan | 8, 4, 8, 4, 8, 3, 1, 2, 3 |
| DDoS | 8, 4, 8, 4, 8, 3, 1, 2, 3 |
| Infiltration | 6, 6, 6, 8, 8, 3, 8, 4, 4, 8, 8, 2, 6 |
| WebAttacks | 4, 3, 6, 4, 1, 6, 8, 3, 8 |

**All six grid values appear, within single families.** Botnet alone flips
between 1 and 8. So the instability E48 saw across families is also present
*within* a family over time — the premise for routing is real.

### But nothing observable predicts it

| | |
|---|---|
| Blocks pooled | 53 |
| Distinct best-`k` values seen | 1, 2, 3, 4, 6, 8 |
| **corr(persistence, best `k`)** | **−0.2498** |
| **corr(clustering, best `k`)** | **+0.0009** |

**Neither observable gets close to predicting the winner.** Clustering is
essentially uncorrelated (r = 0.001). Persistence is weakly *negative* — higher
persistence goes with a *smaller* k, the opposite of the mechanism E48
proposed, and far too weak to act on.

## What we understood

**The instability is not signal, it is noise — and that is the finding.** With
53 blocks and a best-`k` that takes 6 distinct values, the obvious reading of a
table like this is a hidden regime that a smarter observable would reveal. The
correlation says otherwise: the per-block winner is close to unpredictable, so
most of that variation is *estimation noise on the block-level AUC*, not a
property of the attack that changes.

This matters because it kills the routing idea at its root. A routing rule
needs a decision variable. The two natural candidates — how long the flagged
hosts have persisted, and whether their scores clump — carry essentially no
information about which `k` will win. Building a router on either would be
fitting noise.

**So the honest recommendation is the one E48 already pointed to: tune `k` on
the deployment's own labelled traffic, and accept that a fixed `k` is a
compromise.** That is not a failure of the method — it is what E48's
leave-one-seed-out showed *works*: tuning on held-out data helps by up to 0.027
and never hurts. Routing was the elegant alternative; it is simply not
available.

**Caveats, since a negative result needs them stated carefully.** This is
**seed 0 only** — it is a feasibility probe for whether *any* observable works,
not a banded result, and 53 blocks is a small sample. A correlation of −0.25
could be masking a real but weak relationship that more seeds would resolve. The
verdict is "no observable *of this form* predicts it", not "no observable can".
And only two candidate observables were tried; a richer feature (score
autocorrelation across lags, say) is untested.

## Files

- `exp_e50_route_predictability.py`
- `exp_e50_route_predictability.json` — per-block `k`, AUCs, and both observables
