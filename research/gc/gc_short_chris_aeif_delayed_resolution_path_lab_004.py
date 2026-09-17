#!/usr/bin/env python3
"""LAB004 — causal delayed-resolution path audit for frozen LAB003 Chris/AEIF SHORT events.

No signal retuning, no threshold sweep, no XAU execution tuning.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from scipy.stats import spearmanr

ROOT = Path("research/gc")
LAB003 = ROOT / "gc_short_chris_aeif_buy_failure_lab_003.py"
OUT_JSON = ROOT / "GC_SHORT_CHRIS_AEIF_DELAYED_RESOLUTION_PATH_LAB_004.json"
OUT_MD = ROOT / "GC_SHORT_CHRIS_AEIF_DELAYED_RESOLUTION_PATH_LAB_004.md"
OUT_FEATURES = ROOT / "GC_SHORT_CHRIS_AEIF_DELAYED_RESOLUTION_PATH_LAB_004_FEATURES.csv"
OUT_UNIV = ROOT / "GC_SHORT_CHRIS_AEIF_DELAYED_RESOLUTION_PATH_LAB_004_UNIVARIATE.csv"

CHECKPOINTS = (1, 3, 5, 10)
TARGETS = ("winner15", "winner30")
CONT_TARGETS = ("fwd_15m_atr", "fwd_30m_atr")
TRAIN_END = pd.Timestamp("2026-08-20T00:00:00Z")
VALID_END = pd.Timestamp("2026-09-06T22:00:00Z")
LATE_END = pd.Timestamp("2026-09-11T12:46:00Z")


def load_lab003():
    spec = importlib.util.spec_from_file_location("lab003_mod", LAB003)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def period_name(ts: pd.Timestamp) -> str:
    if ts < TRAIN_END: return "TRAIN"
    if ts < VALID_END: return "VALID"
    if ts <= LATE_END: return "LATE_CHECK"
    return "POST_CHECK"


def add_path_features(events: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    b = bars.reset_index(drop=True).copy()
    b["time"] = pd.to_datetime(b.time, utc=True)
    idx_by_time = {t: i for i, t in enumerate(b.time)}
    rows = []
    for r in events.itertuples(index=False):
        entry_time = pd.Timestamp(r.entry_time)
        if entry_time not in idx_by_time:
            continue
        ei = idx_by_time[entry_time]
        atr = float(r.seed_atr14)
        if not np.isfinite(atr) or atr <= 0:
            continue
        row = dict(r._asdict())
        row["period"] = period_name(pd.Timestamp(r.seed_time))
        row["winner15"] = int(float(r.fwd_15m_atr) > 0) if np.isfinite(float(r.fwd_15m_atr)) else np.nan
        row["winner30"] = int(float(r.fwd_30m_atr) > 0) if np.isfinite(float(r.fwd_30m_atr)) else np.nan
        entry = float(r.entry)
        seed_high = np.nan
        seed_close = np.nan
        seed_time = pd.Timestamp(r.seed_time)
        if seed_time in idx_by_time:
            sr = b.iloc[idx_by_time[seed_time]]
            seed_high = float(sr.high); seed_close = float(sr.close)
        for cp in CHECKPOINTS:
            end_i = ei + cp - 1
            if end_i >= len(b) or b.iloc[end_i].time != entry_time + pd.Timedelta(minutes=cp-1):
                for nm in ("ret","mfe","mae","closepos","bear_frac","cum_body","dist_seed_high","dist_seed_close"):
                    row[f"cp{cp}_{nm}"] = np.nan
                continue
            w = b.iloc[ei:end_i+1]
            close = float(w.iloc[-1].close)
            low = float(w.low.min()); high = float(w.high.max())
            rng = high-low
            row[f"cp{cp}_ret"] = (entry-close)/atr
            row[f"cp{cp}_mfe"] = (entry-low)/atr
            row[f"cp{cp}_mae"] = (high-entry)/atr
            # for SHORT, high closepos means close nearer high = worse; low means nearer low = better
            row[f"cp{cp}_closepos"] = ((close-low)/rng) if rng > 0 else 0.5
            row[f"cp{cp}_bear_frac"] = float((w.close < w.open).mean())
            row[f"cp{cp}_cum_body"] = float(((w.open-w.close).sum())/atr)  # positive = bearish cumulative body
            row[f"cp{cp}_dist_seed_high"] = (seed_high-close)/atr if np.isfinite(seed_high) else np.nan
            row[f"cp{cp}_dist_seed_close"] = (seed_close-close)/atr if np.isfinite(seed_close) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def safe_auc(y, x):
    m = np.isfinite(y) & np.isfinite(x)
    y2 = np.asarray(y)[m].astype(int); x2 = np.asarray(x)[m].astype(float)
    if len(y2) < 4 or len(np.unique(y2)) < 2:
        return None, None, len(y2)
    auc = float(roc_auc_score(y2, x2))
    if auc >= 0.5:
        return auc, 1, len(y2)
    return 1.0-auc, -1, len(y2)


def median_sep(y, x, orient):
    m = np.isfinite(y) & np.isfinite(x)
    y2 = np.asarray(y)[m].astype(int); x2 = np.asarray(x)[m].astype(float)
    if len(y2) == 0 or not np.any(y2==1) or not np.any(y2==0): return None, None, None
    mw = float(np.median(x2[y2==1])); ml = float(np.median(x2[y2==0]))
    sep = (mw-ml) * orient
    return mw, ml, float(sep)


def univariate(ft: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [c for c in ft.columns if c.startswith("cp")]
    rows=[]
    for feed in sorted(ft.feed.unique()):
        for period in ("TRAIN","VALID","LATE_CHECK","POST_CHECK","FULL"):
            d = ft[ft.feed.eq(feed)] if period=="FULL" else ft[ft.feed.eq(feed)&ft.period.eq(period)]
            for f in feature_cols:
                x = pd.to_numeric(d[f], errors="coerce").to_numpy(float)
                for targ in TARGETS:
                    y = pd.to_numeric(d[targ], errors="coerce").to_numpy(float)
                    auc, orient, n = safe_auc(y,x)
                    mw, ml, sep = (None,None,None) if orient is None else median_sep(y,x,orient)
                    rows.append({"feed":feed,"period":period,"feature":f,"target":targ,"n":n,"dir_auc":auc,"orientation":orient,"winner_median":mw,"loser_median":ml,"oriented_median_sep":sep})
                for targ in CONT_TARGETS:
                    y = pd.to_numeric(d[targ], errors="coerce").to_numpy(float)
                    m = np.isfinite(y)&np.isfinite(x)
                    rho = None
                    if m.sum() >= 4 and np.std(x[m])>0 and np.std(y[m])>0:
                        rho=float(spearmanr(x[m],y[m]).correlation)
                    rows.append({"feed":feed,"period":period,"feature":f,"target":targ,"n":int(m.sum()),"spearman":rho})
    return pd.DataFrame(rows)


def evidence_candidates(u: pd.DataFrame):
    cands=[]
    rfeed="RITHMIC_RAW"; afeed="AMP_CQG_RAW_EXCLUSIVE"
    features=sorted(u.feature.unique())
    for f in features:
        for targ in TARGETS:
            rv=u[(u.feed==rfeed)&(u.period=="VALID")&(u.feature==f)&(u.target==targ)]
            av=u[(u.feed==afeed)&(u.period=="VALID")&(u.feature==f)&(u.target==targ)]
            rf=u[(u.feed==rfeed)&(u.period=="FULL")&(u.feature==f)&(u.target==targ)]
            af=u[(u.feed==afeed)&(u.period=="FULL")&(u.feature==f)&(u.target==targ)]
            if min(len(rv),len(av),len(rf),len(af)) == 0: continue
            rv, av, rf, af = rv.iloc[0], av.iloc[0], rf.iloc[0], af.iloc[0]
            vals=[rv.dir_auc,av.dir_auc,rv.orientation,av.orientation,rf.orientation,af.orientation,rv.oriented_median_sep,av.oriented_median_sep]
            if any(pd.isna(v) for v in vals): continue
            passed=(rv.n>=8 and av.n>=8 and rv.dir_auc>=0.65 and av.dir_auc>=0.65 and rv.orientation==av.orientation and rf.orientation==rv.orientation and af.orientation==rv.orientation and rv.oriented_median_sep>0 and av.oriented_median_sep>0)
            if passed:
                cands.append({"feature":f,"target":targ,"rith_valid_auc":float(rv.dir_auc),"amp_valid_auc":float(av.dir_auc),"orientation":int(rv.orientation),"rith_full_auc":float(rf.dir_auc),"amp_full_auc":float(af.dir_auc)})
    return cands


def main():
    m = load_lab003()
    work=ROOT/"_chris004_work"; work.mkdir(parents=True,exist_ok=True)
    rz=work/"rithmic.zip"; az=work/"amp.zip"
    if not rz.exists(): m.load_base().download(m.load_base().RITH_URL,rz)
    if not az.exists(): m.load_base().download(m.load_base().AMP_URL,az)
    base=m.load_base()
    if base.sha(rz)!=base.RITH_SHA or base.sha(az)!=base.AMP_SHA: raise SystemExit("source SHA mismatch")
    rb=base.load_rithmic(rz); ab=base.load_amp(az)
    re=m.build_events(rb); ae=m.build_events(ab)
    rft=add_path_features(re,rb); aft=add_path_features(ae,ab)
    ft=pd.concat([rft,aft],ignore_index=True)
    ft.to_csv(OUT_FEATURES,index=False)
    u=univariate(ft); u.to_csv(OUT_UNIV,index=False)
    cands=evidence_candidates(u)
    status="HISTORICAL_DELAYED_RESOLUTION_PATH_SIGNAL_NOT_OOS" if cands else "HISTORICAL_DELAYED_RESOLUTION_PATH_INCONCLUSIVE_NOT_OOS"
    result={"status":status,"event_counts":{str(k):int(v) for k,v in ft.groupby("feed").size().items()},"evidence_candidates":cands}
    OUT_JSON.write_text(json.dumps(result,indent=2),encoding="utf-8")
    lines=["# GC SHORT CHRIS/AEIF DELAYED RESOLUTION PATH LAB004","",f"**Status:** `{status}`","","Frozen LAB003 event set; no signal retuning and no trading overlay.","", "## Evidence-gate candidates",""]
    if cands:
        lines.append("| Feature | Target | Rith VALID AUC | AMP VALID AUC | Orientation | Rith FULL AUC | AMP FULL AUC |")
        lines.append("|---|---|---:|---:|---:|---:|---:|")
        for c in cands:
            lines.append(f"| {c['feature']} | {c['target']} | {c['rith_valid_auc']:.3f} | {c['amp_valid_auc']:.3f} | {c['orientation']:+d} | {c['rith_full_auc']:.3f} | {c['amp_full_auc']:.3f} |")
    else:
        lines.append("No feature/checkpoint combination passed the preregistered cross-feed evidence gate.")
    lines += ["", "## Decision", ""]
    if cands:
        lines.append("A causal delayed-resolution path signal exists descriptively. Do NOT trade it yet; preregister a walk-forward decision-gate LAB005 using only the identified feature/checkpoint family.")
    else:
        lines.append("Path shape is not sufficiently stable cross-feed to justify a decision gate. Do not threshold-mine LAB004 post hoc.")
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(status)
    print(json.dumps(cands,indent=2))

if __name__=="__main__": main()
