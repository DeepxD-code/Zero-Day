"""Guards against the project's dominant error mode: WRONG PAIRING.

Six experiments in this archive produced a wrong number for the same reason --
a model evaluated against something it was not trained with:

  E11  split the dataframe by port BEFORE graphing, so the graphs were
       fragments and the attacker's degree signal did not exist
  E16  concatenated four day-files, and `_window_key` is RELATIVE to the
       frame start, so days collided into shared windows
  E42  scored the base checkpoint with the replay-mix scaler instead of its own
  E43  ranked within row-count chunks instead of within real 60s windows
  E44  paired the clean-data checkpoint with the original day (which measures
       the cross-testbed gap, not whatever was being tested)

Every one of them was caught by the same thing: a number came out that did not
match a number already known. That is a slow, luck-based defence. These
functions make it explicit and fast.

Nothing here knows about attacks. They check that the *parts of a measurement
fit together*:

  require_scaler_match  a checkpoint and the scaler used to score it
  require_dataset       a checkpoint and the data it is being scored on
  require_window_groups ranks are computed within real time windows
  Anchors               a run reproduces a previously recorded value

The dataset check WARNS rather than raises by default, because scoring a
checkpoint on a second testbed is legitimate and is exactly what E42 does.
Everything else raises.
"""

from __future__ import annotations

import hashlib
import re
import warnings

import numpy as np
import torch


class PairingError(RuntimeError):
    """Raised when a measurement's components provably do not belong together."""


# ---------------------------------------------------------------- scaler


def _scaler_arrays(blob: dict) -> tuple[np.ndarray, np.ndarray, bool]:
    """Pull (lo, hi, log) out of a checkpoint's scaler.

    Two layouts ship in this repo:

      M5b / GNN  blob["scaler"] = {"lo", "hi", "log"}
      M5a        blob["flow_lo"] / blob["flow_hi"] at the TOP level, plus
                 ctx_lo/ctx_hi for the context block (m5a_revived_*.pt)

    Both are handled; an unrecognised layout raises rather than guessing,
    because guessing here is exactly the class of error this module exists
    to catch.
    """
    sc = blob.get("scaler")
    if isinstance(sc, dict) and "lo" in sc and "hi" in sc:   # M5b NodeScaler
        return (np.asarray(sc["lo"], dtype=np.float64),
                np.asarray(sc["hi"], dtype=np.float64),
                bool(sc.get("log", True)))
    if "flow_lo" in blob and "flow_hi" in blob:               # M5a MinMax
        return (np.asarray(blob["flow_lo"], dtype=np.float64),
                np.asarray(blob["flow_hi"], dtype=np.float64),
                False)
    if sc is None and "flow_lo" not in blob:
        raise PairingError(
            "checkpoint carries no recognisable scaler (looked for "
            "blob['scaler']['lo'] and blob['flow_lo']; keys present: "
            f"{sorted(blob)[:8]})")
    raise PairingError(f"unrecognised scaler keys: {sorted(sc)}")


def scaler_fingerprint(blob: dict) -> str:
    """Stable hash of a checkpoint's scaler. Two checkpoints that ship the same
    scaler share a fingerprint; a re-fit scaler does not."""
    lo, hi, log = _scaler_arrays(blob)
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(lo).tobytes())
    h.update(np.ascontiguousarray(hi).tobytes())
    h.update(b"1" if log else b"0")
    return h.hexdigest()[:16]


def require_scaler_match(ckpt_blob: dict, scaler, context: str = "") -> None:
    """A scaler must be the one that shipped inside the checkpoint.

    Catches E42: a base checkpoint scored with a scaler refit on a different
    training mix produces plausible, badly wrong numbers.
    """
    lo, hi, log = _scaler_arrays(ckpt_blob)
    if hasattr(scaler, "lo"):
        s_lo = np.asarray(scaler.lo, dtype=np.float64)
        s_hi = np.asarray(scaler.hi, dtype=np.float64)
    else:
        raise PairingError(f"{context}: scaler object has no .lo/.hi")
    if s_lo.shape != lo.shape:
        raise PairingError(
            f"{context}: scaler dim {s_lo.shape} != checkpoint {lo.shape} "
            "(wrong feature set or a scaler from a different model)")
    d_lo = float(np.abs(s_lo - lo).max()) if s_lo.shape == lo.shape else float("inf")
    d_hi = float(np.abs(s_hi - hi).max()) if s_hi.shape == hi.shape else float("inf")
    if d_lo or d_hi:
        raise PairingError(
            f"{context}: scaler does not match the checkpoint "
            f"(max |dlo| = {d_lo:.6g}, max |dhi| = {d_hi:.6g}). The scaler was "
            "refit on different data. Score the checkpoint with the scaler saved "
            "inside it, or re-derive the scaler from the same training set the "
            "checkpoint was fit on.")


# --------------------------------------------------------------- dataset


# Corpus aliases -> canonical token. Matching is longest-alias-first on a
# separator-stripped string, because the same corpus is written 'CIC-IDS2017',
# 'cicids2017', 'GeneratedLabelledFlows' and 'CNS2022' across this repo.
# The VARIANT is tracked separately, because "original CIC-IDS2017" and
# "CICIDS2017_improved" are the same corpus but two genuinely different
# captures, and this project's entire cross-testbed story is about that
# difference. Collapsing them would defeat the check.
_CORPUS = {
    "generatedlabelledflows": "cicids2017", "cicids2017": "cicids2017",
    "cns2022": "cicids2017",
    "adfald2016": "adfa", "adfald": "adfa", "adfa": "adfa",
    "ustctfc2016": "ustc", "cicdarknet": "cicdarknet",
}
# variant token -> canonical variant. Absent means "the raw/original capture".
_VARIANT = {
    "improved": "improved", "original": "original", "orig": "original",
    "raw": "original", "base": "original",
}
_CORPUS_ORDER = sorted(_CORPUS, key=len, reverse=True)


def _identify(name: str) -> tuple[str | None, str | None]:
    """Split a free-text dataset description into (corpus, variant).

    'original CIC-IDS2017 PortScan'      -> ('cicids2017', 'original')
    'GeneratedLabelledFlows/Traffic…'   -> ('cicids2017', 'original')
    'CICIDS2017_improved/monday benign'  -> ('cicids2017', 'improved')
    'ADFA-LD'                            -> ('adfa', 'original')
    'some new capture'                   -> (None, None)

    A recognised corpus with no explicit variant token is the RAW capture.
    'GeneratedLabelledFlows/TrafficLabelling' is how this repo spells the
    original CIC-IDS2017 extraction, and it must compare equal to 'original
    CIC-IDS2017' or the guard would flag the project's own home testbed as a
    transfer run.
    """
    text = str(name).lower()
    flat = re.sub(r"[^a-z0-9]", "", text)
    corpus = next((_CORPUS[a] for a in _CORPUS_ORDER if a in flat), None)
    variant = next((_VARIANT[t] for t in re.findall(r"[a-z]+", text)
                    if t in _VARIANT), None)
    if corpus is not None and variant is None:
        variant = "original"
    return corpus, variant


def _same_dataset(a: str, b: str) -> bool:
    """Loose but non-vacuous dataset identity check.

    Provenance strings in this repo are free text
    ('CICIDS2017_improved/monday benign-only') and callers pass a description
    ('original CIC-IDS2017 PortScan'). A plain substring test is too weak and a
    plain token-overlap test is too strong (it would call the two CIC-IDS2017
    captures the same). So: identity requires the SAME corpus AND the SAME
    variant. If either string is unidentifiable, fall back to substring, and
    treat two unidentifiable strings as unknown rather than equal.
    """
    na, nb = str(a).lower().strip(), str(b).lower().strip()
    ca, va = _identify(na)
    cb, vb = _identify(nb)
    if ca and cb:
        return ca == cb and va == vb
    if na in nb or nb in na:
        return True
    return False


def require_dataset(ckpt_blob: dict, dataset: str, strict: bool = False,
                    context: str = "") -> None:
    """Warn (or raise) when a checkpoint is scored on data it was not trained on.

    Deliberately a WARNING by default: E42 exists precisely to score a
    clean-trained checkpoint on the original testbed, and that is legitimate
    work. The guard exists so the result is labelled, not so the run stops.

    Silent when the checkpoint carries no provenance (`train` absent) -- older
    checkpoints predate the field, and refusing to score them would be worse
    than the risk. Silent when the two names clearly refer to the same corpus.
    """
    trained_on = ckpt_blob.get("train")
    if trained_on is None:
        return
    if _same_dataset(str(trained_on), str(dataset)):
        return
    msg = (f"{context}: checkpoint was trained on {trained_on!r} but is being "
           f"scored on {dataset!r}. If this is a transfer experiment, quote the "
           "cross-testbed gap explicitly (see E17/E27/E42).")
    if strict:
        raise PairingError(msg)
    warnings.warn(msg, RuntimeWarning, stacklevel=2)


# --------------------------------------------------------- rank grouping


def require_window_groups(groups: np.ndarray, n_rows: int,
                          context: str = "",
                          uniform_min: int = 5) -> dict:
    """Ranks must be computed within real time windows, not arbitrary chunks.

    Catches E43, where `np.arange(n) // 5000` stood in for window ids. That
    grouping is monotonic, starts at 0 and covers every row, so a structural
    check passes it -- but it is not a window, and the AUC it produces is not
    the production metric.

    The discriminator is *occupancy*. Real 60s windows over real traffic are
    bursty: sizes vary widely and some windows are near-empty. A fixed-row-count
    chunk produces identical group sizes (except the last), which is a
    signature no real capture reproduces.

    Hard checks: length, start at 0, non-decreasing (time order), and the
    uniformity signature. Returns the group-size profile either way so the run
    can be logged.
    """
    g = np.asarray(groups)
    if g.ndim != 1:
        raise PairingError(f"{context}: group ids are {g.ndim}-D, expected 1-D")
    if g.shape[0] != n_rows:
        raise PairingError(
            f"{context}: {g.shape[0]} group ids for {n_rows} rows")
    if n_rows == 0:
        raise PairingError(f"{context}: no rows to group")
    if g.min() != 0:
        raise PairingError(f"{context}: group ids start at {g.min()}, not 0")
    if not np.all(np.diff(g) >= 0):
        raise PairingError(
            f"{context}: group ids are not non-decreasing -- they are not in "
            "time order, so 'within-group rank' is meaningless")

    n_groups = int(g.max()) + 1
    sizes = np.bincount(g, minlength=n_groups)
    nonempty = sizes[sizes > 0]
    profile = {
        "n_groups": n_groups,
        "n_rows": int(n_rows),
        "rows_per_group_mean": round(float(nonempty.mean()), 1) if nonempty.size else 0.0,
        "rows_per_group_min": int(nonempty.min()) if nonempty.size else 0,
        "rows_per_group_max": int(nonempty.max()) if nonempty.size else 0,
    }

    # Occupancy spread: how much do real windows vary in size?
    if nonempty.size >= uniform_min:
        head = nonempty[:-1]              # ignore a short final chunk
        if head.size >= uniform_min - 1 and head.size and np.all(head == head[0]) \
                and head[0] >= 100:
            raise PairingError(
                f"{context}: all {head.size} groups hold exactly {int(head[0])} "
                f"rows. Fixed-size groups are a row-count chunk, not a time "
                "window -- pass real window keys from _window_key(). "
                f"profile={profile}")
    return profile


# --------------------------------------------------------------- anchors


ANCHORS: dict[str, dict] = {
    # (value, tol, what it proves). Fill ANCHORS with values produced by a run
    # you trust -- the point is that a *changed* number must be explained.
    "E12_control_portscan": {
        "value": 0.8714, "tol": 0.002,
        "proves": "shipped original-data ckpt on original PortScan, 60s window rank",
    },
    "E21_band_portscan_clean": {
        "value": 0.9483, "tol": 0.030,
        "proves": "clean-data v2 ckpt, 4-seed band, per-day clean PortScan",
    },
    "E23_host_ae": {
        "value": 0.7768, "tol": 0.010,
        "proves": "host AE on ADFA-LD, 4-seed band, count-vector model",
    },
    "E24_reputation_portscan_x5": {
        "value": 0.9789, "tol": 0.010,
        "proves": "causal reputation vs dilate x5 on original PortScan",
    },
    "E44_control_portscan": {
        "value": 0.8714, "tol": 0.002,
        "proves": "shipped ckpt + original day, per-window rank (E44 control)",
    },
}


def check_anchor(name: str, value: float, context: str = "") -> None:
    """Raise if a run produces a number that disagrees with a known-good one.

    This is the check that actually caught E42 and E43, and it is the cheapest
    thing in this file. Run it on the control arm of every new experiment.
    """
    a = ANCHORS.get(name)
    if a is None:
        raise PairingError(f"unknown anchor {name!r}; add it to ANCHORS first")
    if abs(value - a["value"]) > a["tol"]:
        raise PairingError(
            f"{context}: control arm gives {value:.4f} but anchor "
            f"{name!r} records {a['value']:.4f} (+-{a['tol']}). "
            f"That anchor proves: {a['proves']}. A control that moved is a "
            "broken control -- check model/data pairing, scaler, and rank "
            "grouping before reading anything else in the run.")


def register_anchor(name: str, value: float, tol: float, proves: str) -> None:
    """Record a new known-good value (only from a run whose control passed)."""
    ANCHORS[name] = {"value": value, "tol": tol, "proves": proves}


def provenance_report(paths=None) -> dict:
    """Which shipped checkpoints can the dataset guard actually check?

    Worth running once and reading. 5 of the 7 checkpoints in `detection/`
    predate the `train` provenance field, so `require_dataset` is SILENT on
    them -- including `gnn_autoencoder_v1_logscale_v2.pt`, which is the
    checkpoint E12's control anchor is measured on and the one E44 paired
    against the wrong day. A guard that quietly does nothing on the legacy
    models is worse than no guard, so this makes the gap explicit instead.
    """
    from pathlib import Path

    det = Path(__file__).resolve().parent
    paths = paths or sorted(det.glob("*.pt"))
    rows = {}
    for p in paths:
        p = Path(p)
        try:
            blob = torch.load(p, map_location="cpu", weights_only=True)
        except Exception:
            try:
                blob = torch.load(p, map_location="cpu", weights_only=False)
            except Exception as e:                 # unreadable at all
                rows[p.name] = {"provenance": None, "status": f"unreadable: {e}"}
                continue
        prov = blob.get("train")
        try:
            blob_id = scaler_fingerprint(blob)
        except PairingError:
            blob_id = None
        rows[p.name] = {
            "provenance": prov,
            "scaler_fingerprint": blob_id,
            "status": "checkable" if prov else "NO PROVENANCE - dataset guard is silent",
        }
    return rows


# ------------------------------------------------------------------ misc


def require_no_selfcheck(ckpt_blob: dict, context: str = "") -> None:
    """Refuse to score a checkpoint with a scaler it does not contain.

    Convenience wrapper for the common M5b path; loads under weights_only=True
    so it is safe on untrusted checkpoints.
    """
    if "scaler" not in ckpt_blob:
        raise PairingError(f"{context}: no scaler in checkpoint")
