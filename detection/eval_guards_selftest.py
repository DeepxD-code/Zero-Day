"""Tests for detection/eval_guards.py — each test reproduces a REAL bug from
the archive, so a regression here means the bug can come back.

    python detection/eval_guards_selftest.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_guards import (ANCHORS, PairingError, _same_dataset, check_anchor,
                         provenance_report, register_anchor, require_dataset,
                         require_scaler_match, require_window_groups,
                         scaler_fingerprint)

PASS, FAIL = [], []


def ok(name, fn):
    try:
        fn()
        PASS.append(name)
    except Exception as e:
        FAIL.append((name, f"{type(e).__name__}: {e}"))


def expect_raises(name, fn, must_contain=""):
    try:
        fn()
    except PairingError as e:
        if must_contain and must_contain not in str(e):
            FAIL.append((name, f"raised but message lacked {must_contain!r}: {e}"))
        else:
            PASS.append(name)
        return
    except Exception as e:
        FAIL.append((name, f"raised {type(e).__name__} not PairingError: {e}"))
        return
    FAIL.append((name, "did NOT raise"))


# ---- fixtures ---------------------------------------------------------
CKPT_A = {"model": {}, "scaler": {"lo": np.zeros(19), "hi": np.ones(19),
                                   "log": True}, "in_dim": 19,
          "train": "CICIDS2017_improved/monday benign-only"}
CKPT_B = {"model": {}, "scaler": {"lo": np.zeros(19), "hi": np.ones(19),
                                   "log": True}, "in_dim": 19}
CKPT_MIXED = {"model": {}, "scaler": {"lo": np.zeros(19) * 0.5,
                                      "hi": np.ones(19) * 2.0, "log": True}}
# M5a layout as it actually ships: scaler arrays at the TOP level, no
# blob['scaler'] key at all (verified against detection/m5a_revived_*.pt).
CKPT_M5A = {"state_dict": {}, "input_dim": 93,
            "flow_lo": np.zeros(76), "flow_hi": np.ones(76),
            "ctx_lo": np.zeros(4), "ctx_hi": np.ones(4)}
CKPT_NO_SCALER = {"model": {}}


class _Sc:
    def __init__(self, lo, hi):
        self.lo = np.asarray(lo, dtype=np.float64)
        self.hi = np.asarray(hi, dtype=np.float64)


# ---- 1. scaler pairing (E42's bug) -----------------------------------
def t_scaler_match_passes():
    require_scaler_match(CKPT_A, _Sc(np.zeros(19), np.ones(19)), "t1")


def t_scaler_mismatch_raises():
    """E42: base checkpoint scored with the replay-mix scaler."""
    require_scaler_match(CKPT_A, _Sc(np.zeros(19) * 0.5, np.ones(19) * 2.0), "t2")


def t_scaler_dim_mismatch_raises():
    require_scaler_match(CKPT_A, _Sc(np.zeros(8), np.ones(8)), "t3")


def t_m5a_scaler_parsed():
    require_scaler_match(CKPT_M5A, _Sc(np.zeros(76), np.ones(76)), "t4")


def t_missing_scaler_raises():
    require_scaler_match(CKPT_NO_SCALER, _Sc(np.zeros(19), np.ones(19)), "t5")


def t_fingerprint_differs():
    a = scaler_fingerprint(CKPT_A)
    b = scaler_fingerprint(CKPT_MIXED)
    assert a != b, "different scalers produced the same fingerprint"
    assert a == scaler_fingerprint(dict(CKPT_A)), "fingerprint not stable"


ok("t1 correct scaler passes", t_scaler_match_passes)
expect_raises("t2 E42 wrong scaler raises", t_scaler_mismatch_raises,
              "refit on different data")
expect_raises("t3 wrong feature-set dim raises", t_scaler_dim_mismatch_raises,
              "wrong feature set")
ok("t4 M5a scaler shape parsed", t_m5a_scaler_parsed)
expect_raises("t5 missing scaler raises", t_missing_scaler_raises,
              "no recognisable scaler")
ok("t6 fingerprint differs by scaler", t_fingerprint_differs)

# ---- 2. dataset provenance -------------------------------------------
def t_dataset_warns_by_default():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        require_dataset(CKPT_A, "original CIC-IDS2017 PortScan", context="t7")
    assert any(issubclass(w.category, RuntimeWarning) for w in caught), \
        "cross-dataset did not warn"


def t_dataset_strict_raises():
    require_dataset(CKPT_A, "original CIC-IDS2017 PortScan", strict=True,
                    context="t8")


def t_dataset_same_silent():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        require_dataset(CKPT_A, "CICIDS2017_improved/monday benign-only", "t9")


def t_dataset_no_provenance_silent():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        require_dataset(CKPT_B, "anything", "t10")


def t_improved_vs_original_differ():
    """The distinction this whole project turns on.

    CICIDS2017_improved is a re-capture of the CIC-IDS2017 corpus. A
    token-overlap identity check would call the two the same dataset and the
    guard would go silent on exactly the cross-testbed case it exists for.
    """
    assert not _same_dataset("CICIDS2017_improved/monday benign-only",
                             "original CIC-IDS2017 PortScan")
    assert _same_dataset("CICIDS2017_improved/monday benign-only",
                         "CICIDS2017_improved monday")
    assert not _same_dataset("CICIDS2017_improved", "CISNET2017")
    assert _same_dataset("original CIC-IDS2017", "CIC-IDS2017 original PortScan")
    assert _same_dataset("ADFA-LD", "adfa ld host logs")
    assert not _same_dataset("ADFA-LD", "original CIC-IDS2017 PortScan")


def t_improved_vs_original_warns():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        require_dataset(CKPT_A, "original CIC-IDS2017 PortScan", context="t11b")
    assert caught, "improved->original should warn"


ok("t7 cross-dataset warns by default", t_dataset_warns_by_default)
expect_raises("t8 strict dataset raises", t_dataset_strict_raises,
              "cross-testbed gap")
ok("t9 matching dataset is silent", t_dataset_same_silent)
ok("t10 missing provenance is silent", t_dataset_no_provenance_silent)
ok("t11a improved != original, and identity resolves", t_improved_vs_original_differ)
ok("t11b improved->original warns", t_improved_vs_original_warns)

# ---- 3. rank grouping (E43's bug) -------------------------------------
def t_real_windows_pass():
    """E24-style: 150 windows over ~30k rows, but BURSTY like real traffic.

    A perfectly uniform 200 rows/window is exactly the signature the guard
    rejects, so the fixture varies occupancy the way a real capture does.
    """
    rng = np.random.default_rng(0)
    sizes = rng.integers(40, 900, size=150)
    g = np.repeat(np.arange(150), sizes)
    return require_window_groups(g, len(g), context="t12")


def t_chunk_groups_raise():
    """E43's bug: np.arange(n) // 5000 standing in for window ids."""
    n = 53082
    g = np.arange(n) // 5000
    require_window_groups(g, n, context="t13")


def t_shuffled_groups_raise():
    rng = np.random.default_rng(0)
    sizes = rng.integers(40, 200, size=10)
    g = np.repeat(np.arange(10), sizes)
    n = len(g)
    require_window_groups(g[rng.permutation(n)], n, context="t14")


def t_wrong_length_raises():
    require_window_groups(np.arange(10), 99, context="t15")


def t_nonzero_start_raises():
    require_window_groups(np.arange(1, 11), 10, context="t16")


ok("t12 real window ids pass", t_real_windows_pass)
expect_raises("t13 E43 chunk groups raise", t_chunk_groups_raise,
              "row-count chunk, not a time window")
expect_raises("t14 non-monotonic groups raise", t_shuffled_groups_raise,
              "not in time order")
expect_raises("t15 group/row length mismatch raises", t_wrong_length_raises,
              "group ids for")
expect_raises("t16 nonzero group start raises", t_nonzero_start_raises,
              "not 0")

# ---- 4. anchors (what actually caught E42/E43) -----------------------
def t_anchor_within_tol_passes():
    check_anchor("E12_control_portscan", 0.8714, "t17")


def t_anchor_outside_tol_raises():
    """E42's tell: a control arm that moved to 0.427."""
    check_anchor("E12_control_portscan", 0.427, "t18")


def t_unknown_anchor_raises():
    check_anchor("nope", 0.5)


def t_register_anchor_roundtrip():
    register_anchor("selftest_tmp", 1.0, 0.1, "selftest")
    check_anchor("selftest_tmp", 1.05)
    del ANCHORS["selftest_tmp"]


ok("t17 anchor within tolerance passes", t_anchor_within_tol_passes)
expect_raises("t18 moved control raises", t_anchor_outside_tol_raises,
              "broken control")
expect_raises("t19 unknown anchor raises", t_unknown_anchor_raises,
              "unknown anchor")
ok("t20 register_anchor roundtrip", t_register_anchor_roundtrip)


# ---- 5. the real shipped checkpoints --------------------------------
def t_shipped_checkpoints_self_consistent():
    det = Path(__file__).resolve().parent
    for f in ["gnn_improved_s0.pt", "gnn_improved_replay.pt",
              "gnn_autoencoder_v1_logscale_v2.pt"]:
        b = torch.load(det / f, map_location="cpu", weights_only=True)
        from eval_guards import _scaler_arrays
        lo, hi, _ = _scaler_arrays(b)
        require_scaler_match(b, _Sc(lo, hi), f)


ok("t21 shipped checkpoints are self-consistent", t_shipped_checkpoints_self_consistent)


# ---- 6. provenance coverage of the real shipped checkpoints -----------
def t_provenance_report_covers_every_ckpt():
    """The dataset guard is only as good as the provenance fields.

    5 of 7 shipped checkpoints predate the `train` key, so `require_dataset`
    cannot fire on them. This test records that gap rather than asserting it
    away: if someone back-fills provenance, the report must change.
    """
    rep = provenance_report()
    assert rep, "no checkpoints found"
    for name, row in rep.items():
        assert "status" in row, name
    checkable = [n for n, r in rep.items() if r["provenance"]]
    missing = [n for n, r in rep.items() if not r["provenance"]]
    print(f"\n  provenance: {len(checkable)} checkable, {len(missing)} missing")
    for n in missing:
        print(f"    no provenance: {n}")
    # Guard against the fixture set being empty or the loader silently failing.
    assert not any(str(r.get("status", "")).startswith("unreadable")
                   for r in rep.values()), \
        f"a shipped checkpoint could not be read: {rep}"
    # E47 back-filled provenance on every shipped checkpoint, so a new one
    # arriving without it is a regression, not a neutral state.
    assert not missing, (
        f"checkpoints have no provenance, so require_dataset is silent on "
        f"them: {missing}. Run "
        f"experiments/E47_provenance_audit/exp_e47_backfill.py --dry-run.")


def t_e44_mistake_is_now_caught():
    """The specific case E47 exists for.

    `gnn_autoencoder_v1_logscale_v2.pt` is the checkpoint E44 paired against a
    clean-data day. Before E47 it carried no `train` field, so the dataset
    guard was silent and the mistake produced a plausible wrong number. It must
    warn now, and it must NOT warn on its own home testbed.
    """
    det = Path(__file__).resolve().parent
    b = torch.load(det / "gnn_autoencoder_v1_logscale_v2.pt", map_location="cpu",
                   weights_only=True)
    assert b.get("train"), "provenance missing; the guard cannot fire"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        require_dataset(b, "CICIDS2017_improved/monday benign-only",
                        context="E44 clean-day pairing")
    assert caught, "E44's mistake is still silent"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        require_dataset(b, "original CIC-IDS2017 GeneratedLabelledFlows/monday",
                        context="home testbed")


def t_raw_extraction_is_not_a_transfer():
    assert _same_dataset("GeneratedLabelledFlows/TrafficLabelling",
                         "original CIC-IDS2017 PortScan")
    assert not _same_dataset("GeneratedLabelledFlows/TrafficLabelling",
                             "CICIDS2017_improved/monday")


ok("t22 provenance report covers every checkpoint",
   t_provenance_report_covers_every_ckpt)
ok("t24 E44's mispairing is now caught by the dataset guard",
   t_e44_mistake_is_now_caught)
ok("t23 raw extraction is the home testbed, not a transfer",
   t_raw_extraction_is_not_a_transfer)

# ---- report -----------------------------------------------------------
print(f"\n{len(PASS)} passed, {len(FAIL)} failed\n")
for n in PASS:
    print("  PASS", n)
for n, why in FAIL:
    print("  FAIL", n, "->", why)
raise SystemExit(1 if FAIL else 0)
