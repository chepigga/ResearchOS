#!/usr/bin/env python3
from __future__ import annotations
import math,re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab110_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")

HORIZONS_MIN=[5,15,30,60,120,240,480,720,1440,2160,2880]
HORIZON_LABELS={5:'5m',15:'15m',30:'30m',60:'1h',120:'2h',240:'4h',480:'8h',720:'12h',1440:'24h',2160:'36h',2880:'48h'}
FAV_LEVELS=[0.10,0.25,0.50,1.00,1.50]
ADV_LEVELS=[0.25,0.50,1.00]
Z_BINS=[1.0,1.25,1.5,2.0,2.5,np.inf]
Z_LABELS=['1.00-1.25','1.25-1.50','1.50-2.00','2.00-2.50','2.50+']

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

# --------- data ----------
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
for c,nm in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]: p[nm]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# H1 ATR14, completed bars only
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prev=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
h1['atr_h1']=tr.rolling(14,min_periods=14).mean(); h1['close_time']=h1.time+pd.Timedelta(hours=1)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),flow[['time','z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['z','atr_h1']).reset_index(drop=True)

BT=base.time.reset_index(drop=True)
BO=base.open.to_numpy(float); BH=base.high.to_numpy(float); BL=base.low.to_numpy(float); BC=base.close.to_numpy(float); BATR=base.atr_h1.to_numpy(float); BZ=base.z.to_numpy(float)

# M15 for STRUCT4 marker
m15=base.set_index('time').resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
m15['close_time']=m15.time+pd.Timedelta(minutes=15)

def z_bin(v):
    a=abs(v)
    for i in range(len(Z_LABELS)):
        if Z_BINS[i] <= a < Z_BINS[i+1]: return Z_LABELS[i]
    return None

def first_hit(side,anchor,atr,start_i,end_i,level,favorable=True):
    if end_i<start_i:return np.nan
    if favorable:
        arr=(BH[start_i:end_i+1]-anchor)/atr if side>0 else (anchor-BL[start_i:end_i+1])/atr
    else:
        arr=(anchor-BL[start_i:end_i+1])/atr if side>0 else (BH[start_i:end_i+1]-anchor)/atr
    ix=np.flatnonzero(arr>=level)
    if not len(ix): return np.nan
    return (int(ix[0])+1)*5.0

def time_m5_break3(side,start_i,end_i):
    for j in range(max(start_i,3),end_i+1):
        hi=float(np.max(BH[j-3:j])); lo=float(np.min(BL[j-3:j]))
        if (BC[j]>hi if side>0 else BC[j]<lo):
            return (j-start_i+1)*5.0
    return np.nan

def time_m15_struct4(side,t0,tend):
    k0=int(m15.close_time.searchsorted(t0,side='right'))
    for k in range(max(4,k0),len(m15)):
        if m15.close_time.iloc[k]>tend: break
        hi=float(m15.high.iloc[k-4:k].max()); lo=float(m15.low.iloc[k-4:k].min()); c=float(m15.close.iloc[k])
        if (c>hi if side>0 else c<lo):
            return (m15.close_time.iloc[k]-t0).total_seconds()/60.0
    return np.nan

def trajectory_class(row):
    # Frozen descriptive taxonomy, not optimized and not a trading gate.
    c1=row['close_1h_atr']; mfe1=row['mfe_1h_atr']; mae1=row['mae_1h_atr']
    c4=row['close_4h_atr']; mfe4=row['mfe_4h_atr']; mae4=row['mae_4h_atr']
    c24=row['close_24h_atr']; mfe24=row['mfe_24h_atr']; mae24=row['mae_24h_atr']
    c48=row['close_48h_atr']; mfe48=row['mfe_48h_atr']; mae48=row['mae_48h_atr']
    if c1>=0.25 and mfe1>=0.50 and mae1<0.25:
        return 'IMMEDIATE_CONTINUATION'
    if c1<=-0.25 and mae1>=0.50 and mfe1<0.25:
        return 'IMMEDIATE_FAILURE'
    if mfe4>=0.50 and c24<=0 and mae24>=0.50:
        return 'FALSE_START'
    if mae4>=0.25 and mfe24>=1.00 and c24>0:
        return 'PULLBACK_THEN_GO'
    if abs(c4)<0.25 and mfe48>=1.00 and c48>=0.50:
        return 'DELAYED_DRIFT'
    if mfe48<0.75 and mae48<0.75:
        return 'COMPRESSION'
    return 'MIXED'

# Fresh signal episodes: first |Z|>=1 after previous bar |Z|<1.
events=[]
last_full_i=len(base)-1-2880//5
for i in range(1,len(base)):
    if not (abs(BZ[i])>=1.0 and abs(BZ[i-1])<1.0): continue
    if i>last_full_i: continue   # main atlas requires full 48h path
    side=-1 if BZ[i]>0 else 1
    anchor=float(BC[i]); atr=float(BATR[i])
    if not np.isfinite(atr) or atr<=0: continue
    row=dict(signal_time=BT.iloc[i],side='BUY' if side>0 else 'SELL',side_num=side,z=float(BZ[i]),abs_z=abs(float(BZ[i])),z_bin=z_bin(BZ[i]),anchor=anchor,atr_h1=atr,year=int(BT.iloc[i].year))
    for mins in HORIZONS_MIN:
        end=min(i+mins//5,len(base)-1)
        hi=float(np.max(BH[i+1:end+1])) if end>=i+1 else anchor
        lo=float(np.min(BL[i+1:end+1])) if end>=i+1 else anchor
        close=float(BC[end])
        mfe=((hi-anchor)/atr) if side>0 else ((anchor-lo)/atr)
        mae=((anchor-lo)/atr) if side>0 else ((hi-anchor)/atr)
        cdisp=side*(close-anchor)/atr
        lab=HORIZON_LABELS[mins]
        row[f'mfe_{lab}_atr']=mfe; row[f'mae_{lab}_atr']=mae; row[f'close_{lab}_atr']=cdisp
    end48=i+2880//5
    for lv in FAV_LEVELS: row[f't_fav_{lv:.2f}R_min']=first_hit(side,anchor,atr,i+1,end48,lv,True)
    for lv in ADV_LEVELS: row[f't_adv_{lv:.2f}R_min']=first_hit(side,anchor,atr,i+1,end48,lv,False)
    row['t_m5_break3_min']=time_m5_break3(side,i+1,end48)
    row['t_m15_struct4_min']=time_m15_struct4(side,BT.iloc[i],BT.iloc[end48])
    # adverse excursion before first favorable milestones
    for lv in [0.50,1.00,1.50]:
        t=row[f't_fav_{lv:.2f}R_min']
        if np.isfinite(t):
            j=min(i+int(t//5),end48)
            if side>0: adv=(anchor-float(np.min(BL[i+1:j+1])))/atr
            else: adv=(float(np.max(BH[i+1:j+1]))-anchor)/atr
            row[f'mae_before_fav_{lv:.2f}R']=max(0.0,adv)
        else:
            row[f'mae_before_fav_{lv:.2f}R']=np.nan
    # simple reclaim: adverse 0.25R occurs first, then favorable +0.25R later
    ta=row['t_adv_0.25R_min']; tf=row['t_fav_0.25R_min']
    row['reclaim_after_adverse025']=int(np.isfinite(ta) and np.isfinite(tf) and tf>ta)
    events.append(row)

ev=pd.DataFrame(events)
ev['split']=np.where(pd.to_datetime(ev.signal_time,utc=True)<TRAIN_END,'TRAIN','OOS')
ev['trajectory_class']=ev.apply(trajectory_class,axis=1)
ev.to_csv(OUT/'LAB110_event_atlas.csv',index=False)

# Aggregate trajectory grid
agg=[]
for split in ['TRAIN','OOS','ALL']:
    q=ev if split=='ALL' else ev[ev.split==split]
    for zb in Z_LABELS:
        for side in ['BUY','SELL','ALL']:
            z=q[q.z_bin==zb]
            if side!='ALL': z=z[z.side==side]
            if not len(z): continue
            for mins in HORIZONS_MIN:
                lab=HORIZON_LABELS[mins]
                agg.append(dict(split=split,z_bin=zb,side=side,horizon=lab,n=len(z),
                                mean_mfe=float(z[f'mfe_{lab}_atr'].mean()),median_mfe=float(z[f'mfe_{lab}_atr'].median()),
                                mean_mae=float(z[f'mae_{lab}_atr'].mean()),median_mae=float(z[f'mae_{lab}_atr'].median()),
                                mean_close=float(z[f'close_{lab}_atr'].mean()),median_close=float(z[f'close_{lab}_atr'].median()),
                                p_close_positive=float((z[f'close_{lab}_atr']>0).mean())))
pd.DataFrame(agg).to_csv(OUT/'LAB110_trajectory_grid.csv',index=False)

# Class distribution + forward outcome by class
cls=[]
for split in ['TRAIN','OOS','ALL']:
    q=ev if split=='ALL' else ev[ev.split==split]
    for c,g in q.groupby('trajectory_class'):
        cls.append(dict(split=split,trajectory_class=c,n=len(g),share=len(g)/len(q),
                        mean_close_24h=float(g.close_24h_atr.mean()),mean_close_48h=float(g.close_48h_atr.mean()),
                        mean_mfe_48h=float(g.mfe_48h_atr.mean()),mean_mae_48h=float(g.mae_48h_atr.mean()),
                        median_t_struct4=float(g.t_m15_struct4_min.median()) if g.t_m15_struct4_min.notna().any() else np.nan))
pd.DataFrame(cls).to_csv(OUT/'LAB110_trajectory_classes.csv',index=False)

# Reaction-event conditional diagnostics
react=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    conditions={
      'ALL':pd.Series(True,index=q.index),
      'M5_BREAK3_1H':q.t_m5_break3_min<=60,
      'M15_STRUCT4_4H':q.t_m15_struct4_min<=240,
      'FAV025_1H':q['t_fav_0.25R_min']<=60,
      'ADV025_BEFORE_FAV025':(q['t_adv_0.25R_min']<q['t_fav_0.25R_min']),
      'RECLAIM_AFTER_ADV025':q.reclaim_after_adverse025==1,
      'NO_FAV025_4H':q['t_fav_0.25R_min']>240
    }
    for name,mask in conditions.items():
        g=q[mask.fillna(False)] if hasattr(mask,'fillna') else q
        if not len(g): continue
        react.append(dict(split=split,reaction=name,n=len(g),share=len(g)/len(q),
                          mean_close_24h=float(g.close_24h_atr.mean()),p24=float((g.close_24h_atr>0).mean()),
                          mean_close_48h=float(g.close_48h_atr.mean()),p48=float((g.close_48h_atr>0).mean()),
                          mean_mfe48=float(g.mfe_48h_atr.mean()),mean_mae48=float(g.mae_48h_atr.mean())))
pd.DataFrame(react).to_csv(OUT/'LAB110_reaction_diagnostics.csv',index=False)

# Signal intensity summary
zi=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for zb,g in q.groupby('z_bin',observed=True):
        zi.append(dict(split=split,z_bin=zb,n=len(g),mean_close_4h=float(g.close_4h_atr.mean()),mean_close_24h=float(g.close_24h_atr.mean()),
                       mean_close_48h=float(g.close_48h_atr.mean()),p48=float((g.close_48h_atr>0).mean()),
                       median_t_fav025=float(g['t_fav_0.25R_min'].median()),median_t_struct4=float(g.t_m15_struct4_min.median())))
pd.DataFrame(zi).to_csv(OUT/'LAB110_z_intensity.csv',index=False)

# Year summary
yr=[]
for y,g in ev.groupby('year'):
    yr.append(dict(year=int(y),n=len(g),mean_close_24h=float(g.close_24h_atr.mean()),mean_close_48h=float(g.close_48h_atr.mean()),
                   p48=float((g.close_48h_atr>0).mean()),mean_mfe48=float(g.mfe_48h_atr.mean()),mean_mae48=float(g.mae_48h_atr.mean())))
pd.DataFrame(yr).to_csv(OUT/'LAB110_yearly.csv',index=False)

# concise report
lines=['# LAB110 — Z SIGNAL × PRICE TRAJECTORY ATLAS','',
'Signal clock is frozen: first 5m observation where |Z| crosses from <1 to >=1; direction is inverse crowd. No STRUCT4 or other execution filter is required to enter the atlas.',
'Anchor is price close at signal time. All future price paths are normalized by causal last-completed H1 ATR. Main cohort requires a complete 48h price path.',
'This is descriptive research only: no threshold is selected from OOS and no trading rule is promoted.','',
f"Events: ALL N={len(ev)} | TRAIN N={(ev.split=='TRAIN').sum()} | OOS N={(ev.split=='OOS').sum()}",'',
'## Baseline path']
for split in ['TRAIN','OOS']:
    g=ev[ev.split==split]
    lines.append(f"- {split}: 4h close={g.close_4h_atr.mean():+.3f} ATR | 24h={g.close_24h_atr.mean():+.3f} | 48h={g.close_48h_atr.mean():+.3f} | P(48h>0)={(g.close_48h_atr>0).mean():.1%} | MFE48={g.mfe_48h_atr.mean():.3f} | MAE48={g.mae_48h_atr.mean():.3f}")
lines+=['','## Trajectory classes']
for split in ['TRAIN','OOS']:
    g=ev[ev.split==split]
    parts=[]
    for c,n in g.trajectory_class.value_counts().items(): parts.append(f"{c} {n} ({n/len(g):.1%})")
    lines.append(f"- {split}: "+'; '.join(parts))
lines+=['','## Reaction diagnostics']
rd=pd.DataFrame(react)
for name in ['M5_BREAK3_1H','M15_STRUCT4_4H','FAV025_1H','RECLAIM_AFTER_ADV025','NO_FAV025_4H']:
    a=rd[(rd.split=='TRAIN')&(rd.reaction==name)]
    b=rd[(rd.split=='OOS')&(rd.reaction==name)]
    if len(a) and len(b):
        a=a.iloc[0]; b=b.iloc[0]
        lines.append(f"- {name}: TRAIN N={int(a.n)} 48h={a.mean_close_48h:+.3f} ATR P+={a.p48:.1%} | OOS N={int(b.n)} 48h={b.mean_close_48h:+.3f} ATR P+={b.p48:.1%}")
(OUT/'LAB110_REPORT.md').write_text('\n'.join(lines)+'\n')

meta=dict(
    signal='fresh |Z|>=1 crossing from below on 5m flow; side=-sign(Z)',
    anchor='price close at signal time',
    normalization='causal last-completed H1 ATR14',
    horizons_minutes=HORIZONS_MIN,
    z_bins=Z_LABELS,
    full_path_required='48h',
    trajectory_classes='frozen descriptive taxonomy; not optimized',
    caveat='2022 data coverage is sparse in available flow/price history; do not interpret yearly 2022 as complete-market validation'
)
(OUT/'LAB110_meta.json').write_text(json.dumps(meta,indent=2))
print('\n'.join(lines))
