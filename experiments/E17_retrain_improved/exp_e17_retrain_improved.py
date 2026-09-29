"""
E17: retrain M5b on IMPROVED Monday benign (CNS2022 clean ground truth).

E16 showed the shipped (original-Monday) checkpoint collapses on clean
data for 4/7 families — it learned testbed normality, not normality.
This retrains the identical architecture (GraphAutoencoder, v2 19-dim,
NodeScaler log1p, benign-only) on improved Monday, then both cards
(E15 original + E16 clean) are re-run against the new checkpoint.

E26 addition: --val-frac holds out the LAST 20%% of Monday windows as
validation (time-ordered, no shuffle leak); best-val-loss epoch is saved
instead of the last epoch. Seeds 2-3 converged 2x worse at fixed 200ep
with no val check (Web 0.93->0.68) — this is the host pipeline's
discipline ported to M5b.

Does NOT overwrite production checkpoints. Output:
detection/gnn_improved_s0.pt

    python detection/exp_e17_retrain_improved.py --epochs 200 --seed 0
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler, set_seed

MONDAY = ROOT / "data" / "CICIDS2017_improved" / "monday.csv"
OUT = Path(__file__).resolve().parents[2] / "detection" / "gnn_improved_s0.pt"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description="E17: retrain on improved Monday.")
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lr", type=float, default=0.01)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--val-frac", type=float, default=0.2,
                    help="E26: fraction of LAST Monday windows held out as "
                         "validation; best-val epoch saved. Default 0.2 "
                         "(on) because val-picking fixed Web's seed-3 tail; "
                         "0 = legacy fixed-epoch training.")
    ap.add_argument("--extra-monday", default=None,
                    help="E27: second Monday CSV (combined-testbed training). "
                         "Host graph features are derived aggregates "
                         "(IP/ports/bytes/duration), so schemas need not match.")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(args.seed)
    df = normalize_columns(read_flows(MONDAY))
    if args.extra_monday:
        dx = normalize_columns(read_flows(args.extra_monday))
        df = pd.concat([df, dx], ignore_index=True)
        print(f"E27 combined Mondays: {len(df)} flows", flush=True)
    df = df[df["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    df = df[df["src_ip"].map(lambda v: isinstance(v, str))
            & df["dst_ip"].map(lambda v: isinstance(v, str))]
    graphs = build_graphs(df, window_seconds=60, feature_set="v2")
    print(f"improved Monday benign: {len(df)} flows -> {len(graphs)} graphs",
          flush=True)
    if args.val_frac > 0:
        n_val = max(1, int(len(graphs) * args.val_frac))
        tr, va = graphs[:-n_val], graphs[-n_val:]
        print(f"E26 val holdout: {len(tr)} train / {len(va)} val (last windows)",
              flush=True)
        scaler = NodeScaler(log=True).fit(tr)
        model = GraphAutoencoder(in_dim=tr[0].x.shape[1]).to(device)
        opt = torch.optim.Adam(model.parameters(), lr=args.lr)
        lf = nn.MSELoss()
        best, best_state, best_ep = float("inf"), None, -1
        for ep in range(args.epochs):
            model.train()
            for g in tr:
                x = scaler.transform(g.x).to(device)
                loss = lf(model(x, g.edge_index.to(device)), x)
                opt.zero_grad(); loss.backward(); opt.step()
            model.eval()
            with torch.no_grad():
                vl = float(np.mean([
                    lf(model(scaler.transform(g.x).to(device),
                             g.edge_index.to(device)),
                       scaler.transform(g.x).to(device)).item() for g in va]))
            if vl < best:
                best, best_state, best_ep = vl, copy.deepcopy(model.state_dict()), ep
            if ep % 40 == 0:
                print(f"  epoch {ep:3d} | val {vl:.6f} | best {best:.6f}@{best_ep}",
                      flush=True)
        model.load_state_dict(best_state)
        print(f"best val {best:.6f} @ epoch {best_ep}", flush=True)
        losses = [best]
    else:
        from gnn_model import train
        model, scaler, losses = train(graphs, epochs=args.epochs, lr=args.lr,
                                      device=device, quiet=False, log_scale=True,
                                      seed=args.seed)
        print(f"final loss {losses[-1]:.6f}", flush=True)
    torch.save({"model": model.state_dict(), "scaler": scaler.state_dict(),
                "in_dim": 19, "epochs": args.epochs, "seed": args.seed,
                "val_frac": args.val_frac,
                "train": "CICIDS2017_improved/monday benign-only"},
               Path(args.out))
    print(f"-> {Path(args.out).name}")


if __name__ == "__main__":
    main()
