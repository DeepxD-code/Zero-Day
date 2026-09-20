"""
E4 (P29 WATCH): structural-augmented M5b training vs A1 injection slope.

P29 (Galli et al.) claims low-degree structural adversarial training lifts
robustness with zero clean tax. Our port: during benign-only Monday training,
each graph/epoch gets m~U{0..8} spurious edges (uniform src -> in-degree
biased dst, P02-shaped noise). Scaler stays fit on UNAUGMENTED graphs
(production convention); x/edge_index inconsistency IS the perturbation.
Arms (100ep, 4 seeds): clean vs hardened. Metrics: clean PortScan edge-AUC
(tax?) + A1 k-sweep slope (k=0,5,20 x 2 inj seeds).

    python detection/exp_e4_hardening.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler, set_seed
from exp_a1_edge_injection import edge_auc
from graph_techniques import edge_injection

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FLOWS = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling"
OUT = Path(__file__).resolve().parent / "exp_e4_hardening.json"
ATTACKER = "172.16.0.1"


def augment(edge_index: torch.Tensor, n: int, rng: np.random.Generator, m: int):
    if m <= 0 or n < 3:
        return edge_index
    deg = np.bincount(edge_index[1].cpu().numpy(), minlength=n).astype(float) + 1.0
    p = deg / deg.sum()
    have = set(map(tuple, edge_index.t().tolist()))
    add = []
    tries = 0
    while len(add) < m and tries < 10 * m:
        tries += 1
        s, d = int(rng.integers(n)), int(rng.choice(n, p=p))
        if s != d and (s, d) not in have:
            have.add((s, d))
            add.append((s, d))
    if not add:
        return edge_index
    return torch.cat([edge_index, torch.tensor(add).t()], dim=1)


def train_arm(graphs, scaler, device, epochs: int, seed: int, harden: bool):
    set_seed(seed)
    model = GraphAutoencoder(in_dim=graphs[0].x.shape[1]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    lf = nn.MSELoss()
    pre = [(g.x, g.edge_index) for g in graphs]
    for ep in range(epochs):
        rng = np.random.default_rng(seed * 7919 + ep)
        for x0, ei0 in pre:
            x = scaler.transform(x0).to(device)
            ei = ei0.to(device)
            if harden:
                ei = augment(ei0, x0.shape[0], rng, int(rng.integers(0, 9))).to(device)
            loss = lf(model(x, ei), x)
            opt.zero_grad(); loss.backward(); opt.step()
    return model


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mon = normalize_columns(read_flows(FLOWS / "Monday-WorkingHours.pcap_ISCX.csv"))
    mon = mon[mon["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    bg = build_graphs(mon, window_seconds=60, feature_set="v2")
    print(f"Monday benign 60s v2: {len(bg)} graphs")
    scaler = NodeScaler(log=True).fit(bg)
    day = normalize_columns(read_flows(
        FLOWS / "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"))

    res = {}
    for arm in ["clean", "hardened"]:
        aucs, slopes = [], []
        for sd in [0, 1, 2, 3]:
            m = train_arm(bg, scaler, device, 100, sd, harden=(arm == "hardened"))
            g0 = build_graphs(day, window_seconds=60, feature_set="v2")
            a0, _ = edge_auc(g0, m, scaler, device, {ATTACKER})
            ak = []
            for k in [5, 20]:
                kk = []
                for inj in [0, 1]:
                    df = edge_injection(day, ATTACKER, k, inj)
                    gk = build_graphs(df, window_seconds=60, feature_set="v2")
                    a, _ = edge_auc(gk, m, scaler, device, {ATTACKER})
                    kk.append(a)
                ak.append(float(np.mean(kk)))
            aucs.append(a0)
            slopes.append((a0 - ak[1]) / 20)  # AUC cost per injected edge
            print(f"{arm} seed {sd}: clean {a0:.4f} k5 {ak[0]:.4f} k20 {ak[1]:.4f}")
        res[arm] = {"clean_auc": [round(float(a), 4) for a in aucs],
                    "slope_per_edge": [round(float(s), 5) for s in slopes]}
    c, h = res["clean"], res["hardened"]
    print(f"\nclean tax: {np.mean(c['clean_auc']):.4f} -> {np.mean(h['clean_auc']):.4f} "
          f"(Δ{np.mean(h['clean_auc']) - np.mean(c['clean_auc']):+.4f})")
    print(f"slope/edge: {np.mean(c['slope_per_edge']):.5f} -> {np.mean(h['slope_per_edge']):.5f}")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
