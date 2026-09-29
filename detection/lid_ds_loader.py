"""LID-DS 2021 syscall-trace loader.

Item 2 of the open list ("unblock the host pillar") was recorded as blocked on
Person A's LID-DS loader. The *data* is genuinely gated -- LID-DS 2021 is a
manual Proton Drive download and there is no public mirror -- but the LOADER
was never the blocked part. The upstream repo already ships
`dataloader/syscall_2021.py` and `lid_ds/data_models/syscall.py`, so the wire
format is documented and this file can be written against it.

Wire format, read from `dataloader/syscall_2021.py` (SyscallSplitPart):

    TIMESTAMP USER_ID PROCESS_ID PROCESS_NAME THREAD_ID SYSCALL_NAME
    DIRECTION PARAMS...

  - one syscall per line, space-separated
  - PARAMS_BEGIN = 7, i.e. everything from field 7 on is the arg list
  - `direction` is a Direction enum (read the recording, or a call into it)

This module converts that into the shape `detection/host_features.load_adfa`
returns, so the E01/E23 host pipeline consumes it unchanged:

    {"seq": [syscall_name, ...], "label": "normal"|"attack", "split": "train"|...}

Recording-level labels come from the directory layout, which upstream defines as
Training_Data_Master / Validation_Data_Master (normal) versus everything else
(attack) -- the same convention `data/download_practice_datasets.py` already
uses.

Nothing here invents a format, and the module is import-safe with no data
present: `available()` reports False and the loader refuses rather than
silently returning an empty set. An empty host corpus is precisely the failure
that produced ADFA's E06/E23 numbers, so it must be loud.

    python detection/lid_ds_loader.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "practice"

# Searched in order; the first non-empty one wins.
CANDIDATE_ROOTS = [
    DATA / "LID-DS_SyscallRecords",
    DATA / "raw_lid_ds" / "LID-DS-master" / "data",
]

# SyscallSplitPart from dataloader/syscall_2021.py
F_TIMESTAMP, F_USER, F_PROC, F_PROC_NAME, F_THREAD, F_NAME, F_DIR, F_PARAMS = range(8)

NORMAL_MARKERS = ("Training_Data_Master", "Validation_Data_Master")
# Upstream records a recording as empty when the first syscall cannot be
# yielded; a trace file with no syscall lines is the same thing.
MIN_SYSCALLS = 1


def available() -> tuple[bool, str]:
    """Is a non-empty LID-DS syscall corpus present? Returns (ok, where)."""
    for root in CANDIDATE_ROOTS:
        if root.is_dir():
            files = [p for p in root.rglob("*") if p.is_file()]
            if files:
                return True, str(root)
            return False, f"{root} exists but is EMPTY (download never completed)"
    return False, (f"no LID-DS data under {DATA}. LID-DS 2021 is a manual "
                   "download (Proton Drive, see the upstream README); the code "
                   "repo is present but the traces are not.")


def _classify(path: Path) -> str:
    parts = {p for p in path.parts}
    for m in NORMAL_MARKERS:
        if m in parts:
            return "normal"
    return "attack"


def parse_trace(path: Path) -> list[str]:
    """One syscall name per line, in order, from a LID-DS 2021 trace file.

    Malformed lines are skipped rather than aborting the file: the upstream
    dataloader is tolerant, and a single bad line should not cost a recording.
    """
    out: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            fields = line.split(" ", F_PARAMS)
            if len(fields) <= F_NAME:
                continue
            name = fields[F_NAME].strip()
            if name:
                out.append(name)
    return out


def load_lid_ds(root: Path | None = None, max_traces: int | None = None,
                require_attacks: bool = True) -> list[dict]:
    """Load LID-DS into the host-features trace shape.

    Returns a list of {"seq", "label", "split", "path"}. `split` follows the
    upstream layout: normal training data -> "train", normal validation ->
    "val", every attack trace -> "test". That mirrors how ADFA-LD is consumed
    in this project, so E01/E23 need no changes.

    Raises if no data is present, or if `require_attacks` is set and no attack
    trace was found. An all-normal corpus would make every host-pillar number
    meaningless, so this must not be silent.
    """
    if root is None:
        ok, where = available()
        if not ok:
            raise FileNotFoundError(where)
        for cand in CANDIDATE_ROOTS:
            if cand.is_dir() and any(p.is_file() for p in cand.rglob("*")):
                root = cand
                break
    root = Path(root)

    traces: list[dict] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".txt", ".log", ".json",
                                                       ".csv", ""):
            continue
        if p.name.lower() in ("readme.md", "license", "version"):
            continue
        seq = parse_trace(p)
        if len(seq) < MIN_SYSCALLS:
            continue
        label = _classify(p)
        if label == "normal":
            split = "val" if any("Validation" in q for q in p.parts) else "train"
        else:
            split = "test"
        traces.append({"seq": seq, "label": label, "split": split,
                       "path": str(p)})
        if max_traces and len(traces) >= max_traces:
            break

    n_atk = sum(1 for t in traces if t["label"] == "attack")
    if require_attacks and n_atk == 0:
        raise ValueError(
            f"{n_atk} attack traces found under {root}. LID-DS is only useful "
            "with attacks; check that the download included the attack "
            "recordings, not just Training_Data_Master.")
    return traces


def summary(traces: list[dict]) -> dict:
    seqs = [t["seq"] for t in traces]
    L = np.array([len(s) for s in seqs]) if seqs else np.array([0])
    vocab = sorted({c for s in seqs for c in s})
    return {
        "traces": len(traces),
        "normal": sum(1 for t in traces if t["label"] == "normal"),
        "attack": sum(1 for t in traces if t["label"] == "attack"),
        "splits": {sp: sum(1 for t in traces if t["split"] == sp)
                   for sp in ("train", "val", "test")},
        "seq_len": {"min": int(L.min()), "median": int(np.median(L)),
                    "mean": round(float(L.mean()), 1), "max": int(L.max())},
        "vocab_size": len(vocab),
        "vocab_sample": vocab[:12],
    }


def main() -> int:
    ok, where = available()
    print(f"LID-DS available: {ok}")
    print(f"  {where}")
    if not ok:
        print("\nTo unblock item 2 (host fusion / Botnet's third fuse input):")
        print("  1. download LID-DS 2021 from the Proton Drive link in")
        print("     data/practice/raw_lid_ds/LID-DS-master/README.md")
        print("  2. extract so traces land under")
        print(f"     {CANDIDATE_ROOTS[0]}")
        print("  3. python detection/lid_ds_loader.py   # this check")
        print("  4. python -c \"import lid_ds_loader as L; "
              "print(L.summary(L.load_lid_ds()))\"")
        return 1
    s = summary(load_lid_ds())
    for k, v in s.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
