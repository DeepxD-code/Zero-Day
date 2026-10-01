# E44 — The two residual evasions, and two attempted network-side fixes

**Verdict: PARTIAL — and it corrects an overclaim in E24** · 2026-09-29

## Aim

[E24](../E24_dilate_reputation/) closed slow-drip *dilution*: reputation held
0.974–0.979 at ×1/×2/×5, while per-window scoring collapsed 0.87 → 0.36 →
0.06. That was read as "E12 is closed".

Two attacks were left open, and the question this experiment answers is
whether either has a network-side fix, or whether Pillar 3 is genuinely the
only answer:

- **R1 host rotation** — one scan, many targets, spread over R source IPs so no
  single host accumulates enough history for reputation.
- **R2 sub-threshold** — pace the scan so no window ever rises above the queue
  (×10 dilution), staying odd only in aggregate over a long horizon.

Candidate fixes, both network-side, both using signals already computed:
**F1** dual-timescale reputation (fast K-window mean fused with a slow
unbounded mean) and **F2** neighbour overlap (a rotated scan has many sources
hitting a *common* target set; independent browsing does not).

## What was done

Shipped `gnn_autoencoder_v1_logscale_v2.pt` (original-data checkpoint) against
the **original** PortScan day, so the control reproduces E24's 0.8714 exactly.
Four arms: control, R1 (5-way rotation, same targets/timings/volume), R2 (×10
dilate), R2+R1 combined. Five scoring modes per arm.

> **The first two attempts at this script were invalid and are worth
> recording.** Run 1 paired the *clean-data* checkpoint with the *original*
> day — that measures the E17 cross-testbed gap, not evasion, and produced a
> nonsense control of 0.394. Run 2 kept the fast/slow caps so far apart
> (20 vs 200,000) that the slow channel never filled, so `slow` and `fast`
> came out byte-identical and the dual-timescale test tested nothing. Both are
> the same error class this archive documents: measuring on the wrong pairing
> and on a population that does not exercise the mechanism. Fixing the pairing
> and setting FAST_K = 20 against a 150-window day made both channels real.

## Results

| Arm | window | repfuse (fast) | slow only | F1 dual | F2 dual+overlap |
|---|---|---|---|---|---|
| **control (×1)** | 0.8714 | 0.9689 | **0.9725** | 0.9709 | 0.6099 |
| **R1 rotation ×5** | 0.8578 | **0.9536** | 0.9492 | 0.9526 | 0.6848 |
| **R2 sub-threshold ×10** | 0.0651 | 0.0976 | 0.0976 | 0.0976 | 0.0828 |
| **R2 ×10 + R1 ×5** | 0.4658 | 0.5009 | 0.5009 | 0.5009 | 0.4996 |

## What we understood

**Correction to E24: reputation does not hold at ×10.** E24 swept {1, 2, 5}
and reported "0.979 at every dilution factor", which invited the reading that
slow-drip was fully closed. At **×10 reputation collapses to 0.098** — the
attacker is ranked *below* typical benign hosts. The rescue has a boundary at
roughly ×5, and the archive should say so. E24's mechanism is real and its
measured range is 1–5×.

**R1 is not an evasion as I synthesised it — and that is informative.**
Rotation over 5 IPs cost the detector almost nothing (0.9536 vs 0.9689). The
reason is mechanical: my `rotate()` reassigns the attacker's rows round-robin
but preserves the target set and the timings, so each of the 5 IPs still opens
~40 distinct peers per window. **Volume is what makes a host anomalous, not
identity.** So an attacker who rotates IPs must *also* reduce per-host volume —
which is R2, and R2 is not survivable. The two attacks are not independent;
rotation only helps in combination with dilution, and then both are already
doomed. The honest reading: **IP rotation buys nothing on its own**, and that is
a useful, non-obvious result.

**R2 is a genuine, unfixed network-side evasion.** ×10 dilution leaves the
attacker at 0.098. `slow_only` and `fast` come out identical (0.0976) — under
this much dilution the per-window score is flat enough that a 20-window mean
and a 150-window mean rank identically. There is no per-window anomaly left to
accumulate; the only remaining signal is *cumulative* and it is now too diluted
to survive pooling with normal windows.

**F1 dual-timescale: rejected.** 0.9709 vs 0.9689 at control (+0.002, inside
noise) and *identical* at ×10. Adding a slower channel does not recover a
signal that is not present at any timescale. F1 is a real improvement on
WebAttacks bursts (E43's OPT3, where the fast channel is too laggy) but it is
not a defence against deliberate dilution.

**F2 neighbour overlap: rejected as implemented.** 0.61 at control — worse
than doing nothing. The formula divides by the number of hosts in the window,
which compresses a genuinely discriminative ratio into a near-constant. The
*idea* is sound (a rotated scan has maximal neighbour-set overlap, and E44's R1
arm confirms rotation is detectable at 0.95) but this implementation measures
the wrong quantity and should be rebuilt before anyone cites it.

**Where this leaves item 6.** I previously argued both residual evasions had a
network-side fix. On the evidence, that was too optimistic:

| Attack | Network-side fix? |
|---|---|
| R1 host rotation | **Not needed** — it costs the attacker nothing because volume, not identity, is the signal |
| R2 sub-threshold ×10 | **No fix found.** Reputation holds to ×5, fails at ×10. Dual-timescale and overlap both rejected. |
| Host rotation *plus* dilution | Defeated by neither fix; the R2 failure dominates |

So the ×10-diluted attack is the project's real residual weakness, and it is
genuinely Pillar 3's problem: eBPF sees the `connect` syscalls at the kernel
regardless of pacing, IP identity, or window boundaries. The network pillar
cannot be made to work for an attacker who never looks anomalous in any window —
and that is not a failure of effort, it is the structural argument for the
three-pillar design. The report should state it that way, with the ×5 boundary
as the measured limit of what the network pillar can do.

**What would still be worth trying** (none cheap): cumulative-decay
reputation with an unbounded horizon across days, or a network-level
correlation that aggregates across *source* hosts rather than scoring them
independently — the latter is a genuinely different model, not a new feature.

## Files

- `exp_e44_residual.py` — the four arms, five scoring modes
- `exp_e44_residual.json` — results
