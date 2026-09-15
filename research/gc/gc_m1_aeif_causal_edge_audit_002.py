#!/usr/bin/env python3
"""GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002

Causal execution-timing audit for the fixed LAB001 M1 mechanism.
No threshold search, no XAU, no stop/target optimization.

Two information-entry clocks:
1) B_NEXT_OPEN: B is known after its M1 bar closes; enter at the exact next M1 open.
2) D_NEXT_OPEN: D confirmation is known only after response bar closes; enter at the
   exact next M1 open after the first qualifying response.

This audit explicitly separates the PRE-DISCOVERY history (< 2026-09-06 22:00 UTC)
from the original ATAS discovery clock and the later history.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path('research/gc')
BASE_PATH=ROOT/'gc_m1_aeif_historical_edge_replication_001.py'
OUT_JSON=ROOT/'GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002.json'
OUT_MD=ROOT/'GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002.md'
OUT_EVENTS=ROOT/'GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002_EVENTS.csv'
HORIZONS=(1,3,5,15)
DISCOVERY_START=pd.Timestamp('2026-09-06T22:00:00Z')
DISCOVERY_END=pd.Timestamp('2026-09-11T12:46:00Z')
RNG_SEED=20260915


def load_base():
    spec=importlib.util.spec_from_file_location('gc_m1_base',BASE_PATH)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def ensure_sources(base):
    work=ROOT/'_m1_edge_work'; work.mkdir(parents=True,exist_ok=True)
    rz=work/'rithmic.zip'; az=work/'amp.zip'
    if not rz.exists(): base.download(base.RITH_URL,rz)
    if not az.exists(): base.download(base.AMP_URL,az)
    if base.sha256_file(rz)!=base.RITH_SHA: raise SystemExit('Rithmic SHA mismatch')
    if base.sha256_file(az)!=base.AMP_SHA: raise SystemExit('AMP SHA mismatch')
    return rz,az


def next_open_outcomes(bars:pd.DataFrame,events:pd.DataFrame,mode:str)->pd.DataFrame:
    index={t:i for i,t in enumerate(bars.time)}
    rows=[]
    source=events[events.stage_b].copy() if mode=='B_NEXT_OPEN' else events[events.stage_d].copy()
    for e in source.itertuples(index=False):
        event_i=index[e.time]
        if mode=='B_NEXT_OPEN':
            signal_time=e.time
            signal_i=event_i
            atr=float(e.atr14)
        else:
            signal_time=pd.Timestamp(e.response_time)
            if signal_time not in index: continue
            signal_i=index[signal_time]
            atr=float(bars.iloc[signal_i].atr14)
        entry_i=signal_i+1
        if entry_i>=len(bars): continue
        entry=bars.iloc[entry_i]
        if entry.time != signal_time+pd.Timedelta(minutes=1): continue
        if not np.isfinite(atr) or atr<=0: continue
        entry_px=float(entry.open)
        side=e.side
        row={
            'feed':e.feed,'mode':mode,'event_time':e.time,'side':side,
            'signal_time':signal_time,'entry_time':entry.time,'entry_price':entry_px,
            'signal_atr14':atr,'event_close':float(e.close),
            'confirmation_capture_atr':(
                ((entry_px-float(e.close))/float(e.atr14)) if side=='LONG'
                else ((float(e.close)-entry_px)/float(e.atr14))
            ) if mode=='D_NEXT_OPEN' and np.isfinite(e.atr14) and e.atr14>0 else np.nan,
        }
        for h in HORIZONS:
            target_i=entry_i+h-1
            if target_i>=len(bars):
                row[f'fwd_{h}m_atr']=np.nan; continue
            target=bars.iloc[target_i]
            expected=entry.time+pd.Timedelta(minutes=h-1)
            if target.time!=expected:
                row[f'fwd_{h}m_atr']=np.nan; continue
            px=float(target.close)
            row[f'fwd_{h}m_atr']=(px-entry_px)/atr if side=='LONG' else (entry_px-px)/atr
        rows.append(row)
    return pd.DataFrame(rows)


def window_mask(df:pd.DataFrame,name:str):
    t=pd.to_datetime(df.event_time,utc=True)
    if name=='PRE_DISCOVERY': return t<DISCOVERY_START
    if name=='DISCOVERY_CLOCK': return (t>=DISCOVERY_START)&(t<=DISCOVERY_END)
    if name=='POST_DISCOVERY': return t>DISCOVERY_END
    if name=='NON_DISCOVERY': return (t<DISCOVERY_START)|(t>DISCOVERY_END)
    if name=='FULL': return pd.Series(True,index=df.index)
    raise ValueError(name)


def cluster_bootstrap_days(df:pd.DataFrame,col:str,n_boot=10000):
    x=df.dropna(subset=[col]).copy()
    if x.empty: return [None,None]
    x['day']=pd.to_datetime(x.event_time,utc=True).dt.date
    groups=[g[col].to_numpy(float) for _,g in x.groupby('day')]
    if len(groups)<2: return [None,None]
    rng=np.random.default_rng(RNG_SEED)
    means=np.empty(n_boot,float)
    n=len(groups)
    for k in range(n_boot):
        picks=rng.integers(0,n,n)
        vals=np.concatenate([groups[i] for i in picks])
        means[k]=vals.mean()
    return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]


def metrics(df:pd.DataFrame):
    out={'n':int(len(df)),'long':int((df.side=='LONG').sum()) if len(df) else 0,'short':int((df.side=='SHORT').sum()) if len(df) else 0,'horizons':{}}
    for h in HORIZONS:
        col=f'fwd_{h}m_atr'; v=df[col].dropna().to_numpy(float)
        days=(df.dropna(subset=[col]).assign(day=pd.to_datetime(df.dropna(subset=[col]).event_time,utc=True).dt.date).groupby('day')[col].mean() if len(v) else pd.Series(dtype=float))
        out['horizons'][str(h)]={
            'n':int(len(v)),'mean_atr':float(v.mean()) if len(v) else None,
            'median_atr':float(np.median(v)) if len(v) else None,
            'win_pct':float((v>0).mean()*100) if len(v) else None,
            'day_cluster_bootstrap_95':cluster_bootstrap_days(df,col),
            'days':int(len(days)),'positive_days':int((days>0).sum()) if len(days) else 0,
            'median_daily_mean_atr':float(days.median()) if len(days) else None,
        }
        out['horizons'][str(h)]['side']={}
        for side in ('LONG','SHORT'):
            sv=df.loc[df.side==side,col].dropna().to_numpy(float)
            out['horizons'][str(h)]['side'][side]={
                'n':int(len(sv)),'mean_atr':float(sv.mean()) if len(sv) else None,
                'win_pct':float((sv>0).mean()*100) if len(sv) else None,
            }
    if 'confirmation_capture_atr' in df and df.confirmation_capture_atr.notna().any():
        c=df.confirmation_capture_atr.dropna().to_numpy(float)
        out['confirmation_capture']={'n':int(len(c)),'mean_atr':float(c.mean()),'median_atr':float(np.median(c)),'positive_pct':float((c>0).mean()*100)}
    return out


def audit_feed(name,bars,events):
    b=next_open_outcomes(bars,events,'B_NEXT_OPEN')
    d=next_open_outcomes(bars,events,'D_NEXT_OPEN')
    both=pd.concat([b,d],ignore_index=True)
    result={}
    for mode,frame in [('B_NEXT_OPEN',b),('D_NEXT_OPEN',d)]:
        result[mode]={}
        for w in ('PRE_DISCOVERY','DISCOVERY_CLOCK','POST_DISCOVERY','NON_DISCOVERY','FULL'):
            result[mode][w]=metrics(frame[window_mask(frame,w)].copy())
    return result,both


def fmt(v): return 'NA' if v is None else f'{v:+.3f}'

def table_for(res,mode):
    lines=['| Window | N | 5m EV | 5m CI95 | 15m EV | 15m CI95 |','|---|---:|---:|---:|---:|---:|']
    for w in ('PRE_DISCOVERY','DISCOVERY_CLOCK','POST_DISCOVERY','NON_DISCOVERY','FULL'):
        m=res[mode][w]; h5=m['horizons']['5']; h15=m['horizons']['15']
        ci5=h5['day_cluster_bootstrap_95']; ci15=h15['day_cluster_bootstrap_95']
        c5='NA' if ci5[0] is None else f'[{ci5[0]:+.3f},{ci5[1]:+.3f}]'
        c15='NA' if ci15[0] is None else f'[{ci15[0]:+.3f},{ci15[1]:+.3f}]'
        lines.append(f"| {w} | {m['n']} | {fmt(h5['mean_atr'])} | {c5} | {fmt(h15['mean_atr'])} | {c15} |")
    return lines


def main():
    base=load_base(); rz,az=ensure_sources(base)
    rb=base.load_rithmic(rz); ab=base.load_amp(az)
    re=base.build_events(rb); ae=base.build_events(ab)
    rr,rev=audit_feed('RITHMIC',rb,re); ar,aev=audit_feed('AMP',ab,ae)
    all_events=pd.concat([rev,aev],ignore_index=True)
    all_events.to_csv(OUT_EVENTS,index=False)
    result={
        'lab':'GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002','status':'COMPLETED_FIXED_RULE_NO_SWEEP',
        'entry_rules':{
            'B_NEXT_OPEN':'exact next clock-contiguous M1 open after completed B bar',
            'D_NEXT_OPEN':'exact next clock-contiguous M1 open after completed first qualifying D response bar',
            'normalization':'B uses B-bar ATR14; D uses completed response-bar ATR14',
            'thresholds_changed':False,
        },
        'windows':{'discovery_start':DISCOVERY_START.isoformat(),'discovery_end':DISCOVERY_END.isoformat()},
        'rithmic':rr,'amp':ar,
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    lines=['# GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002','',
           'Fixed LAB001 M1 selector. No threshold search. This audit removes close-fill/confirmation lookahead from the information-entry clock.','',
           '## Rithmic raw — B next-open','']+table_for(rr,'B_NEXT_OPEN')+['','## Rithmic raw — D next-open after confirmation','']+table_for(rr,'D_NEXT_OPEN')+['','## AMP/CQG raw — B next-open','']+table_for(ar,'B_NEXT_OPEN')+['','## AMP/CQG raw — D next-open after confirmation','']+table_for(ar,'D_NEXT_OPEN')+['',
           '## Interpretation','',
           'PRE_DISCOVERY is the most important historical falsification slice because it predates the original 6–11 Sep ATAS discovery. The two feeds are representations of largely the same GC market and therefore are feed-parity evidence, not two independent market samples. Day-cluster bootstrap CIs are diagnostic, not a substitute for new forward history.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
