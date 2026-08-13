#!/usr/bin/env python3
"""U02C6B — causal risk-set correction for v283 occurrence selector.

Corrects a future-conditioning flaw in U02C6A: controls must NOT be restricted to
episodes that never get v283 later. At each treated episode's first fixed H4 clock
strictly after its first occurrence, controls are B3 episodes that:
- are in the same calendar year,
- are still active at the identical relative B3 age/delay,
- have had NO v283 BUY occurrence at or before that control clock.
They may receive v283 later.

Matching controls use causal volatility measured at the comparison clock:
RV168_control = sqrt(sum(previous 168 completed H1 log-return^2))*100
ATR% = completed H1 ATR14/H1 close*100.

Primary sensitivity estimators: nearest-1 and mean of nearest-5 in z(log RV168, log ATR%).
Outcome: no TP; SL=1.5*H1 ATR14; 48h time exit; $27.5/BTC.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import u02c5_periodic_state_entry_ablation as u5
import u02c6_b3_v283_occurrence_selection as a

OUT=Path('u02c6b_out'); OUT.mkdir(exist_ok=True)
BOOT=20000; SEED=283061


def ctrl_lookup(h1,t):
    q=int(np.searchsorted(h1.close_time.to_numpy('datetime64[ns]'),np.datetime64(pd.Timestamp(t)),'right')-1)
    if q<0:return (np.nan,np.nan)
    return float(h1.rv168_control_pct.iloc[q]),float(h1.atr_pct.iloc[q])


def smd(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float);x=x[np.isfinite(x)];y=y[np.isfinite(y)]
    if len(x)<2 or len(y)<2:return np.nan
    p=np.sqrt((x.var(ddof=1)+y.var(ddof=1))/2)
    return float((x.mean()-y.mean())/p) if p>0 else np.nan


def boot(x,seed):
    z=np.asarray(pd.Series(x).dropna(),float);rng=np.random.default_rng(seed)
    idx=rng.integers(0,len(z),size=(BOOT,len(z)));m=z[idx].mean(1)
    return z.mean(),np.quantile(m,.025),np.quantile(m,.975),(m>0).mean()


def main():
    m1=base.load_zip(base.M1ZIP);m5=base.load_zip(base.M5ZIP);h1=a.h1_controls(m1)
    clock=u5.build_clock(m5);eps=u5.state_episodes(clock);eps=eps[eps.state=='B3_BUY'].copy()
    eps=a.attach_episode_controls(eps,h1);eps=a.mark_occurrence(eps)
    treated=a.build_causal_with(eps,m1,h1).copy()
    # comparison-time causal vol features for treated
    tv=[]
    for r in treated.itertuples(index=False):
        rv,ap=ctrl_lookup(h1,r.selector_time);tv.append((rv,ap))
    treated['rv_at_compare']=[x[0] for x in tv];treated['atrpct_at_compare']=[x[1] for x in tv]
    treated=treated.dropna(subset=['rv_at_compare','atrpct_at_compare']).copy()

    rows=[]; riskset_rows=[]
    for tr in treated.itertuples(index=False):
        delay=float(tr.selector_delay_h); year=int(pd.Timestamp(tr.start).year)
        cand=eps[(eps.episode_id!=tr.episode_id)&(eps.start.dt.year==year)&(eps.duration_h>delay)].copy()
        cand['control_time']=cand.start+pd.to_timedelta(delay,unit='h')
        # Causal risk set: no occurrence known at or before comparison clock.
        cand=cand[cand.first_occurrence.isna() | (cand.first_occurrence>cand.control_time)].copy()
        if cand.empty:continue
        cvs=[]
        for c in cand.itertuples(index=False):
            rv,ap=ctrl_lookup(h1,c.control_time);cvs.append((rv,ap))
        cand['rv_at_compare']=[x[0] for x in cvs];cand['atrpct_at_compare']=[x[1] for x in cvs]
        cand=cand.dropna(subset=['rv_at_compare','atrpct_at_compare']).copy()
        if cand.empty:continue
        # z scaling within current risk set + treated point to avoid global era-scale dominance.
        comb=pd.concat([cand[['rv_at_compare','atrpct_at_compare']],pd.DataFrame([{'rv_at_compare':tr.rv_at_compare,'atrpct_at_compare':tr.atrpct_at_compare}])],ignore_index=True)
        Z=np.log(comb.clip(lower=1e-12));mu=Z.mean();sd=Z.std(ddof=0).replace(0,1)
        zc=(np.log(cand[['rv_at_compare','atrpct_at_compare']].clip(lower=1e-12))-mu)/sd
        zt=(np.log(pd.Series({'rv_at_compare':tr.rv_at_compare,'atrpct_at_compare':tr.atrpct_at_compare}))-mu)/sd
        cand['dist']=np.sqrt(((zc-zt)**2).sum(axis=1))
        cand=cand.sort_values('dist')
        outcomes=[]
        for c in cand.head(5).itertuples(index=False):
            rr=a.replay_one(c.control_time,m1,h1)
            if rr:
                outcomes.append((int(c.episode_id),float(c.dist),float(c.rv_at_compare),float(c.atrpct_at_compare),float(rr['R']),float(rr['pct'])))
        if not outcomes:continue
        k1=outcomes[0]; k5=outcomes
        rows.append({'treated_episode_id':int(tr.episode_id),'year':year,'delay_h':delay,'treated_R':float(tr.R),'treated_pct':float(tr.pct),
                     'treated_rv':float(tr.rv_at_compare),'treated_atrpct':float(tr.atrpct_at_compare),'riskset_N':len(cand),
                     'k1_control_episode':k1[0],'k1_distance':k1[1],'k1_R':k1[4],'k1_pct':k1[5],
                     'k5_N':len(k5),'k5_mean_distance':float(np.mean([x[1] for x in k5])),'k5_mean_R':float(np.mean([x[4] for x in k5])),'k5_mean_pct':float(np.mean([x[5] for x in k5]))})
        for rank,o in enumerate(outcomes,1):
            riskset_rows.append({'treated_episode_id':int(tr.episode_id),'rank':rank,'control_episode_id':o[0],'distance':o[1],'control_rv':o[2],'control_atrpct':o[3],'control_R':o[4],'control_pct':o[5]})
    p=pd.DataFrame(rows);p['delta_k1_R']=p.treated_R-p.k1_R;p['delta_k5_R']=p.treated_R-p.k5_mean_R;p['delta_k1_pct']=p.treated_pct-p.k1_pct;p['delta_k5_pct']=p.treated_pct-p.k5_mean_pct
    p.to_csv(OUT/'riskset_pairs.csv',index=False);rs=pd.DataFrame(riskset_rows);rs.to_csv(OUT/'riskset_controls_top5.csv',index=False)

    summary=[]
    for kind in ['k1','k5']:
        z=boot(p[f'delta_{kind}_R'],SEED+(1 if kind=='k1' else 5));zp=boot(p[f'delta_{kind}_pct'],SEED+11+(1 if kind=='k1' else 5))
        control_R=p.k1_R.mean() if kind=='k1' else p.k5_mean_R.mean(); control_pct=p.k1_pct.mean() if kind=='k1' else p.k5_mean_pct.mean()
        summary.append({'estimator':kind.upper(),'N_treated':len(p),'treated_EV_R':p.treated_R.mean(),'control_EV_R':control_R,'delta_R':z[0],'CI_R_lo':z[1],'CI_R_hi':z[2],'P_delta_R_gt0':z[3],
                        'treated_EV_pct':p.treated_pct.mean(),'control_EV_pct':control_pct,'delta_pct':zp[0],'CI_pct_lo':zp[1],'CI_pct_hi':zp[2],'P_delta_pct_gt0':zp[3],
                        'median_delay_h':p.delay_h.median(),'median_riskset_N':p.riskset_N.median()})
    sm=pd.DataFrame(summary);sm.to_csv(OUT/'riskset_summary.csv',index=False)

    yearly=[]
    for y,g in p.groupby('year'):
        for kind in ['k1','k5']:
            z=boot(g[f'delta_{kind}_R'],SEED+int(y)+(1 if kind=='k1' else 5))
            c=g.k1_R.mean() if kind=='k1' else g.k5_mean_R.mean()
            yearly.append({'year':int(y),'estimator':kind.upper(),'N':len(g),'treated_EV_R':g.treated_R.mean(),'control_EV_R':c,'delta_R':z[0],'P_delta_R_gt0':z[3]})
    yr=pd.DataFrame(yearly);yr.to_csv(OUT/'riskset_yearly.csv',index=False)

    # Balance for nearest-1 and top5 controls at comparison time.
    k1=rs[rs['rank']==1].merge(p[['treated_episode_id','treated_rv','treated_atrpct']],on='treated_episode_id')
    bal=pd.DataFrame([{'estimator':'K1','SMD_log_RV168':smd(np.log(k1.treated_rv),np.log(k1.control_rv)),'SMD_log_ATR_pct':smd(np.log(k1.treated_atrpct),np.log(k1.control_atrpct)),
                       'unique_control_episodes':k1.control_episode_id.nunique(),'max_control_reuse':int(k1.control_episode_id.value_counts().max()) if len(k1) else 0},
                      {'estimator':'K5_POOL','SMD_log_RV168':smd(np.repeat(np.log(p.treated_rv),5)[:len(rs)],np.log(rs.control_rv)) if len(rs) else np.nan,
                       'SMD_log_ATR_pct':smd(np.repeat(np.log(p.treated_atrpct),5)[:len(rs)],np.log(rs.control_atrpct)) if len(rs) else np.nan,
                       'unique_control_episodes':rs.control_episode_id.nunique(),'max_control_reuse':int(rs.control_episode_id.value_counts().max()) if len(rs) else 0}])
    bal.to_csv(OUT/'riskset_balance.csv',index=False)

    # Descriptive volatility and exposure-time association only.
    desc=[]
    for occ,g in eps.groupby('v283_occurs'):
        desc.append({'group':'WITH' if occ else 'NEVER_WITHIN_EPISODE','N':len(g),'median_duration_h':g.duration_h.median(),'mean_duration_h':g.duration_h.mean(),
                     'median_onset_RV168':g.rv168_control_pct.median(),'median_onset_ATR_pct':g.atr_pct.median(),'median_occurrence_delay_h':g.occurrence_delay_h.median()})
    desc=pd.DataFrame(desc);desc.to_csv(OUT/'exposure_volatility_descriptive.csv',index=False)

    rep=['# U02C6B — B3 OCCURRENCE CAUSAL RISK-SET CONTROL','',
         '**Correction:** controls are NOT future-defined never-occurrence episodes. At each treated comparison age, controls are same-year B3 episodes still active at the identical delay and with no v283 occurrence known yet. They may get v283 later.','',
         '**Matching:** causal comparison-time RV168_control + ATR%, nearest-1 and nearest-5 sensitivity. Entry is the fixed H4 clock after occurrence, not the v283 timestamp.','',
         '## Risk-set result','',sm.to_markdown(index=False),'','## Yearly','',yr.to_markdown(index=False),'','## Match balance/reuse','',bal.to_markdown(index=False),'','## Descriptive exposure-time association','',desc.to_markdown(index=False),'','## Decision rule','',
         'Occurrence is accepted as a B3 selector only if the positive delta survives causal risk-set controls, volatility matching, and year splits. A result that exists only against future-defined NEVER controls is rejected.']
    (OUT/'REPORT.md').write_text('\n'.join(rep))
    (OUT/'summary.json').write_text(json.dumps({'seed':SEED,'bootstrap':BOOT,'control':'same-year identical B3 delay, no occurrence known yet','estimators':['K1','K5'],'entry':'first fixed H4 clock after occurrence','exit':'SL1.5 H1 ATR or 48h, no TP'},indent=2))
    print('SUMMARY\n',sm.to_string(index=False));print('\nYEARLY\n',yr.to_string(index=False));print('\nBALANCE\n',bal.to_string(index=False));print('\nDESC\n',desc.to_string(index=False))

if __name__=='__main__':main()
