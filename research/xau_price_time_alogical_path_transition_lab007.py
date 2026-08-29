#!/usr/bin/env python3
"""XAU_PRICE_TIME_ALOGICAL_PATH_TRANSITION_LAB_007

Research question
-----------------
When price creates an unusually obvious directional setup, does the *transition*
from logical behaviour to illogical behaviour create a tradable inverse edge?

This is deliberately price + time only. No indicators/pattern labels are used in
signal formation. ATR is only a causal scale normalizer and for the frozen risk
barrier inherited from LAB001.

Causality
---------
At event minute t0, obviousness uses completed bars t0-1 or earlier.
We then deliberately wait W completed minutes and classify the observed path.
A DIRECT entry executes at the first tick of minute t0+W.
A RETEST entry waits for a completed retest-touch bar and executes at the first
tick of the next minute. Outcome labels are looked up at that *later entry minute*.
No future label participates in event, transition, retest, or entry selection.

Frozen target
-------------
SL = 1.25 ATR14, TP = 2R, horizon = 240 minutes, Bid/Ask-aware LAB001 labels.

Chronology
----------
2023-2024 discovery -> 2025 validation -> 2026 untouched final OOS.
Matrix thresholds are fixed ex-ante below. 240m cooldown is applied per cell and
again globally to the locked portfolio.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

SL_ATR = 1.25
RR = 2.0
H = 240
COMMISSION_RATE_SIDE = 0.000007
BUY_LABEL = "BUY_S1.25_R2_H240"
SELL_LABEL = "SELL_S1.25_R2_H240"
WAIT_WINDOWS = (5, 10, 20, 40)
RETEST_WINDOWS = (10, 20)
RETEST_ZONE_ATR = 0.10


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--bars", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--outdir", type=Path, required=True)
    return p.parse_args()


def pf(r: np.ndarray) -> Optional[float]:
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    if not len(r):
        return None
    gp = float(r[r > 0].sum())
    gl = float(-r[r < 0].sum())
    return gp / gl if gl > 0 else None


def stats(r: np.ndarray) -> Dict[str, float | int | None]:
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n == 0:
        return {"n": 0, "mean_R": None, "pf": None, "win_rate": None, "max_dd_R": None, "sum_R": 0.0}
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return {
        "n": int(n),
        "mean_R": float(np.mean(r)),
        "pf": pf(r),
        "win_rate": float(np.mean(r > 0)),
        "max_dd_R": float(np.max(dd)) if len(dd) else 0.0,
        "sum_R": float(np.sum(r)),
    }


def commission_r(entry: float, atr: float) -> float:
    if not np.isfinite(entry) or not np.isfinite(atr) or atr <= 0:
        return np.nan
    return 2.0 * COMMISSION_RATE_SIDE * entry / (SL_ATR * atr)


def label_to_r(label: float, commission: float) -> float:
    if not np.isfinite(label) or not np.isfinite(commission):
        return np.nan
    if label == 1:
        return RR - commission
    if label == -1:
        return -1.0 - commission
    if label == 0:
        return -commission
    return np.nan


def load_data(bars_path: Path, labels_path: Path) -> pd.DataFrame:
    bars = pd.read_parquet(bars_path)
    labels = pd.read_parquet(labels_path)
    need_b = [
        "minute", "timestamp_from_time_msc", "first_bid", "first_ask",
        "mid_open", "mid_high", "mid_low", "mid_close",
    ]
    need_l = ["minute", "atr14_causal", BUY_LABEL, SELL_LABEL]
    miss_b = [c for c in need_b if c not in bars.columns]
    miss_l = [c for c in need_l if c not in labels.columns]
    if miss_b or miss_l:
        raise RuntimeError(f"schema mismatch bars={miss_b} labels={miss_l}")
    x = bars[need_b].merge(labels[need_l], on="minute", how="inner", validate="one_to_one")
    x = x.sort_values("minute").reset_index(drop=True)
    ts = pd.to_datetime(x["timestamp_from_time_msc"], errors="coerce")
    x["year"] = ts.dt.year.astype("Int64")
    return x


def add_obviousness(x: pd.DataFrame) -> pd.DataFrame:
    d = x.copy()
    pc = d["mid_close"].shift(1).astype(float)
    po = d["mid_open"].shift(1).astype(float)
    atr = d["atr14_causal"].astype(float)

    hi60 = d["mid_high"].shift(2).rolling(60, min_periods=60).max()
    lo60 = d["mid_low"].shift(2).rolling(60, min_periods=60).min()
    width60 = (hi60 - lo60).replace(0, np.nan)
    loc60 = (pc - lo60) / width60
    ret15 = (pc - pc.shift(15)) / atr
    ret60 = (pc - pc.shift(60)) / atr
    body_sign = np.sign((pc - po).fillna(0.0))
    up5 = (body_sign > 0).astype(int).rolling(5, min_periods=5).sum()
    dn5 = (body_sign < 0).astype(int).rolling(5, min_periods=5).sum()

    score = np.zeros(len(d), np.int8)
    score += (pc > hi60).fillna(False).to_numpy(np.int8)
    score -= (pc < lo60).fillna(False).to_numpy(np.int8)
    score += (loc60 >= 0.85).fillna(False).to_numpy(np.int8)
    score -= (loc60 <= 0.15).fillna(False).to_numpy(np.int8)
    score += (ret15 >= 1.00).fillna(False).to_numpy(np.int8)
    score -= (ret15 <= -1.00).fillna(False).to_numpy(np.int8)
    score += (ret60 >= 1.80).fillna(False).to_numpy(np.int8)
    score -= (ret60 <= -1.80).fillna(False).to_numpy(np.int8)
    score += (up5 >= 4).fillna(False).to_numpy(np.int8)
    score -= (dn5 >= 4).fillna(False).to_numpy(np.int8)

    d["crowd_score"] = score
    d["crowd_dir"] = np.sign(score).astype(np.int8)
    d["score_bucket"] = np.where(np.abs(score) >= 4, "S4P", np.where(np.abs(score) == 3, "S3", "LT3"))
    d["origin"] = pc
    return d


def transition_type(mfe: float, mae: float, endp: float) -> Optional[str]:
    if mfe < 0.50 and mae >= 0.40 and endp <= -0.20:
        return "NO_REWARD_REJECT"
    if mfe >= 0.50 and endp <= 0.00 and (mfe - endp) >= 0.60:
        return "FAKE_CONFIRM_RETURN"
    if mfe >= 0.80 and endp <= 0.20 and (mfe - endp) >= 0.80:
        return "OVEREXTEND_SNAPBACK"
    return None


def find_retest_entry(x: pd.DataFrame, start_idx: int, max_wait: int, crowd_dir: int, origin: float, atr: float) -> Optional[int]:
    end = min(len(x) - 2, start_idx + max_wait - 1)
    if end < start_idx:
        return None
    zone = RETEST_ZONE_ATR * atr
    for j in range(start_idx, end + 1):
        if crowd_dir > 0:
            touched = float(x.at[j, "mid_high"]) >= origin - zone
        else:
            touched = float(x.at[j, "mid_low"]) <= origin + zone
        if touched:
            return j + 1
    return None


def outcome_at(x: pd.DataFrame, entry_idx: int, side: str) -> tuple[float, float, float]:
    if entry_idx < 0 or entry_idx >= len(x):
        return np.nan, np.nan, np.nan
    label_col = BUY_LABEL if side == "BUY" else SELL_LABEL
    entry_col = "first_ask" if side == "BUY" else "first_bid"
    lab = float(x.at[entry_idx, label_col])
    entry = float(x.at[entry_idx, entry_col])
    atr = float(x.at[entry_idx, "atr14_causal"])
    c = commission_r(entry, atr)
    return label_to_r(lab, c), lab, c


def build_transitions(x: pd.DataFrame) -> pd.DataFrame:
    rows: List[dict] = []
    eligible = np.flatnonzero(
        (x["score_bucket"].isin(["S3", "S4P"]).to_numpy())
        & np.isfinite(x["origin"].to_numpy(float))
        & np.isfinite(x["atr14_causal"].to_numpy(float))
        & (x["atr14_causal"].to_numpy(float) > 0)
    )
    for i in eligible:
        crowd_dir = int(x.at[i, "crowd_dir"])
        if crowd_dir == 0:
            continue
        origin = float(x.at[i, "origin"])
        atr0 = float(x.at[i, "atr14_causal"])
        for w in WAIT_WINDOWS:
            end_idx = i + w - 1
            direct_idx = i + w
            if direct_idx >= len(x):
                continue
            ph = x.loc[i:end_idx, "mid_high"].to_numpy(float)
            pl = x.loc[i:end_idx, "mid_low"].to_numpy(float)
            if crowd_dir > 0:
                mfe = (float(np.max(ph)) - origin) / atr0
                mae = (origin - float(np.min(pl))) / atr0
            else:
                mfe = (origin - float(np.min(pl))) / atr0
                mae = (float(np.max(ph)) - origin) / atr0
            end_close = float(x.at[end_idx, "mid_close"])
            endp = crowd_dir * (end_close - origin) / atr0
            ttype = transition_type(mfe, mae, endp)
            if ttype is None:
                continue

            base = {
                "event_idx": int(i),
                "event_minute": int(x.at[i, "minute"]),
                "event_year": int(x.at[i, "year"]),
                "crowd_dir": crowd_dir,
                "score_bucket": str(x.at[i, "score_bucket"]),
                "wait_min": int(w),
                "transition": ttype,
                "origin": origin,
                "atr0": atr0,
                "mfe_atr": float(mfe),
                "mae_atr": float(mae),
                "end_progress_atr": float(endp),
                "giveback_atr": float(mfe - endp),
            }

            entry_modes = [("DIRECT", direct_idx)]
            for rw in RETEST_WINDOWS:
                ridx = find_retest_entry(x, direct_idx, rw, crowd_dir, origin, atr0)
                entry_modes.append((f"RETEST_{rw}", ridx))

            for mode, entry_idx in entry_modes:
                if entry_idx is None or entry_idx >= len(x):
                    continue
                inverse_side = "SELL" if crowd_dir > 0 else "BUY"
                obvious_side = "BUY" if crowd_dir > 0 else "SELL"
                rinv, linv, cinv = outcome_at(x, int(entry_idx), inverse_side)
                robv, lobv, cobv = outcome_at(x, int(entry_idx), obvious_side)
                if not np.isfinite(rinv) or not np.isfinite(robv):
                    continue
                row = dict(base)
                row.update({
                    "entry_mode": mode,
                    "entry_idx": int(entry_idx),
                    "entry_minute": int(x.at[int(entry_idx), "minute"]),
                    "entry_year": int(x.at[int(entry_idx), "year"]),
                    "inverse_side": inverse_side,
                    "r_inverse": float(rinv),
                    "r_obvious": float(robv),
                    "inverse_label": int(linv),
                    "obvious_label": int(lobv),
                    "inverse_commission_R": float(cinv),
                    "obvious_commission_R": float(cobv),
                })
                row["cell_id"] = f"D{crowd_dir}|{row['score_bucket']}|W{w}|{ttype}|{mode}"
                rows.append(row)
    return pd.DataFrame(rows)


def cooldown(df: pd.DataFrame, minutes: int = H, minute_col: str = "entry_minute") -> pd.DataFrame:
    if df.empty:
        return df.copy()
    z = df.sort_values(minute_col).copy()
    keep = []
    last = -10**18
    for idx, m in zip(z.index, z[minute_col].to_numpy(np.int64)):
        if int(m) - last >= minutes:
            keep.append(idx)
            last = int(m)
    return z.loc[keep].copy()


def summarize_cell_year(trans: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (cid, yr), g in trans.groupby(["cell_id", "entry_year"], sort=True, observed=True):
        z = cooldown(g)
        si = stats(z["r_inverse"].to_numpy(float))
        so = stats(z["r_obvious"].to_numpy(float))
        rows.append({
            "cell_id": cid, "year": int(yr), "n": si["n"],
            "inverse_mean_R": si["mean_R"], "inverse_pf": si["pf"], "inverse_sum_R": si["sum_R"],
            "obvious_mean_R": so["mean_R"], "obvious_pf": so["pf"],
            "inversion_gap_R": (si["mean_R"] - so["mean_R"]) if si["mean_R"] is not None and so["mean_R"] is not None else None,
        })
    return pd.DataFrame(rows)


def period_stats(trans: pd.DataFrame, years: set[int]) -> pd.DataFrame:
    rows = []
    d = trans[trans["entry_year"].isin(years)]
    for cid, g in d.groupby("cell_id", sort=True, observed=True):
        z = cooldown(g)
        si = stats(z["r_inverse"].to_numpy(float))
        so = stats(z["r_obvious"].to_numpy(float))
        first = z.iloc[0] if len(z) else g.iloc[0]
        rows.append({
            "cell_id": cid,
            "crowd_dir": int(first["crowd_dir"]),
            "score_bucket": str(first["score_bucket"]),
            "wait_min": int(first["wait_min"]),
            "transition": str(first["transition"]),
            "entry_mode": str(first["entry_mode"]),
            "n": si["n"], "inverse_mean_R": si["mean_R"], "inverse_pf": si["pf"], "inverse_sum_R": si["sum_R"],
            "obvious_mean_R": so["mean_R"], "obvious_pf": so["pf"],
            "inversion_gap_R": (si["mean_R"] - so["mean_R"]) if si["mean_R"] is not None and so["mean_R"] is not None else None,
        })
    return pd.DataFrame(rows)


def choose_locked(train: pd.DataFrame, val: pd.DataFrame, final: pd.DataFrame) -> pd.DataFrame:
    t = train.add_prefix("train_").rename(columns={"train_cell_id": "cell_id"})
    v = val.add_prefix("val_").rename(columns={"val_cell_id": "cell_id"})
    f = final.add_prefix("final_").rename(columns={"final_cell_id": "cell_id"})
    m = t.merge(v, on="cell_id", how="outer").merge(f, on="cell_id", how="outer")
    m["discovery_pass"] = (
        (m["train_n"] >= 40)
        & (m["train_inverse_mean_R"] >= 0.08)
        & (m["train_inverse_pf"] >= 1.10)
        & (m["train_inversion_gap_R"] >= 0.12)
    )
    m["validation_pass"] = (
        (m["val_n"] >= 20)
        & (m["val_inverse_mean_R"] > 0.00)
        & (m["val_inverse_pf"] > 1.00)
        & (m["val_inversion_gap_R"] > 0.00)
    )
    m["locked_before_2026"] = m["discovery_pass"] & m["validation_pass"]
    m["final_2026_pass"] = (
        (m["final_n"] >= 10)
        & (m["final_inverse_mean_R"] > 0.00)
        & (m["final_inverse_pf"] > 1.00)
    )
    return m


def locked_portfolio(trans: pd.DataFrame, locked: pd.DataFrame) -> pd.DataFrame:
    cells = set(locked.loc[locked["locked_before_2026"], "cell_id"].astype(str))
    if not cells:
        return pd.DataFrame()
    d = trans[trans["cell_id"].isin(cells)].copy()
    train_rank = locked.set_index("cell_id")["train_inverse_mean_R"].to_dict()
    d["train_rank"] = d["cell_id"].map(train_rank).fillna(-999.0)
    d = d.sort_values(["event_idx", "train_rank", "entry_minute"], ascending=[True, False, True])
    d = d.drop_duplicates("event_idx", keep="first")
    d = d.sort_values("entry_minute")
    return cooldown(d)


def yearly_portfolio(p: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if p.empty:
        return pd.DataFrame(columns=["year", "n", "mean_R", "pf", "sum_R", "max_dd_R"])
    for yr, g in p.groupby("entry_year", sort=True):
        s = stats(g.sort_values("entry_minute")["r_inverse"].to_numpy(float))
        rows.append({"year": int(yr), **s})
    return pd.DataFrame(rows)


def main() -> None:
    a = parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    x = add_obviousness(load_data(a.bars, a.labels))
    trans = build_transitions(x)
    if trans.empty:
        raise RuntimeError("No transitions generated")

    trans.to_parquet(a.outdir / "path_transition_events.parquet", index=False)
    year = summarize_cell_year(trans)
    year.to_csv(a.outdir / "cell_year_summary.csv", index=False)

    train = period_stats(trans, {2023, 2024})
    val = period_stats(trans, {2025})
    final = period_stats(trans, {2026})
    locked = choose_locked(train, val, final)
    locked = locked.sort_values(
        ["locked_before_2026", "train_inverse_mean_R", "val_inverse_mean_R"],
        ascending=[False, False, False], na_position="last",
    )
    locked.to_csv(a.outdir / "candidate_transfer.csv", index=False)

    diag = period_stats(trans, {2023, 2024, 2025, 2026})
    diag = diag.sort_values(["inverse_mean_R", "n"], ascending=[False, False])
    diag.to_csv(a.outdir / "pooled_diagnostic_cells.csv", index=False)

    port = locked_portfolio(trans, locked)
    if not port.empty:
        port.to_csv(a.outdir / "locked_portfolio_trades.csv", index=False)
    yp = yearly_portfolio(port)
    yp.to_csv(a.outdir / "locked_portfolio_yearly.csv", index=False)

    p2026 = port[port["entry_year"] == 2026] if not port.empty else pd.DataFrame()
    s26 = stats(p2026["r_inverse"].to_numpy(float)) if not p2026.empty else stats(np.array([]))
    locked_count = int(locked["locked_before_2026"].sum())
    positive26 = int((locked["locked_before_2026"] & locked["final_2026_pass"]).sum())

    if locked_count == 0:
        verdict = "FAIL_NO_TRANSFER"
    elif s26["n"] >= 20 and s26["mean_R"] is not None and s26["mean_R"] > 0 and s26["pf"] is not None and s26["pf"] > 1.05:
        verdict = "PASS"
    elif s26["n"] >= 10 and s26["mean_R"] is not None and s26["mean_R"] > 0:
        verdict = "WEAK_PASS"
    else:
        verdict = "FAIL_OOS"

    out = {
        "lab": "XAU_PRICE_TIME_ALOGICAL_PATH_TRANSITION_LAB_007",
        "rows_input": int(len(x)),
        "raw_transition_rows": int(len(trans)),
        "unique_origin_events": int(trans["event_idx"].nunique()),
        "matrix_cells": int(trans["cell_id"].nunique()),
        "locked_cells_before_2026": locked_count,
        "locked_cells_positive_in_2026": positive26,
        "final_2026_locked_portfolio": s26,
        "verdict": verdict,
        "causality": "obviousness <= t0-1; path through t0+W-1; DIRECT entry at t0+W; RETEST entry one minute after completed retest-touch; labels looked up only at actual entry minute",
        "target": {"sl_atr": SL_ATR, "rr": RR, "horizon_minutes": H},
    }
    (a.outdir / "verdict.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
