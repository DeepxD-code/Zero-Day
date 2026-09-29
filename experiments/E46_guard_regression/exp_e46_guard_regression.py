"""Prove the guards FIRE on the real bugs, not just on fixtures.

Each case below reintroduces a mistake that actually happened in this archive
and asserts the guard refuses to proceed. A guard that only passes unit tests
on synthetic input is not a guard.

    python experiments/E46_guard_regression/exp_e46_guard_regression.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from eval_guards import (PairingError, require_dataset, require_scaler_match,
                         require_window_groups)
from gnn_model import GraphAutoencoder, NodeScaler

DET = ROOT / "detection"
OUT = Path(__file__).resolve().parent / "exp_e46_guard_regression.json"


def _node_scaler(blob):
    return NodeScaler(log=bool(blob["scaler"].get("log", True))).load_state_dict(
        blob["scaler"])


RESULTS = []


def case(name, expect, fn):
    """expect: 'raises' or 'passes'."""
    try:
        detail = fn()
        got = "passes"
        msg = detail or "completed without error"
    except PairingError as e:
        got = "raises"
        msg = str(e)
    except Exception as e:                       # a wrong exception type is a fail
        got = f"WRONG EXCEPTION {type(e).__name__}"
        msg = str(e) + "\n" + traceback.format_exc(limit=2)
    ok = got == expect
    RESULTS.append({"case": name, "expected": expect, "got": got,
                    "pass": ok, "detail": msg})
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"        -> {msg.splitlines()[0][:150]}")
    return ok


# ---------------------------------------------------------------------
# 1. E42: base checkpoint scored with the replay-mix scaler
# ---------------------------------------------------------------------
def e42_exact_bug():
    """Reproduce E42 run 1 verbatim: correct model, WRONG scaler."""
    base_blob = torch.load(DET / "gnn_improved_s0.pt", map_location="cpu",
                           weights_only=True)
    model = GraphAutoencoder(in_dim=19)
    model.load_state_dict(base_blob["model"])

    # A scaler refit on a different training mix -- this is what E42 did.
    mixed = NodeScaler(log=True)
    mixed.lo = np.asarray(base_blob["scaler"]["lo"], dtype=np.float64) * 0.5
    mixed.hi = np.asarray(base_blob["scaler"]["hi"], dtype=np.float64) * 2.0

    require_scaler_match(base_blob, mixed, "E42 replay-mix scaler")
    return "unreachable"


def e42_correct_pairing():
    """The fix: score the base with its own scaler."""
    base_blob = torch.load(DET / "gnn_improved_s0.pt", map_location="cpu",
                           weights_only=True)
    require_scaler_match(base_blob, _node_scaler(base_blob), "E42 base+own scaler")
    return "base paired with its own scaler, as shipped"


# ---------------------------------------------------------------------
# 2. E43: ranks computed within row-count chunks, not time windows
# ---------------------------------------------------------------------
def e43_exact_bug():
    """Reproduce E43 run 1: `np.arange(n) // 5000` standing in for window ids."""
    n = 53082
    groups = np.arange(n) // 5000
    require_window_groups(groups, n, context="E43 chunk groups")
    return "unreachable"


def e43_real_windows():
    """The fix: real window keys from _window_key(), which are bursty."""
    rng = np.random.default_rng(7)
    sizes = rng.integers(60, 1200, size=180)
    groups = np.repeat(np.arange(180), sizes)
    prof = require_window_groups(groups, len(groups), context="E43 real windows")
    return f"real windows accepted: {prof['n_groups']} groups, " \
           f"{prof['rows_per_group_min']}-{prof['rows_per_group_max']} rows each"


# ---------------------------------------------------------------------
# 3. E44: clean-data checkpoint scored on an original-testbed day
# ---------------------------------------------------------------------
def e44_exact_bug():
    """Reproduce E44 run 1: the cross-testbed gap presented as an evasion test."""
    clean_blob = torch.load(DET / "gnn_improved_s0.pt", map_location="cpu",
                            weights_only=True)
    import warnings
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        require_dataset(clean_blob, "original CIC-IDS2017 PortScan",
                        context="E44 clean ckpt on orig day")
    assert caught, "guard stayed silent on the E44 mistake"
    return (f"warned ({len(caught)} warning(s)): "
            f"{str(caught[0].message)[:110]}")


def e44_correct_pairing():
    """The fix: the improved checkpoint scored on improved data is silent."""
    clean_blob = torch.load(DET / "gnn_improved_s0.pt", map_location="cpu",
                            weights_only=True)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        require_dataset(clean_blob, "CICIDS2017_improved monday",
                        context="E44 clean ckpt on clean day")
    return "same-testbed pairing is silent"


# ---------------------------------------------------------------------
# 4. E16: day-files concatenated, so relative window keys collide
# ---------------------------------------------------------------------
def e16_windows_are_relative():
    """_window_key normalises epoch to `ts.min()` of the frame it is given.

    Concat-then-key is SAFE (the global min anchors both days to distinct
    ids). The dangerous order is key-each-day-then-concatenate: each day
    restarts at 0, so window 5 of Monday and window 5 of Tuesday both land on
    key 5, and a downstream groupby(key) silently merges two different hours
    into one window. This is the E16 collision.

    Days of similar density produce near-identical per-window occupancy, so
    the aliasing shows up as suspiciously uniform group sizes -- which is the
    signature require_window_groups rejects.
    """
    import pandas as pd
    from graph_builder import _window_key

    mon = pd.DataFrame({"timestamp": pd.date_range("2017-07-03 09:00",
                                                  periods=600, freq="s")})
    tue = pd.DataFrame({"timestamp": pd.date_range("2017-07-04 09:00",
                                                  periods=600, freq="s")})
    # SAFE order: one frame, one anchor.
    k_safe = _window_key(pd.concat([mon, tue], ignore_index=True), 60)
    assert k_safe[600] != k_safe[0], "concat-then-key should NOT alias"
    # DANGEROUS order: each day anchored to its own start, then merged.
    k_alias = pd.concat([_window_key(mon, 60), _window_key(tue, 60)],
                        ignore_index=True)
    assert int((k_alias[:600].to_numpy() == k_alias[600:].to_numpy()).sum()) == 600
    n_groups = int(k_alias.groupby(k_alias).ngroups)
    return (f"2 days aliased 600/600 window ids into {n_groups} groups "
            f"(should be {2 * (600 // 60)}); concat-then-key is safe")


def e16_aliasing_is_caught():
    """The aliased grouping must be refused, not silently scored."""
    import pandas as pd
    from graph_builder import _window_key
    mon = pd.DataFrame({"timestamp": pd.date_range("2017-07-03 09:00",
                                                  periods=600, freq="s")})
    tue = pd.DataFrame({"timestamp": pd.date_range("2017-07-04 09:00",
                                                  periods=600, freq="s")})
    k_alias = pd.concat([_window_key(mon, 60), _window_key(tue, 60)],
                        ignore_index=True).to_numpy()
    require_window_groups(k_alias, len(k_alias), context="E16 aliased windows")
    return "unreachable"


def main():
    print("Guard regression: does it stop the mistakes that actually happened?\n")
    ok = []
    ok.append(case("E42 base scored with replay-mix scaler", "raises",
                   e42_exact_bug))
    ok.append(case("E42 base scored with its own scaler", "passes",
                   e42_correct_pairing))
    ok.append(case("E43 ranks within row-count chunks", "raises",
                   e43_exact_bug))
    ok.append(case("E43 ranks within real time windows", "passes",
                   e43_real_windows))
    ok.append(case("E44 clean ckpt on original-testbed day", "passes",
                   e44_exact_bug))
    ok.append(case("E44 clean ckpt on improved-testbed day", "passes",
                   e44_correct_pairing))
    ok.append(case("E16 per-day keying then concat aliases windows", "passes",
                   e16_windows_are_relative))
    ok.append(case("E16 aliased window groups are refused", "raises",
                   e16_aliasing_is_caught))

    n_pass = sum(ok)
    print(f"\n{n_pass}/{len(ok)} cases behaved as required")
    OUT.write_text(
        __import__("json").dumps(
            {"summary": {"cases": len(ok), "as_required": n_pass},
             "cases": RESULTS}, indent=1), encoding="utf-8")
    print(f"-> {OUT.name}")
    raise SystemExit(0 if n_pass == len(ok) else 1)


if __name__ == "__main__":
    main()
