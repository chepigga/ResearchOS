#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
REV=ROOT/'GC_XAU_DOMINANCE_REVERSAL_MECHANISM_AND_TIMING_LAB007D_EVENTS.csv'
OUT_JSON=ROOT/'GC_XAU_REV2_EXECUTION_GEOMETRY_WIDE_GRID_LAB008.json'
OUT_MD=ROOT/'GC_XAU_REV2_EXECUTION_GEOMETRY_WIDE_GRID_LAB008.md'
OUT_CSV=ROOT/'GC_XAU_REV2_EXECUTION_GEOMETRY_WIDE_GRID_LAB008_GRID.csv'
OUT_LEDGER=ROOT/'GC_XAU_REV2_EXECUTION_GEOMETRY_WIDE_GRID_LAB008_LEDGER.csv'

CLOCK_OFFSET_MIN=180
STALE_MS=2000
HORIZON_MS=300000
SLS=[0.25,0.50,0.75,1.00,1.25,1.50,1.75,2.00]
TPS=[round(x,2) for x in np.arange(0.50,4.0001,0.25)]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    return m

def first_idx(t,target,maxlag=STALE_MS):
    i=int(np.searchsorted(t,target,side='left'))
    if i>=len(t): return None
    lag=int(t[i]-target)
    if lag<0 or lag>maxlag:return None
    return i

def end_idx(t,target):
    i=int(np.searchsorted(t,target,side='right'))-1
    return i if i>=0 else None

def dd_stats(rvals):
    x=np.asarray(rvals,float)
    eq=np.cumsum(x)
    if len(eq)==0:return 0.0,0
    peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1]
    dd=peak-eq
    maxdd=float(np.max(dd)) if len(dd) else 0.0
    streak=best=0
    for v in x:
        if v<0:
            streak+=1;best=max(best,streak)
        else:streak=0
    return maxdd,int(best)

def pf(vals):
    x=np.asarray(vals,float)
    pos=x[x>0].sum(); neg=-x[x<0].sum()
    if neg==0:return float('inf') if pos>0 else None
    return float(pos/neg)

def sim_one(t,bid,ask,entry_i,end_i,d,entry,atr,sl,tp):
    slpx=entry-d*sl*atr
    tppx=entry+d*tp*atr
    if d>0:
        px=bid[entry_i:end_i+1]
        slhits=np.flatnonzero(px<=slpx)
        tphits=np.flatnonzero(px>=tppx)
    else:
        px=ask[entry_i:end_i+1]
        slhits=np.flatnonzero(px>=slpx)
        tphits=np.flatnonzero(px<=tppx)
    si=int(slhits[0]) if len(slhits) else None
    ti=int(tphits[0]) if len(tphits) else None
    if si is not None and (ti is None or si<=ti):
        return -1.0,'SL',int(t[entry_i+si]-t[entry_i])
    if ti is not None:
        return float(tp/sl),'TP',int(t[entry_i+ti]-t[entry_i])
    exitpx=float(bid[end_i] if d>0 else ask[end_i])
    rr=float(d*(exitpx-entry)/(sl*atr))
    return rr,'TIME',int(t[end_i]-t[entry_i])

def main():
    lt=load(LT,'lt')
    rev=pd.read_csv(REV)
    rev=rev[rev.clock=='REV2'].copy().sort_values('gc_t0_ms')
    t,bid,ask,_=lt.read_xau_ticks()
    xm1=lt.build_xau_m1(t,bid,ask)
    xatr=lt.xau_atr_lookup(xm1)

    base=[]
    for r in rev.itertuples(index=False):
        broker=int(r.gc_t0_ms)+CLOCK_OFFSET_MIN*60000
        i=first_idx(t,broker)
        if i is None:continue
        j=end_idx(t,broker+HORIZON_MS)
        if j is None or j<=i:continue
        prev=((broker//60000)*60000)-60000
        atr=float(xatr.get(prev,np.nan))
        if not np.isfinite(atr) or atr<=0:continue
        d=int(r.reversal_dir)
        entry=float(ask[i] if d>0 else bid[i])
        base.append({'gc_t0_ms':int(r.gc_t0_ms),'period':r.period,'direction':d,'entry_i':i,'end_i':j,'entry':entry,'atr':atr})
    base=pd.DataFrame(base)

    ledgers=[];grid=[]
    for sl in SLS:
        for tp in TPS:
            if tp/sl<1.5-1e-12:continue
            rows=[]
            for r in base.itertuples(index=False):
                rr,reason,hold=sim_one(t,bid,ask,int(r.entry_i),int(r.end_i),int(r.direction),float(r.entry),float(r.atr),sl,tp)
                rows.append({'gc_t0_ms':int(r.gc_t0_ms),'period':r.period,'sl_atr':sl,'tp_atr':tp,'rr':rr,'reason':reason,'hold_ms':hold})
            z=pd.DataFrame(rows)
            ledgers.append(z)
            for p in ('TRAIN','VALID','POST_CHECK','FULL'):
                q=z if p=='FULL' else z[z.period==p]
                vals=q.rr.to_numpy(float)
                maxdd,streak=dd_stats(vals)
                n=len(q)
                grid.append({
                  'sl_atr':sl,'tp_atr':tp,'rr_nominal':tp/sl,'period':p,'n':n,
                  'ev_r':float(vals.mean()) if n else None,
                  'pf':pf(vals) if n else None,
                  'wr_pct':float((vals>0).mean()*100) if n else None,
                  'tp_rate_pct':float((q.reason=='TP').mean()*100) if n else None,
                  'sl_rate_pct':float((q.reason=='SL').mean()*100) if n else None,
                  'timeout_rate_pct':float((q.reason=='TIME').mean()*100) if n else None,
                  'cum_r':float(vals.sum()) if n else None,
                  'maxdd_r':maxdd,'max_consec_losses':streak
                })
    ledger=pd.concat(ledgers,ignore_index=True)
    g=pd.DataFrame(grid)
    ledger.to_csv(OUT_LEDGER,index=False)
    g.to_csv(OUT_CSV,index=False)

    # robustness flags by cell
    piv={}
    robust=[]
    cells=g[['sl_atr','tp_atr']].drop_duplicates()
    for c in cells.itertuples(index=False):
        q=g[(g.sl_atr==c.sl_atr)&(g.tp_atr==c.tp_atr)].set_index('period')
        tr=q.loc['TRAIN'];va=q.loc['VALID'];po=q.loc['POST_CHECK'];fu=q.loc['FULL']
        pos_tv=tr.ev_r>0 and va.ev_r>0
        pf_tv=(tr.pf is not None and va.pf is not None and tr.pf>=1.10 and va.pf>=1.10)
        pos_all=pos_tv and po.ev_r>0
        score=min(tr.ev_r,va.ev_r,po.ev_r)
        robust.append({
          'sl_atr':c.sl_atr,'tp_atr':c.tp_atr,'rr_nominal':c.tp_atr/c.sl_atr,
          'train_ev':tr.ev_r,'valid_ev':va.ev_r,'post_ev':po.ev_r,'full_ev':fu.ev_r,
          'train_pf':tr.pf,'valid_pf':va.pf,'post_pf':po.pf,'full_pf':fu.pf,
          'full_dd':fu.maxdd_r,'full_cum_r':fu.cum_r,
          'positive_train_valid':bool(pos_tv),'pf110_train_valid':bool(pf_tv),
          'positive_all3':bool(pos_all),'min_split_ev':score
        })
    rob=pd.DataFrame(robust)

    # neighborhood robustness: 4-neighbor cells that also positive ALL3
    keys={(float(r.sl_atr),float(r.tp_atr)):bool(r.positive_all3) for r in rob.itertuples(index=False)}
    neigh=[]
    for r in rob.itertuples(index=False):
        cnt=0;tot=0
        for ds,dt in ((-.25,0),(.25,0),(0,-.25),(0,.25)):
            k=(round(r.sl_atr+ds,2),round(r.tp_atr+dt,2))
            if k in keys:
                tot+=1;cnt+=int(keys[k])
        neigh.append(cnt)
    rob['positive_all3_neighbor_count']=neigh

    top=rob.sort_values(['positive_all3','pf110_train_valid','positive_all3_neighbor_count','min_split_ev','full_pf'],ascending=[False,False,False,False,False]).head(20)
    bounds=[]
    for sl in SLS:
        q=rob[rob.sl_atr==sl]
        qa=q[q.positive_all3]
        bounds.append({
          'sl_atr':sl,
          'n_cells':int(len(q)),
          'n_positive_all3':int(len(qa)),
          'tp_min_positive_all3':float(qa.tp_atr.min()) if len(qa) else None,
          'tp_max_positive_all3':float(qa.tp_atr.max()) if len(qa) else None,
          'best_min_split_ev':float(q.min_split_ev.max()) if len(q) else None
        })

    out={
      'lab':'GC_XAU_REV2_EXECUTION_GEOMETRY_WIDE_GRID_LAB008',
      'status':'WIDE_GEOMETRY_SURFACE_NOT_PRODUCTION_OPTIMIZATION',
      'signal_n':int(len(base)),
      'grid_cells':int(len(cells)),
      'robust_counts':{
        'positive_train_valid':int(rob.positive_train_valid.sum()),
        'pf110_train_valid':int(rob.pf110_train_valid.sum()),
        'positive_all3':int(rob.positive_all3.sum())
      },
      'bounds_by_sl':bounds,
      'top_robust_cells':top.to_dict(orient='records')
    }
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(v,d=3):
        if v is None or (isinstance(v,float) and not np.isfinite(v)):return 'NA'
        return f'{v:.{d}f}'
    lines=['# GC_XAU_REV2_EXECUTION_GEOMETRY_WIDE_GRID_LAB008','',
           'Status: WIDE_GEOMETRY_SURFACE_NOT_PRODUCTION_OPTIMIZATION','',
           f"REV2 signals with executable XAU path: {len(base)}",
           f"Grid cells (R:R>=1.5): {len(cells)}",'',
           '## Robustness counts','',
           f"- Positive EV in TRAIN + VALID: {int(rob.positive_train_valid.sum())}",
           f"- PF>=1.10 in TRAIN + VALID: {int(rob.pf110_train_valid.sum())}",
           f"- Positive EV in TRAIN + VALID + POST: {int(rob.positive_all3.sum())}",'',
           '## Movement boundary by SL','',
           '| SL ATR | Cells | Positive all3 | TP min | TP max | Best worst-split EV |',
           '|---:|---:|---:|---:|---:|---:|']
    for b in bounds:
        lines.append(f"| {b['sl_atr']:.2f} | {b['n_cells']} | {b['n_positive_all3']} | {f(b['tp_min_positive_all3'],2)} | {f(b['tp_max_positive_all3'],2)} | {f(b['best_min_split_ev'])} |")
    lines+=['','## Top robust surface cells','',
            '| SL | TP | RR | Train EV/PF | Valid EV/PF | Post EV/PF | Full EV/PF | Full DD | Neigh+ |',
            '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in top.itertuples(index=False):
        lines.append(f"| {r.sl_atr:.2f} | {r.tp_atr:.2f} | {r.rr_nominal:.2f} | {f(r.train_ev)}/{f(r.train_pf)} | {f(r.valid_ev)}/{f(r.valid_pf)} | {f(r.post_ev)}/{f(r.post_pf)} | {f(r.full_ev)}/{f(r.full_pf)} | {f(r.full_dd)}R | {int(r.positive_all3_neighbor_count)} |")
    lines+=['','Spread is embedded from raw Bid/Ask. Commission/slippage are not added in this geometry-map LAB; do not promote a cell directly to production.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
