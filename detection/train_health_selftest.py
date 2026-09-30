"""Tests for detection/train_health.py.

Each test reproduces a REAL failure from this branch, so a regression here means
the failure can come back.

    python detection/train_health_selftest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from train_health import (UntrainedComponent, require_beats_reference,
                          require_non_degenerate, require_population,
                          require_trained)

PASS, FAIL = [], []


def expect_raises(name, fn, must_contain=""):
    try:
        fn()
    except UntrainedComponent as e:
        if must_contain and must_contain not in str(e):
            FAIL.append((name, f"raised but message lacked {must_contain!r}: {e}"))
        else:
            PASS.append(name)
        return
    except Exception as e:
        FAIL.append((name, f"raised {type(e).__name__} not UntrainedComponent: {e}"))
        return
    FAIL.append((name, "did NOT raise"))


def ok(name, fn):
    try:
        fn()
        PASS.append(name)
    except Exception as e:
        FAIL.append((name, f"{type(e).__name__}: {e}"))


# --- E54: the collapsed VAE -------------------------------------------
ok("t1 healthy component passes",
   lambda: require_trained("healthy", 1.2e-4, 3.3e-5, max_ratio=50))
expect_raises("t2 E54 collapsed VAE raises",
              lambda: require_trained("E54 vae", 1.748e-2, 3.3e-5),
              "did not train")
expect_raises("t3 near-collapsed arm raises",
              lambda: require_trained("E52 head", 3.3e-3, 3.3e-5, max_ratio=50),
              "did not train")

# --- E54: identical values across seeds --------------------------------
ok("t4 healthy seed spread passes",
   lambda: require_non_degenerate("ok", {"0": 0.72, "1": 0.75, "2": 0.70, "3": 0.78}))
expect_raises("t5 E54 identical-per-seed raises",
              lambda: require_non_degenerate(
                  "E54 vae", {"0": 0.0174, "1": 0.0174, "2": 0.0174, "3": 0.0174}),
              "collapsed, not converged")
expect_raises("t6 near-identical per-seed raises",
              lambda: require_non_degenerate(
                  "E55 vae", {"0": 0.9509, "1": 0.9509, "2": 0.9510, "3": 0.9508}),
              "collapsed")

# --- E48: single-class / empty populations -----------------------------
ok("t7 valid population passes",
   lambda: require_population("ok", [0, 1, 0, 1, 1]))
expect_raises("t8 E48 empty positive set raises",
              lambda: require_population("E48 Botnet", [0] * 50),
              "single-class")
expect_raises("t9 empty population raises",
              lambda: require_population("empty", []),
              "empty population")

# --- E52: a readout that cannot beat the trivial scorer ----------------
ok("t10 useful readout passes",
   lambda: require_beats_reference("E54 infiltration gain", 0.6333, 0.5855))
ok("t11 readout exactly equal to reference passes",
   lambda: require_beats_reference("E52 head on a tie", 0.63, 0.63))
expect_raises("t12 E52 webattacks collapse raises",
              lambda: require_beats_reference("E52 web", 0.722, 0.889),
              "not an improvement")
expect_raises("t12b E52 portscan collapse raises",
              lambda: require_beats_reference("E52 portscan", 0.51, 0.63),
              "not an improvement")
ok("t12c small regression allowed when min_ratio < 1",
   lambda: require_beats_reference("E52 tolerated", 0.885, 0.889, min_ratio=0.99))

# --- the guards must not fire on our ACTUAL shipped numbers ------------
def t_shipped_numbers_pass():
    """The real E43/E55 numbers must satisfy every guard, or it is too strict."""
    # E55: the FIXED vae is 23x worse than the AE reference, under the 50x limit
    require_trained("E55 fixed vae", 7.759e-4, 3.3e-5, max_ratio=50)
    # E43 fused: passes the population check
    require_population("Botnet", [0, 1] * 10)


ok("t13 shipped E55 numbers pass the guards", t_shipped_numbers_pass)


print(f"\n{len(PASS)} passed, {len(FAIL)} failed\n")
for n in PASS:
    print("  PASS", n)
for n, why in FAIL:
    print("  FAIL", n, "->", why)
raise SystemExit(1 if FAIL else 0)
