#!/usr/bin/env python3
from __future__ import annotations
import json, re, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

OUT=Path("lab130_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
COSTS=[2.81,7.5]

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
            if not n.lower().endswith(".csv"):continue
            with z.open(n) as fh:
                d=pd.read_csv(fh)
            if len(d):fs.append(d)
        if not fs:raise RuntimeError(f"no csv in {zp}")
        if len(fs)==1:return fs[0]
        common=set(fs[0].columns)
        for d in fs[1:]:common&=set(d.columns)
        cols=list(common)
        return pd.concat([d[cols] for d in fs],ignore_index=True)
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        unit='ns' if med>1e17 else ('us' if med>1e14 else ('ms' if med>1e11 else 's'))
        return pd.to_datetime(x,unit=unit,utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# ---------------- data ----------------
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time']); rc=pick(f.columns,['count_long_short_ratio']); oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
f=f[[tc,rc,oic]].copy()
f['time']=ptime(f[tc]); f['ratio']=pd.to_numeric(f[rc],errors='coerce'); f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna().sort_values('time').drop_duplicates('time',keep='last')
f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean(); sd=f.ratio.rolling(72,min_periods=72).std(ddof=0)
f['z']=(f.ratio-mu)/sd.replace(0,np.nan)

r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']); po=pick(r.columns,['open']); ph=pick(r.columns,['high']); pl=pick(r.columns,['low']); pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy(); p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# TRAIN only from this point onward. BTC OOS is not inspected.
p=p[p.time<TRAIN_END].copy().reset_index(drop=True)
f=f[f.time<TRAIN_END].copy().reset_index(drop=True)

# H1 ATR for stop buffer and normalization.
h1=p.set_index('time').resample('1h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean(); h1['close_time']=h1.time+pd.Timedelta(hours=1)

# H4 no-trend diagnostics.
h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean()
prev=h4.close.shift(1)
htr=pd.concat([(h4.high-h4.low),(h4.high-prev).abs(),(h4.low-prev).abs()],axis=1).max(axis=1)
h4['atr14']=htr.rolling(14,min_periods=14).mean()
h4['slope6_atr']=(h4.ema50-h4.ema50.shift(6)).abs()/h4.atr14
sign=np.sign(h4.close-h4.ema50)
cross=(sign!=sign.shift(1)) & sign.ne(0) & sign.shift(1).ne(0)
h4['crosses12']=cross.astype(int).rolling(12,min_periods=12).sum()
h4['close_time']=h4.time+pd.Timedelta(hours=4)

b=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr']].dropna().sort_values('close_time'),
                left_on='time',right_on='close_time',direction='backward')
b=pd.merge_asof(b.sort_values('time'),h4[['close_time','slope6_atr','crosses12']].dropna().sort_values('close_time'),
                left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
b=pd.merge_asof(b.sort_values('time'),f[['time','z']].dropna().sort_values('time'),
                on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b=b.dropna(subset=['atr','slope6_atr','crosses12','z']).reset_index(drop=True)

# Prior 48h range, strictly excluding current bar.
R=48*12
b['range_high']=b.high.shift(1).rolling(R,min_periods=R).max()
b['range_low']=b.low.shift(1).rolling(R,min_periods=R).min()
b=b.dropna(subset=['range_high','range_low']).reset_index(drop=True)

BT=b.time.reset_index(drop=True); BO=b.open.to_numpy(float); BH=b.high.to_numpy(float); BL=b.low.to_numpy(float); BC=b.close.to_numpy(float); BA=b.atr.to_numpy(float); BZ=b.z.to_numpy(float)
RH=b.range_high.to_numpy(float); RL=b.range_low.to_numpy(float)

# Predeclared range-regime atlas variants. No return-fitted threshold search.
REGIMES={
    'LOOSE':  dict(max_slope=.40,min_crosses=1),
    'BASE':   dict(max_slope=.25,min_crosses=2),
    'STRICT': dict(max_slope=.15,min_crosses=3),
}

# Fresh crowd extreme must already exist at breakout or have appeared in prior 30 minutes.
def fresh_crowd_recent(i,break_dir):
    j0=max(1,i-6)
    for j in range(j0,i+1):
        if abs(BZ[j])>=1 and abs(BZ[j-1])<1:
            crowd_dir=1 if BZ[j]>0 else -1
            if crowd_dir==break_dir:return True,j
    return False,None

# Breakout = wick pierces prior 48h boundary. Re-entry = first M5 close back inside frozen prior range within 4h.
events=[]
for regime,rr in REGIMES.items():
  for i in range(1,len(b)-48*12-2):
    if b.slope6_atr.iloc[i]>rr['max_slope'] or b.crosses12.iloc[i]<rr['min_crosses']: continue
    up=BH[i]>RH[i]; dn=BL[i]<RL[i]
    if up==dn: continue
    break_dir=1 if up else -1
    ok,z_i=fresh_crowd_recent(i,break_dir)
    if not ok:continue
    upper=float(RH[i]); lower=float(RL[i]); mid=(upper+lower)/2
    extreme=float(BH[i] if up else BL[i])
    re=None
    for j in range(i,min(i+4*12,len(b)-2)+1):
        if up:
            extreme=max(extreme,float(BH[j]))
            if BC[j]<upper: re=j;break
        else:
            extreme=min(extreme,float(BL[j]))
            if BC[j]>lower: re=j;break
    if re is None:continue
    ei=re+1; entry=float(BO[ei]); atr=float(BA[i])
    # stop beyond excursion extreme by 0.10 H1 ATR. Target = frozen 48h midpoint.
    stop=(extreme+0.10*atr) if up else (extreme-0.10*atr)
    side=-1 if up else 1
    risk=abs(entry-stop); reward=abs(mid-entry)
    rr_ratio=reward/risk if risk>0 else np.nan
    events.append(dict(regime=regime,signal_i=i,z_i=z_i,reentry_i=re,entry_i=ei,
                       signal_time=BT.iloc[i],reentry_time=BT.iloc[re],entry_time=BT.iloc[ei],
                       side=side,break_dir=break_dir,z=float(BZ[z_i]),atr=atr,
                       range_high=upper,range_low=lower,range_mid=mid,range_width_atr=(upper-lower)/atr,
                       breakout_extreme=extreme,entry=entry,stop=stop,target=mid,risk=risk,reward=reward,rr=rr_ratio,
                       breakout_depth_atr=((extreme-upper)/atr if up else (lower-extreme)/atr),
                       reentry_delay_min=(BT.iloc[re]-BT.iloc[i]).total_seconds()/60,
                       slope6_atr=float(b.slope6_atr.iloc[i]),crosses12=float(b.crosses12.iloc[i])))
ev=pd.DataFrame(events)
ev.to_csv(OUT/'LAB130_B1_train_events.csv',index=False)

# Descriptive TRAIN atlas, including all and prop-compatible RR>=1.5.
atlas=[]
for regime in REGIMES:
    for scope,dd in [('ALL',ev[ev.regime==regime]),('RR15',ev[(ev.regime==regime)&(ev.rr>=1.5)])]:
      for hold_h in [6,12,24,48]:
        vals=[]
        for _,r in dd.iterrows():
            ei=int(r.entry_i);end=min(ei+hold_h*12-1,len(b)-1);side=int(r.side);entry=float(r.entry);risk=float(r.risk)
            if risk<=0:continue
            close=side*(float(BC[end])-entry)/risk
            mfe=((float(np.max(BH[ei:end+1]))-entry)/risk if side>0 else (entry-float(np.min(BL[ei:end+1])))/risk)
            mae=((entry-float(np.min(BL[ei:end+1])))/risk if side>0 else (float(np.max(BH[ei:end+1]))-entry)/risk)
            vals.append((close,mfe,mae))
        if vals:
            a=np.asarray(vals,float)
            atlas.append(dict(regime=regime,scope=scope,hold_h=hold_h,n=len(a),
                              mean_close_r=float(a[:,0].mean()),median_close_r=float(np.median(a[:,0])),
                              mean_mfe_r=float(a[:,1].mean()),mean_mae_r=float(a[:,2].mean()),
                              p_close_positive=float((a[:,0]>0).mean())))
pd.DataFrame(atlas).to_csv(OUT/'LAB130_B1_train_atlas.csv',index=False)

# Frozen execution: only RR>=1.5 to respect production rule. SL beyond excursion, TP at midpoint.
def sim_event(r,cost,max_hold_h=48):
    ei=int(r.entry_i);side=int(r.side);entry=float(r.entry);stop=float(r.stop);target=float(r.target);risk=float(r.risk)
    end=min(ei+max_hold_h*12-1,len(b)-1)
    gross=side*(BC[end]-entry)/risk; reason='TIME'; xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=stop) if side>0 else (BH[j]>=stop)
        ht=(BH[j]>=target) if side>0 else (BL[j]<=target)
        if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
        if hs:gross=-1;reason='SL';xi=j;break
        if ht:gross=float(r.rr);reason='TP_MID';xi=j;break
    net=float(gross-(cost/10000.0)*entry/risk)
    return net,reason,xi

summary=[];trades=[]
for cost in COSTS:
  for regime in REGIMES:
    s=ev[(ev.regime==regime)&(ev.rr>=1.5)].sort_values('entry_time')
    open_until=pd.Timestamp.min.tz_localize('UTC');rows=[]
    for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi=sim_event(r,cost); xt=BT.iloc[xi];open_until=xt
        rows.append(dict(cost_bps=cost,regime=regime,signal_time=r.signal_time,entry_time=r.entry_time,exit_time=xt,
                         side='BUY' if r.side>0 else 'SELL',net_r=net,reason=reason,rr=r.rr,
                         breakout_depth_atr=r.breakout_depth_atr,reentry_delay_min=r.reentry_delay_min,
                         range_width_atr=r.range_width_atr,slope6_atr=r.slope6_atr,crosses12=r.crosses12))
    t=pd.DataFrame(rows)
    if t.empty:continue
    trades.append(t)
    pos=t.loc[t.net_r>0,'net_r'].sum(); neg=-t.loc[t.net_r<0,'net_r'].sum()
    months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
    ce=t.net_r.cumsum();ddr=float((ce.cummax()-ce).max())
    summary.append(dict(cost_bps=cost,regime=regime,n=len(t),trades_month=len(t)/months,
                        ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                        wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),
                        r_month=float(t.net_r.sum()/months),realized_dd_r=ddr,
                        median_rr=float(t.rr.median()),tp_rate=float((t.reason=='TP_MID').mean()),
                        sl_rate=float(t.reason.isin(['SL','BOTH_STOP_FIRST']).mean()),
                        time_rate=float((t.reason=='TIME').mean())))
sm=pd.DataFrame(summary); sm.to_csv(OUT/'LAB130_B1_train_execution.csv',index=False)
if trades:pd.concat(trades,ignore_index=True).to_csv(OUT/'LAB130_B1_train_trades.csv',index=False)

# Event anatomy bins, TRAIN only. Descriptive; no promotion thresholds yet.
anat=[]
d=ev[ev.regime=='BASE'].copy()
d['depth_bin']=pd.cut(d.breakout_depth_atr,[-1,.1,.25,.5,1,999],labels=['<=.1','.1-.25','.25-.5','.5-1','1+'])
d['delay_bin']=pd.cut(d.reentry_delay_min,[-1,15,30,60,120,240],labels=['<=15','15-30','30-60','60-120','120-240'])
d['width_bin']=pd.qcut(d.range_width_atr,4,duplicates='drop')
d['z_abs_bin']=pd.cut(d.z.abs(),[1,1.25,1.5,2,999],labels=['1-1.25','1.25-1.5','1.5-2','2+'])
for dim in ['depth_bin','delay_bin','width_bin','z_abs_bin']:
    for grp,g in d.groupby(dim,observed=True):
        gg=g[g.rr>=1.5]
        if len(gg)<20:continue
        vals=[]
        for _,r in gg.iterrows():
            net,reason,xi=sim_event(r,2.81)
            vals.append(net)
        arr=np.asarray(vals,float);pos=arr[arr>0].sum();neg=-arr[arr<0].sum()
        anat.append(dict(dimension=dim,group=str(grp),n=len(arr),ev=float(arr.mean()),
                         pf=float(pos/neg) if neg>0 else np.inf,wr=float((arr>0).mean())))
pd.DataFrame(anat).to_csv(OUT/'LAB130_B1_anatomy.csv',index=False)

lines=['# LAB130 — B1 FALSE RANGE BREAK','',
       'Protocol: BTC TRAIN only. BTC OOS returns are intentionally not used.',
       'Mechanism: non-trending H4 range -> crowd chases a boundary break -> price closes back inside -> fade toward frozen 48h midpoint.',
       '',
       '## Frozen event definition',
       '- prior 48h high/low excludes the current M5 bar',
       '- fresh |Z|>=1 in breakout direction, occurring on breakout bar or within prior 30m',
       '- breakout = M5 wick beyond frozen boundary',
       '- re-entry = first M5 close back inside frozen range within 4h',
       '- entry = next M5 open',
       '- stop = excursion extreme + 0.10 H1ATR buffer',
       '- target = frozen 48h midpoint',
       '- trade only if entry target/stop RR >= 1.5',
       '- max research hold = 48h; same-bar ambiguity stop-first',
       '',
       '## Predeclared H4 range regimes',
       '- LOOSE: |EMA50 slope over 6 H4 bars| <= 0.40 H4ATR and >=1 EMA cross in prior 12 H4 bars',
       '- BASE: <= 0.25 H4ATR and >=2 crosses',
       '- STRICT: <= 0.15 H4ATR and >=3 crosses',
       '',
       '## TRAIN execution']
for cost in COSTS:
    for regime in REGIMES:
        q=sm[(sm.cost_bps==cost)&(sm.regime==regime)]
        if len(q):
            r=q.iloc[0]
            lines.append(f"- {cost:.2f}bps / {regime}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, medianRR={r.median_rr:.2f}, R/mo={r.r_month:+.2f}, DD={r.realized_dd_r:.1f}R")
lines += ['', '## Decision discipline',
          'This LAB is an atlas on BTC TRAIN only. No BTC OOS acceptance/rejection is permitted.',
          'If a regime shows a material TRAIN edge, freeze ONE candidate definition before any cross-symbol validation.',
          'B1 is a distinct no-trend mechanism and is not allowed to borrow rejected CrowdFade filters from Engine A.']
(OUT/'LAB130_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB130_meta.json').write_text(json.dumps(dict(
    protocol='BTC TRAIN only; no BTC OOS inspection',
    ratio_field='count_long_short_ratio',
    z_window='72xM5 = 6h',
    range='prior 48h high/low, shifted 1 bar',
    regimes=REGIMES,
    reentry_window_hours=4,
    stop='excursion extreme +/- 0.10 H1 ATR',
    target='frozen prior-48h midpoint',
    rr_filter='>=1.5',
    costs=COSTS,
    caveat='TRAIN atlas only; candidate must be frozen before later external validation'
),indent=2))
print('\n'.join(lines))
