#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import math
import re
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

LAB = "BTC_RETAIL_RATIO_ARCHIVE_PRODUCTION_LINEAGE_AND_HIGH_PRECISION_SOURCE_DISCOVERY_LAB_060"
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(parents=True, exist_ok=True)

SYMBOL = "BTCUSDT"
PERIOD = "5m"
KNOWN_REST_SHIFT_MIN = -5
BAPI_SHIFT_GRID = [-10, -5, 0, 5, 10]
MIN_OVERLAP = 200
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; ResearchOS-LAB060/1.0)",
    "Accept": "application/json,text/plain,*/*",
})

OFFICIAL_HOSTS = [
    "https://www.binance.com",
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
    "https://fapi3.binance.com",
    "https://fapi4.binance.com",
]
BAPI_PATHS = [
    "/bapi/futures/v1/public/future/marketData/longShortRatio",
    "/bapi/futures/v1/public/future/marketData/globalLongShortAccountRatio",
    "/bapi/futures/v1/public/future/marketData/longShortAccountRatio",
]


def safe_json_scalar(x: Any):
    if x is None:
        return None
    if isinstance(x, (bool, str, int)):
        return x
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(float(x)) else float(x)
    if isinstance(x, pd.Timestamp):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): safe_json_scalar(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [safe_json_scalar(v) for v in x]
    return str(x)


def parse_ts(x: Any) -> pd.Timestamp | pd.NaT:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return pd.NaT
        if isinstance(x, str) and not re.fullmatch(r"\d+(?:\.0+)?", x.strip()):
            return pd.to_datetime(x, utc=True, errors="coerce")
        v = float(x)
        av = abs(v)
        unit = "us" if av > 1e14 else ("ms" if av > 1e11 else ("s" if av > 1e8 else None))
        if unit:
            return pd.to_datetime(v, unit=unit, utc=True, errors="coerce")
        return pd.NaT
    except Exception:
        return pd.NaT


def decimal_places(s: Any) -> int:
    text = str(s).strip().lower()
    if "e" in text:
        try:
            d = Decimal(text)
            return max(0, -d.as_tuple().exponent)
        except InvalidOperation:
            return 0
    return len(text.split(".", 1)[1]) if "." in text else 0


def parse_archive_zip(content: bytes, source_date: str) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(content))
    names = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if not names:
        return pd.DataFrame()
    d = pd.read_csv(z.open(names[0]), dtype=str)
    d.columns = [str(c).strip() for c in d.columns]
    tc = "create_time" if "create_time" in d.columns else ("timestamp" if "timestamp" in d.columns else None)
    if tc is None or "count_long_short_ratio" not in d.columns:
        return pd.DataFrame()
    t = d[tc].map(parse_ts)
    ratio_s = d["count_long_short_ratio"].astype(str).str.strip()
    out = pd.DataFrame({
        "time": t,
        "archive_ratio_str": ratio_s,
        "archive_ratio": pd.to_numeric(ratio_s, errors="coerce"),
        "archive_digits": ratio_s.map(decimal_places),
        "source_date": source_date,
    }).dropna(subset=["time", "archive_ratio"])
    return out.sort_values("time")


def fetch_archive_probe(day: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    ds = day.strftime("%Y-%m-%d")
    fn = f"{SYMBOL}-metrics-{ds}.zip"
    url = f"https://data.binance.vision/data/futures/um/daily/metrics/{SYMBOL}/{fn}"
    meta = {"date": ds, "url": url, "status": None, "rows": 0, "first": None, "last": None}
    try:
        r = SESSION.get(url, timeout=30)
        meta["status"] = r.status_code
        if r.status_code != 200:
            return pd.DataFrame(), meta
        d = parse_archive_zip(r.content, ds)
        meta["rows"] = int(len(d))
        if len(d):
            meta["first"] = d.time.min().isoformat()
            meta["last"] = d.time.max().isoformat()
        return d, meta
    except Exception as e:
        meta["status"] = type(e).__name__
        return pd.DataFrame(), meta


def recent_archive() -> tuple[pd.DataFrame, list[dict], pd.Timestamp, pd.Timestamp]:
    now = pd.Timestamp.now(tz="UTC")
    days = [now.normalize() - pd.Timedelta(days=i) for i in range(0, 7)]
    parts, manifest = [], []
    for day in days:
        d, m = fetch_archive_probe(day)
        manifest.append(m)
        if len(d):
            parts.append(d)
    if not parts:
        raise RuntimeError("No recent Binance archive metrics available")
    arc = pd.concat(parts, ignore_index=True).sort_values("time").drop_duplicates("time", keep="last")
    latest_archive_time = arc.time.max()
    latest_archive_day = pd.Timestamp(arc.loc[arc.time.idxmax(), "source_date"], tz="UTC")
    # Keep enough recent canonical history for candidate overlap.
    arc = arc[arc.time >= latest_archive_time - pd.Timedelta(days=4)].copy()
    return arc, manifest, latest_archive_day, latest_archive_time


def walk_records(obj: Any) -> list[dict]:
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj):
            return obj
        for x in obj:
            got = walk_records(x)
            if got:
                return got
    if isinstance(obj, dict):
        for key in ["data", "rows", "list", "result"]:
            if key in obj:
                got = walk_records(obj[key])
                if got:
                    return got
        # Sometimes the response itself is one row.
        if any(k in obj for k in ["longShortRatio", "ratio", "countLongShortRatio", "count_long_short_ratio"]):
            return [obj]
        for v in obj.values():
            got = walk_records(v)
            if got:
                return got
    return []


def extract_candidate_frame(obj: Any) -> pd.DataFrame:
    records = walk_records(obj)
    rows = []
    for x in records:
        tk = next((k for k in ["timestamp", "time", "createTime", "create_time", "ts"] if k in x), None)
        rk = next((k for k in ["longShortRatio", "ratio", "countLongShortRatio", "count_long_short_ratio"] if k in x), None)
        if tk is None or rk is None:
            continue
        ts = parse_ts(x.get(tk))
        rs = str(x.get(rk)).strip()
        try:
            rv = float(rs)
        except Exception:
            continue
        la = x.get("longAccount", x.get("long_account"))
        sa = x.get("shortAccount", x.get("short_account"))
        rows.append({
            "time": ts,
            "ratio_str": rs,
            "ratio": rv,
            "digits": decimal_places(rs),
            "longAccount_str": None if la is None else str(la).strip(),
            "shortAccount_str": None if sa is None else str(sa).strip(),
            "longAccount": pd.to_numeric(la, errors="coerce"),
            "shortAccount": pd.to_numeric(sa, errors="coerce"),
        })
    if not rows:
        return pd.DataFrame()
    d = pd.DataFrame(rows).dropna(subset=["time", "ratio"]).sort_values("time").drop_duplicates("time", keep="last")
    return d


def request_json(url: str, params: dict) -> tuple[Any | None, dict]:
    meta = {"url": url, "status": None, "content_type": None, "preview": None, "error": None}
    try:
        r = SESSION.get(url, params=params, timeout=25)
        meta["status"] = r.status_code
        meta["content_type"] = r.headers.get("content-type")
        meta["preview"] = r.text[:500]
        if r.status_code != 200:
            return None, meta
        try:
            return r.json(), meta
        except Exception as e:
            meta["error"] = f"json:{type(e).__name__}"
            return None, meta
    except Exception as e:
        meta["error"] = type(e).__name__
        return None, meta


def fetch_official_window(host: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, list[dict]]:
    rows = []
    metas = []
    cursor = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    while cursor <= end_ms:
        obj, meta = request_json(host + "/futures/data/globalLongShortAccountRatio", {
            "symbol": SYMBOL,
            "period": PERIOD,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 500,
        })
        metas.append(meta)
        if obj is None:
            break
        d = extract_candidate_frame(obj)
        if d.empty:
            break
        rows.append(d)
        last_ms = int(d.time.max().timestamp() * 1000)
        if last_ms < cursor or len(d) < 500:
            break
        cursor = last_ms + 1
    if not rows:
        return pd.DataFrame(), metas
    x = pd.concat(rows, ignore_index=True).sort_values("time").drop_duplicates("time", keep="last")
    return x, metas


def fetch_bapi(path: str) -> tuple[pd.DataFrame, list[dict]]:
    # Frozen parameter variants; candidate path remains fixed.
    variants = [
        {"symbol": SYMBOL, "period": PERIOD, "limit": 500},
        {"symbol": SYMBOL, "period": PERIOD, "size": 500},
    ]
    metas = []
    for params in variants:
        obj, meta = request_json("https://www.binance.com" + path, params)
        meta["params"] = params
        metas.append(meta)
        if obj is None:
            continue
        d = extract_candidate_frame(obj)
        if len(d):
            return d, metas
    return pd.DataFrame(), metas


def series_stats(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if not len(s):
        return {"n": 0}
    return {
        "n": int(len(s)),
        "mean": float(s.mean()),
        "p50": float(s.quantile(.50)),
        "p95": float(s.quantile(.95)),
        "p99": float(s.quantile(.99)),
        "max": float(s.max()),
    }


def compare_to_archive(name: str, cand: pd.DataFrame, arc: pd.DataFrame, shift_min: int, value_col: str = "ratio", raw_digits_col: str | None = "digits") -> dict:
    if cand.empty or value_col not in cand.columns:
        return {"name": name, "shift_min": shift_min, "overlap_n": 0}
    c = cand[["time", value_col] + ([raw_digits_col] if raw_digits_col and raw_digits_col in cand.columns else [])].copy()
    c["time_aligned"] = c.time + pd.Timedelta(minutes=shift_min)
    c = c.drop_duplicates("time_aligned", keep="last")
    a = arc[["time", "archive_ratio"]].copy()
    j = a.merge(c, left_on="time", right_on="time_aligned", how="inner")
    if j.empty:
        return {"name": name, "shift_min": shift_min, "overlap_n": 0}
    err = (pd.to_numeric(j.archive_ratio, errors="coerce") - pd.to_numeric(j[value_col], errors="coerce")).abs()
    exact = err <= 1e-12
    corr = float(j.archive_ratio.corr(pd.to_numeric(j[value_col], errors="coerce"))) if len(j) >= 2 else None
    digits = c[raw_digits_col] if raw_digits_col and raw_digits_col in c.columns else pd.Series(dtype=float)
    result = {
        "name": name,
        "shift_min": int(shift_min),
        "overlap_n": int(len(j)),
        "exact_share": float(exact.mean()),
        "abs_error": series_stats(err),
        "correlation": corr,
        "ratio_digits_ge6_share": None if len(digits) == 0 else float((pd.to_numeric(digits, errors="coerce") >= 6).mean()),
        "ratio_digits_p50": None if len(digits) == 0 else float(pd.to_numeric(digits, errors="coerce").median()),
    }
    return result


def add_reconstructions(d: pd.DataFrame) -> pd.DataFrame:
    if d.empty:
        return d
    x = d.copy()
    la = pd.to_numeric(x.get("longAccount"), errors="coerce")
    sa = pd.to_numeric(x.get("shortAccount"), errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        x["recon_la_sa"] = la / sa
        x["recon_1msa"] = (1.0 - sa) / sa
        x["recon_la_1mla"] = la / (1.0 - la)
    return x


def candidate_gate(cmp: dict, cand_latest: pd.Timestamp | None, archive_latest: pd.Timestamp, digits_override: bool = False) -> dict:
    err = cmp.get("abs_error", {}) or {}
    overlap = int(cmp.get("overlap_n", 0) or 0)
    exact_share = float(cmp.get("exact_share", 0.0) or 0.0)
    max_err = err.get("max")
    precision_ok = digits_override or ((cmp.get("ratio_digits_ge6_share") or 0.0) >= 0.95)
    fresh = cand_latest is not None and pd.notna(cand_latest) and cand_latest >= archive_latest + pd.Timedelta(minutes=5)
    equivalent = overlap >= MIN_OVERLAP and exact_share >= 0.999 and max_err is not None and max_err <= 1e-8 and precision_ok
    return {
        "overlap_ge200": overlap >= MIN_OVERLAP,
        "exact_share_ge99_9": exact_share >= 0.999,
        "max_abs_error_le1e_8": max_err is not None and max_err <= 1e-8,
        "high_precision": bool(precision_ok),
        "fresh_beyond_archive": bool(fresh),
        "archive_equivalent": bool(equivalent),
        "archive_equivalent_live": bool(equivalent and fresh),
    }


def main():
    now = pd.Timestamp.now(tz="UTC")
    arc, archive_manifest, latest_archive_day, latest_archive_time = recent_archive()
    arc.to_csv(OUT / "canonical_recent_archive.csv", index=False)
    pd.DataFrame(archive_manifest).sort_values("date").to_csv(OUT / "archive_probe_manifest.csv", index=False)

    # Candidate window: canonical recent history plus a live extension.
    fetch_start = arc.time.min() - pd.Timedelta(minutes=10)
    fetch_end = now + pd.Timedelta(minutes=10)

    probe_log = {"official": {}, "bapi": {}, "archive_manifest": archive_manifest}
    comparisons = []
    source_summaries = []
    successful_official = []

    # Official REST family.
    for host in OFFICIAL_HOSTS:
        d, metas = fetch_official_window(host, fetch_start, fetch_end)
        probe_log["official"][host] = metas
        if d.empty:
            source_summaries.append({"candidate": host + "/futures/data/globalLongShortAccountRatio", "family": "official_rest", "http_success": False, "rows": 0})
            continue
        d = add_reconstructions(d)
        successful_official.append((host, d))
        d.to_csv(OUT / ("official_" + re.sub(r"[^a-zA-Z0-9]+", "_", host).strip("_") + ".csv"), index=False)
        latest = d.time.max()
        base_cmp = compare_to_archive(host + ":reported", d, arc, KNOWN_REST_SHIFT_MIN, "ratio", "digits")
        gate = candidate_gate(base_cmp, latest + pd.Timedelta(minutes=KNOWN_REST_SHIFT_MIN), latest_archive_time)
        comparisons.append({**base_cmp, "family": "official_rest", "value_kind": "reported", **gate})
        for col in ["recon_la_sa", "recon_1msa", "recon_la_1mla"]:
            cmp = compare_to_archive(host + ":" + col, d, arc, KNOWN_REST_SHIFT_MIN, col, None)
            comparisons.append({**cmp, "family": "official_reconstruction", "value_kind": col, **candidate_gate(cmp, latest + pd.Timedelta(minutes=KNOWN_REST_SHIFT_MIN), latest_archive_time, digits_override=False)})
        source_summaries.append({
            "candidate": host + "/futures/data/globalLongShortAccountRatio",
            "family": "official_rest",
            "http_success": True,
            "rows": int(len(d)),
            "first_time": d.time.min().isoformat(),
            "last_time_raw": latest.isoformat(),
            "last_time_aligned": (latest + pd.Timedelta(minutes=KNOWN_REST_SHIFT_MIN)).isoformat(),
            "digits_p50": float(d.digits.median()),
            "digits_ge6_share": float((d.digits >= 6).mean()),
        })

    # Frozen web/BAPI candidate paths. Diagnostic offset grid only.
    for path in BAPI_PATHS:
        d, metas = fetch_bapi(path)
        probe_log["bapi"][path] = metas
        if d.empty:
            source_summaries.append({"candidate": "https://www.binance.com" + path, "family": "bapi", "http_success": False, "rows": 0})
            continue
        d = add_reconstructions(d)
        latest = d.time.max()
        shift_cmps = [compare_to_archive("bapi:" + path, d, arc, sh, "ratio", "digits") for sh in BAPI_SHIFT_GRID]
        best = max(shift_cmps, key=lambda x: (x.get("exact_share", 0.0), -(x.get("abs_error", {}) or {}).get("mean", 1e9)))
        for cmp in shift_cmps:
            comparisons.append({**cmp, "family": "bapi", "value_kind": "reported", "diagnostic_only": True, **candidate_gate(cmp, latest + pd.Timedelta(minutes=cmp["shift_min"]), latest_archive_time)})
        source_summaries.append({
            "candidate": "https://www.binance.com" + path,
            "family": "bapi",
            "http_success": True,
            "rows": int(len(d)),
            "first_time": d.time.min().isoformat(),
            "last_time_raw": latest.isoformat(),
            "digits_p50": float(d.digits.median()),
            "digits_ge6_share": float((d.digits >= 6).mean()),
            "best_diagnostic_shift_min": int(best.get("shift_min", 0)),
            "best_diagnostic_exact_share": float(best.get("exact_share", 0.0) or 0.0),
        })
        d.to_csv(OUT / ("bapi_" + re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_") + ".csv"), index=False)

    cmpdf = pd.DataFrame(comparisons)
    cmpdf.to_csv(OUT / "candidate_comparisons.csv", index=False)
    pd.DataFrame(source_summaries).to_csv(OUT / "candidate_sources.csv", index=False)
    with open(OUT / "probe_responses.json", "w") as f:
        json.dump(safe_json_scalar(probe_log), f, indent=2)

    # Explicit current-day archive test.
    today = now.normalize()
    today_row = next((m for m in archive_manifest if m["date"] == today.strftime("%Y-%m-%d")), None)
    today_partial_live = bool(today_row and today_row.get("status") == 200 and int(today_row.get("rows", 0)) > 0 and pd.to_datetime(today_row.get("last"), utc=True, errors="coerce") >= now - pd.Timedelta(minutes=20))

    # Identify exact/live candidate according to prereg.
    equivalent_rows = []
    if len(cmpdf):
        equivalent_rows = cmpdf[cmpdf.get("archive_equivalent", False) == True].to_dict("records") if "archive_equivalent" in cmpdf.columns else []
    live_equivalent_rows = [r for r in equivalent_rows if bool(r.get("archive_equivalent_live"))]

    # Official near-lineage diagnostic, prereg-independent and no promotion.
    official_reported = [r for r in comparisons if r.get("family") == "official_rest" and r.get("value_kind") == "reported" and int(r.get("overlap_n", 0) or 0) >= MIN_OVERLAP]
    near_lineage = False
    if official_reported:
        near_lineage = any(
            (r.get("correlation") is not None and r.get("correlation") >= 0.999)
            and ((r.get("abs_error") or {}).get("p99") is not None and (r.get("abs_error") or {}).get("p99") <= 0.001)
            for r in official_reported
        )

    if today_partial_live:
        verdict = "ARCHIVE_EQUIVALENT_LIVE_SOURCE"
        winning_source = "data.binance.vision current-day daily metrics partial file"
    elif live_equivalent_rows:
        verdict = "ARCHIVE_EQUIVALENT_LIVE_SOURCE"
        winning_source = live_equivalent_rows[0].get("name")
    elif equivalent_rows:
        verdict = "ARCHIVE_EQUIVALENT_DELAYED_ONLY"
        winning_source = equivalent_rows[0].get("name")
    elif near_lineage:
        verdict = "NO_HIGH_PRECISION_PUBLIC_SOURCE_FOUND_OFFICIAL_REST_IS_LOSSY_NEAR_LINEAGE"
        winning_source = None
    else:
        verdict = "NO_ARCHIVE_EQUIVALENT_SOURCE_LINEAGE_UNRESOLVED"
        winning_source = None

    # Summarize best official reported route and reconstructions by MAE.
    def best_by_mean(rows):
        rows = [r for r in rows if int(r.get("overlap_n", 0) or 0) > 0 and (r.get("abs_error") or {}).get("mean") is not None]
        return min(rows, key=lambda r: (r["abs_error"]["mean"], -r.get("exact_share", 0.0))) if rows else None

    best_official = best_by_mean(official_reported)
    best_recon = best_by_mean([r for r in comparisons if r.get("family") == "official_reconstruction"])
    best_bapi = best_by_mean([r for r in comparisons if r.get("family") == "bapi"])

    metrics = {
        "lab": LAB,
        "run_time_utc": now,
        "canonical": {
            "latest_archive_day": latest_archive_day,
            "latest_archive_time": latest_archive_time,
            "recent_rows": int(len(arc)),
            "archive_ratio_digits_p50": float(arc.archive_digits.median()),
            "archive_ratio_digits_ge6_share": float((arc.archive_digits >= 6).mean()),
        },
        "current_day_archive_probe": today_row,
        "current_day_partial_live": today_partial_live,
        "official_docs_expected_precision_example": "4 decimals",
        "successful_official_host_n": int(len(successful_official)),
        "successful_bapi_path_n": int(sum(1 for x in source_summaries if x.get("family") == "bapi" and x.get("http_success"))),
        "best_official_reported": best_official,
        "best_component_reconstruction": best_recon,
        "best_bapi": best_bapi,
        "archive_equivalent_candidate_n": int(len(equivalent_rows)),
        "archive_equivalent_live_candidate_n": int(len(live_equivalent_rows) + (1 if today_partial_live else 0)),
        "official_rest_lossy_near_lineage": bool(near_lineage),
        "verdict": verdict,
        "winning_source": winning_source,
        "frozen_short_v1_changed": False,
        "live_allocation": 0,
    }
    with open(OUT / "metrics.json", "w") as f:
        json.dump(safe_json_scalar(metrics), f, indent=2)

    bo = best_official or {}
    br = best_recon or {}
    bb = best_bapi or {}
    report = f"""# {LAB} — REPORT

## Verdict
**{verdict}**

## Canonical archive
- latest available archive day: {latest_archive_day.date()}
- latest archive observation: {latest_archive_time}
- archive median decimal digits: {metrics['canonical']['archive_ratio_digits_p50']:.1f}
- current-day partial archive live: {today_partial_live}

## Best official REST
- candidate: {bo.get('name')}
- overlap N: {bo.get('overlap_n')}
- exact share: {bo.get('exact_share')}
- MAE: {(bo.get('abs_error') or {}).get('mean')}
- p99 abs error: {(bo.get('abs_error') or {}).get('p99')}
- max abs error: {(bo.get('abs_error') or {}).get('max')}
- median returned decimals: {bo.get('ratio_digits_p50')}
- correlation: {bo.get('correlation')}

## Best component reconstruction
- candidate: {br.get('name')}
- overlap N: {br.get('overlap_n')}
- exact share: {br.get('exact_share')}
- MAE: {(br.get('abs_error') or {}).get('mean')}

## Best BAPI candidate
- candidate: {bb.get('name')}
- overlap N: {bb.get('overlap_n')}
- exact share: {bb.get('exact_share')}
- MAE: {(bb.get('abs_error') or {}).get('mean')}

## Governance
Frozen SHORT v1 unchanged. No PnL or outcomes used. Live allocation remains 0. Any newly discovered source requires separate preregistration before clock use.
"""
    (OUT / "REPORT.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
