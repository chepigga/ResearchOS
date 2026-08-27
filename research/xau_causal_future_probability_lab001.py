#!/usr/bin/env python3
"""XAU CAUSAL FUTURE PROBABILITY LAB001

Consumes a ZIP produced by CAUSAL_XAU_RAW_TICK_COLLECTOR_LAB_001.mq5,
audits raw Bid/Ask ticks, builds causal M1 observations, and creates a first
multi-barrier future-label baseline. No trading-pattern features are used.

Labels are intentionally future-looking; ATR/features are causal and use only
information available before the observation tick.
"""
from __future__ import annotations

import argparse
import json
import math
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

try:
    from numba import njit
except Exception:
    njit = None

REQUIRED = {"time_msc", "bid", "ask"}
COMMISSION_RATE_SIDE = 0.000007  # screenshot: 0.0007% USD notional per in/out deal
CONTRACT_SIZE = 100.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("zip_path", type=Path)
    p.add_argument("--outdir", type=Path, default=Path("Results_XAU_CAUSAL_LAB001"))
    p.add_argument("--chunksize", type=int, default=1_000_000)
    p.add_argument("--sample-spreads", type=int, default=2_000_000)
    p.add_argument("--sl-atrs", default="0.75,1.0,1.25")
    p.add_argument("--rrs", default="1.5,2.0")
    p.add_argument("--horizons", default="15,60,240")
    return p.parse_args()


def quantiles(x: np.ndarray) -> Dict[str, float | None]:
    if x.size == 0:
        return {k: None for k in ("p50", "p90", "p95", "p99", "max")}
    return {
        "p50": float(np.quantile(x, 0.50)),
        "p90": float(np.quantile(x, 0.90)),
        "p95": float(np.quantile(x, 0.95)),
        "p99": float(np.quantile(x, 0.99)),
        "max": float(np.max(x)),
    }


def list_csv_members(zf: zipfile.ZipFile) -> List[str]:
    names = [n for n in zf.namelist() if not n.endswith("/") and n.lower().endswith(".csv")]
    return sorted(n for n in names if "manifest" not in Path(n).name.lower())


def read_manifest(zf: zipfile.ZipFile) -> Dict[str, str]:
    names = [n for n in zf.namelist() if Path(n).name.lower() == "causal_xau_raw_manifest.csv"]
    if not names:
        return {}
    try:
        with zf.open(names[0]) as f:
            df = pd.read_csv(f)
        if {"field", "value"}.issubset(df.columns):
            return dict(zip(df["field"].astype(str), df["value"].astype(str)))
    except Exception:
        pass
    return {}


def process_zip(zip_path: Path, chunksize: int, spread_sample_cap: int):
    raw_rows = valid_rows = invalid_bidask = negative_spread = 0
    duplicate_adjacent = monotonic_violations = 0
    first_time = last_time = prev_time = None
    prev_sig = None
    spread_sample_parts: List[np.ndarray] = []
    spread_sample_n = 0
    minute_parts: List[pd.DataFrame] = []
    file_stats = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = list_csv_members(zf)
        manifest = read_manifest(zf)
        if not members:
            raise RuntimeError("ZIP contains no tick CSV files")

        for member in members:
            file_rows = file_valid = 0
            file_first = file_last = None
            print(f"[READ] {member}", flush=True)
            with zf.open(member) as fh:
                for chunk in pd.read_csv(fh, chunksize=chunksize, low_memory=False):
                    raw_rows += len(chunk)
                    file_rows += len(chunk)
                    missing = REQUIRED.difference(chunk.columns)
                    if missing:
                        raise RuntimeError(f"{member}: missing required columns {sorted(missing)}")

                    t = pd.to_numeric(chunk["time_msc"], errors="coerce")
                    bid = pd.to_numeric(chunk["bid"], errors="coerce")
                    ask = pd.to_numeric(chunk["ask"], errors="coerce")
                    ok = t.notna() & bid.notna() & ask.notna() & (bid > 0) & (ask > 0)
                    invalid_bidask += int((~ok).sum())
                    c = pd.DataFrame({
                        "time_msc": t[ok].astype("int64"),
                        "bid": bid[ok].astype("float64"),
                        "ask": ask[ok].astype("float64"),
                    })
                    if c.empty:
                        continue

                    neg = c["ask"] < c["bid"]
                    negative_spread += int(neg.sum())
                    c = c[~neg]
                    if c.empty:
                        continue

                    arr_t = c["time_msc"].to_numpy(np.int64, copy=False)
                    arr_b = c["bid"].to_numpy(np.float64, copy=False)
                    arr_a = c["ask"].to_numpy(np.float64, copy=False)
                    n = len(c)
                    valid_rows += n
                    file_valid += n
                    if file_first is None:
                        file_first = int(arr_t[0])
                    file_last = int(arr_t[-1])
                    if first_time is None:
                        first_time = int(arr_t[0])
                    last_time = int(arr_t[-1])

                    if prev_time is not None and int(arr_t[0]) < prev_time:
                        monotonic_violations += 1
                    if n > 1:
                        monotonic_violations += int(np.sum(np.diff(arr_t) < 0))

                    if prev_sig is not None and (int(arr_t[0]), float(arr_b[0]), float(arr_a[0])) == prev_sig:
                        duplicate_adjacent += 1
                    if n > 1:
                        duplicate_adjacent += int(np.sum(
                            (arr_t[1:] == arr_t[:-1]) &
                            (arr_b[1:] == arr_b[:-1]) &
                            (arr_a[1:] == arr_a[:-1])
                        ))
                    prev_time = int(arr_t[-1])
                    prev_sig = (int(arr_t[-1]), float(arr_b[-1]), float(arr_a[-1]))

                    spreads = arr_a - arr_b
                    if spread_sample_n < spread_sample_cap:
                        room = spread_sample_cap - spread_sample_n
                        if n <= room:
                            take = spreads
                        else:
                            step = max(1, n // room)
                            take = spreads[::step][:room]
                        spread_sample_parts.append(np.asarray(take, dtype=np.float64))
                        spread_sample_n += len(take)

                    c["minute"] = c["time_msc"] // 60_000
                    c["mid"] = (c["bid"] + c["ask"]) * 0.5
                    c["spread"] = c["ask"] - c["bid"]
                    g = c.groupby("minute", sort=False, observed=True)
                    ag = g.agg(
                        first_time_msc=("time_msc", "first"),
                        last_time_msc=("time_msc", "last"),
                        first_bid=("bid", "first"),
                        first_ask=("ask", "first"),
                        bid_high=("bid", "max"),
                        bid_low=("bid", "min"),
                        bid_close=("bid", "last"),
                        ask_high=("ask", "max"),
                        ask_low=("ask", "min"),
                        ask_close=("ask", "last"),
                        mid_open=("mid", "first"),
                        mid_high=("mid", "max"),
                        mid_low=("mid", "min"),
                        mid_close=("mid", "last"),
                        spread_sum=("spread", "sum"),
                        spread_min=("spread", "min"),
                        spread_max=("spread", "max"),
                        tick_count=("time_msc", "size"),
                    ).reset_index()
                    minute_parts.append(ag)
                    del chunk, c, ag

            file_stats.append({
                "member": member,
                "rows": file_rows,
                "valid_rows": file_valid,
                "first_time_msc": file_first,
                "last_time_msc": file_last,
            })

    if not minute_parts:
        raise RuntimeError("No valid ticks retained")

    m = pd.concat(minute_parts, ignore_index=True)
    m = m.sort_values(["minute", "first_time_msc"], kind="stable")
    gm = m.groupby("minute", sort=True, observed=True)
    bars = gm.agg(
        first_time_msc=("first_time_msc", "first"),
        last_time_msc=("last_time_msc", "last"),
        first_bid=("first_bid", "first"),
        first_ask=("first_ask", "first"),
        bid_high=("bid_high", "max"),
        bid_low=("bid_low", "min"),
        bid_close=("bid_close", "last"),
        ask_high=("ask_high", "max"),
        ask_low=("ask_low", "min"),
        ask_close=("ask_close", "last"),
        mid_open=("mid_open", "first"),
        mid_high=("mid_high", "max"),
        mid_low=("mid_low", "min"),
        mid_close=("mid_close", "last"),
        spread_sum=("spread_sum", "sum"),
        spread_min=("spread_min", "min"),
        spread_max=("spread_max", "max"),
        tick_count=("tick_count", "sum"),
    ).reset_index()
    bars["spread_mean"] = bars["spread_sum"] / bars["tick_count"].clip(lower=1)
    bars["timestamp_from_time_msc"] = pd.to_datetime(bars["minute"] * 60_000, unit="ms")

    spread_sample = np.concatenate(spread_sample_parts) if spread_sample_parts else np.array([], dtype=float)
    audit = {
        "zip_path": str(zip_path),
        "zip_size_bytes": int(zip_path.stat().st_size),
        "csv_members": len(file_stats),
        "raw_rows": int(raw_rows),
        "valid_rows": int(valid_rows),
        "invalid_bidask_rows": int(invalid_bidask),
        "negative_spread_rows": int(negative_spread),
        "adjacent_exact_duplicate_ticks": int(duplicate_adjacent),
        "time_monotonicity_violations": int(monotonic_violations),
        "first_time_msc": int(first_time) if first_time is not None else None,
        "last_time_msc": int(last_time) if last_time is not None else None,
        "period_start": pd.to_datetime(first_time, unit="ms").isoformat() if first_time is not None else None,
        "period_end": pd.to_datetime(last_time, unit="ms").isoformat() if last_time is not None else None,
        "m1_minutes": int(len(bars)),
        "tick_count_per_minute": quantiles(bars["tick_count"].to_numpy(np.float64)),
        "spread_price_sample": quantiles(spread_sample),
        "manifest": manifest,
        "files": file_stats,
        "label_clock_note": "M1 observation at first valid tick of each minute; ATR uses only prior completed M1 bars.",
        "label_precision_note": "Baseline uses M1 Bid/Ask extrema. If TP and SL occur in the same minute, label=AMBIGUOUS; no OHLC ordering guess.",
    }
    return bars, audit


def add_causal_atr(bars: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    b = bars.copy()
    prev_close = b["mid_close"].shift(1)
    tr = pd.concat([
        b["mid_high"] - b["mid_low"],
        (b["mid_high"] - prev_close).abs(),
        (b["mid_low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    b[f"atr{period}_causal"] = tr.rolling(period, min_periods=period).mean().shift(1)
    return b


if njit is not None:
    @njit(cache=True)
    def _label_one_side(minutes, high_arr, low_arr, entries, atrs, sl_mult, rr, horizon, side):
        n = len(minutes)
        labels = np.full(n, 9, np.int8)
        t_hit = np.full(n, -1, np.int16)
        for i in range(n):
            atr = atrs[i]
            if not np.isfinite(atr) or atr <= 0 or not np.isfinite(entries[i]):
                continue
            e = entries[i]
            d = sl_mult * atr
            if side == 1:
                tp, sl = e + rr*d, e - d
            else:
                tp, sl = e - rr*d, e + d
            end_min = minutes[i] + horizon - 1
            found = False
            j = i
            while j < n and minutes[j] <= end_min:
                hi, lo = high_arr[j], low_arr[j]
                if side == 1:
                    hit_tp, hit_sl = hi >= tp, lo <= sl
                else:
                    hit_tp, hit_sl = lo <= tp, hi >= sl
                if hit_tp or hit_sl:
                    labels[i] = 2 if (hit_tp and hit_sl) else (1 if hit_tp else -1)
                    t_hit[i] = int(minutes[j] - minutes[i])
                    found = True
                    break
                j += 1
            if not found:
                if minutes[n-1] >= end_min:
                    labels[i] = 0
                    t_hit[i] = horizon
                else:
                    labels[i] = 9
        return labels, t_hit
else:
    def _label_one_side(minutes, high_arr, low_arr, entries, atrs, sl_mult, rr, horizon, side):
        n = len(minutes)
        labels = np.full(n, 9, np.int8)
        t_hit = np.full(n, -1, np.int16)
        for i in range(n):
            atr = atrs[i]
            if not np.isfinite(atr) or atr <= 0 or not np.isfinite(entries[i]):
                continue
            e = entries[i]
            d = sl_mult * atr
            tp, sl = ((e + rr*d, e-d) if side == 1 else (e-rr*d, e+d))
            end_min = minutes[i] + horizon - 1
            found = False
            j = i
            while j < n and minutes[j] <= end_min:
                hi, lo = high_arr[j], low_arr[j]
                hit_tp, hit_sl = ((hi >= tp, lo <= sl) if side == 1 else (lo <= tp, hi >= sl))
                if hit_tp or hit_sl:
                    labels[i] = 2 if (hit_tp and hit_sl) else (1 if hit_tp else -1)
                    t_hit[i] = int(minutes[j] - minutes[i])
                    found = True
                    break
                j += 1
            if not found and minutes[-1] >= end_min:
                labels[i] = 0
                t_hit[i] = horizon
        return labels, t_hit


def wilson_ci(k: int, n: int, z: float = 1.96) -> Tuple[float | None, float | None]:
    if n <= 0:
        return None, None
    p = k / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt((p*(1-p)/n) + z*z/(4*n*n)) / den
    return center-half, center+half


def build_baseline(bars: pd.DataFrame, sl_atrs: List[float], rrs: List[float], horizons: List[int]):
    b = add_causal_atr(bars, 14)
    minutes = b["minute"].to_numpy(np.int64)
    atrs = b["atr14_causal"].to_numpy(np.float64)
    buy_entry = b["first_ask"].to_numpy(np.float64)
    sell_entry = b["first_bid"].to_numpy(np.float64)
    bid_hi = b["bid_high"].to_numpy(np.float64)
    bid_lo = b["bid_low"].to_numpy(np.float64)
    ask_hi = b["ask_high"].to_numpy(np.float64)
    ask_lo = b["ask_low"].to_numpy(np.float64)

    summaries = []
    labels_df = b[["minute", "timestamp_from_time_msc", "first_time_msc", "first_bid", "first_ask", "atr14_causal", "tick_count", "spread_mean", "spread_max"]].copy()

    for side_name, side, hi, lo, entries in [
        ("BUY", 1, bid_hi, bid_lo, buy_entry),
        ("SELL", -1, ask_hi, ask_lo, sell_entry),
    ]:
        for slm in sl_atrs:
            for rr in rrs:
                risk_price = slm * atrs
                commission_rt_usd_per_lot = 2.0 * COMMISSION_RATE_SIDE * entries * CONTRACT_SIZE
                risk_usd_per_lot = risk_price * CONTRACT_SIZE
                commission_r = np.divide(commission_rt_usd_per_lot, risk_usd_per_lot,
                                         out=np.full_like(risk_usd_per_lot, np.nan),
                                         where=(risk_usd_per_lot > 0))
                for h in horizons:
                    labels, t_hit = _label_one_side(minutes, hi, lo, entries, atrs, slm, rr, h, side)
                    col = f"{side_name}_S{slm:g}_R{rr:g}_H{h}"
                    labels_df[col] = labels
                    labels_df[col + "_tmin"] = t_hit

                    valid = np.isin(labels, np.array([-1, 0, 1, 2], dtype=np.int8))
                    resolved = np.isin(labels, np.array([-1, 1], dtype=np.int8))
                    n_valid = int(valid.sum())
                    n_res = int(resolved.sum())
                    tp = int((labels == 1).sum())
                    sl = int((labels == -1).sum())
                    none = int((labels == 0).sum())
                    amb = int((labels == 2).sum())
                    cens = int((labels == 9).sum())
                    wr = tp / n_res if n_res else None
                    lo_ci, hi_ci = wilson_ci(tp, n_res)
                    c_mean = float(np.nanmean(commission_r[resolved])) if n_res else None
                    be = ((1.0 + c_mean) / (1.0 + rr)) if c_mean is not None else None
                    ev_resolved = (wr * rr - (1.0-wr) - c_mean) if wr is not None and c_mean is not None else None
                    summaries.append({
                        "side": side_name,
                        "sl_atr": slm,
                        "rr": rr,
                        "horizon_min": h,
                        "n_valid": n_valid,
                        "n_resolved": n_res,
                        "tp": tp,
                        "sl": sl,
                        "none": none,
                        "ambiguous": amb,
                        "censored": cens,
                        "resolved_win_rate": wr,
                        "wr_ci95_low": lo_ci,
                        "wr_ci95_high": hi_ci,
                        "mean_commission_R": c_mean,
                        "breakeven_win_rate_after_commission": be,
                        "resolved_EV_R_after_commission": ev_resolved,
                        "ambiguous_rate_valid": (amb/n_valid if n_valid else None),
                        "none_rate_valid": (none/n_valid if n_valid else None),
                    })
    return labels_df, pd.DataFrame(summaries)


def monthly_summary(labels_df: pd.DataFrame, config_cols: List[str]) -> pd.DataFrame:
    d = labels_df.copy()
    d["month"] = pd.to_datetime(d["timestamp_from_time_msc"]).dt.to_period("M").astype(str)
    rows = []
    for month, g in d.groupby("month"):
        for col in config_cols:
            a = g[col].to_numpy()
            res = (a == 1) | (a == -1)
            n = int(res.sum())
            rows.append({
                "month": month,
                "config": col,
                "resolved_n": n,
                "tp": int((a == 1).sum()),
                "sl": int((a == -1).sum()),
                "win_rate": (float((a == 1).sum()) / n if n else None),
                "none": int((a == 0).sum()),
                "ambiguous": int((a == 2).sum()),
                "censored": int((a == 9).sum()),
            })
    return pd.DataFrame(rows)


def main():
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    if not args.zip_path.exists():
        raise SystemExit(f"Missing ZIP: {args.zip_path}")

    sl_atrs = [float(x) for x in args.sl_atrs.split(",") if x.strip()]
    rrs = [float(x) for x in args.rrs.split(",") if x.strip()]
    horizons = [int(x) for x in args.horizons.split(",") if x.strip()]

    print("[LAB001] raw audit + causal M1 baseline", flush=True)
    bars, audit = process_zip(args.zip_path, args.chunksize, args.sample_spreads)
    (args.outdir / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    bars.to_parquet(args.outdir / "m1_bidask_bars.parquet", index=False)
    print(f"[AUDIT] rows={audit['raw_rows']:,} valid={audit['valid_rows']:,} m1={audit['m1_minutes']:,}", flush=True)
    print(f"[AUDIT] period={audit['period_start']} -> {audit['period_end']}", flush=True)
    print(f"[AUDIT] spread={audit['spread_price_sample']}", flush=True)

    labels, summary = build_baseline(bars, sl_atrs, rrs, horizons)
    labels.to_parquet(args.outdir / "causal_labels_m1.parquet", index=False)
    summary.to_csv(args.outdir / "baseline_summary.csv", index=False)
    config_cols = [c for c in labels.columns if (c.startswith("BUY_") or c.startswith("SELL_")) and not c.endswith("_tmin")]
    monthly_summary(labels, config_cols).to_csv(args.outdir / "monthly_summary.csv", index=False)

    candidates = summary[(summary["n_resolved"] >= 100) & (summary["ambiguous_rate_valid"] <= 0.05)].copy()
    if not candidates.empty:
        candidates["edge_vs_be"] = candidates["resolved_win_rate"] - candidates["breakeven_win_rate_after_commission"]
        candidates = candidates.sort_values(["edge_vs_be", "n_resolved"], ascending=[False, False])
        top = candidates.head(10).to_dict(orient="records")
    else:
        top = []

    verdict = {
        "status": "BASELINE_ONLY_NOT_STRATEGY",
        "reason": "No pattern/filter features are used. Any positive unconditional result is descriptive, not a tradable edge claim.",
        "observations_m1": int(len(labels)),
        "top_descriptive_configs": top,
        "next_step": "Add one strictly causal feature family at a time and test probability lift with chronological OOS/holdout.",
    }
    (args.outdir / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")

    print("\n=== BASELINE SUMMARY ===", flush=True)
    with pd.option_context("display.max_rows", 200, "display.width", 220, "display.max_columns", 30):
        print(summary.to_string(index=False), flush=True)
    print("\n=== VERDICT ===", flush=True)
    print(json.dumps(verdict, indent=2), flush=True)


if __name__ == "__main__":
    main()
