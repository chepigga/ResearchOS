#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab116_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
ROLL_DAYS=60
MIN_ROLL_N=80
STOP_ATR=1.50
TP_R=1.50
COSTS_BPS=[0.0,2.81,7.5]

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
        for n in z.namelist():
            if not n.lower().endswith('.csv'): continue
            try:
                with z.open(n) as f:d=pd.read_csv(f)
                if len(d):frames.append(d)
            except Exception:pass
        if not frames: raise RuntimeError(f"no csv in {zp}")
        common=set(frames[0].columns)
        for d in frames[1:]: common &= set(d.columns)
        if len(frames)>1 and len(common)>=4:
            cols=list(common); return pd.concat([d[cols] for d in frames],ignore_index=True)
        return frames[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce');med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# ----- data -----
flow=load_zip(FLOW_ZIP)
tc=pick(flow.columns,['create_time','time','timestamp']);rc=pick(flow.columns,['count_long_short_ratio','ratio'])
flow=flow[[tc,rc]].copy();flow['time']=ptime(flow[tc]);flow['ratio']=pd.to_numeric(flow[rc],errors='coerce')
flow=flow.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time',keep='last')
flow=flow[flow.ratio>0].set_index('time').resample('5min').last().dropna().reset_index()
mu=flow.ratio.rolling(72,min_periods=72).mean();sd=flow.ratio.rolling(72,min_periods=72).std(ddof=0)
flow['z']=(flow.ratio-mu)/sd.replace(0,np.nan)

raw=load_zip(PRICE_ZIP)
pt=pick(raw.columns,['time','timestamp','open_time']);po=pick(raw.columns,['open']);ph=pick(raw.columns,['high']);pl=pick(raw.columns,['low']);pc=pick(raw.columns,['close'])
p=raw[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# H1 ATR and H4 trend
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1);tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr_h1']=tr.rolling(14,min_periods=14).mean();h1['close_time']=h1.time+pd.Timedelta(hours=1)
h1['q33']=h1.atr_h1.rolling(1440,min_periods=480).quantile(1/3);h1['q67']=h1.atr_h1.rolling(1440,min_periods=480).quantile(2/3)

h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean();h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend_h4']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
h4['close_time']=h4.time+pd.Timedelta(hours=4)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr_h1','q33','q67']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),h4[['close_time','trend_h4']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
base=pd.merge_asof(base.sort_values('time'),flow[['time','z']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['atr_h1','q33','q67','trend_h4','z']).reset_index(drop=True)
base['vol_regime']=np.where(base.atr_h1<base.q33,'LOW',np.where(base.atr_h1>base.q67,'HIGH','MID'))

BT=base.time.reset_index(drop=True);BO=base.open.to_numpy(float);BH=base.high.to_numpy(float);BL=base.low.to_numpy(float);BC=base.close.to_numpy(float);BA=base.atr_h1.to_numpy(float);BZ=base.z.to_numpy(float)
idx_by_time={t:i for i,t in enumerate(BT)}

# ----- frozen Z events and raw forward outcomes -----
events=[]
last=len(base)-1-48*12-1
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1;atr=float(BA[i]);anchor=float(BC[i])
    if atr<=0 or not np.isfinite(atr):continue
    row=dict(i=i,signal_time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',
             side=side,z=float(BZ[i]),atr=atr,anchor=anchor,vol_regime=base.vol_regime.iloc[i],
             h4_with=int(base.trend_h4.iloc[i])==side)
    for h in [4,24,48]:
        e=i+h*12
        row[f'close_{h}h']=side*(float(BC[e])-anchor)/atr
        row[f'realized_at_{h}h']=BT.iloc[e]
    events.append(row)
ev=pd.DataFrame(events).sort_values('signal_time').reset_index(drop=True)

# Causal rolling historical edge for each event/horizon: only outcomes fully known by signal time.
for h in [4,24,48]:
    vals=[]
    for _,r in ev.iterrows():
        t=r.signal_time
        hist=ev[(ev[f'realized_at_{h}h']<t)&(ev.signal_time>=t-pd.Timedelta(days=ROLL_DAYS))]
        x=hist[f'close_{h}h'].to_numpy(float)
        vals.append((len(x),float(x.mean()) if len(x) else np.nan,float(x.std(ddof=1)) if len(x)>1 else np.nan))
    ev[f'roll_n_{h}h']=[x[0] for x in vals]
    ev[f'roll_mean_{h}h']=[x[1] for x in vals]
    ev[f'roll_dnr_{h}h']=[x[1]/x[2] if x[2] and np.isfinite(x[2]) and x[2]>0 else np.nan for x in vals]

def route_policy(r,policy):
    if policy=='BASE24': return 24
    if policy=='BASE48': return 48
    # eligibility based only on causal rolling history
    ok4=(r.roll_n_4h>=MIN_ROLL_N and r.roll_mean_4h>0)
    ok24=(r.roll_n_24h>=MIN_ROLL_N and r.roll_mean_24h>0)
    ok48=(r.roll_n_48h>=MIN_ROLL_N and r.roll_mean_48h>0)
    if policy=='STATIC_REGIME':
        # Prior LAB115 exploratory regime rule; no rolling kill switch.
        return 48 if (r.vol_regime=='LOW' and bool(r.h4_with)) else 24
    if policy=='CAUSAL_ROUTER':
        if not(ok24 or ok48): return 0
        if r.vol_regime=='LOW' and bool(r.h4_with) and ok48: return 48
        if ok24: return 24
        if ok48: return 48
        if ok4: return 4
        return 0
    if policy=='CAUSAL_KILLSWITCH24':
        return 24 if ok24 else 0
    raise ValueError(policy)

POLICIES=['BASE24','BASE48','STATIC_REGIME','CAUSAL_KILLSWITCH24','CAUSAL_ROUTER']

# trade sim: one position at a time; entry next 5m open; SL 1.5 ATR, TP 1.5R = 2.25 ATR.
def simulate(policy,cost_bps):
    trades=[];equity_points=[];open_until=pd.Timestamp.min.tz_localize('UTC');cumR=0.0
    for _,r in ev.iterrows():
        h=route_policy(r,policy)
        if h==0: continue
        i=int(r.i)
        ei=i+1
        if ei>=len(base):continue
        et=BT.iloc[ei]
        if et<open_until:continue
        side=int(r.side);atr=float(r.atr);entry=float(BO[ei]);stop_dist=STOP_ATR*atr
        slp=entry-side*stop_dist;tpp=entry+side*stop_dist*TP_R
        end=min(ei+h*12,len(base)-1)
        reason='TIME';exit_i=end;grossR=side*(float(BC[end])-entry)/stop_dist
        # mark path and locate first hit; stop-first same bar
        for j in range(ei,end+1):
            hit_sl=(BL[j]<=slp) if side>0 else (BH[j]>=slp)
            hit_tp=(BH[j]>=tpp) if side>0 else (BL[j]<=tpp)
            if hit_sl and hit_tp:
                reason='BOTH_STOP_FIRST';exit_i=j;grossR=-1.0;break
            if hit_sl:
                reason='SL';exit_i=j;grossR=-1.0;break
            if hit_tp:
                reason='TP';exit_i=j;grossR=TP_R;break
        costR=(cost_bps/10000.0)*entry/stop_dist
        netR=grossR-costR
        # MTM equity path at 5m closes, include full round-trip cost from entry for conservative path.
        start_eq=cumR
        for j in range(ei,exit_i+1):
            mtm=side*(float(BC[j])-entry)/stop_dist-costR
            if reason in ['SL','BOTH_STOP_FIRST'] and j==exit_i:mtm=netR
            if reason=='TP' and j==exit_i:mtm=netR
            if reason=='TIME' and j==exit_i:mtm=netR
            equity_points.append((BT.iloc[j],start_eq+mtm))
        cumR+=netR
        xt=BT.iloc[exit_i];open_until=xt
        trades.append(dict(policy=policy,cost_bps=cost_bps,signal_time=r.signal_time,entry_time=et,exit_time=xt,horizon_h=h,
                           side='BUY' if side>0 else 'SELL',vol_regime=r.vol_regime,h4_with=bool(r.h4_with),
                           gross_r=grossR,net_r=netR,reason=reason,split=r['split']))
    t=pd.DataFrame(trades)
    if not len(t): return t,{}
    eq=pd.DataFrame(equity_points,columns=['time','equity_r']).sort_values('time').drop_duplicates('time',keep='last')
    peak=eq.equity_r.cummax();dd=peak-eq.equity_r;max_mtm_dd=float(dd.max())
    # max daily equity drawdown: start-of-UTC-day equity to intraday low
    eq['day']=eq.time.dt.floor('D')
    daily_dd=[]
    prev_close=0.0
    for d,g in eq.groupby('day'):
        start=prev_close
        daily_dd.append(float(start-g.equity_r.min()))
        prev_close=float(g.equity_r.iloc[-1])
    pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
    months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
    met=dict(n=len(t),ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((t.net_r>0).mean()),
             total_r=float(t.net_r.sum()),trades_month=float(len(t)/months),r_month=float(t.net_r.sum()/months),
             max_mtm_dd_r=max_mtm_dd,max_daily_dd_r=max(daily_dd) if daily_dd else np.nan,
             max_mtm_dd_pct_at_025=max_mtm_dd*0.25,max_daily_dd_pct_at_025=(max(daily_dd)*0.25 if daily_dd else np.nan),
             tp_rate=float((t.reason=='TP').mean()),sl_rate=float(t.reason.isin(['SL','BOTH_STOP_FIRST']).mean()),
             time_rate=float((t.reason=='TIME').mean()))
    return t,met

summary=[];alltr=[]
for cost in COSTS_BPS:
    for policy in POLICIES:
        t,m=simulate(policy,cost)
        if len(t):
            alltr.append(t)
            for split in ['ALL','TRAIN','OOS']:
                q=t if split=='ALL' else t[t['split']==split]
                if not len(q):continue
                pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
                summary.append(dict(policy=policy,cost_bps=cost,split=split,n=len(q),ev=float(q.net_r.mean()),
                    pf=float(pos/neg) if neg>0 else np.inf,wr=float((q.net_r>0).mean()),total_r=float(q.net_r.sum()),
                    tp_rate=float((q.reason=='TP').mean()),sl_rate=float(q.reason.isin(['SL','BOTH_STOP_FIRST']).mean()),
                    time_rate=float((q.reason=='TIME').mean()),
                    trades_month=(m['trades_month'] if split=='ALL' else np.nan),r_month=(m['r_month'] if split=='ALL' else np.nan),
                    max_mtm_dd_r=(m['max_mtm_dd_r'] if split=='ALL' else np.nan),max_daily_dd_r=(m['max_daily_dd_r'] if split=='ALL' else np.nan),
                    max_mtm_dd_pct_at_025=(m['max_mtm_dd_pct_at_025'] if split=='ALL' else np.nan),
                    max_daily_dd_pct_at_025=(m['max_daily_dd_pct_at_025'] if split=='ALL' else np.nan)))
pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB116_trades.csv',index=False)
s=pd.DataFrame(summary);s.to_csv(OUT/'LAB116_summary.csv',index=False)

# routing diagnostics
route=[]
for policy in POLICIES:
    rr=ev.copy();rr['route_h']=rr.apply(lambda x:route_policy(x,policy),axis=1)
    for split in ['TRAIN','OOS']:
        g=rr[rr['split']==split]
        for h,cnt in g.route_h.value_counts().sort_index().items():
            route.append(dict(policy=policy,split=split,route_h=int(h),n=int(cnt),share=float(cnt/len(g))))
pd.DataFrame(route).to_csv(OUT/'LAB116_routes.csv',index=False)

# rolling kill-switch diagnostics for 2026 by month
diag=ev.copy();diag['month']=diag.signal_time.dt.to_period('M').astype(str)
diag['router_h']=diag.apply(lambda x:route_policy(x,'CAUSAL_ROUTER'),axis=1)
mon=[]
for m,g in diag[diag.signal_time>=pd.Timestamp('2026-01-01',tz='UTC')].groupby('month'):
    mon.append(dict(month=m,n=len(g),skip_rate=float((g.router_h==0).mean()),
                    mean_roll24=float(g.roll_mean_24h.mean()),mean_roll48=float(g.roll_mean_48h.mean()),
                    route4=int((g.router_h==4).sum()),route24=int((g.router_h==24).sum()),route48=int((g.router_h==48).sum())))
pd.DataFrame(mon).to_csv(OUT/'LAB116_2026_router_monthly.csv',index=False)

# report
lines=['# LAB116 — REGIME → HORIZON ROUTER','',
'Frozen Z context: fresh |Z|>=1 inverse crowd. No new signal optimization.',
'Router uses only information available at signal time. Rolling edge uses prior 60 calendar days and only Z outcomes whose horizon had fully completed before the current signal.',
f'Minimum rolling sample={MIN_ROLL_N}. Production-compatible shell for monetization diagnostic: entry next M5 open, SL={STOP_ATR:.2f} H1 ATR, TP={TP_R:.2f}R, one position, stop-first same-bar.',
'Costs tested: 0 / 2.81 / 7.5 bps RT proxy. Equity DD is 5m mark-to-market for the one-position simulation. 0.25% scaling is shown for prop-risk intuition.',
'Important: 2025-26 is repeatedly inspected development OOS, not pristine validation. STATIC_REGIME was motivated by LAB115 and is exploratory.','',
'CAUSAL_ROUTER: if both rolling 24h and 48h edge <=0 -> SKIP; LOW vol + H4 aligned + positive 48h edge -> 48h; otherwise positive 24h -> 24h; else positive 48h -> 48h; else optional positive 4h -> 4h.','']

for cost in [2.81,7.5]:
    lines.append(f'## Cost {cost} bps')
    for policy in POLICIES:
        a=s[(s.policy==policy)&(s.cost_bps==cost)&(s.split=='ALL')]
        o=s[(s.policy==policy)&(s.cost_bps==cost)&(s.split=='OOS')]
        if len(a) and len(o):
            a=a.iloc[0];o=o.iloc[0]
            lines.append(f"- {policy}: ALL N={int(a.n)} EV={a.ev:+.3f}R PF={a.pf:.2f} R/mo={a.r_month:+.2f} MTM-DD={a.max_mtm_dd_r:.1f}R ({a.max_mtm_dd_pct_at_025:.2f}% @0.25%) daily={a.max_daily_dd_r:.1f}R ({a.max_daily_dd_pct_at_025:.2f}%) | OOS N={int(o.n)} EV={o.ev:+.3f} PF={o.pf:.2f}")
    lines.append('')

(OUT/'LAB116_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB116_meta.json').write_text(json.dumps(dict(
    signal='fresh |Z|>=1 inverse crowd',
    rolling_days=ROLL_DAYS,min_roll_n=MIN_ROLL_N,
    policies=POLICIES,
    router='causal 60d kill switch + low-vol/H4 alignment horizon choice',
    shell=dict(entry='next M5 open',stop_atr=STOP_ATR,tp_r=TP_R,one_position=True,same_bar='stop-first'),
    costs_bps=COSTS_BPS,
    caveat='development evidence; repeated OOS; costs proxy; no swap/funding/slippage beyond bps; do not deploy without broker/prop specs'
),indent=2))
print('\n'.join(lines))
