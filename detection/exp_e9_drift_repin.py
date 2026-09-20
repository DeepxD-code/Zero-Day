"""
E9 (P09 WATCH): re-pinning vs frozen threshold on a drifted host stream.

P09's core claim: adaptation beats frozen operation under drift. Our port,
scoring-only on the shipped host AE: Gaussian feature drift N(0,sigma) added
to count vectors at sigma = 0, 0.05, 0.1, 0.2 (both classes, seeded).
  frozen arm:   clean val-tuned threshold applied to drifted test
  re-pinned arm: threshold re-tuned on drifted VAL, applied to drifted test
(M6-style adaptation; needs labelled drifted val = disclosed supervised
touch.) Metric: test F1 per sigma per arm.

    python detection/exp_e9_drift_repin.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

from host_features import count_vector, load_adfa, pin_vocab
from host_ae import HostAutoencoder, HostScaler
from exp_host_ablation import pr_at_threshold, split_traces, tune_threshold

OUT = Path(__file__).resolve().parent / "exp_e9_drift_repin.json"
CKPT = Path(__file__).resolve().parent / "host_autoencoder_adfa.pt"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = load_adfa()
    tr = [t for t in traces if t["split"] == "train"]
    pin = pin_vocab([t["seq"] for t in tr])
    blob = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = HostAutoencoder(input_dim=blob["n_dim"])
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = HostScaler().load_state_dict(blob["scaler"])

    @torch.no_grad()
    def score(X):
        Xt = torch.tensor(np.asarray(X, dtype=np.float32))
        return model.anomaly_score(scaler.transform(Xt).to(device)).cpu().numpy()

    val_b, test_b, val_a, test_a = split_traces(traces, 0)
    V = lambda ts: np.stack([count_vector(t["seq"], pin) for t in ts])
    Xvb, Xva, Xtb, Xta = V(val_b), V(val_a), V(test_b), V(test_a)
    yv = np.array([0] * len(val_b) + [1] * len(val_a))
    yt = np.array([0] * len(test_b) + [1] * len(test_a))
    thr_clean, _ = tune_threshold(yv, np.concatenate([score(Xvb), score(Xva)]))

    res = {"thr_clean": round(float(thr_clean), 4), "sigmas": {}}
    for sig in [0.0, 0.05, 0.1, 0.2]:
        rng = np.random.default_rng(100 + int(sig * 1000))
        N = lambda X: np.clip(X + rng.normal(0, sig, X.shape), 0, None).astype(np.float32)
        sv = np.concatenate([score(N(Xvb)), score(N(Xva))])
        st = np.concatenate([score(N(Xtb)), score(N(Xta))])
        _, _, f_frozen = pr_at_threshold(yt, st, thr_clean)
        thr_re, _ = tune_threshold(yv, sv)
        _, _, f_repin = pr_at_threshold(yt, st, thr_re)
        res["sigmas"][str(sig)] = {"f1_frozen": round(float(f_frozen), 4),
                                   "f1_repin": round(float(f_repin), 4),
                                   "thr_repin": round(float(thr_re), 4)}
        print(f"sigma={sig:4.2f}: frozen F1 {f_frozen:.4f} vs re-pinned F1 {f_repin:.4f} (thr {thr_re:.4f})")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
