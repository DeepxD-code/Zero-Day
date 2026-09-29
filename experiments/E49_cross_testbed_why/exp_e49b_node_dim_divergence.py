"""E49b: is the cross-testbed gap a FLOW-COUNT difference, not a traffic difference?

E49 found: the two Mondays describe the same network (host Jaccard 0.9999, 9,709
vs 9,710 distinct hosts) but the improved extractor emits 371,624 benign flows
against the original's 529,918 -- **30% fewer flows for the same hosts on the
same day.**

The 19 graph node dimensions are all built from per-window aggregation:
out_degree, in_flows, bytes_sent, flows_per_out_peer, mean_duration and so on.
If the two extractors segment flows differently, then the SAME host behaviour
produces systematically different node values, and a model fitted to one corpus
sees the other as anomalous. That would be the mechanism E27/E29/E42 never
identified.

This measures the node dimensions directly, per corpus, per 60s window.

    python experiments/E49_cross_testbed_why/exp_e49b_node_dim_divergence.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import (build_graphs, node_feature_names, normalize_columns,
                           read_flows, _window_key)

ORIG = ROOT / "data" / "GeneratedLabelledFlows" / "TrafficLabelling"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
OUT = Path(__file__).resolve().parent / "exp_e49b_node_dim_divergence.json"


def node_matrices(path: Path, orig: bool):
    """Build v2 graphs and return per-window stacked node features."""
    # normalize_columns for BOTH sides: read_flows() returns the original
    # file's raw column names, where the label column is not "label".
    df = normalize_columns(read_flows(path) if orig
                           else pd.read_csv(path, low_memory=True))
    lab = df["label"].astype(str).str.strip().str.upper()
    df = df[lab == "BENIGN"]
    df = df.sort_values("timestamp")
    per_win, sizes = [], []
    for _, w in df.groupby(_window_key(df, 60)):
        gs = build_graphs(w, window_seconds=60, feature_set="v2")
        if not gs:
            continue
        g = gs[0]
        per_win.append(g.x.detach().cpu().numpy())
        sizes.append((g.num_nodes, g.num_edges))
    return per_win, np.array(sizes)


def ks(a, b):
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size < 20 or b.size < 20:
        return float("nan")
    grid = np.unique(np.concatenate([
        np.quantile(a, np.linspace(0, 1, 201)),
        np.quantile(b, np.linspace(0, 1, 201))]))
    ca = np.searchsorted(np.sort(a), grid, side="right") / a.size
    cb = np.searchsorted(np.sort(b), grid, side="right") / b.size
    return float(np.max(np.abs(ca - cb)))


def main():
    names = node_feature_names("v2")
    wo, so = node_matrices(ORIG / "Monday-WorkingHours.pcap_ISCX.csv", True)
    wc, sc = node_matrices(CLEAN / "monday.csv", False)

    Xo = np.concatenate(wo, axis=0) if wo else np.zeros((0, len(names)))
    Xc = np.concatenate(wc, axis=0) if wc else np.zeros((0, len(names)))

    print(f"windows: orig {len(wo)}  clean {len(wc)}")
    print(f"node rows: orig {len(Xo):,}  clean {len(Xc):,}")
    print(f"nodes/window: orig {so[:,0].mean():.1f}  clean {sc[:,0].mean():.1f}"
          f"   edges/window: orig {so[:,1].mean():.1f}  clean {sc[:,1].mean():.1f}")
    print(f"edges per node: orig {so[:,1].sum()/max(so[:,0].sum(),1):.3f}  "
          f"clean {sc[:,1].sum()/max(sc[:,0].sum(),1):.3f}")

    rows = []
    for i, nm in enumerate(names):
        a, b = Xo[:, i], Xc[:, i]
        mo, mc = float(np.mean(a)), float(np.mean(b))
        so_, sc_ = float(np.std(a)), float(np.std(b))
        # standardised mean shift: how many within-one-corpus SDs apart
        shift = abs(mo - mc) / max(np.sqrt((so_ ** 2 + sc_ ** 2) / 2), 1e-9)
        rows.append({"dim": i, "name": nm, "ks": round(ks(a, b), 4),
                     "mean_orig": round(mo, 4), "mean_clean": round(mc, 4),
                     "sd_orig": round(so_, 4), "sd_clean": round(sc_, 4),
                     "std_shift": round(shift, 3),
                     "median_ratio": (round(float(np.median(b) / np.median(a)), 3)
                                      if np.median(a) else None)})
    rows.sort(key=lambda r: -r["std_shift"])

    res = {
        "question": "do the 19 graph node dims differ systematically between "
                    "extractors for the same hosts/day?",
        "windows": {"orig": len(wo), "clean": len(wc)},
        "node_rows": {"orig": int(len(Xo)), "clean": int(len(Xc))},
        "per_window": {
            "orig": {"nodes_mean": float(so[:, 0].mean()),
                     "edges_mean": float(so[:, 1].mean()),
                     "edges_per_node": float(so[:, 1].sum() / max(so[:, 0].sum(), 1))},
            "clean": {"nodes_mean": float(sc[:, 0].mean()),
                      "edges_mean": float(sc[:, 1].mean()),
                      "edges_per_node": float(sc[:, 1].sum() / max(sc[:, 0].sum(), 1))},
        },
        "dims": rows,
    }
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")

    print(f"\n{'dim':<4}{'name':<26}{'KS':>7}{'std shift':>11}"
          f"{'mean_o':>12}{'mean_c':>12}{'med ratio':>11}")
    for r in rows:
        print(f"{r['dim']:<4}{r['name']:<26}{r['ks']:>7.3f}{r['std_shift']:>11.2f}"
              f"{r['mean_orig']:>12.3f}{r['mean_clean']:>12.3f}"
              f"{str(r['median_ratio']):>11}")
    big = [r for r in rows if r["std_shift"] > 1.0]
    print(f"\ndims shifted by more than 1 within-corpus SD: {len(big)}/19")
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
