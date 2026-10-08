#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB138_A_B3HIGH_R48_PORTFOLIO_20261008/run_lab138.py"
spec=importlib.util.spec_from_file_location("lab138",SRC)
M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

OUT=Path("lab140_out"); OUT.mkdir(exist_ok=True)
IMG=OUT/"charts"; IMG.mkdir(exist_ok=True)

COST=2.81

# ---------- exact frozen portfolio replay preserving side ----------
def build_exact_portfolio():
    # Engine A + B3_HIGH pool from LAB134 machinery.
    pool=M.A.make_events(COST)
    base=pool[pool.engine.isin(['A','B3_HIGH'])].copy()
    # exact one-position chronology used by LAB134/138
    pri={'A':0,'B3_HIGH':1}
    base['pri']=base.engine.map(pri)
    base=base.sort_values(['entry_time','pri'])
    accepted=[]
    open_until=pd.Timestamp.min.tz_localize('UTC')
    for _,r in base.iterrows():
        if r.entry_time<open_until:
            continue
        open_until=r.exit_time
        accepted.append(dict(
            source=r.engine,
            entry_time=pd.Timestamp(r.entry_time),
            exit_time=pd.Timestamp(r.exit_time),
            side=int(r.side),
            net_r=float(r.net_r)
        ))
    base_acc=pd.DataFrame(accepted)

    # Frozen R48_HIGH = CLEAN_ACCEPT_OI from LAB137.
    R=M.R
    rh=R.df[(~R.df.retest) &
            (R.df.mean_margin>=R.thr['mean_margin_q60']) &
            (R.df.oi_change>=R.thr['oi_q60'])].copy()
    rr=[]
    for _,r in rh.iterrows():
        net,reason,xi=R.sim_one(r,COST)
        rr.append(dict(
            source='R48_HIGH',
            entry_time=pd.Timestamp(r.entry_time),
            exit_time=pd.Timestamp(R.BT.iloc[xi]),
            side=int(r.side),
            net_r=float(net)
        ))
    r48=pd.DataFrame(rr)

    # LAB138 portfolio chronology: combine already-accepted A+B3 with R48,
    # then one-position replay, exact-collision priority A > B3_HIGH > R48_HIGH.
    allp=pd.concat([base_acc,r48],ignore_index=True)
    pri2={'A':0,'B3_HIGH':1,'R48_HIGH':2}
    allp['pri']=allp.source.map(pri2)
    allp=allp.sort_values(['entry_time','pri'])
    final=[]; open_until=pd.Timestamp.min.tz_localize('UTC')
    for _,r in allp.iterrows():
        if r.entry_time<open_until:
            continue
        open_until=r.exit_time
        final.append(r)
    t=pd.DataFrame(final).reset_index(drop=True)
    t['trade_id']=np.arange(1,len(t)+1)
    t['side_name']=np.where(t.side>0,'BUY','SELL')
    return t

trades=build_exact_portfolio()

# Cross-check against frozen LAB138 result.
if len(trades)!=282:
    raise RuntimeError(f"Parity failure: expected 282 trades, got {len(trades)}")

# ---------- exact price tape ----------
# LAB137 -> LAB136 holds the BTC M5 tape used by the same research lineage.
b=M.R.b.copy()
b['time']=pd.to_datetime(b['time'],utc=True)
price=b[['time','open','high','low','close']].copy().sort_values('time')
price=price[(price.time>=pd.Timestamp('2021-01-01',tz='UTC')) &
            (price.time<pd.Timestamp('2025-01-01',tz='UTC'))].copy()

# Entry/exit prices from exact M5 tape.
px=price.set_index('time')
def nearest_price(ts, field='open'):
    ts=pd.Timestamp(ts)
    if ts in px.index:
        return float(px.loc[ts,field])
    k=px.index.get_indexer([ts],method='nearest')[0]
    return float(px.iloc[k][field])
trades['entry_price']=[nearest_price(t,'open') for t in trades.entry_time]
trades['exit_price']=[nearest_price(t,'close') for t in trades.exit_time]
trades['duration_h']=(pd.to_datetime(trades.exit_time,utc=True)-pd.to_datetime(trades.entry_time,utc=True)).dt.total_seconds()/3600
trades.to_csv(OUT/"LAB140_exact_portfolio_trades.csv",index=False)

# Summary.
summary=(trades.groupby(['source','side_name'])
         .agg(n=('trade_id','size'),net_r=('net_r','sum'),ev=('net_r','mean'))
         .reset_index())
summary.to_csv(OUT/"LAB140_engine_side_summary.csv",index=False)

# ---------- plotting ----------
engine_colors={'A':'tab:blue','B3_HIGH':'tab:orange','R48_HIGH':'tab:green'}
def plot_span(start,end,name,title,annotate_ids=False):
    p=price[(price.time>=start)&(price.time<end)].copy()
    t=trades[(trades.entry_time>=start)&(trades.entry_time<end)].copy()
    if p.empty:
        return
    fig,ax=plt.subplots(figsize=(18,8))
    ax.plot(p.time,p.close,linewidth=0.7,label='BTCUSDT M5 close')
    # position paths + markers
    for _,r in t.iterrows():
        c=engine_colors[r.source]
        marker='^' if r.side>0 else 'v'
        ax.scatter(r.entry_time,r.entry_price,s=42,marker=marker,color=c,zorder=4)
        ax.scatter(r.exit_time,r.exit_price,s=28,marker='x',color=c,zorder=4)
        ax.plot([r.entry_time,r.exit_time],[r.entry_price,r.exit_price],color=c,linewidth=0.7,alpha=0.45)
        if annotate_ids:
            ax.annotate(str(int(r.trade_id)),(r.entry_time,r.entry_price),xytext=(2,4),textcoords='offset points',fontsize=6)
    # legend proxies
    for e,c in engine_colors.items():
        ax.scatter([],[],s=45,marker='o',color=c,label=e)
    ax.scatter([],[],s=45,marker='^',color='black',label='BUY entry')
    ax.scatter([],[],s=45,marker='v',color='black',label='SELL entry')
    ax.scatter([],[],s=35,marker='x',color='black',label='Exit')
    ax.set_title(title)
    ax.set_ylabel('BTCUSDT price')
    ax.set_xlabel('UTC')
    ax.grid(True,alpha=0.2)
    ax.legend(loc='upper left',ncol=4,fontsize=8)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=6,maxticks=15))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    fig.tight_layout()
    fig.savefig(IMG/name,dpi=170)
    plt.close(fig)

# Whole history overview.
plot_span(pd.Timestamp('2021-01-01',tz='UTC'),pd.Timestamp('2025-01-01',tz='UTC'),
          'LAB140_BTC_2021_2024_OVERVIEW.png',
          'LAB140 — BTCUSDT M5 exact price + all 282 trades | ENGINE_A + B3_HIGH + R48_HIGH')

# Yearly overviews.
for y in range(2021,2025):
    plot_span(pd.Timestamp(f'{y}-01-01',tz='UTC'),pd.Timestamp(f'{y+1}-01-01',tz='UTC'),
              f'LAB140_BTC_{y}_ALL_TRADES.png',
              f'LAB140 — BTCUSDT {y} | all portfolio trades')

# Quarterly charts, with trade IDs for detailed visual audit.
for y in range(2021,2025):
    for q in range(1,5):
        m0=(q-1)*3+1
        start=pd.Timestamp(f'{y}-{m0:02d}-01',tz='UTC')
        if q<4:
            end=pd.Timestamp(f'{y}-{m0+3:02d}-01',tz='UTC')
        else:
            end=pd.Timestamp(f'{y+1}-01-01',tz='UTC')
        plot_span(start,end,f'LAB140_BTC_{y}_Q{q}.png',
                  f'LAB140 — BTCUSDT {y} Q{q} | entries/exits with trade IDs',annotate_ids=True)

# Trade-centered panels: each image covers +/- 12h around entry and exit span,
# up to 96h total, useful for seeing exactly how each engine behaves.
W=12
for _,r in trades.iterrows():
    st=r.entry_time-pd.Timedelta(hours=W)
    en=max(r.exit_time+pd.Timedelta(hours=W),r.entry_time+pd.Timedelta(hours=W))
    # cap huge visuals at entry + 72h for readability
    en=min(en,r.entry_time+pd.Timedelta(hours=72))
    p=price[(price.time>=st)&(price.time<=en)]
    if p.empty: continue
    fig,ax=plt.subplots(figsize=(12,5))
    ax.plot(p.time,p.close,linewidth=0.9)
    c=engine_colors[r.source]
    marker='^' if r.side>0 else 'v'
    ax.scatter([r.entry_time],[r.entry_price],s=80,marker=marker,color=c,zorder=5,label=f"{r.source} {r.side_name} entry")
    if r.exit_time<=en:
        ax.scatter([r.exit_time],[r.exit_price],s=60,marker='x',color=c,zorder=5,label=f"exit {r.net_r:+.2f}R")
        ax.plot([r.entry_time,r.exit_time],[r.entry_price,r.exit_price],color=c,linewidth=1,alpha=0.6)
    ax.axvline(r.entry_time,linewidth=0.7,alpha=0.5)
    ax.set_title(f"Trade #{int(r.trade_id)} | {r.source} | {r.side_name} | {r.net_r:+.2f}R | {r.duration_h:.1f}h")
    ax.set_ylabel('BTCUSDT price')
    ax.set_xlabel('UTC')
    ax.grid(True,alpha=0.2)
    ax.legend(loc='best',fontsize=8)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    fig.tight_layout()
    fig.savefig(IMG/f"trade_{int(r.trade_id):03d}_{r.source}_{r.side_name}.png",dpi=145)
    plt.close(fig)

meta={
    'portfolio':'ENGINE_A + B3_HIGH + R48_HIGH',
    'cost_bps':COST,
    'trade_count':int(len(trades)),
    'price_source':'same BTC M5 tape loaded by LAB137/LAB138 research lineage',
    'entry_marker':'triangle up BUY / triangle down SELL',
    'exit_marker':'x',
    'line_between_markers':'entry-to-exit holding interval',
    'engine_colors':engine_colors,
    'files':{
        'overview':'LAB140_BTC_2021_2024_OVERVIEW.png',
        'yearly':'LAB140_BTC_YYYY_ALL_TRADES.png',
        'quarterly':'LAB140_BTC_YYYY_QN.png',
        'trade_panels':'charts/trade_###_ENGINE_SIDE.png',
        'trade_csv':'LAB140_exact_portfolio_trades.csv'
    }
}
(OUT/"LAB140_meta.json").write_text(json.dumps(meta,indent=2))

report=f"""# LAB140 — VISUAL AUDIT

Portfolio: `ENGINE_A + B3_HIGH + R48_HIGH`

Purpose: visual parity audit of the frozen LAB138 BTC portfolio on the exact M5 price tape used by the research lineage.

- Exact portfolio trade count: **{len(trades)}**
- Cost replay: **{COST} bps**
- Price chart: BTCUSDT M5 close
- BUY entry: triangle up
- SELL entry: triangle down
- Exit: X
- Entry-to-exit line: holding interval
- Engine colors: A / B3_HIGH / R48_HIGH
- 1 full-history overview
- 4 yearly charts
- 16 quarterly charts with trade IDs
- {len(trades)} trade-centered detail panels
- CSV with exact entry/exit timestamps and prices

This LAB is visualization only. It does not change any signal, threshold, execution rule, or portfolio chronology.
"""
(OUT/"LAB140_REPORT.md").write_text(report)
print(report)
