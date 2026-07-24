#!/usr/bin/env python3
"""Frozen TB flag generator for FXArena Flag-Replay v001.2.

The formulas are copied from TB/TrendBirth v002:
  EFFICIENCY_5 OR BB_EXPANSION OR RANGE_EXPANSION_15.

The exact archived implementation convention required for 3535/3535 parity is:
  * M5 resample: label='right', closed='left'
  * Bollinger population std: ddof=0
  * snapshot: decision_3bar_time + 35 minutes

The +35 label is the completed M5 bar representing the frozen 30-minute
observation window under the archived resample convention. No thresholds are
fit or tuned in this module.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def build_m5_features(m1: pd.DataFrame) -> pd.DataFrame:
    """Build the three frozen TB-v002 M5 feature families."""
    x = m1.set_index("dt").sort_index()
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "tickvol": "sum",
        "spread": "mean",
    }
    m5 = x.resample("5min", label="right", closed="left").agg(agg).dropna()
    f = pd.DataFrame(index=m5.index)
    f["m5_open"] = m5.open
    f["m5_high"] = m5.high
    f["m5_low"] = m5.low
    f["m5_close"] = m5.close
    f["m5_range"] = m5.high - m5.low
    f["m5_body"] = m5.close - m5.open
    f["m5_range_ma20"] = f.m5_range.rolling(20).mean()
    f["m5_close5"] = m5.close.shift(5)
    f["m5_path5"] = m5.close.diff().abs().rolling(5).sum()
    f["m5_bbmid"] = m5.close.rolling(20).mean()
    sd = m5.close.rolling(20).std(ddof=0)
    f["m5_bbup"] = f.m5_bbmid + 2.0 * sd
    f["m5_bblo"] = f.m5_bbmid - 2.0 * sd
    return f


def generate_episode_tb_flags(episodes: pd.DataFrame, m5_features: pd.DataFrame) -> pd.DataFrame:
    """Generate frozen per-episode TB flags without outcome information."""
    required = {"episode_id", "decision_3bar_time_unix", "dir"}
    missing = required - set(episodes.columns)
    if missing:
        raise ValueError(f"missing episode columns: {sorted(missing)}")

    left = episodes[["episode_id", "decision_3bar_time_unix", "dir"]].copy()
    left["_row"] = np.arange(len(left), dtype=np.int64)
    left["observation_time"] = (
        pd.to_datetime(left.decision_3bar_time_unix, unit="s", utc=True)
        + pd.Timedelta(minutes=35)
    )
    right = m5_features.reset_index().rename(columns={"dt": "feature_time", "time": "feature_time"})
    if "feature_time" not in right.columns:
        right = right.rename(columns={right.columns[0]: "feature_time"})

    a = pd.merge_asof(
        left.sort_values("observation_time"),
        right.sort_values("feature_time"),
        left_on="observation_time",
        right_on="feature_time",
        direction="backward",
    ).sort_values("_row", kind="mergesort")

    d = a.dir.to_numpy(np.int8)
    efficiency_5 = (
        (np.abs(a.m5_close - a.m5_close5) > 0.6 * a.m5_path5)
        & (d * (a.m5_close - a.m5_close5) > 0)
    )
    bb_expansion = np.where(
        d > 0,
        a.m5_close > a.m5_bbup,
        a.m5_close < a.m5_bblo,
    )
    range_expansion_15 = (
        (a.m5_range > 1.5 * a.m5_range_ma20)
        & (d * a.m5_body > 0)
    )

    out = episodes[["episode_id", "decision_3bar_time_unix", "entry_t", "dir"]].copy()
    out["observation_time_unix"] = (a.observation_time.astype("int64") // 10**9).to_numpy(np.int64)
    out["feature_time_unix"] = (a.feature_time.astype("int64") // 10**9).to_numpy(np.int64)
    out["EFFICIENCY_5"] = pd.Series(efficiency_5).fillna(False).to_numpy(bool)
    out["BB_EXPANSION"] = pd.Series(bb_expansion).fillna(False).to_numpy(bool)
    out["RANGE_EXPANSION_15"] = pd.Series(range_expansion_15).fillna(False).to_numpy(bool)
    out["tb_flag"] = (
        out.EFFICIENCY_5 | out.BB_EXPANSION | out.RANGE_EXPANSION_15
    )
    if out[["feature_time_unix"]].isna().any().any():
        raise RuntimeError("missing M5 feature snapshot")
    return out
