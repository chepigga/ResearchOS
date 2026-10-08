#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB136_MISSED_OPPORTUNITY_ATLAS_20261008/run_lab136.py"
spec=importlib.util.spec_from_file_location("lab136",SRC)
M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

OUT=Path("lab137_out"); OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
MAX_H=48

# R48 universe frozen from LAB136, BTC TRAIN only.
ev=M.ev[M.ev.mech=='R48_ACCEPT'].copy().reset_index(drop=True)
b=M.b.reset_index(drop=True)
BT=M.BT; BO=M.BO; BH=M.BH; BL=M.BL; BC=M.BC; BA=M.BA; BOI=M.BOI
R48=48*12
r48h=b.high.shift(1).rolling(R48,min_periods=R48).max().to_numpy(float)
r48l=b.low.shift(1).rolling(R48,min_periods=R48).min().to_numpy(float)

# Causal context features known by entry.
rows=[]
for _,r in ev.iterrows():
    i=int(r.signal_i); ei=int(r.entry_i); side=int(r.side); atr=float(r.atr)
    boundary=float(r48h[i] if side>0 else r48l[i])

    # breakout depth at signal close
    breakout_depth=(BC[i]-boundary)*side/atr

    # acceptance window = six M5 bars after breakout, known before entry in LAB136
    acc_idx=np.arange(i+1,i+7)
    closes=BC[acc_idx]
    outside=((closes>boundary) if side>0 else (closes<boundary))
    outside_n=int(np.sum(outside))
    min_margin=float(np.min((closes-boundary)*side/atr))
    mean_margin=float(np.mean((closes-boundary)*side/atr))
    last_margin=float((closes[-1]-boundary)*side/atr)

    # Retest = any bar during acceptance window touches back through boundary.
    if side>0:
        retest=bool(np.any(BL[acc_idx] <= boundary))
        deep_retest=float(max(0.0,(boundary-np.min(BL[acc_idx]))/atr))
    else:
        retest=bool(np.any(BH[acc_idx] >= boundary))
        deep_retest=float(max(0.0,(np.max(BH[acc_idx])-boundary)/atr))

    # OI change breakout->entry.
    oi_change=float(BOI[ei]/BOI[i]-1.0) if BOI[i]>0 else np.nan

    # Volatility expansion: mean true range of acceptance bars / prior 12 M5 bars mean TR.
    tr=np.maximum(BH-BL,np.maximum(np.abs(BH-np.r_[BC[0],BC[:-1]]),np.abs(BL-np.r_[BC[0],BC[:-1]])))
    pre=max(i-12,1)
    pre_tr=float(np.mean(tr[pre:i])) if i>pre else np.nan
    acc_tr=float(np.mean(tr[i:i+7]))
    vol_expand=float(acc_tr/pre_tr) if pre_tr>0 else np.nan

    # Prior boundary touch count in last 24h before breakout.
    lo=max(0,i-24*12)
    tol=0.10*atr
    if side>0:
        touches=int(np.sum(BH[lo:i] >= boundary-tol))
    else:
        touches=int(np.sum(BL[lo:i] <= boundary+tol))

    # Speed: bars from first breakout close to entry; fixed 7 in base, retained for audit.
    row=r.to_dict()
    row.update(dict(boundary=boundary,breakout_depth=breakout_depth,
                    outside_n=outside_n,min_margin=min_margin,mean_margin=mean_margin,last_margin=last_margin,
                    retest=retest,deep_retest=deep_retest,oi_change=oi_change,vol_expand=vol_expand,
                    prior_touches24=touches))
    rows.append(row)
df=pd.DataFrame(rows)

# TRAIN-distribution thresholds only, not return-fitted.
thr={
    'break_depth_q60':float(df.breakout_depth.quantile(.60)),
    'mean_margin_q60':float(df.mean_margin.quantile(.60)),
    'oi_q60':float(df.oi_change.quantile(.60)),
    'vol_q60':float(df.vol_expand.quantile(.60)),
    'touch_q40':float(df.prior_touches24.quantile(.40)),
}
(OUT/'LAB137_thresholds.json').write_text(json.dumps(thr,indent=2))

# Predeclared causal gates.
GATES={
    'ALL':lambda d:pd.Series(True,index=d.index),
    'NO_RETEST':lambda d:~d.retest,
    'STRONG_ACCEPT':lambda d:d.mean_margin>=thr['mean_margin_q60'],
    'OI_BUILD':lambda d:d.oi_change>=thr['oi_q60'],
    'VOL_EXPAND':lambda d:d.vol_expand>=thr['vol_q60'],
    'FRESH_BOUNDARY':lambda d:d.prior_touches24<=thr['touch_q40'],
    'DEPTH_ACCEPT':lambda d:(d.breakout_depth>=thr['break_depth_q60'])&(d.mean_margin>=thr['mean_margin_q60']),
    'CLEAN_ACCEPT':lambda d:(~d.retest)&(d.mean_margin>=thr['mean_margin_q60']),
    'ACCEPT_OI':lambda d:(d.mean_margin>=thr['mean_margin_q60'])&(d.oi_change>=thr['oi_q60']),
    'ACCEPT_VOL':lambda d:(d.mean_margin>=thr['mean_margin_q60'])&(d.vol_expand>=thr['vol_q60']),
    'CLEAN_OI':lambda d:(~d.retest)&(d.oi_change>=thr['oi_q60']),
    'CLEAN_VOL':lambda d:(~d.retest)&(d.vol_expand>=thr['vol_q60']),
    'CLEAN_ACCEPT_OI':lambda d:(~d.retest)&(d.mean_margin>=thr['mean_margin_q60'])&(d.oi_change>=thr['oi_q60']),
}

def sim_one(r,cost):
    ei=int(r.entry_i);side=int(r.side);atr=float(r.atr);entry=float(BO[ei])
    sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(b)-1)
    gross=side*(BC[end]-entry)/atr;reason='TIME';xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
        if hs:gross=-1;reason='SL';xi=j;break
        if ht:gross=3;reason='TP';xi=j;break
    return float(gross-(cost/10000.0)*entry/atr),reason,xi

summary=[];alltr=[]
for cost in COSTS:
  for gate,fn in GATES.items():
    s=df[fn(df)].sort_values('entry_time')
    open_until=pd.Timestamp.min.tz_localize('UTC');rows=[]
    for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi=sim_one(r,cost);xt=BT.iloc[xi];open_until=xt
        rows.append(dict(cost_bps=cost,gate=gate,entry_time=r.entry_time,exit_time=xt,
                         side='BUY' if r.side>0 else 'SELL',net_r=net,reason=reason,
                         breakout_depth=r.breakout_depth,mean_margin=r.mean_margin,retest=r.retest,
                         oi_change=r.oi_change,vol_expand=r.vol_expand,prior_touches24=r.prior_touches24))
    t=pd.DataFrame(rows)
    if t.empty:continue
    alltr.append(t)
    pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
    months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
    ce=t.net_r.cumsum();dd=float((ce.cummax()-ce).max())
    summary.append(dict(cost_bps=cost,gate=gate,n=len(t),trades_month=len(t)/months,
                        ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                        wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),r_month=float(t.net_r.sum()/months),
                        dd_r=dd,buy_n=int((t.side=='BUY').sum()),sell_n=int((t.side=='SELL').sum())))
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB137_summary.csv',index=False)
if alltr:pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB137_trades.csv',index=False)

# Descriptive anatomy bins only; not eligible for promotion.
anat=[]
for col in ['breakout_depth','mean_margin','oi_change','vol_expand','prior_touches24']:
    d=df.copy()
    try:d['_bin']=pd.qcut(d[col],4,duplicates='drop')
    except:d['_bin']='ALL'
    for grp,g in d.groupby('_bin',observed=True):
        if len(g)<30:continue
        vals=[]
        for _,r in g.iterrows():
            net,_,_=sim_one(r,2.81);vals.append(net)
        a=np.asarray(vals,float);pos=a[a>0].sum();neg=-a[a<0].sum()
        anat.append(dict(dimension=col,group=str(grp),n=len(a),ev=float(a.mean()),
                         pf=float(pos/neg) if neg>0 else np.inf,wr=float((a>0).mean())))
pd.DataFrame(anat).to_csv(OUT/'LAB137_anatomy_bins.csv',index=False)

# Rank only predeclared gates with enough frequency.
rank=sm[(sm.cost_bps==2.81)&(sm.n>=60)].copy()
rank=rank.sort_values(['pf','ev'],ascending=False)
rank.to_csv(OUT/'LAB137_rank.csv',index=False)

lines=['# LAB137 — R48_ACCEPT ANATOMY','',
       'Protocol: BTC TRAIN only. No BTC OOS. R48_ACCEPT event definition is frozen from LAB136.',
       'Goal: identify a causal subset that can reduce raw ~19 trades/month toward ~2–4 unique/month while materially improving PF.',
       '',
       'TRAIN-only non-return thresholds:',
       f"- breakout depth q60 = {thr['break_depth_q60']:.3f} H1ATR",
       f"- mean acceptance margin q60 = {thr['mean_margin_q60']:.3f} H1ATR",
       f"- OI change q60 = {thr['oi_q60']:.3%}",
       f"- volatility expansion q60 = {thr['vol_q60']:.2f}x",
       f"- prior boundary touches q40 = {thr['touch_q40']:.1f}",
       '',
       '## Predeclared gate results @2.81bps']
for _,r in rank.iterrows():
    lines.append(f"- {r.gate}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R, BUY/SELL={int(r.buy_n)}/{int(r.sell_n)}")
lines += ['','## Stress @7.5bps']
for gate in rank.gate.tolist()[:8]:
    q=sm[(sm.cost_bps==7.5)&(sm.gate==gate)]
    if len(q):
        r=q.iloc[0]
        lines.append(f"- {gate}: N={int(r.n)}, {r.trades_month:.2f}/mo, EV={r.ev:+.3f}R, PF={r.pf:.2f}, DD={r.dd_r:.1f}R")
lines += ['','## Decision rule',
          'Promote only a predeclared gate that reaches approximately 2–4 trades/month, materially improves on raw R48_ACCEPT PF 1.14, and remains positive under 7.5bps.',
          'Quartile-bin anatomy is descriptive only and cannot be used to retro-fit a threshold in this LAB.']
(OUT/'LAB137_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB137_meta.json').write_text(json.dumps(dict(protocol='BTC TRAIN only',parent='LAB136 R48_ACCEPT',
    thresholds=thr,gates=list(GATES.keys()),execution='SL1 H1ATR TP3R 48h stop-first',caveat='no BTC OOS'),indent=2))
print('\n'.join(lines))
