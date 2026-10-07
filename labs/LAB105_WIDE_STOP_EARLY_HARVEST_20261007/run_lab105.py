#!/usr/bin/env python3
from __future__ import annotations
import json,re,zipfile
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab105_out"); OUT.mkdir(exist_ok=True)
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

# LAB105 — WIDE STOP + EARLY PROFIT HARVEST
# Frozen signal/entry from LAB103:
# fresh |Z|>=1 episode -> inverse crowd -> M30 STRUCT4 -> next M30 open.
# Frozen risk shell: SL = 3.5 H1 ATR, max hold = 60h, one position at a time.
# Only research dimension: early partial harvest at causal 12h M15 structural level.

STOP_MULT=3.5
HOLD_H=60
HARVEST_WINDOW_H=8
HARVEST_FRACTIONS=[0.0,0.25,0.50,0.75]
COSTS=[0.0,1.0,3.0,7.5]

P_OPEN=base.open.to_numpy(float); P_HIGH=base.high.to_numpy(float); P_LOW=base.low.to_numpy(float)
P_CLOSE=base.close.to_numpy(float); P_ATR=base.atr_h1.to_numpy(float)

# M15 causal structure for early harvest target.
m15=base.set_index('time').resample('15min',label='left',closed='left').agg(
    open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')
).dropna().reset_index()
M15_H=m15.high.to_numpy(float); M15_L=m15.low.to_numpy(float)

def structure_target_at_entry(ei,side,entry):
    et=base.time.iloc[ei]
    k=int(m15.time.searchsorted(et,side='right')-1)
    # Entry is aligned to a fresh M30 open, therefore use only fully completed M15 bars before entry.
    if k<48: return np.nan
    # If k bar starts at entry time, exclude it.
    if m15.time.iloc[k] >= et: end=k
    else: end=k+1
    start=max(0,end-48)
    if end-start<48: return np.nan
    if side>0:
        target=float(np.max(M15_H[start:end]))
        return target if target>entry else np.nan
    target=float(np.min(M15_L[start:end]))
    return target if target<entry else np.nan

# Frozen STRUCT4 candidates, ordered by entry time.
entries=[]
for r in eps.itertuples():
    ei=entry_from_episode(r,'STRUCT4')
    if ei is None or ei>=len(base)-1: continue
    entries.append(dict(ei=int(ei),side=int(r.side),z_setup=float(r.z_setup),setup_time=r.setup_time))
entries=sorted(entries,key=lambda x:x['ei'])

# Precompute one 60h path per candidate.
paths=[]
for r in entries:
    ei=r['ei']; side=r['side']; entry=P_OPEN[ei]; atr=P_ATR[ei]
    if not np.isfinite(atr) or atr<=0: continue
    stop=entry-side*STOP_MULT*atr
    end=min(ei+HOLD_H*12,len(base)-1)
    harvest_end=min(ei+HARVEST_WINDOW_H*12,end)
    ht=structure_target_at_entry(ei,side,entry)
    ht_r=((ht-entry)*side)/(STOP_MULT*atr) if np.isfinite(ht) else np.nan

    # first stop
    seg_h=P_HIGH[ei:end+1]; seg_l=P_LOW[ei:end+1]
    hit_sl=((seg_l<=stop) if side>0 else (seg_h>=stop))
    ixsl=np.flatnonzero(hit_sl)
    sl_rel=int(ixsl[0]) if len(ixsl) else None

    # first harvest target, only first 8h and only before catastrophic stop
    harv_rel=None
    if np.isfinite(ht):
        hh=P_HIGH[ei:harvest_end+1]; ll=P_LOW[ei:harvest_end+1]
        hit_h=((hh>=ht) if side>0 else (ll<=ht))
        ixh=np.flatnonzero(hit_h)
        if len(ixh):
            rr=int(ixh[0])
            if sl_rel is None or rr<sl_rel:
                harv_rel=rr

    if sl_rel is not None:
        exi=ei+sl_rel; runner_px=stop; runner_reason='SL'
    else:
        exi=end; runner_px=P_CLOSE[exi]; runner_reason='TIME60'
    runner_r=side*(runner_px-entry)/(STOP_MULT*atr)

    # same-bar harvest vs stop ambiguity: if both would happen same 5m bar, conservative => stop first, no harvest.
    if harv_rel is not None and sl_rel is not None and harv_rel==sl_rel:
        harv_rel=None

    paths.append(dict(**r,entry=entry,atr=atr,stop=stop,exit_i=exi,runner_r=runner_r,runner_reason=runner_reason,
                      harvest_target=ht,harvest_target_r=ht_r,harvest_rel=harv_rel))

def simulate(frac,cost_bps):
    rows=[]; open_until=-1
    for r in paths:
        ei=r['ei']
        if ei<=open_until: continue
        harvest_hit=(frac>0 and r['harvest_rel'] is not None)
        if harvest_hit:
            harvest_r=float(r['harvest_target_r'])
            gross=frac*harvest_r+(1-frac)*float(r['runner_r'])
            harvest_time=base.time.iloc[ei+int(r['harvest_rel'])]
            harvest_contrib=frac*harvest_r
            runner_contrib=(1-frac)*float(r['runner_r'])
        else:
            gross=float(r['runner_r'])
            harvest_time=pd.NaT
            harvest_contrib=0.0
            runner_contrib=float(r['runner_r'])

        # Cost convention: total round-turn bps on full initial notional.
        # Splitting one exit into partial+runner does not change proportional spread/commission total.
        cost_r=(r['entry']*(cost_bps/10000.0))/(STOP_MULT*r['atr'])
        net=gross-cost_r
        exi=int(r['exit_i'])
        rows.append(dict(harvest_frac=frac,cost_bps=cost_bps,setup_time=r['setup_time'],
                         entry_time=base.time.iloc[ei],exit_time=base.time.iloc[exi],
                         side='BUY' if r['side']>0 else 'SELL',z_setup=r['z_setup'],
                         entry=r['entry'],stop=r['stop'],harvest_target=r['harvest_target'],
                         harvest_target_r=r['harvest_target_r'],harvest_hit=harvest_hit,harvest_time=harvest_time,
                         gross_r=gross,net_r=net,harvest_contrib_r=harvest_contrib,runner_contrib_r=runner_contrib,
                         reason=r['runner_reason'],hold_h=(exi-ei)*5/60))
        open_until=exi
    return pd.DataFrame(rows)

def metrics(q):
    if len(q)==0:return {}
    x=q.net_r.to_numpy(float)
    pos=x[x>0].sum(); neg=-x[x<0].sum()
    sd=float(x.std(ddof=1)) if len(x)>1 else np.nan
    se=sd/np.sqrt(len(x)) if len(x)>1 and sd>0 else np.nan
    t=float(x.mean()/se) if np.isfinite(se) and se>0 else np.nan
    eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=float(np.max(pk[1:]-eq))
    return dict(n=len(q),wr=float((x>0).mean()),ev=float(x.mean()),t=t,pf=float(pos/neg) if neg>0 else np.inf,
                sumr=float(x.sum()),dd=dd,harvest_hit=float(q.harvest_hit.mean()),
                med_target_r=float(q.harvest_target_r.dropna().median()) if q.harvest_target_r.notna().any() else np.nan,
                avg_harvest_contrib=float(q.harvest_contrib_r.mean()),avg_runner_contrib=float(q.runner_contrib_r.mean()),
                sl_rate=float((q.reason=='SL').mean()),med_hold=float(q.hold_h.median()),se=se)

alltr=[]; rows=[]
for frac in HARVEST_FRACTIONS:
  for cost in COSTS:
    t=simulate(frac,cost)
    t['year']=pd.to_datetime(t.entry_time,utc=True).dt.year
    t['split']=np.where(pd.to_datetime(t.entry_time,utc=True)<pd.Timestamp('2025-01-01',tz='UTC'),'TRAIN','OOS')
    alltr.append(t)
    for split in ['TRAIN','OOS','ALL']:
      q=t if split=='ALL' else t[t.split==split]
      rows.append(dict(harvest_frac=frac,cost_bps=cost,split=split,**metrics(q)))

trades=pd.concat(alltr,ignore_index=True)
summ=pd.DataFrame(rows)
trades.to_csv(OUT/'LAB105_trades_all.csv',index=False)
summ.to_csv(OUT/'LAB105_summary.csv',index=False)

# TRAIN-only selection for each cost; OOS is read only after selection.
selected=[]
for cost in COSTS:
    g=summ[(summ.cost_bps==cost)&(summ.split=='TRAIN')].copy()
    best=g.sort_values(['ev','t'],ascending=[False,False]).iloc[0]
    frac=float(best.harvest_frac)
    oos=summ[(summ.cost_bps==cost)&(summ.split=='OOS')&(summ.harvest_frac==frac)].iloc[0]
    base_tr=summ[(summ.cost_bps==cost)&(summ.split=='TRAIN')&(summ.harvest_frac==0.0)].iloc[0]
    base_os=summ[(summ.cost_bps==cost)&(summ.split=='OOS')&(summ.harvest_frac==0.0)].iloc[0]
    selected.append(dict(cost_bps=cost,selected_frac=frac,
                         tr_n=int(best.n),tr_ev=best.ev,tr_t=best.t,tr_pf=best.pf,tr_dd=best.dd,
                         va_n=int(oos.n),va_ev=oos.ev,va_t=oos.t,va_pf=oos.pf,va_dd=oos.dd,
                         base_tr_ev=base_tr.ev,base_va_ev=base_os.ev,
                         delta_tr=best.ev-base_tr.ev,delta_va=oos.ev-base_os.ev,
                         va_harvest_hit=oos.harvest_hit,va_med_target_r=oos.med_target_r))
pd.DataFrame(selected).to_csv(OUT/'LAB105_selected.csv',index=False)

# Year/side for gross variants; helps see whether partial harvest fixes or harms regimes.
yr=[]; side_rows=[]
gross=trades[trades.cost_bps==0.0].copy()
for frac in HARVEST_FRACTIONS:
    q=gross[gross.harvest_frac==frac]
    for y,g in q.groupby('year'):
        yr.append(dict(harvest_frac=frac,year=int(y),**metrics(g)))
    for split in ['TRAIN','OOS']:
        z=q[q.split==split]
        for s in ['BUY','SELL']:
            g=z[z.side==s]
            side_rows.append(dict(harvest_frac=frac,split=split,side=s,**metrics(g)))
pd.DataFrame(yr).to_csv(OUT/'LAB105_yearly.csv',index=False)
pd.DataFrame(side_rows).to_csv(OUT/'LAB105_side.csv',index=False)

# Paired delta against no-harvest on exactly same executed trades for statistical clarity.
paired=[]
for cost in COSTS:
    b=trades[(trades.cost_bps==cost)&(trades.harvest_frac==0.0)][['entry_time','split','net_r']].rename(columns={'net_r':'base_r'})
    for frac in [0.25,0.50,0.75]:
        h=trades[(trades.cost_bps==cost)&(trades.harvest_frac==frac)][['entry_time','net_r','harvest_hit']].rename(columns={'net_r':'harvest_r'})
        q=b.merge(h,on='entry_time',how='inner')
        q['delta']=q.harvest_r-q.base_r
        for split in ['TRAIN','OOS']:
            z=q[q.split==split]
            d=z.delta.to_numpy(float)
            if len(d)>1:
                se=float(d.std(ddof=1)/np.sqrt(len(d))); tt=float(d.mean()/se) if se>0 else np.nan
            else: se=tt=np.nan
            paired.append(dict(cost_bps=cost,harvest_frac=frac,split=split,n=len(z),delta_ev=float(d.mean()) if len(d) else np.nan,
                               delta_t=tt,se=se,harvest_hit=float(z.harvest_hit.mean()) if len(z) else np.nan))
pd.DataFrame(paired).to_csv(OUT/'LAB105_paired_vs_baseline.csv',index=False)

lines=['# LAB105 — WIDE STOP + EARLY PROFIT HARVEST','',
       'Frozen: fresh |Z|>=1 inverse crowd -> M30 STRUCT4 -> next M30 open -> SL 3.5 H1 ATR -> runner TIME60.',
       'Harvest: causal M15 prior-48-bar (12h) high/low, valid only if beyond entry; target can trigger only in first 8h.',
       'Tested partial close fractions: 0%, 25%, 50%, 75%. No BE, no trailing, no re-add. Selection uses TRAIN only.','']
for r in selected:
    lines += [f"## Cost {r['cost_bps']:.1f} bps",
              f"- TRAIN-selected harvest: {int(r['selected_frac']*100)}%",
              f"- TRAIN N={r['tr_n']} EV={r['tr_ev']:+.3f}R PF={r['tr_pf']:.2f} t={r['tr_t']:.2f} DD={r['tr_dd']:.1f}R (delta vs no-harvest {r['delta_tr']:+.3f}R)",
              f"- OOS N={r['va_n']} EV={r['va_ev']:+.3f}R PF={r['va_pf']:.2f} t={r['va_t']:.2f} DD={r['va_dd']:.1f}R (delta vs no-harvest {r['delta_va']:+.3f}R)",
              f"- OOS harvest hit={r['va_harvest_hit']:.1%}, median target={r['va_med_target_r']:.2f}R",'']
(OUT/'LAB105_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
