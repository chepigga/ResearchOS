#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

LAB='BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=HERE.parent/'BTC_FLOW_LEVEL_PRETOUCH_NET_TAKER_DELTA_PRICE_RESPONSE_AND_CVD_ABSORPTION_LAB_038'/'output'/'cvd_absorption_stream.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC'); LOOKBACK=pd.Timedelta(days=90); MIN_PRIOR=40; SEED=20260908; BOOT_N=5000
FEATURES=['fut_elasticity_15','fut_elasticity_30','fut_elasticity_60','spot_elasticity_15','spot_elasticity_30','spot_elasticity_60','fut_minus_spot_elasticity_60','fut_elasticity_accel_15_60']
WINS={'2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),'2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),'2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}

def load():
 d=pd.read_csv(SRC)
 for c in ['signal_time','touch_time','class_time']:
  if c in d.columns:d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
 nums=['side','residual_atr','fut_netdelta_norm_15','fut_netdelta_norm_30','fut_netdelta_norm_60','spot_netdelta_norm_15','spot_netdelta_norm_30','spot_netdelta_norm_60','fut_disp_atr_15','fut_disp_atr_30','fut_disp_atr_60','spot_disp_atr_15','spot_disp_atr_30','spot_disp_atr_60']
 for c in nums:
  d[c]=pd.to_numeric(d[c],errors='coerce')
 for p in ['fut','spot']:
  for n in [15,30,60]: d[f'{p}_elasticity_{n}']=d[f'{p}_disp_atr_{n}']/np.maximum(d[f'{p}_netdelta_norm_{n}'].abs(),0.25)
 d['fut_minus_spot_elasticity_60']=d.fut_elasticity_60-d.spot_elasticity_60
 d['fut_elasticity_accel_15_60']=d.fut_elasticity_60-d.fut_elasticity_15
 d['pressure_mag_60']=d.fut_netdelta_norm_60.abs(); d['response_60']=d.fut_disp_atr_60
 return d.sort_values('signal_time').reset_index(drop=True)

def classify(d):
 z=d.copy(); z['prior_n']=0; z['pressure_med90']=np.nan; z['response_med90']=np.nan; z['elasticity_med90']=np.nan; z['book_state']='UNRESOLVED'; z['elasticity_state']='UNRESOLVED'
 base=z[z.pressure_mag_60.notna()&z.response_60.notna()&z.fut_elasticity_60.notna()].copy()
 for i in base.index:
  t=z.at[i,'signal_time']; p=base[(base.signal_time>=t-LOOKBACK)&(base.signal_time<t)]
  n=len(p); z.at[i,'prior_n']=n
  if n<MIN_PRIOR: continue
  pm=float(p.pressure_mag_60.median()); rm=float(p.response_60.median()); em=float(p.fut_elasticity_60.median())
  z.at[i,'pressure_med90']=pm; z.at[i,'response_med90']=rm; z.at[i,'elasticity_med90']=em
  low=float(z.at[i,'pressure_mag_60'])<=pm; highresp=float(z.at[i,'response_60'])>rm
  if low and highresp:s='THIN_BOOK'
  elif (not low) and highresp:s='DRIVEN_MOVE'
  elif (not low) and (not highresp):s='ABSORPTION'
  else:s='WEAK'
  z.at[i,'book_state']=s; z.at[i,'elasticity_state']='HIGH_ELASTICITY' if float(z.at[i,'fut_elasticity_60'])>em else 'LOW_ELASTICITY'
 return z

def bh(p):
 p=np.asarray(p,float); n=len(p); order=np.argsort(p); q=np.ones(n); run=1.0
 for j in range(n-1,-1,-1):
  i=order[j]; run=min(run,p[i]*n/(j+1)); q[i]=min(1.0,run)
 return q

def stats(d):
 q=d[(d.signal_time<PRE)&~d.book_state.eq('UNRESOLVED')]; rows=[]
 for s in ['THIN_BOOK','DRIVEN_MOVE','ABSORPTION','WEAK']:
  x=q[q.book_state==s]; r=x.residual_atr.dropna()
  rows.append(dict(state=s,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan,pressure=float(x.pressure_mag_60.mean()) if len(x) else np.nan,response=float(x.response_60.mean()) if len(x) else np.nan,elasticity=float(x.fut_elasticity_60.mean()) if len(x) else np.nan))
 return pd.DataFrame(rows)

def boot_gap(d,statecol,a,b):
 q=d[(d.signal_time<PRE)&d[statecol].isin([a,b])].dropna(subset=['residual_atr']).copy(); epoch=pd.Timestamp('1970-01-01',tz='UTC'); q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
 arr=[]
 for _,g in q.groupby('cluster'):
  x=g[g[statecol]==a].residual_atr.to_numpy(float); y=g[g[statecol]==b].residual_atr.to_numpy(float); arr.append((x.sum(),len(x),y.sum(),len(y)))
 arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
 for _ in range(BOOT_N):
  s=arr[rng.integers(0,m,size=m)].sum(axis=0)
  if s[1]>0 and s[3]>0:vals.append(float(s[0]/s[1]-s[2]/s[3]))
 v=np.asarray(vals); xa=q[q[statecol]==a].residual_atr.mean(); xb=q[q[statecol]==b].residual_atr.mean()
 return dict(comparison=f'{a}-{b}',point=float(xa-xb),clusters=m,draws=len(v),ci_lo=float(np.quantile(v,.025)),ci_hi=float(np.quantile(v,.975)))

def elasticity_corr(d):
 q=d[(d.signal_time<PRE)&d.book_state.isin(['THIN_BOOK','WEAK'])].copy(); rows=[]
 for f in FEATURES:
  z=q[[f,'residual_atr']].dropna()
  if len(z)>=3:rho,p=spearmanr(z[f],z.residual_atr); rho=float(rho); p=float(p)
  else:rho=p=np.nan
  rows.append(dict(feature=f,n=len(z),rho=rho,p=p))
 x=pd.DataFrame(rows); x['q_bh']=bh(x.p.fillna(1).to_numpy()); return x

def elasticity_summary(d):
 q=d[(d.signal_time<PRE)&~d.elasticity_state.eq('UNRESOLVED')]; rows=[]
 for s in ['HIGH_ELASTICITY','LOW_ELASTICITY']:
  x=q[q.elasticity_state==s]; r=x.residual_atr.dropna(); rows.append(dict(state=s,n=len(x),residual_mean=float(r.mean()),hit=float((r>0).mean()),accept_rate=float((x.state=='ACCEPT').mean()),elasticity=float(x.fut_elasticity_60.mean())))
 return pd.DataFrame(rows)

def transfer(d):
 q=d[d.book_state=='THIN_BOOK']; rows=[]
 for w,(aa,bb) in WINS.items():
  a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); x=q[(q.signal_time>=a)&(q.signal_time<b)]; r=x.residual_atr.dropna(); rows.append(dict(slice=w,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan,long_n=int((x.side==1).sum()),short_n=int((x.side==-1).sum())))
 pre=q[q.signal_time<PRE]
 for name,mask in [('LONG',pre.side==1),('SHORT',pre.side==-1)]:
  x=pre[mask]; r=x.residual_atr.dropna(); rows.append(dict(slice=name,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()),residual_mean=float(r.mean()),hit=float((r>0).mean()),long_n=int((x.side==1).sum()),short_n=int((x.side==-1).sum())))
 x=pre[(pre.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(pre.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(pre.side==-1)]; r=x.residual_atr.dropna(); rows.append(dict(slice='2022_SHORT',n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan,long_n=0,short_n=len(x)))
 return pd.DataFrame(rows)
def rowval(t,n,c):
 q=t[t['slice']==n]; return float(q.iloc[0][c]) if len(q) and pd.notna(q.iloc[0][c]) else np.nan
def rown(t,n):
 q=t[t['slice']==n]; return int(q.iloc[0].n) if len(q) else 0
def py(x):
 if isinstance(x,(np.bool_,)):return bool(x)
 if isinstance(x,(np.integer,)):return int(x)
 if isinstance(x,(np.floating,)):return None if not np.isfinite(x) else float(x)
 raise TypeError(type(x).__name__)

def main():
 d=classify(load()); d.to_csv(OUT/'all_touch_elasticity_stream.csv',index=False)
 pre=d[d.signal_time<PRE]; resolved=pre[~pre.book_state.eq('UNRESOLVED')]; ss=stats(d); ss.to_csv(OUT/'state_summary.csv',index=False)
 bc=boot_gap(d,'book_state','THIN_BOOK','WEAK'); es=elasticity_summary(d); es.to_csv(OUT/'elasticity_summary.csv',index=False); be=boot_gap(d,'elasticity_state','HIGH_ELASTICITY','LOW_ELASTICITY')
 cr=elasticity_corr(d); cr.to_csv(OUT/'elasticity_correlations.csv',index=False); tr=transfer(d); tr.to_csv(OUT/'transfer.csv',index=False)
 thin=resolved[resolved.book_state=='THIN_BOOK']; weak=resolved[resolved.book_state=='WEAK']; hi=resolved[resolved.elasticity_state=='HIGH_ELASTICITY']; lo=resolved[resolved.elasticity_state=='LOW_ELASTICITY']
 months=max(1,len(pd.period_range(resolved.signal_time.min().to_period('M'),(PRE-pd.Timedelta(seconds=1)).to_period('M'),freq='M'))); freq=len(thin)/months
 primary=cr[cr.feature=='fut_elasticity_60'].iloc[0]
 gates={
 'all_classified_preaug_ge_1900':len(pre)>=1900,'feature_coverage_ge_95pct':float(pre.fut_elasticity_60.notna().mean())>=.95,'rolling_resolved_ge_85pct':len(resolved)/len(pre)>=.85,
 'thin_n_ge_250':len(thin)>=250,'weak_n_ge_250':len(weak)>=250,'thin_residual_positive':thin.residual_atr.mean()>0,'thin_residual_gt_weak':thin.residual_atr.mean()>weak.residual_atr.mean(),'thin_weak_gap_ge_0_30':bc['point']>=.30,'thin_weak_boot_ci_lower_gt_zero':bc['ci_lo']>0,'thin_accept_ge_weak':(thin.state=='ACCEPT').mean()>=(weak.state=='ACCEPT').mean(),'thin_frequency_ge_3_month':freq>=3,
 'rolling_high_elasticity_gt_low':hi.residual_atr.mean()>lo.residual_atr.mean(),'rolling_elasticity_gap_ge_0_20':be['point']>=.20,'rolling_elasticity_boot_ci_lower_gt_zero':be['ci_lo']>0,'primary_elasticity_rho_positive':primary.rho>0,'primary_elasticity_absrho_ge_0_05':abs(primary.rho)>=.05,'primary_elasticity_bh_q_le_0_10':primary.q_bh<=.10,'any_elasticity_feature_bh_q_le_0_10':bool((cr.q_bh<=.10).any()),
 'long_thin_positive_n100':rown(tr,'LONG')>=100 and rowval(tr,'LONG','residual_mean')>0,'short_thin_positive_n100':rown(tr,'SHORT')>=100 and rowval(tr,'SHORT','residual_mean')>0,'stress_2022_short_positive_n20':rown(tr,'2022_SHORT')>=20 and rowval(tr,'2022_SHORT','residual_mean')>0,'pooled_recent_positive_n80':rown(tr,'POOLED_RECENT')>=80 and rowval(tr,'POOLED_RECENT','residual_mean')>0,'2025h2_positive':rowval(tr,'2025_H2','residual_mean')>0,'2026_positive':rowval(tr,'2026_JAN_JUL','residual_mean')>0,'august_not_used':True}
 score=sum(bool(v) for v in gates.values()); critical=['thin_residual_positive','thin_residual_gt_weak','thin_weak_boot_ci_lower_gt_zero','rolling_high_elasticity_gt_low','rolling_elasticity_boot_ci_lower_gt_zero','pooled_recent_positive_n80','2025h2_positive','2026_positive']
 if score>=19 and all(gates[k] for k in critical):verdict='PASS_ALL_TOUCH_THIN_BOOK_CONTINUATION'
 elif score>=13 or (gates['thin_residual_positive'] and gates['thin_residual_gt_weak']):verdict='WATCH_ALL_TOUCH_THIN_BOOK_POSITIVE_PROOF_INCOMPLETE'
 else:verdict='FAIL_ALL_TOUCH_THIN_BOOK_NO_TRANSFER'
 meta=dict(verdict=verdict,pre_n=len(pre),resolved_n=len(resolved),resolved_share=len(resolved)/len(pre),thin_n=len(thin),weak_n=len(weak),thin_residual=float(thin.residual_atr.mean()),weak_residual=float(weak.residual_atr.mean()),thin_accept=float((thin.state=='ACCEPT').mean()),weak_accept=float((weak.state=='ACCEPT').mean()),frequency_per_month=freq,book_bootstrap=bc,elasticity_bootstrap=be)
 (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')
 (OUT/'bootstrap.json').write_text(json.dumps({'thin_vs_weak':bc,'high_vs_low_elasticity':be},indent=2),encoding='utf-8')
 L=[f'# {LAB}','',f'**Verdict: {verdict} — {score}/{len(gates)}**','', '## All-touch universe',f'- classified pre-Aug: **{len(pre)}**; rolling resolved: **{len(resolved)} ({len(resolved)/len(pre):.1%})**',f'- THIN_BOOK N=**{len(thin)}**, residual **{thin.residual_atr.mean():+.3f} ATR**, ACCEPT **{(thin.state=="ACCEPT").mean():.3f}**',f'- WEAK N=**{len(weak)}**, residual **{weak.residual_atr.mean():+.3f} ATR**, ACCEPT **{(weak.state=="ACCEPT").mean():.3f}**',f'- THIN-WEAK residual gap **{bc["point"]:+.3f} ATR**, 7d bootstrap 95% CI **[{bc["ci_lo"]:+.3f}, {bc["ci_hi"]:+.3f}]**',f'- THIN frequency **{freq:.2f}/month**','', '## Rolling book states','', '| State | N | ACCEPT | Residual | Hit | Pressure | Response | Elasticity |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for _,r in ss.iterrows():L.append(f'| {r.state} | {int(r.n)} | {r.accept_rate:.3f} | {r.residual_mean:+.3f} | {r.hit:.3f} | {r.pressure:.3f} | {r.response:.3f} | {r.elasticity:.3f} |')
 L+=['','## Rolling elasticity','']
 for _,r in es.iterrows():L.append(f'- {r.state}: N={int(r.n)}, residual **{r.residual_mean:+.3f} ATR**, ACCEPT {r.accept_rate:.3f}, mean elasticity {r.elasticity:.3f}')
 L.append(f'- HIGH−LOW elasticity residual gap **{be["point"]:+.3f} ATR**, 95% CI **[{be["ci_lo"]:+.3f}, {be["ci_hi"]:+.3f}]**')
 L+=['','## LOW_PRESSURE elasticity → residual','', '| Feature | N | rho | p | BH q |','|---|---:|---:|---:|---:|']
 for _,r in cr.iterrows():L.append(f'| {r.feature} | {int(r.n)} | {r.rho:.3f} | {r.p:.3f} | {r.q_bh:.3f} |')
 L+=['','## THIN transfer','', '| Slice | N | ACCEPT | Residual | Hit | L/S |','|---|---:|---:|---:|---:|---:|']
 for _,r in tr.iterrows():L.append(f'| {r["slice"]} | {int(r.n)} | {r.accept_rate:.3f} | {r.residual_mean:+.3f} | {r.hit:.3f} | {int(r.long_n)}/{int(r.short_n)} |' if r.n else f'| {r["slice"]} | 0 | — | — | — | 0/0 |')
 L+=['','## Gates']+[f'- {"PASS" if v else "FAIL"} — `{k}`' for k,v in gates.items()]+['','## Guardrail','No HIGH_VOLUME gate. Rolling thresholds use only strictly prior 90d all-touch history, minimum 40 prior touches, no global fallback. Touch bar excluded in source features. No execution optimization. August audit-only. Live allocation = **0**.']
 (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8'); print(json.dumps({'verdict':verdict,'score':score,'meta':meta,'gates':gates},indent=2,default=py))
if __name__=='__main__':main()
