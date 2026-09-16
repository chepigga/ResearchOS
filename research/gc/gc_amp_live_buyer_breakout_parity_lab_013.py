#!/usr/bin/env python3
"""GC_AMP_LIVE_BUYER_BREAKOUT_PARITY_LAB_013

Forward-only implementation/data parity audit for BUYER_BREAKOUT_LONG_001.

Path A: realtime MT5 snapshots written at decision time.
Path B: independent offline rebuild from AMP/CQG raw ticks.

No strategy discovery, retuning, or PnL optimization is performed here.
"""
from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
LAB = "GC_AMP_LIVE_BUYER_BREAKOUT_PARITY_LAB_013"
SENSOR = "BUYER_BREAKOUT_LONG_001"
FREEZE_COMMIT = "80334cb9550682a1d2e440f73ee4b70033f052e9"
FREEZE_TS = pd.Timestamp("2026-09-16T21:06:12Z")
FREEZE_MS = FREEZE_TS.value // 1_000_000

OUT_JSON = ROOT / f"{LAB}.json"
OUT_MD = ROOT / f"{LAB}.md"
OUT_PAIRS = ROOT / f"{LAB}_PAIRS.csv"

DEFAULT_SNAPSHOT = ROOT / "_lab013_inputs" / "AMP_GC_LIVE_SNAPSHOTS.csv"
DEFAULT_RAW = ROOT / "_lab013_inputs" / "AMP_GC_LIVE_RAW_TICKS.csv"

MIN_PAIRED_BARS = 500
MIN_SIGNALS = 5

TOLS = {
    "open": 1e-8,
    "high": 1e-8,
    "low": 1e-8,
    "close": 1e-8,
    "buy_vol": 1e-8,
    "sell_vol": 1e-8,
    "delta_frac": 1e-10,
    "q90_delta": 1e-10,
    "q75_buy": 1e-8,
    "prior20_high": 1e-8,
    "atr14": 1e-8,
    "close_pos": 1e-10,
    "body_atr": 1e-10,
}

REQ_SNAPSHOT = {
    "record_version", "logger_version", "freeze_commit", "symbol",
    "bar_time_utc_ms", "decision_time_utc_ms", "warmup_ok",
    "open", "high", "low", "close", "buy_vol", "sell_vol", "volume", "delta",
    "delta_frac", "atr14", "body_atr", "close_pos", "q90_delta", "q75_buy",
    "prior20_high", "a_buy", "signal_bool", "raw_tick_count",
    "exclusive_tick_count", "dual_flag_count", "excluded_flag_count", "void_record",
}

REQ_RAW = {"time_msc", "last", "volume", "volume_real", "is_buy", "is_sell"}


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin({"1", "true", "t", "yes", "y"})


def read_csv_or_zip(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csvs:
                raise SystemExit(f"No CSV inside {path}")
            if len(csvs) > 1:
                tickish = [n for n in csvs if "tick" in n.lower()]
                name = tickish[0] if tickish else csvs[0]
            else:
                name = csvs[0]
            with zf.open(name) as raw:
                return pd.read_csv(io.TextIOWrapper(raw, encoding="utf-8-sig"))
    return pd.read_csv(path)


def prepare_ticks(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    missing = sorted(REQ_RAW - set(raw.columns))
    if missing:
        raise SystemExit(f"Raw AMP file missing columns: {missing}")

    d = raw.copy()
    tms = pd.to_numeric(d["time_msc"], errors="coerce")
    px = pd.to_numeric(d["last"], errors="coerce")
    vr = pd.to_numeric(d["volume_real"], errors="coerce").fillna(0.0)
    vi = pd.to_numeric(d["volume"], errors="coerce").fillna(0.0)
    vol = np.where(vr > 0, vr, vi).astype(float)
    ib = pd.to_numeric(d["is_buy"], errors="coerce").fillna(0).astype(int).eq(1)
    ise = pd.to_numeric(d["is_sell"], errors="coerce").fillna(0).astype(int).eq(1)

    dual = ib & ise
    exclusive_buy = ib & ~ise
    exclusive_sell = ise & ~ib
    aggr = np.where(exclusive_buy, "BUY", np.where(exclusive_sell, "SELL", "EXCLUDE"))

    t = pd.DataFrame({
        "time_ms": tms,
        "price": px,
        "volume": vol,
        "aggressor": aggr,
        "dual": dual,
    })
    basic_valid = t["time_ms"].notna() & t["price"].notna() & (t["price"] > 0) & (t["volume"] > 0)
    diagnostics = {
        "raw_rows": int(len(t)),
        "basic_valid_rows": int(basic_valid.sum()),
        "dual_flag_rows": int((basic_valid & dual).sum()),
        "excluded_flag_rows": int((basic_valid & pd.Series(aggr, index=t.index).eq("EXCLUDE")).sum()),
    }
    t = t.loc[basic_valid & t["aggressor"].isin(["BUY", "SELL"])].copy()
    t["time_ms"] = t["time_ms"].astype("int64")
    t = t.sort_values("time_ms", kind="mergesort").reset_index(drop=True)
    diagnostics["exclusive_directional_rows"] = int(len(t))
    return t, diagnostics


def rebuild(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    t, diagnostics = prepare_ticks(raw)
    if t.empty:
        return pd.DataFrame(), diagnostics

    t["bar_time_utc_ms"] = (t["time_ms"] // 60000) * 60000
    t["buy_size"] = np.where(t["aggressor"].eq("BUY"), t["volume"], 0.0)
    t["sell_size"] = np.where(t["aggressor"].eq("SELL"), t["volume"], 0.0)

    g = t.groupby("bar_time_utc_ms", sort=True, observed=True)
    b = g["price"].agg(open="first", high="max", low="min", close="last")
    b["buy_vol"] = g["buy_size"].sum()
    b["sell_vol"] = g["sell_size"].sum()
    b["volume"] = b["buy_vol"] + b["sell_vol"]
    b["delta"] = b["buy_vol"] - b["sell_vol"]
    b["delta_frac"] = b["delta"] / b["volume"]

    pc = b["close"].shift(1)
    b["tr"] = pd.concat(
        [(b["high"] - b["low"]), (b["high"] - pc).abs(), (b["low"] - pc).abs()],
        axis=1,
    ).max(axis=1)
    if len(b):
        b.iloc[0, b.columns.get_loc("tr")] = np.nan
    b["atr14"] = b["tr"].rolling(14, min_periods=14).mean()
    b["body_atr"] = (b["close"] - b["open"]) / b["atr14"]

    bar_range = (b["high"] - b["low"]).replace(0, np.nan)
    b["close_pos"] = ((b["close"] - b["low"]) / bar_range).fillna(0.5)

    b["q90_delta"] = b["delta_frac"].shift(1).rolling(240, min_periods=240).quantile(0.90)
    b["q75_buy"] = b["buy_vol"].shift(1).rolling(240, min_periods=240).quantile(0.75)
    b["prior20_high"] = b["high"].shift(1).rolling(20, min_periods=20).max()

    b["a_buy"] = (b["delta_frac"] >= b["q90_delta"]) & (b["buy_vol"] >= b["q75_buy"])
    b["signal_bool"] = (
        b["a_buy"]
        & (b["close"] > b["open"])
        & (b["close_pos"] >= 0.75)
        & (b["high"] >= b["prior20_high"])
        & (b["body_atr"] > 0)
    )
    b["warmup_ok"] = b[["atr14", "q90_delta", "q75_buy", "prior20_high"]].notna().all(axis=1)
    b["raw_tick_count"] = g.size().astype(int)
    b = b.reset_index()
    return b, diagnostics


def resolve_snapshot(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    missing = sorted(REQ_SNAPSHOT - set(df.columns))
    if missing:
        raise SystemExit(f"Snapshot file missing columns: {missing}")

    x = df.copy()
    x["record_version"] = pd.to_numeric(x["record_version"], errors="coerce").fillna(1).astype(int)
    x["bar_time_utc_ms"] = pd.to_numeric(x["bar_time_utc_ms"], errors="coerce")
    x["decision_time_utc_ms"] = pd.to_numeric(x["decision_time_utc_ms"], errors="coerce")
    for c in ["warmup_ok", "a_buy", "signal_bool", "void_record"]:
        x[c] = as_bool(x[c])

    raw_dupes = int(x.duplicated(["symbol", "bar_time_utc_ms"], keep=False).sum())
    x = x.sort_values(["symbol", "bar_time_utc_ms", "record_version"], kind="stable")
    x = x.drop_duplicates(["symbol", "bar_time_utc_ms"], keep="last")
    x = x.loc[~x["void_record"]].copy()

    numeric = list(TOLS) + [
        "volume", "delta", "raw_tick_count", "exclusive_tick_count",
        "dual_flag_count", "excluded_flag_count",
    ]
    for c in numeric:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    return x, raw_dupes


def waiting(reason: str, **extra) -> dict:
    out = {
        "lab": LAB,
        "sensor": SENSOR,
        "status": "INSUFFICIENT_FRESH_PARITY_SAMPLE",
        "reason": reason,
        "freeze_commit": FREEZE_COMMIT,
        "freeze_utc": FREEZE_TS.isoformat(),
        "governance": "forward-only implementation parity; no retuning",
    }
    out.update(extra)
    return out


def write_report(res: dict) -> None:
    OUT_JSON.write_text(json.dumps(res, indent=2, default=str, allow_nan=False), encoding="utf-8")
    lines = [
        f"# {LAB}", "",
        f"Status: **{res['status']}**", "",
        f"Freeze: `{res['freeze_utc']}` / `{res['freeze_commit']}`.", "",
    ]
    if res.get("reason"):
        lines += [res["reason"], ""]

    if "summary" in res:
        s = res["summary"]
        lines += [
            "## Summary", "",
            f"- paired warmup-valid bars: **{s['paired_bars']}**",
            f"- rebuilt signals: **{s['rebuild_signals']}**",
            f"- live signals: **{s['live_signals']}**",
            f"- matched signal timestamps: **{s['matched_signal_timestamps']}**",
            f"- missing live bars: **{s['missing_live_bars']}**",
            f"- missing rebuild bars: **{s['missing_rebuild_bars']}**",
            f"- raw duplicate snapshot rows: **{s['raw_duplicate_rows']}**",
            "",
            "## Frozen parity checks", "",
            "| Check | Value | Pass |",
            "|---|---:|:---:|",
        ]
        for k, v in res["checks"].items():
            lines.append(f"| {k} | {v['value']} | {'PASS' if v['pass'] else 'FAIL'} |")

        lines += ["", "## Numeric max absolute errors", "", "| Field | Max abs error | Tolerance | Pass |", "|---|---:|---:|:---:|"]
        for k, v in res["numeric"].items():
            lines.append(f"| {k} | {v['max_abs_error']:.12g} | {v['tolerance']:.12g} | {'PASS' if v['pass'] else 'FAIL'} |")

    lines += [
        "",
        "LAB013 is an implementation/data parity audit only. It does not certify profitability or promote E1 over E3.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    args = ap.parse_args()

    if not args.snapshot.exists():
        res = waiting(f"Realtime snapshot file not found: {args.snapshot}")
        write_report(res)
        print(OUT_MD.read_text())
        return
    if not args.raw.exists():
        res = waiting(f"Raw AMP tick file not found: {args.raw}")
        write_report(res)
        print(OUT_MD.read_text())
        return

    live0 = read_csv_or_zip(args.snapshot)
    live, raw_duplicate_rows = resolve_snapshot(live0)

    live = live.loc[
        (live["bar_time_utc_ms"] > FREEZE_MS)
        & live["warmup_ok"]
        & live["freeze_commit"].astype(str).eq(FREEZE_COMMIT)
    ].copy()

    if live.empty:
        res = waiting(
            "No valid post-freeze warmup-valid realtime snapshots.",
            source_snapshot_rows=int(len(live0)),
            raw_duplicate_rows=raw_duplicate_rows,
        )
        write_report(res)
        print(OUT_MD.read_text())
        return

    symbols = sorted(live["symbol"].astype(str).unique())
    if len(symbols) != 1:
        raise SystemExit(f"LAB013 expects exactly one live GC symbol per run, got {symbols}")

    raw = read_csv_or_zip(args.raw)
    rebuilt, raw_diag = rebuild(raw)
    if rebuilt.empty:
        res = waiting("Offline rebuild produced no bars.", raw_diagnostics=raw_diag)
        write_report(res)
        print(OUT_MD.read_text())
        return

    lo = int(live["bar_time_utc_ms"].min())
    hi = int(live["bar_time_utc_ms"].max())
    rb = rebuilt.loc[
        (rebuilt["bar_time_utc_ms"] >= lo)
        & (rebuilt["bar_time_utc_ms"] <= hi)
        & rebuilt["warmup_ok"]
    ].copy()

    live_times = set(live["bar_time_utc_ms"].astype("int64"))
    rb_times = set(rb["bar_time_utc_ms"].astype("int64"))
    missing_live = sorted(rb_times - live_times)
    missing_rebuild = sorted(live_times - rb_times)
    common = sorted(live_times & rb_times)

    if not common:
        res = waiting(
            "No common warmup-valid bars between realtime snapshots and offline raw rebuild.",
            raw_diagnostics=raw_diag,
            missing_live_bars=len(missing_live),
            missing_rebuild_bars=len(missing_rebuild),
        )
        write_report(res)
        print(OUT_MD.read_text())
        return

    L = live.set_index("bar_time_utc_ms").loc[common].sort_index()
    R = rb.set_index("bar_time_utc_ms").loc[common].sort_index()

    pairs = pd.DataFrame(index=pd.Index(common, name="bar_time_utc_ms"))
    pairs["symbol"] = symbols[0]
    for c in TOLS:
        pairs[f"live_{c}"] = L[c]
        pairs[f"rebuild_{c}"] = R[c]
        pairs[f"abs_err_{c}"] = (L[c].astype(float) - R[c].astype(float)).abs()
    for c in ["a_buy", "signal_bool"]:
        pairs[f"live_{c}"] = L[c].astype(bool)
        pairs[f"rebuild_{c}"] = R[c].astype(bool)
        pairs[f"match_{c}"] = pairs[f"live_{c}"].eq(pairs[f"rebuild_{c}"])
    pairs = pairs.reset_index()
    OUT_PAIRS.parent.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(OUT_PAIRS, index=False)

    numeric = {}
    for c, tol in TOLS.items():
        errs = pairs[f"abs_err_{c}"].to_numpy(float)
        finite = np.isfinite(errs)
        maxerr = float(np.max(errs[finite])) if finite.any() else float("inf")
        numeric[c] = {
            "max_abs_error": maxerr,
            "tolerance": tol,
            "pass": bool(finite.all() and maxerr <= tol),
        }

    a_match = int(pairs["match_a_buy"].sum())
    s_match = int(pairs["match_signal_bool"].sum())

    live_sig = set(L.index[L["signal_bool"].astype(bool)].astype("int64"))
    rb_sig = set(R.index[R["signal_bool"].astype(bool)].astype("int64"))
    matched_sig = live_sig & rb_sig
    signal_set_equal = live_sig == rb_sig

    n = len(common)
    checks = {
        "paired_bars_ge_500": {"value": n, "pass": n >= MIN_PAIRED_BARS},
        "rebuilt_signals_ge_5": {"value": len(rb_sig), "pass": len(rb_sig) >= MIN_SIGNALS},
        "zero_missing_live_bars": {"value": len(missing_live), "pass": len(missing_live) == 0},
        "zero_missing_rebuild_bars": {"value": len(missing_rebuild), "pass": len(missing_rebuild) == 0},
        "a_buy_100pct": {"value": f"{a_match}/{n}", "pass": a_match == n},
        "signal_bool_100pct": {"value": f"{s_match}/{n}", "pass": s_match == n},
        "signal_timestamp_sets_equal": {
            "value": f"live={len(live_sig)}, rebuild={len(rb_sig)}, matched={len(matched_sig)}",
            "pass": signal_set_equal,
        },
        "all_numeric_within_tolerance": {
            "value": f"{sum(v['pass'] for v in numeric.values())}/{len(numeric)} fields",
            "pass": all(v["pass"] for v in numeric.values()),
        },
    }

    hard_parity_fail = any(
        not checks[k]["pass"]
        for k in [
            "zero_missing_live_bars", "zero_missing_rebuild_bars", "a_buy_100pct",
            "signal_bool_100pct", "signal_timestamp_sets_equal",
            "all_numeric_within_tolerance",
        ]
    )

    mature = checks["paired_bars_ge_500"]["pass"] and checks["rebuilt_signals_ge_5"]["pass"]
    if hard_parity_fail:
        status = "PARITY_FAIL"
    elif not mature:
        status = "INSUFFICIENT_FRESH_PARITY_SAMPLE"
    else:
        status = "LAB013_PASS"

    res = {
        "lab": LAB,
        "sensor": SENSOR,
        "status": status,
        "freeze_commit": FREEZE_COMMIT,
        "freeze_utc": FREEZE_TS.isoformat(),
        "symbol": symbols[0],
        "summary": {
            "paired_bars": n,
            "rebuild_signals": len(rb_sig),
            "live_signals": len(live_sig),
            "matched_signal_timestamps": len(matched_sig),
            "missing_live_bars": len(missing_live),
            "missing_rebuild_bars": len(missing_rebuild),
            "raw_duplicate_rows": raw_duplicate_rows,
            "first_bar_utc": pd.to_datetime(common[0], unit="ms", utc=True).isoformat(),
            "last_bar_utc": pd.to_datetime(common[-1], unit="ms", utc=True).isoformat(),
        },
        "checks": checks,
        "numeric": numeric,
        "raw_diagnostics": raw_diag,
        "signal_timestamp_diff": {
            "live_only": sorted(int(x) for x in live_sig - rb_sig),
            "rebuild_only": sorted(int(x) for x in rb_sig - live_sig),
        },
        "governance": "forward-only implementation parity; no retuning",
    }
    write_report(res)
    print(OUT_MD.read_text())


if __name__ == "__main__":
    main()
