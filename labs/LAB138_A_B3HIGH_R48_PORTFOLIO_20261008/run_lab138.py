#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
A_SRC=ROOT/"labs/LAB134_ENGINE_A_PLUS_B3_PORTFOLIO_20261008/run_lab134.py"
R_SRC=ROOT/"labs/LAB137_R48_ACCEPT_ANATOMY_20261008/run_lab137.py"

def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

A=loadmod("lab134",A_SRC)
R=loadmod("lab137",R_SRC)

OUT=Path("lab138_out"); OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
RISK=0.25

# frozen sets
r48_high=R.df[(~R.df.retest) &
              (R.df.mean_margin>=R.thr['mean_margin_q60']) &
              (R.df.oi_change>=R.thr['oi_q60'])].copy()
r48_bal=R.df[(R.df.mean_margin>=R.thr['mean_margin_q60']) &
             (R.df.oi_change>=R.thr['oi_q60'])].copy()

def base_events(cost):
    pool=A.make_events(cost)
    s=pool[pool.engine.isin(['A','B3_HIGH'])].copy()
    pri={'A':0,'B3_HIGH':1}; s['pri']=s.engine.map(pri)
    s=s.sort_values(['entry_time','pri'])
    rows=[]; open_until=pd.Timestamp.min.tz_localize('UTC')
    for _,r in s.iterrows():
        if r.entry_time<open_until: continue
        open_until=r.exit_time
        rows.append(dict(source=r.engine,entry_time=r.entry_time,exit_time=r.exit_time,net_r=float(r.net_r)))
    return pd.DataFrame(rows)

def r48_rows(df,cost,label):
    rows=[]
    for _,r in df.iterrows():
        net,reason,xi=R.sim_one(r,cost)
        rows.append(dict(source=label,entry_time=r.entry_time,exit_time=R.BT.iloc[xi],net_r=float(net),
                         side='BUY' if r.side>0 else 'SELL'))
    return pd.DataFrame(rows)

def portfolio(cost,addon,label):
    base=base_events(cost)
    add=r48_rows(addon,cost,label)
    pool=pd.concat([base,add],ignore_index=True,sort=False)
    pri={'A':0,'B3_HIGH':1,label:2}; pool['pri']=pool.source.map(pri)
    pool=pool.sort_values(['entry_time','pri'])
    rows=[]; open_until=pd.Timestamp.min.tz_localize('UTC')
    for _,r in pool.iterrows():
        if r.entry_time<open_until: continue
        open_until=r.exit_time
        rows.append(r)
    t=pd.DataFrame(rows)
    return t

def stats(t):
    pos=t.loc[t.net_r>0,'net_r'].sum(); neg=-t.loc[t.net_r<0,'net_r'].sum()
    months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
    ce=t.net_r.cumsum(); dd=float((ce.cummax()-ce).max())
    return dict(n=len(t),trades_month=len(t)/months,ev=float(t.net_r.mean()),
                pf=float(pos/neg) if neg>0 else np.inf,total_r=float(t.net_r.sum()),
                r_month=float(t.net_r.sum()/months),dd_r=dd,dd_pct=dd*RISK)

summary=[]; attrib=[]; trades=[]
for cost in COSTS:
    base=base_events(cost)
    sb=stats(base); sb.update(cost_bps=cost,portfolio='A_B3HIGH'); summary.append(sb)
    for name,addon,label in [('R48_HIGH',r48_high,'R48_HIGH'),('R48_BALANCED',r48_bal,'R48_BALANCED')]:
        t=portfolio(cost,addon,label)
        s=stats(t); s.update(cost_bps=cost,portfolio='A_B3HIGH_PLUS_'+name); summary.append(s)
        t=t.copy(); t['cost_bps']=cost; t['portfolio']=name; trades.append(t)
        for src,g in t.groupby('source'):
            q=stats(g)
            attrib.append(dict(cost_bps=cost,portfolio=name,source=src,n=q['n'],ev=q['ev'],pf=q['pf'],total_r=q['total_r']))
sm=pd.DataFrame(summary); sm.to_csv(OUT/'LAB138_portfolio_summary.csv',index=False)
pd.DataFrame(attrib).to_csv(OUT/'LAB138_component_attribution.csv',index=False)
if trades: pd.concat(trades,ignore_index=True).to_csv(OUT/'LAB138_portfolio_trades.csv',index=False)

# incremental vs baseline
inc=[]
for cost in COSTS:
    b=sm[(sm.cost_bps==cost)&(sm.portfolio=='A_B3HIGH')].iloc[0]
    for p in ['A_B3HIGH_PLUS_R48_HIGH','A_B3HIGH_PLUS_R48_BALANCED']:
        q=sm[(sm.cost_bps==cost)&(sm.portfolio==p)].iloc[0]
        inc.append(dict(cost_bps=cost,portfolio=p,
                        delta_n=int(q.n-b.n),delta_trades_month=float(q.trades_month-b.trades_month),
                        delta_ev=float(q.ev-b.ev),delta_pf=float(q.pf-b.pf),
                        delta_r_month=float(q.r_month-b.r_month),
                        delta_dd_pct=float(q.dd_pct-b.dd_pct)))
pd.DataFrame(inc).to_csv(OUT/'LAB138_increment.csv',index=False)

# overlap of raw add-on entry times to baseline accepted trades
base_ref=base_events(2.81)
bt=pd.to_datetime(base_ref.entry_time,utc=True).astype('int64').to_numpy()
def nearh(t):
    x=int(pd.Timestamp(t).value); k=np.searchsorted(bt,x); ds=[]
    if k<len(bt): ds.append(abs(bt[k]-x)/3.6e12)
    if k>0: ds.append(abs(bt[k-1]-x)/3.6e12)
    return min(ds) if ds else np.inf
ovs=[]
for name,d in [('R48_HIGH',r48_high),('R48_BALANCED',r48_bal)]:
    z=d.copy(); z['h']=z.entry_time.map(nearh)
    ovs.append(dict(name=name,n=len(z),overlap6=float((z.h<=6).mean()),overlap12=float((z.h<=12).mean()),
                    unique12=float((z.h>12).mean())))
pd.DataFrame(ovs).to_csv(OUT/'LAB138_overlap.csv',index=False)

lines=['# LAB138 — A + B3_HIGH + R48 PORTFOLIO TEST','',
       'BTC TRAIN only. All definitions frozen before this portfolio test.',
       'Baseline = Engine A + B3_HIGH.',
       'R48_HIGH = CLEAN_ACCEPT_OI.',
       'R48_BALANCED = ACCEPT_OI.',
       'One-position chronology. Priority on exact collision: A > B3_HIGH > R48. Risk scale 0.25% per accepted trade.','',
       '## Overlap']
for o in ovs:
    lines.append(f"- {o['name']}: raw N={o['n']}, overlap<=6h={o['overlap6']:.1%}, overlap<=12h={o['overlap12']:.1%}, unique>12h={o['unique12']:.1%}")
for cost in COSTS:
    lines += ['',f'## {cost:.2f}bps']
    for p in ['A_B3HIGH','A_B3HIGH_PLUS_R48_HIGH','A_B3HIGH_PLUS_R48_BALANCED']:
        r=sm[(sm.cost_bps==cost)&(sm.portfolio==p)].iloc[0]
        lines.append(f"- {p}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R / {r.dd_pct:.2f}%")
    lines.append('  Increment:')
    ii=pd.DataFrame(inc); ii=ii[ii.cost_bps==cost]
    for _,r in ii.iterrows():
        lines.append(f"  - {r.portfolio}: +{int(r.delta_n)} trades, {r.delta_trades_month:+.2f}/mo, PF {r.delta_pf:+.2f}, EV {r.delta_ev:+.3f}R, R/mo {r.delta_r_month:+.2f}, DD {r.delta_dd_pct:+.2f}%")
lines += ['','## Decision rule',
          'Promote R48 only if it materially raises unique trade frequency while keeping portfolio PF >=1.5 at 2.81bps and >=1.4 at 7.5bps, with DD remaining compatible with prop risk.',
          'No threshold changes are allowed in this LAB.']
(OUT/'LAB138_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB138_meta.json').write_text(json.dumps(dict(protocol='BTC TRAIN only',risk_pct=RISK,
    baseline='Engine A + B3_HIGH',r48_high='CLEAN_ACCEPT_OI',r48_balanced='ACCEPT_OI',
    caveat='portfolio test only; no BTC OOS'),indent=2))
print('\n'.join(lines))
