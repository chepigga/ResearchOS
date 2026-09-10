#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

LAB = "BTC_LONG_V1_POSTFREEZE_FRESH_SEQUENTIAL_AND_BUY_SELL_PORTFOLIO_CONFLICT_AUDIT_LAB_064"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(parents=True, exist_ok=True)

LAB063_PATH = ROOT / "labs" / "BTC_LONG_POSITIVE_LINEAGE_RECONCILIATION_AND_FROZEN_V1_LAB_063" / "run_lab.py"
SPEC = importlib.util.spec_from_file_location("lab063_frozen", LAB063_PATH)
L63 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(L63)

M1ZIP = ROOT / "btc_1m.zip"
M5ZIP = ROOT / "btc_5m.zip"
SHORT_LEDGER = ROOT / "lab055_execution_stream.csv"

FREEZE_TS = pd.Timestamp("2026-09-10 14:28:51")
TRANSFER_START = pd.Timestamp("2026-08-11 00:00:00")
TRANSFER_END = pd.Timestamp("2026-09-08 23:59:59")
REST_START = pd.Timestamp("2026-08-08 00:00:00")

STOP_ATR = 1.5
TP_R = 1.5
TIME_EXIT_H = 48
PRIMARY_BPS = 5.0
STRESS_BPS = 10.0
LONG_SLOT_RISK_PCT = 0.50 / 6.0
SHORT_RISK_PCT = 0.25


def pf(v):
    x = pd.Series(v, dtype=float).dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    return gp / gl if gl > 0 else (float("inf") if gp > 0 else np.nan)


def max_dd(v):
    x = np.asarray(list(v), dtype=float)
    if len(x) == 0:
        return 0.0
    eq = np.r_[0.0, np.cumsum(np.nan_to_num(x, nan=0.0))]
    peaks = np.maximum.accumulate(eq)
    return float(np.max(peaks - eq))


def to_ms(ts: pd.Timestamp) -> int:
    return int(pd.Timestamp(ts, tz="UTC").timestamp() * 1000) if ts.tzinfo is None else int(ts.timestamp() * 1000)


def fetch_klines(interval: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    interval_ms = {"1m": 60_000, "5m": 300_000}[interval]
    url = "https://www.binance.com/fapi/v1/klines"
    cur = to_ms(start)
    end_ms = to_ms(end)
    rows = []
    s = requests.Session()
    while cur <= end_ms:
        params = {"symbol": "BTCUSDT", "interval": interval, "startTime": cur, "endTime": end_ms, "limit": 1000}
        last_err = None
        data = None
        for attempt in range(5):
            try:
                r = s.get(url, params=params, timeout=30)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                last_err = e
                time.sleep(1 + attempt)
        if data is None:
            raise RuntimeError(f"REST {interval} failed at {cur}: {last_err}")
        if not data:
            break
        rows.extend(data)
        last_open = int(data[-1][0])
        nxt = last_open + interval_ms
        if nxt <= cur:
            raise RuntimeError("REST pagination did not advance")
        cur = nxt
        if len(data) < 1000:
            break
    if not rows:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "close_time"])
    z = pd.DataFrame(rows, columns=["open_ms", "open", "high", "low", "close", "volume", "close_ms", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"])
    z["time"] = pd.to_datetime(z.open_ms.astype("int64"), unit="ms", utc=True).dt.tz_localize(None)
    z["close_time"] = pd.to_datetime(z.close_ms.astype("int64"), unit="ms", utc=True).dt.tz_localize(None)
    for c in ["open", "high", "low", "close"]:
        z[c] = pd.to_numeric(z[c], errors="coerce")
    return z[["time", "open", "high", "low", "close", "close_time"]].dropna().sort_values("time").drop_duplicates("time").reset_index(drop=True)


def merge_prefer_frozen(frozen: pd.DataFrame, rest: pd.DataFrame) -> pd.DataFrame:
    a = frozen[["time", "open", "high", "low", "close"]].copy()
    b = rest[["time", "open", "high", "low", "close"]].copy()
    a["source_rank"] = 0
    b["source_rank"] = 1
    z = pd.concat([a, b], ignore_index=True).sort_values(["time", "source_rank"])
    z = z.drop_duplicates("time", keep="first").drop(columns="source_rank").sort_values("time").reset_index(drop=True)
    return z


def parity(frozen: pd.DataFrame, rest: pd.DataFrame, min_n: int) -> dict:
    a = frozen[["time", "open", "high", "low", "close"]].copy()
    b = rest[["time", "open", "high", "low", "close"]].copy()
    m = a.merge(b, on="time", suffixes=("_frozen", "_rest"), how="inner")
    cols = ["open", "high", "low", "close"]
    if m.empty:
        return {"overlap_n": 0, "min_required": min_n, "exact_rows": 0, "exact_share": 0.0, "max_abs_ohlc_diff": None, "pass": False}
    exact = np.ones(len(m), dtype=bool)
    diffs = []
    for c in cols:
        x = m[f"{c}_frozen"].to_numpy(float)
        y = m[f"{c}_rest"].to_numpy(float)
        exact &= x == y
        diffs.append(np.abs(x - y))
    maxdiff = float(np.nanmax(np.concatenate(diffs)))
    share = float(exact.mean())
    return {
        "overlap_n": int(len(m)),
        "min_required": int(min_n),
        "exact_rows": int(exact.sum()),
        "exact_share": share,
        "max_abs_ohlc_diff": maxdiff,
        "pass": bool(len(m) >= min_n and share == 1.0),
    }


def replay_extended(entries: pd.DataFrame, m1: pd.DataFrame, h1: pd.DataFrame, data_end: pd.Timestamp) -> pd.DataFrame:
    if entries.empty:
        return pd.DataFrame()
    mt = m1.time.to_numpy(dtype="datetime64[ns]")
    mo = m1.open.to_numpy(float); mh = m1.high.to_numpy(float); ml = m1.low.to_numpy(float)
    hct = h1.close_time.to_numpy(dtype="datetime64[ns]"); ha = h1.atr14.to_numpy(float)
    rows = []
    for r in entries.itertuples(index=False):
        sig = pd.Timestamp(r.signal_time)
        j = int(np.searchsorted(mt, np.datetime64(sig + pd.Timedelta(minutes=1)), side="left"))
        q = int(np.searchsorted(hct, np.datetime64(sig), side="right") - 1)
        if j >= len(m1) or q < 0 or not np.isfinite(ha[q]) or ha[q] <= 0:
            continue
        entry_time = pd.Timestamp(m1.time.iloc[j]); entry = float(mo[j]); atr = float(ha[q]); D = STOP_ATR * atr
        sl = entry - D; tp = entry + TP_R * D; horizon = sig + pd.Timedelta(hours=TIME_EXIT_H)
        horizon_reached = bool(data_end >= horizon)
        scan_end_time = min(horizon, data_end + pd.Timedelta(minutes=1))
        je_scan = int(np.searchsorted(mt, np.datetime64(scan_end_time), side="left"))
        je_scan = min(je_scan, len(m1))
        reason = "OPEN"; exit_time = pd.NaT; exit_price = np.nan; gross_r = np.nan
        for k in range(j, je_scan):
            # frozen conservative ambiguity: SL first
            if float(ml[k]) <= sl:
                reason = "SL"; exit_time = pd.Timestamp(m1.time.iloc[k]); exit_price = sl; gross_r = -1.0; break
            if float(mh[k]) >= tp:
                reason = "TP"; exit_time = pd.Timestamp(m1.time.iloc[k]); exit_price = tp; gross_r = TP_R; break
        if reason == "OPEN" and horizon_reached:
            je = int(np.searchsorted(mt, np.datetime64(horizon), side="left"))
            if je < len(m1):
                reason = "TIME"; exit_time = pd.Timestamp(m1.time.iloc[je]); exit_price = float(mo[je]); gross_r = (exit_price - entry) / D
        cost5 = (PRIMARY_BPS / 10000.0) * entry / D
        cost10 = (STRESS_BPS / 10000.0) * entry / D
        row = r._asdict()
        row.update({
            "entry_time": entry_time, "entry_price": entry, "risk_dist": D, "sl": sl, "tp": tp,
            "horizon": horizon, "exit_time": exit_time, "exit_price": exit_price, "exit_reason": reason,
            "completed": bool(reason != "OPEN"),
            "net_r_5bps": gross_r - cost5 if np.isfinite(gross_r) else np.nan,
            "net_r_10bps": gross_r - cost10 if np.isfinite(gross_r) else np.nan,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_window(trades: pd.DataFrame, label: str) -> dict:
    if trades.empty:
        return {"window": label, "signals_with_entry": 0, "completed": 0, "open": 0, "ev5": None, "pf5": None, "ev10": None, "pf10": None, "cumR5": 0.0, "tp": 0, "sl": 0, "time": 0, "additive_dd_pct": 0.0}
    c = trades[trades.completed].copy()
    ret_pct = (c.sort_values("exit_time").net_r_5bps * LONG_SLOT_RISK_PCT) if len(c) else pd.Series(dtype=float)
    return {
        "window": label,
        "signals_with_entry": int(len(trades)), "completed": int(len(c)), "open": int((~trades.completed).sum()),
        "ev5": float(c.net_r_5bps.mean()) if len(c) else None,
        "pf5": pf(c.net_r_5bps) if len(c) else None,
        "ev10": float(c.net_r_10bps.mean()) if len(c) else None,
        "pf10": pf(c.net_r_10bps) if len(c) else None,
        "cumR5": float(c.net_r_5bps.sum()) if len(c) else 0.0,
        "tp": int((c.exit_reason == "TP").sum()) if len(c) else 0,
        "sl": int((c.exit_reason == "SL").sum()) if len(c) else 0,
        "time": int((c.exit_reason == "TIME").sum()) if len(c) else 0,
        "additive_dd_pct": max_dd(ret_pct),
    }


def parse_short_ledger() -> pd.DataFrame:
    s = pd.read_csv(SHORT_LEDGER)
    for c in ["signal_time", "entry_time", "exit_time"]:
        s[c] = pd.to_datetime(s[c], utc=True, errors="coerce").dt.tz_localize(None)
    s["traded_bool"] = s.traded.astype(str).str.lower().eq("true")
    s["side"] = pd.to_numeric(s.side, errors="coerce")
    s["net_r_5bps"] = pd.to_numeric(s.net_r_5bps, errors="coerce")
    s["net_r_10bps"] = pd.to_numeric(s.net_r_10bps, errors="coerce")
    return s[(s.traded_bool) & (s.side == -1)].copy().sort_values("signal_time").reset_index(drop=True)


def position_end(row, data_end):
    if pd.notna(row.exit_time):
        return pd.Timestamp(row.exit_time)
    return data_end


def conflict_audit(long_trades: pd.DataFrame, shorts: pd.DataFrame, data_end: pd.Timestamp):
    direct = []
    for li, l in long_trades.reset_index(drop=True).iterrows():
        le = pd.Timestamp(l.entry_time); lx = position_end(l, data_end)
        for si, s in shorts.reset_index(drop=True).iterrows():
            se = pd.Timestamp(s.entry_time); sx = pd.Timestamp(s.exit_time)
            st = max(le, se); en = min(lx, sx)
            if en > st:
                direct.append({"long_i": li, "short_i": si, "long_entry": le, "short_entry": se, "overlap_start": st, "overlap_end": en, "overlap_h": (en-st).total_seconds()/3600.0})
    d = pd.DataFrame(direct)

    against = []
    for li, l in long_trades.reset_index(drop=True).iterrows():
        t = pd.Timestamp(l.entry_time)
        open_short = shorts[(shorts.entry_time < t) & (shorts.exit_time > t)]
        for si in open_short.index:
            against.append({"entry_side": "LONG", "entry_index": li, "opposite_index": int(si), "entry_time": t})
    for si, s in shorts.reset_index(drop=True).iterrows():
        t = pd.Timestamp(s.entry_time)
        mask = long_trades.apply(lambda l: pd.Timestamp(l.entry_time) < t < position_end(l, data_end), axis=1) if len(long_trades) else pd.Series(dtype=bool)
        for li in long_trades.index[mask] if len(long_trades) else []:
            against.append({"entry_side": "SHORT", "entry_index": si, "opposite_index": int(li), "entry_time": t})
    a = pd.DataFrame(against)

    near = []
    direct_pairs = set((int(x["long_i"]), int(x["short_i"])) for x in direct)
    for li, l in long_trades.reset_index(drop=True).iterrows():
        for si, s in shorts.reset_index(drop=True).iterrows():
            if (li, si) in direct_pairs:
                continue
            dh = abs((pd.Timestamp(l.entry_time) - pd.Timestamp(s.entry_time)).total_seconds()) / 3600.0
            if dh <= 12.0:
                near.append({"long_i": li, "short_i": si, "long_entry": l.entry_time, "short_entry": s.entry_time, "entry_gap_h": dh})
    n = pd.DataFrame(near)

    long_involved = set(d.long_i.astype(int)) if len(d) else set()
    short_involved = set(d.short_i.astype(int)) if len(d) else set()
    metrics = {
        "long_trades": int(len(long_trades)), "short_trades": int(len(shorts)),
        "direct_overlap_pairs": int(len(d)),
        "long_involved_direct": int(len(long_involved)),
        "short_involved_direct": int(len(short_involved)),
        "long_direct_conflict_rate": float(len(long_involved)/len(long_trades)) if len(long_trades) else 0.0,
        "short_direct_conflict_rate": float(len(short_involved)/len(shorts)) if len(shorts) else 0.0,
        "entry_against_open_rows": int(len(a)),
        "near_conflict_12h_pairs": int(len(n)),
        "total_overlap_h": float(d.overlap_h.sum()) if len(d) else 0.0,
        "max_single_overlap_h": float(d.overlap_h.max()) if len(d) else 0.0,
    }
    return metrics, d, a, n


def portfolio_risk_and_realized(long_trades: pd.DataFrame, shorts: pd.DataFrame, data_end: pd.Timestamp):
    ev = []
    for i, r in long_trades.reset_index(drop=True).iterrows():
        en = pd.Timestamp(r.entry_time); ex = position_end(r, data_end)
        ev.append((en, 1, "L", +LONG_SLOT_RISK_PCT))
        ev.append((ex, -1, "L", -LONG_SLOT_RISK_PCT))
    for i, r in shorts.reset_index(drop=True).iterrows():
        en = pd.Timestamp(r.entry_time); ex = pd.Timestamp(r.exit_time)
        ev.append((en, 1, "S", +SHORT_RISK_PCT))
        ev.append((ex, -1, "S", -SHORT_RISK_PCT))
    # exits first at identical timestamp
    ev.sort(key=lambda x: (x[0], x[1]))
    nl=ns=0; rl=rs=0.0
    peak_pos=peak_gross=0.0; peak_abs_net=0.0; peak_l=peak_s=0
    trace=[]
    for t, dn, side, dr in ev:
        if side == "L": nl += dn; rl += dr
        else: ns += dn; rs += dr
        gross = rl + rs; net = rl - rs
        peak_pos = max(peak_pos, nl+ns); peak_gross=max(peak_gross,gross); peak_abs_net=max(peak_abs_net,abs(net)); peak_l=max(peak_l,nl); peak_s=max(peak_s,ns)
        trace.append({"time":t,"long_open":nl,"short_open":ns,"gross_initial_risk_pct":gross,"directional_net_initial_risk_pct":net})

    realized=[]
    for _, r in long_trades[long_trades.completed].iterrows():
        realized.append({"exit_time":pd.Timestamp(r.exit_time),"side":"LONG","r":float(r.net_r_5bps),"risk_pct":LONG_SLOT_RISK_PCT,"return_pct":float(r.net_r_5bps)*LONG_SLOT_RISK_PCT})
    for _, r in shorts.iterrows():
        realized.append({"exit_time":pd.Timestamp(r.exit_time),"side":"SHORT","r":float(r.net_r_5bps),"risk_pct":SHORT_RISK_PCT,"return_pct":float(r.net_r_5bps)*SHORT_RISK_PCT})
    re = pd.DataFrame(realized).sort_values("exit_time") if realized else pd.DataFrame(columns=["exit_time","side","r","risk_pct","return_pct"])
    dd = max_dd(re.return_pct) if len(re) else 0.0
    total = float(re.return_pct.sum()) if len(re) else 0.0
    metrics = {
        "peak_long_positions": int(peak_l), "peak_short_positions": int(peak_s), "peak_total_positions": int(peak_pos),
        "peak_gross_initial_risk_pct": float(peak_gross), "peak_abs_directional_net_initial_risk_pct": float(peak_abs_net),
        "additive_realized_return_pct_5bps": total, "additive_realized_dd_pct_5bps": float(dd),
    }
    return metrics, pd.DataFrame(trace), re


def main():
    if not M1ZIP.exists() or not M5ZIP.exists() or not SHORT_LEDGER.exists():
        raise FileNotFoundError("btc_1m.zip, btc_5m.zip and lab055_execution_stream.csv must be staged")

    run_started = pd.Timestamp.now(tz="UTC").tz_localize(None)
    # Avoid partially formed bars: fetch through two minutes behind now; each interval is later filtered by close_time.
    rest_end = run_started - pd.Timedelta(minutes=2)
    frozen_m1 = L63.BASE.load_zip(str(M1ZIP))
    frozen_m5 = L63.BASE.load_zip(str(M5ZIP))
    rest_m1 = fetch_klines("1m", REST_START, rest_end)
    rest_m5 = fetch_klines("5m", REST_START, rest_end)
    # completed REST bars only
    rest_m1 = rest_m1[rest_m1.close_time <= run_started].copy()
    rest_m5 = rest_m5[rest_m5.close_time <= run_started].copy()

    p1 = parity(frozen_m1, rest_m1, 250)
    p5 = parity(frozen_m5, rest_m5, 100)
    price_parity_pass = bool(p1["pass"] and p5["pass"])

    merged_m1 = merge_prefer_frozen(frozen_m1, rest_m1)
    merged_m5 = merge_prefer_frozen(frozen_m5, rest_m5)
    data_end = pd.Timestamp(merged_m1.time.max())

    clock = L63.build_clock(merged_m5)
    episodes = L63.tier_a_episodes(clock)
    scheduled = L63.schedule_entries(episodes, phase_h=0)
    # Only signals for which the target entry minute is already available.
    scheduled = scheduled[scheduled.signal_time + pd.Timedelta(minutes=1) <= data_end].copy()
    all_trades = replay_extended(scheduled, merged_m1, L63.BASE.h1_atr_from_m1(merged_m1), data_end)

    transfer = all_trades[(all_trades.signal_time >= TRANSFER_START) & (all_trades.signal_time <= TRANSFER_END)].copy()
    fresh = all_trades[all_trades.signal_time > FREEZE_TS].copy()
    transfer_summary = summarize_window(transfer, "LOCKED_TRANSFER_CONFLICT")
    fresh_summary = summarize_window(fresh, "FRESH_POSTFREEZE_LONG")

    shorts_all = parse_short_ledger()
    shorts = shorts_all[(shorts_all.signal_time >= TRANSFER_START) & (shorts_all.signal_time <= TRANSFER_END)].copy().reset_index(drop=True)

    conflict_metrics, direct, against, near = conflict_audit(transfer, shorts, data_end)
    portfolio_metrics, risk_trace, realized = portfolio_risk_and_realized(transfer, shorts, data_end)

    fresh_n = int(fresh_summary["completed"])
    fresh_gates = {
        "n_ge5": bool(fresh_n >= 5),
        "ev5_gt0_if_n5": bool(fresh_n < 5 or (fresh_summary["ev5"] is not None and fresh_summary["ev5"] > 0)),
        "pf5_ge1_10_if_n5": bool(fresh_n < 5 or (fresh_summary["pf5"] is not None and fresh_summary["pf5"] >= 1.10)),
        "ev10_gt0_if_n5": bool(fresh_n < 5 or (fresh_summary["ev10"] is not None and fresh_summary["ev10"] > 0)),
        "dd_le4_if_n5": bool(fresh_n < 5 or fresh_summary["additive_dd_pct"] <= 4.0),
    }
    portfolio_gates = {
        "peak_gross_initial_risk_le1pct": bool(portfolio_metrics["peak_gross_initial_risk_pct"] <= 1.0 + 1e-12),
        "additive_realized_dd_le4pct": bool(portfolio_metrics["additive_realized_dd_pct_5bps"] <= 4.0 + 1e-12),
    }

    canonical_short_fresh_available = bool((shorts_all.signal_time > FREEZE_TS).any())
    if not price_parity_pass:
        verdict = "INVALID_PRICE_TRANSPORT_PARITY_DO_NOT_INTERPRET_FRESH_LONG"
    elif fresh_n < 5:
        verdict = "WATCH_POSTFREEZE_TOO_EARLY__LOCKED_TRANSFER_CONFLICT_AUDIT_COMPLETE"
    elif not all(v for k,v in fresh_gates.items() if k != "n_ge5"):
        verdict = "FAIL_FRESH_LONG_POSTFREEZE"
    elif not canonical_short_fresh_available:
        verdict = "PASS_FRESH_LONG__WATCH_COMBINED_PORTFOLIO_CANONICAL_SHORT_UNAVAILABLE"
    else:
        verdict = "PASS_FRESH_LONG_AND_CANONICAL_PORTFOLIO_AUDIT"

    # Save ledgers before metrics/report.
    episodes.to_csv(OUT / "tier_a_episodes_extended.csv", index=False)
    scheduled.to_csv(OUT / "long_scheduled_extended.csv", index=False)
    all_trades.to_csv(OUT / "long_all_extended.csv", index=False)
    transfer.to_csv(OUT / "long_locked_transfer.csv", index=False)
    fresh.to_csv(OUT / "long_fresh_postfreeze.csv", index=False)
    shorts.to_csv(OUT / "short_canonical_transfer.csv", index=False)
    direct.to_csv(OUT / "direct_overlap_pairs.csv", index=False)
    against.to_csv(OUT / "entry_against_open.csv", index=False)
    near.to_csv(OUT / "near_conflict_12h.csv", index=False)
    risk_trace.to_csv(OUT / "portfolio_risk_trace.csv", index=False)
    realized.to_csv(OUT / "portfolio_realized_ledger.csv", index=False)

    metrics = {
        "lab": LAB,
        "run_started_utc": str(run_started),
        "long_freeze_timestamp_utc": str(FREEZE_TS),
        "hours_since_long_freeze_at_run": float((run_started-FREEZE_TS).total_seconds()/3600.0),
        "windows": {"fresh_postfreeze_start_exclusive": str(FREEZE_TS), "locked_transfer_start": str(TRANSFER_START), "locked_transfer_end": str(TRANSFER_END)},
        "data": {
            "frozen_m1_end": str(frozen_m1.time.max()), "frozen_m5_end": str(frozen_m5.time.max()),
            "rest_m1_end": str(rest_m1.time.max()) if len(rest_m1) else None, "rest_m5_end": str(rest_m5.time.max()) if len(rest_m5) else None,
            "merged_m1_end": str(merged_m1.time.max()), "merged_m5_end": str(merged_m5.time.max()),
        },
        "price_transport_parity": {"m1": p1, "m5": p5, "pass": price_parity_pass},
        "fresh_long": fresh_summary,
        "fresh_long_gates": fresh_gates,
        "canonical_short_fresh_available_after_long_freeze": canonical_short_fresh_available,
        "canonical_short_fresh_status": "AVAILABLE" if canonical_short_fresh_available else "UNAVAILABLE_CANONICAL_SHORT_TAIL",
        "locked_transfer_long": transfer_summary,
        "locked_transfer_short_trades": int(len(shorts)),
        "conflicts": conflict_metrics,
        "portfolio": portfolio_metrics,
        "portfolio_gates": portfolio_gates,
        "verdict": verdict,
        "frozen_long_v1_changed": False,
        "frozen_short_v1_changed": False,
        "live_allocation": 0,
        "no_tuning": True,
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")

    report = [
        f"# {LAB}", "", f"**Verdict:** `{verdict}`", "",
        "## Methodological status", "",
        f"LONG v1 freeze: {FREEZE_TS} UTC. True fresh elapsed at run: {metrics['hours_since_long_freeze_at_run']:.3f} h.",
        "August through 8 September is LOCKED_TRANSFER only and is not eligible for LONG promotion.", "",
        "## Price transport parity", "", "```json", json.dumps(metrics["price_transport_parity"], indent=2), "```", "",
        "## True fresh LONG", "", "```json", json.dumps(fresh_summary, indent=2, default=str), "```", "",
        "## Locked transfer LONG", "", "```json", json.dumps(transfer_summary, indent=2, default=str), "```", "",
        "## Canonical SHORT same-calendar", "", f"Canonical traded SHORT rows: {len(shorts)}", "",
        "## Conflict audit", "", "```json", json.dumps(conflict_metrics, indent=2), "```", "",
        "## Portfolio risk / additive realized accounting", "", "```json", json.dumps(portfolio_metrics, indent=2), "```", "",
        "## Guardrail", "",
        "No conflict policy was selected from outcomes. No LONG or SHORT rule changed. Fresh combined portfolio closure remains unavailable unless a canonical SHORT clock exists after the LONG freeze. Live allocation remains zero.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
