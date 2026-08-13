#!/usr/bin/env python3
"""SELL_CORE_007 — FAILED_ATTACK_OCCURRENCE_AND_TIMING_NULL.

Frozen from SELL_CORE_006B, with no new market filters.

Primary treated population:
- ALL first causal FAILED_ATTACK occurrences from lifecycle-safe 006B correction episodes.
- No future STRUCTURE_BREAK requirement.
- One first failed attack per correction episode.

Execution/outcome:
- SELL next M1 open after failed-attack M15 close.
- SL=1.5 x completed H1 ATR14; no TP.
- 48h primary / 72h sensitivity; $27.5/BTC cost proxy inherited from 006.

Null A — exact timing, conditional on occurrence:
- for each treated correction episode, eligible controls are earlier M15 decisions in the SAME correction episode,
  same exact H4 ST age as the failure, while lifecycle state is genuinely READY with a live attack level;
- failure bar itself excluded;
- compare treated outcome with mean eligible same-episode control outcome.
This tests timestamp alpha only; it deliberately holds occurrence/episode selection fixed.

Null B — causal occurrence risk set:
- for each treated failure at delay d from correction onset, compare other correction episodes at their own onset+d;
- same calendar year, same exact H4 ST age, H4 still bearish, different H4 ST episode;
- control correction must be causally alive and READY with a live attack level at comparison time;
- no failed attack may have occurred in that control correction by comparison time; it MAY fail later;
- nearest H1 ATR% = primary nearest-1 matched control; nearest 5 = frozen sensitivity.
This tests whether failure occurrence selects better SELL episodes beyond being in the correction state.

Structure-break outcome is diagnostic only and never used to define treated/control eligibility.
Frozen unified Binance window: 2024-01-01 through available 2026-08-10 data.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import sell_core_004_htf_bear_local_correction_failed_breakout as p4
import sell_core_006_correction_episode_failed_attack_structure_break as a
import sell_core_006b_correction_episode_state_machine_safe as b

OUT=Path('sell_core_007_out'); OUT.mkdir(exist_ok=True)
START=a.START; HOLDS=a.HOLDS; BOOT=a.BOOT; SEED=407007
READY_EVENTS={'CORRECTION_READY','READY_REFRESH'}
TERMINAL_EVENTS={'CORRECTION_LOST_BEFORE_ATTACK','SUPPORT_BREAK_NO_FAILED_ATTACK','AMBIGUOUS_ATTACK_AND_BREAK_SAME_BAR','STRUCTURE_BREAK_SELL'}


def latest_event(log_by_cid,cid,t):
    g=log_by_cid.get(int(cid))
    if g is None or len(g)==0:return None
    q=g[g.time<=t]
    if len(q)==0:return None
    return q.iloc[-1]


def ready_at(log_by_cid,cid,t):
    e=latest_event(log_by_cid,cid,t)
    if e is None:return False
    return str(e.event) in READY_EVENTS and pd.notna(e.level) and pd.notna(e.support)


def first_terminal_map(log):
    z=log[log.event.isin(TERMINAL_EVENTS)].sort_values('time')
    return z.groupby('correction_id').time.first().to_dict() if len(z) else {}


def first_failure_map(failed):
    if len(failed)==0:return {}
    z=failed.sort_values('failed_attack_time').drop_duplicates('correction_id',keep='first')
    return z.set_index('correction_id').failed_attack_time.to_dict()


def cluster_boot_delta(pair,col,seed):
    z=pair[['st_episode_id',col]].dropna()
    if len(z)==0:return {'mean':np.nan,'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    ids=z.st_episode_id.unique()
    if len(ids)<5:return {'mean':float(z[col].mean()),'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    ag=z.groupby('st_episode_id')[col].agg(['sum','count']).to_numpy(float)
    rng=np.random.default_rng(seed); vals=np.empty(BOOT,float)
    for i in range(BOOT):
        s=ag[rng.integers(0,len(ag),len(ag))].sum(axis=0); vals[i]=s[0]/s[1]
    return {'mean':float(z[col].mean()),'lo':float(np.quantile(vals,.025)),'hi':float(np.quantile(vals,.975)),'P_gt0':float((vals>0).mean())}


def metric(g,name):return a.metric(g,name)


def build_timing_controls(treated,cand,log_by_cid):
    rows=[]; audit=[]
    for _,r in treated.iterrows():
        cid=int(r.correction_id); fail=pd.Timestamp(r.failed_attack_time); onset=pd.Timestamp(r.onset_time)
        q=cand[(cand.decision_time>=onset)&(cand.decision_time<fail)&(cand.st_episode_id==r.st_episode_id)&(cand.st_age==r.st_age)].copy()
        if len(q):
            q=q[q.decision_time.map(lambda t:ready_at(log_by_cid,cid,pd.Timestamp(t)))]
        audit.append({'event_key':cid,'eligible_controls':len(q),'onset_time':onset,'failed_attack_time':fail,'st_age':int(r.st_age)})
        for _,c in q.iterrows():
            d=c.to_dict(); d['event_key']=cid; d['control_time']=pd.Timestamp(c.decision_time); d['treated_fail_time']=fail
            rows.append(d)
    return pd.DataFrame(rows),pd.DataFrame(audit)


def make_pair_from_controls(trep,crep,key='event_key'):
    if len(trep)==0 or len(crep)==0:return pd.DataFrame()
    agg={}
    for hh in HOLDS:
        agg[f'control_R{hh}']=(f'R{hh}','mean'); agg[f'control_pct{hh}']=(f'pct{hh}','mean')
    cm=crep.groupby(key).agg(**agg).reset_index()
    keep=[key,'st_episode_id']
    for hh in HOLDS:keep += [f'R{hh}',f'pct{hh}']
    p=trep[keep].merge(cm,on=key,how='inner')
    for hh in HOLDS:
        p[f'delta_R{hh}']=p[f'R{hh}']-p[f'control_R{hh}']; p[f'delta_pct{hh}']=p[f'pct{hh}']-p[f'control_pct{hh}']
    return p


def build_occurrence_controls(treated,onsets,failed,log,cand):
    # Fast exact-time lookup.
    cidx=cand.set_index('decision_time',drop=False)
    log2=log.copy(); log2['time']=pd.to_datetime(log2.time)
    log_by={int(k):g.sort_values('time') for k,g in log2.groupby('correction_id')}
    terminals=first_terminal_map(log2); firstfails=first_failure_map(failed)
    onset_meta=onsets.sort_values('onset_time').drop_duplicates('correction_id').copy()
    onset_meta['onset_time']=pd.to_datetime(onset_meta.onset_time)
    rows=[]; audit=[]
    for _,tr in treated.iterrows():
        tid=int(tr.correction_id); tf=pd.Timestamp(tr.failed_attack_time); ton=pd.Timestamp(tr.onset_time)
        delay=tf-ton; y=tf.year; target_age=int(tr.st_age); target_atr=float(tr.atr_pct)
        risk=[]
        for _,o in onset_meta.iterrows():
            cid=int(o.correction_id)
            if cid==tid or int(o.st_episode_id)==int(tr.st_episode_id):continue
            cmp=pd.Timestamp(o.onset_time)+delay
            if cmp.year!=y or cmp not in cidx.index:continue
            cr=cidx.loc[cmp]
            if isinstance(cr,pd.DataFrame):cr=cr.iloc[-1]
            if int(cr.st_dir)!=-1 or int(cr.st_episode_id)!=int(o.st_episode_id):continue
            if int(cr.st_age)!=target_age:continue
            term=terminals.get(cid)
            if term is not None and cmp>=pd.Timestamp(term):continue
            ff=firstfails.get(cid)
            if ff is not None and pd.Timestamp(ff)<=cmp:continue
            if not ready_at(log_by,cid,cmp):continue
            d=cr.to_dict(); d['control_correction_id']=cid; d['event_key']=tid; d['control_time']=cmp
            d['corr_delay_h']=delay.total_seconds()/3600.0; d['atr_distance']=abs(float(cr.atr_pct)-target_atr)
            risk.append(d)
        risk=sorted(risk,key=lambda x:(x['atr_distance'],x['control_time'],x['control_correction_id']))
        audit.append({'event_key':tid,'failed_attack_time':tf,'corr_delay_h':delay.total_seconds()/3600.0,'target_st_age':target_age,
                      'riskset_N':len(risk),'nearest_atr_distance':risk[0]['atr_distance'] if risk else np.nan})
        for rank,d in enumerate(risk[:5],1):
            d['match_rank']=rank; rows.append(d)
    return pd.DataFrame(rows),pd.DataFrame(audit)


def occurrence_pairs(trep,crep,k):
    if len(trep)==0 or len(crep)==0:return pd.DataFrame()
    c=crep[crep.match_rank<=k].copy()
    agg={}
    for hh in HOLDS:
        agg[f'control_R{hh}']=(f'R{hh}','mean'); agg[f'control_pct{hh}']=(f'pct{hh}','mean')
    cm=c.groupby('event_key').agg(**agg).reset_index()
    keep=['event_key','st_episode_id']
    for hh in HOLDS:keep += [f'R{hh}',f'pct{hh}']
    p=trep[keep].merge(cm,on='event_key',how='inner')
    for hh in HOLDS:
        p[f'delta_R{hh}']=p[f'R{hh}']-p[f'control_R{hh}']; p[f'delta_pct{hh}']=p[f'pct{hh}']-p[f'control_pct{hh}']
    return p


def delta_table(pair,label,seedbase):
    rows=[]
    for hh in HOLDS:
        qr=cluster_boot_delta(pair,f'delta_R{hh}',seedbase+hh); qp=cluster_boot_delta(pair,f'delta_pct{hh}',seedbase+100+hh)
        rows.append({'test':label,'hold_h':hh,'N_pairs':len(pair),
                     'treated_EV_R':float(pair[f'R{hh}'].mean()) if len(pair) else np.nan,
                     'control_EV_R':float(pair[f'control_R{hh}'].mean()) if len(pair) else np.nan,
                     'delta_R':qr['mean'],'CI_R_lo':qr['lo'],'CI_R_hi':qr['hi'],'P_delta_R_gt0':qr['P_gt0'],
                     'treated_EV_pct':float(pair[f'pct{hh}'].mean()) if len(pair) else np.nan,
                     'control_EV_pct':float(pair[f'control_pct{hh}'].mean()) if len(pair) else np.nan,
                     'delta_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_delta_pct_gt0':qp['P_gt0']})
    return rows


def main():
    m1=base.load_zip(a.M1ZIP); m5=base.load_zip(a.M5ZIP)
    m1=m1[m1.time>=START].copy(); m5=m5[m5.time>=START-pd.Timedelta(days=90)].copy()
    h1=p4.make_h1(m1); clock=p4.make_clock(m5); m15=p4.make_m15(m5)
    cand=p4.attach_states(m15,h1,clock); cand=cand[(cand.decision_time>=START)&cand.st_dir.notna()&cand.st_age.notna()&cand.atr14.notna()].copy()
    piv=a.h1_pivot_events(h1,2)
    completed,onsets,failed,log,census=b.safe_state_machine(cand,piv)
    for x,c in [(onsets,'onset_time'),(failed,'failed_attack_time'),(log,'time'),(completed,'structure_break_time')]:
        if len(x) and c in x:x[c]=pd.to_datetime(x[c])

    # First failed attack per correction episode; 006B currently emits one per correction, but freeze explicitly.
    treated=failed.sort_values('failed_attack_time').drop_duplicates('correction_id',keep='first').copy()
    treated['event_key']=treated.correction_id.astype(int)
    trep=a.replay_at(treated,m1,h1,'failed_attack_time','FIRST_FAILED_ATTACK_ALL_CAUSAL')
    trep['event_key']=trep.correction_id.astype(int)
    treated.to_csv(OUT/'treated_first_failed_attacks.csv',index=False); trep.to_csv(OUT/'replay_treated_first_failed_attacks.csv',index=False)

    # Unconditional treated metrics + bootstrap.
    primary=pd.DataFrame([metric(trep,'FIRST_FAILED_ATTACK_ALL_CAUSAL')])
    primary.to_csv(OUT/'primary_metrics.csv',index=False)
    boots=[]
    for hh in HOLDS:
        q=a.cluster_boot_mean(trep,f'R{hh}',SEED+hh); qp=a.cluster_boot_mean(trep,f'pct{hh}',SEED+100+hh)
        boots.append({'hold_h':hh,'EV_R':q['mean'],'CI_R_lo':q['lo'],'CI_R_hi':q['hi'],'P_R_gt0':q['P_gt0'],
                      'EV_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_pct_gt0':qp['P_gt0']})
    pd.DataFrame(boots).to_csv(OUT/'primary_cluster_bootstrap.csv',index=False)

    # Timing null conditional on same failure-containing correction episode.
    log2=log.copy(); log2['time']=pd.to_datetime(log2.time); log_by={int(k):g.sort_values('time') for k,g in log2.groupby('correction_id')}
    tc,taudit=build_timing_controls(treated,cand,log_by)
    tcrep=a.replay_at(tc,m1,h1,'control_time','TIMING_SAME_CORRECTION_EXACT_H4_AGE') if len(tc) else pd.DataFrame()
    tpair=make_pair_from_controls(trep,tcrep)
    tc.to_csv(OUT/'timing_controls.csv',index=False); taudit.to_csv(OUT/'timing_control_audit.csv',index=False); tcrep.to_csv(OUT/'replay_timing_controls.csv',index=False); tpair.to_csv(OUT/'timing_pairs.csv',index=False)
    timing_stats=delta_table(tpair,'TIMING_SAME_CORRECTION_EXACT_H4_AGE',SEED+1000) if len(tpair) else []
    pd.DataFrame(timing_stats).to_csv(OUT/'timing_null_results.csv',index=False)

    # Causal occurrence risk set.
    oc,oaudit=build_occurrence_controls(treated,onsets,failed,log,cand)
    ocrep=a.replay_at(oc,m1,h1,'control_time','OCCURRENCE_RISKSET_CONTROL') if len(oc) else pd.DataFrame()
    oc.to_csv(OUT/'occurrence_riskset_controls.csv',index=False); oaudit.to_csv(OUT/'occurrence_riskset_audit.csv',index=False); ocrep.to_csv(OUT/'replay_occurrence_controls.csv',index=False)
    occ_rows=[]; opairs={}
    for k in (1,5):
        p=occurrence_pairs(trep,ocrep,k); opairs[k]=p; p.to_csv(OUT/f'occurrence_pairs_k{k}.csv',index=False)
        if len(p):occ_rows += delta_table(p,f'OCCURRENCE_RISKSET_K{k}',SEED+2000+k*100)
    pd.DataFrame(occ_rows).to_csv(OUT/'occurrence_riskset_results.csv',index=False)

    # Year and market-clock diagnostics for all causal failures.
    yearly=[]; buckets=[]
    if len(trep):
        trep['year']=pd.to_datetime(trep.failed_attack_time).dt.year
        trep['bucket']=np.select([trep.st_age<=11,trep.st_age<=27,trep.st_age<=58],['B1','B2','B3'],default='B4')
        for y,g in trep.groupby('year'):yearly.append({'year':int(y),**metric(g,'FIRST_FAILED_ATTACK')})
        for bk,g in trep.groupby('bucket'):buckets.append({'bucket':bk,**metric(g,'FIRST_FAILED_ATTACK')})
    pd.DataFrame(yearly).to_csv(OUT/'yearly_treated.csv',index=False); pd.DataFrame(buckets).to_csv(OUT/'market_clock_treated.csv',index=False)

    # Future structure break diagnostic ONLY, never eligibility.
    broke=set(completed.correction_id.astype(int)) if len(completed) else set()
    diag=treated[['correction_id','failed_attack_time','onset_time','st_episode_id','st_age','atr_pct']].copy()
    diag['later_structure_break']=diag.correction_id.astype(int).isin(broke)
    diag.to_csv(OUT/'future_structure_break_diagnostic.csv',index=False)

    weeks=max((pd.Timestamp(cand.decision_time.max())-START).days/7.0,1)
    freq=pd.DataFrame([{'first_failed_attacks':len(trep),'weeks':weeks,'trades_per_week':len(trep)/weeks,
                        'correction_episodes_started':census['correction_episodes_started'],'failure_occurrence_rate':len(trep)/census['correction_episodes_started'] if census['correction_episodes_started'] else np.nan,
                        'later_structure_break_N':int(diag.later_structure_break.sum()) if len(diag) else 0}])
    freq.to_csv(OUT/'frequency.csv',index=False)

    timing_cov={'treated_N':len(trep),'matched_N':len(tpair),'coverage':len(tpair)/len(trep) if len(trep) else np.nan,
                'mean_controls_per_matched':float(taudit.loc[taudit.eligible_controls>0,'eligible_controls'].mean()) if len(taudit) and (taudit.eligible_controls>0).any() else np.nan}
    occ_cov=[]
    for k in (1,5):
        p=opairs.get(k,pd.DataFrame()); occ_cov.append({'K':k,'treated_N':len(trep),'matched_N':len(p),'coverage':len(p)/len(trep) if len(trep) else np.nan})
    pd.DataFrame([timing_cov]).to_csv(OUT/'timing_coverage.csv',index=False); pd.DataFrame(occ_cov).to_csv(OUT/'occurrence_coverage.csv',index=False)

    report=['# SELL_CORE_007 — FAILED_ATTACK_OCCURRENCE_AND_TIMING_NULL','',
            '**Primary population:** every first causal FAILED_ATTACK from lifecycle-safe SELL_CORE_006B. Future structure break is diagnostic only.','',
            '## Census / frequency','',freq.to_markdown(index=False),'',
            '## Unconditional causal failed-attack SELL','',primary.to_markdown(index=False),'',
            '## Primary cluster bootstrap','',pd.DataFrame(boots).to_markdown(index=False),'',
            '## Timing null — same correction episode, exact H4 age, READY state','',pd.DataFrame(timing_stats).to_markdown(index=False) if timing_stats else 'No matched timing pairs.','',
            'Timing coverage:','',pd.DataFrame([timing_cov]).to_markdown(index=False),'',
            '## Occurrence risk-set — same correction delay/year/exact H4 age, READY, no failure known yet','',pd.DataFrame(occ_rows).to_markdown(index=False) if occ_rows else 'No matched occurrence pairs.','',
            'Occurrence coverage:','',pd.DataFrame(occ_cov).to_markdown(index=False),'',
            '## Yearly treated','',pd.DataFrame(yearly).to_markdown(index=False) if yearly else 'No treated events.','',
            '## Market-clock diagnostic','',pd.DataFrame(buckets).to_markdown(index=False) if buckets else 'No treated events.','',
            '## Future structure-break diagnostic only','',f"Later structure break after first failed attack: {int(diag.later_structure_break.sum()) if len(diag) else 0}/{len(diag)}.",'',
            '## Frozen interpretation','',
            '- Timing alpha requires failed-attack timestamp to beat same-correction READY-state controls.','- Occurrence alpha requires failed-attack episodes to beat causal risk-set controls at the same correction delay and H4 age.','- Do not promote from the 006 completed-sequence subset; all 007 conclusions use the unconditional causal failure population.']
    (OUT/'REPORT.md').write_text('\n'.join(report)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
