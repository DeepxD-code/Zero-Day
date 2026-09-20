"""
A1 (P02 ADOPT): structural edge/node injection vs SHIPPED M5b on PortScan day.

Measures what P02's primitives cost the production artifact
(detection/gnn_autoencoder_v1_logscale_v2.pt, v2 19-dim, 60s):
edge_injection (attacker -> k popular hosts) and node_injection
(k fresh benign hosts + attacker link each). Score = relational mean
endpoint recon -> within-window rank01 -> edge AUC, attacker = 172.16.0.1
(+ fresh nodes for node_injection). k sweep x 3 injection seeds.

    python detection/exp_a1_edge_injection.py
    python detection/exp_a1_edge_injection.py --quick
Branch-only (exp/host-seqae-p37): harness/graph_techniques.py gained the two
P02 functions (flagged B-into-D); this script only measures.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler
from graph_techniques import edge_injection, node_injection

DAY = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"
CKPT = Path(__file__).resolve().parent / "gnn_autoencoder_v1_logscale_v2.pt"
OUT = Path(__file__).resolve().parent / "exp_a1_edge_injection.json"
ATTACKER = "172.16.0.1"


def rank01(s: np.ndarray) -> np.ndarray:
    order = np.argsort(np.argsort(s))
    return order / max(len(s) - 1, 1)


def edge_auc(graphs, model, scaler, device, bad: set[str], exclude: set[str] = frozenset()):
    ys, ss = [], []
    for g in graphs:
        with torch.no_grad():
            ns = model.node_scores(scaler.transform(g.x).to(device),
                                   g.edge_index.to(device)).cpu().numpy()
        ei = g.edge_index.cpu().numpy()
        rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
        r = rank01(rel)
        for e in range(g.num_edges):
            src = g.hosts[int(ei[0, e])]
            if src in exclude:
                continue
            ys.append(1 if src in bad else 0)
            ss.append(float(r[e]))
    from sklearn.metrics import roc_auc_score
    y = np.array(ys)
    if y.sum() == 0 or y.sum() == len(y):
        return None, 0
    return float(roc_auc_score(y, np.array(ss))), len(y)


def main():
    ap = argparse.ArgumentParser(description="A1: P02 structural injection vs shipped M5b.")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    blob = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = GraphAutoencoder(in_dim=19)
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = NodeScaler().load_state_dict(blob["scaler"])
    print(f"shipped {CKPT.name} on {device}")

    day = normalize_columns(read_flows(DAY))
    ks = [0, 1] if args.quick else [0, 1, 2, 5, 10, 20]
    ns = [0, 1] if args.quick else [0, 1, 2, 4, 8]
    res = {"edge": {}, "node": {}}
    for k in ks:
        aucs = []
        for sd in args.seeds:
            df = day if k == 0 else edge_injection(day, ATTACKER, k, sd)
            g = build_graphs(df, window_seconds=60, feature_set="v2")
            a, n = edge_auc(g, model, scaler, device, {ATTACKER})
            aucs.append(a)
        res["edge"][str(k)] = {"mean": round(float(np.mean(aucs)), 4),
                               "std": round(float(np.std(aucs)), 4), "n_edges": n}
        print(f"edge_injection k={k:2d}: AUC {np.mean(aucs):.4f}±{np.std(aucs):.4f}")
    for n in ns:
        aucs = []
        for sd in args.seeds:
            df = day if n == 0 else node_injection(day, ATTACKER, n, 20, sd)
            g = build_graphs(df, window_seconds=60, feature_set="v2")
            fresh = {f"192.168.99.{210 + k}" for k in range(n)}
            a, _ = edge_auc(g, model, scaler, device, {ATTACKER}, exclude=fresh)
            aucs.append(a)
        res["node"][str(n)] = {"mean": round(float(np.mean(aucs)), 4),
                               "std": round(float(np.std(aucs)), 4)}
        print(f"node_injection n={n:2d}: AUC {np.mean(aucs):.4f}±{np.std(aucs):.4f}")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
