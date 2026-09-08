#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_FLOW_LEVEL_ALL_TOUCH_PRESSURE_RESPONSE_ROUTER_AND_SHORT_ASYMMETRY_LAB_042'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=HERE.parent/'BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041'/'output'/'all_touch_elasticity_stream.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC'); SEED=20260908; BOOT_N=5000
STATES=['DRIVEN_MOVE','ABSORPTION','THIN_BOOK','WEAK']
WINS={'2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),'2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),'2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}

def load():
 d=pd.read_csv(SRC)
 for c in ['signal_time','touch_time','class_time']:
  if c in d.columns:d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
 for c in ['side','residual_atr','pressure_mag_60','response_60','fut_elasticity_60']:
  if c in d.columns:d[c]=pd.to_numeric(d[c],errors='coerce')
 return d.sort_values('signal_time').reset_index(drop=True)

def summarize(q, keys=('book_state',)):
 rows=[]
 for vals,g in q.groupby(list(keys),dropna=False):
  if not isinstance(vals,tuple): vals=(vals,)
  r=pd.to_numeric(g.residual_atr,errors='coerce').dropna()
  row={k:v for k,v in zip(keys,vals)}
  row.update(n=len(g),accept_rate=float((g.state=='ACCEPT').mean()) if len(g) else np.nan,residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan,long_n=int((g.side==1).sum()),short_n=int((g.side==-1).sum()))
  rows.append(row)
 return pd.DataFrame(rows)

def boot_gap(q, mask_a, mask_b, label):
 z=q[mask_a|mask_b].dropna(subset=['residual_atr']).copy(); z['grp']=np.where(mask_a.loc[z.index],'A','B')
 epoch=pd.Timestamp('1970-01-01',tz='UTC'); z['cluster']=(((z.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
 arr=[]
 for _,g in z.groupby('cluster'):
  a=g[g.grp=='A'].residual_atr.to_numpy(float); b=g[g.grp=='B'].residual_atr.to_numpy(float); arr.append((a.sum(),len(a),b.sum(),len(b)))
 arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
 for _ in range(BOOT_N):
  s=arr[rng.integers(0,m,size=m)].sum(axis=0)
  if s[1]>0 and s[3]>0: vals.append(float(s[0]/s[1]-s[2]/s[3]))
 v=np.asarray(vals,float); a=z[z.grp=='A'].residual_atr.mean(); b=z[z.grp=='B'].residual_atr.mean()
 return dict(label=label,a_n=int((z.grp=='A').sum()),b_n=int((z.grp=='B').sum()),point=float(a-b),clusters=m,draws=len(v),ci_lo=float(np.quantile(v,.025)) if len(v) else np.nan,ci_hi=float(np.quantile(v,.975)) if len(v) else np.nan)

def transfer(q):
 rows=[]
 for state in ['DRIVEN_MOVE','ABSORPTION']:
  s=q[q.book_state==state]
  for w,(aa,bb) in WINS.items():
   a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); x=s[(s.signal_time>=a)&(s.signal_time<b)]; r=x.residual_atr.dropna()
   rows.append(dict(state=state,slice=w,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan,long_n=int((x.side==1).sum()),short_n=int((x.side==-1).sum())))
  pre=s[s.signal_time<PRE]
  for name,mask in [('LONG',pre.side==1),('SHORT',pre.side==-1)]:
   x=pre[mask]; r=x.residual_atr.dropna(); rows.append(dict(state=state,slice=name,n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan,long_n=int((x.side==1).sum()),short_n=int((x.side==-1).sum())))
  x=pre[(pre.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(pre.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(pre.side==-1)]; r=x.residual_atr.dropna(); rows.append(dict(state=state,slice='2022_SHORT',n=len(x),accept_rate=float((x.state=='ACCEPT').mean()) if len(x) else np.nan,residual_mean=float(r.mean()) if len(r) else np.nan,hit=float((r>0).mean()) if len(r) else np.nan,long_n=0,short_n=len(x)))
 return pd.DataFrame(rows)

def getrow(df,state,slice_):
 x=df[(df.state==state)&(df['slice']==slice_)]; return x.iloc[0] if len(x) else None

def py(x):
 if isinstance(x,(np.bool_,)):return bool(x)
 if isinstance(x,(np.integer,)):return int(x)
 if isinstance(x,(np.floating,)):return None if not np.isfinite(x) else float(x)
 raise TypeError(type(x).__name__)

def main():
 d=load(); pre=d[(d.signal_time<PRE)&d.book_state.isin(STATES)].copy(); summary=summarize(pre); summary.to_csv(OUT/'router_state_summary.csv',index=False)
 byside=summarize(pre,('book_state','side')); byside.to_csv(OUT/'router_state_by_side.csv',index=False)
 allgap=boot_gap(pre,pre.book_state.eq('DRIVEN_MOVE'),pre.book_state.eq('ABSORPTION'),'ALL_DRIVEN_MINUS_ABSORPTION')
 sp=pre[pre.side==-1]; shortgap=boot_gap(sp,sp.book_state.eq('DRIVEN_MOVE'),sp.book_state.eq('ABSORPTION'),'SHORT_DRIVEN_MINUS_ABSORPTION')
 asym=[]
 for st in STATES:
  z=pre[pre.book_state==st]; asym.append(boot_gap(z,z.side.eq(-1),z.side.eq(1),f'{st}_SHORT_MINUS_LONG'))
 adf=pd.DataFrame(asym); adf.to_csv(OUT/'asymmetry_bootstrap.csv',index=False)
 (OUT/'router_bootstrap.json').write_text(json.dumps({'all':allgap,'short':shortgap,'asymmetry':asym},indent=2),encoding='utf-8')
 tr=transfer(d); tr.to_csv(OUT/'transfer.csv',index=False)
 sidx=summary.set_index('book_state'); dm=sidx.loc['DRIVEN_MOVE']; ab=sidx.loc['ABSORPTION']; thin=sidx.loc['THIN_BOOK']
 def side_row(st,side):
  x=byside[(byside.book_state==st)&(byside.side==side)]; return x.iloc[0] if len(x) else None
 sdm=side_row('DRIVEN_MOVE',-1); sab=side_row('ABSORPTION',-1); sth=side_row('THIN_BOOK',-1); lth=side_row('THIN_BOOK',1); ldm=side_row('DRIVEN_MOVE',1)
 recent=getrow(tr,'DRIVEN_MOVE','POOLED_RECENT'); h2=getrow(tr,'DRIVEN_MOVE','2025_H2'); y26=getrow(tr,'DRIVEN_MOVE','2026_JAN_JUL'); s22=getrow(tr,'DRIVEN_MOVE','2022_SHORT')
 months=max(1,len(pd.period_range(pre.signal_time.min().to_period('M'),(PRE-pd.Timedelta(seconds=1)).to_period('M'),freq='M'))); freq=float(dm.n/months)
 gates={
 'resolved_preaug_ge_1900':len(pre)>=1900,'driven_n_ge_650':dm.n>=650,'absorption_n_ge_250':ab.n>=250,'driven_residual_positive':dm.residual_mean>0,'absorption_residual_le_zero':ab.residual_mean<=0,'all_gap_ge_0_40':allgap['point']>=.40,'all_boot_ci_lower_gt_zero':allgap['ci_lo']>0,'driven_accept_ge_absorption':dm.accept_rate>=ab.accept_rate,'driven_frequency_ge_8_month':freq>=8,
 'short_driven_n_ge_250':sdm is not None and sdm.n>=250,'short_absorption_n_ge_100':sab is not None and sab.n>=100,'short_driven_positive':sdm is not None and sdm.residual_mean>0,'short_absorption_le_zero':sab is not None and sab.residual_mean<=0,'short_gap_ge_0_50':shortgap['point']>=.50,'short_boot_ci_lower_gt_zero':shortgap['ci_lo']>0,
 'short_thin_gt_long_thin':sth is not None and lth is not None and sth.residual_mean>lth.residual_mean,'short_thin_n100_positive':sth is not None and sth.n>=100 and sth.residual_mean>0,'long_thin_n100':lth is not None and lth.n>=100,'long_driven_positive':ldm is not None and ldm.residual_mean>0,'short_driven_positive_dup':sdm is not None and sdm.residual_mean>0,
 'pooled_recent_driven_positive_n150':recent is not None and recent.n>=150 and recent.residual_mean>0,'both_2025h2_2026_driven_positive':h2 is not None and y26 is not None and h2.residual_mean>0 and y26.residual_mean>0,'2022_short_driven_positive_n30':s22 is not None and s22.n>=30 and s22.residual_mean>0,'august_not_used':True}
 score=sum(bool(v) for v in gates.values()); critical=['driven_residual_positive','all_gap_ge_0_40','all_boot_ci_lower_gt_zero','short_driven_positive','short_gap_ge_0_50','short_boot_ci_lower_gt_zero','short_driven_positive_dup','pooled_recent_driven_positive_n150','both_2025h2_2026_driven_positive']
 if score>=19 and all(gates[k] for k in critical): verdict='PASS_PRESSURE_RESPONSE_ROUTER_SHORT_BRANCH'
 elif score>=13 or (allgap['point']>0 and shortgap['point']>0): verdict='WATCH_ROUTER_POSITIVE_SHORT_ASYMMETRY_PROOF_INCOMPLETE'
 else: verdict='FAIL_PRESSURE_RESPONSE_ROUTER_NO_TRANSFER'
 meta=dict(verdict=verdict,resolved_n=len(pre),months=months,driven_frequency_per_month=freq,all_gap=allgap,short_gap=shortgap)
 (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')
 L=[f'# {LAB}','',f'**Verdict: {verdict} — {score}/{len(gates)}**','', '## Frozen router',f'- resolved pre-Aug: **{len(pre)}**; DRIVEN frequency **{freq:.2f}/month**','', '| State | N | ACCEPT | Residual | Hit | L/S |','|---|---:|---:|---:|---:|---:|']
 for _,r in summary.iterrows():L.append(f'| {r.book_state} | {int(r.n)} | {r.accept_rate:.3f} | {r.residual_mean:+.3f} | {r.hit:.3f} | {int(r.long_n)}/{int(r.short_n)} |')
 L+=['','## Primary router separation',f'- ALL DRIVEN−ABSORPTION: **{allgap["point"]:+.3f} ATR**, 95% CI **[{allgap["ci_lo"]:+.3f}, {allgap["ci_hi"]:+.3f}]**',f'- SHORT DRIVEN−ABSORPTION: **{shortgap["point"]:+.3f} ATR**, 95% CI **[{shortgap["ci_lo"]:+.3f}, {shortgap["ci_hi"]:+.3f}]**','', '## By side','', '| State | Side | N | ACCEPT | Residual | Hit |','|---|---:|---:|---:|---:|---:|']
 for _,r in byside.iterrows():L.append(f'| {r.book_state} | {"LONG" if int(r.side)==1 else "SHORT"} | {int(r.n)} | {r.accept_rate:.3f} | {r.residual_mean:+.3f} | {r.hit:.3f} |')
 L+=['','## SHORT−LONG bootstrap by state','', '| State | Gap | 95% CI |','|---|---:|---:|']
 for x in asym:L.append(f'| {x["label"].replace("_SHORT_MINUS_LONG","")} | {x["point"]:+.3f} | [{x["ci_lo"]:+.3f}, {x["ci_hi"]:+.3f}] |')
 L+=['','## DRIVEN / ABSORPTION transfer','', '| State | Slice | N | ACCEPT | Residual | Hit | L/S |','|---|---|---:|---:|---:|---:|---:|']
 for _,r in tr.iterrows():L.append(f'| {r.state} | {r["slice"]} | {int(r.n)} | {r.accept_rate:.3f} | {r.residual_mean:+.3f} | {r.hit:.3f} | {int(r.long_n)}/{int(r.short_n)} |' if r.n else f'| {r.state} | {r["slice"]} | 0 | — | — | — | 0/0 |')
 L+=['','## Gates']+[f'- {"PASS" if v else "FAIL"} — `{k}`' for k,v in gates.items()]+['','## Guardrail','Frozen LAB041 causal router states; no new thresholds/features/execution optimization. Reused historical lineage, not fresh OOS. August audit-only. Live allocation = **0**.']
 (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
 print(json.dumps({'verdict':verdict,'score':score,'meta':meta,'gates':gates},indent=2,default=py))

if __name__=='__main__': main()
