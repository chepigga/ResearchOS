#!/usr/bin/env python3
"""XAU_PRICE_TIME_ALOGICAL_TICK_ORDER_SHORT_RESPONSE_LAB_009

Purpose
-------
Resolve the central ambiguity exposed by LAB008: small inverse TP/SL barriers are
usually both touched inside M1, so OHLC cannot tell which came first. Replay the
original FTMO Bid/Ask ticks and determine exact TP-first vs SL-first order.

Lineage / anti-leakage
----------------------
- LAB007 V2 transition definitions are frozen.
- LAB008 M1 information is used ONLY through 2025 to define ambiguity-resolvable
  candidates. 2026 is never used for candidate selection.
- Candidate condition: n train>=80, n validation>=30, target=0.40 ATR, RR=2.0,
  horizon in {20,30} min, and the fraction of ambiguous cases that would need to
  be TP-first for breakeven is <=55% in BOTH 2023-24 and 2025.
- Exact tick outcomes then use 2023-24 discovery, 2025 validation, 2026 final OOS.
- Portfolio is globally de-clustered by 240 minutes.

Execution
---------
BUY: enter Ask, TP/SL resolved on Bid.
SELL: enter Bid, TP/SL resolved on Ask.
Commission = 0.0007% USD notional per side (same frozen model as LAB001).
No slippage is added in this research lab; any surviving edge must later pass a
slippage/spread stress test before EA admission.
"""
from __future__ import annotations

import argparse
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from xau_price_time_alogical_path_transition_lab007_v2 import add_obviousness, build_transitions, cooldown
from xau_price_time_alogical_post_trap_payoff_map_lab008 import load_full, independent_events, surface_period

COMMISSION_RATE_SIDE = 0.000007
TARGET_ATR = 0.40
RR = 2.0
STOP_ATR = TARGET_ATR / RR
QREQ_MAX = 0.55
HORIZONS = {20, 30}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--bars', type=Path, required=True)
    p.add_argument('--labels', type=Path, required=True)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--raw-zip', type=Path, required=True)
    p.add_argument('--outdir', type=Path, required=True)
    return p.parse_args()


def pf(r):
    r=np.asarray(r,float); r=r[np.isfinite(r)]
    if not len(r): return None
    gp=float(r[r>0].sum()); gl=float(-r[r<0].sum())
    return gp/gl if gl>0 else None


def stats(r):
    r=np.asarray(r,float); r=r[np.isfinite(r)]
    if not len(r): return {'n':0,'mean_R':None,'pf':None,'win_rate':None,'sum_R':0.0,'max_dd_R':None}
    eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=peak[1:]-eq
    return {'n':int(len(r)),'mean_R':float(np.mean(r)),'pf':pf(r),'win_rate':float(np.mean(r>0)),
            'sum_R':float(np.sum(r)),'max_dd_R':float(np.max(dd)) if len(dd) else 0.0}


def q_required(mean_r, amb_rate, rr):
    if not np.isfinite(mean_r) or not np.isfinite(amb_rate) or amb_rate<=0: return np.nan
    return max(0.0, -float(mean_r)/(float(amb_rate)*(float(rr)+1.0)))


def choose_pre2026_candidates(x, t):
    tr=surface_period(x,t,{2023,2024}); va=surface_period(x,t,{2025})
    a=tr[['config_id','cell_id','horizon_min','target_atr','rr','n','mean_R','pf','ambiguous_rate']].copy()
    b=va[['config_id','n','mean_R','pf','ambiguous_rate']].copy()
    a=a.rename(columns={c:f'train_{c}' for c in a.columns if c not in ['config_id','cell_id','horizon_min','target_atr','rr']})
    b=b.rename(columns={c:f'val_{c}' for c in b.columns if c!='config_id'})
    m=a.merge(b,on='config_id',how='inner')
    m['qreq_train']=[q_required(r.train_mean_R,r.train_ambiguous_rate,r.rr) for _,r in m.iterrows()]
    m['qreq_val']=[q_required(r.val_mean_R,r.val_ambiguous_rate,r.rr) for _,r in m.iterrows()]
    m['qreq_pre2026']=m[['qreq_train','qreq_val']].max(axis=1)
    keep=(m.train_n>=80)&(m.val_n>=30)&np.isclose(m.target_atr,TARGET_ATR)&np.isclose(m.rr,RR)&m.horizon_min.isin(HORIZONS)&(m.qreq_train<=QREQ_MAX)&(m.qreq_val<=QREQ_MAX)
    c=m.loc[keep].sort_values(['qreq_pre2026','train_n'],ascending=[True,False]).reset_index(drop=True)
    return c


def attach_file_ranges(audit_path: Path):
    a=json.loads(audit_path.read_text())
    fs=[]
    for f in a.get('files',[]):
        if f.get('valid_rows',0)>0 and f.get('first_time_msc') is not None and f.get('last_time_msc') is not None:
            fs.append((f['member'],int(f['first_time_msc']),int(f['last_time_msc'])))
    fs.sort(key=lambda z:z[1])
    if not fs: raise RuntimeError('audit has no valid raw file ranges')
    return fs


def build_event_table(x, t, candidates):
    # M1 bars are sorted and entry_idx is the exact bar index inherited from LAB007.
    # Keep first_time_msc for exact raw replay by merging it from the original bars file separately.
    pairs=candidates[['config_id','cell_id','horizon_min','qreq_pre2026','qreq_train','qreq_val']].copy()
    parts=[]
    for _,c in pairs.iterrows():
        g=t[t.cell_id.eq(c.cell_id)].copy()
        if g.empty: continue
        g['config_id']=c.config_id; g['horizon_min_exact']=int(c.horizon_min)
        g['qreq_pre2026']=float(c.qreq_pre2026); g['qreq_train']=float(c.qreq_train); g['qreq_val']=float(c.qreq_val)
        parts.append(g)
    if not parts: return pd.DataFrame()
    e=pd.concat(parts,ignore_index=True)
    idx=e.entry_idx.to_numpy(np.int64)
    e['entry_time_msc']=x['first_time_msc'].to_numpy(np.int64)[idx]
    e['entry_bid']=x['first_bid'].to_numpy(float)[idx]
    e['entry_ask']=x['first_ask'].to_numpy(float)[idx]
    e['atr_entry']=x['atr14_causal'].to_numpy(float)[idx]
    e['end_time_msc']=(x['minute'].to_numpy(np.int64)[idx] + e['horizon_min_exact'].to_numpy(np.int64))*60_000 - 1
    side_buy=e.inverse_side.eq('BUY').to_numpy()
    entry=np.where(side_buy,e.entry_ask.to_numpy(float),e.entry_bid.to_numpy(float))
    d=e.atr_entry.to_numpy(float)
    e['tp_price']=np.where(side_buy,entry+TARGET_ATR*d,entry-TARGET_ATR*d)
    e['sl_price']=np.where(side_buy,entry-STOP_ATR*d,entry+STOP_ATR*d)
    e['commission_R']=2.0*COMMISSION_RATE_SIDE*entry/(STOP_ATR*d)
    e['event_uid']=np.arange(len(e),dtype=np.int64)
    return e.sort_values('entry_time_msc').reset_index(drop=True)


def replay_ticks(raw_zip: Path, files, events: pd.DataFrame):
    n=len(events)
    outcome=np.full(n,'UNRESOLVED',object)
    r=np.full(n,np.nan,float); hit_time=np.full(n,-1,np.int64); terminal_px=np.full(n,np.nan,float)
    last_seen=np.full(n,-1,np.int64)
    start=events.entry_time_msc.to_numpy(np.int64); end=events.end_time_msc.to_numpy(np.int64)
    side_buy=events.inverse_side.eq('BUY').to_numpy(); tp=events.tp_price.to_numpy(float); sl=events.sl_price.to_numpy(float)
    entry=np.where(side_buy,events.entry_ask.to_numpy(float),events.entry_bid.to_numpy(float)); comm=events.commission_R.to_numpy(float)
    ev_atr=events.atr_entry.to_numpy(float)
    # event indices are in sorted event-time order; use searchsorted to limit overlap checks per raw file.
    with zipfile.ZipFile(raw_zip,'r') as z:
        names=set(z.namelist())
        for k,(member,ft,lt) in enumerate(files,1):
            if member not in names: continue
            # Events whose window can intersect this file range.
            hi=int(np.searchsorted(start,lt,side='right'))
            if hi<=0: continue
            cand=np.flatnonzero((np.arange(n)<hi)&(end>=ft)&(outcome=='UNRESOLVED'))
            if not len(cand): continue
            with z.open(member) as fh:
                df=pd.read_csv(fh,usecols=['time_msc','bid','ask'])
            if df.empty: continue
            tt=df.time_msc.to_numpy(np.int64); bid=df.bid.to_numpy(float); ask=df.ask.to_numpy(float)
            for ei in cand:
                lo_i=int(np.searchsorted(tt,start[ei],side='left')); hi_i=int(np.searchsorted(tt,end[ei],side='right'))
                if hi_i<=lo_i: continue
                px=bid[lo_i:hi_i] if side_buy[ei] else ask[lo_i:hi_i]
                if side_buy[ei]:
                    ih=np.flatnonzero((px>=tp[ei]) | (px<=sl[ei]))
                else:
                    ih=np.flatnonzero((px<=tp[ei]) | (px>=sl[ei]))
                terminal_px[ei]=float(px[-1]); last_seen[ei]=int(tt[hi_i-1])
                if len(ih):
                    j=lo_i+int(ih[0]); p=float(bid[j] if side_buy[ei] else ask[j]); hit_time[ei]=int(tt[j])
                    is_tp=(p>=tp[ei]) if side_buy[ei] else (p<=tp[ei])
                    if is_tp:
                        outcome[ei]='TP'; r[ei]=RR-comm[ei]
                    else:
                        outcome[ei]='SL'; r[ei]=-1.0-comm[ei]
            if k%100==0: print(f'[RAW] {k}/{len(files)} resolved={(outcome!="UNRESOLVED").sum()}/{n}',flush=True)
    # Time-stop unresolved cases at last executable quote observed inside horizon.
    u=np.flatnonzero(outcome=='UNRESOLVED')
    for ei in u:
        if np.isfinite(terminal_px[ei]):
            pnl=(terminal_px[ei]-entry[ei]) if side_buy[ei] else (entry[ei]-terminal_px[ei])
            r[ei]=pnl/(STOP_ATR*ev_atr[ei])-comm[ei]; outcome[ei]='TIME'
        else:
            outcome[ei]='NO_TICKS'
    out=events.copy(); out['tick_outcome']=outcome; out['R_exact']=r; out['hit_time_msc']=hit_time; out['last_seen_msc']=last_seen; out['terminal_exec_price']=terminal_px
    out['minutes_to_hit']=np.where(hit_time>=0,(hit_time-start)/60000.0,np.nan)
    return out


def summarize_configs(e):
    rows=[]
    for (cfg,yr),g in e[np.isfinite(e.R_exact)].groupby(['config_id','entry_year'],sort=True):
        s=stats(g.sort_values('entry_time_msc').R_exact.to_numpy(float)); rows.append({'config_id':cfg,'year':int(yr),**s,
            'tp_rate':float((g.tick_outcome=='TP').mean()),'sl_rate':float((g.tick_outcome=='SL').mean()),'time_rate':float((g.tick_outcome=='TIME').mean()),
            'median_minutes_to_hit':float(g.minutes_to_hit.dropna().median()) if g.minutes_to_hit.notna().any() else None})
    return pd.DataFrame(rows)


def pre2026_lock(summary, candidates):
    tr=summary[summary.year.isin([2023,2024])].groupby('config_id').apply(lambda g: None, include_groups=False) if False else None
    # Recompute from trade rows later; this function only creates metadata shell.
    return candidates.copy()


def config_period(e, years):
    rows=[]
    d=e[e.entry_year.isin(years)&np.isfinite(e.R_exact)]
    for cfg,g in d.groupby('config_id',sort=True): rows.append({'config_id':cfg,**stats(g.sort_values('entry_time_msc').R_exact.to_numpy(float))})
    return pd.DataFrame(rows)


def build_transfer(e,candidates):
    tr=config_period(e,{2023,2024}).add_prefix('train_').rename(columns={'train_config_id':'config_id'})
    va=config_period(e,{2025}).add_prefix('val_').rename(columns={'val_config_id':'config_id'})
    fi=config_period(e,{2026}).add_prefix('final_').rename(columns={'final_config_id':'config_id'})
    m=candidates.merge(tr,on='config_id',how='left').merge(va,on='config_id',how='left').merge(fi,on='config_id',how='left')
    m['discovery_pass']=(m.train_n>=80)&(m.train_mean_R>=0.03)&(m.train_pf>=1.05)
    m['validation_pass']=(m.val_n>=30)&(m.val_mean_R>0)&(m.val_pf>1.0)
    m['locked_before_2026']=m.discovery_pass&m.validation_pass
    m['final_2026_pass']=(m.final_n>=20)&(m.final_mean_R>0)&(m.final_pf>1.0)
    return m.sort_values(['locked_before_2026','train_mean_R','val_mean_R'],ascending=[False,False,False],na_position='last')


def portfolio(e,transfer):
    c=transfer[transfer.locked_before_2026].copy()
    if c.empty: return pd.DataFrame()
    rank=c.set_index('config_id').train_mean_R.to_dict()
    d=e[e.config_id.isin(c.config_id)&np.isfinite(e.R_exact)].copy(); d['rank']=d.config_id.map(rank)
    d=d.sort_values(['entry_time_msc','rank'],ascending=[True,False]).drop_duplicates(['entry_time_msc','inverse_side'])
    return cooldown(d.sort_values('entry_minute'),minutes=240)


def yearly(p):
    if p.empty: return pd.DataFrame(columns=['year','n','mean_R','pf','win_rate','sum_R','max_dd_R'])
    rows=[]
    for y,g in p.groupby('entry_year',sort=True): rows.append({'year':int(y),**stats(g.sort_values('entry_time_msc').R_exact.to_numpy(float))})
    return pd.DataFrame(rows)


def main():
    a=parse_args(); a.outdir.mkdir(parents=True,exist_ok=True)
    # Need exact first tick timestamp from bars in addition to LAB008 load_full schema.
    b=pd.read_parquet(a.bars)
    x=load_full(a.bars,a.labels)
    x=x.merge(b[['minute','first_time_msc']],on='minute',how='left',validate='one_to_one')
    x=add_obviousness(x)
    t=independent_events(build_transitions(x))
    candidates=choose_pre2026_candidates(x,t)
    candidates.to_csv(a.outdir/'pre2026_m1_ambiguity_candidates.csv',index=False)
    if candidates.empty: raise RuntimeError('No pre-2026 ambiguity-resolvable candidates')
    print(f'candidates={len(candidates)}',flush=True)
    events=build_event_table(x,t,candidates)
    print(f'exact replay event rows={len(events)} unique entries={events.entry_time_msc.nunique()}',flush=True)
    files=attach_file_ranges(a.audit)
    exact=replay_ticks(a.raw_zip,files,events)
    exact.to_parquet(a.outdir/'tick_resolved_events.parquet',index=False)
    summary=summarize_configs(exact); summary.to_csv(a.outdir/'config_year_exact_summary.csv',index=False)
    transfer=build_transfer(exact,candidates); transfer.to_csv(a.outdir/'candidate_transfer_exact.csv',index=False)
    p=portfolio(exact,transfer)
    if not p.empty: p.to_csv(a.outdir/'locked_portfolio_exact_trades.csv',index=False)
    yp=yearly(p); yp.to_csv(a.outdir/'locked_portfolio_yearly.csv',index=False)
    p26=p[p.entry_year.eq(2026)] if not p.empty else pd.DataFrame(); s26=stats(p26.R_exact.to_numpy(float)) if not p26.empty else stats([])
    locked=int(transfer.locked_before_2026.sum()); pos=int((transfer.locked_before_2026&transfer.final_2026_pass).sum())
    # exact TP-first frequency among formerly ambiguous cases isn't directly labelled per event here;
    # the exact strategy EV is the authoritative result.
    verdict='FAIL_TICK_ORDER' if locked==0 else ('PASS' if s26['n']>=20 and s26['mean_R'] is not None and s26['mean_R']>0 and s26['pf'] is not None and s26['pf']>1.05 else 'FAIL_OOS')
    out={'lab':'XAU_PRICE_TIME_ALOGICAL_TICK_ORDER_SHORT_RESPONSE_LAB_009','raw_tick_rows_expected':158961208,
         'm1_pre2026_candidate_configs':int(len(candidates)),'exact_event_rows':int(len(exact)),'exact_valid_rows':int(np.isfinite(exact.R_exact).sum()),
         'locked_configs_before_2026':locked,'locked_configs_positive_2026':pos,'final_2026_locked_portfolio':s26,
         'target_atr':TARGET_ATR,'stop_atr':STOP_ATR,'rr':RR,'horizons_min':sorted(HORIZONS),'qreq_pre2026_max':QREQ_MAX,
         'selection_note':'candidate set uses M1 ambiguity bounds through 2025 only; exact tick selection uses 2023-24 discovery + 2025 validation; 2026 untouched','verdict':verdict}
    (a.outdir/'verdict.json').write_text(json.dumps(out,indent=2,default=str)); print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
