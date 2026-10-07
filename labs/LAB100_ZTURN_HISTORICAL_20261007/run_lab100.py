#!/usr/bin/env python3
from __future__ import annotations
import csv, glob, json, math, os, re, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

OUT=Path("lab100_hist_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
ZWIN=72
ATR_N=14
MAX_H=120
STOP_ATR=0.50
TP15_ATR=0.75
TP20_ATR=1.00

def normcol(s):
    return re.sub(r'[^a-z0-9]+','',str(s).lower())

def pick_col(cols, prefs):
    nc={normcol(c):c for c in cols}
    for p in prefs:
        pn=normcol(p)
        if pn in nc: return nc[pn]
    for p in prefs:
        pn=normcol(p)
        for k,v in nc.items():
            if pn in k or k in pn:
                return v
    return None

def load_any_csv_from_zip(zpath):
    with zipfile.ZipFile(zpath) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if not names: raise RuntimeError(f'no csv in {zpath}')
        frames=[]
        for n in names:
            with z.open(n) as f:
                try:
                    d=pd.read_csv(f)
                except Exception:
                    continue
            if len(d): frames.append(d)
        if not frames: raise RuntimeError(f'no readable csv in {zpath}')
        if len(frames)==1: return frames[0], names
        # concat only compatible schemas
        common=set(frames[0].columns)
        for d in frames[1:]: common &= set(d.columns)
        if len(common)>=3:
            return pd.concat([d[list(common)] for d in frames], ignore_index=True), names
        return frames[0], names

flow, flow_names=load_any_csv_from_zip(FLOW_ZIP)
price, price_names=load_any_csv_from_zip(PRICE_ZIP)

# infer flow timestamp + LS ratio
ft=pick_col(flow.columns, ['timestamp','time','datetime','open_time','close_time'])
fr=pick_col(flow.columns, ['longShortRatio','long_short_ratio','ls_ratio','longshortratio','globalLongShortAccountRatio','ratio'])
if ft is None or fr is None:
    raise RuntimeError(f'Could not infer flow time/ratio columns. columns={list(flow.columns)}')

# price columns
pt=pick_col(price.columns,['time','timestamp','datetime','open_time'])
po=pick_col(price.columns,['open'])
ph=pick_col(price.columns,['high'])
pl=pick_col(price.columns,['low'])
pc=pick_col(price.columns,['close'])
if None in [pt,po,ph,pl,pc]:
    raise RuntimeError(f'Could not infer price OHLC columns. columns={list(price.columns)}')

def parse_time(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce')
        med=float(x.dropna().median()) if x.notna().any() else 0
        unit='ms' if med>1e11 else 's'
        return pd.to_datetime(x,unit=unit,errors='coerce',utc=True)
    return pd.to_datetime(s,errors='coerce',utc=True)

flow=flow[[ft,fr]].copy()
flow['time']=parse_time(flow[ft]); flow['ratio']=pd.to_numeric(flow[fr],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[(flow.ratio>0)&np.isfinite(flow.ratio)].reset_index(drop=True)

price=price[[pt,po,ph,pl,pc]].copy()
price['time']=parse_time(price[pt])
for c,new in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:
    price[new]=pd.to_numeric(price[c],errors='coerce')
price=price[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)

# resample price to exact 5m if source isn't clean
price=price.set_index('time').resample('5min').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna().reset_index()
pcprev=price.close.shift(1)
tr=pd.concat([(price.high-price.low),(price.high-pcprev).abs(),(price.low-pcprev).abs()],axis=1).max(axis=1)
price['atr']=tr.rolling(ATR_N,min_periods=ATR_N).mean()

# align ratio to 5m closed observations
flow=flow.set_index('time').resample('5min').last().dropna().reset_index()
r=flow.ratio.astype(float)
m=r.rolling(ZWIN,min_periods=ZWIN).mean()
sd=r.rolling(ZWIN,min_periods=ZWIN).std(ddof=0)
flow['z']=(r-m)/sd.replace(0,np.nan)

# merge onto price timestamps for causal signal evaluation
d=pd.merge_asof(flow.sort_values('time'), price[['time','open','high','low','close','atr']].sort_values('time'),
                on='time', direction='backward', tolerance=pd.Timedelta('5min'))
d=d.dropna(subset=['z','close','atr']).reset_index(drop=True)

# precompute future path by locating exact price index
pidx=pd.Series(np.arange(len(price)),index=price.time)
def bracket_and_stats(signal_time,side,entry,atr):
    # signal is known at close of 5m observation; use next 5m open as causal entry proxy
    k=int(price.time.searchsorted(signal_time,side='right'))
    if k>=len(price): return None
    entry=float(price.open.iloc[k])
    end_t=signal_time+pd.Timedelta(minutes=MAX_H)
    b=int(price.time.searchsorted(end_t,side='right')-1)
    if b<k or b>=len(price): return None
    sub=price.iloc[k:b+1]
    fav=((sub.high-entry) if side>0 else (entry-sub.low))/atr
    adv=((entry-sub.low) if side>0 else (sub.high-entry))/atr
    mfe=float(max(0,fav.max())); mae=float(max(0,adv.max()))
    out={}
    for mins in [5,15,30,60,120]:
        t=signal_time+pd.Timedelta(minutes=mins)
        j=int(price.time.searchsorted(t,side='right')-1)
        out[f'ret{mins}']=float(side*(price.close.iloc[j]-entry)/atr) if j>=k and j<len(price) else np.nan
    def firstpass(tp):
        sl=STOP_ATR
        for _,q in sub.iterrows():
            hit_tp=(q.high>=entry+tp*atr) if side>0 else (q.low<=entry-tp*atr)
            hit_sl=(q.low<=entry-sl*atr) if side>0 else (q.high>=entry+sl*atr)
            if hit_tp and hit_sl: return -1.0
            if hit_sl: return -1.0
            if hit_tp: return tp/sl
        return 0.0
    out.update(entry=entry,mfe120=mfe,mae120=mae,rr15=firstpass(TP15_ATR),rr20=firstpass(TP20_ATR))
    return out

def candidates(absz,approach_thr,reversal_thr,lb,mapping):
    rows=[]
    z=d.z.to_numpy(float)
    for i in range(max(ZWIN,lb+1),len(d)):
        turn=i-1; base=turn-lb
        zz=z[turn]
        if not np.isfinite(zz) or abs(zz)<absz: continue
        prev=z[turn-lb:turn]
        if len(prev)!=lb or not np.all(np.isfinite(prev)) or not np.isfinite(z[i]): continue
        ishigh=np.all(zz>prev); islow=np.all(zz<prev)
        side=0; approach=rev=0.0
        if ishigh:
            approach=zz-z[base]; rev=zz-z[i]
            if approach>=approach_thr and rev>=reversal_thr:
                side=-1 if mapping=='inverse' else +1
        elif islow:
            approach=z[base]-zz; rev=z[i]-zz
            if approach>=approach_thr and rev>=reversal_thr:
                side=+1 if mapping=='inverse' else -1
        if side==0: continue
        sigt=d.time.iloc[i]  # first observation proving the turn
        atr=float(d.atr.iloc[i])
        if not np.isfinite(atr) or atr<=0: continue
        st=bracket_and_stats(sigt,side,float(d.close.iloc[i]),atr)
        if st is None: continue
        rows.append(dict(signal_time=sigt,z_turn_time=d.time.iloc[turn],side=side,z_turn=zz,absz=abs(zz),
                         approach=approach,reversal=rev,lb=lb,mapping=mapping,**st))
    return pd.DataFrame(rows)

grid=[]
all_frames={}
for mapping in ['inverse','direct']:
  for az in [0.3,0.5,0.7,1.0,1.25,1.5,2.0]:
    for ap in [0.05,0.10,0.18,0.25,0.35,0.50]:
      for rv in [0.03,0.06,0.10,0.12,0.18,0.25]:
        for lb in [2,3,4,6]:
          q=candidates(az,ap,rv,lb,mapping)
          if len(q)<20: continue
          q['year']=q.signal_time.dt.year
          train=q[q.signal_time < pd.Timestamp('2025-01-01',tz='UTC')]
          val=q[q.signal_time >= pd.Timestamp('2025-01-01',tz='UTC')]
          def met(x,pfx):
            if len(x)==0:return {pfx+'n':0}
            rr=x.rr20.to_numpy(float)
            return {
              pfx+'n':len(x), pfx+'ev20':float(rr.mean()), pfx+'hit20':float((rr>0).mean()),
              pfx+'ret30':float(x.ret30.mean()), pfx+'ret60':float(x.ret60.mean()), pfx+'ret120':float(x.ret120.mean()),
              pfx+'mfe120':float(x.mfe120.mean()), pfx+'mae120':float(x.mae120.mean())
            }
          row=dict(mapping=mapping,min_abs_z=az,min_approach=ap,min_reversal=rv,lookback=lb)
          row.update(met(train,'tr_')); row.update(met(val,'va_'))
          grid.append(row)
grid=pd.DataFrame(grid)
if len(grid)==0: raise RuntimeError('No grid rows with >=20 signals')

# choose on TRAIN only, require train>=80 and validation>=20
eligible=grid[(grid.tr_n>=80)&(grid.va_n>=20)].copy()
if len(eligible)==0: eligible=grid.copy()
eligible=eligible.sort_values(['tr_ev20','tr_ret60','tr_n'],ascending=[False,False,False])
best=eligible.iloc[0].to_dict()

# diagnostics: robust top profiles by validation and stability
grid['stability']=np.minimum(grid.tr_ev20,grid.va_ev20)
grid['combined_ev20']=(grid.tr_ev20*grid.tr_n+grid.va_ev20*grid.va_n)/(grid.tr_n+grid.va_n)
grid.to_csv(OUT/'LAB100_full_grid.csv',index=False)
eligible.head(50).to_csv(OUT/'LAB100_train_rank_top50.csv',index=False)
grid.sort_values(['stability','combined_ev20'],ascending=[False,False]).head(50).to_csv(OUT/'LAB100_stability_top50.csv',index=False)

bestq=candidates(best['min_abs_z'],best['min_approach'],best['min_reversal'],int(best['lookback']),best['mapping'])
bestq.to_csv(OUT/'LAB100_best_profile_signals.csv',index=False)

# yearly summary
ys=[]
for y,g in bestq.groupby(bestq.signal_time.dt.year):
    rr=g.rr20.to_numpy(float)
    ys.append(dict(year=int(y),n=len(g),ev20=float(rr.mean()),hit20=float((rr>0).mean()),ret30=float(g.ret30.mean()),ret60=float(g.ret60.mean()),ret120=float(g.ret120.mean()),mfe120=float(g.mfe120.mean()),mae120=float(g.mae120.mean())))
pd.DataFrame(ys).to_csv(OUT/'LAB100_best_profile_yearly.csv',index=False)

meta={
 'flow_files':flow_names,'price_files':price_names,'flow_columns':list(flow.columns),'price_columns':list(price.columns),
 'flow_time_col':ft,'flow_ratio_col':fr,'price_time_col':pt,'rows_flow_5m':len(flow),'rows_price_5m':len(price),
 'range_flow':[str(flow.time.min()),str(flow.time.max())],'range_price':[str(price.time.min()),str(price.time.max())],
 'best_train_selected':best
}
(OUT/'LAB100_meta.json').write_text(json.dumps(meta,indent=2,default=str))

# concise report
stable=grid.sort_values(['stability','combined_ev20'],ascending=[False,False]).iloc[0]
lines=[
 '# LAB100 historical Z-turn validity sweep','',
 f"Flow range: {flow.time.min()} -> {flow.time.max()} | 5m rows={len(flow):,}",
 f"Price range: {price.time.min()} -> {price.time.max()} | 5m rows={len(price):,}",
 '',
 '## Train-selected profile (selection uses pre-2025 only)',
 f"- mapping={best['mapping']}, |Z|>={best['min_abs_z']}, approach>={best['min_approach']}, reversal>={best['min_reversal']}, lookback={int(best['lookback'])}",
 f"- TRAIN N={int(best['tr_n'])}, EV2R={best['tr_ev20']:.3f}R, hit2R={best['tr_hit20']:.1%}, ret60={best['tr_ret60']:.3f} ATR",
 f"- VALIDATION 2025+ N={int(best['va_n'])}, EV2R={best['va_ev20']:.3f}R, hit2R={best['va_hit20']:.1%}, ret60={best['va_ret60']:.3f} ATR",
 '',
 '## Most stable profile by min(train EV, validation EV) — diagnostic only',
 f"- mapping={stable.mapping}, |Z|>={stable.min_abs_z}, approach>={stable.min_approach}, reversal>={stable.min_reversal}, lookback={int(stable.lookback)}",
 f"- TRAIN N={int(stable.tr_n)}, EV2R={stable.tr_ev20:.3f}R; VALIDATION N={int(stable.va_n)}, EV2R={stable.va_ev20:.3f}R",
 '',
 'Signal is causal at the first 5m observation after the Z extremum that proves the reversal. Entry proxy is next 5m open. Same-bar TP/SL collision resolves to SL.'
]
(OUT/'LAB100_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
