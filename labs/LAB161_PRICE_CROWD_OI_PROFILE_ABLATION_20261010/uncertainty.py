from pathlib import Path
import pandas as pd,numpy as np
O=Path(__file__).resolve().parents[2]/'results/LAB161_20261010';s=pd.read_csv(O/'LAB161_signals.csv',parse_dates=['time']);s['week']=s.time.dt.strftime('%G-%V');s['false']=(~s.clean_success).astype(int);models=['PRICE','PRICE_CROWD','PRICE_CROWD_OI','PRICE_CROWD_OI_PROFILE'];rows=[]
for rate in [.5,1.,2.]:
 for year in [2024,2025,2026,'ALL']:
  q=s[(s.requested_per_day==rate)&s.model.isin(models)];q=q if year=='ALL' else q[q.year==year];w=q.groupby(['week','model'])['false'].agg(['sum','count']);sums=w['sum'].unstack(fill_value=0);counts=w['count'].unstack(fill_value=0);rng=np.random.default_rng(161);ix=rng.integers(len(sums),size=(1000,len(sums)))
  for prev,cur in zip(models[:-1],models[1:]):
   a=sums[cur].to_numpy();b=counts[cur].to_numpy();c=sums[prev].to_numpy();d=counts[prev].to_numpy();delta=100*(a.sum()/b.sum()-c.sum()/d.sum());z=100*(a[ix].sum(axis=1)/b[ix].sum(axis=1)-c[ix].sum(axis=1)/d[ix].sum(axis=1));rows.append(dict(year=year,requested_per_day=rate,previous=prev,model=cur,delta_false_pp=delta,ci_low=np.quantile(z,.025),ci_high=np.quantile(z,.975)))
pd.DataFrame(rows).to_csv(O/'LAB161_incremental_false.csv',index=False);print(pd.DataFrame(rows).query("year=='ALL' and requested_per_day==1").round(3).to_string(index=False))
