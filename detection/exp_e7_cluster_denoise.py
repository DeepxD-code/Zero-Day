"""
E7 (P22 WATCH): cluster-denoise preprocessing at the edge unit.

P22 (NAD-GNN) denoises by clustering before aggregation. Our port, no
retrain (shipped v2 checkpoint): per 60s window, KMeans on SCALED node
features; variants: none | centroid-replace (x <- cluster centroid) |
drop-small (remove smallest cluster's nodes, induced subgraph). Score =
relational-mean + within-window rank01 -> PortScan edge AUC. k=2,3.

    python detection/exp_e7_cluster_denoise.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.cluster import KMeans
from sklearn.metrics import roc_auc_score

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler
from exp_a1_edge_injection import rank01

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"
CKPT = Path(__file__).resolve().parent / "gnn_autoencoder_v1_logscale_v2.pt"
OUT = Path(__file__).resolve().parent / "exp_e7_cluster_denoise.json"
ATTACKER = "172.16.0.1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def edge_auc_graphs(graphs, model, device):
    ys, ss = [], []
    for g, ns in graphs:
        ei = g.edge_index.cpu().numpy()
        rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
        r = rank01(rel)
        for e in range(g.num_edges):
            ys.append(1 if g.hosts[int(ei[0, e])] == ATTACKER else 0)
            ss.append(float(r[e]))
    y = np.array(ys)
    return round(float(roc_auc_score(y, np.array(ss))), 4), len(y)


@torch.no_grad()
def score_graph(g, model, scaler, device, variant: str, k: int):
    x = scaler.transform(g.x).to(device)
    ei = g.edge_index.to(device)
    if variant == "none":
        ns = model.node_scores(x, ei).cpu().numpy()
        return g, ns
    X = x.cpu().numpy()
    lab = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(X)
    if variant == "centroid":
        cen = np.stack([X[lab == c].mean(axis=0) for c in lab])
        ns = model.node_scores(torch.tensor(cen, dtype=torch.float32).to(device), ei)
        return g, ns.cpu().numpy()
    # drop-small: induced subgraph without smallest cluster
    counts = np.bincount(lab)
    drop = int(np.argmin(counts))
    keep = np.where(lab != drop)[0]
    keep_t = torch.tensor(keep, device=device)
    h = [g.hosts[i] for i in keep]
    xs = x[keep_t]
    mask = torch.isin(ei[0], keep_t) & torch.isin(ei[1], keep_t)
    remap = torch.full((x.size(0),), -1, dtype=torch.long, device=device)
    remap[keep_t] = torch.arange(len(keep), device=device)
    ei2 = torch.stack([remap[ei[0][mask]], remap[ei[1][mask]]])
    ns = model.node_scores(xs, ei2.to(device)).cpu().numpy()
    g2 = type("G", (), {"edge_index": ei2.cpu(), "num_edges": int(mask.sum()),
                        "hosts": h})()
    return g2, ns


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    blob = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = GraphAutoencoder(in_dim=19)
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = NodeScaler().load_state_dict(blob["scaler"])
    day = normalize_columns(read_flows(DAY))
    graphs = build_graphs(day, window_seconds=60, feature_set="v2")
    print(f"PortScan 60s v2: {len(graphs)} graphs")
    res = {}
    for variant, k in [("none", 0), ("centroid", 2), ("centroid", 3),
                       ("drop-small", 2), ("drop-small", 3)]:
        scored = [score_graph(g, model, scaler, device, variant, k) for g in graphs]
        a, n = edge_auc_graphs(scored, model, device)
        res[f"{variant}_k{k}"] = {"auc": a, "n_edges": n}
        print(f"{variant} k={k}: AUC {a} (n={n})")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
