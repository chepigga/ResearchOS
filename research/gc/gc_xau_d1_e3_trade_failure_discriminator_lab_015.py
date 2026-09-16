#!/usr/bin/env python3
"""LAB015 — trade-by-trade failure discriminator for corrected GC->XAU D1/E3.

Bounded historical discovery on already-collected AMP GC + FTMO XAU data.
Primary clock is ORDER_START_DEPLOYABLE. Fill-time model is diagnostic only.
"""
from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path("research/gc")
AMP_ZIP = ROOT / "_lab015" / "amp_gc.zip"
XAU_DIR = ROOT / "_lab015_xau"
BASE = ROOT / "gc_m1_orderflow_edge_discovery_003.py"
SEQ = ROOT / "GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H_SEQUENCES.csv"
LAB006 = ROOT / "GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006_EVENTS.csv"

OUT_JSON = ROOT / "GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015.json"
OUT_MD = ROOT / "GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015.md"
OUT_FEATURES = ROOT / "GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015_FEATURES.csv"
OUT_UNIV = ROOT / "GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015_UNIVARIATE.csv"
OUT_OOF = ROOT / "GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015_OOF.csv"
OUT_COEF = ROOT / "GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015_COEFFICIENTS.csv"

BROKER_OFFSET_MS = 180 * 60_000
COST_R = 0.05
INITIAL_TRAIN = 45
TEST_BLOCK = 12
VETO_QUANTILE = 0.75
EXPECTED_FILLS = 103

PRIMARY_FEATURES = [
    "gc_delta_excess",
    "gc_buy_strength",
    "gc_body_atr",
    "gc_range_atr",
    "gc_close_pos",
    "gc_breakout_atr",
    "gc_buy_loc_excess",
    "xau_spread_start_atr",
]

FILLTIME_FEATURES = PRIMARY_FEATURES + [
    "fill_delay_sec",
    "xau_spread_fill_atr",
    "xau_prefill_range_atr",
    "xau_fill_overshoot_atr",
    "xau_mom_10s_atr",
    "xau_mom_30s_atr",
    "gc_post_delta_frac",
]


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def max_dd(v: np.ndarray) -> float:
    if len(v) == 0:
        return np.nan
    eq = np.cumsum(np.nan_to_num(v, nan=0.0))
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    return float((peak[1:] - eq).max()) if len(eq) else 0.0


def load_base():
    spec = importlib.util.spec_from_file_location("edge003_lab015", BASE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def load_gc_bars() -> pd.DataFrame:
    m = load_base()
    b = m.load_amp(AMP_ZIP).copy()
    b["time"] = pd.to_datetime(b.time, utc=True)
    return b.sort_values("time").reset_index(drop=True)


def load_gc_raw_prefix():
    with zipfile.ZipFile(AMP_ZIP) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise SystemExit(f"Expected one AMP CSV, got {names}")
        with zf.open(names[0]) as raw:
            d = pd.read_csv(
                io.TextIOWrapper(raw, encoding="utf-8-sig"),
                usecols=["time_msc", "volume", "volume_real", "is_buy", "is_sell"],
                low_memory=False,
            )
    for c in ("time_msc", "volume", "volume_real", "is_buy", "is_sell"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    vr = d.volume_real.fillna(0.0)
    vi = d.volume.fillna(0.0)
    vol = np.where(vr > 0, vr, vi)
    ib = d.is_buy.fillna(0).astype(int).eq(1).to_numpy()
    ise = d.is_sell.fillna(0).astype(int).eq(1).to_numpy()
    t = d.time_msc.to_numpy(float)
    valid = np.isfinite(t) & (vol > 0) & (ib ^ ise)
    t = t[valid].astype(np.int64)
    vol = np.asarray(vol, float)[valid]
    buy = np.where(ib[valid], vol, 0.0)
    sell = np.where(ise[valid], vol, 0.0)
    order = np.argsort(t, kind="mergesort")
    t, buy, sell = t[order], buy[order], sell[order]
    buy_cum = np.r_[0.0, np.cumsum(buy)]
    sell_cum = np.r_[0.0, np.cumsum(sell)]
    return t, buy_cum, sell_cum


def gc_window_delta_frac(times, buy_cum, sell_cum, start_ms: int, end_ms: int):
    i0 = int(np.searchsorted(times, start_ms, side="left"))
    i1 = int(np.searchsorted(times, end_ms, side="right"))
    bv = float(buy_cum[i1] - buy_cum[i0])
    sv = float(sell_cum[i1] - sell_cum[i0])
    tot = bv + sv
    return (bv - sv) / tot if tot > 0 else np.nan


def load_xau_ticks():
    files = sorted(p for p in XAU_DIR.glob("XAUUSD_raw_ticks_*.csv") if ".meta." not in p.name)
    ts, bs, aas = [], [], []
    for p in files:
        d = pd.read_csv(p, usecols=lambda c: c in {"time_msc", "bid", "ask", "quote_valid"}, low_memory=False)
        if d.empty:
            continue
        for c in ("time_msc", "bid", "ask"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        if "quote_valid" in d.columns:
            q = pd.to_numeric(d.quote_valid, errors="coerce").fillna(0).eq(1)
        else:
            q = d.bid.gt(0) & d.ask.gt(0)
        d = d[q & d.time_msc.notna() & d.bid.gt(0) & d.ask.gt(0) & d.ask.ge(d.bid)].copy()
        if d.empty:
            continue
        ts.append(d.time_msc.to_numpy(np.int64))
        bs.append(d.bid.to_numpy(float))
        aas.append(d.ask.to_numpy(float))
    if not ts:
        raise SystemExit("No XAU ticks")
    t = np.concatenate(ts)
    b = np.concatenate(bs)
    a = np.concatenate(aas)
    order = np.argsort(t, kind="mergesort")
    t, b, a = t[order], b[order], a[order]
    # same price/time dedup semantics as prior labs
    keep = np.ones(len(t), dtype=bool)
    if len(t) > 1:
        keep[1:] = (t[1:] != t[:-1]) | (b[1:] != b[:-1]) | (a[1:] != a[:-1])
    return t[keep], b[keep], a[keep]


def find_exact_quote_index(times, bids, asks, ts: int, bid_ref=np.nan, ask_ref=np.nan, require_ask_le=None):
    lo = int(np.searchsorted(times, ts, side="left"))
    hi = int(np.searchsorted(times, ts, side="right"))
    if lo >= hi:
        return None
    idx = np.arange(lo, hi)
    if require_ask_le is not None:
        h = idx[asks[idx] <= require_ask_le + 1e-12]
        if len(h):
            return int(h[0])
    if np.isfinite(bid_ref) and np.isfinite(ask_ref):
        err = np.abs(bids[idx] - bid_ref) + np.abs(asks[idx] - ask_ref)
        return int(idx[int(np.argmin(err))])
    return lo


def mid_at_or_before(times, bids, asks, target: int, floor_idx: int):
    j = int(np.searchsorted(times, target, side="right")) - 1
    j = max(j, floor_idx)
    return (float(bids[j]) + float(asks[j])) / 2.0


def load_population() -> tuple[pd.DataFrame, pd.DataFrame]:
    seq = pd.read_csv(SEQ, low_memory=False)
    seq["signal_time_utc"] = pd.to_datetime(seq.signal_time_utc, utc=True)
    for c in ("r", "adj_r_corrected", "fill_time_msc", "exit_time_msc"):
        seq[c] = pd.to_numeric(seq[c], errors="coerce")
    for c in ("filled", "accepted_corrected", "busy_skip_corrected"):
        seq[c] = as_bool(seq[c])
    amp_seq = seq[seq.cohort.eq("AMP_ALL")].sort_values("signal_time_utc").reset_index(drop=True)
    pop = amp_seq[amp_seq.accepted_corrected & amp_seq.filled].copy()

    e = pd.read_csv(LAB006, low_memory=False)
    e = e[e.source_feed.eq("AMP") & e.rule.eq("BUYER_BREAKOUT_LONG")].copy()
    e["signal_time_utc"] = pd.to_datetime(e.signal_time_utc, utc=True)
    e["executable"] = as_bool(e.executable)
    for c in ("broker_target_msc", "entry_tick_msc", "entry_bid", "entry_ask", "xau_atr14_m1"):
        e[c] = pd.to_numeric(e[c], errors="coerce")
    e = e[e.executable].drop_duplicates("signal_time_utc")
    cols = ["signal_time_utc", "broker_target_msc", "entry_tick_msc", "entry_bid", "entry_ask", "xau_atr14_m1"]
    pop = pop.merge(e[cols], on="signal_time_utc", how="left", validate="one_to_one")
    return pop.sort_values("signal_time_utc").reset_index(drop=True), amp_seq


def build_feature_table(pop, gc_bars, gc_raw, xau):
    gt, gbuy, gsell = gc_raw
    xt, xb, xa = xau
    g = gc_bars.set_index("time", drop=False)
    rows = []
    for r in pop.itertuples(index=False):
        sig = pd.Timestamp(r.signal_time_utc)
        if sig not in g.index:
            raise SystemExit(f"Missing GC signal bar {sig}")
        s = g.loc[sig]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[0]
        atr_x = float(r.xau_atr14_m1)
        if not np.isfinite(atr_x) or atr_x <= 0:
            raise SystemExit(f"Bad XAU ATR {sig}")
        start_ts = int(r.entry_tick_msc)
        fill_ts = int(r.fill_time_msc)
        limit_price = float(r.entry_ask) - atr_x
        si = find_exact_quote_index(xt, xb, xa, start_ts, float(r.entry_bid), float(r.entry_ask))
        fi = find_exact_quote_index(xt, xb, xa, fill_ts, require_ask_le=limit_price)
        if si is None or fi is None or fi < si:
            raise SystemExit(f"Cannot reconstruct XAU path {sig} start={si} fill={fi}")
        mid_path = (xb[si:fi + 1] + xa[si:fi + 1]) / 2.0
        mid_fill = (float(xb[fi]) + float(xa[fi])) / 2.0
        m10 = mid_at_or_before(xt, xb, xa, fill_ts - 10_000, si)
        m30 = mid_at_or_before(xt, xb, xa, fill_ts - 30_000, si)
        order_start_utc_ms = int(sig.value // 1_000_000) + 60_000
        fill_utc_ms = fill_ts - BROKER_OFFSET_MS
        q75_buy = float(s.q75_buy)
        q75_buyloc = float(s.q75_buyloc)
        row = {
            "signal_time_utc": sig.isoformat(),
            "status": str(r.status),
            "raw_r": float(r.r),
            "net_r": float(r.adj_r_corrected),
            "sl_label": int(str(r.status) == "SL"),
            "negative_net_label": int(float(r.adj_r_corrected) < 0),
            "gc_delta_excess": float(s.delta_frac - s.q90_delta),
            "gc_buy_strength": float(s.buy_vol / q75_buy) if q75_buy > 0 else np.nan,
            "gc_body_atr": float(s.body_atr),
            "gc_range_atr": float(s.range_atr),
            "gc_close_pos": float(s.close_pos),
            "gc_breakout_atr": float((s.high - s.prior20_high) / s.atr14),
            "gc_buy_loc_excess": float(s.buy_loc - q75_buyloc),
            "xau_spread_start_atr": float((r.entry_ask - r.entry_bid) / atr_x),
            "fill_delay_sec": float((fill_ts - int(r.broker_target_msc)) / 1000.0),
            "xau_spread_fill_atr": float((xa[fi] - xb[fi]) / atr_x),
            "xau_prefill_range_atr": float((np.max(mid_path) - np.min(mid_path)) / atr_x),
            "xau_fill_overshoot_atr": float((limit_price - xa[fi]) / atr_x),
            "xau_mom_10s_atr": float((mid_fill - m10) / atr_x),
            "xau_mom_30s_atr": float((mid_fill - m30) / atr_x),
            "gc_post_delta_frac": gc_window_delta_frac(gt, gbuy, gsell, order_start_utc_ms, fill_utc_ms),
            "xau_atr14_m1": atr_x,
            "fill_time_msc": fill_ts,
        }
        rows.append(row)
    return pd.DataFrame(rows).sort_values("signal_time_utc").reset_index(drop=True)


def univariate_table(df: pd.DataFrame):
    rows = []
    y = df.sl_label.to_numpy(int)
    for f in FILLTIME_FEATURES:
        x = pd.to_numeric(df[f], errors="coerce").to_numpy(float)
        m = np.isfinite(x)
        yy, xx = y[m], x[m]
        auc = np.nan
        if len(np.unique(yy)) == 2:
            auc = float(roc_auc_score(yy, xx))
        sl = xx[yy == 1]
        ok = xx[yy == 0]
        sd = float(np.std(xx, ddof=1)) if len(xx) > 1 else np.nan
        smd = (float(np.mean(sl)) - float(np.mean(ok))) / sd if len(sl) and len(ok) and np.isfinite(sd) and sd > 0 else np.nan
        rows.append({
            "feature": f,
            "clock": "ORDER_START_DEPLOYABLE" if f in PRIMARY_FEATURES else "FILL_TIME_DIAGNOSTIC_ONLY",
            "n": int(m.sum()),
            "sl_median": float(np.median(sl)) if len(sl) else np.nan,
            "non_sl_median": float(np.median(ok)) if len(ok) else np.nan,
            "auc_raw": auc,
            "auc_directionless": max(auc, 1.0 - auc) if np.isfinite(auc) else np.nan,
            "failure_direction": "HIGH" if np.isfinite(auc) and auc >= 0.5 else "LOW",
            "standardized_mean_diff_sl_minus_non": smd,
        })
    return pd.DataFrame(rows).sort_values("auc_directionless", ascending=False, na_position="last")


def make_model():
    return Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(C=1.0, class_weight="balanced", solver="liblinear", max_iter=5000, random_state=20260917)),
    ])


def walkforward(df: pd.DataFrame, features: list[str], clock: str):
    d = df.sort_values("signal_time_utc").reset_index(drop=True)
    preds, coefs, folds = [], [], []
    fold = 0
    start = INITIAL_TRAIN
    while start < len(d):
        end = min(start + TEST_BLOCK, len(d))
        tr = d.iloc[:start].copy()
        te = d.iloc[start:end].copy()
        ytr = tr.sl_label.to_numpy(int)
        if len(np.unique(ytr)) < 2:
            raise SystemExit(f"Single-class training window in {clock} fold {fold}")
        model = make_model()
        model.fit(tr[features], ytr)
        ptr = model.predict_proba(tr[features])[:, 1]
        threshold = float(np.quantile(ptr, VETO_QUANTILE))
        pte = model.predict_proba(te[features])[:, 1]
        veto = pte >= threshold
        block_auc = float(roc_auc_score(te.sl_label, pte)) if te.sl_label.nunique() == 2 else np.nan
        folds.append({
            "clock": clock,
            "fold": fold,
            "train_n": int(len(tr)),
            "test_n": int(len(te)),
            "test_start": str(te.signal_time_utc.iloc[0]),
            "test_end": str(te.signal_time_utc.iloc[-1]),
            "threshold": threshold,
            "test_auc": block_auc,
            "test_sl_rate": float(te.sl_label.mean()),
            "veto_share": float(veto.mean()),
            "veto_sl_rate": float(te.loc[veto, "sl_label"].mean()) if veto.any() else np.nan,
        })
        z = te[["signal_time_utc", "status", "net_r", "sl_label", "negative_net_label"]].copy()
        z["clock"] = clock
        z["fold"] = fold
        z["p_sl"] = pte
        z["threshold"] = threshold
        z["veto"] = veto
        preds.append(z)
        coef = model.named_steps["clf"].coef_[0]
        for f, c in zip(features, coef):
            coefs.append({"clock": clock, "fold": fold, "feature": f, "standardized_logit_coef": float(c)})
        start = end
        fold += 1
    return pd.concat(preds, ignore_index=True), pd.DataFrame(coefs), pd.DataFrame(folds)


def overlay_metrics(oof: pd.DataFrame, amp_seq: pd.DataFrame):
    z = oof.sort_values("signal_time_utc").copy()
    y = z.sl_label.to_numpy(int)
    p = z.p_sl.to_numpy(float)
    auc = float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else np.nan
    ap = float(average_precision_score(y, p)) if len(np.unique(y)) == 2 else np.nan
    veto = z.veto.to_numpy(bool)
    base_sl = float(np.mean(y))
    veto_sl = float(np.mean(y[veto])) if veto.any() else np.nan
    enrich = veto_sl / base_sl if veto.any() and base_sl > 0 else np.nan

    first = pd.Timestamp(z.signal_time_utc.iloc[0])
    seq = amp_seq[amp_seq.signal_time_utc >= first].copy().reset_index(drop=True)
    seq["baseline_r"] = pd.to_numeric(seq.adj_r_corrected, errors="coerce").fillna(0.0)
    seq["overlay_r"] = seq.baseline_r.copy()
    veto_times = set(pd.to_datetime(z.loc[z.veto, "signal_time_utc"], utc=True))
    seq.loc[seq.signal_time_utc.isin(veto_times), "overlay_r"] = 0.0
    half = len(seq) // 2
    late = seq.iloc[half:]

    fv = z.net_r.to_numpy(float)
    ov = np.where(veto, 0.0, fv)
    return {
        "oof_fills": int(len(z)),
        "oof_sl": int(y.sum()),
        "oof_sl_rate": base_sl,
        "oof_auc_sl": auc,
        "oof_average_precision_sl": ap,
        "vetoed_fills": int(veto.sum()),
        "veto_share": float(veto.mean()),
        "veto_sl_rate": veto_sl,
        "veto_sl_enrichment_x": enrich,
        "fill_baseline_sum_r": float(fv.sum()),
        "fill_overlay_sum_r": float(ov.sum()),
        "fill_baseline_ev_r": float(fv.mean()),
        "fill_overlay_ev_r": float(ov.mean()),
        "original_signals_oof_period": int(len(seq)),
        "signal_baseline_sum_r": float(seq.baseline_r.sum()),
        "signal_overlay_sum_r": float(seq.overlay_r.sum()),
        "signal_baseline_ev_r": float(seq.baseline_r.mean()),
        "signal_overlay_ev_r": float(seq.overlay_r.mean()),
        "signal_baseline_maxdd_r": max_dd(seq.baseline_r.to_numpy(float)),
        "signal_overlay_maxdd_r": max_dd(seq.overlay_r.to_numpy(float)),
        "late_half_signals": int(len(late)),
        "late_half_baseline_ev_r": float(late.baseline_r.mean()) if len(late) else np.nan,
        "late_half_overlay_ev_r": float(late.overlay_r.mean()) if len(late) else np.nan,
    }


def coefficient_stability(coefs: pd.DataFrame):
    rows = []
    for (clock, feat), g in coefs.groupby(["clock", "feature"], sort=False):
        v = g.standardized_logit_coef.to_numpy(float)
        med = float(np.median(v))
        sign = 1.0 if med >= 0 else -1.0
        rows.append({
            "clock": clock,
            "feature": feat,
            "folds": int(len(v)),
            "coef_median": med,
            "coef_mean": float(np.mean(v)),
            "coef_abs_median": float(np.median(np.abs(v))),
            "same_sign_as_median_pct": float(np.mean(np.sign(v) == sign) * 100.0),
        })
    return pd.DataFrame(rows).sort_values(["clock", "coef_abs_median"], ascending=[True, False])


def summarize_clock(oof, folds, amp_seq):
    m = overlay_metrics(oof, amp_seq)
    m["folds"] = int(folds.shape[0])
    m["evaluable_auc_folds"] = int(folds.test_auc.notna().sum())
    m["fold_auc_mean"] = float(folds.test_auc.dropna().mean()) if folds.test_auc.notna().any() else np.nan
    return m


def main():
    pop, amp_seq = load_population()
    if len(pop) != EXPECTED_FILLS:
        raise SystemExit(f"Expected {EXPECTED_FILLS} accepted corrected AMP fills, got {len(pop)}")

    gc_bars = load_gc_bars()
    gc_raw = load_gc_raw_prefix()
    xau = load_xau_ticks()
    feat = build_feature_table(pop, gc_bars, gc_raw, xau)
    feat.to_csv(OUT_FEATURES, index=False)

    univ = univariate_table(feat)
    univ.to_csv(OUT_UNIV, index=False)

    p_oof, p_coef, p_folds = walkforward(feat, PRIMARY_FEATURES, "ORDER_START_DEPLOYABLE")
    f_oof, f_coef, f_folds = walkforward(feat, FILLTIME_FEATURES, "FILL_TIME_DIAGNOSTIC")
    all_oof = pd.concat([p_oof, f_oof], ignore_index=True)
    all_oof.to_csv(OUT_OOF, index=False)
    all_coef_raw = pd.concat([p_coef, f_coef], ignore_index=True)
    stab = coefficient_stability(all_coef_raw)
    stab.to_csv(OUT_COEF, index=False)

    primary = summarize_clock(p_oof, p_folds, amp_seq)
    filldiag = summarize_clock(f_oof, f_folds, amp_seq)

    gates = {
        "oof_sl_auc_ge_0_60": bool(primary["oof_auc_sl"] >= 0.60),
        "oof_veto_share_10_to_40pct": bool(0.10 <= primary["veto_share"] <= 0.40),
        "veto_sl_enrichment_ge_1_25x": bool(np.isfinite(primary["veto_sl_enrichment_x"]) and primary["veto_sl_enrichment_x"] >= 1.25),
        "overlay_sum_r_gt_baseline": bool(primary["signal_overlay_sum_r"] > primary["signal_baseline_sum_r"]),
        "overlay_ev_signal_gt_baseline": bool(primary["signal_overlay_ev_r"] > primary["signal_baseline_ev_r"]),
        "late_half_overlay_ev_signal_pos": bool(primary["late_half_overlay_ev_r"] > 0),
        "walkforward_evidence_sufficient": bool(primary["evaluable_auc_folds"] >= 3 or (primary["oof_fills"] >= 40 and p_oof.sl_label.nunique() == 2)),
    }
    passed = all(gates.values())
    status = "HISTORICAL_FAILURE_DISCRIMINATOR_CANDIDATE_PASS_NOT_OOS" if passed else "HISTORICAL_FAILURE_DISCRIMINATOR_FAIL_NOT_OOS"

    top = univ.head(10).replace({np.nan: None}).to_dict("records")
    result = {
        "lab": "GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015",
        "status": status,
        "population": {
            "accepted_corrected_amp_fills": int(len(feat)),
            "sl": int(feat.sl_label.sum()),
            "non_sl": int((1 - feat.sl_label).sum()),
            "negative_net": int(feat.negative_net_label.sum()),
            "first_signal": str(feat.signal_time_utc.iloc[0]),
            "last_signal": str(feat.signal_time_utc.iloc[-1]),
        },
        "primary_clock": "ORDER_START_DEPLOYABLE",
        "primary_features": PRIMARY_FEATURES,
        "filltime_diagnostic_features": FILLTIME_FEATURES,
        "primary": primary,
        "filltime_diagnostic": filldiag,
        "gates": gates,
        "top_univariate": top,
        "governance": {
            "new_market_data": False,
            "independent_oos": False,
            "threshold_search": False,
            "feature_subset_search": False,
            "primary_deployable_at_order_start": True,
            "filltime_model_deployable_as_resting_limit_veto": False,
            "reclaimed_signals_simulated": False,
        },
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    def pct(x): return "NA" if x is None or not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x, d=3): return "NA" if x is None or not np.isfinite(x) else f"{x:+.{d}f}"

    lines = [
        "# GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015",
        "",
        f"**Status: {status}**",
        "",
        "Historical bounded discovery on already-collected data only. Primary model uses only information available when the XAU limit becomes actionable.",
        "",
        "## Population",
        "",
        f"- Corrected AMP accepted fills: **{len(feat)}**",
        f"- SL: **{int(feat.sl_label.sum())}**; non-SL: **{int((1-feat.sl_label).sum())}**; negative-net: **{int(feat.negative_net_label.sum())}**",
        "",
        "## Walk-forward result",
        "",
        "| Clock | OOF fills | SL AUC | Veto | Veto SL rate | Enrichment | Baseline EV/signal | Overlay EV/signal | Baseline SumR | Overlay SumR | MaxDD baseline→overlay | Late overlay EV |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, s in [("ORDER_START_DEPLOYABLE", primary), ("FILL_TIME_DIAGNOSTIC", filldiag)]:
        lines.append(
            f"| {name} | {s['oof_fills']} | {s['oof_auc_sl']:.3f} | {pct(s['veto_share'])} | {pct(s['veto_sl_rate'])} | {s['veto_sl_enrichment_x']:.2f}x | {num(s['signal_baseline_ev_r'])} | {num(s['signal_overlay_ev_r'])} | {num(s['signal_baseline_sum_r'],2)} | {num(s['signal_overlay_sum_r'],2)} | {s['signal_baseline_maxdd_r']:.2f}→{s['signal_overlay_maxdd_r']:.2f}R | {num(s['late_half_overlay_ev_r'])} |"
        )
    lines += ["", "## Primary gates", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")

    lines += ["", "## Strongest descriptive single features", "", "| Feature | Clock | AUC* | SL median | non-SL median | Failure side |", "|---|---|---:|---:|---:|---|"]
    for r in univ.head(8).itertuples(index=False):
        lines.append(f"| {r.feature} | {r.clock} | {r.auc_directionless:.3f} | {r.sl_median:.4g} | {r.non_sl_median:.4g} | {r.failure_direction} |")
    lines += [
        "",
        "`AUC*` is directionless descriptive AUC on the full historical population and is not OOF evidence.",
        "",
        "## Governance",
        "",
        "The fill-time model is diagnostic only: a resting limit would already be filled at touch. A strong fill-time result can justify a later cancel/trigger redesign, not a direct filter. The LAB015 veto overlay is conservative and does not reclaim signals freed by vetoed trades; any candidate must be re-simulated with full state transitions before EA changes.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "primary": primary, "filltime": filldiag, "gates": gates}, indent=2))


if __name__ == "__main__":
    main()
