#!/usr/bin/env python3
from __future__ import annotations
import json, re, zipfile
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab131_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
COSTS=[2.81,7.5]
LOOKBACKS={30:6,60:12,120:24}   # minutes -> M5 bars
OI_QS=[0.60,0.75,0.90]          # severity among negative OI changes; no return fitting
SEARCH_BARS=72                  # max 6h to reversal confirmation
MAX_H=48                        # max hold 48h
IMPULSE_ATR=2.0

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
            with z.open(n) as fh:
                d=pd.read_csv(fh)
            if len(d):fs.append(d)
        if not fs:raise RuntimeError(f'no csv in {zp}')
        if len(fs)==1:return fs[0]
        common=set(fs[0].columns)
        for d in fs[1:]:common&=set(d.columns)
        return pd.concat([d[list(common)] for d in fs],ignore_index=True)
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        unit='ns' if med>1e17 else ('us' if med>1e14 else ('ms' if med>1e11 else 's'))
        return pd.to_datetime(x,unit=unit,utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# ---------------- data ----------------
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time']); oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
if tc is None or oic is None: raise RuntimeError('required flow columns missing')
f=f[[tc,oic]].copy()
f['time']=ptime(f[tc]); f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna().sort_values('time').drop_duplicates('time',keep='last')
f=f[f.oi>0].set_index('time').resample('5min').last().dropna().reset_index()

r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']); po=pick(r.columns,['open']); ph=pick(r.columns,['high']); pl=pick(r.columns,['low']); pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy(); p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# TRAIN only. BTC OOS returns are not read.
p=p[p.time<TRAIN_END].copy().reset_index(drop=True)
f=f[f.time<TRAIN_END].copy().reset_index(drop=True)

# Causal H1 ATR: only last closed H1 bar is available to M5.
h1=p.set_index('time').resample('1h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean()
h1['close_time']=h1.time+pd.Timedelta(hours=1)

b=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr']].dropna().sort_values('close_time'),
                left_on='time',right_on='close_time',direction='backward')
b=pd.merge_asof(b.sort_values('time'),f[['time','oi']].dropna().sort_values('time'),
                on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b=b.dropna(subset=['atr','oi']).reset_index(drop=True)

BT=b.time.reset_index(drop=True); BO=b.open.to_numpy(float); BH=b.high.to_numpy(float); BL=b.low.to_numpy(float); BC=b.close.to_numpy(float); BA=b.atr.to_numpy(float); BOI=b.oi.to_numpy(float)

# TRAIN-only OI drop thresholds, derived mechanically from negative changes, no return fitting.
TH={}
for mins,bars in LOOKBACKS.items():
    ch=b.oi/b.oi.shift(bars)-1
    neg=(-ch[ch<0]).dropna()
    TH[mins]={q:float(neg.quantile(q)) for q in OI_QS}
(OUT/'LAB131_oi_drop_thresholds.json').write_text(json.dumps({str(k):{str(q):v for q,v in z.items()} for k,z in TH.items()},indent=2))

def swing3_entry(i,side):
    # side is intended reversal trade direction
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:return j+1,j,(BC[j]-ref)/BA[i]
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:return j+1,j,(ref-BC[j])/BA[i]
    return None,None,np.nan

# Event atlas. Event is a fresh causal cascade condition for a given horizon x OI severity.
events=[]
for mins,bars in LOOKBACKS.items():
  for q in OI_QS:
    xdrop=TH[mins][q]
    prev_cond=False
    last_kept=-10_000
    for i in range(max(bars,1),len(b)-MAX_H*12-2):
        price_move=(BC[i]-BC[i-bars])/BA[i]
        oi_ch=BOI[i]/BOI[i-bars]-1
        cond=(abs(price_move)>=IMPULSE_ATR and oi_ch<=-xdrop)
        fresh=cond and not prev_cond
        prev_cond=cond
        if not fresh: continue
        # suppress near-duplicate cascades of same variant for 6h
        if i-last_kept<72: continue
        impulse_side=1 if price_move>0 else -1
        trade_side=-impulse_side
        ei,ti,br=swing3_entry(i,trade_side)
        if ei is None:continue
        last_kept=i
        events.append(dict(horizon_min=mins,oi_q=q,oi_drop_thr=xdrop,signal_i=i,entry_i=ei,trigger_i=ti,
                           signal_time=BT.iloc[i],entry_time=BT.iloc[ei],impulse_side=impulse_side,side=trade_side,
                           price_move_atr=float(price_move),oi_change=float(oi_ch),atr=float(BA[i]),
                           break_strength=float(br),confirm_delay_min=(BT.iloc[ei]-BT.iloc[i]).total_seconds()/60))
ev=pd.DataFrame(events)
ev.to_csv(OUT/'LAB131_B2_train_events.csv',index=False)

# Descriptive event atlas before execution.
atlas=[]
for mins in LOOKBACKS:
  for q in OI_QS:
    d=ev[(ev.horizon_min==mins)&(ev.oi_q==q)]
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
            atlas.append(dict(horizon_min=mins,oi_q=q,hold_h=hold_h,n=len(a),
                              mean_close_atr=float(a[:,0].mean()),median_close_atr=float(np.median(a[:,0])),
                              mean_mfe_atr=float(a[:,1].mean()),mean_mae_atr=float(a[:,2].mean()),
                              p_close_positive=float((a[:,0]>0).mean())))
pd.DataFrame(atlas).to_csv(OUT/'LAB131_B2_train_atlas.csv',index=False)

# Frozen execution from hypothesis: next M5 after SWING3, SL 1 H1ATR, TP 3R, max48h, stop-first.
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
  for mins in LOOKBACKS:
    for q in OI_QS:
      s=ev[(ev.horizon_min==mins)&(ev.oi_q==q)].sort_values('entry_time')
      open_until=pd.Timestamp.min.tz_localize('UTC');rows=[]
      for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi=sim_one(int(r.entry_i),int(r.side),float(r.atr),cost);xt=BT.iloc[xi];open_until=xt
        rows.append(dict(cost_bps=cost,horizon_min=mins,oi_q=q,signal_time=r.signal_time,entry_time=r.entry_time,exit_time=xt,
                         side='BUY' if r.side>0 else 'SELL',net_r=net,reason=reason,
                         price_move_atr=r.price_move_atr,oi_change=r.oi_change,confirm_delay_min=r.confirm_delay_min))
      t=pd.DataFrame(rows)
      if t.empty:continue
      alltr.append(t)
      pos=t.loc[t.net_r>0,'net_r'].sum(); neg=-t.loc[t.net_r<0,'net_r'].sum()
      months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
      ce=t.net_r.cumsum();ddr=float((ce.cummax()-ce).max())
      summary.append(dict(cost_bps=cost,horizon_min=mins,oi_q=q,oi_drop_thr=TH[mins][q],n=len(t),
                          trades_month=len(t)/months,ev=float(t.net_r.mean()),
                          pf=float(pos/neg) if neg>0 else np.inf,wr=float((t.net_r>0).mean()),
                          total_r=float(t.net_r.sum()),r_month=float(t.net_r.sum()/months),realized_dd_r=ddr,
                          tp_rate=float((t.reason=='TP').mean()),sl_rate=float(t.reason.isin(['SL','BOTH_STOP_FIRST']).mean()),
                          time_rate=float((t.reason=='TIME').mean())))
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB131_B2_train_execution.csv',index=False)
if alltr:pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB131_B2_train_trades.csv',index=False)

# Anatomy of the neutral Q75 variant across impulse severity, OI collapse and side.
anat=[]
base=ev[ev.oi_q==0.75].copy()
base['impulse_bin']=pd.cut(base.price_move_atr.abs(),[2,2.5,3,4,6,999],labels=['2-2.5','2.5-3','3-4','4-6','6+'],include_lowest=True)
base['oi_drop_bin']=pd.cut(-base.oi_change,[0,.01,.02,.04,.08,.15,999],labels=['0-1%','1-2%','2-4%','4-8%','8-15%','15%+'])
base['delay_bin']=pd.cut(base.confirm_delay_min,[-1,15,30,60,120,360],labels=['<=15','15-30','30-60','60-120','120-360'])
base['impulse_dir']=np.where(base.impulse_side>0,'UP','DOWN')
for dim in ['impulse_bin','oi_drop_bin','delay_bin','impulse_dir']:
    for grp,g in base.groupby(dim,observed=True):
        if len(g)<20:continue
        vals=[]
        for _,r in g.iterrows():
            net,reason,xi=sim_one(int(r.entry_i),int(r.side),float(r.atr),2.81)
            vals.append(net)
        a=np.asarray(vals,float);pos=a[a>0].sum();neg=-a[a<0].sum()
        anat.append(dict(dimension=dim,group=str(grp),n=len(a),ev=float(a.mean()),
                         pf=float(pos/neg) if neg>0 else np.inf,wr=float((a>0).mean())))
pd.DataFrame(anat).to_csv(OUT/'LAB131_B2_anatomy.csv',index=False)

# TRAIN ranking only. This is an atlas, not promotion.
rank=sm[(sm.cost_bps==2.81)&(sm.n>=30)].copy()
rank['rank_score']=rank.ev.clip(-2,2)+0.15*np.log(rank.pf.clip(.1,10))
rank=rank.sort_values(['rank_score','pf','n'],ascending=False)
rank.to_csv(OUT/'LAB131_B2_train_ranking.csv',index=False)

lines=['# LAB131 — B2 DELEVERAGING CASCADE','',
       'Protocol: BTC TRAIN only. BTC OOS returns are intentionally not used.',
       'Mechanism: sharp directional price displacement + simultaneous OI collapse = deleveraging / liquidation-cascade proxy; after M5 structural reversal, fade the exhausted impulse.',
       'Important: this is NOT a direct liquidation feed, so the event is called a deleveraging-cascade proxy.',
       '',
       '## Frozen event skeleton',
       '- price displacement >= 2.0 causal H1 ATR',
       '- event windows: 30m / 60m / 120m (all satisfy <=2h)',
       '- OI must fall over the same window',
       '- OI-collapse severities are TRAIN-distribution quantiles Q60 / Q75 / Q90 among negative OI changes; no return fitting',
       '- fresh condition only; same-variant cascades deduplicated for 6h',
       '- H4 trend is NOT required',
       '- M5 SWING3 break against impulse -> next M5 open',
       '- SL=1 H1ATR, TP=3R, max48h, stop-first',
       '',
       '## TRAIN OI-drop thresholds']
for mins in LOOKBACKS:
    lines.append(f"- {mins}m: Q60={TH[mins][.60]:.3%}, Q75={TH[mins][.75]:.3%}, Q90={TH[mins][.90]:.3%}")
lines += ['', '## TRAIN execution @ 2.81bps']
for _,r in rank.head(12).iterrows():
    lines.append(f"- {int(r.horizon_min)}m / Q{int(round(r.oi_q*100))}: N={int(r.n)} ({r.trades_month:.2f}/mo), OI>={r.oi_drop_thr:.3%} drop, EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, R/mo={r.r_month:+.2f}, DD={r.realized_dd_r:.1f}R")
lines += ['', '## Decision discipline',
          'This is a BTC TRAIN atlas only. No BTC OOS acceptance/rejection is permitted.',
          'If one cascade definition is materially positive on TRAIN, freeze ONE candidate before later cross-symbol validation.',
          'Do not reinterpret OI collapse alone as an edge; the mechanism requires the joint price-shock + deleveraging event + structural reversal.']
(OUT/'LAB131_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB131_meta.json').write_text(json.dumps(dict(
    protocol='BTC TRAIN only; no BTC OOS inspection',
    mechanism='price shock + OI collapse + opposite M5 SWING3',
    price_impulse='>=2 H1 ATR',
    windows_minutes=list(LOOKBACKS.keys()),
    oi_quantiles=OI_QS,
    oi_thresholds={str(k):{str(q):v for q,v in z.items()} for k,z in TH.items()},
    execution='next M5 after opposite SWING3, SL1 H1ATR, TP3R, max48h',
    costs=COSTS,
    caveat='deleveraging proxy, not direct liquidation feed; TRAIN atlas only'
),indent=2))
print('\n'.join(lines))
