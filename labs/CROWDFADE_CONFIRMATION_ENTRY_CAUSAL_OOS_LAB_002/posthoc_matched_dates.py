from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path('labs/CROWDFADE_CONFIRMATION_ENTRY_CAUSAL_OOS_LAB_002'); OUT=ROOT/'diagnostic_output'; OUT.mkdir(exist_ok=True)
CANDS=['confirm_0.25_stop_1.50','confirm_0.35_stop_1.25']
PERIODS=[('May','2026-05-01','2026-06-01'),('Jun','2026-06-01','2026-07-01'),('Jul','2026-07-01','2026-08-01'),('Aug1_7','2026-08-01','2026-08-08')]

def st(x):
 x=np.asarray(x,float)
 if not len(x):return {'N':0}
 p=x[x>0];n=x[x<0];pf=float(p.sum()/abs(n.sum())) if len(n) else float('inf');se=x.std(ddof=1)/np.sqrt(len(x)) if len(x)>1 else np.nan
 return {'N':int(len(x)),'EV':float(x.mean()),'WR':float((x>0).mean()),'PF':pf,'t':float(x.mean()/se) if se>0 else np.nan,'SumR':float(x.sum())}

def main():
 out={}
 for c in CANDS:
  b=pd.read_csv(ROOT/'output'/f'trades_{c}.csv');f=pd.read_csv(ROOT/'ftmo_output'/f'trades_{c}.csv')
  out[c]={}
  for label,a,z in PERIODS:
   a=int(pd.Timestamp(a,tz='UTC').timestamp());z=int(pd.Timestamp(z,tz='UTC').timestamp())
   qb=b[(b.signal_ts>=a)&(b.signal_ts<z)];qf=f[(f.signal_ts>=a)&(f.signal_ts<z)]
   out[c][label]={'binance_gross':st(qb.gross_R.values),'ftmo_native_spread_precommission':st(qf.R.values)}
 (OUT/'matched_dates.json').write_text(json.dumps(out,indent=2,default=float));print(json.dumps(out,indent=2,default=float))
if __name__=='__main__':main()
