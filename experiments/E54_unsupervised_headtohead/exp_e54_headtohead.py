"""E54: head-to-head against unsupervised baselines under ONE protocol.

[E53](../E53_market_position/) established that no published CIC-IDS2017 number
is comparable to ours, because their protocol differs (same-day train/test,
`- Attempted` retained, pooled multiclass F1). A literature table would be a
number that looks like a comparison and is not one.

This removes the mismatch by REIMPLEMENTING the baselines ourselves, on our
data, under the identical E16 protocol. Everything below is trained on
CICIDS2017_improved Monday BENIGN ONLY and evaluated per-family on held-out
days, `- Attempted` excluded, ranked WITHIN each 60s window then pooled.

Arms, all unsupervised, all on the same 19-dim node vectors:

  plain_ae   MLP autoencoder, no message passing. Isolates whether the GRAPH
             helps, or whether the 19 dims alone are enough.
  vae        same backbone, variational. The current strong unsupervised ref.
  masked     masked-context reconstruction: predict a held-out subset of dims
             from the rest (the self-supervised masked-reconstruction line).
  gnn_ae     the shipped GraphAutoencoder -- the incumbent, loaded from disk.

The question E53 left open, made falsifiable: if a VAE beats the graph
autoencoder broadly, the architecture is not the contribution. If the graph wins
where the per-node models are at chance, it is.

    python experiments/E54_unsupervised_headtohead/exp_e54_headtohead.py
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
OUT = Path(__file__).resolve().parent / "exp_e54_headtohead.json"
SEEDS = [0, 1, 2, 3]
IN_DIM = 19
MASK_FRAC = 0.25          # masked-context arm: 25% of dims held out

# verbatim from E43/E48 (see the E48 label-string incident)
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


# ------------------------------------------------------------------ models
class PlainAE(nn.Module):
    def __init__(self, d=IN_DIM, h=64):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d, h), nn.ReLU(), nn.Linear(h, 8))
        self.dec = nn.Sequential(nn.Linear(8, h), nn.ReLU(), nn.Linear(h, d))

    def forward(self, x):
        return self.dec(self.enc(x))


class VAE(nn.Module):
    def __init__(self, d=IN_DIM, h=64, z=8):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d, h), nn.ReLU())
        self.mu = nn.Linear(h, z)
        self.lv = nn.Linear(h, z)
        self.dec = nn.Sequential(nn.Linear(z, h), nn.ReLU(), nn.Linear(h, d))

    def forward(self, x):
        h = self.enc(x)
        mu, lv = self.mu(h), self.lv(h).clamp(-8, 8)
        z = mu + torch.randn_like(mu) * torch.exp(0.5 * lv) if self.training else mu
        return self.dec(z), mu, lv


class Masked(nn.Module):
    """Masked-context reconstruction: given a subset of dims, predict the rest."""

    def __init__(self, d=IN_DIM, h=64, keep=None):
        super().__init__()
        self.keep = list(range(d)) if keep is None else list(keep)
        self.pred = list(range(d)) if keep is None else [i for i in range(d)
                                                        if i not in set(keep)]
        self.net = nn.Sequential(nn.Linear(len(self.keep), h), nn.ReLU(),
                                 nn.Linear(h, len(self.pred)))

    def forward(self, x):
        return self.net(x[:, self.keep]), self.pred


# ------------------------------------------------------------------- data
def train_graphs():
    mon = normalize_columns(pd.read_csv(CLEAN / "monday.csv", low_memory=True))
    lab = mon["label"].astype(str).str.strip().str.upper()
    mon = mon[lab == "BENIGN"].sort_values("timestamp")
    out = []
    for _, w in mon.groupby(_window_key(mon, 60)):
        gs = build_graphs(w, window_seconds=60, feature_set="v2")
        if gs:
            out.append(gs[0])
    return out


def train_arm(name, Xtr, Xva, seed, device, epochs=200):
    torch.manual_seed(seed)
    np.random.seed(seed)
    if name == "plain_ae":
        m = PlainAE().to(device)
    elif name == "vae":
        m = VAE().to(device)
    elif name == "masked":
        rng = np.random.default_rng(seed)
        perm = rng.permutation(IN_DIM)
        nk = int(IN_DIM * (1 - MASK_FRAC))
        m = Masked(keep=perm[:nk]).to(device)
    else:
        raise ValueError(name)
    opt = torch.optim.Adam(m.parameters(), lr=1e-2, weight_decay=1e-5)
    best, best_state = float("inf"), None
    for ep in range(epochs):
        m.train()
        perm = np.random.default_rng(seed * 1000 + ep).permutation(len(Xtr))
        for i in range(0, len(perm), 256):
            b = torch.tensor(perm[i:i + 256], device=device)
            xb = Xtr[b]
            if name == "vae":
                rec, mu, lv = m(xb)
                loss = ((rec - xb) ** 2).mean() - 0.5 * torch.mean(
                    1 + lv - mu.pow(2) - lv.exp())
            elif name == "masked":
                rec, idx = m(xb)
                loss = ((rec - xb[:, idx]) ** 2).mean()
            else:
                loss = ((m(xb) - xb) ** 2).mean()
            opt.zero_grad(); loss.backward(); opt.step()
        m.eval()
        with torch.no_grad():
            if name == "vae":
                rec, _, _ = m(Xva)
                vl = ((rec - Xva) ** 2).mean().item()
            elif name == "masked":
                rec, idx = m(Xva)
                vl = ((rec - Xva[:, idx]) ** 2).mean().item()
            else:
                vl = ((m(Xva) - Xva) ** 2).mean().item()
        if vl < best:
            best, best_state = vl, {k: v.detach().clone()
                                    for k, v in m.state_dict().items()}
    m.load_state_dict(best_state)
    m.eval()
    return m, best


def score(m, name, X):
    with torch.no_grad():
        if name == "masked":
            rec, idx = m(X)
            e = (rec - X[:, idx]).pow(2).mean(1)
        elif name == "vae":
            rec, _, _ = m(X)
            e = (rec - X).pow(2).mean(1)
        else:
            e = (m(X) - X).pow(2).mean(1)
    return e.cpu().numpy()


def rk(s):
    s = np.asarray(s, dtype=float)
    o = np.argsort(np.argsort(s))
    return o / max(len(s) - 1, 1)


def auc(y, s):
    y = np.asarray(y)
    if y.size == 0 or y.sum() == 0 or y.sum() == y.size:
        return None
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, np.asarray(s, dtype=float)))


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}")
    graphs = train_graphs()
    raw = np.concatenate([g.x.numpy() for g in graphs], axis=0)
    sc = NodeScaler(log=True)
    allx = sc._prep(torch.tensor(raw, dtype=torch.float32))
    sc.lo, sc.hi = allx.min(0).values, allx.max(0).values
    X = sc.transform(torch.tensor(raw, dtype=torch.float32))
    n_val = int(len(X) * 0.2)
    Xtr, Xva = X[:-n_val].to(device), X[-n_val:].to(device)
    print(f"train nodes {len(Xtr):,}  val {len(Xva):,}")

    res = {"protocol": "CICIDS2017_improved Monday benign only; per-day eval; "
                       "- Attempted excluded; within-window rank -> pool; "
                       "4 seeds; in_dim 19", "arms": {}, "seeds": SEEDS}

    # gnn_ae is scored too (it is loaded, not trained here), so it needs a slot
    # in the results dict -- the first version omitted it and KeyError'd on the
    # first family.
    for name in ("plain_ae", "vae", "masked", "gnn_ae"):
        res["arms"][name] = {fam: {} for fam in FAMS}

    for seed in SEEDS:
        # ---- per-node baselines -----------------------------------------
        models = {}
        for name in ("plain_ae", "vae", "masked"):
            m, vl = train_arm(name, Xtr, Xva, seed, device)
            models[name] = m
            print(f"  seed {seed} {name} val {vl:.6f}", flush=True)
        # ---- shipped graph autoencoder ----------------------------------
        blob = torch.load(DET / GNN[seed], map_location="cpu", weights_only=True)
        gsc = NodeScaler().load_state_dict(blob["scaler"])
        require_scaler_match(blob, gsc, f"E54 {GNN[seed]}")
        gnn = GraphAutoencoder(in_dim=IN_DIM)
        gnn.load_state_dict(blob["model"]); gnn.eval().to(device)

        for fam, (fn, labels) in FAMS.items():
            d = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
            lab = d["label"].astype(str).str.strip()
            d = d[~lab.str.endswith("- Attempted")].copy()
            lab = d["label"].astype(str).str.strip()
            if not lab.isin(labels).any():
                raise ValueError(f"{fam}: no rows match {sorted(labels)} in {fn}")
            bad_src = set(d["src_ip"][lab.isin(labels)])
            if not bad_src:
                raise ValueError(f"{fam}: attack rows but no attacker host")
            d = d.sort_values("timestamp")
            recs = {k: [] for k in list(models) + ["gnn_ae"]}
            ys, wins = [], []
            for wi, (_, w) in enumerate(d.groupby(_window_key(d, 60))):
                gs = build_graphs(w, window_seconds=60, feature_set="v2")
                if not gs:
                    continue
                g = gs[0]
                # NodeScaler._prep calls torch.clamp, so it needs a TENSOR --
                # passing g.x.numpy() here raised TypeError on the first eval.
                Xw = sc.transform(g.x.to(torch.float32)).to(device)
                ei = g.edge_index.to(device)
                for k, m in models.items():
                    s = score(m, k, Xw)
                    e = ei.cpu().numpy()
                    recs[k].append(np.stack([s[e[0]], s[e[1]]], axis=1))
                with torch.no_grad():
                    n = gnn.node_scores(gsc.transform(g.x).to(device), ei).cpu().numpy()
                e = ei.cpu().numpy()
                recs["gnn_ae"].append(np.stack([n[e[0]], n[e[1]]], axis=1))
                ehost = np.array([g.hosts[s_] for s_ in e[0]])
                ys.append(np.array([1 if h_ in bad_src else 0 for h_ in ehost]))
                wins.append(np.full(g.num_edges, wi))
            Y = np.concatenate(ys)
            W = np.concatenate(wins)
            require_window_groups(W, len(Y), context=f"E54 {fam} s{seed}")
            for k, chunks in recs.items():
                M = np.concatenate(chunks, axis=0)     # (E, 2) endpoint scores
                edge = M.mean(1)
                R = pd.DataFrame({"win": W, "v": edge})
                rank = R.groupby("win")["v"].transform(rk).to_numpy()
                a = auc(Y, rank)
                res["arms"][k][fam][str(seed)] = None if a is None else round(a, 4)
        print(f"  seed {seed} evaluated", flush=True)

    print("\n" + "=" * 84)
    print(f"{'family':14s}" + "".join(f"{k:>17s}" for k in
                                      ("plain_ae", "vae", "masked", "gnn_ae")))
    bands = {}
    for fam in FAMS:
        row = f"{fam:14s}"
        bands[fam] = {}
        for k in ("plain_ae", "vae", "masked", "gnn_ae"):
            v = np.array([x for x in res["arms"][k][fam].values() if x is not None])
            if len(v) < 2:
                row += f"{'n/a':>17s}"
                continue
            bands[fam][k] = {"mean": round(float(v.mean()), 4),
                             "sd": round(float(v.std(ddof=1)), 4)}
            row += f"{v.mean():>11.4f}+-{v.std(ddof=1):.3f}"
        print(row)
    res["bands"] = bands
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()
