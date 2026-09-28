"""
E25: seed-ensemble for Web (and Infiltration control), clean Thursday.

Web graph AUC flips 0.93->0.68 across seeds ( undertraining variance,
seeds 2-3 converged 2x worse). Test: mean of the 4 checkpoints' node
scores per window, then standard 60s edge-rank AUC. Expectation: ensemble
tightens toward consensus instead of seed 3's worst.

    python detection/exp_e25_ensemble.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import build_graphs, normalize_columns, _window_key
from gnn_model import GraphAutoencoder, NodeScaler

DATA = ROOT / "data" / "CICIDS2017_improved" / "thursday.csv"
OUT = Path(__file__).resolve().parent / "exp_e25_ensemble.json"
DET = Path(__file__).resolve().parent
CKS = [DET / "gnn_autoencoder_improved_monday_v2.pt",
       DET / "gnn_improved_s1.pt", DET / "gnn_improved_s2.pt",
       DET / "gnn_improved_s3.pt"]
FAMS = {"Web": {"Web Attack - Brute Force", "Web Attack - XSS",
                "Web Attack - SQL Injection"},
        "Infiltration": {"Infiltration", "Infiltration - Portscan"}}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    from sklearn.metrics import roc_auc_score
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    models = []
    for ck in CKS:
        b = torch.load(ck, map_location="cpu", weights_only=True)
        m = GraphAutoencoder(in_dim=19)
        m.load_state_dict(b["model"])
        m.eval().to(device)
        models.append((m, NodeScaler().load_state_dict(b["scaler"])))
    df = normalize_columns(pd.read_csv(DATA, low_memory=True))
    lab = df["label"].astype(str).str.strip()
    df = df[~lab.str.endswith("- Attempted")].copy()
    lab = df["label"].astype(str).str.strip()
    df = df.sort_values("timestamp")
    recs = {f: [] for f in FAMS}
    for _, w in df.groupby(_window_key(df, 60)):
        gs = build_graphs(w, window_seconds=60, feature_set="v2")
        if not gs:
            continue
        g = gs[0]
        with torch.no_grad():
            nss = [m.node_scores(sc.transform(g.x).to(device),
                                 g.edge_index.to(device)).cpu().numpy()
                   for m, sc in models]
        ens = np.mean(nss, axis=0)
        ei = g.edge_index.cpu().numpy()
        wl = lab.loc[w.index]
        rel = (ens[ei[0]] + ens[ei[1]]) / 2.0
        o = np.argsort(np.argsort(rel))
        r = o / max(len(rel) - 1, 1)
        for f, L in FAMS.items():
            fs = set(w["src_ip"][wl.isin(L).to_numpy()])
            for e in range(g.num_edges):
                src = g.hosts[int(ei[0, e])]
                recs[f].append((1 if src in fs else 0, float(r[e])))
    res = {}
    for f, rows in recs.items():
        y = np.array([a for a, _ in rows])
        s = np.array([b for _, b in rows])
        res[f] = {"auc": float(roc_auc_score(y, s)),
                  "n_atk": int(y.sum()), "n": len(y)}
        print(f"{f}: ensemble AUC {res[f]['auc']:.4f} "
              f"atk {res[f]['n_atk']}/{res[f]['n']}", flush=True)
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
