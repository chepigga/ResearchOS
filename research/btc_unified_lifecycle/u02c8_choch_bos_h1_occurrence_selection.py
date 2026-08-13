#!/usr/bin/env python3
"""U02C8 — H1 CHoCH + BOS H1 OCCURRENCE COMPONENT ABLATION.

Frozen question: after U02C7 showed pure H1 CHoCH is necessary-ish but insufficient,
does adding only the H1 BOS condition recover the successful U02C6B v283-occurrence
B3 selector?

Population / controls / execution are kept identical to U02C7/U02C6B:
- B3 BUY = canonical H4 ST age 28..58.
- selector occurrence = bullish H1 CHoCH AND bullish H1 BOS on the same completed H1 bar.
- no PRE, AI, LateEntry, D1 veto, knife/panic, micro-break, FVG/OB, delivery memory.
- causal entry = first fixed H4 clock strictly after selector occurrence.
- causal risk-set control = same year, same B3 delay, still-active B3 episode with
  no CHoCH+BOS occurrence known yet; future occurrence allowed.
- matched on comparison-time RV168_control + ATR%.
- K1 and K5 estimators.
- exit = SL 1.5x completed H1 ATR14, no TP, 48h time exit, $27.5/BTC.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import u02c2_fast_v283_shadow as fast
import u02c5_periodic_state_entry_ablation as u5
import u02c6_b3_v283_occurrence_selection as a
import u02c7_pure_choch_occurrence_selection as u7

OUT=Path('u02c8_out'); OUT.mkdir(exist_ok=True)


def build_events(m1):
    h1=a.h1_controls(m1)
    av=h1.atr14.to_numpy(float)
    choch=fast.precompute_choch(h1,av)
    bos,_,_=fast.precompute_bos(h1,60)
    pure=pd.DatetimeIndex(h1.loc[choch==1,'close_time']).sort_values()
    combo=pd.DatetimeIndex(h1.loc[(choch==1)&(bos==1),'close_time']).sort_values()
    return h1,pure,combo


def v283_episode_flag(eps):
    sh=pd.read_csv(a.SHADOW); sh['time']=pd.to_datetime(sh.time)
    sh=sh[(sh.action=='BUY')&(sh.pass_stateless==1)].sort_values('time')
    st=sh.time.to_numpy('datetime64[ns]')
    vals=[]
    for e in eps.itertuples(index=False):
        aa=np.searchsorted(st,np.datetime64(e.start),'left')
        bb=np.searchsorted(st,np.datetime64(e.end),'left')
        vals.append(int(bb>aa))
    return np.asarray(vals,int)


def episode_overlap(eps,pure_times,combo_times):
    pure=u7.mark_selector(eps,pure_times,'H1_CHOCH')
    combo=u7.mark_selector(eps,combo_times,'H1_CHOCH_BOS')
    v=v283_episode_flag(eps)
    p=pure.occurs.to_numpy(int); c=combo.occurs.to_numpy(int)
    rows=[]
    for name,x in [('H1_CHOCH',p),('H1_CHOCH_BOS',c)]:
        inter=int(((x==1)&(v==1)).sum()); union=int(((x==1)|(v==1)).sum())
        rows.append({'selector':name,'selector_episodes':int(x.sum()),'v283_episodes':int(v.sum()),
                     'intersection':inter,'v283_coverage':inter/int(v.sum()) if v.sum() else np.nan,
                     'precision_vs_v283':inter/int(x.sum()) if x.sum() else np.nan,
                     'jaccard':inter/union if union else np.nan,
                     'extra_vs_v283':int(((x==1)&(v==0)).sum()),
                     'missed_v283':int(((x==0)&(v==1)).sum())})
    return pd.DataFrame(rows),pure,combo,v


def main():
    m1=base.load_zip(base.M1ZIP); m5=base.load_zip(base.M5ZIP)
    h1,pure_times,combo_times=build_events(m1)
    clock=u5.build_clock(m5)
    eps=u5.state_episodes(clock); eps=eps[eps.state=='B3_BUY'].copy().reset_index(drop=True)

    overlap,pure_eps,combo_eps,vflag=episode_overlap(eps,pure_times,combo_times)
    combo_eps['v283_occurs']=vflag
    combo_eps.to_csv(OUT/'episodes_choch_bos.csv',index=False)
    overlap.to_csv(OUT/'overlap_precision.csv',index=False)

    treated=u7.causal_entries(combo_eps,m1,h1)
    pairs,controls=u7.riskset_pairs(treated,combo_eps,h1,m1,'H1_CHOCH_BOS')
    summary,yearly,balance=u7.summarize('H1_CHOCH_BOS',treated,pairs,controls)
    treated.to_csv(OUT/'treated.csv',index=False)
    pairs.to_csv(OUT/'pairs.csv',index=False)
    controls.to_csv(OUT/'controls.csv',index=False)
    summary.to_csv(OUT/'summary.csv',index=False)
    yearly.to_csv(OUT/'yearly.csv',index=False)
    balance.to_csv(OUT/'balance.csv',index=False)

    # Outcome diagnostics for the component-selection geometry itself.
    # Split pure H1 CHoCH episodes into combo accepted/rejected and v283 accepted/rejected.
    panel=pure_eps[['episode_id','start','end','duration_h','occurs','first_occurrence']].copy()
    panel=panel.rename(columns={'occurs':'pure_choch_occurs','first_occurrence':'pure_first'})
    csmall=combo_eps[['episode_id','occurs','first_occurrence']].rename(columns={'occurs':'combo_occurs','first_occurrence':'combo_first'})
    panel=panel.merge(csmall,on='episode_id',how='left')
    panel['v283_occurs']=vflag
    panel.to_csv(OUT/'component_episode_panel.csv',index=False)

    # Accepted references from U02C7 and U02C6B, fixed values for comparison only.
    bench=pd.DataFrame([
      {'selector':'PURE_H1_CHOCH_U02C7','estimator':'K1','N':67,'treated_EV_R':0.543096,'control_EV_R':0.472959,'delta_R':0.070137,'CI_lo':-0.974493,'CI_hi':1.088849,'P_gt0':0.55310},
      {'selector':'PURE_H1_CHOCH_U02C7','estimator':'K5','N':67,'treated_EV_R':0.543096,'control_EV_R':0.622002,'delta_R':-0.078906,'CI_lo':-0.933396,'CI_hi':0.812089,'P_gt0':0.42535},
      {'selector':'V283_OCCURRENCE_U02C6B','estimator':'K1','N':48,'treated_EV_R':0.917870,'control_EV_R':-0.226739,'delta_R':1.144609,'CI_lo':0.028313,'CI_hi':2.332713,'P_gt0':0.97790},
      {'selector':'V283_OCCURRENCE_U02C6B','estimator':'K5','N':48,'treated_EV_R':0.917870,'control_EV_R':-0.046170,'delta_R':0.964039,'CI_lo':-0.017435,'CI_hi':2.093273,'P_gt0':0.97250},
    ])
    bench.to_csv(OUT/'benchmarks.csv',index=False)

    census=pd.DataFrame([{
      'B3_episodes':len(eps),
      'pure_H1_CHOCH_episodes':int(pure_eps.occurs.sum()),
      'combo_CHOCH_BOS_episodes':int(combo_eps.occurs.sum()),
      'v283_episodes':int(vflag.sum()),
      'combo_causal_entries':len(treated),
      'median_combo_occurrence_delay_h':combo_eps.loc[combo_eps.occurs==1,'occurrence_delay_h'].median()
    }])
    census.to_csv(OUT/'census.csv',index=False)

    rep=['# U02C8 — H1 CHoCH + BOS H1 COMPONENT ABLATION','',
         '**Only new condition versus U02C7 primary:** bullish H1 BOS must be true on the same completed H1 bar as bullish H1 CHoCH. Everything else remains removed.','',
         '## Census','',census.to_markdown(index=False),'','## Precision / overlap','',overlap.to_markdown(index=False),'',
         '## Causal risk-set selector result','',summary.to_markdown(index=False),'','## Yearly','',yearly.to_markdown(index=False),'','## Match balance','',balance.to_markdown(index=False),'',
         '## Benchmarks','',bench.to_markdown(index=False),'','## Decision rule','',
         'CHoCH+BOS is accepted as the minimal replacement candidate only if it materially recovers the U02C6B v283-occurrence excess, improves precision versus pure H1 CHoCH, and does not collapse year stability. Otherwise BOS alone is insufficient and the next component must be isolated separately.']
    (OUT/'REPORT.md').write_text('\n'.join(rep))
    (OUT/'summary.json').write_text(json.dumps({'primary':'H1 bullish CHoCH AND H1 bullish BOS','bos_lookback':60,'choch_pivot_strength':2,'choch_lookback':20,'choch_buffer_h1_atr':0.05,'entry':'next fixed H4 clock after occurrence','control':'same-year same-B3-age causal risk set matched RV168+ATR%','exit':'SL1.5 H1 ATR or 48h, no TP'},indent=2))
    print('CENSUS\n',census.to_string(index=False));print('\nOVERLAP\n',overlap.to_string(index=False));print('\nSUMMARY\n',summary.to_string(index=False));print('\nYEARLY\n',yearly.to_string(index=False));print('\nBALANCE\n',balance.to_string(index=False));print('\nBENCH\n',bench.to_string(index=False))

if __name__=='__main__': main()
