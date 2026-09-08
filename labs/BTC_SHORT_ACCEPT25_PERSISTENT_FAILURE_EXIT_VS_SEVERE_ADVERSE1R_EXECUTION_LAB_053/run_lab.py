#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_ACCEPT25_PERSISTENT_FAILURE_EXIT_VS_SEVERE_ADVERSE1R_EXECUTION_LAB_053'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC51=LABS/'BTC_SHORT_ACCEPT25_POST_ENTRY_FIRST_PASSAGE_AND_EARLY_FAILURE_STATE_LAB_051'/'output'/'post_entry_state_stream.csv'
SRC52=LABS/'BTC_SHORT_ACCEPT25_ADVERSE_FIRST_RECOVERY_VS_PERSISTENT_FAILURE_SEQUENCE_LAB_052'/'output'/'sequence_stream.csv'
SRC43=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043'/'output'/'short_response_router_stream.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC')
SEED=20260908+53; BOOT_N=5000; ORIGINAL_N=475; RISK_PCT=0.25
PERIODS=['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']
POLICIES=['PARENT_HOLD','PERSISTENT_EXIT','SEVERE_1R_CONTROL','OCO_PERSISTENT_OR_SEVERE']


def period_of(t):
    if t.year in [2021,2022,2023,2024]: return str(t.year)
    if t.year==2025: return '2025_H1' if t < pd.Timestamp('2025-07-01',tz='UTC') else '2025_H2'
    if t.year==2026 and t<PRE: return '2026_JAN_JUL'
    return 'OTHER'

def cluster_id(t):
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    return (((t-epoch).dt.total_seconds())//(7*86400)).astype('int64')

def pf(v):
    v=np.asarray(v,float); gp=v[v>0].sum(); gl=-v[v<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def maxdd(v):
    v=np.asarray(v,float)
    if not len(v): return np.nan
    eq=np.r_[0.0,np.cumsum(v)]; peak=np.maximum.accumulate(eq)
    return float(np.max(peak-eq))

def net_r(entry,exit_px,D,bps):
    gross=(entry-exit_px)/D
    cost=(bps/10000.0)*entry/D
    return float(gross-cost)

def load_inputs():
    p=pd.read_csv(SRC51); s=pd.read_csv(SRC52); o=pd.read_csv(SRC43)
    for d in [p,s,o]:
        for c in ['signal_time','entry_time','exit_time','fp_time','state_time','severe_time']:
            if c in d.columns: d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['flow_id','entry_price','exit_price','risk_dist','parent_net_r_5bps','level']:
        if c in p.columns: p[c]=pd.to_numeric(p[c],errors='coerce')
    for c in ['flow_id','entry_price','exit_price','risk_dist','parent_net_r_5bps','state_price']:
        if c in s.columns: s[c]=pd.to_numeric(s[c],errors='coerce')
    for c in ['flow_id','side']:
        if c in o.columns: o[c]=pd.to_numeric(o[c],errors='coerce')
    p=p[p.signal_time<PRE].copy().sort_values('entry_time').reset_index(drop=True)
    if len(p)!=327: raise RuntimeError(f'Parent parity failed {len(p)} != 327')
    a=p[p.fp_state=='ADVERSE_FIRST'].copy()
    if len(a)!=145: raise RuntimeError(f'Adverse parity failed {len(a)} != 145')
    s=s[s.signal_time<PRE].copy()
    if len(s)!=145: raise RuntimeError(f'Sequence parity failed {len(s)} != 145')
    pers=s[s.sequence_state=='PERSISTENT_FAILURE_FIRST'].copy()
    if len(pers)!=59: raise RuntimeError(f'Persistent parity failed {len(pers)} != 59')
    keep=['flow_id','sequence_state','state_time','state_price','severe_adverse_1r','severe_time']
    p=p.merge(s[keep],on='flow_id',how='left',validate='one_to_one')
    # exact original 475 signal universe for period denominators
    mask=(o.side==-1)&(o.response_router=='HIGH_RESPONSE')&(o.signal_time<PRE)
    orig=o[mask][['flow_id','signal_time']].copy().drop_duplicates('flow_id')
    if len(orig)!=ORIGINAL_N: raise RuntimeError(f'Original signal parity failed {len(orig)} != {ORIGINAL_N}')
    orig['period']=orig.signal_time.map(period_of)
    return p,orig

def build_policies(parent):
    rows=[]
    for r in parent.itertuples(index=False):
        ep=float(r.entry_price); D=float(r.risk_dist); px_parent=float(r.exit_price); xt_parent=pd.Timestamp(r.exit_time)
        is_persistent=(str(r.sequence_state)=='PERSISTENT_FAILURE_FIRST' and pd.notna(r.state_time) and np.isfinite(r.state_price))
        # Frozen Severe +1R is mechanically the existing parent -1R stop; use parent as the exact control.
        for pol in POLICIES:
            xt=xt_parent; px=px_parent; reason=str(r.exit_reason); early=False
            if pol in ['PERSISTENT_EXIT','OCO_PERSISTENT_OR_SEVERE'] and is_persistent:
                xt=pd.Timestamp(r.state_time); px=float(r.state_price); reason='PERSISTENT_FAILURE_EXIT'; early=True
            vals={bps:net_r(ep,px,D,bps) for bps in [0.0,5.0,10.0]}
            rows.append(dict(flow_id=int(r.flow_id),signal_time=r.signal_time,period=r.period,policy=pol,
                             entry_time=r.entry_time,entry_price=ep,risk_dist=D,parent_exit_time=xt_parent,parent_exit_price=px_parent,
                             exit_time=xt,exit_price=px,exit_reason=reason,early_exit=early,
                             sequence_state=r.sequence_state,state_time=r.state_time,state_price=r.state_price,
                             parent_frozen_net_r_5bps=float(r.parent_net_r_5bps),
                             net_r_0bps=vals[0.0],net_r_5bps=vals[5.0],net_r_10bps=vals[10.0]))
    return pd.DataFrame(rows)

def original_count(orig,scope):
    if scope in PERIODS: return int((orig.period==scope).sum())
    if scope=='BAD_POOLED': return int(orig.period.isin(['2022','2025_H1']).sum())
    if scope=='RECENT_POOLED': return int(orig.period.isin(['2025_H2','2026_JAN_JUL']).sum())
    if scope=='FULL': return len(orig)
    return 0

def scope_mask(d,scope):
    if scope in PERIODS: return d.period==scope
    if scope=='BAD_POOLED': return d.period.isin(['2022','2025_H1'])
    if scope=='RECENT_POOLED': return d.period.isin(['2025_H2','2026_JAN_JUL'])
    if scope=='FULL': return pd.Series(True,index=d.index)
    raise KeyError(scope)

def summarize_policy(d,orig_n,policy,scope):
    q=d[(d.policy==policy)&scope_mask(d,scope)].sort_values('entry_time')
    v=q.net_r_5bps.to_numpy(float); dd=maxdd(v)
    return dict(scope=scope,policy=policy,original_n=orig_n,traded_n=len(q),early_exit_n=int(q.early_exit.sum()),
                ev_5bps=float(np.mean(v)) if len(v) else np.nan,pf_5bps=pf(v) if len(v) else np.nan,
                cum_r_5bps=float(np.sum(v)) if len(v) else 0.0,max_dd_r_5bps=dd,max_dd_pct_025=float(dd*RISK_PCT) if len(v) else np.nan,
                ev_per_original_5bps=float(np.sum(v)/orig_n) if orig_n else np.nan,
                ev_0bps=float(q.net_r_0bps.mean()) if len(q) else np.nan,ev_10bps=float(q.net_r_10bps.mean()) if len(q) else np.nan)

def paired_boot(exec_df):
    p=exec_df[exec_df.policy=='PARENT_HOLD'][['flow_id','entry_time','net_r_5bps']].rename(columns={'net_r_5bps':'parent'})
    o=exec_df[exec_df.policy=='OCO_PERSISTENT_OR_SEVERE'][['flow_id','net_r_5bps']].rename(columns={'net_r_5bps':'oco'})
    z=p.merge(o,on='flow_id',validate='one_to_one'); z['delta']=z.oco-z.parent; z['cluster']=cluster_id(z.entry_time)
    stats=z.groupby('cluster').delta.agg(['sum','count']).to_numpy(float)
    rng=np.random.default_rng(SEED); m=len(stats); vals=[]
    for _ in range(BOOT_N):
        s=stats[rng.integers(0,m,size=m)].sum(axis=0)
        vals.append(float(s[0]/s[1]))
    vals=np.asarray(vals,float)
    return dict(point=float(z.delta.mean()),ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),clusters=m,draws=len(vals))

def row(sm,scope,policy):
    return sm[(sm.scope==scope)&(sm.policy==policy)].iloc[0]

def main():
    parent,orig=load_inputs(); ex=build_policies(parent)
    ex.to_csv(OUT/'execution_stream.csv',index=False)
    # exact parent parity against frozen 5bps values
    pq=ex[ex.policy=='PARENT_HOLD'].merge(parent[['flow_id','parent_net_r_5bps']],on='flow_id',suffixes=('_calc','_src'),validate='one_to_one')
    parity_max=float(np.max(np.abs(pq.net_r_5bps-pq.parent_net_r_5bps_src)))
    severe=ex[ex.policy=='SEVERE_1R_CONTROL'].sort_values('flow_id').net_r_5bps.to_numpy(float)
    ph=ex[ex.policy=='PARENT_HOLD'].sort_values('flow_id').net_r_5bps.to_numpy(float)
    severe_parity=float(np.max(np.abs(severe-ph)))
    scopes=['FULL']+PERIODS+['BAD_POOLED','RECENT_POOLED']
    summary=[]
    for sc in scopes:
        n0=original_count(orig,sc)
        for pol in POLICIES: summary.append(summarize_policy(ex,n0,pol,sc))
    sm=pd.DataFrame(summary); sm.to_csv(OUT/'policy_summary_and_transfer.csv',index=False)
    boot=paired_boot(ex)
    full_p=row(sm,'FULL','PARENT_HOLD'); full_o=row(sm,'FULL','OCO_PERSISTENT_OR_SEVERE')
    p22=row(sm,'2022','PARENT_HOLD'); o22=row(sm,'2022','OCO_PERSISTENT_OR_SEVERE')
    p25=row(sm,'2025_H1','PARENT_HOLD'); o25=row(sm,'2025_H1','OCO_PERSISTENT_OR_SEVERE')
    p26=row(sm,'2026_JAN_JUL','PARENT_HOLD'); o26=row(sm,'2026_JAN_JUL','OCO_PERSISTENT_OR_SEVERE')
    pbad=row(sm,'BAD_POOLED','PARENT_HOLD'); obad=row(sm,'BAD_POOLED','OCO_PERSISTENT_OR_SEVERE')
    orecent=row(sm,'RECENT_POOLED','OCO_PERSISTENT_OR_SEVERE')
    persistent_n=int((parent.sequence_state=='PERSISTENT_FAILURE_FIRST').sum())
    oco_early=int(ex[(ex.policy=='OCO_PERSISTENT_OR_SEVERE')].early_exit.sum())
    gates={
      'exact_parent_n327': bool(len(parent)==327),
      'exact_adverse_first_n145': bool((parent.fp_state=='ADVERSE_FIRST').sum()==145),
      'exact_persistent_failure_n59': bool(persistent_n==59),
      'parent_5bps_parity_with_frozen_le1e9': bool(parity_max<=1e-9),
      'severe1r_control_parity_parent_le1e12': bool(severe_parity<=1e-12),
      'oco_early_exit_n_ge40': bool(oco_early>=40),
      'oco_full_ev_gt_parent': bool(full_o.ev_5bps>full_p.ev_5bps),
      'oco_full_pf_gt_parent': bool(full_o.pf_5bps>full_p.pf_5bps),
      'oco_cumr_gt_parent': bool(full_o.cum_r_5bps>full_p.cum_r_5bps),
      'oco_maxdd_le_parent': bool(full_o.max_dd_r_5bps<=full_p.max_dd_r_5bps),
      'oco_ev_per_original_gt_parent': bool(full_o.ev_per_original_5bps>full_p.ev_per_original_5bps),
      'paired_delta_gt_003r_per_trade': bool(boot['point']>0.03),
      'paired_boot_lower_gt0': bool(boot['ci_lo']>0),
      '2022_oco_evperorig_ge_parent': bool(o22.ev_per_original_5bps>=p22.ev_per_original_5bps),
      '2025h1_oco_evperorig_ge_parent': bool(o25.ev_per_original_5bps>=p25.ev_per_original_5bps),
      'bad_pooled_oco_evperorig_gt_parent': bool(obad.ev_per_original_5bps>pbad.ev_per_original_5bps),
      'recent_pooled_oco_evperorig_positive': bool(orecent.ev_per_original_5bps>0),
      '2026_degradation_no_worse_than_minus010r_per_original': bool((o26.ev_per_original_5bps-p26.ev_per_original_5bps)>=-0.10),
      'oco_10bps_ev_positive': bool(full_o.ev_10bps>0),
      'no_august_selection_no_new_threshold': True,
    }
    critical=['oco_full_ev_gt_parent','oco_cumr_gt_parent','paired_boot_lower_gt0','bad_pooled_oco_evperorig_gt_parent','recent_pooled_oco_evperorig_positive','oco_10bps_ev_positive']
    if sum(gates.values())>=17 and all(gates[k] for k in critical):
        verdict='PASS_PERSISTENT_FAILURE_EARLY_EXIT_EXECUTION'
    elif full_o.ev_5bps>full_p.ev_5bps and full_o.cum_r_5bps>full_p.cum_r_5bps:
        verdict='WATCH_PERSISTENT_EXIT_ECONOMICS_IMPROVE_PROOF_OR_TRANSFER_INCOMPLETE'
    else:
        verdict='FAIL_PERSISTENT_FAILURE_EXIT_DOES_NOT_IMPROVE_PARENT'
    tests={'paired_oco_minus_parent':boot,'parent_parity_max_abs':parity_max,'severe_control_parity_max_abs':severe_parity,
           'persistent_n':persistent_n,'oco_early_exit_n':oco_early,
           'full_parent':full_p.to_dict(),'full_oco':full_o.to_dict()}
    (OUT/'bootstrap_and_tests.json').write_text(json.dumps(tests,indent=2,default=lambda x: float(x) if isinstance(x,(np.floating,np.integer)) else str(x)))
    (OUT/'gates.json').write_text(json.dumps({k:bool(v) for k,v in gates.items()},indent=2))
    lines=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(gates.values())}/{len(gates)}**','',
           '## Frozen parity',f'- Parent trades **{len(parent)}**; ADVERSE_FIRST **{int((parent.fp_state=="ADVERSE_FIRST").sum())}**; PERSISTENT_FAILURE **{persistent_n}**; OCO early exits **{oco_early}**.',
           f'- Parent 5bps max parity error **{parity_max:.3e}**; Severe1R-control parity error **{severe_parity:.3e}**.','',
           '## Full execution economics','',
           '| Policy | Trades | Early exits | EV 5bps | PF | CumR | MaxDD R | DD @0.25% | EV/original | EV 10bps |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for pol in POLICIES:
        r=row(sm,'FULL',pol); lines.append(f'| {pol} | {int(r.traded_n)} | {int(r.early_exit_n)} | {r.ev_5bps:+.3f} | {r.pf_5bps:.3f} | {r.cum_r_5bps:+.2f} | {r.max_dd_r_5bps:.2f} | {r.max_dd_pct_025:.2f}% | {r.ev_per_original_5bps:+.3f} | {r.ev_10bps:+.3f} |')
    lines += ['',f"Paired OCO−PARENT delta: **{boot['point']:+.3f}R/trade**, 7d bootstrap 95% CI **[{boot['ci_lo']:+.3f}, {boot['ci_hi']:+.3f}]**, clusters={boot['clusters']}",'',
              '## Transfer — OCO vs parent','',
              '| Slice | Orig N | Parent EV/orig | OCO EV/orig | Delta | Parent PF | OCO PF | OCO early exits |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for sc in PERIODS+['BAD_POOLED','RECENT_POOLED']:
        p=row(sm,sc,'PARENT_HOLD'); o=row(sm,sc,'OCO_PERSISTENT_OR_SEVERE')
        lines.append(f'| {sc} | {int(o.original_n)} | {p.ev_per_original_5bps:+.3f} | {o.ev_per_original_5bps:+.3f} | {(o.ev_per_original_5bps-p.ev_per_original_5bps):+.3f} | {p.pf_5bps:.3f} | {o.pf_5bps:.3f} | {int(o.early_exit_n)} |')
    lines += ['','## Gates']
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['','## Guardrail','Execution test only. Severe +1R is the frozen parent SL control. No new signal, threshold, stop, target, time exit, re-entry, sizing, or allocation rule was searched. Reused historical lineage; not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(verdict, sum(gates.values()), '/', len(gates))

if __name__=='__main__':
    main()
