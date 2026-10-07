#!/usr/bin/env python3
from __future__ import annotations
import io, json, math, re, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

OUT=Path("lab104b_out"); OUT.mkdir(exist_ok=True)

FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TICK_ZIP=Path("CF_LAB001_GetLeveraged_Ltd._BTCUSD_TICKS_30D.csv.zip")

ZWIN_5M=72
ATR_N=14
SETUP_Z=1.0
SETUP_MEMORY=12
TRIGGER_LOOKBACK=4
STOP_LOOKBACK=12
STOP_BUFFER_ATR=0.05
STOP_MIN_ATR=0.5
STOP_MAX_ATR=2.0
TP_MIN_R=1.0
TIMEOUT_BARS=32
MAX_TRADES_DAY=3

def norm(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())

def pick(cols,prefs):
    nc={norm(c):c for c in cols}
    for p in prefs:
        if norm(p) in nc: return nc[norm(p)]
    for p in prefs:
        pp=norm(p)
        for k,v in nc.items():
            if pp in k or k in pp: return v
    return None

def load_zip_csv(zp, concat_common=True):
    with zipfile.ZipFile(zp) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        frames=[]
        for n in names:
            try:
                with z.open(n) as f:
                    d=pd.read_csv(f)
                if len(d): frames.append(d)
            except Exception:
                pass
        if not frames: raise RuntimeError(f"no CSV in {zp}")
        if len(frames)==1: return frames[0],names
        if concat_common:
            common=set(frames[0].columns)
            for d in frames[1:]: common &= set(d.columns)
            cols=list(common)
            if len(cols)>=3:
                return pd.concat([d[cols] for d in frames],ignore_index=True),names
        return frames[0],names

def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce')
        med=float(x.dropna().median()) if x.notna().any() else 0
        if med>1e14: unit='us'
        elif med>1e11: unit='ms'
        elif med>1e9: unit='s'
        else: unit='s'
        return pd.to_datetime(x,unit=unit,errors='coerce',utc=True)
    return pd.to_datetime(s,errors='coerce',utc=True)

# ---------------------- Binance flow and price ----------------------
flow,_=load_zip_csv(FLOW_ZIP)
ft=pick(flow.columns,['timestamp','time','datetime','open_time'])
fr=pick(flow.columns,['longShortRatio','long_short_ratio','ls_ratio','globalLongShortAccountRatio','ratio'])
if ft is None or fr is None: raise RuntimeError(f"flow columns unresolved {list(flow.columns)}")
flow=flow[[ft,fr]].copy()
flow['time']=ptime(flow[ft]); flow['ratio']=pd.to_numeric(flow[fr],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(ZWIN_5M,min_periods=ZWIN_5M).mean()
sd=flow.ratio.rolling(ZWIN_5M,min_periods=ZWIN_5M).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)

price,_=load_zip_csv(PRICE_ZIP)
pt=pick(price.columns,['time','timestamp','datetime','open_time'])
po=pick(price.columns,['open']); ph=pick(price.columns,['high']); pl=pick(price.columns,['low']); pc=pick(price.columns,['close'])
if None in [pt,po,ph,pl,pc]: raise RuntimeError(f"price columns unresolved {list(price.columns)}")
p=price[[pt,po,ph,pl,pc]].copy()
p['time']=ptime(p[pt])
for c,nm in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:
    p[nm]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna()

m15=p.resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
m15['close_time']=m15.time+pd.Timedelta(minutes=15)
prev=m15.close.shift(1)
tr=pd.concat([(m15.high-m15.low),(m15.high-prev).abs(),(m15.low-prev).abs()],axis=1).max(axis=1)
m15['atr']=tr.rolling(ATR_N,min_periods=ATR_N).mean()
m15=pd.merge_asof(m15.sort_values('close_time'),flow[['time','z']].dropna().sort_values('time'),
                  left_on='close_time',right_on='time',direction='backward',tolerance=pd.Timedelta('10min'),suffixes=('','_z'))
m15=m15.dropna(subset=['atr','z']).reset_index(drop=True)

# ---------------------- Real broker spread profile ----------------------
ticks,_=load_zip_csv(TICK_ZIP)
tt=pick(ticks.columns,['time_msc','timestamp','time','datetime'])
tb=pick(ticks.columns,['bid']); ta=pick(ticks.columns,['ask'])
if None in [tt,tb,ta]: raise RuntimeError(f"tick columns unresolved {list(ticks.columns)}")
tk=ticks[[tt,tb,ta]].copy()
tk['time']=ptime(tk[tt]); tk['bid']=pd.to_numeric(tk[tb],errors='coerce'); tk['ask']=pd.to_numeric(tk[ta],errors='coerce')
tk=tk.dropna(subset=['time','bid','ask'])
tk=tk[(tk.bid>0)&(tk.ask>tk.bid)]
tk['mid']=(tk.bid+tk.ask)/2
tk['spread_bps']=(tk.ask-tk.bid)/tk.mid*10000.0
# robust trim only impossible/corrupt tails; p99.99 cap
cap=float(tk.spread_bps.quantile(.9999))
tk=tk[(tk.spread_bps>=0)&(tk.spread_bps<=cap)]
tk['hour']=tk.time.dt.hour
spread_prof=tk.groupby('hour').spread_bps.agg(median='median',p95=lambda x:x.quantile(.95),n='size').reset_index()
spread_prof.to_csv(OUT/'LAB104B_spread_by_hour.csv',index=False)
SP_MED={int(r.hour):float(r.median) for r in spread_prof.itertuples()}
SP_P95={int(r.hour):float(r.p95) for r in spread_prof.itertuples()}
GLOBAL_MED=float(tk.spread_bps.median()); GLOBAL_P95=float(tk.spread_bps.quantile(.95))

# ---------------------- Causal 5-bar fractals ----------------------
n=len(m15)
confirmed_highs=[[] for _ in range(n)]
confirmed_lows=[[] for _ in range(n)]
# keep cumulative confirmed pivot prices available by each trigger bar i.
high_piv=[]; low_piv=[]
for i in range(n):
    k=i-2
    if k>=2 and k+2<n:
        h=m15.high
        l=m15.low
        if h.iloc[k]>h.iloc[k-1] and h.iloc[k]>h.iloc[k-2] and h.iloc[k]>=h.iloc[k+1] and h.iloc[k]>=h.iloc[k+2]:
            high_piv.append(float(h.iloc[k]))
        if l.iloc[k]<l.iloc[k-1] and l.iloc[k]<l.iloc[k-2] and l.iloc[k]<=l.iloc[k+1] and l.iloc[k]<=l.iloc[k+2]:
            low_piv.append(float(l.iloc[k]))
    confirmed_highs[i]=list(high_piv)
    confirmed_lows[i]=list(low_piv)

# ---------------------- Setup state ----------------------
# z-side at each bar = latest |z|>=1 event within last 12 bars, inverse sign.
setup_side=np.zeros(n,dtype=int)
episode_id=np.full(n,-1,dtype=int)
last_ext=-999999
last_side=0
ep=-1
for i in range(n):
    z=float(m15.z.iloc[i])
    if abs(z)>=SETUP_Z:
        s=-1 if z>0 else 1
        # new episode only after inactive gap or direction change
        if i-last_ext>SETUP_MEMORY or s!=last_side:
            ep+=1
        last_ext=i; last_side=s
    if i-last_ext<=SETUP_MEMORY and last_side!=0:
        setup_side[i]=last_side; episode_id[i]=ep
    else:
        setup_side[i]=0; episode_id[i]=-1

# ---------------------- trade engine ----------------------
def choose_tp(i,side,entry,tp_mode):
    if tp_mode=='TP_RANGE':
        if i<48: return np.nan
        if side>0:
            return float(m15.high.iloc[i-48:i].max())
        return float(m15.low.iloc[i-48:i].min())
    if tp_mode=='TP_PIVOT':
        if side>0:
            vals=[x for x in confirmed_highs[i] if x>entry]
            return min(vals) if vals else np.nan
        vals=[x for x in confirmed_lows[i] if x<entry]
        return max(vals) if vals else np.nan
    raise KeyError(tp_mode)

def trigger_side(i):
    if i<TRIGGER_LOOKBACK: return 0
    c=float(m15.close.iloc[i])
    hi=float(m15.high.iloc[i-TRIGGER_LOOKBACK:i].max())
    lo=float(m15.low.iloc[i-TRIGGER_LOOKBACK:i].min())
    if c>hi: return 1
    if c<lo: return -1
    return 0

def spread_bps_at(ts,profile):
    h=int(pd.Timestamp(ts).hour)
    if profile=='MEDIAN': return SP_MED.get(h,GLOBAL_MED)
    if profile=='P95': return SP_P95.get(h,GLOBAL_P95)
    if profile=='NONE': return 0.0
    raise KeyError(profile)

def simulate(use_z,tp_mode,extra_bps,spread_mode):
    rows=[]
    open_until=-1
    day=None; count_day=0
    # per z episode count to distinguish first/re-entry.
    ep_entry_count={}
    for i in range(max(60,STOP_LOOKBACK,TRIGGER_LOOKBACK),n-1):
        if i<=open_until: continue
        d=m15.time.iloc[i+1].date()
        if d!=day: day=d; count_day=0
        if count_day>=MAX_TRADES_DAY: continue
        ts=trigger_side(i)
        if ts==0: continue
        if use_z:
            ss=int(setup_side[i])
            if ss==0 or ts!=ss: continue
            ep_id=int(episode_id[i])
        else:
            ep_id=-1
        side=ts
        entry_i=i+1
        entry=float(m15.open.iloc[entry_i])
        atr=float(m15.atr.iloc[i])
        a=i-STOP_LOOKBACK+1
        if side>0:
            stop=float(m15.low.iloc[a:i+1].min())-STOP_BUFFER_ATR*atr
            stop_dist=entry-stop
        else:
            stop=float(m15.high.iloc[a:i+1].max())+STOP_BUFFER_ATR*atr
            stop_dist=stop-entry
        if stop_dist<=0: continue
        stop_atr=stop_dist/atr
        if stop_atr<STOP_MIN_ATR or stop_atr>STOP_MAX_ATR: continue
        tp=choose_tp(i,side,entry,tp_mode)
        if not np.isfinite(tp): continue
        tp_dist=(tp-entry) if side>0 else (entry-tp)
        if tp_dist<=0: continue
        tp_r=tp_dist/stop_dist
        if tp_r<TP_MIN_R: continue

        end=min(entry_i+TIMEOUT_BARS-1,n-1)
        exit_px=float(m15.close.iloc[end]); reason='TIMEOUT'; ex=end
        for j in range(entry_i,end+1):
            h=float(m15.high.iloc[j]); l=float(m15.low.iloc[j])
            hs=(l<=stop) if side>0 else (h>=stop)
            ht=(h>=tp) if side>0 else (l<=tp)
            if hs and ht:
                exit_px=stop; reason='SL_COLLISION'; ex=j; break
            if hs:
                exit_px=stop; reason='SL'; ex=j; break
            if ht:
                exit_px=tp; reason='TP'; ex=j; break

        gross=side*(exit_px-entry)/stop_dist
        # spread modeled as half-spread on entry + half-spread on exit, using real broker hourly profile
        sb_entry=spread_bps_at(m15.time.iloc[entry_i],spread_mode)
        sb_exit=spread_bps_at(m15.time.iloc[ex],spread_mode)
        spread_rt_bps=0.5*(sb_entry+sb_exit)
        total_cost_bps=extra_bps+spread_rt_bps
        cost_r=(entry*(total_cost_bps/10000.0))/stop_dist
        net=gross-cost_r

        if use_z:
            k=ep_entry_count.get(ep_id,0)
            entry_class='FIRST' if k==0 else 'REENTRY'
            ep_entry_count[ep_id]=k+1
        else:
            entry_class='BASELINE'

        rows.append(dict(engine='Z' if use_z else 'NO_Z',tp_mode=tp_mode,extra_bps=extra_bps,spread_mode=spread_mode,
                         signal_time=m15.close_time.iloc[i],entry_time=m15.time.iloc[entry_i],exit_time=m15.time.iloc[ex],
                         side='LONG' if side>0 else 'SHORT',episode_id=ep_id,entry_class=entry_class,z=float(m15.z.iloc[i]),
                         entry=entry,stop=stop,tp=tp,stop_atr=stop_atr,tp_r=tp_r,gross_r=gross,net_r=net,
                         spread_rt_bps=spread_rt_bps,total_cost_bps=total_cost_bps,reason=reason,bars_held=ex-entry_i+1))
        open_until=ex
        count_day+=1
    return pd.DataFrame(rows)

def metrics(q):
    if len(q)==0:
        return dict(n=0,wr=np.nan,ev=np.nan,t=np.nan,pf=np.nan,sumr=0.0,dd=np.nan,tp_rate=np.nan,sl_rate=np.nan,timeout_rate=np.nan,
                    avg_tp_r=np.nan,trades_per_day=np.nan,se=np.nan)
    x=q.net_r.to_numpy(float)
    mean=float(x.mean()); sd=float(x.std(ddof=1)) if len(x)>1 else np.nan
    se=sd/math.sqrt(len(x)) if len(x)>1 and sd>0 else np.nan
    t=mean/se if np.isfinite(se) and se>0 else np.nan
    pos=x[x>0].sum(); neg=-x[x<0].sum()
    eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=float(np.max(pk[1:]-eq))
    days=max(1,(pd.to_datetime(q.entry_time,utc=True).max().date()-pd.to_datetime(q.entry_time,utc=True).min().date()).days+1)
    return dict(n=len(q),wr=float((x>0).mean()),ev=mean,t=t,pf=float(pos/neg) if neg>0 else np.inf,sumr=float(x.sum()),dd=dd,
                tp_rate=float((q.reason=='TP').mean()),sl_rate=float(q.reason.isin(['SL','SL_COLLISION']).mean()),
                timeout_rate=float((q.reason=='TIMEOUT').mean()),avg_tp_r=float(q.tp_r.mean()),trades_per_day=len(q)/days,se=se)

# ---------------------- sweep fixed requested variants ----------------------
alltr=[]; sumrows=[]
for tp_mode in ['TP_PIVOT','TP_RANGE']:
    for spread_mode in ['NONE','MEDIAN','P95']:
        for extra in [0.0,1.0,2.0,3.0]:
            for use_z in [True,False]:
                t=simulate(use_z,tp_mode,extra,spread_mode)
                if len(t)==0: continue
                t['split']=np.where(pd.to_datetime(t.entry_time,utc=True)<pd.Timestamp('2025-01-01',tz='UTC'),'TRAIN','OOS')
                t['year']=pd.to_datetime(t.entry_time,utc=True).dt.year
                alltr.append(t)
                for split in ['TRAIN','OOS','ALL']:
                    q=t if split=='ALL' else t[t.split==split]
                    m=metrics(q)
                    sumrows.append(dict(engine='Z' if use_z else 'NO_Z',tp_mode=tp_mode,spread_mode=spread_mode,extra_bps=extra,split=split,**m))
trades=pd.concat(alltr,ignore_index=True)
summ=pd.DataFrame(sumrows)
trades.to_csv(OUT/'LAB104B_trades_all.csv',index=False)
summ.to_csv(OUT/'LAB104B_summary.csv',index=False)

# Year and side / entry class for realistic median spread + 0..3 bps
yearrows=[]; classrows=[]; monthrows=[]; compare=[]
for tp_mode in ['TP_PIVOT','TP_RANGE']:
  for extra in [0.0,1.0,2.0,3.0]:
    for engine in ['Z','NO_Z']:
      q=trades[(trades.tp_mode==tp_mode)&(trades.spread_mode=='MEDIAN')&(trades.extra_bps==extra)&(trades.engine==engine)].copy()
      for y,g in q.groupby('year'):
        yearrows.append(dict(tp_mode=tp_mode,extra_bps=extra,engine=engine,year=int(y),**metrics(g)))
      for split in ['TRAIN','OOS']:
        z=q[q.split==split]
        for side in ['LONG','SHORT','ALL']:
          g=z if side=='ALL' else z[z.side==side]
          classrows.append(dict(tp_mode=tp_mode,extra_bps=extra,engine=engine,split=split,group='SIDE',bucket=side,**metrics(g)))
        if engine=='Z':
          for ec in ['FIRST','REENTRY']:
            g=z[z.entry_class==ec]
            classrows.append(dict(tp_mode=tp_mode,extra_bps=extra,engine=engine,split=split,group='ENTRY_CLASS',bucket=ec,**metrics(g)))
      q['month']=pd.to_datetime(q.entry_time,utc=True).dt.to_period('M').astype(str)
      for mo,g in q.groupby('month'):
        monthrows.append(dict(tp_mode=tp_mode,extra_bps=extra,engine=engine,month=mo,sumr=float(g.net_r.sum()),n=len(g),ev=float(g.net_r.mean())))

# z vs baseline comparison with standard error difference, same requested engine family.
for tp_mode in ['TP_PIVOT','TP_RANGE']:
  for spread_mode in ['MEDIAN','P95']:
    for extra in [0.0,1.0,2.0,3.0]:
      for split in ['TRAIN','OOS']:
        z=trades[(trades.engine=='Z')&(trades.tp_mode==tp_mode)&(trades.spread_mode==spread_mode)&(trades.extra_bps==extra)&(trades.split==split)]
        b=trades[(trades.engine=='NO_Z')&(trades.tp_mode==tp_mode)&(trades.spread_mode==spread_mode)&(trades.extra_bps==extra)&(trades.split==split)]
        mz=metrics(z); mb=metrics(b)
        sediff=math.sqrt((mz['se'] if np.isfinite(mz['se']) else 0)**2+(mb['se'] if np.isfinite(mb['se']) else 0)**2)
        diff=mz['ev']-mb['ev']
        compare.append(dict(tp_mode=tp_mode,spread_mode=spread_mode,extra_bps=extra,split=split,
                            z_n=mz['n'],z_ev=mz['ev'],z_t=mz['t'],base_n=mb['n'],base_ev=mb['ev'],base_t=mb['t'],
                            ev_diff=diff,se_diff=sediff,beats_by_1se=bool(np.isfinite(sediff) and diff>=sediff)))

pd.DataFrame(yearrows).to_csv(OUT/'LAB104B_yearly.csv',index=False)
pd.DataFrame(classrows).to_csv(OUT/'LAB104B_side_reentry.csv',index=False)
monthly=pd.DataFrame(monthrows); monthly.to_csv(OUT/'LAB104B_monthly.csv',index=False)
pd.DataFrame(compare).to_csv(OUT/'LAB104B_z_vs_baseline.csv',index=False)

# Worst-month summary
worst=[]
for (tp,extra,eng),g in monthly.groupby(['tp_mode','extra_bps','engine']):
    avg=float(g.sumr.mean()); w=float(g.sumr.min())
    worst.append(dict(tp_mode=tp,extra_bps=extra,engine=eng,avg_month_sumr=avg,worst_month_sumr=w,
                      avg_to_abs_worst=(avg/abs(w) if w<0 else np.inf),worst_month=str(g.loc[g.sumr.idxmin(),'month'])))
pd.DataFrame(worst).to_csv(OUT/'LAB104B_worst_month.csv',index=False)

# Selection by TRAIN only among TP variants, for median spread and each extra cost.
selected=[]
for extra in [0.0,1.0,2.0,3.0]:
    g=summ[(summ.engine=='Z')&(summ.spread_mode=='MEDIAN')&(summ.extra_bps==extra)&(summ.split=='TRAIN')].copy()
    if len(g):
        r=g.sort_values(['ev','t'],ascending=[False,False]).iloc[0].to_dict()
        r['selection']='TRAIN_BEST_TP'
        selected.append(r)
pd.DataFrame(selected).to_csv(OUT/'LAB104B_train_selected.csv',index=False)

# Pass/fail requested gate on TRAIN-selected TP at real median spread, per extra bps.
gates=[]
cmpdf=pd.DataFrame(compare)
for sel in selected:
    tp=sel['tp_mode']; extra=sel['extra_bps']
    ztr=summ[(summ.engine=='Z')&(summ.tp_mode==tp)&(summ.spread_mode=='MEDIAN')&(summ.extra_bps==extra)&(summ.split=='TRAIN')].iloc[0]
    zos=summ[(summ.engine=='Z')&(summ.tp_mode==tp)&(summ.spread_mode=='MEDIAN')&(summ.extra_bps==extra)&(summ.split=='OOS')].iloc[0]
    zz=summ[(summ.engine=='Z')&(summ.tp_mode==tp)&(summ.spread_mode=='MEDIAN')&(summ.extra_bps==extra)&(summ.split=='ALL')].iloc[0]
    co=cmpdf[(cmpdf.tp_mode==tp)&(cmpdf.spread_mode=='MEDIAN')&(cmpdf.extra_bps==extra)&(cmpdf.split=='OOS')].iloc[0]
    passed=bool(zos.ev>0 and zz.t>=2 and ztr.ev>0 and zos.ev>0 and co.beats_by_1se)
    gates.append(dict(extra_bps=extra,tp_mode=tp,train_ev=ztr.ev,oos_ev=zos.ev,all_t=zz.t,
                      oos_ev_diff_vs_base=co.ev_diff,oos_se_diff=co.se_diff,beats_base_1se=co.beats_by_1se,pass_gate=passed))
pd.DataFrame(gates).to_csv(OUT/'LAB104B_gates.csv',index=False)

meta=dict(
    flow_range=[str(flow.time.min()),str(flow.time.max())],
    price_range=[str(m15.time.min()),str(m15.time.max())],
    tick_range=[str(tk.time.min()),str(tk.time.max())],
    tick_rows=int(len(tk)),
    broker_spread_global_median_bps=GLOBAL_MED,
    broker_spread_global_p95_bps=GLOBAL_P95,
    assumptions=dict(timeframe='M15',z_window='6h',setup='|z|>=1 inverse sign + 12 M15 bars memory',
        trigger='close beyond prior 4 bars; entry next M15 open',stop='opposite extreme last 12 bars +0.05 ATR, accept 0.5..2 ATR',
        tp_pivot='nearest prior causally confirmed 5-bar fractal beyond entry',tp_range='prior 48-bar high/low',
        min_tp='>=1R',timeout='32 M15 bars=8h',reentry='after close if same z setup remains active and new trigger fires',
        max_trades_day=3,spread='GetLeveraged BTCUSD 30D ticks; hourly median/p95; half entry + half exit spread bps'))
(OUT/'LAB104B_meta.json').write_text(json.dumps(meta,indent=2))

# concise report
lines=['# LAB104B — Structural TP + repeated inverse-crowd entries','',
       f"Real spread source: GetLeveraged BTCUSD tick archive {tk.time.min()} -> {tk.time.max()} | ticks={len(tk):,}",
       f"Global spread: median={GLOBAL_MED:.3f} bps, p95={GLOBAL_P95:.3f} bps.",'',
       'Signal engine: |Z|>=1 inverse direction + 12 M15-bar memory; trigger=4-bar breakout; entry next open; structural 12-bar SL; timeout 8h; max 3/day.',
       'Baseline: same breakout/SL/TP engine without Z.','']
gatedf=pd.DataFrame(gates)
for _,r in gatedf.iterrows():
    lines += [f"## Median real spread + {r.extra_bps:.0f} bps",
              f"- TRAIN-selected TP: {r.tp_mode}",
              f"- TRAIN EV={r.train_ev:+.3f}R | OOS EV={r.oos_ev:+.3f}R | ALL t={r.all_t:.2f}",
              f"- OOS Z-vs-baseline ΔEV={r.oos_ev_diff_vs_base:+.3f}R, SE(diff)={r.oos_se_diff:.3f}R, beats>=1SE={bool(r.beats_base_1se)}",
              f"- Gate: {'PASS' if r.pass_gate else 'FAIL'}",'']
(OUT/'LAB104B_REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
