#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

LAB = "BTC_LONG_V1_CLOSED_BAR_TRANSPORT_PARITY_AND_FRESH_SEQUENTIAL_CONTINUATION_LAB_065"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(parents=True, exist_ok=True)

LAB063_PATH = ROOT / "labs" / "BTC_LONG_POSITIVE_LINEAGE_RECONCILIATION_AND_FROZEN_V1_LAB_063" / "run_lab.py"
SPEC = importlib.util.spec_from_file_location("lab063_frozen_lab065", LAB063_PATH)
L63 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(L63)

M1ZIP = ROOT / "btc_1m.zip"
M5ZIP = ROOT / "btc_5m.zip"
FREEZE_TS = pd.Timestamp("2026-09-10 14:28:51")
REST_START = pd.Timestamp("2026-08-08 00:00:00")
PRIMARY_BPS = 5.0
STRESS_BPS = 10.0
STOP_ATR = 1.5
TP_R = 1.5
TIME_EXIT_H = 48
LONG_SLOT_RISK_PCT = 0.50 / 6.0


def pf(v):
    x = pd.Series(v, dtype=float).dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    if gl > 0:
        return gp / gl
    return float("inf") if gp > 0 else np.nan


def max_dd(v):
    x = np.asarray(list(v), dtype=float)
    if len(x) == 0:
        return 0.0
    eq = np.r_[0.0, np.cumsum(np.nan_to_num(x, nan=0.0))]
    peaks = np.maximum.accumulate(eq)
    return float(np.max(peaks - eq))


def to_ms(ts: pd.Timestamp) -> int:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return int(t.timestamp() * 1000)


def fetch_klines(interval: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    interval_ms = {"1m": 60_000, "5m": 300_000}[interval]
    url = "https://www.binance.com/fapi/v1/klines"
    cur = to_ms(start)
    end_ms = to_ms(end)
    rows = []
    sess = requests.Session()
    while cur <= end_ms:
        params = {
            "symbol": "BTCUSDT",
            "interval": interval,
            "startTime": cur,
            "endTime": end_ms,
            "limit": 1000,
        }
        data = None
        last_err = None
        for attempt in range(5):
            try:
                r = sess.get(url, params=params, timeout=30)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as exc:
                last_err = exc
                time.sleep(1 + attempt)
        if data is None:
            raise RuntimeError(f"REST {interval} failed at {cur}: {last_err}")
        if not data:
            break
        rows.extend(data)
        nxt = int(data[-1][0]) + interval_ms
        if nxt <= cur:
            raise RuntimeError("REST pagination did not advance")
        cur = nxt
        if len(data) < 1000:
            break

    cols = ["time", "open", "high", "low", "close", "close_time"]
    if not rows:
        return pd.DataFrame(columns=cols)
    z = pd.DataFrame(
        rows,
        columns=[
            "open_ms", "open", "high", "low", "close", "volume", "close_ms",
            "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
        ],
    )
    z["time"] = pd.to_datetime(z.open_ms.astype("int64"), unit="ms", utc=True).dt.tz_localize(None)
    z["close_time"] = pd.to_datetime(z.close_ms.astype("int64"), unit="ms", utc=True).dt.tz_localize(None)
    for c in ["open", "high", "low", "close"]:
        z[c] = pd.to_numeric(z[c], errors="coerce")
    return z[cols].dropna().sort_values("time").drop_duplicates("time").reset_index(drop=True)


def split_closed_frozen(frozen: pd.DataFrame, interval: pd.Timedelta):
    z = frozen[["time", "open", "high", "low", "close"]].copy().sort_values("time").reset_index(drop=True)
    max_open = pd.Timestamp(z.time.max())
    z["provably_closed"] = (z.time + interval) <= max_open
    closed = z[z.provably_closed].drop(columns="provably_closed").copy()
    unproven = z[~z.provably_closed].drop(columns="provably_closed").copy()
    return closed, unproven, max_open


def exact_parity(frozen_closed: pd.DataFrame, rest_closed: pd.DataFrame, min_n: int) -> tuple[dict, pd.DataFrame]:
    a = frozen_closed[["time", "open", "high", "low", "close"]].copy()
    b = rest_closed[["time", "open", "high", "low", "close"]].copy()
    m = a.merge(b, on="time", suffixes=("_frozen", "_rest"), how="inner")
    if m.empty:
        return {
            "overlap_n": 0, "min_required": int(min_n), "exact_rows": 0,
            "exact_share": 0.0, "max_abs_ohlc_diff": None, "pass": False,
        }, m
    exact = np.ones(len(m), dtype=bool)
    maxdiff = 0.0
    for c in ["open", "high", "low", "close"]:
        x = m[f"{c}_frozen"].to_numpy(float)
        y = m[f"{c}_rest"].to_numpy(float)
        d = np.abs(x - y)
        exact &= (x == y)
        if len(d):
            maxdiff = max(maxdiff, float(np.nanmax(d)))
        m[f"{c}_diff"] = y - x
    m["exact"] = exact
    share = float(exact.mean())
    metrics = {
        "overlap_n": int(len(m)),
        "min_required": int(min_n),
        "exact_rows": int(exact.sum()),
        "exact_share": share,
        "max_abs_ohlc_diff": float(maxdiff),
        "pass": bool(len(m) >= min_n and share == 1.0),
    }
    return metrics, m


def terminal_diagnostic(unproven: pd.DataFrame, rest_closed: pd.DataFrame) -> pd.DataFrame:
    if unproven.empty:
        return pd.DataFrame()
    a = unproven[["time", "open", "high", "low", "close"]].copy()
    b = rest_closed[["time", "open", "high", "low", "close"]].copy()
    m = a.merge(b, on="time", suffixes=("_frozen_unproven", "_rest_closed"), how="left")
    for c in ["open", "high", "low", "close"]:
        m[f"{c}_diff_rest_minus_frozen"] = m[f"{c}_rest_closed"] - m[f"{c}_frozen_unproven"]
    return m


def merge_closed_frozen_with_rest(frozen_closed: pd.DataFrame, rest_closed: pd.DataFrame) -> pd.DataFrame:
    a = frozen_closed[["time", "open", "high", "low", "close"]].copy()
    b = rest_closed[["time", "open", "high", "low", "close"]].copy()
    a["source_rank"] = 0
    b["source_rank"] = 1
    z = pd.concat([a, b], ignore_index=True).sort_values(["time", "source_rank"])
    z = z.drop_duplicates("time", keep="first").drop(columns="source_rank").sort_values("time").reset_index(drop=True)
    return z


def replay_extended(entries: pd.DataFrame, m1: pd.DataFrame, h1: pd.DataFrame, data_end: pd.Timestamp) -> pd.DataFrame:
    if entries.empty:
        return pd.DataFrame()
    mt = m1.time.to_numpy(dtype="datetime64[ns]")
    mo = m1.open.to_numpy(float)
    mh = m1.high.to_numpy(float)
    ml = m1.low.to_numpy(float)
    hct = h1.close_time.to_numpy(dtype="datetime64[ns]")
    ha = h1.atr14.to_numpy(float)
    rows = []

    for r in entries.itertuples(index=False):
        sig = pd.Timestamp(r.signal_time)
        j = int(np.searchsorted(mt, np.datetime64(sig + pd.Timedelta(minutes=1)), side="left"))
        q = int(np.searchsorted(hct, np.datetime64(sig), side="right") - 1)
        if j >= len(m1) or q < 0 or not np.isfinite(ha[q]) or ha[q] <= 0:
            continue
        entry_time = pd.Timestamp(m1.time.iloc[j])
        entry = float(mo[j])
        atr = float(ha[q])
        D = STOP_ATR * atr
        sl = entry - D
        tp = entry + TP_R * D
        horizon = sig + pd.Timedelta(hours=TIME_EXIT_H)
        horizon_reached = bool(data_end >= horizon)
        scan_end = min(horizon, data_end + pd.Timedelta(minutes=1))
        je_scan = min(int(np.searchsorted(mt, np.datetime64(scan_end), side="left")), len(m1))

        reason = "OPEN"
        exit_time = pd.NaT
        exit_price = np.nan
        gross_r = np.nan
        for k in range(j, je_scan):
            # Frozen candidate ambiguity rule: SL first.
            if float(ml[k]) <= sl:
                reason = "SL"
                exit_time = pd.Timestamp(m1.time.iloc[k])
                exit_price = sl
                gross_r = -1.0
                break
            if float(mh[k]) >= tp:
                reason = "TP"
                exit_time = pd.Timestamp(m1.time.iloc[k])
                exit_price = tp
                gross_r = TP_R
                break

        if reason == "OPEN" and horizon_reached:
            je = int(np.searchsorted(mt, np.datetime64(horizon), side="left"))
            if je < len(m1):
                reason = "TIME"
                exit_time = pd.Timestamp(m1.time.iloc[je])
                exit_price = float(mo[je])
                gross_r = (exit_price - entry) / D

        cost5 = (PRIMARY_BPS / 10000.0) * entry / D
        cost10 = (STRESS_BPS / 10000.0) * entry / D
        row = r._asdict()
        row.update({
            "entry_time": entry_time,
            "entry_price": entry,
            "atr_h1": atr,
            "risk_dist": D,
            "sl": sl,
            "tp": tp,
            "horizon": horizon,
            "exit_time": exit_time,
            "exit_price": exit_price,
            "exit_reason": reason,
            "completed": bool(reason != "OPEN"),
            "net_r_5bps": gross_r - cost5 if np.isfinite(gross_r) else np.nan,
            "net_r_10bps": gross_r - cost10 if np.isfinite(gross_r) else np.nan,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def peak_open_risk(trades: pd.DataFrame, data_end: pd.Timestamp) -> tuple[int, float, pd.DataFrame]:
    if trades.empty:
        return 0, 0.0, pd.DataFrame(columns=["time", "open_positions", "open_initial_risk_pct"])
    events = []
    for r in trades.itertuples(index=False):
        en = pd.Timestamp(r.entry_time)
        ex = pd.Timestamp(r.exit_time) if pd.notna(r.exit_time) else data_end
        events.append((en, +1))
        events.append((ex, -1))
    events.sort(key=lambda x: (x[0], x[1]))  # exits first on ties
    n = 0
    peak = 0
    trace = []
    for t, dn in events:
        n += dn
        peak = max(peak, n)
        trace.append({"time": t, "open_positions": n, "open_initial_risk_pct": n * LONG_SLOT_RISK_PCT})
    return int(peak), float(peak * LONG_SLOT_RISK_PCT), pd.DataFrame(trace)


def summarize_fresh(trades: pd.DataFrame, data_end: pd.Timestamp) -> tuple[dict, pd.DataFrame]:
    if trades.empty:
        return {
            "signals_with_entry": 0, "completed": 0, "open": 0,
            "ev5": None, "pf5": None, "ev10": None, "pf10": None,
            "cumR5": 0.0, "tp": 0, "sl": 0, "time": 0,
            "additive_realized_dd_pct": 0.0,
            "peak_concurrent_long": 0, "peak_open_initial_risk_pct": 0.0,
        }, pd.DataFrame()

    c = trades[trades.completed].copy()
    ret = c.sort_values(["exit_time", "signal_time"]).net_r_5bps.astype(float) * LONG_SLOT_RISK_PCT if len(c) else pd.Series(dtype=float)
    peak_n, peak_risk, trace = peak_open_risk(trades, data_end)
    return {
        "signals_with_entry": int(len(trades)),
        "completed": int(len(c)),
        "open": int((~trades.completed).sum()),
        "ev5": float(c.net_r_5bps.mean()) if len(c) else None,
        "pf5": pf(c.net_r_5bps) if len(c) else None,
        "ev10": float(c.net_r_10bps.mean()) if len(c) else None,
        "pf10": pf(c.net_r_10bps) if len(c) else None,
        "cumR5": float(c.net_r_5bps.sum()) if len(c) else 0.0,
        "tp": int((c.exit_reason == "TP").sum()) if len(c) else 0,
        "sl": int((c.exit_reason == "SL").sum()) if len(c) else 0,
        "time": int((c.exit_reason == "TIME").sum()) if len(c) else 0,
        "additive_realized_dd_pct": max_dd(ret),
        "peak_concurrent_long": peak_n,
        "peak_open_initial_risk_pct": peak_risk,
    }, trace


def tail_state(clock: pd.DataFrame, episodes: pd.DataFrame) -> dict:
    if clock.empty:
        return {"clock_time": None, "state": None, "tier_a_active": False, "episode_onset": None, "next_signal_conditional": None}
    last = clock.sort_values("time").iloc[-1]
    t = pd.Timestamp(last.time)
    state = str(last.state)
    active = state == "TIER_A_BUY"
    onset = None
    next_sig = None
    if active:
        eid = int(last.clock_episode_id)
        g = clock[(clock.clock_episode_id == eid) & (clock.state == "TIER_A_BUY")].sort_values("time")
        if len(g):
            onset = pd.Timestamp(g.time.iloc[0])
            k = 0
            while onset + pd.Timedelta(hours=8 * k) <= t:
                k += 1
            next_sig = onset + pd.Timedelta(hours=8 * k)
    return {
        "clock_time": str(t),
        "state": state,
        "tier_a_active": bool(active),
        "st_dir": float(last.st_dir) if pd.notna(last.st_dir) else None,
        "st_age": float(last.st_age) if pd.notna(last.st_age) else None,
        "episode_onset": str(onset) if onset is not None else None,
        "next_signal_conditional": str(next_sig) if next_sig is not None else None,
    }


def continuity_gaps(df: pd.DataFrame, interval: pd.Timedelta) -> dict:
    if len(df) < 2:
        return {"rows": int(len(df)), "gap_count": 0, "max_gap_minutes": None}
    d = df.time.sort_values().diff().dropna()
    gaps = d[d > interval]
    return {
        "rows": int(len(df)),
        "gap_count": int(len(gaps)),
        "max_gap_minutes": float(d.max().total_seconds() / 60.0),
    }


def main():
    if not M1ZIP.exists() or not M5ZIP.exists():
        raise FileNotFoundError("btc_1m.zip and btc_5m.zip must be staged at repository root")

    run_started = pd.Timestamp.now(tz="UTC").tz_localize(None)
    # REST response can include current incomplete bars. Fetch broadly, then require close_time <= run_started.
    rest_end = run_started

    frozen_m1 = L63.BASE.load_zip(str(M1ZIP))
    frozen_m5 = L63.BASE.load_zip(str(M5ZIP))
    closed_m1, unproven_m1, max_m1_open = split_closed_frozen(frozen_m1, pd.Timedelta(minutes=1))
    closed_m5, unproven_m5, max_m5_open = split_closed_frozen(frozen_m5, pd.Timedelta(minutes=5))

    rest_m1_all = fetch_klines("1m", REST_START, rest_end)
    rest_m5_all = fetch_klines("5m", REST_START, rest_end)
    rest_m1 = rest_m1_all[rest_m1_all.close_time <= run_started].copy()
    rest_m5 = rest_m5_all[rest_m5_all.close_time <= run_started].copy()

    p1, p1_rows = exact_parity(closed_m1, rest_m1, 250)
    p5, p5_rows = exact_parity(closed_m5, rest_m5, 100)
    parity_pass = bool(p1["pass"] and p5["pass"])

    term1 = terminal_diagnostic(unproven_m1, rest_m1)
    term5 = terminal_diagnostic(unproven_m5, rest_m5)

    merged_m1 = merge_closed_frozen_with_rest(closed_m1, rest_m1)
    merged_m5 = merge_closed_frozen_with_rest(closed_m5, rest_m5)
    data_end = pd.Timestamp(merged_m1.time.max())

    clock = L63.build_clock(merged_m5)
    episodes = L63.tier_a_episodes(clock)
    scheduled = L63.schedule_entries(episodes, phase_h=0)
    scheduled = scheduled[scheduled.signal_time + pd.Timedelta(minutes=1) <= data_end].copy()
    trades = replay_extended(scheduled, merged_m1, L63.BASE.h1_atr_from_m1(merged_m1), data_end)
    fresh = trades[trades.signal_time > FREEZE_TS].copy() if len(trades) else pd.DataFrame()
    fresh_summary, risk_trace = summarize_fresh(fresh, data_end)
    tail = tail_state(clock, episodes)

    fresh_n = int(fresh_summary["completed"])
    gates = {
        "closed_m1_overlap_ge250": bool(p1["overlap_n"] >= 250),
        "closed_m1_exact_100pct": bool(p1["exact_share"] == 1.0),
        "closed_m5_overlap_ge100": bool(p5["overlap_n"] >= 100),
        "closed_m5_exact_100pct": bool(p5["exact_share"] == 1.0),
        "fresh_n_ge5": bool(fresh_n >= 5),
        "fresh_ev5_gt0_if_n5": bool(fresh_n < 5 or (fresh_summary["ev5"] is not None and fresh_summary["ev5"] > 0)),
        "fresh_pf5_ge1_10_if_n5": bool(fresh_n < 5 or (fresh_summary["pf5"] is not None and fresh_summary["pf5"] >= 1.10)),
        "fresh_ev10_gt0_if_n5": bool(fresh_n < 5 or (fresh_summary["ev10"] is not None and fresh_summary["ev10"] > 0)),
        "fresh_dd_le4pct_if_n5": bool(fresh_n < 5 or fresh_summary["additive_realized_dd_pct"] <= 4.0),
        "peak_open_long_risk_le0_50pct": bool(fresh_summary["peak_open_initial_risk_pct"] <= 0.50 + 1e-12),
        "no_tuning": True,
    }

    if not parity_pass:
        verdict = "INVALID_CLOSED_BAR_PRICE_TRANSPORT_PARITY_DO_NOT_INTERPRET_FRESH_LONG"
    elif fresh_n < 5:
        verdict = "WATCH_POSTFREEZE_TOO_EARLY__CLOSED_BAR_TRANSPORT_CERTIFIED"
    elif not all([
        gates["fresh_ev5_gt0_if_n5"], gates["fresh_pf5_ge1_10_if_n5"],
        gates["fresh_ev10_gt0_if_n5"], gates["fresh_dd_le4pct_if_n5"],
        gates["peak_open_long_risk_le0_50pct"], gates["no_tuning"],
    ]):
        verdict = "FAIL_FRESH_LONG_POSTFREEZE"
    else:
        verdict = "PASS_FRESH_LONG_POSTFREEZE__BROKER_NATIVE_PARITY_STILL_REQUIRED"

    # Persist evidence.
    p1_rows.to_csv(OUT / "closed_m1_parity_rows.csv", index=False)
    p5_rows.to_csv(OUT / "closed_m5_parity_rows.csv", index=False)
    term1.to_csv(OUT / "unproven_terminal_m1_diagnostic.csv", index=False)
    term5.to_csv(OUT / "unproven_terminal_m5_diagnostic.csv", index=False)
    episodes.to_csv(OUT / "tier_a_episodes_extended.csv", index=False)
    scheduled.to_csv(OUT / "long_scheduled_extended.csv", index=False)
    trades.to_csv(OUT / "long_all_extended.csv", index=False)
    fresh.to_csv(OUT / "long_fresh_postfreeze.csv", index=False)
    risk_trace.to_csv(OUT / "fresh_long_risk_trace.csv", index=False)

    metrics = {
        "lab": LAB,
        "run_started_utc": str(run_started),
        "long_freeze_timestamp_utc": str(FREEZE_TS),
        "elapsed_since_freeze_hours": float((run_started - FREEZE_TS).total_seconds() / 3600.0),
        "elapsed_since_freeze_days": float((run_started - FREEZE_TS).total_seconds() / 86400.0),
        "closed_bar_rule": "frozen row t eligible iff t + interval <= max_frozen_open_time; applied identically to M1/M5",
        "frozen": {
            "m1_max_open": str(max_m1_open),
            "m1_total_rows": int(len(frozen_m1)),
            "m1_provably_closed_rows": int(len(closed_m1)),
            "m1_unproven_terminal_rows": int(len(unproven_m1)),
            "m5_max_open": str(max_m5_open),
            "m5_total_rows": int(len(frozen_m5)),
            "m5_provably_closed_rows": int(len(closed_m5)),
            "m5_unproven_terminal_rows": int(len(unproven_m5)),
        },
        "rest": {
            "m1_completed_end": str(rest_m1.time.max()) if len(rest_m1) else None,
            "m5_completed_end": str(rest_m5.time.max()) if len(rest_m5) else None,
        },
        "closed_bar_price_transport_parity": {"m1": p1, "m5": p5, "pass": parity_pass},
        "merged": {
            "m1_end": str(merged_m1.time.max()),
            "m5_end": str(merged_m5.time.max()),
            "m1_continuity": continuity_gaps(merged_m1[merged_m1.time >= REST_START], pd.Timedelta(minutes=1)),
            "m5_continuity": continuity_gaps(merged_m5[merged_m5.time >= REST_START], pd.Timedelta(minutes=5)),
        },
        "current_causal_state": tail,
        "fresh_long": fresh_summary,
        "gates": gates,
        "verdict": verdict,
        "broker_native_status": "REQUIRED_BEFORE_LIVE",
        "frozen_long_v1_changed": False,
        "frozen_short_v1_changed": False,
        "live_allocation": 0,
        "no_tuning": True,
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")

    report = [
        f"# {LAB}", "", f"**Verdict:** `{verdict}`", "",
        "## Closed-bar transport", "",
        "```json", json.dumps(metrics["closed_bar_price_transport_parity"], indent=2), "```", "",
        "## Structural terminal exclusion", "",
        f"M1 frozen rows: {len(frozen_m1)} total; {len(closed_m1)} provably closed; {len(unproven_m1)} unproven terminal.",
        f"M5 frozen rows: {len(frozen_m5)} total; {len(closed_m5)} provably closed; {len(unproven_m5)} unproven terminal.", "",
        "The same structural rule was applied to both intervals before parity outcomes. No mismatch-driven row filtering is allowed.", "",
        "## True post-freeze LONG v1", "",
        f"Elapsed since freeze: {metrics['elapsed_since_freeze_hours']:.3f} h.",
        "```json", json.dumps(fresh_summary, indent=2, default=str), "```", "",
        "## Current causal state", "", "```json", json.dumps(tail, indent=2, default=str), "```", "",
        "## Gates", "", "```json", json.dumps(gates, indent=2), "```", "",
        "## Guardrail", "",
        "LAB064 remains INVALID under its original all-row parity prereg. LAB065 uses only the separately pre-registered structural closed-bar transport rule. LONG v1 and SHORT v1 are unchanged. No live allocation is authorized; broker-native parity remains required.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
