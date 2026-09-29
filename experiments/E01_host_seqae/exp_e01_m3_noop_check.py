"""Is E01's M3 chunk-shuffle probe actually doing anything?

M3 shuffles a trace in chunks of k=10 and is supposed to destroy order while
preserving the histogram exactly. E06 concluded the count-AE is "undetected"
by M3, and E01 was built to test whether a sequence-reading model fixes that.

But E01's full 4-seed run gives IDENTICAL M3 recall for seq-AE and count-AE
(0.5454545..., i.e. 12/22 to the digit). Two different models cannot agree on
every trace by chance. This checks whether the probe is a no-op on this data.

    python experiments/E01_host_seqae/exp_e01_m3_noop_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "E23_host_ae_hmm"))

from host_features import load_adfa, index_sequence, pin_vocab
from exp_host_ablation import split_traces

OUT = Path(__file__).resolve().parent / "exp_e01_m3_noop_check.json"


def chunk_shuffle(s: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """Reproduce E01's mimicry transform."""
    if len(s) <= k:
        return s
    chunks = [s[i:i + k] for i in range(0, len(s), k)]
    order = rng.permutation(len(chunks))
    return np.concatenate([chunks[i] for i in order])


def main():
    traces = load_adfa()
    tr = [t for t in traces if t["split"] == "train"]
    pin = pin_vocab([t["seq"] for t in tr])
    _, _, _, test_a = split_traces(traces, 0)
    _, _, _, test_b = split_traces(traces, 0)

    rows = []
    for k in (10, 5, 3, 2):
        ident_hist = 0
        ident_seq = 0
        lens = []
        for t in test_a:
            s = index_sequence(t["seq"], pin)
            lens.append(len(s))
            rng = np.random.default_rng(7)
            sh = chunk_shuffle(s, k, rng)
            # histogram preserved? sequence identical?
            if np.array_equal(np.bincount(s, minlength=pin["V"] + 1),
                              np.bincount(sh, minlength=pin["V"] + 1)):
                ident_hist += 1
            if np.array_equal(s, sh):
                ident_seq += 1
        rows.append({"k": k, "n": len(test_a),
                     "median_len": int(np.median(lens)),
                     "min_len": int(np.min(lens)),
                     "frac_noop": ident_seq / len(test_a),
                     "frac_hist_preserved": ident_hist / len(test_a)})
        print(f"k={k:2d}  median trace len {int(np.median(lens)):3d}  "
              f"shuffle is a NO-OP on {ident_seq}/{len(test_a)} traces "
              f"({100*ident_seq/len(test_a):.0f}%)  "
              f"histogram preserved on {ident_hist}/{len(test_a)}")

    L = np.array([len(index_sequence(t["seq"], pin)) for t in test_a])
    verdict = ("M3 at k=10 is a NO-OP on this data -- the test attack traces are "
               "shorter than one chunk, so nothing is shuffled. The identical "
               "seq-AE/count-AE recall is therefore expected, not a finding "
               "about sequence modelling."
               if rows[0]["frac_noop"] > 0.9 else
               "M3 does shuffle this data; the identical recall is a real result.")
    print("\n" + verdict)

    import json
    OUT.write_text(json.dumps({"rows": rows, "verdict": verdict,
                               "test_attack_len": {"n": int(L.size),
                                                   "min": int(L.min()),
                                                   "median": int(np.median(L)),
                                                   "max": int(L.max())}},
                              indent=1), encoding="utf-8")
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
