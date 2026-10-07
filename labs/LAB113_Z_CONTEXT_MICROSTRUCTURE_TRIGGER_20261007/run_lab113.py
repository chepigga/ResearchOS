#!/usr/bin/env python3
from __future__ import annotations
import math,re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab113_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
SEARCH_H=6
HORIZONS=[15,60,240,720,1440]
HL={15:'15m',60:'1h',240:'4h',720:'12h',1440:'24h'}

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
            except:pass
        if not frames:raise RuntimeError(f'no csv in {zp}')
        common=set(frames[0].columns)
        for d in frames[1:]: common &= set(d.columns)
        if len(frames)>1 and len(common)>=4:
            cols=list(common);return pd.concat([d[cols] for d in frames],ignore_index=True)
        return frames[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce');med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# ---------- data ----------
flow=load_zip(FLOW_ZIP)
tc=pick(flow.columns,['create_time','time','timestamp'])
rc=pick(flow.columns,['count_long_short_ratio','long_short_ratio','ratio'])
oic=pick(flow.columns,['sum_open_interest_value','sum_open_interest'])
tkc=pick(flow.columns,['sum_taker_long_short_vol_ratio','taker_ratio'])
if not all([tc,rc,oic,tkc]): raise RuntimeError(f'missing flow cols {flow.columns.tolist()}')
flow=flow[[tc,rc,oic,tkc]].copy()
flow['time']=ptime(flow[tc]);flow['ratio']=pd.to_numeric(flow[rc],errors='coerce');flow['oi']=pd.to_numeric(flow[oic],errors='coerce');flow['taker']=pd.to_numeric(flow[tkc],errors='coerce')
flow=flow.dropna(subset=['time','ratio','oi','taker']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[(flow.ratio>0)&(flow.taker>0)].set_index('time').resample('5min').last().dropna().reset_index()

mu=flow.ratio.rolling(72,min_periods=72).mean();sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)
flow['oi_chg_1h']=flow.oi/flow.oi.shift(12)-1.0
flow['oi_chg_15m']=flow.oi/flow.oi.shift(3)-1.0
flow['log_taker']=np.log(flow.taker.replace(0,np.nan))
tm=flow.log_taker.rolling(72,min_periods=72).mean();ts=flow.log_taker.rolling(72,min_periods=72).std(ddof=0)
flow['taker_z']=(flow.log_taker-tm)/ts.replace(0,np.nan)

raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','datetime','open_time']);po=pick(raw.columns,['open']);ph=pick(raw.columns,['high']);pl=pick(raw.columns,['low']);pc=pick(raw.columns,['close']);pv=pick(raw.columns,['volume'])
cols=[pt,po,ph,pl,pc]+([pv] if pv else [])
p=raw[cols].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
if pv:p['volume']=pd.to_numeric(p[pv],errors='coerce')
else:p['volume']=1.0
p=p[['time','open','high','low','close','volume']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum')).dropna().reset_index()
p['vol_1h']=p.volume.rolling(12,min_periods=12).sum()
vm=p.vol_1h.rolling(288,min_periods=288).mean();vs=p.vol_1h.rolling(288,min_periods=288).std(ddof=0)
p['vol_z_1h']=(p.vol_1h-vm)/vs.replace(0,np.nan)

# H1 ATR
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr_h1']=tr.rolling(14,min_periods=14).mean();h1['close_time']=h1.time+pd.Timedelta(hours=1)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),flow[['time','z','oi','oi_chg_1h','oi_chg_15m','taker','taker_z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['z','oi_chg_1h','oi_chg_15m','taker','taker_z','atr_h1','vol_z_1h']).reset_index(drop=True)

# TRAIN-only thresholds
trm=base.time<TRAIN_END
q_oi_flush=float(base.loc[trm,'oi_chg_1h'].quantile(0.10))
q_oi_build=float(base.loc[trm,'oi_chg_1h'].quantile(0.90))
q_vol_spike=float(base.loc[trm,'vol_z_1h'].quantile(0.90))
# Taker trigger uses fixed causal z threshold 0.5 and sign aligned to Z-bias.
TAKER_Z=0.5

BT=base.time.reset_index(drop=True);BO=base.open.to_numpy(float);BH=base.high.to_numpy(float);BL=base.low.to_numpy(float);BC=base.close.to_numpy(float);BA=base.atr_h1.to_numpy(float);BZ=base.z.to_numpy(float)

def taker_aligned(i,side):
    tz=float(base.taker_z.iloc[i])
    return tz>=TAKER_Z if side>0 else tz<=-TAKER_Z
def taker_opposite(i,side):
    tz=float(base.taker_z.iloc[i])
    return tz<=-TAKER_Z if side>0 else tz>=TAKER_Z

def trigger_index(i,side,name):
    end=min(i+SEARCH_H*12,len(base)-1)
    if name=='TAKER_REVERSAL':
        for j in range(i+1,end+1):
            if taker_aligned(j,side) and taker_opposite(j-1,side): return j
    elif name=='OI_FLUSH':
        for j in range(i+1,end+1):
            if float(base.oi_chg_1h.iloc[j])<=q_oi_flush:return j
    elif name=='OI_BUILD':
        for j in range(i+1,end+1):
            if float(base.oi_chg_1h.iloc[j])>=q_oi_build:return j
    elif name=='VOLUME_SPIKE':
        for j in range(i+1,end+1):
            if float(base.vol_z_1h.iloc[j])>=q_vol_spike:return j
    elif name=='OI_FLUSH_TAKER':
        for j in range(i+1,end+1):
            if float(base.oi_chg_1h.iloc[j])<=q_oi_flush:
                lo=max(i+1,j-3);hi=min(end,j+3)
                for k in range(lo,hi+1):
                    if taker_aligned(k,side): return max(j,k)
    elif name=='OI_BUILD_TAKER':
        for j in range(i+1,end+1):
            if float(base.oi_chg_1h.iloc[j])>=q_oi_build:
                lo=max(i+1,j-3);hi=min(end,j+3)
                for k in range(lo,hi+1):
                    if taker_aligned(k,side): return max(j,k)
    elif name=='FLUSH_TAKER_VOLUME':
        for j in range(i+1,end+1):
            if float(base.oi_chg_1h.iloc[j])<=q_oi_flush and float(base.vol_z_1h.iloc[j])>=q_vol_spike:
                lo=max(i+1,j-3);hi=min(end,j+3)
                for k in range(lo,hi+1):
                    if taker_aligned(k,side): return max(j,k)
    return None

def fwd(j,side,entry,atr,mins):
    end=min(j+mins//5,len(base)-1)
    hi=float(np.max(BH[j:end+1]));lo=float(np.min(BL[j:end+1]));cl=float(BC[end])
    mfe=(hi-entry)/atr if side>0 else (entry-lo)/atr
    mae=(entry-lo)/atr if side>0 else (hi-entry)/atr
    close=side*(cl-entry)/atr
    return mfe,mae,close

TRIGGERS=['TAKER_REVERSAL','OI_FLUSH','OI_BUILD','VOLUME_SPIKE','OI_FLUSH_TAKER','OI_BUILD_TAKER','FLUSH_TAKER_VOLUME']
events=[]
last_i=len(base)-1-max(HORIZONS)//5-1
for i in range(1,last_i):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1;split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS'
    anchor=float(BC[i]);atr=float(BA[i])
    if not np.isfinite(atr) or atr<=0:continue
    for name in TRIGGERS:
        j=trigger_index(i,side,name)
        if j is None or j>=len(base)-1:continue
        ei=j+1;entry=float(BO[ei])
        row=dict(signal_time=BT.iloc[i],trigger_time=BT.iloc[j],entry_time=BT.iloc[ei],split=split,year=int(BT.iloc[i].year),
                 trigger=name,side='BUY' if side>0 else 'SELL',z=float(BZ[i]),abs_z=abs(float(BZ[i])),
                 delay_h=(BT.iloc[j]-BT.iloc[i]).total_seconds()/3600.0,
                 oi_chg_1h=float(base.oi_chg_1h.iloc[j]),oi_chg_15m=float(base.oi_chg_15m.iloc[j]),
                 taker_z=float(base.taker_z.iloc[j]),vol_z_1h=float(base.vol_z_1h.iloc[j]),
                 entry_vs_signal_atr=side*(entry-anchor)/atr)
        for mins in HORIZONS:
            mfe,mae,close=fwd(ei,side,entry,atr,mins)
            lab=HL[mins];row[f'mfe_{lab}']=mfe;row[f'mae_{lab}']=mae;row[f'close_{lab}']=close
        events.append(row)
ev=pd.DataFrame(events);ev.to_csv(OUT/'LAB113_trigger_events.csv',index=False)

# signal counts + trigger conversion
sig=[]
for i in range(1,last_i):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1;split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS'
    for name in TRIGGERS:
        j=trigger_index(i,side,name)
        sig.append(dict(signal_time=BT.iloc[i],split=split,trigger=name,hit=j is not None,delay_h=((BT.iloc[j]-BT.iloc[i]).total_seconds()/3600.0 if j is not None else np.nan)))
sig=pd.DataFrame(sig)

def met(g,lab):
    x=g[f'close_{lab}'].to_numpy(float);mfe=g[f'mfe_{lab}'].to_numpy(float);mae=g[f'mae_{lab}'].to_numpy(float)
    mean=float(np.mean(x));sd=float(np.std(x,ddof=1)) if len(x)>1 else np.nan
    noise=float(np.mean((mfe+mae)/2))
    ratio=float(np.mean(mfe/(mae+1e-9)))
    return dict(n=len(g),mean_close=mean,median_close=float(np.median(x)),p_positive=float(np.mean(x>0)),
                mean_mfe=float(np.mean(mfe)),mean_mae=float(np.mean(mae)),mfe_mae_ratio=ratio,
                dnr_std=(mean/sd if sd>0 else np.nan),dnr_range=(mean/noise if noise>0 else np.nan))

rows=[];conv=[]
for split in ['TRAIN','OOS']:
    s=sig[sig.split==split];ns=s.signal_time.nunique()
    for name in TRIGGERS:
        sg=s[s.trigger==name]
        conv.append(dict(split=split,trigger=name,n_signals=ns,trigger_count=int(sg.hit.sum()),trigger_rate=float(sg.hit.mean()),
                         median_delay_h=float(sg.loc[sg.hit,'delay_h'].median()) if sg.hit.any() else np.nan))
        g=ev[(ev.split==split)&(ev.trigger==name)]
        if not len(g):continue
        for lab in HL.values():
            rows.append(dict(split=split,trigger=name,horizon=lab,**met(g,lab)))
pd.DataFrame(conv).to_csv(OUT/'LAB113_conversion.csv',index=False)
atlas=pd.DataFrame(rows);atlas.to_csv(OUT/'LAB113_atlas.csv',index=False)

# year-by-year 24h for robustness
yr=[]
for split in ['TRAIN','OOS']:
    for name in TRIGGERS:
        g=ev[(ev.split==split)&(ev.trigger==name)]
        for y,z in g.groupby('year'):
            if len(z)<20:continue
            m=met(z,'24h')
            yr.append(dict(split=split,trigger=name,year=int(y),**m))
pd.DataFrame(yr).to_csv(OUT/'LAB113_yearly_24h.csv',index=False)

# rank by TRAIN 24h DNR, show OOS but do not select/promote
top=[]
tr=atlas[(atlas.split=='TRAIN')&(atlas.horizon=='24h')&(atlas.n>=200)].sort_values('dnr_std',ascending=False)
for _,r in tr.iterrows():
    o=atlas[(atlas.split=='OOS')&(atlas.trigger==r.trigger)&(atlas.horizon=='24h')]
    if len(o):
        o=o.iloc[0]
        top.append(dict(trigger=r.trigger,train_n=int(r.n),train_mean=r.mean_close,train_dnr=r.dnr_std,train_mfe_mae=r.mfe_mae_ratio,
                        oos_n=int(o.n),oos_mean=o.mean_close,oos_dnr=o.dnr_std,oos_mfe_mae=o.mfe_mae_ratio))
pd.DataFrame(top).to_csv(OUT/'LAB113_train_rank_with_oos.csv',index=False)

lines=['# LAB113 — Z CONTEXT × MICROSTRUCTURE TRIGGER','',
'Context: fresh |Z|>=1 inverse crowd. Search next 6h for a causal microstructure event; hypothetical entry is next 5m open.',
f'OI flush/build thresholds are TRAIN-only 1h OI-change 10th/90th percentiles: {q_oi_flush:+.4%} / {q_oi_build:+.4%}.',
f'Volume spike threshold is TRAIN-only 90th percentile of rolling 1h volume z: {q_vol_spike:+.3f}. Taker reversal uses fixed rolling taker-z threshold ±{TAKER_Z:.1f}.',
'DNR(std)=mean directional close displacement / std of directional close displacement. No SL/TP optimization in this LAB.','']
cv=pd.DataFrame(conv)
for name in TRIGGERS:
    lines.append(f'## {name}')
    for split in ['TRAIN','OOS']:
        c=cv[(cv.split==split)&(cv.trigger==name)].iloc[0]
        a=atlas[(atlas.split==split)&(atlas.trigger==name)&(atlas.horizon=='24h')]
        if len(a):
            a=a.iloc[0]
            lines.append(f"- {split}: trigger={c.trigger_rate:.1%} N={int(a.n)} delay={c.median_delay_h:.2f}h | 24h close={a.mean_close:+.3f} ATR DNR={a.dnr_std:+.3f} MFE={a.mean_mfe:.2f} MAE={a.mean_mae:.2f} MFE/MAE={a.mfe_mae_ratio:.2f} P+={a.p_positive:.1%}")
    lines.append('')
(OUT/'LAB113_REPORT.md').write_text('\n'.join(lines)+'\n')
meta=dict(context='fresh |Z|>=1 inverse crowd',search_hours=SEARCH_H,triggers=TRIGGERS,
          thresholds=dict(oi_flush_train_q10=q_oi_flush,oi_build_train_q90=q_oi_build,volume_z_train_q90=q_vol_spike,taker_z_fixed=TAKER_Z),
          caveat='descriptive conditional atlas; no trigger is a production rule without independent validation')
(OUT/'LAB113_meta.json').write_text(json.dumps(meta,indent=2))
print('\n'.join(lines))
