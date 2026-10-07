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

# precompute causal broad candidates once; grid only filters them
def path_outcome(signal_time, side, atr):
    k=int(price.time.searchsorted(signal_time, side='right'))
    if k>=len(price): return None
    entry=float(price.open.iloc[k])
    end_t=signal_time+pd.Timedelta(minutes=MAX_H)
    b=int(price.time.searchsorted(end_t,side='right')-1)
    if b<k or b>=len(price): return None
    sub=price.iloc[k:b+1]
    fav=((sub.high-entry) if side>0 else (entry-sub.low))/atr
    adv=((entry-sub.low) if side>0 else (sub.high-entry))/atr
    out={'entry':entry,'mfe120':float(max(0.0,fav.max())),'mae120':float(max(0.0,adv.max()))}
    for mins in [5,15,30,60,120]:
        t=signal_time+pd.Timedelta(minutes=mins)
        j=int(price.time.searchsorted(t,side='right')-1)
        out[f'ret{mins}']=float(side*(price.close.iloc[j]-entry)/atr) if j>=k and j<len(price) else np.nan
    def fp(tp):
        for _,q in sub.iterrows():
            htp=(q.high>=entry+tp*atr) if side>0 else (q.low<=entry-tp*atr)
            hsl=(q.low<=entry-STOP_ATR*atr) if side>0 else (q.high>=entry+STOP_ATR*atr)
            if htp and hsl:return -1.0
            if hsl:return -1.0
            if htp:return tp/STOP_ATR
        return 0.0
    out['rr15']=fp(TP15_ATR); out['rr20']=fp(TP20_ATR)
    return out

z=d.z.to_numpy(float)
broad=[]
for lb in [2,3,4]:
    for i in range(max(ZWIN,lb+1),len(d)):
        turn=i-1; base=turn-lb
        zz=z[turn]
        if not np.isfinite(zz) or abs(zz)<0.50 or not np.isfinite(z[i]): continue
        prev=z[turn-lb:turn]
        if len(prev)!=lb or not np.all(np.isfinite(prev)): continue
        ishigh=np.all(zz>prev); islow=np.all(zz<prev)
        if not (ishigh or islow): continue
        if ishigh:
            approach=zz-z[base]; reversal=zz-z[i]; extreme_type='HIGH'
        else:
            approach=z[base]-zz; reversal=z[i]-zz; extreme_type='LOW'
        if approach<0.10 or reversal<0.06: continue
        sigt=d.time.iloc[i]; atr=float(d.atr.iloc[i])
        if not np.isfinite(atr) or atr<=0: continue
        for mapping in ['inverse','direct']:
            if extreme_type=='HIGH': side=-1 if mapping=='inverse' else +1
            else: side=+1 if mapping=='inverse' else -1
            st=path_outcome(sigt,side,atr)
            if st is None: continue
            broad.append(dict(signal_time=sigt,z_turn_time=d.time.iloc[turn],side=side,z_turn=zz,absz=abs(zz),
                              approach=approach,reversal=reversal,lookback=lb,mapping=mapping,**st))
broad=pd.DataFrame(broad)
if len(broad)==0: raise RuntimeError('No broad candidates')
broad.to_csv(OUT/'LAB100_broad_candidates.csv',index=False)

grid=[]
for mapping in ['inverse','direct']:
  mm=broad[broad.mapping==mapping]
  for az in [0.50,0.70,1.00]:
    for ap in [0.10,0.18,0.25]:
      for rv in [0.06,0.12,0.18]:
        for lb in [2,3,4]:
          q=mm[(mm.absz>=az)&(mm.approach>=ap)&(mm.reversal>=rv)&(mm.lookback==lb)]
          if len(q)<20: continue
          train=q[q.signal_time < pd.Timestamp('2025-01-01',tz='UTC')]
          val=q[q.signal_time >= pd.Timestamp('2025-01-01',tz='UTC')]
          def met(x,pfx):
            if len(x)==0:return {pfx+'n':0,pfx+'ev20':np.nan,pfx+'hit20':np.nan,pfx+'ret30':np.nan,pfx+'ret60':np.nan,pfx+'ret120':np.nan,pfx+'mfe120':np.nan,pfx+'mae120':np.nan}
            rr=x.rr20.to_numpy(float)
            return {pfx+'n':len(x),pfx+'ev20':float(rr.mean()),pfx+'hit20':float((rr>0).mean()),pfx+'ret30':float(x.ret30.mean()),pfx+'ret60':float(x.ret60.mean()),pfx+'ret120':float(x.ret120.mean()),pfx+'mfe120':float(x.mfe120.mean()),pfx+'mae120':float(x.mae120.mean())}
          row=dict(mapping=mapping,min_abs_z=az,min_approach=ap,min_reversal=rv,lookback=lb)
          row.update(met(train,'tr_')); row.update(met(val,'va_')); grid.append(row)
grid=pd.DataFrame(grid)
if len(grid)==0: raise RuntimeError('No grid rows')
eligible=grid[(grid.tr_n>=80)&(grid.va_n>=20)].copy()
if len(eligible)==0: eligible=grid.copy()
eligible=eligible.sort_values(['tr_ev20','tr_ret60','tr_n'],ascending=[False,False,False])
best=eligible.iloc[0].to_dict()
grid['stability']=np.minimum(grid.tr_ev20,grid.va_ev20)
grid['combined_ev20']=(grid.tr_ev20*grid.tr_n+grid.va_ev20*grid.va_n)/(grid.tr_n+grid.va_n)
grid.to_csv(OUT/'LAB100_full_grid.csv',index=False)
eligible.head(50).to_csv(OUT/'LAB100_train_rank_top50.csv',index=False)
grid.sort_values(['stability','combined_ev20'],ascending=[False,False]).head(50).to_csv(OUT/'LAB100_stability_top50.csv',index=False)

bestq=broad[(broad.mapping==best['mapping'])&(broad.absz>=best['min_abs_z'])&(broad.approach>=best['min_approach'])&(broad.reversal>=best['min_reversal'])&(broad.lookback==int(best['lookback']))].copy()
bestq.to_csv(OUT/'LAB100_best_profile_signals.csv',index=False)
ys=[]
for y,g in bestq.groupby(bestq.signal_time.dt.year):
    rr=g.rr20.to_numpy(float)
    ys.append(dict(year=int(y),n=len(g),ev20=float(rr.mean()),hit20=float((rr>0).mean()),ret30=float(g.ret30.mean()),ret60=float(g.ret60.mean()),ret120=float(g.ret120.mean()),mfe120=float(g.mfe120.mean()),mae120=float(g.mae120.mean())))
pd.DataFrame(ys).to_csv(OUT/'LAB100_best_profile_yearly.csv',index=False)

stable=grid.sort_values(['stability','combined_ev20'],ascending=[False,False]).iloc[0]
meta={'flow_files':flow_names,'price_files':price_names,'flow_time_col':ft,'flow_ratio_col':fr,'price_time_col':pt,'rows_flow_5m':len(flow),'rows_price_5m':len(price),'range_flow':[str(flow.time.min()),str(flow.time.max())],'range_price':[str(price.time.min()),str(price.time.max())],'broad_candidates':len(broad),'best_train_selected':best}
(OUT/'LAB100_meta.json').write_text(json.dumps(meta,indent=2,default=str))
lines=['# LAB100 historical Z-turn validity sweep','',
f"Flow range: {flow.time.min()} -> {flow.time.max()} | 5m rows={len(flow):,}",
f"Price range: {price.time.min()} -> {price.time.max()} | 5m rows={len(price):,}",
f"Broad causal outcomes: {len(broad):,}",'',
'## Train-selected profile (selection uses pre-2025 only)',
f"- mapping={best['mapping']}, |Z|>={best['min_abs_z']}, approach>={best['min_approach']}, reversal>={best['min_reversal']}, lookback={int(best['lookback'])}",
f"- TRAIN N={int(best['tr_n'])}, EV2R={best['tr_ev20']:.3f}R, hit2R={best['tr_hit20']:.1%}, ret60={best['tr_ret60']:.3f} ATR",
f"- VALIDATION 2025+ N={int(best['va_n'])}, EV2R={best['va_ev20']:.3f}R, hit2R={best['va_hit20']:.1%}, ret60={best['va_ret60']:.3f} ATR",'',
'## Most stable profile (diagnostic only)',
f"- mapping={stable.mapping}, |Z|>={stable.min_abs_z}, approach>={stable.min_approach}, reversal>={stable.min_reversal}, lookback={int(stable.lookback)}",
f"- TRAIN N={int(stable.tr_n)}, EV2R={stable.tr_ev20:.3f}R; VALIDATION N={int(stable.va_n)}, EV2R={stable.va_ev20:.3f}R",'',
'Signal is causal at first 5m observation after Z extremum proving reversal; entry proxy is next 5m open; same-bar TP/SL collision resolves to SL.']
(OUT/'LAB100_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
