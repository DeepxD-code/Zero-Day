"""
Evasion techniques that target the RELATIONAL detector (M5b), not the per-flow one.

WHY THE EXISTING TECHNIQUES CANNOT TOUCH M5b
---------------------------------------------
`techniques.py` perturbs a 76-dimensional flow feature vector -- mimicry,
padding, slow-drip all move numbers inside one row. That is the right shape of
attack against M5a, which scores exactly that vector.

M5b never sees a flow feature vector. It sees eight per-host aggregates computed
over a time window:

    out_degree, in_degree, out_flows, in_flows,
    bytes_sent, bytes_recv, unique_dst_ports, mean_duration

None of those can be changed by editing a row's `flow_iat_std`. They change only
if the attacker changes its BEHAVIOUR -- who it talks to, how many of them, over
how long, from how many machines. So evading M5b means paying a real operational
cost, and the interesting question is how much.

Every technique here follows `ablation.py`'s fairness rule: the attacker's flows
are REAL BENIGN FLOWS sampled from the dataset with **all 76 feature values
untouched**. Only `src_ip`, `dst_ip`, `dst_port` and `timestamp` are rewritten.
That keeps M5a structurally blind by construction, so any change in detection is
attributable to structure alone and not to the attacker accidentally producing
odd-looking flows.

THE FOUR TECHNIQUES AND WHICH DESIGN DECISION EACH ATTACKS
-----------------------------------------------------------
  slow_scan          spread the sweep over more windows   -> attacks "windows are
                                                              time-based", drives
                                                              out_degree/window down
  distributed_scan   split the sweep across more source   -> attacks "nodes are
                     IPs                                     hosts" / per-host
                                                              aggregation
  cover_traffic      add normal-looking connections       -> attacks the
                     alongside the scan                      neighbourhood shape
                                                              the GNN encodes
  port_narrowing     touch fewer distinct ports per       -> attacks
                     window                                  unique_dst_ports, the
                                                              feature the CICIDS2017
                                                              PortScan eval showed
                                                              actually fires
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WINDOW_SECONDS = 60
ATTACKER = "192.168.99.66"


def _benign_pool(benign: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Sample n real benign flows, with replacement if the pool is small."""
    replace = n > len(benign)
    return benign.sample(n=n, replace=replace, random_state=seed).copy()


def _assign_windows(n_flows: int, spread_windows: int, base: pd.Timestamp,
                    window_seconds: int = WINDOW_SECONDS) -> list[pd.Timestamp]:
    """Spread n_flows evenly across `spread_windows` consecutive time windows.

    Flows are placed in the MIDDLE of each window so that rounding at the window
    boundary cannot accidentally split one window's traffic across two and make
    the evasion look better than it is.
    """
    per_window = int(np.ceil(n_flows / spread_windows))
    stamps = []
    for i in range(n_flows):
        w = i // per_window
        stamps.append(base + pd.Timedelta(seconds=w * window_seconds + window_seconds // 2))
    return stamps


def craft_scan(benign: pd.DataFrame, n_targets: int = 200, *,
               spread_windows: int = 1, n_sources: int = 1,
               n_ports: int = 3, cover_flows: int = 0,
               attacker: str = ATTACKER, base_time: pd.Timestamp | None = None,
               seed: int = 7, window_seconds: int = WINDOW_SECONDS) -> pd.DataFrame:
    """Build a port scan out of untouched benign flows, with evasion knobs.

    n_targets      how many distinct hosts the attacker sweeps in total
    spread_windows over how many consecutive windows the sweep is spread
    n_sources      how many attacker IPs share the sweep
    n_ports        how many distinct destination ports are used
    cover_flows    extra normal-looking flows the attacker sends to popular hosts
    """
    if base_time is None:
        base_time = pd.Timestamp("2017-07-03 09:00:00")

    scan = _benign_pool(benign, n_targets, seed)
    scan["dst_ip"] = [f"192.168.99.{i % 254 + 1}" for i in range(n_targets)]

    # Split the sweep across n_sources attacker machines. Host 0 keeps the
    # canonical attacker IP so the runner always has a host to look up.
    sources = [attacker] + [f"192.168.99.{200 + k}" for k in range(1, n_sources)]
    scan["src_ip"] = [sources[i % n_sources] for i in range(n_targets)]

    ports = [22, 445, 3389, 23, 139, 135, 8080, 21][:max(1, n_ports)]
    scan["dst_port"] = [ports[i % len(ports)] for i in range(n_targets)]
    scan["timestamp"] = _assign_windows(n_targets, spread_windows, base_time,
                                        window_seconds)

    if cover_flows > 0:
        # The attacker also behaves like an ordinary client: repeat traffic to a
        # handful of popular destinations. This lowers the ratio of "distinct
        # peers" to "total flows" without reducing the scan itself, which is the
        # cheapest evasion available -- it costs no scan coverage at all.
        popular = benign["dst_ip"].value_counts().head(5).index.tolist()
        if popular:
            cover = _benign_pool(benign, cover_flows, seed + 1)
            cover["src_ip"] = attacker
            cover["dst_ip"] = [popular[i % len(popular)] for i in range(cover_flows)]
            common = [80, 443, 53]
            cover["dst_port"] = [common[i % len(common)] for i in range(cover_flows)]
            cover["timestamp"] = _assign_windows(cover_flows, spread_windows,
                                                 base_time, window_seconds)
            scan = pd.concat([scan, cover], ignore_index=True)

    return scan


# ---------------------------------------------------------------------------
# Named techniques: each sweeps exactly ONE knob so the result is attributable.
# Each returns (label, list_of_(param_value, attacker_flows)).
# ---------------------------------------------------------------------------

def slow_scan(benign, n_targets=200, spreads=(1, 2, 5, 10, 20, 50), **kw):
    """Spread the same sweep over progressively more time windows."""
    return "slow_scan", [
        (s, craft_scan(benign, n_targets, spread_windows=s, **kw)) for s in spreads
    ]


def distributed_scan(benign, n_targets=200, sources=(1, 2, 4, 8, 16, 32), **kw):
    """Split the same sweep across progressively more attacker machines."""
    return "distributed_scan", [
        (n, craft_scan(benign, n_targets, n_sources=n, **kw)) for n in sources
    ]


def cover_traffic(benign, n_targets=200, covers=(0, 50, 200, 500, 1000, 2000), **kw):
    """Add progressively more normal-looking traffic alongside the scan."""
    return "cover_traffic", [
        (c, craft_scan(benign, n_targets, cover_flows=c, **kw)) for c in covers
    ]


def port_narrowing(benign, n_targets=200, ports=(8, 4, 3, 2, 1), **kw):
    """Use progressively fewer distinct destination ports."""
    return "port_narrowing", [
        (p, craft_scan(benign, n_targets, n_ports=p, **kw)) for p in ports
    ]


ALL_TECHNIQUES = (slow_scan, distributed_scan, cover_traffic, port_narrowing)


# ---------------------------------------------------------------------------
# P02 structural injections (ADDED 2026-09-20, B drifting into D's vertical —
# Avinash to review). Venturi et al. 2403.11830: GNN-NIDS shrug off feature
# attacks but fall to structural ones — a single injected benign edge (C2x_B)
# or an injected node rewires the victim's neighbourhood aggregation.
# Same fairness rule: injected flows are untouched real benign flows; only
# src_ip/dst_ip/timestamp are rewritten. Operates on the ATTACK-DAY df
# itself (not a standalone craft) so windows/neighbours stay realistic.
# ---------------------------------------------------------------------------

def edge_injection(day_df, attacker: str = ATTACKER, n_inject: int = 1,
                   seed: int = 0) -> pd.DataFrame:
    """Attacker -> k most-popular benign hosts (C2x_B single-edge primitive).

    Dilutes the attacker's one-to-many scan shape with legitimate-looking
    client edges. Costs the attacker nothing but k flows — the "free" evasion
    the harness must price.
    """
    rng = np.random.default_rng(seed)
    benign = day_df[day_df["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    popular = benign["dst_ip"].value_counts().head(20).index.tolist()
    inj = _benign_pool(benign, n_inject, seed)
    inj["src_ip"] = attacker
    inj["dst_ip"] = [popular[i % len(popular)] for i in range(n_inject)]
    ts = pd.to_datetime(day_df["timestamp"])
    lo, hi = ts.min(), ts.max()
    span = (hi - lo).total_seconds()
    inj["timestamp"] = [lo + pd.Timedelta(seconds=float(rng.uniform(0, span)))
                        for _ in range(n_inject)]
    return pd.concat([day_df, inj], ignore_index=True)


def node_injection(day_df, attacker: str = ATTACKER, n_nodes: int = 1,
                   flows_per_node: int = 20, seed: int = 0) -> pd.DataFrame:
    """Inject k brand-new benign-looking hosts; attacker links to each once.

    Fresh IPs have no history, so their neighbourhood is whatever the attacker
    shapes: normal client edges to popular hosts plus one attacker edge each.
    Perturbs SAGE neighbourhood aggregation around the attacker (P02 add-node).
    Returns day_df + injected flows. Fresh-node IPs are 192.168.99.210+k.
    """
    rng = np.random.default_rng(seed)
    benign = day_df[day_df["label"].astype(str).str.strip().str.upper() == "BENIGN"]
    popular = benign["dst_ip"].value_counts().head(20).index.tolist()
    ts = pd.to_datetime(day_df["timestamp"])
    lo, hi = ts.min(), ts.max()
    span = (hi - lo).total_seconds()
    parts = [day_df]
    fresh = [f"192.168.99.{210 + k}" for k in range(n_nodes)]
    for k, fip in enumerate(fresh):
        cover = _benign_pool(benign, flows_per_node, seed + 100 + k)
        cover["src_ip"] = fip
        cover["dst_ip"] = [popular[i % len(popular)] for i in range(flows_per_node)]
        link = _benign_pool(benign, 1, seed + 200 + k)
        link["src_ip"] = attacker
        link["dst_ip"] = fip
        both = pd.concat([cover, link], ignore_index=True)
        both["timestamp"] = [lo + pd.Timedelta(seconds=float(rng.uniform(0, span)))
                             for _ in range(len(both))]
        parts.append(both)
    return pd.concat(parts, ignore_index=True)


P02_TECHNIQUES = (edge_injection, node_injection)


# ---------------------------------------------------------------------------
# U1 slow-drip timing (ADDED 2026-09-20, B drifting into D's vertical —
# Avinash to review). V4 verification: TANTRA/TEGA-style timing-only evasion
# (same endpoints, reshaped timing) is the one published >70%-kill class never
# tested against M5b. It passes through structure untouched and lands on the
# load-bearing 60s-window assumption. Operates on the ATTACK-DAY df itself:
# only attacker timestamps are rewritten; endpoints, counts, features intact.
# ---------------------------------------------------------------------------

def spread_dilate(day_df, attacker: str = ATTACKER, factor: float = 2.0,
                  seed: int = 0) -> pd.DataFrame:
    """Stretch attacker timeline by `factor` (dilutes per-window degree at
    zero extra-edge cost). t' = t0 + (t - t0) * factor; windows extend past
    the day end, which is exactly the attacker's cost (time)."""
    df = day_df.copy()
    m = df["src_ip"] == attacker
    ts = pd.to_datetime(df.loc[m, "timestamp"])
    t0 = ts.min()
    df.loc[m, "timestamp"] = (t0 + (ts - t0) * factor).dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def burst_shape(day_df, attacker: str = ATTACKER, mode: str = "front",
                window_seconds: int = WINDOW_SECONDS) -> pd.DataFrame:
    """Reshape INTRA-window attacker timing: front-load (first 5s), back-load
    (last 5s), or even spacing. Same windows, same endpoints — tests IAT and
    window-boundary sensitivity only. mode in {front, back, even}."""
    df = day_df.copy()
    ts = pd.to_datetime(df["timestamp"])
    win = (ts - ts.min()).dt.total_seconds() // window_seconds
    out = df["timestamp"].copy()
    for w in sorted(win.unique()):
        idx = df.index[(win == w) & (df["src_ip"] == attacker)]
        if len(idx) == 0:
            continue
        base = ts.min() + pd.Timedelta(seconds=float(w * window_seconds))
        n = len(idx)
        if mode == "front":
            offs = np.linspace(0, 5, n)
        elif mode == "back":
            offs = np.linspace(window_seconds - 5, window_seconds - 1, n)
        else:
            offs = np.linspace(0, window_seconds - 1, n)
        out.loc[idx] = [(base + pd.Timedelta(seconds=float(o))).strftime("%Y-%m-%d %H:%M:%S")
                        for o in offs]
    df["timestamp"] = out
    return df


U1_TECHNIQUES = (spread_dilate, burst_shape)
