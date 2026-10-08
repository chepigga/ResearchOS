#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab118_out"); OUT.mkdir(exist_ok=True)
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
            if not n.lower().endswith('.csv'):continue
            try:
                with z.open(n) as f:d=pd.read_csv(f)
                if len(d):fs.append(d)
            except:pass
        common=set(fs[0].columns)
        for d in fs[1:]:common &= set(d.columns)
        if len(fs)>1 and len(common)>=4:
            cols=list(common);return pd.concat([d[cols] for d in fs],ignore_index=True)
        return fs[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce');med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# flow
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time','timestamp']);rc=pick(f.columns,['count_long_short_ratio','ratio']);oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
f=f[[tc,rc,oic]].copy();f['time']=ptime(f[tc]);f['ratio']=pd.to_numeric(f[rc],errors='coerce');f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna(subset=['time','ratio','oi']).sort_values('time').drop_duplicates('time',keep='last')
f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean();sd=f.ratio.rolling(72,min_periods=72).std(ddof=0);f['z']=(f.ratio-mu)/sd.replace(0,np.nan)
f['oi_chg_4h']=f.oi/f.oi.shift(48)-1

# price
r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']);po=pick(r.columns,['open']);ph=pick(r.columns,['high']);pl=pick(r.columns,['low']);pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# H1
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean();h1['ema20']=h1.close.ewm(span=20,adjust=False).mean();h1['extension_atr']=(h1.close-h1.ema20)/h1.atr
h1['close_time']=h1.time+pd.Timedelta(hours=1)

# H4
h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean();h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
h4['close_time']=h4.time+pd.Timedelta(hours=4)
# trend age in H4 bars
age=[];last=0;prevv=0
for v in h4.trend:
    if v!=0 and v==prevv:last+=1
    elif v!=0:last=1
    else:last=0
    age.append(last);prevv=v
h4['trend_age']=age
# distance from H4 EMA normalized later by H1 ATR via asof
h4['ema_dist_raw']=h4.close-h4.ema50
# impulse age: bars since largest directional body >1 ATR(H4 proxy) in trend direction
h4tr=pd.concat([(h4.high-h4.low),(h4.high-h4.close.shift(1)).abs(),(h4.low-h4.close.shift(1)).abs()],axis=1).max(axis=1)
h4['atr14']=h4tr.rolling(14,min_periods=14).mean()
body=(h4.close-h4.open)
imp=((body.abs()/h4.atr14)>=1.0)&(np.sign(body)==h4.trend)
imp_age=[];cnt=999
for x in imp.fillna(False):
    cnt=0 if x else min(cnt+1,999);imp_age.append(cnt)
h4['impulse_age']=imp_age

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','extension_atr']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),h4[['close_time','trend','trend_age','ema_dist_raw','impulse_age']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
base=pd.merge_asof(base.sort_values('time'),f[['time','z','oi_chg_4h']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base['h4_ema_dist_atr']=base.ema_dist_raw/base.atr

fd=pd.read_csv(FUNDING)
ft=pick(fd.columns,['time','timestamp']);fc=pick(fd.columns,['funding','funding_rate'])
fd['time']=ptime(fd[ft]);fd['funding']=pd.to_numeric(fd[fc],errors='coerce')
fd=fd[['time','funding']].dropna().sort_values('time').drop_duplicates('time',keep='last')
base=pd.merge_asof(base.sort_values('time'),fd.sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta(hours=16))
base=base.dropna(subset=['atr','extension_atr','trend','trend_age','ema_dist_raw','impulse_age','z','oi_chg_4h','funding']).reset_index(drop=True)

# TRAIN-only thresholds
trm=base.time<TRAIN_END
oi70=float(base.loc[trm,'oi_chg_4h'].quantile(.70))
oi85=float(base.loc[trm,'oi_chg_4h'].quantile(.85))
ext80=float(base.loc[trm,'extension_atr'].abs().quantile(.80))
ext90=float(base.loc[trm,'extension_atr'].abs().quantile(.90))
fund_abs80=float(base.loc[trm,'funding'].abs().quantile(.80))
h4dist80=float(base.loc[trm,'h4_ema_dist_atr'].abs().quantile(.80))

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

rows=[]
last=len(base)-1-H*12
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1;h4t=int(base.trend.iloc[i]);ext=float(base.extension_atr.iloc[i]);atr=float(BA[i]);anchor=float(BC[i])
    if h4t==0 or h4t==side:continue
    extension_against=(side>0 and ext<0) or (side<0 and ext>0)
    if not extension_against:continue
    oi=float(base.oi_chg_4h.iloc[i]);fund=float(base.funding.iloc[i]);h4d=float(base.h4_ema_dist_atr.iloc[i])
    end=i+H*12;hi=float(BH[i+1:end+1].max());lo=float(BL[i+1:end+1].min())
    mfe=(hi-anchor)/atr if side>0 else (anchor-lo)/atr;mae=(anchor-lo)/atr if side>0 else (hi-anchor)/atr
    rr=dict(signal_time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',side='BUY' if side>0 else 'SELL',z=float(BZ[i]),abs_z=abs(float(BZ[i])),
            ext_abs=abs(ext),oi4h=oi,funding=fund,funding_abs=abs(fund),funding_crowd=((fund>0 and BZ[i]>0) or (fund<0 and BZ[i]<0)),
            h4_age=int(base.trend_age.iloc[i]),h4_dist_abs=abs(h4d),impulse_age=int(base.impulse_age.iloc[i]),mfe48=mfe,mae48=mae,close48=side*(float(BC[end])-anchor)/atr)
    for fav,adv in PAIR_TESTS: rr[f'fp_{fav:g}_{adv:g}']=first_pass(i,side,anchor,atr,fav,adv)
    rows.append(rr)
ev=pd.DataFrame(rows)
ev.to_csv(OUT/'LAB118_countertrend_universe.csv',index=False)

# Frozen LAB117 capitulation baseline
ev['cap_base']=(ev.ext_abs>=ext80)&(ev.oi4h>=oi70)
ev['cap_strong_ext']=(ev.ext_abs>=ext90)&(ev.oi4h>=oi70)
ev['cap_strong_oi']=(ev.ext_abs>=ext80)&(ev.oi4h>=oi85)
ev['cap_both_strong']=(ev.ext_abs>=ext90)&(ev.oi4h>=oi85)
ev['funding_extreme']=ev.funding_abs>=fund_abs80
ev['h4_far']=ev.h4_dist_abs>=h4dist80

# anatomy bins frozen from intuitive non-OOS cutpoints
ev['ext_bin']=pd.cut(ev.ext_abs,[0,1.5,2.0,2.5,3.0,np.inf],right=False,labels=['<1.5','1.5-2','2-2.5','2.5-3','3+'])
ev['oi_bin']=pd.cut(ev.oi4h,[-np.inf,oi70,oi85,np.inf],right=False,labels=['<q70','q70-q85','q85+'])
ev['z_bin']=pd.cut(ev.abs_z,[1,1.5,2,2.5,np.inf],right=False,labels=['1-1.5','1.5-2','2-2.5','2.5+'])
ev['age_bin']=pd.cut(ev.h4_age,[0,3,7,13,25,np.inf],right=False,labels=['1-2','3-6','7-12','13-24','25+'])
ev['impulse_bin']=pd.cut(ev.impulse_age,[-1,1,3,7,13,np.inf],right=False,labels=['0','1-2','3-6','7-12','13+'])

def met(g):
    d=dict(n=len(g),mfe=float(g.mfe48.mean()),mae=float(g.mae48.mean()),close=float(g.close48.mean()))
    for fav,adv in PAIR_TESTS:
        x=g[f'fp_{fav:g}_{adv:g}'];d[f'p_{fav:g}_{adv:g}']=float((x==1).mean())
    return d

segments={
'CAP_BASE':lambda q:q.cap_base,
'EXT90_OI70':lambda q:q.cap_strong_ext,
'EXT80_OI85':lambda q:q.cap_strong_oi,
'EXT90_OI85':lambda q:q.cap_both_strong,
'CAP_BASE_FUND_EXTREME':lambda q:q.cap_base&q.funding_extreme,
'CAP_BASE_FUND_CROWD':lambda q:q.cap_base&q.funding_crowd,
'CAP_BASE_H4_FAR':lambda q:q.cap_base&q.h4_far,
'CAP_BASE_AGE_7PLUS':lambda q:q.cap_base&(q.h4_age>=7),
'CAP_BASE_IMPULSE_RECENT':lambda q:q.cap_base&(q.impulse_age<=3),
}
seg=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for name,fn in segments.items():
        g=q[fn(q)]
        if len(g)>=15:seg.append(dict(split=split,segment=name,**met(g)))
seg=pd.DataFrame(seg);seg.to_csv(OUT/'LAB118_segments.csv',index=False)

# one-dimensional anatomy only inside CAP_BASE
grid=[]
for split in ['TRAIN','OOS']:
    q=ev[(ev.split==split)&ev.cap_base]
    for dim in ['ext_bin','oi_bin','z_bin','age_bin','impulse_bin','funding_crowd','funding_extreme','h4_far','side']:
        for group,g in q.groupby(dim,observed=True):
            if len(g)>=10:grid.append(dict(split=split,dimension=dim,group=str(group),**met(g)))
pd.DataFrame(grid).to_csv(OUT/'LAB118_anatomy_grid.csv',index=False)

# yearly baseline
yr=[]
for y,q in ev[ev.cap_base].groupby(ev.signal_time.dt.year):
    if len(q)>=10:yr.append(dict(year=int(y),**met(q)))
pd.DataFrame(yr).to_csv(OUT/'LAB118_yearly.csv',index=False)

lines=['# LAB118 — CAPITULATION REVERSAL ANATOMY','',
'Universe: fresh |Z|>=1 inverse-crowd signals where Z side is against causal H4 trend and price is extended in the reversal direction.',
f'LAB117 frozen CAP_BASE = extension >= TRAIN q80={ext80:.2f} H1 ATR and OI 4h change >= TRAIN q70={oi70:+.3%}.',
f'Additional TRAIN-frozen severity cuts: extension q90={ext90:.2f}; OI q85={oi85:+.3%}; |funding| q80={fund_abs80:.6f}; H4 EMA distance q80={h4dist80:.2f} H1 ATR.',
'No SL/TP optimization. We study +2/-0.5, +3/-1, +5/-1.5 first passage within 48h. Same-bar ambiguity is adverse-first.','']
for name in segments:
    lines.append(f'## {name}')
    for split in ['TRAIN','OOS']:
        a=seg[(seg.split==split)&(seg.segment==name)]
        if len(a):
            r=a.iloc[0]
            lines.append(f"- {split}: N={int(r.n)} MFE={r.mfe:.2f} MAE={r.mae:.2f} | +2/-0.5={r['p_2_0.5']:.1%} +3/-1={r['p_3_1']:.1%} +5/-1.5={r['p_5_1.5']:.1%}")
        else:lines.append(f"- {split}: insufficient N")
    lines.append('')
(OUT/'LAB118_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB118_meta.json').write_text(json.dumps(dict(
    base_capitulation=dict(ext_q80=ext80,oi_q70=oi70),
    stronger=dict(ext_q90=ext90,oi_q85=oi85,funding_abs_q80=fund_abs80,h4dist_q80=h4dist80),
    horizon_h=48,pair_tests=PAIR_TESTS,
    caveat='OOS repeatedly inspected; N is small in stronger subsegments; anatomy is hypothesis generation, not validation'
),indent=2))
print('\n'.join(lines))
