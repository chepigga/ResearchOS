#!/usr/bin/env python3
"""AMP_GC_M5_FOOTPRINT_BUILD_001

Builds a deterministic M5 footprint from the canonical AMP/CQG GC raw trade export.
Pure data transformation: NO AEIF thresholds, NO signal selection, NO trading.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import shutil
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

OWNER = "chepigga"
REPO = "ResearchOS"
TAG = "GC"
RELEASE_API = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{TAG}"
ROOT = Path("research/gc")
AUDIT_JSON = ROOT / "AMP_GC_FEED_AUDIT_001.json"
OUT_CSV = ROOT / "AMP_GC_OOS_001_M5_FOOTPRINT.csv"
OUT_REPORT = ROOT / "AMP_GC_M5_FOOTPRINT_BUILD_001.md"
OUT_MANIFEST = ROOT / "AMP_GC_OOS_001_MANIFEST.json"
WORK = ROOT / "_m5_build_work"
M5_MS = 5 * 60 * 1000


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "ResearchOS-GC-M5/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def download(url: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ResearchOS-GC-M5/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, dst.open("wb") as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def as_int(v, default=0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def as_float(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def tick_reader(zip_path: Path) -> Iterable[dict]:
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise RuntimeError(f"Expected one CSV in {zip_path.name}; got {names}")
        with zf.open(names[0], "r") as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            yield from csv.DictReader(text)


def vol(row: dict) -> float:
    vr = as_float(row.get("volume_real"), 0.0)
    return vr if vr > 0 else float(as_int(row.get("volume"), 0))


def utc_text(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Bar:
    start_msc: int
    o: float
    h: float
    l: float
    c: float
    trades: int = 0
    volume: float = 0.0
    buy_ticks: int = 0
    sell_ticks: int = 0
    both_ticks: int = 0
    none_ticks: int = 0
    buy_vol: float = 0.0
    sell_vol: float = 0.0
    both_vol: float = 0.0
    buy_only_vol: float = 0.0
    sell_only_vol: float = 0.0
    # price -> [buy_inc, sell_inc, buy_only, sell_only]
    levels: Dict[float, List[float]] | None = None

    def __post_init__(self):
        if self.levels is None:
            self.levels = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])

    def add(self, price: float, size: float, is_buy: bool, is_sell: bool):
        if self.trades == 0:
            self.o = self.h = self.l = self.c = price
        else:
            self.h = max(self.h, price)
            self.l = min(self.l, price)
            self.c = price
        self.trades += 1
        self.volume += size
        if is_buy:
            self.buy_ticks += 1
            self.buy_vol += size
        if is_sell:
            self.sell_ticks += 1
            self.sell_vol += size
        if is_buy and is_sell:
            self.both_ticks += 1
            self.both_vol += size
        elif is_buy:
            self.buy_only_vol += size
        elif is_sell:
            self.sell_only_vol += size
        else:
            self.none_ticks += 1
        lvl = self.levels[price]
        if is_buy:
            lvl[0] += size
        if is_sell:
            lvl[1] += size
        if is_buy and not is_sell:
            lvl[2] += size
        if is_sell and not is_buy:
            lvl[3] += size


def finalize_bar(bar: Bar, prev_close: float | None) -> dict:
    rng = bar.h - bar.l
    lower_cut = bar.l + 0.20 * rng
    upper_cut = bar.h - 0.20 * rng

    lower_buy = lower_sell = upper_buy = upper_sell = 0.0
    lower_buy_only = lower_sell_only = upper_buy_only = upper_sell_only = 0.0

    # Inclusive endpoints are intentional and deterministic.
    for price, v in bar.levels.items():
        if price <= lower_cut + 1e-12:
            lower_buy += v[0]
            lower_sell += v[1]
            lower_buy_only += v[2]
            lower_sell_only += v[3]
        if price >= upper_cut - 1e-12:
            upper_buy += v[0]
            upper_sell += v[1]
            upper_buy_only += v[2]
            upper_sell_only += v[3]

    def share(x, d):
        return 0.0 if d <= 0 else x / d

    delta_inc = bar.buy_vol - bar.sell_vol
    denom_inc = bar.buy_vol + bar.sell_vol
    delta_exc = bar.buy_only_vol - bar.sell_only_vol
    denom_exc = bar.buy_only_vol + bar.sell_only_vol

    tr = rng if prev_close is None else max(rng, abs(bar.h - prev_close), abs(bar.l - prev_close))

    return {
        "bar_start_msc": bar.start_msc,
        "bar_start_utc": utc_text(bar.start_msc),
        "open": bar.o,
        "high": bar.h,
        "low": bar.l,
        "close": bar.c,
        "range": rng,
        "true_range": tr,
        "trades": bar.trades,
        "volume": bar.volume,
        "buy_ticks": bar.buy_ticks,
        "sell_ticks": bar.sell_ticks,
        "both_ticks": bar.both_ticks,
        "none_ticks": bar.none_ticks,
        "buy_volume": bar.buy_vol,
        "sell_volume": bar.sell_vol,
        "both_volume": bar.both_vol,
        "buy_only_volume": bar.buy_only_vol,
        "sell_only_volume": bar.sell_only_vol,
        "delta": delta_inc,
        "delta_frac": 0.0 if denom_inc <= 0 else delta_inc / denom_inc,
        "delta_exclusive": delta_exc,
        "delta_frac_exclusive": 0.0 if denom_exc <= 0 else delta_exc / denom_exc,
        "lower20_price_cut": lower_cut,
        "upper20_price_cut": upper_cut,
        "sell_volume_lower20": lower_sell,
        "sell_concentration_lower20": share(lower_sell, bar.sell_vol),
        "buy_volume_upper20": upper_buy,
        "buy_concentration_upper20": share(upper_buy, bar.buy_vol),
        "buy_volume_lower20": lower_buy,
        "buy_concentration_lower20": share(lower_buy, bar.buy_vol),
        "sell_volume_upper20": upper_sell,
        "sell_concentration_upper20": share(upper_sell, bar.sell_vol),
        "sell_only_volume_lower20": lower_sell_only,
        "sell_only_concentration_lower20": share(lower_sell_only, bar.sell_only_vol),
        "buy_only_volume_upper20": upper_buy_only,
        "buy_only_concentration_upper20": share(upper_buy_only, bar.buy_only_vol),
        "buy_only_volume_lower20": lower_buy_only,
        "sell_only_volume_upper20": upper_sell_only,
    }


def add_atr_and_clock_fields(rows: List[dict]) -> None:
    # Diagnostics only. No AEIF threshold is applied here.
    # Both standard Wilder ATR20 and SMA(TR,20) are exported until the frozen
    # Rithmic implementation's exact ATR convention is re-attached by parity.
    trs: List[float] = []
    wilder = None
    prev_start = None
    for i, r in enumerate(rows):
        tr = float(r["true_range"])
        trs.append(tr)
        r["completed_bar_index"] = i + 1
        r["warmup_240_completed"] = 1 if (i + 1) >= 240 else 0
        if prev_start is None:
            r["gap_from_prev_m5_bars"] = 0
            r["clock_contiguous_from_prev"] = 0
        else:
            diff = (r["bar_start_msc"] - prev_start) // M5_MS
            r["gap_from_prev_m5_bars"] = max(0, int(diff - 1))
            r["clock_contiguous_from_prev"] = 1 if diff == 1 else 0
        prev_start = r["bar_start_msc"]

        if len(trs) >= 20:
            r["atr20_sma"] = sum(trs[-20:]) / 20.0
        else:
            r["atr20_sma"] = ""

        if i == 19:
            wilder = sum(trs[:20]) / 20.0
            r["atr20_wilder"] = wilder
        elif i > 19:
            wilder = ((wilder * 19.0) + tr) / 20.0
            r["atr20_wilder"] = wilder
        else:
            r["atr20_wilder"] = ""


def main() -> int:
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    if not audit.get("overall_pass"):
        raise RuntimeError("AMP_GC_FEED_AUDIT_001 is not PASS")
    canonical = audit["canonical_run"]
    run = audit["runs"][canonical]
    expected_rows = int(run["ticks"]["rows"])
    expected_digest = run["asset_sha256"]["TICKS.csv.zip"].replace("sha256:", "")

    release = get_json(RELEASE_API)
    target_name = f"AMP_GC_HISTORY_EXPORTER_001_GCEZ26_{canonical}_TICKS.csv.zip"
    asset = next((a for a in release.get("assets", []) if a.get("name") == target_name), None)
    if asset is None:
        raise RuntimeError(f"Release asset not found: {target_name}")

    WORK.mkdir(parents=True, exist_ok=True)
    zip_path = WORK / target_name
    download(asset["browser_download_url"], zip_path)
    got_digest = sha256_file(zip_path)
    if got_digest != expected_digest:
        raise RuntimeError(f"Canonical ZIP SHA256 mismatch: {got_digest} != {expected_digest}")

    rows: List[dict] = []
    current: Bar | None = None
    prev_close = None
    raw_rows = 0
    raw_buy = raw_sell = raw_both = raw_none = 0
    raw_volume = raw_buy_vol = raw_sell_vol = 0.0
    first_tick = last_tick = None
    prev_tick_time = None
    non_monotonic = 0

    for tick in tick_reader(zip_path):
        raw_rows += 1
        t = as_int(tick.get("time_msc"))
        price = as_float(tick.get("last"))
        size = vol(tick)
        buy = tick.get("is_buy") == "1"
        sell = tick.get("is_sell") == "1"
        if first_tick is None:
            first_tick = t
        last_tick = t
        if prev_tick_time is not None and t < prev_tick_time:
            non_monotonic += 1
        prev_tick_time = t
        if buy: raw_buy += 1; raw_buy_vol += size
        if sell: raw_sell += 1; raw_sell_vol += size
        if buy and sell: raw_both += 1
        if not buy and not sell: raw_none += 1
        raw_volume += size

        start = (t // M5_MS) * M5_MS
        if current is None:
            current = Bar(start, price, price, price, price)
        elif start != current.start_msc:
            rows.append(finalize_bar(current, prev_close))
            prev_close = current.c
            current = Bar(start, price, price, price, price)
        current.add(price, size, buy, sell)

    if current is not None:
        rows.append(finalize_bar(current, prev_close))

    if raw_rows != expected_rows:
        raise RuntimeError(f"Raw row mismatch: {raw_rows} != {expected_rows}")
    if non_monotonic != 0:
        raise RuntimeError(f"Non-monotonic raw ticks: {non_monotonic}")
    if sum(int(r["trades"]) for r in rows) != raw_rows:
        raise RuntimeError("M5 trade-count conservation failed")
    if sum(int(r["buy_ticks"]) for r in rows) != raw_buy:
        raise RuntimeError("M5 BUY tick conservation failed")
    if sum(int(r["sell_ticks"]) for r in rows) != raw_sell:
        raise RuntimeError("M5 SELL tick conservation failed")

    add_atr_and_clock_fields(rows)

    fields = list(rows[0].keys())
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rows)

    footprint_sha = sha256_file(OUT_CSV)
    both_share = 0.0 if raw_rows == 0 else 100.0 * raw_both / raw_rows
    gap_bars = sum(1 for r in rows if int(r["gap_from_prev_m5_bars"]) > 0)
    warm_rows = sum(1 for r in rows if int(r["warmup_240_completed"]) == 1)

    manifest = {
        "dataset_id": "AMP_GC_OOS_001",
        "status": "FROZEN_RAW_AND_M5",
        "source_release": release.get("html_url"),
        "canonical_run": canonical,
        "symbol": run["meta"].get("symbol", "GCEZ26"),
        "account_server": run["meta"].get("account_server"),
        "raw_zip_asset": target_name,
        "raw_zip_sha256": got_digest,
        "raw_rows": raw_rows,
        "first_tick_msc": first_tick,
        "last_tick_msc": last_tick,
        "m5_rows": len(rows),
        "m5_footprint_file": str(OUT_CSV),
        "m5_footprint_sha256": footprint_sha,
        "audit_overlap_sha256": audit["comparison"]["overlap_sha256_b"],
        "aEIF_parameters_applied": False,
        "notes": "M5 footprint only; no selector, quantile threshold, confirmation, or exit logic applied.",
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    first_bar = rows[0]["bar_start_utc"]
    last_bar = rows[-1]["bar_start_utc"]
    lines = [
        "# AMP_GC_M5_FOOTPRINT_BUILD_001",
        "",
        "## Verdict: PASS",
        "",
        "Canonical raw dataset is frozen as **`AMP_GC_OOS_001`**. This LAB is data transformation only: **NO AEIF THRESHOLDS / NO RETUNING / NO TRADING**.",
        "",
        f"- Canonical run: `{canonical}`",
        f"- Raw ZIP SHA256 verified: `{got_digest}`",
        f"- Raw trade prints: **{raw_rows:,}**",
        f"- M5 footprint bars with >=1 trade: **{len(rows):,}**",
        f"- First/last M5: **{first_bar} UTC → {last_bar} UTC**",
        f"- BUY / SELL / BOTH / NONE ticks: **{raw_buy:,} / {raw_sell:,} / {raw_both:,} / {raw_none:,}**",
        f"- BOTH tick share: **{both_share:.4f}%** (preserved; exclusive-side columns also exported)",
        f"- Raw total volume: **{raw_volume:.0f}**",
        f"- BUY / SELL volume: **{raw_buy_vol:.0f} / {raw_sell_vol:.0f}**",
        f"- Bars after >=240 completed-bar warm-up: **{warm_rows:,}**",
        f"- Non-contiguous M5 transitions (market closures/gaps included): **{gap_bars:,}**",
        f"- M5 footprint SHA256: `{footprint_sha}`",
        "",
        "## Conservation checks",
        "",
        f"- raw rows == sum(M5 trades): **{raw_rows:,} == {sum(int(r['trades']) for r in rows):,}**",
        f"- raw BUY ticks == sum(M5 BUY): **{raw_buy:,} == {sum(int(r['buy_ticks']) for r in rows):,}**",
        f"- raw SELL ticks == sum(M5 SELL): **{raw_sell:,} == {sum(int(r['sell_ticks']) for r in rows):,}**",
        f"- raw timestamp monotonic violations: **{non_monotonic}**",
        "",
        "## Exported causal-at-bar-close features",
        "",
        "`OHLC`, `trades`, `volume`, inclusive and exclusive `BUY/SELL volume`, `delta`, `delta_frac`, lower/upper 20% price bands, side volume/concentration inside those bands, `true_range`, `ATR20 SMA`, `ATR20 Wilder`, 240-completed-bar warm-up marker, and clock-gap diagnostics.",
        "",
        "Both ATR20 conventions and both inclusive/exclusive aggressor variants are diagnostics only. The frozen Rithmic AEIF implementation must choose its original convention during parity reconstruction; this LAB deliberately does not choose or tune one.",
        "",
        "## Next",
        "",
        "Reattach the exact frozen Rithmic AEIF selector to this footprint. Known frozen pieces are Q10/Q90 delta tail, Q75 location concentration, failed impact ~0.15 ATR, and max two M5 confirmation bars. The exact original rolling-window/ATR convention must be recovered rather than guessed before signal replication.",
    ]
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT_REPORT.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
