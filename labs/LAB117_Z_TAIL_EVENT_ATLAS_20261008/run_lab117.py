#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab117_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
FUNDING=Path("binance_btc_funding.csv")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
HORIZON_H=48
FAVS=[1.0,2.0,3.0,5.0]
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
            cols=list(common); return pd.concat([d[cols] for d in fs],ignore_index=True)
        return fs[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# flow
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time','timestamp'])
rc=pick(f.columns,['count_long_short_ratio','long_short_ratio','ratio'])
oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
if not all([tc,rc,oic]): raise RuntimeError(f'missing flow cols {f.columns.tolist()}')
f=f[[tc,rc,oic]].copy(); f['time']=ptime(f[tc]); f['ratio']=pd.to_numeric(f[rc],errors='coerce'); f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna(subset=['time','ratio','oi']).sort_values('time').drop_duplicates('time',keep='last')
f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean(); sd=f.ratio.rolling(72,min_periods=72).std(ddof=0)
f['z']=(f.ratio-mu)/sd.replace(0,np.nan)
f['oi_chg_1h']=f.oi/f.oi.shift(12)-1
f['oi_chg_4h']=f.oi/f.oi.shift(48)-1

# price
r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']);po=pick(r.columns,['open']);ph=pick(r.columns,['high']);pl=pick(r.columns,['low']);pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# H1 ATR, compression
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prev=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean()
h1['atr_med24']=h1.atr.rolling(24,min_periods=12).median()
h1['compression']=h1.atr/h1.atr_med24
h1['ema20']=h1.close.ewm(span=20,adjust=False).mean()
h1['extension_atr']=(h1.close-h1.ema20)/h1.atr
h1['close_time']=h1.time+pd.Timedelta(hours=1)

# H4 and D1 trends
h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean(); h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend_h4']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
h4['close_time']=h4.time+pd.Timedelta(hours=4)
d1=p.set_index('time').resample('1D',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
d1['ema50']=d1.close.ewm(span=50,adjust=False).mean(); d1['ema50_lag10']=d1.ema50.shift(10)
d1['trend_d1']=np.where((d1.close>d1.ema50)&(d1.ema50>d1.ema50_lag10),1,np.where((d1.close<d1.ema50)&(d1.ema50<d1.ema50_lag10),-1,0))
d1['close_time']=d1.time+pd.Timedelta(days=1)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','compression','extension_atr']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),h4[['close_time','trend_h4']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
base=pd.merge_asof(base.sort_values('time'),d1[['close_time','trend_d1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_d1'))
base=pd.merge_asof(base.sort_values('time'),f[['time','z','oi_chg_1h','oi_chg_4h']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))

# funding
fd=pd.read_csv(FUNDING)
ft=pick(fd.columns,['time','timestamp']);fc=pick(fd.columns,['funding','funding_rate'])
fd['time']=ptime(fd[ft]);fd['funding']=pd.to_numeric(fd[fc],errors='coerce')
fd=fd[['time','funding']].dropna().sort_values('time').drop_duplicates('time',keep='last')
base=pd.merge_asof(base.sort_values('time'),fd.sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta(hours=16))
base=base.dropna(subset=['atr','compression','extension_atr','trend_h4','trend_d1','z','oi_chg_1h','oi_chg_4h','funding']).reset_index(drop=True)

# TRAIN thresholds only
trm=base.time<TRAIN_END
oi_q70=float(base.loc[trm,'oi_chg_4h'].quantile(.70))
oi_q30=float(base.loc[trm,'oi_chg_4h'].quantile(.30))
comp_q30=float(base.loc[trm,'compression'].quantile(.30))
ext_q80=float(base.loc[trm,'extension_atr'].abs().quantile(.80))

BT=base.time.reset_index(drop=True);BH=base.high.to_numpy(float);BL=base.low.to_numpy(float);BC=base.close.to_numpy(float);BA=base.atr.to_numpy(float);BZ=base.z.to_numpy(float)

def first_pass(i,side,anchor,atr,fav,adv):
    end=min(i+HORIZON_H*12,len(base)-1)
    for j in range(i+1,end+1):
        fav_hit=((BH[j]-anchor)>=fav*atr) if side>0 else ((anchor-BL[j])>=fav*atr)
        adv_hit=((anchor-BL[j])>=adv*atr) if side>0 else ((BH[j]-anchor)>=adv*atr)
        if fav_hit and adv_hit:return 0 # conservative adverse-first
        if fav_hit:return 1
        if adv_hit:return -1
    return 0

events=[]
last=len(base)-1-HORIZON_H*12
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1; atr=float(BA[i]); anchor=float(BC[i])
    if atr<=0 or not np.isfinite(atr): continue
    h4=int(base.trend_h4.iloc[i]);d1v=int(base.trend_d1.iloc[i]);ext=float(base.extension_atr.iloc[i])
    h4_with=(h4==side); d1_with=(d1v==side)
    zbin=('1-1.5' if abs(BZ[i])<1.5 else ('1.5-2' if abs(BZ[i])<2 else ('2-2.5' if abs(BZ[i])<2.5 else '2.5+')))
    comp=bool(base.compression.iloc[i]<=comp_q30)
    oi_build=bool(base.oi_chg_4h.iloc[i]>=oi_q70)
    oi_flush=bool(base.oi_chg_4h.iloc[i]<=oi_q30)
    funding=float(base.funding.iloc[i])
    funding_with_crowd=(funding>0 and BZ[i]>0) or (funding<0 and BZ[i]<0)
    extension_against_signal=(side>0 and ext<-ext_q80) or (side<0 and ext>ext_q80)
    # two worlds
    trend_squeeze=(h4_with and d1_with and oi_build)
    capitulation=(not h4_with and extension_against_signal and oi_build)
    row=dict(signal_time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',year=int(BT.iloc[i].year),
             side='BUY' if side>0 else 'SELL',side_num=side,z=float(BZ[i]),zbin=zbin,
             h4_with=h4_with,d1_with=d1_with,compression=comp,oi_build=oi_build,oi_flush=oi_flush,
             funding_with_crowd=funding_with_crowd,extension_against_signal=extension_against_signal,
             trend_squeeze=trend_squeeze,capitulation=capitulation)
    end=i+HORIZON_H*12
    hi=float(BH[i+1:end+1].max());lo=float(BL[i+1:end+1].min())
    row['mfe48']=(hi-anchor)/atr if side>0 else (anchor-lo)/atr
    row['mae48']=(anchor-lo)/atr if side>0 else (hi-anchor)/atr
    row['close48']=side*(float(BC[end])-anchor)/atr
    for fav in FAVS: row[f'hit_mfe_{fav:g}']=int(row['mfe48']>=fav)
    for fav,adv in PAIR_TESTS: row[f'fav{fav:g}_before_adv{adv:g}']=first_pass(i,side,anchor,atr,fav,adv)
    events.append(row)
ev=pd.DataFrame(events);ev.to_csv(OUT/'LAB117_event_atlas.csv',index=False)

def stats(g):
    d=dict(n=len(g),mean_mfe=float(g.mfe48.mean()),median_mfe=float(g.mfe48.median()),mean_mae=float(g.mae48.mean()),
           mean_close=float(g.close48.mean()),p_close_pos=float((g.close48>0).mean()))
    for fav in FAVS:d[f'p_mfe_{fav:g}']=float((g.mfe48>=fav).mean())
    for fav,adv in PAIR_TESTS:
        x=g[f'fav{fav:g}_before_adv{adv:g}']
        d[f'p_fav{fav:g}_before_adv{adv:g}']=float((x==1).mean())
        d[f'p_adv{adv:g}_before_fav{fav:g}']=float((x==-1).mean())
    return d

segments={
'ALL':lambda q:pd.Series(True,index=q.index),
'H4_WITH':lambda q:q.h4_with,
'H4_AGAINST':lambda q:~q.h4_with,
'H4_D1_WITH':lambda q:q.h4_with&q.d1_with,
'H4_D1_AGAINST':lambda q:(~q.h4_with)&(~q.d1_with),
'COMPRESSION':lambda q:q.compression,
'OI_BUILD':lambda q:q.oi_build,
'TREND_SQUEEZE':lambda q:q.trend_squeeze,
'TREND_SQUEEZE_COMP':lambda q:q.trend_squeeze&q.compression,
'CAPITULATION':lambda q:q.capitulation,
'CAPITULATION_CROWD_FUNDING':lambda q:q.capitulation&q.funding_with_crowd,
'EXTREME_Z_2PLUS':lambda q:q.z.abs()>=2,
}
rows=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for name,fn in segments.items():
        g=q[fn(q)]
        if len(g)>=30: rows.append(dict(split=split,segment=name,**stats(g)))
seg=pd.DataFrame(rows);seg.to_csv(OUT/'LAB117_segments.csv',index=False)

# z-bins + side + trend relation
grid=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for (zb,hw),g in q.groupby(['zbin','h4_with']):
        if len(g)>=30:grid.append(dict(split=split,zbin=zb,h4_with=bool(hw),**stats(g)))
pd.DataFrame(grid).to_csv(OUT/'LAB117_zbin_h4grid.csv',index=False)

# yearly key worlds
yr=[]
for y,q in ev.groupby('year'):
    for name in ['ALL','TREND_SQUEEZE','CAPITULATION']:
        g=q[segments[name](q)]
        if len(g)>=20:yr.append(dict(year=int(y),segment=name,**stats(g)))
pd.DataFrame(yr).to_csv(OUT/'LAB117_yearly.csv',index=False)

lines=['# LAB117 — Z TAIL EVENT ATLAS','',
'Goal: locate large-move tails, not optimize average Z expectancy.',
'Signal is frozen fresh |Z|>=1 inverse-crowd. Horizon 48h. All path tests are causal and use H1 ATR known at signal.',
f'TRAIN-only context thresholds: 4h OI build >= {oi_q70:+.3%}; OI flush <= {oi_q30:+.3%}; compression <= {comp_q30:.3f} ATR/24h-median; extension extreme |EMA20 distance| >= {ext_q80:.2f} ATR.',
'TREND_SQUEEZE = Z direction aligned with both H4 and D1 trends + OI build.',
'CAPITULATION = Z direction against H4 trend + price extremely extended in Z direction-opposite trend + OI build.',
'First-passage metrics are conservative: if favorable and adverse thresholds occur in same M5 bar, adverse wins.','']
for name in ['ALL','H4_WITH','H4_AGAINST','H4_D1_WITH','TREND_SQUEEZE','TREND_SQUEEZE_COMP','CAPITULATION']:
    lines.append(f'## {name}')
    for split in ['TRAIN','OOS']:
        a=seg[(seg.split==split)&(seg.segment==name)]
        if len(a):
            r=a.iloc[0]
            lines.append(f"- {split}: N={int(r.n)} MFE={r.mean_mfe:.2f} MAE={r.mean_mae:.2f} | P(MFE>=2)={r['p_mfe_2']:.1%} P>=3={r['p_mfe_3']:.1%} P>=5={r['p_mfe_5']:.1%} | +2 before -0.5={r['p_fav2_before_adv0.5']:.1%} | +3 before -1={r['p_fav3_before_adv1']:.1%} | +5 before -1.5={r['p_fav5_before_adv1.5']:.1%}")
        else: lines.append(f"- {split}: insufficient N")
    lines.append('')
(OUT/'LAB117_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB117_meta.json').write_text(json.dumps(dict(signal='fresh |Z|>=1 inverse crowd',horizon_h=48,tail_levels=FAVS,pair_tests=PAIR_TESTS,
    trend_squeeze='H4&D1 aligned with Z side + OI build',
    capitulation='H4 against Z side + extreme price extension + OI build',
    caveat='development OOS repeatedly inspected; segment definitions exploratory; not a production strategy'),indent=2))
print('\n'.join(lines))
