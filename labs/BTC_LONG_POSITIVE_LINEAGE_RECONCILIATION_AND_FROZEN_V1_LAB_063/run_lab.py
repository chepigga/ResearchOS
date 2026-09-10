#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

LAB = "BTC_LONG_POSITIVE_LINEAGE_RECONCILIATION_AND_FROZEN_V1_LAB_063"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(parents=True, exist_ok=True)

BASE_PATH = ROOT / "research" / "btc_unified_lifecycle" / "u02c2_v283_market_clock_conditional.py"
SPEC = importlib.util.spec_from_file_location("u02c2_base_lab063", BASE_PATH)
BASE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BASE)

M1ZIP = ROOT / "btc_1m.zip"
M5ZIP = ROOT / "btc_5m.zip"
START = pd.Timestamp("2024-01-01")
STOP_ATR = 1.5
TP_R = 1.5
TIME_EXIT_H = 48
LEGACY_COST_USD = 27.5
PRIMARY_BPS = 5.0
STRESS_BPS = 10.0
EPISODE_BUDGET_PCT = 0.50
CADENCE_H = 8
MAX_SLOTS = math.ceil(TIME_EXIT_H / CADENCE_H)
SLOT_RISK_PCT = EPISODE_BUDGET_PCT / MAX_SLOTS


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
        return np.nan
    eq = np.r_[0.0, np.cumsum(np.nan_to_num(x, nan=0.0))]
    peaks = np.maximum.accumulate(eq)
    return float(np.max(peaks - eq))


def build_clock(m5):
    h4 = BASE.h4_supertrend(m5)
    c = h4[["time", "st_dir", "st_age", "st_dist_atr"]].copy()
    for col in ["st_dir", "st_age", "st_dist_atr"]:
        c[col] = c[col].shift(1)
    c = c.dropna(subset=["st_dir", "st_age"]).copy()
    c = c[c.time >= START].reset_index(drop=True)
    c["state"] = "OTHER"
    c.loc[(c.st_age > 58) & (c.st_dir == -1), "state"] = "TIER_A_BUY"
    prev_state = c.state.shift(1)
    prev_t = c.time.shift(1)
    new_episode = c.state.ne(prev_state) | ((c.time - prev_t) > pd.Timedelta(hours=4, minutes=1))
    c["clock_episode_id"] = new_episode.cumsum().astype(int)
    return c


def tier_a_episodes(clock):
    z = clock[clock.state == "TIER_A_BUY"].copy()
    rows = []
    for eid, g in z.groupby("clock_episode_id"):
        g = g.sort_values("time")
        start = pd.Timestamp(g.time.iloc[0])
        last = pd.Timestamp(g.time.iloc[-1])
        end = last + pd.Timedelta(hours=4)
        rows.append({
            "episode_id": int(eid),
            "start": start,
            "end": end,
            "duration_h": (end - start).total_seconds() / 3600.0,
            "n_h4_bars": int(len(g)),
            "start_year": int(start.year),
        })
    return pd.DataFrame(rows).sort_values("start").reset_index(drop=True)


def schedule_entries(episodes, phase_h=0):
    rows = []
    for e in episodes.itertuples(index=False):
        t = pd.Timestamp(e.start) + pd.Timedelta(hours=phase_h)
        ordinal = 1
        while t < pd.Timestamp(e.end):
            rows.append({
                "episode_id": int(e.episode_id),
                "episode_start": pd.Timestamp(e.start),
                "episode_end": pd.Timestamp(e.end),
                "duration_h": float(e.duration_h),
                "signal_time": t,
                "phase_h": int(phase_h),
                "ordinal": int(ordinal),
                "risk_pct": SLOT_RISK_PCT,
            })
            ordinal += 1
            t += pd.Timedelta(hours=CADENCE_H)
    return pd.DataFrame(rows)


def prepare_arrays(m1, h1):
    mt = m1.time.to_numpy(dtype="datetime64[ns]")
    mo = m1.open.to_numpy(float)
    mh = m1.high.to_numpy(float)
    ml = m1.low.to_numpy(float)
    mc = m1.close.to_numpy(float)
    hct = h1.close_time.to_numpy(dtype="datetime64[ns]")
    ha = h1.atr14.to_numpy(float)
    return mt, mo, mh, ml, mc, hct, ha


def replay(entries, m1, h1, with_tp=True):
    mt, mo, mh, ml, mc, hct, ha = prepare_arrays(m1, h1)
    rows = []
    for r in entries.itertuples(index=False):
        sig = pd.Timestamp(r.signal_time)
        et_target = sig + pd.Timedelta(minutes=1)
        j = int(np.searchsorted(mt, np.datetime64(et_target), side="left"))
        q = int(np.searchsorted(hct, np.datetime64(sig), side="right") - 1)
        if j >= len(m1) or q < 0 or not np.isfinite(ha[q]) or ha[q] <= 0:
            continue
        entry = float(mo[j])
        atr = float(ha[q])
        D = STOP_ATR * atr
        sl = entry - D
        tp = entry + TP_R * D
        tend = sig + pd.Timedelta(hours=TIME_EXIT_H)
        je = int(np.searchsorted(mt, np.datetime64(tend), side="left"))
        if je <= j or je >= len(m1):
            continue

        exit_idx = je
        exit_price = float(mo[je])
        reason = "TIME"
        # Entry M1 bar is eligible because entry is at its open. Conservative ambiguity: SL first.
        for k in range(j, je):
            hit_sl = float(ml[k]) <= sl
            hit_tp = bool(with_tp and float(mh[k]) >= tp)
            if hit_sl:
                exit_idx = k
                exit_price = sl
                reason = "SL"
                break
            if hit_tp:
                exit_idx = k
                exit_price = tp
                reason = "TP"
                break

        exit_time = pd.Timestamp(m1.time.iloc[exit_idx])
        gross_r = (exit_price - entry) / D
        legacy_cost_r = LEGACY_COST_USD / D
        cost5_r = (PRIMARY_BPS / 10000.0) * entry / D
        cost10_r = (STRESS_BPS / 10000.0) * entry / D
        hi = float(np.nanmax(mh[j:je]))
        lo = float(np.nanmin(ml[j:je]))
        row = r._asdict()
        row.update({
            "entry_time": pd.Timestamp(m1.time.iloc[j]),
            "entry": entry,
            "atr_h1": atr,
            "risk_dist": D,
            "sl": sl,
            "tp": tp if with_tp else np.nan,
            "exit_time": exit_time,
            "exit_price": exit_price,
            "exit_reason": reason,
            "gross_r": gross_r,
            "net_r_legacy": gross_r - legacy_cost_r,
            "net_r_5bps": gross_r - cost5_r,
            "net_r_10bps": gross_r - cost10_r,
            "legacy_cost_r": legacy_cost_r,
            "cost5_r": cost5_r,
            "cost10_r": cost10_r,
            "mfe_r_48h": (hi - entry) / D,
            "mae_r_48h": (lo - entry) / D,
            "year": int(sig.year),
            "with_tp": bool(with_tp),
        })
        rows.append(row)
    return pd.DataFrame(rows)


def peak_concurrent(trades):
    if trades.empty:
        return 0, 0.0
    events = []
    for r in trades.itertuples(index=False):
        events.append((pd.Timestamp(r.entry_time), +1, float(r.risk_pct)))
        events.append((pd.Timestamp(r.exit_time), -1, -float(r.risk_pct)))
    # exits first at identical timestamp
    events.sort(key=lambda x: (x[0], x[1]))
    n = 0
    risk = 0.0
    max_n = 0
    max_risk = 0.0
    for _, dn, dr in events:
        n += dn
        risk += dr
        max_n = max(max_n, n)
        max_risk = max(max_risk, risk)
    return int(max_n), float(max_risk)


def realized_dd_pct(trades, rcol="net_r_5bps"):
    if trades.empty:
        return np.nan
    x = trades.sort_values(["exit_time", "signal_time"])[rcol].astype(float) * SLOT_RISK_PCT
    return max_dd(x)


def summarize(trades, episodes, label):
    if trades.empty:
        return {"selector": label, "episodes": len(episodes), "trades": 0}
    weeks = (trades.signal_time.max() - trades.signal_time.min()).total_seconds() / (7 * 86400)
    peak_n, peak_risk = peak_concurrent(trades)
    return {
        "selector": label,
        "episodes": int(len(episodes)),
        "trades": int(len(trades)),
        "trades_per_week": float(len(trades) / weeks) if weeks > 0 else np.nan,
        "ev_legacy": float(trades.net_r_legacy.mean()),
        "pf_legacy": pf(trades.net_r_legacy),
        "ev_5bps": float(trades.net_r_5bps.mean()),
        "pf_5bps": pf(trades.net_r_5bps),
        "ev_10bps": float(trades.net_r_10bps.mean()),
        "pf_10bps": pf(trades.net_r_10bps),
        "cum_r_5bps": float(trades.net_r_5bps.sum()),
        "win_rate_5bps": float((trades.net_r_5bps > 0).mean()),
        "maxdd_r_signal_order_5bps": max_dd(trades.sort_values("signal_time").net_r_5bps),
        "realized_additive_dd_pct_slot_risk": realized_dd_pct(trades, "net_r_5bps"),
        "peak_concurrent_positions": peak_n,
        "peak_concurrent_initial_risk_pct": peak_risk,
        "slot_risk_pct": SLOT_RISK_PCT,
        "tp_n": int((trades.exit_reason == "TP").sum()),
        "sl_n": int((trades.exit_reason == "SL").sum()),
        "time_n": int((trades.exit_reason == "TIME").sum()),
        "start": str(trades.signal_time.min()),
        "end": str(trades.signal_time.max()),
    }


def yearly(trades, selector):
    rows = []
    for y, g in trades.groupby("year"):
        rows.append({
            "selector": selector,
            "year": int(y),
            "n": int(len(g)),
            "ev5": float(g.net_r_5bps.mean()),
            "pf5": pf(g.net_r_5bps),
            "cumR5": float(g.net_r_5bps.sum()),
            "ev10": float(g.net_r_10bps.mean()),
            "pf10": pf(g.net_r_10bps),
        })
    return pd.DataFrame(rows)


def baseline_parity(no_tp):
    # U02C5 published Tier-A 8h baseline: N=163, EV_R=+0.689, PF=2.18 under $27.5/BTC.
    # Use loose numeric tolerance because source release/parser details can produce small endpoint differences.
    n = int(len(no_tp))
    ev = float(no_tp.net_r_legacy.mean()) if n else np.nan
    p = pf(no_tp.net_r_legacy) if n else np.nan
    return {
        "expected_n": 163,
        "actual_n": n,
        "n_exact": bool(n == 163),
        "published_ev_legacy_approx": 0.689,
        "actual_ev_legacy": ev,
        "ev_abs_diff": abs(ev - 0.689) if np.isfinite(ev) else np.nan,
        "published_pf_legacy_approx": 2.18,
        "actual_pf_legacy": p,
        "pf_abs_diff": abs(p - 2.18) if np.isfinite(p) else np.nan,
        "technical_parity_acceptable": bool(n == 163 and abs(ev - 0.689) <= 0.03 and abs(p - 2.18) <= 0.15),
    }


def main():
    if not M1ZIP.exists() or not M5ZIP.exists():
        raise FileNotFoundError("btc_1m.zip and btc_5m.zip must be staged at repository root")

    m1 = BASE.load_zip(str(M1ZIP))
    m5 = BASE.load_zip(str(M5ZIP))
    h1 = BASE.h1_atr_from_m1(m1)
    clock = build_clock(m5)
    episodes = tier_a_episodes(clock)
    entries0 = schedule_entries(episodes, phase_h=0)
    entries4 = schedule_entries(episodes, phase_h=4)

    no_tp = replay(entries0, m1, h1, with_tp=False)
    primary = replay(entries0, m1, h1, with_tp=True)
    phase4 = replay(entries4, m1, h1, with_tp=True)

    episodes.to_csv(OUT / "tier_a_episodes.csv", index=False)
    entries0.to_csv(OUT / "scheduled_entries_primary.csv", index=False)
    primary.to_csv(OUT / "trades_primary_tp15.csv", index=False)
    phase4.to_csv(OUT / "trades_phase4_tp15.csv", index=False)
    no_tp.to_csv(OUT / "technical_u02c5_no_tp_parity.csv", index=False)

    primary_sum = summarize(primary, episodes, "BTC_LONG_V1_TIER_A_8H_TP15")
    phase4_sum = summarize(phase4, episodes, "PHASE_PLUS4_DIAGNOSTIC")
    no_tp_sum = summarize(no_tp, episodes, "U02C5_NO_TP_TECHNICAL_BASELINE")
    summary = pd.DataFrame([primary_sum, phase4_sum, no_tp_sum])
    summary.to_csv(OUT / "summary.csv", index=False)

    yr = pd.concat([
        yearly(primary, "BTC_LONG_V1_TIER_A_8H_TP15"),
        yearly(phase4, "PHASE_PLUS4_DIAGNOSTIC"),
    ], ignore_index=True)
    yr.to_csv(OUT / "yearly.csv", index=False)

    parity = baseline_parity(no_tp)

    # Static reconciliation registry: facts were known before the frozen TP translation outcome.
    lineage = pd.DataFrame([
        {
            "family": "RECENT_H4_TWO_BAR_BUY_LAB019_021",
            "status": "REJECT_LONG_V1",
            "reason": "Strong 2025H2-2026 but negative historical transfer; LAB020 onset and LAB021 mechanism gates failed",
        },
        {
            "family": "V283_TIMING_TIER_A",
            "status": "REMOVE_AS_MANDATORY_TIMING",
            "reason": "U02C4 same-state random null showed Tier-A state carries most edge; v283 timing increment not proven",
        },
        {
            "family": "B3_BUY_STATE",
            "status": "REJECT_LONG_V1",
            "reason": "U02C5 state-only periodic B3 weak, phase-sensitive and deteriorated in 2026",
        },
        {
            "family": "TIER_A_STATE_8H",
            "status": "SELECT_CORE",
            "reason": "U02C5 8h state-only: N163, EV~+0.689R, PF~2.18, positive 2024/2025/2026 and +4h phase positive",
        },
    ])
    lineage.to_csv(OUT / "lineage_reconciliation.csv", index=False)

    years_required = [2024, 2025, 2026]
    yrp = yr[yr.selector == "BTC_LONG_V1_TIER_A_8H_TP15"].set_index("year")
    positive_years = all((y in yrp.index and int(yrp.loc[y, "n"]) >= 5 and float(yrp.loc[y, "ev5"]) > 0) for y in years_required)

    gates = {
        "technical_u02c5_baseline_parity": bool(parity["technical_parity_acceptable"]),
        "primary_n_ge100": bool(primary_sum.get("trades", 0) >= 100),
        "primary_ev5_gt0": bool(primary_sum.get("ev_5bps", -999) > 0),
        "primary_pf5_ge1_30": bool(primary_sum.get("pf_5bps", 0) >= 1.30),
        "primary_ev10_gt0": bool(primary_sum.get("ev_10bps", -999) > 0),
        "primary_pf10_ge1_10": bool(primary_sum.get("pf_10bps", 0) >= 1.10),
        "all_2024_2025_2026_positive_ev5_n5": bool(positive_years),
        "realized_additive_dd_slotrisk_le4pct": bool(primary_sum.get("realized_additive_dd_pct_slot_risk", 999) <= 4.0),
        "peak_concurrent_le6": bool(primary_sum.get("peak_concurrent_positions", 999) <= 6),
        "phase4_ev5_gt0": bool(phase4_sum.get("ev_5bps", -999) > 0),
        "phase4_pf5_ge1_10": bool(phase4_sum.get("pf_5bps", 0) >= 1.10),
        "no_tuning": True,
    }

    economics_keys = [k for k in gates if k not in ("technical_u02c5_baseline_parity", "no_tuning")]
    if not gates["technical_u02c5_baseline_parity"]:
        verdict = "INVALID_IMPLEMENTATION_PARITY_DO_NOT_INTERPRET"
    elif all(gates[k] for k in economics_keys):
        verdict = "FROZEN_LONG_V1_CANDIDATE_READY_FOR_FRESH_OOS"
    else:
        verdict = "REJECT_TP15_TRANSLATION_DO_NOT_FREEZE_LONG_V1"

    metrics = {
        "lab": LAB,
        "candidate": "BTC_LONG_V1_TIER_A_8H_TP15",
        "data": {
            "m1_start": str(m1.time.min()),
            "m1_end": str(m1.time.max()),
            "m5_start": str(m5.time.min()),
            "m5_end": str(m5.time.max()),
            "tier_a_episodes": int(len(episodes)),
        },
        "freeze": {
            "supertrend": "H4 ATR10 x3; BAR_OPEN lag1",
            "state": "st_age>58 and st_dir==-1",
            "cadence_h": CADENCE_H,
            "entry": "signal_time+1m next M1 open",
            "stop_atr_h1": STOP_ATR,
            "tp_r": TP_R,
            "time_exit_h": TIME_EXIT_H,
            "same_m1_ambiguity": "SL_FIRST",
            "episode_budget_pct": EPISODE_BUDGET_PCT,
            "slot_risk_pct": SLOT_RISK_PCT,
            "max_slots": MAX_SLOTS,
        },
        "technical_baseline_parity": parity,
        "primary": primary_sum,
        "phase_plus4": phase4_sum,
        "gates": gates,
        "verdict": verdict,
        "fresh_oos_status": "NOT_AVAILABLE_IN_FROZEN_RELEASE; reused history only",
        "broker_native_status": "REQUIRED_BEFORE_LIVE",
        "frozen_short_v1_changed": False,
        "live_allocation": 0,
        "no_tuning": True,
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")

    report = [
        f"# {LAB}",
        "",
        f"**Verdict:** `{verdict}`",
        "",
        "## Reconciliation",
        "",
        lineage.to_markdown(index=False),
        "",
        "## Technical U02C5 baseline parity",
        "",
        "```json",
        json.dumps(parity, indent=2, default=str),
        "```",
        "",
        "## Frozen TP1.5 translation summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Yearly",
        "",
        yr.to_markdown(index=False),
        "",
        "## Gates",
        "",
        "```json",
        json.dumps(gates, indent=2),
        "```",
        "",
        "## Interpretation guardrail",
        "",
        "All 2024-2026 results in this LAB are reused historical/replication evidence, not fresh OOS. Passing them can freeze a candidate for future sequential OOS, but cannot authorize live trading. FTMO/broker-native parity is separately required.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
