#!/usr/bin/env python3
"""GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H

Independent historical replay audit on the already-collected frozen AMP GC and
FTMO-Demo XAU raw data. No parameter search and no new market data.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
AMP_ZIP = ROOT / "_lab013h" / "amp_gc.zip"
XAU_DIR = ROOT / "_lab013h_xau"
BASE = ROOT / "gc_m1_orderflow_edge_discovery_003.py"
LAB004_EVENTS = ROOT / "GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004_EVENTS.csv"
LAB009_JSON = ROOT / "GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009.json"
OUT_JSON = ROOT / "GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H.json"
OUT_MD = ROOT / "GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H.md"
OUT_GC_DIFF = ROOT / "GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H_GC_DIFF.csv"
OUT_E13 = ROOT / "GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H_E1_E3.csv"

AMP_SHA = "81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b"
EXPECTED_XAU_FILES = 32
EXPECTED_XAU_VALID_QUOTES = 8_236_717
EXPECTED_XAU_FIRST = 1785719100005
EXPECTED_XAU_LAST = 1789516199707
EXPECTED_CLOCK_OFFSET_MIN = 180
CLOCK_OFFSETS = tuple(range(-240, 241, 30))
STALE_MS = 5000
STOP_ATR = 1.5
RR = 3.0
HARD_HORIZON_MIN = 30
EXTRA_COST_R = 0.05
SPLIT = pd.Timestamp("2026-09-01T00:00:00Z")

NUM_TOLS = {
    "open": 1e-10,
    "high": 1e-10,
    "low": 1e-10,
    "close": 1e-10,
    "buy_vol": 1e-8,
    "sell_vol": 1e-8,
    "delta_frac": 1e-12,
    "atr14": 1e-10,
    "body_atr": 1e-12,
    "close_pos": 1e-12,
    "q90_delta": 1e-12,
    "q75_buy": 1e-8,
    "prior20_high": 1e-10,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_base():
    spec = importlib.util.spec_from_file_location("edge003_lab013h", BASE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def canonical_amp() -> pd.DataFrame:
    mod = load_base()
    b = mod.load_amp(AMP_ZIP).copy()
    b["signal_bool"] = (
        b["aggr"].eq("BUY")
        & b["close"].gt(b["open"])
        & b["close_pos"].ge(0.75)
        & b["high"].ge(b["prior20_high"])
        & b["impact"].gt(0)
    )
    return b.sort_values("bar_ms").reset_index(drop=True)


def independent_amp() -> tuple[pd.DataFrame, dict]:
    with zipfile.ZipFile(AMP_ZIP) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise SystemExit(f"Expected one AMP CSV in ZIP, found {names}")
        with zf.open(names[0]) as raw:
            d = pd.read_csv(
                io.TextIOWrapper(raw, encoding="utf-8-sig"),
                usecols=["time_msc", "last", "volume", "volume_real", "is_buy", "is_sell"],
                low_memory=False,
            )
    raw_rows = int(len(d))
    for c in ("time_msc", "last", "volume", "volume_real", "is_buy", "is_sell"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    vr = d.volume_real.fillna(0.0)
    vi = d.volume.fillna(0.0)
    d["vol"] = np.where(vr > 0, vr, vi)
    buyflag = d.is_buy.fillna(0).astype(int).eq(1)
    sellflag = d.is_sell.fillna(0).astype(int).eq(1)
    d["side"] = np.where(buyflag & ~sellflag, "BUY", np.where(sellflag & ~buyflag, "SELL", "EXCLUDE"))
    audit = {
        "raw_rows": raw_rows,
        "dual_flag_rows": int((buyflag & sellflag).sum()),
        "neither_flag_rows": int((~buyflag & ~sellflag).sum()),
    }
    d = d[d.time_msc.notna() & d["last"].gt(0) & d.vol.gt(0)].copy()
    audit["positive_trade_rows"] = int(len(d))
    audit["excluded_direction_rows_after_price_volume_filter"] = int(d.side.eq("EXCLUDE").sum())
    d = d[d.side.isin(["BUY", "SELL"])].copy()
    d = d.sort_values("time_msc", kind="mergesort").reset_index(drop=True)
    audit["exclusive_direction_rows"] = int(len(d))
    d["bar_ms"] = (d.time_msc.astype(np.int64) // 60000) * 60000
    d["buy_size"] = np.where(d.side.eq("BUY"), d.vol, 0.0)
    d["sell_size"] = np.where(d.side.eq("SELL"), d.vol, 0.0)
    g = d.groupby("bar_ms", sort=True, observed=True)
    b = g["last"].agg(open="first", high="max", low="min", close="last")
    b["buy_vol"] = g.buy_size.sum()
    b["sell_vol"] = g.sell_size.sum()
    b["volume"] = b.buy_vol + b.sell_vol
    b["delta"] = b.buy_vol - b.sell_vol
    b["delta_frac"] = b.delta / b.volume
    pc = b.close.shift(1)
    b["tr"] = pd.concat(
        [(b.high - b.low), (b.high - pc).abs(), (b.low - pc).abs()], axis=1
    ).max(axis=1)
    if len(b):
        b.iloc[0, b.columns.get_loc("tr")] = np.nan
    b["atr14"] = b.tr.rolling(14, min_periods=14).mean()
    b["body_atr"] = (b.close - b.open) / b.atr14
    rng = (b.high - b.low).replace(0, np.nan)
    b["close_pos"] = ((b.close - b.low) / rng).fillna(0.5)
    b["q90_delta"] = b.delta_frac.shift(1).rolling(240, min_periods=240).quantile(0.90)
    b["q75_buy"] = b.buy_vol.shift(1).rolling(240, min_periods=240).quantile(0.75)
    b["prior20_high"] = b.high.shift(1).rolling(20, min_periods=20).max()
    b["a_buy"] = b.delta_frac.ge(b.q90_delta) & b.buy_vol.ge(b.q75_buy)
    b["signal_bool"] = (
        b.a_buy
        & b.close.gt(b.open)
        & b.close_pos.ge(0.75)
        & b.high.ge(b.prior20_high)
        & b.body_atr.gt(0)
    )
    b = b.reset_index()
    b["time"] = pd.to_datetime(b.bar_ms, unit="ms", utc=True)
    audit["reconstructed_m1_bars"] = int(len(b))
    return b, audit


def compare_gc(c: pd.DataFrame, i: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    fields = list(NUM_TOLS)
    cc = c[["bar_ms", *fields, "a_buy", "signal_bool"]].copy()
    ii = i[["bar_ms", *fields, "a_buy", "signal_bool"]].copy()
    m = cc.merge(ii, on="bar_ms", how="outer", suffixes=("_canonical", "_independent"), indicator=True)
    out = {
        "canonical_bars": int(len(cc)),
        "independent_bars": int(len(ii)),
        "paired_bars": int((m._merge == "both").sum()),
        "canonical_only_bars": int((m._merge == "left_only").sum()),
        "independent_only_bars": int((m._merge == "right_only").sum()),
        "numeric": {},
    }
    both = m[m._merge.eq("both")].copy()
    for f, tol in NUM_TOLS.items():
        a = pd.to_numeric(both[f"{f}_canonical"], errors="coerce").to_numpy(float)
        b = pd.to_numeric(both[f"{f}_independent"], errors="coerce").to_numpy(float)
        same_nan = np.isnan(a) & np.isnan(b)
        finite = np.isfinite(a) & np.isfinite(b)
        err = np.full(len(a), np.nan)
        err[finite] = np.abs(a[finite] - b[finite])
        bad = ~(same_nan | (finite & (err <= tol)))
        max_abs = float(np.nanmax(err)) if np.any(np.isfinite(err)) else 0.0
        out["numeric"][f] = {"tolerance": tol, "mismatch": int(bad.sum()), "max_abs_error": max_abs}
        both[f"diff_{f}"] = err
    for f in ("a_buy", "signal_bool"):
        a = both[f"{f}_canonical"].astype(bool).to_numpy()
        b = both[f"{f}_independent"].astype(bool).to_numpy()
        out[f"{f}_mismatch"] = int(np.sum(a != b))
        out[f"{f}_true_canonical"] = int(a.sum())
        out[f"{f}_true_independent"] = int(b.sum())
    diffcols = ["bar_ms", "_merge"] + [c for c in both.columns if c.startswith("diff_")]
    return out, both[diffcols]


def independent_events(b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sig_idx = np.flatnonzero(b.signal_bool.to_numpy(bool))
    for idx in sig_idx:
        if idx + 1 >= len(b):
            continue
        cur = b.iloc[idx]
        ent = b.iloc[idx + 1]
        if ent.time != cur.time + pd.Timedelta(minutes=1):
            continue
        atr = float(cur.atr14)
        if not np.isfinite(atr) or atr <= 0:
            continue
        row = {
            "signal_time": cur.time,
            "entry_time": ent.time,
            "atr14": atr,
            "entry": float(ent.open),
        }
        for h in (5, 15):
            j = idx + h
            col = f"fwd_{h}m_atr"
            if j >= len(b) or b.iloc[j].time != ent.time + pd.Timedelta(minutes=h - 1):
                row[col] = np.nan
            else:
                row[col] = (float(b.iloc[j].close) - row["entry"]) / atr
        rows.append(row)
    return pd.DataFrame(rows)


def compare_lab004(ev: pd.DataFrame) -> dict:
    old = pd.read_csv(LAB004_EVENTS, low_memory=False)
    old = old[(old.source_feed == "AMP") & (old.rule == "BUYER_BREAKOUT_LONG")].copy()
    old["signal_time"] = pd.to_datetime(old.signal_time, utc=True)
    new = ev.copy()
    new["signal_time"] = pd.to_datetime(new.signal_time, utc=True)
    os = set(old.signal_time.astype(str))
    ns = set(new.signal_time.astype(str))
    merged = old[["signal_time", "fwd_5m_atr", "fwd_15m_atr"]].merge(
        new[["signal_time", "fwd_5m_atr", "fwd_15m_atr"]], on="signal_time", how="inner", suffixes=("_lab004", "_replay")
    )
    ret = {}
    for h in (5, 15):
        a = pd.to_numeric(merged[f"fwd_{h}m_atr_lab004"], errors="coerce").to_numpy(float)
        b = pd.to_numeric(merged[f"fwd_{h}m_atr_replay"], errors="coerce").to_numpy(float)
        mask = np.isfinite(a) & np.isfinite(b)
        diff = np.abs(a[mask] - b[mask])
        ret[str(h)] = {
            "paired_finite": int(mask.sum()),
            "max_abs_error": float(diff.max()) if len(diff) else None,
            "mismatch_gt_1e-12": int((diff > 1e-12).sum()) if len(diff) else 0,
        }
    return {
        "lab004_amp_events": int(len(old)),
        "replay_amp_events": int(len(new)),
        "timestamp_matches": int(len(os & ns)),
        "lab004_only": int(len(os - ns)),
        "replay_only": int(len(ns - os)),
        "returns": ret,
    }


def read_xau_ticks() -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    files = sorted(p for p in XAU_DIR.glob("XAUUSD_raw_ticks_*.csv") if ".meta." not in p.name)
    frames = []
    stats = []
    valid_total = 0
    monotonic_files = True
    crossed_rows = 0
    for p in files:
        d = pd.read_csv(p, usecols=lambda c: c in {"time_msc", "bid", "ask", "quote_valid"}, low_memory=False)
        if d.empty:
            continue
        for c in ("time_msc", "bid", "ask"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        raw_t = d.time_msc.dropna().to_numpy(np.int64)
        if len(raw_t) and np.any(np.diff(raw_t) < 0):
            monotonic_files = False
        if "quote_valid" in d.columns:
            q = pd.to_numeric(d.quote_valid, errors="coerce").fillna(0).eq(1)
        else:
            q = d.bid.gt(0) & d.ask.gt(0)
        valid = d[q & d.time_msc.notna() & d.bid.gt(0) & d.ask.gt(0)].copy()
        crossed_rows += int(valid.ask.lt(valid.bid).sum())
        valid = valid[valid.ask.ge(valid.bid)]
        if valid.empty:
            continue
        valid_total += int(len(valid))
        stats.append({"file": p.name, "rows": int(len(valid)), "first": int(valid.time_msc.iloc[0]), "last": int(valid.time_msc.iloc[-1])})
        frames.append(valid[["time_msc", "bid", "ask"]])
    if not frames:
        raise SystemExit("No XAU quote-valid ticks")
    x = pd.concat(frames, ignore_index=True)
    first_before = int(x.time_msc.min())
    last_before = int(x.time_msc.max())
    x = x.sort_values("time_msc", kind="mergesort").drop_duplicates(["time_msc", "bid", "ask"]).reset_index(drop=True)
    t = x.time_msc.to_numpy(np.int64)
    b = x.bid.to_numpy(float)
    a = x.ask.to_numpy(float)
    audit = {
        "nonempty_files": int(len(stats)),
        "quote_valid_rows_before_dedup": int(valid_total),
        "rows_after_price_dedup": int(len(x)),
        "first_time_msc": first_before,
        "last_time_msc": last_before,
        "per_file_monotonic": bool(monotonic_files),
        "crossed_quote_rows": int(crossed_rows),
        "expected": {
            "files": EXPECTED_XAU_FILES,
            "quote_valid_rows": EXPECTED_XAU_VALID_QUOTES,
            "first": EXPECTED_XAU_FIRST,
            "last": EXPECTED_XAU_LAST,
        },
    }
    return t, b, a, audit


def build_xau_m1(times: np.ndarray, bids: np.ndarray, asks: np.ndarray) -> pd.DataFrame:
    minute = (times // 60000) * 60000
    mid = (bids + asks) / 2.0
    d = pd.DataFrame({"minute_ms": minute, "mid": mid})
    g = d.groupby("minute_ms", sort=True, observed=True).mid
    out = g.agg(open="first", high="max", low="min", close="last").reset_index()
    prev = out.close.shift(1)
    tr = pd.concat([(out.high - out.low), (out.high - prev).abs(), (out.low - prev).abs()], axis=1).max(axis=1)
    if len(tr):
        tr.iloc[0] = np.nan
    out["atr14"] = tr.rolling(14, min_periods=14).mean()
    dt = out.minute_ms.diff()
    out["ret"] = out.close.pct_change()
    out.loc[dt.ne(60000), "ret"] = np.nan
    return out


def calibrate_clock(gc: pd.DataFrame, xau_m1: pd.DataFrame) -> tuple[int, list[dict]]:
    a = gc[["time", "close"]].copy().sort_values("time")
    a["ret"] = a.close.pct_change()
    a.loc[a.time.diff().ne(pd.Timedelta(minutes=1)), "ret"] = np.nan
    a["minute_utc_ms"] = (a.time.astype("int64") // 1_000_000).astype(np.int64)
    a = a[["minute_utc_ms", "ret"]].dropna().rename(columns={"ret": "gc_ret"})
    base = xau_m1[["minute_ms", "ret"]].dropna().copy()
    rows = []
    for off in CLOCK_OFFSETS:
        z = base.copy()
        z["minute_utc_ms"] = z.minute_ms.astype(np.int64) - off * 60000
        m = a.merge(z[["minute_utc_ms", "ret"]], on="minute_utc_ms", how="inner")
        m = m.replace([np.inf, -np.inf], np.nan).dropna()
        corr = float(m.gc_ret.corr(m.ret)) if len(m) >= 100 else np.nan
        rows.append({"offset_min": int(off), "n_common": int(len(m)), "corr": corr})
    valid = [r for r in rows if np.isfinite(r["corr"])]
    best = sorted(valid, key=lambda r: (r["corr"], r["n_common"]), reverse=True)[0]
    return int(best["offset_min"]), rows


def first_tick(times: np.ndarray, target: int):
    i = int(np.searchsorted(times, target, side="left"))
    if i >= len(times):
        return None, None
    lag = int(times[i] - target)
    if lag < 0 or lag > STALE_MS:
        return None, lag
    return i, lag


def make_executable_events(ev: pd.DataFrame, times, bids, asks, atr_map: dict, offset_min: int) -> pd.DataFrame:
    rows = []
    for row in ev.itertuples(index=False):
        entry_time = pd.Timestamp(row.entry_time)
        if entry_time.tzinfo is None:
            entry_time = entry_time.tz_localize("UTC")
        else:
            entry_time = entry_time.tz_convert("UTC")
        utc_ms = int(entry_time.value // 1_000_000)
        broker_target = utc_ms + offset_min * 60000
        mi, lag = first_tick(times, broker_target)
        if mi is None:
            continue
        prev_min = broker_target - 60000
        atr = float(atr_map.get(prev_min, np.nan))
        if not np.isfinite(atr) or atr <= 0:
            continue
        ask = float(asks[mi]); bid = float(bids[mi])
        if ask <= 0 or bid <= 0 or ask < bid:
            continue
        rows.append({
            "signal_time_utc": pd.Timestamp(row.signal_time).tz_convert("UTC"),
            "entry_time_utc": entry_time,
            "signal_utc_ms": int(pd.Timestamp(row.signal_time).value // 1_000_000),
            "broker_target_msc": int(broker_target),
            "market_idx": int(mi),
            "entry_tick_msc": int(times[mi]),
            "entry_lag_ms": int(lag),
            "market_bid": bid,
            "market_ask": ask,
            "atr": atr,
        })
    return pd.DataFrame(rows).sort_values("signal_time_utc").reset_index(drop=True)


def last_before_or_at(times: np.ndarray, target: int):
    i = int(np.searchsorted(times, target, side="right")) - 1
    return i if i >= 0 else None


def simulate_candidate(events: pd.DataFrame, times, bids, asks, expiry_min: int) -> pd.DataFrame:
    rows = []
    for e in events.itertuples(index=False):
        signal0 = int(e.broker_target_msc)
        mi = int(e.market_idx)
        atr = float(e.atr)
        limit = float(e.market_ask - atr)
        expiry = signal0 + expiry_min * 60000
        j_end = int(np.searchsorted(times, expiry, side="right"))
        hits = np.flatnonzero(asks[mi:j_end] <= limit + 1e-12) if j_end > mi else np.array([], dtype=int)
        rec = {
            "signal_time_utc": e.signal_time_utc,
            "signal_utc_ms": int(e.signal_utc_ms),
            "expiry_min": int(expiry_min),
            "filled": False,
            "fill_time_msc": np.nan,
            "status": "NO_FILL",
            "raw_r": 0.0,
            "exit_time_msc": np.nan,
        }
        if len(hits):
            fi = mi + int(hits[0])
            fill_ts = int(times[fi])
            stop = limit - STOP_ATR * atr
            target = limit + RR * STOP_ATR * atr
            hard_end = signal0 + HARD_HORIZON_MIN * 60000
            last = last_before_or_at(times, hard_end)
            rec["filled"] = True
            rec["fill_time_msc"] = fill_ts
            if last is None or last < fi:
                rec["status"] = "DATA_GAP"
                rec["raw_r"] = np.nan
            else:
                path = bids[fi:last + 1]
                sh = np.flatnonzero(path <= stop + 1e-12)
                th = np.flatnonzero(path >= target - 1e-12)
                si = int(sh[0]) if len(sh) else None
                ti = int(th[0]) if len(th) else None
                if si is not None and (ti is None or si <= ti):
                    k = fi + si
                    rec.update(status="SL", raw_r=-1.0, exit_time_msc=int(times[k]))
                elif ti is not None:
                    k = fi + ti
                    rec.update(status="TP", raw_r=RR, exit_time_msc=int(times[k]))
                else:
                    xi, _ = first_tick(times, hard_end)
                    if xi is None or xi < fi:
                        rec.update(status="DATA_GAP", raw_r=np.nan)
                    else:
                        rval = (float(bids[xi]) - limit) / (STOP_ATR * atr)
                        rec.update(status="TIMEOUT", raw_r=float(rval), exit_time_msc=int(times[xi]))
        rows.append(rec)
    return pd.DataFrame(rows)


def pf(v: np.ndarray) -> float:
    p = float(v[v > 0].sum()); n = float(-v[v < 0].sum())
    if n == 0:
        return float("inf") if p > 0 else np.nan
    return p / n


def max_dd(v: np.ndarray) -> float:
    if len(v) == 0:
        return np.nan
    eq = np.cumsum(np.nan_to_num(v, nan=0.0))
    peaks = np.maximum.accumulate(np.r_[0.0, eq])
    return float((peaks[1:] - eq).max()) if len(eq) else 0.0


def apply_one_active(z: pd.DataFrame, offset_min: int) -> pd.DataFrame:
    q = z.sort_values("signal_time_utc").copy().reset_index(drop=True)
    q["accepted"] = False
    q["busy_skip"] = False
    busy_until_utc = -10**30
    off_ms = offset_min * 60000
    for idx, r in q.iterrows():
        s = int(r.signal_utc_ms)
        if s < busy_until_utc:
            q.at[idx, "busy_skip"] = True
            continue
        q.at[idx, "accepted"] = True
        if bool(r.filled) and np.isfinite(r.exit_time_msc):
            busy_until_utc = int(r.exit_time_msc) - off_ms
        else:
            busy_until_utc = s + int(r.expiry_min) * 60000
    q["stress_r"] = 0.0
    valid = q.accepted & q.raw_r.notna()
    q.loc[valid, "stress_r"] = q.loc[valid, "raw_r"]
    cost = q.accepted & q.filled & q.raw_r.notna()
    q.loc[cost, "stress_r"] = q.loc[cost, "stress_r"] - EXTRA_COST_R
    return q


def metrics(q: pd.DataFrame) -> dict:
    accepted = q.accepted
    filled = q.accepted & q.filled & q.raw_r.notna()
    fill_r = q.loc[filled, "raw_r"].to_numpy(float) - EXTRA_COST_R
    r = q.stress_r.to_numpy(float)
    early = q[q.signal_time_utc < SPLIT].stress_r
    late = q[q.signal_time_utc >= SPLIT].stress_r
    return {
        "original_signals": int(len(q)),
        "accepted_signals": int(accepted.sum()),
        "fills": int(filled.sum()),
        "fill_rate_original_pct": float(filled.sum() / len(q) * 100) if len(q) else None,
        "ev_r_per_original_signal": float(r.mean()) if len(r) else None,
        "ev_r_per_accepted_signal": float(r.sum() / accepted.sum()) if accepted.sum() else None,
        "ev_r_per_fill": float(fill_r.mean()) if len(fill_r) else None,
        "pf": float(pf(r)) if len(r) else None,
        "max_dd_r": max_dd(r),
        "early_ev_r_per_original_signal": float(early.mean()) if len(early) else None,
        "late_ev_r_per_original_signal": float(late.mean()) if len(late) else None,
    }


def compare_lab009(replay: dict) -> dict:
    frozen = json.loads(LAB009_JSON.read_text(encoding="utf-8"))
    ref = frozen["detail"]["AMP_ALL"]["D1.00_E3M"]["ONE_ACTIVE_SETUP"]["0.050R"]
    keys = [
        "original_signals", "accepted_signals", "fills", "fill_rate_original_pct",
        "ev_r_per_original_signal", "ev_r_per_accepted_signal", "ev_r_per_fill", "pf",
        "max_dd_r", "early_ev_r_per_original_signal", "late_ev_r_per_original_signal",
    ]
    out = {}
    for k in keys:
        a, b = ref[k], replay[k]
        if isinstance(a, int) and isinstance(b, int):
            ok = a == b; diff = b - a
        else:
            diff = float(b) - float(a)
            ok = abs(diff) <= 1e-10
        out[k] = {"frozen": a, "replay": b, "diff": diff, "pass": bool(ok)}
    out["all_pass"] = bool(all(v["pass"] for v in out.values() if isinstance(v, dict) and "pass" in v))
    return out


def main():
    source_sha = sha256_file(AMP_ZIP)
    canon = canonical_amp()
    indep, amp_audit = independent_amp()
    gc_parity, gc_diff = compare_gc(canon, indep)
    gc_diff.to_csv(OUT_GC_DIFF, index=False)

    ev = independent_events(indep)
    lab004 = compare_lab004(ev)

    times, bids, asks, xau_audit = read_xau_ticks()
    xau_m1 = build_xau_m1(times, bids, asks)
    best_offset, clock_rows = calibrate_clock(indep, xau_m1)
    atr_map = dict(zip(xau_m1.minute_ms.astype(np.int64), xau_m1.atr14.astype(float)))
    executable = make_executable_events(ev, times, bids, asks, atr_map, best_offset)

    e3_raw = simulate_candidate(executable, times, bids, asks, 3)
    e1_raw = simulate_candidate(executable, times, bids, asks, 1)
    e3 = apply_one_active(e3_raw, best_offset)
    e1 = apply_one_active(e1_raw, best_offset)
    m3 = metrics(e3); m1 = metrics(e1)
    pd.concat([e1.assign(candidate="D1.00_E1M"), e3.assign(candidate="D1.00_E3M")], ignore_index=True).to_csv(OUT_E13, index=False)
    lab009 = compare_lab009(m3)

    numeric_pass = all(v["mismatch"] == 0 for v in gc_parity["numeric"].values())
    xau_expected = (
        xau_audit["nonempty_files"] == EXPECTED_XAU_FILES
        and xau_audit["quote_valid_rows_before_dedup"] == EXPECTED_XAU_VALID_QUOTES
        and xau_audit["first_time_msc"] == EXPECTED_XAU_FIRST
        and xau_audit["last_time_msc"] == EXPECTED_XAU_LAST
        and xau_audit["per_file_monotonic"]
        and xau_audit["crossed_quote_rows"] == 0
    )
    gates = {
        "amp_sha_exact": source_sha == AMP_SHA,
        "gc_bar_timestamp_parity": gc_parity["canonical_only_bars"] == 0 and gc_parity["independent_only_bars"] == 0,
        "gc_numeric_parity": numeric_pass,
        "gc_a_buy_parity": gc_parity["a_buy_mismatch"] == 0,
        "gc_signal_parity": gc_parity["signal_bool_mismatch"] == 0,
        "lab004_event_timestamp_parity": lab004["lab004_only"] == 0 and lab004["replay_only"] == 0,
        "lab004_return_parity": all(lab004["returns"][str(h)]["mismatch_gt_1e-12"] == 0 for h in (5, 15)),
        "xau_frozen_inventory_exact": xau_expected,
        "clock_offset_reproduced": best_offset == EXPECTED_CLOCK_OFFSET_MIN,
        "lab009_d1e3_metrics_reproduced": bool(lab009["all_pass"]),
    }
    status = "HISTORICAL_REPLAY_PASS" if all(gates.values()) else "HISTORICAL_REPLAY_FAIL"
    result = {
        "lab": "GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H",
        "status": status,
        "governance": "Historical internal reproducibility only; not independent OOS.",
        "amp_source_sha": source_sha,
        "amp_raw_audit": amp_audit,
        "gc_parity": gc_parity,
        "lab004_reproduction": lab004,
        "xau_raw_audit": xau_audit,
        "clock_calibration": {"best_offset_min": best_offset, "grid": clock_rows},
        "executable_amp_events": int(len(executable)),
        "d1_e3_replay": m3,
        "d1_e1_historical_diagnostic": m1,
        "lab009_d1e3_comparison": lab009,
        "gates": gates,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str, allow_nan=True), encoding="utf-8")

    lines = [
        "# GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H",
        "",
        f"**Status: {status}**",
        "",
        "Uses only the already-collected frozen AMP GC and FTMO-Demo XAU raw data. No new market data and no retuning.",
        "",
        "## Gates",
        "",
    ]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "",
        "## GC independent replay",
        "",
        f"- AMP raw rows: {amp_audit['raw_rows']:,}",
        f"- exclusive directional rows: {amp_audit['exclusive_direction_rows']:,}",
        f"- reconstructed M1 bars: canonical {gc_parity['canonical_bars']:,} / independent {gc_parity['independent_bars']:,}",
        f"- a_buy mismatches: {gc_parity['a_buy_mismatch']}",
        f"- signal mismatches: {gc_parity['signal_bool_mismatch']}",
        f"- LAB004 AMP events: frozen {lab004['lab004_amp_events']} / replay {lab004['replay_amp_events']} / exact timestamp matches {lab004['timestamp_matches']}",
        "",
        "## FTMO XAU raw inventory",
        "",
        f"- files: {xau_audit['nonempty_files']} (expected {EXPECTED_XAU_FILES})",
        f"- quote-valid rows: {xau_audit['quote_valid_rows_before_dedup']:,} (expected {EXPECTED_XAU_VALID_QUOTES:,})",
        f"- first/last `time_msc`: {xau_audit['first_time_msc']} / {xau_audit['last_time_msc']}",
        f"- crossed quotes: {xau_audit['crossed_quote_rows']}",
        f"- best GC/XAU clock offset: {best_offset:+d} min",
        f"- executable AMP events: {len(executable)}",
        "",
        "## Frozen D1.00 E3 operational replay (+0.05R/fill, one-active)",
        "",
        f"- signals: {m3['original_signals']}; accepted {m3['accepted_signals']}; fills {m3['fills']}",
        f"- EV/original signal: {m3['ev_r_per_original_signal']:+.6f}R",
        f"- EV/fill: {m3['ev_r_per_fill']:+.6f}R",
        f"- PF: {m3['pf']:.6f}",
        f"- MaxDD: {m3['max_dd_r']:.6f}R",
        f"- early/late EV: {m3['early_ev_r_per_original_signal']:+.6f} / {m3['late_ev_r_per_original_signal']:+.6f} R/signal",
        f"- exact LAB009 core-metric reproduction: {'PASS' if lab009['all_pass'] else 'FAIL'}",
        "",
        "## D1.00 E1 historical diagnostic — NOT promoted",
        "",
        f"- signals: {m1['original_signals']}; accepted {m1['accepted_signals']}; fills {m1['fills']}",
        f"- EV/original signal: {m1['ev_r_per_original_signal']:+.6f}R",
        f"- EV/fill: {m1['ev_r_per_fill']:+.6f}R",
        f"- PF: {m1['pf']:.6f}",
        f"- MaxDD: {m1['max_dd_r']:.6f}R",
        f"- early/late EV: {m1['early_ev_r_per_original_signal']:+.6f} / {m1['late_ev_r_per_original_signal']:+.6f} R/signal",
        "",
        "## Interpretation",
        "",
        "A PASS proves internal historical reproducibility of the collected-data pipeline. It does not create untouched OOS evidence and does not retroactively validate E1 as production logic.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "gates": gates, "e3": m3, "e1": m1}, indent=2, default=str))


if __name__ == "__main__":
    main()
