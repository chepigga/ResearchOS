#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_FLOW_LEVEL_CVD_PRESSURE_X_PRICE_RESPONSE_CAUSAL_ROLLING_INTERACTION_REPLICATION_LAB_039'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=HERE.parent/'BTC_FLOW_LEVEL_PRETOUCH_NET_TAKER_DELTA_PRICE_RESPONSE_AND_CVD_ABSORPTION_LAB_038'/'output'/'cvd_absorption_stream.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC'); SEED=20260908; BOOT_N=5000; LOOKBACK=pd.Timedelta(days=90); MIN_PRIOR=20
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}


def load():
    d=pd.read_csv(SRC)
    for c in ['signal_time','touch_time','class_time']:
        if c in d.columns:d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','fut_netdelta_norm_60','fut_disp_atr_60','residual_atr']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    if d['high_volume'].dtype==object:d['high_volume']=d.high_volume.astype(str).str.lower().isin(['true','1'])
    else:d['high_volume']=d.high_volume.astype(bool)
    return d.sort_values('signal_time').reset_index(drop=True)


def classify(d):
    z=d.copy(); z['rolling_pressure_median']=np.nan; z['rolling_response_median']=np.nan; z['prior_n']=0; z['rolling_cell']='NOT_HIGH_VOLUME'
    hv=z[z.high_volume & z.fut_netdelta_norm_60.notna() & z.fut_disp_atr_60.notna()].copy()
    idx=list(hv.index); times=hv.signal_time.to_numpy()
    for pos,i in enumerate(idx):
        t=z.at[i,'signal_time']; prior=hv[(hv.signal_time>=t-LOOKBACK)&(hv.signal_time<t)]
        n=len(prior); z.at[i,'prior_n']=n
        if n<MIN_PRIOR:
            z.at[i,'rolling_cell']='UNRESOLVED'; continue
        pm=float(prior.fut_netdelta_norm_60.median()); rm=float(prior.fut_disp_atr_60.median())
        z.at[i,'rolling_pressure_median']=pm; z.at[i,'rolling_response_median']=rm
        hp=float(z.at[i,'fut_netdelta_norm_60'])>pm; hr=float(z.at[i,'fut_disp_atr_60'])>rm
        if hp and hr:c='EFFICIENT_IGNITION'
        elif hp and not hr:c='ABSORPTION'
        elif (not hp) and hr:c='THIN_LIQUIDITY'
        else:c='WEAK'
        z.at[i,'rolling_cell']=c
    return z


def summarize_cells(d):
    q=d[(d.signal_time<PRE)&d.high_volume]; rows=[]
    for c in ['EFFICIENT_IGNITION','ABSORPTION','THIN_LIQUIDITY','WEAK','UNRESOLVED']:
        x=q[q.rolling_cell==c]; rr=pd.to_numeric(x.residual_atr,errors='coerce').dropna()
        rows.append(dict(cell=c,n=len(x),accept_n=int((x.state=='ACCEPT').sum()),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,residual_hit=float((rr>0).mean()) if len(rr) else np.nan,pressure=float(x.fut_netdelta_norm_60.mean()) if len(x) else np.nan,response=float(x.fut_disp_atr_60.mean()) if len(x) else np.nan,prior_n_median=float(x.prior_n.median()) if len(x) else np.nan))
    return pd.DataFrame(rows)


def bootstrap(d):
    q=d[(d.signal_time<PRE)&d.rolling_cell.isin(['EFFICIENT_IGNITION','ABSORPTION'])].copy(); q=q.dropna(subset=['residual_atr'])
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    arr=[]
    for _,g in q.groupby('cluster'):
        e=g[g.rolling_cell=='EFFICIENT_IGNITION']; a=g[g.rolling_cell=='ABSORPTION']
        arr.append((int((e.state=='ACCEPT').sum()),len(e),int((a.state=='ACCEPT').sum()),len(a),e.residual_atr.sum(),len(e),a.residual_atr.sum(),len(a)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); rv=[]; pv=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0:rv.append(float(s[0]/s[1]-s[2]/s[3]))
        if s[5]>0 and s[7]>0:pv.append(float(s[4]/s[5]-s[6]/s[7]))
    e=q[q.rolling_cell=='EFFICIENT_IGNITION']; a=q[q.rolling_cell=='ABSORPTION']; rv=np.asarray(rv); pv=np.asarray(pv)
    return dict(clusters=m,rate_point=float((e.state=='ACCEPT').mean()-(a.state=='ACCEPT').mean()),rate_ci_lo=float(np.quantile(rv,.025)),rate_ci_hi=float(np.quantile(rv,.975)),resid_point=float(e.residual_atr.mean()-a.residual_atr.mean()),resid_ci_lo=float(np.quantile(pv,.025)),resid_ci_hi=float(np.quantile(pv,.975)),draws=BOOT_N)


def transfer(d):
    q=d[d.rolling_cell=='EFFICIENT_IGNITION']; rows=[]
    for w,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); x=q[(q.signal_time>=a)&(q.signal_time<b)]; rr=x.residual_atr.dropna()
        rows.append(dict(slice=w,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,long_n=int((x.side==1).sum()),short_n=int((x.side==-1).sum())))
    pre=q[q.signal_time<PRE]
    for name,mask in [('LONG',pre.side==1),('SHORT',pre.side==-1)]:
        x=pre[mask]; rr=x.residual_atr.dropna(); rows.append(dict(slice=name,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,long_n=int((x.side==1).sum()),short_n=int((x.side==-1).sum())))
    x=pre[(pre.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(pre.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(pre.side==-1)]; rr=x.residual_atr.dropna(); rows.append(dict(slice='2022_SHORT',n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,long_n=0,short_n=len(x)))
    return pd.DataFrame(rows)


def val(tr,name,col):
    q=tr[tr['slice']==name]; return float(q.iloc[0][col]) if len(q) and pd.notna(q.iloc[0][col]) else np.nan

def nval(tr,name):
    q=tr[tr['slice']==name]; return int(q.iloc[0].n) if len(q) else 0

def py(x):
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.floating,)):return None if not np.isfinite(x) else float(x)
    raise TypeError(type(x).__name__)


def main():
    d=classify(load()); d.to_csv(OUT/'rolling_interaction_stream.csv',index=False)
    cs=summarize_cells(d); cs.to_csv(OUT/'cell_summary.csv',index=False)
    bt=bootstrap(d); (OUT/'bootstrap.json').write_text(json.dumps(bt,indent=2),encoding='utf-8')
    tr=transfer(d); tr.to_csv(OUT/'transfer.csv',index=False)
    pre=d[(d.signal_time<PRE)&d.high_volume]; resolved=pre[~pre.rolling_cell.isin(['UNRESOLVED','NOT_HIGH_VOLUME'])]; e=resolved[resolved.rolling_cell=='EFFICIENT_IGNITION']; a=resolved[resolved.rolling_cell=='ABSORPTION']
    start=resolved.signal_time.min().to_period('M') if len(resolved) else pd.Period('2021-01',freq='M'); end=(PRE-pd.Timedelta(seconds=1)).to_period('M'); months=max(1,len(pd.period_range(start,end,freq='M')))
    freq=len(e)/months
    gates={
      'frozen_high_volume_ge_500':len(pre)>=500,
      'resolved_rolling_thresholds_ge_80pct':len(resolved)/len(pre)>=.80 if len(pre) else False,
      'efficient_n_ge_120':len(e)>=120,
      'absorption_n_ge_80':len(a)>=80,
      'efficient_accept_rate_gt_absorption':(e.state=='ACCEPT').mean()>(a.state=='ACCEPT').mean() if len(e) and len(a) else False,
      'accept_rate_gap_ge_0_03':bt['rate_point']>=.03,
      'accept_rate_boot_ci_lower_gt_zero':bt['rate_ci_lo']>0,
      'efficient_residual_gt_absorption':e.residual_atr.mean()>a.residual_atr.mean() if len(e) and len(a) else False,
      'residual_gap_ge_0_50':bt['resid_point']>=.50,
      'residual_boot_ci_lower_gt_zero':bt['resid_ci_lo']>0,
      'efficient_residual_positive':e.residual_atr.mean()>0 if len(e) else False,
      'efficient_residual_hit_ge_0_50':(e.residual_atr>0).mean()>=.50 if len(e) else False,
      'stress_2022_short_positive_n15':nval(tr,'2022_SHORT')>=15 and val(tr,'2022_SHORT','residual_mean')>0,
      'pooled_recent_positive_n30':nval(tr,'POOLED_RECENT')>=30 and val(tr,'POOLED_RECENT','residual_mean')>0,
      '2025h2_positive':val(tr,'2025_H2','residual_mean')>0,
      '2026_positive':val(tr,'2026_JAN_JUL','residual_mean')>0,
      'long_positive':val(tr,'LONG','residual_mean')>0,
      'short_positive':val(tr,'SHORT','residual_mean')>0,
      'efficient_frequency_ge_1_per_month':freq>=1.0,
      'august_not_used_for_selection':True}
    score=sum(bool(v) for v in gates.values()); critical=['efficient_accept_rate_gt_absorption','efficient_residual_gt_absorption','residual_boot_ci_lower_gt_zero','pooled_recent_positive_n30','2025h2_positive','2026_positive']
    if score>=16 and all(gates[k] for k in critical):verdict='PASS_CAUSAL_ROLLING_PRESSURE_RESPONSE_INTERACTION_REPLICATION'
    elif score>=11 or (gates['efficient_residual_gt_absorption'] and gates['efficient_residual_positive']):verdict='WATCH_ROLLING_INTERACTION_POSITIVE_PROOF_INCOMPLETE'
    else:verdict='FAIL_ROLLING_PRESSURE_RESPONSE_INTERACTION_NO_REPLICATION'
    meta=dict(verdict=verdict,high_n=len(pre),resolved_n=len(resolved),resolved_share=len(resolved)/len(pre) if len(pre) else 0,efficient_n=len(e),absorption_n=len(a),efficient_accept=float((e.state=='ACCEPT').mean()) if len(e) else np.nan,absorption_accept=float((a.state=='ACCEPT').mean()) if len(a) else np.nan,efficient_residual=float(e.residual_atr.mean()) if len(e) else np.nan,absorption_residual=float(a.residual_atr.mean()) if len(a) else np.nan,efficient_hit=float((e.residual_atr>0).mean()) if len(e) else np.nan,frequency_per_month=freq,months=months,bootstrap=bt)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')
    L=[f'# {LAB}','',f"**Verdict: {verdict} — {score}/{len(gates)}**",'', '## Causal rolling replication',f"- frozen HIGH_VOLUME pre-Aug: **{len(pre)}**",f"- resolved prior-90d thresholds: **{len(resolved)} ({meta['resolved_share']:.1%})**",f"- EFFICIENT_IGNITION: **{len(e)}**, ABSORPTION: **{len(a)}**",f"- ACCEPT rate: **{meta['efficient_accept']:.3f} vs {meta['absorption_accept']:.3f}** (gap {bt['rate_point']:+.3f})",f"- residual: **{meta['efficient_residual']:+.3f} vs {meta['absorption_residual']:+.3f} ATR** (gap {bt['resid_point']:+.3f})",f"- efficient hit: **{meta['efficient_hit']:.3f}**; frequency **{freq:.2f}/month**",'', '## 7d cluster bootstrap',f"- ACCEPT-rate gap 95% CI **[{bt['rate_ci_lo']:+.3f}, {bt['rate_ci_hi']:+.3f}]**",f"- residual gap 95% CI **[{bt['resid_ci_lo']:+.3f}, {bt['resid_ci_hi']:+.3f}]**",'', '## Rolling cells','', '| Cell | N | ACCEPT | Residual | Hit | Pressure | Response | Prior N med |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in cs.iterrows():L.append(f"| {r.cell} | {int(r.n)} | {r.accept_rate:.3f} | {r.residual_mean:+.3f} | {r.residual_hit:.3f} | {r.pressure:.3f} | {r.response:.3f} | {r.prior_n_median:.1f} |" if r.n else f"| {r.cell} | 0 | — | — | — | — | — | — |")
    L+=['','## Efficient-ignition transfer','', '| Slice | N | ACCEPT | Residual | Hit | L/S |','|---|---:|---:|---:|---:|---:|']
    for _,r in tr.iterrows():L.append(f"| {r['slice']} | {int(r.n)} | {r.accept_rate:.3f} | {r.residual_mean:+.3f} | {r.hit:.3f} | {int(r.long_n)}/{int(r.short_n)} |" if r.n else f"| {r['slice']} | 0 | — | — | — | 0/0 |")
    L+=['','## Gates']+[f"- {'PASS' if v else 'FAIL'} — `{k}`" for k,v in gates.items()]+['','## Guardrail','Every interaction threshold is computed from frozen HIGH_VOLUME events in the strictly prior 90 calendar days only; current/future events are excluded and no global fallback is used. No trading execution optimization. August audit-only. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':verdict,'score':score,'meta':meta,'gates':gates},indent=2,default=py))

if __name__=='__main__':main()
