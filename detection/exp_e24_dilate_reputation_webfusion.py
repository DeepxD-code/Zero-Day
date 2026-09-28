"""
E24: reputation-vs-dilate (PortScan, original data, shipped ckpt) +
     Web fused band (clean Thursday, improved models, 4 seeds).

(a) E12 showed dilate x2/x5 kills 60s windows (0.87->0.36->0.06). Question:
    does causal running-mean reputation catch what windows miss? Arms per
    dilate factor: single-window rank vs causal reputation edge AUC.
(b) Web graph flips across seeds (0.813+-0.091); M5a-flow holds
    (0.895+-0.026). Question: fused Web band ~0.9 tight? Arms per seed:
    m5b/m5a/noisyor/rankmax/repfuse, within-window-rank metric (E21 rule).

    python detection/exp_e24_dilate_reputation_webfusion.py
Branch-only (exp/host-seqae-p37). Long GPU run.
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
sys.path.insert(0, str(ROOT / "harness"))

from graph_builder import build_graphs, normalize_columns, read_flows, _window_key
from gnn_model import GraphAutoencoder, NodeScaler
from exp_m5a_revival import flow_matrix, build_ctx, MinMax, CtxScaler, RevivedAE
from graph_techniques import spread_dilate

OUT = Path(__file__).resolve().parent / "exp_e24_results.json"
ORIG_PS = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"
SHIPPED = Path(__file__).resolve().parent / "gnn_autoencoder_v1_logscale_v2.pt"
CLEAN_THU = ROOT / "data/CICIDS2017_improved/thursday.csv"
WEB_LABELS = {"Web Attack - Brute Force", "Web Attack - XSS",
              "Web Attack - SQL Injection"}
M5B_I = {0: "gnn_autoencoder_improved_monday_v2.pt",
         1: "gnn_improved_s1.pt", 2: "gnn_improved_s2.pt",
         3: "gnn_improved_s3.pt"}
M5A_I = {0: "m5a_revived_improved_ctx.pt",
         1: "m5a_revived_improved_s1.pt", 2: "m5a_revived_improved_s2.pt",
         3: "m5a_revived_improved_s3.pt"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def r01(s):
    o = np.argsort(np.argsort(np.asarray(s, dtype=float)))
    return o / max(len(s) - 1, 1)


def main():
    from sklearn.metrics import roc_auc_score
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    res = {"dilate_reputation": {}, "web_fusion": {}}
    # ---- (a) dilate x reputation (original PortScan, shipped ckpt) ----
    blob = torch.load(SHIPPED, map_location="cpu", weights_only=True)
    m = GraphAutoencoder(in_dim=19)
    m.load_state_dict(blob["model"]); m.eval().to(device)
    sc = NodeScaler().load_state_dict(blob["scaler"])
    day = normalize_columns(read_flows(ORIG_PS))
    ATK = "172.16.0.1"
    for f in [1, 2, 5]:
        df = day if f == 1 else spread_dilate(day, ATK, f)
        df = df.sort_values("timestamp")
        seq = []
        for _, w in df.groupby(_window_key(df, 60)):
            gs = build_graphs(w, window_seconds=60, feature_set="v2")
            if not gs:
                continue
            g = gs[0]
            with torch.no_grad():
                ns = m.node_scores(sc.transform(g.x).to(device),
                                   g.edge_index.to(device)).cpu().numpy()
            seq.append((g, ns))
        full = {}
        for g, ns in seq:
            for h, s in zip(g.hosts, ns):
                full.setdefault(h, []).append(float(s))
        fullM = {h: float(np.mean(v)) for h, v in full.items()}
        Yw, Sw, Yc, Sc = [], [], [], []
        run = {}
        for g, ns in seq:
            for h, s in zip(g.hosts, ns):
                run.setdefault(h, []).append(float(s))
            ei = g.edge_index.cpu().numpy()
            rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
            r = r01(rel)
            for e in range(g.num_edges):
                src, dst = g.hosts[int(ei[0, e])], g.hosts[int(ei[1, e])]
                y = 1 if src == ATK else 0
                Yw.append(y); Sw.append(float(r[e]))
                Yc.append(y)
                Sc.append((np.mean(run[src]) + np.mean(run[dst])) / 2)
        Yw = np.array(Yw)
        res["dilate_reputation"][f"x{f}"] = {
            "window": round(float(roc_auc_score(Yw, np.array(Sw))), 4),
            "reputation": round(float(roc_auc_score(np.array(Yc), np.array(Sc))), 4)}
        print(f"dilate x{f}: window {res['dilate_reputation'][f'x{f}']['window']} "
              f"reputation {res['dilate_reputation'][f'x{f}']['reputation']}", flush=True)
    # ---- (b) Web fused band (clean Thursday, improved models) ----
    df = normalize_columns(pd.read_csv(CLEAN_THU, low_memory=True))
    lab = df["label"].astype(str).str.strip()
    df = df[~lab.str.endswith("- Attempted")].copy()
    lab = df["label"].astype(str).str.strip()
    df = df.sort_values("timestamp")
    band = {a: [] for a in ["m5b", "m5a", "noisyor", "rankmax", "repfuse"]}
    DET = Path(__file__).resolve().parent
    for sd in [0, 1, 2, 3]:
        gb = torch.load(DET / M5B_I[sd], map_location="cpu", weights_only=True)
        m5b = GraphAutoencoder(in_dim=19)
        m5b.load_state_dict(gb["model"]); m5b.eval().to(device)
        gsc = NodeScaler().load_state_dict(gb["scaler"])
        ra = torch.load(DET / M5A_I[sd], map_location="cpu", weights_only=False)
        rev = RevivedAE(ra["input_dim"])
        rev.load_state_dict(ra["state_dict"]); rev.eval().to(device)
        canon = ra["canonical"]
        fmm = MinMax(); fmm.lo, fmm.hi = ra["flow_lo"], ra["flow_hi"]
        csc = CtxScaler(); csc.lo, csc.hi = ra["ctx_lo"], ra["ctx_hi"]
        FB = {"Y": [], "m5b": [], "m5a": [], "noisyor": [],
              "rankmax": [], "repfuse": [], "win": []}
        run_b, run_a, wi = {}, {}, 0
        for _, w in df.groupby(_window_key(df, 60)):
            wl = lab.loc[w.index]
            fs = set(w["src_ip"][wl.isin(WEB_LABELS).to_numpy()])
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
                fsc = rev.anomaly_score(torch.tensor(X).to(device)).cpu().numpy()
            wr = w.reset_index(drop=True)
            hm = {}
            for i, r_ in enumerate(fsc):
                hm[wr.loc[i, "src_ip"]] = max(hm.get(wr.loc[i, "src_ip"], 0), float(r_))
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
                s_, d_ = g.hosts[int(ei[0, e])], g.hosts[int(ei[1, e])]
                y = 1 if s_ in fs else 0
                rp = ((np.mean(run_b[s_]) + np.mean(run_b[d_])) / 2 * 0.5
                      + (np.mean(run_a.get(s_, [0])) + np.mean(run_a.get(d_, [0]))) / 2 * 0.5)
                FB["Y"].append(y); FB["m5b"].append(float(aa[e]))
                FB["m5a"].append(float(bb[e]))
                FB["noisyor"].append(float(1 - (1 - ra_[e]) * (1 - rb_[e])))
                FB["rankmax"].append(float(max(ra_[e], rb_[e])))
                FB["repfuse"].append(float(rp)); FB["win"].append(wi)
            wi += 1
        yy = np.array(FB["Y"]); wins = np.array(FB["win"])
        for arm in ["m5b", "m5a", "noisyor", "rankmax", "repfuse"]:
            rr = np.zeros(len(yy)); v = np.array(FB[arm])
            for wv in np.unique(wins):
                mk = wins == wv
                rr[mk] = r01(v[mk])
            a = float(roc_auc_score(yy, rr)) if 0 < yy.sum() < len(yy) else None
            band[arm].append(a)
        print(f"web seed {sd}: " + " ".join(
            f"{a}={band[a][-1]:.3f}" for a in band), flush=True)
    res["web_fusion"] = {a: {"mean": float(np.mean(v)), "std": float(np.std(v)),
                             "seeds": v} for a, v in band.items()}
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
