# Supplementary descriptive diagnostic, added after encounter results; not a candidate-selection rule.
from pathlib import Path
import pandas as pd,numpy as np
O=Path(__file__).resolve().parents[2]/'results/LAB162_20261010';d=pd.read_pickle(O/'LAB162_tape.pkl');x=pd.DataFrame(index=d.index);x['LS_change_1h']=d.ratio/d.ratio.shift(12)-1;x['OI_change_1h']=d.oi_quantity/d.oi_quantity.shift(12)-1;x['POC_change_1h']=(d.POC_HVN-d.POC_HVN.shift(12))/d.atr;x['price_previous_1h']=(d.close-d.close.shift(12))/d.atr;x['price_next_1h']=(d.close.shift(-12)-d.close)/d.atr;x=x[x.index.minute==0].replace([np.inf,-np.inf],np.nan);rows=[]
for year in sorted(x.index.year.unique()):
 q=x[x.index.year==year]
 for f in ['LS_change_1h','OI_change_1h','POC_change_1h']:
  for target in ['price_previous_1h','price_next_1h']:
   z=q[[f,target]].dropna();rows.append(dict(year=int(year),feature=f,price_window=target,n=len(z),spearman=z[f].corr(z[target],method='spearman')))
pd.DataFrame(rows).to_csv(O/'LAB162_lead_lag_descriptive.csv',index=False);print(pd.DataFrame(rows).pivot(index=['year','feature'],columns='price_window',values='spearman').round(3).to_string())
