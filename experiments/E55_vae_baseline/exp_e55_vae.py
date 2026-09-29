"""E55: a VAE baseline that actually trains, so the head-to-head is sound.

E54's headline table was correct on the graph-vs-per-node question but its VAE
arm **collapsed**: val reconstruction 0.0174 against the plain AE's 0.000033
(500x worse), identical to six digits across four seeds, per-family AUC SDs of
+-0.000 to +-0.002. A collapsed baseline cannot establish that anything is
worse than it, so E54 refused to cite it.

This fixes the arm. The likely cause is the KL term dominating: with z=8 on a
19-dim input and beta=1 from step 0, the posterior collapses toward the prior
and the decoder ignores x entirely. Standard remedies, swept here:

  beta in {1.0, 0.1, 0.01}      KL weight
  epochs 200 vs 600              schedule length
  mu/lv from a single trunk, logvar clamped to [-8, 8]

Selection is on VALIDATION RECONSTRUCTION against the plain AE's 0.000033. A VAE
that cannot reach that scale on this feature set is not a working baseline, and
that would be a finding about the feature set rather than about VAEs.

    python experiments/E55_vae_baseline/exp_e55_vae.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import build_graphs, normalize_columns, _window_key
from gnn_model import GraphAutoencoder, NodeScaler
from eval_guards import require_scaler_match, require_window_groups

CLEAN = ROOT / "data" / "CICIDS2017_improved"
DET = ROOT / "detection"
OUT = Path(__file__).resolve().parent / "exp_e55_vae.json"
SEEDS = [0, 1, 2, 3]
IN_DIM = 19

FAMS = {
    "Botnet":       ("friday.csv",    {"Botnet"}),
    "PortScan":     ("friday.csv",    {"Portscan"}),
    "DDoS":         ("friday.csv",    {"DDoS"}),
    "Infiltration": ("thursday.csv",  {"Infiltration", "Infiltration - Portscan"}),
    "WebAttacks":   ("thursday.csv",  {"Web Attack - Brute Force",
                                       "Web Attack - XSS",
                                       "Web Attack - SQL Injection"}),
}
GNN = {0: "gnn_improved_s0.pt", 1: "gnn_improved_s1.pt",
       2: "gnn_improved_s2.pt", 3: "gnn_improved_s3.pt"}
CFGS = [("beta1.0_e600", 1.0, 600), ("beta0.1_e600", 0.1, 600),
        ("beta0.01_e600", 0.01, 600)]


class VAE(nn.Module):
    def __init__(self, d=IN_DIM, h=128, z=8):
        super().__init__()
        self.trunk = nn.Sequential(nn.Linear(d, h), nn.ReLU(), nn.Linear(h, h), nn.ReLU())
        self.mu = nn.Linear(h, z)
        self.lv = nn.Linear(h, z)
        self.dec = nn.Sequential(nn.Linear(z, h), nn.ReLU(),
                                 nn.Linear(h, h), nn.ReLU(), nn.Linear(h, d))

    def forward(self, x):
        h = self.trunk(x)
        mu, lv = self.mu(h), self.lv(h).clamp(-8, 8)
        z = mu + torch.randn_like(mu) * torch.exp(0.5 * lv) if self.training else mu
        return self.dec(z), mu, lv


def rk(s):
    s = np.asarray(s, dtype=float)
    return np.argsort(np.argsort(s)) / max(len(s) - 1, 1)


def auc(y, s):
    y = np.asarray(y)
    if y.size == 0 or y.sum() == 0 or y.sum() == y.size:
        return None
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, np.asarray(s, dtype=float)))


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mon = normalize_columns(pd.read_csv(CLEAN / "monday.csv", low_memory=True))
    lab = mon["label"].astype(str).str.strip().str.upper()
    mon = mon[lab == "BENIGN"].sort_values("timestamp")
    blocks = []
    for _, w in mon.groupby(_window_key(mon, 60)):
        gs = build_graphs(w, window_seconds=60, feature_set="v2")
        if gs:
            blocks.append(gs[0].x)
    raw = torch.cat(blocks, 0)
    sc = NodeScaler(log=True)
    px = sc._prep(raw)
    sc.lo, sc.hi = px.min(0).values, px.max(0).values
    X = sc.transform(raw)
    n_val = int(len(X) * 0.2)
    Xtr, Xva = X[:-n_val].to(device), X[-n_val:].to(device)
    print(f"train {len(Xtr):,}  val {len(Xva):,}   (plain_ae val ref 3.3e-05)")

    res = {"reference_plain_ae_val": 3.3e-05, "configs": {}}

    # --- fit every config on seed 0, select on val reconstruction ----------
    sel = None
    for name, beta, epochs in CFGS:
        torch.manual_seed(0); np.random.seed(0)
        m = VAE().to(device)
        opt = torch.optim.Adam(m.parameters(), lr=1e-3, weight_decay=1e-5)
        for ep in range(epochs):
            m.train()
            perm = np.random.default_rng(ep).permutation(len(Xtr))
            for i in range(0, len(perm), 256):
                b = torch.tensor(perm[i:i + 256], device=device)
                xb = Xtr[b]
                rec, mu, lv = m(xb)
                rec_loss = ((rec - xb) ** 2).mean()
                kl = -0.5 * torch.mean(1 + lv - mu.pow(2) - lv.exp())
                loss = rec_loss + beta * kl
                opt.zero_grad(); loss.backward(); opt.step()
        m.eval()
        with torch.no_grad():
            rec, mu, lv = m(Xva)
            rec_only = ((rec - Xva) ** 2).mean().item()
        res["configs"][name] = {"beta": beta, "epochs": epochs,
                                "val_reconstruction": rec_only}
        print(f"  {name:16s} val recon {rec_only:.3e}")
        if sel is None or rec_only < sel[1]:
            sel = (name, rec_only, m)
    print(f"\nselected: {sel[0]}  val recon {sel[1]:.3e}")
    res["selected"] = sel[0]
    res["selected_val_reconstruction"] = sel[1]

    # --- evaluate the selected VAE on all seeds/families -----------------
    res["arms"] = {"vae": {f: {} for f in FAMS}, "gnn_ae": {f: {} for f in FAMS}}
    _, beta, epochs = next(c for c in CFGS if c[0] == sel[0])
    for seed in SEEDS:
        torch.manual_seed(seed); np.random.seed(seed)
        m = VAE().to(device)
        opt = torch.optim.Adam(m.parameters(), lr=1e-3, weight_decay=1e-5)
        for ep in range(epochs):
            m.train()
            perm = np.random.default_rng(seed * 1000 + ep).permutation(len(Xtr))
            for i in range(0, len(perm), 256):
                b = torch.tensor(perm[i:i + 256], device=device)
                xb = Xtr[b]
                rec, mu, lv = m(xb)
                loss = ((rec - xb) ** 2).mean() + beta * (-0.5 * torch.mean(
                    1 + lv - mu.pow(2) - lv.exp()))
                opt.zero_grad(); loss.backward(); opt.step()
        m.eval()
        blob = torch.load(DET / GNN[seed], map_location="cpu", weights_only=True)
        gsc = NodeScaler().load_state_dict(blob["scaler"])
        require_scaler_match(blob, gsc, f"E55 {GNN[seed]}")
        gnn = GraphAutoencoder(in_dim=IN_DIM)
        gnn.load_state_dict(blob["model"]); gnn.eval().to(device)

        for fam, (fn, labels) in FAMS.items():
            d = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
            lab = d["label"].astype(str).str.strip()
            d = d[~lab.str.endswith("- Attempted")].copy()
            lab = d["label"].astype(str).str.strip()
            if not lab.isin(labels).any():
                raise ValueError(f"{fam}: no rows match {sorted(labels)}")
            bad = set(d["src_ip"][lab.isin(labels)])
            d = d.sort_values("timestamp")
            sv, sg, ys, ws = [], [], [], []
            for wi, (_, w) in enumerate(d.groupby(_window_key(d, 60))):
                gs = build_graphs(w, window_seconds=60, feature_set="v2")
                if not gs:
                    continue
                g = gs[0]
                Xw = sc.transform(g.x.to(torch.float32)).to(device)
                ei = g.edge_index.to(device)
                e = ei.cpu().numpy()
                with torch.no_grad():
                    rec, _, _ = m(Xw)
                    nv = (rec - Xw).pow(2).mean(1).cpu().numpy()
                    ng = gnn.node_scores(gsc.transform(g.x).to(device), ei).cpu().numpy()
                sv.append(np.stack([nv[e[0]], nv[e[1]]], 1))
                sg.append(np.stack([ng[e[0]], ng[e[1]]], 1))
                ys.append(np.array([1 if g.hosts[s_] in bad else 0 for s_ in e[0]]))
                ws.append(np.full(g.num_edges, wi))
            Y, W = np.concatenate(ys), np.concatenate(ws)
            require_window_groups(W, len(Y), context=f"E55 {fam} s{seed}")
            for key, chunks in (("vae", sv), ("gnn_ae", sg)):
                v = np.concatenate(chunks, 0).mean(1)
                a = auc(Y, pd.DataFrame({"win": W, "v": v}).groupby(
                    "win")["v"].transform(rk).to_numpy())
                res["arms"][key][fam][str(seed)] = None if a is None else round(a, 4)
        print(f"  seed {seed} done", flush=True)

    print("\n" + "=" * 76)
    print(f"{'family':14s}{'vae (fixed)':>18s}{'gnn_ae':>14s}{'delta':>10s}")
    bands = {}
    for fam in FAMS:
        vv = np.array([x for x in res["arms"]["vae"][fam].values() if x is not None])
        gg = np.array([x for x in res["arms"]["gnn_ae"][fam].values() if x is not None])
        bands[fam] = {"vae": round(float(vv.mean()), 4), "vae_sd": round(float(vv.std(ddof=1)), 4),
                      "gnn": round(float(gg.mean()), 4), "gnn_sd": round(float(gg.std(ddof=1)), 4),
                      "delta": round(float(gg.mean() - vv.mean()), 4)}
        print(f"{fam:14s}{vv.mean():>12.4f}+-{vv.std(ddof=1):.3f}"
              f"{gg.mean():>14.4f}{gg.mean()-vv.mean():>+10.4f}")
    res["bands"] = bands
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()
