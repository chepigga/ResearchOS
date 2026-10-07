#!/usr/bin/env python3
from __future__ import annotations
import math,re,zipfile,json,heapq
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab107b_out"); OUT.mkdir(exist_ok=True)
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

# LAB107B — EARLY FAIL on frozen LAB107A TRAIN-selected parents
PARENTS=[
    dict(label='QUALITY',hold_h=48,max_open=3,mode='SAME_SIDE'),
    dict(label='SECOND',hold_h=48,max_open=3,mode='ANY')
]
CHECK_HOURS=[2,4,6]
MFE_THRESHOLDS=[0.10,0.20,0.30]
COSTS_B=[2.81,7.5]

# Candidate path cache for 48h; fail check uses completed 5m close at check time.
path48={}
for ci,r in enumerate(cands):
    ei=r['ei']; side=r['side']; entry=B_OPEN[ei]; atr=B_ATR[ei]
    stop=entry-side*STOP_MULT*atr
    end=min(ei+48*12,len(base)-1)
    hh=B_HIGH[ei:end+1]; ll=B_LOW[ei:end+1]
    hit=((ll<=stop) if side>0 else (hh>=stop))
    ix=np.flatnonzero(hit)
    if len(ix):
        exi=ei+int(ix[0]); exit_px=stop; reason='SL'
    else:
        exi=end; exit_px=B_CLOSE[exi]; reason='TIME48'
    gross=side*(exit_px-entry)/(STOP_MULT*atr)
    path48[ci]=dict(entry=entry,atr=atr,stop=stop,exi=exi,exit_px=exit_px,gross_r=gross,reason=reason)

def candidate_outcome(ci,check_h,mfe_thr):
    r=cands[ci]; q=path48[ci]
    ei=r['ei']; side=r['side']; entry=q['entry']; risk=STOP_MULT*q['atr']
    # baseline
    if check_h is None:
        return dict(exi=q['exi'],exit_px=q['exit_px'],gross_r=q['gross_r'],reason=q['reason'],failed=False,mfe_at_check=np.nan)
    check_i=min(ei+check_h*12,q['exi'])
    # If baseline trade already ended before/at check, no fail intervention.
    if q['exi']<=ei+check_h*12:
        return dict(exi=q['exi'],exit_px=q['exit_px'],gross_r=q['gross_r'],reason=q['reason'],failed=False,mfe_at_check=np.nan)
    hh=B_HIGH[ei:check_i+1]; ll=B_LOW[ei:check_i+1]
    mfe=float(np.max(hh-entry)/risk) if side>0 else float(np.max(entry-ll)/risk)
    close=float(B_CLOSE[check_i])
    lost=(close<r['break_level']) if side>0 else (close>r['break_level'])
    if mfe<mfe_thr and lost:
        gross=side*(close-entry)/risk
        return dict(exi=check_i,exit_px=close,gross_r=gross,reason=f'FAIL_{check_h}H',failed=True,mfe_at_check=mfe)
    return dict(exi=q['exi'],exit_px=q['exit_px'],gross_r=q['gross_r'],reason=q['reason'],failed=False,mfe_at_check=mfe)

def simulate_parent(parent,check_h,mfe_thr,cost):
    rows=[]; active=[]
    for ci,r in enumerate(cands):
        ei=r['ei']; side=r['side']
        active=[a for a in active if a[0]>=ei]
        if len(active)>=parent['max_open']: continue
        if parent['mode']=='SAME_SIDE' and active and any(a[1]!=side for a in active): continue
        o=candidate_outcome(ci,check_h,mfe_thr)
        q=path48[ci]
        cost_r=(q['entry']*(cost/10000.0))/(STOP_MULT*q['atr'])
        net=o['gross_r']-cost_r
        rows.append(dict(parent=parent['label'],hold_h=48,max_open=parent['max_open'],mode=parent['mode'],cost_bps=cost,
                         check_h=0 if check_h is None else check_h,mfe_thr=0 if mfe_thr is None else mfe_thr,
                         entry_time=r['entry_time'],exit_time=base.time.iloc[o['exi']],side='BUY' if side>0 else 'SELL',
                         z_setup=r['z_setup'],break_level=r['break_level'],entry=q['entry'],stop=q['stop'],
                         gross_r=o['gross_r'],net_r=net,reason=o['reason'],failed=o['failed'],mfe_at_check=o['mfe_at_check'],
                         baseline_reason=q['reason'],baseline_gross_r=q['gross_r']))
        active.append((o['exi'],side))
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
    return dict(n=len(q),ev=float(x.mean()),t=tt,pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),sumr=float(x.sum()),dd=dd,
                se=se,trades_month=len(q)/months,r_month=float(x.sum())/months,fail_rate=float(q.failed.mean()),
                sl_rate=float(q.reason.eq('SL').mean()))

alltr=[]; rows=[]
variants=[(None,None)]+[(h,m) for h in CHECK_HOURS for m in MFE_THRESHOLDS]
for parent in PARENTS:
  for cost in COSTS_B:
    for ch,mf in variants:
      q=simulate_parent(parent,ch,mf,cost)
      q['split']=np.where(pd.to_datetime(q.entry_time,utc=True)<TRAIN_END,'TRAIN','OOS')
      q['year']=pd.to_datetime(q.entry_time,utc=True).dt.year
      alltr.append(q)
      for split in ['TRAIN','OOS','ALL']:
        z=q if split=='ALL' else q[q.split==split]
        rows.append(dict(parent=parent['label'],cost_bps=cost,check_h=0 if ch is None else ch,mfe_thr=0 if mf is None else mf,split=split,**metrics(z)))
trades=pd.concat(alltr,ignore_index=True)
summ=pd.DataFrame(rows)
trades.to_csv(OUT/'LAB107B_trades_all.csv',index=False)
summ.to_csv(OUT/'LAB107B_summary.csv',index=False)

# TRAIN-only selection per parent at real 2.81 bps: maximize R/month, require EV>0 PF>1.10.
selected=[]
for parent in PARENTS:
    g=summ[(summ.parent==parent['label'])&(summ.cost_bps==2.81)&(summ.split=='TRAIN')].copy()
    elig=g[(g.ev>0)&(g.pf>1.10)]
    best=(elig if len(elig) else g).sort_values(['r_month','ev'],ascending=[False,False]).iloc[0]
    o=summ[(summ.parent==parent['label'])&(summ.cost_bps==2.81)&(summ.split=='OOS')&(summ.check_h==best.check_h)&(summ.mfe_thr==best.mfe_thr)].iloc[0]
    btr=g[(g.check_h==0)&(g.mfe_thr==0)].iloc[0]
    bos=summ[(summ.parent==parent['label'])&(summ.cost_bps==2.81)&(summ.split=='OOS')&(summ.check_h==0)&(summ.mfe_thr==0)].iloc[0]
    selected.append(dict(parent=parent['label'],check_h=int(best.check_h),mfe_thr=float(best.mfe_thr),
                         train_n=int(best.n),train_ev=best.ev,train_pf=best.pf,train_t=best.t,train_dd=best.dd,train_trades_month=best.trades_month,train_r_month=best.r_month,
                         oos_n=int(o.n),oos_ev=o.ev,oos_pf=o.pf,oos_t=o.t,oos_dd=o.dd,oos_trades_month=o.trades_month,oos_r_month=o.r_month,
                         delta_train_ev=best.ev-btr.ev,delta_oos_ev=o.ev-bos.ev,delta_train_rmonth=best.r_month-btr.r_month,delta_oos_rmonth=o.r_month-bos.r_month))
pd.DataFrame(selected).to_csv(OUT/'LAB107B_selected.csv',index=False)

# Pure candidate-level diagnostic: how many future baseline SLs get cut, and how many baseline winners get killed.
diag=[]
for ch,mf in [(h,m) for h in CHECK_HOURS for m in MFE_THRESHOLDS]:
    saved=0;killed=0;failn=0;deltas=[]
    for ci,r in enumerate(cands):
        b=path48[ci]; o=candidate_outcome(ci,ch,mf)
        if not o['failed']: continue
        failn+=1
        if b['reason']=='SL' and o['gross_r']>-1: saved+=1
        if b['gross_r']>0 and o['gross_r']<b['gross_r']: killed+=1
        deltas.append(o['gross_r']-b['gross_r'])
    diag.append(dict(check_h=ch,mfe_thr=mf,fail_candidates=failn,saved_future_sl=saved,killed_future_winners=killed,
                     mean_delta_r=float(np.mean(deltas)) if deltas else np.nan))
pd.DataFrame(diag).to_csv(OUT/'LAB107B_fail_diagnostic.csv',index=False)

# year report for selected variants
yr=[]
for s in selected:
    q=trades[(trades.parent==s['parent'])&(trades.cost_bps==2.81)&(trades.check_h==s['check_h'])&(trades.mfe_thr==s['mfe_thr'])]
    for y,z in q.groupby('year'): yr.append(dict(parent=s['parent'],check_h=s['check_h'],mfe_thr=s['mfe_thr'],year=int(y),**metrics(z)))
pd.DataFrame(yr).to_csv(OUT/'LAB107B_selected_yearly.csv',index=False)

lines=['# LAB107B — EARLY FAIL','',
'Parents frozen from LAB107A TRAIN-only: QUALITY=H48/open3/SAME_SIDE; SECOND=H48/open3/ANY.',
'Early fail: at 2/4/6h, if cumulative MFE < 0.10/0.20/0.30R AND 5m close has lost the original STRUCT4 breakout level, exit at that close.',
'Selection within each parent uses TRAIN only at 2.81 bps; objective=max TRAIN R/month subject to EV>0, PF>1.10.','']
for s in selected:
    lines += [f"## {s['parent']}: fail {s['check_h']}h / MFE<{s['mfe_thr']:.2f}R",
              f"- TRAIN N={s['train_n']} EV={s['train_ev']:+.3f} PF={s['train_pf']:.2f} t={s['train_t']:.2f} DD={s['train_dd']:.1f}R trades/mo={s['train_trades_month']:.1f} R/mo={s['train_r_month']:+.2f} | ΔEV={s['delta_train_ev']:+.3f} ΔR/mo={s['delta_train_rmonth']:+.2f}",
              f"- OOS N={s['oos_n']} EV={s['oos_ev']:+.3f} PF={s['oos_pf']:.2f} t={s['oos_t']:.2f} DD={s['oos_dd']:.1f}R trades/mo={s['oos_trades_month']:.1f} R/mo={s['oos_r_month']:+.2f} | ΔEV={s['delta_oos_ev']:+.3f} ΔR/mo={s['delta_oos_rmonth']:+.2f}",'']
(OUT/'LAB107B_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
