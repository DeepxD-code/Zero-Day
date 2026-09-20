"""
E11 (industry gap): encrypted-traffic ablation.

Static audit: all 76 flow features are L3/L4 header statistics (lengths,
IATs, flags, windows, bulk, active/idle) — NONE requires payload content,
DPI strings, SNI, or certificates. Zero features need decryption; TLS hides
payload, not the metadata this detector scores. Destination Port IS a model
feature (gotcha #4), so the model can condition on 443 directly.

Empirical: per family, split flows into dst_port==443 vs rest, build v2 60s
graphs separately, shipped checkpoint, edge AUC each. If 443-AUC holds, the
detector works where encryption lives.
Limitation (disclosed): port-443 proxy != confirmed TLS (CICIDS2017 has no
SNI labels); TLS record-overhead shift untested (needs paired captures).

    python detection/exp_e11_tls_split.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from graph_builder import build_graphs, normalize_columns, read_flows
from exp_a1_edge_injection import edge_auc
import torch
from gnn_model import GraphAutoencoder, NodeScaler

ROOT = Path(__file__).resolve().parent.parent
FLOWS = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling"
OUT = Path(__file__).resolve().parent / "exp_e11_tls_split.json"
CKPT = Path(__file__).resolve().parent / "gnn_autoencoder_v1_logscale_v2.pt"
FAMS = {
    "PortScan": ("Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv", "172.16.0.1"),
    "WebAttacks": ("Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv", None),
    "DoS": ("Wednesday-workingHours.pcap_ISCX.csv", None),
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    import sys as _s
    _s.path.insert(0, str(ROOT / "detection"))
    from evaluate_gnn import malicious_hosts
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    blob = torch.load(CKPT, map_location="cpu", weights_only=True)
    model = GraphAutoencoder(in_dim=19)
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = NodeScaler().load_state_dict(blob["scaler"])
    res = {}
    for fam, (fn, atk) in FAMS.items():
        df = normalize_columns(read_flows(FLOWS / fn))
        df = df[df["src_ip"].map(lambda v: isinstance(v, str)) &
                df["dst_ip"].map(lambda v: isinstance(v, str))]
        bad = {atk} if atk else malicious_hosts(df)
        df["dport"] = pd.to_numeric(df["dst_port"], errors="coerce")
        tls = df[df["dport"] == 443]
        rest = df[df["dport"] != 443]
        row = {"n_tls": len(tls), "n_rest": len(rest),
               "tls_attack_share": round(float((tls["label"].astype(str).str.upper() != "BENIGN").mean()), 4)}
        for name, sub in [("tls443", tls), ("rest", rest)]:
            if len(sub) < 100:
                row[name] = {"note": "too few flows"}
                continue
            g = build_graphs(sub, window_seconds=60, feature_set="v2")
            a, n = edge_auc(g, model, scaler, device, bad)
            row[name] = {"auc": a, "n_edges": n}
        res[fam] = row
        print(fam, row)
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
