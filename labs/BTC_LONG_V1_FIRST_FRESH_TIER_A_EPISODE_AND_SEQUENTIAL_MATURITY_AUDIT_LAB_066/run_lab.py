#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = "BTC_LONG_V1_FIRST_FRESH_TIER_A_EPISODE_AND_SEQUENTIAL_MATURITY_AUDIT_LAB_066"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(parents=True, exist_ok=True)

LAB065_PATH = ROOT / "labs" / "BTC_LONG_V1_CLOSED_BAR_TRANSPORT_PARITY_AND_FRESH_SEQUENTIAL_CONTINUATION_LAB_065" / "run_lab.py"
SPEC = importlib.util.spec_from_file_location("lab065_frozen_lab066", LAB065_PATH)
L65 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(L65)

M1ZIP = ROOT / "btc_1m.zip"
M5ZIP = ROOT / "btc_5m.zip"
FREEZE_TS = pd.Timestamp("2026-09-10 14:28:51")
REST_START = pd.Timestamp("2026-08-08 00:00:00")


def first_fresh_tier_a(clock: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.DataFrame]:
    z = clock.sort_values("time").copy().reset_index(drop=True)
    z["prev_state"] = z.state.shift(1)
    onset_rows = z[(z.time > FREEZE_TS) & (z.state == "TIER_A_BUY") & (z.prev_state != "TIER_A_BUY")].copy()
    onset = pd.Timestamp(onset_rows.time.iloc[0]) if len(onset_rows) else None
    return onset, onset_rows


def current_bearish_episode(clock: pd.DataFrame) -> dict:
    if clock.empty:
        return {
            "clock_time": None, "state": None, "st_dir": None, "st_age": None,
            "bearish_episode_active": False, "bearish_episode_onset": None,
            "observed_duration_h": 0.0, "bars_to_tier_a": None,
            "hours_to_tier_a_at_4h_per_bar": None,
        }
    z = clock.sort_values("time").reset_index(drop=True)
    last = z.iloc[-1]
    t = pd.Timestamp(last.time)
    st_dir = float(last.st_dir) if pd.notna(last.st_dir) else None
    st_age = float(last.st_age) if pd.notna(last.st_age) else None
    active = bool(st_dir == -1.0)
    onset = None
    duration_h = 0.0
    bars_to = None
    hours_to = None
    if active:
        i = len(z) - 1
        while i > 0 and float(z.iloc[i - 1].st_dir) == -1.0 and (pd.Timestamp(z.iloc[i].time) - pd.Timestamp(z.iloc[i - 1].time)) <= pd.Timedelta(hours=4, minutes=1):
            i -= 1
        onset = pd.Timestamp(z.iloc[i].time)
        duration_h = float((t - onset).total_seconds() / 3600.0 + 4.0)
        bars_to = int(max(0, 59 - int(st_age))) if st_age is not None else None
        hours_to = int(4 * bars_to) if bars_to is not None else None
    return {
        "clock_time": str(t),
        "state": str(last.state),
        "st_dir": st_dir,
        "st_age": st_age,
        "tier_a_active": bool(str(last.state) == "TIER_A_BUY"),
        "bearish_episode_active": active,
        "bearish_episode_onset": str(onset) if onset is not None else None,
        "observed_duration_h": duration_h,
        "bars_to_tier_a": bars_to,
        "hours_to_tier_a_at_4h_per_bar": hours_to,
        "maturity_distance_is_not_forecast": True,
    }


def next_slot_if_active(clock: pd.DataFrame, fresh_episodes: pd.DataFrame) -> str | None:
    if clock.empty or fresh_episodes.empty:
        return None
    last = clock.sort_values("time").iloc[-1]
    if str(last.state) != "TIER_A_BUY":
        return None
    t = pd.Timestamp(last.time)
    current = fresh_episodes[(fresh_episodes.start <= t) & (fresh_episodes.end > t)].copy()
    if current.empty:
        return None
    onset = pd.Timestamp(current.sort_values("start").iloc[-1].start)
    k = 0
    while onset + pd.Timedelta(hours=8 * k) <= t:
        k += 1
    return str(onset + pd.Timedelta(hours=8 * k))


def main():
    if not M1ZIP.exists() or not M5ZIP.exists():
        raise FileNotFoundError("btc_1m.zip and btc_5m.zip must be staged at repository root")

    run_started = pd.Timestamp.now(tz="UTC").tz_localize(None)
    frozen_m1 = L65.L63.BASE.load_zip(str(M1ZIP))
    frozen_m5 = L65.L63.BASE.load_zip(str(M5ZIP))

    closed_m1, unproven_m1, _ = L65.split_closed_frozen(frozen_m1, pd.Timedelta(minutes=1))
    closed_m5, unproven_m5, _ = L65.split_closed_frozen(frozen_m5, pd.Timedelta(minutes=5))

    rest_m1_all = L65.fetch_klines("1m", REST_START, run_started)
    rest_m5_all = L65.fetch_klines("5m", REST_START, run_started)
    rest_m1 = rest_m1_all[rest_m1_all.close_time <= run_started].copy()
    rest_m5 = rest_m5_all[rest_m5_all.close_time <= run_started].copy()

    p1, p1_rows = L65.exact_parity(closed_m1, rest_m1, 250)
    p5, p5_rows = L65.exact_parity(closed_m5, rest_m5, 100)

    merged_m1 = L65.merge_closed_frozen_with_rest(closed_m1, rest_m1)
    merged_m5 = L65.merge_closed_frozen_with_rest(closed_m5, rest_m5)
    m1_cont = L65.continuity_gaps(merged_m1[merged_m1.time >= REST_START], pd.Timedelta(minutes=1))
    m5_cont = L65.continuity_gaps(merged_m5[merged_m5.time >= REST_START], pd.Timedelta(minutes=5))
    transport_ok = bool(p1["pass"] and p5["pass"] and m1_cont["gap_count"] == 0 and m5_cont["gap_count"] == 0)

    clock = L65.L63.build_clock(merged_m5)
    episodes = L65.L63.tier_a_episodes(clock)
    onset, onset_rows = first_fresh_tier_a(clock)
    fresh_episodes = episodes[episodes.start > FREEZE_TS].copy() if len(episodes) else pd.DataFrame(columns=episodes.columns)

    scheduled = L65.L63.schedule_entries(episodes, phase_h=0)
    data_end = pd.Timestamp(merged_m1.time.max())
    scheduled = scheduled[(scheduled.signal_time > FREEZE_TS) & (scheduled.signal_time + pd.Timedelta(minutes=1) <= data_end)].copy()
    trades = L65.replay_extended(scheduled, merged_m1, L65.L63.BASE.h1_atr_from_m1(merged_m1), data_end)
    fresh_summary, risk_trace = L65.summarize_fresh(trades, data_end)

    maturity = current_bearish_episode(clock)
    next_slot = next_slot_if_active(clock, fresh_episodes)
    first_slot = str(scheduled.signal_time.min()) if len(scheduled) else None

    completed_n = int(fresh_summary["completed"])
    gates = {
        "closed_m1_exact_100pct": bool(p1["pass"] and p1["max_abs_ohlc_diff"] == 0.0),
        "closed_m5_exact_100pct": bool(p5["pass"] and p5["max_abs_ohlc_diff"] == 0.0),
        "m1_zero_gaps": bool(m1_cont["gap_count"] == 0),
        "m5_zero_gaps": bool(m5_cont["gap_count"] == 0),
        "fresh_n_ge5": bool(completed_n >= 5),
        "fresh_ev5_gt0_if_n5": bool(completed_n < 5 or (fresh_summary["ev5"] is not None and fresh_summary["ev5"] > 0)),
        "fresh_pf5_ge1_10_if_n5": bool(completed_n < 5 or (fresh_summary["pf5"] is not None and fresh_summary["pf5"] >= 1.10)),
        "fresh_ev10_gt0_if_n5": bool(completed_n < 5 or (fresh_summary["ev10"] is not None and fresh_summary["ev10"] > 0)),
        "fresh_dd_le4pct_if_n5": bool(completed_n < 5 or fresh_summary["additive_realized_dd_pct"] <= 4.0),
        "peak_open_long_risk_le0_50pct": bool(fresh_summary["peak_open_initial_risk_pct"] <= 0.50 + 1e-12),
        "no_tuning": True,
    }

    if not transport_ok:
        verdict = "INVALID_TRANSPORT_OR_CONTINUITY_DO_NOT_INTERPRET_LONG"
    elif onset is None:
        verdict = "WATCH_WAITING_FIRST_FRESH_TIER_A_EPISODE"
    elif completed_n < 5:
        verdict = "WATCH_FIRST_FRESH_TIER_A_OBSERVED__SEQUENTIAL_N_LT5"
    elif not all([
        gates["fresh_ev5_gt0_if_n5"], gates["fresh_pf5_ge1_10_if_n5"], gates["fresh_ev10_gt0_if_n5"],
        gates["fresh_dd_le4pct_if_n5"], gates["peak_open_long_risk_le0_50pct"], gates["no_tuning"],
    ]):
        verdict = "FAIL_FRESH_LONG_POSTFREEZE"
    else:
        verdict = "PASS_FRESH_LONG_POSTFREEZE__BROKER_NATIVE_PARITY_STILL_REQUIRED"

    p1_rows.to_csv(OUT / "closed_m1_parity_rows.csv", index=False)
    p5_rows.to_csv(OUT / "closed_m5_parity_rows.csv", index=False)
    onset_rows.to_csv(OUT / "fresh_tier_a_onset_rows.csv", index=False)
    fresh_episodes.to_csv(OUT / "fresh_tier_a_episodes.csv", index=False)
    scheduled.to_csv(OUT / "fresh_scheduled_slots.csv", index=False)
    trades.to_csv(OUT / "fresh_trades.csv", index=False)
    risk_trace.to_csv(OUT / "fresh_risk_trace.csv", index=False)
    clock[clock.time > FREEZE_TS].to_csv(OUT / "postfreeze_causal_clock.csv", index=False)

    metrics = {
        "lab": LAB,
        "run_started_utc": str(run_started),
        "freeze_timestamp_utc": str(FREEZE_TS),
        "elapsed_since_freeze_h": float((run_started - FREEZE_TS).total_seconds() / 3600.0),
        "transport": {
            "closed_m1": p1,
            "closed_m5": p5,
            "m1_continuity": m1_cont,
            "m5_continuity": m5_cont,
            "pass": transport_ok,
            "unproven_terminal_m1_rows": int(len(unproven_m1)),
            "unproven_terminal_m5_rows": int(len(unproven_m5)),
        },
        "first_fresh_tier_a": {
            "observed": bool(onset is not None),
            "onset": str(onset) if onset is not None else None,
            "fresh_episode_count": int(len(fresh_episodes)),
            "first_frozen_slot": first_slot,
            "next_slot_if_currently_active": next_slot,
        },
        "current_maturity": maturity,
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
        "## Transport", "", "```json", json.dumps(metrics["transport"], indent=2, default=str), "```", "",
        "## First fresh Tier-A", "", "```json", json.dumps(metrics["first_fresh_tier_a"], indent=2, default=str), "```", "",
        "## Current maturity", "", "```json", json.dumps(maturity, indent=2, default=str), "```", "",
        "## Fresh LONG", "", "```json", json.dumps(fresh_summary, indent=2, default=str), "```", "",
        "## Gates", "", "```json", json.dumps(gates, indent=2), "```", "",
        "## Guardrail", "",
        "Maturity distance is mechanical only and is not a forecast. The bearish Supertrend direction may reset before Tier-A. No LONG v1 rule changed; no live allocation is authorized.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
