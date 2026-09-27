"""
E17: retrain M5b on IMPROVED Monday benign (CNS2022 clean ground truth).

E16 showed the shipped (original-Monday) checkpoint collapses on clean
data for 4/7 families — it learned testbed normality, not normality.
This retrains the identical architecture (GraphAutoencoder, v2 19-dim,
NodeScaler log1p, benign-only) on improved Monday, then both cards
(E15 original + E16 clean) are re-run against the new checkpoint.

Does NOT overwrite production checkpoints. Output:
detection/gnn_autoencoder_improved_monday_v2.pt

    python detection/exp_e17_retrain_improved.py --epochs 200 --seed 0
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler, set_seed, train

MONDAY = ROOT / "data" / "CICIDS2017_improved" / "monday.csv"
OUT = Path(__file__).resolve().parent / "gnn_autoencoder_improved_monday_v2.pt"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description="E17: retrain on improved Monday.")
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lr", type=float, default=0.01)
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(args.seed)
    df = normalize_columns(read_flows(MONDAY))
    df = df[df["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    df = df[df["src_ip"].map(lambda v: isinstance(v, str))
            & df["dst_ip"].map(lambda v: isinstance(v, str))]
    graphs = build_graphs(df, window_seconds=60, feature_set="v2")
    print(f"improved Monday benign: {len(df)} flows -> {len(graphs)} graphs",
          flush=True)
    model, scaler, losses = train(graphs, epochs=args.epochs, lr=args.lr,
                                  device=device, quiet=False, log_scale=True,
                                  seed=args.seed)
    print(f"final loss {losses[-1]:.6f}", flush=True)
    torch.save({"model": model.state_dict(), "scaler": scaler.state_dict(),
                "in_dim": 19, "epochs": args.epochs, "seed": args.seed,
                "train": "CICIDS2017_improved/monday benign-only"},
               OUT)
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
