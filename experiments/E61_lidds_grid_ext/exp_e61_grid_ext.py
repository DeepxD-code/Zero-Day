"""E61: extend E60's epoch grid, because every cell in it was edge-pinned.

E60's epoch picks, all eight cells:

    CVE-2012-2122  seq-AE   80, 80, 80, 80     <- TOP edge of {10,20,40,80}
    CVE-2012-2122  count-AE 80, 80, 80, 20     <- TOP edge on 3 of 4
    CVE-2014-0160  seq-AE   10, 10, 10, 10     <- BOTTOM edge
    CVE-2014-0160  count-AE 80, 80, 80, 80     <- TOP edge

Standing rule, earned twice already (E01's epoch 40, E48's k=3): a parameter
pinned to the edge of a sweep has not been tested, it has been truncated. E60 is
therefore reported as truncated on both edges and re-run here on

    {5, 10, 20, 40, 80, 160, 320}

which brackets both edges by a factor of ~2. If a pick still lands on 320 the
model wants more and this still is not a ceiling -- that gets reported as such
rather than as a result.

Everything else is byte-identical to E60: same length-blind W=1024 windows, same
K=3, same caps, same 4 seeds, same arms. The only change is the epoch grid.

    python experiments/E61_lidds_grid_ext/exp_e61_grid_ext.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))
sys.path.insert(0, str(ROOT / "experiments" / "E60_lidds_lengthblind"))

import exp_e60_lengthblind as e60
from lid_ds_loader import load_lid_ds

OUT = Path(__file__).resolve().parent / "exp_e61_grid_ext.json"
WIDE = [5, 10, 20, 40, 80, 160, 320]


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    e60.GRID = WIDE                      # the one change
    traces = load_lid_ds(e60.DATA)
    fams = sorted({t["family"] for t in traces if t["family"] != "unknown"})
    out = {"device": str(device), "W": e60.W, "K": e60.K,
           "grid_wide": WIDE,
           "grid_e60": [10, 20, 40, 80],
           "families": {}}
    for fam in fams:
        print(f"\n=== {fam}  (grid {WIDE}) ===", flush=True)
        out["families"][fam] = e60.run_family(traces, fam, device)
        r = out["families"][fam]
        print(f"  picks seqAE   {[x['epochs'] for x in r['arms']['seqae']]}")
        print(f"  picks countAE {[x['epochs'] for x in r['arms']['countae']]}")
        for a in ("seqae", "countae"):
            s = r["arms"][a + "_summary"]
            print(f"  {a:8s} AUCmax {s['auc_max']['mean']:.4f}+-{s['auc_max']['sd']:.4f}"
                  f"  AUCmean {s['auc_mean']['mean']:.4f}+-{s['auc_mean']['sd']:.4f}"
                  f"  det@10 {s['det_max@10fpr']['mean']:.3f}")
        print(f"  delta {r['comparison_max']['delta']:+.4f} "
              f"(z {r['comparison_max']['z']:+.2f}) -> "
              f"{r['comparison_max']['verdict']}")
        for a in ("seqae", "countae"):
            picks = [x["epochs"] for x in r["arms"][a]]
            print(f"  EDGE CHECK {a:8s} max pick {max(picks)} "
                  f"{'STILL TRUNCATED' if max(picks) == WIDE[-1] else 'interior'}"
                  f"   min pick {min(picks)} "
                  f"{'STILL TRUNCATED' if min(picks) == WIDE[0] else 'interior'}")
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT.name}")


if __name__ == "__main__":
    main()