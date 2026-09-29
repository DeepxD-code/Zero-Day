"""
E43: close the fusion-rule gap (E21 repfuse wins Friday, E24 repfuse loses Web).

E21 picked repfuse: best-or-tied on Botnet 0.667 / PortScan 0.952 / DDoS 0.981.
E24 then measured the same five arms on WebAttacks and repfuse came LAST
(0.759 vs noisyor 0.867). The shootout only saw persistent-host families, so
the "one rule wins everywhere" claim is under-evidenced.

Reputation is a running mean -- it needs a host to persist. Botnet/PortScan/
Infiltration persist (0.667 / 0.95 / 0.91). WebAttacks is 62 attacker edges
across a handful of windows out of ~490: nothing to accumulate, and the mean
damps the burst.

Three closes, all evaluated here on the SAME protocol:
  OPT1 persistence-routed  : per-edge, repfuse if the src host has >=N window
                             observations, else noisyor (heuristic)
  OPT2 rule-rank-max      : max(repfuse_rank, noisyor_rank) per edge
  OPT3 burst-aware rep    : short-window (k=3) + long-window (k=all) reputation,
                             fused 50/50, then noisyor-style rank fusion

Control arms: repfuse, noisyor. Families: the E21 Friday three + WebAttacks +
Infiltration, so both regimes are represented.

    python experiments/E43_fusion_rule/ex_e43_fusion_rules.py
Branch-only (exp/host-seqae-p37).
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
sys.path.insert(0, str(ROOT / "experiments"))

from graph_builder import build_graphs, normalize_columns, read_flows, _window_key
from gnn_model import GraphAutoencoder, NodeScaler
from eval_guards import require_scaler_match, require_window_groups
from exp_m5a_revival import flow_matrix, build_ctx, MinMax, CtxScaler, RevivedAE

DET = ROOT / "detection"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
ORIG = ROOT / "data" / "GeneratedLabelledFlows" / "TrafficLabelling"
OUT = Path(__file__).resolve().parent / "exp_e43_fusion_rules.json"

M5B = {0: "gnn_improved_s0.pt", 1: "gnn_improved_s1.pt",
       2: "gnn_improved_s2.pt", 3: "gnn_improved_s3.pt"}
# M5a seed 0 ships in detection/; seeds 1-3 live in the E21_band folder that
# produced them (the cleanup deleted them from detection/ as "one checkpoint is
# enough to serve", which is true for serving and false for banding).
M5A = {0: DET / "m5a_revived_improved.pt"}
for _s in (1, 2, 3):
    _p = (ROOT / "experiments" / "E21_band" / f"m5a_revived_improved_s{_s}.pt")
    if _p.exists():
        M5A[_s] = _p

FAMS = {
    "Botnet":       (["friday.csv"],    {"Botnet"}),
    "PortScan":     (["friday.csv"],    {"Portscan"}),
    "DDoS":         (["friday.csv"],    {"DDoS"}),
    "Infiltration": (["thursday.csv"],  {"Infiltration", "Infiltration - Portscan"}),
    "WebAttacks":   (["thursday.csv"],  {"Web Attack - Brute Force", "Web Attack - XSS",
                                         "Web Attack - SQL Injection"}),
}
MIN_WINDOWS = 5      # OPT1 persistence threshold
SHORT_K = 3          # OPT3 short-window depth

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def r01(x):
    o = np.argsort(np.argsort(np.asarray(x, dtype=float)))
    return o / max(len(x) - 1, 1)


def _window_graph(g, ns):
    ei = g.edge_index.cpu().numpy()
    rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
    return ei, rel


def run_family(fam, m5b, sc_b, rev, ra, device):
    files, labels = FAMS[fam]
    recs = []
    for fn in files:
        d = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
        lab = d["label"].astype(str).str.strip()
        d = d[~lab.str.endswith("- Attempted")].copy()
        lab = d["label"].astype(str).str.strip()
        bad_src = set(d["src_ip"][lab.isin(labels)])
        d = d.sort_values("timestamp")
        run_b, run_a, run_b_short = {}, {}, {}
        win = 0
        for _, w in d.groupby(_window_key(d, 60)):
            gs = build_graphs(w, window_seconds=60, feature_set="v2")
            if not gs:
                continue
            g = gs[0]
            with torch.no_grad():
                ns = m5b.node_scores(sc_b.transform(g.x).to(device),
                                     g.edge_index.to(device)).cpu().numpy()
            X = np.concatenate(
                [ra["fmm"].transform(flow_matrix(w, ra["canon"])),
                 ra["csc"].transform(build_ctx(w, _window_key(w, 60)))], axis=1)
            with torch.no_grad():
                fs = rev.anomaly_score(torch.tensor(X).to(device)).cpu().numpy()
            wr = w.reset_index(drop=True)
            hm = {}
            for i, v in enumerate(fs):
                hm[wr.loc[i, "src_ip"]] = max(hm.get(wr.loc[i, "src_ip"], 0), float(v))
            for h, s in zip(g.hosts, ns):
                run_b.setdefault(h, []).append(float(s))
                run_b_short.setdefault(h, []).append(float(s))
                if len(run_b_short[h]) > SHORT_K:
                    run_b_short[h].pop(0)
            for h, s in hm.items():
                run_a.setdefault(h, []).append(float(s))
            ei, rel = _window_graph(g, ns)
            b = np.array([(hm.get(g.hosts[int(ei[0, e])], 0)
                           + hm.get(g.hosts[int(ei[1, e])], 0)) / 2.0
                          for e in range(g.num_edges)])
            for e in range(g.num_edges):
                s_, t_ = g.hosts[int(ei[0, e])], g.hosts[int(ei[1, e])]
                recs.append({
                    "y": 1 if s_ in bad_src else 0,
                    "win": win,
                    "m5b": float(rel[e]),
                    "m5a": float(b[e]),
                    "rep_b": (np.mean(run_b[s_]) + np.mean(run_b[t_])) / 2.0,
                    "rep_a": (np.mean(run_a.get(s_, [0])) + np.mean(run_a.get(t_, [0]))) / 2.0,
                    "short": (np.mean(run_b_short[s_]) + np.mean(run_b_short[t_])) / 2.0,
                    "nwin": min(len(run_b[s_]), len(run_b[t_])),
                })
            win += 1
    return recs


def evaluate(recs):
    """Rank WITHIN each real 60s window, then pool -- the production metric
    used by every other clean-data experiment in this archive (E16, E21).
    Ranking over row-count chunks is NOT equivalent and was a bug once."""
    from sklearn.metrics import roc_auc_score
    R = pd.DataFrame(recs).reset_index(drop=True)

    # Guard: E43's first run ranked within 5000-row chunks instead of real
    # windows, inflating Botnet repfuse to 0.789 against E21's verified 0.667.
    # Fixed-size groups are the signature; real windows are bursty.
    require_window_groups(R["win"].to_numpy(), len(R), context="E43 rank groups")

    def rk(col):
        return R.groupby("win")[col].transform(lambda s: r01(s.to_numpy()))

    r_m5b, r_m5a = rk("m5b"), rk("m5a")
    r_rep = rk("rep_fuse")
    r_noisy = 1 - (1 - r_m5b) * (1 - r_m5a)
    r_short = rk("short")
    r_opt2 = np.maximum(r_rep.to_numpy(), r_noisy.to_numpy())
    r_opt1 = np.where(R["nwin"].to_numpy() >= MIN_WINDOWS,
                      r_rep.to_numpy(), r_noisy.to_numpy())
    r_opt3 = 1 - (1 - r_short) * (1 - r_noisy)

    y = R["y"].to_numpy()
    out = {}
    for name, v in [("m5b", r_m5b), ("m5a", r_m5a), ("noisyor", r_noisy),
                    ("repfuse", r_rep), ("opt1_persist", r_opt1),
                    ("opt2_rankmax", r_opt2), ("opt3_burst", r_opt3)]:
        out[name] = float(roc_auc_score(y, np.asarray(v)))
    out["n_atk"] = int(y.sum())
    out["n"] = int(len(y))
    return out


ARMS = ["m5b", "m5a", "noisyor", "repfuse", "opt1_persist", "opt2_rankmax",
        "opt3_burst"]


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seeds = sorted(set(M5B) & set(M5A))
    missing = sorted(set(M5B) ^ set(M5A))
    if missing:
        print(f"NOTE: seeds present in one pillar only: {missing} -- "
              f"banding over {seeds}")
    per_seed = {fam: {} for fam in FAMS}
    res = {"seeds": seeds, "per_seed": per_seed, "band": {}}

    for sd in seeds:
        gb = torch.load(DET / M5B[sd] if isinstance(M5B[sd], str) else M5B[sd],
                        map_location="cpu", weights_only=True)
        m5b = GraphAutoencoder(in_dim=19)
        m5b.load_state_dict(gb["model"]); m5b.eval().to(device)
        sc_b = NodeScaler().load_state_dict(gb["scaler"])
        # Both pillars must vary with the seed. Loading M5A[0] unconditionally
        # (the original line here) would have produced a 4-seed band that
        # measured M5b's variance only, and reported it as a fusion band.
        b = torch.load(M5A[sd] if isinstance(M5A[sd], (str, Path)) else M5A[sd],
                       map_location="cpu", weights_only=False)
        rev = RevivedAE(b["input_dim"]); rev.load_state_dict(b["state_dict"]); rev.eval().to(device)
        ra = {"canon": b["canonical"],
              "fmm": MinMax(), "csc": CtxScaler()}
        ra["fmm"].lo, ra["fmm"].hi = b["flow_lo"], b["flow_hi"]
        ra["csc"].lo, ra["csc"].hi = b["ctx_lo"], b["ctx_hi"]

        for fam in FAMS:
            recs = run_family(fam, m5b, sc_b, rev, ra, device)
            for r in recs:
                r["rep_fuse"] = (r["rep_b"] + r["rep_a"]) / 2.0
            row = evaluate(recs)
            per_seed[fam][str(sd)] = row
            print(f"  seed {sd} {fam:13s} m5b {row['m5b']:.3f} | noisyor "
                  f"{row['noisyor']:.3f} | repfuse {row['repfuse']:.3f} | OPT1 "
                  f"{row['opt1_persist']:.3f} | OPT2 {row['opt2_rankmax']:.3f} "
                  f"| OPT3 {row['opt3_burst']:.3f}", flush=True)

    # E21's rule: a single-seed number is noise until shown over seeds.
    for fam in FAMS:
        band = {}
        for arm in ARMS:
            vals = [per_seed[fam][s][arm] for s in per_seed[fam]]
            a = np.asarray(vals, dtype=float)
            band[arm] = {"mean": float(a.mean()), "sd": float(a.std(ddof=1)),
                         "n": int(a.size), "min": float(a.min()),
                         "max": float(a.max())}
        res["band"][fam] = band
        best = max(ARMS, key=lambda k: band[k]["mean"])
        print(f"\n{fam:13s} best={best}  " + "  ".join(
            f"{k} {band[k]['mean']:.3f}±{band[k]['sd']:.3f}" for k in ARMS),
            flush=True)

    OUT.write_text(json.dumps(res, indent=1))
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()
