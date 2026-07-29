#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BH_OOS_Oracle_v002.py
Project: Grok_XAU / AK47_FT BH_SWEEP
Date: 2026-07-24
Status: frozen parity validator
Causal: yes

Implements the frozen BH_SWEEP signal engine from AK47_FT_EA_156.mq5:
F=5, swing age=96, pattern window=3, body>=0.60*range,
opposite shadow<=0.05*range, EMA20 reversal context,
entry at next M15 open, SL extremum +/- 0.25*ATR14,
TP=2R, 96 actual M15-bar timeout, conservative same-bar SL priority.

OOS net convention: R_net = R_raw - 0.05R per trade.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

FRACTAL_DEPTH = 5
SWING_MAX_AGE = 96
PATTERN_WINDOW = 3
BODY_MIN = 0.60
SHADOW_MAX = 0.05
SL_BUFFER_ATR = 0.25
TAKE_PROFIT_R = 2.0
TIME_STOP_BARS = 96
EMA_PERIOD = 20
ATR_PERIOD = 14
COST_R = 0.05


@dataclass
class Swing:
    bar: int
    level: float
    dead: bool = False


@dataclass
class Event:
    bar: int
    direction: int
    level: float
    done: bool = False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wilder_atr(data: pd.DataFrame, period: int = ATR_PERIOD) -> np.ndarray:
    prev_close = data["close"].shift(1)
    tr = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - prev_close).abs(),
            (data["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1).to_numpy(float)

    atr = np.full(len(tr), np.nan)
    if len(tr) < period:
        return atr
    atr[period - 1] = np.nanmean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def load_mt5_m15(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, sep="\t")
    data.columns = [c.strip("<>").lower() for c in data.columns]
    required = {"date", "time", "open", "high", "low", "close"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    data["dt"] = pd.to_datetime(
        data["date"].astype(str) + " " + data["time"].astype(str),
        format="%Y.%m.%d %H:%M:%S",
    )
    for col in ("open", "high", "low", "close"):
        data[col] = pd.to_numeric(data[col], errors="raise")
    data = data.sort_values("dt").drop_duplicates("dt", keep="last").reset_index(drop=True)
    data["ema20"] = data["close"].ewm(span=EMA_PERIOD, adjust=False).mean()
    data["atr14"] = wilder_atr(data)
    return data


def is_belt_hold(o: float, h: float, l: float, c: float, direction: int) -> bool:
    rng = h - l
    if rng <= 0:
        return False
    if abs(c - o) < BODY_MIN * rng:
        return False
    if direction == 1:
        return c > o and (o - l) <= SHADOW_MAX * rng
    return c < o and (h - o) <= SHADOW_MAX * rng


def generate_signals(data: pd.DataFrame) -> pd.DataFrame:
    o = data["open"].to_numpy(float)
    h = data["high"].to_numpy(float)
    l = data["low"].to_numpy(float)
    c = data["close"].to_numpy(float)
    ema = data["ema20"].to_numpy(float)
    times = data["dt"].to_numpy()

    lows: List[Swing] = []
    highs: List[Swing] = []
    events: List[Event] = []
    output = []

    for i in range(len(data)):
        center = i - FRACTAL_DEPTH
        if center >= FRACTAL_DEPTH:
            is_low = True
            is_high = True
            for k in range(1, FRACTAL_DEPTH + 1):
                if not (l[center] < l[center - k] and l[center] < l[center + k]):
                    is_low = False
                if not (h[center] > h[center - k] and h[center] > h[center + k]):
                    is_high = False
                if not is_low and not is_high:
                    break
            if is_low:
                lows.append(Swing(center, l[center]))
            if is_high:
                highs.append(Swing(center, h[center]))

        best_buy = None
        for swing in lows:
            if swing.dead:
                continue
            if i - swing.bar > SWING_MAX_AGE:
                swing.dead = True
                continue
            if l[i] < swing.level:
                if c[i] > swing.level and (best_buy is None or swing.level > best_buy):
                    best_buy = swing.level
                swing.dead = True
        if best_buy is not None:
            events.append(Event(i, 1, best_buy))

        best_sell = None
        for swing in highs:
            if swing.dead:
                continue
            if i - swing.bar > SWING_MAX_AGE:
                swing.dead = True
                continue
            if h[i] > swing.level:
                if c[i] < swing.level and (best_sell is None or swing.level < best_sell):
                    best_sell = swing.level
                swing.dead = True
        if best_sell is not None:
            events.append(Event(i, -1, best_sell))

        selected = None
        for event in events:
            if event.done:
                continue
            age = i - event.bar
            if age < 0:
                continue
            if age > PATTERN_WINDOW:
                event.done = True
                continue
            direction = event.direction
            if not is_belt_hold(o[i], h[i], l[i], c[i], direction):
                continue
            if direction == 1 and c[i] <= event.level:
                continue
            if direction == -1 and c[i] >= event.level:
                continue
            if direction == 1 and c[i] >= ema[i]:
                continue
            if direction == -1 and c[i] <= ema[i]:
                continue
            event.done = True
            if selected is None:
                selected = event

        if selected is not None:
            output.append(
                {
                    "signal_idx": i,
                    "signal_time": pd.Timestamp(times[i]),
                    "dir_num": selected.direction,
                    "dir": "BUY" if selected.direction == 1 else "SELL",
                    "sweep_idx": selected.bar,
                    "sweep_time": pd.Timestamp(times[selected.bar]),
                    "sweep_level": selected.level,
                }
            )

    result = pd.DataFrame(output)
    if result.empty:
        return result
    result["entry_idx"] = result["signal_idx"] + 1
    result = result[result["entry_idx"] < len(data)].copy()
    result["entry_time"] = data.loc[result["entry_idx"], "dt"].to_numpy()
    return result


def execute_m15(signals: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    o = data["open"].to_numpy(float)
    h = data["high"].to_numpy(float)
    l = data["low"].to_numpy(float)
    c = data["close"].to_numpy(float)
    atr = data["atr14"].to_numpy(float)
    times = data["dt"].to_numpy()
    n = len(data)

    rows = []
    for signal in signals.itertuples(index=False):
        si = int(signal.signal_idx)
        ei = int(signal.entry_idx)
        swi = int(signal.sweep_idx)
        direction = int(signal.dir_num)

        if not np.isfinite(atr[si]) or atr[si] <= 0:
            raise RuntimeError(f"Invalid ATR at {signal.signal_time}")

        entry = o[ei]
        extremum = np.min(l[swi : si + 1]) if direction == 1 else np.max(h[swi : si + 1])
        sl = extremum - SL_BUFFER_ATR * atr[si] if direction == 1 else extremum + SL_BUFFER_ATR * atr[si]
        risk = abs(entry - sl)
        if risk <= 0:
            raise RuntimeError(f"Invalid risk at {signal.signal_time}")
        tp = entry + TAKE_PROFIT_R * risk if direction == 1 else entry - TAKE_PROFIT_R * risk

        reason = None
        exit_idx = None
        exit_price = None
        r_raw = None

        timeout_idx = ei + TIME_STOP_BARS - 1
        scan_end = min(timeout_idx, n - 1)
        for j in range(ei, scan_end + 1):
            if direction == 1:
                hit_sl = l[j] <= sl
                hit_tp = h[j] >= tp
            else:
                hit_sl = h[j] >= sl
                hit_tp = l[j] <= tp

            if hit_sl:
                reason, exit_idx, exit_price, r_raw = "SL", j, sl, -1.0
                break
            if hit_tp:
                reason, exit_idx, exit_price, r_raw = "TP", j, tp, TAKE_PROFIT_R
                break

        if reason is None:
            if timeout_idx >= n:
                reason, exit_idx, exit_price, r_raw = "UNRESOLVED", n - 1, c[-1], np.nan
            else:
                reason, exit_idx, exit_price = "TIMESTOP", timeout_idx, c[timeout_idx]
                r_raw = (exit_price - entry) / risk if direction == 1 else (entry - exit_price) / risk

        rows.append(
            {
                "signal_time": signal.signal_time,
                "dir": signal.dir,
                "entry_time": pd.Timestamp(times[ei]),
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "exit_time": pd.Timestamp(times[exit_idx]),
                "exit_reason": reason,
                "R_raw": r_raw,
                "R_net": r_raw - COST_R if np.isfinite(r_raw) else np.nan,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m15", required=True, type=Path)
    parser.add_argument("--from-date", default="2026-05-01")
    parser.add_argument("--to-date", default="2026-07-23 23:59:59")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    data = load_mt5_m15(args.m15)
    signals = generate_signals(data)
    start = pd.Timestamp(args.from_date)
    end = pd.Timestamp(args.to_date)
    selected = signals[(signals["entry_time"] >= start) & (signals["entry_time"] <= end)].copy()
    trades = execute_m15(selected, data)

    trades.to_csv(args.out_dir / "BH_OOS_002_oos_trades.csv", index=False, float_format="%.6f")

    work = trades.copy()
    work["month"] = work["entry_time"].dt.strftime("%Y-%m")
    monthly = work.groupby("month").agg(
        N=("R_net", "size"),
        EV_raw=("R_raw", "mean"),
        EV_net=("R_net", "mean"),
        sumR_raw=("R_raw", "sum"),
        sumR_net=("R_net", "sum"),
    ).reset_index()
    monthly.to_csv(args.out_dir / "BH_OOS_002_monthly.csv", index=False, float_format="%.6f")

    summary = {
        "input": str(args.m15),
        "sha256": sha256_file(args.m15),
        "window": f"{start}..{end}",
        "N": int(len(trades)),
        "BUY": int((trades["dir"] == "BUY").sum()),
        "SELL": int((trades["dir"] == "SELL").sum()),
        "EV_raw": float(trades["R_raw"].mean()),
        "EV_net": float(trades["R_net"].mean()),
        "sumR_net": float(trades["R_net"].sum()),
        "unresolved": int((trades["exit_reason"] == "UNRESOLVED").sum()),
    }
    summary["verdict"] = "INCONCLUSIVE" if summary["N"] < 8 else ("PASS" if summary["EV_net"] >= 0 else "FAIL")
    (args.out_dir / "BH_OOS_002_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
