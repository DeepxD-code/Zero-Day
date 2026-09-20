"""
E3 (P08/P17 WATCH): embedding-space Gaussian MMD vs score-space drift on M5b.

Arms (same reference, FAR-matched at 99th pct of benign-vs-benign):
  S-score: MMD-Gaussian on node recon errors (stronger sibling of M6's
           mean-shift; M6's |mean-baseline|>0.05 reported as reference)
  E-emb:   MMD-Gaussian on frozen v2 encoder embeddings, median-heuristic
           bandwidth (P08/DRIFT-CL feature-space Judge)
Reference: Monday benign 300s v2 graphs. Test: 7 attack days, sliding blocks
of 10 windows. Metrics per family: detection delay (blocks to first crossing
at matched FAR) + AUC of the statistic (day blocks vs Monday blocks).

    python detection/exp_e3_drift_mmd.py
    python detection/exp_e3_drift_mmd.py --quick
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import build_graphs, normalize_columns, read_flows
from gnn_model import GraphAutoencoder, NodeScaler

FLOWS = ROOT / "data/GeneratedLabelledFlows/TrafficLabelling"
CKPT = Path(__file__).resolve().parent / "gnn_autoencoder_v1_logscale_v2.pt"
OUT = Path(__file__).resolve().parent / "exp_e3_drift_mmd.json"
DAYS = {
    "PortScan": "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "DDoS": "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
    "Botnet": "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "Infiltration": "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "WebAttacks": "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    "Patator": "Tuesday-WorkingHours.pcap_ISCX.csv",
    "DoS": "Wednesday-workingHours.pcap_ISCX.csv",
}


def mmd2(X: np.ndarray, Y: np.ndarray, sig2: float) -> float:
    Z = np.vstack([X, Y])
    d2 = ((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1)
    K = np.exp(-d2 / (2 * sig2))
    n, m = len(X), len(Y)
    return float(K[:n, :n].mean() + K[n:, n:].mean() - 2 * K[:n, n:].mean())


def med_sig2(X: np.ndarray, seed: int = 0) -> float:
    r = np.random.default_rng(seed).choice(len(X), size=min(2000, len(X)), replace=False)
    Xs = X[r]
    d2 = ((Xs[:, None, :] - Xs[None, :, :]) ** 2).sum(-1)
    return float(max(np.median(d2[np.triu_indices(len(Xs), 1)]), 1e-6))


@torch.no_grad()
def encode_graphs(graphs, model, scaler, device, cap: int = 400):
    E, S = [], []
    for g in graphs:
        x = scaler.transform(g.x).to(device)
        emb = model.encode(x, g.edge_index.to(device)).cpu().numpy()
        sc = model.node_scores(x, g.edge_index.to(device)).cpu().numpy()
        idx = np.random.default_rng(0).choice(len(emb), size=min(cap, len(emb)),
                                              replace=False)
        E.append(emb[idx])
        S.append(sc[idx])
    return E, S


def blocks(E, S, w: int = 10):
    out = []
    for i in range(0, len(E) - w + 1, w):
        out.append((np.vstack(E[i:i + w]), np.concatenate(S[i:i + w])))
    return out


def main():
    ap = argparse.ArgumentParser(description="E3: embedding-MMD vs score drift.")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    blob = torch.load(CKPT, map_location="cpu", weights_only=True)
    model = GraphAutoencoder(in_dim=19)
    model.load_state_dict(blob["model"])
    model.eval().to(device)
    scaler = NodeScaler().load_state_dict(blob["scaler"])

    days = dict(list(DAYS.items())[:2]) if args.quick else DAYS
    mon = normalize_columns(read_flows(FLOWS / "Monday-WorkingHours.pcap_ISCX.csv"))
    mon = mon[mon["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    mg = build_graphs(mon, window_seconds=300, feature_set="v2")
    Emon, Smon = encode_graphs(mg, model, scaler, device)
    ref_E = np.vstack(Emon[:len(Emon) // 2])
    ref_S = np.concatenate(Smon[:len(Smon) // 2]).reshape(-1, 1)
    cal = blocks(Emon[len(Emon) // 2:], Smon[len(Smon) // 2:])
    rng = np.random.default_rng(1)
    ref_E_s = ref_E[rng.choice(len(ref_E), 3000, replace=False)]
    ref_S_s = ref_S[rng.choice(len(ref_S), 3000, replace=False)]
    # FIXED bandwidths from the reference pool (per-comparison median heuristic
    # rescales every pair differently and makes thresholds/AUC meaningless).
    sig_e, sig_s = med_sig2(ref_E_s), med_sig2(ref_S_s)
    sub = lambda a, n: a[rng.choice(len(a), min(n, len(a)), replace=False)]
    ce = sorted(mmd2(sub(ref_E, 2000), sub(b[0], 2000), sig_e) for b in cal)
    cs = sorted(mmd2(sub(ref_S, 2000), sub(b[1], 2000).reshape(-1, 1), sig_s) for b in cal)
    thr_e, thr_s = float(np.quantile(ce, 0.99)), float(np.quantile(cs, 0.99))
    m6_base = float(np.concatenate(Smon).mean())
    print(f"calibrated@1%FAR: MMD-emb thr={thr_e:.4f} MMD-score thr={thr_s:.4f} | M6 baseline={m6_base:.6f}")
    res = {"thr_emb": thr_e, "thr_score": thr_s, "families": {}}
    for fam, fn in days.items():
        df = normalize_columns(read_flows(FLOWS / fn))
        df = df[df["src_ip"].map(lambda v: isinstance(v, str)) &
                df["dst_ip"].map(lambda v: isinstance(v, str))]  # gotcha #12
        g = build_graphs(df, window_seconds=300, feature_set="v2")
        E, S = encode_graphs(g, model, scaler, device)
        bl = blocks(E, S)
        se = np.array([mmd2(ref_E_s, sub(b[0], 3000), sig_e) for b in bl])
        ss = np.array([mmd2(ref_S_s, sub(b[1], 3000).reshape(-1, 1), sig_s) for b in bl])
        m6 = np.array([abs(b[1].mean() - m6_base) > 0.05 for b in bl])
        de = int(np.argmax(se >= thr_e)) if (se >= thr_e).any() else None
        ds = int(np.argmax(ss >= thr_s)) if (ss >= thr_s).any() else None
        dm = int(np.argmax(m6)) if m6.any() else None
        from sklearn.metrics import roc_auc_score
        y = np.array([1] * len(bl) + [0] * len(cal))
        ae = round(float(roc_auc_score(y, np.concatenate([se, np.array(ce)]))), 4)
        as_ = round(float(roc_auc_score(y, np.concatenate([ss, np.array(cs)]))), 4)
        res["families"][fam] = {"delay_emb": de, "delay_score": ds, "delay_m6": dm,
                                "auc_emb": ae, "auc_score": as_, "n_blocks": len(bl)}
        print(f"{fam:14s} delay emb={de} score={ds} M6={dm} | AUC emb={ae} score={as_}")
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
