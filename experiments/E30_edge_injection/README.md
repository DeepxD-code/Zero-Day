<!-- Renumbered from the A1-series on 2026-09-29 so every experiment uses one scheme. The original ID is preserved in the archive README's Historic ID column and in git history. -->

# E30 — Structural edge/node injection vs the shipped M5b

**Verdict: CONTROL** · 2026-09-26

## Aim

Before testing any defence (E04) or any evasion (E12), we needed a measured
number for what structural tampering costs the **production artefact** — not a
toy model. A1 is that baseline and the metric definition every later robustness
experiment is measured against.

Port [3] (Galli et al.) describes edge-injection and node-injection
primitives. This ports them to the shipped checkpoint and quantifies the slope.

## What was done

Scored with the production checkpoint `gnn_autoencoder_v1_logscale_v2.pt`
(v2 19-dim, 60s graphs), on the PortScan day, attacker `172.16.0.1`:

- **edge_injection(k)** — attacker gains edges to k popular hosts
- **node_injection(n)** — n fresh benign hosts, each linked to the attacker

Score = relational mean endpoint reconstruction error → within-window rank01
→ edge AUC. Sweeps: k ∈ {0,1,2,5,10,20}, n ∈ {0,1,2,4,8}, 3 injection seeds.
Fresh injected nodes are excluded from the positive/negative count (they are
neither).

## Results (quick run, k,n ≤ 1)

| Arm | AUC |
|---|---|
| clean (k=0, n=0) | 0.8714 |
| edge_injection k=1 | 0.8553 ± 0.0087 |
| node_injection n=1 | 0.8523 ± 0.0134 |

Full sweeps are in `exp_a1_edge_injection.json`.

## What we understood

**Injection is cheap for the attacker but not free for the detector.**
Slope ≈ −0.016 AUC per injected edge — an attacker can bury themselves behind
20 decoy hosts for ~0.3 AUC, but it is not the free lunch the literature
sometimes implies. E4 later confirmed the detector cannot be hardened against
it by structural augmentation, and E12 showed the far more effective evasion
is *timing*, not structure.

**Why this is a CONTROL, not a candidate:** it introduced no change to the
project. It defined `slope_per_edge` as the robustness currency that E4 and
E12 both report, and it established that the shipped artifact is the right
thing to measure against (E4's clean arm reproduces 0.8714 here).

## Files

- `exp_a1_edge_injection.py` — procedure, contains the `edge_auc()` helper
  reused by E4, E7, E12, E13
- `exp_a1_edge_injection.json` — full k and n sweeps
