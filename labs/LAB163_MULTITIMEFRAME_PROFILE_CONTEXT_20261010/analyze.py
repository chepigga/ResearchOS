from pathlib import Path
import json
import pandas as pd,numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/LAB163_20261010';P=['level','contact','side'];F={'D1':['D1'],'H4':['H4'],'D1_H4':['D1','H4'],'H4_H1':['H4','H1'],'D1_H4_H1':['D1','H4','H1'],'H4_H1_PHASE':['H4','H1','H1_phase'],'LOCAL_STACK':['H4','H1','M15','M5'],'HIGHER':['higher_context'],'HIGHER_SHAPE':['higher_context','shape'],'JOINT':['higher_context','H1','shape','oi_state','crowd_state']}
def ci_lift(child,parent,target):
 c=child.groupby('week')[target].agg(['sum','count']);p=parent.groupby('week')[target].agg(['sum','count']);ix=c.index.union(p.index);c=c.reindex(ix,fill_value=0);p=p.reindex(ix,fill_value=0);rng=np.random.default_rng(162);j=rng.integers(len(ix),size=(2000,len(ix)));cn=c['count'].to_numpy()[j].sum(axis=1);pn=p['count'].to_numpy()[j].sum(axis=1);valid=(cn>0)&(pn>0);delta=c['sum'].to_numpy()[j].sum(axis=1)[valid]/cn[valid]-p['sum'].to_numpy()[j].sum(axis=1)[valid]/pn[valid];return np.quantile(delta,[.025,.975])
def main():
 e=pd.read_csv(O/'LAB163_encounters.csv',parse_dates=['time']);e=e[e.split!='PURGED'];rows=[]
 for fam,extras in F.items():
  keys=P+extras;tables=[]
  for split in ['DISCOVERY','VALIDATION','CHECK']:
   v=e[e.split==split];parent=v.groupby(P).agg(parent_n=('event_id','size'),parent_pass=('pass_hit','mean'),parent_reject=('reject_hit','mean')).reset_index();tab=v.groupby(keys).agg(n=('event_id','size'),weeks=('week','nunique'),pass_rate=('pass_hit','mean'),reject_rate=('reject_hit','mean')).reset_index().merge(parent,on=P);tab['pass_lift']=tab.pass_rate-tab.parent_pass;tab['reject_lift']=tab.reject_rate-tab.parent_reject;tab=tab.set_index(keys).add_prefix(split.lower()+'_');tables.append(tab)
  tab=tables[0].join(tables[1],how='left').join(tables[2],how='left').reset_index();tab['family']=fam;rows.append(tab)
 allcells=pd.concat(rows,ignore_index=True);allcells.to_csv(O/'LAB163_all_condition_cells.csv',index=False);candidates=[]
 for target in ['pass','reject']:
  keep=(allcells.discovery_n>=100)&(allcells.discovery_weeks>=20)&(allcells.validation_n>=30)&(allcells.validation_weeks>=10)&(allcells[f'discovery_{target}_lift']>=.10)&(allcells[f'validation_{target}_lift']>=.05)
  t=allcells[keep].copy();t['target']=target;candidates.append(t)
 candidates=pd.concat(candidates,ignore_index=True);candidates['rank_lift']=[r[f'discovery_{r.target}_lift'] for _,r in candidates.iterrows()];candidates=candidates.sort_values('rank_lift',ascending=False,kind='stable');selected=candidates.head(10).copy();selected['candidate_id']=['C%02d'%i for i in range(1,len(selected)+1)];selected['check_ci_low']=np.nan;selected['check_ci_high']=np.nan;selected['provisional_replication']=False
 for idx,r in selected.iterrows():
  v=e[e.split=='CHECK'];parent=v.copy()
  for k in P:parent=parent[parent[k]==r[k]]
  child=parent.copy()
  for k in F[r.family]:child=child[child[k]==r[k]]
  if len(child)>=30 and child.week.nunique()>=10:
   low,high=ci_lift(child,parent,r.target+'_hit');selected.loc[idx,['check_ci_low','check_ci_high']]=[low,high];selected.loc[idx,'provisional_replication']=low>0
 selected.to_csv(O/'LAB163_selected_candidates.csv',index=False);candidates.to_csv(O/'LAB163_qualified_candidates.csv',index=False)
 support=(allcells.discovery_n>=100)&(allcells.discovery_weeks>=20)&(allcells.validation_n>=30)&(allcells.validation_weeks>=10)
 audit=dict(sufficient_support_cells=int(support.sum()),discovery_lift_pass_cells=int((support&(allcells.discovery_pass_lift>=.10)).sum()),discovery_lift_reject_cells=int((support&(allcells.discovery_reject_lift>=.10)).sum()),condition_cells=len(allcells),outcome_tests=len(allcells)*2,qualified_train_validation=len(candidates),selected=len(selected),provisional_replicated=int(selected.provisional_replication.sum()),events=len(e),unique_event_times=e.time.nunique(),years=e.groupby(e.time.dt.year).size().to_dict());(O/'LAB163_search_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit));print(selected.to_string(index=False))
if __name__=='__main__':main()
