#!/usr/bin/env python3
from __future__ import annotations
import json, math, re, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

OUT=Path("lab106_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
COSTS=[0.0,1.0,3.0,7.5]
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")

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
                if len(d): frames.append(d)
            except Exception: pass
        if not frames: raise RuntimeError(f"no csv in {zp}")
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

# ---------- common data ----------
flow=load_zip(FLOW_ZIP)
ft=pick(flow.columns,['timestamp','time','datetime','open_time'])
fr=pick(flow.columns,['longShortRatio','long_short_ratio','ls_ratio','globalLongShortAccountRatio','ratio'])
flow=flow[[ft,fr]].copy(); flow['time']=ptime(flow[ft]); flow['ratio']=pd.to_numeric(flow[fr],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(72,min_periods=72).mean(); sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)

raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','datetime','open_time'])
po=pick(raw.columns,['open']); ph=pick(raw.columns,['high']); pl=pick(raw.columns,['low']); pc=pick(raw.columns,['close'])
p=raw[[pt,po,ph,pl,pc]].copy(); p['time']=ptime(p[pt])
for c,nm in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]: p[nm]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# M15 for CrowdFade v2.00
m15=p.set_index('time').resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
m15['close_time']=m15.time+pd.Timedelta(minutes=15)
prev=m15.close.shift(1)
tr=pd.concat([(m15.high-m15.low),(m15.high-prev).abs(),(m15.low-prev).abs()],axis=1).max(axis=1)
m15['atr']=tr.rolling(14,min_periods=14).mean()
m15=pd.merge_asof(m15.sort_values('close_time'),flow[['time','z']].dropna().sort_values('time'),
                  left_on='close_time',right_on='time',direction='backward',tolerance=pd.Timedelta('10min'),suffixes=('','_z'))
m15=m15.dropna(subset=['atr','z']).reset_index(drop=True)

# 5m arrays
P_TIME=p.time.reset_index(drop=True)
P_OPEN=p.open.to_numpy(float); P_HIGH=p.high.to_numpy(float); P_LOW=p.low.to_numpy(float); P_CLOSE=p.close.to_numpy(float)

def pindex(ts,side='left'):
    return int(P_TIME.searchsorted(pd.Timestamp(ts),side=side))

def exit_fixed(entry_i,side,entry,stop,tp,max_minutes):
    end=min(entry_i+max_minutes//5-1,len(p)-1)
    for j in range(entry_i,end+1):
        h=P_HIGH[j]; l=P_LOW[j]
        hs=(l<=stop) if side>0 else (h>=stop)
        ht=(h>=tp) if side>0 else (l<=tp)
        if hs and ht: return j,stop,'SL_COLLISION'
        if hs:return j,stop,'SL'
        if ht:return j,tp,'TP'
    return end,P_CLOSE[end],'TIME'

# ---------- engine A: exact frozen CrowdFade v2.00 BTC core ----------
# Source defaults: z=2.05, M15 confirm 0.25 ATR max4 bars,
# passive retrace limit 0.60 ATR TTL20m, SL4.5 ATR, TP10 ATR, hold24h,
# ATR pause 1.0, max3/day, BE/trailing/chase OFF.
def simulate_crowdfade(cost_bps):
    rows=[]; i=15
    last_entry_px=np.nan; last_entry_atr=np.nan
    day_code=None; day_count=0
    while i < len(m15)-6:
        signal_close_time=m15.close_time.iloc[i]
        d=signal_close_time.date()
        if d!=day_code: day_code=d; day_count=0
        if day_count>=3: i+=1; continue

        z=float(m15.z.iloc[i])
        side=-1 if z>=2.05 else (1 if z<=-2.05 else 0)
        if side==0: i+=1; continue

        # ATR pause = price moved >=1 signal ATR from last entry.
        px=float(m15.close.iloc[i])
        if np.isfinite(last_entry_px) and np.isfinite(last_entry_atr):
            if abs(px-last_entry_px)/last_entry_atr < 1.0:
                i+=1; continue

        sig_px=px; sig_atr=float(m15.atr.iloc[i])
        confirmed_k=None
        for k in range(i+1,min(i+5,len(m15))):
            c=float(m15.close.iloc[k])
            ok=(c>=sig_px+0.25*sig_atr) if side>0 else (c<=sig_px-0.25*sig_atr)
            if ok:
                confirmed_k=k; break
        if confirmed_k is None:
            i+=5; continue

        conf_close=float(m15.close.iloc[confirmed_k])
        limit=conf_close-0.60*sig_atr if side>0 else conf_close+0.60*sig_atr
        pending_start=m15.close_time.iloc[confirmed_k]
        j0=pindex(pending_start,'left')
        j1=min(j0+4,len(p)) # 20 minutes = four M5 bars
        fill_j=None
        for j in range(j0,j1):
            touched=(P_LOW[j]<=limit) if side>0 else (P_HIGH[j]>=limit)
            if touched:
                fill_j=j; break
        if fill_j is None:
            # pending expires; next eligible M15 after expiry
            expiry=pending_start+pd.Timedelta(minutes=20)
            i=max(confirmed_k+1,int(m15.close_time.searchsorted(expiry,side='left')))
            continue

        entry=limit
        stop=entry-side*4.5*sig_atr
        tp=entry+side*10.0*sig_atr
        exi,exit_px,reason=exit_fixed(fill_j,side,entry,stop,tp,24*60)
        risk=4.5*sig_atr
        gross=side*(exit_px-entry)/risk
        cost_r=(entry*(cost_bps/10000.0))/risk
        net=gross-cost_r
        et=P_TIME.iloc[fill_j]; xt=P_TIME.iloc[exi]
        ed=et.date()
        if ed!=day_code:
            day_code=ed; day_count=0
        if day_count>=3:
            # Rare edge case: fill crosses UTC day boundary after signal.
            i=int(m15.close_time.searchsorted(xt,side='right')); continue
        day_count+=1
        rows.append(dict(engine='CROWDFade_v200',entry_time=et,exit_time=xt,side='BUY' if side>0 else 'SELL',
                         z=z,entry=entry,stop=stop,tp=tp,atr_ref=sig_atr,gross_r=gross,net_r=net,
                         reason=reason,hold_h=(exi-fill_j+1)*5/60,cost_bps=cost_bps))
        last_entry_px=entry; last_entry_atr=sig_atr
        # one position; resume only after exit
        i=max(confirmed_k+1,int(m15.close_time.searchsorted(xt,side='right')))
    return pd.DataFrame(rows)

# ---------- engine B: corrected chronological DRIFT CORE ----------
# exact LAB105 0%-harvest baseline: |Z|>=1 fresh episode -> M30 STRUCT4 -> next M30 open
# SL 3.5 H1 ATR, TIME60, one position.
prev5=p.close.shift(1)
tr5=pd.concat([(p.high-p.low),(p.high-prev5).abs(),(p.low-prev5).abs()],axis=1).max(axis=1)
p['atr5']=tr5.rolling(14,min_periods=14).mean()
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prevh=h1.close.shift(1)
trh=pd.concat([(h1.high-h1.low),(h1.high-prevh).abs(),(h1.low-prevh).abs()],axis=1).max(axis=1)
h1['atr_h1']=trh.rolling(14,min_periods=14).mean(); h1['close_time']=h1.time+pd.Timedelta(hours=1)
base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),flow[['time','z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min')).dropna(subset=['z','atr_h1']).reset_index(drop=True)
m30=base.set_index('time').resample('30min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),z=('z','last'),atr_h1=('atr_h1','last')).dropna().reset_index()
m30['close_time']=m30.time+pd.Timedelta(minutes=30)
B_OPEN=base.open.to_numpy(float); B_HIGH=base.high.to_numpy(float); B_LOW=base.low.to_numpy(float); B_CLOSE=base.close.to_numpy(float); B_ATR=base.atr_h1.to_numpy(float)

# fresh |Z| episode
eps=[]
zv=base.z.to_numpy(float)
for ii in range(1,len(base)-1):
    if abs(zv[ii])>=1.0 and abs(zv[ii-1])<1.0:
        eps.append((ii,-1 if zv[ii]>0 else 1,float(zv[ii]),base.time.iloc[ii]))

def struct4_entry(si,side):
    t0=base.time.iloc[si]
    k0=int(m30.close_time.searchsorted(t0,side='right'))
    for k in range(max(4,k0),min(k0+8,len(m30)-1)):
        hi=float(m30.high.iloc[k-4:k].max()); lo=float(m30.low.iloc[k-4:k].min()); c=float(m30.close.iloc[k])
        if (c>hi if side>0 else c<lo):
            et=m30.time.iloc[k+1]
            ei=int(base.time.searchsorted(et,side='left'))
            return ei if ei<len(base)-1 else None
    return None

cands=[]
for si,side,z0,st in eps:
    ei=struct4_entry(si,side)
    if ei is not None:cands.append((ei,side,z0,st))
cands.sort(key=lambda x:x[0])

def simulate_drift(cost_bps):
    rows=[]; open_until=-1
    for ei,side,z0,st in cands:
        if ei<=open_until: continue
        entry=B_OPEN[ei]; atr=B_ATR[ei]
        stop=entry-side*3.5*atr
        end=min(ei+60*12,len(base)-1)
        seg_h=B_HIGH[ei:end+1]; seg_l=B_LOW[ei:end+1]
        hs=(seg_l<=stop) if side>0 else (seg_h>=stop)
        hit=np.flatnonzero(hs)
        if len(hit):
            exi=ei+int(hit[0]); exit_px=stop; reason='SL'
        else:
            exi=end; exit_px=B_CLOSE[exi]; reason='TIME60'
        gross=side*(exit_px-entry)/(3.5*atr)
        cost_r=(entry*(cost_bps/10000.0))/(3.5*atr)
        net=gross-cost_r
        rows.append(dict(engine='DRIFT_CORE',entry_time=base.time.iloc[ei],exit_time=base.time.iloc[exi],
                         side='BUY' if side>0 else 'SELL',z=z0,entry=entry,stop=stop,tp=np.nan,atr_ref=atr,
                         gross_r=gross,net_r=net,reason=reason,hold_h=(exi-ei)*5/60,cost_bps=cost_bps))
        open_until=exi
    return pd.DataFrame(rows)

def metrics(q):
    if len(q)==0:return dict(n=0,ev=np.nan,t=np.nan,pf=np.nan,wr=np.nan,sumr=0,dd=np.nan,se=np.nan,trades_day=np.nan,trades_month=np.nan)
    x=q.net_r.to_numpy(float); sd=float(x.std(ddof=1)) if len(x)>1 else np.nan
    se=sd/math.sqrt(len(x)) if len(x)>1 and sd>0 else np.nan
    tt=float(x.mean()/se) if np.isfinite(se) and se>0 else np.nan
    pos=x[x>0].sum(); neg=-x[x<0].sum()
    eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=float(np.max(pk[1:]-eq))
    ttms=pd.to_datetime(q.entry_time,utc=True)
    days=max(1,(ttms.max().date()-ttms.min().date()).days+1)
    months=max(1,(ttms.max().year-ttms.min().year)*12+ttms.max().month-ttms.min().month+1)
    return dict(n=len(q),ev=float(x.mean()),t=tt,pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),
                sumr=float(x.sum()),dd=dd,se=se,trades_day=len(q)/days,trades_month=len(q)/months)

alltr=[]; summaries=[]
for cost in COSTS:
    for eng,fn in [('CROWDFade_v200',simulate_crowdfade),('DRIFT_CORE',simulate_drift)]:
        q=fn(cost)
        q['split']=np.where(pd.to_datetime(q.entry_time,utc=True)<TRAIN_END,'TRAIN','OOS')
        q['year']=pd.to_datetime(q.entry_time,utc=True).dt.year
        q['month']=pd.to_datetime(q.entry_time,utc=True).dt.strftime('%Y-%m')
        alltr.append(q)
        for split in ['TRAIN','OOS','ALL']:
            z=q if split=='ALL' else q[q.split==split]
            summaries.append(dict(cost_bps=cost,engine=eng,split=split,**metrics(z)))
trades=pd.concat(alltr,ignore_index=True)
summ=pd.DataFrame(summaries)
trades.to_csv(OUT/'LAB106_trades_all.csv',index=False)
summ.to_csv(OUT/'LAB106_summary.csv',index=False)

# year/side/month
yr=[]; sides=[]; mons=[]
for cost in COSTS:
  for eng in ['CROWDFade_v200','DRIFT_CORE']:
    q=trades[(trades.cost_bps==cost)&(trades.engine==eng)]
    for y,g in q.groupby('year'):yr.append(dict(cost_bps=cost,engine=eng,year=int(y),**metrics(g)))
    for split in ['TRAIN','OOS']:
      z=q[q.split==split]
      for side in ['BUY','SELL']:
        g=z[z.side==side]; sides.append(dict(cost_bps=cost,engine=eng,split=split,side=side,**metrics(g)))
    for mo,g in q.groupby('month'):
      mons.append(dict(cost_bps=cost,engine=eng,month=mo,n=len(g),sumr=float(g.net_r.sum()),ev=float(g.net_r.mean())))
pd.DataFrame(yr).to_csv(OUT/'LAB106_yearly.csv',index=False)
pd.DataFrame(sides).to_csv(OUT/'LAB106_side.csv',index=False)
month=pd.DataFrame(mons); month.to_csv(OUT/'LAB106_monthly.csv',index=False)

# Worst month and average/worst ratio.
wm=[]
for (cost,eng),g in month.groupby(['cost_bps','engine']):
    avg=float(g.sumr.mean()); idx=g.sumr.idxmin(); worst=float(g.loc[idx,'sumr'])
    wm.append(dict(cost_bps=cost,engine=eng,avg_month_sumr=avg,worst_month=str(g.loc[idx,'month']),worst_month_sumr=worst,
                   avg_to_abs_worst=avg/abs(worst) if worst<0 else np.inf))
pd.DataFrame(wm).to_csv(OUT/'LAB106_worst_month.csv',index=False)

# Direct comparison; no model selection is done in LAB106.
cmp=[]
for cost in COSTS:
  for split in ['TRAIN','OOS']:
    a=summ[(summ.cost_bps==cost)&(summ.engine=='CROWDFade_v200')&(summ.split==split)].iloc[0]
    b=summ[(summ.cost_bps==cost)&(summ.engine=='DRIFT_CORE')&(summ.split==split)].iloc[0]
    sed=math.sqrt((a.se if np.isfinite(a.se) else 0)**2+(b.se if np.isfinite(b.se) else 0)**2)
    diff=b.ev-a.ev
    cmp.append(dict(cost_bps=cost,split=split,crowd_n=int(a.n),crowd_ev=a.ev,crowd_pf=a.pf,crowd_t=a.t,crowd_dd=a.dd,
                    drift_n=int(b.n),drift_ev=b.ev,drift_pf=b.pf,drift_t=b.t,drift_dd=b.dd,
                    drift_minus_crowd_ev=diff,se_diff=sed,diff_in_se=(diff/sed if sed>0 else np.nan)))
pd.DataFrame(cmp).to_csv(OUT/'LAB106_comparison.csv',index=False)

meta={
 'crowdfade_source':'CrowdFadeMulti_v200.mq5 frozen defaults from Project file',
 'crowdfade':{'z_window_h':6,'z_threshold':2.05,'tf':'M15','confirm_atr':0.25,'confirm_max_bars':4,
              'passive_limit_atr':0.60,'pending_ttl_min':20,'sl_atr_m15':4.5,'tp_atr_m15':10.0,'hold_h':24,
              'pause_mode':'ATR','pause_atr':1.0,'max_trades_day':3,'BE':'OFF','trailing':'OFF','chase':'OFF'},
 'drift':{'z_window_h':6,'z_threshold':1.0,'signal':'fresh episode inverse crowd','confirm':'M30 STRUCT4',
          'entry':'next M30 open','sl':'3.5 H1 ATR','exit':'TIME60 or SL','one_position':True},
 'common':{'price':'Binance BTCUSDT 5m OHLC','flow':'Binance long/short ratio','train':'2021-2024','oos':'2025-2026 through price availability',
           'same_bar_collision':'stop first','costs_bps':COSTS}
}
(OUT/'LAB106_meta.json').write_text(json.dumps(meta,indent=2))

lines=['# LAB106 — CROWDFade BASELINE vs DRIFT CORE','',
       'Apples-to-apples historical comparison on the same BTCUSDT price/flow archive, TRAIN 2021-2024 and OOS 2025-2026.',
       'CrowdFade baseline is reconstructed from frozen CrowdFadeMulti_v200 defaults; DRIFT is corrected chronological LAB105 0%-harvest core.','']
for cost in COSTS:
    lines.append(f'## Cost {cost:.1f} bps')
    for split in ['TRAIN','OOS']:
        r=pd.DataFrame(cmp)
        x=r[(r.cost_bps==cost)&(r.split==split)].iloc[0]
        lines.append(f"- {split}: CrowdFade N={int(x.crowd_n)} EV={x.crowd_ev:+.3f} PF={x.crowd_pf:.2f} t={x.crowd_t:.2f} DD={x.crowd_dd:.1f}R | DRIFT N={int(x.drift_n)} EV={x.drift_ev:+.3f} PF={x.drift_pf:.2f} t={x.drift_t:.2f} DD={x.drift_dd:.1f}R | ΔEV={x.drift_minus_crowd_ev:+.3f} ({x.diff_in_se:+.2f} SE)")
    lines.append('')
(OUT/'LAB106_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
