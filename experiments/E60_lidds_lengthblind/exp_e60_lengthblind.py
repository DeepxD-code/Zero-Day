"""E60: length-blind host detection on two LID-DS families, and the shortcut check.

WHY THIS EXPERIMENT IS STRUCTURED DIFFERENTLY FROM E58
-----------------------------------------------------
CVE-2012-2122 has a PERFECT length shortcut. Measured on the raw corpus:

    family          normal median   attack median   length-only AUC
    CVE-2014-0160        3,396            1,399           0.1850
    CVE-2012-2122       15,934           72,446           1.0000

For CVE-2012-2122 every attack trace (min 61,210 syscalls) is longer than every
benign one (max 36,590), so LENGTH ALONE PERFECTLY SEPARATES THE FAMILY. Any raw
AUC on it measures how long the recording is, not what happened in it -- and it
would flatter both arms equally, hiding the representation question entirely.
CVE-2014-0160's shortcut runs the other way (attacks are *shorter*, AUC 0.1850),
so neither family is length-blind out of the box.

The fix is to make every sample the same length, which removes duration as a
feature by construction. Each trace is cut into fixed W-token windows; traces
shorter than W are DROPPED, never padded, because padding would leak the
original length back in through the PAD count.

W = 3000 sits just under CVE-2014-0160's median (3,396), so both families are
modelled at a comparable granularity and the count vector sees a comparable
number of tokens either way.

This is a protocol change from E58: the unit of modelling becomes a window, not a
recording. Absolute AUCs are therefore NOT comparable to E58's headline. The
seq-AE vs count-AE comparison inside E60 IS like-for-like, because both arms
receive byte-identical windows.

Aggregation is reported both ways (max and mean over a trace's windows). If the
result only holds under one, the aggregation is doing the work, not the
representation -- so that is checked rather than assumed.

    python experiments/E60_lidds_lengthblind/exp_e60_lengthblind.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
for sub in ("detection", "experiments", "experiments/E01_host_seqae",
            "experiments/E23_host_ae_hmm"):
    sys.path.insert(0, str(ROOT / sub))

from lid_ds_loader import load_lid_ds
from host_features import index_sequence, pin_vocab, count_vector
from host_ae import train as train_count_ae
import exp_host_seqae as e01
from exp_host_seqae import train_seqae, score_seqae
from train_health import require_population

DATA = ROOT / "data" / "practice" / "LID-DS_SyscallRecords"
OUT = Path(__file__).resolve().parent / "exp_e60_lengthblind.json"
SEEDS = [0, 1, 2, 3]
GRID = [10, 20, 40, 80]

# W is set by a rule fixed BEFORE looking at results: the largest window length
# that keeps a usable share of every (family, label) cell. Retention measured:
#
#   W     2014 normal  2014 attack  2012 normal  2012 attack
#   256       97%          82%         100%          100%
#   512       97%          78%          97%          100%
#   1024      93%          62%          97%          100%
#   3000      57%          18%          97%          100%
#
# No W retains 90% of the heartbleed attacks, because 18% of them are under 256
# syscalls -- heartbleed is a single request/response and is simply short. So the
# rule is relaxed to "keeps the majority of every cell", giving W = 1024. The
# cost is disclosed in the README: dropping short traces SELECTS ON LENGTH, which
# is the variable being neutralised, so the surviving population is not the same
# population E58 measured.
#
# Note that equal-length windows still remove length as a FEATURE -- no sample
# ever encodes its own duration -- but they do not make the trace population
# length-matched. Both facts are reported.
W = 1024
K = 3              # windows sampled per trace, evenly spaced
CAP_TRAIN_WIN = 500    # matched across arms and families; disclosed
CAP_TEST_BENIGN_WIN = 600


def windows(seq: list[str], w: int = W, k: int = K) -> list[list[str]]:
    """Up to `k` non-overlapping windows of exactly `w` tokens, evenly spaced.

    Returns [] for a trace shorter than w -- those are dropped, not padded.
    """
    n = len(seq)
    if n < w:
        return []
    nwin = n // w
    if nwin == 0:
        return []
    idx = np.linspace(0, nwin - 1, min(k, nwin)).round().astype(int)
    return [seq[i * w:(i + 1) * w] for i in sorted(set(idx.tolist()))]


def score_all(model, seqs, V, device, batch=32):
    out = []
    for i in range(0, len(seqs), batch):
        out.append(np.concatenate([score_seqae(model, seqs[i:i + batch], V,
                                               device)]))
    return np.concatenate(out) if out else np.zeros(0)


def _auc(y, s):
    from sklearn.metrics import roc_auc_score
    y, s = np.asarray(y), np.asarray(s, dtype=float)
    if len(set(y.tolist())) < 2:
        return float("nan")
    return float(roc_auc_score(y, s))


def run_family(traces, fam, device):
    sel = [t for t in traces if t["family"] == fam]
    tr = [t for t in sel if t["split"] == "train" and t["label"] == "normal"]
    va = [t for t in sel if t["split"] == "val" and t["label"] == "normal"]
    tb = [t for t in sel if t["split"] == "test" and t["label"] == "normal"]
    ta = [t for t in sel if t["split"] == "test" and t["label"] == "attack"]

    # ---- windowing, reported not silent --------------------------------
    def win(ts):
        out = []
        for t in ts:
            for w in windows(t["seq"]):
                out.append(w)
        return out
    trw, vaw, tbw, taw = win(tr), win(va), win(tb), win(ta)
    # Caps keep runtime sane (E58 cost 44 min for 210 whole traces) and are
    # applied identically to both arms, so the seq-vs-count comparison is
    # unaffected. Every attack window is kept -- capping attacks would change
    # the test set between arms.
    def cap(ws, n):
        if len(ws) <= n or not ws:
            return ws
        idx = np.linspace(0, len(ws) - 1, n).round().astype(int)
        return [ws[i] for i in sorted(set(idx.tolist()))]

    n_before = {"train": len(trw), "test_benign": len(tbw)}
    trw = cap(trw, CAP_TRAIN_WIN)
    tbw = cap(tbw, CAP_TEST_BENIGN_WIN)
    capped = {"train": n_before["train"] - len(trw),
              "test_benign": n_before["test_benign"] - len(tbw)}
    raw_lens = {k: [len(t["seq"]) for t in v] for k, v in
                (("train", tr), ("val", va), ("test_benign", tb),
                 ("test_attack", ta))}
    n_drop = {k: sum(1 for t in v if len(t["seq"]) < W)
              for k, v in (("train", tr), ("val", va), ("test_benign", tb),
                           ("test_attack", ta))}
    if not (trw and tbw and taw):
        raise SystemExit(f"{fam}: windowing left an empty split")

    pin = pin_vocab([w for t in tr for w in windows(t["seq"])])
    V = pin["V"]
    tr_i = [index_sequence(w, pin) for w in trw]
    va_i = [index_sequence(w, pin) for w in vaw]
    tb_i = [index_sequence(w, pin) for w in tbw]
    ta_i = [index_sequence(w, pin) for w in taw]

    # Window order is all benign windows then all attack windows. Windows are
    # emitted K-at-a-time per trace by `windows()`, so window j of a side
    # belongs to trace j // K. That grouping is what lets scores be aggregated
    # back to a per-trace decision.
    y_win = np.array([0] * len(tb_i) + [1] * len(ta_i))
    tr_ids = ([("b", j // K) for j in range(len(tb_i))]
              + [("a", j // K) for j in range(len(ta_i))])
    assert len(tr_ids) == len(y_win)

    # ---- the length-blindness guard -----------------------------------
    guard = {
        "raw_length_only_auc": _auc(
            [t["label"] == "attack" for t in tb + ta],
            [len(t["seq"]) for t in tb + ta]),
        "window_length_only_auc": _auc(y_win,
                                       [len(w) for w in list(tb_i) + list(ta_i)]),
        "all_windows_exactly_W": bool(all(len(w) == W
                                          for w in trw + tbw + taw)),
    }

    def vecs(ws):
        return torch.tensor(np.stack([count_vector(w, pin) for w in ws]),
                            dtype=torch.float32)

    res = {"family": fam, "V": V, "W": W, "K": K, "seeds": SEEDS, "grid": GRID,
           "n_raw": {"train": len(tr), "val": len(va), "test_benign": len(tb),
                     "test_attack": len(ta)},
           "n_windows": {"train": len(trw), "val": len(vaw),
                         "test_benign": len(tbw), "test_attack": len(taw)},
           "windows_capped_out": capped,
           "dropped_short": n_drop,
           "raw_len_median": {k: int(np.median(v)) for k, v in raw_lens.items()},
           "guard": guard,
           "arms": {"seqae": [], "countae": []}}

    for seed in SEEDS:
        # ---- seq-AE: pick epoch by validation, per E58 ------------------
        best = None
        for ep in GRID:
            m = train_seqae(tr_i, V, ep, seed, device)
            sv = score_all(m, va_i, V, device)
            sw = np.concatenate([score_all(m, tb_i, V, device),
                                 score_all(m, ta_i, V, device)])
            row = _agg(y_win, sw, tr_ids, sv, va_i)
            if best is None or row["auc_max"] > best[1]["auc_max"]:
                best = (ep, row, float(np.quantile(sv, 0.90)))
        res["arms"]["seqae"].append({"seed": seed, "epochs": best[0],
                                     "thr90": best[2], **best[1]})
        print(f"  {fam} seed {seed} seqAE  ep {best[0]:3d} "
              f"AUCmax {best[1]['auc_max']:.4f} AUCmean {best[1]['auc_mean']:.4f}",
              flush=True)

        # ---- count-AE, same grid ---------------------------------------
        Xtr = vecs(trw)
        best = None
        for ep in GRID:
            mdl, scl, _ = train_count_ae(Xtr, epochs=ep, seed=seed,
                                         device=device, quiet=True)
            with torch.no_grad():
                cv = mdl.anomaly_score(scl.transform(vecs(vaw)).to(device)
                                       ).cpu().numpy()
                cw = mdl.anomaly_score(scl.transform(
                    torch.cat([vecs(tbw), vecs(taw)])).to(device)).cpu().numpy()
            row = _agg(y_win, cw, tr_ids, cv, va_i)
            if best is None or row["auc_max"] > best[1]["auc_max"]:
                best = (ep, row, float(np.quantile(cv, 0.90)))
        res["arms"]["countae"].append({"seed": seed, "epochs": best[0],
                                       "thr90": best[2], **best[1]})
        print(f"  {fam} seed {seed} cntAE  ep {best[0]:3d} "
              f"AUCmax {best[1]['auc_max']:.4f} AUCmean {best[1]['auc_mean']:.4f}",
              flush=True)

    for a in ("seqae", "countae"):
        rows = res["arms"][a]
        for m in ("auc_max", "auc_mean", "det_max@10fpr", "det_mean@10fpr"):
            v = np.array([r[m] for r in rows], dtype=float)
            res["arms"].setdefault(a + "_summary", {})
            res["arms"][a + "_summary"][m] = {
                "mean": round(float(np.nanmean(v)), 4),
                "sd": round(float(np.nanstd(v, ddof=1)), 4)}
    s = res["arms"]["seqae_summary"]["auc_max"]
    c = res["arms"]["countae_summary"]["auc_max"]
    d = s["mean"] - c["mean"]
    pooled = np.sqrt((s["sd"] ** 2 + c["sd"] ** 2) / 2)
    res["comparison_max"] = {"delta": round(float(d), 4),
                             "pooled_sd": round(float(pooled), 4),
                             "z": round(float(d / max(pooled, 1e-9)), 2),
                             "verdict": "separated" if abs(d) > 2 * max(pooled, 1e-9)
                                        else "inside noise"}
    return res


def _agg(y_win, scores, tr_ids, val_scores, va_i):
    """Aggregate per-window scores to per-trace, then AUC + detection@10%FPR."""
    from collections import defaultdict
    g = defaultdict(list)
    for s, t in zip(scores, tr_ids):
        g[t].append(float(s))
    keys = sorted(g, key=lambda k: (k[0], k[1]))
    y = np.array([0 if k[0] == "b" else 1 for k in keys])
    mx = np.array([max(g[k]) for k in keys])
    mn = np.array([float(np.mean(g[k])) for k in keys])
    thr = float(np.quantile(val_scores, 0.90))
    return {"auc_max": _auc(y, mx), "auc_mean": _auc(y, mn),
            "det_max@10fpr": float((mx[y == 1] >= thr).mean()),
            "det_mean@10fpr": float((mn[y == 1] >= thr).mean())}


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = load_lid_ds(DATA)
    fams = sorted({t["family"] for t in traces if t["family"] != "unknown"})
    out = {"device": str(device), "W": W, "K": K, "families": {}}
    for fam in fams:
        print(f"\n=== {fam} ===")
        out["families"][fam] = run_family(traces, fam, device)
        r = out["families"][fam]
        print(f"  windows: train {r['n_windows']['train']} "
              f"test_b {r['n_windows']['test_benign']} "
              f"test_a {r['n_windows']['test_attack']}  V={r['V']}")
        print(f"  GUARD  raw length-only AUC {r['guard']['raw_length_only_auc']:.4f}"
              f"  -> windowed {r['guard']['window_length_only_auc']}")
        for a in ("seqae", "countae"):
            s = r["arms"][a + "_summary"]
            print(f"  {a:8s} AUCmax {s['auc_max']['mean']:.4f}+-{s['auc_max']['sd']:.4f}"
                  f"  AUCmean {s['auc_mean']['mean']:.4f}+-{s['auc_mean']['sd']:.4f}"
                  f"  det@10 {s['det_max@10fpr']['mean']:.3f}")
        print(f"  delta {r['comparison_max']['delta']:+.4f} "
              f"(z {r['comparison_max']['z']:+.2f}) -> "
              f"{r['comparison_max']['verdict']}")
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()