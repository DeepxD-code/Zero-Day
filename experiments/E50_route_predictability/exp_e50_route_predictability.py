"""E50: is the fusion rule's best `k` PREDICTABLE at inference time?

E48 measured that the best short-window depth `k` runs in opposite directions
across families: Botnet (persistent) wants k=1, WebAttacks and Infiltration
(bursty) want k=8. That is a design problem for the *deployment* only if the
regime can be identified WITHOUT knowing the attack -- otherwise routing is
circular (you would need the label you are trying to detect).

So the question is not "which family wants which k" (n=5, and 4 of them agree,
which is too weak to route on). It is:

  Is there an observable, computable at inference time, that predicts whether a
  short or a long window is currently the better judge?

Two candidate observables, both computable with no label:
  A. persistence  = median nwin (window-observations so far) of the
     highest-scoring edges in the current block
  B. burstiness   = 1 - (fraction of consecutive window pairs where the same
     edge is in the top decile), i.e. do high scores arrive in clumps?

Method: cut each day into contiguous blocks of windows, sweep k WITHIN each
block, and record the k that maximises AUC in that block. Then test whether
observable A or B predicts the winning k. If nothing predicts it, routing is
not implementable and "tune per site" is the honest recommendation.

Seed 0 only, and said so in the output: this is a feasibility probe for
whether ANY observable works, not a banded result.

    python experiments/E50_route_predictability/exp_e50_route_predictability.py
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
sys.path.insert(0, str(ROOT / "experiments" / "E48_opt_sweep"))

from graph_builder import build_graphs, normalize_columns, read_flows, _window_key
from gnn_model import GraphAutoencoder, NodeScaler
from eval_guards import require_window_groups
from exp_m5a_revival import flow_matrix, build_ctx, MinMax, CtxScaler, RevivedAE

DET = ROOT / "detection"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
OUT = Path(__file__).resolve().parent / "exp_e50_route_predictability.json"

# copied verbatim from E43/E48 after the label-string incident
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
K_MAX = 8
BLOCK = 40          # windows per block


def run_family(fam, m5b, sc_b, rev, ra, device):
    """Same one-pass tail-recording scan as E48 (single seed)."""
    files, labels = FAMS[fam]
    recs = []
    for fn in files:
        d = normalize_columns(pd.read_csv(CLEAN / fn, low_memory=True))
        lab = d["label"].astype(str).str.strip()
        d = d[~lab.str.endswith("- Attempted")].copy()
        lab = d["label"].astype(str).str.strip()
        if not lab.isin(labels).any():
            raise ValueError(f"{fam}: no rows match {sorted(labels)} in {fn}")
        bad_src = set(d["src_ip"][lab.isin(labels)])
        if not bad_src:
            raise ValueError(f"{fam}: attack rows but no attacker host")
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
            ei = g.edge_index.cpu().numpy()
            rel = (ns[ei[0]] + ns[ei[1]]) / 2.0
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


def rk(s: np.ndarray) -> np.ndarray:
    o = np.argsort(np.argsort(np.asarray(s, dtype=float)))
    return o / max(len(s) - 1, 1)


def auc_or_none(y, s):
    y = np.asarray(y)
    if y.size == 0 or y.sum() == 0 or y.sum() == y.size:
        return None
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, np.asarray(s, dtype=float)))


def block_observables(R: pd.DataFrame) -> dict:
    """Label-free observables computable at inference time."""
    m5b_r = R.groupby("win")["m5b"].transform(rk).to_numpy()
    out = {}
    for bi, (_, B) in enumerate(R.groupby((R["win"] // BLOCK))):
        if B["y"].sum() == 0 or len(B) < 20:
            continue
        top = B.nlargest(max(len(B) // 10, 1), "m5b")
        # A: persistence of the currently-flagged edges
        out.setdefault("persistence", []).append(float(top["nwin"].median()))
        # B: burstiness -- how clustered the top-decile edges are in window id
        wins = np.sort(top["win"].unique())
        span = (wins.max() - wins.min() + 1) if wins.size else 1
        out.setdefault("clustering", []).append(float(wins.size / span))
    return out


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    gb = torch.load(DET / "gnn_improved_s0.pt", map_location="cpu", weights_only=True)
    m5b = GraphAutoencoder(in_dim=19)
    m5b.load_state_dict(gb["model"]); m5b.eval().to(device)
    sc_b = NodeScaler().load_state_dict(gb["scaler"])
    b = torch.load(DET / "m5a_revived_improved.pt", map_location="cpu",
                   weights_only=False)
    rev = RevivedAE(b["input_dim"]); rev.load_state_dict(b["state_dict"]); rev.eval().to(device)
    ra = {"canon": b["canonical"], "fmm": MinMax(), "csc": CtxScaler()}
    ra["fmm"].lo, ra["fmm"].hi = b["flow_lo"], b["flow_hi"]
    ra["csc"].lo, ra["csc"].hi = b["ctx_lo"], b["ctx_hi"]

    res = {"seed": 0, "block_windows": BLOCK, "k_grid": K_GRID,
           "note": "feasibility probe, single seed. Question: does any "
                   "label-free observable predict the best k within a block?",
           "families": {}}

    for fam in FAMS:
        recs = run_family(fam, m5b, sc_b, rev, ra, device)
        R = pd.DataFrame(recs)
        require_window_groups(R["win"].to_numpy(), len(R), context=f"E50 {fam}")
        r_m5b = R.groupby("win")["m5b"].transform(rk).to_numpy()
        r_m5a = R.groupby("win")["m5a"].transform(rk).to_numpy()
        r_noisy = 1 - (1 - r_m5b) * (1 - r_m5a)
        R = R.assign(_noisy=r_noisy)
        R["_short"] = [np.mean(a[-1:]) for a in R["tail_s"]]   # k=1 view

        blocks = []
        for bidx, (_, B) in enumerate(R.groupby(R["win"] // BLOCK)):
            obs = block_observables(B)
            if not obs:
                continue
            short_k = {k: np.array(
                [(np.mean(a[-k:]) + np.mean(bb[-k:])) / 2.0
                 for a, bb in zip(B["tail_s"], B["tail_t"])], dtype=float)
                for k in K_GRID}
            per_k = {}
            for k in K_GRID:
                rk_k = B.assign(_v=short_k[k]).groupby("win")["_v"].transform(rk).to_numpy()
                per_k[k] = 1 - (1 - rk_k) * (1 - B["_noisy"].to_numpy())
            aucs = {k: auc_or_none(B["y"].to_numpy(), v) for k, v in per_k.items()}
            aucs = {k: v for k, v in aucs.items() if v is not None}
            if len(aucs) < len(K_GRID):
                continue
            best_k = max(aucs, key=aucs.get)
            blocks.append({
                "block": bidx,
                "best_k": best_k,
                "auc_by_k": {str(k): round(v, 4) for k, v in aucs.items()},
                "persistence": round(float(np.mean(obs["persistence"])), 2),
                "clustering": round(float(np.mean(obs["clustering"])), 3),
                "n": int(len(B)), "n_atk": int(B["y"].sum()),
            })
        res["families"][fam] = {"n_blocks": len(blocks), "blocks": blocks}
        ks = [bl["best_k"] for bl in blocks]
        print(f"{fam:13s} {len(blocks):2d} blocks  best_k: {ks}", flush=True)

    # Does any observable predict best_k? Pool blocks across families.
    rows = [(bl["best_k"], bl["persistence"], bl["clustering"], fam)
            for fam, d in res["families"].items() for bl in d["blocks"]]
    if len(rows) > 3:
        k = np.array([r[0] for r in rows], dtype=float)
        pe = np.array([r[1] for r in rows], dtype=float)
        cl = np.array([r[2] for r in rows], dtype=float)
        def corr(a, b):
            if a.std() == 0 or b.std() == 0:
                return None
            return round(float(np.corrcoef(a, b)[0, 1]), 4)
        res["predictability"] = {
            "n_blocks": len(rows),
            "corr_persistence_vs_bestk": corr(pe, k),
            "corr_clustering_vs_bestk": corr(cl, k),
            "distinct_best_k_values": sorted(set(int(x) for x in k)),
        }
        p = res["predictability"]
        print(f"\npooled {p['n_blocks']} blocks; best_k values seen: "
              f"{p['distinct_best_k_values']}")
        print(f"  corr(persistence, best_k) = {p['corr_persistence_vs_bestk']}")
        print(f"  corr(clustering,  best_k) = {p['corr_clustering_vs_bestk']}")
        strong = [c for c in (p["corr_persistence_vs_bestk"],
                              p["corr_clustering_vs_bestk"])
                  if c is not None and abs(c) > 0.5]
        res["verdict"] = (
            f"an observable correlates with best k (|r|>0.5) on {len(strong)}/2 -> "
            "routing is plausibly implementable" if strong else
            "NO label-free observable predicts the best k (|r|<=0.5) -> routing "
            "is NOT implementable without the attack; tune per site instead")

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n{res.get('verdict','')}")
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
