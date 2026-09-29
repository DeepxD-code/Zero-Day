"""AUC with uncertainty + small-sample guard (fix for E13 R2).

R2: 443-slice AUC 0.8935 on 5 positives has 95% CI 0.71-1.00 — the point
estimate looks precise and is not. Every eval that quotes an AUC must
ship its CI; slices with <30 positives are flagged, not headlined.

Hanley-McNeil SE (no bootstrap cost, exact enough for eval tables).
"""

from __future__ import annotations

import math


def auc_ci(auc: float | None, n_pos: int, n_neg: int) -> tuple[float, float] | None:
    """95% CI for an AUC; None when the AUC itself is None."""
    if auc is None:
        return None
    if n_pos < 2 or n_neg < 1:
        return (0.0, 1.0)
    a = min(max(float(auc), 1e-6), 1 - 1e-6)
    q1 = a / (2 - a)
    q2 = 2 * a * a / (1 + a)
    var = (a * (1 - a) + (n_pos - 1) * (q1 - a * a)
           + (n_neg - 1) * (q2 - a * a)) / (n_pos * n_neg)
    se = math.sqrt(max(var, 0.0))
    return (max(0.0, a - 1.96 * se), min(1.0, a + 1.96 * se))


def slice_verdict(n_pos: int, floor: int = 30) -> str:
    """Headline guard: slices below `floor` positives are diagnostic only."""
    if n_pos < floor:
        return (f"DIAGNOSTIC-ONLY: {n_pos} positives < {floor} — "
                "quote the pooled ALL number with its CI, not this slice.")
    return "quotable"
