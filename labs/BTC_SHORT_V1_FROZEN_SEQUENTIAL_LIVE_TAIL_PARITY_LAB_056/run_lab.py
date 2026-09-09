#!/usr/bin/env python3
from __future__ import annotations

import json
import types
from pathlib import Path

import numpy as np
import pandas as pd
import requests

LAB = "BTC_SHORT_V1_FROZEN_SEQUENTIAL_LIVE_TAIL_PARITY_LAB_056"
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(parents=True, exist_ok=True)
LABS = HERE.parent
L55_DIR = LABS / "BTC_SHORT_V1_FROZEN_FULL_SYSTEM_POSTFREEZE_REPLICATION_LAB_055"
L55_PY = L55_DIR / "run_lab.py"
L55_OUT = L55_DIR / "output"
SEP0 = pd.Timestamp("2026-09-01", tz="UTC")
LIVE0 = pd.Timestamp("2026-09-08", tz="UTC")
SEP9 = pd.Timestamp("2026-09-09", tz="UTC")
REST_TIMEOUT = 20

def load_lab055():
    src = L55_PY.read_text()
    src = src.replace(
        "pd.date_range('2026-09-01',DAILY_END,freq='D')",
        "pd.date_range(pd.Timestamp('2026-09-01',tz='UTC'),DAILY_END,freq='D')",
    )
    mod = types.ModuleType("lab055_frozen")
    mod.__file__ = str(L55_PY)
    mod.__dict__["__name__"] = "lab055_frozen"
    exec(compile(src, str(L55_PY), "exec"), mod.__dict__)
    mod.OUT = OUT
    return mod

def get_json(paths, params):
    errors = []
    for base in [
        "https://www.binance.com",
        "https://fapi.binance.com",
        "https://fapi1.binance.com",
        "https://fapi2.binance.com",
        "https://fapi3.binance.com",
        "https://fapi4.binance.com",
    ]:
        url = base + paths
        try:
            r = requests.get(url, params=params, timeout=REST_TIMEOUT)
            if r.status_code == 200:
                return r.json(), base, None
            errors.append(f"{base}:{r.status_code}")
        except Exception as e:
            errors.append(f"{base}:{type(e).__name__}")
    return None, None, ";".join(errors)

def rest_ratio_5m(start, end):
    rows = []
    cursor = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    host = None
    while cursor <= end_ms:
        data, host, err = get_json(
            "/futures/data/globalLongShortAccountRatio",
            {
                "symbol": "BTCUSDT",
                "period": "5m",
                "startTime": cursor,
                "endTime": end_ms,
                "limit": 500,
            },
        )
        if data is None:
            raise RuntimeError("ratio REST unavailable: " + str(err))
        if not data:
            break
        for x in data:
            rows.append(
                {
                    "time": pd.to_datetime(int(x["timestamp"]), unit="ms", utc=True),
                    "ratio": float(x["longShortRatio"]),
                }
            )
        last = max(int(x["timestamp"]) for x in data)
        if last < cursor:
            break
        cursor = last + 1
        if len(data) < 500:
            break
    d = pd.DataFrame(rows)
    if d.empty:
        raise RuntimeError("ratio REST returned no rows")
    d = d.sort_values("time").drop_duplicates("time", keep="last").set_index("time")
    d = d["ratio"].resample("15min", label="left", closed="left").last().dropna().to_frame()
    return d, host

def rest_futures_15m(start, end):
    rows = []
    cursor = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    host = None
    while cursor <= end_ms:
        data, host, err = get_json(
            "/fapi/v1/klines",
            {
                "symbol": "BTCUSDT",
                "interval": "15m",
                "startTime": cursor,
                "endTime": end_ms,
                "limit": 1500,
            },
        )
        if data is None:
            raise RuntimeError("kline REST unavailable: " + str(err))
        if not data:
            break
        for x in data:
            rows.append(
                {
                    "time": pd.to_datetime(int(x[0]), unit="ms", utc=True),
                    "open": float(x[1]),
                    "high": float(x[2]),
                    "low": float(x[3]),
                    "close": float(x[4]),
                    "quote": float(x[7]),
                    "taker_buy_quote": float(x[10]),
                }
            )
        last = max(int(x[0]) for x in data)
        if last < cursor:
            break
        cursor = last + 15 * 60 * 1000
        if len(data) < 1500:
            break
    d = pd.DataFrame(rows)
    if d.empty:
        raise RuntimeError("kline REST returned no rows")
    d = d.sort_values("time").drop_duplicates("time", keep="last").set_index("time")
    now = pd.Timestamp.now(tz="UTC")
    completed_open = now.floor("15min") - pd.Timedelta(minutes=15)
    d = d[d.index <= completed_open]
    return d, host

def recompute_metrics(base, tail):
    x = pd.concat([base[["ratio"]], tail[["ratio"]]])
    x = x.sort_index()
    x = x[~x.index.duplicated(keep="last")]
    x["delta_ls_12"] = x["ratio"] - x["ratio"].shift(12)
    return x

def recompute_futures(base, tail, l55):
    cols = ["open", "high", "low", "close", "quote", "taker_buy_quote"]
    x = pd.concat([base[cols], tail[cols]])
    x = x.sort_index()
    x = x[~x.index.duplicated(keep="last")]
    pc = x.close.shift(1)
    tr = pd.concat(
        [(x.high - x.low), (x.high - pc).abs(), (x.low - pc).abs()], axis=1
    ).max(axis=1)
    x["atr14"] = tr.rolling(14, min_periods=14).mean()
    x["prior12_low"] = (
        x.low.shift(1).rolling(l55.LEVEL_BARS, min_periods=l55.LEVEL_BARS).min()
    )
    x["prior12_high"] = (
        x.high.shift(1).rolling(l55.LEVEL_BARS, min_periods=l55.LEVEL_BARS).max()
    )
    delta = 2 * x.taker_buy_quote - x.quote
    ds = delta.rolling(4, min_periods=4).sum().shift(1)
    x["netdelta60_raw"] = ds
    x["netdelta60_medabs"] = (
        ds.abs().shift(1).rolling(90 * 96, min_periods=30 * 96).median()
    )
    x["disp60_px"] = x.close.shift(1) - x.close.shift(5)
    return x

def ratio_overlap_parity(base, rest):
    c = base[["ratio"]].join(rest[["ratio"]], how="inner", lsuffix="_arc", rsuffix="_rest")
    if c.empty:
        return {"n": 0, "share": 0.0, "max_abs": None}
    ok = np.isclose(c.ratio_arc.to_numpy(float), c.ratio_rest.to_numpy(float), rtol=0.0, atol=1e-12)
    return {
        "n": int(len(c)),
        "share": float(ok.mean()),
        "max_abs": float(np.max(np.abs(c.ratio_arc.to_numpy(float) - c.ratio_rest.to_numpy(float)))),
    }

def futures_overlap_parity(base, rest):
    cols = ["open", "high", "low", "close", "quote", "taker_buy_quote"]
    c = base[cols].join(rest[cols], how="inner", lsuffix="_arc", rsuffix="_rest")
    if c.empty:
        return {"n": 0, "share": 0.0, "max_rel": None}
    oks = []
    rels = []
    for col in cols:
        a = c[f"{col}_arc"].to_numpy(float)
        b = c[f"{col}_rest"].to_numpy(float)
        ok = np.isclose(a, b, rtol=1e-10, atol=1e-8)
        oks.append(ok)
        denom = np.maximum(np.abs(a), 1.0)
        rels.append(np.abs(a - b) / denom)
    row_ok = np.column_stack(oks).all(axis=1)
    return {
        "n": int(len(c)),
        "share": float(row_ok.mean()),
        "max_rel": float(np.max(np.column_stack(rels))),
    }

def persisted_reproduction(flow, classified):
    oldf = pd.read_csv(L55_OUT / "rebuilt_flow_stream.csv")
    oldf["signal_time"] = pd.to_datetime(oldf.signal_time, errors="coerce", utc=True)
    oldf["side"] = pd.to_numeric(oldf.side, errors="coerce")
    olda = pd.read_csv(L55_OUT / "activation_router_stream.csv")
    olda["signal_time"] = pd.to_datetime(olda.signal_time, errors="coerce", utc=True)
    cutoff = oldf.signal_time.max()

    x = flow[flow.signal_time <= cutoff][["signal_time", "side"]].drop_duplicates()
    y = oldf[oldf.signal_time <= cutoff][["signal_time", "side"]].drop_duplicates()
    m = x.merge(y, on=["signal_time", "side"], how="outer", indicator=True)
    flow_share = float((m["_merge"] == "both").sum() / max(1, len(m)))

    newa = classified[classified.signal_time <= olda.signal_time.max()][
        ["signal_time", "side", "state", "response_router"]
    ].copy()
    oldc = olda[["signal_time", "side", "state", "response_router"]].copy()
    z = newa.merge(oldc, on=["signal_time", "side"], suffixes=("_new", "_old"), how="inner")
    if len(z):
        router_share = float(
            ((z.state_new == z.state_old) & (z.response_router_new == z.response_router_old)).mean()
        )
    else:
        router_share = np.nan
    return {
        "persisted_flow_cutoff": str(cutoff),
        "flow_union_n": int(len(m)),
        "flow_exact_share": flow_share,
        "router_overlap_n": int(len(z)),
        "router_state_exact_share": None if pd.isna(router_share) else router_share,
    }

def pf(v):
    v = np.asarray(v, float)
    gp = v[v > 0].sum()
    gl = -v[v < 0].sum()
    return float(gp / gl) if gl > 0 else (float("inf") if gp > 0 else np.nan)

def maxdd(v):
    v = np.asarray(v, float)
    if not len(v):
        return 0.0
    eq = np.r_[0.0, np.cumsum(v)]
    pk = np.maximum.accumulate(eq)
    return float(np.max(pk - eq))

def summary(events, trades, name):
    e = events.copy()
    q = trades[trades.traded].copy().sort_values("entry_time")
    v = q.net_r_5bps.to_numpy(float)
    dd = maxdd(v)
    return {
        "slice": name,
        "flow_short_n": int((e.side == -1).sum()),
        "high_response_short_n": int(((e.side == -1) & (e.response_router == "HIGH_RESPONSE")).sum()),
        "trade_n": int(len(q)),
        "persistent_exit_n": int(q.persistent_exit.sum()) if len(q) else 0,
        "tp_n": int((q.exit_reason == "TP").sum()) if len(q) else 0,
        "sl_n": int((q.exit_reason == "SL").sum()) if len(q) else 0,
        "time_n": int((q.exit_reason == "TIME").sum()) if len(q) else 0,
        "ev_5bps": float(q.net_r_5bps.mean()) if len(q) else np.nan,
        "ev_10bps": float(q.net_r_10bps.mean()) if len(q) else np.nan,
        "pf_5bps": pf(v) if len(q) else np.nan,
        "cum_r_5bps": float(v.sum()) if len(q) else 0.0,
        "max_dd_r": dd,
        "dd_pct_025": dd * 0.25,
    }

def main():
    l55 = load_lab055()

    archived_summary = pd.read_csv(L55_OUT / "summary.csv")
    archived_summary.to_csv(OUT / "archive_locked_lab055_summary.csv", index=False)
    fresh = archived_summary[archived_summary["slice"] == "FRESH_SEP"].iloc[0]
    formal_verdict = (
        "WATCH_POSTFREEZE_INSUFFICIENT_FRESH_TRADES"
        if int(fresh.accept_trade_n) < 5
        else (
            "PASS_FROZEN_SHORT_V1_POSTFREEZE"
            if (
                fresh.ev_5bps > 0
                and fresh.pf_5bps >= 1.10
                and fresh.ev_10bps > 0
                and fresh.dd_pct_025 <= 4.0
            )
            else "FAIL_FROZEN_SHORT_V1_POSTFREEZE"
        )
    )

    base_metrics = l55.download_metrics()
    base_fut = l55.download_futures()

    now = pd.Timestamp.now(tz="UTC")
    rest_status = "OK"
    rest_error = None
    ratio_host = None
    kline_host = None
    rp = {"n": 0, "share": 0.0, "max_abs": None}
    kp = {"n": 0, "share": 0.0, "max_rel": None}
    rest_ratio = pd.DataFrame()
    rest_fut = pd.DataFrame()

    try:
        rest_ratio, ratio_host = rest_ratio_5m(LIVE0, now)
        rest_fut, kline_host = rest_futures_15m(LIVE0, now)
        rp = ratio_overlap_parity(base_metrics.loc[base_metrics.index >= LIVE0], rest_ratio)
        kp = futures_overlap_parity(base_fut.loc[base_fut.index >= LIVE0], rest_fut)
    except Exception as e:
        rest_status = "UNAVAILABLE"
        rest_error = f"{type(e).__name__}: {e}"

    parity_enabled = (
        rest_status == "OK"
        and rp["n"] > 0
        and kp["n"] > 0
        and rp["share"] >= 0.999
        and kp["share"] >= 0.999
    )

    if parity_enabled:
        metrics = recompute_metrics(base_metrics, rest_ratio[rest_ratio.index > base_metrics.index.max()])
        fut = recompute_futures(base_fut, rest_fut[rest_fut.index > base_fut.index.max()], l55)
    else:
        metrics = base_metrics
        fut = base_fut

    flow = l55.generate_flow(metrics, fut)
    act = l55.build_activation(flow, fut)
    target = act[act.signal_time >= l55.AUG0].copy()
    hist = l55.load_hist_state()
    classified = l55.classify_new(target, hist[hist.signal_time < l55.AUG0].copy())
    rows = [l55.simulate_trade(r, fut) for r in classified.itertuples(index=False)]
    ex = pd.DataFrame(rows)

    repro = persisted_reproduction(flow, classified)
    exact_baseline = (
        repro["flow_exact_share"] == 1.0
        and (
            repro["router_state_exact_share"] is None
            or repro["router_state_exact_share"] == 1.0
        )
    )
    usable_shadow = bool(parity_enabled and exact_baseline)

    fresh_events = classified[classified.signal_time >= SEP0].copy()
    fresh_exec = ex[ex.signal_time >= SEP0].copy()
    shadow = summary(fresh_events, fresh_exec, "FRESH_SEP_ARCHIVE_PLUS_LIVE_SHADOW")
    pd.DataFrame([shadow]).to_csv(OUT / "shadow_summary.csv", index=False)

    new_events = classified[classified.signal_time >= SEP9].copy()
    new_exec = ex[(ex.signal_time >= SEP9) & (ex.traded)].copy()
    new_events.to_csv(OUT / "new_live_shadow_events.csv", index=False)
    new_exec.to_csv(OUT / "new_live_shadow_trades.csv", index=False)

    archive_trade_n = int(fresh.accept_trade_n)
    shadow_trade_n = int(shadow["trade_n"])
    provisional_added = max(0, shadow_trade_n - archive_trade_n) if usable_shadow else 0

    if rest_status != "OK":
        shadow_status = "SHADOW_DATA_UNAVAILABLE"
    elif not usable_shadow:
        shadow_status = "SHADOW_PARITY_FAIL_DO_NOT_USE"
    elif provisional_added > 0:
        shadow_status = "SHADOW_PARITY_PASS_NEW_PROVISIONAL_TRADE"
    else:
        shadow_status = "SHADOW_PARITY_PASS_NO_NEW_TRADE"

    meta = {
        "lab": LAB,
        "run_utc": str(now),
        "formal_verdict": formal_verdict,
        "shadow_status": shadow_status,
        "rest_status": rest_status,
        "rest_error": rest_error,
        "ratio_host": ratio_host,
        "kline_host": kline_host,
        "archive_metrics_max": str(base_metrics.index.max()),
        "archive_futures_max": str(base_fut.index.max()),
        "shadow_metrics_max": str(metrics.index.max()),
        "shadow_futures_max": str(fut.index.max()),
        "eligible_signal_cutoff": str(fut.index.max() - pd.Timedelta(hours=12)),
        "ratio_parity": rp,
        "futures_parity": kp,
        "persisted_reproduction": repro,
        "usable_shadow": usable_shadow,
        "archive_fresh_trade_n": archive_trade_n,
        "shadow_fresh_trade_n": shadow_trade_n,
        "provisional_added_trade_n": provisional_added,
        "new_sep9_flow_short_n": int((new_events.side == -1).sum()) if len(new_events) else 0,
        "new_sep9_high_response_short_n": int(
            ((new_events.side == -1) & (new_events.response_router == "HIGH_RESPONSE")).sum()
        ) if len(new_events) else 0,
        "new_sep9_trade_n": int(len(new_exec)),
        "no_tuning": True,
        "live_allocation": 0,
    }
    (OUT / "parity_and_status.json").write_text(json.dumps(meta, indent=2, default=str))

    def fnum(v):
        return "—" if pd.isna(v) else f"{float(v):+.3f}"

    lines = [
        f"# {LAB}",
        "",
        f"**Formal verdict: {formal_verdict}**",
        f"**Live-shadow status: {shadow_status}**",
        "",
        "## Frozen contract",
        "`FLOW SHORT → HIGH_RESPONSE → ACCEPT → SL 2.5 ATR → TP 1.5R → signal+12h → ADVERSE_FIRST monitor → 2 M15 closes > level before recovery = PERSISTENT_FAILURE EXIT NOW`",
        "",
        "No threshold, signal, stop, target, timeout, management, cost, or sizing parameter changed.",
        "",
        "## Formal archive-locked evidence",
        f"- Fresh Sep trades: **{archive_trade_n}**",
        f"- EV5: **{float(fresh.ev_5bps):+.3f}R**; PF: **{float(fresh.pf_5bps):.3f}**; CumR: **{float(fresh.cum_r_5bps):+.3f}R**",
        f"- EV10: **{float(fresh.ev_10bps):+.3f}R**; DD@0.25%: **{float(fresh.dd_pct_025):.3f}%**",
        "",
        "Formal verdict is unchanged until complete archive-locked fresh N reaches 5.",
        "",
        "## REST/archive parity",
        f"- REST status: **{rest_status}**",
        f"- ratio overlap: N={rp['n']}, exact share={rp['share']:.3%}",
        f"- futures overlap: N={kp['n']}, exact share={kp['share']:.3%}",
        f"- persisted frozen FLOW reproduction: {repro['flow_exact_share']:.3%}",
        f"- persisted router/state reproduction: {repro['router_state_exact_share'] if repro['router_state_exact_share'] is not None else '—'}",
        f"- shadow usable: **{usable_shadow}**",
        "",
        "## Sequential live shadow",
        f"- data through futures bar: **{meta['shadow_futures_max']}**",
        f"- latest signal allowed by full 12h horizon: **{meta['eligible_signal_cutoff']}**",
        f"- Sep archive+shadow FLOW SHORT: **{shadow['flow_short_n']}**",
        f"- Sep archive+shadow HIGH_RESPONSE SHORT: **{shadow['high_response_short_n']}**",
        f"- Sep archive+shadow trades: **{shadow_trade_n}**",
        f"- provisional trades added vs archive: **{provisional_added}**",
        f"- shadow EV5: **{fnum(shadow['ev_5bps'])}R**; PF5: **{shadow['pf_5bps'] if not pd.isna(shadow['pf_5bps']) else '—'}**; CumR: **{fnum(shadow['cum_r_5bps'])}R**",
        f"- shadow EV10: **{fnum(shadow['ev_10bps'])}R**; DD@0.25%: **{shadow['dd_pct_025']:.3f}%**",
        "",
        "## New 9 September eligible population",
        f"- FLOW SHORT: **{meta['new_sep9_flow_short_n']}**",
        f"- HIGH_RESPONSE SHORT: **{meta['new_sep9_high_response_short_n']}**",
        f"- completed frozen trades: **{meta['new_sep9_trade_n']}**",
        "",
        "## Decision",
        "LIVE_SHADOW is monitoring evidence only. It cannot promote the system or modify the freeze. Live/prop allocation remains **0** until archive-locked N is larger and broker/FTMO-native parity is established.",
    ]
    if rest_error:
        lines += ["", "## REST error", f"`{rest_error}`"]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(meta, indent=2, default=str))
    print(json.dumps(shadow, indent=2, default=str))

if __name__ == "__main__":
    main()
