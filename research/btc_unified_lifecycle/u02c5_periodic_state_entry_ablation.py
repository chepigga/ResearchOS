#!/usr/bin/env python3
"""U02C5 — PERIODIC STATE ENTRY ABLATION.

Tests whether the H4 state itself can be traded with a deterministic clock, without
v283/FVG/event timing.

Frozen research choices:
- canonical clock: H4 Supertrend ATR10 x3, U05 BAR_OPEN lag1 convention
- states: TIER_A BUY = age>58 and H4 ST opposite; B3 BUY = age 28..58
- policies: FIRST_ONLY, 4h, 8h, 12h, 24h from causal state onset
- entry: next M1 open after scheduled H4-clock timestamp
- exit: SL=1.5 x completed H1 ATR14 OR 48h time exit; NO TP
- cost proxy: $27.5/BTC round turn
- diagnostic: 1R per trade
- prop episode budget: max 0.5% initial risk per episode using cadence-safe allocation
  FIRST_ONLY=.50%, 4h=.50%/12, 8h=.50%/6, 12h=.50%/4, 24h=.50%/2.

This is a state-clock lab, not an MT5 lifecycle replay.
"""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base

OUT=Path('u02c5_out'); OUT.mkdir(exist_ok=True)
START=pd.Timestamp('2024-01-01')
END=None
STOP_ATR=1.5
TIME_EXIT_H=48
COST_USD=27.5
EPISODE_BUDGET_PCT=0.50
POLICIES={'FIRST_ONLY':None,'4H':4,'8H':8,'12H':12,'24H':24}


def pf(x):
    s=pd.Series(x).dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def max_dd(values):
    s=pd.Series(values).fillna(0.0).cumsum().to_numpy(float)
    if len(s)==0:return np.nan
    peaks=np.maximum.accumulate(np.r_[0.0,s])
    eq=np.r_[0.0,s]
    return float(np.max(peaks-eq))


def build_clock(m5):
    h4=base.h4_supertrend(m5)
    c=h4[['time','st_dir','st_age','st_dist_atr']].copy()
    # U05 parity convention: at bar-open t, only previous H4 raw state is known.
    for col in ['st_dir','st_age','st_dist_atr']:
        c[col]=c[col].shift(1)
    c=c.dropna(subset=['st_dir','st_age']).copy()
    c=c[c.time>=START].reset_index(drop=True)
    # BUY market-clock state only.
    c['state']='OTHER'
    c.loc[(c.st_age>58)&(c.st_dir==-1),'state']='TIER_A'
    c.loc[(c.st_age>=28)&(c.st_age<=58),'state']='B3_BUY'
    # Continuous state episode, broken on any state change or non-4h gap.
    prev_state=c.state.shift(1); prev_t=c.time.shift(1)
    new=(c.state.ne(prev_state)) | ((c.time-prev_t)>pd.Timedelta(hours=4,minutes=1))
    c['clock_episode_id']=new.cumsum().astype(int)
    return c


def state_episodes(clock):
    z=clock[clock.state.isin(['TIER_A','B3_BUY'])].copy()
    rows=[]
    for (eid,state),g in z.groupby(['clock_episode_id','state']):
        g=g.sort_values('time')
        # Require contiguous same-state rows; clock_episode already handles changes.
        start=g.time.iloc[0]; last=g.time.iloc[-1]
        # The state remains valid over the H4 interval beginning at last row.
        end=last+pd.Timedelta(hours=4)
        rows.append({'episode_id':int(eid),'state':state,'start':start,'end':end,
                     'duration_h':(end-start).total_seconds()/3600.0,'n_h4_bars':len(g),
                     'start_year':start.year})
    return pd.DataFrame(rows).sort_values('start').reset_index(drop=True)


def schedule_entries(episodes):
    rows=[]
    for e in episodes.itertuples(index=False):
        for pol,cad in POLICIES.items():
            if cad is None:
                times=[e.start]
                max_slots=1
            else:
                max_slots=int(math.ceil(TIME_EXIT_H/cad))
                times=[]; t=e.start
                while t<e.end:
                    times.append(t); t=t+pd.Timedelta(hours=cad)
            risk_pct=EPISODE_BUDGET_PCT/max_slots
            for k,t in enumerate(times,1):
                rows.append({'episode_id':e.episode_id,'state':e.state,'episode_start':e.start,
                             'episode_end':e.end,'duration_h':e.duration_h,'policy':pol,
                             'cadence_h':cad if cad is not None else 0,'ordinal':k,
                             'signal_time':t,'risk_pct':risk_pct,'max_slots':max_slots})
    return pd.DataFrame(rows)


def replay(entries,m1,h1):
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float); C=m1.close.to_numpy(float)
    hct=h1.close_time.to_numpy('datetime64[ns]'); ha=h1.atr14.to_numpy(float)
    rows=[]
    for r in entries.itertuples(index=False):
        sig=pd.Timestamp(r.signal_time); et=sig+pd.Timedelta(minutes=1)
        j=int(np.searchsorted(mt,np.datetime64(et),'left'))
        q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1)
        if j>=len(m1) or q<0 or not np.isfinite(ha[q]) or ha[q]<=0: continue
        entry=float(O[j]); sd=STOP_ATR*float(ha[q]); sl=entry-sd
        tend=sig+pd.Timedelta(hours=TIME_EXIT_H)
        je=int(np.searchsorted(mt,np.datetime64(tend),'left'))
        if je<=j or je>=len(m1): continue
        stop_idx=np.flatnonzero(L[j:je]<=sl)
        if stop_idx.size:
            si=j+int(stop_idx[0]); exit_time=pd.Timestamp(m1.time.iloc[si]); exit_price=sl
            rr=-1.0-(COST_USD/sd); pct=-(sd/entry*100.0)-(COST_USD/entry*100.0); ex='SL'
        else:
            exit_time=pd.Timestamp(m1.time.iloc[je]); exit_price=float(O[je])
            rr=(exit_price-entry)/sd-(COST_USD/sd); pct=(exit_price-entry)/entry*100.0-(COST_USD/entry*100.0); ex='TIME'
        hi=float(H[j:je].max()); lo=float(L[j:je].min())
        z=r._asdict(); z.update(entry_time=et,entry=entry,atr_h1=float(ha[q]),stop_dist=sd,
                                exit_time=exit_time,exit_price=exit_price,exit_type=ex,
                                R=rr,pct=pct,MFE_R=(hi-entry)/sd,MAE_R=(lo-entry)/sd,
                                prop_return_pct=rr*float(r.risk_pct),year=sig.year)
        rows.append(z)
    return pd.DataFrame(rows)


def trade_metrics(x):
    rows=[]
    weeks=(x.signal_time.max()-x.signal_time.min()).total_seconds()/(7*86400) if len(x)>1 else np.nan
    for (state,pol),g in x.groupby(['state','policy']):
        g=g.sort_values('signal_time')
        rows.append({'state':state,'policy':pol,'N_trades':len(g),'N_episodes':g.episode_id.nunique(),
                     'trades_per_week':len(g)/weeks if weeks and weeks>0 else np.nan,
                     'trades_per_episode':len(g)/g.episode_id.nunique(),
                     'EV_R':g.R.mean(),'PF_R':pf(g.R),'WR':(g.R>0).mean(),'SL_rate':(g.exit_type=='SL').mean(),
                     'median_MFE_R':g.MFE_R.median(),'median_MAE_R':g.MAE_R.median(),
                     'sum_R':g.R.sum(),'raw_realized_maxDD_R':max_dd(g.R),
                     'risk_pct_per_trade':g.risk_pct.iloc[0],
                     'sum_prop_return_pct':g.prop_return_pct.sum(),
                     'prop_realized_maxDD_pct':max_dd(g.prop_return_pct)})
    return pd.DataFrame(rows)


def episode_metrics(x):
    e=(x.groupby(['state','policy','episode_id'],as_index=False)
       .agg(episode_start=('episode_start','first'),duration_h=('duration_h','first'),N=('R','size'),
            sum_R=('R','sum'),mean_R=('R','mean'),prop_return_pct=('prop_return_pct','sum'),
            wins=('R',lambda s:int((s>0).sum())),losses=('R',lambda s:int((s<0).sum()))))
    rows=[]
    for (state,pol),g in e.groupby(['state','policy']):
        rows.append({'state':state,'policy':pol,'N_episodes':len(g),'avg_entries_per_episode':g.N.mean(),
                     'median_entries_per_episode':g.N.median(),'max_entries_per_episode':g.N.max(),
                     'EV_sumR_per_episode':g.sum_R.mean(),'median_sumR_per_episode':g.sum_R.median(),
                     'EV_meanR_per_episode':g.mean_R.mean(),
                     'EV_prop_return_pct_per_episode':g.prop_return_pct.mean(),
                     'PF_episode_prop':pf(g.prop_return_pct),'episode_win_rate':(g.prop_return_pct>0).mean(),
                     'sum_prop_return_pct':g.prop_return_pct.sum()})
    return e,pd.DataFrame(rows)


def yearly_metrics(x):
    rows=[]
    for (year,state,pol),g in x.groupby(['year','state','policy']):
        rows.append({'year':int(year),'state':state,'policy':pol,'N':len(g),'episodes':g.episode_id.nunique(),
                     'EV_R':g.R.mean(),'PF_R':pf(g.R),'WR':(g.R>0).mean(),'sum_R':g.R.sum(),
                     'sum_prop_return_pct':g.prop_return_pct.sum()})
    return pd.DataFrame(rows)


def ordinal_metrics(x):
    # Outcome degradation by entry ordinal; diagnostic only.
    rows=[]
    for (state,pol,ord_),g in x.groupby(['state','policy','ordinal']):
        if len(g)>=3:
            rows.append({'state':state,'policy':pol,'ordinal':int(ord_),'N':len(g),'EV_R':g.R.mean(),
                         'PF_R':pf(g.R),'WR':(g.R>0).mean()})
    return pd.DataFrame(rows)


def concurrency(x):
    rows=[]
    for (state,pol),g in x.groupby(['state','policy']):
        events=[]
        for r in g.itertuples(index=False):
            events.append((pd.Timestamp(r.entry_time),1,float(r.risk_pct)))
            events.append((pd.Timestamp(r.exit_time),-1,-float(r.risk_pct)))
        # exits first when equal time
        events=sorted(events,key=lambda z:(z[0],z[1]))
        n=0;risk=0.;maxn=0;maxrisk=0.
        for _,dn,dr in events:
            n+=dn;risk+=dr;maxn=max(maxn,n);maxrisk=max(maxrisk,risk)
        rows.append({'state':state,'policy':pol,'peak_concurrent_positions':maxn,
                     'peak_concurrent_initial_risk_pct':maxrisk})
    return pd.DataFrame(rows)


def main():
    m1=base.load_zip(base.M1ZIP); m5=base.load_zip(base.M5ZIP); h1=base.h1_atr_from_m1(m1)
    clock=build_clock(m5); eps=state_episodes(clock)
    sch=schedule_entries(eps)
    x=replay(sch,m1,h1)
    x.to_csv(OUT/'periodic_state_entries.csv',index=False)
    eps.to_csv(OUT/'state_episodes.csv',index=False)
    tm=trade_metrics(x); tm.to_csv(OUT/'trade_metrics.csv',index=False)
    ee,em=episode_metrics(x); ee.to_csv(OUT/'episode_results.csv',index=False); em.to_csv(OUT/'episode_metrics.csv',index=False)
    yr=yearly_metrics(x); yr.to_csv(OUT/'yearly_metrics.csv',index=False)
    om=ordinal_metrics(x); om.to_csv(OUT/'ordinal_decay.csv',index=False)
    cm=concurrency(x); cm.to_csv(OUT/'concurrency.csv',index=False)
    merged=tm.merge(em,on=['state','policy'],suffixes=('','_ep')).merge(cm,on=['state','policy'])
    merged.to_csv(OUT/'summary_matrix.csv',index=False)

    # Decision-oriented stability panel.
    stab=[]
    for (state,pol),g in yr.groupby(['state','policy']):
        valid=g[g.N>=5]
        stab.append({'state':state,'policy':pol,'years_N5':len(valid),'positive_years':int((valid.EV_R>0).sum()),
                     'min_year_EV_R':valid.EV_R.min() if len(valid) else np.nan,
                     'median_year_EV_R':valid.EV_R.median() if len(valid) else np.nan})
    stab=pd.DataFrame(stab); stab.to_csv(OUT/'year_stability.csv',index=False)

    rep=['# U02C5 — PERIODIC STATE ENTRY ABLATION','',
         '**Question:** after U02C4 rejected v283 as a proven timing-alpha layer, can Tier A BUY and B3 BUY be traded directly by a deterministic clock?','',
         '**Frozen execution:** next M1 open; SL=1.5×completed H1 ATR14; no TP; 48h time exit; cost=$27.5/BTC.','',
         '**Policies:** FIRST_ONLY, then every 4h/8h/12h/24h from causal state onset while the state remains active.','',
         '**Episode risk model:** max 0.50% initial-risk budget per episode using cadence-safe split (4h=/12, 8h=/6, 12h=/4, 24h=/2). Diagnostic EV_R still treats each entry as 1R.','',
         '## Summary','',merged.to_markdown(index=False),'','## Year stability','',stab.to_markdown(index=False),'','## Yearly details','',yr.to_markdown(index=False),'','## Ordinal decay','',om.to_markdown(index=False),'','## Caveat','',
         'The episode-budget equity return is additive small-risk accounting, not mark-to-market portfolio DD. A later unified portfolio replay must model overlap across branches and floating drawdown.']
    (OUT/'REPORT.md').write_text('\n'.join(rep))
    meta={'states':['TIER_A','B3_BUY'],'policies':POLICIES,'stop_atr':STOP_ATR,'time_exit_h':TIME_EXIT_H,
          'cost_usd':COST_USD,'episode_budget_pct':EPISODE_BUDGET_PCT,'clock':'H4 ST ATR10x3 BAR_OPEN lag1',
          'tier_a':'BUY age>58, H4 ST opposite','b3_buy':'BUY age 28..58','no_v283':True,'no_fvg':True}
    (OUT/'summary.json').write_text(json.dumps(meta,indent=2,default=str))
    print('SUMMARY\n',merged.to_string(index=False)); print('\nSTABILITY\n',stab.to_string(index=False)); print('\nYEARLY\n',yr.to_string(index=False)); print('\nORDINAL\n',om.to_string(index=False))

if __name__=='__main__': main()
