#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path
import numpy as np,pandas as pd

ROOT=Path('research/gc')
EVENTS=ROOT/'GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002_EVENTS.csv'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002A.json'
OUT_MD=ROOT/'GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002A.md'
HMS=(250,500,1000,2000,3000,5000,10000,30000,60000)
THR_ATR=.05
STALE_MS=2000

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader;spec.loader.exec_module(m);return m
def first_idx(t,target):
    i=int(np.searchsorted(t,target,side='left'))
    if i>=len(t):return None
    if t[i]-target>STALE_MS:return None
    return i

def summarize(d):
    out={}
    for ms in HMS:
        c=f'mid_{ms}ms_atr';v=d[c].dropna().to_numpy(float)
        out[str(ms)]={'n':int(len(v)),'ev':float(v.mean()) if len(v) else None,'median':float(np.median(v)) if len(v) else None,'wr':float((v>0).mean()*100) if len(v) else None}
    fp=d[d.fp_hit.isin(['PRED','OPP'])].copy()
    out['first_passage']={'n_hit':int(len(fp)),'pred_first_share':float((fp.fp_hit=='PRED').mean()) if len(fp) else None,'median_pred_ms':float(d.loc[d.fp_hit=='PRED','fp_ms'].median()) if (d.fp_hit=='PRED').any() else None}
    return out

def main():
    if not EVENTS.exists():raise SystemExit('missing LAB002 events')
    ev=pd.read_csv(EVENTS)
    lt=load(LT,'lt');t,b,a,_=lt.read_xau_ticks();mid=(b+a)/2.0
    rows=[]
    for r in ev.itertuples(index=False):
        broker_end=int(r.gc_end_ms)+180*60000
        i=first_idx(t,broker_end)
        if i is None:continue
        m0=float(mid[i]);atr=float(r.xau_atr);d=int(r.direction)
        rec=r._asdict()
        for ms in HMS:
            j=first_idx(t,broker_end+ms)
            rec[f'mid_{ms}ms_atr']=np.nan if j is None else d*(float(mid[j])-m0)/atr
        end=first_idx(t,broker_end+60000)
        fp='NONE';fpms=np.nan
        if end is not None:
            pred=m0+d*THR_ATR*atr;opp=m0-d*THR_ATR*atr
            for j in range(i,end+1):
                x=float(mid[j])
                if (d>0 and x>=pred) or (d<0 and x<=pred):
                    fp='PRED';fpms=int(t[j]-broker_end);break
                if (d>0 and x<=opp) or (d<0 and x>=opp):
                    fp='OPP';fpms=int(t[j]-broker_end);break
        rec['fp_hit']=fp;rec['fp_ms']=fpms;rows.append(rec)
    z=pd.DataFrame(rows)
    result={}
    for w in sorted(z.window_s.unique()):
        for mech in sorted(z.mechanism.unique()):
            k=f'{int(w)}s_{mech}';d=z[(z.window_s==w)&(z.mechanism==mech)]
            result[k]={p:summarize(d if p=='FULL' else d[d.period==p]) for p in ['TRAIN','VALID','POST_CHECK','FULL']}
    OUT_JSON.write_text(json.dumps({'lab':'GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002A','results':result},indent=2),encoding='utf-8')
    def f(x):return 'NA' if x is None else f'{x:+.3f}'
    lines=['# GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002A','','Mid-price information timing diagnostic; frozen LAB002 events.','',
           '| Candidate | Tr1s | Tr5s | Va1s | Va5s | Va30s | Va pred-first | Post5s |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for k,v in result.items():
        tr=v['TRAIN'];va=v['VALID'];po=v['POST_CHECK'];pf=va['first_passage']['pred_first_share']
        lines.append(f"| {k} | {f(tr['1000']['ev'])} | {f(tr['5000']['ev'])} | {f(va['1000']['ev'])} | {f(va['5000']['ev'])} | {f(va['30000']['ev'])} | {'NA' if pf is None else f'{pf*100:.1f}%'} | {f(po['5000']['ev'])} |")
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(OUT_MD.read_text())
if __name__=='__main__':main()
