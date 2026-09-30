"""E56: fuse the VAE into the network pillar — does the third view help?

[E55](../E55_vae_baseline/) established that a properly-trained per-node VAE
beats the graph autoencoder on exactly one family:

    WebAttacks   vae 0.9353  vs  gnn 0.8931     (+0.042 FOR THE VAE)
    Infiltration vae 0.5855  vs  gnn 0.6333
    PortScan     vae 0.9509  vs  gnn 0.9612

So there is a view sitting on the shelf that is stronger than ours precisely
where we are weakest. [E43](../E43_fusion_rule/) showed fusion works by
combining views that FAIL DIFFERENTLY, and [E48](../E48_opt_sweep/) showed no
single fusion rule wins everywhere but rank-max is the robust default.

Prediction, stated before running so it can be falsified:
  **WebAttacks fused  > 0.950** (the current fused system), because fusion
  already beat both single views there.
  **Everything else stays within noise** — neither view dominates, so the gain
  should be small and possibly negative.

Arms: graph alone, VAE alone, noisyor(rank), rank-max — the E43 defaults.
Both views score EDGES with the same symmetric mean, so the comparison is fair
and the only difference is which encoder produced the node errors.

    python experiments/E56_vae_fusion/exp_e56_vae_fusion.py
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
CKPT = DET / "vae_improved_s{}.pt"
OUT = Path(__file__).resolve().parent / "exp_e56_vae_fusion.json"
SEEDS = [0, 1, 2, 3]
IN_DIM = 19
BETA = 0.01          # E55's selected KL weight
EPOCHS = 600

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
VAE_STATE = {0: "state_dict", 1: "state_dict", 2: "state_dict", 3: "state_dict"}


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
    print(f"train {len(Xtr):,} val {len(Xva):,}")

    def node_err(vae, Xw):
        with torch.no_grad():
            rec, _, _ = vae(Xw)
        return (rec - Xw).pow(2).mean(1).cpu().numpy()

    res = {"beta": BETA, "epochs": EPOCHS, "seeds": SEEDS, "arms": {}}
    for k in ("gnn", "vae", "noisyor", "rankmax"):
        res["arms"][k] = {f: {} for f in FAMS}

    for seed in SEEDS:
        # ---- train + checkpoint the VAE --------------------------------
        torch.manual_seed(seed); np.random.seed(seed)
        vae = VAE().to(device)
        opt = torch.optim.Adam(vae.parameters(), lr=1e-3, weight_decay=1e-5)
        best, best_state = float("inf"), None
        for ep in range(EPOCHS):
            vae.train()
            perm = np.random.default_rng(seed * 1000 + ep).permutation(len(Xtr))
            for i in range(0, len(perm), 256):
                b = torch.tensor(perm[i:i + 256], device=device)
                xb = Xtr[b]
                rec, mu, lv = vae(xb)
                loss = ((rec - xb) ** 2).mean() + BETA * (-0.5 * torch.mean(
                    1 + lv - mu.pow(2) - lv.exp()))
                opt.zero_grad(); loss.backward(); opt.step()
            vae.eval()
            with torch.no_grad():
                rec, _, _ = vae(Xva)
                vl = ((rec - Xva) ** 2).mean().item()
            if vl < best:
                best, best_state = vl, {k2: v.detach().clone()
                                        for k2, v in vae.state_dict().items()}
        vae.load_state_dict(best_state); vae.eval()
        torch.save({"state_dict": best_state, "scaler": sc.state_dict(),
                    "in_dim": IN_DIM, "beta": BETA, "epochs": EPOCHS,
                    "seed": seed,
                    "train": "CICIDS2017_improved/monday benign-only",
                    "val_reconstruction": best},
                   CKPT.format(seed))
        print(f"  seed {seed} vae val {best:.3e} -> {CKPT.format(seed).name}",
              flush=True)

        blob = torch.load(DET / GNN[seed], map_location="cpu", weights_only=True)
        gsc = NodeScaler().load_state_dict(blob["scaler"])
        require_scaler_match(blob, gsc, f"E56 {GNN[seed]}")
        gnn = GraphAutoencoder(in_dim=IN_DIM)
        gnn.load_state_dict(blob["model"]); gnn.eval().to(device)

        for fam, (fn, labels) in FAMS.items():
            d = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
            lab = d["label"].astype(str).str.strip()
            d = d[~lab.str.endswith("- Attempted")].copy()
            lab = d["label"].astype(str).str.strip()
            if not lab.isin(labels).any():
                raise ValueError(f"{fam}: no rows match {sorted(labels)} in {fn}")
            bad = set(d["src_ip"][lab.isin(labels)])
            d = d.sort_values("timestamp")
            Rg, Rv, Y, W = [], [], [], []
            for wi, (_, w) in enumerate(d.groupby(_window_key(d, 60))):
                gs = build_graphs(w, window_seconds=60, feature_set="v2")
                if not gs:
                    continue
                g = gs[0]
                ei = g.edge_index.to(device)
                e = ei.cpu().numpy()
                Xw = sc.transform(g.x.to(torch.float32)).to(device)
                with torch.no_grad():
                    ng = gnn.node_scores(gsc.transform(g.x).to(device),
                                        ei).cpu().numpy()
                nv = node_err(vae, Xw)
                Rg.append(np.stack([ng[e[0]], ng[e[1]]], 1))
                Rv.append(np.stack([nv[e[0]], nv[e[1]]], 1))
                Y.append(np.array([1 if g.hosts[s_] in bad else 0 for s_ in e[0]]))
                W.append(np.full(g.num_edges, wi))
            Y, W = np.concatenate(Y), np.concatenate(W)
            require_window_groups(W, len(Y), context=f"E56 {fam} s{seed}")
            D = pd.DataFrame({"win": W})
            D["g"] = np.concatenate(Rg, 0).mean(1)
            D["v"] = np.concatenate(Rv, 0).mean(1)
            D["rg"] = D.groupby("win")["g"].transform(rk)
            D["rv"] = D.groupby("win")["v"].transform(rk)
            D["noisy"] = 1 - (1 - D["rg"]) * (1 - D["rv"])
            D["rmax"] = np.maximum(D["rg"], D["rv"])
            for k, col in (("gnn", "rg"), ("vae", "rv"),
                            ("noisyor", "noisy"), ("rankmax", "rmax")):
                a = auc(Y, D[col].to_numpy())
                res["arms"][k][fam][str(seed)] = None if a is None else round(a, 4)
        print(f"  seed {seed} evaluated", flush=True)

    print("\n" + "=" * 80)
    bands = {}
    for fam in FAMS:
        row = f"{fam:14s}"
        bands[fam] = {}
        for k in ("gnn", "vae", "noisyor", "rankmax"):
            v = np.array([x for x in res["arms"][k][fam].values() if x is not None])
            bands[fam][k] = {"mean": round(float(v.mean()), 4),
                             "sd": round(float(v.std(ddof=1)), 4)}
            row += f"{v.mean():>11.4f}+-{v.std(ddof=1):.3f}"
        print(row)
    res["bands"] = bands
    # E43's fused system (M5b+M5a+reputation) for the predicted comparison
    e43 = json.loads((ROOT / "experiments" / "E43_fusion_rule"
                      / "exp_e43_fusion_rules.json").read_text(encoding="utf-8"))
    res["e43_fused_system"] = {f: round(max(
        (v["mean"] for v in e43["band"][f].values())), 4) for f in FAMS}
    print("\nE43 fused system (2 pillars + reputation) for reference:")
    for f in FAMS:
        print(f"  {f:14s} {res['e43_fused_system'][f]:.4f}")
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()
