# Checkpoints — what ships, what trains, what's evidence

Regenerate any row with the trainer named. Nothing here is unreproducible.

## Production (default paths, untouched by experiment work)

| File | What | Trainer |
|---|---|---|
| `gnn_autoencoder_v1_logscale_v2.pt` | M5b graph, 19 host dims, v2 | `gnn_model.py` on original Monday |
| `m5a_revived_ctx.pt` | M5a flow, 87-dim ctx | `train_m5a_revived.py` |
| `host_autoencoder_adfa.pt` | Pillar 3 host AE, ADFA-LD | `exp_host_ablation.py` |
| `gnn_autoencoder_v1_logscale.pt` | M5b v1 (8 dims), kept for old 60s eval | `gnn_model.py` |
| `gnn_temporal_fused_v1.pt` | GNN+LSTM arm, RC-20 ablation evidence | `gnn_temporal_fused.py` |

## Clean-data models (CICIDS2017_improved) — recommended for new work

| File | What | Trainer |
|---|---|---|
| `gnn_improved_s0..s3.pt` | M5b, 4 seeds, val-picked epoch (E26) | `exp_e17_retrain_improved.py --seed N` |
| `m5a_revived_improved.pt` | M5a, 93-dim, clean Monday | `exp_e18_retrain_m5a_improved.py` |
| `gnn_improved_replay.pt` | Clean model replay-tuned on original Monday; holds both testbeds (E29) | `exp_e17_retrain_improved.py` + replay mix |

## Deleted and why

| Removed | Reason |
|---|---|
| `gnn_improved_s{1,2,3}.pt` (non-val) | Superseded by the val-picked band; E26 measured them inferior |
| `gnn_autoencoder_improved_monday_v2.pt` | Renamed `gnn_improved_s0.pt` |
| `gnn_combined_s0.pt` | E27 rejected — negative transfer both testbeds |
| `gnn_finetuned_orig20.pt` | E29 plain fine-tune — transfers but forgets clean side |
| `gnn_autoencoder_v1_logscale_60s.pt` | Zero references, duplicate of the v2 model |
| `m5a_revived_improved_s{1,2,3}.pt` | Band evidence lives in JSON; one checkpoint is enough to serve |
| `experiments/exp_e10_*.pt` | E10 evidence is in its JSON; regenerate via `exp_e10_graphids_port.py` |

## Conventions

- `gnn_improved_s{N}.pt` = clean-data M5b, seed N, val-picked (default protocol)
- `*_replay.pt` = cross-testbed transfer checkpoint
- M5a has no seed suffix: the flow model is stable across seeds (E22: 0.895±0.026)
