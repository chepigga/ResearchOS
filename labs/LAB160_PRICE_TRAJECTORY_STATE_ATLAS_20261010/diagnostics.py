from pathlib import Path
import pandas as pd,numpy as np
P=Path(__file__).resolve().parents[2]/'results/LAB160_20261010'
d=pd.read_parquet(P/'LAB160_states.parquet').join(pd.read_parquet(P/'LAB160_labels_6h.parquet'))
d=d[d.valid_state & (d.split!='PURGED') & d.terminal_atr.notna()].copy()
c=pd.read_csv(P/'LAB160_candidates.csv');rows=[];abl=[]
for direction,t in [('UP','up2_before_down1'),('DOWN','down2_before_up1')]:
 b=d[d[t]>=0].copy();b['week']=b.index.strftime('%G-%V')
 for _,r in c[c.direction==direction].iterrows():
  out=r.to_dict()
  for split,prefix in [('DISCOVERY','train'),('VALIDATION','val'),('CHECK','check')]:
   par=b[(b.split==split)&(b.trend==r.trend)&(b.crowd==r.crowd)&(b.oi_bucket==r.oi_bucket)]
   out[prefix+'_parent_probability']=par[t].mean();out[prefix+'_incremental_profile_lift']=r[prefix+'_prob']-par[t].mean()
  rows.append(out)
 for oi in ['oi4h_value','oi4h_quantity']:
  b['oi_state']=pd.cut(b[oi],[-np.inf,0,.0035,.00867,np.inf],right=False,labels=['NEG','LOW','MID','HIGH']).astype(str)
  train=b[b.split=='DISCOVERY'];base=train[t].mean()
  for name,kk in [('FLOW',['trend','crowd','oi_state']),('PROFILE',['trend','crowd','oi_state','shape','location'])]:
   g=train.groupby(kk)[t].agg(['sum','count']);pred=((g['sum']+100*base)/(g['count']+100)).reindex(pd.MultiIndex.from_frame(b[kk])).fillna(base).to_numpy()
   b['err_'+name]=(pred-b[t].to_numpy())**2
  for split in ['VALIDATION','CHECK']:
   q=b[b.split==split];abl.append(dict(direction=direction,split=split,oi_measure=oi,n=len(q),flow_brier=q.err_FLOW.mean(),profile_brier=q.err_PROFILE.mean(),delta=q.err_PROFILE.mean()-q.err_FLOW.mean()))
pd.DataFrame(rows).to_csv(P/'LAB160_candidates_parent_comparison.csv',index=False)
pd.DataFrame(abl).to_csv(P/'LAB160_oi_sensitivity.csv',index=False)
print(pd.DataFrame(abl).to_string(index=False))
print('candidate parent lifts:',pd.DataFrame(rows)[['direction','crowd','shape','location','train_incremental_profile_lift','val_incremental_profile_lift','check_incremental_profile_lift']].to_string(index=False))
x=pd.read_csv(P/'LAB160_state_cells.csv');kk=['direction','trend','crowd','oi_bucket','shape','location']
a=x[x.split=='DISCOVERY'].set_index(kk).add_prefix('train_');v=x[x.split=='VALIDATION'].set_index(kk).add_prefix('val_');ch=x[x.split=='CHECK'].set_index(kk).add_prefix('check_')
s=a.join(v,how='inner');s=s[(s.train_n>=500)&(s.val_n>=100)&(s.val_weeks>=10)&(s.train_lift>=.03)&(s.val_lift>=.03)].join(ch).reset_index();s=s[s.crowd.str.endswith(('_LOW','_MID'))].copy()
pa=x.groupby(['split','direction','trend','crowd','oi_bucket'])[['wins','n']].sum();pa['p']=pa.wins/pa.n
s['check_parent_prob']=[pa.loc[('CHECK',r.direction,r.trend,r.crowd,r.oi_bucket),'p'] for r in s.itertuples()];s['check_profile_lift']=s.check_prob-s.check_parent_prob
for i,r in s.iterrows():
 t='up2_before_down1' if r.direction=='UP' else 'down2_before_up1'
 q=d[(d.split=='CHECK')&(d[t]>=0)]
 for k in kk[1:]:q=q[q[k]==r[k]]
 s.loc[i,'check_episode_starts']=(q.index.to_series().diff()!=pd.Timedelta(minutes=5)).sum()
 n=0;last=None
 for tm in q.index:
  if last is None or tm-last>=pd.Timedelta(hours=48):n+=1;last=tm
 s.loc[i,'check_48h_separated']=n
s.to_csv(P/'LAB160_weak_z_candidates_SUPPLEMENTAL.csv',index=False)
rows=[]
for (split,z),g in d.groupby(['split','z_bucket']):
 rows.append(dict(split=split,z_bucket=z,n=len(g),up2_first=(g.up2_before_down1==1).mean(),down2_first=(g.down2_before_up1==1).mean()))
pd.DataFrame(rows).to_csv(P/'LAB160_z_coverage.csv',index=False)
