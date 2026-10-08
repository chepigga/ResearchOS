#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB134_ENGINE_A_PLUS_B3_PORTFOLIO_20261008/run_lab134.py"
spec=importlib.util.spec_from_file_location("lab134",SRC)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OUT=Path("lab135_out"); OUT.mkdir(exist_ok=True)
RISK=0.25
COSTS=[2.81,7.5]

# Rebuild only the frozen A+B3_HIGH portfolio from LAB134 with the same chronology.
def frozen_portfolio(cost):
    pool=m.make_events(cost)
    s=pool[pool.engine.isin(['A','B3_HIGH'])].copy()
    pri={'A':0,'B3_HIGH':1}
    s['pri']=s.engine.map(pri)
    s=s.sort_values(['entry_time','pri'])
    open_until=pd.Timestamp.min.tz_localize('UTC')
    rows=[]
    for _,r in s.iterrows():
        if r.entry_time<open_until: continue
        open_until=r.exit_time
        rows.append(dict(engine=r.engine,signal_time=r.signal_time,entry_time=r.entry_time,exit_time=r.exit_time,
                         side=r.side,net_r=float(r.net_r),reason=r.reason))
    t=pd.DataFrame(rows)
    t['year']=pd.to_datetime(t.entry_time,utc=True).dt.year
    t['pnl_pct']=t.net_r*RISK
    return t

def stats(t):
    if t.empty:return dict(n=0,ev=np.nan,pf=np.nan,wr=np.nan,total_r=0,maxdd_r=np.nan,maxdd_pct=np.nan,max_losing_streak=0)
    pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
    ce=t.net_r.cumsum();dd=(ce.cummax()-ce)
    cp=t.pnl_pct.cumsum();ddp=(cp.cummax()-cp)
    streak=mx=0
    for x in t.net_r:
        if x<0: streak+=1; mx=max(mx,streak)
        else: streak=0
    return dict(n=len(t),ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),
                maxdd_r=float(dd.max()),maxdd_pct=float(ddp.max()),max_losing_streak=int(mx))

summary=[]; yearly=[]; rolling=[]
for cost in COSTS:
    t=frozen_portfolio(cost)
    t.to_csv(OUT/f"LAB135_trades_{str(cost).replace('.','p')}bps.csv",index=False)
    s=stats(t); months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
    s.update(cost_bps=cost,trades_month=len(t)/months,r_month=t.net_r.sum()/months,pct_month=t.pnl_pct.sum()/months)
    summary.append(s)
    for y,g in t.groupby('year'):
        q=stats(g); q.update(cost_bps=cost,year=int(y)); yearly.append(q)
    # fixed chronological halves
    med=t.entry_time.sort_values().iloc[len(t)//2]
    for label,g in [('H1_CHRON',t[t.entry_time<=med]),('H2_CHRON',t[t.entry_time>med])]:
        q=stats(g);q.update(cost_bps=cost,segment=label,start=str(g.entry_time.min()),end=str(g.entry_time.max()))
        rolling.append(q)

# rolling 30-trade windows to inspect local fragility
rw=[]
for cost in COSTS:
    t=frozen_portfolio(cost).reset_index(drop=True)
    w=30
    for i in range(0,max(len(t)-w+1,0)):
        g=t.iloc[i:i+w]
        q=stats(g)
        rw.append(dict(cost_bps=cost,start_idx=i,end_idx=i+w-1,start=str(g.entry_time.iloc[0]),end=str(g.entry_time.iloc[-1]),
                       n=q['n'],ev=q['ev'],pf=q['pf'],total_r=q['total_r']))
pd.DataFrame(summary).to_csv(OUT/"LAB135_summary.csv",index=False)
pd.DataFrame(yearly).to_csv(OUT/"LAB135_yearly.csv",index=False)
pd.DataFrame(rolling).to_csv(OUT/"LAB135_chron_halves.csv",index=False)
pd.DataFrame(rw).to_csv(OUT/"LAB135_rolling30.csv",index=False)

# deterministic block bootstrap over trade sequence (stationary-ish blocks of 8 trades)
boot=[]
rng=np.random.default_rng(135)
for cost in COSTS:
    t=frozen_portfolio(cost).reset_index(drop=True)
    n=len(t); block=8
    arr=t.net_r.to_numpy(float)
    for k in range(2000):
        sample=[]
        while len(sample)<n:
            st=int(rng.integers(0,max(n-block+1,1)))
            sample.extend(arr[st:st+block].tolist())
        a=np.asarray(sample[:n],float)
        pos=a[a>0].sum();neg=-a[a<0].sum()
        ce=np.cumsum(a);dd=np.max(np.maximum.accumulate(ce)-ce)
        boot.append(dict(cost_bps=cost,total_r=float(a.sum()),ev=float(a.mean()),
                         pf=float(pos/neg) if neg>0 else np.inf,maxdd_r=float(dd)))
bd=pd.DataFrame(boot);bd.to_csv(OUT/"LAB135_block_bootstrap.csv",index=False)

lines=['# LAB135 — FROZEN ENGINE A + B3_HIGH ROBUSTNESS REPLAY','',
       'Purpose: re-test the already-frozen A+B3_HIGH construction without changing any signal rule.',
       'Important: this is still the same BTC TRAIN history, so it is a robustness audit, NOT independent validation.',
       'Definitions and one-position chronology are inherited unchanged from LAB134. Risk scale = 0.25% per accepted trade.','']

sm=pd.DataFrame(summary)
for cost in COSTS:
    r=sm[sm.cost_bps==cost].iloc[0]
    lines.append(f"## Cost {cost:.2f}bps")
    lines.append(f"- N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, R/mo={r.r_month:+.2f}, DD={r.maxdd_r:.1f}R / {r.maxdd_pct:.2f}%, max losing streak={int(r.max_losing_streak)}")
    yy=pd.DataFrame(yearly);yy=yy[yy.cost_bps==cost]
    for _,q in yy.iterrows():
        lines.append(f"  - {int(q.year)}: N={int(q.n)}, EV={q.ev:+.3f}R, PF={q.pf:.2f}, total={q.total_r:+.2f}R, DD={q.maxdd_r:.1f}R, maxLS={int(q.max_losing_streak)}")
    hh=pd.DataFrame(rolling);hh=hh[hh.cost_bps==cost]
    for _,q in hh.iterrows():
        lines.append(f"  - {q.segment}: N={int(q.n)}, EV={q.ev:+.3f}R, PF={q.pf:.2f}, total={q.total_r:+.2f}R, DD={q.maxdd_r:.1f}R")
    br=bd[bd.cost_bps==cost]
    lines.append(f"  - block-bootstrap 2000x: totalR p05={br.total_r.quantile(.05):+.1f}, median={br.total_r.median():+.1f}, p95={br.total_r.quantile(.95):+.1f}; PF p05={br.pf.quantile(.05):.2f}; DD p95={br.maxdd_r.quantile(.95):.1f}R")
    rr=pd.DataFrame(rw);rr=rr[rr.cost_bps==cost]
    if len(rr):
        lines.append(f"  - rolling30: worst PF={rr.pf.min():.2f}, median PF={rr.pf.median():.2f}, worst EV={rr.ev.min():+.3f}R")
    lines.append('')

lines += ['## Readiness rule',
          'Ready for DEMO EA implementation only if: frozen replay remains positive at 7.5bps, no single year carries the entire result, and robustness does not reveal catastrophic sequence risk.',
          'Not ready for production/funded deployment until live-feed parity (especially g_ratio vs count_long_short_ratio) and broker-specific execution are verified.',
          'Writing the EA must not begin until broker/prop specifications are confirmed, per project protocol.']
(OUT/"LAB135_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB135_meta.json").write_text(json.dumps(dict(
    protocol='same BTC TRAIN robustness audit; no rule tuning',
    definition='Engine A + B3_HIGH frozen from LAB134',
    costs=COSTS,risk_pct=RISK,
    bootstrap='2000 deterministic block bootstrap replications, block size 8 trades',
    caveat='not independent validation'
),indent=2))
print("\n".join(lines))
