"""
E6 (P18 WATCH): attribution rank-shift under host evasions.

P18 separates adversarial from clean inputs in SHAP-attribution space even
when scores overlap. Our port (LOO attributions on the shipped host AE, A2
machinery): for each TEST attack TP, attribution vector |Delta| over 153
dims on the CLEAN trace vs its M1/M2/M3-mimicked twin (E1 probes, seed 7).
Metric: mean Spearman rho between clean and mimicked attribution rankings.
Baseline: split-half bootstrap over clean TPs (attribution noise floor).
A rank-shift far above the floor = attribution-space evasion fingerprint.

    python detection/exp_e6_attr_shift.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.stats import spearmanr

from host_features import count_vector, index_sequence, load_adfa, pin_vocab
from host_ae import HostAutoencoder, HostScaler
from exp_host_ablation import split_traces, tune_threshold
from exp_host_seqae import mimicry

OUT = Path(__file__).resolve().parent / "exp_e6_attr_shift.json"
CKPT = Path(__file__).resolve().parent / "host_autoencoder_adfa.pt"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = load_adfa()
    tr = [t for t in traces if t["split"] == "train"]
    pin = pin_vocab([t["seq"] for t in tr])
    Xtr = np.stack([count_vector(t["seq"], pin) for t in tr])
    med = np.median(Xtr, axis=0)
    inv = {i: n for n, i in pin["vocab"].items()}

    blob = torch.load(CKPT, map_location="cpu", weights_only=True)
    model = HostAutoencoder(input_dim=blob["n_dim"])
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = HostScaler().load_state_dict(blob["scaler"])

    @torch.no_grad()
    def score(X):
        Xt = torch.tensor(np.asarray(X, dtype=np.float32))
        return model.anomaly_score(scaler.transform(Xt).to(device)).cpu().numpy()

    def attrs(X):
        s0 = score(X)
        A = np.zeros_like(X)
        for d in range(X.shape[1]):
            Xp = X.copy()
            Xp[:, d] = med[d]
            A[:, d] = s0 - score(Xp)
        return np.abs(A)

    val_b, test_b, val_a, test_a = split_traces(traces, 0)
    V = lambda ts: np.stack([count_vector(t["seq"], pin) for t in ts])
    yv = np.array([0] * len(val_b) + [1] * len(val_a))
    thr, _ = tune_threshold(yv, np.concatenate([score(V(val_b)), score(V(val_a))]))
    Xt = V(test_a)
    tp = Xt[score(Xt) >= thr]
    print(f"TPs: {len(tp)}/{len(Xt)}")
    A_clean = attrs(tp)

    ta_i = [index_sequence(t["seq"], pin) for t in test_a]
    tp_mask = score(Xt) >= thr
    ta_tp = [s for s, m in zip(ta_i, tp_mask) if m]
    train_idx = [index_sequence(t["seq"], pin) for t in tr]
    res = {}
    A_mims = {}
    for name, seqs in mimicry(ta_tp, train_idx, 7).items():
        raw = [[inv[int(x)] for x in s] for s in seqs]
        Xm = np.stack([count_vector(r, pin) for r in raw])
        A_mim = attrs(Xm)
        A_mims[name] = A_mim
        rhos = [float(spearmanr(A_clean[i], A_mim[i]).statistic) for i in range(len(tp))]
        res[name] = {"mean_rho": round(float(np.mean(rhos)), 4),
                     "std_rho": round(float(np.std(rhos)), 4)}
        print(f"{name:14s} rho {np.mean(rhos):.4f}+-{np.std(rhos):.4f}")

    # baseline: UNPAIRED clean-i vs mimicked-j (same family) = what "different
    # attribution identity" looks like. LOO is deterministic, so clean-vs-clean
    # paired rho is 1.0 exactly — any paired drop below the unpaired level means
    # evasion preserves identity (no fingerprint); paired AT unpaired level with
    # low absolute value means evasion destroys it.
    fams = np.array([t["family"] for t, m in zip(test_a, tp_mask) if m])
    rng = np.random.default_rng(0)
    unp = []
    for name, A_mim in A_mims.items():
        for i in range(len(tp)):
            same = np.where((fams == fams[i]) & (np.arange(len(tp)) != i))[0]
            if len(same) == 0:
                continue
            j = rng.choice(same)
            unp.append(float(spearmanr(A_clean[i], A_mim[j]).statistic))
    res["baseline_unpaired"] = {"mean_rho": round(float(np.mean(unp)), 4),
                                "std_rho": round(float(np.std(unp)), 4)}
    print(f"baseline unpaired rho {np.mean(unp):.4f}+-{np.std(unp):.4f}")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
