"""Identify each checkpoint's training data EMPIRICALLY, from the scaler itself.

The two checkpoints that documentation cannot settle (`gnn_autoencoder_v1.pt`,
"saved by smoke" per CHANGELOG 2026-08-25, and `gnn_temporal_fused_v1.pt`,
an ablation arm) have no recorded training command. Rather than guess, use the
scaler as physical evidence.

`NodeScaler.fit` sets `lo`/`hi` to the per-feature min and max of the TRAINING
graphs. Those are data fingerprints: fit a scaler on each candidate corpus and
see which one the checkpoint's stored bounds actually match.

    python experiments/E47_provenance_audit/exp_e47_scaler_forensics.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from gnn_model import GraphAutoencoder, NodeScaler
from graph_builder import build_graphs, normalize_columns, read_flows

DET = ROOT / "detection"
ORIG = ROOT / "data" / "GeneratedLabelledFlows" / "TrafficLabelling"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
OUT = Path(__file__).resolve().parent / "exp_e47_scaler_forensics.json"

CANDIDATES = {
    "original_monday": lambda: _graphs(ORIG / "Monday-WorkingHours.pcap_ISCX.csv",
                                       limit=200_000),
    "clean_monday": lambda: _graphs(CLEAN / "monday.csv"),
}


def _graphs(csv: Path, limit: int | None = None):
    df = normalize_columns(read_flows(csv, limit=limit))
    lab = df["label"].astype(str).str.strip().str.upper()
    df = df[lab == "BENIGN"].sort_values("timestamp")
    # Fit a reference for BOTH feature generations, since the shipped
    # checkpoints span 8-dim v1 and 19-dim v2 and the scaler dimension
    # identifies which is which.
    return {"v1": build_graphs(df, window_seconds=60, feature_set="v1"),
            "v2": build_graphs(df, window_seconds=60, feature_set="v2")}


def bounds(graphs, log: bool):
    sc = NodeScaler(log=log).fit(graphs)
    return (np.asarray(sc.lo, dtype=np.float64),
            np.asarray(sc.hi, dtype=np.float64))


def compare(ck_lo, ck_hi, ref_lo, ref_hi):
    """Relative error on the hi vector, which is the discriminating one.

    lo is often 0.0 for count features (the minimum really is zero), so it
    carries almost no information; hi is where two corpora differ.
    """
    scale = np.maximum(np.abs(ref_hi), 1.0)
    d_hi = float(np.abs(ck_hi - ref_hi).max() / scale.max())
    d_hi_mean = float(np.mean(np.abs(ck_hi - ref_hi) / scale))
    d_lo = float(np.abs(ck_lo - ref_lo).max() / max(np.abs(ref_lo).max(), 1.0))
    return {"hi_max_rel": round(d_hi, 6), "hi_mean_rel": round(d_hi_mean, 6),
            "lo_max_rel": round(d_lo, 6)}


def main():
    res = {"note": "Scaler-bound forensics. lo/hi are per-feature min/max of the "
                   "TRAINING graphs, so they fingerprint the corpus. Used to "
                   "settle two checkpoints whose training command was never "
                   "recorded. Reference bounds are fitted on 200k BENIGN flows "
                   "of each Monday; a checkpoint trained on more data than that "
                   "may differ slightly on hi, so the comparison is indicative "
                   "not exact.",
           "references": {}, "checkpoints": {}}

    for name, fn in CANDIDATES.items():
        try:
            byfs = fn()
            for fs, gs in byfs.items():
                for log in (True, False):
                    lo, hi = bounds(gs, log)
                    res["references"][f"{name}/{fs} log={log}"] = {
                        "n_graphs": len(gs), "n_dim": len(hi),
                        "lo": lo.tolist(), "hi": hi.tolist()}
                print(f"reference {name}/{fs}: {len(gs)} graphs")
        except Exception as e:
            res["references"][name] = {"error": f"{type(e).__name__}: {e}"}
            print(f"reference {name}: FAILED {e}")

    targets = ["gnn_autoencoder_v1.pt", "gnn_autoencoder_v1_logscale.pt",
               "gnn_autoencoder_v1_logscale_v2.pt", "gnn_temporal_fused_v1.pt",
               "gnn_improved_s0.pt", "gnn_improved_replay.pt"]
    for f in targets:
        p = DET / f
        if not p.exists():
            continue
        b = torch.load(p, map_location="cpu", weights_only=True)
        sc = b["scaler"]
        ck_lo = np.asarray(sc["lo"], dtype=np.float64)
        ck_hi = np.asarray(sc["hi"], dtype=np.float64)
        ck_log = bool(sc.get("log", False))
        # the checkpoint's own feature count tells us which generation it is
        in_dim = int(np.asarray(ck_hi).shape[0])
        fs = "v2" if in_dim == 19 else ("v1" if in_dim == 8 else f"dim{in_dim}")
        row = {"in_dim": in_dim, "feature_set": fs, "log": ck_log, "matches": {}}
        for rname, ref in res["references"].items():
            if "error" in ref or len(ref["hi"]) != in_dim:
                continue
            c = compare(ck_lo, ck_hi, np.asarray(ref["lo"]), np.asarray(ref["hi"]))
            row["matches"][rname] = c
        if row["matches"]:
            # Judge on the MARGIN between the two corpora, not on absolute
            # error. The reference is fitted on a bounded slice of Monday, so
            # even the right corpus will not match to 1e-6; what matters is
            # that the right corpus is orders of magnitude closer than the
            # wrong one.
            ranked = sorted(row["matches"].items(), key=lambda kv: kv[1]["hi_mean_rel"])
            (bn, bc), runner = ranked[0], (ranked[1] if len(ranked) > 1 else None)
            row["best_match"] = bn
            row["best_hi_mean_rel"] = bc["hi_mean_rel"]
            if runner is not None:
                margin = (runner[1]["hi_mean_rel"] / max(bc["hi_mean_rel"], 1e-9))
                row["margin_vs_runner_up"] = round(margin, 1)
                row["runner_up"] = runner[0]
                row["verdict"] = ("discriminating" if margin >= 5.0
                                  else "AMBIGUOUS - corpora too close to call")
            else:
                row["margin_vs_runner_up"] = None
                row["verdict"] = "only one comparable corpus"
        else:
            row["best_match"] = None
            row["verdict"] = "no comparable reference"
        res["checkpoints"][f] = row
        print(f"{f:34s} dim={in_dim:2d} -> {row['best_match']:26s} "
              f"err={row.get('best_hi_mean_rel')} margin={row.get('margin_vs_runner_up')} "
              f"[{row['verdict']}]")

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
