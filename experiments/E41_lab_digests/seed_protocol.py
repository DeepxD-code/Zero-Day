"""
SEED-REPEAT PROTOCOL — the gate every retrained checkpoint must pass.

Original (2026-08-13, `seed_protocol.py`): trained N independent full
checkpoints with disjoint seed ranges and scored each through the REAL entry
point, `alert_pipeline.score_window()`. That intent is preserved. What it
imported no longer exists:

  * `gnn_model.EdgeScaler`, `train_edge_model`, `ScoreCalibrator`,
    `save_ensemble` — removed when the edge/graph split was consolidated and
    the model became a single `GraphAutoencoder` (see E38)
  * `ensembler.m5a_calibrator` — replaced by the inlined noisyor fusion in
    `alert_pipeline.score_window` (see E36)

So the ensemble-per-checkpoint machinery is gone, and reviving it would rebuild
architecture the project deliberately retired. What survives -- and what
CLAUDE.md gotcha #11 actually demands -- is the *protocol*: train N independent
checkpoints with different seeds, score each through the production entry
point, and report mean +/- std per family.

The seeding itself is NOT reimplemented here. It lives in
`detection/gnn_model.py:set_seed()` and is the authoritative implementation
(CUBLAS_WORKSPACE_CONFIG, cuda.manual_seed_all, cudnn.deterministic,
benchmark=False, PYTHONHASHSEED). Calling it is the whole contract.

Why this gate exists: two identical UNSEEDED full-file sweeps once gave mean
ROC-AUC 0.8997 and 0.9251, and PortScan moved 6.5 points on weight
initialisation alone. Any difference under ~6 points between two
configurations is noise until it holds across seeds.

    python experiments/E41_lab_digests/seed_protocol.py --seeds 0 1 2 3
    python experiments/E41_lab_digests/seed_protocol.py --seeds 0 --quick

Reports per-family mean +/- std through score_window(), the same call the
dashboard and alert API make.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

import torch

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler, set_seed, train
import alert_pipeline as AP
from evaluate_gnn import FLOWS, malicious_hosts

TRAIN_FILE = FLOWS / "Monday-WorkingHours.pcap_ISCX.csv"
ATTACK_FILES = {
    "Patator": "Tuesday-WorkingHours.pcap_ISCX.csv",
    "DoS": "Wednesday-workingHours.pcap_ISCX.csv",
    "WebAttacks": "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    "Infiltration": "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "Botnet": "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "PortScan": "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "DDoS": "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
}
OUT = Path(__file__).resolve().parent / "seed_protocol_results.json"


def auc_from_alerts(alerts, bad):
    """Edge-level ROC-AUC straight off the production alert objects."""
    from sklearn.metrics import roc_auc_score
    y, s = [], []
    for a in alerts:
        if a["is_adversarial_test"]:
            continue
        y.append(1 if a["src_ip"] in bad else 0)
        s.append(a["anomaly_score"])
    y = np.array(y)
    if len(y) == 0 or y.sum() == 0 or y.sum() == len(y):
        return None, 0
    return float(roc_auc_score(y, np.array(s))), int(y.sum())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3])
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--limit", type=int, default=150_000,
                    help="rows per attack file (0 = full); 150k is the "
                         "screening value, 0 is the recorded protocol")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    if args.quick:
        args.seeds, args.epochs, args.limit = [0], 5, 50_000

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device} torch={torch.__version__}", flush=True)

    mon = normalize_columns(read_flows(TRAIN_FILE))
    mon = mon[mon["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    mon = mon[mon["src_ip"].map(lambda v: isinstance(v, str))
              & mon["dst_ip"].map(lambda v: isinstance(v, str))]
    train_graphs = build_graphs(mon, window_seconds=60, feature_set="v2")
    print(f"Monday benign: {len(mon):,} flows -> {len(train_graphs)} graphs",
          flush=True)

    rows = {}
    for sd in args.seeds:
        t0 = time.time()
        set_seed(sd)                       # <- the whole determinism contract
        model, scaler, losses = train(train_graphs, epochs=args.epochs,
                                      device=device, quiet=True, seed=sd)
        ckpt = ROOT / "detection" / f"_seedproto_s{sd}.pt"
        torch.save({"model": model.state_dict(), "scaler": scaler.state_dict(),
                    "in_dim": train_graphs[0].x.shape[1], "seed": sd}, ckpt)
        try:
            AP._M5B_CACHE.pop(ckpt.name, None)
        except Exception:
            pass
        for fam, fn in ATTACK_FILES.items():
            df = normalize_columns(read_flows(FLOWS / fn, limit=args.limit or None))
            df = df[df["src_ip"].map(lambda v: isinstance(v, str))
                    & df["dst_ip"].map(lambda v: isinstance(v, str))]
            bad = set(malicious_hosts(df))
            # score the real entry point, top_k=0 -> no flagging, we want ranks
            alerts = AP.score_window(df, top_k=0, feature_set="v2")
            a, n = auc_from_alerts(alerts, bad)
            rows.setdefault(fam, []).append(a)
            print(f"  seed {sd} {fam:13s} AUC {a} ({n} edges)", flush=True)
        print(f"seed {sd} done in {time.time() - t0:.0f}s (loss {losses[-1]:.6f})",
              flush=True)

    band = {}
    for fam, vals in rows.items():
        v = [x for x in vals if x is not None]
        band[fam] = {"mean": float(np.mean(v)), "std": float(np.std(v)),
                     "seeds": v} if v else None
        if v:
            print(f"{fam:13s} {band[fam]['mean']:.4f} +- {band[fam]['std']:.4f} "
                  f"{[round(x, 4) for x in v]}")
    allv = [b["mean"] for b in band.values() if b]
    if allv:
        print(f"MEAN over {len(allv)} families: {np.mean(allv):.4f}")
    OUT.write_text(json.dumps(band, indent=1))
    print(f"-> {OUT.name}")
    print("NOTE: screening values (--limit 150k) are NOT the recorded protocol; "
          "re-run with --limit 0 before quoting any of these numbers.")


if __name__ == "__main__":
    main()
