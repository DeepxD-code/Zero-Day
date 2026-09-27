"""
E21: 4-seed band on clean data + fusion-rule shootout.

M5b seeds: gnn_autoencoder_improved_monday_v2.pt (s0), gnn_improved_s{1,2,3}.pt
M5a seeds: m5a_revived_improved_ctx.pt (s0), m5a_revived_improved_s{1,2,3}.pt
Per seed: full 7-family clean card (M5b-only, per-day files, 60s edge AUC).
Friday only: fusion arms for Botnet/PortScan/DDoS —
  m5b-only, m5a-only, noisyor, rank_max, reputation-fuse (causal running
  means fused 50/50, then edge-scored).
Rule wins only if best-or-tied everywhere (no per-family cherry-picking).

    python detection/exp_e21_band.py
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
sys.path.insert(0, str(ROOT / "experiments"))

from graph_builder import build_graphs, normalize_columns, _window_key
from gnn_model import GraphAutoencoder, NodeScaler
from exp_m5a_revival import flow_matrix, build_ctx, MinMax, CtxScaler, RevivedAE
from eval_utils import auc_ci

DATA = ROOT / "data" / "CICIDS2017_improved"
OUT = Path(__file__).resolve().parent / "exp_e21_band.json"
DET = Path(__file__).resolve().parent

M5B = {0: DET / "gnn_autoencoder_improved_monday_v2.pt",
       1: DET / "gnn_improved_s1.pt",
       2: DET / "gnn_improved_s2.pt",
       3: DET / "gnn_improved_s3.pt"}
M5A = {0: DET / "m5a_revived_improved_ctx.pt",
       1: DET / "m5a_revived_improved_s1.pt",
       2: DET / "m5a_revived_improved_s2.pt",
       3: DET / "m5a_revived_improved_s3.pt"}

FAMS = {"Patator": ("tuesday.csv", {"FTP-Patator", "SSH-Patator"}),
        "DoS": ("wednesday.csv", {"DoS Hulk", "DoS GoldenEye", "DoS Slowloris",
                                  "DoS Slowhttptest", "Heartbleed"}),
        "WebAttacks": ("thursday.csv", {"Web Attack - Brute Force",
                                        "Web Attack - XSS",
                                        "Web Attack - SQL Injection"}),
        "Infiltration": ("thursday.csv", {"Infiltration",
                                          "Infiltration - Portscan"}),
        "Botnet": ("friday.csv", {"Botnet"}),
        "PortScan": ("friday.csv", {"Portscan"}),
        "DDoS": ("friday.csv", {"DDoS"})}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def r01(s):
    o = np.argsort(np.argsort(np.asarray(s, dtype=float)))
    return o / max(len(s) - 1, 1)


def main():
    from sklearn.metrics import roc_auc_score
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    res = {"seeds": {}, "band": {}, "fusion": {}}
    for sd in [0, 1, 2, 3]:
        gb = torch.load(M5B[sd], map_location="cpu", weights_only=True)
        m5b = GraphAutoencoder(in_dim=19)
        m5b.load_state_dict(gb["model"])
        m5b.eval().to(device)
        gsc = NodeScaler().load_state_dict(gb["scaler"])
        ra = torch.load(M5A[sd], map_location="cpu", weights_only=False)
        rev = RevivedAE(ra["input_dim"])
        rev.load_state_dict(ra["state_dict"])
        rev.eval().to(device)
        canon = ra["canonical"]
        fmm = MinMax(); fmm.lo, fmm.hi = ra["flow_lo"], ra["flow_hi"]
        csc = CtxScaler(); csc.lo, csc.hi = ra["ctx_lo"], ra["ctx_hi"]
        seed_row, fusion_row = {}, {}
        for fam, (fn, labels) in FAMS.items():
            df = normalize_columns(pd.read_csv(DATA / fn, low_memory=True))
            lab = df["label"].astype(str).str.strip()
            df = df[~lab.str.endswith("- Attempted")].copy()
            lab = df["label"].astype(str).str.strip()
            df = df.sort_values("timestamp")
            Y, A, W = [], [], []
            FB = {"Y": [], "m5b": [], "m5a": [], "noisyor": [],
                  "rankmax": [], "repfuse": [], "win": []}
            run_b, run_a = {}, {}
            wi = 0
            for _, w in df.groupby(_window_key(df, 60)):
                wl = lab.loc[w.index]
                fs = set(w["src_ip"][wl.isin(labels).to_numpy()])
                gs0 = build_graphs(w, window_seconds=60, feature_set="v2")
                if not gs0:
                    continue
                g = gs0[0]
                with torch.no_grad():
                    ns = m5b.node_scores(gsc.transform(g.x).to(device),
                                         g.edge_index.to(device)).cpu().numpy()
                X = np.concatenate(
                    [fmm.transform(flow_matrix(w, canon)),
                     csc.transform(build_ctx(w, _window_key(w, 60)))], axis=1)
                with torch.no_grad():
                    fs_sc = rev.anomaly_score(torch.tensor(X).to(device)).cpu().numpy()
                wr = w.reset_index(drop=True)
                hm = {}
                for i, r_ in enumerate(fs_sc):
                    hm[wr.loc[i, "src_ip"]] = max(hm.get(wr.loc[i, "src_ip"], 0),
                                                  float(r_))
                for h, s in zip(g.hosts, ns):
                    run_b.setdefault(h, []).append(float(s))
                for h, s in hm.items():
                    run_a.setdefault(h, []).append(float(s))
                ei = g.edge_index.cpu().numpy()
                aa = (ns[ei[0]] + ns[ei[1]]) / 2.0
                bb = np.array([(hm.get(g.hosts[int(ei[0, e])], 0)
                                + hm.get(g.hosts[int(ei[1, e])], 0)) / 2.0
                               for e in range(g.num_edges)])
                ra_, rb_ = r01(aa), r01(bb)
                for e in range(g.num_edges):
                    y = 1 if g.hosts[int(ei[0, e])] in fs else 0
                    Y.append(y); A.append(float(aa[e])); W.append(wi)
                    if fn == "friday.csv":
                        s_, d_ = g.hosts[int(ei[0, e])], g.hosts[int(ei[1, e])]
                        rp = ((np.mean(run_b[s_]) + np.mean(run_b[d_])) / 2 * 0.5
                              + (np.mean(run_a.get(s_, [0])) + np.mean(run_a.get(d_, [0]))) / 2 * 0.5)
                        FB["Y"].append(y); FB["m5b"].append(float(aa[e]))
                        FB["m5a"].append(float(bb[e]))
                        FB["noisyor"].append(float(1 - (1 - ra_[e]) * (1 - rb_[e])))
                        FB["rankmax"].append(float(max(ra_[e], rb_[e])))
                        FB["repfuse"].append(float(rp)); FB["win"].append(wi)
                wi += 1
            y = np.array(Y)
            # within-window rank (production metric E16), then pool
            W = np.array(W)
            rr = np.zeros(len(y))
            _a = np.array(A)
            for wv in np.unique(W):
                m = W == wv
                rr[m] = r01(_a[m])
            auc = float(roc_auc_score(y, rr)) if 0 < y.sum() < len(y) else None
            seed_row[fam] = {"auc": auc, "n_atk": int(y.sum()), "n": len(y)}
            if fn == "friday.csv":
                fr = {}
                yy = np.array(FB["Y"])
                wins = np.array(FB["win"])
                # within-window rank for every arm (production metric), then pool
                ranked = {}
                for arm in ["m5b", "m5a", "noisyor", "rankmax", "repfuse"]:
                    rr = np.zeros(len(yy))
                    for wv in np.unique(wins):
                        m = wins == wv
                        rr[m] = r01(np.array(FB[arm])[m])
                    ranked[arm] = rr
                    v = rr
                    fr[arm] = float(roc_auc_score(yy, v)) if 0 < yy.sum() < len(yy) else None
                fusion_row[fam] = fr
        # reputation-fuse for friday families (causal running means, 50/50)
        # recomputed from pooled run_b/run_a across friday windows:
        res["seeds"][str(sd)] = {"card": seed_row, "fusion": fusion_row}
        print(f"seed {sd}: " + " ".join(
            f"{f}={seed_row[f]['auc']:.3f}" if seed_row[f]["auc"] else f"{f}=None"
            for f in FAMS), flush=True)
    # band stats
    for fam in FAMS:
        vs = [res["seeds"][str(s)]["card"][fam]["auc"] for s in [0, 1, 2, 3]]
        vs = [v for v in vs if v is not None]
        res["band"][fam] = {"mean": float(np.mean(vs)), "std": float(np.std(vs)),
                            "seeds": vs} if vs else None
    OUT.write_text(json.dumps(res, indent=1))
    print("band:")
    for fam, b in res["band"].items():
        print(f"  {fam:12s} {b['mean']:.4f}±{b['std']:.4f} {b['seeds']}")
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
