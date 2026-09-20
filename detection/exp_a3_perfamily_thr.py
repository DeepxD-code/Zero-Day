"""
A3 (P16 ADOPT): per-family vs global thresholds on the host pipeline.

P16's decision-level adaptation: tune the operating threshold PER attack
family on validation instead of one global argmax-F1. Same splits/checkpoint
as A2 (shipped host_autoencoder_adfa.pt, split-seed 0). Reports global-F1
arm vs per-family-F1 arm on TEST (macro recall + F1). Honest caveat: per-family
thresholds need labelled family samples at tune time (supervised touch).

    python detection/exp_a3_perfamily_thr.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from host_features import count_vector, load_adfa, pin_vocab
from host_ae import HostAutoencoder, HostScaler
from exp_host_ablation import pr_at_threshold, split_traces, tune_threshold

OUT = Path(__file__).resolve().parent / "exp_a3_perfamily_thr.json"
CKPT = Path(__file__).resolve().parent / "host_autoencoder_adfa.pt"


def best_f1_thr(y: np.ndarray, s: np.ndarray) -> tuple[float, float]:
    cands = np.unique(np.quantile(s, np.linspace(0, 1, 400)))
    best = max(((pr_at_threshold(y, s, t)[2], t) for t in cands))
    return float(best[1]), float(best[0])


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = load_adfa()
    tr = [t for t in traces if t["split"] == "train"]
    pin = pin_vocab([t["seq"] for t in tr])
    blob = torch.load(CKPT, map_location="cpu", weights_only=True)
    model = HostAutoencoder(input_dim=blob["n_dim"])
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = HostScaler().load_state_dict(blob["scaler"])

    @torch.no_grad()
    def score(ts):
        X = torch.tensor(np.stack([count_vector(t["seq"], pin) for t in ts]),
                         dtype=torch.float32)
        return model.anomaly_score(scaler.transform(X).to(device)).cpu().numpy()

    val_b, test_b, val_a, test_a = split_traces(traces, 0)
    sv_b, st_b = score(val_b), score(test_b)
    fams = sorted({t["family"] for t in val_a})
    res = {"global": {}, "per_family": {}}

    # GLOBAL arm
    yv = np.array([0] * len(val_b) + [1] * len(val_a))
    thr_g, _ = tune_threshold(yv, np.concatenate([sv_b, score(val_a)]))
    yt = np.array([0] * len(test_b) + [1] * len(test_a))
    p, r, f = pr_at_threshold(yt, np.concatenate([st_b, score(test_a)]), thr_g)
    res["global"] = {"thr": round(thr_g, 4), "f1": round(f, 4),
                     "prec": round(p, 4), "rec": round(r, 4)}
    print(f"GLOBAL thr={thr_g:.4f}: F1 {f:.4f} P {p:.4f} R {r:.4f}")

    # PER-FAMILY arm
    recs, f1s = [], []
    for fam in fams:
        va = [t for t in val_a if t["family"] == fam]
        ta = [t for t in test_a if t["family"] == fam]
        yv_f = np.array([0] * len(val_b) + [1] * len(va))
        thr_f, _ = best_f1_thr(yv_f, np.concatenate([sv_b, score(va)]))
        yt_f = np.array([0] * len(test_b) + [1] * len(ta))
        p, r, f = pr_at_threshold(yt_f, np.concatenate([st_b, score(ta)]), thr_f)
        res["per_family"][fam] = {"thr": round(thr_f, 4), "f1": round(f, 4),
                                  "rec": round(r, 4), "n": len(ta)}
        recs.append(r)
        f1s.append(f)
        print(f"  {fam:16s} thr={thr_f:.4f}: F1 {f:.4f} R {r:.4f} (n={len(ta)})")
    res["per_family"]["macro_rec"] = round(float(np.mean(recs)), 4)
    res["per_family"]["macro_f1"] = round(float(np.mean(f1s)), 4)
    print(f"PER-FAMILY macro R {np.mean(recs):.4f} macro F1 {np.mean(f1s):.4f}")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
