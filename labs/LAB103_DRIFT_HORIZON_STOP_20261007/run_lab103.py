#!/usr/bin/env python3
from __future__ import annotations
import json,re,zipfile
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab103_out"); OUT.mkdir(exist_ok=True)
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

# LAB103 frozen scope: STRUCT4 only; pure time exits; no Z0/BE/trailing.
P_OPEN=base.open.to_numpy(float); P_HIGH=base.high.to_numpy(float); P_LOW=base.low.to_numpy(float); P_CLOSE=base.close.to_numpy(float)
P_Z=base.z.to_numpy(float); P_ATR=base.atr_h1.to_numpy(float)

STRUCT_ENTRIES=[]
for r in eps.itertuples():
    ei=entry_from_episode(r,'STRUCT4')
    if ei is None or ei>=len(base)-1: continue
    STRUCT_ENTRIES.append((int(ei),int(r.side),float(r.z_setup),r.setup_time))

HOURS=[24,36,48,60,72]
STOPS=[2.5,3.0,3.5]
PRECOMP={}
for sm in STOPS:
    recs=[]
    for ei,side,zsetup,st in STRUCT_ENTRIES:
        entry=P_OPEN[ei]; atr=P_ATR[ei]
        if not np.isfinite(atr) or atr<=0: continue
        max_bars=72*12
        endmax=min(ei+max_bars,len(base)-1)
        hh=P_HIGH[ei:endmax+1]; ll=P_LOW[ei:endmax+1]
        stop=entry-side*sm*atr
        hs=(ll<=stop) if side>0 else (hh>=stop)
        hit=np.flatnonzero(hs)
        sl_rel=int(hit[0]) if len(hit) else None
        rec=dict(ei=ei,side=side,z_setup=zsetup,setup_time=st,entry=entry,atr=atr)
        for h in HOURS:
            cap_rel=min(h*12,endmax-ei)
            if sl_rel is not None and sl_rel<=cap_rel:
                exi=ei+sl_rel; exit_px=stop; reason='SL'
            else:
                exi=ei+cap_rel; exit_px=P_CLOSE[exi]; reason=f'TIME{h}'
            gross=side*(exit_px-entry)/(sm*atr)
            seg_h=P_HIGH[ei:exi+1]; seg_l=P_LOW[ei:exi+1]
            fav=((seg_h-entry) if side>0 else (entry-seg_l))/atr
            adv=((entry-seg_l) if side>0 else (seg_h-entry))/atr
            rec[h]=(exi,gross,reason,(exi-ei)*5/60,float(np.nanmax(fav)),float(np.nanmax(adv)))
        recs.append(rec)
    PRECOMP[sm]=recs

def simulate(stop_mult,hold_h,cost_bps):
    rows=[]; open_until=-1
    for r in PRECOMP[stop_mult]:
        ei=r['ei']
        if ei<=open_until: continue
        exi,gross,reason,held,mfe,mae=r[hold_h]
        cost=(r['entry']*(cost_bps/10000.0))/(stop_mult*r['atr'])
        net=gross-cost
        rows.append(dict(stop_mult=stop_mult,hold_h_target=hold_h,cost_bps=cost_bps,
                         setup_time=r['setup_time'],entry_time=base.time.iloc[ei],exit_time=base.time.iloc[exi],
                         side=r['side'],z_setup=r['z_setup'],gross_r=gross,net_r=net,
                         mfe_atr=mfe,mae_atr=mae,reason=reason,actual_hold_h=held))
        open_until=exi
    return pd.DataFrame(rows)

def metrics(t):
    if len(t)==0:return {}
    x=t.net_r.to_numpy(float); pos=x[x>0].sum(); neg=-x[x<0].sum()
    eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=float(np.max(pk[1:]-eq))
    return dict(n=len(t),ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),sumr=float(x.sum()),dd=dd,
                med_hold=float(t.actual_hold_h.median()),med_mfe_atr=float(t.mfe_atr.median()),med_mae_atr=float(t.mae_atr.median()))

sums=[]; alltr=[]
for sm in STOPS:
  for hold_h in HOURS:
    for cost in [0.0,1.0,3.0,7.5]:
      t=simulate(sm,hold_h,cost)
      if len(t)==0: continue
      alltr.append(t)
      for split,a,b in [('TRAIN','2021-01-01','2025-01-01'),('OOS','2025-01-01','2026-09-01')]:
        q=t[(t.entry_time>=pd.Timestamp(a,tz='UTC'))&(t.entry_time<pd.Timestamp(b,tz='UTC'))]
        if len(q):
          m=metrics(q)
          m['sl_rate']=float((q.reason=='SL').mean())
          m['p25']=float(q.net_r.quantile(.25)); m['median']=float(q.net_r.median()); m['p75']=float(q.net_r.quantile(.75))
          sums.append(dict(stop_mult=sm,hold_h=hold_h,cost_bps=cost,split=split,**m))

summ=pd.DataFrame(sums)
summ.to_csv(OUT/'LAB103_summary.csv',index=False)
trall=pd.concat(alltr,ignore_index=True)
trall.to_csv(OUT/'LAB103_trades_all.csv',index=False)

# One-row wide comparison table.
wide=[]
for cost in [0.0,1.0,3.0,7.5]:
  for sm in STOPS:
    for h in HOURS:
      a=summ[(summ.cost_bps==cost)&(summ.stop_mult==sm)&(summ.hold_h==h)&(summ.split=='TRAIN')]
      b=summ[(summ.cost_bps==cost)&(summ.stop_mult==sm)&(summ.hold_h==h)&(summ.split=='OOS')]
      if len(a) and len(b):
        x=a.iloc[0]; y=b.iloc[0]
        wide.append(dict(cost_bps=cost,stop_mult=sm,hold_h=h,
                         tr_n=int(x.n),tr_ev=x.ev,tr_pf=x.pf,tr_dd=x.dd,tr_sl_rate=x.sl_rate,tr_median=x['median'],
                         va_n=int(y.n),va_ev=y.ev,va_pf=y.pf,va_dd=y.dd,va_sl_rate=y.sl_rate,va_median=y['median'],
                         min_ev=min(x.ev,y.ev)))
wide=pd.DataFrame(wide)
wide.to_csv(OUT/'LAB103_grid_wide.csv',index=False)

selected=[]
for cost,g in wide.groupby('cost_bps'):
    trbest=g.sort_values(['tr_ev','tr_pf'],ascending=[False,False]).iloc[0].to_dict(); trbest['selection']='TRAIN_BEST'; selected.append(trbest)
    stable=g.sort_values(['min_ev','va_pf'],ascending=[False,False]).iloc[0].to_dict(); stable['selection']='STABLE_MIN_EV'; selected.append(stable)
pd.DataFrame(selected).to_csv(OUT/'LAB103_selected.csv',index=False)

# yearly stats for gross stable choice
gross=pd.DataFrame([r for r in selected if r['cost_bps']==0.0 and r['selection']=='STABLE_MIN_EV'])
if len(gross):
    g=gross.iloc[0]
    q=trall[(trall.cost_bps==0.0)&(trall.stop_mult==g.stop_mult)&(trall.hold_h_target==g.hold_h)].copy()
    q['year']=pd.to_datetime(q.entry_time,utc=True).dt.year
    yr=[]
    for y,z in q.groupby('year'):
      mm=metrics(z)
      yr.append(dict(year=int(y),n=mm['n'],ev=mm['ev'],pf=mm['pf'],sumr=mm['sumr'],dd=mm['dd'],sl_rate=float((z.reason=='SL').mean())))
    pd.DataFrame(yr).to_csv(OUT/'LAB103_selected_yearly.csv',index=False)

lines=['# LAB103 — drift horizon × catastrophic stop sweep','',
       'Frozen signal/entry: fresh |Z|>=1 inverse-crowd episode -> M30 STRUCT4 -> next M30 open.',
       'Only two dimensions vary: hold = 24/36/48/60/72h; catastrophic stop = 2.5/3.0/3.5 H1 ATR.',
       'No Z0 exit, no BE, no trailing, no new signal filters.','']
for r in selected:
    lines.append(f"- cost {r['cost_bps']:.1f}bps {r['selection']}: stop={r['stop_mult']:.1f} H1ATR hold={int(r['hold_h'])}h | TRAIN N={int(r['tr_n'])} EV={r['tr_ev']:+.3f} PF={r['tr_pf']:.2f} DD={r['tr_dd']:.1f}R SL={r['tr_sl_rate']:.1%} | OOS N={int(r['va_n'])} EV={r['va_ev']:+.3f} PF={r['va_pf']:.2f} DD={r['va_dd']:.1f}R SL={r['va_sl_rate']:.1%}")
(OUT/'LAB103_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
