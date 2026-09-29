"""E51: fix Infiltration's seed-flip at the estimator, not by quoting around it.

[E43](../E43_fusion_rule/) banded the fusion arms and found Infiltration's
ranking FLIPS with the seed:

    seed 0  noisyor 0.645  >  repfuse 0.639     (noisyor wins)
    seed 1  noisyor 0.651  <  repfuse 0.686     (repfuse wins)
    seed 2  noisyor 0.650  <  repfuse 0.698     (repfuse wins)
    seed 3  noisyor 0.652  >  repfuse 0.651     (tie)

  band: repfuse 0.668 +- 0.028   noisyor 0.650 +- 0.003

The instability is entirely in `repfuse` (range 0.059 across seeds) while
`noisyor` is rock-stable (range 0.007). So the target is repfuse's estimator,
not the fusion rule.

Hypothesis: `repfuse` is the mean of two PER-HOST RUNNING MEANS. Infiltration has
only THREE attacker hosts on Thursday, so for the windows that matter each
host's running mean is built from very few observations, and its value depends
sensitively on WHEN that host first appears. A thin-history mean is a
high-variance estimator; that is the whole problem.

The principled fix is variance reduction, not tuning: EMPIRICAL-BAYES
SHRINKAGE. Pull each host's running mean toward the population mean with a
weight set by how little history it has:

    shrunk = (n * mean_h + k * mu) / (n + k)

For a well-observed host (n >> k) this is the running mean, unchanged. For a
host seen once or twice it collapses toward `mu`, so a single surprising window
cannot define it. `mu` is the running global mean of all scores so far -- fully
causal, no future information, no labels.

Success is NOT a higher mean. It is:
  1. repfuse's across-seed SD falls materially
  2. repfuse beats noisyor on the SAME seeds, not a mixture
  3. the other four families do not degrade

    python experiments/E51_infiltration_stability/exp_e51_stability.py
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

from graph_builder import build_graphs, normalize_columns, _window_key
from gnn_model import GraphAutoencoder, NodeScaler
from eval_guards import require_window_groups
from exp_m5a_revival import flow_matrix, build_ctx, MinMax, CtxScaler, RevivedAE

DET = ROOT / "detection"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
OUT = Path(__file__).resolve().parent / "exp_e51_stability.json"

FAMS = {
    "Botnet":       (["friday.csv"],    {"Botnet"}),
    "PortScan":     (["friday.csv"],    {"Portscan"}),
    "DDoS":         (["friday.csv"],    {"DDoS"}),
    "Infiltration": (["thursday.csv"],  {"Infiltration", "Infiltration - Portscan"}),
    "WebAttacks":   (["thursday.csv"],  {"Web Attack - Brute Force",
                                         "Web Attack - XSS",
                                         "Web Attack - SQL Injection"}),
}
M5B = {0: DET / "gnn_improved_s0.pt", 1: DET / "gnn_improved_s1.pt",
       2: DET / "gnn_improved_s2.pt", 3: DET / "gnn_improved_s3.pt"}
M5A = {0: DET / "m5a_revived_improved.pt"}
for _s in (1, 2, 3):
    _p = ROOT / "experiments" / "E21_band" / f"m5a_revived_improved_s{_s}.pt"
    if _p.exists():
        M5A[_s] = _p

K_GRID = [0, 1, 2, 4, 8, 16]


def run_family(fam, m5b, sc_b, rev, ra, device):
    """One pass, recording enough state to evaluate any shrinkage k offline."""
    files, labels = FAMS[fam]
    recs = []
    for fn in files:
        d = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
        lab = d["label"].astype(str).str.strip()
        d = d[~lab.str.endswith("- Attempted")].copy()
        lab = d["label"].astype(str).str.strip()
        n_atk = int(lab.isin(labels).sum())
        if n_atk == 0:
            raise ValueError(f"{fam}: no rows match {sorted(labels)} in {fn}")
        bad_src = set(d["src_ip"][lab.isin(labels)])
        if not bad_src:
            raise ValueError(f"{fam}: attack rows but no attacker host")
        run_b, run_a, run_g = {}, {}, []
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
                run_g.append(float(s))
            for h, s in hm.items():
                run_a.setdefault(h, []).append(float(s))
            mu_b = float(np.mean(run_g))
            # run_a values are variable-length lists -> flatten before mean
            flat_a = [v for lst in run_a.values() for v in lst]
            mu_a = float(np.mean(flat_a)) if flat_a else 0.0
            ei = g.edge_index.cpu().numpy()
            rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
            b = np.array([(hm.get(g.hosts[int(ei[0, e])], 0)
                           + hm.get(g.hosts[int(ei[1, e])], 0)) / 2.0
                          for e in range(g.num_edges)])
            for e in range(g.num_edges):
                s_, t_ = g.hosts[int(ei[0, e])], g.hosts[int(ei[1, e])]
                hb, ht = run_b.get(s_, []), run_b.get(t_, [])
                ha, hc = run_a.get(s_, []), run_a.get(t_, [])
                recs.append({
                    "y": 1 if s_ in bad_src else 0, "win": win,
                    "m5b": float(rel[e]), "m5a": float(b[e]),
                    # (n, mean, mu) triplets for both pillars -> any k offline
                    "nb_s": len(hb), "mb_s": float(np.mean(hb)) if hb else mu_b,
                    "nb_t": len(ht), "mb_t": float(np.mean(ht)) if ht else mu_b,
                    "na_s": len(ha), "ma_s": float(np.mean(ha)) if ha else mu_a,
                    "na_t": len(hc), "ma_t": float(np.mean(hc)) if hc else mu_a,
                    "mu_b": mu_b, "mu_a": mu_a,
                })
            win += 1
    return recs


def shrink(n, m, mu, k):
    if k <= 0:
        return m
    return (n * m + k * mu) / (n + k)


def rk(s):
    s = np.asarray(s, dtype=float)
    o = np.argsort(np.argsort(s))
    return o / max(len(s) - 1, 1)


def evaluate(R, k):
    from sklearn.metrics import roc_auc_score
    y = R["y"].to_numpy()
    r_m5b = R.groupby("win")["m5b"].transform(rk).to_numpy()
    r_m5a = R.groupby("win")["m5a"].transform(rk).to_numpy()
    r_noisy = 1 - (1 - r_m5b) * (1 - r_m5a)
    rb = np.array([(shrink(a, b, c, k) + shrink(d, e, c, k)) / 2.0
                   for a, b, d, e, c in zip(R["nb_s"], R["mb_s"], R["nb_t"],
                                            R["mb_t"], R["mu_b"])])
    ra = np.array([(shrink(a, b, c, k) + shrink(d, e, c, k)) / 2.0
                   for a, b, d, e, c in zip(R["na_s"], R["ma_s"], R["na_t"],
                                            R["ma_t"], R["mu_a"])])
    r_rep = R.assign(_v=rb * 0.5 + ra * 0.5).groupby("win")["_v"].transform(
        rk).to_numpy()
    return {"repfuse": float(roc_auc_score(y, r_rep)),
            "noisyor": float(roc_auc_score(y, r_noisy))}


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seeds = sorted(set(M5B) & set(M5A))
    raw = {}
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
            raw.setdefault(fam, {})[sd] = run_family(fam, m5b, sc_b, rev, ra, device)
            print(f"  seed {sd} {fam} done", flush=True)

    res = {"k_grid": K_GRID, "seeds": seeds, "families": {}}
    for fam in FAMS:
        per = {}
        for k in K_GRID:
            rows = {sd: evaluate(pd.DataFrame(raw[fam][sd]), k) for sd in seeds}
            rep = np.array([rows[s]["repfuse"] for s in seeds])
            noi = np.array([rows[s]["noisyor"] for s in seeds])
            per[str(k)] = {
                "repfuse_mean": round(float(rep.mean()), 4),
                "repfuse_sd": round(float(rep.std(ddof=1)), 4),
                "repfuse_per_seed": [round(float(x), 4) for x in rep],
                "noisyor_mean": round(float(noi.mean()), 4),
                "noisyor_sd": round(float(noi.std(ddof=1)), 4),
                "wins_vs_noisyor": int((rep > noi).sum()),
                "seed_agreement": "unanimous" if (rep > noi).all() or (rep < noi).all()
                                  else "FLIPS",
            }
        res["families"][fam] = per

    print("\n" + "=" * 78)
    for fam in FAMS:
        print(f"\n{fam}")
        print(f"  {'k':>3}  {'repfuse':>16}  {'noisyor':>8}  wins  agreement")
        for k in K_GRID:
            p = res["families"][fam][str(k)]
            print(f"  {k:>3}  {p['repfuse_mean']:.4f} +- {p['repfuse_sd']:.4f}"
                  f"  {p['noisyor_mean']:>8.4f}  {p['wins_vs_noisyor']}/4"
                  f"  {p['seed_agreement']}")

    inf = res["families"]["Infiltration"]
    base, best = inf["0"], min(K_GRID[1:], key=lambda k: inf[str(k)]["repfuse_sd"])
    sd0, sdb = base["repfuse_sd"], inf[str(best)]["repfuse_sd"]
    res["infiltration_finding"] = {
        "sd_at_k0": sd0, "sd_at_best_k": sdb, "best_k": best,
        "sd_reduction_pct": round(100 * (sd0 - sdb) / max(sd0, 1e-9), 1),
        "k0_agreement": base["seed_agreement"],
        "best_agreement": inf[str(best)]["seed_agreement"],
        "k0_wins": base["wins_vs_noisyor"],
        "best_wins": inf[str(best)]["wins_vs_noisyor"],
    }
    print("\n" + "=" * 78)
    print("Infiltration:")
    print(f"  k=0 (raw running mean) SD {sd0:.4f}, {base['seed_agreement']}, "
          f"{base['wins_vs_noisyor']}/4 vs noisyor")
    print(f"  k={best} (shrunk)          SD {sdb:.4f}, "
          f"{inf[str(best)]['seed_agreement']}, "
          f"{inf[str(best)]['wins_vs_noisyor']}/4 vs noisyor")
    print(f"  -> SD reduced {res['infiltration_finding']['sd_reduction_pct']}%")

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()
