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
from collections import Counter
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

# LID-DS 2021 label rule, read from the upstream source
# (dataloader/dataloader_real_world.py:34-37):
#
#     if 'malicious' in path:  return NORMAL_AND_ATTACK
#     return NORMAL
#
# i.e. normal data is the DEFAULT and is not named "normal" or "benign" -- it is
# whatever is left after the attack scenarios. The first version of this loader
# used the ADFA-LD / LID-DS-2019 convention (Training_Data_Master /
# Validation_Data_Master), which is wrong for 2021 and would have labelled every
# 2021 recording as an attack.
#
# `data_loader_2021.py:60` additionally keys off a container whose
# `container["role"] == "normal"`, so a JSON sidecar may carry the role.
ATTACK_MARKERS = ("malicious", "attack", "cve-", "cve_", "cwe-", "cwe_",
                   "juice-shop", "juice_shop", "zipslip", "zip-slip",
                   "bruteforce", "sql-injection", "sqlinjection")
# Legacy markers, kept only so an ADFA-style tree still loads if someone points
# this at LID-DS 2019. They are NOT the 2021 convention.
LEGACY_NORMAL_MARKERS = ("Training_Data_Master", "Validation_Data_Master")
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
    """Fallback only. The JSON sidecar is authoritative -- see _label_from_json."""
    low = str(path).lower()
    if any(m in low for m in ATTACK_MARKERS):
        return "attack"
    parts = {p.lower() for p in path.parts}
    if parts & {m.lower() for m in LEGACY_NORMAL_MARKERS}:
        return "normal"          # LID-DS 2019 / ADFA-style tree
    return "normal"              # the 2021 default


def _split_from_path(path: Path) -> str:
    """LID-DS 2021 puts the split in the scenario directory.

        <scenario>/training/<recording>.sc
        <scenario>/validation/<recording>.sc
        <scenario>/test/normal/<recording>.sc
        <scenario>/test/normal_and_attack/<recording>.sc

    So "validation" anywhere in the path is the right test, but ONLY against the
    scenario directory -- the first version tested the whole path and then
    defaulted everything else to "train", which swept test/normal/ into the
    training set.
    """
    parts = [p.lower() for p in path.parts]
    for i, p in enumerate(parts):
        if p in ("training", "validation", "test"):
            return {"training": "train", "validation": "val",
                    "test": "test"}[p]
    return "train"


def _family_from_path(path: Path) -> str:
    """The CVE scenario directory, e.g. CVE-2012-2122.

    Each CVE ships its OWN benign recordings -- the file names differ entirely
    between archives (abundant_dhawan_6184 vs delicious_kirch_1509), so the two
    scenarios are independent capture sessions, not overlapping normal traffic.
    That is what makes them usable as separate families and separate training
    pools rather than duplicates.
    """
    for p in path.parts:
        if p.upper().startswith("CVE-"):
            return p
    return "unknown"


def _label_from_json(sidecar: Path) -> tuple[str, dict] | None:
    """Authoritative label from the recording's JSON sidecar.

    Read from the real CVE-2014-0160 extract, not from the docs:

        "exploit": true|false        <- whether the attack fired
        "container": [{"role": "attacker"|"victim"|"normal", ...}]

    `exploit` is the ground truth for whether this recording is an attack. An
    `attacker` container marks the host that ran it. Both beat any path
    heuristic, so the path rule is only a fallback for recordings with no
    sidecar.
    """
    import json as _json
    try:
        d = _json.loads(sidecar.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    roles = [str(c.get("role", "")).lower()
             for c in (d.get("container") or []) if isinstance(c, dict)]
    expl = d.get("exploit")
    info = {"exploit": expl, "roles": sorted(set(roles)),
            "exploit_name": d.get("exploit_name"),
            "recording_time": d.get("recording_time")}
    if isinstance(expl, bool):
        return ("attack" if expl else "normal"), info
    if "attacker" in roles or "malicious" in roles:
        return "attack", info
    return None


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
        if not p.is_file():
            continue
        # `.sc` is the syscall-record format and is THE file we want. The first
        # version's allow-list omitted it, so the loader silently fell through
        # to the binary .zip files and reported 6 "syscalls" per trace.
        suf = p.suffix.lower()
        if suf in (".zip", ".pcap", ".scap", ".res", ".png", ".jpg"):
            continue
        if suf in (".ds_store",) or p.name.startswith("._"):
            continue
        if suf not in (".sc", ".txt", ".log", ""):
            # .json is the SIDECAR (read by _label_from_json), never a trace.
            # Parsing it too double-counted every recording and produced
            # "syscalls" like '[', 'true,', '"default",'.
            continue
        if p.name.lower() in ("readme.md", "license", "version"):
            continue
        seq = parse_trace(p)
        if len(seq) < MIN_SYSCALLS:
            continue
        sidecar = p.with_suffix(".json")
        meta = {}
        lab = None
        if sidecar.exists():
            got = _label_from_json(sidecar)
            if got:
                lab, meta = got
        if lab is None:
            lab = _classify(p)          # fallback: no sidecar
        if lab == "normal":
            # Split comes from the SCENARIO directory (training/ validation/
            # test/), not from the label. The first version keyed off
            # "validation" appearing anywhere in the path, which put
            # test/normal/ traces into TRAIN -- a leak, since those are
            # held-out benign recordings.
            split = _split_from_path(p)
        else:
            split = "test"
        traces.append({"seq": seq, "label": lab, "split": split,
                       "family": _family_from_path(p),
                       "path": str(p), "meta": meta})
        if max_traces and len(traces) >= max_traces:
            break

    n_atk = sum(1 for t in traces if t["label"] == "attack")
    if require_attacks and n_atk == 0:
        raise ValueError(
            f"{n_atk} attack traces found under {root}. LID-DS is only useful "
            "with attacks; check that the download included the attack "
            "recordings.")
    return traces


def label_audit(traces: list[dict]) -> dict:
    """Flag files where the name heuristic disagrees with upstream's rule.

    Upstream (dataloader_real_world.py) says an attack recording is one whose
    PATH CONTAINS 'malicious'; everything else is normal. The extra name
    markers in ATTACK_MARKERS are a heuristic layered on top, because the real
    distribution may not use that literal path prefix everywhere. This reports
    any file where the two disagree, so a mislabel is visible rather than
    silently baked into an AUC.
    """
    disagree = []
    for t in traces:
        low = t["path"].lower()
        upstream = "attack" if "malicious" in low else "normal"
        if upstream != t["label"]:
            disagree.append({"path": t["path"], "loader": t["label"],
                             "upstream_rule": upstream})
    return {"n": len(traces), "n_disagree": len(disagree),
            "disagreements": disagree[:25]}


def summary(traces: list[dict]) -> dict:
    seqs = [t["seq"] for t in traces]
    L = np.array([len(s) for s in seqs]) if seqs else np.array([0])
    vocab = sorted({c for s in seqs for c in s})
    fam: dict[str, Counter] = {}
    for t in traces:
        c = fam.setdefault(t.get("family", "unknown"), Counter())
        c[t["label"]] += 1
        c[t["split"]] += 1
    return {
        "traces": len(traces),
        "normal": sum(1 for t in traces if t["label"] == "normal"),
        "attack": sum(1 for t in traces if t["label"] == "attack"),
        "splits": {sp: sum(1 for t in traces if t["split"] == sp)
                   for sp in ("train", "val", "test")},
        "families": {k: dict(v) for k, v in sorted(fam.items())},
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
    a = label_audit(load_lid_ds())
    print(f"\n  label audit: {a['n_disagree']}/{a['n']} files where the name "
          f"heuristic disagrees with upstream's 'malicious in path' rule")
    for d in a["disagreements"]:
        print(f"    {d['path']}  loader={d['loader']} "
              f"upstream={d['upstream_rule']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
