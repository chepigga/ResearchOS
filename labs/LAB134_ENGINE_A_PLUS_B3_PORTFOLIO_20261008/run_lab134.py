#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
A_SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
B_SRC=ROOT/"labs/LAB133_B3_DEPTH050_DECAY_ANATOMY_20261008/run_lab133.py"

def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

A=loadmod("lab124",A_SRC)
B=loadmod("lab133",B_SRC)

OUT=Path("lab134_out"); OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
RISK_PCT=0.25

# ---------- freeze candidate sets ----------
a_ev=A.df[(A.df['split']=='TRAIN') & (A.df.phase.isin(['CONT','REACCEL']))].copy()
b_bal=B.df[B.df.decay_slope>0].copy()
b_high=B.df[B.df.terminal_two_step].copy()

# ---------- per-event standalone execution ----------
def sim_a(r,cost):
    ei=int(r.entry_i); side=int(r.side); atr=float(r.atr)
    net,reason,xi=A.sim_one(ei,side,atr,cost)
    return dict(engine='A',entry_time=A.BT.iloc[ei],exit_time=A.BT.iloc[xi],
                signal_time=r.signal_time,side=side,atr=atr,entry=float(A.BO[ei]),
                net_r=float(net),reason=reason,xi=xi)

def sim_b(r,cost,label):
    ei=int(r.entry_i); side=int(r.side); atr=float(r.atr)
    net,reason,xi=B.sim_one(ei,side,atr,cost)
    return dict(engine=label,entry_time=B.m.BT.iloc[ei],exit_time=B.m.BT.iloc[xi],
                signal_time=r.signal_time,side=side,atr=atr,entry=float(B.m.BO[ei]),
                net_r=float(net),reason=reason,xi=xi)

def make_events(cost):
    rows=[]
    for _,r in a_ev.iterrows(): rows.append(sim_a(r,cost))
    for _,r in b_bal.iterrows(): rows.append(sim_b(r,cost,'B3_BAL'))
    for _,r in b_high.iterrows(): rows.append(sim_b(r,cost,'B3_HIGH'))
    return pd.DataFrame(rows).sort_values('entry_time').reset_index(drop=True)

# ---------- overlap diagnostics ----------
def nearest_hours(ref_times, t):
    if not len(ref_times): return np.inf
    arr=pd.to_datetime(ref_times,utc=True).astype('int64').to_numpy()
    x=pd.Timestamp(t)
    if x.tzinfo is None:x=x.tz_localize('UTC')
    else:x=x.tz_convert('UTC')
    xv=int(x.value);k=np.searchsorted(arr,xv);ds=[]
    if k<len(arr):ds.append(abs(arr[k]-xv)/3.6e12)
    if k>0:ds.append(abs(arr[k-1]-xv)/3.6e12)
    return min(ds) if ds else np.inf

a_times=pd.to_datetime(a_ev.entry_time,utc=True).sort_values()
ov=[]
for name,d in [('B3_BALANCED',b_bal),('B3_HIGH',b_high)]:
    if d.empty: continue
    z=d.copy()
    z['nearest_A_h']=z.entry_time.map(lambda t:nearest_hours(a_times,t))
    ov.append(dict(engine=name,n=len(z),
                   within_6h=int((z.nearest_A_h<=6).sum()),within_6h_pct=float((z.nearest_A_h<=6).mean()),
                   within_12h=int((z.nearest_A_h<=12).sum()),within_12h_pct=float((z.nearest_A_h<=12).mean()),
                   unique_gt12h=int((z.nearest_A_h>12).sum()),unique_gt12h_pct=float((z.nearest_A_h>12).mean())))
pd.DataFrame(ov).to_csv(OUT/"LAB134_overlap.csv",index=False)

# ---------- one-position portfolio replay ----------
PORTS={
    'A_ONLY':['A'],
    'A_PLUS_B3_BALANCED':['A','B3_BAL'],
    'A_PLUS_B3_HIGH':['A','B3_HIGH'],
    'A_PLUS_B3_BALANCED_WITH_HIGH_TAG':['A','B3_BAL'], # same trade universe; HIGH tag attribution reported separately
}
summary=[]; alltr=[]
for cost in COSTS:
    pool=make_events(cost)
    # exact duplicate B3_HIGH rows are subset of B3_BAL; only portfolios selecting HIGH use those.
    for pname,engines in PORTS.items():
        s=pool[pool.engine.isin(engines)].copy()
        # At exact same entry timestamp, prefer A over B3; this is frozen and avoids double-counting.
        pri={'A':0,'B3_HIGH':1,'B3_BAL':2}
        s['pri']=s.engine.map(pri)
        s=s.sort_values(['entry_time','pri'])
        open_until=pd.Timestamp.min.tz_localize('UTC')
        rows=[]; skipped=0
        for _,r in s.iterrows():
            if r.entry_time<open_until:
                skipped+=1; continue
            open_until=r.exit_time
            rr=r.to_dict()
            rr['portfolio']=pname;rr['cost_bps']=cost;rr['risk_pct']=RISK_PCT;rr['pnl_pct']=r.net_r*RISK_PCT
            rr['is_high_tag']=False
            # tag B3 balanced trades that are also in frozen HIGH subset by nearest exact entry time
            if r.engine=='B3_BAL':
                rr['is_high_tag']=bool((pd.to_datetime(b_high.entry_time,utc=True)==pd.Timestamp(r.entry_time)).any())
            rows.append(rr)
        t=pd.DataFrame(rows)
        if t.empty:continue
        alltr.append(t)
        pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
        months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
        ce=t.net_r.cumsum();ddr=float((ce.cummax()-ce).max())
        cep=t.pnl_pct.cumsum();ddp=float((cep.cummax()-cep).max())
        counts=t.engine.value_counts().to_dict()
        summary.append(dict(portfolio=pname,cost_bps=cost,n=len(t),trades_month=len(t)/months,
                            ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                            wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),
                            r_month=float(t.net_r.sum()/months),total_pct=float(t.pnl_pct.sum()),
                            pct_month=float(t.pnl_pct.sum()/months),
                            realized_dd_r=ddr,realized_dd_pct=ddp,skipped_due_open=skipped,
                            n_A=int(counts.get('A',0)),n_B3_BAL=int(counts.get('B3_BAL',0)),
                            n_B3_HIGH=int(counts.get('B3_HIGH',0)),
                            n_high_tag=int(t.is_high_tag.sum())))
sm=pd.DataFrame(summary);sm.to_csv(OUT/"LAB134_portfolio_summary.csv",index=False)
if alltr:pd.concat(alltr,ignore_index=True).to_csv(OUT/"LAB134_portfolio_trades.csv",index=False)

# Incremental effect vs A-only.
inc=[]
for cost in COSTS:
    a=sm[(sm.cost_bps==cost)&(sm.portfolio=='A_ONLY')].iloc[0]
    for pname in ['A_PLUS_B3_BALANCED','A_PLUS_B3_HIGH']:
        q=sm[(sm.cost_bps==cost)&(sm.portfolio==pname)].iloc[0]
        inc.append(dict(cost_bps=cost,portfolio=pname,
                        delta_n=int(q.n-a.n),delta_trades_month=float(q.trades_month-a.trades_month),
                        delta_total_r=float(q.total_r-a.total_r),delta_r_month=float(q.r_month-a.r_month),
                        delta_ev=float(q.ev-a.ev),delta_pf=float(q.pf-a.pf),
                        delta_dd_r=float(q.realized_dd_r-a.realized_dd_r),
                        delta_dd_pct=float(q.realized_dd_pct-a.realized_dd_pct)))
pd.DataFrame(inc).to_csv(OUT/"LAB134_increment_vs_A.csv",index=False)

# High-tag attribution inside A+B3_BALANCED.
tag=[]
for cost in COSTS:
    t=pd.concat(alltr,ignore_index=True)
    t=t[(t.cost_bps==cost)&(t.portfolio=='A_PLUS_B3_BALANCED')]
    for grp,qq in [('A',t[t.engine=='A']),('B3_BAL_NONHIGH',t[(t.engine=='B3_BAL')&(~t.is_high_tag)]),('B3_HIGH_TAG',t[(t.engine=='B3_BAL')&(t.is_high_tag)])]:
        if qq.empty:continue
        pos=qq.loc[qq.net_r>0,'net_r'].sum();neg=-qq.loc[qq.net_r<0,'net_r'].sum()
        tag.append(dict(cost_bps=cost,group=grp,n=len(qq),ev=float(qq.net_r.mean()),
                        pf=float(pos/neg) if neg>0 else np.inf,total_r=float(qq.net_r.sum())))
pd.DataFrame(tag).to_csv(OUT/"LAB134_component_attribution.csv",index=False)

lines=['# LAB134 — ENGINE A + FROZEN B3 PORTFOLIO','',
       'Protocol: BTC TRAIN only. B3 definitions are frozen from LAB133 before this portfolio test.',
       'Engine A is unchanged: CORE_CONT + REACCEL.',
       'B3_BALANCED = 0.50 H1ATR attack + positive slope of five 0.1ATR milestone durations.',
       'B3_HIGH = 0.50 H1ATR attack + d04>d03 and d05>d04.',
       'All legs use their frozen SL1 H1ATR / TP3R / max48h execution. Fixed risk for portfolio comparison = 0.25% per accepted trade.',
       'Portfolio chronology is one-position-only. Exact same-time collisions prefer Engine A.','',
       '## Overlap with Engine A']
for r in ov:
    lines.append(f"- {r['engine']}: raw N={r['n']}; within ±6h A={r['within_6h']} ({r['within_6h_pct']:.1%}); within ±12h={r['within_12h']} ({r['within_12h_pct']:.1%}); unique >12h={r['unique_gt12h']} ({r['unique_gt12h_pct']:.1%})")
for cost in COSTS:
    lines += ['',f'## Portfolio @ {cost:.2f}bps']
    for pname in ['A_ONLY','A_PLUS_B3_BALANCED','A_PLUS_B3_HIGH']:
        q=sm[(sm.cost_bps==cost)&(sm.portfolio==pname)]
        if len(q):
            r=q.iloc[0]
            lines.append(f"- {pname}: N={int(r.n)} ({r.trades_month:.2f}/mo), A={int(r.n_A)}, B3bal={int(r.n_B3_BAL)}, B3high={int(r.n_B3_HIGH)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, pnl/mo={r.pct_month:+.3f}%, DD={r.realized_dd_r:.1f}R / {r.realized_dd_pct:.2f}%")
    lines.append('  Increment vs A:')
    for _,r in pd.DataFrame(inc)[pd.DataFrame(inc).cost_bps==cost].iterrows():
        lines.append(f"  - {r.portfolio}: +{int(r.delta_n)} trades, {r.delta_trades_month:+.2f}/mo, {r.delta_r_month:+.2f} R/mo, PF delta {r.delta_pf:+.2f}, DD delta {r.delta_dd_pct:+.2f}%")
lines += ['', '## Decision',
          'Promote B3 into the CrowdFade portfolio baseline only if it adds genuinely incremental trades and improves or acceptably preserves PF/DD at both normal and stress cost.',
          'Do not alter Engine A logic based on this portfolio test.']
(OUT/"LAB134_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB134_meta.json").write_text(json.dumps(dict(
    protocol='BTC TRAIN only',
    risk_pct=RISK_PCT,
    engineA='CORE_CONT + REACCEL unchanged',
    B3_BALANCED='depth0.50 + decay_slope>0',
    B3_HIGH='depth0.50 + d04>d03 and d05>d04',
    chronology='one position; A priority on exact same entry time',
    costs=COSTS,
    caveat='portfolio composition test only; no BTC OOS used'
),indent=2))
print("\n".join(lines))
