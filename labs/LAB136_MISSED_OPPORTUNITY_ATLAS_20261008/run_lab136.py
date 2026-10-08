#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, re, zipfile
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
PORT_SRC=ROOT/"labs/LAB134_ENGINE_A_PLUS_B3_PORTFOLIO_20261008/run_lab134.py"
spec=importlib.util.spec_from_file_location("lab134",PORT_SRC)
M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

OUT=Path("lab136_out"); OUT.mkdir(exist_ok=True)
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
COSTS=[2.81,7.5]
MAX_H=48
RISK=0.25

# Reuse the exact BTC TRAIN tape / flow already loaded by LAB134 lineage.
b=M.A.b.copy()
b=b[b.time<TRAIN_END].copy().reset_index(drop=True)
BT=b.time.reset_index(drop=True)
BO=b.open.to_numpy(float); BH=b.high.to_numpy(float); BL=b.low.to_numpy(float); BC=b.close.to_numpy(float)
BA=b.atr.to_numpy(float)

# Flow OI from LAB124 source merged again on time.
f=M.A.f[['time','oi']].copy()
f=f[f.time<TRAIN_END].sort_values('time')
b=pd.merge_asof(b.sort_values('time'),f,on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b=b.dropna(subset=['oi']).reset_index(drop=True)
BT=b.time.reset_index(drop=True)
BO=b.open.to_numpy(float); BH=b.high.to_numpy(float); BL=b.low.to_numpy(float); BC=b.close.to_numpy(float)
BA=b.atr.to_numpy(float); BOI=b.oi.to_numpy(float)

# Frozen A+B3_HIGH accepted TRAIN trades, for overlap reference.
def frozen_ab3(cost=2.81):
    pool=M.make_events(cost)
    s=pool[pool.engine.isin(['A','B3_HIGH'])].copy()
    s=s[pd.to_datetime(s.entry_time,utc=True)<TRAIN_END]
    pri={'A':0,'B3_HIGH':1};s['pri']=s.engine.map(pri)
    s=s.sort_values(['entry_time','pri'])
    out=[];open_until=pd.Timestamp.min.tz_localize('UTC')
    for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        open_until=r.exit_time
        out.append(r)
    return pd.DataFrame(out)

BASE=frozen_ab3(2.81)
base_times=pd.to_datetime(BASE.entry_time,utc=True).sort_values().astype('int64').to_numpy()

def nearest_base_h(t):
    if len(base_times)==0:return np.inf
    tt=pd.Timestamp(t)
    if tt.tzinfo is None:tt=tt.tz_localize('UTC')
    else:tt=tt.tz_convert('UTC')
    x=int(tt.value);k=np.searchsorted(base_times,x);d=[]
    if k<len(base_times):d.append(abs(base_times[k]-x)/3.6e12)
    if k>0:d.append(abs(base_times[k-1]-x)/3.6e12)
    return min(d) if d else np.inf

# H1 tape for compression measurements.
p5=b[['time','open','high','low','close']].copy()
h1=p5.set_index('time').resample('1h',label='left',closed='left').agg(
    open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')
).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean()
h1['range24']=h1.high.shift(1).rolling(24,min_periods=24).max()-h1.low.shift(1).rolling(24,min_periods=24).min()
h1['comp24']=h1.range24/h1.atr
COMP_Q30=float(h1.loc[h1.time<TRAIN_END,'comp24'].dropna().quantile(.30))
h1['close_time']=h1.time+pd.Timedelta(hours=1)

bb=pd.merge_asof(b.sort_values('time'),h1[['close_time','comp24']].dropna().sort_values('close_time'),
                 left_on='time',right_on='close_time',direction='backward')
b=bb.reset_index(drop=True)
BT=b.time.reset_index(drop=True)
BO=b.open.to_numpy(float); BH=b.high.to_numpy(float); BL=b.low.to_numpy(float); BC=b.close.to_numpy(float)
BA=b.atr.to_numpy(float); BOI=b.oi.to_numpy(float)

# Frozen price boundaries, excluding current bar.
R24=24*12; R48=48*12
r24h=b.high.shift(1).rolling(R24,min_periods=R24).max().to_numpy(float)
r24l=b.low.shift(1).rolling(R24,min_periods=R24).min().to_numpy(float)
r48h=b.high.shift(1).rolling(R48,min_periods=R48).max().to_numpy(float)
r48l=b.low.shift(1).rolling(R48,min_periods=R48).min().to_numpy(float)

# OI-drop Q75 for 120m, TRAIN mechanical threshold among negative changes.
oi120=pd.Series(BOI).pct_change(24)
neg=(-oi120[oi120<0]).dropna()
OI120_Q75=float(neg.quantile(.75))

events=[]

# C1: POST-DELEVERAGING CONTINUATION
# Shock >=2 H1ATR / <=2h + OI drop Q75. Unlike B2, wait for 0.25ATR pullback then renewed break of shock extreme.
last=-9999
for i in range(24,len(b)-MAX_H*12-2):
    move=(BC[i]-BC[i-24])/BA[i]
    oich=BOI[i]/BOI[i-24]-1
    cond=(abs(move)>=2.0 and oich<=-OI120_Q75)
    if not cond or i-last<72:continue
    d=1 if move>0 else -1
    shock_ext=float(np.max(BH[i-24:i+1]) if d>0 else np.min(BL[i-24:i+1]))
    pull=None
    for j in range(i+1,min(i+73,len(b)-2)):
        adverse=(shock_ext-BL[j])/BA[i] if d>0 else (BH[j]-shock_ext)/BA[i]
        if adverse>=0.25:
            pull=j;break
    if pull is None:continue
    br=None
    for j in range(pull+1,min(pull+73,len(b)-2)):
        if (BC[j]>shock_ext if d>0 else BC[j]<shock_ext):
            br=j;break
    if br is None:continue
    ei=br+1;last=i
    events.append(dict(mech='POST_DELEV_CONT',signal_time=BT.iloc[i],entry_time=BT.iloc[ei],
                       signal_i=i,entry_i=ei,side=d,atr=float(BA[i]),oi_change=float(oich),
                       feature=float(abs(move)),detail='2ATR shock + OI collapse + 0.25ATR pullback + renewed extreme break'))

# C2: COMPRESSION -> ACCEPTED EXPANSION
# 24h range/ATR <= TRAIN q30. First close outside prior24h range + next close also outside on same side.
last=-9999
for i in range(R24+1,len(b)-MAX_H*12-3):
    if not(np.isfinite(b.comp24.iloc[i]) and b.comp24.iloc[i]<=COMP_Q30):continue
    if i-last<24:continue
    up=BC[i]>r24h[i];dn=BC[i]<r24l[i]
    if up==dn:continue
    d=1 if up else -1;boundary=float(r24h[i] if up else r24l[i])
    # acceptance: at least 2 of next 3 closes remain outside, including one immediate bar
    outs=[]
    for j in range(i+1,min(i+4,len(b))):
        outs.append(BC[j]>boundary if d>0 else BC[j]<boundary)
    if len(outs)<3 or sum(outs)<2:continue
    # enter after 3-bar acceptance observation
    ei=i+4;last=i
    events.append(dict(mech='COMP_ACCEPT',signal_time=BT.iloc[i],entry_time=BT.iloc[ei],
                       signal_i=i,entry_i=ei,side=d,atr=float(BA[i]),oi_change=np.nan,
                       feature=float(b.comp24.iloc[i]),detail='24h compression q30 + close breakout + 2/3 acceptance'))

# C3: 48H BREAKOUT ACCEPTANCE
# First close outside frozen 48h boundary, then >=4/6 next closes outside.
last=-9999
for i in range(R48+1,len(b)-MAX_H*12-7):
    if i-last<24:continue
    up=BC[i]>r48h[i];dn=BC[i]<r48l[i]
    if up==dn:continue
    d=1 if up else -1;boundary=float(r48h[i] if up else r48l[i])
    outs=[(BC[j]>boundary if d>0 else BC[j]<boundary) for j in range(i+1,i+7)]
    if sum(outs)<4:continue
    ei=i+7;last=i
    events.append(dict(mech='R48_ACCEPT',signal_time=BT.iloc[i],entry_time=BT.iloc[ei],
                       signal_i=i,entry_i=ei,side=d,atr=float(BA[i]),oi_change=np.nan,
                       feature=float((BC[i]-boundary)/BA[i]*d),detail='48h close breakout + >=4/6 closes accepted outside'))

ev=pd.DataFrame(events).sort_values('entry_time').reset_index(drop=True)
ev['nearest_base_h']=ev.entry_time.map(nearest_base_h)
ev['overlap12']=ev.nearest_base_h<=12
ev.to_csv(OUT/'LAB136_events.csv',index=False)

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
    net=float(gross-(cost/10000.0)*entry/atr)
    return net,reason,xi

# Standalone, unique-only, and portfolio increment.
summary=[];alltr=[]
for cost in COSTS:
  for mech in ['POST_DELEV_CONT','COMP_ACCEPT','R48_ACCEPT']:
    for unique_only in [False,True]:
      s=ev[ev.mech==mech].copy()
      if unique_only:s=s[~s.overlap12]
      s=s.sort_values('entry_time')
      open_until=pd.Timestamp.min.tz_localize('UTC');rows=[]
      for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi=sim_one(r,cost);xt=BT.iloc[xi];open_until=xt
        rows.append(dict(cost_bps=cost,mech=mech,unique_only=unique_only,signal_time=r.signal_time,
                         entry_time=r.entry_time,exit_time=xt,side='BUY' if r.side>0 else 'SELL',
                         net_r=net,reason=reason,overlap12=r.overlap12))
      t=pd.DataFrame(rows)
      if t.empty:continue
      alltr.append(t)
      pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
      months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
      ce=t.net_r.cumsum();dd=float((ce.cummax()-ce).max())
      summary.append(dict(cost_bps=cost,mech=mech,unique_only=unique_only,n=len(t),trades_month=len(t)/months,
                          ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                          wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),
                          r_month=float(t.net_r.sum()/months),realized_dd_r=dd,
                          buy_n=int((t.side=='BUY').sum()),sell_n=int((t.side=='SELL').sum())))
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB136_standalone_summary.csv',index=False)
if alltr:pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB136_standalone_trades.csv',index=False)

# Portfolio add-one-at-a-time against frozen A+B3_HIGH, one-position chronology.
port=[]
for cost in COSTS:
    base=frozen_ab3(cost)
    base_rows=[dict(source='BASE',entry_time=r.entry_time,exit_time=r.exit_time,net_r=float(r.net_r)) for _,r in base.iterrows()]
    for mech in ['POST_DELEV_CONT','COMP_ACCEPT','R48_ACCEPT']:
        cand=ev[(ev.mech==mech)&(~ev.overlap12)].copy()
        crows=[]
        for _,r in cand.iterrows():
            net,reason,xi=sim_one(r,cost)
            crows.append(dict(source=mech,entry_time=r.entry_time,exit_time=BT.iloc[xi],net_r=net))
        pool=pd.DataFrame(base_rows+crows).sort_values(['entry_time','source'])
        open_until=pd.Timestamp.min.tz_localize('UTC');acc=[]
        for _,r in pool.iterrows():
            if r.entry_time<open_until:continue
            open_until=r.exit_time;acc.append(r)
        t=pd.DataFrame(acc)
        pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
        months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
        ce=t.net_r.cumsum();dd=float((ce.cummax()-ce).max())
        n_c=int((t.source==mech).sum())
        port.append(dict(cost_bps=cost,mech=mech,n=len(t),candidate_accepted=n_c,
                         trades_month=len(t)/months,incremental_trades_month=n_c/months,
                         ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                         r_month=float(t.net_r.sum()/months),dd_r=dd))
pd.DataFrame(port).to_csv(OUT/'LAB136_portfolio_addon.csv',index=False)

# Overlap table
ov=[]
for mech,g in ev.groupby('mech'):
    ov.append(dict(mech=mech,raw_n=len(g),overlap12_n=int(g.overlap12.sum()),
                   overlap12_pct=float(g.overlap12.mean()),unique_n=int((~g.overlap12).sum()),
                   unique_pct=float((~g.overlap12).mean())))
pd.DataFrame(ov).to_csv(OUT/'LAB136_overlap.csv',index=False)

lines=['# LAB136 — MISSED OPPORTUNITY ATLAS','',
       'Goal: find an additional mechanism that can add roughly +2–4 UNIQUE trades/month with <=25% temporal overlap versus frozen Engine A+B3_HIGH.',
       'Protocol: BTC TRAIN only. No BTC OOS returns are used. Engine A and B3_HIGH are untouched.','',
       'Predeclared candidate territories:',
       '- POST_DELEV_CONT: post-deleveraging continuation, the opposite hypothesis to rejected B2 fade.',
       '- COMP_ACCEPT: 24h compression (TRAIN q30) followed by accepted expansion.',
       '- R48_ACCEPT: 48h boundary breakout followed by 4-of-6 M5 close acceptance outside the old range.',
       f'- Compression q30 threshold = {COMP_Q30:.3f} x H1ATR; 120m OI-drop Q75 = {OI120_Q75:.3%}.','',
       '## Overlap']
for r in ov:
    lines.append(f"- {r['mech']}: raw N={r['raw_n']}, overlap<=12h={r['overlap12_pct']:.1%}, unique={r['unique_pct']:.1%}")
lines += ['','## Unique-only TRAIN execution @2.81bps']
for mech in ['POST_DELEV_CONT','COMP_ACCEPT','R48_ACCEPT']:
    q=sm[(sm.cost_bps==2.81)&(sm.mech==mech)&(sm.unique_only==True)]
    if len(q):
        r=q.iloc[0]
        lines.append(f"- {mech}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, DD={r.realized_dd_r:.1f}R, BUY/SELL={int(r.buy_n)}/{int(r.sell_n)}")
lines += ['','## Add-on portfolio effect']
pp=pd.DataFrame(port)
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for mech in ['POST_DELEV_CONT','COMP_ACCEPT','R48_ACCEPT']:
        q=pp[(pp.cost_bps==cost)&(pp.mech==mech)]
        if len(q):
            r=q.iloc[0]
            lines.append(f"- +{mech}: accepted +{int(r.candidate_accepted)} ({r.incremental_trades_month:.2f}/mo), portfolio PF={r.pf:.2f}, EV={r.ev:+.3f}R, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R")
lines += ['','## Decision rule',
          'A candidate qualifies for next preregistered LAB only if unique frequency is near the +2–4/month target, overlap <=25%, and edge remains positive after 7.5bps without materially damaging portfolio PF/DD.',
          'This atlas does not authorize threshold tuning on BTC.']
(OUT/'LAB136_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB136_meta.json').write_text(json.dumps(dict(
    protocol='BTC TRAIN only; no BTC OOS inspection',
    target='2-4 unique trades/month, <=25% overlap with A+B3_HIGH',
    candidates=['POST_DELEV_CONT','COMP_ACCEPT','R48_ACCEPT'],
    compression_q30=COMP_Q30,oi120_q75=OI120_Q75,
    execution='SL1 H1ATR TP3R max48h stop-first',
    caveat='atlas only; no candidate thresholds may be tuned on BTC'
),indent=2))
print('\n'.join(lines))
