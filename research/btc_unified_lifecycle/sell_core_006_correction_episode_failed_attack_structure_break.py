#!/usr/bin/env python3
"""SELL_CORE_006 — CORRECTION_EPISODE -> FAILED_ATTACK -> STRUCTURE_BREAK.

Preregistered from the user's visual SELL model after SELL_CORE_004/005 rejected snapshot/location proxies.
This LAB tests event ORDER, not a new indicator stack.

Frozen sequence:
1) GLOBAL BEAR = canonical H4 Supertrend ATR10 x3 DOWN, U05 BAR_OPEN lag1.
2) H1 pivots use strength=2 and are causal only after two right-side H1 bars have CLOSED.
3) ONE bullish correction episode becomes READY only when, inside the current H4-bear episode:
      last H1 swing high > previous H1 swing high  (HH)
      last H1 swing low  > previous H1 swing low   (HL)
      latest HL occurs AFTER latest HH              (pullback after the HH)
   Thus the correction has an actual HH/HL sequence plus a pullback before another attack.
4) ATTACK LEVEL = that latest confirmed H1 HH; SUPPORT = the confirmed H1 HL after it.
5) If an M15 close accepts above ATTACK LEVEL before failure, that level is retired. The state machine waits
   for a NEW confirmed H1 high + later HL; no stale-level reuse.
6) FAILED ATTACK = M15 high > ATTACK LEVEL AND same M15 close < ATTACK LEVEL.
   Freeze ATTACK LEVEL and SUPPORT at this moment.
7) STRUCTURE BREAK = on a LATER M15 bar, close < frozen SUPPORT while H4 remains bearish.
   If the failed attack bar itself also closes below SUPPORT, discard as intrabar-ambiguous (OHLC cannot prove order).
   If price closes above the failed ATTACK LEVEL before structure break, the failure is invalidated and the
   correction returns to READY/waits for a new valid attack structure.
8) ONE SELL maximum per correction episode. After a trade or an unarmed support break, require the bullish
   HH/HL READY condition to turn false before a new correction episode can start.
9) No Funding, FVG, v283, D1, PRE, B3 or resistance-location gate.
10) SELL execution = next M1 open after M15 structure-break close.
    SL=1.5 x completed H1 ATR14; no TP; 48h primary / 72h sensitivity; $27.5/BTC cost proxy.
11) Diagnostics only: entry at correction onset and failed-attack time for the SAME completed sequence;
    B1/B2/B3/B4 at final structure break; year splits; stage delays.
12) Inference clusters by H4 ST episode. The primary hypothesis passes only if completed sequence is positive
    in R and price space, not carried by one year, and STRUCTURE_BREAK improves paired timing versus the
    preceding FAILED_ATTACK on the same completed episodes.

Frozen unified Binance window: 2024-01-01 through available 2026-08-10 data.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import sell_core_004_htf_bear_local_correction_failed_breakout as p4

M1ZIP='btc_1m.zip'; M5ZIP='btc_5m.zip'
OUT=Path('sell_core_006_out'); OUT.mkdir(exist_ok=True)
START=pd.Timestamp('2024-01-01'); HOLDS=(48,72); STOP_ATR=1.5; COST_USD=27.5
BOOT=20000; SEED=406006


def pf(x):
    z=pd.Series(x).dropna(); gp=float(z[z>0].sum()); gl=float(-z[z<0].sum())
    return gp/gl if gl>0 else (float('inf') if gp>0 else np.nan)


def h1_pivot_events(h1,strength=2):
    """Causal H1 high/low pivots; effective only after right-side bars are complete."""
    x=h1.reset_index(drop=True).copy(); H=x.high.to_numpy(float); L=x.low.to_numpy(float); rows=[]
    for p in range(strength,len(x)-strength):
        ci=p+strength
        eff=pd.Timestamp(x.close_time.iloc[ci])
        pt=pd.Timestamp(x.time.iloc[p])
        if H[p]>np.max(H[p-strength:p]) and H[p]>=np.max(H[p+1:p+strength+1]):
            rows.append({'effective_time':eff,'pivot_time':pt,'pivot_idx':int(p),'kind':'H','price':float(H[p])})
        if L[p]<np.min(L[p-strength:p]) and L[p]<=np.min(L[p+1:p+strength+1]):
            rows.append({'effective_time':eff,'pivot_time':pt,'pivot_idx':int(p),'kind':'L','price':float(L[p])})
    return pd.DataFrame(rows).sort_values(['effective_time','pivot_time','kind']).reset_index(drop=True)


def ready_structure(highs,lows):
    if len(highs)<2 or len(lows)<2:return None
    h1,h2=highs[-2],highs[-1]; l1,l2=lows[-2],lows[-1]
    ok=(h2['price']>h1['price']) and (l2['price']>l1['price']) and (l2['pivot_time']>h2['pivot_time'])
    if not ok:return None
    return {'prev_high':h1,'attack_high':h2,'prev_low':l1,'support_low':l2}


def run_state_machine(cand,piv):
    """Process M15 decisions in strict chronological order, resetting on H4 ST episode changes."""
    z=cand.sort_values('decision_time').reset_index(drop=True).copy()
    pe=piv.to_dict('records'); pi=0
    current_st_ep=None; highs=[]; lows=[]
    mode='IDLE'  # IDLE / READY / ARMED / WAIT_RESET
    correction_id=0; active_id=None
    onset_time=None; onset_row=None; attack_level=np.nan; support=np.nan; attack_pivot_idx=None; support_pivot_idx=None
    failed_time=None; failed_row=None; frozen_attack=np.nan; frozen_support=np.nan
    attack_attempts=0; acceptances=0; ambiguous=0; unarmed_breaks=0; invalidated_failures=0
    completed=[]; onset_rows=[]; failed_rows=[]; transition_log=[]; last_ready=False

    for _,r in z.iterrows():
        t=pd.Timestamp(r.decision_time)
        # feed H1 pivots known by decision time
        while pi<len(pe) and pd.Timestamp(pe[pi]['effective_time'])<=t:
            e=pe[pi]; pi+=1
            # pivots are assigned later only if they belong to current bear episode by pivot time >= episode start surrogate.
            # We reset lists on each ST episode, and effective-time processing prevents future leakage.
            if current_st_ep is not None and int(r.st_episode_id)==current_st_ep and int(r.st_dir)==-1:
                if e['kind']=='H': highs.append(e)
                else: lows.append(e)

        st_ep=int(r.st_episode_id); bear=(int(r.st_dir)==-1)
        if current_st_ep!=st_ep:
            current_st_ep=st_ep; highs=[]; lows=[]; mode='IDLE'; active_id=None
            onset_time=None; onset_row=None; failed_time=None; failed_row=None
            attack_level=np.nan; support=np.nan; frozen_attack=np.nan; frozen_support=np.nan
            last_ready=False
            # pivots whose effective_time was processed before the ST reset are intentionally not carried in.

        if not bear:
            mode='IDLE'; active_id=None; last_ready=False
            continue

        rs=ready_structure(highs,lows)
        is_ready=rs is not None

        # WAIT_RESET prevents repeated episodes from the same still-true HH/HL snapshot.
        if mode=='WAIT_RESET':
            if not is_ready:
                mode='IDLE'; last_ready=False
            else:
                last_ready=True
            continue

        # Start one correction episode only on false->true READY transition.
        if mode=='IDLE':
            if is_ready and not last_ready:
                correction_id+=1; active_id=correction_id; mode='READY'
                onset_time=t; onset_row=r.copy()
                attack_level=float(rs['attack_high']['price']); support=float(rs['support_low']['price'])
                attack_pivot_idx=int(rs['attack_high']['pivot_idx']); support_pivot_idx=int(rs['support_low']['pivot_idx'])
                d=r.to_dict(); d.update(correction_id=active_id,onset_time=t,attack_level=attack_level,support=support,
                                      attack_pivot_idx=attack_pivot_idx,support_pivot_idx=support_pivot_idx)
                onset_rows.append(d); transition_log.append({'time':t,'correction_id':active_id,'event':'CORRECTION_READY','level':attack_level,'support':support})
            last_ready=is_ready
            if mode=='IDLE':continue

        # Refresh READY structure only if no failure is armed. This lets accepted attacks roll into a new H1 high+HL.
        if mode=='READY':
            if is_ready:
                new_hi=int(rs['attack_high']['pivot_idx']); new_lo=int(rs['support_low']['pivot_idx'])
                if new_hi!=attack_pivot_idx or new_lo!=support_pivot_idx:
                    attack_level=float(rs['attack_high']['price']); support=float(rs['support_low']['price'])
                    attack_pivot_idx=new_hi; support_pivot_idx=new_lo
                    transition_log.append({'time':t,'correction_id':active_id,'event':'READY_REFRESH','level':attack_level,'support':support})
            else:
                # confirmed H1 structure is no longer HH/HL before the attack sequence completes.
                mode='WAIT_RESET'; transition_log.append({'time':t,'correction_id':active_id,'event':'CORRECTION_LOST_BEFORE_ATTACK','level':np.nan,'support':np.nan}); last_ready=False; continue

            # If local support breaks before a failed attack, this correction ended without our sequence.
            if np.isfinite(support) and float(r.close)<support:
                unarmed_breaks+=1; mode='WAIT_RESET'; transition_log.append({'time':t,'correction_id':active_id,'event':'SUPPORT_BREAK_NO_FAILED_ATTACK','level':attack_level,'support':support}); last_ready=is_ready; continue

            if np.isfinite(attack_level) and float(r.high)>attack_level:
                attack_attempts+=1
                if float(r.close)>attack_level:
                    # accepted above: retire this exact high; keep correction alive but cannot reuse stale level.
                    acceptances+=1; transition_log.append({'time':t,'correction_id':active_id,'event':'ATTACK_ACCEPTED','level':attack_level,'support':support})
                    attack_level=np.nan; support=np.nan; attack_pivot_idx=None; support_pivot_idx=None
                    # stay READY, but require a genuinely new H1 high+HL pair before next attack
                    continue
                if float(r.close)<attack_level:
                    # If same M15 also closes under support, order inside bar is unknowable -> discard episode.
                    if np.isfinite(support) and float(r.close)<support:
                        ambiguous+=1; mode='WAIT_RESET'; transition_log.append({'time':t,'correction_id':active_id,'event':'AMBIGUOUS_ATTACK_AND_BREAK_SAME_BAR','level':attack_level,'support':support}); last_ready=is_ready; continue
                    failed_time=t; failed_row=r.copy(); frozen_attack=float(attack_level); frozen_support=float(support); mode='ARMED'
                    d=r.to_dict(); d.update(correction_id=active_id,onset_time=onset_time,failed_attack_time=t,
                                          attack_level=frozen_attack,support=frozen_support)
                    failed_rows.append(d); transition_log.append({'time':t,'correction_id':active_id,'event':'FAILED_ATTACK','level':frozen_attack,'support':frozen_support})
                    continue

        elif mode=='ARMED':
            # Failed attack is invalid if buyers subsequently accept above the frozen attacked high before breaking HL.
            if float(r.close)>frozen_attack:
                invalidated_failures+=1; mode='READY'; failed_time=None; failed_row=None
                transition_log.append({'time':t,'correction_id':active_id,'event':'FAILED_ATTACK_INVALIDATED','level':frozen_attack,'support':frozen_support})
                # force a new H1 high+HL before another attack; stale level is dead
                attack_level=np.nan; support=np.nan; attack_pivot_idx=None; support_pivot_idx=None
                continue
            if t>failed_time and float(r.close)<frozen_support:
                d=r.to_dict(); d.update(correction_id=active_id,onset_time=onset_time,failed_attack_time=failed_time,
                                      structure_break_time=t,attack_level=frozen_attack,support=frozen_support,
                                      onset_to_fail_h=(failed_time-onset_time).total_seconds()/3600.0,
                                      fail_to_break_h=(t-failed_time).total_seconds()/3600.0,
                                      onset_to_break_h=(t-onset_time).total_seconds()/3600.0)
                # keep selected state from failed and onset for paired replays
                if failed_row is not None:
                    d['failed_st_age']=int(failed_row.st_age); d['failed_atr_pct']=float(failed_row.atr_pct)
                completed.append(d); transition_log.append({'time':t,'correction_id':active_id,'event':'STRUCTURE_BREAK_SELL','level':frozen_attack,'support':frozen_support})
                mode='WAIT_RESET'; last_ready=is_ready
                failed_time=None; failed_row=None
                continue

        last_ready=is_ready

    census={'correction_episodes_started':correction_id,'completed_sequences':len(completed),'failed_attack_events':len(failed_rows),
            'attack_attempts':attack_attempts,'accepted_attacks':acceptances,'ambiguous_same_bar_discarded':ambiguous,
            'unarmed_support_breaks':unarmed_breaks,'invalidated_failures':invalidated_failures}
    return pd.DataFrame(completed),pd.DataFrame(onset_rows),pd.DataFrame(failed_rows),pd.DataFrame(transition_log),census


def replay_at(rows,m1,h1,time_col,label):
    if rows is None or len(rows)==0:return pd.DataFrame()
    return p4.replay(rows,m1,h1,time_col,label)


def metric(g,name):
    row={'branch':name,'N':len(g),'h4_episodes':g.st_episode_id.nunique() if len(g) and 'st_episode_id' in g else 0}
    for hh in HOLDS:
        if len(g):
            z=g[f'R{hh}'].dropna(); row.update({f'EV_R{hh}':float(z.mean()) if len(z) else np.nan,f'PF{hh}':pf(z),
                f'WR{hh}':float((z>0).mean()) if len(z) else np.nan,f'EV_pct{hh}':float(g[f'pct{hh}'].mean()),
                f'SL_rate{hh}':float((g[f'exit{hh}']=='SL').mean())})
        else: row.update({f'EV_R{hh}':np.nan,f'PF{hh}':np.nan,f'WR{hh}':np.nan,f'EV_pct{hh}':np.nan,f'SL_rate{hh}':np.nan})
    return row


def cluster_boot_mean(g,col,seed):
    z=g[['st_episode_id',col]].dropna(); ids=z.st_episode_id.unique()
    if len(ids)<5:return {'mean':float(z[col].mean()) if len(z) else np.nan,'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    a=z.groupby('st_episode_id')[col].agg(['sum','count']).to_numpy(float); rng=np.random.default_rng(seed); vals=[]
    for _ in range(BOOT):
        s=a[rng.integers(0,len(a),len(a))].sum(axis=0); vals.append(s[0]/s[1])
    v=np.asarray(vals); return {'mean':float(z[col].mean()),'lo':float(np.quantile(v,.025)),'hi':float(np.quantile(v,.975)),'P_gt0':float((v>0).mean())}


def paired_boot(pair,col,seed):
    z=pair[['st_episode_id',col]].dropna(); ids=z.st_episode_id.unique()
    if len(ids)<5:return {'mean':float(z[col].mean()) if len(z) else np.nan,'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    a=z.groupby('st_episode_id')[col].agg(['sum','count']).to_numpy(float); rng=np.random.default_rng(seed); vals=[]
    for _ in range(BOOT):
        s=a[rng.integers(0,len(a),len(a))].sum(axis=0); vals.append(s[0]/s[1])
    v=np.asarray(vals); return {'mean':float(z[col].mean()),'lo':float(np.quantile(v,.025)),'hi':float(np.quantile(v,.975)),'P_gt0':float((v>0).mean())}


def main():
    m1=base.load_zip(M1ZIP); m5=base.load_zip(M5ZIP)
    m1=m1[m1.time>=START].copy(); m5=m5[m5.time>=START-pd.Timedelta(days=90)].copy()
    h1=p4.make_h1(m1); clock=p4.make_clock(m5); m15=p4.make_m15(m5)
    cand=p4.attach_states(m15,h1,clock)
    cand=cand[(cand.decision_time>=START)&cand.st_dir.notna()&cand.st_age.notna()&cand.atr14.notna()].copy()
    piv=h1_pivot_events(h1,2); piv.to_csv(OUT/'h1_causal_pivots.csv',index=False)

    completed,onsets,failed,log,census=run_state_machine(cand,piv)
    completed.to_csv(OUT/'completed_sequences.csv',index=False); onsets.to_csv(OUT/'correction_onsets.csv',index=False)
    failed.to_csv(OUT/'failed_attack_events.csv',index=False); log.to_csv(OUT/'state_transitions.csv',index=False)
    pd.DataFrame([census]).to_csv(OUT/'census.csv',index=False)

    # Primary execution at causal structure break.
    primary=replay_at(completed,m1,h1,'structure_break_time','STRUCTURE_BREAK')
    primary.to_csv(OUT/'replay_structure_break.csv',index=False)

    # Paired stage replays only for completed sequences, so all three rows refer to the same eventual episodes.
    stagebase=completed.copy()
    onset_rep=replay_at(stagebase,m1,h1,'onset_time','CORRECTION_ONSET_DIAGNOSTIC')
    fail_rep=replay_at(stagebase,m1,h1,'failed_attack_time','FAILED_ATTACK_DIAGNOSTIC')
    onset_rep.to_csv(OUT/'replay_onset_completed_sequences.csv',index=False)
    fail_rep.to_csv(OUT/'replay_failed_attack_completed_sequences.csv',index=False)

    stages=pd.DataFrame([metric(onset_rep,'CORRECTION_ONSET_completed_only'),metric(fail_rep,'FAILED_ATTACK_completed_only'),metric(primary,'STRUCTURE_BREAK_PRIMARY')])
    stages.to_csv(OUT/'stage_metrics.csv',index=False)

    # Primary yearly + market-clock decomposition at structure break.
    yearly=[]; buckets=[]
    if len(primary):
        primary['year']=pd.to_datetime(primary.structure_break_time).dt.year
        primary['bucket']=np.select([primary.st_age<=11,primary.st_age<=27,primary.st_age<=58],['B1','B2','B3'],default='B4')
        for y,g in primary.groupby('year'): yearly.append({'year':int(y),**metric(g,'STRUCTURE_BREAK_PRIMARY')})
        for b,g in primary.groupby('bucket'): buckets.append({'bucket':b,**metric(g,'STRUCTURE_BREAK_PRIMARY')})
    pd.DataFrame(yearly).to_csv(OUT/'yearly_primary.csv',index=False); pd.DataFrame(buckets).to_csv(OUT/'market_clock_buckets.csv',index=False)

    # Cluster-bootstrap absolute primary EV.
    boots=[]
    for hh in HOLDS:
        if len(primary):
            q=cluster_boot_mean(primary,f'R{hh}',SEED+hh); qp=cluster_boot_mean(primary,f'pct{hh}',SEED+100+hh)
            boots.append({'hold_h':hh,'EV_R':q['mean'],'CI_R_lo':q['lo'],'CI_R_hi':q['hi'],'P_R_gt0':q['P_gt0'],
                          'EV_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_pct_gt0':qp['P_gt0']})
    pd.DataFrame(boots).to_csv(OUT/'primary_cluster_bootstrap.csv',index=False)

    # Pair exact same completed sequences: does waiting for structure break improve over failed-attack timing?
    pairs=[]
    if len(primary) and len(fail_rep):
        fcols=['correction_id','R48','pct48','R72','pct72']; scols=['correction_id','st_episode_id','R48','pct48','R72','pct72']
        p=primary[scols].merge(fail_rep[fcols],on='correction_id',suffixes=('_break','_fail'))
        for hh in HOLDS:
            p[f'delta_R{hh}']=p[f'R{hh}_break']-p[f'R{hh}_fail']; p[f'delta_pct{hh}']=p[f'pct{hh}_break']-p[f'pct{hh}_fail']
        p.to_csv(OUT/'paired_break_vs_failed_attack.csv',index=False)
        for hh in HOLDS:
            q=paired_boot(p,f'delta_R{hh}',SEED+200+hh); qp=paired_boot(p,f'delta_pct{hh}',SEED+300+hh)
            pairs.append({'hold_h':hh,'N_pairs':len(p),'break_EV_R':float(p[f'R{hh}_break'].mean()),'failed_EV_R':float(p[f'R{hh}_fail'].mean()),
                          'delta_R':q['mean'],'CI_R_lo':q['lo'],'CI_R_hi':q['hi'],'P_delta_R_gt0':q['P_gt0'],
                          'break_EV_pct':float(p[f'pct{hh}_break'].mean()),'failed_EV_pct':float(p[f'pct{hh}_fail'].mean()),
                          'delta_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_delta_pct_gt0':qp['P_gt0']})
    pd.DataFrame(pairs).to_csv(OUT/'paired_timing_test.csv',index=False)

    # Delay distribution and frequency.
    delays=pd.DataFrame()
    if len(completed):
        delays=completed[['correction_id','st_episode_id','onset_to_fail_h','fail_to_break_h','onset_to_break_h','st_age']].copy()
        delays.to_csv(OUT/'sequence_delays.csv',index=False)
    weeks=max((pd.Timestamp(cand.decision_time.max())-START).days/7.0,1)
    frequency={'trades':len(primary),'weeks':weeks,'trades_per_week':len(primary)/weeks,'h4_bear_episodes_with_trade':int(primary.st_episode_id.nunique()) if len(primary) else 0,
               'median_onset_to_fail_h':float(completed.onset_to_fail_h.median()) if len(completed) else np.nan,
               'median_fail_to_break_h':float(completed.fail_to_break_h.median()) if len(completed) else np.nan,
               'median_onset_to_break_h':float(completed.onset_to_break_h.median()) if len(completed) else np.nan}
    pd.DataFrame([frequency]).to_csv(OUT/'frequency_and_delays.csv',index=False)

    report=['# SELL_CORE_006 — CORRECTION_EPISODE → FAILED_ATTACK → STRUCTURE_BREAK','',
            '**Primary test:** causal sequence/state machine, one SELL maximum per correction episode. No Funding/FVG/v283/B3/location gate.','',
            '## Frozen sequence','',
            'H4 ST bearish → causal H1 HH/HL with HL after latest HH → M15 attack of that HH → same-bar rejection → later M15 close below frozen HL → SELL.','',
            'Same-bar attack+HL-break is discarded because OHLC cannot establish event order. Accepted closes above the attack high invalidate/retire that attack level.','',
            '## Census','',pd.DataFrame([census]).to_markdown(index=False),'',
            '## Stage replay (same completed sequences)','',stages.to_markdown(index=False),'',
            '## Primary cluster bootstrap','',pd.DataFrame(boots).to_markdown(index=False) if boots else 'No primary trades.','',
            '## Paired STRUCTURE_BREAK vs FAILED_ATTACK timing','',pd.DataFrame(pairs).to_markdown(index=False) if pairs else 'No paired trades.','',
            '## Yearly primary','',pd.DataFrame(yearly).to_markdown(index=False) if yearly else 'No yearly trades.','',
            '## Market-clock diagnostic at structure break','',pd.DataFrame(buckets).to_markdown(index=False) if buckets else 'No bucket trades.','',
            '## Frequency / delay','',pd.DataFrame([frequency]).to_markdown(index=False),'',
            '## Verdict rule','',
            'PASS only if STRUCTURE_BREAK primary is positive in R and price space, transfers across years with usable N, and waiting for the structure break improves paired timing versus the preceding failed attack. B1/B2/B3/B4 remain diagnostics, not gates.']
    (OUT/'REPORT.md').write_text('\n'.join(report))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
