#!/usr/bin/env python3
"""LAB005 — post-10m residual edge audit for frozen LAB003 Chris/AEIF SHORT events.

No signal retuning, no threshold sweep, no XAU execution tuning.
Checkpoint state is frozen at +10m; targets are residual returns after +10m only.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from scipy.stats import spearmanr

ROOT=Path("research/gc")
LAB004=ROOT/"gc_short_chris_aeif_delayed_resolution_path_lab_004.py"
OUT_JSON=ROOT/"GC_SHORT_CHRIS_AEIF_POST10_RESIDUAL_EDGE_LAB_005.json"
OUT_MD=ROOT/"GC_SHORT_CHRIS_AEIF_POST10_RESIDUAL_EDGE_LAB_005.md"
OUT_CSV=ROOT/"GC_SHORT_CHRIS_AEIF_POST10_RESIDUAL_EDGE_LAB_005_UNIVARIATE.csv"

FEATURES=("cp10_ret","cp10_cum_body","cp10_bear_frac","cp10_closepos","cp10_mfe","cp10_mae","cp10_dist_seed_close","cp10_dist_seed_high")
TARGETS=("resid_10_15_atr","resid_10_20_atr","resid_10_30_atr")
TRAIN_END=pd.Timestamp("2026-08-20T00:00:00Z")
VALID_END=pd.Timestamp("2026-09-06T22:00:00Z")
LATE_END=pd.Timestamp("2026-09-11T12:46:00Z")


def load_lab004():
    s=importlib.util.spec_from_file_location("lab004_mod",LAB004)
    m=importlib.util.module_from_spec(s); assert s and s.loader; s.loader.exec_module(m); return m

def period(ts):
    if ts<TRAIN_END:return "TRAIN"
    if ts<VALID_END:return "VALID"
    if ts<=LATE_END:return "LATE_CHECK"
    return "POST_CHECK"

def add_residuals(ft,bars):
    b=bars.reset_index(drop=True).copy(); b["time"]=pd.to_datetime(b.time,utc=True)
    idx={t:i for i,t in enumerate(b.time)}; out=[]
    for r in ft.itertuples(index=False):
        et=pd.Timestamp(r.entry_time); atr=float(r.seed_atr14)
        if et not in idx or not np.isfinite(atr) or atr<=0: continue
        ei=idx[et]; cp_i=ei+9
        if cp_i>=len(b) or b.iloc[cp_i].time!=et+pd.Timedelta(minutes=9): continue
        cp_close=float(b.iloc[cp_i].close)
        row=dict(r._asdict()); row["period"]=period(pd.Timestamp(r.seed_time))
        for end in (15,20,30):
            j=ei+end-1
            key=f"resid_10_{end}_atr"
            if j<len(b) and b.iloc[j].time==et+pd.Timedelta(minutes=end-1):
                row[key]=(cp_close-float(b.iloc[j].close))/atr
            else: row[key]=np.nan
        out.append(row)
    return pd.DataFrame(out)

def auc_fixed(y,x,orientation):
    m=np.isfinite(y)&np.isfinite(x); y=np.asarray(y)[m].astype(int); x=np.asarray(x)[m].astype(float)*orientation
    if len(y)<4 or len(np.unique(y))<2:return None,int((y==1).sum()),int((y==0).sum())
    return float(roc_auc_score(y,x)),int((y==1).sum()),int((y==0).sum())

def train_orientation(d,f,t):
    x=pd.to_numeric(d[f],errors="coerce").to_numpy(float); y=(pd.to_numeric(d[t],errors="coerce").to_numpy(float)>0).astype(int)
    m=np.isfinite(x)&np.isfinite(pd.to_numeric(d[t],errors="coerce").to_numpy(float)); x=x[m]; y=y[m]
    if len(y)<4 or len(np.unique(y))<2:return None
    a=float(roc_auc_score(y,x)); return 1 if a>=0.5 else -1

def main():
    m4=load_lab004(); m3=m4.load_lab003(); base=m3.load_base()
    work=ROOT/"_chris005_work"; work.mkdir(parents=True,exist_ok=True); rz=work/"rithmic.zip"; az=work/"amp.zip"
    if not rz.exists(): base.download(base.RITH_URL,rz)
    if not az.exists(): base.download(base.AMP_URL,az)
    if base.sha(rz)!=base.RITH_SHA or base.sha(az)!=base.AMP_SHA: raise SystemExit("source SHA mismatch")
    rb=base.load_rithmic(rz); ab=base.load_amp(az)
    re=m3.build_events(rb); ae=m3.build_events(ab)
    rft=add_residuals(m4.add_path_features(re,rb),rb); aft=add_residuals(m4.add_path_features(ae,ab),ab)
    ft=pd.concat([rft,aft],ignore_index=True)
    rows=[]; passes=[]
    rfeed="RITHMIC_RAW"; afeed="AMP_CQG_RAW_EXCLUSIVE"
    for f in FEATURES:
      for t in TARGETS:
        tr=ft[(ft.feed==rfeed)&(ft.period=="TRAIN")]
        orient=train_orientation(tr,f,t)
        if orient is None: continue
        rec={"feature":f,"target":t,"orientation":orient}
        ok=True
        for feed,label in ((rfeed,"rith"),(afeed,"amp")):
          for p in ("VALID","FULL"):
            d=ft[ft.feed.eq(feed)] if p=="FULL" else ft[ft.feed.eq(feed)&ft.period.eq(p)]
            xv=pd.to_numeric(d[f],errors="coerce").to_numpy(float); rv=pd.to_numeric(d[t],errors="coerce").to_numpy(float)
            y=(rv>0).astype(int)
            auc,w,l=auc_fixed(y,xv,orient)
            rec[f"{label}_{p.lower()}_auc"]=auc; rec[f"{label}_{p.lower()}_winners"]=w; rec[f"{label}_{p.lower()}_losers"]=l
            mm=np.isfinite(xv)&np.isfinite(rv)
            rho=None
            if mm.sum()>=4 and np.std(xv[mm])>0 and np.std(rv[mm])>0: rho=float(spearmanr(xv[mm]*orient,rv[mm]).correlation)
            rec[f"{label}_{p.lower()}_rho"]=rho
        gate=(rec.get("rith_valid_auc") is not None and rec.get("amp_valid_auc") is not None and rec.get("rith_full_auc") is not None and rec.get("amp_full_auc") is not None and rec["rith_valid_auc"]>=.65 and rec["amp_valid_auc"]>=.65 and rec["rith_full_auc"]>=.60 and rec["amp_full_auc"]>=.60 and rec["rith_valid_winners"]>=3 and rec["rith_valid_losers"]>=3 and rec["amp_valid_winners"]>=3 and rec["amp_valid_losers"]>=3)
        rec["gate_pass"]=bool(gate); rows.append(rec)
        if gate: passes.append(rec)
    pd.DataFrame(rows).to_csv(OUT_CSV,index=False)
    status="HISTORICAL_POST10_RESIDUAL_EDGE_SIGNAL_NOT_OOS" if passes else "HISTORICAL_POST10_RESIDUAL_EDGE_FAIL_NOT_OOS"
    result={"status":status,"event_counts":{str(k):int(v) for k,v in ft.groupby("feed").size().items()},"passing_features":passes,"all_tests":rows}
    OUT_JSON.write_text(json.dumps(result,indent=2),encoding="utf-8")
    lines=["# GC SHORT CHRIS/AEIF POST10 RESIDUAL EDGE LAB005","",f"**Status:** `{status}`","","Frozen LAB003 event set. Checkpoint = +10m. Targets are residual returns after +10m only.","","## Passing preregistered residual features",""]
    if passes:
      lines += ["| Feature | Residual | Orient | Rith VALID | AMP VALID | Rith FULL | AMP FULL |","|---|---|---:|---:|---:|---:|---:|"]
      for r in passes: lines.append(f"| {r['feature']} | {r['target']} | {r['orientation']:+d} | {r['rith_valid_auc']:.3f} | {r['amp_valid_auc']:.3f} | {r['rith_full_auc']:.3f} | {r['amp_full_auc']:.3f} |")
      lines += ["","## Decision","","A genuine post-10m residual signal exists historically. Do NOT trade it yet. Next step: preregister a walk-forward decision-gate using only the passing feature/horizon family."]
    else:
      lines += ["No feature passed the frozen cross-feed residual gate.","","## Decision","","LAB004 cp10 strength was mainly descriptive of movement already realized by +10m. Do not convert it into a trading gate."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(status); print(json.dumps(passes,indent=2))

if __name__=="__main__": main()
