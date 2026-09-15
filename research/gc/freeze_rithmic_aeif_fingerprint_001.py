#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ZIP_URL = "https://github.com/chepigga/ResearchOS/releases/download/GC/GC_RITHMIC_40D_003_GCZ6.zip"
ZIP_SHA256 = "b12465a783f36aac41b82a9f2a5c4e74bd2dcf7024ffc3636e8c41a8fd01e803"
CORE_EXPECTED_SHA256 = "6f7bbed475cb8a627c51f5083852fb804d682d4a97b08313e51f6f918b4c011f"
CONF_EXPECTED_SHA256 = "05f343268d596a56dbce880e692ea9f055b51abcafbb98020a0608ab5da1bd69"
M5_MS = 300_000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dst: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ResearchOS-AEIF-Freeze/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response, dst.open("wb") as f:
        shutil.copyfileobj(response, f, 1024 * 1024)


def build_m5(zip_path: Path) -> pd.DataFrame:
    frames = []
    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(name for name in zf.namelist() if name.endswith(".csv.gz"))
        for name in names:
            with zf.open(name) as raw:
                with gzip.GzipFile(fileobj=raw) as gz:
                    day = pd.read_csv(gz, usecols=["time_ms", "price", "volume", "aggressor"])
            if len(day):
                frames.append(day)

    ticks = pd.concat(frames, ignore_index=True)
    ticks = ticks.sort_values("time_ms", kind="mergesort").reset_index(drop=True)
    ticks["bar_ms"] = (ticks.time_ms.astype("int64") // M5_MS) * M5_MS

    grouped = ticks.groupby("bar_ms", sort=True, observed=True)
    bars = grouped["price"].agg(open="first", high="max", low="min", close="last")
    bars["trades"] = grouped.size().astype("int64")
    bars["volume"] = grouped["volume"].sum()

    ticks["is_buy"] = ticks.aggressor.eq("BUY")
    ticks["is_sell"] = ticks.aggressor.eq("SELL")
    ticks["buy_size"] = ticks.volume.where(ticks.is_buy, 0.0)
    ticks["sell_size"] = ticks.volume.where(ticks.is_sell, 0.0)
    bars["buy_vol"] = grouped["buy_size"].sum()
    bars["sell_vol"] = grouped["sell_size"].sum()

    low = ticks["bar_ms"].map(bars["low"])
    high = ticks["bar_ms"].map(bars["high"])
    bar_range = high - low
    lower_cut = low + 0.20 * bar_range
    upper_cut = high - 0.20 * bar_range

    ticks["sell_lower20"] = ticks.volume.where(ticks.is_sell & (ticks.price <= lower_cut), 0.0)
    ticks["buy_upper20"] = ticks.volume.where(ticks.is_buy & (ticks.price >= upper_cut), 0.0)
    bars["sell_lower20"] = grouped["sell_lower20"].sum()
    bars["buy_upper20"] = grouped["buy_upper20"].sum()

    bars["sell_loc"] = np.where(bars.sell_vol > 0, bars.sell_lower20 / bars.sell_vol, 0.0)
    bars["buy_loc"] = np.where(bars.buy_vol > 0, bars.buy_upper20 / bars.buy_vol, 0.0)
    bars["delta"] = bars.buy_vol - bars.sell_vol
    bars["delta_frac"] = np.where(
        (bars.buy_vol + bars.sell_vol) > 0,
        bars.delta / (bars.buy_vol + bars.sell_vol),
        0.0,
    )

    prev_close = bars.close.shift(1)
    bars["tr"] = pd.concat(
        [
            bars.high - bars.low,
            (bars.high - prev_close).abs(),
            (bars.low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1, skipna=True)
    bars.loc[bars.index[0], "tr"] = np.nan
    bars["atr14_wilder"] = bars.tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    bars["q10_prior240"] = bars.delta_frac.shift(1).rolling(240, min_periods=240).quantile(0.10)
    bars["q90_prior240"] = bars.delta_frac.shift(1).rolling(240, min_periods=240).quantile(0.90)
    bars["q75_sell_loc_prior240"] = bars.sell_loc.shift(1).rolling(240, min_periods=240).quantile(0.75)
    bars["q75_buy_loc_prior240"] = bars.buy_loc.shift(1).rolling(240, min_periods=240).quantile(0.75)

    bars["down_body"] = (bars.open - bars.close).clip(lower=0)
    bars["up_body"] = (bars.close - bars.open).clip(lower=0)
    bars["dn_eff"] = bars.down_body / bars.atr14_wilder
    bars["up_eff"] = bars.up_body / bars.atr14_wilder

    bars = bars.reset_index()
    bars["bar"] = pd.to_datetime(bars.bar_ms, unit="ms", utc=True)
    return bars


def build_core_ledger(bars: pd.DataFrame) -> pd.DataFrame:
    long_mask = (
        (bars.delta_frac <= bars.q10_prior240)
        & (bars.sell_loc >= bars.q75_sell_loc_prior240)
        & (bars.dn_eff <= 0.15)
    )
    short_mask = (
        (bars.delta_frac >= bars.q90_prior240)
        & (bars.buy_loc >= bars.q75_buy_loc_prior240)
        & (bars.up_eff <= 0.15)
    )
    mask = long_mask | short_mask

    selected = bars.loc[mask].copy()
    selected["side"] = np.where(long_mask[mask].to_numpy(), "LONG", "SHORT")
    selected["directional_impact_atr"] = np.where(
        selected.side.eq("LONG"), selected.dn_eff, selected.up_eff
    )

    cooldown_keep = []
    last_kept = None
    for timestamp in selected.bar:
        keep = last_kept is None or (timestamp - last_kept) >= pd.Timedelta(minutes=30)
        cooldown_keep.append(int(keep))
        if keep:
            last_kept = timestamp
    selected["cooldown30_keep"] = cooldown_keep

    return pd.DataFrame(
        {
            "core_bar_utc": selected.bar.map(lambda value: value.isoformat()),
            "side": selected.side,
            "open": selected.open,
            "high": selected.high,
            "low": selected.low,
            "close": selected.close,
            "atr14_wilder": selected.atr14_wilder,
            "delta_frac": selected.delta_frac,
            "q10_prior240": selected.q10_prior240,
            "q90_prior240": selected.q90_prior240,
            "sell_loc": selected.sell_loc,
            "q75_sell_loc_prior240": selected.q75_sell_loc_prior240,
            "buy_loc": selected.buy_loc,
            "q75_buy_loc_prior240": selected.q75_buy_loc_prior240,
            "directional_impact_atr": selected.directional_impact_atr,
            "cooldown30_keep": selected.cooldown30_keep.astype(int),
        }
    )


def build_confirmed_ledger(bars: pd.DataFrame, core: pd.DataFrame) -> pd.DataFrame:
    bar_index = {timestamp: i for i, timestamp in enumerate(bars.bar)}
    rows = []

    for event in core.itertuples(index=False):
        core_time = pd.Timestamp(event.core_bar_utc)
        i = bar_index[core_time]

        for offset in (1, 2):
            if i + offset >= len(bars):
                break

            confirm = bars.iloc[i + offset]
            if confirm.bar != core_time + pd.Timedelta(minutes=5 * offset):
                break

            is_confirmed = (
                event.side == "LONG"
                and confirm.close > confirm.open
                and confirm.delta > 0
            ) or (
                event.side == "SHORT"
                and confirm.close < confirm.open
                and confirm.delta < 0
            )

            if is_confirmed:
                rows.append(
                    {
                        "core_bar_utc": core_time.isoformat(),
                        "side": event.side,
                        "confirm_bar_utc": confirm.bar.isoformat(),
                        "confirm_offset_bars": offset,
                        "confirm_open": confirm.open,
                        "confirm_close": confirm.close,
                        "confirm_delta": confirm.delta,
                        "entry_eligible_utc": (confirm.bar + pd.Timedelta(minutes=5)).isoformat(),
                    }
                )
                break

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("research/gc"))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.zip is None:
        work = Path(tempfile.mkdtemp())
        zip_path = work / "GC_RITHMIC_40D_003_GCZ6.zip"
        download(ZIP_URL, zip_path)
    else:
        zip_path = args.zip

    source_sha = sha256_file(zip_path)
    if source_sha != ZIP_SHA256:
        raise SystemExit(f"Source ZIP SHA256 mismatch: {source_sha}")

    bars = build_m5(zip_path)
    core = build_core_ledger(bars)
    confirmed = build_confirmed_ledger(bars, core)

    core_path = args.out_dir / "RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CORE_EVENTS.csv"
    confirmed_path = args.out_dir / "RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CONFIRMED_EVENTS.csv"
    manifest_path = args.out_dir / "RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_MANIFEST.json"

    core.to_csv(core_path, index=False)
    confirmed.to_csv(confirmed_path, index=False)

    core_sha = sha256_file(core_path)
    confirmed_sha = sha256_file(confirmed_path)

    if len(bars) != 8231:
        raise SystemExit(f"M5 fingerprint fail: {len(bars)} != 8231")
    if len(core) != 105:
        raise SystemExit(f"Core count fail: {len(core)} != 105")
    if int(core.cooldown30_keep.sum()) != 92:
        raise SystemExit(f"Cooldown count fail: {int(core.cooldown30_keep.sum())} != 92")
    if len(confirmed) != 61:
        raise SystemExit(f"Confirmation count fail: {len(confirmed)} != 61")
    if core_sha != CORE_EXPECTED_SHA256:
        raise SystemExit(f"Core ledger SHA256 fail: {core_sha}")
    if confirmed_sha != CONF_EXPECTED_SHA256:
        raise SystemExit(f"Confirmed ledger SHA256 fail: {confirmed_sha}")

    manifest = {
        "artifact_id": "RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001",
        "status": "SIGNAL_FINGERPRINT_CERTIFIED",
        "source_release_tag": "GC",
        "source_asset": "GC_RITHMIC_40D_003_GCZ6.zip",
        "source_asset_sha256": ZIP_SHA256,
        "raw_trade_prints": 3949646,
        "m5_bars": len(bars),
        "core_events": len(core),
        "core_long": int(core.side.eq("LONG").sum()),
        "core_short": int(core.side.eq("SHORT").sum()),
        "cooldown30_events": int(core.cooldown30_keep.sum()),
        "confirmed_events": len(confirmed),
        "confirmed_long": int(confirmed.side.eq("LONG").sum()),
        "confirmed_short": int(confirmed.side.eq("SHORT").sum()),
        "core_ledger": core_path.name,
        "core_ledger_sha256": core_sha,
        "confirmed_ledger": confirmed_path.name,
        "confirmed_ledger_sha256": confirmed_sha,
        "amp_oos_used_for_parameter_selection": False,
        "amp_gate": "OPEN_FOR_SINGLE_UNTOUCHED_OOS_SIGNAL_REPLICATION",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
