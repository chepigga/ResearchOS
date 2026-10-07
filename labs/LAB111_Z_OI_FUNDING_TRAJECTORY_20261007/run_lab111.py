#!/usr/bin/env python3
from __future__ import annotations
import math,re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab111_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
FUNDING_CSV=Path("binance_btc_funding.csv")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
HORIZONS=[240,1440,2880]
HL={240:'4h',1440:'24h',2880:'48h'}

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
        for d in frames[1:]:common &= set(d.columns)
        if len(frames)>1 and len(common)>=4:
            cols=list(common);return pd.concat([d[cols] for d in frames],ignore_index=True)
        return frames[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce');med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# long Binance flow: OI + long/short ratio
flow=load_zip(FLOW_ZIP)
tc=pick(flow.columns,['create_time','time','timestamp'])
rc=pick(flow.columns,['count_long_short_ratio','long_short_ratio','ratio'])
oic=pick(flow.columns,['sum_open_interest_value','sum_open_interest'])
if not all([tc,rc,oic]):raise RuntimeError(f'flow cols missing: {flow.columns.tolist()}')
flow=flow[[tc,rc,oic]].copy();flow['time']=ptime(flow[tc]);flow['ratio']=pd.to_numeric(flow[rc],errors='coerce');flow['oi']=pd.to_numeric(flow[oic],errors='coerce')
flow=flow.dropna(subset=['time','ratio','oi']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow.set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(72,min_periods=72).mean();sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)
flow['oi_chg_1h']=flow.oi/flow.oi.shift(12)-1.0
flow['oi_chg_prev1h']=flow.oi.shift(12)/flow.oi.shift(24)-1.0
flow['oi_accel_1h']=flow.oi_chg_1h-flow.oi_chg_prev1h

# price M5
raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','datetime','open_time']);po=pick(raw.columns,['open']);ph=pick(raw.columns,['high']);pl=pick(raw.columns,['low']);pc=pick(raw.columns,['close'])
p=raw[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
p['price_ret_1h']=p.close/p.close.shift(12)-1.0

# H1 ATR
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1);tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr_h1']=tr.rolling(14,min_periods=14).mean();h1['close_time']=h1.time+pd.Timedelta(hours=1)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),flow[['time','z','oi','oi_chg_1h','oi_accel_1h']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['z','oi','oi_chg_1h','oi_accel_1h','atr_h1','price_ret_1h']).reset_index(drop=True)

# funding, causal carry-forward from latest published funding timestamp
fund=pd.read_csv(FUNDING_CSV)
ft=pick(fund.columns,['time','timestamp']);fc=pick(fund.columns,['funding','funding_rate'])
fund['time']=ptime(fund[ft]);fund['funding']=pd.to_numeric(fund[fc],errors='coerce')
fund=fund[['time','funding']].dropna().sort_values('time').drop_duplicates('time',keep='last')
base=pd.merge_asof(base.sort_values('time'),fund.sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta(hours=16))

# classify funding: tiny band around zero = neutral
base['funding_regime']=np.where(base.funding.abs()<=1e-5,'NEUTRAL',np.where(base.funding>0,'POSITIVE','NEGATIVE'))

# TRAIN-derived tertiles for OI 1h change and acceleration; frozen for OOS
train_mask=base.time<TRAIN_END
q_oi=base.loc[train_mask,'oi_chg_1h'].quantile([1/3,2/3]).to_numpy()
q_acc=base.loc[train_mask,'oi_accel_1h'].quantile([1/3,2/3]).to_numpy()
def tert(v,q,labels):
    if v<q[0]:return labels[0]
    if v<q[1]:return labels[1]
    return labels[2]
base['oi_regime']=[tert(v,q_oi,['FALLING','FLAT','RISING']) for v in base.oi_chg_1h]
base['oi_accel_regime']=[tert(v,q_acc,['DECELERATING','FLAT','ACCELERATING']) for v in base.oi_accel_1h]
def divcat(pr,oi):
    if pr>0 and oi>0:return 'PRICE_UP_OI_UP'
    if pr>0 and oi<0:return 'PRICE_UP_OI_DOWN'
    if pr<0 and oi>0:return 'PRICE_DOWN_OI_UP'
    if pr<0 and oi<0:return 'PRICE_DOWN_OI_DOWN'
    return 'FLAT'
base['oi_price_state']=[divcat(pr,oi) for pr,oi in zip(base.price_ret_1h,base.oi_chg_1h)]

BT=base.time.reset_index(drop=True);BH=base.high.to_numpy(float);BL=base.low.to_numpy(float);BC=base.close.to_numpy(float);BA=base.atr_h1.to_numpy(float);BZ=base.z.to_numpy(float)

events=[];last_full=len(base)-1-2880//5
for i in range(1,len(base)):
    if i>last_full:continue
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    if pd.isna(base.funding.iloc[i]):continue
    side=-1 if BZ[i]>0 else 1;anchor=float(BC[i]);atr=float(BA[i])
    row=dict(signal_time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',year=int(BT.iloc[i].year),
             side='BUY' if side>0 else 'SELL',z=float(BZ[i]),abs_z=abs(float(BZ[i])),
             oi_regime=base.oi_regime.iloc[i],oi_accel_regime=base.oi_accel_regime.iloc[i],
             oi_price_state=base.oi_price_state.iloc[i],funding_regime=base.funding_regime.iloc[i],
             funding=float(base.funding.iloc[i]),oi_chg_1h=float(base.oi_chg_1h.iloc[i]),oi_accel_1h=float(base.oi_accel_1h.iloc[i]),price_ret_1h=float(base.price_ret_1h.iloc[i]))
    for mins in HORIZONS:
        e=i+mins//5;hi=float(np.max(BH[i+1:e+1]));lo=float(np.min(BL[i+1:e+1]));cl=float(BC[e])
        row[f'mfe_{HL[mins]}']=(hi-anchor)/atr if side>0 else (anchor-lo)/atr
        row[f'mae_{HL[mins]}']=(anchor-lo)/atr if side>0 else (hi-anchor)/atr
        row[f'close_{HL[mins]}']=side*(cl-anchor)/atr
    events.append(row)
ev=pd.DataFrame(events)
ev.to_csv(OUT/'LAB111_event_atlas.csv',index=False)

def metrics(g,h):
    x=g[f'close_{h}'].to_numpy(float);mfe=g[f'mfe_{h}'].to_numpy(float);mae=g[f'mae_{h}'].to_numpy(float)
    mean=float(np.mean(x));std=float(np.std(x,ddof=1)) if len(x)>1 else np.nan
    noise_range=float(np.mean((mfe+mae)/2))
    return dict(n=len(g),mean_close=mean,median_close=float(np.median(x)),p_positive=float(np.mean(x>0)),
                mean_mfe=float(np.mean(mfe)),mean_mae=float(np.mean(mae)),std_close=std,
                drift_to_noise_std=(mean/std if std>0 else np.nan),
                drift_to_noise_range=(mean/noise_range if noise_range>0 else np.nan))

rows=[]
dimensions={
 'OI_REGIME':'oi_regime',
 'FUNDING_REGIME':'funding_regime',
 'OI_ACCEL':'oi_accel_regime',
 'OI_PRICE_STATE':'oi_price_state'
}
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for dim,col in dimensions.items():
        for group,g in q.groupby(col):
            for h in ['4h','24h','48h']:
                rows.append(dict(split=split,dimension=dim,group=group,horizon=h,**metrics(g,h)))
pd.DataFrame(rows).to_csv(OUT/'LAB111_segment_atlas.csv',index=False)

# 2D OI x funding only, to avoid combinatorial fishing
cross=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for (oi,fu),g in q.groupby(['oi_regime','funding_regime']):
        if len(g)<30:continue
        for h in ['4h','24h','48h']:
            cross.append(dict(split=split,oi_regime=oi,funding_regime=fu,horizon=h,**metrics(g,h)))
pd.DataFrame(cross).to_csv(OUT/'LAB111_oi_x_funding.csv',index=False)

# descriptive top groups by TRAIN 48h DNR, with matching OOS shown; no promotion.
seg=pd.DataFrame(rows)
tr=seg[(seg.split=='TRAIN')&(seg.horizon=='48h')&(seg.n>=100)].sort_values('drift_to_noise_std',ascending=False)
tops=[]
for _,r in tr.head(12).iterrows():
    o=seg[(seg.split=='OOS')&(seg.dimension==r.dimension)&(seg.group==r.group)&(seg.horizon=='48h')]
    if len(o):
        o=o.iloc[0]
        tops.append(dict(dimension=r.dimension,group=r.group,
                         train_n=int(r.n),train_mean=r.mean_close,train_dnr=r.drift_to_noise_std,train_p=r.p_positive,
                         oos_n=int(o.n),oos_mean=o.mean_close,oos_dnr=o.drift_to_noise_std,oos_p=o.p_positive))
pd.DataFrame(tops).to_csv(OUT/'LAB111_top_train_groups_with_oos.csv',index=False)

# report
lines=['# LAB111 — Z × OI/FUNDING TRAJECTORY ATLAS','',
       'Same fresh |Z|>=1 inverse-crowd event clock as LAB110. OI and funding are context only; no entry/exit optimization.',
       f"OI regime uses TRAIN tertiles of 1h OI change: q33={q_oi[0]:+.6f}, q67={q_oi[1]:+.6f}. OI acceleration uses TRAIN tertiles: q33={q_acc[0]:+.6f}, q67={q_acc[1]:+.6f}.",
       'Funding: POSITIVE / NEGATIVE / NEUTRAL (|funding|<=1e-5). OI-price state is sign of 1h price return versus sign of 1h OI change.',
       'DNR(std)=mean directional close displacement / std of directional close displacement. DNR(range)=mean close / mean((MFE+MAE)/2).','',
       f"Events with OI+funding+full48h: ALL N={len(ev)} TRAIN N={(ev.split=='TRAIN').sum()} OOS N={(ev.split=='OOS').sum()}",'']

seg=pd.DataFrame(rows)
for dim in dimensions:
    lines.append(f'## {dim} — 48h')
    for split in ['TRAIN','OOS']:
        q=seg[(seg.dimension==dim)&(seg.split==split)&(seg.horizon=='48h')].sort_values('drift_to_noise_std',ascending=False)
        vals=[]
        for _,r in q.iterrows():
            vals.append(f"{r.group}: N={int(r.n)} mean={r.mean_close:+.3f} ATR DNR={r.drift_to_noise_std:+.3f} P+={r.p_positive:.1%}")
        lines.append(f"- {split}: "+' | '.join(vals))
    lines.append('')

(OUT/'LAB111_REPORT.md').write_text('\n'.join(lines)+'\n')
meta=dict(event_clock='LAB110 fresh |Z|>=1 inverse crowd',oi_change_window='1h',oi_regime='TRAIN tertiles frozen to OOS',
          oi_acceleration='1h change minus previous 1h change; TRAIN tertiles',funding_neutral_band=1e-5,
          dnr_std='mean directional close ATR / std directional close ATR',dnr_range='mean close ATR / mean half-path range',
          caution='descriptive segmentation; no cell is a validated trade filter; 2022 coverage remains sparse')
(OUT/'LAB111_meta.json').write_text(json.dumps(meta,indent=2))
print('\n'.join(lines))
