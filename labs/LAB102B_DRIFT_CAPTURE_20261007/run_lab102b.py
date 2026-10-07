#!/usr/bin/env python3
from __future__ import annotations
import json,re,zipfile
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab102b_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
ZWIN=72
ATR_N=14
SETUP_Z=1.0
ARM_PULLBACK=0.10

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
# M5 ATR and H1 ATR projected to M5
prev=price.close.shift(1); tr=pd.concat([(price.high-price.low),(price.high-prev).abs(),(price.low-prev).abs()],axis=1).max(axis=1)
price['atr5']=tr.rolling(ATR_N,min_periods=ATR_N).mean()
h1=price.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prevh=h1.close.shift(1); trh=pd.concat([(h1.high-h1.low),(h1.high-prevh).abs(),(h1.low-prevh).abs()],axis=1).max(axis=1)
h1['atr_h1']=trh.rolling(ATR_N,min_periods=ATR_N).mean(); h1['close_time']=h1.time+pd.Timedelta(hours=1)
base=pd.merge_asof(price.sort_values('time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),flow[['time','z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min')).dropna(subset=['z','atr_h1']).reset_index(drop=True)

# M30 bars for STRUCT4 trigger
m30=base.set_index('time').resample('30min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),z=('z','last'),atr_h1=('atr_h1','last')).dropna().reset_index()
m30['close_time']=m30.time+pd.Timedelta(minutes=30)

def setup_episodes():
    # episodes begin on crossing into |Z|>=1; side inverse crowd
    z=base.z.to_numpy(float); rows=[]; active=False
    for i in range(1,len(base)-1):
        now=abs(z[i])>=SETUP_Z; prev=abs(z[i-1])>=SETUP_Z
        if now and not prev:
            side=-1 if z[i]>0 else 1
            rows.append(dict(setup_i=i,setup_time=base.time.iloc[i],side=side,z_setup=float(z[i])))
    return pd.DataFrame(rows)

eps=setup_episodes()

def entry_from_episode(r,mode):
    si=int(r.setup_i); side=int(r.side); z0=float(r.z_setup)
    if mode=='SETUP':
        ei=si+1
        return ei if ei<len(base) else None
    if mode=='ARMED':
        extreme=z0
        deadline=min(si+36,len(base)-2) # 3h max wait
        for j in range(si+1,deadline+1):
            zj=float(base.z.iloc[j])
            if side<0:
                extreme=max(extreme,zj)
                if extreme-zj>=ARM_PULLBACK:return j+1
            else:
                extreme=min(extreme,zj)
                if zj-extreme>=ARM_PULLBACK:return j+1
        return None
    if mode=='STRUCT4':
        t0=base.time.iloc[si]
        k0=int(m30.close_time.searchsorted(t0,side='right'))
        for k in range(max(4,k0),min(k0+8,len(m30)-1)): # up to 4h wait
            hi=float(m30.high.iloc[k-4:k].max()); lo=float(m30.low.iloc[k-4:k].min()); c=float(m30.close.iloc[k])
            ok=(c>hi) if side>0 else (c<lo)
            if ok:
                et=m30.time.iloc[k+1]
                ei=int(base.time.searchsorted(et,side='left'))
                return ei if ei<len(base) else None
        return None
    return None

def simulate(mode,stop_mult,exit_mode,cost_bps):
    rows=[]; open_until=-1
    for r in eps.itertuples():
        ei=entry_from_episode(r,mode)
        if ei is None or ei<=open_until or ei>=len(base)-1: continue
        entry=float(base.open.iloc[ei]); atr=float(base.atr_h1.iloc[ei]); side=int(r.side)
        if not np.isfinite(atr) or atr<=0: continue
        stop=entry-side*stop_mult*atr
        if exit_mode=='Z0_24H': max_bars=288
        elif exit_mode=='Z0_48H': max_bars=576
        elif exit_mode=='TIME24': max_bars=288
        elif exit_mode=='TIME48': max_bars=576
        else: raise KeyError(exit_mode)
        end=min(ei+max_bars,len(base)-1); exit_px=float(base.close.iloc[end]); reason='TIME'; ex=end
        mfe=0; mae=0
        for j in range(ei,end+1):
            h=float(base.high.iloc[j]); l=float(base.low.iloc[j]); c=float(base.close.iloc[j]); z=float(base.z.iloc[j])
            fav=((h-entry) if side>0 else (entry-l))/atr
            adv=((entry-l) if side>0 else (h-entry))/atr
            mfe=max(mfe,fav); mae=max(mae,adv)
            hs=(l<=stop) if side>0 else (h>=stop)
            if hs:
                exit_px=stop; reason='SL'; ex=j; break
            if exit_mode.startswith('Z0'):
                crossed=(z>=0) if side>0 else (z<=0)
                if crossed:
                    exit_px=c; reason='Z0'; ex=j; break
        gross=side*(exit_px-entry)/(stop_mult*atr)
        cost=(entry*(cost_bps/10000.0))/(stop_mult*atr)
        net=gross-cost
        rows.append(dict(mode=mode,stop_mult=stop_mult,exit_mode=exit_mode,cost_bps=cost_bps,
                         setup_time=r.setup_time,entry_time=base.time.iloc[ei],exit_time=base.time.iloc[ex],side=side,z_setup=r.z_setup,
                         gross_r=gross,net_r=net,mfe_atr=mfe,mae_atr=mae,reason=reason,hold_h=(ex-ei)*5/60))
        open_until=ex
    return pd.DataFrame(rows)

def metrics(t):
    if len(t)==0:return {}
    x=t.net_r.to_numpy(float); pos=x[x>0].sum(); neg=-x[x<0].sum()
    eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=float(np.max(pk[1:]-eq))
    return dict(n=len(t),ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),sumr=float(x.sum()),dd=dd,
                med_hold=float(t.hold_h.median()),med_mfe_atr=float(t.mfe_atr.median()),med_mae_atr=float(t.mae_atr.median()))

sums=[]; alltr=[]
for mode in ['SETUP','ARMED','STRUCT4']:
  for sm in [2.0,2.5,3.0]:
    for exm in ['Z0_24H','Z0_48H','TIME24','TIME48']:
      for cost in [0.0,1.0,3.0,7.5]:
        t=simulate(mode,sm,exm,cost); 
        if len(t)==0: continue
        alltr.append(t)
        for split,a,b in [('TRAIN','2021-01-01','2025-01-01'),('OOS','2025-01-01','2026-09-01')]:
            q=t[(t.entry_time>=pd.Timestamp(a,tz='UTC'))&(t.entry_time<pd.Timestamp(b,tz='UTC'))]
            if len(q):
                sums.append(dict(mode=mode,stop_mult=sm,exit_mode=exm,cost_bps=cost,split=split,**metrics(q)))
summ=pd.DataFrame(sums); summ.to_csv(OUT/'LAB102B_summary.csv',index=False)
pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB102B_trades_all.csv',index=False)

# rank profiles by TRAIN EV with OOS gate, separately by cost
sel=[]
for cost,g in summ.groupby('cost_bps'):
    wide=g.pivot_table(index=['mode','stop_mult','exit_mode'],columns='split',values=['n','ev','pf','dd','med_hold','med_mfe_atr','med_mae_atr'],aggfunc='first')
    rows=[]
    for idx,row in wide.iterrows():
        try:
            d=dict(mode=idx[0],stop_mult=idx[1],exit_mode=idx[2],cost_bps=cost,
                   tr_n=row[('n','TRAIN')],tr_ev=row[('ev','TRAIN')],tr_pf=row[('pf','TRAIN')],tr_dd=row[('dd','TRAIN')],
                   va_n=row[('n','OOS')],va_ev=row[('ev','OOS')],va_pf=row[('pf','OOS')],va_dd=row[('dd','OOS')],
                   tr_hold=row[('med_hold','TRAIN')],va_hold=row[('med_hold','OOS')])
            rows.append(d)
        except KeyError: pass
    rr=pd.DataFrame(rows)
    eligible=rr[(rr.tr_n>=100)&(rr.va_n>=40)].copy()
    if len(eligible)==0: eligible=rr
    trainbest=eligible.sort_values(['tr_ev','tr_pf'],ascending=[False,False]).iloc[0].to_dict(); trainbest['selection']='TRAIN_BEST'; sel.append(trainbest)
    stable=eligible.copy(); stable['min_ev']=np.minimum(stable.tr_ev,stable.va_ev)
    sb=stable.sort_values(['min_ev','va_pf'],ascending=[False,False]).iloc[0].to_dict(); sb['selection']='STABLE'; sel.append(sb)
pd.DataFrame(sel).to_csv(OUT/'LAB102B_selected.csv',index=False)

lines=['# LAB102B — BTC drift capture','',
'One trade per fresh |Z|>=1 episode, inverse crowd direction. Entry modes: immediate SETUP, ARMED after 0.10 Z pullback, or M30 STRUCT4. Catastrophic stop = 2/2.5/3 H1 ATR. Exits = Z0 with 24/48h cap, or pure 24/48h time.','']
for r in sel:
    lines.append(f"- cost {r['cost_bps']:.1f}bps {r['selection']}: {r['mode']} stop={r['stop_mult']:.1f}H1ATR exit={r['exit_mode']} | TRAIN N={int(r['tr_n'])} EV={r['tr_ev']:+.3f} PF={r['tr_pf']:.2f} DD={r['tr_dd']:.1f}R | OOS N={int(r['va_n'])} EV={r['va_ev']:+.3f} PF={r['va_pf']:.2f} DD={r['va_dd']:.1f}R")
(OUT/'LAB102B_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
