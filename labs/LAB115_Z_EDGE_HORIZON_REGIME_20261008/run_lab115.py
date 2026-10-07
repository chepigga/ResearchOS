#!/usr/bin/env python3
from __future__ import annotations
import math,re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab115_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
HOURS=[1,2,4,8,12,24,36,48]

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
            if not n.lower().endswith('.csv'):continue
            try:
                with z.open(n) as f:d=pd.read_csv(f)
                if len(d):frames.append(d)
            except:pass
        if not frames:raise RuntimeError(f'no csv in {zp}')
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

# Flow / Z
flow=load_zip(FLOW_ZIP)
tc=pick(flow.columns,['create_time','time','timestamp'])
rc=pick(flow.columns,['count_long_short_ratio','long_short_ratio','ratio'])
flow=flow[[tc,rc]].copy(); flow['time']=ptime(flow[tc]); flow['ratio']=pd.to_numeric(flow[rc],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(72,min_periods=72).mean(); sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)

# Price
raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','datetime','open_time']);po=pick(raw.columns,['open']);ph=pick(raw.columns,['high']);pl=pick(raw.columns,['low']);pc=pick(raw.columns,['close'])
p=raw[[pt,po,ph,pl,pc]].copy(); p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# H1 ATR
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prev=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
h1['atr_h1']=tr.rolling(14,min_periods=14).mean()
h1['ema50']=h1.close.ewm(span=50,adjust=False).mean()
h1['ema50_lag12']=h1.ema50.shift(12)
h1['trend_h1']=np.where((h1.close>h1.ema50)&(h1.ema50>h1.ema50_lag12),1,np.where((h1.close<h1.ema50)&(h1.ema50<h1.ema50_lag12),-1,0))
h1['close_time']=h1.time+pd.Timedelta(hours=1)

# H4 trend
h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean()
h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend_h4']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
h4['close_time']=h4.time+pd.Timedelta(hours=4)

# D1 macro trend
d1=p.set_index('time').resample('1D',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
d1['sma200']=d1.close.rolling(200,min_periods=200).mean()
d1['sma200_lag20']=d1.sma200.shift(20)
d1['trend_d1']=np.where((d1.close>d1.sma200)&(d1.sma200>d1.sma200_lag20),1,np.where((d1.close<d1.sma200)&(d1.sma200<d1.sma200_lag20),-1,0))
d1['close_time']=d1.time+pd.Timedelta(days=1)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1','trend_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),h4[['close_time','trend_h4']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
base=pd.merge_asof(base.sort_values('time'),d1[['close_time','trend_d1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_d1'))
base=pd.merge_asof(base.sort_values('time'),flow[['time','z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['atr_h1','trend_h1','trend_h4','trend_d1','z']).reset_index(drop=True)

# causal rolling volatility regime from H1 ATR percentile over prior 60d
h1v=h1[['close_time','atr_h1']].dropna().copy()
# rolling 1440 h =60d percentile rank approximated by rolling quantiles
h1v['q33']=h1v.atr_h1.rolling(1440,min_periods=480).quantile(1/3)
h1v['q67']=h1v.atr_h1.rolling(1440,min_periods=480).quantile(2/3)
base=pd.merge_asof(base.sort_values('time'),h1v[['close_time','q33','q67']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=base.dropna(subset=['q33','q67']).reset_index(drop=True)
base['vol_regime']=np.where(base.atr_h1<base.q33,'LOW',np.where(base.atr_h1>base.q67,'HIGH','MID'))

BT=base.time.reset_index(drop=True);BH=base.high.to_numpy(float);BL=base.low.to_numpy(float);BC=base.close.to_numpy(float);BA=base.atr_h1.to_numpy(float);BZ=base.z.to_numpy(float)

def regname(v): return 'UP' if v>0 else ('DOWN' if v<0 else 'SIDE')
events=[]
last=len(base)-1-max(HOURS)*12
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1;anchor=float(BC[i]);atr=float(BA[i])
    if atr<=0 or not np.isfinite(atr):continue
    row=dict(signal_time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',year=int(BT.iloc[i].year),month=str(BT.iloc[i].to_period('M')),
             side='BUY' if side>0 else 'SELL',side_num=side,z=float(BZ[i]),abs_z=abs(float(BZ[i])),
             h1_regime=regname(int(base.trend_h1.iloc[i])),h4_regime=regname(int(base.trend_h4.iloc[i])),d1_regime=regname(int(base.trend_d1.iloc[i])),
             vol_regime=base.vol_regime.iloc[i],
             h1_with=int(base.trend_h1.iloc[i])==side,h4_with=int(base.trend_h4.iloc[i])==side,d1_with=int(base.trend_d1.iloc[i])==side)
    for h in HOURS:
        e=i+h*12
        hi=float(BH[i+1:e+1].max());lo=float(BL[i+1:e+1].min());cl=float(BC[e])
        row[f'mfe_{h}h']=(hi-anchor)/atr if side>0 else (anchor-lo)/atr
        row[f'mae_{h}h']=(anchor-lo)/atr if side>0 else (hi-anchor)/atr
        row[f'close_{h}h']=side*(cl-anchor)/atr
    events.append(row)
ev=pd.DataFrame(events);ev.to_csv(OUT/'LAB115_event_atlas.csv',index=False)

def met(g,h):
    x=g[f'close_{h}h'].to_numpy(float);mfe=g[f'mfe_{h}h'].to_numpy(float);mae=g[f'mae_{h}h'].to_numpy(float)
    mean=float(x.mean());sd=float(x.std(ddof=1)) if len(x)>1 else np.nan;noise=float(np.mean((mfe+mae)/2))
    return dict(n=len(g),mean_close=mean,p_positive=float((x>0).mean()),mean_mfe=float(mfe.mean()),mean_mae=float(mae.mean()),
                mfe_mae_ratio=float(mfe.mean()/mae.mean()) if mae.mean()>0 else np.nan,
                dnr_std=mean/sd if sd>0 else np.nan,dnr_range=mean/noise if noise>0 else np.nan)

# overall horizon curve
overall=[]
for split in ['TRAIN','OOS','ALL']:
    g=ev if split=='ALL' else ev[ev.split==split]
    for h in HOURS: overall.append(dict(split=split,horizon_h=h,**met(g,h)))
pd.DataFrame(overall).to_csv(OUT/'LAB115_overall_horizon.csv',index=False)

# one-dimensional regimes
dims=['h1_regime','h4_regime','d1_regime','vol_regime','h1_with','h4_with','d1_with','side']
rows=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for dim in dims:
        for group,g in q.groupby(dim):
            if len(g)<30:continue
            for h in HOURS: rows.append(dict(split=split,dimension=dim,group=str(group),horizon_h=h,**met(g,h)))
pd.DataFrame(rows).to_csv(OUT/'LAB115_regime_atlas.csv',index=False)

# compact 2D: H4 relation to signal x volatility regime
cross=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for (hw,vr),g in q.groupby(['h4_with','vol_regime']):
        if len(g)<50:continue
        for h in HOURS:cross.append(dict(split=split,h4_with=bool(hw),vol_regime=vr,horizon_h=h,**met(g,h)))
pd.DataFrame(cross).to_csv(OUT/'LAB115_h4xvol.csv',index=False)

# rolling 60-day horizon map stepping 14 days
roll=[]
start=ev.signal_time.min().floor('D');end=ev.signal_time.max().floor('D')
for t in pd.date_range(start,end,freq='14D',tz='UTC'):
    g=ev[(ev.signal_time>=t-pd.Timedelta(days=60))&(ev.signal_time<t)]
    if len(g)<100:continue
    for h in HOURS:
        m=met(g,h);roll.append(dict(window_end=t,n_events=len(g),horizon_h=h,**m))
pd.DataFrame(roll).to_csv(OUT/'LAB115_rolling60d.csv',index=False)

# find dominant horizon per rolling window, descriptive only
rr=pd.DataFrame(roll)
dom=[]
for t,g in rr.groupby('window_end'):
    z=g.sort_values('dnr_std',ascending=False).iloc[0]
    dom.append(dict(window_end=t,best_horizon_h=int(z.horizon_h),best_dnr=float(z.dnr_std),best_mean=float(z.mean_close),n=int(z.n)))
pd.DataFrame(dom).to_csv(OUT/'LAB115_rolling_dominant_horizon.csv',index=False)

# 2026 monthly horizon map
mon=[]
for m,g in ev[ev.year==2026].groupby('month'):
    if len(g)<30:continue
    for h in HOURS:mon.append(dict(month=m,horizon_h=h,**met(g,h)))
pd.DataFrame(mon).to_csv(OUT/'LAB115_2026_monthly.csv',index=False)

# report
ov=pd.DataFrame(overall);rg=pd.DataFrame(rows);mx=pd.DataFrame(mon)
lines=['# LAB115 — Z EDGE × HORIZON × REGIME','',
'Question: is Z a regime-dependent horizon signal rather than a stable intraday timing signal?',
'Signal is frozen: fresh |Z|>=1 inverse-crowd. No execution rule, no SL/TP optimization.',
'Regimes are causal at signal time: H1 EMA50 trend, H4 EMA50 trend, D1 SMA200 macro trend, and H1 ATR low/mid/high versus trailing 60d quantiles.',
'Rolling map uses prior 60d windows stepped every 14d.','',
'## Overall horizon curve']
for split in ['TRAIN','OOS']:
    vals=[]
    for _,r in ov[ov.split==split].iterrows():
        vals.append(f"{int(r.horizon_h)}h:{r.mean_close:+.3f}ATR/DNR{r.dnr_std:+.3f}")
    lines.append(f"- {split}: "+' | '.join(vals))
lines+=['','## 2026 monthly 4h vs 24h vs 48h']
for m,g in mx.groupby('month'):
    vals=[]
    for h in [4,24,48]:
        z=g[g.horizon_h==h]
        if len(z):
            r=z.iloc[0]; vals.append(f"{h}h {r.mean_close:+.3f}/DNR{r.dnr_std:+.3f}")
    lines.append(f"- {m}: "+' | '.join(vals))
lines+=['','## OOS H4 alignment']
for grp in ['True','False']:
    g=rg[(rg.split=='OOS')&(rg.dimension=='h4_with')&(rg.group==grp)&(rg.horizon_h.isin([4,12,24,48]))]
    if len(g):
        vals=[f"{int(r.horizon_h)}h {r.mean_close:+.3f}/DNR{r.dnr_std:+.3f}" for _,r in g.iterrows()]
        lines.append(f"- H4_with={grp}: "+' | '.join(vals))
lines+=['','## OOS volatility regime']
for vr in ['LOW','MID','HIGH']:
    g=rg[(rg.split=='OOS')&(rg.dimension=='vol_regime')&(rg.group==vr)&(rg.horizon_h.isin([4,12,24,48]))]
    if len(g):
        vals=[f"{int(r.horizon_h)}h {r.mean_close:+.3f}/DNR{r.dnr_std:+.3f}" for _,r in g.iterrows()]
        lines.append(f"- {vr}: "+' | '.join(vals))
(OUT/'LAB115_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB115_meta.json').write_text(json.dumps(dict(signal='fresh |Z|>=1 inverse crowd',horizons_h=HOURS,train_end=str(TRAIN_END),
    regimes=['H1 EMA50 slope+price','H4 EMA50 slope+price','D1 SMA200 slope+price','H1 ATR trailing60d tertile'],
    caveat='OOS 2025-26 repeatedly inspected in prior labs; this is development evidence, not pristine validation'),indent=2))
print('\n'.join(lines))
