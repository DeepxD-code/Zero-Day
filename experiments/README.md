# Experiments — the Zero-Day evidence archive

## What this folder is

This folder is the **evidence layer** of the Zero-Day FYP. Everything in
`detection/` is the product: the code that actually runs and emits alerts.
Everything here is the *record of how we know it works* — the experiment
scripts, the raw result JSONs, the rejected attempts, and the reasoning
behind each decision.

The rule that separates them:

- **`detection/`** ships. If it is imported by `alert_pipeline.py`, it is product.
- **`experiments/`** records. If nothing in production imports it, it is evidence.

Nothing here is required to run the detector. The whole folder can be deleted
without breaking a single alert — but you could not defend a single number in
the report without it.

### Why this structure exists

Before this folder existed, experiment scripts lived inside `detection/`
alongside production modules, and results were scattered flat across the repo
root, `detection/`, and `experiments/`. Three consequences:

1. **Failed experiments were deleted.** Three separate transfer attempts
   (combined training, dual-checkpoint ensemble, plain fine-tune) were tried,
   measured, and thrown away. That history is the most valuable part — it is
   what stops the next person re-running the same dead ends.
2. **Checkpoints were ambiguous.** Fourteen `.pt` files with names like
   `gnn_improved_s0_val.pt` and `gnn_replay_orig20.pt`, with no way to tell
   which was live.
3. **Results were unrepeatable.** A JSON on disk with no script beside it is a
   claim, not a measurement.

Every experiment now lives in one numbered folder with its script, its
results, and a README that explains what was attempted, what happened, and
what it changed. **Failures are kept, labelled `NEGATIVE`.** A negative result
is worth more than a missing one.

### How to read this archive

1. Start with the **table of contents** below — it gives you the number, the
   name, the verdict, and the date for everything.
2. Jump to the experiment's folder. Its `README.md` answers: what was the aim,
   what was done, what was found, what we understood from it, why this
   specific number (3 seeds? 4? 40 epochs?), and which files matter.
3. The script is the procedure. The JSON is the raw output. Both are committed,
   so any number can be regenerated rather than trusted.

### Conventions used in this archive

| Label | Meaning |
|---|---|
| **PASS** | Hypothesis held. Adopted into production or confirmed a claim. |
| **NEGATIVE** | Hypothesis tested and rejected. Kept so nobody repeats it. |
| **PARTIAL** | Partly worked; the limit is documented and the open part named. |
| **CONTROL** | Establishes a baseline or bounds a claim. Not a candidate change. |
| **BUG** | Found a defect in our own method or measurement. Fixed here. |
| **INCOMPLETE** | Started, not finished. The obstacle is recorded, not hidden. |

| Numeric convention | Why |
|---|---|
| Every headline carries a **4-seed band** | Two identical unseeded runs once gave 0.8997 and 0.9251 (CLAUDE.md gotcha #11). Single seeds lie. |
| Every AUC carries a **95% CI** | A 5-positive slice gave AUC 0.89 with CI 0.71–1.00. Point estimates on thin slices are noise with decimals. |
| **Device + torch build** recorded | The same seed gave WebAttacks 0.5048 on CPU and 0.9948 on GPU (gotcha #24). |
| **Attempted attacks excluded** on clean data | The CNS2022 release splits `- Attempted` attacks out. Counting them as real attacks is the pollution E15/E16 exposed. |

### Environment note

- `hmmlearn` (used by E01, E08, E23) has no wheel for Python 3.14. It is
  installed in `venv312/` (gitignored). Run those with
  `venv312\Scripts\python.exe -u experiments/...`.
- Everything else runs on the system Python with CUDA.

---

## Table of contents

### Pillar 1 — network flow (M5a / M5b / M5c)

| # | Experiment | Verdict | Date | Files | Commit |
|---|---|---|---|---|---|
| [E02](E02_edge_fusion/) | Edge-level fusion reproduction (RC-20) | CONTROL | 2026-09-26 | script, 3 JSON | `7fe9d5b` |
| [E10](E10_graphids_port/) | GraphIDS port vs SAGE-MLP, held-out protocol | CONTROL | 2026-09-26 | script, JSON | `77e3afe` |
| [E11](E11_tls_split/) | Encrypted-traffic (port 443) ablation | BUG | 2026-09-26 | script, JSON | `a9cb8c3` |
| [E12](E12_slowdrip/) | Slow-drip timing evasion vs M5b | NEGATIVE | 2026-09-26 | script, JSON | `ba286ca` |
| [E13](E13_tls_fix/) | Port-conditioned TLS fix + multi-window | PASS | 2026-09-26 | script, JSON | `c54490e`, `d51a9c3`, `cc557ec` |
| [E14](E14_risk_controls/) | R1/R2/R3 risk elimination in code | PASS | 2026-09-26 | 3 modules | `53d5dd3` |
| [E15](E15_card_original/) | 7-family report card, original data | CONTROL | 2026-09-27 | script, JSON | `8f8756c` |
| [E16](E16_card_clean/) | 7-family report card, clean data | PASS | 2026-09-27 | script, JSON | `b63783d`, `418225e`, `edd0746` |
| [E17](E17_retrain_improved/) | Retrain M5b on improved Monday | PASS | 2026-09-27 | script, 2 JSON | `b743558` |
| [E18](E18_retrain_m5a/) | Retrain revived M5a on improved Monday | PASS | 2026-09-27 | script | `3760ffa` |
| [E19](E19_fusion_botnet/) | Fusion rule shootout vs Botnet | PARTIAL | 2026-09-27 | JSON | `3760ffa` |
| [E20](E20_reputation_infil/) | Causal reputation vs single-window | PASS | 2026-09-27 | JSON | `a2be3f7` |
| [E21](E21_band/) | 4-seed band + fusion-rule shootout | PASS | 2026-09-27 | script, JSON, 3 ckpt | `fdc96cf` |
| [E22](E22_web_m5a/) | M5a-flow stability on WebAttacks | PASS | 2026-09-27 | JSON | `4e3a15f` |
| [E24](E24_dilate_reputation/) | Reputation vs slow-drip + Web fused band | PASS | 2026-09-27 | script, JSON | `0807a6f` |
| [E25](E25_ensemble/) | Seed-ensemble for Web | NEGATIVE | 2026-09-28 | script, JSON | `110fbd1` |
| [E26](E26_val_epochs/) | Val-picked epochs (E28 band) | PASS | 2026-09-28 | JSON, 4 ckpt | `07f475a` |
| [E27](E27_combined_monday/) | Combined-Monday training | NEGATIVE | 2026-09-28 | 2 JSON, ckpt | `a114d24` |
| [E28](E28_web_valband/) | Web band after val-epoch fix | PASS | 2026-09-28 | JSON | `4ab2313` |
| [E29](E29_transfer/) | Cross-testbed transfer (3 attempts) | PASS | 2026-09-28 | JSON, 2 ckpt | `74a6d64` |
| [E30](E30_edge_injection/) | Edge/node injection vs shipped M5b | CONTROL | 2026-09-26 | script, JSON | `53219eb`+ |

### Pillar 3 — host syscalls (ADFA-LD)

| # | Experiment | Verdict | Date | Files | Commit |
|---|---|---|---|---|---|
| [E01](E01_host_seqae/) | Attention seq-AE vs count-AE vs HMM — **adopted** | PASS | 2026-09-29 | script, 3 JSON | `85a1ebd` |
| [E03](E03_drift_mmd/) | Drift MMD statistic + detection delay | NEGATIVE | 2026-09-26 | script, JSON | `8f7e678` |
| [E04](E04_hardening/) | Structural-augmented adversarial training | NEGATIVE | 2026-09-26 | script, JSON | `8f7e678` |
| [E05](E05_dgi_warmstart/) | DGI contrastive warm-start | NEGATIVE | 2026-09-26 | script, JSON | `8f7e678` |
| [E06](E06_attr_shift/) | Attribution-space evasion fingerprint | NEGATIVE | 2026-09-26 | script, JSON | `8f7e678` |
| [E07](E07_cluster_denoise/) | Cluster denoise of the alert queue | NEGATIVE | 2026-09-26 | script, JSON | `8f7e678` |
| [E08](E08_diverse_fusion/) | Diverse-arm fusion (IF/PCA/AE/HMM) | NEGATIVE | 2026-09-26 | script, JSON | `99b1a77` |
| [E09](E09_drift_repin/) | Threshold re-pinning under drift | NEGATIVE | 2026-09-26 | script, JSON | `451a7b4` |
| [E23](E23_host_ae_hmm/) | Host AE vs HMM ablation, reproduced | PASS | 2026-09-28 | script, JSON | `7b78a44` |
| [E31](E31_fliptest/) | Top-k attribution flip test | NEGATIVE | 2026-09-26 | script, JSON | `53219eb`+ |
| [E32](E32_perfamily_thr/) | Per-family thresholds on host AE | NEGATIVE | 2026-09-26 | script, JSON | `53219eb`+ |

### Cross-cutting — methods, controls, and the pre-branch record

| # | Experiment | Verdict | Date | Files | Commit |
|---|---|---|---|---|---|
| [E02](E02_edge_fusion/) | Edge-level fusion reproduction (RC-20) | CONTROL | 2026-09-26 | script, 3 JSON | `7fe9d5b` |
| [E33](E33_baselines/) | PCA / IF / MLP-AE under identical conditions (RC-31) | CONTROL | 2026-08-21 | JSON, logs, script | `80675c5` |
| [E34](E34_external_repl/) | IDS2018 + CTU-13 external replication (RC-29/32) | PASS | 2026-08-21 | 4 JSON, logs, script | `9e11646` |
| [E35](E35_multiwindow/) | Multi-window 60s+300s fusion | PASS | 2026-08-20 | 2 JSON, 2 scripts, logs | `9af7e96` |
| [E36](E36_mw_ablation/) | Decisive multi-window ablation (RC-26) | PASS | 2026-08-25 | JSON, 6 logs, 4 scripts | `7220d47` |
| [E37](E37_p100_diag/) | P@100 structural-cap diagnosis (RC-27/28) | CONTROL | 2026-08-21 | 2 logs, JSON | `f222f44` |
| [E38](E38_feature_set_v2/) | Feature set v2 (19 dims) + latent control (RC-30) | PASS | 2026-08-25 | 8 JSON, 3 scripts, logs | `115ff25` |
| [E39](E39_m5a_revival/) | Revived 87-dim M5a + the LODO negative | PASS | 2026-08-25 | 3 JSON, 5 loop JSON, script | `f319055` |
| [E40](E40_temporal_lstm/) | The temporal/LSTM half (RC-20) | NEGATIVE | 2026-08-11 | script | `f218639` |
| [E41](E41_lab_digests/) | Lab digests, training logs, harness record | CONTROL | 2026-07→08 | 2 digests, 6 logs | assorted |
| [E42](E42_replay_all_families/) | Replay-tune transfer, all 7 families | PASS (5/7) | 2026-09-29 | script, JSON | — |
| [E43](E43_fusion_rule/) | Three closes for the family-dependent fusion rule | PASS (4-seed) | 2026-09-29 | script, JSON | — |
| [E44](E44_residual_evasion/) | Residual evasions (rotation, sub-threshold) + 2 fixes | NEGATIVE | 2026-09-29 | script, JSON | — |
| [E45](E45_tls_reality_check/) | How much of the testbed is actually encrypted | NEGATIVE | 2026-09-29 | script, JSON | — |
| [E46](E46_guard_regression/) | Pairing guards vs the archive's dominant error mode | PASS | 2026-09-29 | script, JSON | — |
| [E47](E47_provenance_audit/) | Back-fill checkpoint provenance (closes E46's gap) | PASS | 2026-09-29 | 3 scripts, 3 JSON | — |
| [E48](E48_opt_sweep/) | Sweep the OPT thresholds E43 set by eye | PASS | 2026-09-29 | script, JSON | — |
| [E49](E49_cross_testbed_why/) | **Why** the two extractors disagree — mechanism found | PASS | 2026-09-29 | 2 scripts, 2 JSON | — |
| [E50](E50_route_predictability/) | Can the fusion rule route itself? | NEGATIVE | 2026-09-29 | script, JSON | — |
| [E51](E51_infiltration_stability/) | Fix Infiltration's seed-flip at the estimator | NEGATIVE | 2026-09-29 | script, JSON | — |
| [E52](E52_edge_head/) | Edge-level granularity: is the fixed mean the bottleneck? | NEGATIVE | 2026-09-30 | script, JSON | — |
| [E53](E53_market_position/) | Where we stand vs published work — no protocol-matched table exists | POSITIONING | 2026-09-30 | README | — |
| [E54](E54_unsupervised_headtohead/) | Head-to-head: graph vs per-node vs VAE, one protocol | SUPERSEDED by E55 | 2026-09-30 | script, JSON | — |
| [E55](E55_vae_baseline/) | A working VAE baseline + the honest competitive position | PASS | 2026-09-30 | script, JSON | — |
| [E56](E56_vae_fusion/) | Fuse the VAE as a third view | PARTIAL | 2026-09-30 | script, JSON, 4 ckpt | — |
| [E57](E57_representation_audit/) | Audit: was the representation lever already pulled? (yes — E38) | AUDIT | 2026-09-30 | README | — |
| [E58](E58_lidds_host/) | First LID-DS host result — E01 replicates | **SUPERSEDED** by E60 (length confound) | 2026-10-01 | script, JSON | — |
| [E59](E59_lidds_curves/) | FPR curve + learning curve | **SUPERSEDED** by E60 (length confound) | 2026-10-01 | script, JSON | — |
| [E60](E60_lidds_lengthblind/) | Length-blind host detection, 2 LID-DS families | **PARTLY RETRACTED** by E61 | 2026-10-01 | script, JSON | — |
| [E61](E61_lidds_grid_ext/) | Extend E60's grid — memcached gap was a truncated-grid artefact | **RETRACT + PARTIAL** | 2026-10-01 | script, partial JSON | — |
| [E62](E62_lidds_rerun/) | Resumable re-run, grid {2…640} — heartbleed confirmed clean | PASS (partial) | 2026-10-01 | script, checkpoint JSON | — |

### Historic IDs

Three experiments were committed as `A1`/`A2`/`A3` before the E-series existed
and were renumbered on 2026-09-29 so the archive uses one scheme. Git history
and the CHANGELOG still use the old IDs.

| Now | Was | Name |
|---|---|---|
| [E30](E30_edge_injection/) | A1 | Edge/node injection vs shipped M5b |
| [E31](E31_fliptest/) | A2 | Top-k attribution flip test |
| [E32](E32_perfamily_thr/) | A3 | Per-family thresholds on host AE |

### One file deliberately left at the `experiments/` root

`exp_m5a_revival.py` is a **shared module, not evidence** — it is imported by
production code (`detection/alert_pipeline.py`, `detection/shap_revived_ctx.py`,
`detection/train_m5a_revived.py`). Moving it would mean editing four production
import paths for no organisational gain. It resolves its one experiment-local
dependency (`exp_v2b_temporal_aug`, now in
[E38](E38_feature_set_v2/)) through an explicit `sys.path` insert.

Everything else that was loose in this folder is now numbered. See
[E41](E41_lab_digests/) for the full explanation, including one dormant helper
that turned out to be stale.

---

## Scoreboard

**26 PASS · 16 NEGATIVE · 3 PARTIAL · 2 BUG · 1 INCOMPLETE · 10 CONTROL**

The NEGATIVE count is a feature. Twelve of the sixteen dead ends (E03–E09, E31,
E32, E25, E40) are attempts to *improve* on what we had; four of those (E04, E05,
E08, E09) tested ideas that prior literature recommends, and all four failed
on our data. Knowing that is worth more than the four successes.

## What the archive changed about the project

| Before this archive | After |
|---|---|
| Headline 0.9996±0.0001 on original CICIDS2017 | 0.900±0.017 Web / 0.943–0.972 on four families, clean data, 4 seeds |
| "Beats PIKACHU" (unverifiable figure) | Dropped — PIKACHU is a provenance-graph model, different task |
| Frozen Monday threshold (precision 0.037) | Rank-cut alerting via `top_k` |
| Single-seed quotes | Every number banded with a CI |
| One testbed | Disclosed cross-testbed gap + a transfer recipe (E29) |
| `detection/` mixed product with 14 loose `.pt` files | 9 checkpoints, catalogued in `detection/CHECKPOINTS.md` |

## Still open

**Closed this batch:** replay-tune beyond PortScan (E42, 5/7, boundary and cost
measured) · provenance back-fill (E47, 9/9 checkable) · the E43 4-seed band ·
**the OPT threshold sweep (E48) — the fusion rule is now fully measured; what
remains is a design decision** · `seed_protocol.py` revival · the v2 x noisyor
caveat (superseded).

### Open — runnable

1. **E01 epoch-grid extension — the first result was WRONG and is retracted.**
   The {10,20,40} grid gave seq-AE 0.7799 ± 0.0066 vs count-AE 0.7768 ± 0.0050
   (Δ 0.47 SD, "inside the noise") with no M3 gain, and that was reported as a
   negative. **It was an artefact of a truncated grid** — all four seeds had
   selected epoch 40, the maximum offered. On {40,80,120,160}:
   **seq-AE 0.8340 ± 0.0037 vs count-AE 0.7756 ± 0.0059, Δ = +0.058 = 11.9
   pooled SD**, and M3 (the reorder blind spot) goes **0.545 → 0.832** while the
   count-AE stays at 0.545. A 4.4× longer budget turned a null into the largest
   effect in the host pillar. **Standing rule now: a parameter pinned to the
   edge of a sweep has not been tested, it has been truncated.** A {160…400}
   grid is running (3 of 4 seeds again picked the maximum), but the 0.058 gap is
   far too large for the exact value to be in doubt.

### Open — runnable

2. **Botnet host fusion** — **no longer blocked.** The LID-DS loader works
   (`detection/lid_ds_loader.py`) and two CVE families are extracted and
   measured (E60/E61). Network-side ceiling is 0.709 ± 0.025 (E43 band,
   `repfuse`); every graph rule fails tightly. LID-DS is the third fuse input and
   is now available. **The caveat that decides whether it can help: the host arm
   must clear Botnet's network-side score of 0.709 to move the fused result at
   all, and on LID-DS the two arms have ranged from 0.53 to 0.99 depending
   entirely on the epoch budget.** Not yet attempted.

### Closed this batch

3. ~~**E01 epoch-grid extension**~~ — **closed.** The original {10,20,40} grid
   gave a null (0.47 SD); the {40…160} grid gave the real +0.058 (11.9 SD) with
   the M3 fix. Seed 0 selects epoch 240, interior to {160,240,320,400}, so the
   number is not grid-limited. The {160…400} follow-up was killed at 80
   min/seed because the 0.058 gap is far too large for the exact epoch to matter.

### Closed by decision, kept as disclosed limitations

4. **Sub-threshold pacing at x10** — **removed from the to-do list, not fixed.**
   [E44](E44_residual_evasion/) measured it honestly: the rescue holds to x5
   (0.974) and collapses at x10 (0.098), and both network-side fixes were
   rejected on evidence. It is a **disclosed limitation**, and it is Pillar
   3's territory — the host pillar is the only place it can be addressed, which
   is also why item 1 matters. E44's useful positive result is preserved:
   **IP rotation alone is not an evasion** (0.954 vs 0.969 control), because
   volume, not identity, is the signal.

5. **The TLS claim is structural, not empirical** —
   [E45](E45_tls_reality_check/): only **0.24% of attack traffic in the whole
   corpus is on encrypted ports**, and six of eight day-files contain none.
   E13's "0.89 on 443" was a 5-positive slice of an almost-empty population.
   The public encrypted-traffic datasets (CSTNET-TLS1.3, CESNET-TLS22) are
   app-classification, not IDS. Not a task — a wording constraint. Quote the
   feature audit ("no feature needs decryption"), never "evaluated on encrypted
   traffic".

### Open — research question, mechanism now known (E49)

6. **Cross-testbed: the *fix* is still open, the *explanation* is not.**
   [E49](E49_cross_testbed_why/) identified the mechanism. The two Mondays are
   the same network (host Jaccard **0.9999**, 9,709 vs 9,710 hosts), and the two
   extractors agree on UDP to within **0.07%** (224,178 vs 224,023 flows) but
   disagree on TCP by **52%** (305,423 vs 147,204). The improved extractor drops
   half the TCP flow records, so 	cp_frac per graph node collapses
   **0.516 -> 0.036** and edges-per-node falls **1.480 -> 1.088**. The model
   did not learn the wrong thing; it learned the truth about a pipeline it
   never sees at inference time.

   **This also explains why E27 pooling failed** (it averaged two incompatible
   flow densities; its validation loss bottomed at **epoch 17 of 400**), and
   **why replay-tuning works** (a one-sided covariate shift is exactly what
   20% replay is designed to handle).

   **E49c confirms it causally.** UDP-only graphs are a dead heat — KS median
   **0.003**, edges-per-node **1.027 vs 1.028** — while TCP-only graphs diverge
   at KS 0.427. If the pipelines differed in general, UDP would diverge too; it
   does not diverge at all. **But there is a residual:** downsampling the
   original's TCP to the clean count moves the divergence only part of the way
   (KS 0.427 → 0.373, edges/node 1.470 → 1.292 against a target of 1.032), so
   at matched count the two TCP streams still build different graphs. The
   improved extractor segments TCP flows differently, not just more coarsely.

   **Remaining:** normalising per-protocol flow density is now justified by
   measurement and would close the dominant term, but the residual means a real
   fix also has to align TCP flow *segmentation* — extractor-level work a
   detector cannot correct downstream. Replay-tune remains the pragmatic answer
   today.

### Open — closed by negative result

7. **~~Route the fusion rule on attack persistence?~~ — NO, and the reason is
   measured.** [E50](E50_route_predictability/) tested whether any label-free
   observable predicts the best k within a 40-window block. The best k
   genuinely moves (all six grid values appear, Botnet alone flips 1 <-> 8), so
   the premise was real — but across 53 blocks
   **corr(persistence, best k) = -0.25** and **corr(clustering, best k) = 0.001**.
   The instability is estimation noise, not a hidden regime, so there is no
   decision variable to route on. **Recommendation stands: tune k on local
   labelled traffic**, which E48 showed helps by up to 0.027 and never hurts.
