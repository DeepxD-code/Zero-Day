"""
E10 (GraphIDS head-to-head): E-GraphSAGE + masked-Transformer recon vs our
SAGE-MLP recon under OUR protocol.

GraphIDS (Guerra et al., NeurIPS'25): E-GraphSAGE encoder + Transformer
masked-autoencoder, benign-only reconstruction — same paradigm, ~0.99x scale,
but closed splits (never held-out families). Port their two load-bearing
ingredients: (1) edge-aware message passing (edge MLP updated with endpoint
pairs, nodes aggregate edge-informed messages), (2) masked-node training
(25% nodes replaced by a learned mask token, loss on masked only; full-pass
recon error at test). Arms (Monday 60s v2, 100ep, 4 seeds): ours-fresh vs
graphids-port. Metric: host-window AUC per family (max-score per host).

    python detection/exp_e10_graphids_port.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score
from torch_geometric.nn import SAGEConv
from torch_geometric.utils import scatter

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler, set_seed
from evaluate_gnn import malicious_hosts

ROOT = Path(__file__).resolve().parent.parent
FLOWS = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling"
OUT = Path(__file__).resolve().parent / "exp_e10_graphids_port.json"
FAMS = {
    "PortScan": "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "DDoS": "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
    "Botnet": "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "Infiltration": "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "WebAttacks": "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    "Patator": "Tuesday-WorkingHours.pcap_ISCX.csv",
    "DoS": "Wednesday-workingHours.pcap_ISCX.csv",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class EGraphSAGEEnc(nn.Module):
    """Edge-aware SAGE (Lo et al.): edges updated from endpoint pairs, nodes
    aggregate the updated edge embeddings alongside neighbour features."""

    def __init__(self, in_dim: int, edge_dim: int, hidden: int = 32, latent: int = 8):
        super().__init__()
        self.conv1 = SAGEConv(in_dim, hidden)
        self.e1 = nn.Sequential(nn.Linear(2 * in_dim + edge_dim, hidden), nn.ReLU())
        self.conv2 = SAGEConv(2 * hidden, latent)

    def forward(self, x, edge_index, edge_attr):
        s, d = edge_index[0], edge_index[1]
        e = self.e1(torch.cat([x[s], x[d], edge_attr], dim=1))
        agg = scatter(e, d, dim=0, dim_size=x.size(0), reduce="mean")
        h = torch.relu(self.conv1(x, edge_index))
        return self.conv2(torch.cat([h, agg], dim=1), edge_index)


class GraphIDSPort(nn.Module):
    """EGraphSAGEEnc -> project -> Transformer -> reconstruct node features."""

    def __init__(self, in_dim: int, edge_dim: int, hidden: int = 32,
                 latent: int = 8, tdim: int = 32, heads: int = 4, layers: int = 2):
        super().__init__()
        self.enc = EGraphSAGEEnc(in_dim, edge_dim, hidden, latent)
        self.up = nn.Linear(latent, tdim)
        self.mask_tok = nn.Parameter(torch.zeros(tdim))
        layer = nn.TransformerEncoderLayer(d_model=tdim, nhead=heads,
                                           dim_feedforward=64, batch_first=True)
        self.trans = nn.TransformerEncoder(layer, num_layers=layers)
        self.out = nn.Linear(tdim, in_dim)

    def forward(self, x, edge_index, edge_attr, mask: torch.Tensor | None = None):
        z = self.enc(x, edge_index, edge_attr)
        t = self.up(z).unsqueeze(0)
        if mask is not None:
            t = torch.where(mask.unsqueeze(0).unsqueeze(-1), self.mask_tok.expand_as(t), t)
        return self.out(self.trans(t)).squeeze(0)

    @torch.no_grad()
    def node_scores(self, x, edge_index, edge_attr):
        return torch.mean((self.forward(x, edge_index, edge_attr) - x) ** 2, dim=1)


# SCREENING run: deterministic=False (fast scatter path). Both arms share one
# process so relative deltas are fair (E2/E4 style); published retrains keep
# the deterministic default. See gnn_model.set_seed docstring.
FAST = True


def train_ours(graphs, scaler, device, epochs: int, seed: int):
    set_seed(seed, deterministic=not FAST)
    model = GraphAutoencoder(in_dim=graphs[0].x.shape[1]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    lf = nn.MSELoss()
    pre = [(scaler.transform(g.x).to(device), g.edge_index.to(device)) for g in graphs]
    for _ in range(epochs):
        for x, ei in pre:
            loss = lf(model(x, ei), x)
            opt.zero_grad(); loss.backward(); opt.step()
    return model


def train_port(graphs, scaler, device, epochs: int, seed: int, edge_dim: int):
    set_seed(seed + 5000, deterministic=not FAST)
    in_dim = graphs[0].x.shape[1]
    model = GraphIDSPort(in_dim, edge_dim).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    lf = nn.MSELoss()
    pre = [(scaler.transform(g.x).to(device), g.edge_index.to(device),
            g.edge_attr[:, :edge_dim].to(device).float()) for g in graphs]
    mask_ratio = 0.25
    for _ in range(epochs):
        for x, ei, ea in pre:
            n = x.size(0)
            m = torch.zeros(n, dtype=torch.bool, device=device)
            m[torch.randperm(n, device=device)[:max(1, int(mask_ratio * n))]] = True
            recon = model(x, ei, ea, m)
            loss = lf(recon[m], x[m])
            opt.zero_grad(); loss.backward(); opt.step()
    return model


@torch.no_grad()
def host_auc(graphs, model, scaler, device, bad: set, port: bool):
    best: dict[str, float] = {}
    for g in graphs:
        x = scaler.transform(g.x).to(device)
        ei = g.edge_index.to(device)
        if port:
            ea = g.edge_attr[:, :5].to(device).float()
            ns = model.node_scores(x, ei, ea).cpu().numpy()
        else:
            ns = model.node_scores(x, ei).cpu().numpy()
        for h, s in zip(g.hosts, ns):
            if s > best.get(h, -1):
                best[h] = float(s)
    y = np.array([1 if h in bad else 0 for h in best])
    s = np.array([best[h] for h in best])
    if y.sum() == 0 or y.sum() == len(y):
        return None
    return float(roc_auc_score(y, s))


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mon = normalize_columns(read_flows(FLOWS / "Monday-WorkingHours.pcap_ISCX.csv"))
    mon = mon[mon["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    bg = build_graphs(mon, window_seconds=60, feature_set="v2")
    print(f"Monday benign 60s v2: {len(bg)} graphs, edge_dim={bg[0].edge_attr.shape[1]}")
    scaler = NodeScaler(log=True).fit(bg)
    fams = {}
    for fam, fn in FAMS.items():
        df = normalize_columns(read_flows(FLOWS / fn))
        df = df[df["src_ip"].map(lambda v: isinstance(v, str)) &
                df["dst_ip"].map(lambda v: isinstance(v, str))]
        fams[fam] = (build_graphs(df, window_seconds=60, feature_set="v2"),
                     malicious_hosts(df))

    res = {"ours": {}, "port": {}}
    for sd in [0, 1, 2, 3]:
        mo = train_ours(bg, scaler, device, 100, sd)
        mp = train_port(bg, scaler, device, 100, sd, edge_dim=5)
        ro, rp = {}, {}
        for fam, (g, bad) in fams.items():
            ro[fam] = host_auc(g, mo, scaler, device, bad, False)
            rp[fam] = host_auc(g, mp, scaler, device, bad, True)
        res["ours"][str(sd)] = ro
        res["port"][str(sd)] = rp
        mo_m = np.mean([v for v in ro.values() if v is not None])
        mp_m = np.mean([v for v in rp.values() if v is not None])
        print(f"seed {sd}: ours {mo_m:.4f} vs port {mp_m:.4f} (delta {mp_m - mo_m:+.4f})")
    for arm in ["ours", "port"]:
        arr = np.array([[res[arm][str(s)][f] for f in FAMS] for s in ["0", "1", "2", "3"]],
                       dtype=float)
        print(f"{arm}: mean {arr.mean():.4f}+-{arr.mean(axis=1).std():.4f}")
    print("per-family (ours vs port means):")
    ao = np.array([[res["ours"][str(s)][f] for f in FAMS] for s in ["0", "1", "2", "3"]], dtype=float)
    ap = np.array([[res["port"][str(s)][f] for f in FAMS] for s in ["0", "1", "2", "3"]], dtype=float)
    for j, fam in enumerate(FAMS):
        print(f"  {fam:14s} {ao[:, j].mean():.4f} vs {ap[:, j].mean():.4f} ({ap[:, j].mean() - ao[:, j].mean():+.4f})")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
