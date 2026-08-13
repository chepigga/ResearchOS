#!/usr/bin/env python3
"""SELL_CORE_009 — BUYER_REGAIN_FALSE_POSITIVE_REJECTION.

Preregistered AFTER SELL_CORE_008, so this is same-history confirmation, NOT independent OOS.

Population:
- every FIRST causal failed attack from lifecycle-safe SELL_CORE_006B;
- post-failure features and early eligibility are inherited exactly from SELL_CORE_008;
- no future structure-break eligibility.

Primary horizon = 60 minutes because SELL_CORE_008 showed strongest winner/other response separation there.
15/30m are frozen sensitivity only; no horizon search in this LAB.

Buyer-regain veto at horizon, using only completed M5 bars after failed attack:
HARD_REGAIN:
  any completed M5 close > frozen attack_level.
SOFT_REGAIN votes (2 of 3):
  1) horizon close > failed-attack close;
  2) >50% completed M5 closes > failed-attack close;
  3) bullish path efficiency > 0, where bullish_eff=(last_close-fail_close)/sum(abs(M5 close path)).
BUYER_REGAIN_VETO = HARD_REGAIN OR SOFT_REGAIN.
SELL_KEEP = NOT BUYER_REGAIN_VETO.

No FVG/funding/v283/B3/location gates. No thresholds are optimized from outcomes in 009.

Execution:
- SELL next M1 open after 15/30/60m horizon only for SELL_KEEP;
- SL=1.5x completed H1 ATR14; no TP; 48h primary / 72h sensitivity; frozen $27.5/BTC cost proxy;
- paired against immediate failed-attack entry on the same kept events.

Primary success requires at 60m:
A) veto rejects a materially higher fraction of future non-break losers than future break winners;
B) SELL_KEEP is positive in R AND price space at 48h;
C) not carried by one year;
D) delayed 60m entry does not materially lose paired value vs immediate entry on same kept events.
Future structure break remains a diagnostic label only.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import sell_core_004_htf_bear_local_correction_failed_breakout as p4
import sell_core_006_correction_episode_failed_attack_structure_break as a
import sell_core_006b_correction_episode_state_machine_safe as b
import sell_core_008_post_failed_attack_early_response as s8

OUT=Path('sell_core_009_out'); OUT.mkdir(exist_ok=True)
START=a.START; HOLDS=a.HOLDS; BOOT=a.BOOT; SEED=409009
HORIZONS=(15,30,60); PRIMARY=60


def enrich_buyer_regain(feat,m5):
    x=m5.sort_values('time').copy(); x['bar_close_time']=pd.to_datetime(x.time)+pd.Timedelta(minutes=5)
    rows=[]
    for _,r in feat.iterrows():
        ft=pd.Timestamp(r.failed_attack_time); ht=pd.Timestamp(r.early_time); fail_close=float(r.close); attack=float(r.attack_level)
        w=x[(x.bar_close_time>ft)&(x.bar_close_time<=ht)].copy()
        closes=w.close.astype(float).to_numpy()
        if len(closes)==0: continue
        last=float(closes[-1]); path=float(np.abs(np.diff(np.r_[fail_close,closes])).sum())
        hard=bool((w.close.astype(float)>attack).any())
        horizon_above=bool(last>fail_close)
        acceptance_above=float((w.close.astype(float)>fail_close).mean())
        bull_eff=(last-fail_close)/path if path>0 else 0.0
        soft_votes=int(horizon_above)+int(acceptance_above>0.50)+int(bull_eff>0)
        soft=soft_votes>=2
        veto=hard or soft
        d=r.to_dict(); d.update({'hard_regain':hard,'horizon_close_above_failure':horizon_above,
                                 'acceptance_above':acceptance_above,'bullish_efficiency':bull_eff,
                                 'soft_regain_votes':soft_votes,'soft_regain':soft,
                                 'buyer_regain_veto':veto,'sell_keep':not veto})
        rows.append(d)
    return pd.DataFrame(rows)


def metric(g,name): return a.metric(g,name)


def paired_delta(pair,col,seed):
    z=pair[['st_episode_id',col]].dropna()
    if len(z)==0:return {'mean':np.nan,'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    ag=z.groupby('st_episode_id')[col].agg(['sum','count']).to_numpy(float)
    if len(ag)<5:return {'mean':float(z[col].mean()),'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    rng=np.random.default_rng(seed); vals=np.empty(BOOT,float)
    for i in range(BOOT):
        s=ag[rng.integers(0,len(ag),len(ag))].sum(axis=0); vals[i]=s[0]/s[1]
    return {'mean':float(z[col].mean()),'lo':float(np.quantile(vals,.025)),'hi':float(np.quantile(vals,.975)),'P_gt0':float((vals>0).mean())}


def replay_pair(sel,m1,h1,hm):
    er=a.replay_at(sel,m1,h1,'early_time',f'SELL_KEEP_{hm}M')
    ir=a.replay_at(sel,m1,h1,'failed_attack_time',f'IMMEDIATE_SAME_KEEP_{hm}M')
    keep=['correction_id','st_episode_id']+[f'R{h}' for h in HOLDS]+[f'pct{h}' for h in HOLDS]
    p=er[keep].merge(ir[['correction_id']+[f'R{h}' for h in HOLDS]+[f'pct{h}' for h in HOLDS]],on='correction_id',suffixes=('_early','_imm'))
    stats=[]
    for hh in HOLDS:
        p[f'delta_R{hh}']=p[f'R{hh}_early']-p[f'R{hh}_imm']; p[f'delta_pct{hh}']=p[f'pct{hh}_early']-p[f'pct{hh}_imm']
        qr=paired_delta(p,f'delta_R{hh}',SEED+hm*100+hh); qp=paired_delta(p,f'delta_pct{hh}',SEED+hm*100+500+hh)
        stats.append({'horizon_min':hm,'hold_h':hh,'N_pairs':len(p),
                      'early_EV_R':float(p[f'R{hh}_early'].mean()),'immediate_EV_R':float(p[f'R{hh}_imm'].mean()),
                      'delta_R':qr['mean'],'CI_R_lo':qr['lo'],'CI_R_hi':qr['hi'],'P_delta_R_gt0':qr['P_gt0'],
                      'early_EV_pct':float(p[f'pct{hh}_early'].mean()),'immediate_EV_pct':float(p[f'pct{hh}_imm'].mean()),
                      'delta_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_delta_pct_gt0':qp['P_gt0']})
    return er,ir,p,stats


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
    resolution=s8.resolution_after_first_failure(log,first_fail)
    feat=s8.horizon_features(first_fail,m5,cand,resolution)
    feat=enrich_buyer_regain(feat,m5)
    feat.to_csv(OUT/'buyer_regain_features.csv',index=False)

    confusion=[]; group_metrics=[]; boot=[]; yearly=[]; pairs_all=[]
    for hm in HORIZONS:
        g=feat[feat.horizon_min==hm].copy()
        win=g.future_structure_break_winner.astype(bool); veto=g.buyer_regain_veto.astype(bool)
        W=int(win.sum()); L=int((~win).sum())
        confusion.append({'horizon_min':hm,'eligible_N':len(g),'winner_N':W,'loser_N':L,
                          'winners_vetoed':int((win&veto).sum()),'winners_kept':int((win&~veto).sum()),
                          'winner_retention':float((win&~veto).sum()/W) if W else np.nan,
                          'losers_vetoed':int(((~win)&veto).sum()),'losers_kept':int(((~win)&~veto).sum()),
                          'loser_rejection':float(((~win)&veto).sum()/L) if L else np.nan,
                          'hard_veto_N':int(g.hard_regain.sum()),'soft_veto_N':int(g.soft_regain.sum()),
                          'sell_keep_N':int(g.sell_keep.sum())})
        # descriptive outcomes if one sold KEEP vs sold VETO population
        for label,sg in [('SELL_KEEP',g[g.sell_keep]),('BUYER_REGAIN_VETOED',g[g.buyer_regain_veto]),('ALL_ELIGIBLE',g)]:
            if len(sg):
                rep=a.replay_at(sg,m1,h1,'early_time',f'{label}_{hm}M')
                if label=='SELL_KEEP': rep.to_csv(OUT/f'replay_sell_keep_{hm}m.csv',index=False)
                group_metrics.append({'horizon_min':hm,**metric(rep,f'{label}_{hm}M')})
                if label=='SELL_KEEP':
                    for hh in HOLDS:
                        qr=a.cluster_boot_mean(rep,f'R{hh}',SEED+hm*10+hh); qp=a.cluster_boot_mean(rep,f'pct{hh}',SEED+hm*10+500+hh)
                        boot.append({'horizon_min':hm,'hold_h':hh,'EV_R':qr['mean'],'CI_R_lo':qr['lo'],'CI_R_hi':qr['hi'],'P_R_gt0':qr['P_gt0'],
                                     'EV_pct':qp['mean'],'CI_pct_lo':qp['lo'],'CI_pct_hi':qp['hi'],'P_pct_gt0':qp['P_gt0']})
                    rep['year']=pd.to_datetime(rep.early_time).dt.year
                    for y,yg in rep.groupby('year'):
                        yearly.append({'horizon_min':hm,'year':int(y),**metric(yg,f'SELL_KEEP_{hm}M')})
        sel=g[g.sell_keep].copy()
        if len(sel):
            er,ir,p,stats=replay_pair(sel,m1,h1,hm)
            ir.to_csv(OUT/f'replay_immediate_same_keep_{hm}m.csv',index=False); p.to_csv(OUT/f'paired_keep_{hm}m.csv',index=False)
            pairs_all += stats

    cdf=pd.DataFrame(confusion); mdf=pd.DataFrame(group_metrics); bdf=pd.DataFrame(boot); ydf=pd.DataFrame(yearly); pdf=pd.DataFrame(pairs_all)
    cdf.to_csv(OUT/'veto_confusion.csv',index=False); mdf.to_csv(OUT/'group_metrics.csv',index=False); bdf.to_csv(OUT/'sell_keep_bootstrap.csv',index=False); ydf.to_csv(OUT/'yearly_sell_keep.csv',index=False); pdf.to_csv(OUT/'paired_delayed_vs_immediate.csv',index=False)

    # Resolution-type diagnostic for PRIMARY only, still future-label diagnostic.
    pg=feat[feat.horizon_min==PRIMARY].copy()
    resdiag=pg.groupby(['future_resolution','buyer_regain_veto']).agg(N=('correction_id','size'),mean_bull_eff=('bullish_efficiency','mean'),mean_accept_above=('acceptance_above','mean')).reset_index()
    resdiag.to_csv(OUT/'primary_resolution_diagnostic.csv',index=False)

    report=['# SELL_CORE_009 — BUYER_REGAIN_FALSE_POSITIVE_REJECTION','',
            '**Preregistered after 008; same-history confirmation, not independent OOS. Primary horizon = 60m.**','',
            '## Veto confusion / future-label diagnostic','',cdf.to_markdown(index=False),'',
            '## Trading metrics by group','',mdf.to_markdown(index=False),'',
            '## SELL_KEEP cluster bootstrap','',bdf.to_markdown(index=False),'',
            '## Paired delayed vs immediate on same kept events','',pdf.to_markdown(index=False),'',
            '## Yearly SELL_KEEP','',ydf.to_markdown(index=False),'',
            '## Primary 60m resolution diagnostic','',resdiag.to_markdown(index=False),'',
            '## Frozen verdict rule','',
            'Primary 60m is credible only if buyer-regain veto rejects materially more future non-break losers than winners, SELL_KEEP is positive in both R and price space at 48h, the result is not carried by one year, and delaying to 60m does not materially destroy value versus immediate entry on the same kept events.']
    (OUT/'REPORT.md').write_text('\n'.join(report)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
