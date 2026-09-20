"""
A2 (P11 ADOPT): perturbation flip-test on the shipped host AE.

P11's protocol: attributions must be CAUSAL — perturbing the top-attributed
input must flip the decision far more often than perturbing random inputs.
Here: shipped host_autoencoder_adfa.pt (seed 1, 40ep) + pinned vocab.
Attribution = leave-one-out Delta-score vs benign-train median per dim.
Flip = set top-k dims to benign median, count TP attacks falling below the
val-tuned threshold. Random-k is the baseline. The minimal flip set is also
the evasion-handle list for D's harness (which syscalls hide the attack).

    python detection/exp_a2_fliptest.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from host_features import count_vector, index_sequence, load_adfa, load_nr_map, pin_vocab
from host_ae import HostAutoencoder, HostScaler
from exp_host_ablation import split_traces, tune_threshold

OUT = Path(__file__).resolve().parent / "exp_a2_fliptest.json"
CKPT = Path(__file__).resolve().parent / "host_autoencoder_adfa.pt"


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = load_adfa()
    tr = [t for t in traces if t["split"] == "train"]
    pin = pin_vocab([t["seq"] for t in tr])
    Xtr = np.stack([count_vector(t["seq"], pin) for t in tr])
    med = np.median(Xtr, axis=0)
    nr = load_nr_map()
    idx2name = {i: nr.get(n, f"nr_{n}") for n, i in pin["vocab"].items()}

    blob = torch.load(CKPT, map_location="cpu", weights_only=True)
    model = HostAutoencoder(input_dim=blob["n_dim"])
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = HostScaler().load_state_dict(blob["scaler"])

    @torch.no_grad()
    def score(X: np.ndarray):
        Xt = torch.tensor(X, dtype=torch.float32)
        return model.anomaly_score(scaler.transform(Xt).to(device)).cpu().numpy()

    val_b, test_b, val_a, test_a = split_traces(traces, 0)
    V = lambda ts: np.stack([count_vector(t["seq"], pin) for t in ts])
    yv = np.array([0] * len(val_b) + [1] * len(val_a))
    thr, _ = tune_threshold(yv, np.concatenate([score(V(val_b)), score(V(val_a))]))
    Xt = V(test_a)
    st = score(Xt)
    tp_idx = np.where(st >= thr)[0]
    print(f"thr={thr:.4f} | test attacks {len(Xt)}, TPs {len(tp_idx)}")

    # LOO attribution on TPs: Delta = score(x) - score(x with dim=median)
    rng = np.random.default_rng(0)
    D = Xt.shape[1]
    los = np.zeros((len(tp_idx), D), dtype=np.float32)
    Xtp = Xt[tp_idx]
    s0 = score(Xtp)
    for d in range(D):
        Xp = Xtp.copy()
        Xp[:, d] = med[d]
        los[:, d] = s0 - score(Xp)
    attr = np.abs(los).mean(axis=0)
    top_dims = np.argsort(attr)[::-1]

    res = {"thr": round(float(thr), 4), "n_tp": len(tp_idx), "k": {}}
    for k in [1, 3, 5, 10]:
        Xf = Xtp.copy()
        Xf[:, top_dims[:k]] = med[top_dims[:k]]
        flip_top = float((score(Xf) < thr).mean())
        flips_rand = []
        for r in range(5):
            dims = rng.choice(D, size=k, replace=False)
            Xr = Xtp.copy()
            Xr[:, dims] = med[dims]
            flips_rand.append(float((score(Xr) < thr).mean()))
        res["k"][str(k)] = {"topk_flip": round(flip_top, 4),
                            "rand_flip": round(float(np.mean(flips_rand)), 4)}
        print(f"k={k:2d}: top-k flip {flip_top:.3f} vs random {np.mean(flips_rand):.3f}")
    names = [idx2name.get(int(d), f"extra_{d}") for d in top_dims[:10]]
    res["top_dims"] = names
    print("top attributed dims:", names)
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
