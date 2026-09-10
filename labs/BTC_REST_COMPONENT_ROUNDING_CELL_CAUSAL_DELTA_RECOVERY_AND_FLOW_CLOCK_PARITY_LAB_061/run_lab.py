#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import math
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

LAB = "BTC_REST_COMPONENT_ROUNDING_CELL_CAUSAL_DELTA_RECOVERY_AND_FLOW_CLOCK_PARITY_LAB_061"
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(parents=True, exist_ok=True)

ARCHIVE_START = pd.Timestamp("2026-05-01", tz="UTC")
REST_START = pd.Timestamp("2026-08-10", tz="UTC")
REST_SHIFT = pd.Timedelta(minutes=-5)
HALF_UNIT = 0.00005
FLOW_COOLDOWN = pd.Timedelta(hours=12)
EVENT_PREROLL = pd.Timedelta(hours=24)
MIN_PRIOR_N = 1000
MIN_COMPARE_N = 1500


def utc_now():
    return pd.Timestamp.now(tz="UTC")


def latest_complete_archive_day():
    # Daily archive is expected only after UTC day close. Probe backwards from yesterday.
    return (utc_now().normalize() - pd.Timedelta(days=1))


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
    out = pd.DataFrame({"time": time, "ratio": pd.to_numeric(d["count_long_short_ratio"], errors="coerce")})
    return out.dropna().sort_values("time")


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
    end_day = latest_complete_archive_day()
    days = list(pd.date_range(ARCHIVE_START.normalize(), end_day, freq="D"))
    parts, manifest = [], []
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
    x = x[x.time >= ARCHIVE_START]
    return x.set_index("time")[["ratio"]]


def get_rest_json(params: dict):
    errors = []
    bases = [
        "https://www.binance.com",
        "https://fapi.binance.com",
        "https://fapi1.binance.com",
        "https://fapi2.binance.com",
        "https://fapi3.binance.com",
        "https://fapi4.binance.com",
    ]
    for base in bases:
        try:
            r = requests.get(base + "/futures/data/globalLongShortAccountRatio", params=params, timeout=20)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return data, base
            errors.append(f"{base}:{r.status_code}")
        except Exception as e:
            errors.append(f"{base}:{type(e).__name__}")
    raise RuntimeError("REST unavailable: " + ";".join(errors))


def download_rest_raw(end_time: pd.Timestamp) -> tuple[pd.DataFrame, str]:
    start_ms = int(REST_START.timestamp() * 1000)
    end_ms = int((end_time + pd.Timedelta(minutes=10)).timestamp() * 1000)
    cursor = start_ms
    rows = []
    used_host = None
    while cursor <= end_ms:
        data, used_host = get_rest_json({
            "symbol": "BTCUSDT",
            "period": "5m",
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 500,
        })
        if not data:
            break
        for x in data:
            try:
                rows.append({
                    "time": pd.to_datetime(int(x["timestamp"]), unit="ms", utc=True),
                    "ratio_reported": float(x["longShortRatio"]),
                    "longAccount": float(x["longAccount"]),
                    "shortAccount": float(x["shortAccount"]),
                })
            except Exception:
                pass
        last = max(int(x["timestamp"]) for x in data)
        if last < cursor:
            break
        cursor = last + 1
        if len(data) < 500:
            break
    if not rows:
        raise RuntimeError("REST returned no rows")
    d = pd.DataFrame(rows).sort_values("time").drop_duplicates("time", keep="last")
    d["time"] = d["time"] + REST_SHIFT
    d = d[(d.time >= REST_START + REST_SHIFT) & (d.time <= end_time)]
    return d.set_index("time"), str(used_host)


def add_component_cell(rest: pd.DataFrame) -> pd.DataFrame:
    x = rest.copy()
    L = x.longAccount.astype(float)
    S = x.shortAccount.astype(float)
    lo1, hi1 = L - HALF_UNIT, L + HALF_UNIT
    lo2, hi2 = 1.0 - (S + HALF_UNIT), 1.0 - (S - HALF_UNIT)
    x["p_lo"] = np.maximum(lo1, lo2).clip(lower=1e-12, upper=1-1e-12)
    x["p_hi"] = np.minimum(hi1, hi2).clip(lower=1e-12, upper=1-1e-12)
    x["cell_valid"] = x.p_lo <= x.p_hi
    x["r_lo"] = x.p_lo / (1.0 - x.p_lo)
    x["r_hi"] = x.p_hi / (1.0 - x.p_hi)
    x.loc[~x.cell_valid, ["r_lo", "r_hi"]] = np.nan
    x["cell_width"] = x.r_hi - x.r_lo
    return x


def to_m15_archive(raw: pd.DataFrame) -> pd.DataFrame:
    x = raw["ratio"].resample("15min", label="left", closed="left").last().ffill(limit=2).dropna().to_frame("ratio")
    x["delta"] = x.ratio - x.ratio.shift(12)
    return x


def to_m15_rest(raw: pd.DataFrame) -> pd.DataFrame:
    # Frozen aggregation: last 5m observation in each M15 bucket. Keep its whole rounding cell.
    cols = ["ratio_reported", "longAccount", "shortAccount", "p_lo", "p_hi", "r_lo", "r_hi", "cell_width", "cell_valid"]
    x = raw[cols].resample("15min", label="left", closed="left").last().ffill(limit=2).dropna(subset=["r_lo", "r_hi"])
    x["delta_lo"] = x.r_lo - x.r_hi.shift(12)
    x["delta_hi"] = x.r_hi - x.r_lo.shift(12)
    x["delta_mid"] = (x.delta_lo + x.delta_hi) / 2.0
    return x


def add_thresholds(arc: pd.DataFrame) -> pd.DataFrame:
    x = arc.copy()
    prior = x.delta.shift(1)
    x["q20"] = prior.rolling("90D", min_periods=MIN_PRIOR_N).quantile(0.20)
    x["q80"] = prior.rolling("90D", min_periods=MIN_PRIOR_N).quantile(0.80)
    return x


def classify_archive(delta, q20, q80):
    d = np.asarray(delta, float); lo = np.asarray(q20, float); hi = np.asarray(q80, float)
    out = np.zeros(len(d), dtype=np.int8)
    out[d <= lo] = 1
    out[d >= hi] = -1
    return out


def recover_side(row):
    if row.delta_lo >= row.q80:
        return -1, "CERTAIN_SHORT"
    if row.delta_hi <= row.q20:
        return 1, "CERTAIN_BUY"
    if row.delta_lo > row.q20 and row.delta_hi < row.q80:
        return 0, "CERTAIN_NEUTRAL"
    return np.nan, "UNCERTAIN"


def event_stream(times, sides):
    rows, last = [], None
    for t, s in zip(times, sides):
        if pd.isna(s):
            continue
        s = int(s)
        if s == 0:
            continue
        if last is not None and t - last < FLOW_COOLDOWN:
            continue
        rows.append({"signal_time": t, "side": s})
        last = t
    return pd.DataFrame(rows, columns=["signal_time", "side"])


def union_metrics(a, b, side=None):
    aa, bb = a.copy(), b.copy()
    if side is not None:
        aa = aa[aa.side == side]; bb = bb[bb.side == side]
    aset = set(zip(aa.signal_time.astype(str), aa.side.astype(int)))
    bset = set(zip(bb.signal_time.astype(str), bb.side.astype(int)))
    inter, union = aset & bset, aset | bset
    return {
        "archive_n": len(aset), "recovered_n": len(bset), "intersection_n": len(inter), "union_n": len(union),
        "union_match": 1.0 if not union else len(inter)/len(union),
        "archive_only_n": len(aset-bset), "recovered_only_n": len(bset-aset),
    }


def qstats(s):
    s = pd.to_numeric(pd.Series(s), errors="coerce").replace([np.inf,-np.inf], np.nan).dropna()
    if not len(s): return {"n":0}
    return {"n":int(len(s)),"min":float(s.min()),"p01":float(s.quantile(.01)),"p05":float(s.quantile(.05)),"p50":float(s.quantile(.5)),"p95":float(s.quantile(.95)),"p99":float(s.quantile(.99)),"max":float(s.max()),"mean":float(s.mean())}


def nearest_same_side_drift(arc_events, rec_events):
    vals = []
    if arc_events.empty or rec_events.empty: return vals
    for _, r in arc_events.iterrows():
        cand = rec_events[rec_events.side == r.side]
        if cand.empty: continue
        diffs = (cand.signal_time - r.signal_time).dt.total_seconds()/3600.0
        j = diffs.abs().idxmin()
        vals.append(float(diffs.loc[j]))
    return vals


def main():
    arc_raw = download_archive_raw()
    archive_end = arc_raw.index.max()
    rest_raw, rest_host = download_rest_raw(archive_end)
    rest_raw = add_component_cell(rest_raw)

    raw_cmp = arc_raw.join(rest_raw[["ratio_reported","longAccount","shortAccount","p_lo","p_hi","r_lo","r_hi","cell_width","cell_valid"]], how="inner")
    raw_cmp["archive_inside_cell"] = (raw_cmp.ratio >= raw_cmp.r_lo) & (raw_cmp.ratio <= raw_cmp.r_hi)
    raw_cmp.to_csv(OUT / "raw_component_cell_overlap.csv")

    arc = add_thresholds(to_m15_archive(arc_raw))
    rest = to_m15_rest(rest_raw)
    j = arc[["ratio","delta","q20","q80"]].join(rest, how="inner").dropna(subset=["delta","q20","q80","delta_lo","delta_hi"])
    j = j[j.index >= REST_START + pd.Timedelta(hours=3)]
    if j.empty:
        raise RuntimeError("No comparable M15 rows")

    j["side_arc"] = classify_archive(j.delta.values, j.q20.values, j.q80.values)
    rec = j.apply(recover_side, axis=1, result_type="expand")
    j["recovered_side"] = rec[0]
    j["recovered_label"] = rec[1]
    j["certain"] = j.recovered_label != "UNCERTAIN"
    j["certain_correct"] = (~j.certain) | (j.recovered_side == j.side_arc)
    j["short_arc"] = j.side_arc == -1
    j["buy_arc"] = j.side_arc == 1
    j["short_pred"] = j.recovered_side == -1
    j["buy_pred"] = j.recovered_side == 1
    j["nearest_threshold_dist"] = np.minimum((j.delta-j.q20).abs(), (j.delta-j.q80).abs())
    j.to_csv(OUT / "m15_component_cell_decision_recovery.csv")

    uncertain = j[~j.certain].copy(); uncertain.to_csv(OUT / "uncertain_decisions.csv")
    false_certain = j[j.certain & (j.recovered_side != j.side_arc)].copy(); false_certain.to_csv(OUT / "false_certain_decisions.csv")

    n = len(j)
    certain = j[j.certain]
    certainty_coverage = len(certain)/n
    certain_accuracy = 1.0 if len(certain)==0 else float((certain.recovered_side==certain.side_arc).mean())
    short_pred = j[j.short_pred]
    short_precision = 1.0 if len(short_pred)==0 else float((short_pred.side_arc==-1).mean())
    short_recall = 1.0 if j.short_arc.sum()==0 else float((j.short_arc & j.short_pred).sum()/j.short_arc.sum())
    buy_pred = j[j.buy_pred]
    buy_precision = 1.0 if len(buy_pred)==0 else float((buy_pred.side_arc==1).mean())
    buy_recall = 1.0 if j.buy_arc.sum()==0 else float((j.buy_arc & j.buy_pred).sum()/j.buy_arc.sum())

    archive_events_all = event_stream(j.index, j.side_arc.values)
    recovered_events_all = event_stream(j.index, j.recovered_side.values)
    formal_start = j.index.min() + EVENT_PREROLL
    archive_events = archive_events_all[archive_events_all.signal_time >= formal_start].copy()
    recovered_events = recovered_events_all[recovered_events_all.signal_time >= formal_start].copy()
    archive_events.to_csv(OUT / "archive_flow_events.csv", index=False)
    recovered_events.to_csv(OUT / "recovered_flow_events.csv", index=False)

    all_clock = union_metrics(archive_events, recovered_events)
    short_clock = union_metrics(archive_events, recovered_events, side=-1)
    drift = nearest_same_side_drift(archive_events, recovered_events)

    raw_coverage = float(raw_cmp.archive_inside_cell.mean()) if len(raw_cmp) else 0.0
    gates = {
        "comparable_m15_n_ge1500": n >= MIN_COMPARE_N,
        "archive_ratio_inside_component_cell_ge99_9pct": raw_coverage >= .999,
        "certain_decision_coverage_ge99pct": certainty_coverage >= .99,
        "certain_decision_accuracy_eq100pct": certain_accuracy == 1.0,
        "false_certain_n_eq0": len(false_certain) == 0,
        "certain_short_precision_eq100pct": short_precision == 1.0,
        "canonical_short_recall_ge99pct": short_recall >= .99,
        "certain_buy_precision_eq100pct": buy_precision == 1.0,
        "canonical_buy_recall_ge99pct": buy_recall >= .99,
        "all_side_flow_event_union_match_ge95pct": all_clock["union_match"] >= .95,
        "short_flow_event_union_match_ge95pct": short_clock["union_match"] >= .95,
        "no_tuning": True,
    }

    unsafe = raw_coverage < .999 or len(false_certain)>0 or short_precision < 1.0
    if n < MIN_COMPARE_N:
        verdict = "INSUFFICIENT_DATA"
    elif unsafe:
        verdict = "FAIL_COMPONENT_CELL_UNSAFE"
    elif all(gates.values()):
        verdict = "PASS_COMPONENT_CELL_FLOW_CLOCK_PARITY"
    else:
        verdict = "WATCH_COMPONENT_CELL_SAFE_BUT_CLOCK_OR_RECALL_LOW"

    metrics = {
        "lab": LAB,
        "run_time_utc": utc_now().isoformat(),
        "rest_host": rest_host,
        "fixed_rest_shift_minutes": -5,
        "component_half_unit": HALF_UNIT,
        "archive_latest_time": archive_end.isoformat(),
        "raw_overlap_n": int(len(raw_cmp)),
        "raw_component_cell_valid_share": float(raw_cmp.cell_valid.mean()) if len(raw_cmp) else 0.0,
        "archive_ratio_inside_component_cell_share": raw_coverage,
        "raw_component_ratio_cell_width": qstats(raw_cmp.cell_width),
        "compare_m15_n": int(n),
        "compare_start": j.index.min().isoformat(),
        "compare_end": j.index.max().isoformat(),
        "certainty_coverage": certainty_coverage,
        "uncertain_n": int(len(uncertain)),
        "certain_n": int(len(certain)),
        "certain_accuracy": certain_accuracy,
        "false_certain_n": int(len(false_certain)),
        "canonical_short_n": int(j.short_arc.sum()),
        "certain_short_pred_n": int(j.short_pred.sum()),
        "certain_short_precision": short_precision,
        "canonical_short_recall": short_recall,
        "canonical_buy_n": int(j.buy_arc.sum()),
        "certain_buy_pred_n": int(j.buy_pred.sum()),
        "certain_buy_precision": buy_precision,
        "canonical_buy_recall": buy_recall,
        "uncertain_threshold_distance": qstats(uncertain.nearest_threshold_dist),
        "certain_threshold_distance": qstats(certain.nearest_threshold_dist),
        "clock_event_eval_start": formal_start.isoformat(),
        "clock_all": all_clock,
        "clock_short": short_clock,
        "nearest_same_side_event_drift_hours": qstats(drift),
        "gates": gates,
        "verdict": verdict,
        "frozen_short_v1_changed": False,
        "live_allocation": 0,
    }
    with open(OUT / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    report = f"""# {LAB} — REPORT\n\n## Verdict\n**{verdict}**\n\n## Component-cell lineage\n- raw overlap: {len(raw_cmp)}\n- archive ratio inside mathematically implied cell: {raw_coverage:.6%}\n- median ratio-cell width: {metrics['raw_component_ratio_cell_width'].get('p50')}\n\n## Pointwise recovery\n- comparable M15: {n}\n- certainty coverage: {certainty_coverage:.6%}\n- false-certain: {len(false_certain)}\n- certain accuracy: {certain_accuracy:.6%}\n- SHORT precision: {short_precision:.6%}\n- SHORT recall: {short_recall:.6%}\n- BUY precision: {buy_precision:.6%}\n- BUY recall: {buy_recall:.6%}\n\n## Frozen 12h FLOW clock\n- all-side union match: {all_clock['union_match']:.6%}\n- SHORT union match: {short_clock['union_match']:.6%}\n- archive SHORT events: {short_clock['archive_n']}\n- recovered SHORT events: {short_clock['recovered_n']}\n\nFrozen SHORT v1 unchanged. Live allocation = 0.\n"""
    (OUT / "REPORT.md").write_text(report)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
