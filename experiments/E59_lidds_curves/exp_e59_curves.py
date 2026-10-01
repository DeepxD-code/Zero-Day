"""E59: close E58's two caveats without new data.

E58's result is solid (+0.0483, 2.19 SD) but two things were left open, and
both are answerable from the data already downloaded:

1. **F1 = 0.0000 at one operating point.** A single 10%-FPR threshold is a weak
   measure: the count-AE "detects nothing" there, but that says as much about the
   threshold as about the model. This replaces the single point with a full
   DETECTION-RATE vs FALSE-POSITIVE-RATE curve for both arms, so the claim
   becomes "at FPR x the seq-AE detects y" across the whole range instead of one
   operating point.

2. **210 training traces.** If the count vector is genuinely limited by what a
   histogram can represent (E58's reading), then more data should help BOTH arms
   roughly equally and the GAP should persist or shrink slowly. If instead the
   gap is a data-starvation artefact, the gap should close fast as n grows. A
   learning curve over subsampled training sets separates those two readings,
   and it is the direct test of the conclusion E58 drew.

    python experiments/E59_lidds_curves/exp_e59_curves.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "E01_host_seqae"))
sys.path.insert(0, str(ROOT / "experiments" / "E23_host_ae_hmm"))

from lid_ds_loader import load_lid_ds
from host_features import index_sequence, pin_vocab, count_vector
from host_ae import train as train_count_ae
import exp_host_seqae as e01
from exp_host_seqae import train_seqae, score_seqae
from train_health import require_population

DATA = ROOT / "data" / "practice" / "LID-DS_SyscallRecords"
OUT = Path(__file__).resolve().parent / "exp_e59_curves.json"
SEEDS = [0, 1, 2, 3]
EPOCHS = 20                      # E58 picked ep 20 on all 4 seeds (interior)
SIZES = [25, 50, 100, 210]
FPRS = [0.01, 0.02, 0.05, 0.10, 0.20, 0.30]


def score_all(model, seqs, V, device, batch=32):
    out = []
    for i in range(0, len(seqs), batch):
        out.append(np.concatenate([score_seqae(model, seqs[i:i + batch], V,
                                               device)]))
    return np.concatenate(out)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = load_lid_ds(DATA)
    tr = [t for t in traces if t["split"] == "train" and t["label"] == "normal"]
    va = [t for t in traces if t["split"] == "val" and t["label"] == "normal"]
    te_b = [t for t in traces if t["split"] == "test" and t["label"] == "normal"]
    te_a = [t for t in traces if t["split"] == "test" and t["label"] == "attack"]
    pin = pin_vocab([t["seq"] for t in tr])
    V = pin["V"]
    va_i = [index_sequence(t["seq"], pin) for t in va]
    tb_i = [index_sequence(t["seq"], pin) for t in te_b]
    ta_i = [index_sequence(t["seq"], pin) for t in te_a]
    y = np.array([0] * len(tb_i) + [1] * len(ta_i))
    require_population("E59 test", y)

    res = {"seeds": SEEDS, "epochs": EPOCHS, "sizes": SIZES, "fprs": FPRS,
           "curve": {}, "learning": {}, "n_val": len(va_i),
           "n_test": int(len(y)), "n_attack": len(ta_i)}

    # ---------- part 1: detection vs FPR, full training set --------------
    curves = {a: {str(f): [] for f in FPRS} for a in ("seqae", "countae")}
    aucs = {a: [] for a in ("seqae", "countae")}
    for seed in SEEDS:
        tr_i = [index_sequence(t["seq"], pin) for t in tr]
        Xtr = torch.tensor(np.stack([count_vector(t["seq"], pin) for t in tr]),
                           dtype=torch.float32)
        def vecs(ts):
            return torch.tensor(np.stack([count_vector(t["seq"], pin) for t in ts]),
                                dtype=torch.float32)
        # seq-AE
        m = train_seqae(tr_i, V, EPOCHS, seed, device)
        sv = score_all(m, va_i, V, device)
        st = np.concatenate([score_all(m, tb_i, V, device),
                             score_all(m, ta_i, V, device)])
        aucs["seqae"].append(float(_auc(y, st)))
        for f in FPRS:
            curves["seqae"][str(f)].append(_detect(st, y, sv, f))
        # count-AE
        mdl, scl, _ = train_count_ae(Xtr, epochs=EPOCHS, seed=seed,
                                      device=device, quiet=True)
        with torch.no_grad():
            cv = mdl.anomaly_score(scl.transform(vecs(va)).to(device)).cpu().numpy()
            ct = mdl.anomaly_score(scl.transform(
                torch.cat([vecs(te_b), vecs(te_a)])).to(device)).cpu().numpy()
        aucs["countae"].append(float(_auc(y, ct)))
        for f in FPRS:
            curves["countae"][str(f)].append(_detect(ct, y, cv, f))
        print(f"  seed {seed}: seqAUC {aucs['seqae'][-1]:.4f} "
              f"cntAUC {aucs['countae'][-1]:.4f}", flush=True)

    for a in ("seqae", "countae"):
        res["curve"][a] = {str(f): {"detection_rate": round(float(np.mean(v)), 4),
                                    "sd": round(float(np.std(v, ddof=1)), 4)}
                           for f, v in curves[a].items()}
        res["curve"][a]["auc_mean"] = round(float(np.mean(aucs[a])), 4)
        res["curve"][a]["auc_sd"] = round(float(np.std(aucs[a], ddof=1)), 4)
    print("\ndetection rate at fixed FPR on validation benign:")
    print(f"  {'FPR':>6} {'seq-AE':>16} {'count-AE':>16}")
    for f in FPRS:
        s, c = res["curve"]["seqae"][str(f)], res["curve"]["countae"][str(f)]
        print(f"  {f:>6.0%} {s['detection_rate']:>10.3f}+-{s['sd']:.3f} "
              f"{c['detection_rate']:>10.3f}+-{c['sd']:.3f}")

    # ---------- part 2: learning curve ----------------------------------
    for n in SIZES:
        row = {}
        for a in ("seqae", "countae"):
            vals = []
            for seed in SEEDS:
                rng = np.random.default_rng(seed)
                idx = rng.permutation(len(tr))[:n]
                sub = [tr[i] for i in idx]
                tr_i = [index_sequence(t["seq"], pin) for t in sub]
                Xtr = torch.tensor(
                    np.stack([count_vector(t["seq"], pin) for t in sub]),
                    dtype=torch.float32)
                if a == "seqae":
                    m = train_seqae(tr_i, V, EPOCHS, seed, device)
                    st = np.concatenate([score_all(m, tb_i, V, device),
                                         score_all(m, ta_i, V, device)])
                else:
                    mdl, scl, _ = train_count_ae(Xtr, epochs=EPOCHS, seed=seed,
                                                 device=device, quiet=True)
                    def vecs(ts):
                        return torch.tensor(
                            np.stack([count_vector(t["seq"], pin) for t in ts]),
                            dtype=torch.float32)
                    with torch.no_grad():
                        st = mdl.anomaly_score(scl.transform(
                            torch.cat([vecs(te_b), vecs(te_a)])
                        ).to(device)).cpu().numpy()
                vals.append(float(_auc(y, st)))
            row[a] = {"mean": round(float(np.mean(vals)), 4),
                      "sd": round(float(np.std(vals, ddof=1)), 4)}
        row["delta"] = round(row["seqae"]["mean"] - row["countae"]["mean"], 4)
        res["learning"][str(n)] = row
        print(f"  n={n:4d}  seqAE {row['seqae']['mean']:.4f}  "
              f"countAE {row['countae']['mean']:.4f}  delta {row['delta']:+.4f}",
              flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


def _auc(y, s):
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(np.asarray(y), np.asarray(s, dtype=float))


def _detect(test_scores, y, val_scores, target_fpr):
    """Threshold on validation benign at `target_fpr`, then report detection
    rate on the test attacks."""
    thr = float(np.quantile(val_scores, 1.0 - target_fpr))
    fire = np.asarray(test_scores, dtype=float) >= thr
    y = np.asarray(y)
    n_atk = int((y == 1).sum())
    return float(fire[y == 1].sum() / max(n_atk, 1))


if __name__ == "__main__":
    main()