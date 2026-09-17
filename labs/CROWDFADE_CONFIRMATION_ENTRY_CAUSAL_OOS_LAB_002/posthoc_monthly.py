from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path('labs/CROWDFADE_CONFIRMATION_ENTRY_CAUSAL_OOS_LAB_002'); OUT=ROOT/'diagnostic_output'; OUT.mkdir(parents=True,exist_ok=True)
CANDS=['confirm_0.25_stop_1.25','confirm_0.25_stop_1.50','confirm_0.35_stop_1.25']

def stat(x):
    x=np.asarray(x,float)
    if not len(x):return {'N':0}
    pos=x[x>0];neg=x[x<0];pf=float(pos.sum()/abs(neg.sum())) if len(neg) else float('inf');eq=np.cumsum(x);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max());se=x.std(ddof=1)/np.sqrt(len(x)) if len(x)>1 else np.nan
    return {'N':int(len(x)),'WR':float((x>0).mean()),'EV':float(x.mean()),'t':float(x.mean()/se) if se>0 else np.nan,'PF':pf,'SumR':float(x.sum()),'MaxDD_R':dd}

def monthly(df,col):
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True); out={}
    for p,g in df.assign(month=t.dt.strftime('%Y-%m')).groupby('month'):
        out[p]=stat(g[col].to_numpy())
    return out

def main():
    res={}
    for c in CANDS:
        b=pd.read_csv(ROOT/'output'/f'trades_{c}.csv'); f=pd.read_csv(ROOT/'ftmo_output'/f'trades_{c}.csv')
        res[c]={'binance_gross':monthly(b,'gross_R'),'binance_half_proxy':monthly(b,'half_cost_R'),'ftmo_native_spread_precommission':monthly(f,'R')}
    (OUT/'monthly_stability.json').write_text(json.dumps(res,indent=2,default=float));print(json.dumps(res,indent=2,default=float))
if __name__=='__main__':main()
