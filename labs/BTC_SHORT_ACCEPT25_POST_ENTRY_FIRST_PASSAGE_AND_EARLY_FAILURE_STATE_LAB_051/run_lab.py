#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_ACCEPT25_POST_ENTRY_FIRST_PASSAGE_AND_EARLY_FAILURE_STATE_LAB_051'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC44=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044'/'output'/'execution_stream.csv'
SRC35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'output'/'activation_stream.csv'
R35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab035',R35)
L35=importlib.util.module_from_spec(spec); spec.loader.exec_module(L35); L35.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC')
SEED=20260908+51; BOOT_N=5000
PERIODS=['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']


def period_of(t):
    y=t.year
    if y in [2021,2022,2023,2024]: return str(y)
    if y==2025: return '2025_H1' if t < pd.Timestamp('2025-07-01',tz='UTC') else '2025_H2'
    if y==2026 and t < PRE: return '2026_JAN_JUL'
    return 'OTHER'

def cluster_id(t):
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    return (((t-epoch).dt.total_seconds())//(7*86400)).astype('int64')

def load_parent():
    e=pd.read_csv(SRC44)
    a=pd.read_csv(SRC35)
    for c in ['signal_time','entry_time','horizon','exit_time']:
        e[c]=pd.to_datetime(e[c],errors='coerce',utc=True)
    for c in ['signal_time','touch_time','class_time']:
        if c in a.columns: a[c]=pd.to_datetime(a[c],errors='coerce',utc=True)
    for c in ['flow_id','stop_atr','entry_price','exit_price','net_r_5bps']:
        e[c]=pd.to_numeric(e[c],errors='coerce')
    for c in ['flow_id','atr14','level','class_price']:
        a[c]=pd.to_numeric(a[c],errors='coerce')
    traded=e['traded'].astype(str).str.lower().eq('true')
    q=e[(e.clock=='ACCEPT') & (np.isclose(e.stop_atr,2.5)) & traded & (e.signal_time<PRE)].copy()
    q=q[['flow_id','signal_time','entry_time','entry_price','exit_time','exit_price','exit_reason','net_r_5bps']]
    q=q.merge(a[['flow_id','atr14','level','class_time','class_price']],on='flow_id',how='left',validate='one_to_one')
    q=q.sort_values('entry_time').reset_index(drop=True)
    if len(q)!=327: raise RuntimeError(f'Frozen parent parity failed: {len(q)} != 327')
    q['period']=q.signal_time.map(period_of)
    q['risk_dist']=2.5*q.atr14
    q['entry_class_parity']=(q.entry_time==q.class_time) & np.isclose(q.entry_price,q.class_price,equal_nan=False)
    return q

def path_slice(fut,et,end,include_end=True):
    if pd.isna(et) or pd.isna(end): return fut.iloc[0:0]
    if include_end: return fut[(fut.index>et)&(fut.index<=end)]
    return fut[(fut.index>et)&(fut.index<end)]

def first_passage(path,entry,D):
    fav=entry-0.5*D; adv=entry+0.5*D
    for tt,b in path.iterrows():
        hf=float(b.low)<=fav
        ha=float(b.high)>=adv
        if hf and ha: return 'ADVERSE_FIRST',tt,adv
        if ha: return 'ADVERSE_FIRST',tt,adv
        if hf: return 'FAVORABLE_FIRST',tt,fav
    return 'NONE_120',pd.NaT,np.nan

def reclaim_states(path_close,level):
    r1_t=pd.NaT; r1_px=np.nan; r2_t=pd.NaT; r2_px=np.nan; consec=0
    for tt,b in path_close.iterrows():
        c=float(b.close)
        if c>level:
            if pd.isna(r1_t): r1_t=tt; r1_px=c
            consec += 1
            if consec>=2 and pd.isna(r2_t):
                r2_t=tt; r2_px=c
                break
        else:
            consec=0
    return r1_t,r1_px,r2_t,r2_px

def excursion(path,entry,D):
    if path.empty or not np.isfinite(D) or D<=0: return np.nan,np.nan
    mfe=max(0.0,entry-float(path.low.min()))/D
    mae=max(0.0,float(path.high.max())-entry)/D
    return float(mfe),float(mae)

def analyze_one(r,fut):
    et=pd.Timestamp(r.entry_time); xt=pd.Timestamp(r.exit_time)
    D=float(r.risk_dist); ep=float(r.entry_price); xp=float(r.exit_price); level=float(r.level)
    covered=bool(et in fut.index and xt in fut.index and np.isfinite(D) and D>0 and np.isfinite(ep) and np.isfinite(xp) and np.isfinite(level))
    base=dict(flow_id=int(r.flow_id),signal_time=r.signal_time,entry_time=et,exit_time=xt,exit_reason=r.exit_reason,period=r.period,
              entry_price=ep,exit_price=xp,atr14=float(r.atr14),risk_dist=D,level=level,parent_net_r_5bps=float(r.net_r_5bps),covered=covered)
    if not covered:
        base.update(fp_state='UNCOVERED',fp_time=pd.NaT,fp_price=np.nan,fp_minutes=np.nan,fp_residual_r=np.nan,
                    mfe60_r=np.nan,mae60_r=np.nan,mfe120_r=np.nan,mae120_r=np.nan,
                    reclaim1=False,reclaim1_time=pd.NaT,reclaim1_price=np.nan,reclaim1_residual_r=np.nan,
                    reclaim2=False,reclaim2_time=pd.NaT,reclaim2_price=np.nan,reclaim2_residual_r=np.nan)
        return base
    end120=min(et+pd.Timedelta(minutes=120),xt)
    p120=path_slice(fut,et,end120,include_end=True)
    state,st,sp=first_passage(p120,ep,D)
    residual=(sp-xp)/D if pd.notna(st) and np.isfinite(sp) else np.nan
    mins=(st-et).total_seconds()/60.0 if pd.notna(st) else np.nan
    end60=min(et+pd.Timedelta(minutes=60),xt)
    p60=path_slice(fut,et,end60,include_end=True)
    mfe60,mae60=excursion(p60,ep,D); mfe120,mae120=excursion(p120,ep,D)
    # Close-based reclaim is observable only before an intrabar SL/TP exit bar; TIME close at exit is observable.
    close_include_end=(str(r.exit_reason)=='TIME')
    pc=path_slice(fut,et,end120,include_end=close_include_end if end120==xt else True)
    r1t,r1px,r2t,r2px=reclaim_states(pc,level)
    r1res=(r1px-xp)/D if pd.notna(r1t) else np.nan
    r2res=(r2px-xp)/D if pd.notna(r2t) else np.nan
    base.update(fp_state=state,fp_time=st,fp_price=sp,fp_minutes=mins,fp_residual_r=residual,
                mfe60_r=mfe60,mae60_r=mae60,mfe120_r=mfe120,mae120_r=mae120,
                reclaim1=bool(pd.notna(r1t)),reclaim1_time=r1t,reclaim1_price=r1px,reclaim1_residual_r=r1res,
                reclaim2=bool(pd.notna(r2t)),reclaim2_time=r2t,reclaim2_price=r2px,reclaim2_residual_r=r2res)
    return base

def fp_summary(d,scope):
    rows=[]
    for s in ['FAVORABLE_FIRST','ADVERSE_FIRST','NONE_120']:
        z=d[d.fp_state==s]
        rows.append(dict(scope=scope,state=s,n=len(z),share=len(z)/len(d) if len(d) else np.nan,
                         residual_ev=float(z.fp_residual_r.mean()) if z.fp_residual_r.notna().any() else np.nan,
                         parent_ev=float(z.parent_net_r_5bps.mean()) if len(z) else np.nan,
                         median_minutes=float(z.fp_minutes.median()) if z.fp_minutes.notna().any() else np.nan,
                         mfe60=float(z.mfe60_r.median()) if len(z) else np.nan,mae60=float(z.mae60_r.median()) if len(z) else np.nan,
                         mfe120=float(z.mfe120_r.median()) if len(z) else np.nan,mae120=float(z.mae120_r.median()) if len(z) else np.nan))
    return pd.DataFrame(rows)

def contrast_boot(d,seed=SEED):
    z=d[d.fp_state.isin(['FAVORABLE_FIRST','ADVERSE_FIRST']) & d.fp_residual_r.notna()].copy()
    z['cluster']=cluster_id(z.entry_time)
    arr=[]
    for _,g in z.groupby('cluster'):
        f=g[g.fp_state=='FAVORABLE_FIRST'].fp_residual_r.to_numpy(float)
        a=g[g.fp_state=='ADVERSE_FIRST'].fp_residual_r.to_numpy(float)
        arr.append((f.sum(),len(f),a.sum(),len(a)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(seed); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0: vals.append(float(s[0]/s[1]-s[2]/s[3]))
    vals=np.asarray(vals,float)
    f=z[z.fp_state=='FAVORABLE_FIRST'].fp_residual_r.mean(); a=z[z.fp_state=='ADVERSE_FIRST'].fp_residual_r.mean()
    return dict(point=float(f-a),fav_ev=float(f),adv_ev=float(a),ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),clusters=m,draws=len(vals))

def scope_row(d,name):
    z=d.copy(); r=contrast_boot(z,seed=SEED+abs(hash(name))%10000) if set(z.fp_state).intersection({'FAVORABLE_FIRST','ADVERSE_FIRST'}) else dict(point=np.nan,fav_ev=np.nan,adv_ev=np.nan,ci_lo=np.nan,ci_hi=np.nan,clusters=0,draws=0)
    resolved=z[z.fp_state.isin(['FAVORABLE_FIRST','ADVERSE_FIRST'])]
    adv_share=float((resolved.fp_state=='ADVERSE_FIRST').mean()) if len(resolved) else np.nan
    return dict(scope=name,n=len(z),resolved_n=len(resolved),fav_n=int((z.fp_state=='FAVORABLE_FIRST').sum()),adv_n=int((z.fp_state=='ADVERSE_FIRST').sum()),adv_share=adv_share,
                fav_residual=r['fav_ev'],adv_residual=r['adv_ev'],gap=r['point'],boot_lo=r['ci_lo'],boot_hi=r['ci_hi'])

def main():
    parent=load_parent(); fut=L35.download_futures()
    rows=[analyze_one(r,fut) for r in parent.itertuples(index=False)]
    d=pd.DataFrame(rows).sort_values('entry_time').reset_index(drop=True)
    d.to_csv(OUT/'post_entry_state_stream.csv',index=False)
    coverage=float(d.covered.mean()); parity=float(parent.entry_class_parity.mean())
    full=fp_summary(d,'FULL'); full.to_csv(OUT/'first_passage_summary.csv',index=False)
    boot=contrast_boot(d)
    transfers=[]
    for p in PERIODS: transfers.append(scope_row(d[d.period==p],p))
    transfers.append(scope_row(d[d.period.isin(['2022','2025_H1'])],'BAD_POOLED'))
    transfers.append(scope_row(d[d.period.isin(['2025_H2','2026_JAN_JUL'])],'RECENT_POOLED'))
    tr=pd.DataFrame(transfers); tr.to_csv(OUT/'transfer.csv',index=False)
    r2=d[d.reclaim2].copy(); nr2=d[~d.reclaim2].copy()
    reclaim=dict(reclaim1_n=int(d.reclaim1.sum()),reclaim1_residual=float(d.loc[d.reclaim1,'reclaim1_residual_r'].mean()) if d.reclaim1.any() else np.nan,
                 reclaim2_n=len(r2),reclaim2_residual=float(r2.reclaim2_residual_r.mean()) if len(r2) else np.nan,
                 reclaim2_parent_ev=float(r2.parent_net_r_5bps.mean()) if len(r2) else np.nan,
                 no_reclaim2_parent_ev=float(nr2.parent_net_r_5bps.mean()) if len(nr2) else np.nan)
    bad=tr[tr.scope=='BAD_POOLED'].iloc[0]; recent=tr[tr.scope=='RECENT_POOLED'].iloc[0]
    fav_n=int((d.fp_state=='FAVORABLE_FIRST').sum()); adv_n=int((d.fp_state=='ADVERSE_FIRST').sum()); resolved=fav_n+adv_n
    gates={
      'exact_frozen_parent_n327': bool(len(d)==327),
      'parent_path_coverage_ge99pct': bool(coverage>=.99),
      'first_passage_resolved_n_ge100': bool(resolved>=100),
      'favorable_first_n_ge40': bool(fav_n>=40),
      'adverse_first_n_ge40': bool(adv_n>=40),
      'favorable_residual_positive': bool(boot['fav_ev']>0),
      'adverse_residual_negative': bool(boot['adv_ev']<0),
      'residual_gap_ge0_30r': bool(boot['point']>=.30),
      'residual_gap_boot_lower_gt0': bool(boot['ci_lo']>0),
      'bad_pooled_residual_gap_positive': bool(pd.notna(bad.gap) and bad.gap>0),
      'recent_pooled_residual_gap_positive': bool(pd.notna(recent.gap) and recent.gap>0),
      'reclaim2_n_ge20': bool(reclaim['reclaim2_n']>=20),
      'reclaim2_residual_negative': bool(pd.notna(reclaim['reclaim2_residual']) and reclaim['reclaim2_residual']<0),
      'reclaim2_parent_ev_lt_no_reclaim2': bool(pd.notna(reclaim['reclaim2_parent_ev']) and reclaim['reclaim2_parent_ev']<reclaim['no_reclaim2_parent_ev']),
      'august_not_used_for_selection': True,
    }
    primary_keys=list(gates.keys())[:11]+['august_not_used_for_selection']
    reclaim_pass=sum(gates[k] for k in ['reclaim2_n_ge20','reclaim2_residual_negative','reclaim2_parent_ev_lt_no_reclaim2'])
    if all(gates[k] for k in primary_keys) and reclaim_pass>=2:
        verdict='PASS_POST_ENTRY_EARLY_FAILURE_STATE'
    elif boot['point']>0 and boot['adv_ev']<boot['fav_ev']:
        verdict='WATCH_EARLY_PATH_DISCRIMINATIVE_PROOF_INCOMPLETE'
    else:
        verdict='FAIL_NO_POST_ENTRY_EARLY_FAILURE_STATE'
    tests={'primary_first_passage':boot,'coverage':coverage,'entry_class_parity':parity,'reclaim':reclaim,'resolved_n':resolved,'fav_n':fav_n,'adv_n':adv_n}
    (OUT/'bootstrap_and_tests.json').write_text(json.dumps(tests,indent=2))
    (OUT/'gates.json').write_text(json.dumps(gates,indent=2))
    lines=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(gates.values())}/{len(gates)}**','',
           '## Frozen parity',f'- Parent ACCEPT2.5 trades: **{len(d)}**; M15 path coverage: **{coverage:.1%}**; entry/class parity: **{parity:.1%}**','',
           '## Primary first-passage within 120m','', '| State | N | Share | Residual EV | Frozen parent EV | Median min | MFE60 | MAE60 | MFE120 | MAE120 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in full.iterrows():
        def f(x): return '—' if pd.isna(x) else f'{x:+.3f}'
        lines.append(f"| {r.state} | {int(r.n)} | {r.share:.1%} | {f(r.residual_ev)} | {f(r.parent_ev)} | {('—' if pd.isna(r.median_minutes) else f'{r.median_minutes:.0f}')} | {f(r.mfe60)} | {f(r.mae60)} | {f(r.mfe120)} | {f(r.mae120)} |")
    lines += ['',f"FAVORABLE−ADVERSE residual gap: **{boot['point']:+.3f}R**, 7d bootstrap 95% CI **[{boot['ci_lo']:+.3f}, {boot['ci_hi']:+.3f}]**, clusters={boot['clusters']}",
              f"FAVORABLE residual **{boot['fav_ev']:+.3f}R**; ADVERSE residual **{boot['adv_ev']:+.3f}R**",'',
              '## Frozen transfer','', '| Slice | N | Resolved | Fav N | Adv N | Adv share | Fav residual | Adv residual | Gap | Boot 95% CI |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for _,r in tr.iterrows():
        lines.append(f"| {r.scope} | {int(r.n)} | {int(r.resolved_n)} | {int(r.fav_n)} | {int(r.adv_n)} | {('—' if pd.isna(r.adv_share) else f'{r.adv_share:.1%}')} | {('—' if pd.isna(r.fav_residual) else f'{r.fav_residual:+.3f}')} | {('—' if pd.isna(r.adv_residual) else f'{r.adv_residual:+.3f}')} | {('—' if pd.isna(r.gap) else f'{r.gap:+.3f}')} | [{('—' if pd.isna(r.boot_lo) else f'{r.boot_lo:+.3f}')}, {('—' if pd.isna(r.boot_hi) else f'{r.boot_hi:+.3f}')} ] |")
    lines += ['','## Early reclaim diagnostics',f"- RECLAIM1 N={reclaim['reclaim1_n']}, residual **{reclaim['reclaim1_residual']:+.3f}R**",
              f"- RECLAIM2 N={reclaim['reclaim2_n']}, residual **{reclaim['reclaim2_residual']:+.3f}R**",
              f"- Frozen parent EV: RECLAIM2 **{reclaim['reclaim2_parent_ev']:+.3f}R** vs NO_RECLAIM2 **{reclaim['no_reclaim2_parent_ev']:+.3f}R**",'', '## Gates']
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['','## Guardrail','Mechanism/state audit only. No early exit, breakeven, trailing, stop tightening, re-entry, or allocation rule was searched or promoted. Reused historical lineage; not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(verdict, sum(gates.values()), '/', len(gates))

if __name__=='__main__': main()
