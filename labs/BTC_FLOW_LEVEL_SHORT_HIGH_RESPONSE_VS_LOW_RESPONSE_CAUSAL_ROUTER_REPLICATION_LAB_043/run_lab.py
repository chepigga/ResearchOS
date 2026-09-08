#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=HERE.parent/'BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041'/'output'/'all_touch_elasticity_stream.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC'); SEED=20260908; BOOT_N=5000
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}


def load():
    d=pd.read_csv(SRC)
    for c in ['signal_time','touch_time','class_time']:
        if c in d.columns: d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','residual_atr']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d[(d.side==-1)&d.book_state.isin(['DRIVEN_MOVE','THIN_BOOK','ABSORPTION','WEAK'])].copy()
    d['response_router']=np.where(d.book_state.isin(['DRIVEN_MOVE','THIN_BOOK']),'HIGH_RESPONSE','LOW_RESPONSE')
    return d.sort_values('signal_time').reset_index(drop=True)


def summary(d):
    q=d[d.signal_time<PRE]; rows=[]
    for s in ['HIGH_RESPONSE','LOW_RESPONSE']:
        x=q[q.response_router==s]; r=x.residual_atr.dropna()
        rows.append(dict(router=s,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,
                         residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan,
                         sum_residual=float(r.sum()) if len(r) else np.nan))
    return pd.DataFrame(rows)


def components(d):
    q=d[d.signal_time<PRE]; rows=[]
    for s in ['DRIVEN_MOVE','THIN_BOOK','ABSORPTION','WEAK']:
        x=q[q.book_state==s]; r=x.residual_atr.dropna()
        rows.append(dict(state=s,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,
                         residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan))
    return pd.DataFrame(rows)


def bootstrap(d):
    q=d[d.signal_time<PRE].dropna(subset=['residual_atr']).copy()
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    arr=[]
    for _,g in q.groupby('cluster'):
        h=g[g.response_router=='HIGH_RESPONSE'].residual_atr.to_numpy(float)
        l=g[g.response_router=='LOW_RESPONSE'].residual_atr.to_numpy(float)
        arr.append((h.sum(),len(h),l.sum(),len(l)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        z=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if z[1]>0 and z[3]>0: vals.append(float(z[0]/z[1]-z[2]/z[3]))
    v=np.asarray(vals,float)
    h=q[q.response_router=='HIGH_RESPONSE'].residual_atr.mean(); l=q[q.response_router=='LOW_RESPONSE'].residual_atr.mean()
    return dict(point=float(h-l),clusters=m,draws=len(v),ci_lo=float(np.quantile(v,.025)),ci_hi=float(np.quantile(v,.975)))


def transfer(d):
    rows=[]
    for w,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC')
        for s in ['HIGH_RESPONSE','LOW_RESPONSE']:
            x=d[(d.signal_time>=a)&(d.signal_time<b)&(d.response_router==s)]; r=x.residual_atr.dropna()
            rows.append(dict(slice=w,router=s,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,
                             residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan))
    return pd.DataFrame(rows)


def slice_gap(tr,name):
    h=tr[(tr['slice']==name)&(tr.router=='HIGH_RESPONSE')]
    l=tr[(tr['slice']==name)&(tr.router=='LOW_RESPONSE')]
    if len(h) and len(l):
        return dict(slice=name,high_n=int(h.iloc[0].n),low_n=int(l.iloc[0].n),high=float(h.iloc[0].residual_mean),low=float(l.iloc[0].residual_mean),gap=float(h.iloc[0].residual_mean-l.iloc[0].residual_mean))
    return dict(slice=name,high_n=0,low_n=0,high=np.nan,low=np.nan,gap=np.nan)


def row(summary,name):
    q=summary[summary.router==name]; return q.iloc[0] if len(q) else None

def cval(comp,name,col='residual_mean'):
    q=comp[comp.state==name]; return float(q.iloc[0][col]) if len(q) else np.nan

def py(x):
    if isinstance(x,(np.bool_,)): return bool(x)
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,)): return None if not np.isfinite(x) else float(x)
    raise TypeError(type(x).__name__)


def main():
    d=load(); d.to_csv(OUT/'short_response_router_stream.csv',index=False)
    s=summary(d); s.to_csv(OUT/'router_summary.csv',index=False)
    comp=components(d); comp.to_csv(OUT/'component_summary.csv',index=False)
    bt=bootstrap(d); (OUT/'bootstrap.json').write_text(json.dumps(bt,indent=2),encoding='utf-8')
    tr=transfer(d); tr.to_csv(OUT/'transfer.csv',index=False)
    gaps=pd.DataFrame([slice_gap(tr,k) for k in WINS]); gaps.to_csv(OUT/'transfer_gaps.csv',index=False)
    pre=d[d.signal_time<PRE]; hi=row(s,'HIGH_RESPONSE'); lo=row(s,'LOW_RESPONSE')
    months=max(1,len(pd.period_range(pre.signal_time.min().to_period('M'),(PRE-pd.Timedelta(seconds=1)).to_period('M'),freq='M')))
    freq=float(hi.n/months)
    def gv(name,key):
        q=gaps[gaps['slice']==name]; return float(q.iloc[0][key]) if len(q) and pd.notna(q.iloc[0][key]) else np.nan
    def gn(name,key):
        q=gaps[gaps['slice']==name]; return int(q.iloc[0][key]) if len(q) else 0
    gates={
      'short_resolved_preaug_ge_900':len(pre)>=900,
      'high_response_n_ge_450':int(hi.n)>=450,
      'low_response_n_ge_450':int(lo.n)>=450,
      'high_response_residual_positive':float(hi.residual_mean)>0,
      'low_response_residual_le_zero':float(lo.residual_mean)<=0,
      'residual_gap_ge_0_50':bt['point']>=.50,
      'cluster_boot_ci_lower_gt_zero':bt['ci_lo']>0,
      'high_response_hit_ge_0_50':float(hi.hit)>=.50,
      'high_response_frequency_ge_6_month':freq>=6,
      '2021_high_positive':gv('2021','high')>0,
      '2022_high_positive':gv('2022','high')>0,
      '2023_high_positive':gv('2023','high')>0,
      '2024_high_positive':gv('2024','high')>0,
      '2025h1_high_positive':gv('2025_H1','high')>0,
      '2025h2_high_positive':gv('2025_H2','high')>0,
      '2026_high_positive':gv('2026_JAN_JUL','high')>0,
      'pooled_recent_high_positive_n60':gn('POOLED_RECENT','high_n')>=60 and gv('POOLED_RECENT','high')>0,
      'pooled_recent_low_le_zero_n60':gn('POOLED_RECENT','low_n')>=60 and gv('POOLED_RECENT','low')<=0,
      'pooled_recent_gap_ge_0_50':gv('POOLED_RECENT','gap')>=.50,
      '2022_stress_high_positive_n50':gn('2022','high_n')>=50 and gv('2022','high')>0,
      'thin_book_short_positive':cval(comp,'THIN_BOOK')>0,
      'driven_move_short_positive':cval(comp,'DRIVEN_MOVE')>0,
      'absorption_short_le_zero':cval(comp,'ABSORPTION')<=0,
      'weak_short_le_zero':cval(comp,'WEAK')<=0,
      'august_not_used_for_selection':True}
    score=sum(bool(v) for v in gates.values())
    critical=['high_response_residual_positive','low_response_residual_le_zero','residual_gap_ge_0_50','cluster_boot_ci_lower_gt_zero','2025h2_high_positive','2026_high_positive','pooled_recent_high_positive_n60','pooled_recent_low_le_zero_n60','pooled_recent_gap_ge_0_50']
    if score>=21 and all(gates[k] for k in critical): verdict='PASS_SHORT_HIGH_RESPONSE_CAUSAL_ROUTER_REPLICATION'
    elif score>=14 or gates['high_response_residual_positive']: verdict='WATCH_SHORT_HIGH_RESPONSE_ROUTER_POSITIVE_PROOF_INCOMPLETE'
    else: verdict='FAIL_SHORT_HIGH_RESPONSE_ROUTER_NO_REPLICATION'
    meta=dict(verdict=verdict,pre_n=len(pre),high_n=int(hi.n),low_n=int(lo.n),high_residual=float(hi.residual_mean),low_residual=float(lo.residual_mean),gap=bt['point'],high_hit=float(hi.hit),low_hit=float(lo.hit),high_accept=float(hi.accept_rate),low_accept=float(lo.accept_rate),frequency_per_month=freq,bootstrap=bt)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')
    L=[f'# {LAB}','',f'**Verdict: {verdict} — {score}/{len(gates)}**','', '## Primary SHORT response router',
       f'- frozen resolved SHORT pre-Aug: **{len(pre)}**; HIGH_RESPONSE **{int(hi.n)}**, LOW_RESPONSE **{int(lo.n)}**',
       f'- HIGH_RESPONSE residual **{float(hi.residual_mean):+.3f} ATR**, hit **{float(hi.hit):.3f}**, ACCEPT **{float(hi.accept_rate):.3f}**',
       f'- LOW_RESPONSE residual **{float(lo.residual_mean):+.3f} ATR**, hit **{float(lo.hit):.3f}**, ACCEPT **{float(lo.accept_rate):.3f}**',
       f'- gap **{bt["point"]:+.3f} ATR**, 7d bootstrap 95% CI **[{bt["ci_lo"]:+.3f}, {bt["ci_hi"]:+.3f}]**, clusters={bt["clusters"]}',
       f'- HIGH_RESPONSE frequency **{freq:.2f}/month**','', '## Frozen component decomposition','', '| Component | N | ACCEPT | Residual | Hit |','|---|---:|---:|---:|---:|']
    for _,r in comp.iterrows(): L.append(f'| {r.state} | {int(r.n)} | {r.accept_rate:.3f} | {r.residual_mean:+.3f} | {r.hit:.3f} |')
    L+=['','## Transfer','', '| Slice | HIGH N | HIGH residual | LOW N | LOW residual | Gap |','|---|---:|---:|---:|---:|---:|']
    for _,r in gaps.iterrows(): L.append(f'| {r["slice"]} | {int(r.high_n)} | {r.high:+.3f} | {int(r.low_n)} | {r.low:+.3f} | {r.gap:+.3f} |')
    L+=['','## Gates']+[f'- {"PASS" if v else "FAIL"} — `{k}`' for k,v in gates.items()]+['','## Guardrail','Frozen LAB041 causal states collapsed to SHORT HIGH_RESPONSE vs LOW_RESPONSE only. No new thresholds/features/execution optimization. Reused historical lineage, not fresh OOS. August audit-only. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':verdict,'score':score,'meta':meta,'gates':gates},indent=2,default=py))

if __name__=='__main__': main()
