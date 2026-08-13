#!/usr/bin/env python3
"""U02C4 — SAME_STATE_INCREMENTAL_VALUE / RANDOM-TIME NULL.

Preregistered focus cells from U02C2/U02C3:
- BUY TIER_A
- BUY OTHER_B3 (broad B3 BUY shell)
- BUY TIER_B
- SELL SELL_B3

For every episode-first v283 opportunity, sample K random M5 timestamps from the
same continuous causal H4 market-clock state episode. The null is not a deployable
strategy; it is a counterfactual timing benchmark inside the same realized regime
window. Primary inference is paired at the v283-event level:
    delta = v283 outcome - mean(random outcomes matched to that event)
Bootstrap resamples v283 events, not individual random draws.

Exit geometry is exactly U02C3: no TP, SL=1.5*completed H1 ATR14, otherwise
time-exit at 24/48/72h, $27.5/BTC cost proxy.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as m
import u02c3_no_tp_time_exit as n

OUT=Path('u02c4_out'); OUT.mkdir(exist_ok=True)
FOCUS=[('BUY','TIER_A'),('BUY','OTHER_B3'),('BUY','TIER_B'),('SELL','SELL_B3')]
K=200
SEED=28304
B=20000
H=[24,48,72]


def pf(s):
    s=pd.Series(s).dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def build_clock_grid():
    m5=m.load_zip(m.M5ZIP)
    h4=m.h4_supertrend(m5)
    rows=[]
    for side in ['BUY','SELL']:
        g=m5[['time']].copy(); g['action']=side
        g=m.attach_clock(g,h4).dropna(subset=['st_age','st_dir']).copy()
        g['market_state']=g.apply(m.state_label,axis=1)
        # A state episode is a continuous run of the same side-specific canonical state.
        new=g.market_state.ne(g.market_state.shift(1))
        g['state_episode_id']=new.cumsum().astype(int)
        g['state_episode_key']=side+'|'+g.state_episode_id.astype(str)
        rows.append(g[['time','action','market_state','st_dir','st_age','h4_trade_relation','state_episode_id','state_episode_key']])
    return pd.concat(rows,ignore_index=True).sort_values(['action','time']).reset_index(drop=True)


def attach_episode_ids(ep,grid):
    out=[]
    for side,g in ep.groupby('action'):
        z=grid[grid.action.eq(side)].sort_values('time')
        q=pd.merge_asof(g.sort_values('time'),z[['time','state_episode_id','state_episode_key']],on='time',direction='backward')
        out.append(q)
    x=pd.concat(out,ignore_index=True).sort_values('time').reset_index(drop=True)
    x['event_id']=np.arange(1,len(x)+1)
    return x


def sample_random(ep,grid,data_end):
    rng=np.random.default_rng(SEED)
    rows=[]
    latest=data_end-pd.Timedelta(hours=max(H)+1)
    # Cache candidate times per side/state episode for speed and exact matching.
    cache={}
    for r in ep.itertuples(index=False):
        key=(r.action,int(r.state_episode_id))
        if key not in cache:
            g=grid[(grid.action==r.action)&(grid.state_episode_id==int(r.state_episode_id))&(grid.time<=latest)]
            cache[key]=g.time.to_numpy(dtype='datetime64[ns]')
        cand=cache[key]
        if len(cand)==0: continue
        # Exclude the actual v283 M5 timestamp when alternatives exist.
        mask=cand!=np.datetime64(pd.Timestamp(r.time))
        c2=cand[mask] if mask.any() else cand
        idx=rng.choice(len(c2),size=K,replace=len(c2)<K)
        for draw,j in enumerate(idx,1):
            rows.append({'time':pd.Timestamp(c2[int(j)]),'action':r.action,'market_state':r.market_state,
                         'state_episode_id':int(r.state_episode_id),'state_episode_key':r.state_episode_key,
                         'match_event_id':int(r.event_id),'draw_id':draw})
    return pd.DataFrame(rows)


def boot_ci(d,seed_offset=0):
    d=np.asarray(pd.Series(d).dropna(),float)
    if len(d)<2:return (np.nan,np.nan,np.nan)
    rng=np.random.default_rng(SEED+seed_offset)
    means=np.empty(B,float)
    for i in range(B): means[i]=rng.choice(d,size=len(d),replace=True).mean()
    return float(np.quantile(means,.025)),float(np.quantile(means,.975)),float((means>0).mean())


def state_metrics(actual,random):
    rows=[]; paired_rows=[]
    for side,state in FOCUS:
        a=actual[(actual.action==side)&(actual.market_state==state)].copy()
        rr=random[(random.action==side)&(random.market_state==state)].copy()
        for hh in H:
            col=f'notp{hh}_R'; pct=f'notp{hh}_pct'
            # Per-event matched random mean: this is the primary null comparator.
            rm=rr.groupby('match_event_id').agg(rand_R=(col,'mean'),rand_pct=(pct,'mean')).reset_index()
            p=a[['event_id','time',col,pct]].merge(rm,left_on='event_id',right_on='match_event_id',how='inner')
            p['delta_R']=p[col]-p.rand_R; p['delta_pct']=p[pct]-p.rand_pct
            lo,hi,prob=boot_ci(p.delta_R,hh+len(state))
            plo,phi,pprob=boot_ci(p.delta_pct,100+hh+len(state))
            rows.append({'side':side,'state':state,'horizon_h':hh,'N_events':len(p),'random_draws_per_event':K,
                         'v283_EV_R':float(p[col].mean()) if len(p) else np.nan,'v283_PF_R':pf(p[col]),'v283_WR':float((p[col]>0).mean()) if len(p) else np.nan,
                         'random_EV_R':float(p.rand_R.mean()) if len(p) else np.nan,
                         'delta_EV_R':float(p.delta_R.mean()) if len(p) else np.nan,'delta_R_CI_lo':lo,'delta_R_CI_hi':hi,'P_delta_R_gt0':prob,
                         'beats_event_random_mean':float((p.delta_R>0).mean()) if len(p) else np.nan,
                         'v283_EV_pct':float(p[pct].mean()) if len(p) else np.nan,'random_EV_pct':float(p.rand_pct.mean()) if len(p) else np.nan,
                         'delta_EV_pct':float(p.delta_pct.mean()) if len(p) else np.nan,'delta_pct_CI_lo':plo,'delta_pct_CI_hi':phi,'P_delta_pct_gt0':pprob})
            p['side']=side; p['state']=state; p['horizon_h']=hh; paired_rows.append(p)
    return pd.DataFrame(rows),pd.concat(paired_rows,ignore_index=True)


def yearly_metrics(paired):
    x=paired.copy(); x['year']=pd.to_datetime(x.time).dt.year
    rows=[]
    for (y,side,state,hh),g in x.groupby(['year','side','state','horizon_h']):
        rows.append({'year':int(y),'side':side,'state':state,'horizon_h':int(hh),'N':len(g),
                     'v283_EV_R':g[[c for c in g.columns if c==f'notp{int(hh)}_R'][0]].mean(),
                     'random_EV_R':g.rand_R.mean(),'delta_EV_R':g.delta_R.mean(),'beats_random':(g.delta_R>0).mean()})
    return pd.DataFrame(rows)


def random_distribution_metrics(random):
    rows=[]
    for (side,state),g in random.groupby(['action','market_state']):
        if (side,state) not in FOCUS: continue
        for hh in H:
            c=f'notp{hh}_R'
            rows.append({'side':side,'state':state,'horizon_h':hh,'N_draws':len(g),'EV_R':g[c].mean(),'PF_R':pf(g[c]),'WR':(g[c]>0).mean(),'EV_pct':g[f'notp{hh}_pct'].mean(),'SL_rate':(g[f'exit{hh}']=='SL').mean()})
    return pd.DataFrame(rows)


def main():
    # Rebuild identical U02C3 episode-first opportunity population.
    ep=n.build_events()
    ep=ep[[ (r.action,r.market_state) in FOCUS for r in ep.itertuples(index=False) ]].copy()
    grid=build_clock_grid()
    ep=attach_episode_ids(ep,grid)
    # Sanity: event state must equal grid state for its episode.
    gstate=grid[['action','state_episode_id','market_state']].drop_duplicates()
    chk=ep.merge(gstate,on=['action','state_episode_id'],suffixes=('','_grid'),how='left')
    bad=chk[chk.market_state!=chk.market_state_grid]
    if len(bad): raise RuntimeError(f'state episode mismatch N={len(bad)}')
    m1=m.load_zip(m.M1ZIP); data_end=m1.time.max()
    random_events=sample_random(ep,grid,data_end)
    # Replay actual and random under identical no-TP geometry. n.replay loads the same frozen M1 internally.
    actual=n.replay(ep); random=n.replay(random_events)
    actual.to_csv(OUT/'v283_focus_actual_no_tp.csv',index=False)
    random.to_csv(OUT/'random_same_state_draws_no_tp.csv',index=False)
    sm,paired=state_metrics(actual,random); sm.to_csv(OUT/'same_state_null_summary.csv',index=False); paired.to_csv(OUT/'paired_event_deltas.csv',index=False)
    yr=yearly_metrics(paired); yr.to_csv(OUT/'yearly_paired_deltas.csv',index=False)
    rd=random_distribution_metrics(random); rd.to_csv(OUT/'random_distribution_metrics.csv',index=False)

    # Simple decision labels: evidence refers to timing increment, not state edge.
    dec=[]
    for r in sm[sm.horizon_h==24].itertuples(index=False):
        if r.N_events<20: label='INSUFFICIENT_N'
        elif r.delta_R_CI_lo>0: label='V283_TIMING_ADD'
        elif r.delta_R_CI_hi<0: label='V283_TIMING_HARMS'
        else: label='NO_CLEAR_INCREMENT'
        dec.append({'side':r.side,'state':r.state,'N':r.N_events,'delta24_R':r.delta_EV_R,'CI_lo':r.delta_R_CI_lo,'CI_hi':r.delta_R_CI_hi,'P_delta_gt0':r.P_delta_R_gt0,'decision':label})
    dec=pd.DataFrame(dec); dec.to_csv(OUT/'decision_24h.csv',index=False)

    summary={'lab':'U02C4_SAME_STATE_INCREMENTAL_VALUE_RANDOM_TIME_NULL','focus':FOCUS,'K_random_per_event':K,'bootstrap_resamples':B,'seed':SEED,
             'null_definition':'random M5 timestamp inside the same continuous side-specific H4 market-clock state episode; event-level paired inference',
             'exit':'no TP; SL=1.5x completed H1 ATR14; otherwise 24/48/72h time exit; $27.5/BTC cost proxy',
             'important_caveat':'random comparator conditions on the realized full state episode window and is a statistical null, not a causal deployable strategy'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    rep=['# U02C4 — SAME-STATE INCREMENTAL VALUE / RANDOM-TIME NULL','',
         'Primary question: does v283 choose a better timestamp than a random timestamp inside the exact same realized H4 market-clock episode?','',
         '**Null:** 200 random M5 timestamps per v283 episode-first event, same side and same continuous state episode. Paired bootstrap resamples v283 events, not random draws.','',
         '**Exit:** no TP; SL=1.5×completed H1 ATR14; otherwise time exit; $27.5/BTC cost proxy.','',
         '## Paired same-state results','',sm.to_markdown(index=False),'','## 24h decision panel','',dec.to_markdown(index=False),'','## Yearly paired deltas','',yr.to_markdown(index=False),'','## Caveat','',
         'This is a timing-alpha null test on the historical default-v283 stateless shadow, not exact MT5 lifecycle parity. The random comparator uses the realized full state window only as a statistical benchmark; it is not a deployable trading rule.']
    (OUT/'REPORT.md').write_text('\n'.join(rep))
    print('SAME-STATE NULL SUMMARY'); print(sm.to_string(index=False)); print('\n24H DECISIONS'); print(dec.to_string(index=False)); print('\nYEARLY'); print(yr.to_string(index=False))

if __name__=='__main__': main()
