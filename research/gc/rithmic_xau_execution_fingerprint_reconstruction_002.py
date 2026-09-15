#!/usr/bin/env python3
"""RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002

Reverse-engineer ONLY implementation-equivalent XAU execution conventions on the
historical Rithmic 51-transfer sample. AMP data is forbidden here.

Target fingerprints (already historical/frozen):
 all 51: EV +0.563R, Sum +28.69R, PF 2.15, DD 3.42R
 single position: N 46, EV +0.666R, Sum +30.63R, PF 2.33, DD 3.32R

This is execution parity reconstruction, not strategy optimization.
"""
from __future__ import annotations
import itertools, json, math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path('research/gc')
RITH=ROOT/'RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CONFIRMED_EVENTS.csv'
XAU=Path('XAUUSD_M1_2026.csv')
OUT=ROOT/'RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002.json'
OUTMD=ROOT/'RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002.md'
OUTCSV=ROOT/'RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002_CANDIDATES.csv'

TARGET_ALL={'n':51,'ev':0.563,'sum':28.69,'pf':2.15,'dd':3.42}
TARGET_SP={'n':46,'ev':0.666,'sum':30.63,'pf':2.33,'dd':3.32}


def stats(trades):
    r=np.array([x['r'] for x in trades],float)
    if not len(r): return {'n':0,'ev':None,'sum':0,'pf':0,'dd':0,'streak':0}
    eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0.0,eq])[1:]; dd=float(np.max(peak-eq))
    gp=float(r[r>0].sum()); gl=float(-r[r<0].sum()); pf=gp/gl if gl else (math.inf if gp else 0.0)
    st=cur=0
    for x in r:
        if x<0: cur+=1; st=max(st,cur)
        else: cur=0
    return {'n':len(r),'ev':float(r.mean()),'sum':float(r.sum()),'pf':float(pf),'dd':dd,'streak':st}

def score(a,s):
    # Count is especially diagnostic; normalize continuous metric errors.
    return (
        2.0*abs(a['n']-TARGET_ALL['n']) + 4.0*abs(s['n']-TARGET_SP['n']) +
        8.0*abs(a['ev']-TARGET_ALL['ev']) + 0.25*abs(a['sum']-TARGET_ALL['sum']) +
        2.0*abs(a['pf']-TARGET_ALL['pf']) + 0.8*abs(a['dd']-TARGET_ALL['dd']) +
        10.0*abs(s['ev']-TARGET_SP['ev']) + 0.25*abs(s['sum']-TARGET_SP['sum']) +
        2.0*abs(s['pf']-TARGET_SP['pf']) + 0.8*abs(s['dd']-TARGET_SP['dd'])
    )

def load():
    x=pd.read_csv(XAU,sep=';')
    x['t']=pd.to_datetime(x.time,format='%Y.%m.%d %H:%M')
    for c in ['open','high','low','close','spread']: x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x.sort_values('t').reset_index(drop=True)
    m=x.set_index('t').resample('5min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna()
    pc=m.close.shift(1)
    m['tr']=pd.concat([(m.high-m.low),(m.high-pc).abs(),(m.low-pc).abs()],axis=1).max(axis=1)
    m.iloc[0,m.columns.get_loc('tr')]=np.nan
    m['atr_wilder']=m.tr.ewm(alpha=1/20,adjust=False,min_periods=20).mean()
    m['atr_sma']=m.tr.rolling(20,min_periods=20).mean()
    e=pd.read_csv(RITH)
    e['entry_utc']=pd.to_datetime(e.entry_eligible_utc,utc=True)
    e['t']=e.entry_utc.dt.tz_convert(None)+pd.Timedelta(hours=2)
    times=set(x.t)
    e=e[e.t.isin(times)].sort_values('t').reset_index(drop=True)
    assert len(e)==51, len(e)
    return x,m,e

def run_trade(e,x,m,atr_kind='wilder',atr_anchor='prev',entry_kind='open',session_gap_min=60,time_exit='last_leq',include_entry_bar=True):
    t=e.t; idxs=x.index[x.t.eq(t)]
    if len(idxs)!=1: return None
    i=int(idxs[0])
    if atr_anchor=='prev': key=t.floor('5min')-pd.Timedelta(minutes=5)
    elif atr_anchor=='entry': key=t.floor('5min')
    else: raise ValueError(atr_anchor)
    col='atr_wilder' if atr_kind=='wilder' else 'atr_sma'
    if key not in m.index or pd.isna(m.at[key,col]): return None
    atr=float(m.at[key,col]); side=e.side
    if entry_kind=='open': entry=float(x.iloc[i].open)
    elif entry_kind=='prev_close':
        if i==0:return None
        entry=float(x.iloc[i-1].close)
    else: raise ValueError(entry_kind)
    sl=entry-atr if side=='LONG' else entry+atr
    tp=entry+3*atr if side=='LONG' else entry-3*atr
    horizon=t+pd.Timedelta(minutes=240)
    start=i if include_entry_bar else i+1
    reason='TIME'; exit_t=None; exit_px=None
    j=start
    last_valid=i
    while j<len(x) and x.iloc[j].t <= horizon:
        rr=x.iloc[j]
        if j>i:
            gap=(rr.t-x.iloc[j-1].t).total_seconds()/60
            if session_gap_min is not None and gap>=session_gap_min:
                p=x.iloc[j-1]; exit_t=p.t; exit_px=float(p.close); reason='SESSION'; break
        lo=float(rr.low); hi=float(rr.high)
        sl_hit=(lo<=sl) if side=='LONG' else (hi>=sl)
        tp_hit=(hi>=tp) if side=='LONG' else (lo<=tp)
        if sl_hit and tp_hit:
            exit_t=rr.t; exit_px=sl; reason='BOTH_SL'; break
        if sl_hit:
            exit_t=rr.t; exit_px=sl; reason='SL'; break
        if tp_hit:
            exit_t=rr.t; exit_px=tp; reason='TP'; break
        last_valid=j; j+=1
    if exit_t is None:
        # Exit at final available M1 close on/before wall-clock horizon.
        if time_exit=='last_leq':
            k=x.index[x.t<=horizon]
            k=int(k[-1]) if len(k) else last_valid
        elif time_exit=='exact_or_prev':
            exact=x.index[x.t.eq(horizon)]
            k=int(exact[0]) if len(exact) else last_valid
        else: raise ValueError(time_exit)
        # Do not cross a session gap to a future row; k is <= horizon.
        exit_t=x.iloc[k].t; exit_px=float(x.iloc[k].close); reason='TIME'
    r=(exit_px-entry)/atr if side=='LONG' else (entry-exit_px)/atr
    return {'entry_t':t,'exit_t':exit_t,'side':side,'r':float(r),'reason':reason,'atr':atr}

def single(trades,boundary='strict'):
    kept=[]; busy=None
    for tr in trades:
        if busy is not None:
            conflict=tr['entry_t'] < busy if boundary=='strict' else tr['entry_t'] <= busy
            if conflict: continue
        kept.append(tr); busy=tr['exit_t']
    return kept

def main():
    x,m,e=load(); rows=[]
    axes={
        'atr_kind':['wilder','sma'],
        'atr_anchor':['prev','entry'],
        'entry_kind':['open','prev_close'],
        'session_gap_min':[None,15,30,60,90],
        'time_exit':['last_leq','exact_or_prev'],
        'include_entry_bar':[True,False],
        'single_boundary':['strict','inclusive'],
    }
    keys=list(axes)
    for vals in itertools.product(*(axes[k] for k in keys)):
        cfg=dict(zip(keys,vals)); trades=[]
        for ev in e.itertuples(index=False):
            tr=run_trade(ev,x,m,**{k:cfg[k] for k in keys if k!='single_boundary'})
            if tr is not None: trades.append(tr)
        a=stats(trades); sp=stats(single(trades,cfg['single_boundary']))
        rec={**cfg,'all_n':a['n'],'all_ev':a['ev'],'all_sum':a['sum'],'all_pf':a['pf'],'all_dd':a['dd'],
             'sp_n':sp['n'],'sp_ev':sp['ev'],'sp_sum':sp['sum'],'sp_pf':sp['pf'],'sp_dd':sp['dd'],'sp_streak':sp['streak']}
        rec['score']=score(a,sp); rows.append(rec)
    df=pd.DataFrame(rows).sort_values(['score','sp_n']).reset_index(drop=True)
    df.to_csv(OUTCSV,index=False)
    top=df.head(20).to_dict('records')
    best=top[0]
    result={'lab':'RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002','amp_data_used':False,'candidate_count':len(df),
            'targets':{'all':TARGET_ALL,'single_position':TARGET_SP},'best':best,'top20':top,
            'exact_count_candidates':int(((df.all_n==51)&(df.sp_n==46)).sum())}
    OUT.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    md=['# RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002','',
        '**AMP data used: NO. Historical Rithmic/XAU implementation parity only.**','',
        f"Candidates enumerated: **{len(df)}**; candidates with exact 51→46 count: **{result['exact_count_candidates']}**.",'',
        '## Best implementation-equivalent candidate','']
    for k in keys: md.append(f"- {k}: `{best[k]}`")
    md += ['',f"All 51: EV **{best['all_ev']:+.4f}R**, Sum **{best['all_sum']:+.3f}R**, PF **{best['all_pf']:.3f}**, DD **{best['all_dd']:.3f}R**",
           f"Single-position: N **{best['sp_n']}**, EV **{best['sp_ev']:+.4f}R**, Sum **{best['sp_sum']:+.3f}R**, PF **{best['sp_pf']:.3f}**, DD **{best['sp_dd']:.3f}R**",'',
           'Historical targets: all 51 EV +0.563R / Sum +28.69R / PF2.15 / DD3.42; single 46 EV +0.666R / Sum+30.63R / PF2.33 / DD3.32.']
    OUTMD.write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(OUTMD.read_text()); print(json.dumps(result,indent=2,default=str))

if __name__=='__main__': main()
