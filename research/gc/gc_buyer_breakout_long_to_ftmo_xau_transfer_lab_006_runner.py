#!/usr/bin/env python3
"""Technical runner for LAB006.

Only fixes pandas-3 datetime integer-resolution ambiguity in clock calibration.
Research rules, offsets, signal ledger, horizons and gates remain unchanged.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

P = Path("research/gc/gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py")
spec = importlib.util.spec_from_file_location("lab006", P)
lab = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(lab)


def calibrate_clock_fixed(amp, xau_m1):
    a = amp[["time", "ret"]].dropna().copy()
    # Timestamp.value is always nanoseconds, independent of pandas datetime dtype resolution.
    a["minute_utc_ms"] = a["time"].map(lambda t: int(pd.Timestamp(t).value // 1_000_000)).astype(np.int64)
    a = a[["minute_utc_ms", "ret"]].rename(columns={"ret": "gc_ret"})
    base = xau_m1[["minute_ms", "ret"]].dropna().copy()
    rows = []
    for off in lab.CLOCK_OFFSETS_MIN:
        z = base.copy()
        z["minute_utc_ms"] = z.minute_ms.astype(np.int64) - off * 60000
        m = a.merge(z[["minute_utc_ms", "ret"]], on="minute_utc_ms", how="inner")
        m = m.replace([np.inf, -np.inf], np.nan).dropna()
        corr = float(m.gc_ret.corr(m.ret)) if len(m) >= 100 else np.nan
        rows.append({"offset_min": off, "n_common": int(len(m)), "pearson_m1_return_corr": corr})
    out = pd.DataFrame(rows)
    valid = out.dropna(subset=["pearson_m1_return_corr"])
    if valid.empty:
        raise SystemExit("Clock calibration has no valid correlations")
    best = valid.sort_values(["pearson_m1_return_corr", "n_common"], ascending=[False, False]).iloc[0]
    return int(best.offset_min), out


lab.calibrate_clock = calibrate_clock_fixed
lab.main()
