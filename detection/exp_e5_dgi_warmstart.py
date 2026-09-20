"""
E5 (P04 WATCH): DGI self-supervised warm-start for M5b seed variance.

P04 (Gu et al.) retains >98% supervised performance with <4% labels via
in-context pre-training. Our translation: Deep Graph Infomax pre-training
(node-vs-summary mutual info, feature-shuffle corruption) initializes M5b's
SAGE encoder before reconstruction fine-tuning. Question is VARIANCE, not
labels: fresh 100ep single models span 0.74-0.89 on PortScan (E4 clean arm).
Arms (100ep recon both, 4 seeds): scratch vs DGI-50 + recon-100.
Metric: PortScan clean edge-AUC mean +- std.

    python detection/exp_e5_dgi_warmstart.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch_geometric.nn import SAGEConv

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler, set_seed
from exp_a1_edge_injection import edge_auc

ROOT = Path(__file__).resolve().parent.parent
FLOWS = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling"
OUT = Path(__file__).resolve().parent / "exp_e5_dgi_warmstart.json"
ATTACKER = "172.16.0.1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class DGIEncoder(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 32, latent: int = 8):
        super().__init__()
        self.conv1 = SAGEConv(in_dim, hidden)
        self.conv2 = SAGEConv(hidden, latent)
        self.bilin = nn.Bilinear(latent, latent, 1)

    def encode(self, x, ei):
        return self.conv2(torch.relu(self.conv1(x, ei)), ei)

    def forward(self, x, ei):
        h = self.encode(x, ei)
        s = h.mean(dim=0, keepdim=True).expand_as(h)
        with torch.no_grad():
            perm = torch.randperm(x.size(0), device=x.device)
        hc = self.encode(x[perm], ei)
        pos = self.bilin(h, s).squeeze(-1)
        neg = self.bilin(hc, s).squeeze(-1)
        return pos, neg


def pretrain_dgi(graphs, scaler, device, epochs: int, seed: int) -> DGIEncoder:
    set_seed(seed)
    enc = DGIEncoder(graphs[0].x.shape[1]).to(device)
    opt = torch.optim.Adam(enc.parameters(), lr=1e-3)
    bce = nn.BCEWithLogitsLoss()
    pre = [(scaler.transform(g.x).to(device), g.edge_index.to(device)) for g in graphs]
    for _ in range(epochs):
        for x, ei in pre:
            pos, neg = enc(x, ei)
            y = torch.cat([torch.ones_like(pos), torch.zeros_like(neg)])
            loss = bce(torch.cat([pos, neg]), y)
            opt.zero_grad(); loss.backward(); opt.step()
    return enc


def train_recon(graphs, scaler, device, epochs: int, seed: int, init: DGIEncoder | None):
    set_seed(seed + (1000 if init is not None else 0))
    model = GraphAutoencoder(in_dim=graphs[0].x.shape[1]).to(device)
    if init is not None:
        model.conv1.load_state_dict(init.conv1.state_dict())
        model.conv2.load_state_dict(init.conv2.state_dict())
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    lf = nn.MSELoss()
    pre = [(scaler.transform(g.x).to(device), g.edge_index.to(device)) for g in graphs]
    for _ in range(epochs):
        for x, ei in pre:
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
    g0 = build_graphs(day, window_seconds=60, feature_set="v2")

    res = {}
    for arm in ["scratch", "dgi"]:
        aucs = []
        for sd in [0, 1, 2, 3]:
            init = pretrain_dgi(bg, scaler, device, 50, sd) if arm == "dgi" else None
            m = train_recon(bg, scaler, device, 100, sd, init)
            a, _ = edge_auc(g0, m, scaler, device, {ATTACKER})
            aucs.append(a)
            print(f"{arm} seed {sd}: clean AUC {a:.4f}")
        res[arm] = [round(float(a), 4) for a in aucs]
    s, d = np.array(res["scratch"]), np.array(res["dgi"])
    print(f"\nscratch {s.mean():.4f}+-{s.std():.4f} | dgi {d.mean():.4f}+-{d.std():.4f}")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
