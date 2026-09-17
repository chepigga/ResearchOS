#!/usr/bin/env python3
"""LAB006 — causal walk-forward Q50 gate on LAB005 cp10_dist_seed_high.

Frozen: LAB003 signal, +10m checkpoint, feature family and Q50 expanding-history gate.
No threshold sweep, no XAU execution tuning.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path("research/gc")
LAB005=ROOT/"gc_short_chris_aeif_post10_residual_edge_lab_005.py"
OUT_JSON=ROOT/"GC_SHORT_CHRIS_AEIF_POST10_DISTANCE_GATE_WALKFORWARD_LAB_006.json"
OUT_MD=ROOT/"GC_SHORT_CHRIS_AEIF_POST10_DISTANCE_GATE_WALKFORWARD_LAB_006.md"
OUT_OOF=ROOT/"GC_SHORT_CHRIS_AEIF_POST10_DISTANCE_GATE_WALKFORWARD_LAB_006_OOF.csv"

FEATURE="cp10_dist_seed_high"
PRIMARY="resid_10_20_atr"
SECONDARY="resid_10_30_atr"
MIN_HISTORY=8


def load_lab005():
    s=importlib.util.spec_from_file_location("lab005_mod",LAB005)
    m=importlib.util.module_from_spec(s); assert s and s.loader; s.loader.exec_module(m); return m


def build_dataset():
    m5=load_lab005(); m4=m5.load_lab004(); m3=m4.load_lab003(); base=m3.load_base()
    work=ROOT/"_chris006_work"; work.mkdir(parents=True,exist_ok=True)
    rz=work/"rithmic.zip"; az=work/"amp.zip"
    if not rz.exists(): base.download(base.RITH_URL,rz)
    if not az.exists(): base.download(base.AMP_URL,az)
    if base.sha(rz)!=base.RITH_SHA or base.sha(az)!=base.AMP_SHA: raise SystemExit("source SHA mismatch")
    rb=base.load_rithmic(rz); ab=base.load_amp(az)
    re=m3.build_events(rb); ae=m3.build_events(ab)
    rft=m5.add_residuals(m4.add_path_features(re,rb),rb)
    aft=m5.add_residuals(m4.add_path_features(ae,ab),ab)
    return pd.concat([rft,aft],ignore_index=True)


def walkforward_feed(d: pd.DataFrame) -> pd.DataFrame:
    d=d.copy()
    d["entry_time"]=pd.to_datetime(d.entry_time,utc=True)
    d=d.sort_values("entry_time").reset_index(drop=True)
    rows=[]
    history=[]
    for r in d.itertuples(index=False):
        x=float(getattr(r,FEATURE)) if np.isfinite(float(getattr(r,FEATURE))) else np.nan
        p=float(getattr(r,PRIMARY)) if np.isfinite(float(getattr(r,PRIMARY))) else np.nan
        s=float(getattr(r,SECONDARY)) if np.isfinite(float(getattr(r,SECONDARY))) else np.nan
        eligible=np.isfinite(x) and np.isfinite(p) and np.isfinite(s)
        if eligible and len(history)>=MIN_HISTORY:
            thr=float(np.median(history))
            selected=bool(x>=thr)
            rows.append({
                "feed":r.feed,"seed_time":r.seed_time,"entry_time":r.entry_time,
                FEATURE:x,"threshold_q50":thr,"selected":selected,
                PRIMARY:p,SECONDARY:s,"prior_history_n":len(history)
            })
        if eligible:
            history.append(x)
    return pd.DataFrame(rows)


def stats(d: pd.DataFrame, target: str):
    if len(d)==0:
        return {"n":0,"selected_n":0,"selection_share":None,"baseline_ev":None,"selected_ev":None,"rejected_ev":None,"uplift":None,"selected_wr":None}
    vals=d[target].to_numpy(float); sel=d.selected.to_numpy(bool)
    base=float(np.mean(vals))
    sv=vals[sel]; rv=vals[~sel]
    sev=float(np.mean(sv)) if len(sv) else None
    rev=float(np.mean(rv)) if len(rv) else None
    return {
        "n":int(len(d)),
        "selected_n":int(sel.sum()),
        "selection_share":float(sel.mean()),
        "baseline_ev":base,
        "selected_ev":sev,
        "rejected_ev":rev,
        "uplift":None if sev is None else float(sev-base),
        "selected_wr":None if not len(sv) else float((sv>0).mean())
    }


def main():
    ft=build_dataset()
    parts=[]
    for feed in sorted(ft.feed.unique()):
        parts.append(walkforward_feed(ft[ft.feed.eq(feed)]))
    oof=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    oof.to_csv(OUT_OOF,index=False)

    feeds={}
    for feed in sorted(oof.feed.unique()):
        d=oof[oof.feed.eq(feed)].copy()
        feeds[feed]={PRIMARY:stats(d,PRIMARY),SECONDARY:stats(d,SECONDARY)}

    r=feeds.get("RITHMIC_RAW",{}).get(PRIMARY,{})
    a=feeds.get("AMP_CQG_RAW_EXCLUSIVE",{}).get(PRIMARY,{})
    r2=feeds.get("RITHMIC_RAW",{}).get(SECONDARY,{})
    a2=feeds.get("AMP_CQG_RAW_EXCLUSIVE",{}).get(SECONDARY,{})
    checks={
        "rith_oof_n_ge12":r.get("n",0)>=12,
        "amp_oof_n_ge12":a.get("n",0)>=12,
        "rith_selection_25_75":r.get("selection_share") is not None and .25<=r["selection_share"]<=.75,
        "amp_selection_25_75":a.get("selection_share") is not None and .25<=a["selection_share"]<=.75,
        "rith_selected_ev_pos":r.get("selected_ev") is not None and r["selected_ev"]>0,
        "amp_selected_ev_pos":a.get("selected_ev") is not None and a["selected_ev"]>0,
        "rith_selected_gt_baseline":r.get("selected_ev") is not None and r.get("baseline_ev") is not None and r["selected_ev"]>r["baseline_ev"],
        "amp_selected_gt_baseline":a.get("selected_ev") is not None and a.get("baseline_ev") is not None and a["selected_ev"]>a["baseline_ev"],
        "rith_uplift_ge010":r.get("uplift") is not None and r["uplift"]>=.10,
        "amp_uplift_ge010":a.get("uplift") is not None and a["uplift"]>=.10,
        "rith_selected_wr_ge55":r.get("selected_wr") is not None and r["selected_wr"]>=.55,
        "amp_selected_wr_ge55":a.get("selected_wr") is not None and a["selected_wr"]>=.55,
        "rith_secondary_nonneg":r2.get("selected_ev") is not None and r2["selected_ev"]>=0,
        "amp_secondary_nonneg":a2.get("selected_ev") is not None and a2["selected_ev"]>=0,
    }
    checks["pass"]=all(checks.values())
    status="HISTORICAL_POST10_DISTANCE_GATE_WALKFORWARD_PASS_NOT_OOS" if checks["pass"] else "HISTORICAL_POST10_DISTANCE_GATE_WALKFORWARD_FAIL_NOT_OOS"
    result={"status":status,"feature":FEATURE,"threshold_rule":"expanding prior-event Q50 after min history 8","primary":PRIMARY,"secondary":SECONDARY,"feeds":feeds,"gates":checks}
    OUT_JSON.write_text(json.dumps(result,indent=2),encoding="utf-8")

    lines=["# GC SHORT CHRIS/AEIF POST10 DISTANCE GATE WALKFORWARD LAB006","",f"**Status:** `{status}`","",f"Feature: `{FEATURE}`; gate: expanding prior-event Q50 after {MIN_HISTORY} historical events.","", "## OOF results","", "| Feed | Target | N | Selected | Share | Baseline EV | Selected EV | Rejected EV | Uplift | Selected WR |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for feed,dd in feeds.items():
        for target in (PRIMARY,SECONDARY):
            s=dd[target]
            fmt=lambda x:"NA" if x is None else f"{x:+.4f}"
            pct=lambda x:"NA" if x is None else f"{100*x:.1f}%"
            lines.append(f"| {feed} | {target} | {s['n']} | {s['selected_n']} | {pct(s['selection_share'])} | {fmt(s['baseline_ev'])} | {fmt(s['selected_ev'])} | {fmt(s['rejected_ev'])} | {fmt(s['uplift'])} | {pct(s['selected_wr'])} |")
    lines += ["","## Frozen gates",""]
    for k,v in checks.items():
        if k!="pass": lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["","## Decision",""]
    if checks["pass"]:
        lines.append("This exact historical GC walk-forward gate passes. It may advance to a separate GC->XAU transfer/execution study, but it is not OOS and not demo/live ready.")
    else:
        lines.append("Reject this exact Q50 walk-forward gate. Do not sweep alternative quantiles post hoc on this dataset.")
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(status); print(json.dumps(result,indent=2))

if __name__=="__main__": main()
