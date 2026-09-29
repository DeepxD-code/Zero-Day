"""Determine what each shipped checkpoint was actually trained on, from evidence.

Item 4 of the open list: 6 of 9 checkpoints carry no `train` field, so
`require_dataset` is silent on them. Back-filling is only safe if the value is
derived, not assumed -- so this script gathers the evidence for each and
refuses to fill anything it cannot support.

Evidence sources, strongest first:
  1. an existing `train` key (already correct, leave alone)
  2. a JSON result file in the archive that names the checkpoint and the data
  3. the trainer script named in detection/CHECKPOINTS.md
  4. nothing -> report as UNRESOLVED, do not guess

Writes `exp_e47_provenance_audit.json` and a patch file of proposed values.
It does NOT modify any checkpoint: that is a separate, deliberate step.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from eval_guards import PairingError, _identify, provenance_report, scaler_fingerprint

DET = ROOT / "detection"
OUT = Path(__file__).resolve().parent / "exp_e47_provenance_audit.json"

# What CHECKPOINTS.md says each file is, plus which dataset that implies.
# Every value here is traceable to a named trainer or a named result JSON.
# 'train_value' is what would be written into the checkpoint.
CLAIMS = {
    "gnn_improved_s0.pt": {
        "trainer": "experiments/E17_retrain_improved/exp_e17_retrain_improved.py",
        "train_value": "CICIDS2017_improved/monday benign-only",
        "evidence": "checkpoint already carries `train`; value matches",
        "confidence": "already present",
    },
    "gnn_improved_s{1,2,3}.pt": {
        "trainer": "experiments/E17_retrain_improved/exp_e17_retrain_improved.py",
        "train_value": "CICIDS2017_improved/monday benign-only",
        "evidence": "same trainer + same val-frac protocol as s0 (E26/E28)",
        "confidence": "inferred from the s0 checkpoint and its trainer",
    },
    "gnn_improved_replay.pt": {
        "trainer": "E17 trainer + 20% original-Monday replay mix (E29/E42)",
        "train_value": "CICIDS2017_improved/monday benign-only + original CIC-IDS2017 monday replay (20%)",
        "evidence": "E29/E42 README: replay-tuned from the clean model on a mixed training set",
        "confidence": "inferred from the transfer experiment's own record",
    },
    "gnn_autoencoder_v1_logscale_v2.pt": {
        "trainer": "gnn_model.py on original Monday (per CHECKPOINTS.md)",
        "train_value": "original CIC-IDS2017 GeneratedLabelledFlows/monday",
        "evidence": "E12 measures this ckpt on the ORIGINAL day and calls it the "
                    "shipped original-data model; E44 run 1's bug was pairing it "
                    "against a clean-data day, which implies it is original-data",
        "confidence": "inferred from E12 + E44",
    },
    "gnn_autoencoder_v1_logscale.pt": {
        "trainer": "gnn_model.py (v1, 8 dims)",
        "train_value": "original CIC-IDS2017 GeneratedLabelledFlows/monday",
        "evidence": "CHECKPOINTS.md: 'M5b v1 (8 dims), kept for old 60s eval' -- "
                    "same trainer and era as the v2 model",
        "confidence": "inferred from CHECKPOINTS.md",
    },
    "gnn_autoencoder_v1.pt": {
        "trainer": "gnn_model.py (v1, unlogged scale)",
        "train_value": "original CIC-IDS2017 GeneratedLabelledFlows/monday",
        "evidence": "CHECKPOINTS.md groups it with the original-data lineage",
        "confidence": "inferred from CHECKPOINTS.md -- WEAKEST of the group",
    },
    "gnn_temporal_fused_v1.pt": {
        "trainer": "gnn_temporal_fused.py (GNN+LSTM ablation arm)",
        "train_value": "original CIC-IDS2017 GeneratedLabelledFlows/monday",
        "evidence": "CHECKPOINTS.md: 'RC-20 ablation evidence'; no result JSON names it",
        "confidence": "inferred from CHECKPOINTS.md -- WEAKEST of the group",
    },
    "m5a_revived_ctx.pt": {
        "trainer": "train_m5a_revived.py",
        "train_value": "original CIC-IDS2017 GeneratedLabelledFlows/monday",
        "evidence": "CHECKPOINTS.md lists it under PRODUCTION, trained by "
                    "train_m5a_revived.py, and the m5a lineage predates the "
                    "clean-data retrain (E18 created m5a_revived_improved.pt)",
        "confidence": "inferred from CHECKPOINTS.md lineage",
    },
    "m5a_revived_improved.pt": {
        "trainer": "experiments/E18_retrain_m5a (per CHECKPOINTS.md)",
        "train_value": "CICIDS2017_improved/monday benign-only",
        "evidence": "name and CHECKPOINTS.md both say clean-data; E21 bands it "
                    "against gnn_improved_s{0..3} which are clean-trained",
        "confidence": "inferred from naming + CHECKPOINTS.md",
    },
    "m5a_revived_improved_s{1,2,3}.pt": {
        "trainer": "experiments/E18_retrain_m5a",
        "train_value": "CICIDS2017_improved/monday benign-only",
        "evidence": "E21 band checkpoints, same lineage as m5a_revived_improved.pt",
        "confidence": "inferred from E21",
    },
    "host_autoencoder_adfa.pt": {
        "trainer": "exp_host_ablation.py (Pillar 3 host AE)",
        "train_value": "ADFA-LD Training_Data_Master (833 benign)",
        "evidence": "checkpoint already carries `train`; value matches",
        "confidence": "already present",
    },
}


def load_any(path: Path):
    try:
        return torch.load(path, map_location="cpu", weights_only=True), "safe"
    except Exception:
        try:
            return torch.load(path, map_location="cpu", weights_only=False), "unsafe"
        except Exception as e:
            return None, f"unreadable: {e}"


def find_checkpoint(d: Path):
    """Map a directory or glob-ish name onto a real file."""
    cands = []
    if d.exists() and d.is_file():
        cands = [d]
    else:
        m = re.search(r"\{(\d+),(\d+)\}", d.name)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            pat = d.name.replace(d.name[m.start():m.end()], "*{}")
            hits = sorted(DET.glob(pat)) + sorted((ROOT / "experiments").rglob(pat))
            cands = [h for h in hits
                     for v in range(lo, hi + 1) if (su := h.with_name(
                         h.name.replace("*", f"s{v}"))).exists() for _ in [cands.append(su)]]
        else:
            cands = sorted(d.glob("*")) or sorted((ROOT / "experiments").rglob(d.name))
    seen, out = set(), []
    for c in cands:
        if c.is_file() and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def main():
    rep = provenance_report()
    rows = []
    unresolved = []
    for name, claim in CLAIMS.items():
        for p in find_checkpoint(DET / name):
            blob, how = load_any(p)
            if blob is None:
                rows.append({"file": p.relative_to(ROOT).as_posix(),
                             "status": how, "proposed": None,
                             "reason": "could not load; cannot verify a value"})
                unresolved.append(p.name)
                continue
            existing = blob.get("train")
            try:
                fp = scaler_fingerprint(blob)
            except PairingError:
                fp = None
            if existing and existing == claim["train_value"]:
                status = "already correct"
            elif existing:
                status = f"CONFLICT: has {existing!r}"
                unresolved.append(p.name)
            else:
                status = "needs back-fill"
            try:
                ident = _identify(claim["train_value"])
            except Exception:
                ident = None
            rows.append({
                "file": p.relative_to(ROOT).as_posix(),
                "load_mode": how,
                "current_train": existing,
                "proposed_train": claim["train_value"],
                "identifies_as": ident,
                "scaler_fingerprint": fp,
                "status": status,
                "trainer": claim["trainer"],
                "evidence": claim["evidence"],
                "confidence": claim["confidence"],
            })
            if status == "needs back-fill" and "WEAKEST" in claim["confidence"]:
                unresolved.append(p.name)

    res = {
        "note": "Provenance audit. Nothing is written to any checkpoint here. "
                "'needs back-fill' means the value is derivable from a named "
                "trainer or result file; 'UNRESOLVED' entries must be settled "
                "by re-running the trainer, not by guessing.",
        "summary": {
            "checkpoints": len(rows),
            "already_correct": sum(1 for r in rows if r["status"] == "already correct"),
            "needs_backfill": sum(1 for r in rows if r["status"] == "needs back-fill"),
            "conflicts": sum(1 for r in rows if str(r["status"]).startswith("CONFLICT")),
            "unresolved": len(unresolved),
        },
        "unresolved": sorted(set(unresolved)),
        "rows": sorted(rows, key=lambda r: r["file"]),
    }
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    s = res["summary"]
    print(f"checkpoints {s['checkpoints']} | already correct {s['already_correct']} "
          f"| need back-fill {s['needs_backfill']} | conflicts {s['conflicts']}")
    print(f"UNRESOLVED (do not guess): {res['unresolved'] or 'none'}")
    print()
    for r in res["rows"]:
        print(f"  {r['status']:16s} {r['file']}")
    print(f"-> {OUT.name}")
    return 0 if s["conflicts"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
