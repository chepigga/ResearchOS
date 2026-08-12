#!/usr/bin/env python3
import json
from pathlib import Path
import pandas as pd
import u02c2_v283_market_clock_conditional as m


def main():
    sh=pd.read_csv(m.SHADOW); sh['time']=pd.to_datetime(sh.time)
    sh=sh[(sh.time>=m.START)&(sh.action!='WAIT')&(sh.pass_stateless==1)].copy()
    m5=m.load_zip(m.M5ZIP); h4=m.h4_supertrend(m5)
    sh=m.attach_clock(sh,h4).dropna(subset=['st_age','st_dir']).copy(); sh['market_state']=sh.apply(m.state_label,axis=1)
    ep=m.episode_first(sh); ep['market_state']=ep.apply(m.state_label,axis=1)
    m1=m.load_zip(m.M1ZIP); h1=m.h1_atr_from_m1(m1)
    data_end=min(m1.time.max(),sh.time.max()+pd.Timedelta(hours=48)); m.ANALYSIS_WEEKS=(data_end-m.START).total_seconds()/(7*86400)
    poll=m.add_outcomes(sh,m1,h1); eps=m.add_outcomes(ep,m1,h1)
    poll.to_csv(m.OUT/'historical_shadow_passed_polls.csv',index=False); eps.to_csv(m.OUT/'historical_shadow_episode_first.csv',index=False)
    pm=m.metrics(poll,'RAW_POLL_DIAGNOSTIC'); em=m.metrics(eps,'EPISODE_FIRST_PRIMARY')
    pd.concat([em,pm],ignore_index=True).to_csv(m.OUT/'state_matrix_detailed.csv',index=False)
    agg=m.aggregate_other(eps); agg.to_csv(m.OUT/'state_matrix_primary_5way.csv',index=False)
    yr=m.yearly_metrics(eps); yr.to_csv(m.OUT/'yearly_state_matrix.csv',index=False)
    tag=[]
    for (side,state,t),g in eps.groupby(['action','market_state','tag']):
        tag.append({'side':side,'state':state,'tag':t,'N':len(g),'EV24h_R':g.real24h_R.mean(),'PF24h':m.pf(g.real24h_R),'WR24h':(g.real24h_R>0).mean()})
    pd.DataFrame(tag).to_csv(m.OUT/'tag_x_state_matrix.csv',index=False)
    exact=m.exact_aug_sanity()
    if len(exact): exact.to_csv(m.OUT/'exact_aug_exec_state_sanity.csv',index=False)
    stab=[]
    for (side,state),g in yr.groupby(['side','state']):
        valid=g[g.N>=5]; stab.append({'side':side,'state':state,'years_N5':len(valid),'positive_years_N5':int((valid.EV24h_R>0).sum()),'years_total':len(g)})
    stab=pd.DataFrame(stab); stab.to_csv(m.OUT/'year_stability.csv',index=False)
    counts={f'{a}|{s}':int(n) for (a,s),n in eps.groupby(['action','market_state']).size().items()}
    summary={'mode':'HISTORICAL_V283_DEFAULT_STATELESS_SHADOW_NOT_MT5_PARITY','transition_prereg':'H4_ST_AGE 0..2, outcome-blind','clock':'H4 Supertrend ATR10 x3; U05 BAR_OPEN lag1 parity convention','population_raw_passed_polls':len(poll),'population_episode_first':len(eps),'analysis_weeks':m.ANALYSIS_WEEKS,'state_counts_episode':counts,'limitations':['historical replay is opportunity-level shadow, not exact MT5 trade lifecycle','v283 default liquidity filter=false makes SmartMock A/D unreachable; Priority E is disabled, so reachable default SmartMock families here are B/C','stateful delivery-memory gates, open-position suppression and cooldown lifecycle are excluded','raw polls are correlated and diagnostic; episode-first is primary']}
    (m.OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    rep=['# BTC V283 MARKET-CLOCK CONDITIONAL LAB U02C2','',
         '**Status:** historical conditional default-v283 stateless SHADOW diagnostic — not exact MT5 lifecycle parity.','',
         '## Preregistered market-clock states','',
         '- TRANSITION: H4 Supertrend age 0–2 (first ~12h after flip).','- TIER_A: BUY, H4 age >58, trade-coordinate relation −1.','- TIER_B: BUY, H4 age >58, relation +1.','- SELL_B3: SELL, H4 age 27–50.','- OTHER_B1: remaining age 3–11.','- OTHER_B2: remaining age 12–27.','- OTHER_B3: remaining age 28–58.','- OTHER_B4: remaining age >58.','',
         'Primary unit is episode-first opportunity; repeated raw M5 polls are diagnostic only. Common outcome: 1.5×H1 ATR stop, TP=1.5R, otherwise time exit; $27.5/BTC cost proxy.','',
         '## Primary 5-way matrix','',agg.to_markdown(index=False),'','## Detailed matrix','',em.to_markdown(index=False),'','## Year stability (N>=5/cell/year)','',stab.to_markdown(index=False),'','## Caveat','',
         'Default v283 has liquidity filter OFF and Priority E OFF, so A/D/E SmartMock paths are not active. The remaining historical non-parity is mainly stateful delivery-memory, open-position/cooldown lifecycle and MT5 execution differences. Exact August MT5 executions are kept as a separate sanity panel.']
    (m.OUT/'REPORT.md').write_text('\n'.join(rep))
    print('PRIMARY 5-WAY\n',agg.to_string(index=False)); print('\nDETAILED\n',em.to_string(index=False)); print('\nSTABILITY\n',stab.to_string(index=False)); print('\nEXACT AUG\n',exact.to_string(index=False) if len(exact) else 'NONE'); print('\nSUMMARY\n',json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
