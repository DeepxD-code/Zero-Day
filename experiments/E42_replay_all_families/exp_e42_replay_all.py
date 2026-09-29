"""
E30b: replay-tune transfer across the other six families.

E29 proved the replay-tune recipe on PortScan only:
  improved-only  ORIG 0.5477 / CLEAN 0.9708
  replay-tune    ORIG 0.9056 / CLEAN 0.9033
PortScan is the EASIEST case (most distinctive topology in the suite), so
"transfer works" is currently a one-family claim.

This applies the identical recipe to every remaining family and reports the
transfer table. Recipe unchanged from E29:
  start from gnn_improved_s0.pt (clean-data model)
  20 epochs, LR 1e-4, batches = original Monday graphs + 20% replay of
  clean Monday graphs.

    python experiments/E42_replay_all_families/exp_e42_replay_all.py
Branch-only (exp/host-seqae-p37).
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

from graph_builder import build_graphs, normalize_columns, read_flows, _window_key
from gnn_model import GraphAutoencoder, NodeScaler, set_seed

OUT = Path(__file__).resolve().parent / "exp_e42_replay_all.json"
DET = ROOT / "detection"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
ORIG = ROOT / "data" / "GeneratedLabelledFlows" / "TrafficLabelling"

# clean-data families: label -> labels
CLEAN_FAMS = {
    "Patator":      (["tuesday.csv"],   {"FTP-Patator", "SSH-Patator"}),
    "DoS":          (["wednesday.csv"], {"DoS Hulk", "DoS GoldenEye", "DoS Slowloris",
                                         "DoS Slowhttptest", "Heartbleed"}),
    "WebAttacks":   (["thursday.csv"],  {"Web Attack - Brute Force", "Web Attack - XSS",
                                         "Web Attack - SQL Injection"}),
    "Infiltration": (["thursday.csv"],  {"Infiltration", "Infiltration - Portscan"}),
    "Botnet":       (["friday.csv"],    {"Botnet"}),
    "PortScan":     (["friday.csv"],    {"Portscan"}),
    "DDoS":         (["friday.csv"],    {"DDoS"}),
}
# original-data families: label -> file, fixed attacker
ORIG_FAMS = {
    "Patator":      "Tuesday-WorkingHours.pcap_ISCX.csv",
    "DoS":          "Wednesday-workingHours.pcap_ISCX.csv",
    "WebAttacks":   "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    "Infiltration": "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "Botnet":       "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "PortScan":     "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "DDoS":         "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(path: Path):
    b = torch.load(path, map_location="cpu", weights_only=True)
    m = GraphAutoencoder(in_dim=19)
    m.load_state_dict(b["model"])
    sc = NodeScaler().load_state_dict(b["scaler"])
    return m, sc


def _score(model, scaler, window, device):
    gs = build_graphs(window, window_seconds=60, feature_set="v2")
    if not gs:
        return None
    g = gs[0]
    with torch.no_grad():
        ns = model.node_scores(scaler.transform(g.x).to(device),
                               g.edge_index.to(device)).cpu().numpy()
    ei = g.edge_index.cpu().numpy()
    rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
    o = np.argsort(np.argsort(rel))
    return g, o / max(len(rel) - 1, 1)


def _auc(model, scaler, df, bad, device):
    """within-window rank -> pool -> edge AUC. df must be one day only."""
    ys, ss = [], []
    for _, w in df.sort_values("timestamp").groupby(_window_key(df, 60)):
        out = _score(model, scaler, w, device)
        if out is None:
            continue
        g, r = out
        ei = g.edge_index.cpu().numpy()
        for e in range(g.num_edges):
            ys.append(1 if g.hosts[int(ei[0, e])] in bad else 0)
            ss.append(float(r[e]))
    y = np.array(ys)
    if len(y) == 0 or y.sum() == 0 or y.sum() == len(y):
        return None, 0
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, np.array(ss))), int(y.sum())


def main():
    from evaluate_gnn import malicious_hosts
    import random

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seed = 0
    set_seed(seed)

    # ---- training graphs -------------------------------------------------
    orig_monday = normalize_columns(read_flows(ORIG / "Monday-WorkingHours.pcap_ISCX.csv"))
    orig_monday = orig_monday[
        orig_monday["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    orig_monday = orig_monday[orig_monday["src_ip"].map(lambda v: isinstance(v, str))
                               & orig_monday["dst_ip"].map(lambda v: isinstance(v, str))]
    clean_monday = normalize_columns(read_flows(CLEAN / "monday.csv"))
    clean_monday = clean_monday[
        clean_monday["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    GA = build_graphs(orig_monday, window_seconds=60, feature_set="v2")
    GI = build_graphs(clean_monday, window_seconds=60, feature_set="v2")
    replay = random.Random(seed).sample(GI, k=int(0.2 * len(GA)))
    train_graphs = GA + replay
    print(f"train: {len(GA)} original + {len(replay)} replay = {len(train_graphs)}",
          flush=True)

    # ---- replay-tune every seed (cheap enough to band) -------------------
    models = {}
    for sd in [0, 1, 2, 3]:
        m, sc = load(DET / "gnn_improved_s0.pt")
        m.to(device)
        sc = NodeScaler(log=True).fit(train_graphs)   # scaler on the MIX
        opt = torch.optim.Adam(m.parameters(), lr=1e-4)
        lf = nn.MSELoss()
        m.train()
        rng = np.random.default_rng(sd)
        for _ in range(20):
            for i in rng.permutation(len(train_graphs)):
                g = train_graphs[i]
                x = sc.transform(g.x).to(device)
                loss = lf(m(x, g.edge_index.to(device)), x)
                opt.zero_grad(); loss.backward(); opt.step()
        m.eval()
        models[sd] = (m, sc)
        print(f"  seed {sd} replay-tuned", flush=True)

    base, _ = load(DET / "gnn_improved_s0.pt")
    base = base.to(device).eval()

    res = {}
    for fam, (files, labels) in CLEAN_FAMS.items():
        row = {}
        # clean side
        ys, ss = [], []
        for fn in files:
            d = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
            lab = d["label"].astype(str).str.strip()
            d = d[~lab.str.endswith("- Attempted")].copy()
            lab = d["label"].astype(str).str.strip()
            bad_src = set(d["src_ip"][lab.isin(labels)])
            d = d.sort_values("timestamp")
            for _, w in d.groupby(_window_key(d, 60)):
                g, r = _score(base, models[0][1], w, device) or (None, None)
                if g is None:
                    continue
                ei = g.edge_index.cpu().numpy()
                for e in range(g.num_edges):
                    ys.append(1 if g.hosts[int(ei[0, e])] in bad_src else 0)
                    ss.append(float(r[e]))
        y = np.array(ys)
        row["clean_base"] = float(roc_auc_score(y, np.array(ss))) if 0 < y.sum() < len(y) else None
        row["clean_n"] = int(y.sum())
        # original side
        d = normalize_columns(read_flows(ORIG / ORIG_FAMS[fam]))
        d = d[d["src_ip"].map(lambda v: isinstance(v, str))
              & d["dst_ip"].map(lambda v: isinstance(v, str))]
        bad = set(malicious_hosts(d))
        a_base, n = _auc(base, models[0][1], d, bad, device)
        row["orig_base"] = a_base
        row["orig_n"] = n
        a_rep, _ = _auc(models[0][0], models[0][1], d, bad, device)
        row["orig_replay"] = a_rep
        # replay model on clean side
        ys2, ss2 = [], []
        for fn in files:
            d2 = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
            lab2 = d2["label"].astype(str).str.strip()
            d2 = d2[~lab2.str.endswith("- Attempted")].copy()
            lab2 = d2["label"].astype(str).str.strip()
            bad_src = set(d2["src_ip"][lab2.isin(labels)])
            d2 = d2.sort_values("timestamp")
            for _, w in d2.groupby(_window_key(d2, 60)):
                g, r = _score(models[0][0], models[0][1], w, device) or (None, None)
                if g is None:
                    continue
                ei = g.edge_index.cpu().numpy()
                for e in range(g.num_edges):
                    ys2.append(1 if g.hosts[int(ei[0, e])] in bad_src else 0)
                    ss2.append(float(r[e]))
        y2 = np.array(ys2)
        row["clean_replay"] = float(roc_auc_score(y2, np.array(ss2))) if 0 < y2.sum() < len(y2) else None
        res[fam] = row
        print(f"{fam:13s} ORIG base {row['orig_base']} -> replay {row['orig_replay']}  |  "
              f"CLEAN base {row['clean_base']} -> replay {row['clean_replay']}", flush=True)

    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    import warnings
    from sklearn.metrics import roc_auc_score  # noqa: F401  (used in main)
    main()
