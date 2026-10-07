#!/usr/bin/env python3
from __future__ import annotations
import math,re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab106c_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
SPREAD_BPS=2.81
TP_R=1.5
BODY_ATR_MIN=0.55
BODY_RANGE_MIN=0.65
STOP_BUF_H1=0.10
STOP_MIN_H1=0.20
STOP_MAX_H1=3.50
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")

def norm(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())
def pick(cols,prefs):
    nc={norm(c):c for c in cols}
    for p in prefs:
        if norm(p) in nc:return nc[norm(p)]
    for p in prefs:
        pp=norm(p)
        for k,v in nc.items():
            if pp in k or k in pp:return v
    return None
def load_zip(zp):
    with zipfile.ZipFile(zp) as z:
        frames=[]
        for n in z.namelist():
            if not n.lower().endswith('.csv'): continue
            try:
                with z.open(n) as f:d=pd.read_csv(f)
                if len(d):frames.append(d)
            except: pass
        if not frames: raise RuntimeError(f'no csv in {zp}')
        common=set(frames[0].columns)
        for d in frames[1:]:common &= set(d.columns)
        if len(frames)>1 and len(common)>=4:
            cols=list(common); return pd.concat([d[cols] for d in frames],ignore_index=True)
        return frames[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

flow=load_zip(FLOW_ZIP)
ft=pick(flow.columns,['timestamp','time','datetime','open_time'])
fr=pick(flow.columns,['longShortRatio','long_short_ratio','ls_ratio','globalLongShortAccountRatio','ratio'])
flow=flow[[ft,fr]].copy(); flow['time']=ptime(flow[ft]); flow['ratio']=pd.to_numeric(flow[fr],errors='coerce')
flow=flow.dropna().sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(72,min_periods=72).mean(); sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)

raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','datetime','open_time']); po=pick(raw.columns,['open']); ph=pick(raw.columns,['high']); pl=pick(raw.columns,['low']); pc=pick(raw.columns,['close'])
p=raw[[pt,po,ph,pl,pc]].copy(); p['time']=ptime(p[pt])
for c,nm in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[nm]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# M15 + ATR14
m15=p.set_index('time').resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
m15['close_time']=m15.time+pd.Timedelta(minutes=15)
prev=m15.close.shift(1)
tr=pd.concat([(m15.high-m15.low),(m15.high-prev).abs(),(m15.low-prev).abs()],axis=1).max(axis=1)
m15['atr15']=tr.rolling(14,min_periods=14).mean()
m15['body']=(m15.close-m15.open).abs()
m15['range']=(m15.high-m15.low)
m15['body_atr']=m15.body/m15.atr15
m15['body_range']=m15.body/m15.range.replace(0,np.nan)

# H1 ATR14 projected causally to M15
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h1['close_time']=h1.time+pd.Timedelta(hours=1)
pr=h1.close.shift(1)
trh=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr_h1']=trh.rolling(14,min_periods=14).mean()

# H4 EMA50 bias; use last completed H4 bar only.
h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['close_time']=h4.time+pd.Timedelta(hours=4)
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean()
h4['bias']=np.where(h4.close>h4.ema50,1,np.where(h4.close<h4.ema50,-1,0))

m15=pd.merge_asof(m15.sort_values('close_time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),on='close_time',direction='backward')
m15=pd.merge_asof(m15.sort_values('close_time'),h4[['close_time','bias']].dropna().sort_values('close_time'),on='close_time',direction='backward')
m15=pd.merge_asof(m15.sort_values('close_time'),flow[['time','z']].dropna().sort_values('time'),left_on='close_time',right_on='time',direction='backward',tolerance=pd.Timedelta('10min'),suffixes=('','_z'))
m15=m15.dropna(subset=['atr15','atr_h1','bias','z']).reset_index(drop=True)

PT=p.time
PH=p.high.to_numpy(float); PL=p.low.to_numpy(float); PO=p.open.to_numpy(float); PC=p.close.to_numpy(float)

def pidx(ts): return int(PT.searchsorted(pd.Timestamp(ts),side='left'))
def in_session(ts):
    h=ts.hour+ts.minute/60
    if 7<=h<9:return 'LONDON'
    if 13<=h<15:return 'NY'
    return None

def zclass(side,z):
    if abs(z)<1:return 'NEUTRAL'
    # crowd direction = sign(z); trade against crowd if trade side is opposite sign(z)
    crowd=1 if z>0 else -1
    return 'AGAINST_CROWD' if side==-crowd else 'WITH_CROWD'

rows=[]; open_until=-1
for i,r in m15.iterrows():
    sess=in_session(r.time)
    if sess is None: continue
    side=1 if r.close>r.open else (-1 if r.close<r.open else 0)
    if side==0 or side!=int(r.bias): continue
    if r.body_atr < BODY_ATR_MIN or r.body_range < BODY_RANGE_MIN: continue
    entry_time=r.close_time
    ei=pidx(entry_time)
    if ei>=len(p): continue
    if ei<=open_until: continue
    entry=PO[ei]

    # last 3 completed M5 bars including impulse candle endpoint (bars immediately before next-M15 open)
    end5=ei
    start5=end5-3
    if start5<0: continue
    if side>0:
        stop=float(np.min(PL[start5:end5]))-STOP_BUF_H1*r.atr_h1
        risk=entry-stop
    else:
        stop=float(np.max(PH[start5:end5]))+STOP_BUF_H1*r.atr_h1
        risk=stop-entry
    if risk<=0:continue
    risk_h1=risk/r.atr_h1
    if risk_h1<STOP_MIN_H1 or risk_h1>STOP_MAX_H1:continue
    tp=entry+side*TP_R*risk

    # no time-stop specified in frozen rules: follow until TP/SL or data end, one position at a time
    ex=None; xp=None; reason=None
    for j in range(ei,len(p)):
        hs=(PL[j]<=stop) if side>0 else (PH[j]>=stop)
        ht=(PH[j]>=tp) if side>0 else (PL[j]<=tp)
        if hs and ht: ex=j;xp=stop;reason='SL_COLLISION';break
        if hs: ex=j;xp=stop;reason='SL';break
        if ht: ex=j;xp=tp;reason='TP';break
    if ex is None:continue
    gross=side*(xp-entry)/risk
    cost_r=(entry*(SPREAD_BPS/10000.0))/risk
    net=gross-cost_r
    rows.append(dict(entry_time=entry_time,exit_time=PT.iloc[ex],session=sess,side='LONG' if side>0 else 'SHORT',
                     h4_bias=int(r.bias),body_atr=r.body_atr,body_range=r.body_range,atr_h1=r.atr_h1,
                     stop_h1=risk_h1,z=r.z,z_class=zclass(side,r.z),entry=entry,stop=stop,tp=tp,
                     gross_r=gross,net_r=net,cost_r=cost_r,reason=reason,hold_h=(ex-ei+1)*5/60))
    open_until=ex

t=pd.DataFrame(rows)
t['split']=np.where(pd.to_datetime(t.entry_time,utc=True)<TRAIN_END,'TRAIN','OOS')
t['year']=pd.to_datetime(t.entry_time,utc=True).dt.year
t['month']=pd.to_datetime(t.entry_time,utc=True).dt.strftime('%Y-%m')
t.to_csv(OUT/'LAB106C_trades.csv',index=False)

def metrics(q):
    if len(q)==0:return dict(n=0,ev=np.nan,t=np.nan,pf=np.nan,wr=np.nan,sumr=0.0,dd=np.nan,se=np.nan,tp_rate=np.nan,sl_rate=np.nan)
    x=q.net_r.to_numpy(float); sd=float(x.std(ddof=1)) if len(x)>1 else np.nan
    se=sd/math.sqrt(len(x)) if len(x)>1 and sd>0 else np.nan
    tt=float(x.mean()/se) if np.isfinite(se) and se>0 else np.nan
    pos=x[x>0].sum();neg=-x[x<0].sum()
    eq=np.cumsum(x);pk=np.maximum.accumulate(np.r_[0,eq]);dd=float(np.max(pk[1:]-eq))
    return dict(n=len(q),ev=float(x.mean()),t=tt,pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),sumr=float(x.sum()),dd=dd,se=se,
                tp_rate=float((q.reason=='TP').mean()),sl_rate=float(q.reason.isin(['SL','SL_COLLISION']).mean()))

# Part1
s=[]
for split in ['TRAIN','OOS','ALL']:
    q=t if split=='ALL' else t[t.split==split]
    s.append(dict(split=split,**metrics(q)))
pd.DataFrame(s).to_csv(OUT/'LAB106C_part1_summary.csv',index=False)
yr=[]
for y,q in t.groupby('year'): yr.append(dict(year=int(y),**metrics(q)))
pd.DataFrame(yr).to_csv(OUT/'LAB106C_yearly.csv',index=False)

# Part2 z groups
zg=[]
for split in ['TRAIN','OOS','ALL']:
    qq=t if split=='ALL' else t[t.split==split]
    for cls in ['AGAINST_CROWD','WITH_CROWD','NEUTRAL']:
        q=qq[qq.z_class==cls]
        zg.append(dict(split=split,z_class=cls,**metrics(q)))
pd.DataFrame(zg).to_csv(OUT/'LAB106C_z_groups.csv',index=False)

# Filters as counterfactual: BASE, BLOCK_WITH, ONLY_AGAINST, AGAINST_PLUS_NEUTRAL
fr=[]
for split in ['TRAIN','OOS']:
    qq=t[t.split==split]
    filters={
      'BASE':qq,
      'BLOCK_WITH':qq[qq.z_class!='WITH_CROWD'],
      'ONLY_AGAINST':qq[qq.z_class=='AGAINST_CROWD'],
      'AGAINST_PLUS_NEUTRAL':qq[qq.z_class.isin(['AGAINST_CROWD','NEUTRAL'])]
    }
    for name,q in filters.items(): fr.append(dict(split=split,filter=name,**metrics(q)))
pd.DataFrame(fr).to_csv(OUT/'LAB106C_filter_counterfactual.csv',index=False)

# side/session breakdown
detail=[]
for split in ['TRAIN','OOS']:
    qq=t[t.split==split]
    for sess in ['LONDON','NY']:
      for side in ['LONG','SHORT']:
        q=qq[(qq.session==sess)&(qq.side==side)]
        detail.append(dict(split=split,session=sess,side=side,**metrics(q)))
pd.DataFrame(detail).to_csv(OUT/'LAB106C_session_side.csv',index=False)

# worst month
mo=t.groupby('month').net_r.agg(['sum','count','mean']).reset_index()
mo.to_csv(OUT/'LAB106C_monthly.csv',index=False)

lines=['# LAB106C — Session Momentum + z','',
'Frozen rules: BTCUSDT M15; London 07:00-09:00 UTC; NY 13:00-15:00 UTC; strong impulse body>=0.55 ATR15 and body/range>=0.65;',
'H4 EMA50 directional bias from last completed H4; enter next M15 open; SL from last 3 M5 bars +/-0.1 H1 ATR, valid 0.2..3.5 H1 ATR; TP 1.5R; GetLeveraged spread 2.81 bps.',
'One position at a time; same-bar TP/SL collision = stop. No time stop added because none was specified.','']
for r in s:
    lines.append(f"- {r['split']}: N={r['n']} EV={r['ev']:+.3f}R PF={r['pf']:.2f} t={r['t']:.2f} WR={r['wr']:.1%} DD={r['dd']:.1f}R")
lines+=['','## Z groups']
for r in zg:
    if r['split'] in ['TRAIN','OOS']:
        lines.append(f"- {r['split']} {r['z_class']}: N={r['n']} EV={r['ev']:+.3f}R PF={r['pf']:.2f} t={r['t']:.2f}")
(OUT/'LAB106C_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
