#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
spec=importlib.util.spec_from_file_location("lab124",SRC)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OUT=Path("lab126_out"); OUT.mkdir(exist_ok=True)
TRAIN_END=m.TRAIN_END
b=m.b.copy()
p=m.p.copy()
BT=m.BT; BO=m.BO; BH=m.BH; BL=m.BL; BC=m.BC; BA=m.BA; BZ=m.BZ
COSTS=[2.81,7.5]
SEARCH_BARS=72
HOLDS=[12,24,48]
TPS=[1.5,2.0,3.0]
SLS=[1.0,1.5]

# ----- add D1 trend and causal H1 volatility regime -----
d1=p.set_index('time').resample('1D',label='left',closed='left').agg(
    open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')
).dropna().reset_index()
d1['ema50']=d1.close.ewm(span=50,adjust=False).mean()
d1['ema50_lag10']=d1.ema50.shift(10)
d1['trend_d1']=np.where(
    (d1.close>d1.ema50)&(d1.ema50>d1.ema50_lag10),1,
    np.where((d1.close<d1.ema50)&(d1.ema50<d1.ema50_lag10),-1,0)
)
d1['close_time_d1']=d1.time+pd.Timedelta(days=1)

h1=m.h1.copy()
# Causal 60-day ATR median (1440 H1 bars) as a simple low-vol regime gate.
h1['atr_med60d']=h1.atr.shift(1).rolling(24*60,min_periods=24*20).median()
h1['low_vol']=h1.atr<h1.atr_med60d
h1['close_time_vol']=h1.time+pd.Timedelta(hours=1)

ctx=b[['time']].copy()
ctx=pd.merge_asof(ctx.sort_values('time'),
                  d1[['close_time_d1','trend_d1']].dropna().sort_values('close_time_d1'),
                  left_on='time',right_on='close_time_d1',direction='backward')
ctx=pd.merge_asof(ctx.sort_values('time'),
                  h1[['close_time_vol','low_vol']].dropna().sort_values('close_time_vol'),
                  left_on='time',right_on='close_time_vol',direction='backward')
b['trend_d1']=ctx.trend_d1.values
b['low_vol']=ctx.low_vol.fillna(False).values

# ----- fresh |Z|>=1 inverse-crowd continuation universe -----
events=[]
last=len(b)-48*12-2
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1): continue
    side=-1 if BZ[i]>0 else 1
    h4t=int(b.trend.iloc[i])
    if h4t==0 or side!=h4t: continue
    events.append(dict(
        signal_i=i, signal_time=BT.iloc[i],
        split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',
        side=side, atr=float(BA[i]),
        h4d1=(int(b.trend_d1.iloc[i])==side),
        low_vol=bool(b.low_vol.iloc[i]),
        abs_z=abs(float(BZ[i]))
    ))
ev=pd.DataFrame(events)
ev.to_csv(OUT/'LAB126_universe.csv',index=False)

def entry_market(i,side,atr):
    return i+1

def entry_pullback(i,side,atr,thr):
    anchor=float(BC[i])
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        hit=(BL[j] <= anchor-thr*atr) if side>0 else (BH[j] >= anchor+thr*atr)
        if hit:return j+1
    return None

def entry_failed_countertrend(i,side,atr,thr):
    anchor=float(BC[i]); adverse=False
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        if side>0:
            if BL[j] <= anchor-thr*atr: adverse=True
            if adverse and BC[j] > anchor: return j+1
        else:
            if BH[j] >= anchor+thr*atr: adverse=True
            if adverse and BC[j] < anchor: return j+1
    return None

ENTRY_METHODS={
    'MARKET_Z':lambda i,s,a:entry_market(i,s,a),
    'PULLBACK_025':lambda i,s,a:entry_pullback(i,s,a,.25),
    'PULLBACK_050':lambda i,s,a:entry_pullback(i,s,a,.50),
    'FAILED_CT_025':lambda i,s,a:entry_failed_countertrend(i,s,a,.25),
    'FAILED_CT_050':lambda i,s,a:entry_failed_countertrend(i,s,a,.50),
}

entries=[]
for _,r in ev.iterrows():
    i=int(r.signal_i); side=int(r.side); atr=float(r.atr)
    for name,fn in ENTRY_METHODS.items():
        ei=fn(i,side,atr)
        if ei is None:continue
        entries.append(dict(
            method=name,signal_i=i,entry_i=ei,signal_time=r.signal_time,
            entry_time=BT.iloc[ei],split=r['split'],side=side,atr=atr,
            h4d1=bool(r.h4d1),low_vol=bool(r.low_vol),abs_z=float(r.abs_z),
            delay_min=(BT.iloc[ei]-BT.iloc[i]).total_seconds()/60.0,
            entry_delta_atr=side*(float(BO[ei])-float(BC[i]))/atr
        ))
en=pd.DataFrame(entries)
en.to_csv(OUT/'LAB126_entries.csv',index=False)

def sim_one(ei,side,atr,sl_atr,tp_r,hold_h,cost):
    entry=float(BO[ei]);dist=sl_atr*atr
    sl=entry-side*dist;tp=entry+side*tp_r*dist
    end=min(ei+hold_h*12-1,len(b)-1)
    gross=side*(BC[end]-entry)/dist;reason='TIME';xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
        if hs:gross=-1;reason='SL';xi=j;break
        if ht:gross=tp_r;reason='TP';xi=j;break
    return float(gross-(cost/10000.0)*entry/dist),reason,xi

CONTEXTS={
    'H4_ONLY':lambda d:pd.Series(True,index=d.index),
    'H4_D1':lambda d:d.h4d1,
    'H4_LOWVOL':lambda d:d.low_vol,
    'H4_D1_LOWVOL':lambda d:d.h4d1 & d.low_vol,
}

summary=[]; alltr=[]
for cost in COSTS:
  for method in ENTRY_METHODS:
    em=en[en.method==method].copy()
    for ctxname,ctxfn in CONTEXTS.items():
      s=em[ctxfn(em)].sort_values('entry_time')
      if s.empty:continue
      for sl_atr in SLS:
        for tp_r in TPS:
          for hold_h in HOLDS:
            open_until=pd.Timestamp.min.tz_localize('UTC');rows=[];eq=[];cum=0.0
            for _,r in s.iterrows():
                if r.entry_time<open_until:continue
                net,reason,xi=sim_one(int(r.entry_i),int(r.side),float(r.atr),sl_atr,tp_r,hold_h,cost)
                start=cum;entry=float(BO[int(r.entry_i)]);dist=sl_atr*float(r.atr)
                for j in range(int(r.entry_i),xi+1):
                    mtm=int(r.side)*(BC[j]-entry)/dist-(cost/10000.0)*entry/dist
                    if j==xi: mtm=net
                    eq.append((BT.iloc[j],start+mtm))
                cum+=net;open_until=BT.iloc[xi]
                rows.append(dict(cost_bps=cost,method=method,context=ctxname,sl_atr=sl_atr,tp_r=tp_r,hold_h=hold_h,
                                 split=r['split'],signal_time=r.signal_time,entry_time=r.entry_time,exit_time=BT.iloc[xi],
                                 side='BUY' if r.side>0 else 'SELL',net_r=net,reason=reason,
                                 delay_min=r.delay_min,entry_delta_atr=r.entry_delta_atr))
            t=pd.DataFrame(rows)
            if t.empty:continue
            alltr.append(t)
            ep=pd.DataFrame(eq,columns=['time','equity']).sort_values('time').drop_duplicates('time',keep='last')
            maxdd=float((ep.equity.cummax()-ep.equity).max())
            months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
            for split in ['ALL','TRAIN','OOS']:
                q=t if split=='ALL' else t[t.split==split]
                if q.empty:continue
                pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
                summary.append(dict(cost_bps=cost,method=method,context=ctxname,sl_atr=sl_atr,tp_r=tp_r,hold_h=hold_h,
                                    split=split,n=len(q),ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                                    wr=float((q.net_r>0).mean()),total_r=float(q.net_r.sum()),
                                    trades_month=(len(t)/months if split=='ALL' else np.nan),
                                    r_month=(t.net_r.sum()/months if split=='ALL' else np.nan),
                                    maxdd_r=(maxdd if split=='ALL' else np.nan),
                                    tp_rate=float((q.reason=='TP').mean()),sl_rate=float(q.reason.isin(['SL','BOTH_STOP_FIRST']).mean()),
                                    time_rate=float((q.reason=='TIME').mean())))
sm=pd.DataFrame(summary)
sm.to_csv(OUT/'LAB126_grid_summary.csv',index=False)
pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB126_trades.csv',index=False)

# TRAIN-only ranking; OOS shown only after selection. Require N>=80 TRAIN to avoid tiny samples.
rank=sm[(sm.cost_bps==2.81)&(sm.split=='TRAIN')&(sm.n>=80)].copy()
rank['score_train']=rank.ev.clip(lower=-2,upper=2)+0.15*np.log(rank.pf.clip(lower=.1,upper=10))
rank=rank.sort_values(['score_train','pf','n'],ascending=False)
rank.to_csv(OUT/'LAB126_train_ranking.csv',index=False)

sel=[]
for _,r in rank.head(15).iterrows():
    o=sm[(sm.cost_bps==2.81)&(sm.split=='OOS')&
         (sm.method==r.method)&(sm.context==r.context)&
         (sm.sl_atr==r.sl_atr)&(sm.tp_r==r.tp_r)&(sm.hold_h==r.hold_h)]
    a=sm[(sm.cost_bps==2.81)&(sm.split=='ALL')&
         (sm.method==r.method)&(sm.context==r.context)&
         (sm.sl_atr==r.sl_atr)&(sm.tp_r==r.tp_r)&(sm.hold_h==r.hold_h)]
    d=dict(method=r.method,context=r.context,sl_atr=r.sl_atr,tp_r=r.tp_r,hold_h=int(r.hold_h),
           train_n=int(r.n),train_ev=r.ev,train_pf=r.pf)
    if len(o):
        oo=o.iloc[0];d.update(oos_n=int(oo.n),oos_ev=oo.ev,oos_pf=oo.pf)
    if len(a):
        aa=a.iloc[0];d.update(all_n=int(aa.n),trades_month=aa.trades_month,r_month=aa.r_month,maxdd_r=aa.maxdd_r)
    sel.append(d)
pd.DataFrame(sel).to_csv(OUT/'LAB126_top_train_selected.csv',index=False)

# Entry-method anatomy before SL/TP, descriptive 24h path.
atlas=[]
for method in ENTRY_METHODS:
    q=en[en.method==method]
    for ctxname,ctxfn in CONTEXTS.items():
        qq=q[ctxfn(q)]
        for split in ['TRAIN','OOS']:
            z=qq[qq.split==split]
            if len(z)<20:continue
            vals=[]
            for _,r in z.iterrows():
                ei=int(r.entry_i);end=min(ei+24*12,len(b)-1);side=int(r.side);atr=float(r.atr);entry=float(BO[ei])
                close=side*(BC[end]-entry)/atr
                hi=(max(BH[ei:end+1])-entry)/atr if side>0 else (entry-min(BL[ei:end+1]))/atr
                lo=(entry-min(BL[ei:end+1]))/atr if side>0 else (max(BH[ei:end+1])-entry)/atr
                vals.append((close,hi,lo))
            a=np.asarray(vals,float)
            atlas.append(dict(method=method,context=ctxname,split=split,n=len(z),
                              mean24=float(a[:,0].mean()),mfe24=float(a[:,1].mean()),mae24=float(a[:,2].mean()),
                              delay_med=float(z.delay_min.median()),entry_delta_med=float(z.entry_delta_atr.median())))
pd.DataFrame(atlas).to_csv(OUT/'LAB126_entry_atlas.csv',index=False)

lines=['# LAB126 — ANTI-CROWD TREND CONTINUATION / FAILED COUNTERTREND','',
       'Universe: fresh |Z|>=1 where inverse-crowd side equals causal H4 trend. No capitulation extension/OI gate.',
       'Contexts: H4 only; H4+D1 aligned; H4 low-vol; H4+D1 low-vol.',
       'Entries: MARKET_Z, PULLBACK 0.25/0.50 H1 ATR, FAILED_COUNTERTREND 0.25/0.50 ATR then reclaim of signal anchor.',
       'Execution grid: SL 1.0/1.5 H1 ATR, TP 1.5/2/3R, hold 12/24/48h, one position, stop-first same-bar, costs 2.81/7.5bps.',
       'Ranking uses TRAIN only (minimum TRAIN N=80). OOS is displayed only after ranking; historical OOS is development OOS, not pristine validation.','']

lines.append('## Top TRAIN-selected configurations @2.81bps')
for d in sel[:12]:
    extra=''
    if 'oos_n' in d:extra=f" | OOS N={d['oos_n']} EV={d['oos_ev']:+.3f} PF={d['oos_pf']:.2f}"
    lines.append(f"- {d['method']} / {d['context']} / SL{d['sl_atr']:.1f} / TP{d['tp_r']:.1f}R / {d['hold_h']}h: TRAIN N={d['train_n']} EV={d['train_ev']:+.3f} PF={d['train_pf']:.2f}{extra} | {d.get('trades_month',float('nan')):.2f}/mo")
lines.append('')

# Best by method among TRAIN-ranked
lines.append('## Best per entry method (TRAIN-selected)')
for method in ENTRY_METHODS:
    rr=rank[rank.method==method]
    if rr.empty:continue
    r=rr.iloc[0]
    o=sm[(sm.cost_bps==2.81)&(sm.split=='OOS')&(sm.method==method)&(sm.context==r.context)&(sm.sl_atr==r.sl_atr)&(sm.tp_r==r.tp_r)&(sm.hold_h==r.hold_h)]
    extra=''
    if len(o):
        oo=o.iloc[0];extra=f" | OOS N={int(oo.n)} EV={oo.ev:+.3f} PF={oo.pf:.2f}"
    lines.append(f"- {method}: {r.context}, SL{r.sl_atr:.1f}, TP{r.tp_r:.1f}R, {int(r.hold_h)}h | TRAIN N={int(r.n)} EV={r.ev:+.3f} PF={r.pf:.2f}{extra}")
lines.append('')

(OUT/'LAB126_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB126_meta.json').write_text(json.dumps(dict(
    universe='fresh |Z|>=1, inverse-crowd direction equals H4 trend',
    contexts=list(CONTEXTS.keys()),entries=list(ENTRY_METHODS.keys()),
    sl_atr=SLS,tp_r=TPS,holds_h=HOLDS,cost_bps=COSTS,
    low_vol='H1 ATR below causal prior 60d median',
    failed_countertrend='adverse excursion threshold then close back through original Z-signal anchor in trend direction; enter next M5 open',
    caveat='research only; OOS repeatedly inspected in prior labs; TRAIN ranking does not restore pristine OOS'
),indent=2))
print('\n'.join(lines))
