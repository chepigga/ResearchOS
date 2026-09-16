#!/usr/bin/env python3
"""Runner/hardening layer for LAB013H.

Keeps the preregistered base audit intact, fixes timestamp-resolution portability
under pandas 3, then appends a separate diagnostic for the one-active unfilled
expiry clock. This is defect analysis, not parameter tuning.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
BASE = ROOT / "gc_xau_existing_data_full_replay_audit_lab_013h.py"
OUT_JSON = ROOT / "GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H.json"
OUT_MD = ROOT / "GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H.md"
OUT_SEM = ROOT / "GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H_ONEACTIVE_SEMANTIC.csv"


def load_base():
    spec = importlib.util.spec_from_file_location("lab013h_base", BASE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def utc_ms(series: pd.Series) -> np.ndarray:
    """Resolution-independent UTC epoch milliseconds for pandas 2/3."""
    s = pd.to_datetime(series, utc=True)
    # pandas 3 can carry datetime64[us]; normalize explicitly to ns first.
    return (s.dt.as_unit("ns").astype("int64") // 1_000_000).to_numpy(np.int64)


def patched_calibrate_clock(gc: pd.DataFrame, xau_m1: pd.DataFrame):
    a = gc[["time", "close"]].copy().sort_values("time")
    a["ret"] = a.close.pct_change()
    a.loc[a.time.diff().ne(pd.Timedelta(minutes=1)), "ret"] = np.nan
    a["minute_utc_ms"] = utc_ms(a["time"])
    a = a[["minute_utc_ms", "ret"]].dropna().rename(columns={"ret": "gc_ret"})

    base = xau_m1[["minute_ms", "ret"]].dropna().copy()
    rows = []
    for off in mod.CLOCK_OFFSETS:
        z = base.copy()
        z["minute_utc_ms"] = z.minute_ms.astype(np.int64) - int(off) * 60000
        m = a.merge(z[["minute_utc_ms", "ret"]], on="minute_utc_ms", how="inner")
        m = m.replace([np.inf, -np.inf], np.nan).dropna()
        corr = float(m.gc_ret.corr(m.ret)) if len(m) >= 100 else np.nan
        rows.append({"offset_min": int(off), "n_common": int(len(m)), "corr": corr})
    valid = [r for r in rows if np.isfinite(r["corr"])]
    if not valid:
        raise SystemExit(
            "Clock calibration has no finite overlap after explicit ns normalization; "
            f"gc_ms=[{int(a.minute_utc_ms.min()) if len(a) else None},"
            f"{int(a.minute_utc_ms.max()) if len(a) else None}] "
            f"xau_ms=[{int(base.minute_ms.min()) if len(base) else None},"
            f"{int(base.minute_ms.max()) if len(base) else None}]"
        )
    best = sorted(valid, key=lambda r: (r["corr"], r["n_common"]), reverse=True)[0]
    return int(best["offset_min"]), rows


def apply_one_active_corrected(z: pd.DataFrame, offset_min: int) -> pd.DataFrame:
    """Operationally causal one-active clock.

    For an unfilled limit, busy time starts when the order becomes actionable
    (next M1 / broker_target), not at the left edge of the signal bar.
    Filled setups remain busy until their exit, same as frozen LAB009.
    """
    q = z.sort_values("signal_time_utc").copy().reset_index(drop=True)
    q["accepted"] = False
    q["busy_skip"] = False
    busy_until_utc = -10**30
    off_ms = int(offset_min) * 60000
    for idx, r in q.iterrows():
        signal_utc = int(r.signal_utc_ms)
        if signal_utc < busy_until_utc:
            q.at[idx, "busy_skip"] = True
            continue
        q.at[idx, "accepted"] = True
        if bool(r.filled) and np.isfinite(r.exit_time_msc):
            busy_until_utc = int(r.exit_time_msc) - off_ms
        else:
            # Frozen historical execution starts at the next M1 open. The
            # broker_target is therefore signal left-edge + 1 minute + offset.
            order_start_utc = signal_utc + 60_000
            busy_until_utc = order_start_utc + int(r.expiry_min) * 60_000
    q["stress_r"] = 0.0
    valid = q.accepted & q.raw_r.notna()
    q.loc[valid, "stress_r"] = q.loc[valid, "raw_r"]
    cost = q.accepted & q.filled & q.raw_r.notna()
    q.loc[cost, "stress_r"] = q.loc[cost, "stress_r"] - mod.EXTRA_COST_R
    return q


def append_semantic_diagnostic():
    indep, _ = mod.independent_amp()
    ev = mod.independent_events(indep)
    times, bids, asks, _ = mod.read_xau_ticks()
    xau_m1 = mod.build_xau_m1(times, bids, asks)
    best_offset, _ = patched_calibrate_clock(indep, xau_m1)
    atr_map = dict(zip(xau_m1.minute_ms.astype(np.int64), xau_m1.atr14.astype(float)))
    executable = mod.make_executable_events(ev, times, bids, asks, atr_map, best_offset)

    rows = []
    detail = {}
    for expiry, label in ((1, "D1.00_E1M"), (3, "D1.00_E3M")):
        raw = mod.simulate_candidate(executable, times, bids, asks, expiry)
        frozen_q = mod.apply_one_active(raw, best_offset)
        corrected_q = apply_one_active_corrected(raw, best_offset)
        frozen_m = mod.metrics(frozen_q)
        corrected_m = mod.metrics(corrected_q)
        detail[label] = {
            "frozen_signal_left_edge_busy_clock": frozen_m,
            "corrected_order_start_busy_clock": corrected_m,
            "delta": {
                k: (corrected_m[k] - frozen_m[k])
                for k in frozen_m
                if isinstance(frozen_m[k], (int, float))
                and isinstance(corrected_m[k], (int, float))
                and frozen_m[k] is not None and corrected_m[k] is not None
            },
        }
        for mode, q in (("FROZEN_SIGNAL_LEFT_EDGE", frozen_q), ("CORRECTED_ORDER_START", corrected_q)):
            t = q[["signal_time_utc", "expiry_min", "filled", "status", "raw_r", "accepted", "busy_skip", "stress_r"]].copy()
            t["candidate"] = label
            t["busy_clock"] = mode
            rows.append(t)
    pd.concat(rows, ignore_index=True).to_csv(OUT_SEM, index=False)

    result = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    result["one_active_semantic_diagnostic"] = {
        "issue": "LAB009 unfilled busy expiry used signal-bar left edge rather than actionable order-start clock",
        "classification": "execution_semantic_defect_diagnostic_not_retuning",
        "detail": detail,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str, allow_nan=True), encoding="utf-8")

    md = OUT_MD.read_text(encoding="utf-8")
    add = [
        "",
        "## One-active clock semantic audit",
        "",
        "Frozen LAB009 released an **unfilled** setup at `signal_time + expiry`; the actionable XAU limit starts at the next M1, so the operational clock should be `order_start + expiry`. Filled setups are unchanged.",
        "",
        "| Candidate | Clock | Accepted | Fills | EV/signal | EV/fill | PF | MaxDD R | Late EV |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label in ("D1.00_E1M", "D1.00_E3M"):
        for key, name in (("frozen_signal_left_edge_busy_clock", "Frozen"), ("corrected_order_start_busy_clock", "Corrected")):
            m = detail[label][key]
            add.append(
                f"| {label} | {name} | {m['accepted_signals']} | {m['fills']} | "
                f"{m['ev_r_per_original_signal']:+.6f} | {m['ev_r_per_fill']:+.6f} | "
                f"{m['pf']:.4f} | {m['max_dd_r']:.4f} | {m['late_ev_r_per_original_signal']:+.6f} |"
            )
    add += [
        "",
        "This correction is reported separately and does not overwrite the frozen LAB009 baseline. If material, the corrected execution semantics must become the reference for subsequent robustness work.",
    ]
    OUT_MD.write_text(md.rstrip() + "\n" + "\n".join(add) + "\n", encoding="utf-8")
    return detail


mod = load_base()
mod.calibrate_clock = patched_calibrate_clock
mod.main()
semantic = append_semantic_diagnostic()
print(json.dumps({"lab013h": json.loads(OUT_JSON.read_text())["status"], "semantic": semantic}, indent=2, default=str))
