#!/usr/bin/env python3
from __future__ import annotations
import json,re,zipfile
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab102a_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
ZWIN=72
ATR_N=14

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
        frames=[]; names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        for n in names:
            try:
                with z.open(n) as f:d=pd.read_csv(f)
                if len(d):frames.append(d)
            except Exception: pass
        if not frames: raise RuntimeError(f"no csv in {zp}")
        common=set(frames[0].columns)
        for d in frames[1:]: common &= set(d.columns)
        if len(frames)>1 and len(common)>=4:
            cols=list(common); return pd.concat([d[cols] for d in frames],ignore_index=True),names
        return frames[0],names

def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),errors='coerce',utc=True)
    return pd.to_datetime(s,errors='coerce',utc=True)

flow,_=load_zip(FLOW_ZIP); price,_=load_zip(PRICE_ZIP)
ft=pick(flow.columns,['timestamp','time','datetime','open_time']); fr=pick(flow.columns,['longShortRatio','long_short_ratio','ls_ratio','globalLongShortAccountRatio','ratio'])
pt=pick(price.columns,['time','timestamp','datetime','open_time']); po=pick(price.columns,['open']); ph=pick(price.columns,['high']); pl=pick(price.columns,['low']); pc=pick(price.columns,['close'])
if ft is None or fr is None or None in [pt,po,ph,pl,pc]: raise RuntimeError("column inference failed")

flow=flow[[ft,fr]].copy(); flow['time']=ptime(flow[ft]); flow['ratio']=pd.to_numeric(flow[fr],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
m=flow.ratio.rolling(ZWIN,min_periods=ZWIN).mean(); sd=flow.ratio.rolling(ZWIN,min_periods=ZWIN).std(ddof=0)
flow['z']=(flow.ratio-m)/sd.replace(0,np.nan)

price=price[[pt,po,ph,pl,pc]].copy(); price['time']=ptime(price[pt])
for c,nm in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]: price[nm]=pd.to_numeric(price[c],errors='coerce')
price=price[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
price=price.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

def tfbars(tf):
    p=price.set_index('time').resample(f'{tf}min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    p['close_time']=p.time+pd.Timedelta(minutes=tf)
    prev=p.close.shift(1); tr=pd.concat([(p.high-p.low),(p.high-prev).abs(),(p.low-prev).abs()],axis=1).max(axis=1)
    p['atr']=tr.rolling(ATR_N,min_periods=ATR_N).mean()
    p=pd.merge_asof(p.sort_values('close_time'),flow[['time','z']].dropna().sort_values('time'),left_on='close_time',right_on='time',direction='backward',tolerance=pd.Timedelta('10min'),suffixes=('','_z'))
    return p.dropna(subset=['atr','z']).reset_index(drop=True)

def classify(side,z):
    if abs(z)<1.0:return 'NEUTRAL'
    if (side>0 and z>=1.0) or (side<0 and z<=-1.0):return 'WITH_CROWD'
    return 'AGAINST_CROWD'

def sim(tf,lookback,sl_atr,tp_r,timeout):
    p=tfbars(tf); rows=[]; open_until=-1
    for i in range(max(ATR_N,lookback),len(p)-1):
        if i<=open_until: continue
        hi=float(p.high.iloc[i-lookback:i].max()); lo=float(p.low.iloc[i-lookback:i].min()); c=float(p.close.iloc[i])
        side=1 if c>hi else (-1 if c<lo else 0)
        if side==0: continue
        atr=float(p.atr.iloc[i]); entry=float(p.open.iloc[i+1]); stop=entry-side*sl_atr*atr; target=entry+side*tp_r*sl_atr*atr
        end=min(i+1+timeout,len(p)-1); exit_px=float(p.close.iloc[end]); reason='TIME'; ex=end
        for j in range(i+1,end+1):
            h=float(p.high.iloc[j]); l=float(p.low.iloc[j])
            hs=(l<=stop) if side>0 else (h>=stop); ht=(h>=target) if side>0 else (l<=target)
            if hs and ht: exit_px=stop; reason='SL_COLLISION'; ex=j; break
            if hs: exit_px=stop; reason='SL'; ex=j; break
            if ht: exit_px=target; reason='TP'; ex=j; break
        r=side*(exit_px-entry)/(sl_atr*atr)
        z=float(p.z.iloc[i])
        rows.append(dict(tf=tf,lookback=lookback,entry_time=p.time.iloc[i+1],side=side,z=z,bucket=classify(side,z),R=r,reason=reason))
        open_until=ex
    return pd.DataFrame(rows)

def metrics(q):
    x=q.R.to_numpy(float)
    if len(x)==0:return dict(n=0,ev=np.nan,pf=np.nan,wr=np.nan,sumr=0,dd=np.nan)
    pos=x[x>0].sum(); neg=-x[x<0].sum(); eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=float(np.max(pk[1:]-eq))
    return dict(n=len(x),ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),sumr=float(x.sum()),dd=dd)

trades=[]; sums=[]
for tf in [15,30]:
  for lb in [1,4]:
    t=sim(tf,lb,1.5,2.0,16); trades.append(t)
    for split,a,b in [('TRAIN','2021-01-01','2025-01-01'),('OOS','2025-01-01','2026-09-01'),('ALL','2021-01-01','2026-09-01')]:
      q=t[(t.entry_time>=pd.Timestamp(a,tz='UTC'))&(t.entry_time<pd.Timestamp(b,tz='UTC'))]
      for bucket in ['WITH_CROWD','AGAINST_CROWD','NEUTRAL','ALL']:
        z=q if bucket=='ALL' else q[q.bucket==bucket]
        row=dict(tf=tf,lookback=lb,split=split,bucket=bucket,**metrics(z)); sums.append(row)
alltr=pd.concat(trades,ignore_index=True); summ=pd.DataFrame(sums)
alltr.to_csv(OUT/'LAB102A_trades.csv',index=False); summ.to_csv(OUT/'LAB102A_summary.csv',index=False)

# filter effect: baseline vs removing WITH_CROWD
frows=[]
for (tf,lb,split),g in summ[summ.bucket.isin(['WITH_CROWD','AGAINST_CROWD','NEUTRAL','ALL'])].groupby(['tf','lookback','split']):
    pass
for tf in [15,30]:
  for lb in [1,4]:
    t=alltr[(alltr.tf==tf)&(alltr.lookback==lb)]
    for split,a,b in [('TRAIN','2021-01-01','2025-01-01'),('OOS','2025-01-01','2026-09-01')]:
      q=t[(t.entry_time>=pd.Timestamp(a,tz='UTC'))&(t.entry_time<pd.Timestamp(b,tz='UTC'))]
      m0=metrics(q); mf=metrics(q[q.bucket!='WITH_CROWD'])
      frows.append(dict(tf=tf,lookback=lb,split=split,base_n=m0['n'],base_ev=m0['ev'],base_pf=m0['pf'],base_dd=m0['dd'],filtered_n=mf['n'],filtered_ev=mf['ev'],filtered_pf=mf['pf'],filtered_dd=mf['dd'],delta_ev=mf['ev']-m0['ev']))
filt=pd.DataFrame(frows); filt.to_csv(OUT/'LAB102A_filter_effect.csv',index=False)

lines=['# LAB102A — Z as directional filter on independent price-only structure entries','',
'Entry universe deliberately does NOT use Z: close beyond prior 1 or 4 TF bars, entry next bar open, SL 1.5 ATR, TP 2R, timeout 16 bars.',
'Z is only an overlay classifier: WITH_CROWD / AGAINST_CROWD / NEUTRAL.','']
for _,r in filt.iterrows():
    lines.append(f"- TF{int(r.tf)} L{int(r.lookback)} {r.split}: base N={int(r.base_n)} EV={r.base_ev:+.3f} PF={r.base_pf:.2f} DD={r.base_dd:.1f}R -> block WITH_CROWD: N={int(r.filtered_n)} EV={r.filtered_ev:+.3f} PF={r.filtered_pf:.2f} DD={r.filtered_dd:.1f}R ΔEV={r.delta_ev:+.3f}")
(OUT/'LAB102A_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
