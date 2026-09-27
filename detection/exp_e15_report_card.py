"""
E15 report card: all 7 held-out families on the SHIPPED v2 checkpoint.

No retraining (uses detection/gnn_autoencoder_v1_logscale_v2.pt).
Per family: edge AUC (shipped 60s rule), attacker ranks, 443-conditioned
AUC + Hanley-McNeil 95% CI (eval_utils), slice verdict. Honest numbers:
AUC is threshold-free ranking; operating points come from top_k at
serve time (E14), never frozen Monday thresholds (E13 R1).

    python detection/exp_e15_report_card.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import build_graphs, normalize_columns, read_flows, _window_key
from gnn_model import GraphAutoencoder, NodeScaler
from eval_utils import auc_ci, slice_verdict

FLOWS = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling"
CKPT = Path(__file__).resolve().parent / "gnn_autoencoder_v1_logscale_v2.pt"
OUT = Path(__file__).resolve().parent / "exp_e15_report_card.json"

FAMS = {
    "Patator": "Tuesday-WorkingHours.pcap_ISCX.csv",
    "DoS": "Wednesday-workingHours.pcap_ISCX.csv",
    "WebAttacks": "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    "Infiltration": "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "Botnet": "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "PortScan": "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "DDoS": "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    from evaluate_gnn import malicious_hosts
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
    print(f"shipped {CKPT.name} on {device}", flush=True)

    card = {}
    for fam, fn in FAMS.items():
        df = normalize_columns(read_flows(FLOWS / fn))
        df = df[df["src_ip"].map(lambda v: isinstance(v, str))
                & df["dst_ip"].map(lambda v: isinstance(v, str))]
        bad = set(malicious_hosts(df))
        df = df.sort_values("timestamp")
        ys, ss, ports = [], [], []
        n_graphs = 0
        for _, w in df.groupby(_window_key(df, 60)):
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
            dom = w.groupby(["src_ip", "dst_ip"])["dst_port"].agg(
                lambda s: s.mode().iloc[0])
            for e in range(g.num_edges):
                src = g.hosts[int(ei[0, e])]
                dst = g.hosts[int(ei[1, e])]
                ys.append(1 if src in bad else 0)
                ss.append(float(r[e]))
                ports.append(int(dom.loc[(src, dst)]))
        y = np.array(ys)
        s = np.array(ss)
        auc = float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else None
        n_pos, n_neg = int(y.sum()), int(len(y) - y.sum())
        # attacker ranks among all edges (best rank of any attacker edge)
        order = np.argsort(-s)
        ranked = y[order]
        atk_positions = (np.where(ranked == 1)[0] + 1).tolist()
        best = min(atk_positions) if atk_positions else None
        # 443-conditioned slice
        m443 = np.array(ports) == 443
        ya, sa = y[m443], s[m443]
        a443 = float(roc_auc_score(ya, sa)) if 0 < ya.sum() < len(ya) else None
        row = {
            "flows": len(df), "graphs": n_graphs, "edges": len(y),
            "attackers": sorted(bad), "n_atk_edges": n_pos,
            "edge_auc": auc, "ci95": auc_ci(auc, n_pos, n_neg),
            "best_attacker_rank": best,
            "recall_at_100": float((np.array(atk_positions) <= 100).mean())
            if atk_positions else None,
            "tls443": {"auc": a443, "n": int(m443.sum()),
                       "n_atk": int(ya.sum()),
                       "ci95": auc_ci(a443, int(ya.sum()),
                                      int(m443.sum()) - int(ya.sum())),
                       "verdict": slice_verdict(int(ya.sum()))},
        }
        card[fam] = row
        print(f"{fam:12s} AUC {auc} CI {row['ci95']} "
              f"best_rank {best} atk_edges {n_pos}/{len(y)} "
              f"443 {a443} ({row['tls443']['verdict'][:16]})", flush=True)
    Path(_a.out).write_text(json.dumps(card, indent=1))
    print(f"-> {_a.out}")


if __name__ == "__main__":
    main()
