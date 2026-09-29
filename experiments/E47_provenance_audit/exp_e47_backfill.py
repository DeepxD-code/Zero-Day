"""Back-fill checkpoint provenance, using only evidence-backed values.

Every value written here is traceable to one of:
  - an existing correct `train` key                          (verified)
  - scaler-bound forensics (exp_e47_scaler_forensics.py)    (measured)
  - the trainer's own source, read directly                 (documented)

The two checkpoints whose provenance the archive never recorded are NOT
back-filled with a guess. `gnn_autoencoder_v1.pt` and
`gnn_temporal_fused_v1.pt` share a byte-identical scaler (fingerprint
ad2aafe47c2d8a1c) and CHANGELOG 2026-08-25 records the first as "saved by
smoke" -- a smoke run, not a documented Monday train. Their corpus is
genuinely unknown, so they get an explicit UNKNOWN marker, which makes
`require_dataset` WARN on any use instead of silently passing.

    python experiments/E47_provenance_audit/exp_e47_backfill.py
    python experiments/E47_provenance_audit/exp_e47_backfill.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

DET = ROOT / "detection"
OUT = Path(__file__).resolve().parent / "exp_e47_backfill.json"

ORIGINAL = "original CIC-IDS2017 GeneratedLabelledFlows/monday"
CLEAN = "CICIDS2017_improved/monday benign-only"

# file -> (train value, basis, evidence)
BACKFILL = {
    "gnn_improved_s0.pt": (
        CLEAN, "verified (already present)",
        "checkpoint already carried this value; scaler forensics confirm it "
        "(clean_monday/v2 margin 167x)"),
    "m5a_revived_improved.pt": (
        CLEAN, "verified (already present)",
        "checkpoint already carried this value"),
    "host_autoencoder_adfa.pt": (
        "ADFA-LD Training_Data_Master (833 benign)", "verified (already present)",
        "checkpoint already carried this value"),
    "gnn_improved_replay.pt": (
        CLEAN + " + original CIC-IDS2017 monday replay (20%)",
        "scaler forensics + E29/E42 record",
        "scaler matches clean Monday exactly (err 0.0, margin 3.2e8); the "
        "weights are E29's replay tune on a mixed training set, so the honest "
        "value names both corpora"),
    "gnn_autoencoder_v1_logscale_v2.pt": (
        ORIGINAL, "scaler forensics (margin 14.2x)",
        "hi-vector matches an original-Monday scaler 14.2x more closely than a "
        "clean-Monday one; this is the checkpoint E12's control anchor is "
        "measured on and the one E44 mispaired"),
    "gnn_autoencoder_v1_logscale.pt": (
        ORIGINAL, "scaler forensics (margin 12.0x)",
        "hi-vector matches original Monday 12x more closely than clean Monday"),
    "m5a_revived_ctx.pt": (
        ORIGINAL, "trainer source (detection/train_m5a_revived.py:30)",
        "reads FLOWS/'Monday-WorkingHours.pcap_ISCX.csv' from the ORIGINAL "
        "extraction; docstring says 'Trained on Monday GLF benign only'"),
}

# Never guess. These get an explicit unknown marker instead.
UNKNOWN = {
    "gnn_autoencoder_v1.pt": (
        "UNKNOWN (smoke run; training corpus not recorded)",
        "CHANGELOG 2026-08-25: 'New gnn_autoencoder_v1.pt saved by smoke'. "
        "Scaler fingerprint ad2aafe47c2d8a1c is byte-identical to "
        "gnn_temporal_fused_v1.pt, and its hi-vector sits between the two "
        "corpora (margin 1.5x, AMBIGUOUS), so the corpus cannot be called."),
    "gnn_temporal_fused_v1.pt": (
        "UNKNOWN (shares a scaler with gnn_autoencoder_v1.pt; corpus not recorded)",
        "byte-identical scaler to gnn_autoencoder_v1.pt (fingerprint "
        "ad2aafe47c2d8a1c), so both are the same run; forensics AMBIGUOUS"),
}


def patch(name: str, value: str, basis: str, evidence: str, dry: bool) -> dict:
    p = DET / name
    rec = {"file": p.relative_to(ROOT).as_posix(), "new_train": value,
           "basis": basis, "evidence": evidence}
    if not p.exists():
        rec["status"] = "MISSING"
        return rec
    try:
        blob = torch.load(p, map_location="cpu", weights_only=True)
        mode = "safe"
    except Exception:
        try:
            blob = torch.load(p, map_location="cpu", weights_only=False)
            mode = "unsafe"
        except Exception as e:
            rec["status"] = f"unreadable: {e}"
            return rec
    rec["load_mode"] = mode
    rec["old_train"] = blob.get("train")
    if blob.get("train") == value:
        rec["status"] = "already correct"
        return rec
    if dry:
        rec["status"] = "would write"
        return rec
    blob["train"] = value
    blob["provenance"] = {"basis": basis, "evidence": evidence,
                          "backfilled_by": "experiments/E47_provenance_audit/"
                                           "exp_e47_backfill.py",
                          "date": "2026-09-29"}
    tmp = p.with_suffix(".pt.tmp")
    torch.save(blob, tmp)
    shutil.move(str(tmp), str(p))
    rec["status"] = "written"
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = [patch(n, v, b, e, a.dry_run) for n, (v, b, e) in BACKFILL.items()]
    # UNKNOWN entries are (value, evidence) -- basis is fixed by definition.
    rows += [patch(n, v, "no evidence exists; marked unknown on purpose", e,
                   a.dry_run) for n, (v, e) in UNKNOWN.items()]
    res = {"dry_run": a.dry_run, "rows": rows,
           "summary": {}}
    for k in ("written", "already correct", "would write", "MISSING"):
        res["summary"][k] = sum(1 for r in rows if r["status"] == k)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for r in rows:
        print(f"  {r['status']:16s} {r['file']:44s} {r['new_train'][:46]}")
    print(f"summary: {res['summary']}")
    print(f"-> {OUT.name}")
    return 0 if res["summary"].get("MISSING", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
