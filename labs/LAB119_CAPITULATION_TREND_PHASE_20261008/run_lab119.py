#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab119_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
FUNDING=Path("binance_btc_funding.csv")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
H=48
PAIR_TESTS=[(2.0,0.5),(3.0,1.0),(5.0,1.5)]

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
        fs=[]
        for n in z.namelist():
            if not n.lower().endswith('.csv'): continue
            try:
                with z.open(n) as f:d=pd.read_csv(f)
                if len(d):fs.append(d)
            except: pass
        if not fs: raise RuntimeError(f'no csv in {zp}')
        common=set(fs[0].columns)
        for d in fs[1:]: common &= set(d.columns)
        if len(fs)>1 and len(common)>=4:
            cols=list(common);return pd.concat([d[cols] for d in fs],ignore_index=True)
        return fs[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce');med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# Flow / Z / OI
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time','timestamp']); rc=pick(f.columns,['count_long_short_ratio','ratio']); oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
f=f[[tc,rc,oic]].copy(); f['time']=ptime(f[tc]); f['ratio']=pd.to_numeric(f[rc],errors='coerce'); f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna(subset=['time','ratio','oi']).sort_values('time').drop_duplicates('time',keep='last')
f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean(); sd=f.ratio.rolling(72,min_periods=72).std(ddof=0)
f['z']=(f.ratio-mu)/sd.replace(0,np.nan)
f['oi_chg_4h']=f.oi/f.oi.shift(48)-1.0

# Price
r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']); po=pick(r.columns,['open']); ph=pick(r.columns,['high']); pl=pick(r.columns,['low']); pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy(); p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]: p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# H1 ATR + extension
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prev=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean()
h1['ema20']=h1.close.ewm(span=20,adjust=False).mean()
h1['extension_atr']=(h1.close-h1.ema20)/h1.atr
h1['close_time']=h1.time+pd.Timedelta(hours=1)

# H4 trend state
h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean()
h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
h4['ema_slope6']=(h4.ema50-h4.ema50_lag6)

# H4 ATR / impulse
h4prev=h4.close.shift(1)
h4tr=pd.concat([(h4.high-h4.low),(h4.high-h4prev).abs(),(h4.low-h4prev).abs()],axis=1).max(axis=1)
h4['atr14']=h4tr.rolling(14,min_periods=14).mean()
h4['body_atr']=(h4.close-h4.open)/h4.atr14

# trend age
age=[];cur=0;pv=0
for v in h4.trend:
    if v!=0 and v==pv: cur+=1
    elif v!=0: cur=1
    else: cur=0
    age.append(cur);pv=v
h4['trend_age']=age

# bars since directional impulse >=0.8 H4 ATR in trend direction
imp=((h4.body_atr.abs()>=0.8)&(np.sign(h4.body_atr)==h4.trend))
imp_age=[];cnt=999
for x in imp.fillna(False):
    cnt=0 if x else min(cnt+1,999);imp_age.append(cnt)
h4['impulse_age']=imp_age

# slope deceleration: absolute EMA slope now vs 3 H4 bars ago
h4['slope_abs']=h4.ema_slope6.abs()/h4.atr14
h4['slope_abs_lag3']=h4.slope_abs.shift(3)
h4['decelerating']=h4.slope_abs < h4.slope_abs_lag3
h4['close_time']=h4.time+pd.Timedelta(hours=4)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','extension_atr']].dropna().sort_values('close_time'),
                   left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),h4[['close_time','trend','trend_age','impulse_age','slope_abs','decelerating']].dropna().sort_values('close_time'),
                   left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
base=pd.merge_asof(base.sort_values('time'),f[['time','z','oi_chg_4h']].dropna().sort_values('time'),
                   on='time',direction='backward',tolerance=pd.Timedelta('5min'))

fd=pd.read_csv(FUNDING)
ft=pick(fd.columns,['time','timestamp']);fc=pick(fd.columns,['funding','funding_rate'])
fd['time']=ptime(fd[ft]);fd['funding']=pd.to_numeric(fd[fc],errors='coerce')
fd=fd[['time','funding']].dropna().sort_values('time').drop_duplicates('time',keep='last')
base=pd.merge_asof(base.sort_values('time'),fd,on='time',direction='backward',tolerance=pd.Timedelta(hours=16))
base=base.dropna(subset=['atr','extension_atr','trend','trend_age','impulse_age','slope_abs','z','oi_chg_4h','funding']).reset_index(drop=True)

# Freeze LAB118 base thresholds on TRAIN
trm=base.time<TRAIN_END
ext80=float(base.loc[trm,'extension_atr'].abs().quantile(.80))
oi70=float(base.loc[trm,'oi_chg_4h'].quantile(.70))

BT=base.time.reset_index(drop=True);BH=base.high.to_numpy(float);BL=base.low.to_numpy(float);BC=base.close.to_numpy(float);BA=base.atr.to_numpy(float);BZ=base.z.to_numpy(float)

def first_pass(i,side,anchor,atr,fav,adv):
    end=i+H*12
    for j in range(i+1,end+1):
        fh=((BH[j]-anchor)>=fav*atr) if side>0 else ((anchor-BL[j])>=fav*atr)
        ah=((anchor-BL[j])>=adv*atr) if side>0 else ((BH[j]-anchor)>=adv*atr)
        if fh and ah:return 0
        if fh:return 1
        if ah:return -1
    return 0

def phase(age,imp_age,decel):
    # Mutually exclusive, causal, pre-registered from trend lifecycle intuition.
    if age<=3:
        return 'BIRTH_1_3'
    if imp_age<=2:
        return 'REACCEL_IMPULSE'
    if age<=12:
        return 'CONTINUATION_4_12'
    if age<=24 and not decel:
        return 'MATURE_13_24'
    if age<=24 and decel:
        return 'MATURE_DECEL_13_24'
    if age>=25 and not decel:
        return 'LATE_25PLUS'
    return 'LATE_DECEL_25PLUS'

rows=[]
last=len(base)-1-H*12
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1
    h4t=int(base.trend.iloc[i]); ext=float(base.extension_atr.iloc[i]); oi=float(base.oi_chg_4h.iloc[i])
    if h4t==0 or h4t==side:continue
    # LAB118 CAP_BASE: extended against H4 trend in Z-reversal direction + OI build
    ext_against=(side>0 and ext<0) or (side<0 and ext>0)
    if not ext_against or abs(ext)<ext80 or oi<oi70:continue
    atr=float(BA[i]);anchor=float(BC[i]);age=int(base.trend_age.iloc[i]);ia=int(base.impulse_age.iloc[i]);decel=bool(base.decelerating.iloc[i])
    phs=phase(age,ia,decel)
    end=i+H*12;hi=float(BH[i+1:end+1].max());lo=float(BL[i+1:end+1].min())
    mfe=(hi-anchor)/atr if side>0 else (anchor-lo)/atr
    mae=(anchor-lo)/atr if side>0 else (hi-anchor)/atr
    fund=float(base.funding.iloc[i])
    row=dict(signal_time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',year=int(BT.iloc[i].year),
             side='BUY' if side>0 else 'SELL',phase=phs,h4_age=age,impulse_age=ia,decelerating=decel,
             abs_z=abs(float(BZ[i])),ext_abs=abs(ext),oi4h=oi,funding=fund,
             funding_crowd=((fund>0 and BZ[i]>0) or (fund<0 and BZ[i]<0)),
             mfe48=mfe,mae48=mae,close48=side*(float(BC[end])-anchor)/atr)
    for fav,adv in PAIR_TESTS:row[f'fp_{fav:g}_{adv:g}']=first_pass(i,side,anchor,atr,fav,adv)
    rows.append(row)
ev=pd.DataFrame(rows)
ev.to_csv(OUT/'LAB119_events.csv',index=False)

def met(g):
    d=dict(n=len(g),mean_mfe=float(g.mfe48.mean()),mean_mae=float(g.mae48.mean()),mean_close=float(g.close48.mean()))
    for fav,adv in PAIR_TESTS:
        x=g[f'fp_{fav:g}_{adv:g}']
        d[f'p_{fav:g}_{adv:g}']=float((x==1).mean())
    return d

summary=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    # overall
    if len(q):summary.append(dict(split=split,dimension='ALL',group='ALL',**met(q)))
    for dim in ['phase','side','decelerating','funding_crowd']:
        for group,g in q.groupby(dim,observed=True):
            if len(g)>=8:summary.append(dict(split=split,dimension=dim,group=str(group),**met(g)))
    for (phs,side),g in q.groupby(['phase','side'],observed=True):
        if len(g)>=6:summary.append(dict(split=split,dimension='phase_x_side',group=f'{phs}|{side}',**met(g)))
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB119_phase_summary.csv',index=False)

# yearly phase stability
yr=[]
for y,q in ev.groupby('year'):
    for phs,g in q.groupby('phase'):
        if len(g)>=8:yr.append(dict(year=int(y),phase=phs,**met(g)))
pd.DataFrame(yr).to_csv(OUT/'LAB119_yearly_phase.csv',index=False)

# chronological OOS half split as an extra stress check
oos=ev[ev.split=='OOS'].sort_values('signal_time').copy()
if len(oos):
    cut=oos.signal_time.quantile(.5)
    oos['oos_half']=np.where(oos.signal_time<=cut,'OOS_EARLY','OOS_LATE')
    hh=[]
    for half,q in oos.groupby('oos_half'):
        for phs,g in q.groupby('phase'):
            if len(g)>=5:hh.append(dict(oos_half=half,phase=phs,**met(g)))
    pd.DataFrame(hh).to_csv(OUT/'LAB119_oos_half.csv',index=False)
else:
    cut=None

lines=['# LAB119 — CAPITULATION × TREND PHASE','',
       f'Frozen LAB118 CAP_BASE: fresh |Z|>=1 inverse crowd, against H4 trend, extension >= {ext80:.2f} H1 ATR, OI4h >= {oi70:+.3%}.',
       'No new severity optimization. Trend phase is causal and mutually exclusive:',
       'BIRTH_1_3 = H4 trend age 1-3 bars; REACCEL_IMPULSE = older trend but directional H4 impulse within last 2 bars; CONTINUATION_4_12 = age 4-12 without recent impulse; MATURE_13_24 and LATE_25PLUS are split by EMA-slope deceleration.',
       'Primary geometry remains +3 ATR before -1 ATR within 48h; +2/-0.5 and +5/-1.5 are secondary. Same-bar ambiguity is adverse-first.',
       'OOS is development OOS and has been repeatedly inspected; small cells are hypothesis generation only.','']

for phs in ['BIRTH_1_3','REACCEL_IMPULSE','CONTINUATION_4_12','MATURE_13_24','MATURE_DECEL_13_24','LATE_25PLUS','LATE_DECEL_25PLUS']:
    lines.append(f'## {phs}')
    for split in ['TRAIN','OOS']:
        a=sm[(sm.split==split)&(sm.dimension=='phase')&(sm.group==phs)]
        if len(a):
            r=a.iloc[0]
            lines.append(f"- {split}: N={int(r.n)} MFE={r.mean_mfe:.2f} MAE={r.mean_mae:.2f} | +2/-0.5={r['p_2_0.5']:.1%} +3/-1={r['p_3_1']:.1%} +5/-1.5={r['p_5_1.5']:.1%}")
        else:
            lines.append(f"- {split}: insufficient N")
    lines.append('')

lines.append('## BUY vs SELL')
for side in ['BUY','SELL']:
    for split in ['TRAIN','OOS']:
        a=sm[(sm.split==split)&(sm.dimension=='side')&(sm.group==side)]
        if len(a):
            r=a.iloc[0]
            lines.append(f"- {split} {side}: N={int(r.n)} +3/-1={r['p_3_1']:.1%} +5/-1.5={r['p_5_1.5']:.1%} MFE={r.mean_mfe:.2f} MAE={r.mean_mae:.2f}")

(OUT/'LAB119_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB119_meta.json').write_text(json.dumps(dict(
    cap_base=dict(ext80=ext80,oi70=oi70),
    phases=['BIRTH_1_3','REACCEL_IMPULSE','CONTINUATION_4_12','MATURE_13_24','MATURE_DECEL_13_24','LATE_25PLUS','LATE_DECEL_25PLUS'],
    primary='+3 ATR before -1 ATR within 48h',
    oos_half_cut=str(cut) if cut is not None else None,
    caveat='development OOS repeatedly inspected; small phase cells are not validation'
),indent=2))
print('\n'.join(lines))
