#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

LAB = "BTC_RETAIL_RATIO_ARCHIVE_VS_REST_DECISION_PARITY_AND_THRESHOLD_MARGIN_LAB_057"
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(parents=True, exist_ok=True)

ARCHIVE_END = pd.Timestamp("2026-09-08 23:59:59", tz="UTC")
ARCHIVE_START = pd.Timestamp("2026-05-01", tz="UTC")
REST_START = pd.Timestamp("2026-08-10", tz="UTC")
REST_SHIFT = pd.Timedelta(minutes=-5)
FLOW_COOLDOWN = pd.Timedelta(hours=12)
EVENT_PREROLL = pd.Timedelta(hours=24)
MIN_PRIOR_N = 1000
MIN_COMPARE_N = 1500


def ts_num(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    med = v.dropna().abs().median() if v.notna().any() else np.nan
    unit = "us" if pd.notna(med) and med > 1e14 else ("ms" if pd.notna(med) and med > 1e11 else "s")
    return pd.to_datetime(v, unit=unit, errors="coerce", utc=True)


def parse_metric_zip(content: bytes) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(content))
    names = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if not names:
        return pd.DataFrame()
    d = pd.read_csv(z.open(names[0]))
    d.columns = [str(c).strip() for c in d.columns]
    tc = "create_time" if "create_time" in d.columns else ("timestamp" if "timestamp" in d.columns else None)
    if tc is None or "count_long_short_ratio" not in d.columns:
        return pd.DataFrame()
    t = d[tc]
    time = ts_num(t) if pd.api.types.is_numeric_dtype(t) else pd.to_datetime(t.astype(str).str.strip(), errors="coerce", utc=True)
    return pd.DataFrame({"time": time, "ratio": pd.to_numeric(d["count_long_short_ratio"], errors="coerce")}).dropna()


def fetch_archive_day(t: pd.Timestamp):
    ds = t.strftime("%Y-%m-%d")
    fn = f"BTCUSDT-metrics-{ds}.zip"
    url = f"https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/{fn}"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return None, {"date": ds, "status": r.status_code, "rows": 0}
        d = parse_metric_zip(r.content)
        return d, {"date": ds, "status": 200, "rows": len(d)}
    except Exception as e:
        return None, {"date": ds, "status": type(e).__name__, "rows": 0}


def download_archive_raw() -> pd.DataFrame:
    days = list(pd.date_range(ARCHIVE_START.normalize(), ARCHIVE_END.normalize(), freq="D"))
    parts = []
    manifest = []
    with ThreadPoolExecutor(max_workers=24) as ex:
        fs = [ex.submit(fetch_archive_day, t) for t in days]
        for f in as_completed(fs):
            d, m = f.result()
            manifest.append(m)
            if d is not None and len(d):
                parts.append(d)
    pd.DataFrame(manifest).sort_values("date").to_csv(OUT / "archive_manifest.csv", index=False)
    if not parts:
        raise RuntimeError("No archive metrics downloaded")
    x = pd.concat(parts, ignore_index=True).sort_values("time").drop_duplicates("time", keep="last")
    x = x[(x.time >= ARCHIVE_START) & (x.time <= ARCHIVE_END)]
    return x.set_index("time")[["ratio"]]


def get_rest_json(path: str, params: dict):
    errors = []
    for base in [
        "https://www.binance.com",
        "https://fapi.binance.com",
        "https://fapi1.binance.com",
        "https://fapi2.binance.com",
        "https://fapi3.binance.com",
        "https://fapi4.binance.com",
    ]:
        try:
            r = requests.get(base + path, params=params, timeout=20)
            if r.status_code == 200:
                return r.json(), base
            errors.append(f"{base}:{r.status_code}")
        except Exception as e:
            errors.append(f"{base}:{type(e).__name__}")
    raise RuntimeError("REST unavailable: " + ";".join(errors))


def download_rest_raw() -> tuple[pd.DataFrame, str]:
    start_ms = int(REST_START.timestamp() * 1000)
    end_ms = int(ARCHIVE_END.timestamp() * 1000)
    cursor = start_ms
    rows = []
    used_host = None
    while cursor <= end_ms:
        data, used_host = get_rest_json(
            "/futures/data/globalLongShortAccountRatio",
            {
                "symbol": "BTCUSDT",
                "period": "5m",
                "startTime": cursor,
                "endTime": end_ms,
                "limit": 500,
            },
        )
        if not data:
            break
        for x in data:
            rows.append({
                "time": pd.to_datetime(int(x["timestamp"]), unit="ms", utc=True),
                "ratio": float(x["longShortRatio"]),
            })
        last = max(int(x["timestamp"]) for x in data)
        if last < cursor:
            break
        cursor = last + 1
        if len(data) < 500:
            break
    if not rows:
        raise RuntimeError("REST returned no ratio rows")
    d = pd.DataFrame(rows).sort_values("time").drop_duplicates("time", keep="last")
    d["time"] = d["time"] + REST_SHIFT
    d = d[(d.time >= REST_START + REST_SHIFT) & (d.time <= ARCHIVE_END)]
    return d.set_index("time")[["ratio"]], str(used_host)


def to_m15(raw: pd.DataFrame) -> pd.DataFrame:
    x = raw["ratio"].resample("15min", label="left", closed="left").last().ffill(limit=2).dropna().to_frame("ratio")
    x["delta_ls_12"] = x.ratio - x.ratio.shift(12)
    return x


def archive_thresholds(arc_m15: pd.DataFrame) -> pd.DataFrame:
    x = arc_m15.copy()
    prior = x["delta_ls_12"].shift(1)
    x["q20"] = prior.rolling("90D", min_periods=MIN_PRIOR_N).quantile(0.20)
    x["q80"] = prior.rolling("90D", min_periods=MIN_PRIOR_N).quantile(0.80)
    return x


def classify(delta: np.ndarray, q20: np.ndarray, q80: np.ndarray) -> np.ndarray:
    out = np.zeros(len(delta), dtype=np.int8)
    out[delta <= q20] = 1
    out[delta >= q80] = -1
    return out


def event_stream(times: pd.DatetimeIndex, sides: np.ndarray) -> pd.DataFrame:
    rows = []
    last = None
    for t, s in zip(times, sides):
        s = int(s)
        if s == 0:
            continue
        if last is not None and t - last < FLOW_COOLDOWN:
            continue
        rows.append({"signal_time": t, "side": s})
        last = t
    return pd.DataFrame(rows)


def union_match(a: pd.DataFrame, b: pd.DataFrame) -> tuple[float, int, int, int]:
    if a.empty and b.empty:
        return 1.0, 0, 0, 0
    m = a.merge(b, on=["signal_time", "side"], how="outer", indicator=True)
    both = int((m._merge == "both").sum())
    return float(both / max(1, len(m))), int(len(m)), int(len(a)), int(len(b))


def qstats(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if not len(s):
        return {"n": 0}
    return {
        "n": int(len(s)),
        "min": float(s.min()),
        "p01": float(s.quantile(.01)),
        "p05": float(s.quantile(.05)),
        "p50": float(s.quantile(.50)),
        "p95": float(s.quantile(.95)),
        "p99": float(s.quantile(.99)),
        "max": float(s.max()),
        "mean": float(s.mean()),
    }


def main():
    arc_raw = download_archive_raw()
    rest_raw, rest_host = download_rest_raw()

    raw_cmp = arc_raw.join(rest_raw, how="inner", lsuffix="_arc", rsuffix="_rest")
    raw_cmp["abs_ratio_err"] = (raw_cmp.ratio_arc - raw_cmp.ratio_rest).abs()
    raw_cmp.to_csv(OUT / "raw_ratio_overlap.csv")

    arc = archive_thresholds(to_m15(arc_raw))
    rest = to_m15(rest_raw)
    j = arc[["ratio", "delta_ls_12", "q20", "q80"]].join(
        rest[["ratio", "delta_ls_12"]], how="inner", lsuffix="_arc", rsuffix="_rest"
    ).dropna()
    j = j[j.index >= REST_START + pd.Timedelta(hours=1)]
    if j.empty:
        raise RuntimeError("No comparable M15 rows")

    j["side_arc"] = classify(j.delta_ls_12_arc.to_numpy(float), j.q20.to_numpy(float), j.q80.to_numpy(float))
    j["side_rest"] = classify(j.delta_ls_12_rest.to_numpy(float), j.q20.to_numpy(float), j.q80.to_numpy(float))
    j["decision_match"] = j.side_arc == j.side_rest
    j["short_arc"] = j.side_arc == -1
    j["short_rest"] = j.side_rest == -1
    j["buy_arc"] = j.side_arc == 1
    j["buy_rest"] = j.side_rest == 1
    j["short_match"] = j.short_arc == j.short_rest
    j["buy_match"] = j.buy_arc == j.buy_rest
    j["ratio_abs_err"] = (j.ratio_arc - j.ratio_rest).abs()
    j["delta_abs_err"] = (j.delta_ls_12_arc - j.delta_ls_12_rest).abs()
    j["band_width"] = (j.q80 - j.q20).abs()
    j["normalized_delta_err"] = j.delta_abs_err / j.band_width.replace(0, np.nan)
    j["dist_q20"] = (j.delta_ls_12_arc - j.q20).abs()
    j["dist_q80"] = (j.delta_ls_12_arc - j.q80).abs()
    j["nearest_threshold_dist"] = j[["dist_q20", "dist_q80"]].min(axis=1)
    j["margin_error_ratio"] = j.nearest_threshold_dist / j.delta_abs_err.replace(0, np.nan)
    j["q80_signed_margin_arc"] = j.delta_ls_12_arc - j.q80
    j["q80_signed_margin_rest"] = j.delta_ls_12_rest - j.q80

    n = len(j)
    all_parity = float(j.decision_match.mean())
    short_parity = float(j.short_match.mean())
    buy_parity = float(j.buy_match.mean())
    fp = int((~j.short_arc & j.short_rest).sum())
    fn = int((j.short_arc & ~j.short_rest).sum())
    actual_neg = int((~j.short_arc).sum())
    actual_pos = int(j.short_arc.sum())
    fp_rate = float(fp / max(1, actual_neg))
    fn_rate = float(fn / max(1, actual_pos))

    flips = j[~j.decision_match].copy()
    flips.to_csv(OUT / "decision_flips.csv")
    short_flips = j[j.short_arc != j.short_rest].copy()
    short_flips.to_csv(OUT / "short_decision_flips.csv")

    compare_start = j.index.min()
    event_eval_start = compare_start + EVENT_PREROLL
    ea = event_stream(j.index, j.side_arc.to_numpy())
    er = event_stream(j.index, j.side_rest.to_numpy())
    ea_eval = ea[ea.signal_time >= event_eval_start].copy()
    er_eval = er[er.signal_time >= event_eval_start].copy()
    event_share, event_union_n, event_arc_n, event_rest_n = union_match(ea_eval, er_eval)
    eas = ea_eval[ea_eval.side == -1].copy()
    ers = er_eval[er_eval.side == -1].copy()
    short_event_share, short_event_union_n, short_event_arc_n, short_event_rest_n = union_match(eas, ers)
    ea_eval.to_csv(OUT / "archive_flow_events.csv", index=False)
    er_eval.to_csv(OUT / "rest_flow_events.csv", index=False)

    metrics = {
        "lab": LAB,
        "rest_host": rest_host,
        "archive_raw_min": str(arc_raw.index.min()),
        "archive_raw_max": str(arc_raw.index.max()),
        "rest_raw_min_after_fixed_shift": str(rest_raw.index.min()),
        "rest_raw_max_after_fixed_shift": str(rest_raw.index.max()),
        "fixed_rest_shift_minutes": -5,
        "raw_overlap_n": int(len(raw_cmp)),
        "raw_ratio_abs_error": qstats(raw_cmp.abs_ratio_err),
        "compare_m15_n": int(n),
        "compare_start": str(j.index.min()),
        "compare_end": str(j.index.max()),
        "all_class_pointwise_parity": all_parity,
        "short_binary_parity": short_parity,
        "buy_binary_parity": buy_parity,
        "archive_short_rows": actual_pos,
        "rest_short_rows": int(j.short_rest.sum()),
        "short_false_positive_n": fp,
        "short_false_negative_n": fn,
        "short_false_positive_rate": fp_rate,
        "short_false_negative_rate": fn_rate,
        "all_decision_flip_n": int(len(flips)),
        "short_decision_flip_n": int(len(short_flips)),
        "ratio_abs_error_m15": qstats(j.ratio_abs_err),
        "delta_abs_error": qstats(j.delta_abs_err),
        "normalized_delta_error": qstats(j.normalized_delta_err),
        "nearest_threshold_distance": qstats(j.nearest_threshold_dist),
        "margin_error_ratio": qstats(j.margin_error_ratio),
        "short_archive_q80_positive_margin": qstats(j.loc[j.short_arc, "q80_signed_margin_arc"]),
        "flip_threshold_distance": qstats(flips.nearest_threshold_dist),
        "flip_delta_abs_error": qstats(flips.delta_abs_err),
        "short_flip_threshold_distance": qstats(short_flips.nearest_threshold_dist),
        "short_flip_delta_abs_error": qstats(short_flips.delta_abs_err),
        "event_eval_start": str(event_eval_start),
        "all_side_flow_event_union_match": event_share,
        "all_side_flow_event_union_n": event_union_n,
        "archive_flow_event_n": event_arc_n,
        "rest_flow_event_n": event_rest_n,
        "short_flow_event_union_match": short_event_share,
        "short_flow_event_union_n": short_event_union_n,
        "archive_short_flow_event_n": short_event_arc_n,
        "rest_short_flow_event_n": short_event_rest_n,
    }

    gates = {
        "comparable_m15_n_ge1500": n >= MIN_COMPARE_N,
        "all_class_pointwise_parity_ge99pct": all_parity >= 0.990,
        "short_binary_parity_ge99_5pct": short_parity >= 0.995,
        "short_false_positive_rate_le0_5pct": fp_rate <= 0.005,
        "short_false_negative_rate_le0_5pct": fn_rate <= 0.005,
        "all_side_flow_event_union_match_ge95pct": event_share >= 0.950,
        "short_flow_event_union_match_ge95pct": short_event_share >= 0.950,
        "no_tuning": True,
    }
    verdict = "PASS_REST_DECISION_PARITY_FOR_SHADOW_MONITORING" if all(gates.values()) else "FAIL_REST_DECISION_PARITY"
    metrics["verdict"] = verdict
    metrics["gates"] = {k: bool(v) for k, v in gates.items()}
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))

    j.to_csv(OUT / "m15_decision_comparison.csv")

    L = [
        f"# {LAB}",
        "",
        f"**Verdict: {verdict} — {sum(gates.values())}/{len(gates)} gates**",
        "",
        "## Frozen comparison",
        "Archive `count_long_short_ratio` vs REST `globalLongShortAccountRatio`, fixed REST timestamp shift **-5m**, same strictly-prior archive q20/q80 threshold at each M15 timestamp.",
        "",
        "## Decision parity",
        f"- Comparable M15 rows: **{n}** ({j.index.min()} → {j.index.max()})",
        f"- All-class BUY/SHORT/NEUTRAL parity: **{all_parity:.4%}**",
        f"- SHORT binary parity: **{short_parity:.4%}**",
        f"- BUY binary parity: **{buy_parity:.4%}**",
        f"- SHORT archive rows: **{actual_pos}**; REST SHORT rows: **{int(j.short_rest.sum())}**",
        f"- SHORT false positives: **{fp} ({fp_rate:.4%})**",
        f"- SHORT false negatives: **{fn} ({fn_rate:.4%})**",
        f"- All decision flips: **{len(flips)}**; SHORT-specific flips: **{len(short_flips)}**",
        "",
        "## Frozen 12h FLOW event parity",
        f"- Event evaluation starts after 24h preroll: **{event_eval_start}**",
        f"- All-side event union match: **{event_share:.4%}** (archive {event_arc_n}, REST {event_rest_n}, union {event_union_n})",
        f"- SHORT event union match: **{short_event_share:.4%}** (archive {short_event_arc_n}, REST {short_event_rest_n}, union {short_event_union_n})",
        "",
        "## Transport error / threshold margin",
        f"- Raw 5m overlap N: **{len(raw_cmp)}**; max |ratio diff|: **{metrics['raw_ratio_abs_error'].get('max', np.nan):.8f}**",
        f"- M15 median |delta diff|: **{metrics['delta_abs_error'].get('p50', np.nan):.8f}**; p99: **{metrics['delta_abs_error'].get('p99', np.nan):.8f}**; max: **{metrics['delta_abs_error'].get('max', np.nan):.8f}**",
        f"- Median normalized delta error / (q80-q20): **{metrics['normalized_delta_error'].get('p50', np.nan):.6f}**; p99: **{metrics['normalized_delta_error'].get('p99', np.nan):.6f}**",
        f"- Median nearest-threshold / transport-error ratio: **{metrics['margin_error_ratio'].get('p50', np.nan):.2f}x**",
        "",
        "## Gates",
    ]
    L += [f"- {'PASS' if v else 'FAIL'} — `{k}`" for k, v in gates.items()]
    L += [
        "",
        "## Guardrail",
        "This LAB contains no PnL and no outcome-conditioned tuning. PASS would authorize REST only as a separately controlled shadow-monitor transport; archive daily metrics remain canonical fresh evidence until separately changed by preregistration.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(L) + "\n")
    print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
