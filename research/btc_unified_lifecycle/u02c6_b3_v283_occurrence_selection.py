#!/usr/bin/env python3
"""U02C6 — B3 v283 OCCURRENCE SELECTION ABLATION.

Question:
Does the *occurrence* of at least one default-v283 BUY opportunity identify a better
B3 BUY episode, even though U02C4 rejected exact v283 timestamp as proven timing alpha?

Frozen design before outcomes:
- B3 BUY episode = canonical U02C5 H4 market-clock state, age 28..58.
- v283 occurrence = >=1 historical default-v283 stateless BUY pass inside episode.
- Descriptive WITH/WITHOUT episode comparison is NOT deployable from episode onset.
- Primary causal selector entry = first fixed H4 clock boundary strictly after the
  first v283 occurrence, while B3 state remains active. Never enter on v283 timestamp.
- Comparator = B3 episode with NO v283 occurrence, exact year matched and nearest
  neighbor on causal onset volatility controls (log RV168_control, log ATR%), evaluated
  at the same relative H4-clock delay from episode onset. Matching is with replacement.
- RV168_control is explicitly defined for this lab as sqrt(sum(H1 log-return^2)) over
  the previous 168 completed H1 bars, expressed in percent. It is a volatility control,
  not claimed to be byte-identical to any earlier RV168 implementation.
- ATR% = completed H1 ATR14 / H1 close * 100 at B3 episode onset.
- Exit = SL 1.5 x completed H1 ATR14 at entry OR 48h time exit; no TP; $27.5/BTC cost.
- Primary inference = paired bootstrap over WITH episodes, not over matched/null rows.
- Secondary exploratory: 4h/8h/12h periodic entries after causal selector activation,
  with the same 0.50% episode-risk budget convention as U02C5.
"""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import u02c5_periodic_state_entry_ablation as u5

OUT=Path('u02c6_out'); OUT.mkdir(exist_ok=True)
SHADOW=Path('u01_shadow/u01_v283_shadow_events.csv')
STOP_ATR=1.5
EXIT_H=48
COST=27.5
SEED=28306
BOOT=20000
EP_BUDGET=0.50


def pf(x):
    s=pd.Series(x).dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def h1_controls(m1):
    h=base.h1_atr_from_m1(m1).copy()
    lr=np.log(h.close/h.close.shift(1))
    h['rv168_control_pct']=np.sqrt((lr*lr).rolling(168,min_periods=168).sum())*100.0
    h['atr_pct']=h.atr14/h.close*100.0
    return h


def attach_episode_controls(eps,h1):
    x=eps.copy().sort_values('start')
    h=h1[['close_time','rv168_control_pct','atr_pct']].dropna().sort_values('close_time')
    x=pd.merge_asof(x,h,left_on='start',right_on='close_time',direction='backward')
    return x.drop(columns=['close_time'])


def mark_occurrence(eps):
    sh=pd.read_csv(SHADOW); sh['time']=pd.to_datetime(sh.time)
    sh=sh[(sh.action=='BUY')&(sh.pass_stateless==1)].sort_values('time').copy()
    st=sh.time.to_numpy('datetime64[ns]')
    rows=[]
    for e in eps.itertuples(index=False):
        a=np.searchsorted(st,np.datetime64(e.start),'left'); b=np.searchsorted(st,np.datetime64(e.end),'left')
        n=int(b-a)
        first=pd.Timestamp(sh.time.iloc[a]) if n>0 else pd.NaT
        rows.append({'episode_id':e.episode_id,'v283_occurs':int(n>0),'v283_count':n,'first_occurrence':first,
                     'occurrence_delay_h':((first-e.start).total_seconds()/3600.0 if n>0 else np.nan)})
    return eps.merge(pd.DataFrame(rows),on='episode_id',how='left')


def replay_one(sig,m1,h1):
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); L=m1.low.to_numpy(float)
    hct=h1.close_time.to_numpy('datetime64[ns]'); ha=h1.atr14.to_numpy(float)
    sig=pd.Timestamp(sig); et=sig+pd.Timedelta(minutes=1)
    j=int(np.searchsorted(mt,np.datetime64(et),'left')); q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1)
    if j>=len(O) or q<0 or not np.isfinite(ha[q]) or ha[q]<=0:return None
    entry=float(O[j]); sd=STOP_ATR*float(ha[q]); sl=entry-sd; tend=sig+pd.Timedelta(hours=EXIT_H)
    je=int(np.searchsorted(mt,np.datetime64(tend),'left'))
    if je<=j or je>=len(O):return None
    hit=np.flatnonzero(L[j:je]<=sl)
    if hit.size:
        rr=-1.0-COST/sd; pct=-(sd/entry*100)-COST/entry*100; ex='SL'
    else:
        end=float(O[je]); rr=(end-entry)/sd-COST/sd; pct=(end-entry)/entry*100-COST/entry*100; ex='TIME'
    return {'signal_time':sig,'entry_time':et,'entry':entry,'stop_dist':sd,'R':rr,'pct':pct,'exit_type':ex}


def next_h4_after(start,t):
    # episode starts on canonical H4 clock. Strictly after occurrence.
    dh=(pd.Timestamp(t)-pd.Timestamp(start)).total_seconds()/3600.0
    k=int(math.floor(dh/4.0))+1
    return pd.Timestamp(start)+pd.Timedelta(hours=4*k), k


def descriptive_first_only(eps,m1,h1):
    rows=[]
    for e in eps.itertuples(index=False):
        r=replay_one(e.start,m1,h1)
        if r:
            rows.append({**e._asdict(),**r})
    return pd.DataFrame(rows)


def build_causal_with(eps,m1,h1):
    rows=[]
    for e in eps[eps.v283_occurs==1].itertuples(index=False):
        t,k=next_h4_after(e.start,e.first_occurrence)
        if t>=e.end: continue
        r=replay_one(t,m1,h1)
        if r:
            rows.append({**e._asdict(),'selector_time':t,'selector_delay_h':(t-e.start).total_seconds()/3600.0,
                         'selector_clock_index':k,**r})
    return pd.DataFrame(rows)


def nearest_matches(withx,without):
    # Exact year + nearest neighbor on log RV168 and log ATR%, same relative clock must exist.
    allv=pd.concat([withx[['rv168_control_pct','atr_pct']],without[['rv168_control_pct','atr_pct']]],ignore_index=True)
    Z=np.log(allv.clip(lower=1e-12)); mu=Z.mean(); sd=Z.std(ddof=0).replace(0,1)
    def feat(df): return (np.log(df[['rv168_control_pct','atr_pct']].clip(lower=1e-12))-mu)/sd
    zw=feat(withx); zn=feat(without)
    rows=[]
    for ix,e in withx.iterrows():
        cand=without[(without.start.dt.year==e.start.year)&(without.duration_h>e.selector_delay_h)].copy()
        if cand.empty: continue
        fc=((np.log(cand[['rv168_control_pct','atr_pct']].clip(lower=1e-12))-mu)/sd)
        d=np.sqrt(((fc-zw.loc[ix])**2).sum(axis=1))
        j=d.idxmin(); c=cand.loc[j]
        rows.append({'with_episode_id':int(e.episode_id),'control_episode_id':int(c.episode_id),
                     'distance_z':float(d.loc[j]),'year':int(e.start.year),'delay_h':float(e.selector_delay_h),
                     'with_rv168':float(e.rv168_control_pct),'control_rv168':float(c.rv168_control_pct),
                     'with_atr_pct':float(e.atr_pct),'control_atr_pct':float(c.atr_pct),
                     'control_signal_time':pd.Timestamp(c.start)+pd.Timedelta(hours=float(e.selector_delay_h))})
    return pd.DataFrame(rows)


def bootstrap_delta(d,seed=SEED):
    a=np.asarray(pd.Series(d).dropna(),float); rng=np.random.default_rng(seed)
    if len(a)==0:return (np.nan,np.nan,np.nan,np.nan)
    idx=rng.integers(0,len(a),size=(BOOT,len(a))); means=a[idx].mean(axis=1)
    return float(a.mean()),float(np.quantile(means,.025)),float(np.quantile(means,.975)),float((means>0).mean())


def smd(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float);p=np.sqrt((np.var(a,ddof=1)+np.var(b,ddof=1))/2)
    return float((np.mean(a)-np.mean(b))/p) if p>0 else np.nan


def periodic_after_activation(causal, m1,h1, cad):
    maxslots=int(math.ceil(EXIT_H/cad)); risk=EP_BUDGET/maxslots; rows=[]
    for e in causal.itertuples(index=False):
        t=pd.Timestamp(e.selector_time); ord_=1
        while t<pd.Timestamp(e.end):
            r=replay_one(t,m1,h1)
            if r: rows.append({'episode_id':e.episode_id,'cadence_h':cad,'ordinal':ord_,'risk_pct':risk,
                               'prop_return_pct':r['R']*risk,**r})
            ord_+=1;t+=pd.Timedelta(hours=cad)
    return pd.DataFrame(rows)


def main():
    m1=base.load_zip(base.M1ZIP); m5=base.load_zip(base.M5ZIP); h1=h1_controls(m1)
    clock=u5.build_clock(m5); eps=u5.state_episodes(clock); eps=eps[eps.state=='B3_BUY'].copy()
    eps=attach_episode_controls(eps,h1); eps=mark_occurrence(eps)
    eps.to_csv(OUT/'b3_episodes_occurrence.csv',index=False)

    # A) descriptive whole-episode split. Not deployable from onset.
    first=descriptive_first_only(eps,m1,h1); first.to_csv(OUT/'descriptive_first_only.csv',index=False)
    desc=[]
    for occ,g in first.groupby('v283_occurs'):
        desc.append({'group':'WITH' if occ else 'WITHOUT','N':len(g),'EV_R':g.R.mean(),'PF_R':pf(g.R),'WR':(g.R>0).mean(),
                     'EV_pct':g.pct.mean(),'median_duration_h':g.duration_h.median(),
                     'median_RV168_pct':g.rv168_control_pct.median(),'median_ATR_pct':g.atr_pct.median(),
                     'mean_RV168_pct':g.rv168_control_pct.mean(),'mean_ATR_pct':g.atr_pct.mean()})
    desc=pd.DataFrame(desc); desc.to_csv(OUT/'descriptive_group_metrics.csv',index=False)

    # B) causal selector entry after first occurrence.
    causal=build_causal_with(eps,m1,h1); causal.to_csv(OUT/'causal_with_entries.csv',index=False)
    without=eps[eps.v283_occurs==0].copy()
    pairs=nearest_matches(causal,without)
    ctrl=[]
    for p in pairs.itertuples(index=False):
        r=replay_one(p.control_signal_time,m1,h1)
        if r: ctrl.append({**p._asdict(),**r})
    ctrl=pd.DataFrame(ctrl); ctrl.to_csv(OUT/'matched_without_entries.csv',index=False)
    pair=causal.merge(ctrl[['with_episode_id','control_episode_id','distance_z','R','pct','control_signal_time']],left_on='episode_id',right_on='with_episode_id',suffixes=('_with','_control'))
    pair['delta_R']=pair.R_with-pair.R_control; pair['delta_pct']=pair.pct_with-pair.pct_control
    pair.to_csv(OUT/'paired_causal_selector.csv',index=False)

    dR=bootstrap_delta(pair.delta_R); dP=bootstrap_delta(pair.delta_pct,SEED+1)
    # Feature balance before and after matching.
    with_all=eps[eps.v283_occurs==1]; no_all=eps[eps.v283_occurs==0]
    bal=[{'stage':'UNMATCHED','N_with':len(with_all),'N_without':len(no_all),
          'SMD_log_RV168':smd(np.log(with_all.rv168_control_pct),np.log(no_all.rv168_control_pct)),
          'SMD_log_ATR_pct':smd(np.log(with_all.atr_pct),np.log(no_all.atr_pct))}]
    if len(pairs):
        bal.append({'stage':'MATCHED','N_with':len(pairs),'N_without':len(pairs),
                    'SMD_log_RV168':smd(np.log(pairs.with_rv168),np.log(pairs.control_rv168)),
                    'SMD_log_ATR_pct':smd(np.log(pairs.with_atr_pct),np.log(pairs.control_atr_pct))})
    bal=pd.DataFrame(bal);bal.to_csv(OUT/'volatility_balance.csv',index=False)

    primary=pd.DataFrame([{'N_with_causal':len(causal),'N_pairs':len(pair),
                           'WITH_EV_R':causal.R.mean() if len(causal) else np.nan,'WITH_PF_R':pf(causal.R) if len(causal) else np.nan,
                           'CONTROL_EV_R':ctrl.R.mean() if len(ctrl) else np.nan,'CONTROL_PF_R':pf(ctrl.R) if len(ctrl) else np.nan,
                           'DELTA_R':dR[0],'DELTA_R_CI_lo':dR[1],'DELTA_R_CI_hi':dR[2],'P_DELTA_R_gt0':dR[3],
                           'WITH_EV_pct':causal.pct.mean() if len(causal) else np.nan,'CONTROL_EV_pct':ctrl.pct.mean() if len(ctrl) else np.nan,
                           'DELTA_pct':dP[0],'DELTA_pct_CI_lo':dP[1],'DELTA_pct_CI_hi':dP[2],'P_DELTA_pct_gt0':dP[3],
                           'median_selector_delay_h':causal.selector_delay_h.median() if len(causal) else np.nan,
                           'median_match_distance_z':pairs.distance_z.median() if len(pairs) else np.nan}])
    primary.to_csv(OUT/'primary_causal_result.csv',index=False)

    # Year split of paired deltas.
    yrs=[]
    for y,g in pair.groupby(pair.start.dt.year):
        z=bootstrap_delta(g.delta_R,SEED+int(y)); yrs.append({'year':int(y),'N':len(g),'WITH_EV_R':g.R_with.mean(),'CONTROL_EV_R':g.R_control.mean(),
                                                             'DELTA_R':z[0],'P_DELTA_R_gt0':z[3]})
    yrs=pd.DataFrame(yrs);yrs.to_csv(OUT/'yearly_paired.csv',index=False)

    # Secondary exploratory periodic post-activation.
    per=[]; per_rows=[]
    for cad in [4,8,12]:
        q=periodic_after_activation(causal,m1,h1,cad); q.to_csv(OUT/f'periodic_after_{cad}h.csv',index=False)
        if len(q):
            ep=q.groupby('episode_id').prop_return_pct.sum()
            per.append({'cadence_h':cad,'N_trades':len(q),'N_episodes':q.episode_id.nunique(),'EV_R_trade':q.R.mean(),'PF_R':pf(q.R),
                        'EV_prop_pct_episode':ep.mean(),'PF_episode':pf(ep),'episode_win_rate':(ep>0).mean()})
    per=pd.DataFrame(per);per.to_csv(OUT/'periodic_post_activation_summary.csv',index=False)

    # occurrence-volatility associations
    assoc=pd.DataFrame([{'N_with':len(with_all),'N_without':len(no_all),
                         'WITH_mean_RV168':with_all.rv168_control_pct.mean(),'WITHOUT_mean_RV168':no_all.rv168_control_pct.mean(),
                         'WITH_mean_ATR_pct':with_all.atr_pct.mean(),'WITHOUT_mean_ATR_pct':no_all.atr_pct.mean(),
                         'SMD_log_RV168':bal.iloc[0].SMD_log_RV168,'SMD_log_ATR_pct':bal.iloc[0].SMD_log_ATR_pct}])
    assoc.to_csv(OUT/'occurrence_volatility_association.csv',index=False)

    rep=['# U02C6 — B3 V283 OCCURRENCE SELECTION ABLATION','',
         '**Primary question:** does at least one v283 BUY occurrence select a better B3 BUY episode after controlling for volatility, without using the v283 timestamp as the entry?','',
         '**Causal entry:** first fixed H4 clock boundary strictly after first occurrence. Comparator: same-year B3 episode with no v283 occurrence, nearest matched on causal onset log(RV168_control) and log(ATR%), evaluated at the same relative delay.','',
         '**RV168_control definition:** sqrt(sum of squared H1 log returns) over previous 168 completed H1 bars, in %. This is a control defined for this LAB, not asserted byte-identical to prior RV168 research.','',
         '## Episode census / descriptive split (NOT deployable from onset)','',desc.to_markdown(index=False),'',
         '## Volatility balance','',bal.to_markdown(index=False),'',
         '## Primary causal matched result','',primary.to_markdown(index=False),'',
         '## Yearly paired deltas','',yrs.to_markdown(index=False),'',
         '## Secondary periodic entries after activation','',per.to_markdown(index=False),'',
         '## Interpretation guardrail','',
         'A descriptive WITH/WITHOUT difference at episode onset is not a deployable selector because occurrence may happen later. Only the post-occurrence fixed-clock matched result is causal enough to inform the core. If the advantage disappears after RV168/ATR% matching, occurrence is treated as a volatility/activity proxy rather than an independent selector.']
    (OUT/'REPORT.md').write_text('\n'.join(rep))
    meta={'seed':SEED,'bootstrap':BOOT,'state':'B3_BUY age28..58','occurrence':'default-v283 BUY stateless pass >=1 inside episode',
          'primary_entry':'next fixed H4 clock strictly after first occurrence','matching':'same year + nearest z distance in log RV168_control, log ATR%',
          'rv168_control':'sqrt(sum(H1 logret^2,168))*100','atr_pct':'H1 ATR14/H1 close*100 at episode onset','stop_atr':STOP_ATR,'time_exit_h':EXIT_H,'cost_usd':COST}
    (OUT/'summary.json').write_text(json.dumps(meta,indent=2))
    print('DESC\n',desc.to_string(index=False));print('\nBALANCE\n',bal.to_string(index=False));print('\nPRIMARY\n',primary.to_string(index=False));print('\nYEARLY\n',yrs.to_string(index=False));print('\nPERIODIC\n',per.to_string(index=False))

if __name__=='__main__': main()
