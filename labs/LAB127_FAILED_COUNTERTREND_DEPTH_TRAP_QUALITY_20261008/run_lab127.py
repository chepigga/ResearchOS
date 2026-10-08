#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
spec=importlib.util.spec_from_file_location("lab124",SRC)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OUT=Path("lab127_out"); OUT.mkdir(exist_ok=True)
b=m.b.copy(); p=m.p.copy()
BT=m.BT; BO=m.BO; BH=m.BH; BL=m.BL; BC=m.BC; BA=m.BA; BZ=m.BZ
TRAIN_END=m.TRAIN_END
COSTS=[2.81,7.5]
DEPTHS=[0.25,0.50,0.75,1.00]
SEARCH_BARS=72
MAX_H=48
SL_ATR=1.5
TP_R=3.0

# Add D1 trend.
d1=p.set_index('time').resample('1D',label='left',closed='left').agg(
    open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')
).dropna().reset_index()
d1['ema50']=d1.close.ewm(span=50,adjust=False).mean(); d1['ema50_lag10']=d1.ema50.shift(10)
d1['trend_d1']=np.where((d1.close>d1.ema50)&(d1.ema50>d1.ema50_lag10),1,
                        np.where((d1.close<d1.ema50)&(d1.ema50<d1.ema50_lag10),-1,0))
d1['ct']=d1.time+pd.Timedelta(days=1)
ctx=pd.merge_asof(b[['time']].sort_values('time'),d1[['ct','trend_d1']].dropna().sort_values('ct'),
                  left_on='time',right_on='ct',direction='backward')
b['trend_d1']=ctx.trend_d1.values

# Add raw OI from LAB124 flow frame.
ff=m.f[['time','oi']].copy().dropna().sort_values('time')
tmp=pd.merge_asof(b[['time']].sort_values('time'),ff,on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b['oi_raw']=tmp.oi.values

# Fresh inverse-crowd events aligned with BOTH H4 and D1 trend.
events=[]
last=len(b)-MAX_H*12-2
for i in range(12,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1): continue
    side=-1 if BZ[i]>0 else 1
    if int(b.trend.iloc[i])!=side or int(b.trend_d1.iloc[i])!=side: continue
    events.append(dict(signal_i=i,signal_time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',
                       side=side,atr=float(BA[i]),z0=float(BZ[i]),oi0=float(b.oi_raw.iloc[i]) if pd.notna(b.oi_raw.iloc[i]) else np.nan))
ev=pd.DataFrame(events)
ev.to_csv(OUT/'LAB127_universe.csv',index=False)

def find_trap(i,side,atr,depth):
    anchor=float(BC[i]); hit=None
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        adverse=((anchor-BL[j])>=depth*atr) if side>0 else ((BH[j]-anchor)>=depth*atr)
        if adverse:
            hit=j;break
    if hit is None:return None
    reclaim=None
    for j in range(hit,min(hit+SEARCH_BARS,len(b)-2)+1):
        if (side>0 and BC[j]>anchor) or (side<0 and BC[j]<anchor):
            reclaim=j;break
    if reclaim is None:return None

    # Trap anatomy known by reclaim close.
    prev_lo=float(np.min(BL[max(0,hit-12):hit])); prev_hi=float(np.max(BH[max(0,hit-12):hit]))
    new_extreme=(BL[hit]<prev_lo) if side>0 else (BH[hit]>prev_hi)

    z_hit=float(BZ[hit]); same_crowd_sign=(np.sign(z_hit)==np.sign(BZ[i]))
    z_strength=(abs(z_hit)-abs(float(BZ[i]))) if same_crowd_sign else -abs(float(BZ[i]))
    z_strengthened=z_strength>=0.25

    oi0=float(b.oi_raw.iloc[i]) if pd.notna(b.oi_raw.iloc[i]) else np.nan
    oih=float(b.oi_raw.iloc[hit]) if pd.notna(b.oi_raw.iloc[hit]) else np.nan
    oi_delta=(oih/oi0-1.0) if np.isfinite(oi0) and np.isfinite(oih) and oi0>0 else np.nan
    oi_build=bool(np.isfinite(oi_delta) and oi_delta>0)

    reclaim_minutes=(BT.iloc[reclaim]-BT.iloc[hit]).total_seconds()/60.0
    body=side*(BC[reclaim]-BO[reclaim])/atr
    impulse_reclaim=body>=0.25
    fast_reclaim=reclaim_minutes<=60
    very_fast=reclaim_minutes<=30

    # How far beyond the requested depth the attack actually stretched.
    if side>0:
        realized_depth=(anchor-float(np.min(BL[i+1:reclaim+1])))/atr
    else:
        realized_depth=(float(np.max(BH[i+1:reclaim+1]))-anchor)/atr

    # Enter next M5 open after reclaim.
    ei=reclaim+1
    return dict(hit_i=hit,reclaim_i=reclaim,entry_i=ei,new_extreme=new_extreme,
                z_strength=z_strength,z_strengthened=z_strengthened,
                oi_delta=oi_delta,oi_build=oi_build,reclaim_min=reclaim_minutes,
                impulse_reclaim=impulse_reclaim,fast_reclaim=fast_reclaim,very_fast=very_fast,
                realized_depth=realized_depth)

rows=[]
for _,r in ev.iterrows():
    i=int(r.signal_i);side=int(r.side);atr=float(r.atr)
    for depth in DEPTHS:
        q=find_trap(i,side,atr,depth)
        if q is None:continue
        rows.append(dict(depth=depth,signal_i=i,signal_time=r.signal_time,split=r['split'],side=side,atr=atr,**q))
traps=pd.DataFrame(rows)
traps.to_csv(OUT/'LAB127_traps.csv',index=False)

def sim(ei,side,atr,cost):
    entry=float(BO[ei]);dist=SL_ATR*atr;sl=entry-side*dist;tp=entry+side*TP_R*dist
    end=min(ei+MAX_H*12-1,len(b)-1);gross=side*(BC[end]-entry)/dist;reason='TIME';xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
        if hs:gross=-1;reason='SL';xi=j;break
        if ht:gross=TP_R;reason='TP';xi=j;break
    net=float(gross-(cost/10000.0)*entry/dist)
    return net,reason,xi

# Predeclared trap-quality gates.
GATES={
 'ALL':lambda d:pd.Series(True,index=d.index),
 'NEW_EXTREME':lambda d:d.new_extreme,
 'Z_STRENGTH':lambda d:d.z_strengthened,
 'OI_BUILD':lambda d:d.oi_build,
 'FAST60':lambda d:d.fast_reclaim,
 'FAST30':lambda d:d.very_fast,
 'IMPULSE_RECLAIM':lambda d:d.impulse_reclaim,
 'EXTREME_Z':lambda d:d.new_extreme & d.z_strengthened,
 'EXTREME_OI':lambda d:d.new_extreme & d.oi_build,
 'Z_OI':lambda d:d.z_strengthened & d.oi_build,
 'TRAP_STRONG':lambda d:d.new_extreme & d.z_strengthened & d.oi_build,
 'TRAP_STRONG_FAST':lambda d:d.new_extreme & d.z_strengthened & d.oi_build & d.fast_reclaim,
 'TRAP_STRONG_IMP':lambda d:d.new_extreme & d.z_strengthened & d.oi_build & d.impulse_reclaim,
}

summary=[]; trade_rows=[]
for cost in COSTS:
  for depth in DEPTHS:
    dd=traps[traps.depth==depth].copy()
    for gate,fn in GATES.items():
      s=dd[fn(dd)].sort_values('entry_i')
      if s.empty:continue
      open_until=pd.Timestamp.min.tz_localize('UTC');trs=[]
      for _,r in s.iterrows():
        et=BT.iloc[int(r.entry_i)]
        if et<open_until:continue
        net,reason,xi=sim(int(r.entry_i),int(r.side),float(r.atr),cost)
        xt=BT.iloc[xi];open_until=xt
        trs.append(dict(cost_bps=cost,depth=depth,gate=gate,split=r['split'],
                        signal_time=r.signal_time,entry_time=et,exit_time=xt,
                        side='BUY' if r.side>0 else 'SELL',net_r=net,reason=reason,
                        realized_depth=r.realized_depth,reclaim_min=r.reclaim_min,
                        z_strength=r.z_strength,oi_delta=r.oi_delta,new_extreme=r.new_extreme,
                        z_strengthened=r.z_strengthened,oi_build=r.oi_build,
                        impulse_reclaim=r.impulse_reclaim))
      t=pd.DataFrame(trs)
      if t.empty:continue
      trade_rows.append(t)
      ce=t.net_r.cumsum();ddr=float((ce.cummax()-ce).max())
      months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
      for split in ['ALL','TRAIN','OOS']:
        q=t if split=='ALL' else t[t.split==split]
        if q.empty:continue
        pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
        summary.append(dict(cost_bps=cost,depth=depth,gate=gate,split=split,n=len(q),
                            ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                            wr=float((q.net_r>0).mean()),total_r=float(q.net_r.sum()),
                            trades_month=len(t)/months if split=='ALL' else np.nan,
                            r_month=t.net_r.sum()/months if split=='ALL' else np.nan,
                            realized_dd_r=ddr if split=='ALL' else np.nan,
                            tp_rate=float((q.reason=='TP').mean()),
                            sl_rate=float(q.reason.isin(['SL','BOTH_STOP_FIRST']).mean()),
                            time_rate=float((q.reason=='TIME').mean())))
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB127_summary.csv',index=False)
pd.concat(trade_rows,ignore_index=True).to_csv(OUT/'LAB127_trades.csv',index=False)

# TRAIN-only ranking. Require TRAIN N>=60.
rank=sm[(sm.cost_bps==2.81)&(sm.split=='TRAIN')&(sm.n>=60)].copy()
rank['rank_score']=rank.ev.clip(-2,2)+0.15*np.log(rank.pf.clip(.1,10))
rank=rank.sort_values(['rank_score','pf','n'],ascending=False)
rank.to_csv(OUT/'LAB127_train_ranking.csv',index=False)

top=[]
for _,r in rank.head(20).iterrows():
    o=sm[(sm.cost_bps==2.81)&(sm.split=='OOS')&(sm.depth==r.depth)&(sm.gate==r.gate)]
    a=sm[(sm.cost_bps==2.81)&(sm.split=='ALL')&(sm.depth==r.depth)&(sm.gate==r.gate)]
    s75=sm[(sm.cost_bps==7.5)&(sm.split=='OOS')&(sm.depth==r.depth)&(sm.gate==r.gate)]
    d=dict(depth=float(r.depth),gate=r.gate,train_n=int(r.n),train_ev=float(r.ev),train_pf=float(r.pf))
    if len(o):
        q=o.iloc[0];d.update(oos_n=int(q.n),oos_ev=float(q.ev),oos_pf=float(q.pf))
    if len(a):
        q=a.iloc[0];d.update(all_n=int(q.n),trades_month=float(q.trades_month),r_month=float(q.r_month),dd_r=float(q.realized_dd_r))
    if len(s75):
        q=s75.iloc[0];d.update(oos75_ev=float(q.ev),oos75_pf=float(q.pf))
    top.append(d)
pd.DataFrame(top).to_csv(OUT/'LAB127_top_train_selected.csv',index=False)

# Anatomy: bins of reclaim speed, z strengthening, OI change, realized depth.
an=traps.copy()
an['reclaim_bin']=pd.cut(an.reclaim_min,[-1,30,60,120,240,99999],labels=['<=30','30-60','60-120','120-240','>240'])
an['z_bin']=pd.cut(an.z_strength,[-999,-.25,0,.25,.5,1,999],labels=['<-0.25','-0.25-0','0-.25','.25-.5','.5-1','1+'])
an['oi_bin']=pd.cut(an.oi_delta,[-999,-.01,0,.01,.03,.10,999],labels=['<-1%','-1-0','0-1%','1-3%','3-10%','10%+'])
an['real_depth_bin']=pd.cut(an.realized_depth,[0,.5,.75,1,1.25,1.5,2,999],labels=['<.5','.5-.75','.75-1','1-1.25','1.25-1.5','1.5-2','2+'])
anat=[]
for depth in DEPTHS:
    d=an[an.depth==depth]
    for dim in ['reclaim_bin','z_bin','oi_bin','real_depth_bin','new_extreme','impulse_reclaim']:
        for grp,g in d.groupby(dim,observed=True):
            if len(g)<30:continue
            # descriptive 48h close in trend direction from entry
            vals=[]
            for _,r in g.iterrows():
                ei=int(r.entry_i);end=min(ei+48*12,len(b)-1);entry=float(BO[ei])
                vals.append(int(r.side)*(float(BC[end])-entry)/float(r.atr))
            anat.append(dict(depth=depth,dimension=dim,group=str(grp),n=len(g),mean48_atr=float(np.mean(vals)),median48_atr=float(np.median(vals))))
pd.DataFrame(anat).to_csv(OUT/'LAB127_anatomy.csv',index=False)

lines=['# LAB127 — FAILED COUNTERTREND DEPTH × TRAP QUALITY','',
       'Universe: fresh |Z|>=1 where inverse-crowd direction aligns with BOTH H4 and D1 trend.',
       'Failed countertrend depth tested: 0.25 / 0.50 / 0.75 / 1.00 H1 ATR, hit within 6h, then reclaim of original Z-signal anchor within 6h.',
       'Trap quality at reclaim: new local extreme, crowd Z strengthening during attack, raw OI build during attack, reclaim speed, reclaim impulse.',
       'Execution frozen from LAB126 candidate: enter next M5 after reclaim, SL=1.5 H1ATR, TP=3R, max hold48h, one position, costs 2.81/7.5bps.',
       'Ranking is TRAIN-only with minimum TRAIN N=60. Development OOS remains previously inspected.','']

lines.append('## Top TRAIN-selected @2.81bps')
for d in top[:15]:
    lines.append(f"- depth {d['depth']:.2f} / {d['gate']}: TRAIN N={d['train_n']} EV={d['train_ev']:+.3f} PF={d['train_pf']:.2f} | OOS N={d.get('oos_n',0)} EV={d.get('oos_ev',float('nan')):+.3f} PF={d.get('oos_pf',float('nan')):.2f} | {d.get('trades_month',float('nan')):.2f}/mo | OOS7.5 PF={d.get('oos75_pf',float('nan')):.2f}")
lines.append('')
lines.append('## Best by depth')
for depth in DEPTHS:
    rr=rank[rank.depth==depth]
    if rr.empty:continue
    r=rr.iloc[0]
    o=sm[(sm.cost_bps==2.81)&(sm.split=='OOS')&(sm.depth==depth)&(sm.gate==r.gate)]
    ex=''
    if len(o):
        q=o.iloc[0];ex=f" | OOS N={int(q.n)} EV={q.ev:+.3f} PF={q.pf:.2f}"
    lines.append(f"- {depth:.2f} ATR: {r.gate} | TRAIN N={int(r.n)} EV={r.ev:+.3f} PF={r.pf:.2f}{ex}")
(OUT/'LAB127_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB127_meta.json').write_text(json.dumps(dict(
    universe='fresh |Z|>=1; inverse crowd = H4 = D1 trend',
    depths=DEPTHS,search_hours=6,execution='next M5 after reclaim, SL1.5 H1ATR, TP3R, 48h, one position',
    gates=list(GATES.keys()),costs=COSTS,
    trap_features=['new_extreme','z_strengthened>=+0.25 absZ','raw_OI_build','reclaim<=60m','reclaim_body>=0.25ATR'],
    caveat='research only; OOS is development OOS and has been repeatedly inspected'
),indent=2))
print('\n'.join(lines))
