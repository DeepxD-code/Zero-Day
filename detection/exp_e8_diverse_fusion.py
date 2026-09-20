"""
E8 (P26 WATCH, host-side): detector diversity + rank fusion on ADFA-LD.

P26 fuses IF+PCA+AE+LSTM-AE by weighted vote. Our port, same splits as the
week-5 ablation (split-seed 0): IsolationForest + PCA-recon + shipped
count-AE (seed 1) + HMM-16, all benign-only, val-F1 thresholds. Fusion =
rank_mean over arms (batch protocol, disclosed — cf. gotcha #17). Question:
does diversity + rank fusion beat the best single (AE 0.7768)?

    python detection/exp_e8_diverse_fusion.py
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score

from host_features import count_vector, index_sequence, load_adfa, pin_vocab
from host_ae import HostAutoencoder, HostScaler
from exp_host_ablation import pr_at_threshold, split_traces, tune_threshold

OUT = Path(__file__).resolve().parent / "exp_e8_diverse_fusion.json"
CKPT = Path(__file__).resolve().parent / "host_autoencoder_adfa.pt"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def rank01(s: np.ndarray) -> np.ndarray:
    o = np.argsort(np.argsort(s))
    return o / max(len(s) - 1, 1)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = load_adfa()
    tr = [t for t in traces if t["split"] == "train"]
    pin = pin_vocab([t["seq"] for t in tr])
    Xtr = np.stack([count_vector(t["seq"], pin) for t in tr])
    val_b, test_b, val_a, test_a = split_traces(traces, 0)
    V = lambda ts: np.stack([count_vector(t["seq"], pin) for t in ts])
    Xv_b, Xv_a, Xt_b, Xt_a = V(val_b), V(val_a), V(test_b), V(test_a)

    blob = torch.load(CKPT, map_location="cpu", weights_only=False)
    ae = HostAutoencoder(input_dim=blob["n_dim"])
    ae.load_state_dict(blob["model"])
    ae.eval().to(device)
    asc = HostScaler().load_state_dict(blob["scaler"])

    @torch.no_grad()
    def ae_s(X):
        Xt = torch.tensor(np.asarray(X, dtype=np.float32))
        return ae.anomaly_score(asc.transform(Xt).to(device)).cpu().numpy()

    iff = IsolationForest(n_estimators=200, random_state=0).fit(Xtr)
    if_s = lambda X: -iff.score_samples(X)
    pc = PCA(n_components=0.95, random_state=0).fit(Xtr)
    pc_s = lambda X: ((X - pc.inverse_transform(pc.transform(X))) ** 2).mean(axis=1)
    from hmmlearn.hmm import CategoricalHMM
    tr_i = [index_sequence(t["seq"], pin) for t in tr]
    va_i = [index_sequence(t["seq"], pin) for t in val_a]
    ta_i = [index_sequence(t["seq"], pin) for t in test_a]
    vb_i = [index_sequence(t["seq"], pin) for t in val_b]
    tb_i = [index_sequence(t["seq"], pin) for t in test_b]
    hmm = CategoricalHMM(n_components=16, n_iter=60, random_state=0)
    hmm.fit(np.concatenate(tr_i).reshape(-1, 1), [len(s) for s in tr_i])
    hmm_s = lambda ss: np.array([-hmm.score(s.reshape(-1, 1)) / len(s) for s in ss])

    arms = {"ae": (ae_s(Xv_b), ae_s(Xv_a), ae_s(Xt_b), ae_s(Xt_a)),
            "if": (if_s(Xv_b), if_s(Xv_a), if_s(Xt_b), if_s(Xt_a)),
            "pca": (pc_s(Xv_b), pc_s(Xv_a), pc_s(Xt_b), pc_s(Xt_a)),
            "hmm": (hmm_s(vb_i), hmm_s(va_i), hmm_s(tb_i), hmm_s(ta_i))}
    yv = np.array([0] * len(val_b) + [1] * len(val_a))
    yt = np.array([0] * len(test_b) + [1] * len(test_a))
    res = {}
    for name, (svb, sva, stb, sta) in arms.items():
        thr, _ = tune_threshold(yv, np.concatenate([svb, sva]))
        p, r, f = pr_at_threshold(yt, np.concatenate([stb, sta]), thr)
        res[name] = {"auc": round(float(roc_auc_score(yt, np.concatenate([stb, sta]))), 4),
                     "f1": round(float(f), 4)}
        print(f"{name:4s}: test AUC {res[name]['auc']:.4f} F1 {f:.4f}")
    fused_v = np.mean([rank01(np.concatenate([svb, sva])) for svb, sva, _, _ in arms.values()], axis=0)
    fused_t = np.mean([rank01(np.concatenate([stb, sta])) for _, _, stb, sta in arms.values()], axis=0)
    thr, _ = tune_threshold(yv, fused_v)
    p, r, f = pr_at_threshold(yt, fused_t, thr)
    res["rank_mean"] = {"auc": round(float(roc_auc_score(yt, fused_t)), 4), "f1": round(float(f), 4)}
    print(f"rank_mean fusion: test AUC {res['rank_mean']['auc']:.4f} F1 {f:.4f} (batch protocol)")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
