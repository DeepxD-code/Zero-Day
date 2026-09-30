"""Training-health guard: a model that did not train is not a result.

This branch produced three invalid experiments in one session, and none of them
was caught by looking at the numbers:

  E48  three of five families returned silent `nan` because label strings were
       retyped from memory -- an empty positive set scored as a number
  E52  a head trained to regress a LEVEL was used as an anomaly SCORE; it
       reported -0.167 on WebAttacks and read like a refutation
  E54  a VAE collapsed (val reconstruction 500x worse than a matched AE,
       identical to six digits across four seeds) and was about to be published
       as "we beat the VAE by 0.45"

[E46](../E46_guard_regression/)'s guards catch WRONG PAIRING -- model with the
wrong data, scaler or rank group. None of them asks the prior question: did the
component train at all? A collapsed model is perfectly paired with the right
data and the right rank group, and still yields a confident wrong number.

So this is the remaining class. Every check here is cheap, runs before results
are recorded, and fires on a component rather than on a conclusion.

    python detection/eval_guards.py            # (module, no CLI)
    python detection/train_health_selftest.py
"""

from __future__ import annotations

import warnings


class UntrainedComponent(RuntimeError):
    """Raised when a model component did not train, so its numbers mean nothing."""


def require_trained(what: str, val_metric: float, reference: float,
                    max_ratio: float = 50.0, lower_is_better: bool = True) -> None:
    """A component must be within `max_ratio` of a matched reference.

    `reference` is the val metric of a deliberately simple model fitted on the
    SAME data with the SAME budget -- the plain autoencoder's 3.3e-05 in E55.
    A component that is orders of magnitude worse has not learned the task, and
    whatever AUC it produces downstream is an artifact of its degeneracy.
    """
    if reference <= 0:
        raise ValueError(f"{what}: reference must be > 0, got {reference}")
    ratio = (val_metric / reference) if lower_is_better else (reference / val_metric)
    if ratio > max_ratio:
        raise UntrainedComponent(
            f"{what}: val metric {val_metric:.3e} is {ratio:.0f}x worse than the "
            f"matched reference {reference:.3e} (limit {max_ratio}x). This "
            "component did not train; its downstream scores are artifacts and "
            "must not be reported. E54's VAE failed exactly this way at 500x.")


def require_non_degenerate(name: str, per_seed_scores: dict,
                           min_sd: float = 1e-3) -> None:
    """Scores that barely move across seeds indicate a collapsed, not a model.

    A healthy estimator varies with its seed. E54's VAE returned an identical
    0.0174 to six digits on four seeds and per-family AUC SDs of 0.000-0.002 --
    a degenerate solution that still produced plausible-looking AUCs.
    """
    vals = [v for v in per_seed_scores.values() if v is not None]
    if len(vals) < 3:
        return
    mean = sum(vals) / len(vals)
    if mean == 0:
        spread = 0.0
    else:
        spread = (max(vals) - min(vals)) / abs(mean)
    if spread < min_sd:
        raise UntrainedComponent(
            f"{name}: values vary by only {spread:.2e} across {len(vals)} seeds "
            f"({['%.6g' % v for v in vals]}). A model that returns the same "
            "answer regardless of seed has collapsed, not converged. See E54.")


def require_population(name: str, y) -> None:
    """A score needs both classes. An empty positive set scores as `nan`.

    E48's first run produced `nan` on three of five families and it read as a
    result until printed. sklearn emits an UndefinedMetricWarning for this and
    returns nan; this turns that into a hard stop.
    """
    import numpy as np
    y = np.asarray(y)
    if y.size == 0:
        raise UntrainedComponent(f"{name}: empty population (0 rows)")
    classes = set(np.unique(y).tolist())
    if classes != {0, 1}:
        raise UntrainedComponent(
            f"{name}: population has classes {sorted(classes)}, expected "
            "{{0, 1}}. A single-class set makes ROC-AUC undefined (nan) -- the "
            "E48 failure mode. Check the label strings and the attacker-host "
            "set before trusting any score.")


def require_beats_reference(name: str, value: float, reference: float,
                            min_ratio: float = 1.0) -> None:
    """A component used as a SCORER must at least match the trivial scorer.

    `min_ratio` is the minimum acceptable value/reference; 1.0 means "at least
    as good as what it replaces". Pass a value below 1.0 to allow a small
    regression in exchange for something else (cost, latency, robustness).

    E52's head scored -0.023 to -0.167 against the fixed symmetric mean and was
    only caught by reading the table. A readout that cannot match the mean it
    replaces is either mis-specified or useless; either way it is not a result.
    """
    if value < reference * min_ratio:
        raise UntrainedComponent(
            f"{name}: {value:.4f} is below the {reference:.4f} reference it "
            f"replaces (minimum ratio {min_ratio}). A readout that cannot match "
            "the trivial scorer is not an improvement -- see E52, where the "
            "head scored a level instead of a residual.")


def check_all(*checks) -> dict:
    """Run several checks, collecting failures rather than raising on the first.

    Useful right after training, when it is better to see everything that is
    wrong with a run at once.
    """
    out = {"ok": [], "failed": []}
    for label, fn in checks:
        try:
            fn()
            out["ok"].append(label)
        except UntrainedComponent as e:
            out["failed"].append((label, str(e)))
    for label, msg in out["failed"]:
        warnings.warn(f"{label}: {msg}", RuntimeWarning, stacklevel=2)
    return out
