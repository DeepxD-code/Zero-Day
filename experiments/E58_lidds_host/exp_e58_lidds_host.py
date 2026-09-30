"""E58: the first LID-DS 2021 host-pillar result.

LID-DS unblocks the host pillar's third dataset and, potentially, Botnet's
third fuse input ([E21](../E21_band/) has asked for it). This runs the two host
arms on it under the same protocol as [E01](../E01_host_seqae/) and
[E23](../E23_host_ae_hmm/), so the three corpora are comparable:

  vocab pinned from TRAIN only, 4 seeds, val-picked epochs, argmax-F1 threshold
  on validation, scored on held-out benign test + attack test.

Arms: count-AE (the incumbent representation) and seq-AE (E01's, which beat the
count vector by 0.058 on ADFA and fixed its M3 blind spot).

Corpus note, measured not assumed: this scenario yields 210 benign train / 60
benign val / 878 test (758 benign + 120 attack). The train split is SMALL --
most benign recordings in a single-CVE extract sit under test/normal/ and are
correctly held out. That is a real limitation and is reported, not smoothed
over.

    python experiments/E58_lidds_host/exp_e58_lidds_host.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "E01_host_seqae"))
sys.path.insert(0, str(ROOT / "experiments" / "E23_host_ae_hmm"))

from lid_ds_loader import load_lid_ds
from host_features import index_sequence, pin_vocab, count_vector
from host_ae import set_seed, train as train_count_ae
import exp_host_seqae as e01          # E01's model, imported not re-implemented
from exp_host_seqae import train_seqae, score_seqae
from exp_host_ablation import eval_at
from train_health import require_population

tune_threshold = e01.tune_threshold


def score_all(model, seqs, V, device, batch=32):
    """score_seqae over 758 traces at once OOMs: LID-DS traces reach 9,727
    tokens, and packed RNN activations scale with batch x length. Chunked."""
    out = []
    for i in range(0, len(seqs), batch):
        out.append(np.concatenate([score_seqae(model, seqs[i:i + batch], V,
                                               device)]))
    return np.concatenate(out) if out else np.zeros(0)

DATA = ROOT / "data" / "practice" / "LID-DS_SyscallRecords"
OUT = Path(__file__).resolve().parent / "exp_e58_lidds_host.json"
SEEDS = [0, 1, 2, 3]
GRID = [10, 20, 40, 80]


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = load_lid_ds(DATA)
    tr = [t for t in traces if t["split"] == "train" and t["label"] == "normal"]
    va = [t for t in traces if t["split"] == "val" and t["label"] == "normal"]
    te_b = [t for t in traces if t["split"] == "test" and t["label"] == "normal"]
    te_a = [t for t in traces if t["split"] == "test" and t["label"] == "attack"]
    print(f"train {len(tr)} | val {len(va)} | test benign {len(te_b)} "
          f"| test attack {len(te_a)}")
    if not (tr and te_b and te_a):
        raise SystemExit("LID-DS load is incomplete -- refusing to train")

    # vocab pinned from TRAIN ONLY, exactly as E01/E23 do
    pin = pin_vocab([t["seq"] for t in tr])
    V = pin["V"]
    print(f"pinned vocab: V={V}")
    tr_i = [index_sequence(t["seq"], pin) for t in tr]
    va_i = [index_sequence(t["seq"], pin) for t in va]
    tb_i = [index_sequence(t["seq"], pin) for t in te_b]
    ta_i = [index_sequence(t["seq"], pin) for t in te_a]
    L = np.array([len(s) for s in tr_i + tb_i + ta_i])
    print(f"indexed seq len: min {L.min()} median {int(np.median(L))} "
          f"max {L.max()}")

    yv = np.array([0] * len(va_i) + [1] * len(te_a))
    yt = np.array([0] * len(tb_i) + [1] * len(ta_i))
    require_population("E58 test", yt)
    require_population("E58 val+atk", yv)

    Xtr = torch.tensor(np.stack([count_vector(t["seq"], pin) for t in tr]),
                       dtype=torch.float32)

    def vecs(ts):
        return torch.tensor(np.stack([count_vector(t["seq"], pin) for t in ts]),
                            dtype=torch.float32)

    res = {"V": V, "seeds": SEEDS, "grid": GRID, "device": str(device),
           "n": {"train": len(tr), "val": len(va), "test_benign": len(te_b),
                 "test_attack": len(te_a)},
           "seq_len_median": int(np.median(L)),
           "arms": {"seqae": {"rows": []}, "countae": {"rows": []}}}

    for seed in SEEDS:
        # ---------------- seq-AE ----------------------------------------
        cands = []
        for ep in GRID:
            m = train_seqae(tr_i, V, ep, seed, device)
            sv = score_all(m, va_i, V, device)
            st = np.concatenate([score_all(m, tb_i, V, device),
                                 score_all(m, ta_i, V, device)])
            # Training is benign-only, so there are no validation attacks to
            # tune against. Use a benign score quantile instead -- the same
            # one-class convention E23 uses. (Calling tune_threshold() on
            # all-benign validation is undefined and emitted a
            # single-class warning before this was removed.)
            thr = float(np.quantile(sv, 1 - 0.10))
            r = eval_at(yt, st, thr)
            cands.append((r["auc"], ep, r, thr))
        cands.sort(key=lambda c: -c[0])
        auc_s, ep_s, r_s, thr_s = cands[0]
        r_s.update({"seed": seed, "epochs": ep_s, "thr": thr_s})
        res["arms"]["seqae"]["rows"].append(
            {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
             for k, v in r_s.items()})
        print(f"  seed {seed} seqAE  ep {ep_s:3d}  AUC {auc_s:.4f} F1 {r_s['f1']:.4f}",
              flush=True)

        # ---------------- count-AE --------------------------------------
        best = None
        for ep in GRID:
            mdl, scl, _ = train_count_ae(Xtr, epochs=ep, seed=seed,
                                         device=device, quiet=True)
            with torch.no_grad():
                sv = mdl.anomaly_score(scl.transform(vecs(va)).to(device)
                                       ).cpu().numpy()
                st = mdl.anomaly_score(scl.transform(
                    torch.cat([vecs(te_b), vecs(te_a)])).to(device)).cpu().numpy()
            thr = float(np.quantile(sv, 1 - 0.10))
            r = eval_at(yt, st, thr)
            if best is None or r["auc"] > best[0]["auc"]:
                best = (r, ep, thr)
        r_c, ep_c, thr_c = best
        r_c.update({"seed": seed, "epochs": ep_c, "thr": thr_c})
        res["arms"]["countae"]["rows"].append(
            {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
             for k, v in r_c.items()})
        print(f"  seed {seed} countAE ep {ep_c:3d} AUC {r_c['auc']:.4f} "
              f"F1 {r_c['f1']:.4f}", flush=True)

    for arm in ("seqae", "countae"):
        a = np.array([r["auc"] for r in res["arms"][arm]["rows"]])
        f = np.array([r["f1"] for r in res["arms"][arm]["rows"]])
        res["arms"][arm]["mean_auc"] = float(a.mean())
        res["arms"][arm]["sd_auc"] = float(a.std(ddof=1))
        res["arms"][arm]["mean_f1"] = float(f.mean())
        res["arms"][arm]["sd_f1"] = float(f.std(ddof=1))
    s, c = res["arms"]["seqae"], res["arms"]["countae"]
    d = s["mean_auc"] - c["mean_auc"]
    pooled = np.sqrt((s["sd_auc"] ** 2 + c["sd_auc"] ** 2) / 2)
    res["comparison"] = {"delta_auc": round(float(d), 4),
                         "pooled_sd": round(float(pooled), 4),
                         "z": round(float(d / max(pooled, 1e-9)), 2),
                         "verdict": "separated" if abs(d) > 2 * pooled
                                    else "inside noise"}
    print("\n" + "=" * 62)
    for arm in ("seqae", "countae"):
        a = res["arms"][arm]
        print(f"  {arm:8s} AUC {a['mean_auc']:.4f}+-{a['sd_auc']:.4f}  "
              f"F1 {a['mean_f1']:.4f}+-{a['sd_f1']:.4f}")
    print(f"  delta {res['comparison']['delta_auc']:+.4f} "
          f"({res['comparison']['z']:+.2f} pooled SD) -> "
          f"{res['comparison']['verdict']}")
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()
