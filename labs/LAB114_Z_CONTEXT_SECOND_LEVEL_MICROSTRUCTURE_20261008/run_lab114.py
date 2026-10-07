#!/usr/bin/env python3
from __future__ import annotations
import json, math, re, zipfile
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab114_out"); OUT.mkdir(exist_ok=True)
SEC_ZIP=Path("BTCUSDT_sec.csv.zip")
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
SEARCH_H=6
SHORT_H=[15,60,240]
LONG_H=[12,24]
TRIGGERS=['ALIGNED_FLOW_BURST','TRADE_RATE_BURST','FLOW_REVERSAL','ABSORPTION','ABSORPTION_REVERSAL','EXHAUSTION']

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
            if not n.lower().endswith('.csv'):continue
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

# -------- 5m flow / Z --------
flow=load_zip(FLOW_ZIP)
tc=pick(flow.columns,['create_time','time','timestamp']);rc=pick(flow.columns,['count_long_short_ratio','ratio'])
flow=flow[[tc,rc]].copy();flow['time']=ptime(flow[tc]);flow['ratio']=pd.to_numeric(flow[rc],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(72,min_periods=72).mean();sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)

# -------- 5m price + causal H1 ATR --------
raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','open_time']);po=pick(raw.columns,['open']);ph=pick(raw.columns,['high']);pl=pick(raw.columns,['low']);pc=pick(raw.columns,['close'])
p=raw[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1);tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr_h1']=tr.rolling(14,min_periods=14).mean();h1['close_time']=h1.time+pd.Timedelta(hours=1)
p=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
p=pd.merge_asof(p.sort_values('time'),flow[['time','z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
p=p.dropna(subset=['atr_h1','z']).reset_index(drop=True)

# -------- second data -> causal 10-second micro bars --------
parts=[]
with zipfile.ZipFile(SEC_ZIP) as z:
    member=[n for n in z.namelist() if n.lower().endswith('.csv')][0]
    with z.open(member) as f:
        for ch in pd.read_csv(f,chunksize=1_000_000):
            ch=ch[['ts','o','h','l','c','bv','sv','bn','sn','bnot','snot','maxrun']].copy()
            ch['bucket']=(pd.to_numeric(ch.ts,errors='coerce').astype('Int64')//10)*10
            for c in ['o','h','l','c','bv','sv','bn','sn','bnot','snot','maxrun']: ch[c]=pd.to_numeric(ch[c],errors='coerce')
            ch=ch.dropna(subset=['bucket','o','h','l','c'])
            g=ch.groupby('bucket',sort=False).agg(
                o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last'),
                bv=('bv','sum'),sv=('sv','sum'),bn=('bn','sum'),sn=('sn','sum'),
                bnot=('bnot','sum'),snot=('snot','sum'),maxrun=('maxrun','max'))
            parts.append(g.reset_index())
sec=pd.concat(parts,ignore_index=True)
sec=sec.groupby('bucket',as_index=False).agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last'),bv=('bv','sum'),sv=('sv','sum'),bn=('bn','sum'),sn=('sn','sum'),bnot=('bnot','sum'),snot=('snot','sum'),maxrun=('maxrun','max'))
sec=sec.sort_values('bucket').drop_duplicates('bucket').reset_index(drop=True)
sec['time']=pd.to_datetime(sec.bucket,unit='s',utc=True)
sec['notional']=sec.bnot+sec.snot
sec['trades']=sec.bn+sec.sn
# 30-second rolling aggregates
rb=sec.bnot.rolling(3,min_periods=3).sum(); rs=sec.snot.rolling(3,min_periods=3).sum()
rn=rb+rs
sec['imb30']=(rb-rs)/rn.replace(0,np.nan)
rbc=sec.bn.rolling(3,min_periods=3).sum(); rsc=sec.sn.rolling(3,min_periods=3).sum()
sec['cntimb30']=(rbc-rsc)/(rbc+rsc).replace(0,np.nan)
sec['not30']=rn
sec['trades30']=rbc+rsc
sec['ret30']=sec.c/sec.c.shift(3)-1.0
# rolling 1h z-scores on log activity
for src,out in [('not30','notz'),('trades30','tradesz')]:
    x=np.log1p(sec[src].clip(lower=0))
    m=x.rolling(360,min_periods=180).mean();s=x.rolling(360,min_periods=180).std(ddof=0)
    sec[out]=(x-m)/s.replace(0,np.nan)
sec=sec.dropna(subset=['imb30','cntimb30','notz','tradesz','ret30']).reset_index(drop=True)

SEC_START=sec.time.iloc[0]; SEC_END=sec.time.iloc[-1]
# overlap Z events only
pz=p[(p.time>=SEC_START)&(p.time<=SEC_END-pd.Timedelta(hours=24))].copy().reset_index(drop=True)
zv=pz.z.to_numpy(float)
sig_idx=np.flatnonzero((np.abs(zv[1:])>=1)&(np.abs(zv[:-1])<1))+1
signals=[]
for k in sig_idx:
    side=-1 if zv[k]>0 else 1
    signals.append(dict(signal_time=pz.time.iloc[k],side=side,z=float(zv[k]),atr=float(pz.atr_h1.iloc[k]),anchor=float(pz.close.iloc[k])))
sig=pd.DataFrame(signals)
if len(sig)<100: raise RuntimeError(f'too few overlapping signals: {len(sig)} sec={SEC_START}..{SEC_END}')

# chronological DEV/HOLDOUT split within second-data era (not pristine OOS)
cut=sig.signal_time.quantile(0.60)
sig['split']=np.where(sig.signal_time<=cut,'DEV60','HOLDOUT40')

st=sec.bucket.to_numpy(np.int64)
so=sec.o.to_numpy(float);sh=sec.h.to_numpy(float);sl=sec.l.to_numpy(float);sc=sec.c.to_numpy(float)
imb=sec.imb30.to_numpy(float);cimb=sec.cntimb30.to_numpy(float);notz=sec.notz.to_numpy(float);trz=sec.tradesz.to_numpy(float)

def idx_at(t):
    return int(np.searchsorted(st,int(pd.Timestamp(t).timestamp()),side='left'))
def trig_mask(side):
    d=side*imb; dc=side*cimb
    aligned=(d>=0.35)&(notz>=1.5)
    trade=(dc>=0.25)&(trz>=1.5)
    rev=(d>=0.25)&np.r_[False,(d[:-1]<=-0.25)]
    return d,aligned,trade,rev

masks={}
for side in [1,-1]:
    d,aligned,trade,rev=trig_mask(side)
    masks[(side,'ALIGNED_FLOW_BURST')]=aligned
    masks[(side,'TRADE_RATE_BURST')]=trade
    masks[(side,'FLOW_REVERSAL')]=rev
# absorption is signal-ATR-dependent, evaluated event-by-event.

def first_simple(mask,a,b):
    ix=np.flatnonzero(mask[a:b])
    return None if not len(ix) else a+int(ix[0])

def find_trigger(srow,name):
    side=int(srow.side);atr=float(srow.atr)
    a=idx_at(srow.signal_time)+1;b=min(a+SEARCH_H*360,len(sec)-2)
    if a>=b:return None
    if name in ['ALIGNED_FLOW_BURST','TRADE_RATE_BURST','FLOW_REVERSAL']:
        return first_simple(masks[(side,name)],a,b)
    d=side*imb
    # 30s adverse move in ATR units, positive means against desired side
    adverse=-side*(sc/np.r_[sc[0],sc[:-1]]-1.0) * sc / atr
    # More stable direct 30s displacement in ATR:
    px30=np.r_[np.repeat(sc[0],3),sc[:-3]]
    adverse30=-side*(sc-px30)/atr
    absorption=(d<=-0.35)&(notz>=1.5)&(adverse30<=0.03)
    if name=='ABSORPTION':return first_simple(absorption,a,b)
    if name in ['ABSORPTION_REVERSAL','EXHAUSTION']:
        abs_ix=np.flatnonzero(absorption[a:b])
        for off in abs_ix:
            j=a+int(off);e=min(j+30,b) # next 5 min
            if name=='ABSORPTION_REVERSAL':
                cand=np.flatnonzero(d[j+1:e]>=0.25)
            else:
                cand=np.flatnonzero((d[j+1:e]>=0.25)&(notz[j+1:e]<1.0))
            if len(cand):return j+1+int(cand[0])
    return None

def short_path(j,side,entry,atr,minutes):
    e=min(j+minutes*6,len(sec)-1)
    hi=float(sh[j:e+1].max());lo=float(sl[j:e+1].min());cl=float(sc[e])
    mfe=(hi-entry)/atr if side>0 else (entry-lo)/atr
    mae=(entry-lo)/atr if side>0 else (hi-entry)/atr
    return mfe,mae,side*(cl-entry)/atr

# 5m forward path from trigger time
ptimes=(pd.to_datetime(p.time,utc=True).astype('int64')//10**9).to_numpy();PH=p.high.to_numpy(float);PL=p.low.to_numpy(float);PC=p.close.to_numpy(float)
def long_path(t,side,entry,atr,hours):
    a=int(np.searchsorted(ptimes,int(pd.Timestamp(t).timestamp()),side='left'));e=min(a+hours*12,len(p)-1)
    hi=float(PH[a:e+1].max());lo=float(PL[a:e+1].min());cl=float(PC[e])
    return ((hi-entry)/atr if side>0 else (entry-lo)/atr),((entry-lo)/atr if side>0 else (hi-entry)/atr),side*(cl-entry)/atr

rows=[]
for _,srow in sig.iterrows():
    for name in TRIGGERS:
        j=find_trigger(srow,name)
        if j is None:continue
        entry_j=j+1;entry=float(so[entry_j]);side=int(srow.side);atr=float(srow.atr)
        r=dict(signal_time=srow.signal_time,split=srow.split,trigger=name,side='BUY' if side>0 else 'SELL',z=srow.z,
               trigger_time=sec.time.iloc[j],entry_time=sec.time.iloc[entry_j],
               delay_min=(sec.time.iloc[j]-srow.signal_time).total_seconds()/60.0,
               imb30=float(imb[j]),cntimb30=float(cimb[j]),notz=float(notz[j]),tradesz=float(trz[j]))
        for mins in SHORT_H:
            mfe,mae,cl=short_path(entry_j,side,entry,atr,mins);lab=f'{mins}m' if mins<60 else f'{mins//60}h'
            r[f'mfe_{lab}']=mfe;r[f'mae_{lab}']=mae;r[f'close_{lab}']=cl
        for h in LONG_H:
            mfe,mae,cl=long_path(sec.time.iloc[entry_j],side,entry,atr,h);lab=f'{h}h'
            r[f'mfe_{lab}']=mfe;r[f'mae_{lab}']=mae;r[f'close_{lab}']=cl
        rows.append(r)
ev=pd.DataFrame(rows)
if ev.empty: raise RuntimeError(f'no microstructure triggers found; signals={len(sig)} sec={SEC_START}..{SEC_END}')
ev.to_csv(OUT/'LAB114_trigger_events.csv',index=False)

def met(g,lab):
    x=g[f'close_{lab}'].to_numpy(float);mfe=g[f'mfe_{lab}'].to_numpy(float);mae=g[f'mae_{lab}'].to_numpy(float)
    mean=float(x.mean());sd=float(x.std(ddof=1)) if len(x)>1 else np.nan;noise=float(np.mean((mfe+mae)/2))
    return dict(n=len(g),mean_close=mean,p_positive=float((x>0).mean()),mean_mfe=float(mfe.mean()),mean_mae=float(mae.mean()),
                mfe_mae_ratio=float(mfe.mean()/mae.mean()) if mae.mean()>0 else np.nan,
                dnr_std=mean/sd if sd>0 else np.nan,dnr_range=mean/noise if noise>0 else np.nan)

atlas=[];conv=[]
for split in ['DEV60','HOLDOUT40']:
    qs=sig[sig.split==split]
    for name in TRIGGERS:
        g=ev[(ev.split==split)&(ev.trigger==name)]
        conv.append(dict(split=split,trigger=name,n_signals=len(qs),n_trigger=len(g),trigger_rate=len(g)/len(qs) if len(qs) else np.nan,
                         median_delay_min=float(g.delay_min.median()) if len(g) else np.nan))
        for lab in ['15m','1h','4h','12h','24h']:
            if len(g):atlas.append(dict(split=split,trigger=name,horizon=lab,**met(g,lab)))
atlas=pd.DataFrame(atlas);atlas.to_csv(OUT/'LAB114_atlas.csv',index=False)
cv=pd.DataFrame(conv);cv.to_csv(OUT/'LAB114_conversion.csv',index=False)

# Baseline Z events on exact same overlap sample.
base_rows=[]
for split in ['DEV60','HOLDOUT40']:
    for _,srow in sig[sig.split==split].iterrows():
        side=int(srow.side);atr=float(srow.atr);entry=float(srow.anchor)
        rr=dict(split=split)
        for h in [4,12,24]:
            mfe,mae,cl=long_path(srow.signal_time,side,entry,atr,h);rr[f'mfe_{h}h']=mfe;rr[f'mae_{h}h']=mae;rr[f'close_{h}h']=cl
        base_rows.append(rr)
basev=pd.DataFrame(base_rows)
baseline=[]
for split in ['DEV60','HOLDOUT40']:
    g=basev[basev.split==split]
    for lab in ['4h','12h','24h']:baseline.append(dict(split=split,horizon=lab,**met(g,lab)))
pd.DataFrame(baseline).to_csv(OUT/'LAB114_baseline.csv',index=False)

# year/month robustness for holdout where possible
monthly=[]
for split in ['DEV60','HOLDOUT40']:
    for name in TRIGGERS:
        g=ev[(ev.split==split)&(ev.trigger==name)].copy()
        if not len(g):continue
        g['month']=pd.to_datetime(g.signal_time,utc=True).dt.to_period('M').astype(str)
        for m,z in g.groupby('month'):
            if len(z)>=20:monthly.append(dict(split=split,trigger=name,month=m,**met(z,'4h')))
pd.DataFrame(monthly).to_csv(OUT/'LAB114_monthly_4h.csv',index=False)

lines=['# LAB114 — Z CONTEXT × SECOND-LEVEL MICROSTRUCTURE','',
       f'Second data coverage: {SEC_START} → {SEC_END}. Derived causal 10-second bars from true 1-second Binance aggressor-flow records.',
       f'Overlapping fresh |Z|>=1 inverse-crowd signals: N={len(sig)}. Chronological split inside this short second-data era: DEV60 through {cut}; HOLDOUT40 after it.',
       'No SL/TP optimization. Triggers are fixed definitions; entry proxy is next 10-second open. 15m/1h/4h paths use second-derived bars; 12h/24h use 5m price.',
       'This is development validation only, not pristine OOS, because 2026 has already been repeatedly inspected.','']
bdf=pd.DataFrame(baseline)
for split in ['DEV60','HOLDOUT40']:
    b=bdf[(bdf.split==split)&(bdf.horizon=='4h')].iloc[0]
    lines.append(f"- {split} Z-only baseline 4h: N={int(b.n)} close={b.mean_close:+.3f} ATR DNR={b.dnr_std:+.3f} MFE/MAE={b.mfe_mae_ratio:.2f}")
lines.append('')
for name in TRIGGERS:
    lines.append(f'## {name}')
    for split in ['DEV60','HOLDOUT40']:
        c=cv[(cv.split==split)&(cv.trigger==name)].iloc[0];a=atlas[(atlas.split==split)&(atlas.trigger==name)&(atlas.horizon=='4h')]
        if len(a):
            a=a.iloc[0]
            lines.append(f"- {split}: rate={c.trigger_rate:.1%} N={int(a.n)} delay={c.median_delay_min:.1f}m | 4h close={a.mean_close:+.3f} ATR DNR={a.dnr_std:+.3f} MFE={a.mean_mfe:.2f} MAE={a.mean_mae:.2f} MFE/MAE={a.mfe_mae_ratio:.2f} P+={a.p_positive:.1%}")
        else: lines.append(f"- {split}: no events")
    lines.append('')
(OUT/'LAB114_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB114_meta.json').write_text(json.dumps(dict(sec_start=str(SEC_START),sec_end=str(SEC_END),signals=len(sig),split_cut=str(cut),triggers=TRIGGERS,
    definitions=dict(flow_burst='directional 30s aggressor-notional imbalance >=0.35 and rolling 1h log-notional z>=1.5',
                     trade_rate_burst='directional 30s trade-count imbalance >=0.25 and rolling 1h log-trade z>=1.5',
                     flow_reversal='30s directional imbalance crosses from <=-0.25 to >=+0.25',
                     absorption='opposing imbalance <=-0.35 with notional z>=1.5 but <=0.03 H1 ATR adverse 30s price response',
                     absorption_reversal='absorption then aligned imbalance >=0.25 within 5m',
                     exhaustion='absorption then aligned imbalance >=0.25 with notional z<1 within 5m'),
    caveat='short 2026 second-level sample; chronological holdout is development evidence only'),indent=2))
print('\n'.join(lines))
