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

