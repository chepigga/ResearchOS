#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path
import numpy as np,pandas as pd

ROOT=Path('research/gc')
LAB4=ROOT/'gc_xau_large_move_reverse_precursor_discovery_lab004.py'
LAB2=ROOT/'gc_xau_micro_lead_lag_flow_burst_lab002.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_LARGE_MOVE_TAIL_PRECURSOR_AUDIT_LAB004B.json'
OUT_MD=ROOT/'GC_XAU_LARGE_MOVE_TAIL_PRECURSOR_AUDIT_LAB004B.md'
THRESHOLDS=(2.0,3.0)

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader;spec.loader.exec_module(m);return m

def main():
    l4=load(LAB4,'l4');l2=load(LAB2,'l2');lt=load(LT,'lt')
    work=ROOT/'_lab004b';work.mkdir(exist_ok=True)
    base=l2.load(l2.BASE,'base')
    az=work/'amp.zip'
    if not az.exists():base.download(base.AMP_URL,az)
    if base.sha(az)!=base.AMP_SHA:raise SystemExit('AMP SHA mismatch')
    gt=l2.read_amp_ticks(az);gatr=l2.m1_atr_map(gt)
    aligned={w:l2.causal_features(l2.aggregate_window(gt,w),w,gatr) for w in l4.WINDOWS}
    xt,xb,xa,_=lt.read_xau_ticks();xm1=lt.build_xau_m1(xt,xb,xa);xatr=lt.xau_atr_lookup(xm1)
    sec,mid=l4.build_xau_seconds(xt,xb,xa)
    out={}
    lines=['# GC_XAU_LARGE_MOVE_TAIL_PRECURSOR_AUDIT_LAB004B','','Tail event audit: +/-2 ATR and +/-3 ATR first passage within 5m.','','| Threshold | Period | N | Quiet | delta_flip ALL enrich | repeated ALL enrich | repeated QUIET enrich |','|---:|---|---:|---:|---:|---:|---:|']
    for th in THRESHOLDS:
        l4.MOVE_ATR=th
        events=l4.detect_large_moves(sec,mid,xatr)
        pres=[]
        for r in events.itertuples(index=False):
            z={'gc_event_ms':int(r.gc_event_ms),'event_utc':r.event_utc,'period':r.period,'direction':int(r.direction),'side':r.side,'quiet_start':bool(r.quiet_start)}
            z.update(l4.features_at(gt,gatr,aligned,int(r.gc_event_ms),int(r.direction)));pres.append(z)
        pre=pd.DataFrame(pres)
        ctr=l4.controls(events)
        cps=[]
        for r in ctr.itertuples(index=False):
            z=r._asdict();z.update(l4.features_at(gt,gatr,aligned,int(r.gc_event_ms),int(r.direction)));cps.append(z)
        cpre=pd.DataFrame(cps)
        sig=l4.summarize(events,pre,cpre)
        counts={}
        for p in ('TRAIN','VALID','POST_CHECK','FULL'):
            z=events if p=='FULL' else events[events.period==p]
            counts[p]={'n':int(len(z)),'quiet':int(z.quiet_start.sum()),'up':int((z.direction==1).sum()),'down':int((z.direction==-1).sum()),'median_time_s':float(z.time_to_1atr_ms.median()/1000) if len(z) else None}
        def enr(subset,p,signal):
            z=sig[(sig.subset==subset)&(sig.period==p)&(sig.signal==signal)]
            if not len(z):return None
            v=z.iloc[0].enrichment
            return None if pd.isna(v) else float(v)
        metrics={}
        for p in ('TRAIN','VALID','POST_CHECK'):
            metrics[p]={
                'delta_flip_all':enr('ALL',p,'delta_flip'),
                'repeated_all':enr('ALL',p,'repeated_failed_attack'),
                'repeated_quiet':enr('QUIET',p,'repeated_failed_attack'),
            }
            x=metrics[p]
            def f(v):return 'NA' if v is None or not np.isfinite(v) else f'{v:.2f}x'
            lines.append(f"| {th:.1f} ATR | {p} | {counts[p]['n']} | {counts[p]['quiet']} | {f(x['delta_flip_all'])} | {f(x['repeated_all'])} | {f(x['repeated_quiet'])} |")
        out[str(th)]={'counts':counts,'key_enrichment':metrics}
    OUT_JSON.write_text(json.dumps({'lab':'GC_XAU_LARGE_MOVE_TAIL_PRECURSOR_AUDIT_LAB004B','results':out},indent=2),encoding='utf-8')
    lines+=['','No threshold winner selected. No execution optimization.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())
if __name__=='__main__':main()
