"""E49c: causal confirmation that the TCP flow deficit CAUSES the node divergence.

E49 found: the extractors agree on UDP to 0.07% and disagree on TCP by 52%.
E49b found the 19 graph node dims diverge, worst on `tcp_frac`
(0.516 -> 0.036). That is a correlation between two observations.

This is the test that separates correlation from cause, and it needs no
synthetic manipulation of the data. The prediction is specific and falsifiable:

  If the mechanism is "the improved extractor loses TCP flow records, and the
  graph is built from those records", then:

    PREDICTED  UDP-only graphs  -> node dims AGREE between extractors
    PREDICTED  TCP-only graphs  -> node dims DIVERGE between extractors
    PREDICTED  downsampled TCP  -> divergence shrinks toward the clean side

  If instead the node dims diverge on UDP as much as on TCP, then something
  about the pipeline as a whole differs and E49's mechanism is WRONG.

The TCP-downsample arm closes the loop: take the original's TCP flows, cut them
to the improved extractor's TCP flow count, and check that the divergence moves
toward the clean measurement rather than staying where it was.

    python experiments/E49_cross_testbed_why/exp_e49c_causal_confirm.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import (build_graphs, node_feature_names, normalize_columns,
                           read_flows, _window_key)

ORIG = ROOT / "data" / "GeneratedLabelledFlows" / "TrafficLabelling"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
OUT = Path(__file__).resolve().parent / "exp_e49c_causal_confirm.json"

TCP, UDP = 6, 17


def benign(path: Path, orig: bool) -> pd.DataFrame:
    df = normalize_columns(read_flows(path) if orig
                           else pd.read_csv(path, low_memory=True))
    lab = df["label"].astype(str).str.strip().str.upper()
    return df[lab == "BENIGN"].sort_values("timestamp")


def node_feats(df: pd.DataFrame):
    """Stack the 19 node dims over all 60s windows of df."""
    names = node_feature_names("v2")
    chunks, sizes = [], []
    for _, w in df.groupby(_window_key(df, 60)):
        gs = build_graphs(w, window_seconds=60, feature_set="v2")
        if not gs:
            continue
        g = gs[0]
        chunks.append(g.x.detach().cpu().numpy())
        sizes.append((g.num_nodes, g.num_edges))
    if not chunks:
        return np.zeros((0, len(names))), np.array([(0, 0)])
    return np.concatenate(chunks, axis=0), np.array(sizes)


def ks(a, b):
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if a.size < 20 or b.size < 20:
        return float("nan")
    grid = np.unique(np.concatenate([
        np.quantile(a, np.linspace(0, 1, 201)),
        np.quantile(b, np.linspace(0, 1, 201))]))
    ca = np.searchsorted(np.sort(a), grid, side="right") / a.size
    cb = np.searchsorted(np.sort(b), grid, side="right") / b.size
    return float(np.max(np.abs(ca - cb)))


def compare(Xa, Xb, names):
    rows = []
    for i, nm in enumerate(names):
        a, b = Xa[:, i], Xb[:, i]
        sa, sb = float(np.std(a)), float(np.std(b))
        shift = abs(float(np.mean(a)) - float(np.mean(b))) / max(
            np.sqrt((sa ** 2 + sb ** 2) / 2), 1e-9)
        rows.append({"dim": i, "name": nm, "ks": round(ks(a, b), 4),
                     "std_shift": round(shift, 3),
                     "mean_orig": round(float(np.mean(a)), 4),
                     "mean_clean": round(float(np.mean(b)), 4)})
    return rows


def summarise(rows, label):
    valid = [r for r in rows if not np.isnan(r["ks"])]
    ks_med = float(np.median([r["ks"] for r in valid])) if valid else float("nan")
    ks_p90 = float(np.percentile([r["ks"] for r in valid], 90)) if valid else float("nan")
    n_big = sum(1 for r in rows if r["std_shift"] > 1.0)
    return {"label": label, "n_dims_compared": len(valid),
            "ks_median": round(ks_med, 4), "ks_p90": round(ks_p90, 4),
            "n_dims_shifted_gt_1sd": n_big, "dims": rows}


def main():
    names = node_feature_names("v2")
    o_all = benign(ORIG / "Monday-WorkingHours.pcap_ISCX.csv", True)
    c_all = benign(CLEAN / "monday.csv", False)

    o = o_all[pd.to_numeric(o_all["protocol"], errors="coerce") == UDP]
    c = c_all[pd.to_numeric(c_all["protocol"], errors="coerce") == UDP]
    ot = o_all[pd.to_numeric(o_all["protocol"], errors="coerce") == TCP]
    ct = c_all[pd.to_numeric(c_all["protocol"], errors="coerce") == TCP]

    counts = {"udp": {"orig": int(len(o)), "clean": int(len(c))},
              "tcp": {"orig": int(len(ot)), "clean": int(len(ct))}}
    print(f"UDP flows: orig {len(o):,}  clean {len(c):,}  "
          f"ratio {len(c)/max(len(o),1):.4f}")
    print(f"TCP flows: orig {len(ot):,}  clean {len(ct):,}  "
          f"ratio {len(ct)/max(len(ot),1):.4f}")

    res = {"flow_counts": counts, "arms": {}}

    # --- arm 1: UDP only -------------------------------------------------
    Xo, so = node_feats(o)
    Xc, sc = node_feats(c)
    udp = summarise(compare(Xo, Xc, names), "UDP only")
    udp["per_window"] = {
        "orig": {"nodes": float(so[:, 0].mean()), "edges": float(so[:, 1].mean()),
                 "edges_per_node": float(so[:, 1].sum() / max(so[:, 0].sum(), 1))},
        "clean": {"nodes": float(sc[:, 0].mean()), "edges": float(sc[:, 1].mean()),
                  "edges_per_node": float(sc[:, 1].sum() / max(sc[:, 0].sum(), 1))}}
    res["arms"]["udp_only"] = udp
    print(f"\nUDP-only  KS median {udp['ks_median']:.3f}  p90 {udp['ks_p90']:.3f}  "
          f"dims >1SD: {udp['n_dims_shifted_gt_1sd']}")
    print(f"          edges/node orig {udp['per_window']['orig']['edges_per_node']:.3f}"
          f"  clean {udp['per_window']['clean']['edges_per_node']:.3f}")

    # --- arm 2: TCP only -------------------------------------------------
    Xot, sot = node_feats(ot)
    Xct, sct = node_feats(ct)
    tcp = summarise(compare(Xot, Xct, names), "TCP only")
    tcp["per_window"] = {
        "orig": {"nodes": float(sot[:, 0].mean()), "edges": float(sot[:, 1].mean()),
                 "edges_per_node": float(sot[:, 1].sum() / max(sot[:, 0].sum(), 1))},
        "clean": {"nodes": float(sct[:, 0].mean()), "edges": float(sct[:, 1].mean()),
                  "edges_per_node": float(sct[:, 1].sum() / max(sct[:, 0].sum(), 1))}}
    res["arms"]["tcp_only"] = tcp
    print(f"\nTCP-only  KS median {tcp['ks_median']:.3f}  p90 {tcp['ks_p90']:.3f}  "
          f"dims >1SD: {tcp['n_dims_shifted_gt_1sd']}")
    print(f"          edges/node orig {tcp['per_window']['orig']['edges_per_node']:.3f}"
          f"  clean {tcp['per_window']['clean']['edges_per_node']:.3f}")

    # --- arm 3: original TCP downsampled to the clean TCP count ---------
    rng = np.random.default_rng(0)
    k = min(len(ct), len(ot))
    sub = ot.iloc[np.sort(rng.choice(len(ot), size=k, replace=False))]
    Xs, ss = node_feats(sub)
    down = summarise(compare(Xs, Xct, names), "orig TCP downsampled to clean count")
    down["n_tcp_flows_used"] = int(k)
    down["per_window"] = {
        "orig_downsampled": {"edges_per_node": float(ss[:, 1].sum() / max(ss[:, 0].sum(), 1))},
        "clean": {"edges_per_node": float(sct[:, 1].sum() / max(sct[:, 0].sum(), 1))}}
    res["arms"]["tcp_downsampled"] = down
    print(f"\nTCP downsampled to {k:,} flows  KS median {down['ks_median']:.3f}  "
          f"p90 {down['ks_p90']:.3f}  dims >1SD: {down['n_dims_shifted_gt_1sd']}")
    print(f"          edges/node orig_sub {down['per_window']['orig_downsampled']['edges_per_node']:.3f}"
          f"  clean {down['per_window']['clean']['edges_per_node']:.3f}")

    # --- verdict --------------------------------------------------------
    tcp_worse = tcp["ks_median"] > udp["ks_median"]
    moved = down["ks_median"] < tcp["ks_median"]
    res["verdict"] = {
        "udp_agrees_more_than_tcp": bool(tcp_worse),
        "downsampling_tcp_reduces_divergence": bool(moved),
        "confirmed": bool(tcp_worse and moved),
    }
    print("\n" + "=" * 68)
    if tcp_worse and moved:
        print("CONFIRMED. The TCP flow deficit causes the node divergence:")
        print(f"  UDP-only KS {udp['ks_median']:.3f} vs TCP-only KS {tcp['ks_median']:.3f}")
        print(f"  downsampling the original's TCP to the clean count moves the")
        print(f"  divergence {tcp['ks_median']:.3f} -> {down['ks_median']:.3f}")
        print("  => the mechanism is flow-record density, not traffic content.")
    elif tcp_worse:
        print("PARTIAL. UDP agrees better than TCP, so the effect is TCP-specific,")
        print("but downsampling did not move the divergence -- something else also")
        print("contributes to the TCP-only arm.")
    else:
        print("REFUTED. UDP node dims diverge at least as much as TCP's, so the")
        print("mechanism is NOT TCP-specific and E49's explanation is wrong.")
    print("=" * 68)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
