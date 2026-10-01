# E02 — Edge-level fusion reproduction (RC-20 lineage)

**Verdict: CONTROL** · 2026-09-26 · commit `7fe9d5b`

## Aim

CLAUDE.md carries a load-bearing negative: the temporal/LSTM half of M5b adds
nothing at edge level (RC-20). That claim was originally measured with a
throwaway script. This folder holds the reproduction so the negative is
anchored to committed code rather than a lost one-off.

It is also the origin of two things used everywhere downstream:
`experiments/seed_protocol.py` (the canonical 4-seed, CUDA-deterministic
harness) and the `exp_edge_rc20.py` runner.

## What was done

Re-runs the edge-level fusion comparison at two seed groupings:

- `exp_edge_e2_s01.json` — seeds 0 and 1
- `exp_edge_e2_s23.json` — seeds 2 and 3
- `exp_edge_e2.json` — the combined record

All three check out against the branch's hardening pass: `weights_only=True` on
every `torch.load`, import fallbacks for the `legacy/stub_detector` shim, and
the `set_seed(deterministic=)` split added here so screening runs can skip
determinism cost without changing the recorded protocol.

## What we understood

This is a control, and controls earn their place by making other numbers
trustworthy. Two things came out of it:

1. **The RC-20 negative holds at both seed groupings** — the LSTM half is not
   rescued by a luckier seed. That closed the question and freed the LSTM arm
   for ablation-only use (`gnn_temporal_fused.py` stays in `detection/` for
   the report's architecture comparison, nothing imports it in production).
2. **`seed_protocol.py` was born here** and is now the shared seeding helper.
   The gotcha it encodes — nothing was seeded before 2026-08-11, and two
   identical unseeded full-file sweeps gave mean ROC-AUC 0.8997 and 0.9251 — is
   the single most important methodological fact in the project.

## Files

- `exp_edge_rc20.py` — procedure
- `exp_edge_e2.json`, `exp_edge_e2_s01.json`, `exp_edge_e2_s23.json` — results
- `../seed_protocol.py` — the shared 4-seed harness (parent folder)
