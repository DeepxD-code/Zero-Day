# Week 4 Task — Deep (Person B, Detection Modeling)
Scope: my commits only, 2026-08-25 to 2026-09-03 (previous week + this week).
Source: `git log --since="2026-08-20" --author="Deep"`.

## 1. Production recipe: revived-M5a + noisyor (the headline)
- `80e8699b` PROD: revived-M5a (87-dim ctx) + gnn-logscale fused by within-window rank noisyor is the default
- `5f3e55bd` Week-4 freeze: band confirms noisyor 0.9996+/-0.0001 (beats pure in 4/4)
- `f3190551` M5A REVIVED INTO PROD: ctx-features AE (87-dim) + rank_mean fusion with v2b = 7/7 wins, 4/4 seeds
- `9daece42` Prod rule finalized: rank_MAX(m5a_revived, v2b) — 7/7 no-regressions
- `2925813d` + `df8842bd` MW ablation gains revived-M5a arms (rev_multi / three_way_rev_rm / pure_noisyor_rev / pure_rmax_rev) — decisive comparison vs RC-26 headline
- `f809c181` MW ablation: --feature-set flag (v1/v2) + in_dim inference — enables production-combo confirmation runs
- What it means: old shipped M5a hurt fusion (0.9499). Revived ctx-M5a helps everywhere. Noisyor compares ranks, not raw scores. New headline 0.9996 ± 0.0001, v2 0.9997 ± 0.0001.
- Note: log-scale itself was Week 3 (Aug 12). Week 4 kept it as default, did not invent it.

## 2. Bands you can trust (multi-seed + externals)
- `a1479f1c` Overnight 4-seed x 60ep band reproduced: pure_rank_mean 0.9989+/-0.0006, v2 0.9997+/-0.0001
- `9e116462` Externals 4-seeded: IDS2018 top-11 (3/4 seeds), CTU Virut #1 all seeds, Rbot C&C #1 in 3/4
- `b2b7c0ab` Overnight run logs for 2026-08-25b/c
- `cb376840` Verification artifacts: baselines exact-match + full-file ablation on merged main
- `9164d1d5` Caveats closed: noisyor rule 7/7x4 (+0.028), EDGE fusion table, IDS2018 fusion replicates (best rank 5->2)
- What it means: nothing was seeded before Aug 11 (same code gave 0.8997 vs 0.9251). All Week 4 numbers are GPU + CUDA-deterministic mean ± std. No seed flips any conclusion.

## 3. v2 features → production default
- `115ff257` Formal checkpoints: v1 logscale (production) + v1 logscale v2 19-dim (opt-in) — seed 0, Monday full, 200ep
- `ca25e890` train(): infer in_dim from graphs — fixes v2 training crash
- `f9a52390` Dimension guard: score_window(feature_set='v2') refuses loudly without 19-dim checkpoint
- `c7a5bbd3` + `a761ad94` CHANGELOG 2026-08-25f/c entries + CLAUDE.md refresh, gnn_model --feature-set/--out/--seed flags
- What it means: v2 = 19 host dims (indices 0-7 same as v1). Dimension mismatch now errors loudly instead of crashing on scaler.

## 4. Clean slate: legacy quarantine + loud failures
- `621f7e1a` Week-4 clean slate: legacy M5a quarantined to legacy/, missing revived checkpoint now hard-fails, v2 is production, PAPER_OUTLINE.md
- `ea75f8b8` CLAUDE.md: stub_detector marked as shim to legacy/
- `cd420f59` Clean detection/: stale impls -> legacy/, exp_*.py -> experiments/, v2+noisyor is single source of truth
- What it means: prod surface = live code only. Every emitted alert is guaranteed fused. No silent stale model_source.

## 5. Docs + schema (so C/D don't guess)
- `3139ddfd` schemas: feature_vector.json v2.0 -> v3.0 (76 -> 87 dims, flow + ctx window)
- `5e86eee8` docs: detection/training_features/README.md — frozen 87-dim flow + 8/19 host catalogue
- `f7135769` docs: training_features README — v2-only production catalogue
- `f67747e0` Remove synthetic training_data/ (collapsed graphs) + document data/ — training vs held-out vs external vs results
- What it means: source of truth is code, doc is mirror. A's synthetic 10k set can't form graphs (documented, removed from training path).

## 6. Pillar 3 start (Week 4, early)
- `0f2993d7` detection: host AE skeleton (Pillar 3, Week 4) — reuses AE plumbing, no Checkpoint-1 touch
- What it means: placeholder for eBPF host-syscall autoencoder. Does not affect Pillar 1 production.

## How to verify
```powershell
git log --since="2026-08-25" --until="2026-09-04" --author="Deep" --oneline
git show 80e8699b --stat
git show 621f7e1a --stat
```
