"""
E1 (WATCH P37): benign-only attention sequence-AE vs count-AE vs HMM-16 on
ADFA-LD, same protocol as exp_host_ablation (pinned vocab, split-seed 0,
val-picked epochs, argmax-F1 threshold), plus MIMICRY probes (P39 lesson).

Model: emb(V+1,32) -> GRU encoder(64) -> additive-attention pooling ->
GRU decoder (teacher forcing) -> logits over V. Score = mean token CE.
Probes on TEST attacks (seeded): M1 benign-interleave (+30% len),
M2 benign-substitution (20% tokens), M3 chunk-shuffle (k=10, order kill).

    python detection/exp_host_seqae.py --seeds 0 1 2 3
    python detection/exp_host_seqae.py --seeds 0 --epochs 5 --quick
Branch-only experiment file (exp/host-seqae-p37): nothing in prod imports it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.nn.utils.rnn import pad_sequence, pack_padded_sequence, pad_packed_sequence

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))
sys.path.insert(0, str(ROOT / "experiments"))
# exp_host_ablation lives in E23's folder, not detection/ -- this import was
# only ever satisfied by the old venv312 working directory.
sys.path.insert(0, str(ROOT / "experiments" / "E23_host_ae_hmm"))

from host_features import index_sequence, load_adfa, pin_vocab, count_vector
from host_ae import set_seed
from exp_host_ablation import (eval_at, run_ae_seed, run_hmm, split_traces,
                               tune_threshold)

OUT = Path(__file__).resolve().parent / "ablation_host_seqae.json"


class SeqAE(nn.Module):
    def __init__(self, V: int, emb: int = 32, hid: int = 64):
        super().__init__()
        self.emb = nn.Embedding(V + 1, emb, padding_idx=V)
        self.enc = nn.GRU(emb, hid, batch_first=True)
        self.attn = nn.Linear(hid * 2, 1)
        self.proj = nn.Linear(hid, hid)
        self.dec = nn.GRU(emb, hid, batch_first=True)
        self.out = nn.Linear(hid, V)
        self.hid = hid

    def forward(self, x, lens):
        e = self.emb(x)
        packed = pack_padded_sequence(e, lens.cpu(), batch_first=True, enforce_sorted=False)
        packed_out, h_last = self.enc(packed)                               # h_last: (1,B,H)
        h, _ = pad_packed_sequence(packed_out, batch_first=True)            # (B,T,H)
        q = h_last.squeeze(0).unsqueeze(1).expand_as(h)                          # query
        w = torch.softmax(self.attn(torch.cat([h, q], dim=-1)).squeeze(-1), dim=1)  # (B,T)
        ctx = (w.unsqueeze(-1) * h).sum(dim=1)                                  # (B,H)
        dh = self.proj(ctx).unsqueeze(0)                                        # decoder init
        d_in = torch.cat([torch.zeros_like(e[:, :1]), e[:, :-1]], dim=1)        # shift right
        d, _ = self.dec(d_in, dh)
        return self.out(d), w


def collate(seqs: list[np.ndarray], V: int):
    order = np.argsort([-len(s) for s in seqs])
    lens = torch.tensor([len(seqs[i]) for i in order])
    x = pad_sequence([torch.from_numpy(seqs[i]).long() for i in order],
                     batch_first=True, padding_value=V)
    return x, lens, order


def train_seqae(train_idx: list[np.ndarray], V: int, epochs: int, seed: int, device):
    set_seed(seed)
    model = SeqAE(V).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    ce = nn.CrossEntropyLoss(reduction="none")
    model.train()
    for _ in range(epochs):
        perm = np.random.permutation(len(train_idx))
        for i in range(0, len(perm), 32):
            batch = [train_idx[j] for j in perm[i:i + 32]]
            x, lens, _ = collate(batch, V)
            x = x.to(device)
            logits, _ = model(x, lens)
            tgt = x.clone()
            tgt[torch.arange(x.size(1)).unsqueeze(0) >= lens.unsqueeze(1)] = -100
            loss = ce(logits.reshape(-1, V), tgt.reshape(-1)).mean()
            opt.zero_grad(); loss.backward(); opt.step()
    return model


@torch.no_grad()
def score_seqae(model, seqs: list[np.ndarray], V: int, device):
    model.eval()
    out = np.zeros(len(seqs))
    for i in range(0, len(seqs), 64):
        batch = seqs[i:i + 64]
        x, lens, order = collate(batch, V)
        x = x.to(device)
        logits, _ = model(x, lens)
        ce = nn.CrossEntropyLoss(reduction="none")
        tgt = x.clone()
        mask = torch.arange(x.size(1)).unsqueeze(0) < lens.unsqueeze(1)
        tgt[~mask] = -100
        tok = ce(logits.reshape(-1, V), tgt.reshape(-1)).reshape(x.shape).cpu().numpy()
        tok[~mask.cpu().numpy()] = 0.0
        s = tok.sum(axis=1) / lens.cpu().numpy()
        inv = np.argsort(order)
        out[i:i + 64] = s[inv]
    return out


def mimicry(atk: list[np.ndarray], benign_pool: list[np.ndarray], seed: int):
    rng = np.random.default_rng(seed)
    uni = np.concatenate(benign_pool)
    m1, m2, m3 = [], [], []
    for a in atk:
        ins = rng.choice(uni, size=max(1, int(0.3 * len(a))))
        pos = np.sort(rng.choice(len(a) + 1, size=len(ins), replace=True))
        m1.append(np.insert(a, pos, ins))
        b = a.copy()
        sub = rng.choice(len(b), size=max(1, int(0.2 * len(b))), replace=False)
        b[sub] = rng.choice(uni, size=len(sub))
        m2.append(b)
        c = [a[i:i + 10] for i in range(0, len(a), 10)]
        rng.shuffle(c)
        m3.append(np.concatenate(c))
    return {"M1_interleave": m1, "M2_substitute": m2, "M3_reshuffle": m3}


def main():
    ap = argparse.ArgumentParser(description="E1: attention seq-AE vs count-AE vs HMM + mimicry.")
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3])
    ap.add_argument("--epochs", nargs="+", type=int, default=[10, 20, 40])
    ap.add_argument("--split-seed", type=int, default=0)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--arm", choices=["torch", "hmm", "all"], default="all",
                    help="Split the run so the GPU work does not depend on "
                         "hmmlearn. E01 was killed three times because "
                         "hmmlearn has no Python 3.14 wheel, forcing the WHOLE "
                         "job onto CPU-only venv312 for hours. Run the torch arm "
                         "in system Python on CUDA (minutes), then the hmm arm "
                         "in venv312 (CPU, hmmlearn), which merges into the "
                         "same JSON.")
    args = ap.parse_args()

    out_path = (ROOT / "experiments" / "E01_host_seqae"
                / f"ablation_host_seqae_{args.arm}.json")
    if args.arm == "hmm":
        # CPU-only continuation: no torch/CUDA work, no hmmlearn needed here.
        from hmmlearn.hmm import CategoricalHMM
    else:
        CategoricalHMM = None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device} torch={torch.__version__}")
    set_seed(args.split_seed)
    traces = load_adfa()
    tr = [t for t in traces if t["split"] == "train"]
    pin = pin_vocab([t["seq"] for t in tr])
    V = pin["V"]
    train_idx = [index_sequence(t["seq"], pin) for t in tr]
    val_b, test_b, val_a, test_a = split_traces(traces, args.split_seed)
    bi = [index_sequence(t["seq"], pin) for t in val_b + test_b]
    va_i, ta_i = ([index_sequence(t["seq"], pin) for t in val_a],
                  [index_sequence(t["seq"], pin) for t in test_a])
    yv = np.array([0] * len(val_b) + [1] * len(val_a))
    yt = np.array([0] * len(test_b) + [1] * len(test_a))

    seeds = [0] if args.quick else args.seeds
    grid = [5] if args.quick else args.epochs
    rows, probes = [], {}
    for sd in seeds:
        cands = []
        for ep in grid:
            m = train_seqae(train_idx, V, ep, sd, device)
            sv = np.concatenate([score_seqae(m, bi[:len(val_b)], V, device),
                                 score_seqae(m, va_i, V, device)])
            thr, vauc = tune_threshold(yv, sv)
            st = np.concatenate([score_seqae(m, bi[len(val_b):], V, device),
                                 score_seqae(m, ta_i, V, device)])
            r = eval_at(yt, st, thr)
            cands.append((vauc, ep, r, thr, m))
        cands.sort(key=lambda c: (-c[0], c[1]))
        _, ep, r, thr, _ = cands[0]
        r.update({"seed": sd, "epochs": ep})
        rows.append(r)
        print(f"seqAE seed {sd}: picked ep {ep} -> test AUC {r['auc']:.4f} F1 {r['f1']:.4f}")
        if sd == seeds[0]:
            for name, seqs in mimicry(ta_i, train_idx, 7).items():
                s = score_seqae(cands[0][4], seqs, V, device)
                probes[name] = {"seqae_recall": float((s >= thr).mean())}

    # baselines on identical splits (count-AE same grid logic, HMM-16)
    Xtr = torch.tensor(np.stack([count_vector(t["seq"], pin) for t in tr]), dtype=torch.float32)
    def vecs(ts):
        return torch.tensor(np.stack([count_vector(t["seq"], pin) for t in ts]), dtype=torch.float32)
    ae_rows = []
    for sd in seeds:
        r, _, _, _ = run_ae_seed(Xtr, (vecs(val_b), vecs(val_a)),
                                 (vecs(test_b), vecs(test_a)), sd, grid, device)
        ae_rows.append(r)
    # ---- HMM arm -------------------------------------------------------
    # hmmlearn is the only CPU-bound dependency in this script and the only
    # reason E01 ever needed venv312. Skipped here so the torch arms can run
    # on CUDA in system Python; the HMM arm is computed by --arm hmm.
    hmm_row = None
    if args.arm in ("hmm", "all"):
        hmm_row, _, _ = run_hmm(train_idx, (bi[:len(val_b)], va_i),
                                (bi[len(val_b):], ta_i), [16])
    # mimicry recall for baselines at their own tuned thrs (seed-0 models)
    r0, _, _, _ = run_ae_seed(Xtr, (vecs(val_b), vecs(val_a)),
                              (vecs(test_b), vecs(test_a)), seeds[0], grid, device)
    from host_ae import train as train_ae
    h0 = None
    if hmm_row is not None:
        Xc = np.concatenate(train_idx).reshape(-1, 1)
        h0 = CategoricalHMM(n_components=16, n_iter=60,
                            random_state=0).fit(Xc, [len(s) for s in train_idx])
    mdl0, scl0, _ = train_ae(Xtr, epochs=r0["epochs"], seed=seeds[0], device=device, quiet=True)
    with torch.no_grad():
        def ae_s(X):
            return mdl0.anomaly_score(scl0.transform(X).to(device)).cpu().numpy()
    for name, seqs in mimicry(ta_i, train_idx, 7).items():
        # count vectors need raw syscall numbers: invert indices (unk impossible here —
        # mimicry draws only from train/attack indices, all covered by the pinned vocab)
        inv = {i: n for n, i in pin["vocab"].items()}
        raw = [[inv[int(x)] for x in s] for s in seqs]
        a = ae_s(torch.tensor(np.stack([count_vector(r, pin) for r in raw]), dtype=torch.float32))
        probes[name]["countae_recall"] = float((a >= r0["thr"]).mean())
        if hmm_row is not None:
            h = np.array([-h0.score(s.reshape(-1, 1)) / len(s) for s in seqs])
            probes[name]["hmm_recall"] = float((h >= hmm_row["thr"]).mean())
    print("\nmimicry recall (seed-0 models @ own tuned thr):")
    for name, d in probes.items():
        hh = f"  HMM {d['hmm_recall']:.3f}" if "hmm_recall" in d else "  HMM n/a"
        print(f"  {name:14s} seqAE {d['seqae_recall']:.3f}  "
              f"countAE {d['countae_recall']:.3f}{hh}")

    sa = np.array([r["auc"] for r in rows])
    aa = np.array([r["auc"] for r in ae_rows])
    res = {"seeds": seeds, "grid": grid, "device": str(device),
           "arm": args.arm,
           "seqae": {"mean_auc": float(sa.mean()), "std_auc": float(sa.std()), "rows": rows},
           "countae": {"mean_auc": float(aa.mean()), "std_auc": float(aa.std())},
           "hmm": hmm_row, "mimicry": probes}

    # --arm torch writes the GPU half and stops; --arm hmm reads it back and
    # merges, so the CPU-only venv312 run does not repeat the CUDA work.
    if args.arm == "torch":
        out_path.write_text(json.dumps(res, indent=1))
        print(f"\nseqAE {sa.mean():.4f}±{sa.std():.4f} | countAE "
              f"{aa.mean():.4f}±{aa.std():.4f} | HMM deferred -> {out_path.name}")
        print(f"next: venv312\\Scripts\\python.exe -u "
              f"experiments/E01_host_seqae/exp_host_seqae.py --arm hmm")
        return
    if args.arm == "hmm":
        torch_side = out_path.parent / "ablation_host_seqae_torch.json"
        if torch_side.exists():
            prev = json.loads(torch_side.read_text())
            res["seqae"] = prev.get("seqae", res["seqae"])
            res["countae"] = prev.get("countae", res["countae"])
            for k, v in (prev.get("mimicry") or {}).items():
                res["mimicry"].setdefault(k, {}).update(
                    {kk: vv for kk, vv in v.items() if kk != "hmm_recall"})
            print(f"merged torch arm from {torch_side.name}")

    OUT.write_text(json.dumps(res, indent=1))
    hh = f"{hmm_row['auc']:.4f}" if hmm_row else "n/a"
    print(f"\nseqAE {sa.mean():.4f}±{sa.std():.4f} | countAE {aa.mean():.4f}±{aa.std():.4f} | HMM {hh} -> {OUT.name}")


if __name__ == "__main__":
    main()
