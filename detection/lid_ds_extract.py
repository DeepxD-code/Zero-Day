"""Extract a LID-DS 2021 CVE archive into the trace layout the loader wants.

The published archives are nested: an outer zip holds
`CVE-YYYY-NNNN/{training,validation,test/{normal,normal_and_attack}}/*.zip`, and
each inner zip holds `<name>.{json,sc,pcap,res}`. This unpacks only the `.sc`
trace and its `.json` sidecar into

    <dest>/CVE-YYYY-NNNN/<split>/<recording>/<recording>.{sc,json}

which is exactly what `detection/lid_ds_loader.py` walks, and drops the `.pcap`
and `.res` payloads (network traces and resource snapshots -- not host features,
and they are the bulk of the bytes).

Only `.sc` and `.json` are extracted on purpose: the loader's label source is the
JSON sidecar, so both must land together or a recording would silently fall back
to a path heuristic.

    python detection/lid_ds_extract.py <archive.zip>
    python detection/lid_ds_extract.py <archive.zip> --dest <dir>
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / "data" / "practice" / "LID-DS_SyscallRecords"
KEEP = {".sc", ".json"}
# Inner payloads we deliberately drop.
DROP = {".pcap", ".scap", ".res", ".png", ".jpg"}


def extract(archive: Path, dest: Path = DEFAULT_DEST, dry_run: bool = False) -> dict:
    counts: Counter = Counter()
    skipped: list[str] = []
    seen_inner = 0
    with zipfile.ZipFile(archive) as outer:
        for info in outer.infolist():
            name = info.filename
            if info.is_dir() or "__MACOSX" in name or "/._" in name \
                    or name.endswith("/.DS_Store"):
                continue
            if not name.lower().endswith(".zip"):
                continue
            # <scenario>/<splitdir>/[<test subdir>/]<recording>.zip
            parts = Path(name).parts
            if len(parts) < 3:
                skipped.append(name)
                continue
            # <scenario>/<splitdir>/[<test subdir>/]<recording>.zip
            # Keep the scenario directory: an archive dropped straight at the
            # destination root destroys the family grouping, and the loader's
            # _family_from_path then reports every trace as "unknown". The first
            # version sliced parts[1:-1], which cut the scenario off.
            rel = Path(*parts[:-1])           # CVE-2012-2122/test/normal
            stem = Path(parts[-1]).stem
            outdir = dest / rel / stem
            seen_inner += 1
            if dry_run:
                continue
            try:
                with outer.open(name) as raw:
                    import io
                    with zipfile.ZipFile(io.BytesIO(raw.read())) as inner:
                        got = []
                        for m in inner.infolist():
                            suf = Path(m.filename).suffix.lower()
                            if suf in DROP or Path(m.filename).name.startswith("._"):
                                continue
                            if suf not in KEEP:
                                continue
                            outdir.mkdir(parents=True, exist_ok=True)
                            out = outdir / f"{stem}{suf}"
                            out.write_bytes(inner.read(m))
                            got.append(suf)
                counts[f"n:{rel.as_posix()}"] += 1
                if ".sc" in got and ".json" in got:
                    counts["complete"] += 1
                else:
                    counts["INCOMPLETE"] += 1
                    skipped.append(f"{rel.as_posix()}/{stem} -> {got}")
            except Exception as exc:                       # noqa: BLE001
                counts["ERROR"] += 1
                skipped.append(f"{rel.as_posix()}/{stem}: {exc}")
    return {"archive": archive.name, "inner_zips": seen_inner,
            "counts": dict(counts), "skipped": skipped[:40],
            "n_skipped": len(skipped)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.archive.is_file():
        print(f"no such archive: {a.archive}")
        return 1
    r = extract(a.archive, a.dest, a.dry_run)
    print(f"archive      {r['archive']}")
    print(f"inner zips   {r['inner_zips']}")
    for k in sorted(r["counts"]):
        print(f"  {k:44s} {r['counts'][k]}")
    if r["n_skipped"]:
        print(f"  skipped/flagged: {r['n_skipped']}")
        for s in r["skipped"]:
            print(f"    {s}")
    if not a.dry_run:
        print("\nnext: python detection/lid_ds_loader.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())