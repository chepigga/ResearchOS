#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
SRC_EVENTS=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009_EVENTS.csv'
SRC_THRESH=ROOT/'GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C.json'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'

OUT_JSON=ROOT/'GC_XAU_REV2_Q60_Q65_FROZEN_EXECUTION_GEOMETRY_EQUITY_COST_LAB010.json'
OUT_MD=ROOT/'GC_XAU_REV2_Q60_Q65_FROZEN_EXECUTION_GEOMETRY_EQUITY_COST_LAB010.md'
OUT_GRID=ROOT/'GC_XAU_REV2_Q60_Q65_FROZEN_EXECUTION_GEOMETRY_EQUITY_COST_LAB010_GRID.csv'
OUT_LEDGER=ROOT/'GC_XAU_REV2_Q60_Q65_FROZEN_EXECUTION_GEOMETRY_EQUITY_COST_LAB010_LEDGER.csv'

CLOCK_OFFSET_MIN=180
STALE_MS=2000
HORIZON_MS=300000
SLS=[round(x,2) for x in np.arange(0.50,4.0001,0.25)]
TPS=[round(x,2) for x in np.arange(0.75,8.0001,0.25)]
COSTS=[0.00,0.02,0.05,0.10,0.15]
CANDS=('Q60','Q65')

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

def pf(vals):
    x=np.asarray(vals,float)
    if not len(x): return None
    p=x[x>0].sum(); n=-x[x<0].sum()
    if n==0:return float('inf') if p>0 else None
    return float(p/n)

def dd_stats(vals):
    x=np.asarray(vals,float)
    if not len(x): return 0.0,0
    eq=np.cumsum(x)
    peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1]
    dd=peak-eq
    maxdd=float(np.max(dd)) if len(dd) else 0.0
    cur=best=0
    for v in x:
        if v<0: cur+=1; best=max(best,cur)
        else: cur=0
    return maxdd,int(best)

def sim_one(t,bid,ask,entry_i,end_i,d,entry,atr,sl,tp):
    slpx=entry-d*sl*atr
    tppx=entry+d*tp*atr
    if d>0:
        px=bid[entry_i:end_i+1]
        slhits=np.flatnonzero(px<=slpx); tphits=np.flatnonzero(px>=tppx)
    else:
        px=ask[entry_i:end_i+1]
        slhits=np.flatnonzero(px>=slpx); tphits=np.flatnonzero(px<=tppx)
    si=int(slhits[0]) if len(slhits) else None
    ti=int(tphits[0]) if len(tphits) else None
    if si is not None and (ti is None or si<=ti):
        return -1.0,'SL',int(t[entry_i+si]-t[entry_i])
    if ti is not None:
        return float(tp/sl),'TP',int(t[entry_i+ti]-t[entry_i])
    exitpx=float(bid[end_i] if d>0 else ask[end_i])
    rr=float(d*(exitpx-entry)/(sl*atr))
    return rr,'TIME',int(t[end_i]-t[entry_i])

def make_candidates():
    ev=pd.read_csv(SRC_EVENTS)
    th=json.loads(SRC_THRESH.read_text())
    d5=ev[ev.window_s==5][['gc_t0_ms','period','direction','post_signed_impulse_atr']].copy()
    d30=ev[ev.window_s==30][['gc_t0_ms','period','direction','post_aligned_volume']].copy()
    m=d5.merge(d30,on=['gc_t0_ms','period','direction'],how='inner')
    out=[]
    for c in CANDS:
        imp=float(th['thresholds'][c]['impulse'])
        av=float(th['thresholds'][c]['aligned_volume'])
        z=m[(m.post_signed_impulse_atr>=imp)&(m.post_aligned_volume>=av)].copy()
        z['candidate']=c
        z['impulse_thr']=imp
        z['aligned_volume_thr']=av
        out.append(z)
    return pd.concat(out,ignore_index=True)

def main():
    lt=load(LT,'lt')
    cand=make_candidates().sort_values(['candidate','gc_t0_ms']).reset_index(drop=True)

    t,bid,ask,_=lt.read_xau_ticks()
    xm1=lt.build_xau_m1(t,bid,ask)
    xatr=lt.xau_atr_lookup(xm1)

    base=[]
    for r in cand.itertuples(index=False):
        broker0=int(r.gc_t0_ms)+CLOCK_OFFSET_MIN*60000+30000
        i=first_idx(t,broker0)
        if i is None: continue
        j=end_idx(t,broker0+HORIZON_MS)
        if j is None or j<=i: continue
        prev=((broker0//60000)*60000)-60000
        atr=float(xatr.get(prev,np.nan))
        if not np.isfinite(atr) or atr<=0: continue
        d=int(r.direction)
        entry=float(ask[i] if d>0 else bid[i])
        base.append({
          'candidate':r.candidate,'gc_t0_ms':int(r.gc_t0_ms),'period':r.period,'direction':d,
          'entry_i':i,'end_i':j,'entry':entry,'atr':atr,
          'post_signed_impulse_atr':float(r.post_signed_impulse_atr),
          'post_aligned_volume':float(r.post_aligned_volume)
        })
    base=pd.DataFrame(base)

    ledgers=[]; rows=[]
    for c in CANDS:
        bc=base[base.candidate==c].copy()
        for sl in SLS:
            for tp in TPS:
                if tp/sl<1.5-1e-12: continue
                trade_rows=[]
                for r in bc.itertuples(index=False):
                    rr,reason,hold=sim_one(t,bid,ask,int(r.entry_i),int(r.end_i),int(r.direction),float(r.entry),float(r.atr),sl,tp)
                    trade_rows.append({
                      'candidate':c,'gc_t0_ms':int(r.gc_t0_ms),'period':r.period,
                      'sl_atr':sl,'tp_atr':tp,'gross_r':rr,'reason':reason,'hold_ms':hold
                    })
                z=pd.DataFrame(trade_rows).sort_values('gc_t0_ms')
                for cost in COSTS:
                    zz=z.copy()
                    zz['cost_r']=cost
                    zz['net_r']=zz.gross_r-cost
                    ledgers.append(zz)
                    for p in ('TRAIN','VALID','POST_CHECK','FULL'):
                        q=zz if p=='FULL' else zz[zz.period==p]
                        vals=q.net_r.to_numpy(float)
                        n=len(q); maxdd,streak=dd_stats(vals)
                        rows.append({
                          'candidate':c,'sl_atr':sl,'tp_atr':tp,'rr_nominal':tp/sl,'cost_r':cost,'period':p,'n':n,
                          'ev_r':float(vals.mean()) if n else None,'pf':pf(vals) if n else None,
                          'wr_pct':float((vals>0).mean()*100) if n else None,
                          'tp_rate_pct':float((q.reason=='TP').mean()*100) if n else None,
                          'sl_rate_pct':float((q.reason=='SL').mean()*100) if n else None,
                          'timeout_rate_pct':float((q.reason=='TIME').mean()*100) if n else None,
                          'cum_r':float(vals.sum()) if n else None,
                          'maxdd_r':maxdd,'maxdd_pct_at_025':maxdd*0.25,
                          'max_consec_losses':streak
                        })

    ledger=pd.concat(ledgers,ignore_index=True)
    grid=pd.DataFrame(rows)
    ledger.to_csv(OUT_LEDGER,index=False)
    grid.to_csv(OUT_GRID,index=False)

    robust_summary={}
    for c in CANDS:
        g0=grid[(grid.candidate==c)&(grid.cost_r==0)].copy()
        g5=grid[(grid.candidate==c)&(grid.cost_r==0.05)].copy()
        cells=g0[['sl_atr','tp_atr']].drop_duplicates()
        rs=[]
        for cell in cells.itertuples(index=False):
            z0=g0[(g0.sl_atr==cell.sl_atr)&(g0.tp_atr==cell.tp_atr)].set_index('period')
            z5=g5[(g5.sl_atr==cell.sl_atr)&(g5.tp_atr==cell.tp_atr)].set_index('period')
            tr=z0.loc['TRAIN'];va=z0.loc['VALID'];po=z0.loc['POST_CHECK'];fu=z0.loc['FULL']
            tr5=z5.loc['TRAIN'];va5=z5.loc['VALID']
            pos_tv=bool(tr.ev_r>0 and va.ev_r>0)
            pf_tv=bool(tr.pf is not None and va.pf is not None and tr.pf>=1.10 and va.pf>=1.10)
            pos_cost=bool(tr5.ev_r>0 and va5.ev_r>0)
            rs.append({
              'sl_atr':cell.sl_atr,'tp_atr':cell.tp_atr,'rr_nominal':cell.tp_atr/cell.sl_atr,
              'train_ev':tr.ev_r,'valid_ev':va.ev_r,'post_ev':po.ev_r,'full_ev':fu.ev_r,
              'train_pf':tr.pf,'valid_pf':va.pf,'post_pf':po.pf,'full_pf':fu.pf,
              'full_dd_r':fu.maxdd_r,'full_dd_pct_025':fu.maxdd_pct_at_025,
              'full_cum_r':fu.cum_r,'full_streak':int(fu.max_consec_losses),
              'positive_tv':pos_tv,'pf110_tv':pf_tv,'positive_tv_cost005':pos_cost
            })
        rr=pd.DataFrame(rs)
        keyset={(float(r.sl_atr),float(r.tp_atr)):bool(r.positive_tv and r.pf110_tv and r.positive_tv_cost005) for r in rr.itertuples(index=False)}
        neigh=[]
        for r in rr.itertuples(index=False):
            cnt=0
            for ds,dt in ((-.25,0),(.25,0),(0,-.25),(0,.25)):
                k=(round(r.sl_atr+ds,2),round(r.tp_atr+dt,2))
                if keyset.get(k,False): cnt+=1
            neigh.append(cnt)
        rr['robust_neighbor_count']=neigh
        rr['robust_cell']=rr.positive_tv & rr.pf110_tv & rr.positive_tv_cost005 & (rr.robust_neighbor_count>=2)
        top=rr.sort_values(['robust_cell','robust_neighbor_count','valid_ev','train_ev'],ascending=[False,False,False,False]).head(20)
        robust_summary[c]={
          'signal_n_total':int(len(base[base.candidate==c])),
          'signal_n_train':int(len(base[(base.candidate==c)&(base.period=='TRAIN')])),
          'signal_n_valid':int(len(base[(base.candidate==c)&(base.period=='VALID')])),
          'signal_n_post':int(len(base[(base.candidate==c)&(base.period=='POST_CHECK')])),
          'positive_tv_cells':int(rr.positive_tv.sum()),
          'pf110_tv_cells':int(rr.pf110_tv.sum()),
          'positive_tv_cost005_cells':int(rr.positive_tv_cost005.sum()),
          'robust_cells':int(rr.robust_cell.sum()),
          'top_cells':top.to_dict(orient='records')
        }

    out={'lab':'GC_XAU_REV2_Q60_Q65_FROZEN_EXECUTION_GEOMETRY_EQUITY_COST_LAB010',
         'status':'FROZEN_CANDIDATE_EXECUTION_AUDIT_NOT_OOS',
         'costs_r':COSTS,'robust_summary':robust_summary}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(v,d=3):
        if v is None or (isinstance(v,float) and not np.isfinite(v)): return 'NA'
        return f'{v:.{d}f}'

    lines=['# GC_XAU_REV2_Q60_Q65_FROZEN_EXECUTION_GEOMETRY_EQUITY_COST_LAB010','',
           'Status: FROZEN_CANDIDATE_EXECUTION_AUDIT_NOT_OOS','',
           'Spread is embedded in raw FTMO XAU Bid/Ask. Additional cost stress is deducted in R/trade.','']
    for c in CANDS:
        s=robust_summary[c]
        lines += [f'## {c}', '',
                  f"Signals: FULL {s['signal_n_total']} / TRAIN {s['signal_n_train']} / VALID {s['signal_n_valid']} / POST {s['signal_n_post']}",
                  f"Positive TRAIN+VALID cells: {s['positive_tv_cells']}",
                  f"PF>=1.10 TRAIN+VALID cells: {s['pf110_tv_cells']}",
                  f"Positive TRAIN+VALID at 0.05R cost: {s['positive_tv_cost005_cells']}",
                  f"Robust neighbor-supported cells: {s['robust_cells']}", '',
                  '| SL | TP | RR | Train EV/PF | Valid EV/PF | Post EV/PF | Full EV/PF | Full CumR | DD R | DD% @0.25 | Streak | Neigh | Robust |',
                  '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
        for r in s['top_cells']:
            lines.append(
              f"| {r['sl_atr']:.2f} | {r['tp_atr']:.2f} | {r['rr_nominal']:.2f} | "
              f"{f(r['train_ev'])}/{f(r['train_pf'])} | {f(r['valid_ev'])}/{f(r['valid_pf'])} | "
              f"{f(r['post_ev'])}/{f(r['post_pf'])} | {f(r['full_ev'])}/{f(r['full_pf'])} | "
              f"{f(r['full_cum_r'])} | {f(r['full_dd_r'])} | {f(r['full_dd_pct_025'])}% | "
              f"{r['full_streak']} | {r['robust_neighbor_count']} | {r['robust_cell']} |")
        lines.append('')
    lines += ['Cost stress layers: 0, 0.02R, 0.05R, 0.10R, 0.15R per trade.',
              'Exact live commission/slippage conversion is intentionally not claimed here; production conversion requires current FTMO XAU contract and execution specs.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
