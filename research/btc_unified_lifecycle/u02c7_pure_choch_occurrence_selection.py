#!/usr/bin/env python3
"""U02C7 — PURE CHoCH OCCURRENCE SELECTION ABLATION.

Question: can the successful B3 v283-occurrence selector from U02C6B be reduced to the
raw CHoCH detector itself?

Frozen before outcomes:
- Population: canonical B3 BUY episodes from U02C5 (H4 ST age 28..58).
- PRIMARY selector: bullish H1 CHoCH occurrence using literal v283 detector mechanics:
  pivot strength=2, lookback=20, buffer=0.05*completed H1 ATR14.
- SECONDARY: bullish M15 CHoCH and H1_OR_M15 CHoCH.
- No PRE score, no AI, no BOS gate, no LateEntry, no D1 veto, no knife/panic, no FVG/OB.
- Causal treated entry: first fixed H4 clock strictly after first occurrence.
- Causal risk-set control: same year, same B3 delay, still-active B3 episode with no
  occurrence of the same selector known yet. Controls may receive it later.
- Match at comparison clock on log(RV168_control) and log(ATR%).
- K1 and K5 sensitivity estimators.
- Exit: SL=1.5*completed H1 ATR14, no TP, 48h time exit, $27.5/BTC cost proxy.
"""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import u02c2_fast_v283_shadow as fast
import u02c5_periodic_state_entry_ablation as u5
import u02c6_b3_v283_occurrence_selection as a
import u02c6b_b3_occurrence_riskset_control as rb

OUT=Path('u02c7_out'); OUT.mkdir(exist_ok=True)
BOOT=20000; SEED=28307


def build_choch_events(m1):
    h1=a.h1_controls(m1)
    m15=base.resample(m1,'15min')
    # Exact detector uses H1 ATR for both H1 and M15 CHoCH buffers.
    h1av=h1.atr14.to_numpy(float)
    c1=fast.precompute_choch(h1,h1av)
    hct=h1.close_time.to_numpy('datetime64[ns]')
    mct=m15.close_time.to_numpy('datetime64[ns]')
    av15=np.full(len(m15),np.nan)
    for i,t in enumerate(mct):
        q=int(np.searchsorted(hct,t,'right')-1)
        if q>=0: av15[i]=h1av[q]
    c15=fast.precompute_choch(m15,av15)
    h1bull=pd.DatetimeIndex(h1.loc[c1==1,'close_time']).sort_values()
    m15bull=pd.DatetimeIndex(m15.loc[c15==1,'close_time']).sort_values()
    anybull=pd.DatetimeIndex(sorted(set(h1bull.tolist())|set(m15bull.tolist())))
    return h1, {'H1':h1bull,'M15':m15bull,'ANY':anybull}


def mark_selector(eps,times,name):
    st=np.asarray(times,dtype='datetime64[ns]')
    rows=[]
    for e in eps.itertuples(index=False):
        aa=int(np.searchsorted(st,np.datetime64(e.start),'left'))
        bb=int(np.searchsorted(st,np.datetime64(e.end),'left'))
        n=bb-aa
        first=pd.Timestamp(st[aa]) if n>0 else pd.NaT
        rows.append({'episode_id':int(e.episode_id),'selector':name,'occurs':int(n>0),'count':int(n),
                     'first_occurrence':first,'occurrence_delay_h':((first-e.start).total_seconds()/3600 if n>0 else np.nan)})
    return eps.merge(pd.DataFrame(rows),on='episode_id',how='left')


def causal_entries(eps,m1,h1):
    rows=[]
    for e in eps[eps.occurs==1].itertuples(index=False):
        t,k=a.next_h4_after(e.start,e.first_occurrence)
        if t>=e.end: continue
        r=a.replay_one(t,m1,h1)
        if r:
            rv,ap=rb.ctrl_lookup(h1,t)
            if np.isfinite(rv) and np.isfinite(ap):
                rows.append({**e._asdict(),'selector_time':t,'selector_delay_h':(t-e.start).total_seconds()/3600,
                             'selector_clock_index':k,'rv_at_compare':rv,'atrpct_at_compare':ap,**r})
    return pd.DataFrame(rows)


def riskset_pairs(treated,eps,h1,m1,selector_name):
    rows=[]; pool=[]
    for tr in treated.itertuples(index=False):
        delay=float(tr.selector_delay_h); year=int(pd.Timestamp(tr.start).year)
        cand=eps[(eps.episode_id!=tr.episode_id)&(eps.start.dt.year==year)&(eps.duration_h>delay)].copy()
        cand['control_time']=cand.start+pd.to_timedelta(delay,unit='h')
        # no same-selector occurrence known yet; future occurrence allowed
        cand=cand[cand.first_occurrence.isna() | (cand.first_occurrence>cand.control_time)].copy()
        if cand.empty: continue
        cvs=[rb.ctrl_lookup(h1,t) for t in cand.control_time]
        cand['rv_at_compare']=[x[0] for x in cvs]; cand['atrpct_at_compare']=[x[1] for x in cvs]
        cand=cand.dropna(subset=['rv_at_compare','atrpct_at_compare']).copy()
        if cand.empty: continue
        comb=pd.concat([cand[['rv_at_compare','atrpct_at_compare']],pd.DataFrame([{'rv_at_compare':tr.rv_at_compare,'atrpct_at_compare':tr.atrpct_at_compare}])],ignore_index=True)
        Z=np.log(comb.clip(lower=1e-12)); mu=Z.mean(); sd=Z.std(ddof=0).replace(0,1)
        zc=(np.log(cand[['rv_at_compare','atrpct_at_compare']].clip(lower=1e-12))-mu)/sd
        zt=(np.log(pd.Series({'rv_at_compare':tr.rv_at_compare,'atrpct_at_compare':tr.atrpct_at_compare}))-mu)/sd
        cand['dist']=np.sqrt(((zc-zt)**2).sum(axis=1)); cand=cand.sort_values('dist')
        outs=[]
        for c in cand.head(5).itertuples(index=False):
            rr=a.replay_one(c.control_time,m1,h1)
            if rr: outs.append((int(c.episode_id),float(c.dist),float(c.rv_at_compare),float(c.atrpct_at_compare),float(rr['R']),float(rr['pct'])))
        if not outs: continue
        k1=outs[0]
        rows.append({'selector':selector_name,'treated_episode_id':int(tr.episode_id),'year':year,'delay_h':delay,
                     'treated_R':float(tr.R),'treated_pct':float(tr.pct),'treated_rv':float(tr.rv_at_compare),'treated_atrpct':float(tr.atrpct_at_compare),
                     'riskset_N':len(cand),'k1_control_episode':k1[0],'k1_distance':k1[1],'k1_R':k1[4],'k1_pct':k1[5],
                     'k5_N':len(outs),'k5_mean_distance':float(np.mean([x[1] for x in outs])),
                     'k5_mean_R':float(np.mean([x[4] for x in outs])),'k5_mean_pct':float(np.mean([x[5] for x in outs]))})
        for rank,o in enumerate(outs,1):
            pool.append({'selector':selector_name,'treated_episode_id':int(tr.episode_id),'rank':rank,'control_episode_id':o[0],
                         'distance':o[1],'control_rv':o[2],'control_atrpct':o[3],'control_R':o[4],'control_pct':o[5]})
    p=pd.DataFrame(rows); rs=pd.DataFrame(pool)
    if len(p):
        p['delta_k1_R']=p.treated_R-p.k1_R; p['delta_k5_R']=p.treated_R-p.k5_mean_R
        p['delta_k1_pct']=p.treated_pct-p.k1_pct; p['delta_k5_pct']=p.treated_pct-p.k5_mean_pct
    return p,rs


def summarize(selector,treated,p,rs):
    out=[]
    if not len(p): return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    for kind in ['k1','k5']:
        z=rb.boot(p[f'delta_{kind}_R'],SEED+(1 if kind=='k1' else 5))
        zp=rb.boot(p[f'delta_{kind}_pct'],SEED+11+(1 if kind=='k1' else 5))
        cr=p.k1_R.mean() if kind=='k1' else p.k5_mean_R.mean(); cp=p.k1_pct.mean() if kind=='k1' else p.k5_mean_pct.mean()
        out.append({'selector':selector,'estimator':kind.upper(),'N_treated':len(p),'treated_EV_R':p.treated_R.mean(),'control_EV_R':cr,
                    'delta_R':z[0],'CI_R_lo':z[1],'CI_R_hi':z[2],'P_delta_R_gt0':z[3],
                    'treated_EV_pct':p.treated_pct.mean(),'control_EV_pct':cp,'delta_pct':zp[0],'CI_pct_lo':zp[1],'CI_pct_hi':zp[2],'P_delta_pct_gt0':zp[3],
                    'median_delay_h':p.delay_h.median(),'median_riskset_N':p.riskset_N.median()})
    yr=[]
    for y,g in p.groupby('year'):
        for kind in ['k1','k5']:
            z=rb.boot(g[f'delta_{kind}_R'],SEED+int(y)+(1 if kind=='k1' else 5))
            cr=g.k1_R.mean() if kind=='k1' else g.k5_mean_R.mean()
            yr.append({'selector':selector,'year':int(y),'estimator':kind.upper(),'N':len(g),'treated_EV_R':g.treated_R.mean(),'control_EV_R':cr,'delta_R':z[0],'P_delta_R_gt0':z[3]})
    # K1 balance only + K5 pooled reuse diagnostic
    k1=rs[rs['rank']==1].merge(p[['treated_episode_id','treated_rv','treated_atrpct']],on='treated_episode_id') if len(rs) else pd.DataFrame()
    bal=[]
    if len(k1):
        bal.append({'selector':selector,'estimator':'K1','SMD_log_RV168':rb.smd(np.log(k1.treated_rv),np.log(k1.control_rv)),
                    'SMD_log_ATR_pct':rb.smd(np.log(k1.treated_atrpct),np.log(k1.control_atrpct)),
                    'unique_control_episodes':k1.control_episode_id.nunique(),'max_control_reuse':int(k1.control_episode_id.value_counts().max())})
    return pd.DataFrame(out),pd.DataFrame(yr),pd.DataFrame(bal)


def v283_overlap(eps):
    sh=pd.read_csv(a.SHADOW); sh['time']=pd.to_datetime(sh.time)
    sh=sh[(sh.action=='BUY')&(sh.pass_stateless==1)].sort_values('time')
    st=sh.time.to_numpy('datetime64[ns]')
    vals=[]
    for e in eps.itertuples(index=False):
        aa=np.searchsorted(st,np.datetime64(e.start),'left');bb=np.searchsorted(st,np.datetime64(e.end),'left')
        vals.append(int(bb>aa))
    return pd.Series(vals,index=eps.index)


def main():
    m1=base.load_zip(base.M1ZIP); m5=base.load_zip(base.M5ZIP)
    h1,events=build_choch_events(m1)
    clock=u5.build_clock(m5); eps=u5.state_episodes(clock); eps=eps[eps.state=='B3_BUY'].copy().reset_index(drop=True)
    eps['v283_occurs']=v283_overlap(eps)

    sums=[]; yrs=[]; bals=[]; census=[]; overlap=[]
    for sel in ['H1','M15','ANY']:
        ex=mark_selector(eps,events[sel],sel)
        treated=causal_entries(ex,m1,h1)
        p,rs=riskset_pairs(treated,ex,h1,m1,sel)
        s,y,b=summarize(sel,treated,p,rs)
        if len(s): sums.append(s)
        if len(y): yrs.append(y)
        if len(b): bals.append(b)
        ex.to_csv(OUT/f'episodes_{sel}.csv',index=False); treated.to_csv(OUT/f'treated_{sel}.csv',index=False); p.to_csv(OUT/f'pairs_{sel}.csv',index=False); rs.to_csv(OUT/f'controls_{sel}.csv',index=False)
        census.append({'selector':sel,'episodes_total':len(ex),'episodes_occurrence':int(ex.occurs.sum()),'causal_entries':len(treated),
                       'median_occurrence_delay_h':ex.loc[ex.occurs==1,'occurrence_delay_h'].median()})
        both=((ex.occurs==1)&(ex.v283_occurs==1)).sum(); union=((ex.occurs==1)|(ex.v283_occurs==1)).sum()
        overlap.append({'selector':sel,'choch_occurrence_episodes':int(ex.occurs.sum()),'v283_occurrence_episodes':int(ex.v283_occurs.sum()),
                        'intersection':int(both),'jaccard':float(both/union) if union else np.nan,
                        'v283_covered_by_choch':float(both/ex.v283_occurs.sum()) if ex.v283_occurs.sum() else np.nan,
                        'choch_precision_vs_v283_episode':float(both/ex.occurs.sum()) if ex.occurs.sum() else np.nan})
    sm=pd.concat(sums,ignore_index=True); yr=pd.concat(yrs,ignore_index=True); bal=pd.concat(bals,ignore_index=True)
    cen=pd.DataFrame(census); ov=pd.DataFrame(overlap)
    sm.to_csv(OUT/'summary.csv',index=False); yr.to_csv(OUT/'yearly.csv',index=False); bal.to_csv(OUT/'balance.csv',index=False); cen.to_csv(OUT/'census.csv',index=False); ov.to_csv(OUT/'overlap_with_v283.csv',index=False)

    # Explicit benchmark from accepted U02C6B for readability.
    bench=pd.DataFrame([{'selector':'V283_OCCURRENCE_U02C6B','estimator':'K1','N_treated':48,'treated_EV_R':0.91787,'control_EV_R':-0.226739,'delta_R':1.144609,'CI_R_lo':0.028313,'CI_R_hi':2.332713,'P_delta_R_gt0':0.9779},
                        {'selector':'V283_OCCURRENCE_U02C6B','estimator':'K5','N_treated':48,'treated_EV_R':0.91787,'control_EV_R':-0.046170,'delta_R':0.964039,'CI_R_lo':-0.017435,'CI_R_hi':2.093273,'P_delta_R_gt0':0.9725}])
    bench.to_csv(OUT/'u02c6b_benchmark.csv',index=False)
    rep=['# U02C7 — PURE CHoCH OCCURRENCE SELECTION ABLATION','',
         '**Primary:** H1 bullish CHoCH only. Secondary: M15 and H1_OR_M15. No AI, PRE, BOS gate, LateEntry, D1 veto, knife/panic, FVG/OB.','',
         '**Entry:** next fixed H4 clock after first occurrence. **Control:** causal same-year same-B3-age risk set, matched on current RV168_control + ATR%.','',
         '## Census','',cen.to_markdown(index=False),'','## Selector result','',sm.to_markdown(index=False),'','## Yearly','',yr.to_markdown(index=False),'','## Match balance','',bal.to_markdown(index=False),'','## Overlap with v283 occurrence','',ov.to_markdown(index=False),'','## Accepted v283 benchmark from U02C6B','',bench.to_markdown(index=False),'','## Decision rule','',
         'If H1 CHoCH preserves the U02C6B excess with comparable year stability and acceptable volatility balance, replace v283 occurrence with pure H1 CHoCH in the core. If it collapses, the selector value belongs to additional v283 components and requires component ablation rather than restoration of the whole v283 engine.']
    (OUT/'REPORT.md').write_text('\n'.join(rep))
    (OUT/'summary.json').write_text(json.dumps({'primary':'H1 bullish CHoCH','secondary':['M15 bullish CHoCH','H1_OR_M15 bullish CHoCH'],'pivot_strength':2,'lookback':20,'buffer':'0.05*H1_ATR14','entry':'next H4 clock','control':'causal risk-set same year/same B3 delay + RV168/ATR% matching','exit':'SL1.5 H1 ATR or 48h, no TP'},indent=2))
    print('CENSUS\n',cen.to_string(index=False)); print('\nSUMMARY\n',sm.to_string(index=False)); print('\nYEARLY\n',yr.to_string(index=False)); print('\nBALANCE\n',bal.to_string(index=False)); print('\nOVERLAP\n',ov.to_string(index=False))

if __name__=='__main__': main()
