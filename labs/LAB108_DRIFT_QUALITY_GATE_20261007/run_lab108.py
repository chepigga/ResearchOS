#!/usr/bin/env python3
from __future__ import annotations
import math,re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab108_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
STOP_MULT=3.5
HOLD_H=48
MAX_OPEN=3
COST_PRIMARY=2.81
COST_STRESS=7.5
RIDGE_ALPHA=10.0
RETAIN_FRACS=[1.00,0.85,0.75,0.65,0.55,0.45]

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

# ---------- data ----------
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
for c,nm in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[nm]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# H1 ATR14 + trend state
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
prev=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
h1['atr_h1']=tr.rolling(14,min_periods=14).mean()
h1['ema50']=h1.close.ewm(span=50,adjust=False).mean()
h1['ema50_lag4']=h1.ema50.shift(4)
h1['trend_h1']=np.where((h1.close>h1.ema50)&(h1.ema50>h1.ema50_lag4),1,np.where((h1.close<h1.ema50)&(h1.ema50<h1.ema50_lag4),-1,0))
h1['close_time']=h1.time+pd.Timedelta(hours=1)

# H4 trend state
h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean()
h4['ema50_lag4']=h4.ema50.shift(4)
h4['trend_h4']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag4),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag4),-1,0))
h4['close_time']=h4.time+pd.Timedelta(hours=4)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1','trend_h1']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),h4[['close_time','trend_h4']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
base=pd.merge_asof(base.sort_values('time'),flow[['time','z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['z','atr_h1','trend_h1','trend_h4']).reset_index(drop=True)

m30=base.set_index('time').resample('30min',label='left',closed='left').agg(
    open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),z=('z','last'),atr_h1=('atr_h1','last')
).dropna().reset_index()
m30['close_time']=m30.time+pd.Timedelta(minutes=30)

B_OPEN=base.open.to_numpy(float); B_HIGH=base.high.to_numpy(float); B_LOW=base.low.to_numpy(float); B_CLOSE=base.close.to_numpy(float); B_ATR=base.atr_h1.to_numpy(float)
zv=base.z.to_numpy(float)

# fresh |Z|>=1 episodes
eps=[]
for i in range(1,len(base)-1):
    if abs(zv[i])>=1.0 and abs(zv[i-1])<1.0:
        eps.append(dict(si=i,side=-1 if zv[i]>0 else 1,z_setup=float(zv[i]),setup_time=base.time.iloc[i]))

def struct4_entry(ep):
    si=ep['si']; side=ep['side']; t0=base.time.iloc[si]
    k0=int(m30.close_time.searchsorted(t0,side='right'))
    for k in range(max(4,k0),min(k0+8,len(m30)-1)):
        hi=float(m30.high.iloc[k-4:k].max()); lo=float(m30.low.iloc[k-4:k].min())
        c=float(m30.close.iloc[k]); o=float(m30.open.iloc[k]); h=float(m30.high.iloc[k]); l=float(m30.low.iloc[k])
        level=hi if side>0 else lo
        if (c>hi if side>0 else c<lo):
            et=m30.time.iloc[k+1]
            ei=int(base.time.searchsorted(et,side='left'))
            if ei<len(base)-1:
                return dict(ei=ei,k=k,level=level,trig_o=o,trig_h=h,trig_l=l,trig_c=c)
    return None

cands=[]
for ep in eps:
    s=struct4_entry(ep)
    if s is None:continue
    ei=s['ei']; side=ep['side']; entry=float(B_OPEN[ei]); atr=float(B_ATR[ei])
    if not np.isfinite(atr) or atr<=0:continue
    z_entry=float(base.z.iloc[ei])
    tr1=int(base.trend_h1.iloc[ei]); tr4=int(base.trend_h4.iloc[ei])
    rng=max(1e-12,s['trig_h']-s['trig_l']); body=abs(s['trig_c']-s['trig_o'])
    cands.append(dict(
        ei=ei,entry_time=base.time.iloc[ei],side=side,z_setup=ep['z_setup'],setup_time=ep['setup_time'],
        break_level=s['level'],abs_z_setup=abs(ep['z_setup']),abs_z_entry=abs(z_entry),
        delta_abs_z=abs(z_entry)-abs(ep['z_setup']),
        break_strength=(side*(s['trig_c']-s['level']))/atr,
        trigger_body_h1=body/atr,trigger_body_range=body/rng,
        entry_extension=(side*(entry-s['level']))/atr,
        episode_age_h=(base.time.iloc[ei]-ep['setup_time']).total_seconds()/3600.0,
        trend_h1=tr1,trend_h4=tr4,trend_align=int(tr1==tr4 and tr1!=0),trend_with_side_h1=int(tr1==side),trend_with_side_h4=int(tr4==side),
        vol_pct=atr/entry,side_num=side
    ))
cands=sorted(cands,key=lambda x:x['ei'])

# independent candidate outcome at H48
for r in cands:
    ei=r['ei']; side=r['side']; entry=B_OPEN[ei]; atr=B_ATR[ei]; stop=entry-side*STOP_MULT*atr
    end=min(ei+HOLD_H*12,len(base)-1)
    hh=B_HIGH[ei:end+1]; ll=B_LOW[ei:end+1]
    hit=((ll<=stop) if side>0 else (hh>=stop)); ix=np.flatnonzero(hit)
    if len(ix):
        exi=ei+int(ix[0]); exit_px=stop; reason='SL'
    else:
        exi=end; exit_px=B_CLOSE[exi]; reason='TIME48'
    gross=side*(exit_px-entry)/(STOP_MULT*atr)
    cost_r=(entry*(COST_PRIMARY/10000.0))/(STOP_MULT*atr)
    r.update(entry=float(entry),atr=float(atr),stop=float(stop),exi=int(exi),exit_time=base.time.iloc[exi],
             gross_r=float(gross),net_r_ind=float(gross-cost_r),reason=reason)

df=pd.DataFrame(cands)
df['split']=np.where(pd.to_datetime(df.entry_time,utc=True)<TRAIN_END,'TRAIN','OOS')
df['year']=pd.to_datetime(df.entry_time,utc=True).dt.year

FEATURES=['abs_z_setup','abs_z_entry','delta_abs_z','break_strength','trigger_body_h1','trigger_body_range',
          'entry_extension','episode_age_h','trend_h1','trend_h4','trend_align','trend_with_side_h1','trend_with_side_h4','vol_pct','side_num']

# ---------- ridge helpers ----------
def fit_ridge(train):
    X=train[FEATURES].to_numpy(float); y=train.net_r_ind.to_numpy(float)
    mu=X.mean(axis=0); sd=X.std(axis=0); sd[sd<1e-12]=1.0
    Z=(X-mu)/sd
    Z=np.column_stack([np.ones(len(Z)),Z])
    I=np.eye(Z.shape[1]); I[0,0]=0
    beta=np.linalg.solve(Z.T@Z + RIDGE_ALPHA*I, Z.T@y)
    return mu,sd,beta
def pred(model,frame):
    mu,sd,beta=model; X=frame[FEATURES].to_numpy(float); Z=(X-mu)/sd; Z=np.column_stack([np.ones(len(Z)),Z]); return Z@beta

train=df[df.split=='TRAIN'].copy()
oos=df[df.split=='OOS'].copy()

# leave-one-year-out OOF scores on TRAIN
train['score_oof']=np.nan
years=sorted(train.year.unique())
for y in years:
    tr=train[train.year!=y]; va=train[train.year==y]
    model=fit_ridge(tr)
    train.loc[va.index,'score_oof']=pred(model,va)

# capacity sim from candidate frame, score gate
def simulate(frame,score_col,cutoff,cost_bps):
    q=frame.sort_values('entry_time')
    rows=[]; active=[]
    for _,r in q.iterrows():
        if float(r[score_col]) < cutoff: continue
        ei=int(r.ei); side=int(r.side)
        active=[a for a in active if a[0]>=ei]
        if len(active)>=MAX_OPEN: continue
        entry=float(r.entry); atr=float(r.atr)
        cost_r=(entry*(cost_bps/10000.0))/(STOP_MULT*atr)
        net=float(r.gross_r)-cost_r
        rows.append(dict(entry_time=r.entry_time,exit_time=r.exit_time,side='BUY' if side>0 else 'SELL',
                         score=float(r[score_col]),gross_r=float(r.gross_r),net_r=net,reason=r.reason,
                         z_setup=float(r.z_setup),break_strength=float(r.break_strength),abs_z_entry=float(r.abs_z_entry),
                         trend_h1=int(r.trend_h1),trend_h4=int(r.trend_h4),ei=ei,exi=int(r.exi)))
        active.append((int(r.exi),side))
    return pd.DataFrame(rows)

def metrics(q):
    if len(q)==0:return dict(n=0,ev=np.nan,pf=np.nan,t=np.nan,wr=np.nan,dd=np.nan,se=np.nan,trades_month=np.nan,r_month=np.nan)
    x=q.net_r.to_numpy(float); sd=float(x.std(ddof=1)) if len(x)>1 else np.nan
    se=sd/math.sqrt(len(x)) if len(x)>1 and sd>0 else np.nan
    tt=float(x.mean()/se) if np.isfinite(se) and se>0 else np.nan
    pos=x[x>0].sum(); neg=-x[x<0].sum()
    eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=float(np.max(pk[1:]-eq))
    t=pd.to_datetime(q.entry_time,utc=True); months=max(1,(t.max().year-t.min().year)*12+t.max().month-t.min().month+1)
    return dict(n=len(q),ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,t=tt,wr=float((x>0).mean()),dd=dd,se=se,
                trades_month=len(q)/months,r_month=float(x.sum())/months)

# TRAIN OOF selection across retention fractions
selrows=[]
for frac in RETAIN_FRACS:
    cutoff=-np.inf if frac>=0.999 else float(train.score_oof.quantile(1-frac))
    q=simulate(train,'score_oof',cutoff,COST_PRIMARY)
    m=metrics(q)
    selrows.append(dict(retain_frac=frac,cutoff_oof=cutoff,**m))
sel=pd.DataFrame(selrows)
sel.to_csv(OUT/'LAB108_train_oof_grid.csv',index=False)

# Primary selection: meet user's quality target if possible, keep >=30 trades/month.
eligible=sel[(sel.ev>0.10)&(sel.pf>=1.30)&(sel.trades_month>=30)]
if len(eligible):
    chosen=eligible.sort_values(['pf','ev','r_month'],ascending=[False,False,False]).iloc[0]
    selection_reason='PASS_TARGETS'
else:
    eligible2=sel[(sel.ev>0)&(sel.trades_month>=30)]
    chosen=(eligible2 if len(eligible2) else sel).sort_values(['pf','ev','r_month'],ascending=[False,False,False]).iloc[0]
    selection_reason='BEST_AVAILABLE'

retain=float(chosen.retain_frac)

# Refit on all TRAIN, calibrate absolute cutoff using TRAIN full-model score distribution only.
model=fit_ridge(train)
train['score_full']=pred(model,train); oos['score_full']=pred(model,oos)
full_cutoff=-np.inf if retain>=0.999 else float(train.score_full.quantile(1-retain))

# report baseline + selected at primary/stress costs
summary=[]
trade_ledgers=[]
for label,cut in [('BASELINE',-np.inf),('QUALITY_GATE',full_cutoff)]:
  for cost in [COST_PRIMARY,COST_STRESS]:
    for split,frame in [('TRAIN',train),('OOS',oos)]:
        q=simulate(frame,'score_full',cut,cost)
        if len(q): q['label']=label; q['cost_bps']=cost; q['split']=split; trade_ledgers.append(q)
        summary.append(dict(label=label,cost_bps=cost,split=split,cutoff=cut,retain_frac=(1.0 if label=='BASELINE' else retain),**metrics(q)))
summary=pd.DataFrame(summary)
summary.to_csv(OUT/'LAB108_summary.csv',index=False)
pd.concat(trade_ledgers,ignore_index=True).to_csv(OUT/'LAB108_trades_selected.csv',index=False)

# coefficient report
coef=pd.DataFrame({'feature':['INTERCEPT']+FEATURES,'coef_std':model[2]})
coef['abs_coef']=coef.coef_std.abs()
coef.sort_values('abs_coef',ascending=False).to_csv(OUT/'LAB108_model_coefficients.csv',index=False)

# univariate quartile diagnostics, TRAIN only, independent candidates (not capacity simulation)
diag=[]
for f in FEATURES:
    try:
        bins=pd.qcut(train[f],4,duplicates='drop')
    except Exception:
        continue
    for b,g in train.groupby(bins,observed=True):
        x=g.net_r_ind.to_numpy(float)
        diag.append(dict(feature=f,bucket=str(b),n=len(g),ev=float(x.mean()),wr=float((x>0).mean())))
pd.DataFrame(diag).to_csv(OUT/'LAB108_univariate_train.csv',index=False)

# yearly selected at primary cost
yr=[]
for split,frame in [('TRAIN',train),('OOS',oos)]:
    q=simulate(frame,'score_full',full_cutoff,COST_PRIMARY)
    if len(q):
        q['year']=pd.to_datetime(q.entry_time,utc=True).dt.year
        for y,g in q.groupby('year'): yr.append(dict(split=split,year=int(y),**metrics(g)))
pd.DataFrame(yr).to_csv(OUT/'LAB108_selected_yearly.csv',index=False)

meta=dict(
    parent='LAB107A H48 / max_open=3 / ANY',
    features=FEATURES,ridge_alpha=RIDGE_ALPHA,retain_fracs=RETAIN_FRACS,
    selection='leave-one-year-out OOF on TRAIN 2021-2024; OOS untouched; choose PF>=1.30 EV>0.10 trades/month>=30 if available',
    chosen_retain_frac=retain,selection_reason=selection_reason,full_train_cutoff=full_cutoff,
    costs_bps=[COST_PRIMARY,COST_STRESS]
)
(OUT/'LAB108_meta.json').write_text(json.dumps(meta,indent=2))

lines=['# LAB108 — DRIFT QUALITY GATE','',
       'Parent frozen: LAB107A H48 / max 3 concurrent / ANY direction / SL 3.5 H1 ATR.',
       'Quality model uses only information known by entry. Ridge alpha fixed at 10. TRAIN scored by leave-one-year-out OOF; threshold chosen on TRAIN only; OOS untouched.',
       f"Chosen retain fraction={retain:.0%} ({selection_reason}).",'']
for cost in [COST_PRIMARY,COST_STRESS]:
    lines.append(f'## Cost {cost:.2f} bps')
    for split in ['TRAIN','OOS']:
        b=summary[(summary.label=='BASELINE')&(summary.cost_bps==cost)&(summary.split==split)].iloc[0]
        g=summary[(summary.label=='QUALITY_GATE')&(summary.cost_bps==cost)&(summary.split==split)].iloc[0]
        lines.append(f"- {split} BASE: N={int(b.n)} EV={b.ev:+.3f} PF={b.pf:.2f} t={b.t:.2f} DD={b.dd:.1f}R trades/mo={b.trades_month:.1f} R/mo={b.r_month:+.2f}")
        lines.append(f"- {split} GATE: N={int(g.n)} EV={g.ev:+.3f} PF={g.pf:.2f} t={g.t:.2f} DD={g.dd:.1f}R trades/mo={g.trades_month:.1f} R/mo={g.r_month:+.2f}")
    lines.append('')
lines+=['## Top standardized coefficients']
for _,r in coef[coef.feature!='INTERCEPT'].sort_values('abs_coef',ascending=False).head(8).iterrows():
    lines.append(f"- {r.feature}: {r.coef_std:+.4f}")
(OUT/'LAB108_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
