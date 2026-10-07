#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd
OUT=Path("lab113_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip"); PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC"); SEARCH_BARS=72
HORIZONS=[15,60,240,720,1440]; HL={15:'15m',60:'1h',240:'4h',720:'12h',1440:'24h'}
TRIGGERS=['TAKER_REVERSAL','OI_FLUSH','OI_BUILD','VOLUME_SPIKE','OI_FLUSH_TAKER','OI_BUILD_TAKER','FLUSH_TAKER_VOLUME']
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
            if n.lower().endswith('.csv'):
                try:
                    with z.open(n) as f:d=pd.read_csv(f)
                    if len(d):frames.append(d)
                except:pass
        common=set(frames[0].columns)
        for d in frames[1:]:common&=set(d.columns)
        if len(frames)>1 and len(common)>=4:
            cols=list(common);return pd.concat([d[cols] for d in frames],ignore_index=True)
        return frames[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce');med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')
flow=load_zip(FLOW_ZIP)
tc=pick(flow.columns,['create_time','time']);rc=pick(flow.columns,['count_long_short_ratio','ratio']);oic=pick(flow.columns,['sum_open_interest_value','sum_open_interest']);tkc=pick(flow.columns,['sum_taker_long_short_vol_ratio','taker_ratio'])
flow=flow[[tc,rc,oic,tkc]].copy();flow['time']=ptime(flow[tc])
flow['ratio']=pd.to_numeric(flow[rc],errors='coerce');flow['oi']=pd.to_numeric(flow[oic],errors='coerce');flow['taker']=pd.to_numeric(flow[tkc],errors='coerce')
flow=flow.dropna(subset=['time','ratio','oi','taker']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[(flow.ratio>0)&(flow.taker>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(72,min_periods=72).mean();sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0);flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)
flow['oi_chg_1h']=flow.oi/flow.oi.shift(12)-1;flow['oi_chg_15m']=flow.oi/flow.oi.shift(3)-1
flow['log_taker']=np.log(flow.taker);tm=flow.log_taker.rolling(72,min_periods=72).mean();ts=flow.log_taker.rolling(72,min_periods=72).std(ddof=0);flow['taker_z']=(flow.log_taker-tm)/ts.replace(0,np.nan)
raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','open_time']);po=pick(raw.columns,['open']);ph=pick(raw.columns,['high']);pl=pick(raw.columns,['low']);pc=pick(raw.columns,['close']);pv=pick(raw.columns,['volume'])
cols=[pt,po,ph,pl,pc]+([pv] if pv else []);p=raw[cols].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p['volume']=pd.to_numeric(p[pv],errors='coerce') if pv else 1.0
p=p[['time','open','high','low','close','volume']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum')).dropna().reset_index()
p['vol_1h']=p.volume.rolling(12,min_periods=12).sum();vm=p.vol_1h.rolling(288,min_periods=288).mean();vs=p.vol_1h.rolling(288,min_periods=288).std(ddof=0);p['vol_z_1h']=(p.vol_1h-vm)/vs.replace(0,np.nan)
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1);tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1);h1['atr_h1']=tr.rolling(14,min_periods=14).mean();h1['close_time']=h1.time+pd.Timedelta(hours=1)
base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),flow[['time','z','oi_chg_1h','oi_chg_15m','taker_z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['z','oi_chg_1h','oi_chg_15m','taker_z','atr_h1','vol_z_1h']).reset_index(drop=True)
trm=base.time<TRAIN_END;qflush=float(base.loc[trm,'oi_chg_1h'].quantile(.10));qbuild=float(base.loc[trm,'oi_chg_1h'].quantile(.90));qvol=float(base.loc[trm,'vol_z_1h'].quantile(.90));TZ=.5
oi=base.oi_chg_1h.to_numpy(float);tz=base.taker_z.to_numpy(float);vz=base.vol_z_1h.to_numpy(float)
def aligned_hist(side):
    a=(tz>=TZ) if side>0 else (tz<=-TZ)
    o=(tz<=-TZ) if side>0 else (tz>=TZ)
    rev=a & np.r_[False,o[:-1]]
    recent=np.zeros(len(a),bool)
    for k in range(4):
        recent |= np.r_[np.zeros(k,bool),a[:len(a)-k]] if k else a
    return a,rev,recent
masks={}
for side in [1,-1]:
    a,rev,recent=aligned_hist(side)
    flush=oi<=qflush;build=oi>=qbuild;vol=vz>=qvol
    masks[(side,'TAKER_REVERSAL')]=rev;masks[(side,'OI_FLUSH')]=flush;masks[(side,'OI_BUILD')]=build;masks[(side,'VOLUME_SPIKE')]=vol
    masks[(side,'OI_FLUSH_TAKER')]=flush&recent;masks[(side,'OI_BUILD_TAKER')]=build&recent;masks[(side,'FLUSH_TAKER_VOLUME')]=flush&recent&vol
def next_true(mask):
    n=len(mask);out=np.full(n,n,dtype=np.int64);nxt=n
    for i in range(n-1,-1,-1):
        if mask[i]:nxt=i
        out[i]=nxt
    return out
nextmap={k:next_true(v) for k,v in masks.items()}
BT=base.time.reset_index(drop=True);BO=base.open.to_numpy(float);BH=base.high.to_numpy(float);BL=base.low.to_numpy(float);BC=base.close.to_numpy(float);BA=base.atr_h1.to_numpy(float);BZ=base.z.to_numpy(float)
def fwd(j,side,entry,atr,mins):
    e=min(j+mins//5,len(base)-1);hi=float(BH[j:e+1].max());lo=float(BL[j:e+1].min());cl=float(BC[e])
    return ((hi-entry)/atr if side>0 else (entry-lo)/atr),((entry-lo)/atr if side>0 else (hi-entry)/atr),side*(cl-entry)/atr
sig_idx=np.flatnonzero((np.abs(BZ[1:])>=1)&(np.abs(BZ[:-1])<1))+1
last=len(base)-1-max(HORIZONS)//5-1;sig_idx=sig_idx[sig_idx<last]
rows=[];conv=[]
for side in [1,-1]:
  inds=sig_idx[np.where(np.where(BZ[sig_idx]>0,-1,1)==side)[0]]
  for name in TRIGGERS:
    nm=nextmap[(side,name)]
    for split in ['TRAIN','OOS']:
      tvals=pd.to_datetime(BT.iloc[inds],utc=True).astype('int64').to_numpy(); cut=TRAIN_END.value
      ss=inds[(tvals<cut) if split=='TRAIN' else (tvals>=cut)]
      hits=0;delays=[]
      for i in ss:
        j=int(nm[i+1]) if i+1<len(nm) else len(base)
        if j>=len(base) or j>i+SEARCH_BARS:continue
        hits+=1;delays.append((BT.iloc[j]-BT.iloc[i]).total_seconds()/3600)
        ei=j+1;entry=float(BO[ei]);atr=float(BA[i])
        r=dict(signal_time=BT.iloc[i],trigger_time=BT.iloc[j],entry_time=BT.iloc[ei],split=split,trigger=name,side='BUY' if side>0 else 'SELL',z=float(BZ[i]),delay_h=delays[-1],oi_chg_1h=float(oi[j]),oi_chg_15m=float(base.oi_chg_15m.iloc[j]),taker_z=float(tz[j]),vol_z_1h=float(vz[j]))
        for mins in HORIZONS:
            mfe,mae,close=fwd(ei,side,entry,atr,mins);lab=HL[mins];r[f'mfe_{lab}']=mfe;r[f'mae_{lab}']=mae;r[f'close_{lab}']=close
        rows.append(r)
      conv.append(dict(split=split,side='BUY' if side>0 else 'SELL',trigger=name,n_signals=len(ss),trigger_count=hits,trigger_rate=hits/len(ss) if len(ss) else np.nan,median_delay_h=float(np.median(delays)) if delays else np.nan))
ev=pd.DataFrame(rows);ev.to_csv(OUT/'LAB113_trigger_events.csv',index=False);pd.DataFrame(conv).to_csv(OUT/'LAB113_conversion_side.csv',index=False)
def met(g,lab):
    x=g[f'close_{lab}'].to_numpy(float);mfe=g[f'mfe_{lab}'].to_numpy(float);mae=g[f'mae_{lab}'].to_numpy(float);mean=float(x.mean());sd=float(x.std(ddof=1)) if len(x)>1 else np.nan;noise=float(np.mean((mfe+mae)/2))
    return dict(n=len(g),mean_close=mean,p_positive=float((x>0).mean()),mean_mfe=float(mfe.mean()),mean_mae=float(mae.mean()),mfe_mae_ratio=float(mfe.mean()/mae.mean()) if mae.mean()>0 else np.nan,dnr_std=mean/sd if sd>0 else np.nan,dnr_range=mean/noise if noise>0 else np.nan)
atlas=[]
for split in ['TRAIN','OOS']:
  for name in TRIGGERS:
    g=ev[(ev.split==split)&(ev.trigger==name)]
    for lab in HL.values():
      if len(g):atlas.append(dict(split=split,trigger=name,horizon=lab,**met(g,lab)))
atlas=pd.DataFrame(atlas);atlas.to_csv(OUT/'LAB113_atlas.csv',index=False)
# pooled conversion
cv=[]
cvs=pd.DataFrame(conv)
for split in ['TRAIN','OOS']:
  for name in TRIGGERS:
    g=cvs[(cvs.split==split)&(cvs.trigger==name)]
    cv.append(dict(split=split,trigger=name,n_signals=int(g.n_signals.sum()),trigger_count=int(g.trigger_count.sum()),trigger_rate=float(g.trigger_count.sum()/g.n_signals.sum()),median_delay_h=float(ev[(ev.split==split)&(ev.trigger==name)].delay_h.median())))
cv=pd.DataFrame(cv);cv.to_csv(OUT/'LAB113_conversion.csv',index=False)
lines=['# LAB113 — Z CONTEXT × MICROSTRUCTURE TRIGGER','',
'Context: fresh |Z|>=1 inverse crowd. Search next 6h; entry proxy is next 5m open after trigger.',
f'TRAIN-only thresholds: OI flush q10={qflush:+.4%}; OI build q90={qbuild:+.4%}; volume z q90={qvol:+.3f}; taker z fixed ±{TZ}.',
'Composite triggers are fully causal: OI event on current bar plus aligned taker state on current/previous 15m. No future-centered matching.','']
for name in TRIGGERS:
  lines.append(f'## {name}')
  for split in ['TRAIN','OOS']:
    c=cv[(cv.split==split)&(cv.trigger==name)].iloc[0];a=atlas[(atlas.split==split)&(atlas.trigger==name)&(atlas.horizon=='24h')].iloc[0]
    lines.append(f"- {split}: rate={c.trigger_rate:.1%} N={int(a.n)} delay={c.median_delay_h:.2f}h | 24h close={a.mean_close:+.3f} ATR DNR={a.dnr_std:+.3f} MFE={a.mean_mfe:.2f} MAE={a.mean_mae:.2f} MFE/MAE={a.mfe_mae_ratio:.2f} P+={a.p_positive:.1%}")
  lines.append('')
(OUT/'LAB113_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB113_meta.json').write_text(json.dumps(dict(context='fresh |Z|>=1 inverse crowd',search_h=6,thresholds=dict(oi_flush_q10=qflush,oi_build_q90=qbuild,vol_z_q90=qvol,taker_z=TZ),caveat='descriptive atlas; repeated OOS is development evidence, not pristine validation'),indent=2))
print('\n'.join(lines))
