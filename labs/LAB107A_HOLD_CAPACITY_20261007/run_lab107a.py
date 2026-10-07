#!/usr/bin/env python3
from __future__ import annotations
import math,re,zipfile,json,heapq
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab107a_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
HOLDS=[12,24,36,48,60]
MAX_OPEN_LIST=[1,2,3]
MODES=['ANY','SAME_SIDE']
COSTS=[0.0,2.81,7.5]
STOP_MULT=3.5

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
        for d in frames[1:]: common &= set(d.columns)
        if len(frames)>1 and len(common)>=4:
            cols=list(common); return pd.concat([d[cols] for d in frames],ignore_index=True)
        return frames[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),errors='coerce',utc=True)
    return pd.to_datetime(s,errors='coerce',utc=True)

# ---------- data ----------
flow=load_zip(FLOW_ZIP)
ft=pick(flow.columns,['timestamp','time','datetime','open_time'])
fr=pick(flow.columns,['longShortRatio','long_short_ratio','ls_ratio','globalLongShortAccountRatio','ratio'])
flow=flow[[ft,fr]].copy(); flow['time']=ptime(flow[ft]); flow['ratio']=pd.to_numeric(flow[fr],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(72,min_periods=72).mean(); sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)

raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','datetime','open_time']); po=pick(raw.columns,['open']); ph=pick(raw.columns,['high']); pl=pick(raw.columns,['low']); pc=pick(raw.columns,['close'])
p=raw[[pt,po,ph,pl,pc]].copy(); p['time']=ptime(p[pt])
for c,nm in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[nm]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# H1 ATR14, causal
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prev=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
h1['atr_h1']=tr.rolling(14,min_periods=14).mean(); h1['close_time']=h1.time+pd.Timedelta(hours=1)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),flow[['time','z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['z','atr_h1']).reset_index(drop=True)

m30=base.set_index('time').resample('30min',label='left',closed='left').agg(
    open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),z=('z','last'),atr_h1=('atr_h1','last')
).dropna().reset_index()
m30['close_time']=m30.time+pd.Timedelta(minutes=30)

B_OPEN=base.open.to_numpy(float); B_HIGH=base.high.to_numpy(float); B_LOW=base.low.to_numpy(float); B_CLOSE=base.close.to_numpy(float); B_ATR=base.atr_h1.to_numpy(float)
zv=base.z.to_numpy(float)

# fresh |Z|>=1 episode
eps=[]
for i in range(1,len(base)-1):
    if abs(zv[i])>=1.0 and abs(zv[i-1])<1.0:
        eps.append(dict(si=i,side=-1 if zv[i]>0 else 1,z_setup=float(zv[i]),setup_time=base.time.iloc[i]))

def struct4_entry(ep):
    si=ep['si']; side=ep['side']; t0=base.time.iloc[si]
    k0=int(m30.close_time.searchsorted(t0,side='right'))
    for k in range(max(4,k0),min(k0+8,len(m30)-1)):
        hi=float(m30.high.iloc[k-4:k].max()); lo=float(m30.low.iloc[k-4:k].min()); c=float(m30.close.iloc[k])
        if (c>hi if side>0 else c<lo):
            et=m30.time.iloc[k+1]
            ei=int(base.time.searchsorted(et,side='left'))
            if ei<len(base)-1:
                return ei,float(hi if side>0 else lo)
    return None,None

cands=[]
for ep in eps:
    ei,level=struct4_entry(ep)
    if ei is None:continue
    cands.append(dict(ei=ei,entry_time=base.time.iloc[ei],side=ep['side'],z_setup=ep['z_setup'],setup_time=ep['setup_time'],break_level=level))
cands=sorted(cands,key=lambda x:x['ei'])

# Precompute each candidate's path for every hold.
paths={}
for ci,r in enumerate(cands):
    ei=r['ei']; side=r['side']; entry=B_OPEN[ei]; atr=B_ATR[ei]
    stop=entry-side*STOP_MULT*atr
    for hold in HOLDS:
        end=min(ei+hold*12,len(base)-1)
        hh=B_HIGH[ei:end+1]; ll=B_LOW[ei:end+1]
        hit=((ll<=stop) if side>0 else (hh>=stop))
        ix=np.flatnonzero(hit)
        if len(ix):
            exi=ei+int(ix[0]); exit_px=stop; reason='SL'
        else:
            exi=end; exit_px=B_CLOSE[exi]; reason=f'TIME{hold}'
        gross=side*(exit_px-entry)/(STOP_MULT*atr)
        paths[(ci,hold)]=dict(entry=entry,atr=atr,stop=stop,exi=exi,exit_time=base.time.iloc[exi],gross_r=gross,reason=reason,hold_real_h=(exi-ei)*5/60)

def simulate(hold,max_open,mode,cost):
    rows=[]
    active=[] # list of (exi,side,trade_index)
    for ci,r in enumerate(cands):
        ei=r['ei']; side=r['side']
        # purge closed BEFORE this entry timestamp; if exi < ei it is free, same-bar exit means occupied until that bar closes
        active=[a for a in active if a[0]>=ei]
        if len(active)>=max_open: continue
        if mode=='SAME_SIDE' and len(active)>0 and any(a[1]!=side for a in active): continue

        q=paths[(ci,hold)]
        cost_r=(q['entry']*(cost/10000.0))/(STOP_MULT*q['atr'])
        net=q['gross_r']-cost_r
        rows.append(dict(hold_h=hold,max_open=max_open,mode=mode,cost_bps=cost,entry_time=r['entry_time'],exit_time=q['exit_time'],
                         side='BUY' if side>0 else 'SELL',z_setup=r['z_setup'],break_level=r['break_level'],
                         entry=q['entry'],stop=q['stop'],gross_r=q['gross_r'],net_r=net,reason=q['reason'],hold_real_h=q['hold_real_h']))
        active.append((q['exi'],side,len(rows)-1))
    return pd.DataFrame(rows)

def metrics(q):
    if len(q)==0:return {}
    x=q.net_r.to_numpy(float); sd=float(x.std(ddof=1)) if len(x)>1 else np.nan
    se=sd/math.sqrt(len(x)) if len(x)>1 and sd>0 else np.nan
    tt=float(x.mean()/se) if np.isfinite(se) and se>0 else np.nan
    pos=x[x>0].sum(); neg=-x[x<0].sum()
    eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=float(np.max(pk[1:]-eq))
    ttms=pd.to_datetime(q.entry_time,utc=True)
    months=max(1,(ttms.max().year-ttms.min().year)*12+ttms.max().month-ttms.min().month+1)
    days=max(1,(ttms.max().date()-ttms.min().date()).days+1)
    return dict(n=len(q),ev=float(x.mean()),t=tt,pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),sumr=float(x.sum()),dd=dd,
                se=se,trades_month=len(q)/months,trades_day=len(q)/days,r_month=float(x.sum())/months,sl_rate=float((q.reason=='SL').mean()),
                median_hold=float(q.hold_real_h.median()))

alltr=[]; sr=[]
for hold in HOLDS:
  for mo in MAX_OPEN_LIST:
    for mode in MODES:
      for cost in COSTS:
        q=simulate(hold,mo,mode,cost)
        if len(q)==0:continue
        q['split']=np.where(pd.to_datetime(q.entry_time,utc=True)<TRAIN_END,'TRAIN','OOS')
        q['year']=pd.to_datetime(q.entry_time,utc=True).dt.year
        alltr.append(q)
        for split in ['TRAIN','OOS','ALL']:
            z=q if split=='ALL' else q[q.split==split]
            sr.append(dict(hold_h=hold,max_open=mo,mode=mode,cost_bps=cost,split=split,**metrics(z)))
trades=pd.concat(alltr,ignore_index=True)
summ=pd.DataFrame(sr)
trades.to_csv(OUT/'LAB107A_trades_all.csv',index=False)
summ.to_csv(OUT/'LAB107A_summary.csv',index=False)

# TRAIN-only frozen selections at real spread 2.81 bps.
g=summ[(summ.cost_bps==2.81)&(summ.split=='TRAIN')].copy()
quality=g.sort_values(['ev','pf','dd'],ascending=[False,False,True]).iloc[0]
eligible=g[(g.ev>0)&(g.pf>1.10)].copy()
throughput=eligible.sort_values(['r_month','ev'],ascending=[False,False]).iloc[0] if len(eligible) else g.sort_values('r_month',ascending=False).iloc[0]
selected=[]
for label,row in [('QUALITY',quality),('THROUGHPUT',throughput)]:
    key=(int(row.hold_h),int(row.max_open),row['mode'])
    if any((x['hold_h'],x['max_open'],x['mode'])==key for x in selected): continue
    o=summ[(summ.cost_bps==2.81)&(summ.split=='OOS')&(summ.hold_h==row.hold_h)&(summ.max_open==row.max_open)&(summ['mode']==row['mode'])].iloc[0]
    selected.append(dict(label=label,hold_h=int(row.hold_h),max_open=int(row.max_open),mode=row['mode'],
                         train_n=int(row.n),train_ev=row.ev,train_pf=row.pf,train_t=row.t,train_dd=row.dd,train_trades_month=row.trades_month,train_r_month=row.r_month,
                         oos_n=int(o.n),oos_ev=o.ev,oos_pf=o.pf,oos_t=o.t,oos_dd=o.dd,oos_trades_month=o.trades_month,oos_r_month=o.r_month))
# if duplicate collapsed, add next distinct throughput/quality option
if len(selected)<2:
    used={(x['hold_h'],x['max_open'],x['mode']) for x in selected}
    for _,row in eligible.sort_values(['r_month','ev'],ascending=[False,False]).iterrows():
        key=(int(row.hold_h),int(row.max_open),row['mode'])
        if key in used:continue
        o=summ[(summ.cost_bps==2.81)&(summ.split=='OOS')&(summ.hold_h==row.hold_h)&(summ.max_open==row.max_open)&(summ['mode']==row['mode'])].iloc[0]
        selected.append(dict(label='SECOND',hold_h=key[0],max_open=key[1],mode=key[2],
                             train_n=int(row.n),train_ev=row.ev,train_pf=row.pf,train_t=row.t,train_dd=row.dd,train_trades_month=row.trades_month,train_r_month=row.r_month,
                             oos_n=int(o.n),oos_ev=o.ev,oos_pf=o.pf,oos_t=o.t,oos_dd=o.dd,oos_trades_month=o.trades_month,oos_r_month=o.r_month))
        break
pd.DataFrame(selected).to_csv(OUT/'LAB107A_selected.csv',index=False)

# year x selected
yr=[]
for s in selected:
    q=trades[(trades.cost_bps==2.81)&(trades.hold_h==s['hold_h'])&(trades.max_open==s['max_open'])&(trades['mode']==s['mode'])]
    for y,z in q.groupby('year'):yr.append(dict(label=s['label'],year=int(y),**metrics(z)))
pd.DataFrame(yr).to_csv(OUT/'LAB107A_selected_yearly.csv',index=False)

lines=['# LAB107A — HOLD × CAPACITY','',
'Frozen signal: fresh |Z|>=1 inverse crowd -> M30 STRUCT4 -> next M30 open; SL 3.5 H1 ATR.',
'Grid: hold 12/24/36/48/60h × max open 1/2/3 × ANY or SAME_SIDE. Costs: 0, 2.81, 7.5 bps.',
'Selection for Stage B uses TRAIN 2021-2024 only at 2.81 bps. QUALITY=max TRAIN EV. THROUGHPUT=max TRAIN R/month subject to EV>0 and PF>1.10.','']
for s in selected:
    lines += [f"## {s['label']}: H{s['hold_h']} / open{s['max_open']} / {s['mode']}",
              f"- TRAIN N={s['train_n']} EV={s['train_ev']:+.3f} PF={s['train_pf']:.2f} t={s['train_t']:.2f} DD={s['train_dd']:.1f}R trades/mo={s['train_trades_month']:.1f} R/mo={s['train_r_month']:+.2f}",
              f"- OOS N={s['oos_n']} EV={s['oos_ev']:+.3f} PF={s['oos_pf']:.2f} t={s['oos_t']:.2f} DD={s['oos_dd']:.1f}R trades/mo={s['oos_trades_month']:.1f} R/mo={s['oos_r_month']:+.2f}",'']
(OUT/'LAB107A_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
