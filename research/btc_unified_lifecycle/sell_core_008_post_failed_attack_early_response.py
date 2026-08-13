#!/usr/bin/env python3
"""SELL_CORE_008 — POST_FAILED_ATTACK_EARLY_RESPONSE.

Frozen before outcomes, directly after SELL_CORE_007.

Population:
- every FIRST causal failed attack from lifecycle-safe SELL_CORE_006B;
- no future structure-break eligibility.

Post-failure horizons: 15 / 30 / 60 minutes.
At each horizon, using only completed M5 bars after the failed-attack M15 close:
1) bearish_displacement = (failure_close - horizon_close) / failure H1 ATR14.
2) bearish_efficiency = signed bearish net close move / sum(abs(M5 close-to-close path)), seeded by failure_close.
3) repeated_reclaim = any completed M5 close > frozen attack_level.
4) acceptance_below = fraction of completed M5 closes < failure_close.
5) lower_high = at least one causal M5 strength-1 swing high, confirmed by the next M5 bar by the horizon,
   whose high remains below frozen attack_level.

Frozen score (not optimized): one bearish vote for displacement>0, efficiency>0, NO repeated_reclaim,
acceptance_below>0.50, and lower_high=True. EARLY_RESPONSE_PASS = >=3 of 5 votes.

Early-horizon eligibility:
- horizon must remain inside the same canonical H4 bearish ST episode;
- no full structure break belonging to the FIRST failed attack may have occurred before/equal horizon.
This prevents calling a post-break observation an "early" predictor.

Future structure break is diagnostic label only. For the FIRST failed attack, winner=True only if the next lifecycle
resolution after that failure is STRUCTURE_BREAK_SELL; if FAILED_ATTACK_INVALIDATED_HIGH_RETIRED occurs first, it is not
a winner even if the correction later creates another failure and eventually breaks.

Execution tests:
- SELL next M1 open after 15/30/60m response horizon for EARLY_RESPONSE_PASS;
- same frozen SL=1.5x completed H1 ATR14, no TP, 48h primary / 72h sensitivity, $27.5/BTC cost proxy;
- paired against immediate failed-attack entry on exactly the same selected events.

No Funding/FVG/v283/B3/location threshold tuning. Market-clock buckets and years are diagnostics only.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import sell_core_004_htf_bear_local_correction_failed_breakout as p4
import sell_core_006_correction_episode_failed_attack_structure_break as a
import sell_core_006b_correction_episode_state_machine_safe as b

OUT=Path('sell_core_008_out'); OUT.mkdir(exist_ok=True)
START=a.START; HOLDS=a.HOLDS; BOOT=a.BOOT; SEED=408008
HORIZONS=(15,30,60)


def resolution_after_first_failure(log, first_fail):
    z=log.copy(); z['time']=pd.to_datetime(z.time)
    result={}
    for _,r in first_fail.iterrows():
        cid=int(r.correction_id); ft=pd.Timestamp(r.failed_attack_time)
        q=z[(z.correction_id==cid)&(z.time>ft)&z.event.isin(['FAILED_ATTACK_INVALIDATED_HIGH_RETIRED','STRUCTURE_BREAK_SELL'])].sort_values('time')
        if len(q)==0:
            result[cid]={'resolution':'UNRESOLVED','resolution_time':pd.NaT,'winner':False}
        else:
            e=q.iloc[0]
            result[cid]={'resolution':str(e.event),'resolution_time':pd.Timestamp(e.time),'winner':str(e.event)=='STRUCTURE_BREAK_SELL'}
    return result


def lower_high_m5(win, attack):
    if len(win)<3:return False
    H=win.high.to_numpy(float)
    for i in range(1,len(H)-1):
        if H[i]>H[i-1] and H[i]>=H[i+1] and H[i]<attack:
            return True
    return False


def horizon_features(first_fail,m5,cand,resolution):
    x=m5.sort_values('time').copy()
    x['bar_close_time']=pd.to_datetime(x.time)+pd.Timedelta(minutes=5)
    cidx=cand.set_index('decision_time',drop=False)
    rows=[]
    for _,r in first_fail.iterrows():
        cid=int(r.correction_id); ft=pd.Timestamp(r.failed_attack_time); fail_close=float(r.close)
        atr=float(r.atr14); attack=float(r.attack_level); res=resolution[cid]
        for hm in HORIZONS:
            ht=ft+pd.Timedelta(minutes=hm)
            # canonical H4 state must still be same bearish episode at horizon.
            if ht not in cidx.index:
                state_ok=False
            else:
                cr=cidx.loc[ht]
                if isinstance(cr,pd.DataFrame):cr=cr.iloc[-1]
                state_ok=int(cr.st_dir)==-1 and int(cr.st_episode_id)==int(r.st_episode_id)
            # If the FIRST failure already produced its full structure break, this is no longer early.
            broke_early=bool(res['winner'] and pd.notna(res['resolution_time']) and pd.Timestamp(res['resolution_time'])<=ht)
            w=x[(x.bar_close_time>ft)&(x.bar_close_time<=ht)].copy()
            complete=(len(w)==hm//5)
            if not complete or not state_ok or broke_early:
                continue
            closes=w.close.to_numpy(float)
            last=float(closes[-1])
            path=np.abs(np.diff(np.r_[fail_close,closes])).sum()
            disp=(fail_close-last)/atr if atr>0 else np.nan
            eff=(fail_close-last)/path if path>0 else 0.0
            reclaim=bool((w.close.astype(float)>attack).any())
            acc=float((w.close.astype(float)<fail_close).mean())
            lh=lower_high_m5(w,attack)
            votes=int(disp>0)+int(eff>0)+int(not reclaim)+int(acc>0.50)+int(lh)
            d=r.to_dict(); d.update({
                'early_time':ht,'horizon_min':hm,'bearish_displacement':disp,'bearish_efficiency':eff,
                'repeated_reclaim':reclaim,'acceptance_below':acc,'lower_high':lh,'bear_votes':votes,
                'early_response_pass':votes>=3,'future_resolution':res['resolution'],'future_resolution_time':res['resolution_time'],
                'future_structure_break_winner':res['winner']})
            rows.append(d)
    return pd.DataFrame(rows)


def feature_separation(feat):
    rows=[]
    oriented=['bearish_displacement','bearish_efficiency','acceptance_below','bear_votes']
    binary=['repeated_reclaim','lower_high','early_response_pass']
    for hm,g in feat.groupby('horizon_min'):
        for f in oriented:
            w=g[g.future_structure_break_winner][f].astype(float); n=g[~g.future_structure_break_winner][f].astype(float)
            rows.append({'horizon_min':hm,'feature':f,'winner_N':len(w),'other_N':len(n),'winner_mean':w.mean() if len(w) else np.nan,
                         'other_mean':n.mean() if len(n) else np.nan,'delta_winner_minus_other':(w.mean()-n.mean()) if len(w) and len(n) else np.nan})
        for f in binary:
            w=g[g.future_structure_break_winner][f].astype(float); n=g[~g.future_structure_break_winner][f].astype(float)
            rows.append({'horizon_min':hm,'feature':f,'winner_N':len(w),'other_N':len(n),'winner_mean':w.mean() if len(w) else np.nan,
                         'other_mean':n.mean() if len(n) else np.nan,'delta_winner_minus_other':(w.mean()-n.mean()) if len(w) and len(n) else np.nan})
    return pd.DataFrame(rows)


def metric(g,name):return a.metric(g,name)


def cluster_boot(g,col,seed):
    return a.cluster_boot_mean(g,col,seed)


def paired_delta(pair,col,seed):
    z=pair[['st_episode_id',col]].dropna()
    if len(z)==0:return {'mean':np.nan,'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    if z.st_episode_id.nunique()<5:return {'mean':float(z[col].mean()),'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    ag=z.groupby('st_episode_id')[col].agg(['sum','count']).to_numpy(float)
    rng=np.random.default_rng(seed); vals=np.empty(BOOT,float)
    for i in range(BOOT):
        s=ag[rng.integers(0,len(ag),len(ag))].sum(axis=0); vals[i]=s[0]/s[1]
    return {'mean':float(z[col].mean()),'lo':float(np.quantile(vals,.025)),'hi':float(np.quantile(vals,.975)),'P_gt0':float((vals>0).mean())}


def paired_early_vs_immediate(selected,m1,h1,hm):
    if len(selected)==0:return pd.DataFrame(),pd.DataFrame(),[]
    er=a.replay_at(selected,m1,h1,'early_time',f'EARLY_RESPONSE_{hm}M')
    ir=a.replay_at(selected,m1,h1,'failed_attack_time',f'IMMEDIATE_FAILURE_SAME_{hm}M')
    keep=['correction_id','st_episode_id']+[f'R{h}' for h in HOLDS]+[f'pct{h}' for h in HOLDS]
    p=er[keep].merge(ir[['correction_id']+[f'R{h}' for h in HOLDS]+[f'pct{h}' for h in HOLDS]],on='correction_id',suffixes=('_early','_imm'))
    stats=[]
    for hh in HOLDS:
        p[f'delta_R{hh}']=p[f'R{hh}_early']-p[f'R{hh}_imm']; p[f'delta_pct{hh}']=p[f'pct{hh}_early']-p[f'pct{hh}_imm']
        q=paired_delta(p,f'delta_R{hh}',SEED+hm*100+hh); qp=paired_delta(p,f'delta_pct{hh}',SEED+hm*100+500+hh)
        stats.append({'horizon_min':hm,'hold_h':hh,'N_pairs':len(p),
                      'early_EV_R':float(p[f'R{hh}_early'].mean()),'immediate_EV_R':float(p[f'R{hh}_imm'].mean()),
                      'delta_R':q['mean'],'CI_R_lo':q['lo'],'CI_R_hi':q['hi'],'P_delta_R_gt0':q['P_gt0'],
                      'early_EV_pct':float(p[f'pct{hh}_early'].mean()),'immediate_EV_pct':float(p[f'pct{hh}_imm'].mean()),
                      'delta_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_delta_pct_gt0':qp['P_gt0']})
    return er,ir,stats


def main():
    m1=base.load_zip(a.M1ZIP); m5=base.load_zip(a.M5ZIP)
    m1=m1[m1.time>=START].copy(); m5=m5[m5.time>=START-pd.Timedelta(days=90)].copy()
    h1=p4.make_h1(m1); clock=p4.make_clock(m5); m15=p4.make_m15(m5)
    cand=p4.attach_states(m15,h1,clock); cand=cand[(cand.decision_time>=START)&cand.st_dir.notna()&cand.st_age.notna()&cand.atr14.notna()].copy()
    piv=a.h1_pivot_events(h1,2)
    completed,onsets,failed,log,census=b.safe_state_machine(cand,piv)
    if len(failed): failed['failed_attack_time']=pd.to_datetime(failed.failed_attack_time)
    if len(log): log['time']=pd.to_datetime(log.time)
    first_fail=failed.sort_values('failed_attack_time').drop_duplicates('correction_id',keep='first').copy()
    resolution=resolution_after_first_failure(log,first_fail)
    feat=horizon_features(first_fail,m5,cand,resolution)
    feat.to_csv(OUT/'post_failure_features.csv',index=False)
    sep=feature_separation(feat); sep.to_csv(OUT/'winner_feature_separation.csv',index=False)

    gate_metrics=[]; gate_boot=[]; pair_stats=[]; yearly=[]; score_rows=[]
    for hm in HORIZONS:
        g=feat[feat.horizon_min==hm].copy()
        for score,sg in g.groupby('bear_votes'):
            score_rows.append({'horizon_min':hm,'bear_votes':int(score),'N':len(sg),'winner_rate':float(sg.future_structure_break_winner.mean()),
                               'winner_N':int(sg.future_structure_break_winner.sum())})
        sel=g[g.early_response_pass].copy()
        if len(sel)==0:continue
        er,ir,ps=paired_early_vs_immediate(sel,m1,h1,hm); pair_stats+=ps
        er.to_csv(OUT/f'replay_early_{hm}m.csv',index=False); ir.to_csv(OUT/f'replay_immediate_same_{hm}m.csv',index=False)
        gate_metrics.append({'horizon_min':hm,**metric(er,f'EARLY_RESPONSE_PASS_{hm}M')})
        for hh in HOLDS:
            q=cluster_boot(er,f'R{hh}',SEED+hm*10+hh); qp=cluster_boot(er,f'pct{hh}',SEED+hm*10+500+hh)
            gate_boot.append({'horizon_min':hm,'hold_h':hh,'EV_R':q['mean'],'CI_R_lo':q['lo'],'CI_R_hi':q['hi'],'P_R_gt0':q['P_gt0'],
                              'EV_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_pct_gt0':qp['P_gt0']})
        er['year']=pd.to_datetime(er.early_time).dt.year
        for y,yg in er.groupby('year'):
            yearly.append({'horizon_min':hm,'year':int(y),**metric(yg,f'EARLY_RESPONSE_PASS_{hm}M')})
    pd.DataFrame(score_rows).to_csv(OUT/'score_diagnostic.csv',index=False)
    pd.DataFrame(gate_metrics).to_csv(OUT/'early_gate_metrics.csv',index=False)
    pd.DataFrame(gate_boot).to_csv(OUT/'early_gate_bootstrap.csv',index=False)
    pd.DataFrame(pair_stats).to_csv(OUT/'paired_early_vs_immediate.csv',index=False)
    pd.DataFrame(yearly).to_csv(OUT/'yearly_early_gate.csv',index=False)

    coverage=[]
    for hm in HORIZONS:
        g=feat[feat.horizon_min==hm]
        coverage.append({'horizon_min':hm,'eligible_N':len(g),'pass_N':int(g.early_response_pass.sum()) if len(g) else 0,
                         'future_break_winners_eligible':int(g.future_structure_break_winner.sum()) if len(g) else 0,
                         'pass_winner_rate':float(g[g.early_response_pass].future_structure_break_winner.mean()) if g.early_response_pass.any() else np.nan})
    pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False)

    report=['# SELL_CORE_008 — POST_FAILED_ATTACK_EARLY_RESPONSE','',
            '**Frozen:** all first causal failed attacks; 15/30/60m post-failure M5 response; natural 3-of-5 bearish vote; no threshold tuning.','',
            '## Coverage','',pd.DataFrame(coverage).to_markdown(index=False),'',
            '## Winner vs other feature separation (diagnostic label only)','',sep.to_markdown(index=False),'',
            '## Score diagnostic','',pd.DataFrame(score_rows).to_markdown(index=False),'',
            '## EARLY_RESPONSE_PASS trading metrics','',pd.DataFrame(gate_metrics).to_markdown(index=False) if gate_metrics else 'No selected trades.','',
            '## Cluster bootstrap','',pd.DataFrame(gate_boot).to_markdown(index=False) if gate_boot else 'No selected trades.','',
            '## Paired early vs immediate failed-attack entry','',pd.DataFrame(pair_stats).to_markdown(index=False) if pair_stats else 'No pairs.','',
            '## Yearly early-gate','',pd.DataFrame(yearly).to_markdown(index=False) if yearly else 'No yearly rows.','',
            '## Frozen verdict rule','',
            'A horizon is a credible EARLY SELL candidate only if the 3/5 gate is positive in both R and price space, is not carried by one year, and does not lose paired value versus immediate failure entry. Feature/winner separation is diagnostic and cannot by itself promote a threshold.']
    (OUT/'REPORT.md').write_text('\n'.join(report)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
