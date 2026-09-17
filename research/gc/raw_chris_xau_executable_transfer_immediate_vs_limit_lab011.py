#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import importlib.util

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
EVENTS = ROOT / "GC_SHORT_CHRIS_AEIF_BUY_FAILURE_LAB_003_EVENTS.csv"
LONG_TRANSFER = ROOT / "gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py"

OUT_JSON = ROOT / "RAW_CHRIS_XAU_EXECUTABLE_TRANSFER_IMMEDIATE_VS_LIMIT_LAB011.json"
OUT_MD = ROOT / "RAW_CHRIS_XAU_EXECUTABLE_TRANSFER_IMMEDIATE_VS_LIMIT_LAB011.md"
OUT_EVENTS = ROOT / "RAW_CHRIS_XAU_EXECUTABLE_TRANSFER_IMMEDIATE_VS_LIMIT_LAB011_EVENTS.csv"

FEED = "AMP_CQG_RAW_EXCLUSIVE"
CLOCK_OFFSET_MIN = 180
STALE_MS = 5000
SL_ATR = 1.0
TP_ATR = 2.0
TIMEOUT_MIN = 30
LIMIT_OFFSET_ATR = 0.50
LIMIT_EXPIRY_MIN = 5
EXTRA_COSTS_R = (0.0, 0.05, 0.10)
BOOT_N = 20000
SEED = 20260917


def load_helper():
    spec = importlib.util.spec_from_file_location("lt", LONG_TRANSFER)
    m = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    return m


def max_dd(vals):
    if len(vals) == 0:
        return None
    c = np.cumsum(vals)
    peak = np.maximum.accumulate(np.r_[0.0, c])
    eq = np.r_[0.0, c]
    return float(np.max(peak - eq))


def max_neg_streak(vals):
    best = cur = 0
    for x in vals:
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def pf(vals):
    vals = np.asarray(vals, float)
    pos = vals[vals > 0].sum()
    neg = -vals[vals < 0].sum()
    if neg == 0:
        return float("inf") if pos > 0 else None
    return float(pos / neg)


def bootstrap(vals, n=BOOT_N):
    vals = np.asarray(vals, float)
    if len(vals) < 2:
        return {"p_ev_gt0": None, "ci95": [None, None]}
    rng = np.random.default_rng(SEED)
    means = np.empty(n)
    for i in range(n):
        means[i] = rng.choice(vals, size=len(vals), replace=True).mean()
    return {
        "p_ev_gt0": float((means > 0).mean()),
        "ci95": [float(np.quantile(means, .025)), float(np.quantile(means, .975))]
    }


def stats(df, variant):
    z = df[df["variant"].eq(variant)].sort_values("gc_entry_time").copy()
    fills = z[z["filled"]].copy()
    vals = fills["gross_r"].dropna().to_numpy(float)
    out = {
        "signals": int(len(z)),
        "filled": int(len(fills)),
        "fill_rate": float(len(fills) / len(z)) if len(z) else None,
        "gross_ev_r_fill": float(vals.mean()) if len(vals) else None,
        "gross_signal_ev_r": float(vals.sum() / len(z)) if len(z) and len(vals) else None,
        "gross_wr": float((vals > 0).mean()) if len(vals) else None,
        "gross_pf": pf(vals) if len(vals) else None,
        "gross_sum_r": float(vals.sum()) if len(vals) else None,
        "gross_maxdd_r": max_dd(vals) if len(vals) else None,
        "gross_max_negative_streak": max_neg_streak(vals) if len(vals) else None,
        "tp": int((fills["exit_reason"] == "TP").sum()),
        "sl": int((fills["exit_reason"] == "SL").sum()),
        "timeout": int((fills["exit_reason"] == "TIMEOUT").sum()),
        "bootstrap_gross": bootstrap(vals) if len(vals) else None,
        "cost_stress": {},
        "monthly": {},
    }
    for c in EXTRA_COSTS_R:
        nv = vals - c
        out["cost_stress"][f"{c:.2f}R"] = {
            "ev_r_fill": float(nv.mean()) if len(nv) else None,
            "signal_ev_r": float(nv.sum() / len(z)) if len(z) and len(nv) else None,
            "pf": pf(nv) if len(nv) else None,
            "sum_r": float(nv.sum()) if len(nv) else None,
            "maxdd_r": max_dd(nv) if len(nv) else None,
        }
    if len(fills):
        fills["month"] = pd.to_datetime(fills["gc_entry_time"], utc=True).dt.strftime("%Y-%m")
        for month, g in fills.groupby("month"):
            v = g["gross_r"].dropna().to_numpy(float)
            out["monthly"][month] = {
                "n": int(len(v)),
                "ev_r": float(v.mean()) if len(v) else None,
                "sum_r": float(v.sum()) if len(v) else None,
                "wr": float((v > 0).mean()) if len(v) else None,
            }
    return out


def first_idx(times, target):
    i = int(np.searchsorted(times, target, side="left"))
    if i >= len(times):
        return None, None
    lag = int(times[i] - target)
    if lag < 0 or lag > STALE_MS:
        return None, lag
    return i, lag


def sim_short(times, bids, asks, start_i, fill_price, atr, deadline_ms):
    if not np.isfinite(atr) or atr <= 0:
        return None
    sl = fill_price + SL_ATR * atr
    tp = fill_price - TP_ATR * atr
    end_i = int(np.searchsorted(times, deadline_ms, side="right"))
    end_i = min(end_i, len(times))
    for j in range(start_i, end_i):
        a = asks[j]
        if not np.isfinite(a):
            continue
        if a >= sl:
            gross_r = (fill_price - a) / atr
            return {"exit_reason": "SL", "exit_i": j, "exit_price": float(a), "gross_r": float(gross_r)}
        if a <= tp:
            return {"exit_reason": "TP", "exit_i": j, "exit_price": float(tp), "gross_r": float(TP_ATR)}
    j, lag = first_idx(times, deadline_ms)
    if j is None or j < start_i:
        return None
    a = asks[j]
    return {"exit_reason": "TIMEOUT", "exit_i": j, "exit_price": float(a), "gross_r": float((fill_price - a) / atr)}


def main():
    if not EVENTS.exists():
        raise SystemExit(f"Missing {EVENTS}")

    ev = pd.read_csv(EVENTS)
    ev = ev[ev["feed"].eq(FEED)].copy()
    ev["entry_time"] = pd.to_datetime(ev["entry_time"], utc=True)
    ev = ev.sort_values("entry_time").reset_index(drop=True)

    lt = load_helper()
    times, bids, asks, file_stats = lt.read_xau_ticks()
    xau_m1 = lt.build_xau_m1(times, bids, asks)
    atr_map = lt.xau_atr_lookup(xau_m1)

    rows = []

    for r in ev.itertuples(index=False):
        utc_ms = int(pd.Timestamp(r.entry_time).value // 1_000_000)
        target_ms = utc_ms + CLOCK_OFFSET_MIN * 60000
        i, lag = first_idx(times, target_ms)
        common = {
            "seed_time": pd.Timestamp(r.seed_time).isoformat(),
            "gc_entry_time": pd.Timestamp(r.entry_time).isoformat(),
            "broker_target_msc": target_ms,
            "entry_lag_ms": lag,
        }

        if i is None:
            for variant in ("IMMEDIATE", "LIMIT_050_5M"):
                rows.append({**common, "variant": variant, "filled": False, "reject_reason": "NO_INITIAL_XAU_TICK"})
            continue

        atr = float(atr_map.get(target_ms - 60000, np.nan))
        if not np.isfinite(atr) or atr <= 0:
            for variant in ("IMMEDIATE", "LIMIT_050_5M"):
                rows.append({**common, "variant": variant, "filled": False, "reject_reason": "NO_XAU_ATR"})
            continue

        ibid = float(bids[i])
        iask = float(asks[i])
        spread = iask - ibid
        deadline = target_ms + TIMEOUT_MIN * 60000

        sim = sim_short(times, bids, asks, i, ibid, atr, deadline)
        if sim is None:
            rows.append({**common, "variant": "IMMEDIATE", "filled": False, "reject_reason": "NO_TIMEOUT_TICK"})
        else:
            rows.append({
                **common, "variant": "IMMEDIATE", "filled": True, "reject_reason": "",
                "xau_atr14": atr, "initial_bid": ibid, "initial_ask": iask, "initial_spread": spread,
                "fill_msc": int(times[i]), "fill_price": ibid, "fill_delay_ms": int(times[i] - target_ms),
                "limit_price": np.nan,
                "exit_msc": int(times[sim["exit_i"]]), "exit_price": sim["exit_price"],
                "exit_reason": sim["exit_reason"], "gross_r": sim["gross_r"],
            })

        limit_price = ibid + LIMIT_OFFSET_ATR * atr
        expiry = target_ms + LIMIT_EXPIRY_MIN * 60000
        e = int(np.searchsorted(times, expiry, side="right"))
        fill_i = None
        for j in range(i, min(e, len(times))):
            if bids[j] >= limit_price:
                fill_i = j
                break
        if fill_i is None:
            rows.append({
                **common, "variant": "LIMIT_050_5M", "filled": False, "reject_reason": "LIMIT_NOT_FILLED",
                "xau_atr14": atr, "initial_bid": ibid, "initial_ask": iask, "initial_spread": spread,
                "limit_price": limit_price,
            })
        else:
            sim2 = sim_short(times, bids, asks, fill_i, limit_price, atr, deadline)
            if sim2 is None:
                rows.append({
                    **common, "variant": "LIMIT_050_5M", "filled": False, "reject_reason": "NO_TIMEOUT_TICK",
                    "xau_atr14": atr, "initial_bid": ibid, "initial_ask": iask, "initial_spread": spread,
                    "limit_price": limit_price,
                })
            else:
                rows.append({
                    **common, "variant": "LIMIT_050_5M", "filled": True, "reject_reason": "",
                    "xau_atr14": atr, "initial_bid": ibid, "initial_ask": iask, "initial_spread": spread,
                    "fill_msc": int(times[fill_i]), "fill_price": limit_price,
                    "fill_delay_ms": int(times[fill_i] - target_ms),
                    "limit_price": limit_price,
                    "exit_msc": int(times[sim2["exit_i"]]), "exit_price": sim2["exit_price"],
                    "exit_reason": sim2["exit_reason"], "gross_r": sim2["gross_r"],
                })

    out = pd.DataFrame(rows)
    out.to_csv(OUT_EVENTS, index=False)

    a = stats(out, "IMMEDIATE")
    b = stats(out, "LIMIT_050_5M")

    gates_a = {
        "signals_ge20": a["signals"] >= 20,
        "filled_ge20": a["filled"] >= 20,
        "gross_ev_pos": a["gross_ev_r_fill"] is not None and a["gross_ev_r_fill"] > 0,
        "cost_005_ev_pos": a["cost_stress"]["0.05R"]["ev_r_fill"] is not None and a["cost_stress"]["0.05R"]["ev_r_fill"] > 0,
        "gross_pf_ge110": a["gross_pf"] is not None and a["gross_pf"] >= 1.10,
        "max_neg_streak_le8": a["gross_max_negative_streak"] is not None and a["gross_max_negative_streak"] <= 8,
    }
    gates_a["pass"] = all(gates_a.values())

    gates_b = {
        "signals_ge20": b["signals"] >= 20,
        "filled_ge10": b["filled"] >= 10,
        "fill_rate_40_85pct": b["fill_rate"] is not None and .40 <= b["fill_rate"] <= .85,
        "gross_ev_fill_pos": b["gross_ev_r_fill"] is not None and b["gross_ev_r_fill"] > 0,
        "gross_signal_ev_pos": b["gross_signal_ev_r"] is not None and b["gross_signal_ev_r"] > 0,
        "cost_005_ev_fill_pos": b["cost_stress"]["0.05R"]["ev_r_fill"] is not None and b["cost_stress"]["0.05R"]["ev_r_fill"] > 0,
        "gross_pf_ge110": b["gross_pf"] is not None and b["gross_pf"] >= 1.10,
        "max_neg_streak_le8": b["gross_max_negative_streak"] is not None and b["gross_max_negative_streak"] <= 8,
    }
    gates_b["pass"] = all(gates_b.values())

    if gates_a["pass"] and gates_b["pass"]:
        status = "HISTORICAL_XAU_TRANSFER_BOTH_VARIANTS_PASS_SMALL_SAMPLE_NOT_OOS"
    elif gates_a["pass"]:
        status = "HISTORICAL_XAU_TRANSFER_IMMEDIATE_PASS_LIMIT_FAIL_SMALL_SAMPLE_NOT_OOS"
    elif gates_b["pass"]:
        status = "HISTORICAL_XAU_TRANSFER_LIMIT_PASS_IMMEDIATE_FAIL_SMALL_SAMPLE_NOT_OOS"
    else:
        status = "HISTORICAL_XAU_TRANSFER_BOTH_VARIANTS_FAIL_SMALL_SAMPLE_NOT_OOS"

    result = {
        "status": status,
        "frozen": {
            "source_feed": FEED,
            "clock_offset_min": CLOCK_OFFSET_MIN,
            "sl_atr": SL_ATR,
            "tp_atr": TP_ATR,
            "timeout_min_from_original_entry_clock": TIMEOUT_MIN,
            "limit_offset_atr": LIMIT_OFFSET_ATR,
            "limit_expiry_min": LIMIT_EXPIRY_MIN,
            "short_execution": "entry Bid/limit; exit Ask; spread embedded",
            "stop_execution": "actual Ask at first crossing; TP at target price",
            "extra_cost_stress_r": list(EXTRA_COSTS_R),
        },
        "xau_file_stats": file_stats,
        "immediate": a,
        "limit": b,
        "gates_immediate": gates_a,
        "gates_limit": gates_b,
        "notes": [
            "This Aug-Sep overlap is chronologically after the long-history LAB010 source window, but not clean independent OOS because the same market period was previously inspected in earlier Chris transfer labs.",
            "No new session, spread, score, threshold, stop, target, or timing sweep was performed in LAB011.",
            "Exact FTMO XAU commission is not hard-coded; spread is embedded and flat extra-cost stress of 0.05R and 0.10R is reported."
        ],
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    def pct(x):
        return "NA" if x is None else f"{100*x:.1f}%"
    def num(x):
        return "NA" if x is None else f"{x:+.3f}"

    lines = [
        "# RAW CHRIS XAU EXECUTABLE TRANSFER — IMMEDIATE VS LIMIT LAB011", "",
        f"**Status:** `{status}`", "",
        "Frozen transfer of LAB010 execution hypotheses to FTMO-Demo XAUUSD raw Bid/Ask ticks on the Aug-Sep 2026 GC/XAU overlap.", "",
        "## Frozen variants", "",
        "- A: immediate SHORT at XAU Bid; SL 1.0 XAU ATR; TP 2.0 XAU ATR; hard timeout 30m.",
        "- B: SELL LIMIT at initial Bid +0.50 XAU ATR; expiry 5m; same SL/TP; hard timeout remains 30m from original GC entry clock.",
        "- Clock mapping frozen at UTC+180m from prior LAB007.",
        "- SHORT exits use XAU Ask. Spread is therefore embedded.",
        "- Stop loss uses actual first Ask crossing; TP uses target price.",
        "- No new filter or parameter sweep.", "",
        "## Results", "",
        "| Variant | Signals | Fills | Fill rate | EV/fill | Signal EV | PF | WR | SumR | MaxDD | Max neg streak | TP/SL/TO |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, s in [("Immediate", a), ("Limit +0.50ATR/5m", b)]:
        lines.append(
            f"| {name} | {s['signals']} | {s['filled']} | {pct(s['fill_rate'])} | {num(s['gross_ev_r_fill'])} | {num(s['gross_signal_ev_r'])} | "
            f"{num(s['gross_pf'])} | {pct(s['gross_wr'])} | {num(s['gross_sum_r'])} | {num(s['gross_maxdd_r'])} | {s['gross_max_negative_streak']} | "
            f"{s['tp']}/{s['sl']}/{s['timeout']} |"
        )
    lines += ["", "## Extra-cost stress", "",
              "| Variant | +0.00R | +0.05R | +0.10R |",
              "|---|---:|---:|---:|"]
    for name, s in [("Immediate", a), ("Limit +0.50ATR/5m", b)]:
        lines.append(f"| {name} | {num(s['cost_stress']['0.00R']['ev_r_fill'])} | {num(s['cost_stress']['0.05R']['ev_r_fill'])} | {num(s['cost_stress']['0.10R']['ev_r_fill'])} |")
    lines += ["", "## Bootstrap", ""]
    for name, s in [("Immediate", a), ("Limit +0.50ATR/5m", b)]:
        bt = s["bootstrap_gross"]
        if bt:
            lines.append(f"- {name}: P(EV>0) = {pct(bt['p_ev_gt0'])}; 95% CI [{num(bt['ci95'][0])}, {num(bt['ci95'][1])}] R.")
    lines += ["", "## Monthly", ""]
    for name, s in [("Immediate", a), ("Limit +0.50ATR/5m", b)]:
        lines.append(f"### {name}")
        for month, m in s["monthly"].items():
            lines.append(f"- {month}: N={m['n']}, EV={num(m['ev_r'])}R, Sum={num(m['sum_r'])}R, WR={pct(m['wr'])}.")
        lines.append("")
    lines += ["## Frozen gates", "", "### Immediate"]
    for k, v in gates_a.items():
        if k != "pass":
            lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", "### Limit"]
    for k, v in gates_b.items():
        if k != "pass":
            lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", "## Decision", ""]
    if gates_a["pass"] or gates_b["pass"]:
        lines.append("At least one frozen LAB010 geometry transfers positively to executable XAU on the available overlap. Because N is small and this period is not clean untouched OOS, treat the survivor only as a Demo-shadow candidate, not production/funded authorization.")
    else:
        lines.append("Neither frozen LAB010 geometry passes the executable-XAU transfer gates on the available overlap. Do not rescue by tuning stop, target, limit depth, expiry, session, or spread filters on this same sample.")
    lines.append("")
    lines.append("Exact commission is not assumed. Spread is embedded, and +0.05R/+0.10R extra-cost stress is shown separately.")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(status)
    print(json.dumps({"immediate": a, "limit": b, "gates_immediate": gates_a, "gates_limit": gates_b}, indent=2))


if __name__ == "__main__":
    main()
