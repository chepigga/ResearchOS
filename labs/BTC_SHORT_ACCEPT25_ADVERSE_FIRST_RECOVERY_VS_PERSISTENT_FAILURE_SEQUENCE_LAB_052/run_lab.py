#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_ACCEPT25_ADVERSE_FIRST_RECOVERY_VS_PERSISTENT_FAILURE_SEQUENCE_LAB_052'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC51=LABS/'BTC_SHORT_ACCEPT25_POST_ENTRY_FIRST_PASSAGE_AND_EARLY_FAILURE_STATE_LAB_051'/'output'/'post_entry_state_stream.csv'
R35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab035',R35)
L35=importlib.util.module_from_spec(spec); spec.loader.exec_module(L35); L35.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC')
SEED=20260908+52; BOOT_N=5000
PERIODS=['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']


def cluster_id(t):
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    return (((t-epoch).dt.total_seconds())//(7*86400)).astype('int64')


def load_adverse():
    d=pd.read_csv(SRC51)
    for c in ['signal_time','entry_time','exit_time','fp_time']:
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['flow_id','entry_price','exit_price','atr14','risk_dist','level','parent_net_r_5bps','fp_price','fp_minutes']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d[(d.fp_state=='ADVERSE_FIRST') & (d.signal_time<PRE)].copy()
    d=d.sort_values('fp_time').reset_index(drop=True)
    if len(d)!=145: raise RuntimeError(f'Frozen LAB051 ADVERSE_FIRST parity failed: {len(d)} != 145')
    return d


def close_path(fut,start,end,exit_reason):
    if pd.isna(start) or pd.isna(end): return fut.iloc[0:0]
    # only closes strictly after adverse-first state. Intrabar SL/TP exit-bar close is not observable.
    include_end=(str(exit_reason)=='TIME')
    if include_end: return fut[(fut.index>start)&(fut.index<=end)]
    return fut[(fut.index>start)&(fut.index<end)]


def barrier_path(fut,start,end):
    if pd.isna(start) or pd.isna(end): return fut.iloc[0:0]
    return fut[(fut.index>start)&(fut.index<=end)]


def analyze_one(r,fut):
    fp=pd.Timestamp(r.fp_time); xt=pd.Timestamp(r.exit_time)
    ep=float(r.entry_price); xp=float(r.exit_price); level=float(r.level); D=float(r.risk_dist)
    covered=bool(fp in fut.index and xt in fut.index and np.isfinite(ep) and np.isfinite(xp) and np.isfinite(level) and np.isfinite(D) and D>0)
    base=dict(flow_id=int(r.flow_id),signal_time=r.signal_time,period=r.period,entry_time=r.entry_time,fp_time=fp,fp_minutes=float(r.fp_minutes),
              exit_time=xt,exit_reason=r.exit_reason,entry_price=ep,exit_price=xp,level=level,risk_dist=D,parent_net_r_5bps=float(r.parent_net_r_5bps),covered=covered)
    if not covered:
        base.update(sequence_state='UNCOVERED',state_time=pd.NaT,state_price=np.nan,state_minutes_after_fp=np.nan,residual_r=np.nan,severe_adverse_1r=False,severe_time=pd.NaT)
        return base
    pc=close_path(fut,fp,xt,r.exit_reason)
    recovered_t=pd.NaT; recovered_px=np.nan
    persistent_t=pd.NaT; persistent_px=np.nan
    consec_above=0
    for tt,b in pc.iterrows():
        c=float(b.close)
        # OCO: on a closed bar, recovery at/below entry dominates because it cannot also be > level when level > entry;
        # if unusual level ordering exists, evaluate recovery first exactly as preregistered.
        if c<=ep:
            recovered_t=tt; recovered_px=c; break
        if c>level:
            consec_above += 1
            if consec_above>=2:
                persistent_t=tt; persistent_px=c; break
        else:
            consec_above=0
    if pd.notna(recovered_t):
        state='RECOVERED_FIRST'; st=recovered_t; sp=recovered_px
    elif pd.notna(persistent_t):
        state='PERSISTENT_FAILURE_FIRST'; st=persistent_t; sp=persistent_px
    else:
        state='UNRESOLVED'; st=pd.NaT; sp=np.nan
    residual=(sp-xp)/D if pd.notna(st) and np.isfinite(sp) else np.nan
    mins=(st-fp).total_seconds()/60.0 if pd.notna(st) else np.nan
    # Secondary audit: +1R adverse barrier after ADVERSE_FIRST and before recovery/state/end.
    end_bar=st if pd.notna(st) else xt
    pb=barrier_path(fut,fp,end_bar)
    severe_level=ep+1.0*D; severe=False; severe_t=pd.NaT
    for tt,b in pb.iterrows():
        if float(b.high)>=severe_level:
            severe=True; severe_t=tt; break
    base.update(sequence_state=state,state_time=st,state_price=sp,state_minutes_after_fp=mins,residual_r=float(residual) if np.isfinite(residual) else np.nan,
                severe_adverse_1r=bool(severe),severe_time=severe_t)
    return base


def state_summary(d,scope):
    rows=[]
    for s in ['RECOVERED_FIRST','PERSISTENT_FAILURE_FIRST','UNRESOLVED']:
        z=d[d.sequence_state==s]
        rows.append(dict(scope=scope,state=s,n=len(z),share=len(z)/len(d) if len(d) else np.nan,
                         residual_ev=float(z.residual_r.mean()) if z.residual_r.notna().any() else np.nan,
                         parent_ev=float(z.parent_net_r_5bps.mean()) if len(z) else np.nan,
                         median_minutes_after_fp=float(z.state_minutes_after_fp.median()) if z.state_minutes_after_fp.notna().any() else np.nan,
                         severe1r_share=float(z.severe_adverse_1r.mean()) if len(z) else np.nan))
    return pd.DataFrame(rows)


def contrast_boot(d,seed=SEED):
    z=d[d.sequence_state.isin(['RECOVERED_FIRST','PERSISTENT_FAILURE_FIRST']) & d.residual_r.notna()].copy()
    if z.empty: return dict(point=np.nan,recovered_ev=np.nan,persistent_ev=np.nan,ci_lo=np.nan,ci_hi=np.nan,clusters=0,draws=0)
    z['cluster']=cluster_id(z.fp_time)
    arr=[]
    for _,g in z.groupby('cluster'):
        r=g[g.sequence_state=='RECOVERED_FIRST'].residual_r.to_numpy(float)
        p=g[g.sequence_state=='PERSISTENT_FAILURE_FIRST'].residual_r.to_numpy(float)
        arr.append((r.sum(),len(r),p.sum(),len(p)))
    arr=np.asarray(arr,float); m=len(arr); rng=np.random.default_rng(seed); vals=[]
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0: vals.append(float(s[0]/s[1]-s[2]/s[3]))
    vals=np.asarray(vals,float)
    re=z[z.sequence_state=='RECOVERED_FIRST'].residual_r.mean(); pe=z[z.sequence_state=='PERSISTENT_FAILURE_FIRST'].residual_r.mean()
    return dict(point=float(re-pe),recovered_ev=float(re),persistent_ev=float(pe),
                ci_lo=float(np.quantile(vals,.025)) if len(vals) else np.nan,ci_hi=float(np.quantile(vals,.975)) if len(vals) else np.nan,
                clusters=m,draws=len(vals))


def scope_row(d,name,seed):
    b=contrast_boot(d,seed)
    rr=d[d.sequence_state=='RECOVERED_FIRST']; pp=d[d.sequence_state=='PERSISTENT_FAILURE_FIRST']; resolved=len(rr)+len(pp)
    return dict(scope=name,n=len(d),resolved_n=resolved,recovered_n=len(rr),persistent_n=len(pp),unresolved_n=int((d.sequence_state=='UNRESOLVED').sum()),
                recovered_residual=b['recovered_ev'],persistent_residual=b['persistent_ev'],gap=b['point'],boot_lo=b['ci_lo'],boot_hi=b['ci_hi'],
                recovered_parent_ev=float(rr.parent_net_r_5bps.mean()) if len(rr) else np.nan,
                persistent_parent_ev=float(pp.parent_net_r_5bps.mean()) if len(pp) else np.nan)


def main():
    parent=load_adverse(); fut=L35.download_futures()
    rows=[analyze_one(r,fut) for r in parent.itertuples(index=False)]
    d=pd.DataFrame(rows).sort_values('fp_time').reset_index(drop=True)
    d.to_csv(OUT/'sequence_stream.csv',index=False)
    coverage=float(d.covered.mean())
    full=state_summary(d,'FULL'); full.to_csv(OUT/'state_summary.csv',index=False)
    boot=contrast_boot(d)
    transfers=[]
    for i,p in enumerate(PERIODS): transfers.append(scope_row(d[d.period==p],p,SEED+100+i))
    transfers.append(scope_row(d[d.period.isin(['2022','2025_H1'])],'BAD_POOLED',SEED+500))
    transfers.append(scope_row(d[d.period.isin(['2025_H2','2026_JAN_JUL'])],'RECENT_POOLED',SEED+600))
    tr=pd.DataFrame(transfers); tr.to_csv(OUT/'transfer.csv',index=False)

    rr=d[d.sequence_state=='RECOVERED_FIRST']; pp=d[d.sequence_state=='PERSISTENT_FAILURE_FIRST']; resolved=len(rr)+len(pp)
    recovered_parent=float(rr.parent_net_r_5bps.mean()) if len(rr) else np.nan
    persistent_parent=float(pp.parent_net_r_5bps.mean()) if len(pp) else np.nan
    bad=tr[tr.scope=='BAD_POOLED'].iloc[0]; recent=tr[tr.scope=='RECENT_POOLED'].iloc[0]
    gates={
      'exact_lab051_adverse_first_n145': bool(len(d)==145),
      'path_coverage_ge99pct': bool(coverage>=.99),
      'sequence_resolved_n_ge60': bool(resolved>=60),
      'recovered_first_n_ge20': bool(len(rr)>=20),
      'persistent_failure_first_n_ge20': bool(len(pp)>=20),
      'recovered_residual_positive': bool(pd.notna(boot['recovered_ev']) and boot['recovered_ev']>0),
      'persistent_residual_negative': bool(pd.notna(boot['persistent_ev']) and boot['persistent_ev']<0),
      'residual_gap_ge0_30r': bool(pd.notna(boot['point']) and boot['point']>=.30),
      'residual_gap_boot_lower_gt0': bool(pd.notna(boot['ci_lo']) and boot['ci_lo']>0),
      'persistent_parent_ev_lt_recovered_parent_ev': bool(pd.notna(persistent_parent) and pd.notna(recovered_parent) and persistent_parent<recovered_parent),
      'bad_pooled_persistent_residual_negative': bool(pd.notna(bad.persistent_residual) and bad.persistent_residual<0),
      'bad_pooled_residual_gap_positive': bool(pd.notna(bad.gap) and bad.gap>0),
      'recent_pooled_recovered_residual_positive': bool(pd.notna(recent.recovered_residual) and recent.recovered_residual>0),
      'recent_pooled_persistent_residual_nonpositive': bool(pd.notna(recent.persistent_residual) and recent.persistent_residual<=0),
      'august_not_used_for_selection': True,
    }
    core_keys=list(gates.keys())[:10]
    transfer_pass=sum(gates[k] for k in list(gates.keys())[10:14])
    if all(gates[k] for k in core_keys) and transfer_pass>=3:
        verdict='PASS_ADVERSE_RECOVERY_VS_PERSISTENT_FAILURE_SEQUENCE'
    elif pd.notna(boot['point']) and boot['point']>0 and pd.notna(boot['persistent_ev']) and pd.notna(boot['recovered_ev']) and boot['persistent_ev']<boot['recovered_ev']:
        verdict='WATCH_SEQUENCE_DISCRIMINATIVE_PROOF_INCOMPLETE'
    else:
        verdict='FAIL_NO_ADVERSE_RECOVERY_PERSISTENT_FAILURE_SEQUENCE'

    tests={'primary':boot,'coverage':coverage,'resolved_n':resolved,'recovered_n':len(rr),'persistent_n':len(pp),
           'recovered_parent_ev':recovered_parent,'persistent_parent_ev':persistent_parent,
           'severe1r_share_all':float(d.severe_adverse_1r.mean()),
           'severe1r_share_recovered':float(rr.severe_adverse_1r.mean()) if len(rr) else np.nan,
           'severe1r_share_persistent':float(pp.severe_adverse_1r.mean()) if len(pp) else np.nan}
    (OUT/'bootstrap_and_tests.json').write_text(json.dumps(tests,indent=2))
    (OUT/'gates.json').write_text(json.dumps(gates,indent=2))

    lines=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(gates.values())}/{len(gates)}**','',
           '## Frozen parity',f'- LAB051 ADVERSE_FIRST cohort: **{len(d)}**; M15 path coverage: **{coverage:.1%}**','',
           '## Primary adverse-first sequence','',
           '| State | N | Share | Residual EV | Frozen parent EV | Median min after adverse | Severe +1R share |','|---|---:|---:|---:|---:|---:|---:|']
    fs=full.set_index('state')
    for s in ['RECOVERED_FIRST','PERSISTENT_FAILURE_FIRST','UNRESOLVED']:
        r=fs.loc[s]
        def ff(x): return '—' if pd.isna(x) else f'{x:+.3f}'
        lines.append(f"| {s} | {int(r.n)} | {r.share:.1%} | {ff(r.residual_ev)} | {ff(r.parent_ev)} | {('—' if pd.isna(r.median_minutes_after_fp) else f'{r.median_minutes_after_fp:.0f}')} | {('—' if pd.isna(r.severe1r_share) else f'{r.severe1r_share:.1%}')} |")
    lines += ['',f"RECOVERED−PERSISTENT residual gap: **{boot['point']:+.3f}R**, 7d bootstrap 95% CI **[{boot['ci_lo']:+.3f}, {boot['ci_hi']:+.3f}]**, clusters={boot['clusters']}",
              f"RECOVERED residual **{boot['recovered_ev']:+.3f}R**; PERSISTENT residual **{boot['persistent_ev']:+.3f}R**",'',
              '## Frozen transfer','',
              '| Slice | N | Resolved | Recovered N | Persistent N | Rec residual | Persist residual | Gap | Boot 95% CI |','|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for _,r in tr.iterrows():
        def f2(x): return '—' if pd.isna(x) else f'{x:+.3f}'
        ci='—' if pd.isna(r.boot_lo) else f'[{r.boot_lo:+.3f}, {r.boot_hi:+.3f}]'
        lines.append(f"| {r.scope} | {int(r.n)} | {int(r.resolved_n)} | {int(r.recovered_n)} | {int(r.persistent_n)} | {f2(r.recovered_residual)} | {f2(r.persistent_residual)} | {f2(r.gap)} | {ci} |")
    lines += ['', '## Severe-adverse diagnostic',
              f"- +1.0R adverse after ADVERSE_FIRST before sequence/end: ALL **{tests['severe1r_share_all']:.1%}**, RECOVERED **{tests['severe1r_share_recovered']:.1%}**, PERSISTENT **{tests['severe1r_share_persistent']:.1%}**",'',
              '## Gates']
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['','## Guardrail','Sequence mechanism audit only. No early exit, breakeven, stop tightening, trailing, re-entry, allocation, or new threshold is promoted. Reused historical lineage; not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(verdict, sum(gates.values()), '/', len(gates))

if __name__=='__main__': main()
