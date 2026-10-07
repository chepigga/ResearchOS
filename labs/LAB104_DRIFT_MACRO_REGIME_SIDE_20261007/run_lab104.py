#!/usr/bin/env python3
from __future__ import annotations
import json,re,zipfile
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab104_out"); OUT.mkdir(exist_ok=True)
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

# LAB104 frozen execution from LAB103. NO optimization.
# Signal: fresh |Z|>=1 inverse crowd -> M30 STRUCT4 -> next M30 open.
# Execution: catastrophic stop 3.5 H1 ATR, pure time exit 60h.
# Research dimension only: causal macro regime x side.

STOP_MULT=3.5
HOLD_H=60
COSTS=[0.0,1.0,3.0,7.5]

# --- Causal D1 macro regime ---
# Completed daily bars only. Regime known from PRIOR completed D1 bar at entry.
d1=price.set_index('time').resample('1D',label='left',closed='left').agg(
    open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')
).dropna().reset_index()
d1['close_time']=d1.time+pd.Timedelta(days=1)
d1['sma200']=d1.close.rolling(200,min_periods=200).mean()
d1['sma200_lag20']=d1.sma200.shift(20)
d1['sma50']=d1.close.rolling(50,min_periods=50).mean()
d1['ret90']=d1.close.pct_change(90)

def macro_label(row):
    if not np.isfinite(row.sma200) or not np.isfinite(row.sma200_lag20): return 'WARMUP'
    slope=row.sma200-row.sma200_lag20
    if row.close < row.sma200 and slope < 0: return 'BEAR'
    if row.close > row.sma200 and slope > 0: return 'BULL'
    return 'SIDEWAYS'
d1['regime']=d1.apply(macro_label,axis=1)

# Secondary diagnostic only: stronger bear if below both SMA50 and SMA200 and 90d return<0.
def bear_strict(row):
    return bool(np.isfinite(row.sma200) and np.isfinite(row.sma50) and np.isfinite(row.ret90)
                and row.close<row.sma200 and row.close<row.sma50 and row.ret90<0)
d1['bear_strict']=d1.apply(bear_strict,axis=1)

P_OPEN=base.open.to_numpy(float); P_HIGH=base.high.to_numpy(float); P_LOW=base.low.to_numpy(float)
P_CLOSE=base.close.to_numpy(float); P_ATR=base.atr_h1.to_numpy(float)

# Frozen STRUCT4 entries before overlap suppression.
entries=[]
for r in eps.itertuples():
    ei=entry_from_episode(r,'STRUCT4')
    if ei is None or ei>=len(base)-1: continue
    et=base.time.iloc[ei]
    # regime from last completed D1 bar, never current unfinished day
    k=int(d1.close_time.searchsorted(et,side='right')-1)
    if k<0: continue
    reg=d1.regime.iloc[k]; strict=bool(d1.bear_strict.iloc[k])
    if reg=='WARMUP': continue
    entries.append(dict(ei=int(ei),entry_time=et,side=int(r.side),z_setup=float(r.z_setup),
                        setup_time=r.setup_time,regime=reg,bear_strict=strict,
                        d1_close=float(d1.close.iloc[k]),d1_sma200=float(d1.sma200.iloc[k]),
                        d1_sma50=float(d1.sma50.iloc[k]) if np.isfinite(d1.sma50.iloc[k]) else np.nan,
                        d1_ret90=float(d1.ret90.iloc[k]) if np.isfinite(d1.ret90.iloc[k]) else np.nan))

cand=pd.DataFrame(entries)
cand['year']=pd.to_datetime(cand.entry_time,utc=True).dt.year
cand.to_csv(OUT/'LAB104_candidates_before_overlap.csv',index=False)

# Precompute frozen 60h outcome.
recs=[]
for r in cand.itertuples():
    ei=int(r.ei); side=int(r.side); entry=P_OPEN[ei]; atr=P_ATR[ei]
    if not np.isfinite(atr) or atr<=0: continue
    end=min(ei+HOLD_H*12,len(base)-1)
    hh=P_HIGH[ei:end+1]; ll=P_LOW[ei:end+1]
    stop=entry-side*STOP_MULT*atr
    hs=(ll<=stop) if side>0 else (hh>=stop)
    hit=np.flatnonzero(hs)
    if len(hit):
        rel=int(hit[0]); exi=ei+rel; exit_px=stop; reason='SL'
    else:
        exi=end; exit_px=P_CLOSE[exi]; reason='TIME60'
    gross=side*(exit_px-entry)/(STOP_MULT*atr)
    seg_h=P_HIGH[ei:exi+1]; seg_l=P_LOW[ei:exi+1]
    fav=((seg_h-entry) if side>0 else (entry-seg_l))/(STOP_MULT*atr)
    adv=((entry-seg_l) if side>0 else (seg_h-entry))/(STOP_MULT*atr)
    recs.append(dict(ei=ei,entry_time=r.entry_time,setup_time=r.setup_time,side=side,
                     side_name='BUY' if side>0 else 'SELL',regime=r.regime,bear_strict=r.bear_strict,
                     z_setup=r.z_setup,entry=entry,atr_h1=atr,stop=stop,exit_time=base.time.iloc[exi],
                     gross_r=gross,reason=reason,hold_h=(exi-ei)*5/60,
                     mfe_r=float(np.nanmax(fav)),mae_r=float(np.nanmax(adv)),exit_i=exi))
pre=pd.DataFrame(recs)

def apply_overlap_and_cost(cost_bps):
    out=[]; open_until=-1
    for r in pre.sort_values('entry_time').itertuples():
        if int(r.ei)<=open_until: continue
        cost=(float(r.entry)*(cost_bps/10000.0))/(STOP_MULT*float(r.atr_h1))
        d=r._asdict(); d['cost_bps']=cost_bps; d['net_r']=float(r.gross_r)-cost
        out.append(d); open_until=int(r.exit_i)
    return pd.DataFrame(out)

def metrics(q):
    if len(q)==0:return dict(n=0,ev=np.nan,pf=np.nan,wr=np.nan,sumr=0.0,dd=np.nan,sl_rate=np.nan,med_mfe=np.nan,med_mae=np.nan,med_hold=np.nan)
    x=q.net_r.to_numpy(float); pos=x[x>0].sum(); neg=-x[x<0].sum()
    eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=float(np.max(pk[1:]-eq))
    return dict(n=len(q),ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),
                sumr=float(x.sum()),dd=dd,sl_rate=float((q.reason=='SL').mean()),
                med_mfe=float(q.mfe_r.median()),med_mae=float(q.mae_r.median()),med_hold=float(q.hold_h.median()))

all_exec=[]; summary=[]
for cost in COSTS:
    t=apply_overlap_and_cost(cost)
    t['year']=pd.to_datetime(t.entry_time,utc=True).dt.year
    t['split']=np.where(pd.to_datetime(t.entry_time,utc=True)<pd.Timestamp('2025-01-01',tz='UTC'),'TRAIN','OOS')
    all_exec.append(t)
    for split in ['TRAIN','OOS','ALL']:
        qs=t if split=='ALL' else t[t.split==split]
        for regime in ['BEAR','BULL','SIDEWAYS','ALL']:
            qr=qs if regime=='ALL' else qs[qs.regime==regime]
            for side_name in ['BUY','SELL','ALL']:
                q=qr if side_name=='ALL' else qr[qr.side_name==side_name]
                m=metrics(q)
                summary.append(dict(cost_bps=cost,split=split,regime=regime,side=side_name,**m))
execs=pd.concat(all_exec,ignore_index=True)
summ=pd.DataFrame(summary)
execs.to_csv(OUT/'LAB104_trades.csv',index=False)
summ.to_csv(OUT/'LAB104_regime_side_summary.csv',index=False)

# Year x regime x side, gross only.
yrows=[]
g=execs[execs.cost_bps==0.0].copy()
for (y,reg,side),q in g.groupby(['year','regime','side_name']):
    yrows.append(dict(year=int(y),regime=reg,side=side,**metrics(q)))
pd.DataFrame(yrows).to_csv(OUT/'LAB104_year_regime_side.csv',index=False)

# 2022 focused audit.
q22=g[g.year==2022].copy()
q22.to_csv(OUT/'LAB104_2022_trades.csv',index=False)
audit=[]
for reg in ['BEAR','BULL','SIDEWAYS','ALL']:
    qr=q22 if reg=='ALL' else q22[q22.regime==reg]
    for s in ['BUY','SELL','ALL']:
        z=qr if s=='ALL' else qr[qr.side_name==s]
        audit.append(dict(regime=reg,side=s,**metrics(z)))
pd.DataFrame(audit).to_csv(OUT/'LAB104_2022_audit.csv',index=False)

# Candidate scarcity diagnostic: before overlap vs executed by year/regime.
cc=cand.groupby(['year','regime']).size().reset_index(name='candidates_before_overlap')
ee=g.groupby(['year','regime']).size().reset_index(name='executed_after_overlap')
freq=cc.merge(ee,on=['year','regime'],how='outer').fillna(0)
freq.to_csv(OUT/'LAB104_frequency_audit.csv',index=False)

# Counterfactual portfolio policies, no parameter search:
# ALL = current system; BLOCK_BUY_BEAR; SELL_ONLY_BEAR (only changes BEAR regime).
polrows=[]
for cost in COSTS:
    t=execs[execs.cost_bps==cost].copy()
    policies={
      'ALL':t,
      'BLOCK_BUY_BEAR':t[~((t.regime=='BEAR')&(t.side_name=='BUY'))],
      'SELL_ONLY_BEAR':pd.concat([t[t.regime!='BEAR'],t[(t.regime=='BEAR')&(t.side_name=='SELL')]]).sort_values('entry_time')
    }
    for name,q in policies.items():
        for split in ['TRAIN','OOS']:
            z=q[q.split==split]
            polrows.append(dict(cost_bps=cost,policy=name,split=split,**metrics(z)))
pd.DataFrame(polrows).to_csv(OUT/'LAB104_policy_counterfactual.csv',index=False)

# Report.
def get(cost,split,reg,side):
    q=summ[(summ.cost_bps==cost)&(summ.split==split)&(summ.regime==reg)&(summ.side==side)]
    return None if len(q)==0 else q.iloc[0]
lines=['# LAB104 — DRIFT × MACRO REGIME × SIDE','',
'Frozen LAB103 execution: fresh |Z|>=1 inverse-crowd -> M30 STRUCT4 -> next M30 open -> SL 3.5 H1 ATR -> TIME60.',
'No signal/stop/hold optimization. Research dimension only: causal D1 macro regime and BUY/SELL asymmetry.',
'Macro regime uses last completed D1 bar: BEAR = close<SMA200 and SMA200 slope over prior 20 completed days <0; BULL symmetric; otherwise SIDEWAYS.','']
for split in ['TRAIN','OOS']:
    lines.append(f'## {split} gross')
    for reg in ['BEAR','BULL','SIDEWAYS']:
        a=get(0.0,split,reg,'ALL'); b=get(0.0,split,reg,'BUY'); s=get(0.0,split,reg,'SELL')
        if a is None: continue
        lines.append(f"- {reg}: ALL N={int(a.n)} EV={a.ev:+.3f} PF={a.pf:.2f}; BUY N={int(b.n)} EV={b.ev:+.3f} PF={b.pf:.2f}; SELL N={int(s.n)} EV={s.ev:+.3f} PF={s.pf:.2f}")
lines += ['','## 2022 gross audit']
for reg in ['BEAR','BULL','SIDEWAYS','ALL']:
    a=pd.DataFrame(audit); q=a[(a.regime==reg)&(a.side=='ALL')].iloc[0]
    lines.append(f"- {reg}: N={int(q.n)} EV={q.ev:+.3f} PF={q.pf:.2f} DD={q.dd:.1f}R")
lines += ['','Interpretation rule: LAB104 is a stress test. Any BUY/SELL regime asymmetry is descriptive unless it survives TRAIN/OOS and enough N; do not promote a side filter from 2022 alone.']
(OUT/'LAB104_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
