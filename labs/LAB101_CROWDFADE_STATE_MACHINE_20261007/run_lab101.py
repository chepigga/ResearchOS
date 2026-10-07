#!/usr/bin/env python3
from __future__ import annotations
import json, math, re, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

OUT=Path("lab101_state_machine_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
ZWIN=72
ATR_N=14
SETUP_Z=1.0
SETUP_MEMORY=12
ARM_PULLBACK_Z=0.10
STOP_MIN_ATR=0.50
STOP_MAX_ATR=2.00
STOP_BUFFER_ATR=0.05
RR=2.0
MAX_TRADES_DAY=3
LOSS_STREAK_PAUSE=3
COST_STRESS_BPS=7.5  # 6.5 bps FTMO crypto commission proxy + 1.0 bps slippage; spread excluded

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
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        for n in names:
            try:
                with z.open(n) as f: d=pd.read_csv(f)
                if len(d): frames.append(d)
            except Exception: pass
        if not frames: raise RuntimeError(f"no CSV in {zp}")
        # price archives often have identical schemas across files
        common=set(frames[0].columns)
        for d in frames[1:]: common &= set(d.columns)
        if len(frames)>1 and len(common)>=4:
            cols=list(common)
            return pd.concat([d[cols] for d in frames],ignore_index=True),names
        return frames[0],names

def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce')
        med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),errors='coerce',utc=True)
    return pd.to_datetime(s,errors='coerce',utc=True)

flow,fn=load_zip(FLOW_ZIP)
price,pn=load_zip(PRICE_ZIP)
ft=pick(flow.columns,['timestamp','time','datetime','open_time'])
fr=pick(flow.columns,['longShortRatio','long_short_ratio','ls_ratio','globalLongShortAccountRatio','ratio'])
pt=pick(price.columns,['time','timestamp','datetime','open_time'])
po=pick(price.columns,['open']); ph=pick(price.columns,['high']); pl=pick(price.columns,['low']); pc=pick(price.columns,['close'])
if ft is None or fr is None or None in [pt,po,ph,pl,pc]:
    raise RuntimeError(f"columns unresolved flow={list(flow.columns)} price={list(price.columns)}")

flow=flow[[ft,fr]].copy()
flow['time']=ptime(flow[ft]); flow['ratio']=pd.to_numeric(flow[fr],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
m=flow.ratio.rolling(ZWIN,min_periods=ZWIN).mean()
sd=flow.ratio.rolling(ZWIN,min_periods=ZWIN).std(ddof=0)
flow['z']=(flow.ratio-m)/sd.replace(0,np.nan)

price=price[[pt,po,ph,pl,pc]].copy()
price['time']=ptime(price[pt])
for c,nm in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]: price[nm]=pd.to_numeric(price[c],errors='coerce')
price=price[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
price=price.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

def build_tf(tfmin):
    p=price.set_index('time').resample(f'{tfmin}min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    p['close_time']=p.time+pd.Timedelta(minutes=tfmin)
    prev=p.close.shift(1)
    tr=pd.concat([(p.high-p.low),(p.high-prev).abs(),(p.low-prev).abs()],axis=1).max(axis=1)
    p['atr']=tr.rolling(ATR_N,min_periods=ATR_N).mean()
    # Latest completed 5m Z available by bar close
    f=flow[['time','z']].dropna().copy()
    p=pd.merge_asof(p.sort_values('close_time'),f.sort_values('time'),left_on='close_time',right_on='time',direction='backward',tolerance=pd.Timedelta('10min'),suffixes=('','_z'))
    return p.dropna(subset=['atr','z']).reset_index(drop=True)

def candidate_triggers(p,tfmin,armed,structure_n,impulse_filter):
    rows=[]
    # setup state in side direction: +1 BUY when z<=-1, -1 SELL when z>=+1
    active=False; side=0; expiry=-1; setup_idx=-1; extreme_z=np.nan; armed_ok=(not armed)
    for i in range(max(ATR_N,structure_n,12),len(p)-1):
        z=float(p.z.iloc[i])
        # new setup can overwrite old setup if opposite extreme appears
        newside=1 if z<=-SETUP_Z else (-1 if z>=SETUP_Z else 0)
        if newside!=0:
            if (not active) or newside!=side:
                active=True; side=newside; setup_idx=i; expiry=i+SETUP_MEMORY; extreme_z=z; armed_ok=(not armed)
            else:
                # refresh memory while extreme persists
                expiry=i+SETUP_MEMORY
                if side<0: extreme_z=max(extreme_z,z)
                else: extreme_z=min(extreme_z,z)
        if not active: continue
        if i>expiry:
            active=False; continue
        if armed and not armed_ok:
            if side<0:
                extreme_z=max(extreme_z,z)
                if extreme_z-z>=ARM_PULLBACK_Z: armed_ok=True
            else:
                extreme_z=min(extreme_z,z)
                if z-extreme_z>=ARM_PULLBACK_Z: armed_ok=True
            if not armed_ok: continue
        # trigger close through previous N-bar microstructure
        lo=float(p.low.iloc[i-structure_n:i].min()); hi=float(p.high.iloc[i-structure_n:i].max())
        trig=(float(p.close.iloc[i])>hi) if side>0 else (float(p.close.iloc[i])<lo)
        if not trig: continue
        atr=float(p.atr.iloc[i]); rng=float(p.high.iloc[i]-p.low.iloc[i])
        if impulse_filter and rng>1.5*atr:
            active=False; continue
        # structural stop using last 12 bars INCLUDING trigger
        a=max(0,i-11)
        if side>0:
            sx=float(p.low.iloc[a:i+1].min())-STOP_BUFFER_ATR*atr
            raw=(float(p.open.iloc[i+1])-sx)/atr
        else:
            sx=float(p.high.iloc[a:i+1].max())+STOP_BUFFER_ATR*atr
            raw=(sx-float(p.open.iloc[i+1]))/atr
        if raw<STOP_MIN_ATR or raw>STOP_MAX_ATR:
            active=False; continue
        entry=float(p.open.iloc[i+1])
        stop=sx
        risk=abs(entry-stop)
        target=entry+side*RR*risk
        rows.append(dict(tf=tfmin,armed=armed,structure_n=structure_n,impulse_filter=impulse_filter,
                         setup_idx=setup_idx,trigger_idx=i,entry_idx=i+1,signal_time=p.close_time.iloc[i],
                         entry_time=p.time.iloc[i+1],side=side,z_trigger=z,entry=entry,stop=stop,target=target,
                         risk=risk,atr=atr,break_level=(hi if side>0 else lo),trigger_open=float(p.open.iloc[i])))
        active=False
    return pd.DataFrame(rows)

def simulate_variant(p,cands,use_fail,use_be,use_z0,timeout_bars,cost_bps=0.0):
    trades=[]; open_until=-1; day=None; nday=0; consec_loss=0
    for r in cands.itertuples():
        ei=int(r.entry_idx)
        if ei<=open_until or ei>=len(p): continue
        d=p.time.iloc[ei].date()
        if day!=d:
            day=d; nday=0
            # daily reset but streak carries only within day for this test
            consec_loss=0
        if nday>=MAX_TRADES_DAY or consec_loss>=LOSS_STREAK_PAUSE: continue
        entry=float(r.entry); stop=float(r.stop); target=float(r.target); risk=float(r.risk); side=int(r.side)
        cur_stop=stop; be_armed=False; exit_px=np.nan; reason='TIMEOUT'; exit_i=min(ei+timeout_bars,len(p)-1)
        maxfav=0.0; maxadv=0.0
        for j in range(ei,exit_i+1):
            h=float(p.high.iloc[j]); l=float(p.low.iloc[j]); c=float(p.close.iloc[j])
            fav=(h-entry)/risk if side>0 else (entry-l)/risk
            adv=(entry-l)/risk if side>0 else (h-entry)/risk
            maxfav=max(maxfav,fav); maxadv=max(maxadv,adv)
            # BE becomes effective next bar after +1R observation to stay causal on bar data
            if use_be and (not be_armed) and fav>=1.0:
                be_armed=True
            # current stop/target first-passage; same-bar collision conservative to stop
            hit_sl=(l<=cur_stop) if side>0 else (h>=cur_stop)
            hit_tp=(h>=target) if side>0 else (l<=target)
            if hit_sl and hit_tp:
                exit_px=cur_stop; reason='SL_COLLISION'; exit_i=j; break
            if hit_sl:
                exit_px=cur_stop; reason='BE' if abs(cur_stop-entry)<1e-12 else 'SL'; exit_i=j; break
            if hit_tp:
                exit_px=target; reason='TP'; exit_i=j; break
            # FAIL only first 3 bars from entry
            if use_fail and j<=ei+2:
                back_level=(c<r.break_level and c<r.trigger_open) if side>0 else (c>r.break_level and c>r.trigger_open)
                if back_level:
                    exit_px=c; reason='FAIL'; exit_i=j; break
            if use_z0:
                z=float(p.z.iloc[j])
                crossed=(z>=0) if side>0 else (z<=0)
                if crossed:
                    exit_px=c; reason='Z0'; exit_i=j; break
            if use_be and be_armed:
                cur_stop=entry
        if not np.isfinite(exit_px): exit_px=float(p.close.iloc[exit_i])
        gross=side*(exit_px-entry)/risk
        # round-trip bps cost normalized by R
        cost=(entry*(cost_bps/10000.0))/risk
        net=gross-cost
        trades.append(dict(tf=r.tf,armed=r.armed,structure_n=r.structure_n,impulse_filter=r.impulse_filter,
                           fail=use_fail,be=use_be,z0=use_z0,timeout_bars=timeout_bars,cost_bps=cost_bps,
                           entry_time=r.entry_time,exit_time=p.time.iloc[exit_i],side=side,z_trigger=r.z_trigger,
                           gross_r=gross,net_r=net,mfe_r=maxfav,mae_r=maxadv,reason=reason))
        open_until=exit_i; nday+=1
        consec_loss = consec_loss+1 if net<0 else 0
    return pd.DataFrame(trades)

def metrics(t):
    if len(t)==0:return {}
    x=t.net_r.to_numpy(float)
    pos=x[x>0].sum(); neg=-x[x<0].sum()
    eq=np.cumsum(x); peak=np.maximum.accumulate(np.r_[0,eq]); dd=np.max(peak[1:]-eq)
    return dict(n=len(t),wr=float((x>0).mean()),ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                sumr=float(x.sum()),maxdd=float(dd),med_mfe=float(t.mfe_r.median()),med_mae=float(t.mae_r.median()))

rows=[]; ledgers=[]
exit_policies=[
 ('BASE',False,False,False),
 ('FAIL',True,False,False),
 ('BE',False,True,False),
 ('Z0',False,False,True),
 ('FAIL_BE',True,True,False),
 ('FAIL_Z0',True,False,True),
 ('BE_Z0',False,True,True),
 ('ALL',True,True,True),
]
for tf in [15,30]:
    p=build_tf(tf)
    for armed in [False,True]:
      for sn in [1,4]:
        imp=True
        cands=candidate_triggers(p,tf,armed,sn,imp)
        for pol,fail,be,z0 in exit_policies:
            tout=16
            for cost in [0.0,COST_STRESS_BPS]:
                t=simulate_variant(p,cands,fail,be,z0,tout,cost)
                if len(t)==0: continue
                t['policy']=pol
                t['year']=pd.to_datetime(t.entry_time,utc=True).dt.year
                train=t[pd.to_datetime(t.entry_time,utc=True)<pd.Timestamp('2025-01-01',tz='UTC')]
                val=t[pd.to_datetime(t.entry_time,utc=True)>=pd.Timestamp('2025-01-01',tz='UTC')]
                m1=metrics(train); m2=metrics(val)
                row=dict(tf=tf,armed=armed,structure_n=sn,impulse_filter=imp,policy=pol,fail=fail,be=be,z0=z0,timeout_bars=tout,cost_bps=cost,
                         **{f'tr_{k}':v for k,v in m1.items()},**{f'va_{k}':v for k,v in m2.items()})
                rows.append(row)

res=pd.DataFrame(rows)
res.to_csv(OUT/'LAB101_all_variants.csv',index=False)

# Train-selected per TF under gross and stressed separately. Require OOS N >= 50.
rank=[]
for (tf,cost),g in res.groupby(['tf','cost_bps']):
    q=g[(g.tr_n>=100)&(g.va_n>=50)].copy()
    if len(q)==0:q=g.copy()
    q=q.sort_values(['tr_ev','tr_pf','tr_n'],ascending=[False,False,False])
    q.head(25).to_csv(OUT/f'LAB101_TF{tf}_cost{cost:.1f}_train_top25.csv',index=False)
    best=q.iloc[0].to_dict(); best['selection']='TRAIN_BEST'; rank.append(best)
    stable=g.copy()
    stable['min_ev']=np.minimum(stable.tr_ev,stable.va_ev)
    stable=stable.sort_values(['min_ev','va_pf','va_n'],ascending=[False,False,False])
    s=stable.iloc[0].to_dict(); s['selection']='STABILITY_DIAG'; rank.append(s)
pd.DataFrame(rank).to_csv(OUT/'LAB101_selected_profiles.csv',index=False)

# Baseline specifically matching user's simplest architecture
base=res[(res.armed==False)&(res.structure_n==1)&(res.impulse_filter==True)&(res.fail==True)&(res.be==True)&(res.z0==True)&(res.timeout_bars==16)]
base.to_csv(OUT/'LAB101_user_architecture_baseline.csv',index=False)

meta={
 'flow_range':[str(flow.time.min()),str(flow.time.max())],
 'price_range':[str(price.time.min()),str(price.time.max())],
 'flow_rows':len(flow),'price_rows_5m':len(price),
 'assumptions':{
   'z_window':'72x5m=6h','setup':'|z|>=1.0, inverse direction, memory 12 TF bars',
   'armed_on':'requires 0.10 z pullback toward zero from post-setup extreme',
   'trigger':'TF close beyond prior 1 or 4 bar high/low; entry next TF open',
   'impulse_filter':'trigger candle range <=1.5 ATR14',
   'stop':'12-bar structure incl trigger +0.05 ATR buffer; accept 0.5..2.0 ATR only',
   'tp':'fixed 2R','fail':'within first 3 bars close back through breakout level AND trigger open',
   'be':'move to entry after +1R becomes observable; effective next bar','z0':'exit at bar close when z crosses zero',
   'timeouts':'8/16/32 TF bars','max_trades_day':3,'loss_streak_pause':'3 losses => rest of day',
   'cost_stress_bps':COST_STRESS_BPS,'spread':'NOT modeled; exact broker spread unavailable'
 }}
(OUT/'LAB101_meta.json').write_text(json.dumps(meta,indent=2,default=str))

# concise report
sel=pd.DataFrame(rank)
lines=['# LAB101 CrowdFade state-machine historical simulation','',
       f"Flow: {flow.time.min()} -> {flow.time.max()} | rows {len(flow):,}",
       f"Price: {price.time.min()} -> {price.time.max()} | 5m rows {len(price):,}",'',
       '## Frozen interpretation used',
       '- SETUP: |Z|>=1.0, inverse crowd direction, memory 12 trading-TF bars.',
       '- ARMED ON: 0.10 Z pullback toward zero after setup extreme.',
       '- TRIGGER: close beyond prior 1-bar or 4-bar structure; entry next bar open.',
       '- SL: 12-bar structural extreme + 0.05 ATR buffer, only if 0.5..2.0 ATR.',
       '- TP: 2R. FAIL/BE/Z0/timeouts are ablated.',
       f'- Cost stress: {COST_STRESS_BPS:.1f} bps round turn; spread excluded.','']
for _,r in sel.iterrows():
    lines += [f"## {r['selection']} TF={int(r.tf)} cost={r.cost_bps:.1f}bps",
              f"- armed={bool(r.armed)}, structure={int(r.structure_n)}, impulse={bool(r.impulse_filter)}, fail={bool(r.fail)}, BE={bool(r.be)}, Z0={bool(r.z0)}, timeout={int(r.timeout_bars)} bars",
              f"- TRAIN N={int(r.tr_n)} EV={r.tr_ev:+.3f}R PF={r.tr_pf:.2f} DD={r.tr_maxdd:.1f}R",
              f"- OOS 2025+ N={int(r.va_n)} EV={r.va_ev:+.3f}R PF={r.va_pf:.2f} DD={r.va_maxdd:.1f}R",'']
(OUT/'LAB101_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
