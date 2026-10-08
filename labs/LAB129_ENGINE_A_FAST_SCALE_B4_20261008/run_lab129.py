#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, zipfile, re
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
spec=importlib.util.spec_from_file_location("lab124",SRC)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OUT=Path("lab129_out"); OUT.mkdir(exist_ok=True)
TRAIN_END=m.TRAIN_END
p=m.p.copy()
f=m.f.copy()

# -------- B4 = exact 4x time-scale compression of Engine A --------
# H4 trend -> H1 trend
# H1 extension -> M15 extension
# OI4h -> OI1h
# Z 6h -> Z 90m
# SWING3 remains M5 because base price tape is M5
# trigger search 6h -> 90m; max hold 48h -> 12h
# SL 1 H1 ATR -> 1 M15 ATR; TP remains 3R
Z_BARS=18
OI_BARS=12
SEARCH_BARS=18
MAX_H=12
COSTS=[2.81,7.5]

# Recompute flow fields at fast scale from the same explicit ratio/OI series.
ff=f[['time','ratio','oi']].copy().sort_values('time').drop_duplicates('time',keep='last')
mu=ff.ratio.rolling(Z_BARS,min_periods=Z_BARS).mean()
sd=ff.ratio.rolling(Z_BARS,min_periods=Z_BARS).std(ddof=0)
ff['z_fast']=(ff.ratio-mu)/sd.replace(0,np.nan)
ff['dz15']=ff.z_fast-ff.z_fast.shift(3)
ff['oi1h']=ff.oi/ff.oi.shift(OI_BARS)-1

# M15 extension/ATR shell.
m15=p.set_index('time').resample('15min',label='left',closed='left').agg(
    open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')
).dropna().reset_index()
pr=m15.close.shift(1)
tr=pd.concat([(m15.high-m15.low),(m15.high-pr).abs(),(m15.low-pr).abs()],axis=1).max(axis=1)
m15['atr']=tr.rolling(14,min_periods=14).mean()
m15['ema20']=m15.close.ewm(span=20,adjust=False).mean()
m15['extension']=(m15.close-m15.ema20)/m15.atr
m15['close_time']=m15.time+pd.Timedelta(minutes=15)

# H1 trend using the same bar-count logic as Engine A H4 trend.
h1=p.set_index('time').resample('1h',label='left',closed='left').agg(
    open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')
).dropna().reset_index()
h1['ema50']=h1.close.ewm(span=50,adjust=False).mean()
h1['ema50_lag6']=h1.ema50.shift(6)
h1['trend']=np.where((h1.close>h1.ema50)&(h1.ema50>h1.ema50_lag6),1,
                     np.where((h1.close<h1.ema50)&(h1.ema50<h1.ema50_lag6),-1,0))
prev=h1.close.shift(1)
htr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
h1['atr14']=htr.rolling(14,min_periods=14).mean()
h1['body_atr']=(h1.close-h1.open)/h1.atr14
age=[];cur=0;pv=0
for v in h1.trend:
    if v!=0 and v==pv: cur+=1
    elif v!=0: cur=1
    else: cur=0
    age.append(cur); pv=v
h1['trend_age']=age
imp=(h1.body_atr.abs()>=0.8)&(np.sign(h1.body_atr)==h1.trend)
ia=[];cnt=999
for x in imp.fillna(False):
    cnt=0 if x else min(cnt+1,999); ia.append(cnt)
h1['impulse_age']=ia
h1['close_time']=h1.time+pd.Timedelta(hours=1)

# Merge all causal contexts to M5.
b=pd.merge_asof(p.sort_values('time'),
    m15[['close_time','atr','extension']].dropna().sort_values('close_time'),
    left_on='time',right_on='close_time',direction='backward')
b=pd.merge_asof(b.sort_values('time'),
    h1[['close_time','trend','trend_age','impulse_age']].dropna().sort_values('close_time'),
    left_on='time',right_on='close_time',direction='backward',suffixes=('','_h1'))
b=pd.merge_asof(b.sort_values('time'),
    ff[['time','z_fast','dz15','oi1h']].dropna().sort_values('time'),
    on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b=b.dropna(subset=['atr','extension','trend','trend_age','impulse_age','z_fast','oi1h']).reset_index(drop=True)

# TRAIN-only percentile thresholds: same percentile concept as Engine A, no return fitting.
trn=b.time<TRAIN_END
EXT80=float(b.loc[trn,'extension'].abs().quantile(.80))
OI70=float(b.loc[trn,'oi1h'].quantile(.70))

BT=b.time.reset_index(drop=True);BO=b.open.to_numpy(float);BH=b.high.to_numpy(float)
BL=b.low.to_numpy(float);BC=b.close.to_numpy(float);BA=b.atr.to_numpy(float);BZ=b.z_fast.to_numpy(float)

def phase(age,imp_age):
    if age<=3:return 'BIRTH'
    if imp_age<=2:return 'REACCEL'
    if age<=12:return 'CONT'
    if age<=24:return 'MATURE'
    return 'LATE'

def swing3_entry(i,side):
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:return j+1,j,(BC[j]-ref)/BA[i]
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:return j+1,j,(ref-BC[j])/BA[i]
    return None,None,np.nan

# Atlas universe. We intentionally NEVER read BTC OOS returns in this LAB.
events=[]
last=len(b)-MAX_H*12-2
for i in range(1,last):
    if BT.iloc[i]>=TRAIN_END: continue
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1
    trend=int(b.trend.iloc[i])
    if trend==0 or trend==side:continue
    ext=float(b.extension.iloc[i]);oi=float(b.oi1h.iloc[i])
    if not((side>0 and ext<0) or (side<0 and ext>0)):continue
    if abs(ext)<EXT80 or oi<OI70:continue
    ph=phase(int(b.trend_age.iloc[i]),int(b.impulse_age.iloc[i]))
    ei,ti,br=swing3_entry(i,side)
    if ei is None:continue
    events.append(dict(signal_i=i,entry_i=ei,trigger_i=ti,signal_time=BT.iloc[i],entry_time=BT.iloc[ei],
                       side=side,phase=ph,z=float(BZ[i]),ext_abs=abs(ext),oi1h=oi,atr=float(BA[i]),
                       break_strength=br,delay_min=(BT.iloc[ei]-BT.iloc[i]).total_seconds()/60))
ev=pd.DataFrame(events)
ev.to_csv(OUT/'LAB129_B4_train_events.csv',index=False)

# Descriptive TRAIN atlas: future close/MFE/MAE by phase and horizon.
atlas=[]
for scope,dd in [('ALL',ev),('CORE_CONT_REACCEL',ev[ev.phase.isin(['CONT','REACCEL'])]),
                 ('CONT',ev[ev.phase=='CONT']),('REACCEL',ev[ev.phase=='REACCEL'])]:
    for hold_h in [3,6,12]:
        vals=[]
        for _,r in dd.iterrows():
            ei=int(r.entry_i);end=min(ei+hold_h*12-1,len(b)-1);side=int(r.side);atr=float(r.atr);entry=float(BO[ei])
            close=side*(float(BC[end])-entry)/atr
            mfe=((float(np.max(BH[ei:end+1]))-entry)/atr if side>0 else
                 (entry-float(np.min(BL[ei:end+1])))/atr)
            mae=((entry-float(np.min(BL[ei:end+1])))/atr if side>0 else
                 (float(np.max(BH[ei:end+1]))-entry)/atr)
            vals.append((close,mfe,mae))
        if vals:
            a=np.asarray(vals,float)
            atlas.append(dict(scope=scope,hold_h=hold_h,n=len(a),
                              mean_close_atr=float(a[:,0].mean()),median_close_atr=float(np.median(a[:,0])),
                              mean_mfe_atr=float(a[:,1].mean()),mean_mae_atr=float(a[:,2].mean()),
                              p_close_positive=float((a[:,0]>0).mean())))
pd.DataFrame(atlas).to_csv(OUT/'LAB129_B4_train_atlas.csv',index=False)

# Frozen execution analog: next M5 open, SL=1 M15ATR, TP=3R, max12h.
def sim_one(ei,side,atr,cost):
    entry=float(BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(b)-1)
    gross=side*(BC[end]-entry)/atr;reason='TIME';xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
        if hs:gross=-1;reason='SL';xi=j;break
        if ht:gross=3;reason='TP';xi=j;break
    return float(gross-(cost/10000.0)*entry/atr),reason,xi

summary=[];trades=[]
for cost in COSTS:
    for scope,dd in [('ALL',ev),('CORE_CONT_REACCEL',ev[ev.phase.isin(['CONT','REACCEL'])]),
                     ('CONT',ev[ev.phase=='CONT']),('REACCEL',ev[ev.phase=='REACCEL'])]:
        s=dd.sort_values('entry_time');open_until=pd.Timestamp.min.tz_localize('UTC');rows=[]
        for _,r in s.iterrows():
            if r.entry_time<open_until:continue
            net,reason,xi=sim_one(int(r.entry_i),int(r.side),float(r.atr),cost);open_until=BT.iloc[xi]
            rows.append(dict(cost_bps=cost,scope=scope,phase=r.phase,signal_time=r.signal_time,
                             entry_time=r.entry_time,exit_time=BT.iloc[xi],
                             side='BUY' if r.side>0 else 'SELL',net_r=net,reason=reason))
        t=pd.DataFrame(rows)
        if t.empty:continue
        trades.append(t)
        pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
        months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
        ce=t.net_r.cumsum();ddr=float((ce.cummax()-ce).max())
        summary.append(dict(cost_bps=cost,scope=scope,n=len(t),trades_month=len(t)/months,
                            ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                            wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),
                            r_month=float(t.net_r.sum()/months),realized_dd_r=ddr,
                            tp_rate=float((t.reason=='TP').mean()),sl_rate=float(t.reason.isin(['SL','BOTH_STOP_FIRST']).mean())))
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB129_B4_train_execution.csv',index=False)
if trades:pd.concat(trades,ignore_index=True).to_csv(OUT/'LAB129_B4_train_trades.csv',index=False)

# Overlap with frozen Engine A TRAIN core signals from LAB124.
abase=m.df[(m.df['split']=='TRAIN') & (m.df.phase.isin(['CONT','REACCEL']))].copy()
a_times=pd.to_datetime(abase.signal_time,utc=True).sort_values().to_numpy()
def nearest_hours(t):
    if len(a_times)==0:return np.inf
    x=np.datetime64(pd.Timestamp(t).to_datetime64())
    k=np.searchsorted(a_times,x)
    ds=[]
    if k<len(a_times):ds.append(abs((pd.Timestamp(a_times[k])-pd.Timestamp(t)).total_seconds())/3600)
    if k>0:ds.append(abs((pd.Timestamp(a_times[k-1])-pd.Timestamp(t)).total_seconds())/3600)
    return min(ds) if ds else np.inf
core=ev[ev.phase.isin(['CONT','REACCEL'])].copy()
if len(core):
    core['nearest_A_h']=core.signal_time.map(nearest_hours)
    core['overlap_A_6h']=core.nearest_A_h<=6
    core['overlap_A_12h']=core.nearest_A_h<=12
    core.to_csv(OUT/'LAB129_B4_overlap_engineA.csv',index=False)
    overlap=dict(
        b4_core_raw_n=int(len(core)),
        within_6h_n=int(core.overlap_A_6h.sum()),
        within_6h_pct=float(core.overlap_A_6h.mean()),
        within_12h_n=int(core.overlap_A_12h.sum()),
        within_12h_pct=float(core.overlap_A_12h.mean()),
        unique_gt12h_n=int((~core.overlap_A_12h).sum()),
        unique_gt12h_pct=float((~core.overlap_A_12h).mean())
    )
else: overlap={}

lines=['# LAB129 — B4 ENGINE A FAST SCALE','',
       'Purpose: close B4 before searching for a genuinely separate Engine B.',
       'Protocol: BTC TRAIN only. BTC OOS returns are intentionally not used.',
       '',
       '## Frozen 4x scale mapping',
       '- H4 trend -> H1 trend (same EMA50 + lag6 bar logic)',
       '- H1 EMA20/ATR extension -> M15 EMA20/ATR extension',
       '- OI4h -> OI1h',
       '- Z6h (72xM5) -> Z90m (18xM5)',
       '- fresh |Z|>=1, inverse-crowd side opposite established trend',
       '- extension threshold = TRAIN 80th percentile, OI threshold = TRAIN 70th percentile',
       '- M5 SWING3 confirmation retained; search window 90m',
       '- next M5 open; SL=1 M15ATR; TP=3R; max hold=12h',
       '',
       f'Frozen TRAIN thresholds: extension >= {EXT80:.3f} M15ATR; OI1h >= {OI70:+.3%}.',
       '',
       '## TRAIN execution']
for cost in COSTS:
    for scope in ['CORE_CONT_REACCEL','CONT','REACCEL','ALL']:
        q=sm[(sm.cost_bps==cost)&(sm.scope==scope)]
        if len(q):
            r=q.iloc[0]
            lines.append(f"- {cost:.2f}bps / {scope}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, realizedDD={r.realized_dd_r:.1f}R")
lines += ['', '## Overlap with frozen Engine A TRAIN core']
if overlap:
    lines.append(f"- B4 core raw events: {overlap['b4_core_raw_n']}")
    lines.append(f"- within ±6h of Engine A signal: {overlap['within_6h_n']} ({overlap['within_6h_pct']:.1%})")
    lines.append(f"- within ±12h of Engine A signal: {overlap['within_12h_n']} ({overlap['within_12h_pct']:.1%})")
    lines.append(f"- unique >12h from Engine A: {overlap['unique_gt12h_n']} ({overlap['unique_gt12h_pct']:.1%})")
lines += ['', '## Decision rule',
          'B4 is only worth external-symbol validation if TRAIN shows a material positive edge after costs AND a material share of signals are temporally distinct from Engine A.',
          'No BTC OOS promotion/rejection decision is allowed in this LAB.']
(OUT/'LAB129_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB129_meta.json').write_text(json.dumps(dict(
    protocol='BTC TRAIN only; no BTC OOS return inspection',
    mapping=dict(z_window_m5=18,trend='H1 EMA50 lag6',extension='M15 EMA20 / ATR14',
                 oi='1h growth',swing='M5 SWING3',search_minutes=90,hold_hours=12,sl='1 M15ATR',tp='3R'),
    thresholds=dict(ext80=EXT80,oi70=OI70),overlap=overlap,
    caveat='B4 is a scale-extension of Engine A, not a distinct Engine B mechanism'
),indent=2))
print('\n'.join(lines))
