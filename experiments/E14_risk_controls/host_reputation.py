"""Causal host-reputation tracker (deploy arm of E13 R3).

R3 verification: whole-day-mean fusion scores 443-cond 1.0, and the
causal running-mean scores 0.9997 — reputation works live with no
hindsight. This module is that running mean, keyed by host, with
optional 300s/60s dual-window fusion weights.

    rep = HostReputation()
    rep.update(window_host_scores_60s, window_host_scores_300s)
    edge_score = rep.edge(src, dst)   # fused reputation for one conversation
"""

from __future__ import annotations


class HostReputation:
    """Running per-host anomaly reputation (causal: history only)."""

    def __init__(self, w60: float = 0.5, w300: float = 0.5):
        self.w60 = float(w60)
        self.w300 = float(w300)
        self._sum: dict[str, float] = {}
        self._n: dict[str, int] = {}

    def update(self, scores60: dict[str, float],
               scores300: dict[str, float] | None = None) -> None:
        for h, s in scores60.items():
            fused = self.w60 * float(s)
            if scores300 is not None and h in scores300:
                fused += self.w300 * float(scores300[h])
            elif scores300 is None:
                fused = float(s)
            else:  # host absent from 300s view: keep 60s contribution only
                pass
            self._sum[h] = self._sum.get(h, 0.0) + fused
            self._n[h] = self._n.get(h, 0) + 1

    def host(self, h: str) -> float:
        n = self._n.get(h, 0)
        return self._sum.get(h, 0.0) / n if n else 0.0

    def edge(self, src: str, dst: str) -> float:
        return (self.host(src) + self.host(dst)) / 2.0
