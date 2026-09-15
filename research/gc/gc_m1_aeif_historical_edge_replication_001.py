#!/usr/bin/env python3
"""GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001

Purpose
-------
Test the ORIGINAL LAB001 M1 effort/result hypothesis on the raw historical GC
feeds already available in the GC release. This is a mechanism replication,
not an optimizer. No XAU data and no trade execution are used.

Frozen LAB001 hypothesis used here:
A: prior-240 M1 delta_frac Q10/Q90 extreme + aggressor-side volume >= prior Q75.
B: current directional body/ATR14 is <= causal Q20 among PRIOR same-side A events,
   requiring at least 15 prior same-side A events.
D: first clock-contiguous next <=2 M1 bars has opposite delta and reversal-direction body.

ATR convention: simple rolling mean of True Range over 14 M1 bars. This follows the
LAB003 report's explicit description of LAB001 ATR14 as the clock-time reference
approximated by simple ATR3 on M5.

Primary forward outcome is directional close-to-close ATR-normalized return from
A/B event close at exact +1/+3/+5/+15 minute clock bars, matching LAB001's
information-edge framing. D is a subset label; no executable entry is implied.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
OUT_JSON = ROOT / "GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001.json"
OUT_MD = ROOT / "GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001.md"
OUT_EVENTS = ROOT / "GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001_EVENTS.csv"

RITH_URL = "https://github.com/chepigga/ResearchOS/releases/download/GC/GC_RITHMIC_40D_003_GCZ6.zip"
RITH_SHA = "b12465a783f36aac41b82a9f2a5c4e74bd2dcf7024ffc3636e8c41a8fd01e803"
AMP_URL = "https://github.com/chepigga/ResearchOS/releases/download/GC/AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip"
AMP_SHA = "81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b"

M1_MS = 60_000
HORIZONS = (1, 3, 5, 15)
ATAS_START = pd.Timestamp("2026-09-06T22:00:00Z")
ATAS_END = pd.Timestamp("2026-09-11T12:46:00Z")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, p: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ResearchOS-GC-M1-AEIF/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, p.open("wb") as f:
        shutil.copyfileobj(r, f, 1024 * 1024)


def aggregate_ticks(t: pd.DataFrame, feed: str) -> pd.DataFrame:
    t = t.sort_values("time_ms", kind="mergesort").reset_index(drop=True)
    t = t[(t.price > 0) & (t.volume > 0)].copy()
    t["bar_ms"] = (t.time_ms.astype("int64") // M1_MS) * M1_MS
    t["buy_size"] = t.volume.where(t.aggressor.eq("BUY"), 0.0)
    t["sell_size"] = t.volume.where(t.aggressor.eq("SELL"), 0.0)
    g = t.groupby("bar_ms", sort=True, observed=True)
    b = g.price.agg(open="first", high="max", low="min", close="last")
    b["trades"] = g.size().astype(int)
    b["volume"] = g.volume.sum()
    b["buy_vol"] = g.buy_size.sum()
    b["sell_vol"] = g.sell_size.sum()
    b["delta"] = b.buy_vol - b.sell_vol
    den = b.buy_vol + b.sell_vol
    b["delta_frac"] = np.where(den > 0, b.delta / den, 0.0)
    pc = b.close.shift(1)
    b["tr"] = pd.concat(
        [(b.high - b.low), (b.high - pc).abs(), (b.low - pc).abs()], axis=1
    ).max(axis=1)
    b.iloc[0, b.columns.get_loc("tr")] = np.nan
    b["atr14"] = b.tr.rolling(14, min_periods=14).mean()
    b["body_atr"] = (b.close - b.open) / b.atr14
    b["q10_delta"] = b.delta_frac.shift(1).rolling(240, min_periods=240).quantile(0.10)
    b["q90_delta"] = b.delta_frac.shift(1).rolling(240, min_periods=240).quantile(0.90)
    b["q75_buy"] = b.buy_vol.shift(1).rolling(240, min_periods=240).quantile(0.75)
    b["q75_sell"] = b.sell_vol.shift(1).rolling(240, min_periods=240).quantile(0.75)
    b = b.reset_index()
    b["time"] = pd.to_datetime(b.bar_ms, unit="ms", utc=True)
    b["feed"] = feed
    return b


def load_rithmic(zp: Path) -> pd.DataFrame:
    frames = []
    with zipfile.ZipFile(zp) as zf:
        names = sorted(n for n in zf.namelist() if n.endswith(".csv.gz"))
        for name in names:
            with zf.open(name) as raw, gzip.GzipFile(fileobj=raw) as gz:
                d = pd.read_csv(gz, usecols=["time_ms", "price", "volume", "aggressor"])
            if len(d):
                frames.append(d)
    t = pd.concat(frames, ignore_index=True)
    t["aggressor"] = t.aggressor.astype(str).str.upper()
    t = t[t.aggressor.isin(["BUY", "SELL"])]
    return aggregate_ticks(t, "RITHMIC_RAW")


def load_amp(zp: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zp) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise RuntimeError(f"AMP zip expected one csv, got {names}")
        with zf.open(names[0]) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            d = pd.read_csv(
                text,
                usecols=["time_msc", "last", "volume", "volume_real", "is_buy", "is_sell"],
            )
    vr = pd.to_numeric(d.volume_real, errors="coerce").fillna(0.0)
    vi = pd.to_numeric(d.volume, errors="coerce").fillna(0.0)
    size = np.where(vr > 0, vr, vi)
    is_buy = pd.to_numeric(d.is_buy, errors="coerce").fillna(0).astype(int).eq(1)
    is_sell = pd.to_numeric(d.is_sell, errors="coerce").fillna(0).astype(int).eq(1)
    # Pre-registered bridge: exclude simultaneous BUY+SELL flags from directional volume.
    aggressor = np.where(
        is_buy & ~is_sell,
        "BUY",
        np.where(is_sell & ~is_buy, "SELL", "EXCLUDE"),
    )
    t = pd.DataFrame(
        {
            "time_ms": pd.to_numeric(d.time_msc, errors="coerce"),
            "price": pd.to_numeric(d["last"], errors="coerce"),
            "volume": size,
            "aggressor": aggressor,
        }
    )
    t = t[t.aggressor.isin(["BUY", "SELL"])].dropna(subset=["time_ms", "price"])
    return aggregate_ticks(t, "AMP_CQG_RAW_EXCLUSIVE")


def build_events(b: pd.DataFrame) -> pd.DataFrame:
    a_long = (b.delta_frac <= b.q10_delta) & (b.sell_vol >= b.q75_sell)
    a_short = (b.delta_frac >= b.q90_delta) & (b.buy_vol >= b.q75_buy)
    if bool((a_long & a_short).any()):
        raise RuntimeError("same bar long+short A")

    a = b.loc[a_long | a_short].copy()
    a["side"] = np.where(a_long[a_long | a_short].to_numpy(), "LONG", "SHORT")
    # Price result in aggression direction: positive means aggression moved price as expected.
    a["dir_result"] = np.where(a.side.eq("LONG"), -a.body_atr, a.body_atr)
    a["b_thresh"] = np.nan
    a["stage_b"] = False

    history = {"LONG": [], "SHORT": []}
    for idx, row in a.iterrows():
        prior = history[row.side]
        if len(prior) >= 15:
            q20 = float(np.quantile(np.asarray(prior, float), 0.20))
            a.at[idx, "b_thresh"] = q20
            a.at[idx, "stage_b"] = bool(row.dir_result <= q20)
        prior.append(float(row.dir_result))

    idx_by_time = {timestamp: i for i, timestamp in enumerate(b.time)}
    # Explicit UTC dtype: pandas 3.x rejects tz-aware assignment into tz-naive datetime64.
    a["response_time"] = pd.Series(pd.NaT, index=a.index, dtype="datetime64[ns, UTC]")
    a["response_offset"] = np.nan
    for idx, row in a[a.stage_b].iterrows():
        i = idx_by_time[row.time]
        for offset in (1, 2):
            if i + offset >= len(b):
                break
            response = b.iloc[i + offset]
            if response.time != row.time + pd.Timedelta(minutes=offset):
                break
            confirmed = (
                row.side == "LONG" and response.delta > 0 and response.close > response.open
            ) or (
                row.side == "SHORT" and response.delta < 0 and response.close < response.open
            )
            if confirmed:
                a.at[idx, "response_time"] = response.time
                a.at[idx, "response_offset"] = offset
                break
    a["stage_d"] = a.response_time.notna()

    close_by_time = dict(zip(b.time, b.close))
    for horizon in HORIZONS:
        values = []
        for row in a.itertuples():
            future_time = row.time + pd.Timedelta(minutes=horizon)
            future_close = close_by_time.get(future_time, np.nan)
            if not np.isfinite(future_close) or not np.isfinite(row.atr14) or row.atr14 <= 0:
                values.append(np.nan)
            else:
                values.append(
                    (future_close - row.close) / row.atr14
                    if row.side == "LONG"
                    else (row.close - future_close) / row.atr14
                )
        a[f"fwd_{horizon}m_atr"] = values
    return a


def metric(x: pd.DataFrame, horizon: int) -> dict:
    values = x[f"fwd_{horizon}m_atr"].dropna().astype(float).to_numpy()
    if not len(values):
        return {"n": 0, "mean_atr": None, "median_atr": None, "win_pct": None}
    return {
        "n": int(len(values)),
        "mean_atr": float(values.mean()),
        "median_atr": float(np.median(values)),
        "win_pct": float((values > 0).mean() * 100),
    }


def summarize_window(ev: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    z = ev[(ev.time >= start) & (ev.time <= end)].copy()
    out = {
        "events_A": int(len(z)),
        "events_B": int(z.stage_b.sum()),
        "events_D": int(z.stage_d.sum()),
        "long_A": int((z.side == "LONG").sum()),
        "short_A": int((z.side == "SHORT").sum()),
        "long_B": int(((z.side == "LONG") & z.stage_b).sum()),
        "short_B": int(((z.side == "SHORT") & z.stage_b).sum()),
        "long_D": int(((z.side == "LONG") & z.stage_d).sum()),
        "short_D": int(((z.side == "SHORT") & z.stage_d).sum()),
        "stage": {},
    }
    for stage, mask in [
        ("A", pd.Series(True, index=z.index)),
        ("B", z.stage_b),
        ("D", z.stage_d),
    ]:
        out["stage"][stage] = {}
        for horizon in HORIZONS:
            out["stage"][stage][str(horizon)] = metric(z[mask], horizon)
        out["stage"][stage]["side_5m"] = {
            "LONG": metric(z[mask & (z.side == "LONG")], 5),
            "SHORT": metric(z[mask & (z.side == "SHORT")], 5),
        }
        out["stage"][stage]["side_15m"] = {
            "LONG": metric(z[mask & (z.side == "LONG")], 15),
            "SHORT": metric(z[mask & (z.side == "SHORT")], 15),
        }

    # Day stability is descriptive only and never gates/selects a variant.
    b_events = z[z.stage_b].copy()
    for horizon in (5, 15):
        tmp = b_events.dropna(subset=[f"fwd_{horizon}m_atr"]).copy()
        tmp["day"] = tmp.time.dt.date
        daily = tmp.groupby("day")[f"fwd_{horizon}m_atr"].mean()
        out[f"B_day_stability_{horizon}m"] = {
            "days": int(len(daily)),
            "positive_days": int((daily > 0).sum()),
            "median_daily_mean_atr": float(daily.median()) if len(daily) else None,
        }
    return out


def run_feed(b: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    events = build_events(b)
    start = b.time.iloc[0]
    end = b.time.iloc[-1]
    overlap_start = max(start, ATAS_START)
    overlap_end = min(end, ATAS_END)
    result = {
        "bars": int(len(b)),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "full": summarize_window(events, start, end),
        "atas_overlap": (
            summarize_window(events, overlap_start, overlap_end)
            if overlap_start < overlap_end
            else None
        ),
    }
    return result, events


def fmt_stage(name: str, result: dict) -> list[str]:
    lines = [
        f"### {name}",
        "",
        "| Stage | N | 1m | 3m | 5m | 15m |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for stage in ("A", "B", "D"):
        metrics = result["stage"][stage]
        n = metrics["5"]["n"]

        def value(horizon: int) -> str:
            v = metrics[str(horizon)]["mean_atr"]
            return "NA" if v is None else f"{v:+.3f}"

        lines.append(
            f"| {stage} | {n} | {value(1)} | {value(3)} | {value(5)} | {value(15)} |"
        )
    return lines


def main() -> None:
    work = ROOT / "_m1_edge_work"
    work.mkdir(parents=True, exist_ok=True)
    rithmic_zip = work / "rithmic.zip"
    amp_zip = work / "amp.zip"
    if not rithmic_zip.exists():
        download(RITH_URL, rithmic_zip)
    if not amp_zip.exists():
        download(AMP_URL, amp_zip)
    if sha256_file(rithmic_zip) != RITH_SHA:
        raise SystemExit("Rithmic SHA mismatch")
    if sha256_file(amp_zip) != AMP_SHA:
        raise SystemExit("AMP SHA mismatch")

    rithmic_bars = load_rithmic(rithmic_zip)
    amp_bars = load_amp(amp_zip)
    rithmic_result, rithmic_events = run_feed(rithmic_bars)
    amp_result, amp_events = run_feed(amp_bars)

    all_events = pd.concat([rithmic_events, amp_events], ignore_index=True)
    columns = [
        "feed", "time", "side", "open", "high", "low", "close",
        "buy_vol", "sell_vol", "delta", "delta_frac", "atr14", "body_atr",
        "dir_result", "b_thresh", "stage_b", "response_time", "response_offset",
        "stage_d", *[f"fwd_{horizon}m_atr" for horizon in HORIZONS],
    ]
    all_events[columns].to_csv(OUT_EVENTS, index=False)

    result = {
        "lab": "GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001",
        "status": "COMPLETED_NO_PARAMETER_SWEEP",
        "hypothesis_source": "LAB001_GC_CAUSAL_EFFORT_RESULT / ATAS-dxFeed M1",
        "parameters": {
            "tf": "M1",
            "prior_bars": 240,
            "delta_q": [0.10, 0.90],
            "side_volume_q": 0.75,
            "atr": "SMA TR14",
            "B_q": 0.20,
            "B_min_prior_same_side_A": 15,
            "D_max_bars": 2,
            "horizons_min": list(HORIZONS),
        },
        "rithmic": rithmic_result,
        "amp": amp_result,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        "# GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001",
        "",
        "Exact LAB001-style M1 mechanism replication on raw GC feeds already in the GC release. No XAU, no execution model, no threshold sweep.",
        "",
        "## Original ATAS/dxFeed reference",
        "",
        "- LAB001 reference: A N=356, B N=77, D N=46 on 2026-09-06 22:00 through 2026-09-11 12:46.",
        "- Reference B EV: 5m +0.407 ATR; 15m +0.561 ATR.",
        "- Reference D EV: 5m +0.399 ATR; 15m +0.646 ATR.",
        "",
    ]
    for feed_name, feed_result in [
        ("Rithmic raw", rithmic_result),
        ("AMP/CQG raw", amp_result),
    ]:
        lines += [
            f"## {feed_name}",
            "",
            f"Coverage: `{feed_result['start']}` → `{feed_result['end']}`; M1 bars **{feed_result['bars']}**.",
            "",
        ]
        lines += fmt_stage("Full historical coverage", feed_result["full"]) + [""]
        if feed_result["atas_overlap"]:
            lines += fmt_stage(
                "Exact ATAS/LAB001 clock overlap", feed_result["atas_overlap"]
            ) + [""]
            overlap = feed_result["atas_overlap"]
            lines += [
                f"Overlap counts: A **{overlap['events_A']}**, B **{overlap['events_B']}**, D **{overlap['events_D']}**.",
                "",
            ]

    lines += [
        "## Interpretation rule",
        "",
        "This LAB does not select a winner across feeds or variants. The question is whether the original M1 effort/result mechanism remains directionally positive on longer raw histories and on the exact LAB001 clock overlap. If full-history B/D loses sign while only the short overlap is positive, the edge is regime/sample-specific. If B/D remains positive across both raw feeds, it is materially stronger evidence for a transportable M1 GC edge.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT_MD.read_text())
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
