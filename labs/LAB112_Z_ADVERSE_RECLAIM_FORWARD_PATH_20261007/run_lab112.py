#!/usr/bin/env python3
from __future__ import annotations
import math,re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab112_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")

ADVERSE_LEVELS=[0.25,0.50,0.75,1.00]
RECLAIM_WINDOWS_H=[4,8,12,24]
FORWARD_H=[4,12,24,48]
STOP_ATR=[0.50,0.75,1.00,1.50]
RRS=[1.5,2.0]

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
        if not frames: raise RuntimeError(f"no csv in {zp}")
        common=set(frames[0].columns)
        for d in frames[1:]: common &= set(d.columns)
        if len(frames)>1 and len(common)>=4:
            cols=list(common); return pd.concat([d[cols] for d in frames],ignore_index=True)
        return frames[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce');med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

flow=load_zip(FLOW_ZIP)
ft=pick(flow.columns,['create_time','timestamp','time','datetime','open_time'])
fr=pick(flow.columns,['count_long_short_ratio','longShortRatio','long_short_ratio','ratio'])
flow=flow[[ft,fr]].copy();flow['time']=ptime(flow[ft]);flow['ratio']=pd.to_numeric(flow[fr],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(72,min_periods=72).mean();sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)

raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','datetime','open_time']);po=pick(raw.columns,['open']);ph=pick(raw.columns,['high']);pl=pick(raw.columns,['low']);pc=pick(raw.columns,['close'])
p=raw[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prev=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
h1['atr_h1']=tr.rolling(14,min_periods=14).mean();h1['close_time']=h1.time+pd.Timedelta(hours=1)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),flow[['time','z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['z','atr_h1']).reset_index(drop=True)

BT=base.time.reset_index(drop=True)
BO=base.open.to_numpy(float);BH=base.high.to_numpy(float);BL=base.low.to_numpy(float);BC=base.close.to_numpy(float);BA=base.atr_h1.to_numpy(float);BZ=base.z.to_numpy(float)

def first_adverse(i,side,anchor,atr,level,max_h=24):
    end=min(i+max_h*12,len(base)-2)
    if side>0:
        x=(anchor-BL[i+1:end+1])/atr
    else:
        x=(BH[i+1:end+1]-anchor)/atr
    ix=np.flatnonzero(x>=level)
    return None if not len(ix) else i+1+int(ix[0])

def first_reclaim(advi,i,side,anchor,window_h):
    end=min(advi+window_h*12,len(base)-2)
    for j in range(advi,end+1):
        if (BC[j]>=anchor if side>0 else BC[j]<=anchor):
            entry_i=j+1
            if entry_i<len(base): return j,entry_i
    return None,None

def forward_metrics(entry_i,side,entry,atr,hours):
    end=min(entry_i+hours*12-1,len(base)-1)
    if end<entry_i:return None
    hi=float(np.max(BH[entry_i:end+1]));lo=float(np.min(BL[entry_i:end+1]));cl=float(BC[end])
    mfe=(hi-entry)/atr if side>0 else (entry-lo)/atr
    mae=(entry-lo)/atr if side>0 else (hi-entry)/atr
    close=side*(cl-entry)/atr
    return mfe,mae,close,end

def first_hit_result(entry_i,side,entry,atr,stop_atr,rr,hours=48):
    sl=entry-side*stop_atr*atr;tp=entry+side*stop_atr*rr*atr
    end=min(entry_i+hours*12-1,len(base)-1)
    for j in range(entry_i,end+1):
        hit_sl=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        hit_tp=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hit_sl and hit_tp:return -1.0,'BOTH_STOP_FIRST',j
        if hit_sl:return -1.0,'SL',j
        if hit_tp:return rr,'TP',j
    exitr=side*(BC[end]-entry)/(stop_atr*atr)
    return float(exitr),'TIME48',end

events=[]
max_tail=(24+48)*12
last_i=len(base)-1-max_tail
for i in range(1,last_i):
    if not(abs(BZ[i])>=1.0 and abs(BZ[i-1])<1.0):continue
    side=-1 if BZ[i]>0 else 1;anchor=float(BC[i]);atr=float(BA[i])
    if not np.isfinite(atr) or atr<=0:continue
    split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS'
    for adv in ADVERSE_LEVELS:
        ai=first_adverse(i,side,anchor,atr,adv,24)
        if ai is None:continue
        for rw in RECLAIM_WINDOWS_H:
            rci,ei=first_reclaim(ai,i,side,anchor,rw)
            if ei is None:continue
            entry=float(BO[ei])
            row=dict(signal_time=BT.iloc[i],split=split,year=int(BT.iloc[i].year),
                     side='BUY' if side>0 else 'SELL',side_num=side,z=float(BZ[i]),abs_z=abs(float(BZ[i])),
                     adverse_atr=adv,reclaim_window_h=rw,adverse_time=BT.iloc[ai],reclaim_close_time=BT.iloc[rci],entry_time=BT.iloc[ei],
                     signal_anchor=anchor,entry=entry,atr_h1=atr,
                     time_to_adverse_h=(BT.iloc[ai]-BT.iloc[i]).total_seconds()/3600,
                     time_adverse_to_reclaim_h=(BT.iloc[rci]-BT.iloc[ai]).total_seconds()/3600,
                     total_delay_h=(BT.iloc[ei]-BT.iloc[i]).total_seconds()/3600,
                     entry_vs_anchor_atr=side*(entry-anchor)/atr)
            for h in FORWARD_H:
                m=forward_metrics(ei,side,entry,atr,h)
                row[f'mfe_{h}h']=m[0];row[f'mae_{h}h']=m[1];row[f'close_{h}h']=m[2]
            for st in STOP_ATR:
                for rr in RRS:
                    r,reason,exi=first_hit_result(ei,side,entry,atr,st,rr,48)
                    row[f'R_s{st:.2f}_rr{rr:.1f}']=r
                    row[f'exit_s{st:.2f}_rr{rr:.1f}']=reason
            events.append(row)
ev=pd.DataFrame(events)
ev.to_csv(OUT/'LAB112_reclaim_events.csv',index=False)

# unique availability / conversion from original Z signals
sig=[]
for i in range(1,last_i):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1;anchor=float(BC[i]);atr=float(BA[i])
    if not np.isfinite(atr) or atr<=0:continue
    split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS'
    for adv in ADVERSE_LEVELS:
        ai=first_adverse(i,side,anchor,atr,adv,24)
        for rw in RECLAIM_WINDOWS_H:
            got=False;delay=np.nan
            if ai is not None:
                rci,ei=first_reclaim(ai,i,side,anchor,rw)
                got=ei is not None
                if got:delay=(BT.iloc[ei]-BT.iloc[i]).total_seconds()/3600
            sig.append(dict(signal_time=BT.iloc[i],split=split,adverse_atr=adv,reclaim_window_h=rw,adverse_hit=ai is not None,reclaim=got,total_delay_h=delay))
sig=pd.DataFrame(sig)
conv=[]
for split in ['TRAIN','OOS']:
    q=sig[sig.split==split]
    nsignals=q.signal_time.nunique()
    for adv in ADVERSE_LEVELS:
        for rw in RECLAIM_WINDOWS_H:
            g=q[(q.adverse_atr==adv)&(q.reclaim_window_h==rw)]
            conv.append(dict(split=split,adverse_atr=adv,reclaim_window_h=rw,n_signals=nsignals,
                             adverse_hit_rate=float(g.adverse_hit.mean()),reclaim_rate_all=float(g.reclaim.mean()),
                             reclaim_rate_given_adverse=float(g.loc[g.adverse_hit,'reclaim'].mean()) if g.adverse_hit.any() else np.nan,
                             median_total_delay_h=float(g.loc[g.reclaim,'total_delay_h'].median()) if g.reclaim.any() else np.nan))
pd.DataFrame(conv).to_csv(OUT/'LAB112_conversion.csv',index=False)

def path_metrics(g,h):
    x=g[f'close_{h}h'].to_numpy(float);mfe=g[f'mfe_{h}h'].to_numpy(float);mae=g[f'mae_{h}h'].to_numpy(float)
    sd=float(np.std(x,ddof=1)) if len(x)>1 else np.nan
    mean=float(np.mean(x));noise=float(np.mean((mfe+mae)/2))
    return dict(n=len(g),mean_close=mean,median_close=float(np.median(x)),p_positive=float(np.mean(x>0)),
                mean_mfe=float(np.mean(mfe)),median_mfe=float(np.median(mfe)),mean_mae=float(np.mean(mae)),median_mae=float(np.median(mae)),
                dnr_std=mean/sd if sd>0 else np.nan,dnr_range=mean/noise if noise>0 else np.nan)

rows=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for adv in ADVERSE_LEVELS:
        for rw in RECLAIM_WINDOWS_H:
            g=q[(q.adverse_atr==adv)&(q.reclaim_window_h==rw)]
            if not len(g):continue
            for h in FORWARD_H:
                rows.append(dict(split=split,adverse_atr=adv,reclaim_window_h=rw,horizon_h=h,**path_metrics(g,h)))
pd.DataFrame(rows).to_csv(OUT/'LAB112_forward_atlas.csv',index=False)

# R:R feasibility table; descriptive, not selecting by OOS
rrrows=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for adv in ADVERSE_LEVELS:
        for rw in RECLAIM_WINDOWS_H:
            g=q[(q.adverse_atr==adv)&(q.reclaim_window_h==rw)]
            if not len(g):continue
            for st in STOP_ATR:
                for rr in RRS:
                    c=f'R_s{st:.2f}_rr{rr:.1f}';x=g[c].to_numpy(float)
                    pos=x[x>0].sum();neg=-x[x<0].sum()
                    rrrows.append(dict(split=split,adverse_atr=adv,reclaim_window_h=rw,stop_atr=st,rr=rr,n=len(g),
                                       ev=float(np.mean(x)),pf=float(pos/neg) if neg>0 else np.inf,wr=float(np.mean(x>0)),
                                       tp_rate=float(np.mean(g[f'exit_s{st:.2f}_rr{rr:.1f}']=='TP')),
                                       sl_rate=float(np.mean(g[f'exit_s{st:.2f}_rr{rr:.1f}'].isin(['SL','BOTH_STOP_FIRST'])))))
pd.DataFrame(rrrows).to_csv(OUT/'LAB112_rr_feasibility.csv',index=False)

# TRAIN-ranked configurations with OOS shown, but no promotion
rrdf=pd.DataFrame(rrrows)
tr=rrdf[(rrdf.split=='TRAIN')&(rrdf.n>=300)].sort_values(['pf','ev'],ascending=False).head(15)
tops=[]
for _,r in tr.iterrows():
    o=rrdf[(rrdf.split=='OOS')&(rrdf.adverse_atr==r.adverse_atr)&(rrdf.reclaim_window_h==r.reclaim_window_h)&(rrdf.stop_atr==r.stop_atr)&(rrdf.rr==r.rr)]
    if len(o):
        o=o.iloc[0]
        tops.append(dict(adverse_atr=r.adverse_atr,reclaim_window_h=int(r.reclaim_window_h),stop_atr=r.stop_atr,rr=r.rr,
                         train_n=int(r.n),train_ev=r.ev,train_pf=r.pf,train_wr=r.wr,
                         oos_n=int(o.n),oos_ev=o.ev,oos_pf=o.pf,oos_wr=o.wr))
pd.DataFrame(tops).to_csv(OUT/'LAB112_top_train_with_oos.csv',index=False)

# report key path and a priori representative configurations
atlas=pd.DataFrame(rows);rrdf=pd.DataFrame(rrrows);convdf=pd.DataFrame(conv)
lines=['# LAB112 — Z EVENT → ADVERSE EXCURSION → RECLAIM → FORWARD MFE/MAE','',
'Signal clock: fresh |Z|>=1, inverse crowd. No execution gate before the adverse/reclaim sequence.',
'Adverse excursion: price reaches 0.25/0.50/0.75/1.00 H1 ATR against signal within 24h.',
'Reclaim: first subsequent 5m close back through the original Z-signal anchor; hypothetical entry is next 5m open (causal).',
'Forward path from reclaim entry: 4/12/24/48h MFE, MAE, close displacement. R:R feasibility uses stop-first same-bar and TP >=1.5R.','']
for adv in ADVERSE_LEVELS:
    lines.append(f'## Adverse {adv:.2f} ATR')
    for rw in [4,12,24]:
        a=convdf[(convdf.split=='TRAIN')&(convdf.adverse_atr==adv)&(convdf.reclaim_window_h==rw)].iloc[0]
        b=convdf[(convdf.split=='OOS')&(convdf.adverse_atr==adv)&(convdf.reclaim_window_h==rw)].iloc[0]
        pa=atlas[(atlas.split=='TRAIN')&(atlas.adverse_atr==adv)&(atlas.reclaim_window_h==rw)&(atlas.horizon_h==48)].iloc[0]
        pb=atlas[(atlas.split=='OOS')&(atlas.adverse_atr==adv)&(atlas.reclaim_window_h==rw)&(atlas.horizon_h==48)].iloc[0]
        lines.append(f"- reclaim<={rw}h | TRAIN conversion={a.reclaim_rate_all:.1%}, delay={a.median_total_delay_h:.1f}h, 48h close={pa.mean_close:+.3f} ATR, MFE={pa.mean_mfe:.2f}, MAE={pa.mean_mae:.2f}, DNR={pa.dnr_std:+.3f} | OOS conversion={b.reclaim_rate_all:.1%}, delay={b.median_total_delay_h:.1f}h, close={pb.mean_close:+.3f}, MFE={pb.mean_mfe:.2f}, MAE={pb.mean_mae:.2f}, DNR={pb.dnr_std:+.3f}")
    lines.append('')

lines.append('## Representative RR feasibility (stop 0.75 ATR, TP 1.5R)')
for adv in ADVERSE_LEVELS:
    for rw in [4,12,24]:
        a=rrdf[(rrdf.split=='TRAIN')&(rrdf.adverse_atr==adv)&(rrdf.reclaim_window_h==rw)&(rrdf.stop_atr==0.75)&(rrdf.rr==1.5)].iloc[0]
        b=rrdf[(rrdf.split=='OOS')&(rrdf.adverse_atr==adv)&(rrdf.reclaim_window_h==rw)&(rrdf.stop_atr==0.75)&(rrdf.rr==1.5)].iloc[0]
        lines.append(f"- adv{adv:.2f}/reclaim{rw}h: TRAIN PF={a.pf:.2f} EV={a.ev:+.3f} N={int(a.n)} | OOS PF={b.pf:.2f} EV={b.ev:+.3f} N={int(b.n)}")
(OUT/'LAB112_REPORT.md').write_text('\n'.join(lines)+'\n')
meta=dict(signal='fresh |Z|>=1 inverse crowd',adverse_levels_atr=ADVERSE_LEVELS,reclaim_windows_h=RECLAIM_WINDOWS_H,
          reclaim='first 5m close back through original signal anchor; entry next 5m open',forward_h=FORWARD_H,
          rr_grid=dict(stop_atr=STOP_ATR,rr=RRS),caveat='descriptive grid; do not promote a configuration based on OOS; 2022 source coverage remains sparse')
(OUT/'LAB112_meta.json').write_text(json.dumps(meta,indent=2))
print('\n'.join(lines))
