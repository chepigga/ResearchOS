#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
spec=importlib.util.spec_from_file_location("lab124",SRC)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OUT=Path("lab126_out"); OUT.mkdir(exist_ok=True)
b=m.b.copy(); p=m.p.copy(); h1=m.h1.copy()
BT=m.BT; BO=m.BO; BH=m.BH; BL=m.BL; BC=m.BC; BA=m.BA; BZ=m.BZ
TRAIN_END=m.TRAIN_END
COSTS=[2.81,7.5]; SEARCH_BARS=72; HOLDS=[12,24,48]; TPS=[1.5,2.0,3.0]; SLS=[1.0,1.5]

# Contexts.
d1=p.set_index('time').resample('1D',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
d1['ema50']=d1.close.ewm(span=50,adjust=False).mean(); d1['ema50_lag10']=d1.ema50.shift(10)
d1['trend_d1']=np.where((d1.close>d1.ema50)&(d1.ema50>d1.ema50_lag10),1,np.where((d1.close<d1.ema50)&(d1.ema50<d1.ema50_lag10),-1,0))
d1['ct']=d1.time+pd.Timedelta(days=1)
h1['atr_med60d']=h1.atr.shift(1).rolling(24*60,min_periods=24*20).median(); h1['low_vol']=h1.atr<h1.atr_med60d; h1['ctv']=h1.time+pd.Timedelta(hours=1)
ctx=b[['time']].copy()
ctx=pd.merge_asof(ctx,d1[['ct','trend_d1']].dropna().sort_values('ct'),left_on='time',right_on='ct',direction='backward')
ctx=pd.merge_asof(ctx,h1[['ctv','low_vol']].dropna().sort_values('ctv'),left_on='time',right_on='ctv',direction='backward')
b['trend_d1']=ctx.trend_d1.values; b['low_vol']=ctx.low_vol.fillna(False).values

# Fresh inverse-crowd aligned with H4 trend.
events=[]
last=len(b)-48*12-2
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1): continue
    side=-1 if BZ[i]>0 else 1
    if int(b.trend.iloc[i])!=side: continue
    events.append(dict(signal_i=i,signal_time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',
                       side=side,atr=float(BA[i]),h4d1=(int(b.trend_d1.iloc[i])==side),low_vol=bool(b.low_vol.iloc[i]),abs_z=abs(float(BZ[i]))))
ev=pd.DataFrame(events); ev.to_csv(OUT/'LAB126_universe.csv',index=False)

def market(i,s,a): return i+1
def pullback(i,s,a,t):
    anchor=float(BC[i])
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        if (s>0 and BL[j]<=anchor-t*a) or (s<0 and BH[j]>=anchor+t*a): return j+1
    return None
def failed(i,s,a,t):
    anchor=float(BC[i]);adv=False
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        if s>0:
            adv |= BL[j]<=anchor-t*a
            if adv and BC[j]>anchor:return j+1
        else:
            adv |= BH[j]>=anchor+t*a
            if adv and BC[j]<anchor:return j+1
    return None
METHODS={
 'MARKET_Z':lambda i,s,a:market(i,s,a),
 'PULLBACK_025':lambda i,s,a:pullback(i,s,a,.25),
 'PULLBACK_050':lambda i,s,a:pullback(i,s,a,.50),
 'FAILED_CT_025':lambda i,s,a:failed(i,s,a,.25),
 'FAILED_CT_050':lambda i,s,a:failed(i,s,a,.50),
}
entries=[]
for _,r in ev.iterrows():
    i=int(r.signal_i);s=int(r.side);a=float(r.atr)
    for name,fn in METHODS.items():
        ei=fn(i,s,a)
        if ei is None:continue
        entries.append(dict(method=name,signal_i=i,entry_i=ei,signal_time=r.signal_time,entry_time=BT.iloc[ei],split=r['split'],
                            side=s,atr=a,h4d1=r.h4d1,low_vol=r.low_vol,abs_z=r.abs_z,
                            delay_min=(BT.iloc[ei]-BT.iloc[i]).total_seconds()/60,
                            entry_delta_atr=s*(float(BO[ei])-float(BC[i]))/a))
en=pd.DataFrame(entries); en.to_csv(OUT/'LAB126_entries.csv',index=False)

# Precompute path outcomes per entry, SL, TP, hold at zero cost.
raw=[]
for rid,r in en.iterrows():
    ei=int(r.entry_i);s=int(r.side);a=float(r.atr);entry=float(BO[ei]);maxend=min(ei+48*12-1,len(b)-1)
    hi=BH[ei:maxend+1]; lo=BL[ei:maxend+1]; cl=BC[ei:maxend+1]
    for sl in SLS:
        dist=sl*a
        fav=(hi-entry)/dist if s>0 else (entry-lo)/dist
        adv=(entry-lo)/dist if s>0 else (hi-entry)/dist
        stop_hits=np.flatnonzero(adv>=1.0)
        stop0=int(stop_hits[0]) if len(stop_hits) else 10**9
        for tp in TPS:
            tp_hits=np.flatnonzero(fav>=tp); tp0=int(tp_hits[0]) if len(tp_hits) else 10**9
            for hold in HOLDS:
                lim=min(hold*12-1,len(cl)-1)
                si=stop0 if stop0<=lim else 10**9; ti=tp0 if tp0<=lim else 10**9
                if si<=ti:
                    if si<10**9: xi=si;gross=-1.0;reason='SL'
                    else: xi=lim;gross=s*(float(cl[lim])-entry)/dist;reason='TIME'
                else:
                    xi=ti;gross=tp;reason='TP'
                raw.append(dict(rid=rid,sl_atr=sl,tp_r=tp,hold_h=hold,exit_i=ei+xi,gross_r=gross,reason=reason,
                                cost_scale=entry/dist))
out=pd.DataFrame(raw)
out.to_csv(OUT/'LAB126_precomputed_outcomes.csv',index=False)

CONTEXTS={
 'H4_ONLY':lambda d:np.ones(len(d),dtype=bool),
 'H4_D1':lambda d:d.h4d1.to_numpy(bool),
 'H4_LOWVOL':lambda d:d.low_vol.to_numpy(bool),
 'H4_D1_LOWVOL':lambda d:(d.h4d1 & d.low_vol).to_numpy(bool),
}
summary=[]; selected_trades=[]
for cost in COSTS:
  for method in METHODS:
    em=en[en.method==method].copy()
    for ctxname,fn in CONTEXTS.items():
      s=em.loc[fn(em)].sort_values('entry_time')
      if s.empty:continue
      srids=set(s.index.tolist())
      oo=out[out.rid.isin(srids)]
      for sl in SLS:
       for tp in TPS:
        for hold in HOLDS:
         z=oo[(oo.sl_atr==sl)&(oo.tp_r==tp)&(oo.hold_h==hold)].set_index('rid')
         open_until=pd.Timestamp.min.tz_localize('UTC'); rows=[]
         for rid,r in s.iterrows():
            if r.entry_time<open_until:continue
            q=z.loc[rid]; exit_time=BT.iloc[int(q.exit_i)]
            net=float(q.gross_r-(cost/10000.0)*q.cost_scale)
            rows.append((r['split'],net,q.reason,r.entry_time,exit_time,r.side,r.delay_min,r.entry_delta_atr))
            open_until=exit_time
         if not rows:continue
         t=pd.DataFrame(rows,columns=['split','net_r','reason','entry_time','exit_time','side','delay_min','entry_delta_atr'])
         ce=t.net_r.cumsum(); realized_dd=float((ce.cummax()-ce).max())
         months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
         for split in ['ALL','TRAIN','OOS']:
            q=t if split=='ALL' else t[t.split==split]
            if q.empty:continue
            pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
            summary.append(dict(cost_bps=cost,method=method,context=ctxname,sl_atr=sl,tp_r=tp,hold_h=hold,split=split,n=len(q),
                                ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((q.net_r>0).mean()),total_r=float(q.net_r.sum()),
                                trades_month=len(t)/months if split=='ALL' else np.nan,r_month=t.net_r.sum()/months if split=='ALL' else np.nan,
                                realized_dd_r=realized_dd if split=='ALL' else np.nan,tp_rate=float((q.reason=='TP').mean()),
                                sl_rate=float((q.reason=='SL').mean()),time_rate=float((q.reason=='TIME').mean())))
sm=pd.DataFrame(summary); sm.to_csv(OUT/'LAB126_grid_summary.csv',index=False)

rank=sm[(sm.cost_bps==2.81)&(sm.split=='TRAIN')&(sm.n>=80)].copy()
rank['rank_score']=rank.ev.clip(-2,2)+0.15*np.log(rank.pf.clip(.1,10))
rank=rank.sort_values(['rank_score','pf','n'],ascending=False); rank.to_csv(OUT/'LAB126_train_ranking.csv',index=False)

sel=[]
for _,r in rank.head(15).iterrows():
    o=sm[(sm.cost_bps==2.81)&(sm.split=='OOS')&(sm.method==r.method)&(sm.context==r.context)&(sm.sl_atr==r.sl_atr)&(sm.tp_r==r.tp_r)&(sm.hold_h==r.hold_h)]
    a=sm[(sm.cost_bps==2.81)&(sm.split=='ALL')&(sm.method==r.method)&(sm.context==r.context)&(sm.sl_atr==r.sl_atr)&(sm.tp_r==r.tp_r)&(sm.hold_h==r.hold_h)]
    d=dict(method=r.method,context=r.context,sl_atr=float(r.sl_atr),tp_r=float(r.tp_r),hold_h=int(r.hold_h),train_n=int(r.n),train_ev=float(r.ev),train_pf=float(r.pf))
    if len(o):
        q=o.iloc[0];d.update(oos_n=int(q.n),oos_ev=float(q.ev),oos_pf=float(q.pf))
    if len(a):
        q=a.iloc[0];d.update(all_n=int(q.n),trades_month=float(q.trades_month),r_month=float(q.r_month),realized_dd_r=float(q.realized_dd_r))
    sel.append(d)
pd.DataFrame(sel).to_csv(OUT/'LAB126_top_train_selected.csv',index=False)

# Exact MTM DD for top 10 only.
ddrows=[]
for d in sel[:10]:
    s=en[en.method==d['method']].copy()
    if d['context']=='H4_D1':s=s[s.h4d1]
    elif d['context']=='H4_LOWVOL':s=s[s.low_vol]
    elif d['context']=='H4_D1_LOWVOL':s=s[s.h4d1&s.low_vol]
    s=s.sort_values('entry_time'); z=out[(out.sl_atr==d['sl_atr'])&(out.tp_r==d['tp_r'])&(out.hold_h==d['hold_h'])].set_index('rid')
    open_until=pd.Timestamp.min.tz_localize('UTC');cum=0.0;eq=[]
    for rid,r in s.iterrows():
        if r.entry_time<open_until:continue
        q=z.loc[rid];xi=int(q.exit_i);entry=float(BO[int(r.entry_i)]);dist=d['sl_atr']*float(r.atr)
        net=float(q.gross_r-(2.81/10000.0)*q.cost_scale);start=cum
        for j in range(int(r.entry_i),xi+1):
            mtm=int(r.side)*(BC[j]-entry)/dist-(2.81/10000.0)*entry/dist
            if j==xi:mtm=net
            eq.append((BT.iloc[j],start+mtm))
        cum+=net;open_until=BT.iloc[xi]
    ep=pd.DataFrame(eq,columns=['time','equity']).sort_values('time').drop_duplicates('time',keep='last')
    dd=float((ep.equity.cummax()-ep.equity).max()) if len(ep) else np.nan
    ddrows.append(dict(**d,exact_mtm_dd_r=dd))
pd.DataFrame(ddrows).to_csv(OUT/'LAB126_top_exact_mtm_dd.csv',index=False)

# Best per method, plus 7.5bps stress.
lines=['# LAB126 — ANTI-CROWD TREND CONTINUATION / FAILED COUNTERTREND','',
'Universe: fresh |Z|>=1 where inverse-crowd direction equals causal H4 trend. No extension or OI capitulation gate.',
'Contexts: H4 only, H4+D1 alignment, H4 low-vol, H4+D1 low-vol.',
'Entries: MARKET_Z; pullback 0.25/0.50 H1ATR; failed countertrend 0.25/0.50ATR then reclaim original signal anchor.',
'Grid: SL1/1.5 H1ATR, TP1.5/2/3R, 12/24/48h, one-position chronology. Ranking is TRAIN-only, min TRAIN N=80.',
'OOS is development OOS already inspected in prior studies; treat as transfer evidence, not pristine validation.','']

lines.append('## Top TRAIN-selected @2.81bps')
for d in sel[:12]:
    lines.append(f"- {d['method']} / {d['context']} / SL{d['sl_atr']:.1f} TP{d['tp_r']:.1f}R {d['hold_h']}h: TRAIN N={d['train_n']} EV={d['train_ev']:+.3f} PF={d['train_pf']:.2f} | OOS N={d.get('oos_n',0)} EV={d.get('oos_ev',float('nan')):+.3f} PF={d.get('oos_pf',float('nan')):.2f} | {d.get('trades_month',float('nan')):.2f}/mo")
lines.append('')
lines.append('## Best per entry method')
for method in METHODS:
    rr=rank[rank.method==method]
    if rr.empty:continue
    r=rr.iloc[0]
    o=sm[(sm.cost_bps==2.81)&(sm.split=='OOS')&(sm.method==method)&(sm.context==r.context)&(sm.sl_atr==r.sl_atr)&(sm.tp_r==r.tp_r)&(sm.hold_h==r.hold_h)]
    s75=sm[(sm.cost_bps==7.5)&(sm.split=='OOS')&(sm.method==method)&(sm.context==r.context)&(sm.sl_atr==r.sl_atr)&(sm.tp_r==r.tp_r)&(sm.hold_h==r.hold_h)]
    extra=''
    if len(o):q=o.iloc[0];extra+=f" | OOS2.81 N={int(q.n)} EV={q.ev:+.3f} PF={q.pf:.2f}"
    if len(s75):q=s75.iloc[0];extra+=f" | OOS7.5 EV={q.ev:+.3f} PF={q.pf:.2f}"
    lines.append(f"- {method}: {r.context}, SL{r.sl_atr:.1f}, TP{r.tp_r:.1f}R, {int(r.hold_h)}h | TRAIN EV={r.ev:+.3f} PF={r.pf:.2f}{extra}")
(OUT/'LAB126_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB126_meta.json').write_text(json.dumps(dict(universe='fresh |Z|>=1; inverse crowd = H4 trend',methods=list(METHODS),costs=COSTS,holds=HOLDS,tps=TPS,sls=SLS,
    low_vol='H1 ATR below causal prior 60d median',failed_countertrend='adverse threshold then close through original signal anchor in H4 trend direction; next M5 open',
    caveat='development OOS repeatedly inspected; research only'),indent=2))
print('\n'.join(lines))
