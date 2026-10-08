#!/usr/bin/env python3
from __future__ import annotations
import json, re, zipfile
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab132_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
COSTS=[2.81,7.5]
DEPTHS=[0.50,0.75,1.00]
SEARCH_ATTACK_BARS=72   # 6h
SEARCH_RECLAIM_BARS=72  # 6h
MAX_H=48
Z_STRENGTH_MIN=0.25

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
            if not n.lower().endswith('.csv'): continue
            with z.open(n) as fh:
                d=pd.read_csv(fh)
            if len(d):fs.append(d)
        if not fs:raise RuntimeError(f'no csv in {zp}')
        if len(fs)==1:return fs[0]
        common=set(fs[0].columns)
        for d in fs[1:]:common &= set(d.columns)
        return pd.concat([d[list(common)] for d in fs],ignore_index=True)
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        unit='ns' if med>1e17 else ('us' if med>1e14 else ('ms' if med>1e11 else 's'))
        return pd.to_datetime(x,unit=unit,utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# ---------------- Data: explicit research ratio ----------------
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time'])
rc=pick(f.columns,['count_long_short_ratio'])
oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
if tc is None or rc is None or oic is None: raise RuntimeError('required flow columns missing')
f=f[[tc,rc,oic]].copy()
f['time']=ptime(f[tc]); f['ratio']=pd.to_numeric(f[rc],errors='coerce'); f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna().sort_values('time').drop_duplicates('time',keep='last')
f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean()
sd=f.ratio.rolling(72,min_periods=72).std(ddof=0)
f['z']=(f.ratio-mu)/sd.replace(0,np.nan)

r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']); po=pick(r.columns,['open']); ph=pick(r.columns,['high']); pl=pick(r.columns,['low']); pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy(); p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# Strict TRAIN-only research. Do not inspect BTC OOS returns.
p=p[p.time<TRAIN_END].copy().reset_index(drop=True)
f=f[f.time<TRAIN_END].copy().reset_index(drop=True)

# H1 ATR, causal closed-bar context.
h1=p.set_index('time').resample('1h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean()
h1['close_time']=h1.time+pd.Timedelta(hours=1)

# Frozen Engine-A family H4 trend logic, used only as regime context.
h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean()
h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,
                     np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
age=[];cur=0;pv=0
for v in h4.trend:
    if v!=0 and v==pv:cur+=1
    elif v!=0:cur=1
    else:cur=0
    age.append(cur);pv=v
h4['trend_age']=age
h4['close_time']=h4.time+pd.Timedelta(hours=4)

b=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr']].dropna().sort_values('close_time'),
                left_on='time',right_on='close_time',direction='backward')
b=pd.merge_asof(b.sort_values('time'),h4[['close_time','trend','trend_age']].dropna().sort_values('close_time'),
                left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
b=pd.merge_asof(b.sort_values('time'),f[['time','z','oi']].dropna().sort_values('time'),
                on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b=b.dropna(subset=['atr','trend','trend_age','z','oi']).reset_index(drop=True)

BT=b.time.reset_index(drop=True); BO=b.open.to_numpy(float); BH=b.high.to_numpy(float); BL=b.low.to_numpy(float)
BC=b.close.to_numpy(float); BA=b.atr.to_numpy(float); BZ=b.z.to_numpy(float); BOI=b.oi.to_numpy(float)

def first_milestones(i,trend,atr,depth):
    # Attack direction is countertrend. Milestones every 0.1 ATR from signal close.
    anchor=float(BC[i]); n=int(round(depth/0.10))
    hits=[]; levels=[]
    for k in range(1,n+1):
        d=0.10*k
        level=anchor-trend*d*atr
        levels.append(level)
        hit=None
        start=i+1 if not hits else hits[-1]
        for j in range(start,min(i+SEARCH_ATTACK_BARS,len(b)-2)+1):
            touched=(BL[j]<=level) if trend>0 else (BH[j]>=level)
            if touched:
                hit=j;break
        if hit is None:return None,None
        hits.append(hit)
    return hits,levels

def decay_features(i,hits):
    # Bars spent to earn each successive 0.1 ATR of countertrend progress.
    idx=[i]+list(hits)
    intervals=np.diff(np.asarray(idx,dtype=int)).astype(float)
    strict=bool(len(intervals)>=3 and np.all(np.diff(intervals)>0))
    nondec=bool(len(intervals)>=3 and np.all(np.diff(intervals)>=0) and intervals[-1]>intervals[0])
    first=intervals[:max(1,len(intervals)//2)]
    last=intervals[len(intervals)//2:]
    ratio=float(last.mean()/max(first.mean(),1e-9)) if len(last) else np.nan
    slope=float(np.polyfit(np.arange(len(intervals)),intervals,1)[0]) if len(intervals)>=2 else np.nan
    return intervals,strict,nondec,ratio,slope

events=[]
for i in range(1,len(b)-MAX_H*12-2):
    # Fresh crowd extreme.
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    trend=int(b.trend.iloc[i]); age=int(b.trend_age.iloc[i])
    if trend==0 or age<4:continue  # established H4 trend
    crowd_dir=1 if BZ[i]>0 else -1
    if crowd_dir!=-trend:continue  # crowd attacks countertrend
    z0=float(BZ[i]);oi0=float(BOI[i]);atr=float(BA[i])
    for depth in DEPTHS:
        hits,levels=first_milestones(i,trend,atr,depth)
        if hits is None:continue
        hit=hits[-1]
        zh=float(BZ[hit]);oih=float(BOI[hit])
        z_strength=(abs(zh)-abs(z0)) if np.sign(zh)==crowd_dir else -abs(z0)
        oi_change=oih/oi0-1.0 if oi0>0 else np.nan
        # B3 requires crowd + OI to strengthen during the attack.
        if not(z_strength>=Z_STRENGTH_MIN and np.isfinite(oi_change) and oi_change>0):continue

        intervals,strict,nondec,decay_ratio,decay_slope=decay_features(i,hits)

        # Start of final 0.1ATR wave = previous milestone.
        if len(levels)<2:continue
        last_wave_start=float(levels[-2])
        reclaim=None
        for j in range(hit,min(hit+SEARCH_RECLAIM_BARS,len(b)-2)+1):
            ok=(BC[j]>last_wave_start) if trend>0 else (BC[j]<last_wave_start)
            if ok:
                reclaim=j;break
        if reclaim is None:continue
        ei=reclaim+1
        events.append(dict(
            depth=depth,signal_i=i,hit_i=hit,reclaim_i=reclaim,entry_i=ei,
            signal_time=BT.iloc[i],hit_time=BT.iloc[hit],reclaim_time=BT.iloc[reclaim],entry_time=BT.iloc[ei],
            side=trend,trend=trend,trend_age=age,atr=atr,z0=z0,z_hit=zh,z_strength=z_strength,
            oi_change=oi_change,attack_bars=hit-i,reclaim_bars=reclaim-hit,
            intervals='|'.join(str(int(x)) for x in intervals),
            strict_decay=strict,nondecreasing_decay=nondec,decay_ratio=decay_ratio,decay_slope=decay_slope,
            last_wave_start=last_wave_start,entry=float(BO[ei])
        ))

ev=pd.DataFrame(events)
ev.to_csv(OUT/'LAB132_B3_train_events.csv',index=False)

# Predeclared mechanism gates. STRICT is the user's primary B3 definition.
GATES={
    'CONTROL_ZOI':lambda d:pd.Series(True,index=d.index),
    'STRICT_DECAY':lambda d:d.strict_decay,
    'NONDECREASING_DECAY':lambda d:d.nondecreasing_decay,
    'LATE_DECAY_1P5':lambda d:d.decay_ratio>=1.5,
    'POSITIVE_SLOPE':lambda d:d.decay_slope>0,
}

# Descriptive close/MFE/MAE atlas before execution.
atlas=[]
for depth in DEPTHS:
  d0=ev[ev.depth==depth]
  for gate,fn in GATES.items():
    d=d0[fn(d0)]
    for hold_h in [6,12,24,48]:
      vals=[]
      for _,r in d.iterrows():
        ei=int(r.entry_i);end=min(ei+hold_h*12-1,len(b)-1);side=int(r.side);atr=float(r.atr);entry=float(BO[ei])
        close=side*(float(BC[end])-entry)/atr
        mfe=((float(np.max(BH[ei:end+1]))-entry)/atr if side>0 else (entry-float(np.min(BL[ei:end+1])))/atr)
        mae=((entry-float(np.min(BL[ei:end+1])))/atr if side>0 else (float(np.max(BH[ei:end+1]))-entry)/atr)
        vals.append((close,mfe,mae))
      if vals:
        a=np.asarray(vals,float)
        atlas.append(dict(depth=depth,gate=gate,hold_h=hold_h,n=len(a),
                          mean_close_atr=float(a[:,0].mean()),median_close_atr=float(np.median(a[:,0])),
                          mean_mfe_atr=float(a[:,1].mean()),mean_mae_atr=float(a[:,2].mean()),
                          p_close_positive=float((a[:,0]>0).mean())))
pd.DataFrame(atlas).to_csv(OUT/'LAB132_B3_train_atlas.csv',index=False)

# Frozen execution: same shell as Engine A to isolate signal quality.
def sim_one(ei,side,atr,cost):
    entry=float(BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(b)-1)
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
  for depth in DEPTHS:
    d0=ev[ev.depth==depth]
    for gate,fn in GATES.items():
      s=d0[fn(d0)].sort_values('entry_time')
      open_until=pd.Timestamp.min.tz_localize('UTC');rows=[]
      for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi=sim_one(int(r.entry_i),int(r.side),float(r.atr),cost);xt=BT.iloc[xi];open_until=xt
        rows.append(dict(cost_bps=cost,depth=depth,gate=gate,signal_time=r.signal_time,entry_time=r.entry_time,exit_time=xt,
                         side='BUY' if r.side>0 else 'SELL',net_r=net,reason=reason,trend_age=r.trend_age,
                         attack_bars=r.attack_bars,reclaim_bars=r.reclaim_bars,decay_ratio=r.decay_ratio,decay_slope=r.decay_slope,
                         z_strength=r.z_strength,oi_change=r.oi_change))
      t=pd.DataFrame(rows)
      if t.empty:continue
      alltr.append(t)
      pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
      months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
      ce=t.net_r.cumsum();ddr=float((ce.cummax()-ce).max())
      summary.append(dict(cost_bps=cost,depth=depth,gate=gate,n=len(t),trades_month=len(t)/months,
                          ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                          wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),r_month=float(t.net_r.sum()/months),
                          realized_dd_r=ddr,tp_rate=float((t.reason=='TP').mean()),
                          sl_rate=float(t.reason.isin(['SL','BOTH_STOP_FIRST']).mean()),time_rate=float((t.reason=='TIME').mean())))
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB132_B3_train_execution.csv',index=False)
if alltr:pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB132_B3_train_trades.csv',index=False)

# Comparison: does decay add value over CONTROL_ZOI at same depth?
comp=[]
for cost in COSTS:
  for depth in DEPTHS:
    c=sm[(sm.cost_bps==cost)&(sm.depth==depth)&(sm.gate=='CONTROL_ZOI')]
    if not len(c):continue
    c=c.iloc[0]
    for gate in ['STRICT_DECAY','NONDECREASING_DECAY','LATE_DECAY_1P5','POSITIVE_SLOPE']:
        q=sm[(sm.cost_bps==cost)&(sm.depth==depth)&(sm.gate==gate)]
        if not len(q):continue
        q=q.iloc[0]
        comp.append(dict(cost_bps=cost,depth=depth,gate=gate,n=int(q.n),
                         ev=float(q.ev),pf=float(q.pf),delta_ev=float(q.ev-c.ev),delta_pf=float(q.pf-c.pf),
                         control_n=int(c.n),control_ev=float(c.ev),control_pf=float(c.pf)))
pd.DataFrame(comp).to_csv(OUT/'LAB132_B3_decay_increment.csv',index=False)

# TRAIN-only ranking is descriptive; PRIMARY decision is strict-decay vs same-depth control.
rank=sm[(sm.cost_bps==2.81)&(sm.n>=20)].copy()
rank['rank_score']=rank.ev.clip(-2,2)+0.15*np.log(rank.pf.clip(.1,10))
rank=rank.sort_values(['rank_score','pf','n'],ascending=False)
rank.to_csv(OUT/'LAB132_B3_train_ranking.csv',index=False)

lines=['# LAB132 — B3 COUNTERTREND ATTACK EXHAUSTION','',
       'Protocol: BTC TRAIN only. BTC OOS returns are intentionally not used.',
       'Mechanism: established H4 trend -> crowd attacks countertrend -> Z strengthens in attack direction + OI rises -> each next 0.1 H1ATR of countertrend progress takes longer -> reclaim of start of final attack wave -> continuation entry with H4 trend.',
       '',
       '## Frozen primary definition',
       '- established H4 trend: same EMA50/lag6 logic, trend age >=4 H4 bars',
       '- fresh |Z|>=1 with crowd direction opposite H4 trend',
       '- countertrend attack depth: 0.50 / 0.75 / 1.00 H1ATR, reached within 6h',
       f'- |Z| must strengthen by >= {Z_STRENGTH_MIN:.2f} by depth hit and retain attack sign',
       '- OI must increase from signal to depth hit',
       '- attack is divided into causal 0.1ATR milestones',
       '- PRIMARY STRICT_DECAY: every successive 0.1ATR interval requires strictly more M5 bars than the previous interval',
       '- reclaim = first M5 close back through the previous 0.1ATR milestone (start of final attack wave)',
       '- entry = next M5 open in H4 trend direction',
       '- execution shell frozen: SL=1 H1ATR, TP=3R, max48h, stop-first',
       '',
       '## TRAIN execution @ 2.81bps']
for depth in DEPTHS:
  for gate in ['CONTROL_ZOI','STRICT_DECAY','NONDECREASING_DECAY','LATE_DECAY_1P5','POSITIVE_SLOPE']:
    q=sm[(sm.cost_bps==2.81)&(sm.depth==depth)&(sm.gate==gate)]
    if len(q):
      r=q.iloc[0]
      lines.append(f"- depth {depth:.2f} / {gate}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, R/mo={r.r_month:+.2f}, DD={r.realized_dd_r:.1f}R")
lines += ['', '## Primary question: does strict velocity decay improve the same-depth control?']
cc=pd.DataFrame(comp)
for depth in DEPTHS:
    q=cc[(cc.cost_bps==2.81)&(cc.depth==depth)&(cc.gate=='STRICT_DECAY')]
    if len(q):
        r=q.iloc[0]
        lines.append(f"- {depth:.2f} ATR: STRICT N={int(r.n)}, PF={r.pf:.2f}, EV={r.ev:+.3f}R | control PF={r.control_pf:.2f}, EV={r.control_ev:+.3f}R | delta PF={r.delta_pf:+.2f}, delta EV={r.delta_ev:+.3f}R")
lines += ['', '## Decision discipline',
          'B3 survives only if velocity decay itself adds material TRAIN edge over the same Z+OI countertrend-attack control.',
          'Generic anti-crowd trend continuation remains rejected; CONTROL_ZOI is diagnostic only and cannot be promoted.',
          'No BTC OOS acceptance/rejection is permitted in this LAB.']
(OUT/'LAB132_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB132_meta.json').write_text(json.dumps(dict(
    protocol='BTC TRAIN only; no BTC OOS inspection',
    ratio_field='count_long_short_ratio',
    trend='causal H4 EMA50 + lag6, age>=4',
    depths=DEPTHS,
    z_strength_min=Z_STRENGTH_MIN,
    oi_rule='OI hit / OI signal - 1 > 0',
    primary_decay='successive 0.1 H1ATR milestone intervals strictly increasing in M5 bars',
    reclaim='close through prior 0.1ATR milestone after depth hit',
    execution='next M5, SL1 H1ATR, TP3R, max48h',
    costs=COSTS,
    caveat='CONTROL_ZOI is diagnostic only; generic trend continuation remains rejected'
),indent=2))
print('\n'.join(lines))
