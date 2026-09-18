#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
LAB2=ROOT/'gc_xau_micro_lead_lag_flow_burst_lab002.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_CROWDFade_DIRECTIONAL_BIAS_TRANSFER_LAB005.json'
OUT_MD=ROOT/'GC_XAU_CROWDFade_DIRECTIONAL_BIAS_TRANSFER_LAB005.md'
OUT_EVENTS=ROOT/'GC_XAU_CROWDFade_DIRECTIONAL_BIAS_TRANSFER_LAB005_EVENTS.csv'

TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
OFFSET=180
STALE_MS=2000
H=(60,180,300,600,900)
STATES=('ALL','DIVERGE_EARLY','CROWD_PERSISTS','REVERSAL_CONFIRM')

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    return m

def first_idx(t,target):
    i=int(np.searchsorted(t,target,side='left'))
    if i>=len(t) or t[i]-target>STALE_MS:
        return None
    return i

def period(ms):
    x=pd.to_datetime(ms,unit='ms',utc=True)
    return 'TRAIN' if x<TRAIN_END else ('VALID' if x<VALID_END else 'POST_CHECK')

def state_flags(r5,r10,r30):
    return {
        'ALL':True,
        'DIVERGE_EARLY': bool(r5>0 and r10>0),
        'CROWD_PERSISTS': bool(r5<0 and r10<0),
        'REVERSAL_CONFIRM': bool(r5<=0 and r30>0),
    }

def metric(z,h):
    c=f'bias_{h}s_atr'
    v=z[c].dropna().to_numpy(float)
    if len(v)==0:
        return {'n':0,'accuracy':None,'mean':None,'median':None,'mean_abs':None,'efficiency':None}
    mean=float(v.mean())
    ma=float(np.abs(v).mean())
    return {
        'n':int(len(v)),
        'accuracy':float((v>0).mean()),
        'mean':mean,
        'median':float(np.median(v)),
        'mean_abs':ma,
        'efficiency':float(mean/ma) if ma>0 else None
    }

def main():
    l2=load(LAB2,'l2'); lt=load(LT,'lt')
    work=ROOT/'_lab005bias'; work.mkdir(exist_ok=True)
    az=work/'amp.zip'
    base=l2.load(l2.BASE,'base')
    if not az.exists():
        base.download(base.AMP_URL,az)
    if base.sha(az)!=base.AMP_SHA:
        raise SystemExit('AMP SHA mismatch')

    gt=l2.read_amp_ticks(az)
    atrmap=l2.m1_atr_map(gt)
    gb=l2.causal_features(l2.aggregate_window(gt,30),30,atrmap)
    idxs=l2.select_events(gb,30,'FADE_STALL')

    t,b,a,_=lt.read_xau_ticks()
    mid=(b+a)/2.0
    xm1=lt.build_xau_m1(t,b,a)
    xatr=lt.xau_atr_lookup(xm1)

    rows=[]
    for idx,d in idxs:
        r=gb.iloc[idx]
        end_ms=int(r.end_ms)
        broker_end=end_ms+OFFSET*60000
        i0=first_idx(t,broker_end)
        if i0 is None: continue
        prev=((broker_end//60000)*60000)-60000
        atr=float(xatr.get(prev,np.nan))
        if not np.isfinite(atr) or atr<=0: continue
        m0=float(mid[i0])

        vals={}
        good=True
        for sec in (5,10,30):
            j=first_idx(t,broker_end+sec*1000)
            if j is None:
                good=False;break
            vals[sec]=d*(float(mid[j])-m0)/atr
        if not good: continue

        flags=state_flags(vals[5],vals[10],vals[30])

        path_end=first_idx(t,broker_end+900000)
        if path_end is None: continue
        p=mid[i0:path_end+1]
        pred=d*(p-m0)/atr
        mfe=float(np.nanmax(pred))
        mae=float(np.nanmin(pred))

        hit='NONE'; hit_ms=np.nan
        for j in range(i0,path_end+1):
            z=d*(float(mid[j])-m0)/atr
            if z>=0.25:
                hit='PRED'; hit_ms=int(t[j]-broker_end); break
            if z<=-0.25:
                hit='OPP'; hit_ms=int(t[j]-broker_end); break

        common={
            'gc_end_ms':end_ms,
            'gc_end_utc':pd.to_datetime(end_ms,unit='ms',utc=True).isoformat(),
            'period':period(end_ms),
            'direction':d,
            'side':'LONG' if d>0 else 'SHORT',
            'xau_atr':atr,
            'r5':vals[5],'r10':vals[10],'r30':vals[30],
            'mfe_15m_atr':mfe,'mae_15m_atr':mae,
            'first025_hit':hit,'first025_ms':hit_ms,
            'gc_delta_frac':float(r.delta_frac),
            'gc_volume':float(r.volume),
            'gc_impact':float(r.impact),
        }
        for sec in H:
            j=first_idx(t,broker_end+sec*1000)
            common[f'bias_{sec}s_atr']=np.nan if j is None else d*(float(mid[j])-m0)/atr

        for state,on in flags.items():
            if on:
                rec=dict(common);rec['state']=state;rows.append(rec)

    ev=pd.DataFrame(rows)
    ev.to_csv(OUT_EVENTS,index=False)

    result={}
    candidates=[]
    for state in STATES:
        result[state]={}
        for p in ('TRAIN','VALID','POST_CHECK','FULL'):
            z=ev[ev.state.eq(state)]
            if p!='FULL': z=z[z.period.eq(p)]
            result[state][p]={str(h):metric(z,h) for h in H}
            fp=z[z.first025_hit.isin(['PRED','OPP'])]
            result[state][p]['first025_pred_share']=float((fp.first025_hit=='PRED').mean()) if len(fp) else None
            result[state][p]['mfe_mean']=float(z.mfe_15m_atr.mean()) if len(z) else None
            result[state][p]['mae_mean']=float(z.mae_15m_atr.mean()) if len(z) else None

        tr=result[state]['TRAIN'];va=result[state]['VALID']
        gate=(
            tr['180']['n']>=10 and va['180']['n']>=10 and
            tr['180']['accuracy'] is not None and tr['180']['accuracy']>0.50 and
            va['180']['accuracy'] is not None and va['180']['accuracy']>0.50 and
            tr['300']['accuracy'] is not None and tr['300']['accuracy']>0.50 and
            va['300']['accuracy'] is not None and va['300']['accuracy']>0.50 and
            tr['180']['mean'] is not None and tr['180']['mean']>0 and
            va['180']['mean'] is not None and va['180']['mean']>0 and
            tr['300']['mean'] is not None and tr['300']['mean']>0 and
            va['300']['mean'] is not None and va['300']['mean']>0 and
            va['180']['efficiency'] is not None and va['180']['efficiency']>0 and
            va['300']['efficiency'] is not None and va['300']['efficiency']>0
        )
        result[state]['gate_pass']=bool(gate)
        if gate:candidates.append(state)

    OUT_JSON.write_text(json.dumps({
        'lab':'GC_XAU_CROWDFade_DIRECTIONAL_BIAS_TRANSFER_LAB005',
        'candidates':candidates,'results':result
    },indent=2),encoding='utf-8')

    def f(x):
        return 'NA' if x is None else f'{x:+.3f}'
    def pct(x):
        return 'NA' if x is None else f'{x*100:.1f}%'

    lines=[
        '# GC_XAU_CROWDFade_DIRECTIONAL_BIAS_TRANSFER_LAB005','',
        'Bias-only audit. XAU mid-price; no entry/spread/SL/TP optimization.','',
        '| State | Gate | TrN | TrAcc3 | TrEV3 | TrAcc5 | TrEV5 | VaN | VaAcc3 | VaEV3 | VaAcc5 | VaEV5 | PostAcc5 | PostEV5 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for state in STATES:
        tr=result[state]['TRAIN'];va=result[state]['VALID'];po=result[state]['POST_CHECK']
        lines.append(
            f"| {state} | {'PASS' if result[state]['gate_pass'] else 'FAIL'} | "
            f"{tr['180']['n']} | {pct(tr['180']['accuracy'])} | {f(tr['180']['mean'])} | "
            f"{pct(tr['300']['accuracy'])} | {f(tr['300']['mean'])} | "
            f"{va['180']['n']} | {pct(va['180']['accuracy'])} | {f(va['180']['mean'])} | "
            f"{pct(va['300']['accuracy'])} | {f(va['300']['mean'])} | "
            f"{pct(po['300']['accuracy'])} | {f(po['300']['mean'])} |"
        )

    lines += ['','## Full horizon profile','',
              '| State | 1m | 3m | 5m | 10m | 15m | First +0.25 side (FULL) |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for state in STATES:
        x=result[state]['FULL']
        lines.append(
            f"| {state} | {f(x['60']['mean'])} | {f(x['180']['mean'])} | {f(x['300']['mean'])} | "
            f"{f(x['600']['mean'])} | {f(x['900']['mean'])} | {pct(x['first025_pred_share'])} |"
        )
    lines += ['',f'Candidates: {candidates if candidates else "NONE"}','',
              'POST_CHECK was not used for candidate selection. This LAB tests directional information only, not an executable strategy.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
