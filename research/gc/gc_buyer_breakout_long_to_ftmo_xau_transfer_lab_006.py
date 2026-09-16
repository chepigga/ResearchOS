#!/usr/bin/env python3
"""GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006

Frozen transfer test from historical GC M1 BUYER_BREAKOUT_LONG_001 events to
executable FTMO-Demo XAUUSD raw Bid/Ask ticks.

See GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006_PREREG.md.
No signal/exit optimization is performed here.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
LEDGER = ROOT / "GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004_EVENTS.csv"
BASE = ROOT / "gc_m1_orderflow_edge_discovery_003.py"
XAU_DIR = ROOT / "_lab006_xau"
WORK = ROOT / "_lab006_work"
OUT_JSON = ROOT / "GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006.json"
OUT_MD = ROOT / "GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006.md"
OUT_EVENTS = ROOT / "GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006_EVENTS.csv"
OUT_CLOCK = ROOT / "GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006_CLOCK.csv"

HORIZONS = (1, 3, 5, 10, 15, 30, 60)
PRIMARY_H = 15
STALE_MS = 5000
CLOCK_OFFSETS_MIN = tuple(range(-240, 241, 30))
RULES = ("BUYER_BREAKOUT_LONG", "PRICE_BREAKOUT_NO_OF", "PRICE_BREAKOUT_ALL")
SEED = 20260916


def load_base():
    spec = importlib.util.spec_from_file_location("edge003", BASE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ResearchOS-LAB006/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, path.open("wb") as f:
        shutil.copyfileobj(r, f, 1024 * 1024)


def load_amp_m1_for_clock():
    m = load_base()
    WORK.mkdir(parents=True, exist_ok=True)
    zp = WORK / "amp_gc.zip"
    if not zp.exists():
        download(m.AMP_URL, zp)
    if sha256_file(zp) != m.AMP_SHA:
        raise SystemExit("AMP source SHA mismatch")
    b = m.load_amp(zp)[["time", "close"]].copy()
    b["time"] = pd.to_datetime(b["time"], utc=True)
    b = b.sort_values("time").reset_index(drop=True)
    dt = b.time.diff()
    b["ret"] = b.close.pct_change()
    b.loc[dt.ne(pd.Timedelta(minutes=1)), "ret"] = np.nan
    return b


def read_xau_ticks():
    files = sorted(p for p in XAU_DIR.glob("XAUUSD_raw_ticks_*.csv") if ".meta." not in p.name)
    if not files:
        raise SystemExit(f"No XAU raw tick files in {XAU_DIR}")
    frames = []
    file_stats = []
    for p in files:
        d = pd.read_csv(
            p,
            usecols=lambda c: c in {"time_msc", "bid", "ask", "quote_valid", "spread_price", "spread_points"},
            low_memory=False,
        )
        if d.empty:
            continue
        for c in ("time_msc", "bid", "ask"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        if "quote_valid" in d.columns:
            qv = pd.to_numeric(d["quote_valid"], errors="coerce").fillna(0).eq(1)
        else:
            qv = d.bid.gt(0) & d.ask.gt(0)
        d = d[qv & d.time_msc.notna() & d.bid.gt(0) & d.ask.gt(0) & d.ask.ge(d.bid)].copy()
        if d.empty:
            continue
        file_stats.append(
            {
                "file": p.name,
                "rows": int(len(d)),
                "first_time_msc": int(d.time_msc.iloc[0]),
                "last_time_msc": int(d.time_msc.iloc[-1]),
            }
        )
        frames.append(d[["time_msc", "bid", "ask"]])
    if not frames:
        raise SystemExit("XAU files contained no quote-valid ticks")
    x = pd.concat(frames, ignore_index=True)
    x = x.sort_values("time_msc", kind="mergesort").drop_duplicates(["time_msc", "bid", "ask"]).reset_index(drop=True)
    times = x.time_msc.to_numpy(np.int64)
    bids = x.bid.to_numpy(float)
    asks = x.ask.to_numpy(float)
    if np.any(np.diff(times) < 0):
        raise SystemExit("XAU time_msc not monotonic after sort")
    return times, bids, asks, file_stats


def build_xau_m1(times, bids, asks):
    minute = (times // 60000) * 60000
    mid = (bids + asks) / 2.0
    d = pd.DataFrame({"minute_ms": minute, "mid": mid})
    g = d.groupby("minute_ms", sort=True, observed=True).mid
    b = g.agg(open="first", high="max", low="min", close="last").reset_index()
    prev = b.close.shift(1)
    tr = pd.concat([(b.high - b.low), (b.high - prev).abs(), (b.low - prev).abs()], axis=1).max(axis=1)
    tr.iloc[0] = np.nan
    b["atr14"] = tr.rolling(14, min_periods=14).mean()
    dt = b.minute_ms.diff()
    b["ret"] = b.close.pct_change()
    b.loc[dt.ne(60000), "ret"] = np.nan
    return b


def calibrate_clock(amp, xau_m1):
    a = amp[["time", "ret"]].dropna().copy()
    a["minute_utc_ms"] = (a.time.astype("int64") // 1_000_000).astype(np.int64)
    a = a[["minute_utc_ms", "ret"]].rename(columns={"ret": "gc_ret"})
    base = xau_m1[["minute_ms", "ret"]].dropna().copy()
    rows = []
    for off in CLOCK_OFFSETS_MIN:
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


def xau_atr_lookup(xau_m1):
    # ATR attached to each completed broker-clock M1 bar.
    return dict(zip(xau_m1.minute_ms.astype(np.int64), xau_m1.atr14.astype(float)))


def first_tick_index(times: np.ndarray, target_ms: int):
    i = int(np.searchsorted(times, target_ms, side="left"))
    if i >= len(times):
        return None, None
    lag = int(times[i] - target_ms)
    if lag < 0 or lag > STALE_MS:
        return None, lag
    return i, lag


def transfer_event(row, times, bids, asks, offset_min, atr_map):
    entry_utc = pd.Timestamp(row.entry_time)
    if entry_utc.tzinfo is None:
        entry_utc = entry_utc.tz_localize("UTC")
    else:
        entry_utc = entry_utc.tz_convert("UTC")
    entry_utc_ms = int(entry_utc.value // 1_000_000)
    broker_target_ms = entry_utc_ms + offset_min * 60000
    i, entry_lag = first_tick_index(times, broker_target_ms)
    base = {
        "source_feed": row.source_feed,
        "rule": row.rule,
        "signal_time_utc": pd.Timestamp(row.signal_time).isoformat(),
        "entry_time_utc": entry_utc.isoformat(),
        "clock_offset_min": offset_min,
        "broker_target_msc": broker_target_ms,
        "entry_tick_msc": None,
        "entry_lag_ms": entry_lag,
        "entry_bid": np.nan,
        "entry_ask": np.nan,
        "entry_spread": np.nan,
        "entry_spread_bps": np.nan,
        "xau_atr14_m1": np.nan,
        "executable": False,
        "reject_reason": "",
    }
    for h in HORIZONS:
        base[f"exit_{h}m_bid"] = np.nan
        base[f"exit_{h}m_lag_ms"] = np.nan
        base[f"ret_{h}m_bps"] = np.nan
        base[f"ret_{h}m_atr"] = np.nan
    for h in (15, 60):
        base[f"mfe_{h}m_bps"] = np.nan
        base[f"mae_{h}m_bps"] = np.nan
        base[f"mfe_{h}m_atr"] = np.nan
        base[f"mae_{h}m_atr"] = np.nan
    if i is None:
        base["reject_reason"] = "NO_ENTRY_TICK_WITHIN_5S"
        return base
    entry_bid = float(bids[i])
    entry_ask = float(asks[i])
    if not np.isfinite(entry_ask) or entry_ask <= 0 or entry_ask < entry_bid:
        base["reject_reason"] = "INVALID_ENTRY_QUOTE"
        return base
    prev_minute = broker_target_ms - 60000
    atr = float(atr_map.get(prev_minute, np.nan))
    spread = entry_ask - entry_bid
    base.update(
        {
            "entry_tick_msc": int(times[i]),
            "entry_bid": entry_bid,
            "entry_ask": entry_ask,
            "entry_spread": spread,
            "entry_spread_bps": spread / entry_ask * 10000.0,
            "xau_atr14_m1": atr,
            "executable": True,
        }
    )
    for h in HORIZONS:
        target = broker_target_ms + h * 60000
        j, lag = first_tick_index(times, target)
        base[f"exit_{h}m_lag_ms"] = lag if lag is not None else np.nan
        if j is None or j < i:
            continue
        exit_bid = float(bids[j])
        diff = exit_bid - entry_ask
        base[f"exit_{h}m_bid"] = exit_bid
        base[f"ret_{h}m_bps"] = diff / entry_ask * 10000.0
        if np.isfinite(atr) and atr > 0:
            base[f"ret_{h}m_atr"] = diff / atr
        if h in (15, 60):
            path = bids[i : j + 1]
            if len(path):
                mfe = float(np.nanmax(path) - entry_ask)
                mae = float(np.nanmin(path) - entry_ask)
                base[f"mfe_{h}m_bps"] = mfe / entry_ask * 10000.0
                base[f"mae_{h}m_bps"] = mae / entry_ask * 10000.0
                if np.isfinite(atr) and atr > 0:
                    base[f"mfe_{h}m_atr"] = mfe / atr
                    base[f"mae_{h}m_atr"] = mae / atr
    return base


def day_cluster_ci(df, col, n_boot=10000):
    z = df.dropna(subset=[col]).copy()
    if z.empty:
        return [None, None]
    z["day"] = pd.to_datetime(z.signal_time_utc, utc=True).dt.date
    groups = [g[col].to_numpy(float) for _, g in z.groupby("day")]
    if len(groups) < 2:
        return [None, None]
    rng = np.random.default_rng(SEED)
    vals = np.empty(n_boot)
    k = len(groups)
    for j in range(n_boot):
        picks = rng.integers(0, k, k)
        vals[j] = np.concatenate([groups[i] for i in picks]).mean()
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def summarize_group(df):
    out = {}
    for h in HORIZONS:
        col = f"ret_{h}m_bps"
        z = df.dropna(subset=[col]).copy()
        v = z[col].to_numpy(float)
        if len(z):
            z["day"] = pd.to_datetime(z.signal_time_utc, utc=True).dt.date
            daily = z.groupby("day")[col].mean()
        else:
            daily = pd.Series(dtype=float)
        out[str(h)] = {
            "n": int(len(v)),
            "ev_bps": float(v.mean()) if len(v) else None,
            "median_bps": float(np.median(v)) if len(v) else None,
            "wr_pct": float((v > 0).mean() * 100) if len(v) else None,
            "ev_atr": float(z[f"ret_{h}m_atr"].dropna().mean()) if len(z[f"ret_{h}m_atr"].dropna()) else None,
            "days": int(len(daily)),
            "positive_days": int((daily > 0).sum()),
            "day_ci95_bps": day_cluster_ci(df, col),
        }
    valid_spread = df.entry_spread_bps.dropna()
    out["entry"] = {
        "events_total": int(len(df)),
        "executable": int(df.executable.sum()),
        "median_spread_bps": float(valid_spread.median()) if len(valid_spread) else None,
        "mean_spread_bps": float(valid_spread.mean()) if len(valid_spread) else None,
        "median_entry_lag_ms": float(df.entry_lag_ms.dropna().median()) if len(df.entry_lag_ms.dropna()) else None,
    }
    for h in (15, 60):
        for k in ("mfe", "mae"):
            c = f"{k}_{h}m_atr"
            out[f"{k}_{h}m_atr_mean"] = float(df[c].dropna().mean()) if len(df[c].dropna()) else None
            out[f"{k}_{h}m_atr_median"] = float(df[c].dropna().median()) if len(df[c].dropna()) else None
    return out


def fnum(x, digits=3):
    return "NA" if x is None or not np.isfinite(x) else f"{x:+.{digits}f}"


def main():
    if not LEDGER.exists():
        raise SystemExit(f"Missing frozen event ledger {LEDGER}")
    times, bids, asks, file_stats = read_xau_ticks()
    xau_m1 = build_xau_m1(times, bids, asks)
    amp = load_amp_m1_for_clock()
    offset_min, clock_table = calibrate_clock(amp, xau_m1)
    clock_table.to_csv(OUT_CLOCK, index=False)
    atr_map = xau_atr_lookup(xau_m1)

    ledger = pd.read_csv(LEDGER)
    ledger["signal_time"] = pd.to_datetime(ledger.signal_time, utc=True)
    ledger["entry_time"] = pd.to_datetime(ledger.entry_time, utc=True)
    ledger = ledger[ledger.rule.isin(RULES) & ledger.source_feed.isin(["RITHMIC", "AMP"])].copy()

    rows = []
    for r in ledger.itertuples(index=False):
        rows.append(transfer_event(r, times, bids, asks, offset_min, atr_map))
    ev = pd.DataFrame(rows)
    ev.to_csv(OUT_EVENTS, index=False)

    summaries = {}
    for feed in ("RITHMIC", "AMP"):
        summaries[feed] = {}
        for rule in RULES:
            summaries[feed][rule] = summarize_group(ev[(ev.source_feed == feed) & (ev.rule == rule)].copy())

    # Exact common-clock candidate subset between the two feed ledgers.
    rc = ev[(ev.source_feed == "RITHMIC") & (ev.rule == "BUYER_BREAKOUT_LONG")].copy()
    ac = ev[(ev.source_feed == "AMP") & (ev.rule == "BUYER_BREAKOUT_LONG")].copy()
    common_times = sorted(set(rc.signal_time_utc) & set(ac.signal_time_utc))
    common = rc[rc.signal_time_utc.isin(common_times)].drop_duplicates("signal_time_utc").copy()
    common_summary = summarize_group(common)

    primary = {}
    for feed in ("RITHMIC", "AMP"):
        c = summaries[feed]["BUYER_BREAKOUT_LONG"][str(PRIMARY_H)]
        p = summaries[feed]["PRICE_BREAKOUT_NO_OF"][str(PRIMARY_H)]
        primary[feed] = {
            "candidate_n": c["n"],
            "candidate_ev_bps": c["ev_bps"],
            "candidate_ev_atr": c["ev_atr"],
            "candidate_wr_pct": c["wr_pct"],
            "candidate_days": c["days"],
            "candidate_positive_days": c["positive_days"],
            "price_no_of_ev_bps": p["ev_bps"],
            "incremental_bps": None if c["ev_bps"] is None or p["ev_bps"] is None else c["ev_bps"] - p["ev_bps"],
            "day_ci95_bps": c["day_ci95_bps"],
        }

    checks = {
        "rithmic_n_ge100": primary["RITHMIC"]["candidate_n"] >= 100,
        "amp_n_ge100": primary["AMP"]["candidate_n"] >= 100,
        "rithmic_ev15_bps_pos": (primary["RITHMIC"]["candidate_ev_bps"] or -1e99) > 0,
        "amp_ev15_bps_pos": (primary["AMP"]["candidate_ev_bps"] or -1e99) > 0,
        "rithmic_ev15_atr_pos": (primary["RITHMIC"]["candidate_ev_atr"] or -1e99) > 0,
        "amp_ev15_atr_pos": (primary["AMP"]["candidate_ev_atr"] or -1e99) > 0,
        "rithmic_incremental_vs_price_no_of_pos": (primary["RITHMIC"]["incremental_bps"] or -1e99) > 0,
        "amp_incremental_vs_price_no_of_pos": (primary["AMP"]["incremental_bps"] or -1e99) > 0,
        "common_clock_ev15_pos": (common_summary[str(PRIMARY_H)]["ev_bps"] or -1e99) > 0,
        "rithmic_positive_days_ge50pct": primary["RITHMIC"]["candidate_days"] > 0 and primary["RITHMIC"]["candidate_positive_days"] * 2 >= primary["RITHMIC"]["candidate_days"],
        "amp_positive_days_ge50pct": primary["AMP"]["candidate_days"] > 0 and primary["AMP"]["candidate_positive_days"] * 2 >= primary["AMP"]["candidate_days"],
    }
    passed = all(checks.values())

    best_clock_row = clock_table.loc[clock_table.pearson_m1_return_corr.idxmax()].to_dict()
    result = {
        "lab": "GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006",
        "status": "TRANSFER_PASS" if passed else "TRANSFER_FAIL",
        "frozen_primary_horizon_min": PRIMARY_H,
        "clock": {
            "selected_offset_min_ftmo_clock_equals_utc_plus": offset_min,
            "best": best_clock_row,
            "scan_offsets_min": list(CLOCK_OFFSETS_MIN),
        },
        "xau_source": {
            "directory": str(XAU_DIR),
            "raw_files": len(file_stats),
            "quote_valid_ticks": int(len(times)),
            "first_time_msc": int(times[0]),
            "last_time_msc": int(times[-1]),
            "file_stats": file_stats,
        },
        "primary_15m": primary,
        "common_clock_candidate": common_summary,
        "summaries": summaries,
        "gate": checks,
        "governance": {
            "signal_thresholds_optimized": False,
            "xau_stop_target_optimized": False,
            "spread_included_by_ask_entry_bid_exit": True,
            "commission_included": False,
            "clock_selected_by_market_return_correlation_only": True,
        },
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        "# GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006",
        "",
        f"**Verdict: {result['status']}**",
        "",
        f"Clock calibration: `FTMO clock = UTC {offset_min/60:+.1f}h`; M1 return correlation = **{best_clock_row['pearson_m1_return_corr']:.4f}** on N={int(best_clock_row['n_common'])} common M1 returns.",
        "",
        "Primary horizon was frozen at **15 minutes** before this run. Entry is XAU Ask; exit is XAU Bid; quoted spread is therefore included.",
        "",
        "| Feed | Candidate N | XAU EV 15m (bps) | EV 15m (ATR) | WR | Positive days | Price-no-OF EV (bps) | Incremental (bps) | Day CI95 (bps) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for feed in ("RITHMIC", "AMP"):
        p = primary[feed]
        ci = p["day_ci95_bps"]
        cis = "NA" if ci[0] is None else f"[{ci[0]:+.3f},{ci[1]:+.3f}]"
        lines.append(
            f"| {feed} | {p['candidate_n']} | {fnum(p['candidate_ev_bps'])} | {fnum(p['candidate_ev_atr'])} | {p['candidate_wr_pct']:.1f}% | {p['candidate_positive_days']}/{p['candidate_days']} | {fnum(p['price_no_of_ev_bps'])} | {fnum(p['incremental_bps'])} | {cis} |"
        )
    cc = common_summary[str(PRIMARY_H)]
    lines += [
        "",
        f"Exact common-clock candidate subset: **N={cc['n']}**, XAU 15m EV **{fnum(cc['ev_bps'])} bps**, WR **{cc['wr_pct']:.1f}%**.",
        "",
        "## Horizon profile — candidate only",
        "",
        "| Feed | 1m | 3m | 5m | 10m | 15m | 30m | 60m |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for feed in ("RITHMIC", "AMP"):
        s = summaries[feed]["BUYER_BREAKOUT_LONG"]
        vals = [fnum(s[str(h)]["ev_bps"]) for h in HORIZONS]
        lines.append(f"| {feed} | " + " | ".join(vals) + " |")
    lines += [
        "",
        "## Gate",
        "",
    ]
    for k, v in checks.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "",
        "## Governance",
        "",
        "No GC threshold, session filter, stop, take-profit, time-stop, retest entry or XAU outcome filter was optimized in this LAB. Commission and discretionary slippage are not applied; quoted FTMO spread is already included through Ask-entry/Bid-exit. If this transfer passes, execution geometry belongs in a separate LAB007.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT_MD.read_text())


if __name__ == "__main__":
    main()
