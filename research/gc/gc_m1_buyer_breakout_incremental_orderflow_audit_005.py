#!/usr/bin/env python3
"""GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005

Tests whether the frozen historical BUYER_BREAKOUT_LONG candidate adds information
beyond the same bullish price-breakout structure.

No thresholds are searched. Candidate is frozen from LAB003/004:
- price breakout: bullish M1, close_pos >= 0.75, high >= prior20 completed-bar high
- buyer-flow gate: buyer A = delta_frac >= prior240 Q90 AND buy_vol >= prior240 Q75
- enter exact next clock-contiguous M1 open, LONG
- fixed diagnostic horizons: 5m and 15m

Controls:
1) price-only complement (same price breakout, buyer A false)
2) deterministic time-placebo shifts of the buyer-A state relative to price bars:
   +/-1,2,3,5,10,15,30,60,120 minutes. These are not optimized; all are reported.
3) day-cluster bootstrap for actual candidate-minus-complement delta.

This is historical characterization, not independent OOS certification.
"""
from __future__ import annotations
import importlib.util,json
from pathlib import Path
import numpy as np,pandas as pd

ROOT=Path('research/gc')
BASE=ROOT/'gc_m1_orderflow_edge_discovery_003.py'
OUT_JSON=ROOT/'GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005.json'
OUT_MD=ROOT/'GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005.md'
OUT_CSV=ROOT/'GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005_PLACEBOS.csv'
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
LATE_END=pd.Timestamp('2026-09-11T12:46:00Z')
SHIFTS=(-120,-60,-30,-15,-10,-5,-3,-2,-1,1,2,3,5,10,15,30,60,120)
SEED=20260915
HORIZONS=(5,15)


def load_base():
 spec=importlib.util.spec_from_file_location('edge003',BASE); m=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(m); return m

def sources(m):
 work=ROOT/'_edge003_work'; work.mkdir(exist_ok=True); rz=work/'rithmic.zip'; az=work/'amp.zip'
 if not rz.exists(): m.download(m.RITH_URL,rz)
 if not az.exists(): m.download(m.AMP_URL,az)
 if m.sha(rz)!=m.RITH_SHA or m.sha(az)!=m.AMP_SHA: raise SystemExit('source SHA mismatch')
 return m.load_rithmic(rz),m.load_amp(az)

def window_mask(t,label):
 if label=='TRAIN': return t<TRAIN_END
 if label=='VALID': return (t>=TRAIN_END)&(t<VALID_END)
 if label=='LATE': return (t>=VALID_END)&(t<=LATE_END)
 if label=='POST': return t>LATE_END
 if label=='PRE_DISCOVERY': return t<VALID_END
 if label=='FULL': return pd.Series(True,index=t.index)
 raise ValueError(label)

def build_universe(b):
 buyer_a=b.aggr.eq('BUY')
 price=(b.close>b.open)&(b.close_pos>=.75)&(b.high>=b.prior20_high)
 rows=[]
 for i in np.flatnonzero(price.to_numpy()):
  if i+1>=len(b): continue
  entry=b.iloc[i+1]
  if entry.time!=b.iloc[i].time+pd.Timedelta(minutes=1): continue
  atr=float(b.iloc[i].atr14)
  if not np.isfinite(atr) or atr<=0: continue
  row={'signal_i':i,'time':b.iloc[i].time,'day':b.iloc[i].time.date(),'entry_time':entry.time,'atr14':atr,'entry':float(entry.open),'buyer_a':bool(buyer_a.iloc[i])}
  for h in HORIZONS:
   j=i+h
   if j>=len(b) or b.iloc[j].time!=entry.time+pd.Timedelta(minutes=h-1): row[f'r{h}']=np.nan
   else: row[f'r{h}']=(float(b.iloc[j].close)-float(entry.open))/atr
  rows.append(row)
 return pd.DataFrame(rows),buyer_a

def ev(z,col):
 v=z[col].dropna().to_numpy(float); return float(v.mean()) if len(v) else None

def delta_bootstrap(z,col,n=10000):
 q=z.dropna(subset=[col]).copy()
 days=sorted(q.day.unique())
 if len(days)<2:return [None,None]
 groups={d:q[q.day==d] for d in days}; rng=np.random.default_rng(SEED); vals=[]
 for _ in range(n):
  picks=rng.choice(days,size=len(days),replace=True); parts=[groups[d] for d in picks]; s=pd.concat(parts,ignore_index=True)
  a=s[s.buyer_a]; c=s[~s.buyer_a]
  if len(a) and len(c): vals.append(float(a[col].mean()-c[col].mean()))
 if not vals:return [None,None]
 return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]

def actual_metrics(u,label):
 t=pd.to_datetime(u.time,utc=True); z=u[window_mask(t,label)].copy(); a=z[z.buyer_a]; c=z[~z.buyer_a]
 out={'price_n':int(len(z)),'candidate_n':int(len(a)),'complement_n':int(len(c))}
 for h in HORIZONS:
  ae=ev(a,f'r{h}'); ce=ev(c,f'r{h}')
  out[str(h)]={'candidate_ev':ae,'complement_ev':ce,'incremental':None if ae is None or ce is None else ae-ce,'incremental_day_bootstrap95':delta_bootstrap(z,f'r{h}')}
 return out

def placebo_rows(b,u,buyer_a,feed,label):
 t=pd.to_datetime(u.time,utc=True); z=u[window_mask(t,label)].copy(); time_to_a=dict(zip(b.time,buyer_a.astype(bool))); rows=[]
 for shift in SHIFTS:
  sel=z.time.map(lambda x: bool(time_to_a.get(x-pd.Timedelta(minutes=shift),False)))
  a=z[sel.to_numpy()]; c=z[~sel.to_numpy()]
  for h in HORIZONS:
   ae=ev(a,f'r{h}'); ce=ev(c,f'r{h}')
   rows.append({'feed':feed,'period':label,'shift_min':shift,'horizon':h,'candidate_n':int(len(a)),'candidate_ev':ae,'complement_ev':ce,'incremental':None if ae is None or ce is None else ae-ce})
 return rows

def audit_feed(b,feed):
 u,a=build_universe(b); periods={p:actual_metrics(u,p) for p in ('TRAIN','VALID','LATE','POST','PRE_DISCOVERY','FULL')}; rows=[]
 for p in periods: rows+=placebo_rows(b,u,a,feed,p)
 return periods,rows

def placebo_summary(rows,feed,period,h=15):
 x=pd.DataFrame(rows); x=x[(x.feed==feed)&(x.period==period)&(x.horizon==h)].dropna(subset=['incremental'])
 if x.empty:return {'n':0,'mean':None,'max':None,'positive_fraction':None}
 return {'n':int(len(x)),'mean':float(x.incremental.mean()),'max':float(x.incremental.max()),'positive_fraction':float((x.incremental>0).mean())}
def f(v):return 'NA' if v is None else f'{v:+.3f}'
def main():
 m=load_base(); rb,ab=sources(m); rr,rp=audit_feed(rb,'RITHMIC'); ar,ap=audit_feed(ab,'AMP'); rows=rp+ap; pd.DataFrame(rows).to_csv(OUT_CSV,index=False)
 result={'lab':'GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005','status':'HISTORICAL_INCREMENTAL_AUDIT_NOT_OOS','actual':{'rithmic':rr,'amp':ar},'placebo':{}}
 for feed in ('RITHMIC','AMP'):
  result['placebo'][feed]={p:placebo_summary(rows,feed,p,15) for p in ('TRAIN','VALID','LATE','POST','PRE_DISCOVERY','FULL')}
 OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
 lines=['# GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005','','Historical incremental-information audit; no threshold search.','', '| Feed/period | Price N | OF N | OF 15m | No-OF 15m | Incremental | Delta CI95 | Placebo mean inc | Placebo max inc |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for feed,label,data in [('RITHMIC','Rithmic',rr),('AMP','AMP',ar)]:
  for p in ('TRAIN','VALID','LATE','POST','PRE_DISCOVERY','FULL'):
   x=data[p]; d=x['15']; ci=d['incremental_day_bootstrap95']; cis='NA' if ci[0] is None else f'[{ci[0]:+.3f},{ci[1]:+.3f}]'; ps=result['placebo'][feed][p]
   lines.append(f"| {label} {p} | {x['price_n']} | {x['candidate_n']} | {f(d['candidate_ev'])} | {f(d['complement_ev'])} | {f(d['incremental'])} | {cis} | {f(ps['mean'])} | {f(ps['max'])} |")
 lines += ['','## Interpretation','','A useful order-flow edge should show positive synchronous incremental return versus the same price-breakout complement, preferably larger than typical shifted-flow placebo alignment. Because the candidate was discovered historically, even a strong result here creates a **frozen historical candidate**, not a validated OOS strategy.']
 OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(OUT_MD.read_text())
if __name__=='__main__':main()
