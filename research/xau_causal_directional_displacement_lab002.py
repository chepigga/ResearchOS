#!/usr/bin/env python3
"""XAU CAUSAL DIRECTIONAL DISPLACEMENT OOS LAB002.

Uses LAB001 M1 bars + future barrier labels. Tests exactly one causal feature
family: prior directional price displacement normalised by causal ATR.

No current-bar information is used by features. Thresholds are learned on
2023-2024 only, a single configuration per side is locked from TRAIN, then
reported unchanged on 2025 validation and 2026 final OOS.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

COMMISSION_RATE_SIDE = 0.000007
SL_ATR = 1.25
RR = 2.0
HORIZON_MIN = 240
COOLDOWN_MIN = 240
LABEL_COL = {"BUY": "BUY_S1.25_R2_H240", "SELL": "SELL_S1.25_R2_H240"}
LOOKBACKS = (5, 15, 60, 240)
QUANTILES = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.975, 0.99, 0.995)
MODES = ("CONTINUATION", "REVERSAL")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--bars", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--outdir", type=Path, default=Path("Results_XAU_CAUSAL_LAB002"))
    return p.parse_args()


def wilson_ci(k: int, n: int, z: float = 1.96):
    if n <= 0:
        return (None, None)
    p = k / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return center-half, center+half


def decluster(mask: np.ndarray, minutes: np.ndarray, cooldown: int) -> np.ndarray:
    out = np.zeros(len(mask), dtype=bool)
    last = -10**18
    for i in np.flatnonzero(mask):
        m = int(minutes[i])
        if m >= last + cooldown:
            out[i] = True
            last = m
    return out


def commission_r(entry: np.ndarray, atr: np.ndarray) -> np.ndarray:
    risk = SL_ATR * atr
    return np.divide(2.0 * COMMISSION_RATE_SIDE * entry, risk,
                     out=np.full_like(entry, np.nan, dtype=float), where=risk > 0)


def metrics(df: pd.DataFrame, side: str, select_mask: np.ndarray, split_name: str):
    lab = df[LABEL_COL[side]].to_numpy()
    minutes = df["minute"].to_numpy(np.int64)
    selected = decluster(select_mask, minutes, COOLDOWN_MIN)
    resolved = selected & np.isin(lab, np.array([-1, 1], dtype=np.int8))
    tp = int(np.sum(selected & (lab == 1)))
    sl = int(np.sum(selected & (lab == -1)))
    none = int(np.sum(selected & (lab == 0)))
    amb = int(np.sum(selected & (lab == 2)))
    n_sel = int(selected.sum())
    n_res = int(resolved.sum())
    wr = tp / n_res if n_res else None
    lo, hi = wilson_ci(tp, n_res)
    entry_col = "first_ask" if side == "BUY" else "first_bid"
    c = commission_r(df[entry_col].to_numpy(float), df["atr14_causal"].to_numpy(float))
    cmean = float(np.nanmean(c[resolved])) if n_res else None
    ev = (wr * RR - (1.0-wr) - cmean) if wr is not None and cmean is not None else None
    be = ((1.0 + cmean) / (1.0 + RR)) if cmean is not None else None
    years = pd.to_datetime(df.loc[selected, "timestamp_from_time_msc"]).dt.year
    year_span = max(1e-9, (pd.to_datetime(df["timestamp_from_time_msc"]).max() - pd.to_datetime(df["timestamp_from_time_msc"]).min()).total_seconds() / (365.25*86400))
    return {
        "split": split_name, "side": side, "selected_n": n_sel, "resolved_n": n_res,
        "tp": tp, "sl": sl, "none": none, "ambiguous": amb,
        "resolved_win_rate": wr, "wr_ci95_low": lo, "wr_ci95_high": hi,
        "mean_commission_R": cmean, "breakeven_win_rate_after_commission": be,
        "EV_R_after_commission": ev,
        "events_per_year": n_sel / year_span,
        "active_years": int(years.nunique()) if n_sel else 0,
    }


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    prior_close = d["mid_close"].shift(1)
    atr = d["atr14_causal"]
    for lb in LOOKBACKS:
        d[f"disp_{lb}_atr"] = (prior_close - d["mid_close"].shift(1 + lb)) / atr
    return d


def split_masks(ts: pd.Series):
    t = pd.to_datetime(ts)
    return {
        "TRAIN_2023_2024": (t < pd.Timestamp("2025-01-01")),
        "VALID_2025": ((t >= pd.Timestamp("2025-01-01")) & (t < pd.Timestamp("2026-01-01"))),
        "OOS_2026": (t >= pd.Timestamp("2026-01-01")),
    }


def main():
    a = parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    bars = pd.read_parquet(a.bars)
    labels = pd.read_parquet(a.labels)

    need_b = ["minute", "mid_close"]
    need_l = ["minute", "timestamp_from_time_msc", "first_bid", "first_ask", "atr14_causal", LABEL_COL["BUY"], LABEL_COL["SELL"]]
    miss_b = [c for c in need_b if c not in bars.columns]
    miss_l = [c for c in need_l if c not in labels.columns]
    if miss_b or miss_l:
        raise SystemExit(f"Missing columns bars={miss_b} labels={miss_l}")

    d = labels[need_l].merge(bars[need_b], on="minute", how="inner", validate="one_to_one")
    d = d.sort_values("minute").reset_index(drop=True)
    d = add_features(d)
    masks = split_masks(d["timestamp_from_time_msc"])
    train = masks["TRAIN_2023_2024"].to_numpy(bool)

    surface_rows = []
    selected_cfg = {}
    locked_rows = []
    yearly_rows = []

    for side in ("BUY", "SELL"):
        side_sign = 1.0 if side == "BUY" else -1.0
        candidates = []
        for lb in LOOKBACKS:
            x = d[f"disp_{lb}_atr"].to_numpy(float)
            directed = side_sign * x
            finite_train = train & np.isfinite(directed)
            train_vals = directed[finite_train]
            if len(train_vals) < 1000:
                continue
            for mode in MODES:
                basis = directed if mode == "CONTINUATION" else -directed
                basis_train = basis[finite_train]
                for q in QUANTILES:
                    thr = float(np.quantile(basis_train, q))
                    raw = np.isfinite(basis) & (basis >= thr)
                    row = {"lookback_min": lb, "mode": mode, "train_quantile": q, "threshold": thr}
                    split_metrics = {}
                    for split_name, sm in masks.items():
                        m = metrics(d.loc[sm].reset_index(drop=True), side, raw[sm.to_numpy(bool)], split_name)
                        split_metrics[split_name] = m
                        surface_rows.append({**row, **m})
                    tr = split_metrics["TRAIN_2023_2024"]
                    if tr["resolved_n"] >= 300 and tr["EV_R_after_commission"] is not None:
                        candidates.append((tr["EV_R_after_commission"], tr["resolved_n"], lb, mode, q, thr))

        if not candidates:
            selected_cfg[side] = None
            continue
        candidates.sort(key=lambda z: (z[0], z[1]), reverse=True)
        _, _, lb, mode, q, thr = candidates[0]
        selected_cfg[side] = {"lookback_min": lb, "mode": mode, "train_quantile": q, "threshold": thr}
        x = d[f"disp_{lb}_atr"].to_numpy(float)
        directed = side_sign * x
        basis = directed if mode == "CONTINUATION" else -directed
        raw = np.isfinite(basis) & (basis >= thr)

        for split_name, sm in masks.items():
            locked_rows.append({**selected_cfg[side], **metrics(d.loc[sm].reset_index(drop=True), side, raw[sm.to_numpy(bool)], split_name)})

        years = pd.to_datetime(d["timestamp_from_time_msc"]).dt.year
        for y in sorted(years.unique()):
            ym = (years == y).to_numpy(bool)
            if ym.sum() == 0:
                continue
            yearly_rows.append({**selected_cfg[side], **metrics(d.loc[ym].reset_index(drop=True), side, raw[ym], str(y))})

    surface = pd.DataFrame(surface_rows)
    locked = pd.DataFrame(locked_rows)
    yearly = pd.DataFrame(yearly_rows)
    surface.to_csv(a.outdir / "feature_surface.csv", index=False)
    locked.to_csv(a.outdir / "locked_oos_summary.csv", index=False)
    yearly.to_csv(a.outdir / "locked_yearly_summary.csv", index=False)

    verdict_side = {}
    for side in ("BUY", "SELL"):
        z = locked[locked["side"] == side] if not locked.empty else pd.DataFrame()
        if z.empty:
            verdict_side[side] = {"status": "NO_TRAIN_CANDIDATE"}
            continue
        tr = z[z["split"] == "TRAIN_2023_2024"].iloc[0]
        va = z[z["split"] == "VALID_2025"].iloc[0]
        oo = z[z["split"] == "OOS_2026"].iloc[0]
        pass_oos = (
            va["resolved_n"] >= 30 and oo["resolved_n"] >= 30 and
            va["EV_R_after_commission"] > 0 and oo["EV_R_after_commission"] > 0 and
            va["wr_ci95_low"] > va["breakeven_win_rate_after_commission"] and
            oo["wr_ci95_low"] > oo["breakeven_win_rate_after_commission"]
        )
        verdict_side[side] = {
            "status": "PASS_STRONG_OOS" if pass_oos else "FAIL_OR_WEAK_OOS",
            "locked_config": selected_cfg[side],
            "train_EV_R": float(tr["EV_R_after_commission"]),
            "validation_2025_EV_R": float(va["EV_R_after_commission"]),
            "oos_2026_EV_R": float(oo["EV_R_after_commission"]),
            "validation_2025_n": int(va["resolved_n"]),
            "oos_2026_n": int(oo["resolved_n"]),
        }

    any_pass = any(v.get("status") == "PASS_STRONG_OOS" for v in verdict_side.values())
    verdict = {
        "lab": "XAU_CAUSAL_DIRECTIONAL_DISPLACEMENT_OOS_LAB002",
        "feature_family": "prior directional displacement / causal ATR only",
        "canonical_target": {"sl_atr": SL_ATR, "rr": RR, "horizon_min": HORIZON_MIN, "cooldown_min": COOLDOWN_MIN},
        "causality": "feature at t uses completed M1 closes through t-1 only; ATR14 is LAB001 causal ATR; train thresholds never use 2025/2026",
        "selection": "single config per side chosen on 2023-2024 TRAIN only; 2025 validation and 2026 OOS are untouched",
        "side_verdicts": verdict_side,
        "status": "PROMOTE_FAMILY" if any_pass else "REJECT_FAMILY_AS_STANDALONE",
        "next_step": "If promoted, replicate locked rule with execution stress and event-level portfolio accounting. If rejected, move to the next single causal feature family without combining this one.",
    }
    (a.outdir / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    (a.outdir / "selected_configs.json").write_text(json.dumps(selected_cfg, indent=2), encoding="utf-8")

    print("===== LOCKED OOS SUMMARY =====")
    print(locked.to_string(index=False) if not locked.empty else "EMPTY")
    print("===== YEARLY =====")
    print(yearly.to_string(index=False) if not yearly.empty else "EMPTY")
    print("===== VERDICT =====")
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
