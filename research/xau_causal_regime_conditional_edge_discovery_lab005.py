#!/usr/bin/env python3
"""XAU_CAUSAL_REGIME_CONDITIONAL_EDGE_DISCOVERY_LAB005

Causal OOS discovery of event-family x market-regime interaction on XAU.

Frozen target from LAB001/LAB004:
    SL = 1.25 ATR14, TP = 2R, horizon = 240 minutes.

Protocol:
- Rebuild LAB004 V2 router walk-forward using only data before each OOS month.
- Event definitions are fixed ex-ante and use only completed bars t-1 or earlier.
- At observation t, evaluate event-only vs the same events split by router state.
- HOSTILE is tested as a veto; FAVORABLE is tested as a boost, not assumed useful.
- A 240-minute cooldown per event-family/side creates a non-overlapping event stream.

No future label is used in an event definition or router feature.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SL_ATR = 1.25
RR = 2.0
H = 240
COMMISSION_RATE_SIDE = 0.000007
LABEL = {"BUY": "BUY_S1.25_R2_H240", "SELL": "SELL_S1.25_R2_H240"}

FAV_Q = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95)
HOST_Q = (0.05, 0.10, 0.20, 0.30, 0.40, 0.50)
MIN_FIT = 100
MIN_CAL = 30

FEATURES = [
    "atr_pct", "atr_ratio_4h", "atr_ratio_1d", "atr_accel_15", "atr_accel_60",
    "prev_range_atr", "rv15_atr", "rv60_atr", "eff15", "eff60",
    "tick_ratio_60", "spread_ratio_60", "spread_atr", "trend15_atr", "trend60_atr",
    "hour_sin", "hour_cos",
]

EVENT_FAMILIES = [
    "SWEEP_RECLAIM_20",
    "BREAKOUT_ACCEPT_20",
    "IMPULSE_PULLBACK_2BAR",
    "COMPRESSION_BREAK_15",
    "PROTECTED_PIVOT_BREAK",
    "VOL_EXP_CONTINUATION",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--bars", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--outdir", type=Path, required=True)
    return p.parse_args()


def add_router_features(d: pd.DataFrame) -> pd.DataFrame:
    x = d.sort_values("minute").copy()
    atr = x["atr14_causal"].astype(float)
    pc = x["mid_close"].shift(1).astype(float)
    pret = x["mid_close"].pct_change().shift(1)
    pac = x["mid_close"].diff().abs().shift(1)
    pr = (x["mid_high"].shift(1) - x["mid_low"].shift(1)).astype(float)
    pt = x["tick_count"].shift(1).astype(float)
    ps = x["spread_mean"].shift(1).astype(float)
    x["atr_pct"] = atr / pc
    x["atr_ratio_4h"] = atr / atr.rolling(240, min_periods=120).median()
    x["atr_ratio_1d"] = atr / atr.rolling(1440, min_periods=720).median()
    x["atr_accel_15"] = atr / atr.shift(15)
    x["atr_accel_60"] = atr / atr.shift(60)
    x["prev_range_atr"] = pr / atr
    x["rv15_atr"] = (pret.rolling(15, min_periods=10).std() * pc) / atr
    x["rv60_atr"] = (pret.rolling(60, min_periods=40).std() * pc) / atr
    for lb in (15, 60):
        den = pac.rolling(lb, min_periods=max(10, lb // 2)).sum()
        x[f"eff{lb}"] = (pc - pc.shift(lb)).abs() / den
        x[f"trend{lb}_atr"] = (pc - pc.shift(lb)) / atr
    x["tick_ratio_60"] = pt / pt.rolling(60, min_periods=30).median()
    x["spread_ratio_60"] = ps / ps.rolling(60, min_periods=30).median()
    x["spread_atr"] = ps / atr
    ts = pd.to_datetime(x["timestamp_from_time_msc"])
    hour = ts.dt.hour + ts.dt.minute / 60.0
    x["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    x["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    x.replace([np.inf, -np.inf], np.nan, inplace=True)
    return x


def add_fixed_causal_events(d: pd.DataFrame) -> pd.DataFrame:
    x = d.copy()
    a = x["atr14_causal"].astype(float)
    o1, h1, l1, c1 = [x[c].shift(1).astype(float) for c in ("mid_open", "mid_high", "mid_low", "mid_close")]
    o2, h2, l2, c2 = [x[c].shift(2).astype(float) for c in ("mid_open", "mid_high", "mid_low", "mid_close")]
    h3, l3 = x["mid_high"].shift(3).astype(float), x["mid_low"].shift(3).astype(float)
    h4, l4 = x["mid_high"].shift(4).astype(float), x["mid_low"].shift(4).astype(float)
    h5, l5 = x["mid_high"].shift(5).astype(float), x["mid_low"].shift(5).astype(float)
    r1 = (h1 - l1).replace(0, np.nan)
    body1 = c1 - o1
    close_pos = (c1 - l1) / r1
    prior_hi20 = x["mid_high"].shift(2).rolling(20, min_periods=20).max()
    prior_lo20 = x["mid_low"].shift(2).rolling(20, min_periods=20).min()
    x["EV_SWEEP_RECLAIM_20_BUY"] = (l1 < prior_lo20) & (c1 > prior_lo20) & (close_pos >= 0.60)
    x["EV_SWEEP_RECLAIM_20_SELL"] = (h1 > prior_hi20) & (c1 < prior_hi20) & (close_pos <= 0.40)
    x["EV_BREAKOUT_ACCEPT_20_BUY"] = (c1 > prior_hi20) & (body1 >= 0.35 * a) & (r1 >= 0.80 * a) & (close_pos >= 0.65)
    x["EV_BREAKOUT_ACCEPT_20_SELL"] = (c1 < prior_lo20) & (body1 <= -0.35 * a) & (r1 >= 0.80 * a) & (close_pos <= 0.35)
    r2 = (h2 - l2).replace(0, np.nan)
    b2 = c2 - o2
    buy_imp = (b2 >= 0.80 * a) & (r2 >= 1.10 * a)
    sell_imp = (b2 <= -0.80 * a) & (r2 >= 1.10 * a)
    x["EV_IMPULSE_PULLBACK_2BAR_BUY"] = buy_imp & (c1 < c2) & (l1 <= c2 - 0.20 * b2) & (c1 >= o2 + 0.45 * b2) & (r1 <= 1.10 * a)
    x["EV_IMPULSE_PULLBACK_2BAR_SELL"] = sell_imp & (c1 > c2) & (h1 >= c2 - 0.20 * b2) & (c1 <= o2 + 0.45 * b2) & (r1 <= 1.10 * a)
    comp_hi = x["mid_high"].shift(2).rolling(15, min_periods=15).max()
    comp_lo = x["mid_low"].shift(2).rolling(15, min_periods=15).min()
    compressed = (comp_hi - comp_lo) <= 3.25 * a
    x["EV_COMPRESSION_BREAK_15_BUY"] = compressed & (c1 > comp_hi) & (body1 >= 0.30 * a) & (r1 >= 0.75 * a)
    x["EV_COMPRESSION_BREAK_15_SELL"] = compressed & (c1 < comp_lo) & (body1 <= -0.30 * a) & (r1 >= 0.75 * a)
    pivot_low = (l3 < l4) & (l3 < l5) & (l3 < l2) & (l3 < l1)
    pivot_high = (h3 > h4) & (h3 > h5) & (h3 > h2) & (h3 > h1)
    x["EV_PROTECTED_PIVOT_BREAK_BUY"] = pivot_low & (c1 > h2) & (body1 > 0) & ((c1 - l3) >= 0.60 * a)
    x["EV_PROTECTED_PIVOT_BREAK_SELL"] = pivot_high & (c1 < l2) & (body1 < 0) & ((h3 - c1) >= 0.60 * a)
    x["EV_VOL_EXP_CONTINUATION_BUY"] = (r1 >= 1.50 * a) & (body1 >= 0.80 * a) & (close_pos >= 0.80)
    x["EV_VOL_EXP_CONTINUATION_SELL"] = (r1 >= 1.50 * a) & (body1 <= -0.80 * a) & (close_pos <= 0.20)
    for fam in EVENT_FAMILIES:
        for side in ("BUY", "SELL"):
            col = f"EV_{fam}_{side}"
            x[col] = x[col].fillna(False).astype(bool)
    return x


def commission_r(df: pd.DataFrame, side: str) -> np.ndarray:
    e = df["first_ask" if side == "BUY" else "first_bid"].to_numpy(float)
    a = df["atr14_causal"].to_numpy(float)
    return np.divide(2 * COMMISSION_RATE_SIDE * e, SL_ATR * a, out=np.full(len(df), np.nan), where=a > 0)


def actual_r(df: pd.DataFrame, side: str) -> np.ndarray:
    lab = df[LABEL[side]].to_numpy()
    c = commission_r(df, side)
    r = np.full(len(df), np.nan)
    r[lab == 1] = RR - c[lab == 1]
    r[lab == -1] = -1.0 - c[lab == -1]
    r[lab == 0] = -c[lab == 0]
    return r


def make_model() -> Pipeline:
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("lr", LogisticRegression(C=0.20, max_iter=1000, solver="lbfgs"))])


def fit_pair(df: pd.DataFrame, side: str):
    lab = df[LABEL[side]].to_numpy()
    valid = np.isin(lab, [-1, 0, 1])
    if valid.sum() < MIN_FIT:
        return None
    yres = (lab[valid] != 0).astype(int)
    u = np.unique(yres)
    if len(u) == 1:
        if u[0] != 1:
            return None
        resolve = None
    else:
        resolve = make_model().fit(df.loc[valid, FEATURES], yres)
    res = valid & np.isin(lab, [-1, 1])
    yw = (lab[res] == 1).astype(int)
    if res.sum() < MIN_FIT or len(np.unique(yw)) < 2:
        return None
    win = make_model().fit(df.loc[res, FEATURES], yw)
    return resolve, win


def score_pair(models, df: pd.DataFrame, side: str) -> np.ndarray:
    if models is None:
        return np.full(len(df), np.nan)
    resolve, win = models
    X = df[FEATURES]
    pres = np.ones(len(df)) if resolve is None else resolve.predict_proba(X)[:, 1]
    pwin = win.predict_proba(X)[:, 1]
    return pres * ((RR + 1.0) * pwin - 1.0) - commission_r(df, side)


def choose_router_quantiles(fdf, cdf, side, fs, cs):
    fr = actual_r(fdf, side)
    cr = actual_r(cdf, side)
    ff = np.isfinite(fs) & np.isfinite(fr)
    cf = np.isfinite(cs) & np.isfinite(cr)
    fav = None
    host = None
    if ff.sum() < MIN_FIT or cf.sum() < MIN_CAL:
        return None, None
    for q in FAV_Q:
        th = float(np.quantile(fs[ff], q)); fm = ff & (fs >= th); cm = cf & (cs >= th)
        fe = float(np.mean(fr[fm])) if fm.sum() else np.nan; ce = float(np.mean(cr[cm])) if cm.sum() else np.nan
        if fm.sum() >= MIN_FIT and cm.sum() >= MIN_CAL and fe > 0 and ce > 0:
            key = (min(fe, ce), ce, int(cm.sum())); fav = (key, q) if fav is None or key > fav[0] else fav
    for q in HOST_Q:
        th = float(np.quantile(fs[ff], q)); fm = ff & (fs <= th); cm = cf & (cs <= th)
        fe = float(np.mean(fr[fm])) if fm.sum() else np.nan; ce = float(np.mean(cr[cm])) if cm.sum() else np.nan
        if fm.sum() >= MIN_FIT and cm.sum() >= MIN_CAL and fe < 0 and ce < 0:
            key = (max(fe, ce), ce, -int(cm.sum())); host = (key, q) if host is None or key < host[0] else host
    return (fav[1] if fav else None), (host[1] if host else None)


def summarize_rows(df: pd.DataFrame, state_filter: str) -> dict:
    if df.empty:
        return {"state_filter": state_filter, "n": 0}
    r = df["actual_R"].to_numpy(float); lab = df["label"].to_numpy(); ok = np.isfinite(r); r, lab = r[ok], lab[ok]; n = len(r)
    if n == 0:
        return {"state_filter": state_filter, "n": 0}
    tp = int((lab == 1).sum()); sl = int((lab == -1).sum()); none = int((lab == 0).sum()); resolved = tp + sl; wr = tp / resolved if resolved else None
    mean_r = float(np.mean(r)); sd = float(np.std(r, ddof=1)) if n > 1 else None; se = sd / math.sqrt(n) if sd is not None else None
    gp = float(r[r > 0].sum()); gl = float(-r[r < 0].sum())
    return {"state_filter": state_filter, "n": n, "tp": tp, "sl": sl, "none": none, "resolved_n": resolved, "resolved_win_rate": wr, "mean_R": mean_r, "mean_R_ci95_low": mean_r - 1.96 * se if se is not None else None, "mean_R_ci95_high": mean_r + 1.96 * se if se is not None else None, "profit_factor_R": gp / gl if gl > 0 else None}


def main() -> None:
    a = parse_args(); a.outdir.mkdir(parents=True, exist_ok=True)
    bars = pd.read_parquet(a.bars); labels = pd.read_parquet(a.labels)
    bcols = ["minute", "mid_open", "mid_high", "mid_low", "mid_close"]
    lcols = ["minute", "timestamp_from_time_msc", "first_bid", "first_ask", "atr14_causal", "tick_count", "spread_mean", LABEL["BUY"], LABEL["SELL"]]
    d = labels[lcols].merge(bars[bcols], on="minute", how="inner", validate="one_to_one").sort_values("minute").reset_index(drop=True)
    d = add_router_features(d); d = add_fixed_causal_events(d)
    ts = pd.to_datetime(d["timestamp_from_time_msc"]); d["year"] = ts.dt.year; d["month"] = ts.dt.to_period("M").astype(str); d["grid_bucket"] = d["minute"] // H; d["is_grid"] = ~d["grid_bucket"].duplicated()
    start = max(pd.Timestamp("2024-01-01"), ts.min().normalize() + pd.Timedelta(days=365)).to_period("M").to_timestamp(); end = ts.max().to_period("M").to_timestamp(); months = pd.date_range(start, end, freq="MS")
    last_event = {(fam, side): -10**18 for fam in EVENT_FAMILIES for side in ("BUY", "SELL")}
    event_rows = []; monthly_counts = []; router_months = []
    for m0 in months:
        m1 = m0 + pd.offsets.MonthBegin(1); tr0 = m0 - pd.Timedelta(days=365); cal0 = m0 - pd.Timedelta(days=90)
        full = (ts >= tr0) & (ts < m0) & d["is_grid"]; fit = (ts >= tr0) & (ts < cal0) & d["is_grid"]; cal = (ts >= cal0) & (ts < m0) & d["is_grid"]; test = (ts >= m0) & (ts < m1)
        if fit.sum() < 500 or cal.sum() < 100 or test.sum() == 0: continue
        fdf = d.loc[fit].reset_index(drop=True); cdf = d.loc[cal].reset_index(drop=True); fulldf = d.loc[full].reset_index(drop=True); tdf = d.loc[test].copy().reset_index(drop=True)
        for side in ("BUY", "SELL"):
            base = fit_pair(fdf, side)
            if base is None: continue
            fs = score_pair(base, fdf, side); cs = score_pair(base, cdf, side); fq, hq = choose_router_quantiles(fdf, cdf, side, fs, cs)
            fm = fit_pair(fulldf, side)
            if fm is None: continue
            trscore = score_pair(fm, fulldf, side); finite = np.isfinite(trscore)
            fth = float(np.quantile(trscore[finite], fq)) if fq is not None and finite.any() else None; hth = float(np.quantile(trscore[finite], hq)) if hq is not None and finite.any() else None
            score = score_pair(fm, tdf, side); state = np.full(len(tdf), "NEUTRAL", dtype=object)
            if hth is not None: state[np.isfinite(score) & (score <= hth)] = "HOSTILE"
            if fth is not None: state[np.isfinite(score) & (score >= fth)] = "FAVORABLE"
            router_months.append({"test_month": str(m0.date()), "side": side, "favorable_q": fq, "hostile_q": hq, "favorable_threshold": fth, "hostile_threshold": hth, "favorable_enabled": fq is not None, "hostile_enabled": hq is not None, "resolver_mode": "MODEL" if fm[0] is not None else "CONSTANT_ONE"})
            labels_side = tdf[LABEL[side]].to_numpy(); r_side = actual_r(tdf, side)
            for fam in EVENT_FAMILIES:
                em = tdf[f"EV_{fam}_{side}"].to_numpy(bool); raw_idx = np.flatnonzero(em & np.isin(labels_side, [-1, 0, 1]) & np.isfinite(r_side)); chosen = []
                for i in raw_idx:
                    minute = int(tdf.loc[i, "minute"])
                    if minute >= last_event[(fam, side)] + H:
                        chosen.append(i); last_event[(fam, side)] = minute
                monthly_counts.append({"test_month": str(m0.date()), "side": side, "family": fam, "raw_n": int(len(raw_idx)), "independent_n": int(len(chosen)), "hostile_enabled": hth is not None, "favorable_enabled": fth is not None})
                for i in chosen:
                    event_rows.append({"minute": int(tdf.loc[i, "minute"]), "timestamp": str(tdf.loc[i, "timestamp_from_time_msc"]), "year": int(tdf.loc[i, "year"]), "month": str(tdf.loc[i, "month"]), "side": side, "family": fam, "router_state": str(state[i]), "router_score": float(score[i]) if np.isfinite(score[i]) else None, "label": int(labels_side[i]), "actual_R": float(r_side[i]), "atr14_causal": float(tdf.loc[i, "atr14_causal"])})
    events = pd.DataFrame(event_rows); counts = pd.DataFrame(monthly_counts); pd.DataFrame(router_months).to_csv(a.outdir / "router_months.csv", index=False); counts.to_csv(a.outdir / "event_frequency_monthly.csv", index=False)
    if not events.empty: events.to_parquet(a.outdir / "independent_event_oos.parquet", index=False)
    summary_rows = []; yearly_rows = []; uplift_rows = []
    if not events.empty:
        for fam in EVENT_FAMILIES:
            for side in ("BUY", "SELL"):
                z = events[(events["family"] == fam) & (events["side"] == side)].copy()
                filters = {"ALL": np.ones(len(z), dtype=bool), "NON_HOSTILE": z["router_state"].ne("HOSTILE").to_numpy(), "FAVORABLE": z["router_state"].eq("FAVORABLE").to_numpy(), "NEUTRAL": z["router_state"].eq("NEUTRAL").to_numpy(), "HOSTILE": z["router_state"].eq("HOSTILE").to_numpy()}
                local = {}
                for name, mask in filters.items():
                    s = summarize_rows(z.loc[mask], name); s.update({"family": fam, "side": side}); summary_rows.append(s); local[name] = s
                    for year in sorted(z["year"].unique()):
                        zy = z.loc[mask & z["year"].eq(year).to_numpy()]; sy = summarize_rows(zy, name); sy.update({"year": int(year), "family": fam, "side": side}); yearly_rows.append(sy)
                def gv(name, field):
                    v = local.get(name, {}).get(field); return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else v
                all_ev = gv("ALL", "mean_R"); nh_ev = gv("NON_HOSTILE", "mean_R"); fav_ev = gv("FAVORABLE", "mean_R"); host_ev = gv("HOSTILE", "mean_R")
                uplift_rows.append({"family": fam, "side": side, "all_n": gv("ALL", "n"), "all_ev_R": all_ev, "non_hostile_n": gv("NON_HOSTILE", "n"), "non_hostile_ev_R": nh_ev, "non_hostile_uplift_R": (nh_ev - all_ev) if nh_ev is not None and all_ev is not None else None, "favorable_n": gv("FAVORABLE", "n"), "favorable_ev_R": fav_ev, "favorable_uplift_R": (fav_ev - all_ev) if fav_ev is not None and all_ev is not None else None, "hostile_n": gv("HOSTILE", "n"), "hostile_ev_R": host_ev, "hostile_damage_R": (host_ev - all_ev) if host_ev is not None and all_ev is not None else None})
    summary = pd.DataFrame(summary_rows); yearly = pd.DataFrame(yearly_rows); uplift = pd.DataFrame(uplift_rows); summary.to_csv(a.outdir / "event_regime_summary.csv", index=False); yearly.to_csv(a.outdir / "event_regime_yearly.csv", index=False); uplift.to_csv(a.outdir / "regime_uplift.csv", index=False)
    candidates = []
    if not summary.empty:
        for fam in EVENT_FAMILIES:
            for side in ("BUY", "SELL"):
                allr = summary[(summary.family == fam) & (summary.side == side) & (summary.state_filter == "ALL")]; nhr = summary[(summary.family == fam) & (summary.side == side) & (summary.state_filter == "NON_HOSTILE")]; hr = summary[(summary.family == fam) & (summary.side == side) & (summary.state_filter == "HOSTILE")]
                if allr.empty or nhr.empty: continue
                A, N = allr.iloc[0], nhr.iloc[0]; Hs = hr.iloc[0] if not hr.empty else None
                all_ev = float(A.mean_R) if pd.notna(A.get("mean_R")) else None; nh_ev = float(N.mean_R) if pd.notna(N.get("mean_R")) else None; uplift_v = nh_ev - all_ev if nh_ev is not None and all_ev is not None else None; pf = float(N.profit_factor_R) if pd.notna(N.get("profit_factor_R")) else None; ci = float(N.mean_R_ci95_low) if pd.notna(N.get("mean_R_ci95_low")) else None
                yn = yearly[(yearly.family == fam) & (yearly.side == side) & (yearly.state_filter == "NON_HOSTILE") & (yearly.n >= 20)]; usable_years = len(yn); positive_years = int((yn.mean_R > 0).sum()) if usable_years else 0; host_ev = float(Hs.mean_R) if Hs is not None and pd.notna(Hs.get("mean_R")) else None
                strong = int(N.n) >= 150 and nh_ev is not None and nh_ev > 0.05 and ci is not None and ci > 0 and pf is not None and pf >= 1.15 and uplift_v is not None and uplift_v >= 0.05 and usable_years >= 2 and positive_years >= usable_years - 1
                weak = int(N.n) >= 100 and nh_ev is not None and nh_ev > 0 and pf is not None and pf >= 1.05 and uplift_v is not None and uplift_v >= 0.03 and usable_years >= 2 and positive_years >= 2
                veto = int(N.n) >= 100 and uplift_v is not None and uplift_v >= 0.05 and host_ev is not None and all_ev is not None and host_ev <= all_ev - 0.10
                status_c = "PROMOTE_CONDITIONAL_EDGE" if strong else ("REPLICATE_WEAK_CONDITIONAL_EDGE" if weak else ("ROUTER_VETO_ONLY" if veto else "FAIL_CONDITIONAL_EDGE"))
                candidates.append({"family": fam, "side": side, "status": status_c, "all_n": int(A.n), "all_mean_R": all_ev, "non_hostile_n": int(N.n), "non_hostile_mean_R": nh_ev, "non_hostile_ci95_low": ci, "non_hostile_PF_R": pf, "uplift_R": uplift_v, "hostile_mean_R": host_ev, "positive_years": positive_years, "usable_years": usable_years})
    cand = pd.DataFrame(candidates)
    if not cand.empty:
        cand = cand.sort_values(["status", "non_hostile_mean_R", "non_hostile_n"], ascending=[True, False, False]); cand.to_csv(a.outdir / "candidate_verdicts.csv", index=False)
    if not cand.empty and (cand.status == "PROMOTE_CONDITIONAL_EDGE").any(): status = "PROMOTE_EVENT_X_REGIME_EDGE"
    elif not cand.empty and (cand.status == "REPLICATE_WEAK_CONDITIONAL_EDGE").any(): status = "REPLICATE_WEAK_EVENT_X_REGIME_EDGE"
    elif not cand.empty and (cand.status == "ROUTER_VETO_ONLY").any(): status = "KEEP_ROUTER_AS_VETO_SEARCH_NEW_EVENTS"
    else: status = "REJECT_FIXED_EVENT_FAMILIES"
    top = []
    if not cand.empty:
        for _, r in cand.sort_values("non_hostile_mean_R", ascending=False).head(8).iterrows():
            top.append({"family": r.family, "side": r.side, "status": r.status, "n": int(r.non_hostile_n), "mean_R": None if pd.isna(r.non_hostile_mean_R) else float(r.non_hostile_mean_R), "uplift_R": None if pd.isna(r.uplift_R) else float(r.uplift_R), "PF_R": None if pd.isna(r.non_hostile_PF_R) else float(r.non_hostile_PF_R)})
    verdict = {"lab": "XAU_CAUSAL_REGIME_CONDITIONAL_EDGE_DISCOVERY_LAB005", "status": status, "target": {"sl_atr": SL_ATR, "tp_R": RR, "horizon_min": H}, "event_families": EVENT_FAMILIES, "router": "LAB004 V2 logic rebuilt monthly; rolling 12m, ~9m fit + 90d calibration, next month pure OOS", "event_clock": "entry observation is first tick of minute t; event uses only completed M1 bars t-1 or earlier", "independence_guard": "240m cooldown per event-family/side before regime split", "interpretation": "positive NON_HOSTILE edge is required for promotion; less-negative is only veto evidence", "top_non_hostile_candidates": top}
    (a.outdir / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8"); print(json.dumps(verdict, indent=2), flush=True)

if __name__ == "__main__":
    main()
