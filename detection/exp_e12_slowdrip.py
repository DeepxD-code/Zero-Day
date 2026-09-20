"""
E12 (V4-U1): slow-drip timing vs shipped M5b on PortScan day.

TANTRA/TEGA-style timing-only evasion: same endpoints, reshaped timing.
spread_dilate (factors 1,2,5,10): stretches the attacker timeline, diluting
per-window degree at zero extra-edge cost (time IS the cost).
burst_shape (front/back/even): intra-window reshaping only — tests IAT and
window-boundary sensitivity. Shipped v2 checkpoint, 60s graphs, edge AUC.

    python detection/exp_e12_slowdrip.py
Branch-only (exp/host-seqae-p37). Techniques flagged B-into-D in
harness/graph_techniques.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler
from exp_a1_edge_injection import edge_auc
from graph_techniques import burst_shape, spread_dilate

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"
CKPT = Path(__file__).resolve().parent / "gnn_autoencoder_v1_logscale_v2.pt"
OUT = Path(__file__).resolve().parent / "exp_e12_slowdrip.json"
ATTACKER = "172.16.0.1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    blob = torch.load(CKPT, map_location="cpu", weights_only=True)
    model = GraphAutoencoder(in_dim=19)
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = NodeScaler().load_state_dict(blob["scaler"])
    day = normalize_columns(read_flows(DAY))
    res = {"dilate": {}, "burst": {}}
    for f in [1, 2, 5, 10]:
        df = day if f == 1 else spread_dilate(day, ATTACKER, f)
        g = build_graphs(df, window_seconds=60, feature_set="v2")
        a, n = edge_auc(g, model, scaler, device, {ATTACKER})
        res["dilate"][str(f)] = {"auc": a, "n_edges": n, "n_graphs": len(g)}
        print(f"dilate x{f:2d}: AUC {a} (graphs {len(g)})")
    for mode in ["even", "front", "back"]:
        df = burst_shape(day, ATTACKER, mode)
        g = build_graphs(df, window_seconds=60, feature_set="v2")
        a, n = edge_auc(g, model, scaler, device, {ATTACKER})
        res["burst"][mode] = {"auc": a, "n_edges": n}
        print(f"burst {mode:5s}: AUC {a}")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
