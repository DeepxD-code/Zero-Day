"""
E18: retrain REVIVED M5a (per-flow pillar) on IMPROVED Monday benign.

The original-trained m5a_revived_ctx.pt is missing 20/76 canonical
columns on clean data (fixed extractor renamed them) — it cannot score
there. Same recipe as train_m5a_revived.py (87-dim, 60ep, seed 0),
new canonical pinned from improved Monday, separate output.

Output: detection/m5a_revived_improved.pt (prod file untouched).

    python detection/exp_e18_retrain_m5a_improved.py --epochs 60 --seed 0
Branch-only (exp/host-seqae-p37).
"""

from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from detection.graph_builder import normalize_columns, _window_key
from experiments.exp_m5a_revival import (pin_canonical, flow_matrix, build_ctx,
                                         MinMax, CtxScaler, RevivedAE, CTX_DIMS)

MONDAY = ROOT / "data" / "CICIDS2017_improved" / "monday.csv"
OUT = Path(__file__).resolve().parent / "m5a_revived_improved.pt"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(epochs=60, seed=0, out=str(OUT)):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed); np.random.seed(seed)
    torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False

    tr = normalize_columns(pd_read(MONDAY))
    tr = tr[tr["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    tr = tr[tr["src_ip"].map(lambda v: isinstance(v, str))
            & tr["dst_ip"].map(lambda v: isinstance(v, str))]
    wk = _window_key(tr, 60)
    # Improved extractor ships 82 numeric flow cols (not 76): pin all of
    # them. pin_canonical() asserts EXPECTED_FEATURES==76 (original
    # release), so pin locally here; RevivedAE sizes itself to X.
    from experiments.exp_m5a_revival import META as _META
    _feats = tr.drop(columns=[c for c in _META if c in tr.columns], errors="ignore")
    _feats = _feats.apply(pd.to_numeric, errors="coerce")
    _feats = _feats.replace([np.inf, -np.inf], np.nan).dropna(axis=1)
    canonical = list(_feats.columns)
    print(f"pinned {len(canonical)} canonical cols on improved Monday")

    fmm = MinMax().fit(flow_matrix(tr, canonical))
    csc = CtxScaler().fit(build_ctx(tr, wk))
    X = np.concatenate([fmm.transform(flow_matrix(tr, canonical)),
                        csc.transform(build_ctx(tr, wk))], axis=1)
    print(f"Training revived M5a (improved) on {X.shape[0]:,} x {X.shape[1]} ({epochs} ep)...",
          flush=True)

    model = RevivedAE(X.shape[1]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    lf = torch.nn.MSELoss()
    Xt = torch.tensor(X)
    loader = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(Xt),
                                         batch_size=4096, shuffle=True)
    for ep in range(epochs):
        tot = 0.0
        for (b,) in loader:
            b = b.to(device)
            l = lf(model(b), b)
            opt.zero_grad(); l.backward(); opt.step()
            tot += l.item() * len(b)
        if ep % 10 == 0:
            print(f"  ep{ep} loss {tot/len(Xt):.6f}", flush=True)

    torch.save({
        "state_dict": model.state_dict(),
        "input_dim": X.shape[1],
        "canonical": canonical,
        "flow_lo": fmm.lo, "flow_hi": fmm.hi,
        "ctx_lo": csc.lo, "ctx_hi": csc.hi,
        "ctx_names": CTX_DIMS,
        "window_seconds": 60,
        "seed": seed,
        "train": "CICIDS2017_improved/monday benign-only",
    }, Path(out))
    print(f"Saved -> {Path(out).name}")


def pd_read(p):
    import pandas as pd
    return pd.read_csv(p, low_memory=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    main(a.epochs, a.seed, a.out)
