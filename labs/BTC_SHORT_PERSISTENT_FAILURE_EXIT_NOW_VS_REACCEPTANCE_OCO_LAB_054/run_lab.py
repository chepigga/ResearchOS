#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_PERSISTENT_FAILURE_EXIT_NOW_VS_REACCEPTANCE_OCO_LAB_054'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC53=LABS/'BTC_SHORT_ACCEPT25_PERSISTENT_FAILURE_EXIT_VS_SEVERE_ADVERSE1R_EXECUTION_LAB_053'/'output'/'execution_stream.csv'
SRC52=LABS/'BTC_SHORT_ACCEPT25_ADVERSE_FIRST_RECOVERY_VS_PERSISTENT_FAILURE_SEQUENCE_LAB_052'/'output'/'sequence_stream.csv'
SRC43=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043'/'output'/'short_response_router_stream.csv'
R35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab035',R35); L35=importlib.util.module_from_spec(spec); spec.loader.exec_module(L35); L35.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC'); SEED=20260908+54; BOOT_N=5000; RISK_PCT=.25
PERIODS=['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']
POLICIES=['PARENT_HOLD','EXIT_NOW','WAIT_REACCEPT_OCO']

def cluster_id(t):
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); return (((t-epoch).dt.total_seconds())//(7*86400)).astype('int64')
def pf(v):
    v=np.asarray(v,float); gp=v[v>0].sum(); gl=-v[v<0].sum(); return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)
def maxdd(v):
    v=np.asarray(v,float); eq=np.r_[0.,np.cumsum(v)]; peak=np.maximum.accumulate(eq); return float(np.max(peak-eq))
def net_r(entry,exit_px,D,bps):
    return float((entry-exit_px)/D - (bps/10000.)*entry/D)
def period_of(t):
    if t.year in [2021,2022,2023,2024]: return str(t.year)
    if t.year==2025: return '2025_H1' if t<pd.Timestamp('2025-07-01',tz='UTC') else '2025_H2'
    if t.year==2026 and t<PRE: return '2026_JAN_JUL'
    return 'OTHER'

def load_inputs():
    e=pd.read_csv(SRC53); s=pd.read_csv(SRC52); o=pd.read_csv(SRC43)
    for d in [e,s,o]:
        for c in ['signal_time','entry_time','parent_exit_time','exit_time','state_time','fp_time']:
            if c in d.columns: d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['flow_id','entry_price','risk_dist','parent_exit_price','exit_price','state_price','net_r_5bps','net_r_10bps']:
        if c in e.columns: e[c]=pd.to_numeric(e[c],errors='coerce')
    for c in ['flow_id','state_price']:
        if c in s.columns: s[c]=pd.to_numeric(s[c],errors='coerce')
    ph=e[e.policy=='PARENT_HOLD'].copy().sort_values('entry_time').reset_index(drop=True)
    ex=e[e.policy=='PERSISTENT_EXIT'][['flow_id','exit_time','exit_price','net_r_5bps']].rename(columns={'exit_time':'exit_now_time','exit_price':'exit_now_price','net_r_5bps':'exit_now_net5'})
    if len(ph)!=327: raise RuntimeError(f'parent {len(ph)} !=327')
    ph=ph.merge(ex,on='flow_id',validate='one_to_one')
    seq=s[s.signal_time<PRE].copy(); pers=seq[seq.sequence_state=='PERSISTENT_FAILURE_FIRST'][['flow_id','state_time','state_price']].copy()
    if len(seq)!=145: raise RuntimeError(f'adverse sequence {len(seq)} !=145')
    if len(pers)!=59: raise RuntimeError(f'persistent {len(pers)} !=59')
    ph=ph.drop(columns=['state_time','state_price'],errors='ignore').merge(pers,on='flow_id',how='left',validate='one_to_one')
    mask=(o.side==-1)&(o.response_router=='HIGH_RESPONSE')&(o.signal_time<PRE)
    orig=o[mask][['flow_id','signal_time']].drop_duplicates('flow_id').copy(); orig['signal_time']=pd.to_datetime(orig.signal_time,utc=True); orig['period']=orig.signal_time.map(period_of)
    if len(orig)!=475: raise RuntimeError(f'original {len(orig)} !=475')
    return ph,seq,pers,orig

def wait_outcome(r,fut):
    # non-persistent = parent
    if pd.isna(r.state_time) or not np.isfinite(r.state_price):
        return r.parent_exit_time,float(r.parent_exit_price),str(r.exit_reason),'NO_PERSISTENT_PARENT',False
    st=pd.Timestamp(r.state_time); xt=pd.Timestamp(r.parent_exit_time); ep=float(r.entry_price); D=float(r.risk_dist); sp=float(r.state_price)
    ext=sp+0.25*D; stop=ep+D
    bars=fut[(fut.index>st)&(fut.index<=xt)]
    for tt,b in bars.iterrows():
        is_exit_bar=(tt==xt)
        # frozen parent exit remains active. For SL, extension can win only if it lies strictly before the stop.
        if is_exit_bar and str(r.exit_reason)=='SL' and ext>=stop:
            return xt,float(r.parent_exit_price),str(r.exit_reason),'PARENT_BEFORE_EXTENSION',False
        if float(b.high)>=ext:
            return tt,float(ext),'FAILURE_EXTENSION_025_EXIT','EXTENSION_EXIT',True
        # close-based reaccept cannot use intrabar SL/TP exit-bar close
        if not (is_exit_bar and str(r.exit_reason) in ['SL','TP']) and float(b.close)<=ep:
            return xt,float(r.parent_exit_price),str(r.exit_reason),'REACCEPT_PARENT_HOLD',False
        if is_exit_bar:
            return xt,float(r.parent_exit_price),str(r.exit_reason),'UNRESOLVED_PARENT',False
    return xt,float(r.parent_exit_price),str(r.exit_reason),'UNRESOLVED_PARENT',False

def build(parent,fut):
    rows=[]
    for r in parent.itertuples(index=False):
        for pol in POLICIES:
            if pol=='PARENT_HOLD': xt=r.parent_exit_time; px=float(r.parent_exit_price); rs=str(r.exit_reason); branch='PARENT'; early=False
            elif pol=='EXIT_NOW': xt=r.exit_now_time; px=float(r.exit_now_price); rs='PERSISTENT_FAILURE_EXIT' if pd.notna(r.state_time) else str(r.exit_reason); branch='EXIT_NOW' if pd.notna(r.state_time) else 'PARENT'; early=bool(pd.notna(r.state_time))
            else: xt,px,rs,branch,early=wait_outcome(r,fut)
            rows.append(dict(flow_id=int(r.flow_id),signal_time=r.signal_time,period=r.period,policy=pol,entry_time=r.entry_time,entry_price=float(r.entry_price),risk_dist=float(r.risk_dist),parent_exit_time=r.parent_exit_time,parent_exit_price=float(r.parent_exit_price),exit_time=xt,exit_price=px,exit_reason=rs,oco_branch=branch,early_exit=early,state_time=r.state_time,state_price=r.state_price,net_r_5bps=net_r(float(r.entry_price),px,float(r.risk_dist),5.),net_r_10bps=net_r(float(r.entry_price),px,float(r.risk_dist),10.)))
    return pd.DataFrame(rows)
def scope_mask(d,sc):
    if sc in PERIODS: return d.period==sc
    if sc=='BAD_POOLED': return d.period.isin(['2022','2025_H1'])
    if sc=='RECENT_POOLED': return d.period.isin(['2025_H2','2026_JAN_JUL'])
    return pd.Series(True,index=d.index)
def orig_n(o,sc):
    if sc in PERIODS: return int((o.period==sc).sum())
    if sc=='BAD_POOLED': return int(o.period.isin(['2022','2025_H1']).sum())
    if sc=='RECENT_POOLED': return int(o.period.isin(['2025_H2','2026_JAN_JUL']).sum())
    return len(o)
def summary(d,o,sc,pol):
    q=d[(d.policy==pol)&scope_mask(d,sc)].sort_values('entry_time'); v=q.net_r_5bps.to_numpy(float); n0=orig_n(o,sc); dd=maxdd(v)
    return dict(scope=sc,policy=pol,original_n=n0,traded_n=len(q),early_exit_n=int(q.early_exit.sum()),ev_5bps=float(v.mean()),pf_5bps=pf(v),cum_r_5bps=float(v.sum()),max_dd_r_5bps=dd,max_dd_pct_025=dd*RISK_PCT,ev_per_original_5bps=float(v.sum()/n0),ev_10bps=float(q.net_r_10bps.mean()))
def paired(d,a,b):
    x=d[d.policy==a][['flow_id','entry_time','net_r_5bps']].rename(columns={'net_r_5bps':'a'}); y=d[d.policy==b][['flow_id','net_r_5bps']].rename(columns={'net_r_5bps':'b'}); z=x.merge(y,on='flow_id'); z['delta']=z.a-z.b; z['cluster']=cluster_id(z.entry_time)
    st=z.groupby('cluster').delta.agg(['sum','count']).to_numpy(float); rng=np.random.default_rng(SEED+(1 if b=='EXIT_NOW' else 2)); m=len(st); vals=[]
    for _ in range(BOOT_N):
        s=st[rng.integers(0,m,size=m)].sum(axis=0); vals.append(float(s[0]/s[1]))
    vals=np.asarray(vals); return dict(point=float(z.delta.mean()),ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),clusters=m)
def row(sm,sc,pol): return sm[(sm.scope==sc)&(sm.policy==pol)].iloc[0]

def main():
    parent,seq,pers,orig=load_inputs(); fut=L35.download_futures(); d=build(parent,fut); d.to_csv(OUT/'execution_stream.csv',index=False)
    # parity
    p=d[d.policy=='PARENT_HOLD'].sort_values('flow_id'); src=parent.sort_values('flow_id'); parent_parity=float(np.max(np.abs(p.net_r_5bps.to_numpy()-src.net_r_5bps.to_numpy())))
    x=d[d.policy=='EXIT_NOW'].sort_values('flow_id'); exit_parity=float(np.max(np.abs(x.net_r_5bps.to_numpy()-src.exit_now_net5.to_numpy())))
    scopes=['FULL']+PERIODS+['BAD_POOLED','RECENT_POOLED']; sm=pd.DataFrame([summary(d,orig,sc,pol) for sc in scopes for pol in POLICIES]); sm.to_csv(OUT/'policy_summary_and_transfer.csv',index=False)
    pe=paired(d,'WAIT_REACCEPT_OCO','EXIT_NOW'); pp=paired(d,'WAIT_REACCEPT_OCO','PARENT_HOLD')
    pers_wait=d[(d.policy=='WAIT_REACCEPT_OCO')&d.flow_id.isin(pers.flow_id)]
    counts=pers_wait.oco_branch.value_counts().to_dict(); resolved=int(counts.get('REACCEPT_PARENT_HOLD',0)+counts.get('EXTENSION_EXIT',0)); rec=int(counts.get('REACCEPT_PARENT_HOLD',0)); ext=int(counts.get('EXTENSION_EXIT',0))
    full_w=row(sm,'FULL','WAIT_REACCEPT_OCO'); full_e=row(sm,'FULL','EXIT_NOW'); bad_w=row(sm,'BAD_POOLED','WAIT_REACCEPT_OCO'); bad_e=row(sm,'BAD_POOLED','EXIT_NOW'); recent_w=row(sm,'RECENT_POOLED','WAIT_REACCEPT_OCO'); y26w=row(sm,'2026_JAN_JUL','WAIT_REACCEPT_OCO'); y26e=row(sm,'2026_JAN_JUL','EXIT_NOW')
    gates={
      'exact_parent_n327':len(parent)==327,'exact_adverse_n145':len(seq)==145,'exact_persistent_n59':len(pers)==59,
      'path_coverage_ge99pct':float(parent.entry_time.isin(fut.index).mean())>=.99,
      'parent_parity_le1e9':parent_parity<=1e-9,'exit_now_parity_le1e9':exit_parity<=1e-9,
      'oco_resolved_n_ge30':resolved>=30,'reaccept_n_ge10':rec>=10,'extension_n_ge10':ext>=10,
      'wait_full_ev_gt_exit':full_w.ev_5bps>full_e.ev_5bps,'wait_full_pf_gt_exit':full_w.pf_5bps>full_e.pf_5bps,'wait_cumr_gt_exit':full_w.cum_r_5bps>full_e.cum_r_5bps,'wait_dd_le_exit':full_w.max_dd_r_5bps<=full_e.max_dd_r_5bps,
      'paired_wait_exit_delta_gt0':pe['point']>0,'paired_wait_exit_boot_lower_gt0':pe['ci_lo']>0,
      '2026_wait_evorig_gt_exit':y26w.ev_per_original_5bps>y26e.ev_per_original_5bps,
      'bad_wait_not_worse_than_exit_minus002':bad_w.ev_per_original_5bps>=bad_e.ev_per_original_5bps-.02,
      'recent_wait_evorig_positive':recent_w.ev_per_original_5bps>0,'wait_10bps_ev_positive':full_w.ev_10bps>0,
      'no_august_no_new_threshold':True}
    critical=['exact_parent_n327','exact_adverse_n145','exact_persistent_n59','path_coverage_ge99pct','parent_parity_le1e9','exit_now_parity_le1e9','oco_resolved_n_ge30','reaccept_n_ge10','extension_n_ge10','wait_full_ev_gt_exit','wait_full_pf_gt_exit','wait_cumr_gt_exit','wait_dd_le_exit','paired_wait_exit_delta_gt0','paired_wait_exit_boot_lower_gt0','2026_wait_evorig_gt_exit','bad_wait_not_worse_than_exit_minus002','recent_wait_evorig_positive','wait_10bps_ev_positive','no_august_no_new_threshold']
    if all(gates[k] for k in critical): verdict='PASS_WAIT_REACCEPT_OCO_BEATS_EXIT_NOW'
    elif full_w.ev_5bps>full_e.ev_5bps and pe['point']>0: verdict='WATCH_WAIT_OCO_ECONOMICS_IMPROVE_PROOF_OR_TRANSFER_INCOMPLETE'
    else: verdict='FAIL_WAIT_OCO_DOES_NOT_BEAT_EXIT_NOW'
    tests={'parent_parity':parent_parity,'exit_now_parity':exit_parity,'wait_minus_exit':pe,'wait_minus_parent':pp,'oco_counts':counts,'resolved':resolved,'reaccept_n':rec,'extension_n':ext}
    (OUT/'bootstrap_and_tests.json').write_text(json.dumps(tests,indent=2)); (OUT/'gates.json').write_text(json.dumps({k:bool(v) for k,v in gates.items()},indent=2))
    lines=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(gates.values())}/{len(gates)}**','',f'- Parent N **{len(parent)}**; ADVERSE_FIRST **{len(seq)}**; PERSISTENT **{len(pers)}**; OCO resolved **{resolved}** (REACCEPT {rec}, EXTENSION {ext}).',f'- Parent parity **{parent_parity:.3e}**; EXIT_NOW parity **{exit_parity:.3e}**.','', '## Full economics','','| Policy | EV 5bps | PF | CumR | MaxDD R | DD @0.25% | EV/original | EV 10bps |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for pol in POLICIES:
        r=row(sm,'FULL',pol); lines.append(f'| {pol} | {r.ev_5bps:+.3f} | {r.pf_5bps:.3f} | {r.cum_r_5bps:+.2f} | {r.max_dd_r_5bps:.2f} | {r.max_dd_pct_025:.2f}% | {r.ev_per_original_5bps:+.3f} | {r.ev_10bps:+.3f} |')
    lines += ['',f"WAIT−EXIT paired delta **{pe['point']:+.3f}R/trade**, 7d bootstrap 95% CI **[{pe['ci_lo']:+.3f}, {pe['ci_hi']:+.3f}]**.",f"WAIT−PARENT paired delta **{pp['point']:+.3f}R/trade**, 95% CI **[{pp['ci_lo']:+.3f}, {pp['ci_hi']:+.3f}]**.",'','## Transfer','','| Slice | Parent EV/orig | EXIT NOW | WAIT OCO | WAIT−EXIT |','|---|---:|---:|---:|---:|']
    for sc in PERIODS+['BAD_POOLED','RECENT_POOLED']:
        a=row(sm,sc,'PARENT_HOLD'); b=row(sm,sc,'EXIT_NOW'); c=row(sm,sc,'WAIT_REACCEPT_OCO'); lines.append(f'| {sc} | {a.ev_per_original_5bps:+.3f} | {b.ev_per_original_5bps:+.3f} | {c.ev_per_original_5bps:+.3f} | {c.ev_per_original_5bps-b.ev_per_original_5bps:+.3f} |')
    lines += ['','## Gates']+[f"- {'PASS' if v else 'FAIL'} — `{k}`" for k,v in gates.items()]+['','## Guardrail','Final reused-sample post-failure management decision LAB. No further sequence refinement is promoted from this lineage. Not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(lines))
if __name__=='__main__': main()
