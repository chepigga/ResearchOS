#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

LAB='BTC_FLOW_LEVEL_DIRECTIONAL_LIQUIDITY_ELASTICITY_AND_THIN_BOOK_CONTINUATION_LAB_040'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=HERE.parent/'BTC_FLOW_LEVEL_CVD_PRESSURE_X_PRICE_RESPONSE_CAUSAL_ROLLING_INTERACTION_REPLICATION_LAB_039'/'output'/'rolling_interaction_stream.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC'); LOOKBACK=pd.Timedelta(days=90); MIN_PRIOR=20; SEED=20260908; BOOT_N=5000
FEATURES=['fut_elasticity_15','fut_elasticity_30','fut_elasticity_60','spot_elasticity_15','spot_elasticity_30','spot_elasticity_60','fut_minus_spot_elasticity_60','fut_elasticity_accel_15_60']
PRIMARY='fut_elasticity_60'
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}


def load():
    d=pd.read_csv(SRC)
    for c in ['signal_time','touch_time','class_time']:
        if c in d.columns:d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    nums=['side','residual_atr']
    for p in ['fut','spot']:
        for n in [15,30,60]: nums += [f'{p}_netdelta_norm_{n}',f'{p}_disp_atr_{n}']
    for c in nums:
        if c in d.columns:d[c]=pd.to_numeric(d[c],errors='coerce')
    if d.high_volume.dtype==object:d['high_volume']=d.high_volume.astype(str).str.lower().isin(['true','1'])
    else:d['high_volume']=d.high_volume.astype(bool)
    return d.sort_values('signal_time').reset_index(drop=True)


def add_elasticity(d):
    z=d.copy()
    for p in ['fut','spot']:
        for n in [15,30,60]:
            den=z[f'{p}_netdelta_norm_{n}'].abs().clip(lower=.25)
            z[f'{p}_elasticity_{n}']=z[f'{p}_disp_atr_{n}']/den
    z['fut_minus_spot_elasticity_60']=z.fut_elasticity_60-z.spot_elasticity_60
    z['fut_elasticity_accel_15_60']=z.fut_elasticity_60-z.fut_elasticity_15
    return z


def bh(p):
    p=np.asarray(p,float); n=len(p); order=np.argsort(p); q=np.ones(n); run=1.0
    for j in range(n-1,-1,-1):
        i=order[j]; run=min(run,p[i]*n/(j+1)); q[i]=min(1.0,run)
    return q


def state_tests(d):
    q=d[(d.signal_time<PRE)&d.rolling_cell.isin(['THIN_LIQUIDITY','WEAK'])]; rows=[]
    for feat in FEATURES:
        a=pd.to_numeric(q.loc[q.rolling_cell=='THIN_LIQUIDITY',feat],errors='coerce').dropna().to_numpy(float)
        b=pd.to_numeric(q.loc[q.rolling_cell=='WEAK',feat],errors='coerce').dropna().to_numpy(float)
        if len(a)>=3 and len(b)>=3:
            u,p=mannwhitneyu(a,b,alternative='two-sided'); rbc=2*float(u)/(len(a)*len(b))-1
        else:p=rbc=np.nan
        rows.append(dict(feature=feat,n_thin=len(a),n_weak=len(b),thin_median=float(np.median(a)) if len(a) else np.nan,weak_median=float(np.median(b)) if len(b) else np.nan,rbc=float(rbc) if np.isfinite(rbc) else np.nan,p=float(p) if np.isfinite(p) else np.nan))
    x=pd.DataFrame(rows); x['q_bh']=bh(x.p.fillna(1).to_numpy(float)); return x


def residual_tests(d):
    q=d[(d.signal_time<PRE)&d.rolling_cell.isin(['THIN_LIQUIDITY','WEAK'])]; rows=[]
    for feat in FEATURES:
        z=q[[feat,'residual_atr']].apply(pd.to_numeric,errors='coerce').dropna()
        if len(z)>=3:
            rho,p=spearmanr(z[feat],z.residual_atr); rho=float(rho); p=float(p)
        else:rho=p=np.nan
        rows.append(dict(feature=feat,n=len(z),rho=rho,p=p))
    x=pd.DataFrame(rows); x['q_bh']=bh(x.p.fillna(1).to_numpy(float)); return x


def cluster_gap(d,a_name,b_name,cell_col='rolling_cell'):
    q=d[(d.signal_time<PRE)&d[cell_col].isin([a_name,b_name])].copy().dropna(subset=['residual_atr'])
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    arr=[]
    for _,g in q.groupby('cluster'):
        a=g[g[cell_col]==a_name]; b=g[g[cell_col]==b_name]
        arr.append((int((a.state=='ACCEPT').sum()),len(a),int((b.state=='ACCEPT').sum()),len(b),a.residual_atr.sum(),len(a),b.residual_atr.sum(),len(b)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); rate=[]; resid=[]; m=len(arr)
    if not len(arr): return dict(clusters=0,rate_point=np.nan,rate_ci_lo=np.nan,rate_ci_hi=np.nan,resid_point=np.nan,resid_ci_lo=np.nan,resid_ci_hi=np.nan)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0:rate.append(float(s[0]/s[1]-s[2]/s[3]))
        if s[5]>0 and s[7]>0:resid.append(float(s[4]/s[5]-s[6]/s[7]))
    a=q[q[cell_col]==a_name]; b=q[q[cell_col]==b_name]; rv=np.asarray(rate,float); pv=np.asarray(resid,float)
    return dict(clusters=m,draws=BOOT_N,rate_point=float((a.state=='ACCEPT').mean()-(b.state=='ACCEPT').mean()),rate_ci_lo=float(np.quantile(rv,.025)),rate_ci_hi=float(np.quantile(rv,.975)),resid_point=float(a.residual_atr.mean()-b.residual_atr.mean()),resid_ci_lo=float(np.quantile(pv,.025)),resid_ci_hi=float(np.quantile(pv,.975)))


def rolling_elasticity(d):
    z=d.copy(); z['rolling_elasticity_median']=np.nan; z['elasticity_prior_n']=0; z['elasticity_state']='NOT_HIGH_VOLUME'
    hv=z[z.high_volume & z[PRIMARY].notna()].copy()
    for i,r in hv.iterrows():
        t=r.signal_time; prior=hv[(hv.signal_time>=t-LOOKBACK)&(hv.signal_time<t)&hv[PRIMARY].notna()]
        n=len(prior); z.at[i,'elasticity_prior_n']=n
        if n<MIN_PRIOR:
            z.at[i,'elasticity_state']='UNRESOLVED'; continue
        med=float(prior[PRIMARY].median()); z.at[i,'rolling_elasticity_median']=med
        z.at[i,'elasticity_state']='HIGH_ELASTICITY' if float(r[PRIMARY])>med else 'LOW_ELASTICITY'
    return z


def summarize_primary(d):
    q=d[(d.signal_time<PRE)&d.rolling_cell.isin(['THIN_LIQUIDITY','WEAK'])]; rows=[]
    for c in ['THIN_LIQUIDITY','WEAK']:
        x=q[q.rolling_cell==c]; rr=x.residual_atr.dropna()
        rows.append(dict(cell=c,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,pressure=float(x.fut_netdelta_norm_60.mean()) if len(x) else np.nan,response=float(x.fut_disp_atr_60.mean()) if len(x) else np.nan,elasticity=float(x[PRIMARY].mean()) if len(x) else np.nan))
    return pd.DataFrame(rows)


def summarize_elasticity_state(d):
    q=d[(d.signal_time<PRE)&d.elasticity_state.isin(['HIGH_ELASTICITY','LOW_ELASTICITY'])]; rows=[]
    for c in ['HIGH_ELASTICITY','LOW_ELASTICITY']:
        x=q[q.elasticity_state==c]; rr=x.residual_atr.dropna()
        rows.append(dict(state=c,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,elasticity=float(x[PRIMARY].mean()) if len(x) else np.nan,prior_n_median=float(x.elasticity_prior_n.median()) if len(x) else np.nan))
    return pd.DataFrame(rows)


def transfer(d):
    q=d[d.rolling_cell=='THIN_LIQUIDITY']; rows=[]
    for w,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); x=q[(q.signal_time>=a)&(q.signal_time<b)]; rr=x.residual_atr.dropna()
        rows.append(dict(slice=w,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,long_n=int((x.side==1).sum()),short_n=int((x.side==-1).sum())))
    pre=q[q.signal_time<PRE]
    for name,mask in [('LONG',pre.side==1),('SHORT',pre.side==-1)]:
        x=pre[mask]; rr=x.residual_atr.dropna(); rows.append(dict(slice=name,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,long_n=int((x.side==1).sum()),short_n=int((x.side==-1).sum())))
    x=pre[(pre.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(pre.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(pre.side==-1)]; rr=x.residual_atr.dropna(); rows.append(dict(slice='2022_SHORT',n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,long_n=0,short_n=len(x)))
    return pd.DataFrame(rows)


def val(df,name,col):
    q=df[df['slice']==name]; return float(q.iloc[0][col]) if len(q) and pd.notna(q.iloc[0][col]) else np.nan

def nval(df,name):
    q=df[df['slice']==name]; return int(q.iloc[0].n) if len(q) else 0

def py(x):
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.floating,)):return None if not np.isfinite(x) else float(x)
    raise TypeError(type(x).__name__)


def main():
    d=rolling_elasticity(add_elasticity(load())); d.to_csv(OUT/'liquidity_elasticity_stream.csv',index=False)
    ps=summarize_primary(d); ps.to_csv(OUT/'primary_thin_vs_weak.csv',index=False)
    st=state_tests(d); st.to_csv(OUT/'elasticity_state_tests.csv',index=False)
    rt=residual_tests(d); rt.to_csv(OUT/'elasticity_residual_tests.csv',index=False)
    bt=cluster_gap(d,'THIN_LIQUIDITY','WEAK'); (OUT/'thin_weak_bootstrap.json').write_text(json.dumps(bt,indent=2),encoding='utf-8')
    es=summarize_elasticity_state(d); es.to_csv(OUT/'rolling_elasticity_summary.csv',index=False)
    eb=cluster_gap(d,'HIGH_ELASTICITY','LOW_ELASTICITY','elasticity_state'); (OUT/'rolling_elasticity_bootstrap.json').write_text(json.dumps(eb,indent=2),encoding='utf-8')
    tr=transfer(d); tr.to_csv(OUT/'transfer.csv',index=False)

    pre=d[(d.signal_time<PRE)&d.high_volume]; resolved=pre[pre.rolling_cell.isin(['EFFICIENT_IGNITION','ABSORPTION','THIN_LIQUIDITY','WEAK'])]
    thin=resolved[resolved.rolling_cell=='THIN_LIQUIDITY']; weak=resolved[resolved.rolling_cell=='WEAK']
    pstate=st[st.feature==PRIMARY].iloc[0]; presid=rt[rt.feature==PRIMARY].iloc[0]
    hi=es[es.state=='HIGH_ELASTICITY'].iloc[0] if len(es[es.state=='HIGH_ELASTICITY']) else None; lo=es[es.state=='LOW_ELASTICITY'].iloc[0] if len(es[es.state=='LOW_ELASTICITY']) else None
    months=max(1,len(pd.period_range(resolved.signal_time.min().to_period('M'),(PRE-pd.Timedelta(seconds=1)).to_period('M'),freq='M'))) if len(resolved) else 1
    freq=len(thin)/months
    gates={
      'frozen_high_volume_ge_500':len(pre)>=500,
      'resolved_lab039_cells_ge_400':len(resolved)>=400,
      'thin_n_ge_50':len(thin)>=50,
      'weak_n_ge_120':len(weak)>=120,
      'thin_residual_positive':thin.residual_atr.mean()>0 if len(thin) else False,
      'thin_residual_gt_weak':thin.residual_atr.mean()>weak.residual_atr.mean() if len(thin) and len(weak) else False,
      'thin_weak_residual_gap_ge_0_50':bt['resid_point']>=.50,
      'thin_weak_resid_boot_ci_lower_gt_zero':bt['resid_ci_lo']>0,
      'thin_accept_rate_ge_weak':(thin.state=='ACCEPT').mean()>=(weak.state=='ACCEPT').mean() if len(thin) and len(weak) else False,
      'accept_rate_boot_ci_lower_gt_zero':bt['rate_ci_lo']>0,
      'primary_elasticity_thin_gt_weak':pstate.thin_median>pstate.weak_median,
      'primary_elasticity_state_bh_q_le_0_10':pstate.q_bh<=.10,
      'any_elasticity_state_bh_q_le_0_10':bool((st.q_bh<=.10).any()),
      'primary_elasticity_residual_rho_positive':presid.rho>0,
      'primary_elasticity_residual_absrho_ge_0_05':abs(presid.rho)>=.05,
      'primary_elasticity_residual_bh_q_le_0_10':presid.q_bh<=.10,
      'rolling_high_elasticity_residual_gt_low':bool(hi is not None and lo is not None and hi.residual_mean>lo.residual_mean),
      'rolling_elasticity_boot_ci_lower_gt_zero':eb['resid_ci_lo']>0,
      'stress_2022_short_thin_positive_n8':nval(tr,'2022_SHORT')>=8 and val(tr,'2022_SHORT','residual_mean')>0,
      'pooled_recent_thin_positive_n15':nval(tr,'POOLED_RECENT')>=15 and val(tr,'POOLED_RECENT','residual_mean')>0,
      'both_2025h2_2026_thin_positive':val(tr,'2025_H2','residual_mean')>0 and val(tr,'2026_JAN_JUL','residual_mean')>0,
      'long_thin_positive':val(tr,'LONG','residual_mean')>0,
      'short_thin_positive':val(tr,'SHORT','residual_mean')>0,
      'thin_frequency_ge_0_5_per_month':freq>=.5,
      'august_not_used_for_selection':True}
    score=sum(bool(v) for v in gates.values()); critical=['thin_residual_positive','thin_residual_gt_weak','thin_weak_resid_boot_ci_lower_gt_zero','primary_elasticity_thin_gt_weak','primary_elasticity_residual_rho_positive','rolling_elasticity_boot_ci_lower_gt_zero','pooled_recent_thin_positive_n15','both_2025h2_2026_thin_positive']
    if score>=19 and all(gates[k] for k in critical):verdict='PASS_DIRECTIONAL_LIQUIDITY_ELASTICITY_THIN_BOOK_CONTINUATION'
    elif score>=13 or gates['thin_residual_gt_weak']:verdict='WATCH_THIN_BOOK_CONTINUATION_POSITIVE_PROOF_INCOMPLETE'
    else:verdict='FAIL_NO_DIRECTIONAL_LIQUIDITY_ELASTICITY_EDGE'
    meta=dict(verdict=verdict,score=score,high_n=len(pre),resolved_n=len(resolved),thin_n=len(thin),weak_n=len(weak),thin_residual=float(thin.residual_atr.mean()) if len(thin) else np.nan,weak_residual=float(weak.residual_atr.mean()) if len(weak) else np.nan,thin_accept=float((thin.state=='ACCEPT').mean()) if len(thin) else np.nan,weak_accept=float((weak.state=='ACCEPT').mean()) if len(weak) else np.nan,frequency_per_month=freq,thin_weak_bootstrap=bt,elasticity_bootstrap=eb)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')

    def f(x):return '—' if pd.isna(x) else f'{float(x):.3f}'
    L=[f'# {LAB}','',f"**Verdict: {verdict} — {score}/{len(gates)}**",'', '## Primary THIN vs WEAK',f"- frozen HIGH_VOLUME pre-Aug: **{len(pre)}**, resolved LAB039 cells: **{len(resolved)}**",f"- THIN_LIQUIDITY N=**{len(thin)}**, residual **{meta['thin_residual']:+.3f} ATR**, ACCEPT **{meta['thin_accept']:.3f}**",f"- WEAK N=**{len(weak)}**, residual **{meta['weak_residual']:+.3f} ATR**, ACCEPT **{meta['weak_accept']:.3f}**",f"- residual gap **{bt['resid_point']:+.3f} ATR**, 7d bootstrap 95% CI **[{bt['resid_ci_lo']:+.3f}, {bt['resid_ci_hi']:+.3f}]**",f"- ACCEPT-rate gap **{bt['rate_point']:+.3f}**, 95% CI **[{bt['rate_ci_lo']:+.3f}, {bt['rate_ci_hi']:+.3f}]**",f"- THIN frequency **{freq:.2f}/month**",'', '## Elasticity state discrimination','', '| Feature | Thin N | Weak N | Thin median | Weak median | RBC | p | BH q |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in st.iterrows():L.append(f"| {r.feature} | {int(r.n_thin)} | {int(r.n_weak)} | {f(r.thin_median)} | {f(r.weak_median)} | {f(r.rbc)} | {f(r.p)} | {f(r.q_bh)} |")
    L+=['','## LOW_PRESSURE elasticity → residual','', '| Feature | N | rho | p | BH q |','|---|---:|---:|---:|---:|']
    for _,r in rt.iterrows():L.append(f"| {r.feature} | {int(r.n)} | {f(r.rho)} | {f(r.p)} | {f(r.q_bh)} |")
    L+=['','## Causal rolling elasticity diagnostic','', '| State | N | ACCEPT | Residual | Hit | Elasticity | Prior N med |','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in es.iterrows():L.append(f"| {r.state} | {int(r.n)} | {f(r.accept_rate)} | {f(r.residual_mean)} | {f(r.hit)} | {f(r.elasticity)} | {f(r.prior_n_median)} |")
    L += [f"- HIGH−LOW residual bootstrap: **{eb['resid_point']:+.3f} ATR**, 95% CI **[{eb['resid_ci_lo']:+.3f}, {eb['resid_ci_hi']:+.3f}]**",'', '## THIN transfer','', '| Slice | N | ACCEPT | Residual | Hit | L/S |','|---|---:|---:|---:|---:|---:|']
    for _,r in tr.iterrows():L.append(f"| {r['slice']} | {int(r.n)} | {f(r.accept_rate)} | {f(r.residual_mean)} | {f(r.hit)} | {int(r.long_n)}/{int(r.short_n)} |")
    L+=['','## Gates']+[f"- {'PASS' if v else 'FAIL'} — `{k}`" for k,v in gates.items()]+['','## Guardrail','Frozen FLOW/LEVEL/HIGH_VOLUME and causal rolling pressure/response lineage from LAB039. Elasticity uses only pre-touch features already frozen in LAB038. No trading execution optimization. August audit-only. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':verdict,'score':score,'meta':meta,'gates':gates},indent=2,default=py))

if __name__=='__main__':main()
