#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab123_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
H=48
COSTS=[2.81,7.5]
SEARCH_BARS=72

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
        if not fs:raise RuntimeError(f'no csv in {zp}')
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

# Flow / Z / OI
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time']);rc=pick(f.columns,['count_long_short_ratio','ratio']);oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
f=f[[tc,rc,oic]].copy();f['time']=ptime(f[tc]);f['ratio']=pd.to_numeric(f[rc],errors='coerce');f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna().sort_values('time').drop_duplicates('time',keep='last');f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean();sd=f.ratio.rolling(72,min_periods=72).std(ddof=0)
f['z']=(f.ratio-mu)/sd.replace(0,np.nan)
f['dz_15']=f.z-f.z.shift(3)
f['dz_60']=f.z-f.z.shift(12)
f['oi4h']=f.oi/f.oi.shift(48)-1

# Price
r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']);po=pick(r.columns,['open']);ph=pick(r.columns,['high']);pl=pick(r.columns,['low']);pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# H1 context
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prev=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean()
h1['ema20']=h1.close.ewm(span=20,adjust=False).mean()
h1['ret4h']=h1.close/h1.close.shift(4)-1
h1['atr_med24']=h1.atr.rolling(24,min_periods=12).median()
h1['vol_expanding']=h1.atr>h1.atr_med24
h1['close_time']=h1.time+pd.Timedelta(hours=1)

# H4 trend
h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean();h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
h4['close_time']=h4.time+pd.Timedelta(hours=4)

# D1 trend
d1=p.set_index('time').resample('1D',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
d1['ema50']=d1.close.ewm(span=50,adjust=False).mean();d1['ema50_lag10']=d1.ema50.shift(10)
d1['trend']=np.where((d1.close>d1.ema50)&(d1.ema50>d1.ema50_lag10),1,np.where((d1.close<d1.ema50)&(d1.ema50<d1.ema50_lag10),-1,0))
d1['close_time']=d1.time+pd.Timedelta(days=1)

b=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','ret4h','vol_expanding']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
b=pd.merge_asof(b.sort_values('time'),h4[['close_time','trend']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
b=pd.merge_asof(b.sort_values('time'),d1[['close_time','trend']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_d1'))
b.rename(columns={'trend':'trend_h4','trend_d1':'trend_d1'},inplace=True)
b=pd.merge_asof(b.sort_values('time'),f[['time','z','dz_15','dz_60','oi4h']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b=b.dropna(subset=['atr','ret4h','vol_expanding','trend_h4','trend_d1','z','dz_15','dz_60','oi4h']).reset_index(drop=True)

# TRAIN frozen OI build threshold
trm=b.time<TRAIN_END
OI70=float(b.loc[trm,'oi4h'].quantile(.70))

BT=b.time.reset_index(drop=True);BO=b.open.to_numpy(float);BH=b.high.to_numpy(float);BL=b.low.to_numpy(float);BC=b.close.to_numpy(float);BA=b.atr.to_numpy(float);BZ=b.z.to_numpy(float)

# Event stages from absolute Z level + direction of crowd relative to trade side
# FOLLOW direction = same as sign(z); FADE direction = -sign(z)
STAGES=[
    ('EARLY_0_05',0.0,0.5),
    ('JOIN_05_10',0.5,1.0),
    ('MATURE_10_15',1.0,1.5),
    ('LATE_15_20',1.5,2.0),
    ('EXTREME_20P',2.0,np.inf),
]

def stage_of(z):
    a=abs(z)
    for n,lo,hi in STAGES:
        if a>=lo and a<hi:return n
    return None

# Fresh stage-entry event: abs(z) enters a higher bucket from below bucket lower bound.
events=[]
for i in range(1,len(b)-H*12-1):
    z=float(BZ[i]);pz=float(BZ[i-1]);stage=stage_of(z)
    if stage is None or z==0:continue
    # identify stage lower edge
    lo=next(x[1] for x in STAGES if x[0]==stage)
    if not(abs(z)>=lo and abs(pz)<lo):continue
    crowd_side=1 if z>0 else -1
    h4t=int(b.trend_h4.iloc[i]);d1t=int(b.trend_d1.iloc[i]);oi=float(b.oi4h.iloc[i]);atr=float(BA[i]);anchor=float(BC[i])
    price4h_side=np.sign(float(b.ret4h.iloc[i]))
    trend_align=(h4t==crowd_side and d1t==crowd_side)
    price_align=(price4h_side==crowd_side)
    oi_build=oi>=OI70
    vol_exp=bool(b.vol_expanding.iloc[i])
    dz_align=(np.sign(float(b.dz_60.iloc[i]))==crowd_side)
    for mode,side in [('FOLLOW',crowd_side),('FADE',-crowd_side)]:
        end=i+H*12
        hi=float(BH[i+1:end+1].max());lo_px=float(BL[i+1:end+1].min());cl=float(BC[end])
        mfe=(hi-anchor)/atr if side>0 else (anchor-lo_px)/atr
        mae=(anchor-lo_px)/atr if side>0 else (hi-anchor)/atr
        rows=dict(signal_i=i,time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',stage=stage,mode=mode,side=side,
                  z=z,trend_align=trend_align,price_align=price_align,oi_build=oi_build,vol_exp=vol_exp,dz_align=dz_align,
                  context_all=trend_align and price_align and oi_build and vol_exp and dz_align,
                  mfe48=mfe,mae48=mae,close48=side*(cl-anchor)/atr)
        # first passage +3/-1
        fp=0
        for j in range(i+1,end+1):
            fh=((BH[j]-anchor)>=3*atr) if side>0 else ((anchor-BL[j])>=3*atr)
            ah=((anchor-BL[j])>=1*atr) if side>0 else ((BH[j]-anchor)>=1*atr)
            if fh and ah:fp=0;break
            if fh:fp=1;break
            if ah:fp=-1;break
        rows['fp3_1']=fp
        events.append(rows)
ev=pd.DataFrame(events);ev.to_csv(OUT/'LAB123_lifecycle_events.csv',index=False)

def met(g):
    x=g.close48.to_numpy(float);mfe=g.mfe48.to_numpy(float);mae=g.mae48.to_numpy(float)
    return dict(n=len(g),mean_close=float(x.mean()),p_pos=float((x>0).mean()),mfe=float(mfe.mean()),mae=float(mae.mean()),
                mfe_mae=float(mfe.mean()/mae.mean()) if mae.mean()>0 else np.nan,
                p3_1=float((g.fp3_1==1).mean()))

# Atlas by stage/mode/context
atlas=[]
for split in ['TRAIN','OOS']:
    q=ev[ev.split==split]
    for stage in [x[0] for x in STAGES]:
        for mode in ['FOLLOW','FADE']:
            baseq=q[(q.stage==stage)&(q.mode==mode)]
            if len(baseq)>=30:atlas.append(dict(split=split,stage=stage,mode=mode,context='ALL',**met(baseq)))
            for cname,col in [('TREND_ALIGN','trend_align'),('TREND_PRICE_OI','trend_align'),('FULL_CONTEXT','context_all')]:
                if cname=='TREND_PRICE_OI':
                    g=baseq[baseq.trend_align&baseq.price_align&baseq.oi_build]
                else:g=baseq[baseq[col]]
                if len(g)>=20:atlas.append(dict(split=split,stage=stage,mode=mode,context=cname,**met(g)))
at=pd.DataFrame(atlas);at.to_csv(OUT/'LAB123_stage_atlas.csv',index=False)

# Direct comparison FOLLOW minus FADE on same event population for contexts
pairs=[]
for split in ['TRAIN','OOS']:
    for stage in [x[0] for x in STAGES]:
        for ctx in ['ALL','TREND_ALIGN','TREND_PRICE_OI','FULL_CONTEXT']:
            frow=at[(at.split==split)&(at.stage==stage)&(at.mode=='FOLLOW')&(at.context==ctx)]
            arow=at[(at.split==split)&(at.stage==stage)&(at.mode=='FADE')&(at.context==ctx)]
            if len(frow) and len(arow):
                fr=frow.iloc[0];ar=arow.iloc[0]
                pairs.append(dict(split=split,stage=stage,context=ctx,n=min(int(fr.n),int(ar.n)),
                                  follow_close=fr.mean_close,fade_close=ar.mean_close,delta_close=fr.mean_close-ar.mean_close,
                                  follow_p3_1=fr.p3_1,fade_p3_1=ar.p3_1,delta_p3_1=fr.p3_1-ar.p3_1))
pd.DataFrame(pairs).to_csv(OUT/'LAB123_follow_vs_fade.csv',index=False)

# Tradable FOLLOW candidate: same-direction H4+D1, price aligned, OI build, volatility expanding, crowd acceleration aligned.
# M5 swing3 break in crowd direction. Evaluate 1ATR/3R.
def swing3_entry(i,side):
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:return j+1
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:return j+1
    return None
def sim(ei,side,atr,cost):
    entry=float(BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+H*12-1,len(b)-1)
    gross=side*(BC[end]-entry)/atr;reason='TIME';xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
        if hs:gross=-1;reason='SL';xi=j;break
        if ht:gross=3;reason='TP';xi=j;break
    return gross-(cost/10000.0)*entry/atr,reason,xi

trad=[]
for _,r in ev[(ev.mode=='FOLLOW')&ev.context_all].iterrows():
    # only early+join+mature candidate stages, not late/extreme
    if r.stage not in ['EARLY_0_05','JOIN_05_10','MATURE_10_15']:continue
    ei=swing3_entry(int(r.signal_i),int(r.side))
    if ei is None:continue
    trad.append(dict(stage=r.stage,split=r['split'],signal_time=r.time,entry_i=ei,entry_time=BT.iloc[ei],side=int(r.side),atr=float(BA[int(r.signal_i)])))
tr=pd.DataFrame(trad);tr.to_csv(OUT/'LAB123_follow_trade_candidates.csv',index=False)

summ=[]
if len(tr):
  for cost in COSTS:
    for stages_name,stages in {
        'EARLY':['EARLY_0_05'],
        'JOIN':['JOIN_05_10'],
        'MATURE':['MATURE_10_15'],
        'EARLY_JOIN':['EARLY_0_05','JOIN_05_10'],
        'ALL_EARLY_MATURE':['EARLY_0_05','JOIN_05_10','MATURE_10_15']
    }.items():
      s=tr[tr.stage.isin(stages)].sort_values('entry_time')
      open_until=pd.Timestamp.min.tz_localize('UTC');rows=[]
      for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi=sim(int(r.entry_i),int(r.side),float(r.atr),cost)
        open_until=BT.iloc[xi]
        rows.append(dict(split=r['split'],net_r=net,reason=reason,entry_time=r.entry_time,exit_time=BT.iloc[xi]))
      t=pd.DataFrame(rows)
      if t.empty:continue
      months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
      for split in ['ALL','TRAIN','OOS']:
        q=t if split=='ALL' else t[t.split==split]
        if q.empty:continue
        pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
        summ.append(dict(portfolio=stages_name,cost_bps=cost,split=split,n=len(q),ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                         wr=float((q.net_r>0).mean()),total_r=float(q.net_r.sum()),trades_month=(len(t)/months if split=='ALL' else np.nan),
                         r_month=(t.net_r.sum()/months if split=='ALL' else np.nan)))
sm=pd.DataFrame(summ);sm.to_csv(OUT/'LAB123_follow_execution.csv',index=False)

lines=['# LAB123 — CROWD LIFECYCLE: FOLLOW → FADE','',
'Goal: determine whether crowd direction should be followed early and faded late.',
'Stages are frozen by |Z|: EARLY 0→0.5, JOIN 0.5→1, MATURE 1→1.5, LATE 1.5→2, EXTREME >=2. Fresh stage-entry events only.',
'FOLLOW = trade in sign(Z); FADE = trade opposite sign(Z). Context uses causal H4+D1 alignment, 4h price direction, OI build, volatility expansion, and 60m Z acceleration.',
f'OI build threshold is TRAIN q70={OI70:+.3%}. Atlas is descriptive; execution candidate uses SWING3_BREAK, SL1 H1 ATR, TP3R, 48h.',
'Development OOS has been repeatedly inspected; do not treat it as pristine validation.','']

for ctx in ['ALL','TREND_ALIGN','TREND_PRICE_OI','FULL_CONTEXT']:
    lines.append(f'## {ctx}')
    for stage in [x[0] for x in STAGES]:
        for split in ['TRAIN','OOS']:
            fr=at[(at.split==split)&(at.stage==stage)&(at.mode=='FOLLOW')&(at.context==ctx)]
            ar=at[(at.split==split)&(at.stage==stage)&(at.mode=='FADE')&(at.context==ctx)]
            if len(fr) and len(ar):
                f0=fr.iloc[0];a0=ar.iloc[0]
                lines.append(f"- {split} {stage}: FOLLOW N={int(f0.n)} close={f0.mean_close:+.3f}ATR +3/-1={f0.p3_1:.1%} | FADE close={a0.mean_close:+.3f} +3/-1={a0.p3_1:.1%}")
    lines.append('')

if len(sm):
    lines.append('## FOLLOW execution candidates')
    for cost in COSTS:
        lines.append(f'### Cost {cost} bps')
        for pname in ['EARLY','JOIN','MATURE','EARLY_JOIN','ALL_EARLY_MATURE']:
            a=sm[(sm.portfolio==pname)&(sm.cost_bps==cost)&(sm.split=='ALL')]
            o=sm[(sm.portfolio==pname)&(sm.cost_bps==cost)&(sm.split=='OOS')]
            if len(a):
                aa=a.iloc[0];extra=''
                if len(o):
                    oo=o.iloc[0];extra=f" | OOS N={int(oo.n)} EV={oo.ev:+.3f} PF={oo.pf:.2f}"
                lines.append(f"- {pname}: N={int(aa.n)} ({aa.trades_month:.2f}/mo) EV={aa.ev:+.3f} PF={aa.pf:.2f} R/mo={aa.r_month:+.2f}{extra}")
        lines.append('')

(OUT/'LAB123_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB123_meta.json').write_text(json.dumps(dict(
    stages={x[0]:[x[1],None if np.isinf(x[2]) else x[2]] for x in STAGES},
    follow='same as sign(Z)',fade='opposite sign(Z)',oi70=OI70,
    full_context='H4+D1 aligned with crowd + 4h price aligned + OI build + vol expanding + dz60 aligned',
    execution='SWING3_BREAK, next M5 open, SL1 H1 ATR, TP3R, 48h',
    caveat='development OOS repeatedly inspected; follow execution is exploratory'
),indent=2))
print('\n'.join(lines))
