#!/usr/bin/env python3
"""U02C10 — MINIMAL B3 SELECTOR.

Primary hypothesis frozen before outcome inspection:
    B3 BUY + bullish H1 CHoCH + HTF bias BUY + score-free LateEntry pass.

Primary LateEntry geometry is deliberately PRE/score-free:
    BUY distance to H1 EMA50 <= 1.5 * completed H1 ATR14.

Sensitivity only:
    original U02C9/v283 late geometry (1.35 ATR when breakoutProbe else 1.5 ATR),
    with PRE>=60 eligibility removed. This sensitivity may still use the legacy score
    internally to classify breakoutProbe, so it is NOT the primary minimal rule.

Everything else is frozen from U02C6B/U02C7:
- canonical B3 BUY episodes (H4 ST age 28..58)
- causal occurrence selector; one BUY on first fixed H4 clock strictly after occurrence
- causal same-year/same-B3-age risk-set controls; controls may get occurrence later
- matching on comparison-time RV168 + ATR%
- SL=1.5*completed H1 ATR14, no TP, 48h time exit, $27.5/BTC cost proxy
- K1/K5 paired episode bootstrap
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import u02c5_periodic_state_entry_ablation as u5
import u02c6_b3_v283_occurrence_selection as a
import u02c7_pure_choch_occurrence_selection as c7
import u02c9_ordered_component_ladder as c9

OUT=Path('u02c10_out'); OUT.mkdir(exist_ok=True)


def selector_times(panel, mask):
    return pd.DatetimeIndex(panel.loc[mask,'time']).sort_values()


def v283_episode_flags(eps):
    sh=pd.read_csv(a.SHADOW); sh['time']=pd.to_datetime(sh.time)
    sh=sh[(sh.action=='BUY')&(sh.pass_stateless==1)].sort_values('time')
    st=sh.time.to_numpy('datetime64[ns]'); vals=[]
    for e in eps.itertuples(index=False):
        aa=np.searchsorted(st,np.datetime64(e.start),'left'); bb=np.searchsorted(st,np.datetime64(e.end),'left')
        vals.append(int(bb>aa))
    return pd.Series(vals,index=eps.index)


def run_selector(name,times,eps,m1,h1):
    ex=c7.mark_selector(eps,times,name)
    tr=c7.causal_entries(ex,m1,h1)
    p,rs=c7.riskset_pairs(tr,ex,h1,m1,name)
    s,y,b=c7.summarize(name,tr,p,rs)
    return ex,tr,p,rs,s,y,b


def overlap_row(name,ex):
    occ=int(ex.occurs.sum()); v=int(ex.v283_occurs.sum())
    inter=int(((ex.occurs==1)&(ex.v283_occurs==1)).sum())
    union=int(((ex.occurs==1)|(ex.v283_occurs==1)).sum())
    return {'selector':name,'selector_episodes':occ,'v283_episodes':v,'intersection':inter,
            'v283_coverage':inter/v if v else np.nan,'precision_vs_v283':inter/occ if occ else np.nan,
            'extra_vs_v283':occ-inter,'missed_v283':v-inter,'jaccard':inter/union if union else np.nan}


def main():
    m1=base.load_zip(base.M1ZIP); m5_clock=base.load_zip(base.M5ZIP)
    panel,_=c9.build_panel(m1)
    # Primary is truly PRE/score-free: only H1 CHoCH (panel population), HTF BUY, dist<=1.5 ATR.
    panel['minimal_late_pass']=((panel['dist']<=1.5)).astype(int)
    panel.to_csv(OUT/'minimal_component_panel.csv',index=False)

    h1=a.h1_controls(m1)
    clock=u5.build_clock(m5_clock); eps=u5.state_episodes(clock)
    eps=eps[eps.state=='B3_BUY'].copy().reset_index(drop=True)
    eps['v283_occurs']=v283_episode_flags(eps)

    specs=[
      ('MINIMAL_SCORE_FREE', selector_times(panel,(panel.htf_buy==1)&(panel.minimal_late_pass==1))),
      ('LEGACY_LATE_SENSITIVITY', selector_times(panel,(panel.htf_buy==1)&(panel.late_pass==1))),
    ]
    sums=[]; yrs=[]; bals=[]; ovs=[]
    for name,times in specs:
        ex,tr,p,rs,s,y,b=run_selector(name,times,eps,m1,h1)
        if len(s): sums.append(s)
        if len(y): yrs.append(y)
        if len(b): bals.append(b)
        ovs.append(overlap_row(name,ex))
        ex.to_csv(OUT/f'episodes_{name}.csv',index=False)
        tr.to_csv(OUT/f'treated_{name}.csv',index=False)
        p.to_csv(OUT/f'pairs_{name}.csv',index=False)
        rs.to_csv(OUT/f'controls_{name}.csv',index=False)

    sm=pd.concat(sums,ignore_index=True); yr=pd.concat(yrs,ignore_index=True); bal=pd.concat(bals,ignore_index=True); ov=pd.DataFrame(ovs)
    sm.to_csv(OUT/'summary.csv',index=False);yr.to_csv(OUT/'yearly.csv',index=False);bal.to_csv(OUT/'balance.csv',index=False);ov.to_csv(OUT/'overlap_precision.csv',index=False)

    bench=pd.DataFrame([
      {'selector':'V283_U02C6B','estimator':'K1','N':48,'treated_EV_R':0.91787,'control_EV_R':-0.226739,'delta_R':1.144609,'CI_lo':0.028313,'CI_hi':2.332713,'P_gt0':0.9779},
      {'selector':'U02C9_LADDER_THROUGH_LATE','estimator':'K1','N':48,'treated_EV_R':0.844698,'control_EV_R':-0.226320,'delta_R':1.071017,'CI_lo':-0.029732,'CI_hi':2.264987,'P_gt0':0.9708},
    ])
    bench.to_csv(OUT/'benchmarks.csv',index=False)
    k1=sm[sm.estimator=='K1'].merge(ov,on='selector',how='left')
    report=['# U02C10 — MINIMAL B3 SELECTOR','',
      '**Primary:** B3 BUY + bullish H1 CHoCH + HTF BUY + `dist_to_H1_EMA50 <= 1.5 H1 ATR`. No PRE threshold and no PRE score in the primary geometry.','',
      '**Sensitivity:** same but legacy v283 LateEntry geometry; this is diagnostic only.','',
      '## K1 primary result','',k1.to_markdown(index=False),'','## K1/K5 full summary','',sm.to_markdown(index=False),'','## Yearly','',yr.to_markdown(index=False),'','## Match balance','',bal.to_markdown(index=False),'','## Overlap with v283','',ov.to_markdown(index=False),'','## Benchmarks','',bench.to_markdown(index=False),'','## Frozen decision rule','',
      'Freeze the minimal B3 selector only if the score-free primary materially preserves the U02C6B/U02C9 excess, remains positive across 2024/2025/2026, and does not lose materially more v283 coverage than the legacy late-geometry sensitivity.']
    (OUT/'REPORT.md').write_text('\n'.join(report))
    (OUT/'summary.json').write_text(json.dumps({'primary':'H1 CHoCH + HTF BUY + dist<=1.5 H1 ATR','pre_score_used_in_primary':False,'exit':'SL 1.5 H1 ATR; no TP; 48h'},indent=2))
    print(k1.to_string(index=False));print('\nYEARLY\n',yr.to_string(index=False));print('\nOVERLAP\n',ov.to_string(index=False))

if __name__=='__main__': main()
