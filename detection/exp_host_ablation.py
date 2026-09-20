"""
Host AE-vs-HMM ablation on ADFA-LD — Pillar 3, Week 5 (Person B).

Controlled comparison, same protocol for both arms (mirrors the network
AE-vs-GNN ablation):
  * train BENIGN-ONLY on Training_Data_Master (833 traces)
  * vocab pinned from train (host_features.pin_vocab)
  * val  = 50% Validation benign + 50% attacks (per-family stratified)
  * test = rest. Threshold = argmax F1 on VAL, applied to TEST.
  * AE arm: HostAutoencoder count-vector MSE (detection/host_ae.py), 4 seeds
  * HMM arm: hmmlearn CategoricalHMM on index sequences, score -logprob/len,
    n_states picked by val AUC from {4, 8, 16}

    python detection/exp_host_ablation.py --seeds 0 1 2 3
    python detection/exp_host_ablation.py --seeds 0 --epochs 10 --quick
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from host_features import count_vector, index_sequence, load_adfa, pin_vocab
from host_ae import set_seed, train as train_ae

OUT = Path(__file__).resolve().parent / "ablation_host.json"


def split_traces(traces: list[dict], seed: int):
    rng = np.random.default_rng(seed)
    benign = [t for t in traces if t["split"] == "val_benign"]
    attacks = [t for t in traces if t["split"] == "attack"]
    perm_b = rng.permutation(len(benign))
    hb = len(benign) // 2
    val_b = [benign[i] for i in perm_b[:hb]]
    test_b = [benign[i] for i in perm_b[hb:]]
    val_a, test_a = [], []
    by_fam: dict[str, list[dict]] = {}
    for t in attacks:
        by_fam.setdefault(t["family"], []).append(t)
    for fam, lst in by_fam.items():
        perm = rng.permutation(len(lst))
        h = len(lst) // 2
        val_a += [lst[i] for i in perm[:h]]
        test_a += [lst[i] for i in perm[h:]]
    return val_b, test_b, val_a, test_a


def pr_at_threshold(y: np.ndarray, s: np.ndarray, thr: float):
    p = (s >= thr).astype(int)
    tp = int(((p == 1) & (y == 1)).sum())
    fp = int(((p == 1) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum())
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-12)
    return prec, rec, f1


def tune_threshold(y: np.ndarray, s: np.ndarray) -> tuple[float, float]:
    from sklearn.metrics import roc_auc_score
    auc = float(roc_auc_score(y, s))
    cands = np.unique(np.quantile(s, np.linspace(0, 1, 400)))
    best = max(((pr_at_threshold(y, s, t)[2], t) for t in cands))
    return float(best[1]), auc


def eval_at(y: np.ndarray, s: np.ndarray, thr: float) -> dict:
    from sklearn.metrics import roc_auc_score
    prec, rec, f1 = pr_at_threshold(y, s, thr)
    return {"auc": float(roc_auc_score(y, s)), "f1": f1,
            "prec": prec, "rec": rec, "thr": float(thr)}


def run_ae_seed(Xtr: torch.Tensor, val: tuple, test: tuple, seed: int,
                epoch_grid: list[int], device):
    """Train one AE per epoch count (same init); pick epochs by VAL AUC.

    Returns (picked_row, test_scores, test_labels, per_ep_rows).
    """
    model0, scaler, _ = train_ae(Xtr, epochs=0, seed=seed, device=device, quiet=True)
    init_state = {k: v.cpu().clone() for k, v in model0.state_dict().items()}

    from host_ae import HostAutoencoder
    import torch.nn as nn
    yv = np.array([0] * len(val[0]) + [1] * len(val[1]))
    yt = np.array([0] * len(test[0]) + [1] * len(test[1]))
    Xn = scaler.transform(Xtr).to(device)

    per_ep = []
    for epochs in epoch_grid:
        set_seed(seed)
        model = HostAutoencoder(input_dim=Xtr.shape[1]).to(device)
        model.load_state_dict({k: v.to(device) for k, v in init_state.items()})
        opt = torch.optim.Adam(model.parameters(), lr=1e-3)
        lf = nn.MSELoss()
        model.train()
        for _ in range(epochs):
            loss = lf(model(Xn), Xn)
            opt.zero_grad(); loss.backward(); opt.step()

        @torch.no_grad()
        def score(X: torch.Tensor):
            return model.anomaly_score(scaler.transform(X).to(device)).cpu().numpy()

        sv = np.concatenate([score(val[0]), score(val[1])])
        thr, val_auc = tune_threshold(yv, sv)
        st = np.concatenate([score(test[0]), score(test[1])])
        row = eval_at(yt, st, thr)
        row.update({"seed": seed, "epochs": epochs, "val_auc": val_auc})
        per_ep.append((row, st))
    # pick by val AUC, tie -> fewer epochs
    per_ep.sort(key=lambda r: (-r[0]["val_auc"], r[0]["epochs"]))
    return per_ep[0][0], per_ep[0][1], yt, [r for r, _ in per_ep]


def run_hmm(train_seqs: list[np.ndarray], val: tuple, test: tuple, states: list[int]):
    from hmmlearn.hmm import CategoricalHMM
    Xc = np.concatenate(train_seqs).reshape(-1, 1)
    lens = [len(s) for s in train_seqs]

    def hmm_scores(seqs_b, seqs_a, mdl):
        sb = np.array([-mdl.score(s.reshape(-1, 1)) / len(s) for s in seqs_b])
        sa = np.array([-mdl.score(s.reshape(-1, 1)) / len(s) for s in seqs_a])
        return sb, sa

    yv = np.array([0] * len(val[0]) + [1] * len(val[1]))
    best, best_cfg = None, None
    for k in states:
        mdl = CategoricalHMM(n_components=k, n_iter=60, tol=1e-3, random_state=0, verbose=False)
        mdl.fit(Xc, lens)
        sb, sa = hmm_scores(val[0], val[1], mdl)
        thr, auc = tune_threshold(yv, np.concatenate([sb, sa]))
        if best is None or auc > best[0]:
            best = (auc, thr, mdl, k)
    _, thr, mdl, k = best
    yt = np.array([0] * len(test[0]) + [1] * len(test[1]))
    sb, sa = hmm_scores(test[0], test[1], mdl)
    out = eval_at(yt, np.concatenate([sb, sa]), thr)
    out["n_states"] = k
    return out, np.concatenate([sb, sa]), yt


def main():
    ap = argparse.ArgumentParser(description="Host AE-vs-HMM ablation on ADFA-LD (week 5).")
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3])
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--split-seed", type=int, default=0)
    ap.add_argument("--states", nargs="+", type=int, default=[4, 8, 16])
    ap.add_argument("--quick", action="store_true", help="1 seed, 10 epochs, 1 HMM state (smoke test)")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device} torch={torch.__version__}")
    set_seed(args.split_seed)

    traces = load_adfa()
    tr = [t for t in traces if t["split"] == "train"]
    pin = pin_vocab([t["seq"] for t in tr])
    print(f"train {len(tr)} | V={pin['V']} N={pin['V'] + 3}")

    Xtr = torch.tensor(np.stack([count_vector(t["seq"], pin) for t in tr]), dtype=torch.float32)
    train_idx = [index_sequence(t["seq"], pin) for t in tr]
    val_b, test_b, val_a, test_a = split_traces(traces, args.split_seed)
    print(f"val {len(val_b)}b+{len(val_a)}a | test {len(test_b)}b+{len(test_a)}a")

    def vecs(ts):
        return torch.tensor(np.stack([count_vector(t["seq"], pin) for t in ts]), dtype=torch.float32)

    def idxs(ts):
        return [index_sequence(t["seq"], pin) for t in ts]

    val = (vecs(val_b), vecs(val_a))
    test = (vecs(test_b), vecs(test_a))
    val_i, test_i = (idxs(val_b), idxs(val_a)), (idxs(test_b), idxs(test_a))

    seeds = [0] if args.quick else args.seeds
    epoch_grid = [10] if args.quick else [10, 20, 40, 60]
    states = [8] if args.quick else args.states

    ae_rows, ae_curves = [], []
    seed_tests = []
    for sd in seeds:
        r, st, yt, curve = run_ae_seed(Xtr, val, test, sd, epoch_grid, device)
        ae_rows.append(r)
        ae_curves.append({c["epochs"]: round(c["val_auc"], 4) for c in curve})
        seed_tests.append((st, r["thr"]))
        print(f"AE seed {sd}: picked ep {r['epochs']} (val AUC {r['val_auc']:.4f}) -> "
              f"test AUC {r['auc']:.4f} F1 {r['f1']:.4f} (P {r['prec']:.3f} R {r['rec']:.3f})")
    print(f"AE val-AUC by epochs: {ae_curves}")
    st = np.mean([s for s, _ in seed_tests], axis=0)  # mean-score ensemble for family table

    hmm_row, hst, _ = run_hmm(train_idx, val_i, test_i, states)
    print(f"HMM states={hmm_row['n_states']}: test AUC {hmm_row['auc']:.4f} F1 {hmm_row['f1']:.4f} "
          f"(P {hmm_row['prec']:.3f} R {hmm_row['rec']:.3f})")

    # per-family recall on TEST attacks: each seed at its OWN tuned thr, then averaged
    fams: dict[str, list[int]] = {}
    for i, t in enumerate(test_a):
        fams.setdefault(t["family"], []).append(len(test_b) + i)
    print("\nper-family recall @ each seed's tuned thr (mean over seeds):")
    fam_rows = {}
    for fam, idx in sorted(fams.items()):
        ra = float(np.mean([(s[idx] >= thr).mean() for s, thr in seed_tests]))
        rh = float((hst[idx] >= hmm_row["thr"]).mean())
        fam_rows[fam] = {"ae_recall": ra, "hmm_recall": rh, "n": len(idx)}
        print(f"  {fam:16s} n={len(idx):3d}  AE {ra:.3f}  HMM {rh:.3f}")

    auc = np.array([r["auc"] for r in ae_rows])
    f1 = np.array([r["f1"] for r in ae_rows])
    res = {"seeds": seeds, "epoch_grid": epoch_grid, "pick": "val_auc", "device": str(device), "torch": torch.__version__,
           "ae": {"mean_auc": float(auc.mean()), "std_auc": float(auc.std()),
                  "mean_f1": float(f1.mean()), "std_f1": float(f1.std()), "rows": ae_rows},
           "hmm": hmm_row, "per_family": fam_rows}
    OUT.write_text(json.dumps(res, indent=1))
    print(f"\nAE  mean AUC {auc.mean():.4f}±{auc.std():.4f}  F1 {f1.mean():.4f}±{f1.std():.4f}")
    print(f"HMM AUC {hmm_row['auc']:.4f}  F1 {hmm_row['f1']:.4f} -> {OUT.name}")


if __name__ == "__main__":
    main()
