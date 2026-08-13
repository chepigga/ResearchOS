#!/usr/bin/env python3
"""SELL_CORE_006B — technical correction of SELL_CORE_006 state-machine lifecycle.

NO hypothesis/threshold changes vs preregistered 006A.
Corrections only:
A) Once an H1 attack-high has been accepted by an M15 close above it, that exact pivot is retired and cannot
   be immediately reused. A new causally confirmed H1 swing high + later HL is required.
B) H1 pivots whose pivot_time predates the current H4-bear episode start are not allowed to seed that episode,
   even if their confirmation/effective_time occurs after the H4 episode begins.
C) A failed attack invalidated by later acceptance retires that attacked high as well.

All sequence, execution, exit and verdict rules are unchanged from SELL_CORE_006A.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import sell_core_006_correction_episode_failed_attack_structure_break as a
import u02c2_v283_market_clock_conditional as base
import sell_core_004_htf_bear_local_correction_failed_breakout as p4

OUT=Path('sell_core_006b_out'); OUT.mkdir(exist_ok=True)
START=a.START; HOLDS=a.HOLDS; BOOT=a.BOOT; SEED=a.SEED


def safe_state_machine(cand,piv):
    z=cand.sort_values('decision_time').reset_index(drop=True).copy()
    pe=piv.to_dict('records'); pi=0
    current_st_ep=None; episode_start=None; highs=[]; lows=[]; retired_highs=set()
    mode='IDLE'; correction_id=0; active_id=None
    onset_time=None; attack_level=np.nan; support=np.nan; attack_pivot_idx=None; support_pivot_idx=None
    failed_time=None; failed_row=None; frozen_attack=np.nan; frozen_support=np.nan; frozen_attack_pivot_idx=None
    attack_attempts=0; acceptances=0; ambiguous=0; unarmed_breaks=0; invalidated_failures=0
    completed=[]; onset_rows=[]; failed_rows=[]; transition_log=[]; last_ready=False
    ignored_pre_episode_pivots=0

    for _,r in z.iterrows():
        t=pd.Timestamp(r.decision_time); st_ep=int(r.st_episode_id); bear=(int(r.st_dir)==-1)

        # Reset FIRST, before ingesting pivots whose effective time is this decision.
        if current_st_ep!=st_ep:
            current_st_ep=st_ep; episode_start=t; highs=[]; lows=[]; retired_highs=set(); mode='IDLE'; active_id=None
            onset_time=None; failed_time=None; failed_row=None; attack_level=np.nan; support=np.nan
            frozen_attack=np.nan; frozen_support=np.nan; frozen_attack_pivot_idx=None; last_ready=False

        # Feed newly known pivots, but only if the pivot itself formed inside this H4 episode.
        while pi<len(pe) and pd.Timestamp(pe[pi]['effective_time'])<=t:
            e=pe[pi]; pi+=1
            if bear and pd.Timestamp(e['pivot_time'])>=episode_start:
                if e['kind']=='H': highs.append(e)
                else: lows.append(e)
            else:
                ignored_pre_episode_pivots+=1

        if not bear:
            mode='IDLE'; active_id=None; last_ready=False
            continue

        rs=a.ready_structure(highs,lows); is_ready=rs is not None

        if mode=='WAIT_RESET':
            if not is_ready:
                mode='IDLE'; last_ready=False
            else:last_ready=True
            continue

        if mode=='IDLE':
            if is_ready and not last_ready:
                hi_idx=int(rs['attack_high']['pivot_idx'])
                # A retired high cannot seed a new correction attack level.
                if hi_idx not in retired_highs:
                    correction_id+=1; active_id=correction_id; mode='READY'; onset_time=t
                    attack_level=float(rs['attack_high']['price']); support=float(rs['support_low']['price'])
                    attack_pivot_idx=hi_idx; support_pivot_idx=int(rs['support_low']['pivot_idx'])
                    d=r.to_dict(); d.update(correction_id=active_id,onset_time=t,attack_level=attack_level,support=support,
                                          attack_pivot_idx=attack_pivot_idx,support_pivot_idx=support_pivot_idx)
                    onset_rows.append(d); transition_log.append({'time':t,'correction_id':active_id,'event':'CORRECTION_READY','level':attack_level,'support':support})
            last_ready=is_ready
            if mode=='IDLE':continue

        if mode=='READY':
            # Refresh only to a non-retired attack high.
            if is_ready:
                new_hi=int(rs['attack_high']['pivot_idx']); new_lo=int(rs['support_low']['pivot_idx'])
                if new_hi!=attack_pivot_idx or new_lo!=support_pivot_idx:
                    if new_hi not in retired_highs:
                        attack_level=float(rs['attack_high']['price']); support=float(rs['support_low']['price'])
                        attack_pivot_idx=new_hi; support_pivot_idx=new_lo
                        transition_log.append({'time':t,'correction_id':active_id,'event':'READY_REFRESH','level':attack_level,'support':support})
                    else:
                        attack_level=np.nan; support=np.nan; attack_pivot_idx=None; support_pivot_idx=None
            else:
                mode='WAIT_RESET'; transition_log.append({'time':t,'correction_id':active_id,'event':'CORRECTION_LOST_BEFORE_ATTACK','level':np.nan,'support':np.nan}); last_ready=False; continue

            if np.isfinite(support) and float(r.close)<support:
                unarmed_breaks+=1; mode='WAIT_RESET'; transition_log.append({'time':t,'correction_id':active_id,'event':'SUPPORT_BREAK_NO_FAILED_ATTACK','level':attack_level,'support':support}); last_ready=is_ready; continue

            if np.isfinite(attack_level) and float(r.high)>attack_level:
                attack_attempts+=1
                if float(r.close)>attack_level:
                    acceptances+=1; retired_highs.add(int(attack_pivot_idx))
                    transition_log.append({'time':t,'correction_id':active_id,'event':'ATTACK_ACCEPTED_RETIRED','level':attack_level,'support':support})
                    attack_level=np.nan; support=np.nan; attack_pivot_idx=None; support_pivot_idx=None
                    continue
                if float(r.close)<attack_level:
                    if np.isfinite(support) and float(r.close)<support:
                        ambiguous+=1; mode='WAIT_RESET'; transition_log.append({'time':t,'correction_id':active_id,'event':'AMBIGUOUS_ATTACK_AND_BREAK_SAME_BAR','level':attack_level,'support':support}); last_ready=is_ready; continue
                    failed_time=t; failed_row=r.copy(); frozen_attack=float(attack_level); frozen_support=float(support); frozen_attack_pivot_idx=int(attack_pivot_idx); mode='ARMED'
                    d=r.to_dict(); d.update(correction_id=active_id,onset_time=onset_time,failed_attack_time=t,attack_level=frozen_attack,support=frozen_support,attack_pivot_idx=frozen_attack_pivot_idx)
                    failed_rows.append(d); transition_log.append({'time':t,'correction_id':active_id,'event':'FAILED_ATTACK','level':frozen_attack,'support':frozen_support})
                    continue

        elif mode=='ARMED':
            if float(r.close)>frozen_attack:
                invalidated_failures+=1; retired_highs.add(int(frozen_attack_pivot_idx)); mode='READY'; failed_time=None; failed_row=None
                transition_log.append({'time':t,'correction_id':active_id,'event':'FAILED_ATTACK_INVALIDATED_HIGH_RETIRED','level':frozen_attack,'support':frozen_support})
                attack_level=np.nan; support=np.nan; attack_pivot_idx=None; support_pivot_idx=None
                continue
            if t>failed_time and float(r.close)<frozen_support:
                d=r.to_dict(); d.update(correction_id=active_id,onset_time=onset_time,failed_attack_time=failed_time,structure_break_time=t,
                                      attack_level=frozen_attack,support=frozen_support,attack_pivot_idx=frozen_attack_pivot_idx,
                                      onset_to_fail_h=(failed_time-onset_time).total_seconds()/3600.0,
                                      fail_to_break_h=(t-failed_time).total_seconds()/3600.0,
                                      onset_to_break_h=(t-onset_time).total_seconds()/3600.0)
                if failed_row is not None:
                    d['failed_st_age']=int(failed_row.st_age); d['failed_atr_pct']=float(failed_row.atr_pct)
                completed.append(d); transition_log.append({'time':t,'correction_id':active_id,'event':'STRUCTURE_BREAK_SELL','level':frozen_attack,'support':frozen_support})
                mode='WAIT_RESET'; last_ready=is_ready; failed_time=None; failed_row=None
                continue
        last_ready=is_ready

    census={'correction_episodes_started':correction_id,'completed_sequences':len(completed),'failed_attack_events':len(failed_rows),
            'attack_attempts':attack_attempts,'accepted_attacks':acceptances,'ambiguous_same_bar_discarded':ambiguous,
            'unarmed_support_breaks':unarmed_breaks,'invalidated_failures':invalidated_failures,'ignored_pre_episode_pivots':ignored_pre_episode_pivots}
    return pd.DataFrame(completed),pd.DataFrame(onset_rows),pd.DataFrame(failed_rows),pd.DataFrame(transition_log),census


def main():
    m1=base.load_zip(a.M1ZIP); m5=base.load_zip(a.M5ZIP)
    m1=m1[m1.time>=START].copy(); m5=m5[m5.time>=START-pd.Timedelta(days=90)].copy()
    h1=p4.make_h1(m1); clock=p4.make_clock(m5); m15=p4.make_m15(m5)
    cand=p4.attach_states(m15,h1,clock); cand=cand[(cand.decision_time>=START)&cand.st_dir.notna()&cand.st_age.notna()&cand.atr14.notna()].copy()
    piv=a.h1_pivot_events(h1,2); piv.to_csv(OUT/'h1_causal_pivots.csv',index=False)
    completed,onsets,failed,log,census=safe_state_machine(cand,piv)
    completed.to_csv(OUT/'completed_sequences.csv',index=False); onsets.to_csv(OUT/'correction_onsets.csv',index=False); failed.to_csv(OUT/'failed_attack_events.csv',index=False); log.to_csv(OUT/'state_transitions.csv',index=False); pd.DataFrame([census]).to_csv(OUT/'census.csv',index=False)

    primary=a.replay_at(completed,m1,h1,'structure_break_time','STRUCTURE_BREAK')
    onset_rep=a.replay_at(completed,m1,h1,'onset_time','CORRECTION_ONSET_DIAGNOSTIC')
    fail_rep=a.replay_at(completed,m1,h1,'failed_attack_time','FAILED_ATTACK_DIAGNOSTIC')
    primary.to_csv(OUT/'replay_structure_break.csv',index=False); onset_rep.to_csv(OUT/'replay_onset_completed_sequences.csv',index=False); fail_rep.to_csv(OUT/'replay_failed_attack_completed_sequences.csv',index=False)
    stages=pd.DataFrame([a.metric(onset_rep,'CORRECTION_ONSET_completed_only'),a.metric(fail_rep,'FAILED_ATTACK_completed_only'),a.metric(primary,'STRUCTURE_BREAK_PRIMARY')]); stages.to_csv(OUT/'stage_metrics.csv',index=False)

    yearly=[]; buckets=[]
    if len(primary):
        primary['year']=pd.to_datetime(primary.structure_break_time).dt.year
        primary['bucket']=np.select([primary.st_age<=11,primary.st_age<=27,primary.st_age<=58],['B1','B2','B3'],default='B4')
        for y,g in primary.groupby('year'):yearly.append({'year':int(y),**a.metric(g,'STRUCTURE_BREAK_PRIMARY')})
        for b,g in primary.groupby('bucket'):buckets.append({'bucket':b,**a.metric(g,'STRUCTURE_BREAK_PRIMARY')})
    pd.DataFrame(yearly).to_csv(OUT/'yearly_primary.csv',index=False); pd.DataFrame(buckets).to_csv(OUT/'market_clock_buckets.csv',index=False)

    boots=[]
    for hh in HOLDS:
        if len(primary):
            q=a.cluster_boot_mean(primary,f'R{hh}',SEED+hh); qp=a.cluster_boot_mean(primary,f'pct{hh}',SEED+100+hh)
            boots.append({'hold_h':hh,'EV_R':q['mean'],'CI_R_lo':q['lo'],'CI_R_hi':q['hi'],'P_R_gt0':q['P_gt0'],'EV_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_pct_gt0':qp['P_gt0']})
    pd.DataFrame(boots).to_csv(OUT/'primary_cluster_bootstrap.csv',index=False)

    pairs=[]
    if len(primary) and len(fail_rep):
        p=primary[['correction_id','st_episode_id','R48','pct48','R72','pct72']].merge(fail_rep[['correction_id','R48','pct48','R72','pct72']],on='correction_id',suffixes=('_break','_fail'))
        for hh in HOLDS:
            p[f'delta_R{hh}']=p[f'R{hh}_break']-p[f'R{hh}_fail']; p[f'delta_pct{hh}']=p[f'pct{hh}_break']-p[f'pct{hh}_fail']
        p.to_csv(OUT/'paired_break_vs_failed_attack.csv',index=False)
        for hh in HOLDS:
            q=a.paired_boot(p,f'delta_R{hh}',SEED+200+hh); qp=a.paired_boot(p,f'delta_pct{hh}',SEED+300+hh)
            pairs.append({'hold_h':hh,'N_pairs':len(p),'break_EV_R':float(p[f'R{hh}_break'].mean()),'failed_EV_R':float(p[f'R{hh}_fail'].mean()),'delta_R':q['mean'],'CI_R_lo':q['lo'],'CI_R_hi':q['hi'],'P_delta_R_gt0':q['P_gt0'],'break_EV_pct':float(p[f'pct{hh}_break'].mean()),'failed_EV_pct':float(p[f'pct{hh}_fail'].mean()),'delta_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_delta_pct_gt0':qp['P_gt0']})
    pd.DataFrame(pairs).to_csv(OUT/'paired_timing_test.csv',index=False)

    weeks=max((pd.Timestamp(cand.decision_time.max())-START).days/7.0,1)
    freq={'trades':len(primary),'weeks':weeks,'trades_per_week':len(primary)/weeks,'h4_bear_episodes_with_trade':int(primary.st_episode_id.nunique()) if len(primary) else 0,
          'median_onset_to_fail_h':float(completed.onset_to_fail_h.median()) if len(completed) else np.nan,'median_fail_to_break_h':float(completed.fail_to_break_h.median()) if len(completed) else np.nan,'median_onset_to_break_h':float(completed.onset_to_break_h.median()) if len(completed) else np.nan}
    pd.DataFrame([freq]).to_csv(OUT/'frequency_and_delays.csv',index=False)

    report=['# SELL_CORE_006B — CORRECTION_EPISODE → FAILED_ATTACK → STRUCTURE_BREAK — LIFECYCLE SAFE','',
            '**Technical correction only:** accepted/invalidated H1 attack highs are permanently retired; pivots formed before the current H4-bear episode cannot seed its correction. No research thresholds changed.','',
            '## Census','',pd.DataFrame([census]).to_markdown(index=False),'','## Stage replay — same completed sequences','',stages.to_markdown(index=False),'',
            '## Primary cluster bootstrap','',pd.DataFrame(boots).to_markdown(index=False) if boots else 'No primary trades.','',
            '## Paired structure-break vs failed-attack timing','',pd.DataFrame(pairs).to_markdown(index=False) if pairs else 'No paired trades.','',
            '## Yearly primary','',pd.DataFrame(yearly).to_markdown(index=False) if yearly else 'No yearly trades.','',
            '## Market-clock diagnostic at break','',pd.DataFrame(buckets).to_markdown(index=False) if buckets else 'No bucket trades.','',
            '## Frequency','',pd.DataFrame([freq]).to_markdown(index=False),'',
            '## Verdict rule','',
            'Same preregistered rule as 006A: PASS only if STRUCTURE_BREAK is positive in R and price space, transfers across years, and improves paired timing versus FAILED_ATTACK.']
    (OUT/'REPORT.md').write_text('\n'.join(report)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
