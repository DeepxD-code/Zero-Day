"""
E16 report card on the CLEAN data (CICIDS2017_improved, CNS2022).

Same shipped v2 checkpoint, same 60s edge-AUC rule as E15 — the only
change is the data: relabeled ground truth, "- Attempted" attacks split
out (EXCLUDED from scoring: ambiguous by construction — that exclusion
IS the pollution fix), families cut by label instead of by file.

Family map (completed attacks only):
  Patator      FTP-Patator, SSH-Patator
  DoS          DoS Hulk/GoldenEye/Slowloris/Slowhttptest, Heartbleed
  WebAttacks   Web Attack - Brute Force/XSS/SQL Injection (completed)
  Infiltration Infiltration, Infiltration - Portscan
  Botnet       Botnet
  PortScan     Portscan
  DDoS         DDoS

    python detection/exp_e16_report_card_improved.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations


import json
import sys
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "detection"))
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "E14_risk_controls"))


import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import build_graphs, normalize_columns, _window_key
from gnn_model import GraphAutoencoder, NodeScaler


from eval_utils import auc_ci, slice_verdict

DATA = ROOT / "data" / "CICIDS2017_improved"
CKPT = Path(__file__).resolve().parents[2] / "detection" / "gnn_autoencoder_v1_logscale_v2.pt"
OUT = Path(__file__).resolve().parent / "exp_e16_report_card_improved.json"

DAYFILES = ["tuesday.csv", "wednesday.csv", "thursday.csv", "friday.csv"]

FAMS = {
    "Patator": {"FTP-Patator", "SSH-Patator"},
    "DoS": {"DoS Hulk", "DoS GoldenEye", "DoS Slowloris",
            "DoS Slowhttptest", "Heartbleed"},
    "WebAttacks": {"Web Attack - Brute Force", "Web Attack - XSS",
                   "Web Attack - SQL Injection"},
    "Infiltration": {"Infiltration", "Infiltration - Portscan"},
    "Botnet": {"Botnet"},
    "PortScan": {"Portscan"},
    "DDoS": {"DDoS"},
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    from sklearn.metrics import roc_auc_score
    import argparse as _ap
    _p = _ap.ArgumentParser()
    _p.add_argument("--ckpt", default=str(CKPT))
    _p.add_argument("--out", default=str(OUT))
    _a = _p.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    blob = torch.load(_a.ckpt, map_location="cpu", weights_only=True)
    model = GraphAutoencoder(in_dim=19)
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = NodeScaler().load_state_dict(blob["scaler"])
    print(f"shipped {CKPT.name} on {device} | clean data", flush=True)

    df = pd.concat([pd.read_csv(DATA / f, low_memory=True) for f in DAYFILES],
                   ignore_index=True)
    df = normalize_columns(df)
    df = df[df["src_ip"].map(lambda v: isinstance(v, str))
            & df["dst_ip"].map(lambda v: isinstance(v, str))]
    lab = df["label"].astype(str).str.strip()
    attempted = lab.str.endswith("- Attempted")
    print(f"flows {len(df)} attempted-excluded {int(attempted.sum())}",
          flush=True)
    df = df[~attempted].copy()
    # NOTE (E17 fix): _window_key is RELATIVE to df.min(), so a concatenated
    # multi-day df collides days into shared windows. Score each day-file
    # separately (absolute per-day windows), pool edges per family after.
    dayframes = []
    for f in DAYFILES:
        d = normalize_columns(pd.read_csv(DATA / f, low_memory=True))
        d = d[d["src_ip"].map(lambda v: isinstance(v, str))
              & d["dst_ip"].map(lambda v: isinstance(v, str))]
        l = d["label"].astype(str).str.strip()
        d = d[~l.str.endswith("- Attempted")].copy()
        d = d.sort_values("timestamp")
        d.attrs["day"] = f
        dayframes.append(d)

    DAY_OF = {"Patator": "tuesday.csv", "DoS": "wednesday.csv",
              "WebAttacks": "thursday.csv", "Infiltration": "thursday.csv",
              "Botnet": "friday.csv", "PortScan": "friday.csv", "DDoS": "friday.csv"}

    card = {}
    for fam, labels in FAMS.items():
        # E19 fix: score each family on its own day-file only. Pooling
        # benign edges from other days dilutes pooled AUC (Inf 0.76 pooled
        # vs 0.93 per-day).
        d = [x for x in dayframes if x.attrs.get("day") == DAY_OF[fam]][0]
        lab_d = d["label"].astype(str).str.strip()
        ys, ss = [], []
        n_graphs = 0
        for _, w in d.groupby(_window_key(d, 60)):
            gs = build_graphs(w, window_seconds=60, feature_set="v2")
            if not gs:
                continue
            g = gs[0]
            n_graphs += 1
            with torch.no_grad():
                ns = model.node_scores(scaler.transform(g.x).to(device),
                                       g.edge_index.to(device)).cpu().numpy()
            ei = g.edge_index.cpu().numpy()
            rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
            o = np.argsort(np.argsort(rel))
            r = o / max(len(rel) - 1, 1)
            wl = lab_d.loc[w.index]
            fam_srcs = set(w["src_ip"][wl.isin(labels).to_numpy()])
            for e in range(g.num_edges):
                src = g.hosts[int(ei[0, e])]
                ys.append(1 if src in fam_srcs else 0)
                ss.append(float(r[e]))
        y = np.array(ys)
        s = np.array(ss)
        auc = float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else None
        n_pos = int(y.sum())
        order = np.argsort(-s)
        atk_pos = (np.where(y[order] == 1)[0] + 1).tolist()
        row = {"edges": len(y), "graphs": n_graphs, "n_atk_edges": n_pos,
               "edge_auc": auc, "ci95": auc_ci(auc, n_pos, len(y) - n_pos),
               "verdict": slice_verdict(n_pos),
               "best_attacker_rank": min(atk_pos) if atk_pos else None,
               "recall_at_100": float((np.array(atk_pos) <= 100).mean())
               if atk_pos else None}
        card[fam] = row
        print(f"{fam:12s} AUC {auc} CI {row['ci95']} "
              f"best_rank {row['best_attacker_rank']} "
              f"atk {n_pos}/{len(y)} {row['verdict'][:16]}", flush=True)
    Path(_a.out).write_text(json.dumps(card, indent=1))
    print(f"-> {_a.out}")


if __name__ == "__main__":
    main()
