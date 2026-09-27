"""Threshold helpers that transfer across days (fix for E13 R1).

R1: a raw-score threshold fit on Monday (p95) gives precision 0.037 on
Friday — the score scale drifts, but rank order survives (AUC 0.9998).
So never ship a frozen raw threshold. These helpers cut by within-window
rank (top-k) or a rolling percentile, both of which transfer by
construction. Batch-only, like all rank ops (gotcha #17).

    from thresholds import topk_mask, RollingPercentile
"""

from __future__ import annotations

import numpy as np


def topk_mask(scores: np.ndarray, k: int) -> np.ndarray:
    """Boolean mask for the top-k scores (ties broken by order)."""
    s = np.asarray(scores, dtype=float)
    if k <= 0:
        return np.zeros_like(s, dtype=bool)
    if k >= len(s):
        return np.ones_like(s, dtype=bool)
    cut = np.partition(s, -k)[-k]
    mask = s > cut
    need = k - int(mask.sum())
    if need > 0:  # fill ties at the cutoff deterministically
        tie = np.where(s == cut)[0][:need]
        mask[tie] = True
    return mask


class RollingPercentile:
    """Causal running threshold: percentile over recent history only.

    update() with each window's scores, then threshold() gives the cutoff.
    No future data, no frozen Monday constant — the operating point adapts
    as the score scale drifts (M6 companion).
    """

    def __init__(self, pct: float = 95.0, maxlen: int = 10000):
        self.pct = float(pct)
        self.maxlen = int(maxlen)
        self._hist: list[float] = []

    def update(self, scores: np.ndarray) -> None:
        self._hist.extend(float(v) for v in np.asarray(scores).ravel())
        if len(self._hist) > self.maxlen:
            self._hist = self._hist[-self.maxlen:]

    def threshold(self) -> float | None:
        if not self._hist:
            return None
        return float(np.percentile(self._hist, self.pct))

    def mask(self, scores: np.ndarray) -> np.ndarray | None:
        t = self.threshold()
        if t is None:
            return None
        return np.asarray(scores, dtype=float) >= t
