"""E52: an edge-LEVEL representation, not more capacity.

The per-flow gap is not a capacity problem. Widths move thousandths; the
binding constraint is what a single edge score can express. Today
`GraphAutoencoder.edge_scores` is a hand-fixed symmetric mean:

    edge = (node_err[src] + node_err[dst]) / 2

That throws away everything asymmetric about an edge for free. A flow where the
client is anomalous but the server is not, and a flow where BOTH ends are
equally anomalous, receive the same score. There is no parameter to tune that
recovers that distinction -- it was never represented.

So: keep the trained node autoencoder EXACTLY as it is (no retraining, no new
capacity) and learn a small head that reads the edge's own feature vector:

    phi(e) = [n_src, n_dst, |n_src - n_dst|, min, max,
              log1p(deg_src), log1p(deg_dst), mean, |n_src-n_dst| / (max+eps)]

The head is trained on BENIGN EDGES ONLY, on the same train split, with the same
val-picked protocol as every other model here. It learns which shape of
asymmetry looks normal; at inference an edge whose shape departs from that is
anomalous even if its mean error is small.

This is granularity work in the literal sense: the same parameters now resolve
a finer distinction. If it fails, the conclusion is that the edge-level gap is
not a representation problem either, and that is worth knowing.

    python experiments/E52_edge_head/exp_e52_edge_head.py
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
OUT = Path(__file__).resolve().parent / "exp_e52_edge_head.json"

# verbatim from E43/E48, after the label-string incident
FAMS = {
    "Botnet":       ("friday.csv",    {"Botnet"}),
    "PortScan":     ("friday.csv",    {"Portscan"}),
    "DDoS":         ("friday.csv",    {"DDoS"}),
    "Infiltration": ("thursday.csv",  {"Infiltration", "Infiltration - Portscan"}),
    "WebAttacks":   ("thursday.csv",  {"Web Attack - Brute Force",
                                       "Web Attack - XSS",
                                       "Web Attack - SQL Injection"}),
}
CKPT = {0: "gnn_improved_s0.pt", 1: "gnn_improved_s1.pt",
        2: "gnn_improved_s2.pt", 3: "gnn_improved_s3.pt"}
PHI_DIM = 8
EPS = 1e-6


def phi(n_src, n_dst, deg_src, deg_dst):
    """Per-edge feature vector. Pure function of quantities the graph already
    carries -- no new information is computed, only arranged differently."""
    mn = np.minimum(n_src, n_dst)
    mx = np.maximum(n_src, n_dst)
    return np.stack([
        n_src, n_dst, np.abs(n_src - n_dst), mn, mx,
        np.log1p(np.maximum(deg_src, 0)), np.log1p(np.maximum(deg_dst, 0)),
        (n_src + n_dst) / 2.0,
    ], axis=1)


class EdgeHead(nn.Module):
    """Small MLP over the edge's own features. 8 -> 16 -> 1, ~150 parameters.

    Deliberately tiny: the claim under test is that GRANULARITY buys signal, so
    a head with real capacity would confound the result.
    """

    def __init__(self, dim=PHI_DIM, hid=16):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(dim, hid), nn.ReLU(),
                                 nn.Linear(hid, 1))

    def forward(self, p):
        return self.net(p).squeeze(-1)


def scan(fam, model, scaler, device, labelled: bool):
    """One pass. Returns (records) with per-edge phi, mean-edge, and label."""
    fn, labels = FAMS[fam]
    d = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
    lab = d["label"].astype(str).str.strip()
    d = d[~lab.str.endswith("- Attempted")].copy()
    lab = d["label"].astype(str).str.strip()
    if labelled:
        if not lab.isin(labels).any():
            raise ValueError(f"{fam}: no rows match {sorted(labels)} in {fn}")
        bad_src = set(d["src_ip"][lab.isin(labels)])
        if not bad_src:
            raise ValueError(f"{fam}: attack rows but no attacker host")
    d = d.sort_values("timestamp")
    out = []
    for wi, (_, w) in enumerate(d.groupby(_window_key(d, 60))):
        gs = build_graphs(w, window_seconds=60, feature_set="v2")
        if not gs:
            continue
        g = gs[0]
        with torch.no_grad():
            n = model.node_scores(scaler.transform(g.x).to(device),
                                  g.edge_index.to(device)).cpu().numpy()
        ei = g.edge_index.cpu().numpy()
        if ei.shape[1] == 0:
            continue
        src = ei[0]
        dst = ei[1]
        n_src, n_dst = n[src], n[dst]
        deg_src = np.bincount(src, minlength=len(n)).astype(float)
        deg_dst = np.bincount(dst, minlength=len(n)).astype(float)
        P = phi(n_src, n_dst, deg_src[src], deg_dst[dst])
        mean_e = (n_src + n_dst) / 2.0
        y = None
        if labelled:
            y = np.array([1 if g.hosts[s_] in bad_src else 0 for s_ in src])
        out.append({"win": wi, "P": P, "mean": mean_e, "y": y})
    return out


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
    res = {"phi_dim": PHI_DIM, "families": {}, "seeds": sorted(CKPT)}
    print(f"device={device}")
    for fam in FAMS:
        res["families"][fam] = {}
        for sd in sorted(CKPT):
            blob = torch.load(DET / CKPT[sd], map_location="cpu", weights_only=True)
            require_scaler_match(blob, NodeScaler().load_state_dict(blob["scaler"]),
                                 f"E52 {CKPT[sd]}")
            model = GraphAutoencoder(in_dim=19)
            model.load_state_dict(blob["model"]); model.eval().to(device)
            scaler = NodeScaler().load_state_dict(blob["scaler"])

            # TRAIN split = monday benign only, same protocol as every model here
            mon = normalize_columns(pd.read_csv(CLEAN / "monday.csv", low_memory=True))
            mlab = mon["label"].astype(str).str.strip().str.upper()
            mon = mon[mlab == "BENIGN"].sort_values("timestamp")
            tr_blocks = []
            for _, w in mon.groupby(_window_key(mon, 60)):
                gs = build_graphs(w, window_seconds=60, feature_set="v2")
                if not gs:
                    continue
                g = gs[0]
                with torch.no_grad():
                    n = model.node_scores(scaler.transform(g.x).to(device),
                                          g.edge_index.to(device)).cpu().numpy()
                ei = g.edge_index.cpu().numpy()
                if ei.shape[1] == 0:
                    continue
                src, dst = ei[0], ei[1]
                ds = np.bincount(src, minlength=len(n)).astype(float)
                dd = np.bincount(dst, minlength=len(n)).astype(float)
                tr_blocks.append(phi(n[src], n[dst], ds[src], dd[dst]))
            Ptr = np.concatenate(tr_blocks, axis=0)
            # NB: named feat_mu/feat_sd, NOT mu/sd -- `sd` is the seed variable
            # in this loop and shadowing it silently broke the RNG seed.
            feat_mu, feat_sd = Ptr.mean(0), Ptr.std(0) + EPS
            Ptr = (Ptr - feat_mu) / feat_sd
            Ptr_t = torch.tensor(Ptr, dtype=torch.float32, device=device)

            head = EdgeHead().to(device)
            opt = torch.optim.Adam(head.parameters(), lr=1e-2)
            lossf = nn.MSELoss()
            best, best_state = float("inf"), None
            n_val = max(1, int(len(Ptr_t) * 0.2))
            tr_i, va_i = np.arange(len(Ptr_t) - n_val), np.arange(len(Ptr_t) - n_val,
                                                                  len(Ptr_t))
            for ep in range(30):
                head.train()
                perm = np.random.default_rng(sd * 100 + ep).permutation(tr_i)
                for i in range(0, len(perm), 4096):
                    b = torch.tensor(perm[i:i + 4096], device=device)
                    opt.zero_grad()
                    loss = lossf(head(Ptr_t[b]), Ptr_t[b][:, 0])
                    loss.backward(); opt.step()
                head.eval()
                with torch.no_grad():
                    vl = lossf(head(Ptr_t[torch.tensor(va_i, device=device)]),
                               Ptr_t[torch.tensor(va_i, device=device)][:, 0]).item()
                if vl < best:
                    best, best_state = vl, {k: v.detach().clone()
                                            for k, v in head.state_dict().items()}

            ev = scan(fam, model, scaler, device, labelled=True)
            require_window_groups(np.concatenate(
                [np.full(len(b["y"]), b["win"]) for b in ev]),
                sum(len(b["y"]) for b in ev), context=f"E52 {fam}")
            Y = np.concatenate([b["y"] for b in ev])
            Pev = np.concatenate([b["P"] for b in ev])
            MEAN = np.concatenate([b["mean"] for b in ev])
            WIN = np.concatenate([np.full(len(b["y"]), b["win"]) for b in ev])
            Pev_n = (Pev - feat_mu) / feat_sd

            R = pd.DataFrame(Pev_n)
            R["win"] = WIN
            # within-window rank for BOTH arms -> like-for-like production metric
            R["_m"] = MEAN
            mean_rank = R.groupby("win")["_m"].transform(rk).to_numpy()
            R["_h"] = head(torch.tensor(Pev_n, dtype=torch.float32,
                                        device=device)).detach().cpu().numpy()
            head_rank = R.groupby("win")["_h"].transform(rk).to_numpy()

            a_mean = auc(Y, mean_rank)
            a_head = auc(Y, head_rank)
            res["families"][fam][str(sd)] = {
                "fixed_mean": None if a_mean is None else round(a_mean, 4),
                "learned_head": None if a_head is None else round(a_head, 4),
                "delta": None if (a_mean is None or a_head is None)
                         else round(a_head - a_mean, 4),
                "n_edges": int(len(Y)), "n_atk": int(Y.sum()),
                "head_val_loss": round(float(best), 6),
                "head_params": sum(p.numel() for p in head.parameters()),
            }
            print(f"  {fam:13s} seed {sd}  fixed {a_mean:.4f}  head {a_head:.4f}"
                  f"  delta {a_head - a_mean:+.4f}", flush=True)

    print("\n" + "=" * 74)
    for fam in FAMS:
        v = res["families"][fam]
        fm = np.array([x["fixed_mean"] for x in v.values() if x["fixed_mean"]])
        hd = np.array([x["learned_head"] for x in v.values()
                       if x["learned_head"]])
        if len(fm) < 2:
            continue
        dlt = hd - fm
        pooled = np.sqrt((fm.std(ddof=1) ** 2 + hd.std(ddof=1) ** 2) / 2)
        z = dlt.mean() / max(pooled, 1e-9)
        res["families"][fam]["band"] = {
            "fixed_mean": round(float(fm.mean()), 4), "fixed_sd": round(float(fm.std(ddof=1)), 4),
            "learned_head": round(float(hd.mean()), 4), "head_sd": round(float(hd.std(ddof=1)), 4),
            "delta": round(float(dlt.mean()), 4), "z": round(float(z), 2),
            "verdict": "separated" if abs(z) > 2 else "inside noise"}
        print(f"{fam:13s} fixed {fm.mean():.4f}+-{fm.std(ddof=1):.4f}  "
              f"head {hd.mean():.4f}+-{hd.std(ddof=1):.4f}  "
              f"delta {dlt.mean():+.4f}  z={z:+.2f}  "
              f"[{res['families'][fam]['band']['verdict']}]")

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()
