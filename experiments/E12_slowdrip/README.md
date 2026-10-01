# E12 — Slow-drip timing evasion vs M5b

**Verdict: NEGATIVE (severe)** · 2026-09-26 · commit `ba286ca`

## Aim

A1 (edge injection) and E4 (hardening) both operate on **structure**. The
cheapest evasion against a rate-based graph detector is not to change the graph
at all but to change **when** the edges appear: the same scan, stretched over
5× the wall-clock time. Per-window degree falls, and a detector whose entire
signal is per-window degree goes quiet.

If that works, the project has a real, cheap evasion and must either fix it or
disclose it. This is the experiment that decided the project's stance on
timing attacks.

## What was done

PortScan day, shipped `gnn_autoencoder_v1_logscale_v2.pt`, v2 60s graphs,
edge AUC, attacker `172.16.0.1`. Two TANTRA/TEGA-style timing primitives
(flagged to Person D in `harness/graph_techniques.py`):

- **`spread_dilate(f)`** — stretch the attacker's timeline by factor
  f ∈ {1, 2, 5, 10}. Same endpoints, same edge count, redistributed in time.
  This is the real evasion: it costs the attacker *nothing* but patience.
- **`burst_shape(mode)`** — intra-window reshaping only: `even` / `front` /
  `back`. Reshapes arrivals **within** a window, changing IAT and
  window-boundary sensitivity but not per-window totals.

## Results

| Dilate factor | AUC | Graphs | Attacker edges |
|---|---|---|---|
| ×1 (control) | **0.8714** | 150 | 30,613 |
| ×2 | **0.3578** | 166 | 30,613 |
| ×5 | **0.0637** | 176 | 30,613 |
| ×10 | 0.0651 | 176 | 30,613 |

| Burst mode | AUC |
|---|---|
| even | 0.8714 |
| front | 0.8714 |
| back | 0.8714 |

## What we understood

**This is the most serious negative in the archive, and it is a property of the
architecture, not a bug.**

`spread_dilate ×5` takes the detector from 0.87 to **0.064 — worse than random,
meaning the attacker now ranks *below* typical benign hosts.** And the price is
zero: identical endpoints, identical edge count, no extra traffic, no
injection. The attacker only waits longer. The AUC is flat from ×5 to ×10
because at that dilution there is no per-window anomaly left to find — the
signal is not degraded, it is *gone*.

`burst_shape` being identical across all three modes is the diagnostic that
separates the two effects: intra-window timing (IAT, arrival distribution) is
worth **nothing** to this detector, because it scores endpoint aggregates, not
sequences. Only the cross-window count matters. That is a clean, uncomfortable
statement about what the model actually uses.

**The fix, and where it lives.** A detector scoring one window at a time cannot
win this — the evasion removes the object it measures. It requires accumulating
across windows, which is exactly [E24](../E24_dilate_reputation/)'s
reputation tracker, and it measured **0.979 at ×5** (0.982/0.974/0.979 at
×1/×2/×5). A persistently-odd host cannot hide behind slow pacing; windows see
moments, an accumulator sees history.

**Residual risk, stated honestly:** reputation closes the *dilate* evasion.
An attacker who also rotates source hosts, or who stays under the per-window
threshold for a long time, is not addressed by it. The principled kill for that
is the eBPF host pillar, which sees the `connect` syscalls regardless of
pacing — network signals cannot be made to work for every attacker, which is
the entire argument for Pillar 3.

## Files

- `exp_e12_slowdrip.py` — procedure
- `exp_e12_slowdrip.json` — dilate sweep and burst modes
- `../../harness/graph_techniques.py` — the primitives (D's seam, flagged
  B-into-D)
