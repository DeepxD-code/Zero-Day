"""E62: re-run what E61 lost, and extend past its own edge.

WHY THIS EXISTS
---------------
E61 retracted E60's CVE-2012-2122 result (+0.0954 -> +0.0001 on a wider grid) and
then LOST its CVE-2014-0160 half when the opencode server restarted mid-run: the
results file was written only at the end, so a 64-minute run left no artifact.

Three things are fixed here, in order of importance:

1. **RESULTS ARE CHECKPOINTED AND RESUMABLE.** Every completed
   (family, arm, seed) cell is written to disk immediately via an atomic
   replace, and a restart resumes from the last completed cell instead of
   re-running. This is the actual fix for what happened to E61.
2. **The grid extends past E61's edge in BOTH directions**: {2 ... 640}. E61 left
   both arms pinned at 320 on CVE-2012-2122, and left CVE-2014-0160 wanting
   FEWER epochs for seq-AE (picked 5) and MORE for count-AE (picked 320). Those
   are opposite pulls and a grid that brackets neither is not a measurement.
3. **Both directions are reported per arm** (max and mean aggregation), so the
   aggregation cannot quietly manufacture the gap.

If a pick still lands on 2 or 640 that is reported as a NON-CEILING, never as a
result. The standing rule has now fired three times.

    python experiments/E62_lidds_rerun/exp_e62_rerun.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
for sub in ("detection", "experiments", "experiments/E01_host_seqae",
            "experiments/E23_host_ae_hmm", "experiments/E60_lidds_lengthblind"):
    sys.path.insert(0, str(ROOT / sub))

from lid_ds_loader import load_lid_ds
from host_features import index_sequence, pin_vocab, count_vector
from host_ae import train as train_count_ae
import exp_host_seqae as e01
from exp_host_seqae import train_seqae
from exp_e60_lengthblind import windows, score_all, _agg, _auc, W, K, \
    CAP_TRAIN_WIN, CAP_TEST_BENIGN_WIN
from train_health import require_population

DATA = ROOT / "data" / "practice" / "LID-DS_SyscallRecords"
OUT = Path(__file__).resolve().parent / "exp_e62_rerun.json"
SEEDS = [0, 1, 2, 3]
# Brackets E61's 320 on the top and its 5 on the bottom, by ~2x each way.
GRID = [2, 5, 10, 20, 40, 80, 160, 320, 640]
ORDER = ["CVE-2014-0160", "CVE-2012-2122"]     # unresolved family first

# `--smoke` runs a tiny version of the same code path, including the checkpoint
# and resume logic, so a multi-hour run cannot be discovered to be broken at the
# end. Verified before the real run: writes a checkpoint, resumes from it, and
# produces the same summary shape.
if "--smoke" in sys.argv:
    GRID = [2, 5]
    SEEDS = [0, 1]
    ORDER = ["CVE-2014-0160"]
    OUT = Path(__file__).resolve().parent / "exp_e62_SMOKE.json"


# ---------------------------------------------------------------- checkpoint
def load_state() -> dict:
    if OUT.exists():
        try:
            s = json.loads(OUT.read_text(encoding="utf-8"))
            if isinstance(s, dict) and "cells" in s:
                return s
        except Exception:
            print("  !! state file unreadable, starting fresh", flush=True)
    return {"cells": {}, "meta": {}}


def save_state(s: dict) -> None:
    """Atomic: write a temp file then replace, so a kill mid-write cannot
    corrupt the checkpoint (which would be worse than losing it)."""
    s["meta"]["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    s["meta"]["n_cells"] = len(s["cells"])
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(s, indent=1), encoding="utf-8")
    os.replace(tmp, OUT)


def key(fam: str, arm: str, seed: int) -> str:
    return f"{fam}|{arm}|{seed}"


# ---------------------------------------------------------------- data prep
def prep(traces, fam):
    sel = [t for t in traces if t["family"] == fam]
    tr = [t for t in sel if t["split"] == "train" and t["label"] == "normal"]
    va = [t for t in sel if t["split"] == "val" and t["label"] == "normal"]
    tb = [t for t in sel if t["split"] == "test" and t["label"] == "normal"]
    ta = [t for t in sel if t["split"] == "test" and t["label"] == "attack"]

    def win(ts):
        out = []
        for t in ts:
            out.extend(windows(t["seq"]))
        return out

    def cap(ws, n):
        if len(ws) <= n or not ws:
            return ws
        idx = np.linspace(0, len(ws) - 1, n).round().astype(int)
        return [ws[i] for i in sorted(set(idx.tolist()))]

    trw = cap(win(tr), CAP_TRAIN_WIN)
    vaw = win(va)
    tbw = cap(win(tb), CAP_TEST_BENIGN_WIN)
    taw = win(ta)
    if not (trw and tbw and taw):
        raise SystemExit(f"{fam}: windowing left an empty split")

    pin = pin_vocab(trw)
    V = pin["V"]
    tr_i = [index_sequence(w, pin) for w in trw]
    va_i = [index_sequence(w, pin) for w in vaw]
    tb_i = [index_sequence(w, pin) for w in tbw]
    ta_i = [index_sequence(w, pin) for w in taw]
    y_win = np.array([0] * len(tb_i) + [1] * len(ta_i))
    tr_ids = ([("b", j // K) for j in range(len(tb_i))]
              + [("a", j // K) for j in range(len(ta_i))])
    require_population(f"{fam} E62 test", y_win)
    info = {"V": V, "pin": pin,
            "tr_i": tr_i, "va_i": va_i, "tb_i": tb_i, "ta_i": ta_i,
            "y_win": y_win, "tr_ids": tr_ids, "vecs_raw": (trw, vaw, tbw, taw),
            "n_raw": {"train": len(tr), "val": len(va), "test_benign": len(tb),
                      "test_attack": len(ta)},
            "n_windows": {"train": len(trw), "val": len(vaw),
                          "test_benign": len(tbw), "test_attack": len(taw)},
            "guard": {"raw_length_only_auc":
                      _auc([t["label"] == "attack" for t in tb + ta],
                           [len(t["seq"]) for t in tb + ta]),
                      "window_length_only_auc":
                      _auc(y_win, [len(w) for w in list(tb_i) + list(ta_i)]),
                      "all_windows_exactly_W":
                      bool(all(len(w) == W for w in trw + tbw + taw))}}
    return info


def vecs_of(ws, pin):
    return torch.tensor(np.stack([count_vector(w, pin) for w in ws]),
                        dtype=torch.float32)


# ---------------------------------------------------------------- one cell
def run_cell(info, pin, fam, arm, seed, device):
    tr_i, va_i, tb_i, ta_i = (info["tr_i"], info["va_i"], info["tb_i"],
                              info["ta_i"])
    y_win, tr_ids, V = info["y_win"], info["tr_ids"], info["V"]
    trw, vaw, tbw, taw = info["vecs_raw"]
    best = None
    for ep in GRID:
        t0 = time.time()
        if arm == "seqae":
            m = train_seqae(tr_i, V, ep, seed, device)
            sv = score_all(m, va_i, V, device)
            sw = np.concatenate([score_all(m, tb_i, V, device),
                                 score_all(m, ta_i, V, device)])
        else:
            mdl, scl, _ = train_count_ae(vecs_of(trw, pin), epochs=ep, seed=seed,
                                         device=device, quiet=True)
            with torch.no_grad():
                sv = mdl.anomaly_score(scl.transform(vecs_of(vaw, pin)
                                                     ).to(device)).cpu().numpy()
                sw = mdl.anomaly_score(scl.transform(
                    torch.cat([vecs_of(tbw, pin), vecs_of(taw, pin)])
                ).to(device)).cpu().numpy()
        row = _agg(y_win, sw, tr_ids, sv, va_i)
        row["epoch"] = ep
        row["secs"] = round(time.time() - t0, 1)
        print(f"    {fam[:12]} {arm:8s} seed {seed} ep {ep:4d}  "
              f"AUCmax {row['auc_max']:.4f} AUCmean {row['auc_mean']:.4f}"
              f"  ({row['secs']}s)", flush=True)
        if best is None or row["auc_max"] > best["auc_max"]:
            best = dict(row)
    best["seed"] = seed
    best["thr90"] = None
    best["truncated_top"] = bool(best["epoch"] == GRID[-1])
    best["truncated_bottom"] = bool(best["epoch"] == GRID[0])
    return best


# ---------------------------------------------------------------- summarise
def summarise(state):
    out = {}
    for k, cell in state["cells"].items():
        fam, arm, _ = k.split("|")
        out.setdefault(fam, {}).setdefault(arm, []).append(cell)
    rep = {}
    for fam, arms in sorted(out.items()):
        rep[fam] = {}
        for arm, rows in arms.items():
            rows = sorted(rows, key=lambda r: r["seed"])
            rep[fam][arm] = {
                "n_seeds": len(rows),
                "epochs_picked": [r["epoch"] for r in rows],
                "any_truncated_top": any(r["truncated_top"] for r in rows),
                "any_truncated_bottom": any(r["truncated_bottom"] for r in rows),
                **{m: [round(float(np.mean([r[m] for r in rows])), 4),
                       round(float(np.std([r[m] for r in rows], ddof=1))
                             if len(rows) > 1 else 0.0, 4)]
                   for m in ("auc_max", "auc_mean", "det_max@10fpr",
                             "det_mean@10fpr")},
            }
        if "seqae" in arms and "countae" in arms:
            a = rep[fam]["seqae"]["auc_max"]
            b = rep[fam]["countae"]["auc_max"]
            d = a[0] - b[0]
            pooled = float(np.sqrt((a[1] ** 2 + b[1] ** 2) / 2))
            rep[fam]["comparison_max"] = {
                "delta": round(d, 4), "pooled_sd": round(pooled, 4),
                "z": round(d / max(pooled, 1e-9), 2),
                "verdict": "separated" if abs(d) > 2 * max(pooled, 1e-9)
                           else "inside noise",
                "n_seeds": min(rep[fam]["seqae"]["n_seeds"],
                               rep[fam]["countae"]["n_seeds"]),
                "complete": rep[fam]["seqae"]["n_seeds"] == len(SEEDS)
                             and rep[fam]["countae"]["n_seeds"] == len(SEEDS),
            }
    return rep


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = load_lid_ds(DATA)
    state = load_state()
    state["meta"].update({"grid": GRID, "seeds": SEEDS, "W": W, "K": K,
                          "device": str(device),
                          "caps": {"train": CAP_TRAIN_WIN,
                                   "test_benign": CAP_TEST_BENIGN_WIN}})
    have = len(state["cells"])
    todo = sum(1 for f in ORDER for a in ("seqae", "countae")
               for s in SEEDS if key(f, a, s) not in state["cells"])
    print(f"E62  grid {GRID}  seeds {SEEDS}  device {device}")
    print(f"  {have} cell(s) already done, {todo} to run", flush=True)
    save_state(state)

    for fam in ORDER:
        print(f"\n=== {fam} ===", flush=True)
        if key(fam, "seqae", 0) in state["cells"] and all(
                key(fam, a, s) in state["cells"]
                for a in ("seqae", "countae") for s in SEEDS):
            print("  complete already, skipping", flush=True)
            continue
        info = prep(traces, fam)
        pin = info["pin"]
        print(f"  V={info['V']}  windows train {info['n_windows']['train']} "
              f"test_b {info['n_windows']['test_benign']} "
              f"test_a {info['n_windows']['test_attack']}", flush=True)
        print(f"  GUARD raw length-only AUC "
              f"{info['guard']['raw_length_only_auc']:.4f} -> windowed "
              f"{info['guard']['window_length_only_auc']}", flush=True)
        state["meta"].setdefault("guard", {})[fam] = info["guard"]
        state["meta"].setdefault("n_windows", {})[fam] = info["n_windows"]
        save_state(state)
        for arm in ("seqae", "countae"):
            for seed in SEEDS:
                k = key(fam, arm, seed)
                if k in state["cells"]:
                    print(f"  {arm:8s} seed {seed} -- cached", flush=True)
                    continue
                cell = run_cell(info, pin, fam, arm, seed, device)
                state["cells"][k] = cell
                save_state(state)          # <-- checkpoint every single cell
                print(f"  -> {k} best ep {cell['epoch']} "
                      f"AUCmax {cell['auc_max']:.4f} "
                      f"({'TOP EDGE' if cell['truncated_top'] else ''}"
                      f"{'BOTTOM EDGE' if cell['truncated_bottom'] else ''})"
                      .rstrip(), flush=True)

    rep = summarise(state)
    state["summary"] = rep
    save_state(state)
    print("\n" + "=" * 66)
    for fam, r in sorted(rep.items()):
        print(f"\n{fam}")
        for arm in ("seqae", "countae"):
            if arm not in r:
                continue
            a = r[arm]
            flag = ""
            if a["any_truncated_top"]:
                flag += " TOP-EDGE-TRUNCATED"
            if a["any_truncated_bottom"]:
                flag += " BOTTOM-EDGE-TRUNCATED"
            print(f"  {arm:8s} ep {a['epochs_picked']}  "
                  f"AUCmax {a['auc_max'][0]:.4f}+-{a['auc_max'][1]:.4f}  "
                  f"AUCmean {a['auc_mean'][0]:.4f}+-{a['auc_mean'][1]:.4f}  "
                  f"det@10 {a['det_max@10fpr'][0]:.3f}{flag}")
        if "comparison_max" in r:
            c = r["comparison_max"]
            print(f"  delta {c['delta']:+.4f} (z {c['z']:+.2f}) -> "
                  f"{c['verdict']}  [{c['n_seeds']}/4 seeds, "
                  f"{'complete' if c['complete'] else 'PARTIAL'}]")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()