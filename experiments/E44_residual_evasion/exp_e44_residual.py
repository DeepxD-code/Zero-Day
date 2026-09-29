"""
E44: the two residual evasions E24 does not close, and network-side fixes.

E24 closed slow-drip DILUTION (x5 -> 0.979 via reputation). Two attacks
survive it. Pillar 3 is the robust answer, but both have a network-side fix,
so shipping them as "Pillar 3's problem" would leave a cheap fix on the table:

  R1 HOST ROTATION   one scan, many targets, spread over R source IPs so no
                     single host accumulates enough history for reputation.
  R2 SUB-THRESHOLD  pace the scan so no window ever rises above the queue,
                     but the host is odd in aggregate over a long horizon.

Fixes tested (network-side, all using signals we already compute):

  F1 DUAL-TIMESCALE   fast running mean (last K windows, catches bursts) fused
                      with a slow unbounded mean (catches persistent-but-slow).
  F2 NEIGHBOUR OVERLAP a rotated scan has many sources hitting a COMMON target
                      set; independent browsing does not. Per host: the
                      fraction of its out-neighbours that are also
                      out-neighbours of some other host in the same window.

MODEL/DATA MATCHING (this is the whole point of the first two runs getting it
wrong): this experiment uses the SHIPPED original-data checkpoint against the
ORIGINAL PortScan day, so the control reproduces E24's 0.8714. Pairing the
clean-data checkpoint with the original day measures the E17 cross-testbed gap
and says nothing about evasion.

    python experiments/E44_residual_evasion/exp_e44_residual.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))
sys.path.insert(0, str(ROOT / "harness"))

from graph_builder import build_graphs, normalize_columns, read_flows, _window_key
from gnn_model import GraphAutoencoder, NodeScaler
from eval_guards import (check_anchor, require_dataset, require_scaler_match,
                         require_window_groups)
from graph_techniques import spread_dilate

DET = ROOT / "detection"
ORIG = ROOT / "data" / "GeneratedLabelledFlows" / "TrafficLabelling"
DAY = ORIG / "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"
OUT = Path(__file__).resolve().parent / "exp_e44_residual.json"
ATTACKER = "172.16.0.1"
ROT_IPS = ["10.66.0.1", "10.66.0.2", "10.66.0.3", "10.66.0.4", "10.66.0.5"]
FAST_K = 20          # windows kept in the fast channel

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def rotate(df, n_hosts):
    """One attacker -> n source IPs. Same targets, same timings, same volume."""
    d = df.copy()
    idx = d.index[d["src_ip"] == ATTACKER].to_numpy()
    if len(idx) == 0:
        return d
    assign = np.arange(len(idx)) % n_hosts
    d.loc[idx, "src_ip"] = [ROT_IPS[a % n_hosts] for a in assign]
    return d


def overlap_scores(g):
    """Per-edge: fraction of the source's out-neighbours that are ALSO
    out-neighbours of some other host this window. Rotated scan -> ~1.0.
    Independent browsing -> ~0.0."""
    ei = g.edge_index.cpu().numpy()
    hosts = list(g.hosts)
    adj = defaultdict(set)
    for e in range(g.num_edges):
        adj[hosts[int(ei[0, e])]].add(hosts[int(ei[1, e])])
    out = np.zeros(g.num_edges)
    for e in range(g.num_edges):
        s = hosts[int(ei[0, e])]
        nb = adj[s]
        if not nb:
            continue
        shared = 0
        for h, other in adj.items():
            if h != s:
                shared += len(nb & other)
        out[e] = min(1.0, shared / len(nb) / max(len(adj) - 1, 1))
    return out


def evaluate(day, model, scaler, device, bad, label):
    from sklearn.metrics import roc_auc_score
    day = day.sort_values("timestamp")
    recs, win = [], 0
    fast, slow = defaultdict(list), defaultdict(list)
    for _, w in day.groupby(_window_key(day, 60)):
        gs = build_graphs(w, window_seconds=60, feature_set="v2")
        if not gs:
            continue
        g = gs[0]
        with torch.no_grad():
            ns = model.node_scores(scaler.transform(g.x).to(device),
                                   g.edge_index.to(device)).cpu().numpy()
        for h, s in zip(g.hosts, ns):
            slow[h].append(float(s))
            fast[h].append(float(s))
            if len(fast[h]) > FAST_K:
                fast[h].pop(0)
        ei = g.edge_index.cpu().numpy()
        rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
        ov = overlap_scores(g)
        for e in range(g.num_edges):
            s_, t_ = g.hosts[int(ei[0, e])], g.hosts[int(ei[1, e])]
            f = (np.mean(fast[s_]) + np.mean(fast[t_])) / 2
            sl = (np.mean(slow[s_]) + np.mean(slow[t_])) / 2
            recs.append({"y": 1 if s_ in bad else 0, "win": win,
                         "window": float(rel[e]), "fast": f, "slow": sl,
                         "dual": 0.5 * f + 0.5 * sl,
                         "dual_ov": 0.45 * f + 0.45 * sl + 0.10 * ov[e]})
        win += 1
    R = pd.DataFrame(recs)
    y = R["y"].to_numpy()
    if len(y) == 0 or y.sum() == 0 or y.sum() == len(y):
        return None

    # Guard: ranks must be within real 60s windows. `win` increments per
    # window in run_family, so it is already a window key -- this asserts it
    # rather than trusting it (the E43 chunk-grouping bug had the same shape).
    require_window_groups(R["win"].to_numpy(), len(R), context=f"E44 {label}")

    def rk(col):
        return R.groupby("win")[col].transform(
            lambda s: (np.argsort(np.argsort(s.to_numpy()))
                       / max(len(s) - 1, 1)))

    arms = {"window": rk("window").to_numpy(),
            "repfuse_fast": rk("fast").to_numpy(),
            "slow_only": rk("slow").to_numpy(),
            "F1_dual": rk("dual").to_numpy(),
            "F2_dual_ov": rk("dual_ov").to_numpy()}
    out = {k: float(roc_auc_score(y, v)) for k, v in arms.items()}
    out["n_atk"] = int(y.sum())
    out["n"] = int(len(y))
    out["fast_k"] = FAST_K
    print(f"{label:26s} " + "  ".join(
        f"{k} {v:.4f}" for k, v in out.items()
        if k not in ("n_atk", "n", "fast_k")), flush=True)
    return out


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # SHIPPED original-data checkpoint, to match the ORIGINAL day.
    blob = torch.load(DET / "gnn_autoencoder_v1_logscale_v2.pt",
                      map_location="cpu", weights_only=True)
    model = GraphAutoencoder(in_dim=19)
    model.load_state_dict(blob["model"]); model.eval().to(device)
    scaler = NodeScaler().load_state_dict(blob["scaler"])
    # Guard: E44 run 1 paired the CLEAN-data checkpoint with the ORIGINAL day,
    # so the "control" it reported was the cross-testbed gap rather than a
    # control. This checkpoint has no `train` provenance, so the dataset guard
    # cannot fire -- the scaler binding is the check that still holds, and the
    # absence of provenance is recorded in detection/eval_guards.py's
    # provenance_report() rather than assumed away.
    require_scaler_match(blob, scaler, "E44 shipped ckpt")
    day = normalize_columns(read_flows(DAY))
    base = {ATTACKER}
    rot = set(ROT_IPS)

    res = {"model": "gnn_autoencoder_v1_logscale_v2.pt (original-data)",
           "day": "original PortScan"}
    res["control"] = evaluate(day, model, scaler, device, base, "control (x1)")
    # The control arm is the one number in this archive that has reproduced
    # exactly across runs (0.8714, E12). If it moves, every evasion result
    # below it is unreadable until the pairing is explained.
    if res["control"]:
        check_anchor("E44_control_portscan", res["control"]["window"],
                     "E44 control window arm")
    res["R1_rotate_5"] = evaluate(rotate(day, 5), model, scaler, device, rot,
                                 "R1 host rotation x5")
    res["R2_dilate_x10"] = evaluate(spread_dilate(day, ATTACKER, 10), model, scaler,
                                    device, base, "R2 sub-threshold x10")
    res["R2_x10_plus_R1"] = evaluate(
        rotate(spread_dilate(day, ATTACKER, 10), 5), model, scaler, device, rot,
        "R2 x10 + R1 rotate x5")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
