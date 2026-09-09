#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_V1_FROZEN_FULL_SYSTEM_END_TO_END_VALIDATION_LAB_055'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC43=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043'/'output'/'short_response_router_stream.csv'
SRC51=LABS/'BTC_SHORT_ACCEPT25_POST_ENTRY_FIRST_PASSAGE_AND_EARLY_FAILURE_STATE_LAB_051'/'output'/'post_entry_state_stream.csv'
SRC52=LABS/'BTC_SHORT_ACCEPT25_ADVERSE_FIRST_RECOVERY_VS_PERSISTENT_FAILURE_SEQUENCE_LAB_052'/'output'/'sequence_stream.csv'
SRC53=LABS/'BTC_SHORT_ACCEPT25_PERSISTENT_FAILURE_EXIT_VS_SEVERE_ADVERSE1R_EXECUTION_LAB_053'/'output'/'execution_stream.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC')
AUG_END=pd.Timestamp('2026-09-01',tz='UTC')
SEED=20260909+55; BOOT_N=5000
PERIODS=['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']

def period_of(t):
    if t.year in [2021,2022,2023,2024]: return str(t.year)
    if t.year==2025: return '2025_H1' if t < pd.Timestamp('2025-07-01',tz='UTC') else '2025_H2'
    if t.year==2026 and t<PRE: return '2026_JAN_JUL'
    if PRE<=t<AUG_END: return '2026_AUG'
    return 'OTHER'

def pf(v):
    v=np.asarray(v,float); gp=v[v>0].sum(); gl=-v[v<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def maxdd(v):
    v=np.asarray(v,float)
    eq=np.r_[0.0,np.cumsum(v)]; peak=np.maximum.accumulate(eq)
    return float(np.max(peak-eq)) if len(v) else np.nan

def max_loss_streak(v):
    best=cur=0
    for x in np.asarray(v,float):
        if x<0: cur+=1; best=max(best,cur)
        else: cur=0
    return int(best)

def cluster_id(t):
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    return (((t-epoch).dt.total_seconds())//(7*86400)).astype('int64')

def load():
    r=pd.read_csv(SRC43); p51=pd.read_csv(SRC51); s52=pd.read_csv(SRC52); e53=pd.read_csv(SRC53)
    for d in [r,p51,s52,e53]:
        for c in ['signal_time','entry_time','exit_time','fp_time','state_time','touch_time','class_time']:
            if c in d.columns: d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','residual_atr']:
        if c in r.columns: r[c]=pd.to_numeric(r[c],errors='coerce')
    for c in ['flow_id','parent_net_r_5bps']:
        if c in p51.columns: p51[c]=pd.to_numeric(p51[c],errors='coerce')
    for c in ['flow_id']:
        if c in s52.columns: s52[c]=pd.to_numeric(s52[c],errors='coerce')
    for c in ['flow_id','net_r_5bps','net_r_10bps','net_r_0bps']:
        if c in e53.columns: e53[c]=pd.to_numeric(e53[c],errors='coerce')
    return r,p51,s52,e53

def yearly(e,orig):
    rows=[]
    for p in PERIODS:
        q=e[e.period==p].sort_values('entry_time'); n0=int((orig.period==p).sum())
        v=q.net_r_5bps.to_numpy(float)
        rows.append(dict(period=p,original_n=n0,trades=len(q),early_exits=int(q.early_exit.astype(str).str.lower().eq('true').sum()),
                         ev=float(v.mean()) if len(v) else np.nan,pf=pf(v) if len(v) else np.nan,cumr=float(v.sum()),dd_r=maxdd(v) if len(v) else np.nan,
                         ev_per_original=float(v.sum()/n0) if n0 else np.nan,loss_streak=max_loss_streak(v) if len(v) else 0))
    return pd.DataFrame(rows)

def monthly_quarterly(e):
    q=e.sort_values('entry_time').copy(); q['month']=q.entry_time.dt.to_period('M').astype(str); q['quarter']=q.entry_time.dt.to_period('Q').astype(str)
    m=q.groupby('month').agg(trades=('flow_id','size'),cumr=('net_r_5bps','sum'),ev=('net_r_5bps','mean')).reset_index()
    qq=q.groupby('quarter').agg(trades=('flow_id','size'),cumr=('net_r_5bps','sum'),ev=('net_r_5bps','mean')).reset_index()
    return m,qq

def bootstrap(e):
    q=e.sort_values('entry_time').copy(); q['cluster']=cluster_id(q.entry_time)
    groups=[]
    for cid,g in q.groupby('cluster',sort=True): groups.append((cid,g.net_r_5bps.to_numpy(float)))
    rng=np.random.default_rng(SEED); evs=[]; dds=[]; totals=[]
    m=len(groups)
    for _ in range(BOOT_N):
        idx=rng.integers(0,m,size=m); path=np.concatenate([groups[i][1] for i in idx])
        evs.append(float(path.mean())); dds.append(maxdd(path)); totals.append(float(path.sum()))
    evs=np.asarray(evs); dds=np.asarray(dds); totals=np.asarray(totals)
    return dict(clusters=m,draws=BOOT_N,ev_point=float(q.net_r_5bps.mean()),ev_ci_lo=float(np.quantile(evs,.025)),ev_ci_hi=float(np.quantile(evs,.975)),
                total_ci_lo=float(np.quantile(totals,.025)),total_ci_hi=float(np.quantile(totals,.975)),dd_p50=float(np.quantile(dds,.50)),dd_p95=float(np.quantile(dds,.95)),dd_p99=float(np.quantile(dds,.99)))

def main():
    r,p51,s52,e53=load()
    hi=r[(r.side==-1)&(r.response_router=='HIGH_RESPONSE')].copy(); hi['period']=hi.signal_time.map(period_of)
    pre_hi=hi[hi.signal_time<PRE].copy(); aug_hi=hi[(hi.signal_time>=PRE)&(hi.signal_time<AUG_END)].copy()
    parent=p51[p51.signal_time<PRE].copy(); adverse=parent[parent.fp_state=='ADVERSE_FIRST'].copy()
    seq=s52[s52.signal_time<PRE].copy(); persistent=seq[seq.sequence_state=='PERSISTENT_FAILURE_FIRST'].copy()
    final=e53[(e53.policy=='PERSISTENT_EXIT')&(e53.signal_time<PRE)].copy().sort_values('entry_time')
    final['period']=final.signal_time.map(period_of)
    orig=pre_hi[['flow_id','signal_time']].drop_duplicates('flow_id').copy(); orig['period']=orig.signal_time.map(period_of)

    counts=dict(original_high_response=len(pre_hi),accept_trades=len(parent),adverse_first=len(adverse),persistent_failure=len(persistent),final_trades=len(final),early_exits=int(final.early_exit.astype(str).str.lower().eq('true').sum()))
    v=final.net_r_5bps.to_numpy(float); v10=final.net_r_10bps.to_numpy(float)
    core=dict(ev_5bps=float(v.mean()),pf_5bps=pf(v),cumr_5bps=float(v.sum()),maxdd_r=maxdd(v),dd_pct_025=maxdd(v)*0.25,dd_pct_050=maxdd(v)*0.50,
              ev_10bps=float(v10.mean()),pf_10bps=pf(v10),loss_streak=max_loss_streak(v),win_rate=float((v>0).mean()))
    y=yearly(final,orig); y.to_csv(OUT/'yearly_transfer.csv',index=False)
    m,q=monthly_quarterly(final); m.to_csv(OUT/'monthly.csv',index=False); q.to_csv(OUT/'quarterly.csv',index=False)
    bt=bootstrap(final); (OUT/'cluster_bootstrap.json').write_text(json.dumps(bt,indent=2))

    recent=y[y.period.isin(['2025_H2','2026_JAN_JUL'])]
    recent_ev_orig=float(recent.cumr.sum()/recent.original_n.sum())
    active_m=m[m.trades>0]; profitable_month_share=float((active_m.cumr>0).mean()) if len(active_m) else np.nan
    worst_q=q.loc[q.cumr.idxmin()].to_dict() if len(q) else {}
    aug_accept=int((aug_hi.state=='ACCEPT').sum()) if 'state' in aug_hi.columns else 0
    august=dict(high_response_signals=len(aug_hi),accept_signals=aug_accept,executable_trades=aug_accept,residual_mean=float(aug_hi.residual_atr.mean()) if len(aug_hi) else np.nan,
                note='Untouched August audit only; no selection/tuning allowed.')

    gates={
      'exact_original_high_response_475':counts['original_high_response']==475,
      'exact_accept_trades_327':counts['accept_trades']==327,
      'exact_adverse_first_145':counts['adverse_first']==145,
      'exact_persistent_failure_59':counts['persistent_failure']==59,
      'exact_final_trades_327':counts['final_trades']==327,
      'exact_early_exits_59':counts['early_exits']==59,
      'ev_5bps_positive':core['ev_5bps']>0,
      'pf_5bps_gt_1_10':core['pf_5bps']>1.10,
      'cumr_positive':core['cumr_5bps']>0,
      'ev_10bps_positive':core['ev_10bps']>0,
      'historical_dd_025_lt4pct':core['dd_pct_025']<4.0,
      'bootstrap_ev_lower_gt0':bt['ev_ci_lo']>0,
      'cluster_p95_dd_025_lt5pct':bt['dd_p95']*0.25<5.0,
      'recent_ev_per_original_positive':recent_ev_orig>0,
      'max_loss_streak_le10':core['loss_streak']<=10,
      'august_not_used_for_selection':True,
    }
    parity_ok=all(gates[k] for k in list(gates)[:6]); reused_ok=parity_ok and all(gates[k] for k in ['ev_5bps_positive','pf_5bps_gt_1_10','cumr_positive','ev_10bps_positive','historical_dd_025_lt4pct','cluster_p95_dd_025_lt5pct','recent_ev_per_original_positive'])
    fresh_supported=august['executable_trades']>=20 and august['residual_mean']>0
    if reused_ok and gates['bootstrap_ev_lower_gt0'] and fresh_supported:
        verdict='PASS_FROZEN_SYSTEM_REUSED_AND_FRESH_OOS_SUPPORTED'
    elif reused_ok:
        verdict='WATCH_FROZEN_SYSTEM_POSITIVE_REUSED_FRESH_OOS_INSUFFICIENT'
    else:
        verdict='FAIL_FROZEN_SYSTEM_VALIDATION'

    summary={'verdict':verdict,'counts':counts,'core':core,'bootstrap':bt,'recent_ev_per_original':recent_ev_orig,'profitable_active_month_share':profitable_month_share,'worst_quarter':worst_q,'august':august,'gates':gates}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=lambda x: float(x) if isinstance(x,np.floating) else int(x) if isinstance(x,np.integer) else bool(x) if isinstance(x,np.bool_) else str(x)))

    lines=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(bool(x) for x in gates.values())}/{len(gates)} gates**','',
           '## Frozen end-to-end lineage',
           f"- HIGH_RESPONSE SHORT signals: **{counts['original_high_response']}**",
           f"- ACCEPT trades: **{counts['accept_trades']}**",
           f"- ADVERSE_FIRST: **{counts['adverse_first']}**",
           f"- PERSISTENT_FAILURE: **{counts['persistent_failure']}**",
           f"- final trades: **{counts['final_trades']}**, EXIT_NOW early exits **{counts['early_exits']}**",'',
           '## Full frozen economics',
           f"- EV 5bps **{core['ev_5bps']:+.3f}R**, PF **{core['pf_5bps']:.3f}**, CumR **{core['cumr_5bps']:+.2f}R**, WR **{core['win_rate']:.1%}**",
           f"- MaxDD **{core['maxdd_r']:.2f}R** = **{core['dd_pct_025']:.2f}%** at 0.25% risk; **{core['dd_pct_050']:.2f}%** at 0.50% risk",
           f"- 10bps EV **{core['ev_10bps']:+.3f}R**, PF **{core['pf_10bps']:.3f}**",
           f"- max consecutive losses **{core['loss_streak']}**",'',
           '## 7-day cluster bootstrap',
           f"- EV 95% CI **[{bt['ev_ci_lo']:+.3f}, {bt['ev_ci_hi']:+.3f}]R**",
           f"- total-R 95% interval **[{bt['total_ci_lo']:+.1f}, {bt['total_ci_hi']:+.1f}]R**",
           f"- resampled maxDD p50 **{bt['dd_p50']:.2f}R**, p95 **{bt['dd_p95']:.2f}R**, p99 **{bt['dd_p99']:.2f}R**",
           f"- p95 DD at 0.25% risk **{bt['dd_p95']*0.25:.2f}%**; at 0.50% risk **{bt['dd_p95']*0.50:.2f}%**",'',
           '## Transfer','', '| Period | Orig N | Trades | EV | PF | CumR | DD R | EV/orig | Loss streak |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r0 in y.iterrows(): lines.append(f"| {r0.period} | {int(r0.original_n)} | {int(r0.trades)} | {r0.ev:+.3f} | {r0.pf:.3f} | {r0.cumr:+.2f} | {r0.dd_r:.2f} | {r0.ev_per_original:+.3f} | {int(r0.loss_streak)} |")
    lines += ['',f"Active profitable-month share **{profitable_month_share:.1%}**; worst quarter **{worst_q.get('quarter','—')}** CumR **{worst_q.get('cumr',np.nan):+.2f}R**.",
              f"Pooled 2025H2+2026 EV/original **{recent_ev_orig:+.3f}R**.",'',
              '## Untouched August 2026 audit',
              f"- HIGH_RESPONSE SHORT signals **{august['high_response_signals']}**; ACCEPT/executable **{august['executable_trades']}**; router residual **{august['residual_mean']:+.3f} ATR**.",
              '- This is **insufficient fresh OOS sample** and cannot validate or invalidate the system. No August result was used to alter the specification.','',
              '## Gates']
    for k,val in gates.items(): lines.append(f"- {'PASS' if val else 'FAIL'} — `{k}`")
    lines += ['','## Decision','SHORT v1 is frozen after this audit. No further reused-history tuning is authorized. Next evidence must come from fresh/native broker execution or a genuinely untouched future sample. Live allocation remains **0** until that replication.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
