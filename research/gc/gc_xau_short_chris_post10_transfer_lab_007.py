#!/usr/bin/env python3
"""LAB007 — transfer frozen GC Chris/AEIF POST10 SHORT gate to executable FTMO XAUUSD.

Historical transfer only. No signal/gate/execution optimization.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
OOF = ROOT / "GC_SHORT_CHRIS_AEIF_POST10_DISTANCE_GATE_WALKFORWARD_LAB_006_OOF.csv"
LONG_TRANSFER = ROOT / "gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py"
OUT_JSON = ROOT / "GC_XAU_SHORT_CHRIS_POST10_TRANSFER_LAB_007.json"
OUT_MD = ROOT / "GC_XAU_SHORT_CHRIS_POST10_TRANSFER_LAB_007.md"
OUT_EVENTS = ROOT / "GC_XAU_SHORT_CHRIS_POST10_TRANSFER_LAB_007_EVENTS.csv"
OUT_CLOCK = ROOT / "GC_XAU_SHORT_CHRIS_POST10_TRANSFER_LAB_007_CLOCK.csv"

HORIZONS = (5, 10, 20, 30)
PRIMARY_H = 10
SECONDARY_H = 20
STALE_MS = 5000


def load_long_transfer():
    spec = importlib.util.spec_from_file_location("long_transfer_lab006", LONG_TRANSFER)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def transfer_row(r, times, bids, asks, offset_min, atr_map, lt):
    et = pd.Timestamp(r.entry_time)
    if et.tzinfo is None:
        et = et.tz_localize("UTC")
    else:
        et = et.tz_convert("UTC")
    checkpoint = et + pd.Timedelta(minutes=10)
    utc_ms = int(checkpoint.value // 1_000_000)
    broker_target_ms = utc_ms + offset_min * 60000
    i, lag = lt.first_tick_index(times, broker_target_ms)

    out = {
        "feed": r.feed,
        "seed_time": pd.Timestamp(r.seed_time).isoformat(),
        "gc_entry_time": et.isoformat(),
        "checkpoint_time_utc": checkpoint.isoformat(),
        "selected": bool(r.selected),
        "cp10_dist_seed_high": float(r.cp10_dist_seed_high),
        "threshold_q50": float(r.threshold_q50),
        "prior_history_n": int(r.prior_history_n),
        "clock_offset_min": int(offset_min),
        "broker_target_msc": int(broker_target_ms),
        "entry_tick_msc": None,
        "entry_lag_ms": lag,
        "entry_bid": np.nan,
        "entry_ask": np.nan,
        "entry_spread_bps": np.nan,
        "xau_atr14_m1": np.nan,
        "executable": False,
        "reject_reason": "",
    }
    for h in HORIZONS:
        out[f"exit_{h}m_ask"] = np.nan
        out[f"exit_{h}m_lag_ms"] = np.nan
        out[f"ret_{h}m_bps"] = np.nan
        out[f"ret_{h}m_atr"] = np.nan

    if i is None:
        out["reject_reason"] = "NO_ENTRY_TICK_WITHIN_5S"
        return out

    ebid = float(bids[i]); eask = float(asks[i])
    if not np.isfinite(ebid) or ebid <= 0 or not np.isfinite(eask) or eask < ebid:
        out["reject_reason"] = "INVALID_ENTRY_QUOTE"
        return out

    atr = float(atr_map.get(broker_target_ms - 60000, np.nan))
    spread = eask - ebid
    out.update({
        "entry_tick_msc": int(times[i]),
        "entry_bid": ebid,
        "entry_ask": eask,
        "entry_spread_bps": spread / ebid * 10000.0,
        "xau_atr14_m1": atr,
        "executable": True,
    })

    for h in HORIZONS:
        j, xlag = lt.first_tick_index(times, broker_target_ms + h * 60000)
        out[f"exit_{h}m_lag_ms"] = xlag if xlag is not None else np.nan
        if j is None or j < i:
            continue
        xask = float(asks[j])
        diff = ebid - xask
        out[f"exit_{h}m_ask"] = xask
        out[f"ret_{h}m_bps"] = diff / ebid * 10000.0
        if np.isfinite(atr) and atr > 0:
            out[f"ret_{h}m_atr"] = diff / atr
    return out


def stats(d: pd.DataFrame, h: int):
    z = d[d.executable].dropna(subset=[f"ret_{h}m_bps"]).copy()
    v = z[f"ret_{h}m_bps"].to_numpy(float)
    va = z[f"ret_{h}m_atr"].dropna().to_numpy(float)
    return {
        "n": int(len(v)),
        "ev_bps": float(v.mean()) if len(v) else None,
        "median_bps": float(np.median(v)) if len(v) else None,
        "wr_pct": float((v > 0).mean() * 100) if len(v) else None,
        "ev_atr": float(va.mean()) if len(va) else None,
    }


def summarize_feed(d: pd.DataFrame):
    groups = {
        "all_oof": d,
        "selected": d[d.selected],
        "rejected": d[~d.selected],
    }
    return {g: {str(h): stats(x, h) for h in HORIZONS} for g, x in groups.items()}


def metric(summary, feed, group, h, key):
    return summary.get(feed, {}).get(group, {}).get(str(h), {}).get(key)


def fnum(x, digits=3):
    return "NA" if x is None or not np.isfinite(x) else f"{x:+.{digits}f}"


def main():
    if not OOF.exists():
        raise SystemExit(f"Missing frozen LAB006 OOF ledger: {OOF}")
    oof = pd.read_csv(OOF)
    oof["selected"] = as_bool(oof["selected"])
    for c in ("seed_time", "entry_time"):
        oof[c] = pd.to_datetime(oof[c], utc=True)

    lt = load_long_transfer()
    times, bids, asks, file_stats = lt.read_xau_ticks()
    xau_m1 = lt.build_xau_m1(times, bids, asks)
    amp = lt.load_amp_m1_for_clock()
    offset_min, clock_table = lt.calibrate_clock(amp, xau_m1)
    clock_table.to_csv(OUT_CLOCK, index=False)
    atr_map = lt.xau_atr_lookup(xau_m1)

    rows = [transfer_row(r, times, bids, asks, offset_min, atr_map, lt) for r in oof.itertuples(index=False)]
    ev = pd.DataFrame(rows)
    ev.to_csv(OUT_EVENTS, index=False)

    summary = {feed: summarize_feed(ev[ev.feed.eq(feed)].copy()) for feed in sorted(ev.feed.unique())}
    rfeed = "RITHMIC_RAW"; afeed = "AMP_CQG_RAW_EXCLUSIVE"

    rs = set(ev[(ev.feed.eq(rfeed)) & ev.selected].seed_time)
    aps = set(ev[(ev.feed.eq(afeed)) & ev.selected].seed_time)
    common = rs & aps
    common_df = ev[(ev.feed.eq(rfeed)) & ev.selected & ev.seed_time.isin(common)].copy()
    common_stats = {str(h): stats(common_df, h) for h in HORIZONS}

    best = clock_table.dropna(subset=["pearson_m1_return_corr"]).sort_values(
        ["pearson_m1_return_corr", "n_common"], ascending=[False, False]
    ).iloc[0]
    best_corr = float(best.pearson_m1_return_corr)

    def val(feed, group, h, key):
        return metric(summary, feed, group, h, key)

    gates = {
        "clock_offset_eq_180": offset_min == 180,
        "clock_corr_ge_098": best_corr >= 0.98,
        "rith_selected_n_ge6": (val(rfeed, "selected", PRIMARY_H, "n") or 0) >= 6,
        "amp_selected_n_ge6": (val(afeed, "selected", PRIMARY_H, "n") or 0) >= 6,
        "rith_selected_10m_ev_pos": val(rfeed, "selected", 10, "ev_bps") is not None and val(rfeed, "selected", 10, "ev_bps") > 0,
        "amp_selected_10m_ev_pos": val(afeed, "selected", 10, "ev_bps") is not None and val(afeed, "selected", 10, "ev_bps") > 0,
        "rith_selected_gt_baseline_10m": val(rfeed, "selected", 10, "ev_bps") is not None and val(rfeed, "all_oof", 10, "ev_bps") is not None and val(rfeed, "selected", 10, "ev_bps") > val(rfeed, "all_oof", 10, "ev_bps"),
        "amp_selected_gt_baseline_10m": val(afeed, "selected", 10, "ev_bps") is not None and val(afeed, "all_oof", 10, "ev_bps") is not None and val(afeed, "selected", 10, "ev_bps") > val(afeed, "all_oof", 10, "ev_bps"),
        "rith_selected_gt_rejected_10m": val(rfeed, "selected", 10, "ev_bps") is not None and val(rfeed, "rejected", 10, "ev_bps") is not None and val(rfeed, "selected", 10, "ev_bps") > val(rfeed, "rejected", 10, "ev_bps"),
        "amp_selected_gt_rejected_10m": val(afeed, "selected", 10, "ev_bps") is not None and val(afeed, "rejected", 10, "ev_bps") is not None and val(afeed, "selected", 10, "ev_bps") > val(afeed, "rejected", 10, "ev_bps"),
        "rith_selected_wr_ge50": val(rfeed, "selected", 10, "wr_pct") is not None and val(rfeed, "selected", 10, "wr_pct") >= 50,
        "amp_selected_wr_ge50": val(afeed, "selected", 10, "wr_pct") is not None and val(afeed, "selected", 10, "wr_pct") >= 50,
        "rith_selected_20m_nonneg": val(rfeed, "selected", 20, "ev_bps") is not None and val(rfeed, "selected", 20, "ev_bps") >= 0,
        "amp_selected_20m_nonneg": val(afeed, "selected", 20, "ev_bps") is not None and val(afeed, "selected", 20, "ev_bps") >= 0,
        "common_selected_10m_ev_pos": common_stats["10"]["ev_bps"] is not None and common_stats["10"]["ev_bps"] > 0,
    }
    gates["pass"] = all(gates.values())
    status = "HISTORICAL_GC_XAU_SHORT_CHRIS_TRANSFER_PASS_NOT_OOS" if gates["pass"] else "HISTORICAL_GC_XAU_SHORT_CHRIS_TRANSFER_FAIL_NOT_OOS"

    result = {
        "status": status,
        "clock": {"offset_min": int(offset_min), "best_corr": best_corr},
        "source": "LAB006 frozen OOF ledger",
        "decision_time": "GC entry_time + 10m completed checkpoint",
        "xau_execution": "SHORT entry Bid / exit Ask; spread embedded",
        "file_stats": file_stats,
        "summary": summary,
        "exact_common_selected": {"n_seed_times": int(len(common)), "stats": common_stats},
        "gates": gates,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# GC→XAU SHORT CHRIS POST10 TRANSFER LAB007", "",
        f"**Status:** `{status}`", "",
        "Frozen LAB006 gate transferred to executable FTMO-Demo XAUUSD. Historical only; not independent OOS.", "",
        f"Clock: **UTC + {offset_min}m**, M1 return correlation **{best_corr:.6f}**.", "",
        "## XAU directional transfer", "",
        "| Feed | Group | H | N | EV bps | EV ATR | WR |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for feed in (rfeed, afeed):
        for group in ("all_oof", "selected", "rejected"):
            for h in HORIZONS:
                s = summary.get(feed, {}).get(group, {}).get(str(h), {})
                wr = s.get("wr_pct")
                wr_txt = "NA" if wr is None else f"{wr:.1f}%"
                lines.append(f"| {feed} | {group} | {h}m | {s.get('n',0)} | {fnum(s.get('ev_bps'))} | {fnum(s.get('ev_atr'))} | {wr_txt} |")
    common_wr = common_stats["10"]["wr_pct"]
    common_wr_txt = "NA" if common_wr is None else f"{common_wr:.1f}%"
    lines += ["", "## Exact-common selected subset", "", f"Common selected seed-times: **{len(common)}**; XAU 10m EV **{fnum(common_stats['10']['ev_bps'])} bps**; WR **{common_wr_txt}**.", "", "## Frozen gates", ""]
    for k, v in gates.items():
        if k != "pass":
            lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", "## Decision", ""]
    if gates["pass"]:
        lines.append("The frozen GC Chris POST10 gate transfers positively to executable XAU historically. Advance only to a separately preregistered XAU execution-geometry study; do not tune LAB007 post hoc.")
    else:
        lines.append("The frozen GC Chris POST10 gate does not pass the preregistered XAU transfer gates. Do not rescue it by tuning XAU timing, entry depth, stops, targets, sessions or spread filters on this sample.")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)
    print(json.dumps(gates, indent=2))


if __name__ == "__main__":
    main()
