#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab121_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
COSTS=[0.0,2.81,7.5]
TPS=[1.5,2.0,3.0]
SLMODES=['ATR1','STRUCT3','STRUCT6']
MAX_HOLD_H=48
SEARCH_BARS=72

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
            if n.lower().endswith('.csv'):
                try:
                    with z.open(n) as f:d=pd.read_csv(f)
                    if len(d):fs.append(d)
                except:pass
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

# data
f=load_zip(FLOW_ZIP);tc=pick(f.columns,['create_time','time']);rc=pick(f.columns,['count_long_short_ratio','ratio']);oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
f=f[[tc,rc,oic]].copy();f['time']=ptime(f[tc]);f['ratio']=pd.to_numeric(f[rc],errors='coerce');f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna().sort_values('time').drop_duplicates('time',keep='last');f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean();sd=f.ratio.rolling(72,min_periods=72).std(ddof=0);f['z']=(f.ratio-mu)/sd.replace(0,np.nan);f['oi4h']=f.oi/f.oi.shift(48)-1

r=load_zip(PRICE_ZIP);pt=pick(r.columns,['time','timestamp','open_time']);po=pick(r.columns,['open']);ph=pick(r.columns,['high']);pl=pick(r.columns,['low']);pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1);tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean();h1['ema20']=h1.close.ewm(span=20,adjust=False).mean();h1['extension']=(h1.close-h1.ema20)/h1.atr;h1['close_time']=h1.time+pd.Timedelta(hours=1)

h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean();h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
age=[];cur=0;pv=0
for v in h4.trend:
    if v!=0 and v==pv:cur+=1
    elif v!=0:cur=1
    else:cur=0
    age.append(cur);pv=v
h4['trend_age']=age;h4['close_time']=h4.time+pd.Timedelta(hours=4)

b=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','extension']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
b=pd.merge_asof(b.sort_values('time'),h4[['close_time','trend','trend_age']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
b=pd.merge_asof(b.sort_values('time'),f[['time','z','oi4h']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b=b.dropna(subset=['atr','extension','trend','trend_age','z','oi4h']).reset_index(drop=True)

trm=b.time<TRAIN_END
EXT80=float(b.loc[trm,'extension'].abs().quantile(.80));OI70=float(b.loc[trm,'oi4h'].quantile(.70))
BT=b.time.reset_index(drop=True);BO=b.open.to_numpy(float);BH=b.high.to_numpy(float);BL=b.low.to_numpy(float);BC=b.close.to_numpy(float);BA=b.atr.to_numpy(float);BZ=b.z.to_numpy(float)

# frozen CONTINUATION_4_12 + SWING3_BREAK
signals=[]
last=len(b)-1-MAX_HOLD_H*12-1
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1;trend=int(b.trend.iloc[i]);age=int(b.trend_age.iloc[i]);ext=float(b.extension.iloc[i]);oi=float(b.oi4h.iloc[i])
    if not(4<=age<=12):continue
    if trend==0 or trend==side:continue
    if not((side>0 and ext<0) or (side<0 and ext>0)):continue
    if abs(ext)<EXT80 or oi<OI70:continue
    atr=float(BA[i]);anchor=float(BC[i])
    # swing3 break
    trig=None
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:trig=j;break
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:trig=j;break
    if trig is None:continue
    ei=trig+1
    signals.append(dict(signal_i=i,trigger_i=trig,entry_i=ei,signal_time=BT.iloc[i],entry_time=BT.iloc[ei],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',side=side,atr=atr))
sig=pd.DataFrame(signals)

def stop_price(ei,side,atr,mode):
    entry=float(BO[ei])
    if mode=='ATR1':
        return entry-side*atr,atr
    n=3 if mode=='STRUCT3' else 6
    a=max(0,ei-n); 
    if side>0:
        px=float(np.min(BL[a:ei]));dist=entry-px
    else:
        px=float(np.max(BH[a:ei]));dist=px-entry
    # protect against absurdly tight/wide structural stop
    dist=max(dist,0.35*atr);dist=min(dist,2.0*atr)
    return entry-side*dist,dist

def sim_one(ei,side,atr,slmode,tpR,costbps):
    entry=float(BO[ei]);sl,dist=stop_price(ei,side,atr,slmode);tp=entry+side*tpR*dist
    end=min(ei+MAX_HOLD_H*12-1,len(b)-1);reason='TIME';gross=side*(BC[end]-entry)/dist;exit_i=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';exit_i=j;break
        if hs:gross=-1;reason='SL';exit_i=j;break
        if ht:gross=tpR;reason='TP';exit_i=j;break
    costR=(costbps/10000.0)*entry/dist
    return float(gross-costR),reason,exit_i,entry,dist

# one-position chronology per config
summary=[];trades=[]
for slm in SLMODES:
  for tpR in TPS:
    for cost in COSTS:
      open_until=pd.Timestamp.min.tz_localize('UTC');cumR=0.0;eqpts=[];trs=[]
      for _,r in sig.sort_values('entry_time').iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi,entry,dist=sim_one(int(r.entry_i),int(r.side),float(r.atr),slm,tpR,cost)
        start=cumR
        for j in range(int(r.entry_i),xi+1):
            mtm=int(r.side)*(BC[j]-entry)/dist-(cost/10000.0)*entry/dist
            if j==xi:mtm=net
            eqpts.append((BT.iloc[j],start+mtm))
        cumR+=net;open_until=BT.iloc[xi]
        trs.append(dict(sl_mode=slm,tp_r=tpR,cost_bps=cost,split=r['split'],signal_time=r.signal_time,entry_time=r.entry_time,exit_time=BT.iloc[xi],side='BUY' if r.side>0 else 'SELL',net_r=net,reason=reason,stop_atr=dist/r.atr))
      t=pd.DataFrame(trs)
      if t.empty:continue
      trades.append(t)
      eq=pd.DataFrame(eqpts,columns=['time','equity']).sort_values('time').drop_duplicates('time',keep='last')
      dd=(eq.equity.cummax()-eq.equity);maxdd=float(dd.max())
      eq['day']=eq.time.dt.floor('D');prev=0.;dds=[]
      for d,g in eq.groupby('day'):
        dds.append(float(prev-g.equity.min()));prev=float(g.equity.iloc[-1])
      months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
      for split in ['ALL','TRAIN','OOS']:
        q=t if split=='ALL' else t[t.split==split]
        if q.empty:continue
        pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
        summary.append(dict(sl_mode=slm,tp_r=tpR,cost_bps=cost,split=split,n=len(q),ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((q.net_r>0).mean()),total_r=float(q.net_r.sum()),tp_rate=float((q.reason=='TP').mean()),sl_rate=float(q.reason.isin(['SL','BOTH_STOP_FIRST']).mean()),time_rate=float((q.reason=='TIME').mean()),trades_month=(len(t)/months if split=='ALL' else np.nan),r_month=(t.net_r.sum()/months if split=='ALL' else np.nan),max_mtm_dd_r=(maxdd if split=='ALL' else np.nan),max_daily_dd_r=(max(dds) if split=='ALL' else np.nan),max_mtm_dd_pct_025=(maxdd*.25 if split=='ALL' else np.nan)))
pd.concat(trades,ignore_index=True).to_csv(OUT/'LAB121_trades.csv',index=False)
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB121_summary.csv',index=False)

# year by year at 2.81bps for all configs
yr=[]
tt=pd.concat(trades,ignore_index=True)
for slm in SLMODES:
  for tpR in TPS:
    q=tt[(tt.sl_mode==slm)&(tt.tp_r==tpR)&(tt.cost_bps==2.81)].copy()
    q['year']=q.entry_time.dt.year
    for y,g in q.groupby('year'):
      if len(g)<2:continue
      pos=g.loc[g.net_r>0,'net_r'].sum();neg=-g.loc[g.net_r<0,'net_r'].sum()
      yr.append(dict(sl_mode=slm,tp_r=tpR,year=int(y),n=len(g),ev=float(g.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,total_r=float(g.net_r.sum())))
pd.DataFrame(yr).to_csv(OUT/'LAB121_yearly.csv',index=False)

# report focused on 2.81 and 7.5
lines=['# LAB121 — CONTINUATION CAPITULATION EXECUTION TRANSFER','',
f'Frozen signal: LAB120 CONTINUATION_4_12 + SWING3_BREAK. Thresholds ext>={EXT80:.2f} H1 ATR, OI4h>={OI70:+.3%}.',
'Execution transfer: one-position chronology, next M5 open, max hold 48h, stop-first same-bar.',
'Stops: ATR1=1.0 H1 ATR; STRUCT3/STRUCT6 use prior 3/6 M5-bar extreme, clamped 0.35..2.0 H1 ATR. TP=1.5R/2R/3R.',
'Costs: 0/2.81/7.5 bps RT proxy. MTM DD uses 5m mark-to-market. 0.25% risk scaling shown for prop intuition.',
'Development OOS is repeatedly inspected; OOS N is tiny, so execution transfer is exploratory.','']
for cost in [2.81,7.5]:
    lines.append(f'## Cost {cost} bps')
    for slm in SLMODES:
        for tpR in TPS:
            a=sm[(sm.sl_mode==slm)&(sm.tp_r==tpR)&(sm.cost_bps==cost)&(sm.split=='ALL')]
            o=sm[(sm.sl_mode==slm)&(sm.tp_r==tpR)&(sm.cost_bps==cost)&(sm.split=='OOS')]
            if len(a):
                a=a.iloc[0];extra=''
                if len(o):
                    oo=o.iloc[0];extra=f" | OOS N={int(oo.n)} EV={oo.ev:+.3f} PF={oo.pf:.2f}"
                lines.append(f"- {slm} TP{tpR:.1f}R: ALL N={int(a.n)} EV={a.ev:+.3f} PF={a.pf:.2f} R/mo={a.r_month:+.2f} DD={a.max_mtm_dd_r:.1f}R ({a.max_mtm_dd_pct_025:.2f}%@0.25%){extra}")
    lines.append('')
(OUT/'LAB121_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB121_meta.json').write_text(json.dumps(dict(
  frozen_signal='CONTINUATION_4_12 + SWING3_BREAK',ext80=EXT80,oi70=OI70,
  sl_modes=SLMODES,tp_r=TPS,cost_bps=COSTS,max_hold_h=MAX_HOLD_H,
  caveat='research only; OOS tiny and repeatedly inspected; costs proxy; no swap/funding/slippage beyond bps'
),indent=2))
print('\n'.join(lines))
