import pandas as pd, numpy as np
from pathlib import Path
COST=27.5
WIDTHS=[1.5,2.0,2.5,3.0,4.0,5.0,7.5]
out=Path('u02c1f'); out.mkdir(exist_ok=True)
r=pd.read_csv('prior/events.csv')
c=pd.read_csv('continuation.csv')[['zone_id','entry_price','NET48_SPREAD_PCT','year']].drop_duplicates('zone_id')
r=r.drop(columns=['frozen_net48','year'],errors='ignore').merge(c,on='zone_id',how='left')
assert len(r)==176 and r.entry_price.notna().all(), (len(r),r.entry_price.isna().sum())
old=r.entry.to_numpy(float); a=r.atr_h1.to_numpy(float)
maxp=old+r.adverse_atr.to_numpy(float)*a
minp=old-r.favorable_atr.to_numpy(float)*a
net_old=r.terminal_net_pct.to_numpy(float)
terminal=old*(1-net_old/100.0)-COST
f=r.entry_price.to_numpy(float)
r['entry_frozen']=f; r['terminal_abs']=terminal
r['adverse_atr_frozen']=(maxp-f)/a
r['favorable_atr_frozen']=(f-minp)/a
r['terminal_net_pct_frozen']=(f-terminal)/f*100-COST/f*100

def pf(x):
    s=pd.Series(x).dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum(); return float(gp/gl) if gl>0 else float('inf')
for w in WIDTHS:
    hit=maxp>=f+w*a; costR=COST/(w*a)
    r[f'hit_{w:g}']=hit
    r[f'R_{w:g}']=np.where(hit,-1-costR,(f-terminal)/(w*a)-costR)
    r[f'pct_{w:g}']=np.where(hit,-(w*a)/f*100-COST/f*100,(f-terminal)/f*100-COST/f*100)
aq=r.adverse_atr_frozen.quantile([.25,.5,.75,.9,.95,.99]).rename('adverse_atr').reset_index().rename(columns={'index':'quantile'})
fq=r.favorable_atr_frozen.quantile([.25,.5,.75,.9,.95,.99]).rename('favorable_atr').reset_index().rename(columns={'index':'quantile'})
sm=[]
for w in WIDTHS:
    z=r[f'R_{w:g}']; p=r[f'pct_{w:g}']
    sm.append({'stop_atr':w,'N':len(r),'stop_hit_rate':r[f'hit_{w:g}'].mean(),'EV_R':z.mean(),'PF_R':pf(z),'WR_R':(z>0).mean(),'EV_pct':p.mean(),'PF_pct':pf(p),'WR_pct':(p>0).mean()})
sm=pd.DataFrame(sm)
yr=[]
for y,g in r.groupby('year'):
    for w in WIDTHS:
        z=g[f'R_{w:g}']; yr.append({'year':int(y),'stop_atr':w,'N':len(g),'stop_hit_rate':g[f'hit_{w:g}'].mean(),'EV_R':z.mean(),'PF_R':pf(z),'WR_R':(z>0).mean()})
yr=pd.DataFrame(yr)
r['parity_diff']=r.terminal_net_pct_frozen-r.NET48_SPREAD_PCT
print('ADVERSE'); print(aq.to_string(index=False))
print('\nFAVORABLE'); print(fq.to_string(index=False))
print('\nSUMMARY'); print(sm.to_string(index=False))
print('\nYEARLY'); print(yr.to_string(index=False))
print('\nNO_STOP',r.terminal_net_pct_frozen.mean(),pf(r.terminal_net_pct_frozen),(r.terminal_net_pct_frozen>0).mean())
print('PARITY_MAE',r.parity_diff.abs().mean(),'MAX',r.parity_diff.abs().max(),'CORR',r[['terminal_net_pct_frozen','NET48_SPREAD_PCT']].corr().iloc[0,1])
r.to_csv(out/'events.csv',index=False); aq.to_csv(out/'adverse_quantiles.csv',index=False); fq.to_csv(out/'favorable_quantiles.csv',index=False); sm.to_csv(out/'summary.csv',index=False); yr.to_csv(out/'yearly.csv',index=False)
(out/'REPORT.md').write_text('\n'.join(['# U02C1F SELL B3 Frozen Entry Stop Width','',f'N={len(r)}','',aq.to_markdown(index=False),'',sm.to_markdown(index=False),'',yr.to_markdown(index=False),'',f'No-stop EV={r.terminal_net_pct_frozen.mean():.6f}% PF={pf(r.terminal_net_pct_frozen):.4f} WR={(r.terminal_net_pct_frozen>0).mean():.3f}',f'Parity MAE={r.parity_diff.abs().mean():.6f}pp corr={r[["terminal_net_pct_frozen","NET48_SPREAD_PCT"]].corr().iloc[0,1]:.4f}']))
