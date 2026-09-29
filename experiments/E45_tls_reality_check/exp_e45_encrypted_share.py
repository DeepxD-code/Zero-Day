"""
E45: how much of our testbed is actually encrypted?

Item 5 asked for a confirmed-TLS testbed (ISCX VPN-nonVPN, USTC-TFC2016,
CSTNET-TLS1.3). Before downloading one, measure what the existing data
actually contains, because E11/E13's "encryption" results are all port-443
proxies and it matters whether that proxy has anything behind it.

Result to compare against: if the fraction of confirmed-encrypted traffic is
near zero, then the E13 claim ("we work on encrypted traffic") is carried
entirely by the static feature audit plus a small proxy slice, and the report
must say exactly that rather than implying a TLS evaluation happened.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "detection"))

from graph_builder import normalize_columns, read_flows

ORIG = ROOT / "data" / "GeneratedLabelledFlows" / "TrafficLabelling"
CLEAN = ROOT / "data" / "CICIDS2017_improved"
OUT = Path(__file__).resolve().parent / "exp_e45_encrypted_share.json"
ENCRYPTED_PORTS = {443, 8443, 993, 995, 465, 636, 5061, 5222, 5223}


def profile(name, df):
    port = pd.to_numeric(df["dst_port"], errors="coerce")
    enc = port.isin(ENCRYPTED_PORTS)
    n = len(df)
    atk = df["label"].astype(str).str.strip().str.upper() != "BENIGN"
    atk = atk & ~df["label"].astype(str).str.endswith("- Attempted")
    return {
        "flows": int(n),
        "encrypted_pct": round(float(enc.mean()) * 100, 3),
        "encrypted_attack_flows": int((enc & atk).sum()),
        "attack_flows": int(atk.sum()),
        "encrypted_attack_pct": (round(float((enc & atk).sum()
                                              / max(int(atk.sum()), 1)) * 100, 3)),
        "top_dst_ports": {int(k): int(v) for k, v in
                          port.value_counts().head(8).items()},
    }


def main():
    res = {}
    for day in ["Monday-WorkingHours", "Tuesday-WorkingHours",
                "Wednesday-workingHours",
                "Thursday-WorkingHours-Morning-WebAttacks",
                "Thursday-WorkingHours-Afternoon-Infilteration",
                "Friday-WorkingHours-Morning",
                "Friday-WorkingHours-Afternoon-PortScan",
                "Friday-WorkingHours-Afternoon-DDos"]:
        df = normalize_columns(read_flows(ORIG / f"{day}.pcap_ISCX.csv"))
        res[f"orig/{day}"] = profile(day, df)
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
        df = normalize_columns(pd.read_csv(CLEAN / f"{day}.csv", low_memory=True))
        res[f"clean/{day}"] = profile(day, df)

    tot = sum(r["flows"] for r in res.values())
    enc = sum(r["encrypted_pct"] / 100 * r["flows"] for r in res.values())
    atk = sum(r["attack_flows"] for r in res.values())
    enc_atk = sum(r["encrypted_attack_flows"] for r in res.values())
    res["TOTAL"] = {
        "flows": int(tot),
        "encrypted_pct": round(enc / max(tot, 1) * 100, 3),
        "attack_flows": int(atk),
        "encrypted_attack_flows": int(enc_atk),
        "encrypted_attack_pct": round(enc_atk / max(atk, 1) * 100, 4),
    }
    print(json.dumps(res["TOTAL"], indent=1))
    print()
    for k, v in res.items():
        if k == "TOTAL":
            continue
        print("%-52s enc %6.2f%%  enc-atk %5.2f%%  top %s"
              % (k, v["encrypted_pct"], v["encrypted_attack_pct"],
                 list(v["top_dst_ports"])[:5]))
    OUT.write_text(json.dumps(res, indent=1))
    print(f"-> {OUT.name}")


if __name__ == "__main__":
    main()
