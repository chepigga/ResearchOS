#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab122_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
MAX_H=48
SEARCH_BARS=72
COSTS=[2.81,7.5]

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
        fs=[]
        for n in z.namelist():
            if not n.lower().endswith('.csv'):continue
            try:
                with z.open(n) as f:d=pd.read_csv(f)
                if len(d):fs.append(d)
            except:pass
        if not fs:raise RuntimeError(f'no csv in {zp}')
        common=set(fs[0].columns)
        for d in fs[1:]:common&=set(d.columns)
        if len(fs)>1 and len(common)>=4:
            cols=list(common);return pd.concat([d[cols] for d in fs],ignore_index=True)
        return fs[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce');med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# ---------- Data ----------
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time']);rc=pick(f.columns,['count_long_short_ratio','ratio']);oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
f=f[[tc,rc,oic]].copy();f['time']=ptime(f[tc]);f['ratio']=pd.to_numeric(f[rc],errors='coerce');f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna().sort_values('time').drop_duplicates('time',keep='last');f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean();sd=f.ratio.rolling(72,min_periods=72).std(ddof=0)
f['z']=(f.ratio-mu)/sd.replace(0,np.nan);f['oi4h']=f.oi/f.oi.shift(48)-1

r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']);po=pick(r.columns,['open']);ph=pick(r.columns,['high']);pl=pick(r.columns,['low']);pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean();h1['ema20']=h1.close.ewm(span=20,adjust=False).mean();h1['extension']=(h1.close-h1.ema20)/h1.atr;h1['close_time']=h1.time+pd.Timedelta(hours=1)

h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean();h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
h4prev=h4.close.shift(1);h4tr=pd.concat([(h4.high-h4.low),(h4.high-h4prev).abs(),(h4.low-h4prev).abs()],axis=1).max(axis=1)
h4['atr14']=h4tr.rolling(14,min_periods=14).mean();h4['body_atr']=(h4.close-h4.open)/h4.atr14
age=[];cur=0;pv=0
for v in h4.trend:
    if v!=0 and v==pv:cur+=1
    elif v!=0:cur=1
    else:cur=0
    age.append(cur);pv=v
h4['trend_age']=age
imp=((h4.body_atr.abs()>=0.8)&(np.sign(h4.body_atr)==h4.trend))
ia=[];cnt=999
for x in imp.fillna(False):
    cnt=0 if x else min(cnt+1,999);ia.append(cnt)
h4['impulse_age']=ia;h4['close_time']=h4.time+pd.Timedelta(hours=4)

d1=p.set_index('time').resample('1D',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
d1['ema50']=d1.close.ewm(span=50,adjust=False).mean();d1['ema50_lag10']=d1.ema50.shift(10)
d1['trend']=np.where((d1.close>d1.ema50)&(d1.ema50>d1.ema50_lag10),1,np.where((d1.close<d1.ema50)&(d1.ema50<d1.ema50_lag10),-1,0))
d1['close_time']=d1.time+pd.Timedelta(days=1)

b=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','extension']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
b=pd.merge_asof(b.sort_values('time'),h4[['close_time','trend','trend_age','impulse_age']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
b=pd.merge_asof(b.sort_values('time'),d1[['close_time','trend']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_d1'))
b.rename(columns={'trend':'trend_h4','trend_d1':'trend_d1'},inplace=True)
b=pd.merge_asof(b.sort_values('time'),f[['time','z','oi4h']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b=b.dropna(subset=['atr','extension','trend_h4','trend_age','impulse_age','trend_d1','z','oi4h']).reset_index(drop=True)

trm=b.time<TRAIN_END
EXT80=float(b.loc[trm,'extension'].abs().quantile(.80));OI70=float(b.loc[trm,'oi4h'].quantile(.70))
BT=b.time.reset_index(drop=True);BO=b.open.to_numpy(float);BH=b.high.to_numpy(float);BL=b.low.to_numpy(float);BC=b.close.to_numpy(float);BA=b.atr.to_numpy(float);BZ=b.z.to_numpy(float)

def swing3_entry(i,side):
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:return j+1,j
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:return j+1,j
    return None,None

def phase(age,imp_age):
    if age<=3:return 'BIRTH'
    if imp_age<=2:return 'REACCEL'
    if age<=12:return 'CONT'
    return 'OTHER'

# Candidate legs are predeclared, not selected on OOS:
# 1 CORE_CONT: frozen LAB121 continuation capitulation.
# 2 REACCEL: same CAP_BASE + reaccel phase.
# 3 BIRTH: same CAP_BASE + birth phase.
# 4 TREND_SQUEEZE: inverse-crowd side aligned H4 & D1 + OI build (not capitulation), same SWING3 confirmation.
signals=[]
last=len(b)-1-MAX_H*12-1
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1
    h4t=int(b.trend_h4.iloc[i]);d1t=int(b.trend_d1.iloc[i]);age=int(b.trend_age.iloc[i]);imp_age=int(b.impulse_age.iloc[i]);ext=float(b.extension.iloc[i]);oi=float(b.oi4h.iloc[i])
    phs=phase(age,imp_age)
    legs=[]
    ext_against=(side>0 and ext<0) or (side<0 and ext>0)
    if h4t!=0 and h4t!=side and ext_against and abs(ext)>=EXT80 and oi>=OI70:
        if phs=='CONT':legs.append('CORE_CONT')
        if phs=='REACCEL':legs.append('REACCEL')
        if phs=='BIRTH':legs.append('BIRTH')
    if h4t==side and d1t==side and oi>=OI70:
        legs.append('TREND_SQUEEZE')
    if not legs:continue
    ei,trig=swing3_entry(i,side)
    if ei is None:continue
    for leg in legs:
        signals.append(dict(leg=leg,signal_i=i,entry_i=ei,signal_time=BT.iloc[i],entry_time=BT.iloc[ei],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',side=side,atr=float(BA[i])))
sig=pd.DataFrame(signals)
sig.to_csv(OUT/'LAB122_signal_candidates.csv',index=False)

def sim_one(ei,side,atr,costbps):
    entry=float(BO[ei]);dist=atr;sl=entry-side*dist;tp=entry+side*3.0*dist;end=min(ei+MAX_H*12-1,len(b)-1)
    gross=side*(BC[end]-entry)/dist;reason='TIME';xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
        if hs:gross=-1;reason='SL';xi=j;break
        if ht:gross=3.0;reason='TP';xi=j;break
    costR=(costbps/10000.0)*entry/dist
    return gross-costR,reason,xi,entry,dist

PORTS={
'CORE':['CORE_CONT'],
'CORE_REACCEL':['CORE_CONT','REACCEL'],
'CORE_BIRTH':['CORE_CONT','BIRTH'],
'CORE_REACCEL_BIRTH':['CORE_CONT','REACCEL','BIRTH'],
'CORE_TREND':['CORE_CONT','TREND_SQUEEZE'],
'FULL_4LEG':['CORE_CONT','REACCEL','BIRTH','TREND_SQUEEZE']
}

alltr=[];summary=[]
for cost in COSTS:
  for pname,legs in PORTS.items():
    s=sig[sig.leg.isin(legs)].sort_values(['entry_time','leg']).copy()
    # Deduplicate same underlying signal/entry if multiple legs happen to map to it.
    s=s.drop_duplicates(['signal_time','entry_time','side'],keep='first')
    open_until=pd.Timestamp.min.tz_localize('UTC');cum=0.;eqpts=[];trs=[]
    for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi,entry,dist=sim_one(int(r.entry_i),int(r.side),float(r.atr),cost)
        st=cum
        for j in range(int(r.entry_i),xi+1):
            mtm=int(r.side)*(BC[j]-entry)/dist-(cost/10000.0)*entry/dist
            if j==xi:mtm=net
            eqpts.append((BT.iloc[j],st+mtm))
        cum+=net;open_until=BT.iloc[xi]
        trs.append(dict(portfolio=pname,cost_bps=cost,leg=r.leg,split=r['split'],signal_time=r.signal_time,entry_time=r.entry_time,exit_time=BT.iloc[xi],side='BUY' if r.side>0 else 'SELL',net_r=net,reason=reason))
    t=pd.DataFrame(trs)
    if t.empty:continue
    alltr.append(t)
    eq=pd.DataFrame(eqpts,columns=['time','equity']).sort_values('time').drop_duplicates('time',keep='last')
    maxdd=float((eq.equity.cummax()-eq.equity).max())
    eq['day']=eq.time.dt.floor('D');prev=0.;dds=[]
    for d,g in eq.groupby('day'):
        dds.append(float(prev-g.equity.min()));prev=float(g.equity.iloc[-1])
    months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
    for split in ['ALL','TRAIN','OOS']:
        q=t if split=='ALL' else t[t.split==split]
        if q.empty:continue
        pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
        summary.append(dict(portfolio=pname,cost_bps=cost,split=split,n=len(q),ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((q.net_r>0).mean()),total_r=float(q.net_r.sum()),trades_month=(len(t)/months if split=='ALL' else np.nan),r_month=(t.net_r.sum()/months if split=='ALL' else np.nan),max_mtm_dd_r=(maxdd if split=='ALL' else np.nan),max_daily_dd_r=(max(dds) if split=='ALL' else np.nan),dd_pct_025=(maxdd*.25 if split=='ALL' else np.nan)))
pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB122_portfolio_trades.csv',index=False)
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB122_portfolio_summary.csv',index=False)

# leg standalone stats under same one-position shell, for attribution
legsum=[]
for cost in COSTS:
  for leg in ['CORE_CONT','REACCEL','BIRTH','TREND_SQUEEZE']:
    s=sig[sig.leg==leg].sort_values('entry_time')
    open_until=pd.Timestamp.min.tz_localize('UTC');trs=[]
    for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi,entry,dist=sim_one(int(r.entry_i),int(r.side),float(r.atr),cost)
        open_until=BT.iloc[xi]
        trs.append(dict(split=r['split'],net_r=net,reason=reason,entry_time=r.entry_time,exit_time=BT.iloc[xi]))
    t=pd.DataFrame(trs)
    if t.empty:continue
    for split in ['ALL','TRAIN','OOS']:
        q=t if split=='ALL' else t[t.split==split]
        if q.empty:continue
        pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
        legsum.append(dict(leg=leg,cost_bps=cost,split=split,n=len(q),ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,total_r=float(q.net_r.sum())))
pd.DataFrame(legsum).to_csv(OUT/'LAB122_leg_attribution.csv',index=False)

# yearly 2.81 only
yr=[]
tt=pd.concat(alltr,ignore_index=True)
for pname in PORTS:
    q=tt[(tt.portfolio==pname)&(tt.cost_bps==2.81)].copy();q['year']=q.entry_time.dt.year
    for y,g in q.groupby('year'):
        if len(g)<2:continue
        pos=g.loc[g.net_r>0,'net_r'].sum();neg=-g.loc[g.net_r<0,'net_r'].sum()
        yr.append(dict(portfolio=pname,year=int(y),n=len(g),ev=float(g.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,total_r=float(g.net_r.sum())))
pd.DataFrame(yr).to_csv(OUT/'LAB122_yearly.csv',index=False)

lines=['# LAB122 — CAPITULATION PORTFOLIO EXPANSION','',
f'Frozen execution for every leg: SWING3_BREAK -> next M5 open, SL=1 H1 ATR, TP=3R, max hold 48h, one-position chronology. Costs 2.81/7.5 bps.',
f'Frozen CAP thresholds ext>={EXT80:.2f} H1 ATR, OI4h>={OI70:+.3%}. No threshold relaxation.',
'Candidate legs: CORE_CONT (LAB121 core), REACCEL, BIRTH, and TREND_SQUEEZE (inverse-crowd direction aligned with H4 & D1 + OI build).',
'Portfolio variants are predeclared combinations; no OOS-based selection. Development OOS remains repeatedly inspected and small.','']
for cost in COSTS:
    lines.append(f'## Cost {cost} bps')
    for pname in PORTS:
        a=sm[(sm.portfolio==pname)&(sm.cost_bps==cost)&(sm.split=='ALL')]
        o=sm[(sm.portfolio==pname)&(sm.cost_bps==cost)&(sm.split=='OOS')]
        if len(a):
            a=a.iloc[0];extra=''
            if len(o):
                oo=o.iloc[0];extra=f" | OOS N={int(oo.n)} EV={oo.ev:+.3f} PF={oo.pf:.2f}"
            lines.append(f"- {pname}: N={int(a.n)} ({a.trades_month:.2f}/mo) EV={a.ev:+.3f} PF={a.pf:.2f} R/mo={a.r_month:+.2f} DD={a.max_mtm_dd_r:.1f}R ({a.dd_pct_025:.2f}%@0.25%){extra}")
    lines.append('')
lines.append('## Standalone leg attribution @2.81bps')
ls=pd.DataFrame(legsum)
for leg in ['CORE_CONT','REACCEL','BIRTH','TREND_SQUEEZE']:
    a=ls[(ls.leg==leg)&(ls.cost_bps==2.81)&(ls.split=='ALL')]
    o=ls[(ls.leg==leg)&(ls.cost_bps==2.81)&(ls.split=='OOS')]
    if len(a):
        aa=a.iloc[0];extra=''
        if len(o):
            oo=o.iloc[0];extra=f" | OOS N={int(oo.n)} EV={oo.ev:+.3f} PF={oo.pf:.2f}"
        lines.append(f"- {leg}: N={int(aa.n)} EV={aa.ev:+.3f} PF={aa.pf:.2f}{extra}")
(OUT/'LAB122_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB122_meta.json').write_text(json.dumps(dict(
    frozen_execution='SWING3_BREAK, next M5 open, SL1 H1 ATR, TP3R, 48h, one-position',
    candidate_legs=['CORE_CONT','REACCEL','BIRTH','TREND_SQUEEZE'],
    portfolios=PORTS,cost_bps=COSTS,
    caveat='research only; OOS repeatedly inspected and small; same instrument BTC so portfolio is signal-leg diversification, not asset diversification'
),indent=2))
print('\n'.join(lines))
