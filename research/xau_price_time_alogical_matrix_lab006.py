#!/usr/bin/env python3
"""XAU_PRICE_TIME_ALOGICAL_MATRIX_LAB006

Purpose
-------
Test a price+time contrarian hypothesis without indicators or discretionary
pattern names: when the recent tape makes one direction unusually obvious, but
price fails to reward that direction within a reasonable amount of time, does
trading the opposite side have positive conditional expectancy?

Data
----
Consumes causal M1 Bid/Ask bars + multi-barrier labels produced by
XAU_CAUSAL_FUTURE_PROBABILITY_LAB001.

Causality
---------
All state variables at observation minute t use completed bars t-1 or earlier.
Execution/labels start at the first valid tick of minute t.

Frozen target
-------------
SL = 1.25 ATR14, TP = 2R, horizon = 240 minutes.

Research protocol
-----------------
* 2023-2024: discovery only.
* 2025: validation gate.
* 2026: untouched final OOS.
* Matrix thresholds are fixed ex-ante in this file, not optimized by outcome.
* A 240-minute cooldown is used for independent trade-like samples.

"Crowd" here is explicitly a PRICE-ONLY PROXY for what a conventional chart
trader would likely infer (breakout/extension/location/persistence). It is not
actual broker positioning or order-book sentiment.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd

try:
    from numba import njit
except Exception:  # pragma: no cover
    njit = None

SL_ATR = 1.25
RR = 2.0
H = 240
COMMISSION_RATE_SIDE = 0.000007
BUY_LABEL = "BUY_S1.25_R2_H240"
SELL_LABEL = "SELL_S1.25_R2_H240"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--bars", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--outdir", type=Path, required=True)
    return p.parse_args()


def _age_extreme_py(x: np.ndarray, lookback: int, want_high: bool) -> np.ndarray:
    n = len(x)
    out = np.full(n, -1, np.int16)
    for i in range(n):
        start = i - lookback + 1
        if start < 0:
            continue
        best = start
        bestv = x[start]
        for j in range(start + 1, i + 1):
            v = x[j]
            if (want_high and v >= bestv) or ((not want_high) and v <= bestv):
                best, bestv = j, v
        out[i] = i - best
    return out


if njit is not None:
    @njit(cache=True)
    def _age_extreme_nb(x, lookback, want_high):
        n = len(x)
        out = np.full(n, -1, np.int16)
        for i in range(n):
            start = i - lookback + 1
            if start < 0:
                continue
            best = start
            bestv = x[start]
            for j in range(start + 1, i + 1):
                v = x[j]
                if (want_high and v >= bestv) or ((not want_high) and v <= bestv):
                    best = j
                    bestv = v
            out[i] = i - best
        return out

    @njit(cache=True)
    def _global_cooldown_nb(minutes, mask, cooldown):
        keep = np.zeros(len(minutes), np.bool_)
        last = -10**18
        for i in range(len(minutes)):
            if mask[i] and minutes[i] - last >= cooldown:
                keep[i] = True
                last = minutes[i]
        return keep
else:
    _age_extreme_nb = None
    _global_cooldown_nb = None


def age_extreme(x: np.ndarray, lookback: int, want_high: bool) -> np.ndarray:
    if _age_extreme_nb is not None:
        return _age_extreme_nb(x.astype(np.float64), lookback, want_high)
    return _age_extreme_py(x, lookback, want_high)


def global_cooldown(minutes: np.ndarray, mask: np.ndarray, cooldown: int = H) -> np.ndarray:
    if _global_cooldown_nb is not None:
        return _global_cooldown_nb(minutes.astype(np.int64), mask.astype(np.bool_), cooldown)
    keep = np.zeros(len(minutes), bool)
    last = -10**18
    for i in range(len(minutes)):
        if mask[i] and int(minutes[i]) - last >= cooldown:
            keep[i] = True
            last = int(minutes[i])
    return keep


def commission_r(df: pd.DataFrame, side: str) -> np.ndarray:
    entry_col = "first_ask" if side == "BUY" else "first_bid"
    e = df[entry_col].to_numpy(float)
    a = df["atr14_causal"].to_numpy(float)
    return np.divide(
        2.0 * COMMISSION_RATE_SIDE * e,
        SL_ATR * a,
        out=np.full(len(df), np.nan),
        where=np.isfinite(a) & (a > 0),
    )


def actual_r(df: pd.DataFrame, side: str) -> np.ndarray:
    col = BUY_LABEL if side == "BUY" else SELL_LABEL
    lab = df[col].to_numpy()
    c = commission_r(df, side)
    r = np.full(len(df), np.nan)
    r[lab == 1] = RR - c[lab == 1]
    r[lab == -1] = -1.0 - c[lab == -1]
    r[lab == 0] = -c[lab == 0]
    return r


def add_states(df: pd.DataFrame) -> pd.DataFrame:
    x = df.sort_values("minute").reset_index(drop=True).copy()

    # Everything below is known before minute t begins.
    pc = x["mid_close"].shift(1).astype(float)
    ph = x["mid_high"].shift(1).astype(float)
    pl = x["mid_low"].shift(1).astype(float)
    po = x["mid_open"].shift(1).astype(float)
    atr = x["atr14_causal"].astype(float)

    # Prior range excludes the latest completed bar so a breakout is causal.
    hi60_prior = x["mid_high"].shift(2).rolling(60, min_periods=60).max()
    lo60_prior = x["mid_low"].shift(2).rolling(60, min_periods=60).min()
    width60 = (hi60_prior - lo60_prior).replace(0, np.nan)
    loc60 = (pc - lo60_prior) / width60

    ret15 = (pc - pc.shift(15)) / atr
    ret60 = (pc - pc.shift(60)) / atr
    body = pc - po
    body_sign = np.sign(body.fillna(0.0))
    up5 = (body_sign > 0).astype(int).rolling(5, min_periods=5).sum()
    dn5 = (body_sign < 0).astype(int).rolling(5, min_periods=5).sum()

    score = np.zeros(len(x), np.int8)
    score += (pc > hi60_prior).fillna(False).to_numpy(np.int8)
    score -= (pc < lo60_prior).fillna(False).to_numpy(np.int8)
    score += (loc60 >= 0.85).fillna(False).to_numpy(np.int8)
    score -= (loc60 <= 0.15).fillna(False).to_numpy(np.int8)
    score += (ret15 >= 1.00).fillna(False).to_numpy(np.int8)
    score -= (ret15 <= -1.00).fillna(False).to_numpy(np.int8)
    score += (ret60 >= 1.80).fillna(False).to_numpy(np.int8)
    score -= (ret60 <= -1.80).fillna(False).to_numpy(np.int8)
    score += (up5 >= 4).fillna(False).to_numpy(np.int8)
    score -= (dn5 >= 4).fillna(False).to_numpy(np.int8)

    crowd_dir = np.sign(score).astype(np.int8)
    abs_score = np.abs(score)

    # Age of the most recent completed 20-bar extreme. 0 = just printed on t-1.
    high_age20 = age_extreme(ph.to_numpy(float), 20, True)
    low_age20 = age_extreme(pl.to_numpy(float), 20, False)
    extreme_age = np.where(crowd_dir > 0, high_age20, np.where(crowd_dir < 0, low_age20, -1))

    # Has the obvious direction made progress during the last five completed bars?
    dir_progress5 = crowd_dir.astype(float) * ((pc - pc.shift(5)) / atr).to_numpy(float)

    # Path efficiency: low values mean much movement but little net progress.
    abs_step = pc.diff().abs()
    path5 = abs_step.rolling(5, min_periods=5).sum()
    eff5 = ((pc - pc.shift(5)).abs() / path5.replace(0, np.nan)).to_numpy(float)

    score_bucket = np.full(len(x), "LT2", object)
    score_bucket[abs_score == 2] = "S2"
    score_bucket[abs_score == 3] = "S3"
    score_bucket[abs_score >= 4] = "S4P"

    age_bucket = np.full(len(x), "NA", object)
    age_bucket[(extreme_age >= 0) & (extreme_age <= 2)] = "A0_2"
    age_bucket[(extreme_age >= 3) & (extreme_age <= 5)] = "A3_5"
    age_bucket[(extreme_age >= 6) & (extreme_age <= 10)] = "A6_10"
    age_bucket[(extreme_age >= 11) & (extreme_age <= 19)] = "A11_19"

    progress_bucket = np.full(len(x), "NA", object)
    progress_bucket[np.isfinite(dir_progress5) & (dir_progress5 >= 0.35)] = "CONTINUE"
    progress_bucket[np.isfinite(dir_progress5) & (dir_progress5 >= -0.10) & (dir_progress5 < 0.35)] = "STALL"
    progress_bucket[np.isfinite(dir_progress5) & (dir_progress5 < -0.10)] = "REJECT"

    ts = pd.to_datetime(x["timestamp_from_time_msc"], errors="coerce")
    hour = ts.dt.hour.to_numpy()
    session = np.where(hour <= 6, "ASIA", np.where(hour <= 12, "EUROPE", np.where(hour <= 17, "US", "LATE")))

    x["crowd_score"] = score
    x["crowd_dir"] = crowd_dir
    x["abs_crowd_score"] = abs_score
    x["score_bucket"] = score_bucket
    x["extreme_age20"] = extreme_age
    x["age_bucket"] = age_bucket
    x["dir_progress5_atr"] = dir_progress5
    x["eff5"] = eff5
    x["progress_bucket"] = progress_bucket
    x["session"] = session
    x["year"] = ts.dt.year.astype("Int64")
    x["r_buy"] = actual_r(x, "BUY")
    x["r_sell"] = actual_r(x, "SELL")
    x["r_obvious"] = np.where(crowd_dir > 0, x["r_buy"], np.where(crowd_dir < 0, x["r_sell"], np.nan))
    x["r_inverse"] = np.where(crowd_dir > 0, x["r_sell"], np.where(crowd_dir < 0, x["r_buy"], np.nan))
    return x


def pf(r: np.ndarray) -> float | None:
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return None
    gp = float(r[r > 0].sum())
    gl = float(-r[r < 0].sum())
    return gp / gl if gl > 0 else None


def summary(r: np.ndarray) -> Dict[str, float | int | None]:
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n == 0:
        return {"n": 0, "mean_R": None, "pf": None, "win_rate": None, "max_dd_R": None}
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return {
        "n": int(n),
        "mean_R": float(np.mean(r)),
        "pf": pf(r),
        "win_rate": float(np.mean(r > 0)),
        "max_dd_R": float(np.max(dd)) if len(dd) else 0.0,
    }


def fixed_eligible(x: pd.DataFrame) -> pd.Series:
    # This is the alogical zone: obvious enough to attract consensus, but no
    # longer receiving clean directional reward from time/progress.
    return (
        x["score_bucket"].isin(["S2", "S3", "S4P"])
        & x["age_bucket"].isin(["A3_5", "A6_10", "A11_19"])
        & x["progress_bucket"].isin(["STALL", "REJECT"])
        & (x["crowd_dir"] != 0)
        & np.isfinite(x["r_obvious"])
        & np.isfinite(x["r_inverse"])
    )


def independent_mask_for_cell(g: pd.DataFrame) -> np.ndarray:
    mins = g["minute"].to_numpy(np.int64)
    return global_cooldown(mins, np.ones(len(g), bool), H)


def build_matrix(x: pd.DataFrame, include_session: bool = False) -> pd.DataFrame:
    d = x.loc[fixed_eligible(x)].copy()
    keys = ["crowd_dir", "score_bucket", "age_bucket", "progress_bucket"]
    if include_session:
        keys.append("session")
    rows = []
    for kvals, g in d.groupby(keys, sort=True, observed=True):
        if not isinstance(kvals, tuple):
            kvals = (kvals,)
        base = dict(zip(keys, kvals))
        g = g.sort_values("minute")
        keep = independent_mask_for_cell(g)
        gi = g.loc[keep]
        for sample_name, z in (("RAW", g), ("INDEPENDENT_240M", gi)):
            ro = z["r_obvious"].to_numpy(float)
            ri = z["r_inverse"].to_numpy(float)
            so, si = summary(ro), summary(ri)
            row = {
                **base,
                "sample": sample_name,
                "n": si["n"],
                "obvious_mean_R": so["mean_R"],
                "obvious_pf": so["pf"],
                "inverse_mean_R": si["mean_R"],
                "inverse_pf": si["pf"],
                "inversion_gap_R": (si["mean_R"] - so["mean_R"]) if si["mean_R"] is not None and so["mean_R"] is not None else None,
            }
            rows.append(row)
    return pd.DataFrame(rows)


def cell_id_frame(df: pd.DataFrame) -> pd.Series:
    return (
        df["crowd_dir"].astype(int).astype(str) + "|" +
        df["score_bucket"].astype(str) + "|" +
        df["age_bucket"].astype(str) + "|" +
        df["progress_bucket"].astype(str)
    )


def independent_cell_year(x: pd.DataFrame) -> pd.DataFrame:
    d = x.loc[fixed_eligible(x)].copy()
    d["cell_id"] = cell_id_frame(d)
    rows = []
    for (cid, yr), g in d.groupby(["cell_id", "year"], sort=True, observed=True):
        g = g.sort_values("minute")
        keep = independent_mask_for_cell(g)
        z = g.loc[keep]
        so = summary(z["r_obvious"].to_numpy(float))
        si = summary(z["r_inverse"].to_numpy(float))
        rows.append({
            "cell_id": cid,
            "year": int(yr),
            "n": si["n"],
            "obvious_mean_R": so["mean_R"],
            "inverse_mean_R": si["mean_R"],
            "inverse_pf": si["pf"],
            "inversion_gap_R": (si["mean_R"] - so["mean_R"]) if si["mean_R"] is not None and so["mean_R"] is not None else None,
        })
    return pd.DataFrame(rows)


def discover_candidates(yearly: pd.DataFrame) -> Tuple[pd.DataFrame, set[str]]:
    rows = []
    for cid, g in yearly.groupby("cell_id", observed=True):
        tr = g[g["year"].isin([2023, 2024])]
        va = g[g["year"] == 2025]
        oo = g[g["year"] == 2026]
        tr_n = int(tr["n"].sum())
        if tr_n:
            tr_inv = float(np.average(tr["inverse_mean_R"], weights=tr["n"]))
            tr_gap = float(np.average(tr["inversion_gap_R"], weights=tr["n"]))
        else:
            tr_inv = tr_gap = np.nan
        va_n = int(va["n"].sum())
        va_inv = float(np.average(va["inverse_mean_R"], weights=va["n"])) if va_n else np.nan
        va_gap = float(np.average(va["inversion_gap_R"], weights=va["n"])) if va_n else np.nan
        oo_n = int(oo["n"].sum())
        oo_inv = float(np.average(oo["inverse_mean_R"], weights=oo["n"])) if oo_n else np.nan
        oo_gap = float(np.average(oo["inversion_gap_R"], weights=oo["n"])) if oo_n else np.nan

        discovery_pass = tr_n >= 30 and tr_inv > 0.05 and tr_gap > 0.15
        validation_pass = va_n >= 8 and va_inv > 0.0 and va_gap > 0.0
        locked = discovery_pass and validation_pass
        final_oos_pass = oo_n >= 8 and oo_inv > 0.0 and oo_gap > 0.0
        rows.append({
            "cell_id": cid,
            "train_2023_2024_n": tr_n,
            "train_inverse_mean_R": tr_inv,
            "train_inversion_gap_R": tr_gap,
            "validation_2025_n": va_n,
            "validation_inverse_mean_R": va_inv,
            "validation_inversion_gap_R": va_gap,
            "discovery_pass": discovery_pass,
            "validation_pass": validation_pass,
            "locked_before_2026": locked,
            "final_2026_n": oo_n,
            "final_2026_inverse_mean_R": oo_inv,
            "final_2026_inversion_gap_R": oo_gap,
            "final_2026_pass": final_oos_pass if locked else False,
        })
    out = pd.DataFrame(rows).sort_values(
        ["locked_before_2026", "validation_inverse_mean_R", "train_inverse_mean_R"],
        ascending=[False, False, False],
        na_position="last",
    )
    locked = set(out.loc[out["locked_before_2026"], "cell_id"].astype(str))
    return out, locked


def strategy_stream(x: pd.DataFrame, locked: set[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    d = x.loc[fixed_eligible(x)].copy()
    d["cell_id"] = cell_id_frame(d)
    d = d[d["cell_id"].isin(locked)].sort_values("minute").copy()
    if d.empty:
        return d, pd.DataFrame()
    keep = global_cooldown(d["minute"].to_numpy(np.int64), np.ones(len(d), bool), H)
    z = d.loc[keep].copy()
    z["trade_side"] = np.where(z["crowd_dir"] > 0, "SELL", "BUY")
    z["trade_R"] = z["r_inverse"]
    rows = []
    for yr, g in z.groupby("year", observed=True):
        s = summary(g["trade_R"].to_numpy(float))
        rows.append({"year": int(yr), **s})
    return z, pd.DataFrame(rows)


def main() -> None:
    a = parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    bars = pd.read_parquet(a.bars)
    labels = pd.read_parquet(a.labels)

    need_b = {"minute", "first_bid", "first_ask", "mid_open", "mid_high", "mid_low", "mid_close", "atr14_causal", "timestamp_from_time_msc"}
    need_l = {"minute", BUY_LABEL, SELL_LABEL}
    mb = need_b.difference(bars.columns)
    ml = need_l.difference(labels.columns)
    if mb or ml:
        raise RuntimeError(f"Missing columns bars={sorted(mb)} labels={sorted(ml)}")

    x = bars[list(need_b)].merge(labels[list(need_l)], on="minute", how="inner", validate="one_to_one")
    x = add_states(x)

    matrix = build_matrix(x, include_session=False)
    matrix_session = build_matrix(x, include_session=True)
    yearly = independent_cell_year(x)
    candidates, locked = discover_candidates(yearly)
    trades, strategy_yearly = strategy_stream(x, locked)

    matrix.to_csv(a.outdir / "alogical_matrix.csv", index=False)
    matrix_session.to_csv(a.outdir / "alogical_matrix_by_session.csv", index=False)
    yearly.to_csv(a.outdir / "cell_yearly_transfer.csv", index=False)
    candidates.to_csv(a.outdir / "candidate_transfer.csv", index=False)
    strategy_yearly.to_csv(a.outdir / "locked_strategy_yearly.csv", index=False)
    if not trades.empty:
        trades[["minute", "timestamp_from_time_msc", "year", "cell_id", "crowd_score", "crowd_dir", "score_bucket", "age_bucket", "progress_bucket", "trade_side", "trade_R"]].to_csv(a.outdir / "locked_trades.csv", index=False)

    ind = matrix[matrix["sample"] == "INDEPENDENT_240M"].copy()
    if not ind.empty:
        ind = ind.sort_values(["inversion_gap_R", "inverse_mean_R", "n"], ascending=[False, False, False])
        ind.head(30).to_csv(a.outdir / "top_inversion_cells.csv", index=False)

    final_2026 = strategy_yearly[strategy_yearly["year"] == 2026] if not strategy_yearly.empty else pd.DataFrame()
    final = final_2026.iloc[0].to_dict() if len(final_2026) else {}
    locked_rows = candidates[candidates["locked_before_2026"]] if not candidates.empty else pd.DataFrame()
    passed_final = locked_rows[locked_rows["final_2026_pass"]] if not locked_rows.empty else pd.DataFrame()

    verdict = {
        "lab": "XAU_PRICE_TIME_ALOGICAL_MATRIX_LAB006",
        "hypothesis": "obvious price direction + time/progress failure can create a contrarian edge",
        "crowd_proxy_warning": "price-only proxy, not actual positioning",
        "target": {"sl_atr": SL_ATR, "rr": RR, "horizon_minutes": H},
        "matrix_definition": {
            "crowd_score_components": ["60m breakout", "60m range location", "15m displacement", "60m displacement", "4-of-5 candle persistence"],
            "alogical_zone": "abs crowd score >=2 AND extreme age >=3 bars AND progress=STALL/REJECT",
            "primary_metric": "inverse_mean_R - obvious_mean_R",
        },
        "protocol": "2023-2024 discovery; 2025 validation gate; 2026 untouched final OOS; 240m cooldown",
        "independent_matrix_cells": int(len(ind)),
        "locked_cells_before_2026": int(len(locked_rows)),
        "locked_cells_positive_in_2026": int(len(passed_final)),
        "final_2026_strategy": final,
        "verdict": (
            "PASS" if final and final.get("n", 0) >= 20 and (final.get("mean_R") or -999) > 0.05 and (final.get("pf") or 0) > 1.10
            else "WEAK_PASS" if final and final.get("n", 0) >= 10 and (final.get("mean_R") or -999) > 0
            else "FAIL"
        ),
    }
    (a.outdir / "verdict.json").write_text(json.dumps(verdict, indent=2, default=str), encoding="utf-8")

    print(json.dumps(verdict, indent=2, default=str))
    print("\nTOP INVERSION CELLS")
    if not ind.empty:
        print(ind.head(15).to_string(index=False))
    print("\nCANDIDATE TRANSFER")
    if not candidates.empty:
        print(candidates.head(20).to_string(index=False))
    print("\nLOCKED STRATEGY YEARLY")
    if not strategy_yearly.empty:
        print(strategy_yearly.to_string(index=False))


if __name__ == "__main__":
    main()
