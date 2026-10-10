"""Necessary control: preserve OLD_PROFILE in both arms; vary profile on new events only."""
from pathlib import Path
import numpy as np,pandas as pd
p=Path(__file__).with_name('run_lab160c.py');src=p.read_text();g={'__file__':str(p)}
exec(compile(src.split('for cost in [7.5,2.81]:')[0],str(p),'exec'),g)
O=g['OUT'];sets=g['sets'];replay=g['replay'];fn=g['fn'];perf=g['perf']
newnames=[]
for name in ['R48_RETEST','R48_OI','R48_BOTH','A_Z075','A_OI50','A_Z075_OI50']:
 d=sets[name];newname=name+'_NEW_ALL';sets[newname]=d[~((d.source=='R48_HIGH')&~d.is_new&(d.profile_shape=='b'))].copy();newnames.append(newname)
 sets[newname].assign(variant=newname).to_csv(O/f'raw_{newname}.csv',index=False)
read=lambda n:pd.read_csv(O/f'LAB160C_{n}.csv').to_dict('records')
summary=read('summary');annual=read('annual');attr=read('attribution');monthly=read('monthly');delta=read('portfolio_delta_decomposition');stand=read('standalone_new')
tt=pd.read_csv(O/'LAB160C_trades.csv');alltr=[tt]
for cost in [7.5,2.81]:
 for name in newnames:
  d=sets[name];t,eq,sk,adds=replay(d,cost);s=fn.stats(t,eq);s.update(variant=name,cost_bps=cost,raw_n=len(d),new_raw=int(d.is_new.sum()),skipped=sk,addons=adds,trades_month=len(t)/48,r_month=t.net_r.sum()/48,mtm_dd_pct_with_initial_zero=float((np.maximum.accumulate(np.r_[0,eq.equity_r])[1:]-eq.equity_r).max()*.25));summary.append(s)
  t['variant']=name;t['cost_bps']=cost;alltr.append(t)
  for y,q in t.groupby(pd.to_datetime(t.entry_time).dt.year):annual.append(dict(variant=name,cost_bps=cost,year=int(y),**perf(q)))
  for new,q in t.groupby('is_new'):attr.append(dict(variant=name,cost_bps=cost,cohort='NEW_RAW_ACCEPTED' if new else 'OLD_RAW_ACCEPTED',**perf(q)))
  m=t.groupby(pd.to_datetime(t.exit_time).dt.strftime('%Y-%m')).net_r.sum().reindex(pd.period_range('2021-01','2024-12',freq='M').astype(str),fill_value=0);assert abs(m.sum()-t.net_r.sum())<1e-8
  monthly.extend([dict(cost_bps=cost,variant=name,month=month,total_r=v) for month,v in m.items()])
  for base in ['OLD','OLD_PROFILE']:
   b=tt[(tt.variant==base)&(tt.cost_bps==cost)];common=set(t.event_id)&set(b.event_id);added=t[~t.event_id.isin(b.event_id)];removed=b[~b.event_id.isin(t.event_id)];change=t[t.event_id.isin(common)].net_r.sum()-b[b.event_id.isin(common)].net_r.sum();diff=t.net_r.sum()-b.net_r.sum();assert abs(diff-(added.net_r.sum()-removed.net_r.sum()+change))<1e-8
   delta.append(dict(cost_bps=cost,variant=name,baseline=base,delta_r=diff,delta_rmo=diff/48,added_executed_n=len(added),added_executed_r=added.net_r.sum(),removed_n=len(removed),removed_r=removed.net_r.sum(),common_outcome_delta_r=change))
  # Standalone new universe and ATR are identical to corresponding no-profile arm.
  stand.extend([dict(r,variant=name) for r in list(stand) if r['variant']==name.removesuffix('_NEW_ALL') and r['cost_bps']==cost])
  print(cost,name,'N',len(t),'PF',round(s['pf'],3),'Rmo',round(s['r_month'],3),'DD',round(s['mtm_dd_pct'],3),flush=True)
for n,rows in [('summary',summary),('annual',annual),('attribution',attr),('monthly',monthly),('portfolio_delta_decomposition',delta),('standalone_new',stand)]:pd.DataFrame(rows).to_csv(O/f'LAB160C_{n}.csv',index=False)
pd.concat(alltr,ignore_index=True).to_csv(O/'LAB160C_trades.csv',index=False)
# Same seed resampling across paired comparisons, all arms published.
mo=pd.DataFrame(monthly);cis=[];rng=np.random.default_rng(1603);indices=rng.integers(0,48,size=(2000,48))
for cost in [7.5,2.81]:
 m=mo[mo.cost_bps==cost].pivot(index='month',columns='variant',values='total_r')
 for name in m:
  bases=['OLD','OLD_PROFILE']
  if name.endswith('_PROFILE') and name!='OLD_PROFILE':bases.append(name.removesuffix('_PROFILE')+'_NEW_ALL')
  for base in bases:
   diff=(m[name]-m[base]).to_numpy();means=diff[indices].mean(axis=1);cis.append(dict(cost_bps=cost,variant=name,baseline=base,delta_rmo=diff.mean(),ci_low=np.quantile(means,.025),ci_high=np.quantile(means,.975),positive_months=int((diff>0).sum())))
pd.DataFrame(cis).to_csv(O/'LAB160C_delta_monthly_bootstrap.csv',index=False)
print('MATCHED CONTROLS COMPLETE')

import json
meta=json.loads((O/'LAB160C_meta.json').read_text());meta.update(variants=20,cost_scenarios=2,matched_control_amendment=True)
(O/'LAB160C_meta.json').write_text(json.dumps(meta,indent=2))
