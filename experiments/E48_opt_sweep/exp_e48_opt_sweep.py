"""E48: sweep the OPT thresholds (k=3, nwin=5) that were set by inspection.

E43's open caveat: the burst-aware arm used SHORT_K=3 and the persistence arm
used MIN_WINDOWS=5, both chosen by eye. This measures the surface they sit on.

Two design points, both deliberate:

1. SHORT_K is applied during accumulation, so it cannot be varied afterwards
   without re-scoring. Instead of re-running the graph pipeline per k, each
   edge records the last K_MAX scores of both endpoints, and short-k is
   reconstructed as mean(tail[-k:]) for any k <= K_MAX. One pass, all k.

2. Selecting the best threshold on the same 4 seeds that report the result is
   selection on the evaluation set, and would produce a number that is
   optimistic by construction. So this reports the FULL surface, and adds a
   leave-one-seed-out check: pick the threshold on 3 seeds, score it on the
   4th. The gap between "best on all seeds" and "chosen without seeing it" is
   the honest measure of how much the choice is worth.

    python experiments/E48_opt_sweep/exp_e48_opt_sweep.py
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
from eval_guards import require_window_groups
from exp_m5a_revival import flow_matrix, build_ctx, MinMax, CtxScaler, RevivedAE

DET = ROOT / "detection"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
OUT = Path(__file__).resolve().parent / "exp_e48_opt_sweep.json"

M5B = {0: DET / "gnn_improved_s0.pt", 1: DET / "gnn_improved_s1.pt",
       2: DET / "gnn_improved_s2.pt", 3: DET / "gnn_improved_s3.pt"}
M5A = {0: DET / "m5a_revived_improved.pt"}
for _s in (1, 2, 3):
    _p = ROOT / "experiments" / "E21_band" / f"m5a_revived_improved_s{_s}.pt"
    if _p.exists():
        M5A[_s] = _p

# Label strings copied VERBATIM from E43. Guessing these produced three
# families with an empty positive set and silent `nan` AUCs: the clean-data
# labels are "Botnet" (not "Bot"), "Portscan" (lowercase s), and
# "Web Attack - SQL Injection" (uppercase SQL).
FAMS = {
    "Botnet":       (["friday.csv"],    {"Botnet"}),
    "PortScan":     (["friday.csv"],    {"Portscan"}),
    "DDoS":         (["friday.csv"],    {"DDoS"}),
    "Infiltration": (["thursday.csv"],  {"Infiltration", "Infiltration - Portscan"}),
    "WebAttacks":   (["thursday.csv"],  {"Web Attack - Brute Force",
                                         "Web Attack - XSS",
                                         "Web Attack - SQL Injection"}),
}
K_GRID = [1, 2, 3, 4, 6, 8]
NWIN_GRID = [3, 5, 8, 12, 10**6]      # 1e6 = never persists, i.e. always noisyor
K_MAX = 8


def _window_graph(g, ns):
    ei = g.edge_index.cpu().numpy()
    rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
    return ei, rel


def evaluate(recs, k, nwin):
    from sklearn.metrics import roc_auc_score
    R = pd.DataFrame(recs)
    require_window_groups(R["win"].to_numpy(), len(R), context="E48 rank groups")

    def rk(s):
        s = np.asarray(s, dtype=float)
        o = np.argsort(np.argsort(s))
        return o / max(len(s) - 1, 1)

    def within(col_vals):
        return R.assign(_v=col_vals).groupby("win")["_v"].transform(rk).to_numpy()

    r_m5b = within(R["m5b"].to_numpy())
    r_m5a = within(R["m5a"].to_numpy())
    r_rep = within(R["rep_b"].to_numpy() * 0.5 + R["rep_a"].to_numpy() * 0.5)
    r_noisy = 1 - (1 - r_m5b) * (1 - r_m5a)

    ts = R["tail_s"].tolist()
    tt = R["tail_t"].to_list()
    short = np.array([(np.mean(a[-k:]) + np.mean(b[-k:])) / 2.0
                      for a, b in zip(ts, tt)], dtype=float)
    r_short = within(short)
    r_opt3 = 1 - (1 - r_short) * (1 - r_noisy)
    r_opt1 = np.where(R["nwin"].to_numpy() >= nwin, r_rep, r_noisy)

    y = R["y"].to_numpy()
    return {"opt1": float(roc_auc_score(y, r_opt1)),
            "opt3": float(roc_auc_score(y, r_opt3)),
            "repfuse": float(roc_auc_score(y, r_rep)),
            "noisyor": float(roc_auc_score(y, r_noisy))}


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seeds = sorted(set(M5B) & set(M5A))
    raw = {}                                     # fam -> seed -> recs
    for sd in seeds:
        gb = torch.load(M5B[sd], map_location="cpu", weights_only=True)
        m5b = GraphAutoencoder(in_dim=19)
        m5b.load_state_dict(gb["model"]); m5b.eval().to(device)
        sc_b = NodeScaler().load_state_dict(gb["scaler"])
        b = torch.load(M5A[sd], map_location="cpu", weights_only=False)
        rev = RevivedAE(b["input_dim"]); rev.load_state_dict(b["state_dict"]); rev.eval().to(device)
        ra = {"canon": b["canonical"], "fmm": MinMax(), "csc": CtxScaler()}
        ra["fmm"].lo, ra["fmm"].hi = b["flow_lo"], b["flow_hi"]
        ra["csc"].lo, ra["csc"].hi = b["ctx_lo"], b["ctx_hi"]
        for fam in FAMS:
            recs = run_family(fam, m5b, sc_b, rev, ra, device)
            raw.setdefault(fam, {})[sd] = recs
            print(f"  seed {sd} {fam:13s} {len(recs)} edges", flush=True)

    res = {"k_grid": K_GRID, "nwin_grid": NWIN_GRID, "seeds": seeds,
           "surface": {}, "opt3_vs_defaults": {}, "opt1_vs_defaults": {},
           "loso": {}}
    for fam in FAMS:
        surf3, surf1 = {}, {}
        for sd in seeds:
            for k in K_GRID:
                r = evaluate(raw[fam][sd], k, 5)
                surf3.setdefault(str(k), {})[str(sd)] = r["opt3"]
            for nw in NWIN_GRID:
                r = evaluate(raw[fam][sd], 3, nw)
                surf1.setdefault(str(nw), {})[str(sd)] = r["opt1"]
        res["surface"].setdefault(fam, {})["opt3_by_k"] = {
            k: {"mean": float(np.mean(list(v.values()))),
                "sd": float(np.std(list(v.values()), ddof=1))}
            for k, v in surf3.items()}
        res["surface"][fam]["opt1_by_nwin"] = {
            n: {"mean": float(np.mean(list(v.values()))),
                "sd": float(np.std(list(v.values()), ddof=1))}
            for n, v in surf1.items()}
        # defaults used by E43
        res["opt3_vs_defaults"][fam] = {
            "at_k3": res["surface"][fam]["opt3_by_k"]["3"],
            "best_k": max(res["surface"][fam]["opt3_by_k"],
                          key=lambda k: res["surface"][fam]["opt3_by_k"][k]["mean"]),
            "repfuse": float(np.mean([evaluate(raw[fam][sd], 3, 5)["repfuse"]
                                      for sd in seeds])),
        }
        res["opt1_vs_defaults"][fam] = {
            "at_nwin5": res["surface"][fam]["opt1_by_nwin"]["5"],
            "best_nwin": max(res["surface"][fam]["opt1_by_nwin"],
                             key=lambda n: res["surface"][fam]["opt1_by_nwin"][n]["mean"]),
        }
        print(f"\n{fam}")
        for k, v in res["surface"][fam]["opt3_by_k"].items():
            print(f"   opt3 k={k:>2s}  {v['mean']:.4f} +- {v['sd']:.4f}")
        for n, v in res["surface"][fam]["opt1_by_nwin"].items():
            print(f"   opt1 nwin={n:>7s}  {v['mean']:.4f} +- {v['sd']:.4f}", flush=True)

    res["loso"] = loso_check(raw, res, seeds)
    print("\nleave-one-seed-out: pick k on 3 seeds, score on the 4th")
    for fam, v in res["loso"].items():
        print(f"  {fam:13s} tuned {v['holdout_mean']:.4f}+-{v['holdout_sd']:.4f}"
              f"   k=3 fixed {v['k3_fixed_mean']:.4f}+-{v['k3_fixed_sd']:.4f}"
              f"   delta {v['delta']:+.4f}  [{v['verdict']}]")

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


def loso_check(raw, res, seeds):
    """Pick k on 3 seeds, score it on the 4th. The honest version.

    The band above is measured at whichever k looks best on all four seeds,
    which is selection on the evaluation set. This asks the only question that
    matters for a tuned constant: if you had chosen k without seeing this seed,
    would you have been right?
    """
    out = {}
    for fam in FAMS:
        surf = res["surface"][fam]["opt3_by_k"]
        per_seed_holdout, per_seed_oracle = [], []
        for held in seeds:
            train_seeds = [s for s in seeds if s != held]
            best_k = max(K_GRID, key=lambda k: np.mean(
                [evaluate(raw[fam][s], k, 5)["opt3"] for s in train_seeds]))
            per_seed_holdout.append(evaluate(raw[fam][held], best_k, 5)["opt3"])
            per_seed_oracle.append(evaluate(raw[fam][held], 3, 5)["opt3"])
        t, k3 = float(np.mean(per_seed_holdout)), float(np.mean(per_seed_oracle))
        # Correct orientation: tuning is only a problem if the held-out score
        # is WORSE than the untuned default. The first version of this check
        # had the comparison reversed and labelled three families "OVERFITS"
        # when tuning had in fact beaten k=3 by 0.010-0.027.
        delta = t - k3
        if delta > 0.005:
            verdict = f"tuning HELPS (+{delta:.4f})"
        elif delta > -0.005:
            verdict = f"tuning is a wash ({delta:+.4f}, inside noise)"
        else:
            verdict = f"TUNING OVERFITS ({delta:+.4f}) - k=3 is safer"
        out[fam] = {
            "holdout_mean": t,
            "holdout_sd": float(np.std(per_seed_holdout, ddof=1)),
            "k3_fixed_mean": k3,
            "k3_fixed_sd": float(np.std(per_seed_oracle, ddof=1)),
            "delta": round(delta, 6),
            "verdict": verdict,
        }
    return out


def run_family(fam, m5b, sc_b, rev, ra, device):
    """One pass over a family, recording per-edge endpoint tails.

    Each edge stores the last K_MAX scores of both endpoints, so short-k
    reputation is reconstructable afterwards as mean(tail[-k:]) for any
    k <= K_MAX -- one pass instead of one per k. `full` counts the untrimmed
    history so `nwin` is not corrupted by the trimming.
    """
    recs = []
    for fn, labels in [(FAMS[fam][0][0], FAMS[fam][1])]:
        d = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
        lab = d["label"].astype(str).str.strip()
        d = d[~lab.str.endswith("- Attempted")].copy()
        lab = d["label"].astype(str).str.strip()
        n_rows_attack = int(lab.isin(labels).sum())
        if n_rows_attack == 0:
            raise ValueError(
                f"{fam}: 0 rows match labels {sorted(labels)} in {fn}. A wrong "
                "label string yields an empty positive set and silent nan AUCs "
                "-- this check exists because that happened once.")
        bad_src = set(d["src_ip"][lab.isin(labels)])
        if not bad_src:
            raise ValueError(f"{fam}: {n_rows_attack} attack rows but no src_ip "
                             "resolved to a host -- population unusable.")
        print(f"    {fam}/{fn}: {n_rows_attack} attack rows, "
              f"{len(bad_src)} attacker hosts", flush=True)
        run_b, run_a, full = {}, {}, {}
        d = d.sort_values("timestamp")
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
                if len(run_b[h]) > K_MAX:
                    run_b[h].pop(0)
                full[h] = full.get(h, 0) + 1
            for h, s in hm.items():
                run_a.setdefault(h, []).append(float(s))
            ei, rel = _window_graph(g, ns)
            b = np.array([(hm.get(g.hosts[int(ei[0, e])], 0)
                           + hm.get(g.hosts[int(ei[1, e])], 0)) / 2.0
                          for e in range(g.num_edges)])
            for e in range(g.num_edges):
                s_, t_ = g.hosts[int(ei[0, e])], g.hosts[int(ei[1, e])]
                recs.append({
                    "y": 1 if s_ in bad_src else 0, "win": win,
                    "m5b": float(rel[e]), "m5a": float(b[e]),
                    "rep_b": (np.mean(run_b[s_]) + np.mean(run_b[t_])) / 2.0,
                    "rep_a": (np.mean(run_a.get(s_, [0])) + np.mean(run_a.get(t_, [0]))) / 2.0,
                    "tail_s": list(run_b[s_]), "tail_t": list(run_b[t_]),
                    "nwin": min(full.get(s_, 0), full.get(t_, 0)),
                })
            win += 1
    return recs


if __name__ == "__main__":
    main()
