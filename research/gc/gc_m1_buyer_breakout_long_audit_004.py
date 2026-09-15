#!/usr/bin/env python3
"""GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004

Post-discovery historical audit of the directional branch observed in LAB003 discovery.
The candidate rule is frozen BEFORE this audit from BREAKOUT_CONT LONG:
- M1 completed bar
- buyer aggression A: delta_frac >= prior240 Q90 AND buy volume >= prior240 Q75
- current high >= prior 20 completed-bar high
- close in top 25% of current bar
- bullish body / positive buyer impact
- entry exact next clock-contiguous M1 open, LONG

Controls are fixed and diagnostic:
PRICE_BREAKOUT_ALL: same price structure without order-flow gates.
PRICE_BREAKOUT_NO_OF: price structure excluding the order-flow candidate.
BUYER_A_ALL: buyer A without requiring breakout structure.
MIRROR_SELLER_BREAKOUT_SHORT: exact mirror, SHORT.

No thresholds are tuned here. This is historical characterization, not independent OOS.
"""
from __future__ import annotations
import importlib.util,json
from pathlib import Path
import numpy as np,pandas as pd

ROOT=Path('research/gc')
BASE=ROOT/'gc_m1_orderflow_edge_discovery_003.py'
OUT_JSON=ROOT/'GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004.json'
OUT_MD=ROOT/'GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004.md'
OUT_EVENTS=ROOT/'GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004_EVENTS.csv'
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z'); VALID_END=pd.Timestamp('2026-09-06T22:00:00Z'); LATE_END=pd.Timestamp('2026-09-11T12:46:00Z')
HORIZONS=(5,15)
SEED=20260915
RULES=('BUYER_BREAKOUT_LONG','PRICE_BREAKOUT_ALL','PRICE_BREAKOUT_NO_OF','BUYER_A_ALL','MIRROR_SELLER_BREAKOUT_SHORT')

def load_base():
 spec=importlib.util.spec_from_file_location('edge003',BASE); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def sources(m):
 work=ROOT/'_edge003_work'; work.mkdir(exist_ok=True); rz=work/'rithmic.zip'; az=work/'amp.zip'
 if not rz.exists(): m.download(m.RITH_URL,rz)
 if not az.exists(): m.download(m.AMP_URL,az)
 if m.sha(rz)!=m.RITH_SHA or m.sha(az)!=m.AMP_SHA: raise SystemExit('SHA mismatch')
 return m.load_rithmic(rz),m.load_amp(az)

def masks(b):
 buyer=b.aggr.eq('BUY'); seller=b.aggr.eq('SELL')
 bull=(b.close>b.open)&(b.close_pos>=.75)&(b.high>=b.prior20_high)
 bear=(b.close<b.open)&(b.close_pos<=.25)&(b.low<=b.prior20_low)
 of_buy=buyer&bull&(b.impact>0)
 of_sell=seller&bear&(b.impact>0)
 price=bull
 return {
  'BUYER_BREAKOUT_LONG':(of_buy,1),
  'PRICE_BREAKOUT_ALL':(price,1),
  'PRICE_BREAKOUT_NO_OF':(price&~of_buy,1),
  'BUYER_A_ALL':(buyer,1),
  'MIRROR_SELLER_BREAKOUT_SHORT':(of_sell,-1),
 }

def events(b,rule):
 mask,d=masks(b)[rule]; rows=[]
 for i in np.flatnonzero(mask.to_numpy()):
  if i+1>=len(b): continue
  entry=b.iloc[i+1]
  if entry.time!=b.iloc[i].time+pd.Timedelta(minutes=1): continue
  atr=float(b.iloc[i].atr14)
  if not np.isfinite(atr) or atr<=0: continue
  ep=float(entry.open); row={'feed':b.iloc[i].feed,'rule':rule,'signal_time':b.iloc[i].time,'entry_time':entry.time,'side':'LONG' if d>0 else 'SHORT','atr14':atr,'entry':ep}
  for h in HORIZONS:
   j=i+h
   if j>=len(b) or b.iloc[j].time!=entry.time+pd.Timedelta(minutes=h-1): row[f'fwd_{h}m_atr']=np.nan
   else: row[f'fwd_{h}m_atr']=d*(float(b.iloc[j].close)-ep)/atr
  rows.append(row)
 return pd.DataFrame(rows)
def window(df,p):
 t=pd.to_datetime(df.signal_time,utc=True)
 if p=='TRAIN': return df[t<TRAIN_END]
 if p=='VALID': return df[(t>=TRAIN_END)&(t<VALID_END)]
 if p=='LATE': return df[(t>=VALID_END)&(t<=LATE_END)]
 if p=='POST': return df[t>LATE_END]
 if p=='PRE_DISCOVERY': return df[t<VALID_END]
 return df

def day_ci(df,col,n=10000):
 z=df.dropna(subset=[col]).copy()
 if z.empty:return [None,None]
 z['day']=pd.to_datetime(z.signal_time,utc=True).dt.date; gs=[g[col].to_numpy(float) for _,g in z.groupby('day')]
 if len(gs)<2:return [None,None]
 rng=np.random.default_rng(SEED); vals=np.empty(n); k=len(gs)
 for j in range(n): vals[j]=np.concatenate([gs[i] for i in rng.integers(0,k,k)]).mean()
 return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]
def metric(df,h):
 col=f'fwd_{h}m_atr'; z=df.dropna(subset=[col]).copy(); v=z[col].to_numpy(float)
 if len(z): z['day']=pd.to_datetime(z.signal_time,utc=True).dt.date; daily=z.groupby('day')[col].mean()
 else: daily=pd.Series(dtype=float)
 return {'n':int(len(v)),'ev':float(v.mean()) if len(v) else None,'median':float(np.median(v)) if len(v) else None,'wr':float((v>0).mean()*100) if len(v) else None,'ci95_day':day_ci(df,col),'days':int(len(daily)),'positive_days':int((daily>0).sum()),'median_daily':float(daily.median()) if len(daily) else None}
def summarize(df): return {p:{str(h):metric(window(df,p),h) for h in HORIZONS} for p in ('TRAIN','VALID','LATE','POST','PRE_DISCOVERY','FULL')}
def parity(a,b):
 common_start=max(pd.to_datetime(a.signal_time,utc=True).min(),pd.to_datetime(b.signal_time,utc=True).min()); common_end=min(pd.to_datetime(a.signal_time,utc=True).max(),pd.to_datetime(b.signal_time,utc=True).max())
 A=set(pd.to_datetime(a.loc[(pd.to_datetime(a.signal_time,utc=True)>=common_start)&(pd.to_datetime(a.signal_time,utc=True)<=common_end),'signal_time'],utc=True).map(lambda x:x.isoformat()))
 B=set(pd.to_datetime(b.loc[(pd.to_datetime(b.signal_time,utc=True)>=common_start)&(pd.to_datetime(b.signal_time,utc=True)<=common_end),'signal_time'],utc=True).map(lambda x:x.isoformat()))
 return {'start':common_start.isoformat(),'end':common_end.isoformat(),'rithmic_n':len(A),'amp_n':len(B),'matched':len(A&B),'rithmic_only':len(A-B),'amp_only':len(B-A),'jaccard':len(A&B)/len(A|B) if A|B else 1.0}
def f(v):return 'NA' if v is None else f'{v:+.3f}'
def main():
 m=load_base(); rb,ab=sources(m); result={}; exported=[]
 for rule in RULES:
  re=events(rb,rule); ae=events(ab,rule); result[rule]={'rithmic':summarize(re),'amp':summarize(ae),'parity':parity(re,ae)}
  exported += [re.assign(source_feed='RITHMIC'),ae.assign(source_feed='AMP')]
 pd.concat(exported,ignore_index=True).to_csv(OUT_EVENTS,index=False)
 cand=result['BUYER_BREAKOUT_LONG']; ctrl=result['PRICE_BREAKOUT_NO_OF']; mir=result['MIRROR_SELLER_BREAKOUT_SHORT']
 result['incremental_diagnostics']={}
 for feed in ('rithmic','amp'):
  result['incremental_diagnostics'][feed]={}
  for p in ('TRAIN','VALID','LATE','POST','PRE_DISCOVERY','FULL'):
   ce=cand[feed][p]['15']['ev']; pe=ctrl[feed][p]['15']['ev']; me=mir[feed][p]['15']['ev']
   result['incremental_diagnostics'][feed][p]={'candidate_minus_price_no_of_15m':None if ce is None or pe is None else ce-pe,'candidate_minus_mirror_15m':None if ce is None or me is None else ce-me}
 result['lab']='GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004'; result['status']='POST_DISCOVERY_HISTORICAL_CANDIDATE_AUDIT_NOT_OOS'; OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
 lines=['# GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004','','Frozen after bounded discovery 003. **Historical candidate audit, not OOS.**','', 'Candidate: extreme buyer aggression (prior240 delta Q90 + buy-volume Q75), high reaches prior20 high, bullish body, top-quartile close, next M1 open LONG.','', '| Feed/period | N | 5m EV | 15m EV | 15m day-CI95 | Price-no-OF 15m | Mirror SHORT 15m |','|---|---:|---:|---:|---:|---:|---:|']
 for feed,label in [('rithmic','Rithmic'),('amp','AMP')]:
  for p in ('TRAIN','VALID','LATE','POST','PRE_DISCOVERY','FULL'):
   c=cand[feed][p]; pc=result['PRICE_BREAKOUT_NO_OF'][feed][p]; mm=mir[feed][p]; ci=c['15']['ci95_day']; cis='NA' if ci[0] is None else f'[{ci[0]:+.3f},{ci[1]:+.3f}]'
   lines.append(f"| {label} {p} | {c['15']['n']} | {f(c['5']['ev'])} | {f(c['15']['ev'])} | {cis} | {f(pc['15']['ev'])} | {f(mm['15']['ev'])} |")
 lines += ['','## Feed event parity','',f"Candidate common-clock event Jaccard: **{cand['parity']['jaccard']:.3f}** ({cand['parity']['matched']} exact matches; R {cand['parity']['rithmic_n']}, AMP {cand['parity']['amp_n']}).",'', '## Interpretation','','The key question is whether buyer order flow adds information beyond the same bullish local-high price pattern. A positive candidate with a near-zero/negative PRICE_BREAKOUT_NO_OF complement is stronger evidence for a genuine order-flow selector. Mirror SHORT is reported to expose directional asymmetry rather than hiding it.']
 OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(OUT_MD.read_text())
if __name__=='__main__':main()
