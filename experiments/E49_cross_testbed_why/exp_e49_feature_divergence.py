"""E49: WHY do the two extractors learn different notions of normal?

The cross-testbed gap is methodologically handled but mechanistically
unexplained. E17 exonerated the architecture (same net, clean data, 4 of 7
families fixed). E27 ruled out pooling (it learns neither). E29/E42 found
replay-tuning works on 5 of 7. Nothing says WHY.

This measures the most likely mechanism directly, before any training: the two
extraction pipelines do not emit the same feature VALUES for the same kind of
traffic, and if a subset of features is dead or wildly rescaled in one corpus,
the model's learned "normality" is anchored to features that mean something
different on the other side.

Three questions, all answerable from the two Monday files:
  1. Which features are DEAD (constant / all-NaN / all-zero) in one corpus only?
  2. How far does each feature's benign distribution move between extractors?
  3. Do the two corpora even describe the same traffic?

    python experiments/E49_cross_testbed_why/exp_e49_feature_divergence.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import normalize_columns

ORIG = ROOT / "data" / "GeneratedLabelledFlows" / "TrafficLabelling"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
OUT = Path(__file__).resolve().parent / "exp_e49_feature_divergence.json"

# Features the v2 graph node vector actually reads (19 host dims derived from
# these); a divergence in a heavily-weighted feature matters more than one in a
# feature the graph never touches.
DURATION_HINT = ("duration", "iat", "time", "timestamp")


def load(path: Path, benign_only: bool = True) -> pd.DataFrame:
    d = normalize_columns(pd.read_csv(path, low_memory=True))
    if benign_only and "label" in d.columns:
        lab = d["label"].astype(str).str.strip().str.upper()
        d = d[lab == "BENIGN"].copy()
    return d


def numeric_features(d: pd.DataFrame) -> list[str]:
    out = []
    for c in d.columns:
        if c in ("label", "src_ip", "dst_ip", "timestamp", "source", "dest",
                 "src", "dst", "Source", "Destination", "proto", "flgs",
                 "type", "service", "state", "attack", "Attack"):
            continue
        s = pd.to_numeric(d[c], errors="coerce")
        if s.notna().sum() > 0:
            out.append(c)
    return out


def profile(d: pd.DataFrame, feats: list[str]) -> dict:
    p = {}
    for c in feats:
        s = pd.to_numeric(d[c], errors="coerce")
        n = int(s.notna().sum())
        nn = float(s.isna().mean())
        uniq = int(s.nunique(dropna=True))
        p[c] = {
            "nan_frac": round(nn, 4),
            "n_unique": uniq,
            "mean": float(s.mean()) if n else None,
            "p50": float(s.quantile(.5)) if n else None,
            "p99": float(s.quantile(.99)) if n else None,
            "max": float(s.max()) if n else None,
            "DEAD": bool(uniq <= 1),
        }
    return p


def ks_like(a: np.ndarray, b: np.ndarray) -> float:
    """Cheap Kolmogorov-Smirnov statistic on the empirical CDFs.

    KS is distribution-free, so it does not assume the two extractors produce
    comparable scales -- which is exactly the question. Returns 0..1.
    """
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size < 10 or b.size < 10:
        return float("nan")
    grid = np.unique(np.concatenate([
        np.quantile(a, np.linspace(0, 1, 101)),
        np.quantile(b, np.linspace(0, 1, 101))]))
    ca = np.searchsorted(np.sort(a), grid, side="right") / a.size
    cb = np.searchsorted(np.sort(b), grid, side="right") / b.size
    return float(np.max(np.abs(ca - cb)))


def main():
    o = load(ORIG / "Monday-WorkingHours.pcap_ISCX.csv")
    c = load(CLEAN / "monday.csv")

    fo, fc = set(numeric_features(o)), set(numeric_features(c))
    shared = sorted(fo & fc)
    only_o, only_c = sorted(fo - fc), sorted(fc - fo)

    po, pc = profile(o, shared), profile(c, shared)

    rows = []
    for f in shared:
        so = pd.to_numeric(o[f], errors="coerce").to_numpy(dtype=float)
        sc = pd.to_numeric(c[f], errors="coerce").to_numpy(dtype=float)
        d = {
            "feature": f,
            "dead_orig": po[f]["DEAD"], "dead_clean": pc[f]["DEAD"],
            "dead_in_one_only": bool(po[f]["DEAD"] != pc[f]["DEAD"]),
            "nan_orig": po[f]["nan_frac"], "nan_clean": pc[f]["nan_frac"],
            "nan_gap": round(abs(po[f]["nan_frac"] - pc[f]["nan_frac"]), 4),
            "ks": None,
            "p50_orig": po[f]["p50"], "p50_clean": pc[f]["p50"],
        }
        # compare on the CLEAN side's scale: if one is constant/zero, KS is
        # meaningless and the dead-flag is the real signal
        if not (po[f]["DEAD"] or pc[f]["DEAD"]):
            d["ks"] = round(ks_like(so, sc), 4)
        d["duration_like"] = any(h in f.lower() for h in DURATION_HINT)
        rows.append(d)

    rows.sort(key=lambda r: (-(r["ks"] if r["ks"] is not None else -1)))
    dead_one = [r for r in rows if r["dead_in_one_only"]]
    ks_rows = [r for r in rows if r["ks"] is not None]
    ks_rows.sort(key=lambda r: -r["ks"])

    # traffic identity: are these the same benign traffic at all?
    def host_set(d):
        cols = [x for x in ("src_ip", "dst_ip") if x in d.columns]
        return set(d[cols].astype(str).values.ravel().tolist()) if cols else set()

    ho, hc = host_set(o), host_set(c)
    jacc = len(ho & hc) / max(len(ho | hc), 1)

    res = {
        "question": "why do the two extractors learn different notions of normal?",
        "rows": {
            "orig_benign_flows": int(len(o)),
            "clean_benign_flows": int(len(c)),
            "numeric_features_orig": len(fo),
            "numeric_features_clean": len(fc),
            "shared": len(shared),
            "only_in_orig": only_o,
            "only_in_clean": only_c,
        },
        "host_overlap": {"orig_hosts": len(ho), "clean_hosts": len(hc),
                         "jaccard": round(jacc, 4),
                         "note": "low jaccard => the two Mondays are "
                                 "different network segments, not just "
                                 "different extractions"},
        "dead_in_one_corpus_only": [
            {"feature": r["feature"], "dead_orig": r["dead_orig"],
             "dead_clean": r["dead_clean"]} for r in dead_one],
        "top_ks_divergence": [
            {"feature": r["feature"], "ks": r["ks"],
             "p50_orig": r["p50_orig"], "p50_clean": r["p50_clean"]}
            for r in ks_rows[:15]],
        "ks_summary": {
            "n_compared": len(ks_rows),
            "ks_median": round(float(np.nanmedian([r["ks"] for r in ks_rows])), 4),
            "ks_p90": round(float(np.nanpercentile([r["ks"] for r in ks_rows], 90)), 4),
            "frac_ks_gt_0_5": round(float(np.mean(
                [r["ks"] > 0.5 for r in ks_rows])), 4),
        },
        "all_features": rows,
    }
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")

    print(f"benign flows: orig {len(o):,}  clean {len(c):,}")
    print(f"numeric features: orig {len(fo)}  clean {len(fc)}  shared {len(shared)}")
    if only_o:
        print(f"  only in orig: {only_o}")
    if only_c:
        print(f"  only in clean: {only_c}")
    print(f"\nhost overlap (Jaccard): {jacc:.4f}  "
          f"({len(ho)} orig vs {len(hc)} clean distinct hosts)")
    print(f"\nDEAD in one corpus only: {len(dead_one)}")
    for r in dead_one[:10]:
        print(f"  {r['feature']:28s} dead_orig={r['dead_orig']} "
              f"dead_clean={r['dead_clean']}")
    s = res["ks_summary"]
    print(f"\nKS divergence over {s['n_compared']} comparable features: "
          f"median {s['ks_median']}, p90 {s['ks_p90']}, "
          f"{100*s['frac_ks_gt_0_5']:.0f}% above 0.5")
    print("\ntop 12 most-divergent features:")
    for r in res["top_ks_divergence"][:12]:
        print(f"  {r['feature']:28s} KS {r['ks']:.3f}   "
              f"p50 orig {r['p50_orig']!s:>12}  clean {r['p50_clean']!s:>12}")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()
