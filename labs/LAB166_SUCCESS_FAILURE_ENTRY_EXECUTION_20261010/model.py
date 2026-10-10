import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from prepare import R,O
import json,joblib,numpy as np,pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score,brier_score_loss,average_precision_score
RETENTIONS=[.25,.5,.75]

def clustered_diff(q,predicate):
 # Resample identical calendar weeks for subset and its full parent.
 w=q.assign(selected=np.asarray(predicate,dtype=bool));rows=[]
 for _,v in w.groupby('week'):
  z=v[v.selected];rows.append([v.success.sum(),len(v),z.success.sum(),len(z)])
 a=np.asarray(rows,float);rng=np.random.default_rng(166);boot=[]
 for _ in range(500):
  z=a[rng.integers(len(a),size=len(a))].sum(axis=0)
  if z[3]>0:boot.append(z[2]/z[3]-z[0]/z[1])
 return np.percentile(boot,[2.5,97.5])*100 if boot else [np.nan,np.nan]

def main():
 x=pd.read_csv(O/'features.csv.gz',parse_dates=['time']);groups=json.loads((O/'feature_groups.json').read_text());valid=x[x.split!='PURGED'].copy();fit=valid[valid.split=='FIT'];cal=valid[valid.split=='CAL'];cols=sum(groups.values(),[]);des=[];bucket=[]
 for feature in cols:
  borders=np.unique(np.nanquantile(fit[feature],[0,.2,.4,.6,.8,1]));
  for split,q in valid.groupby('split'):
   good=q.loc[q.success==1,feature].dropna();bad=q.loc[q.success==0,feature].dropna();pool=np.sqrt((good.var()+bad.var())/2);smd=(good.mean()-bad.mean())/pool if pool>0 else np.nan;des.append(dict(feature=feature,split=split,success_n=len(good),failure_n=len(bad),success_median=good.median(),failure_median=bad.median(),standardized_difference=smd))
   if len(borders)>=3:
    edges=np.r_[-np.inf,borders[1:-1],np.inf];cats=pd.cut(q[feature],edges,include_lowest=True)
    for label,v in q.groupby(cats,observed=True):bucket.append(dict(feature=feature,split=split,bucket=str(label),n=len(v),success_pct=100*v.success.mean()))
 pd.DataFrame(des).to_csv(O/'feature_comparison.csv',index=False);pd.DataFrame(bucket).to_csv(O/'feature_buckets.csv',index=False)
 rates=[]
 for keys in [['shape'],['D1_alignment','H4_alignment'],['H1_alignment','M15_alignment'],['room_over1atr'],['room_over2atr']]:
  for key,q in valid.groupby(['split']+keys,dropna=False):rates.append(dict(zip(['split']+keys,key))|dict(grouping='+'.join(keys),n=len(q),success_pct=100*q.success.mean()))
 pd.DataFrame(rates).to_csv(O/'state_success_rates.csv',index=False)
 metrics=[];filters=[];features=[];md=O/'models';md.mkdir(exist_ok=True);previous={}
 for level,new in groups.items():
  features+=new;print('fit',level,len(features),len(fit),flush=True);model=HistGradientBoostingClassifier(max_iter=80,max_leaf_nodes=7,min_samples_leaf=50,learning_rate=.05,l2_regularization=10,early_stopping=False,random_state=166);model.fit(fit[features],fit.success);cv=model.predict_proba(cal[features])[:,1];pr=model.predict_proba(valid[features])[:,1];valid['score_'+level]=pr;joblib.dump(dict(model=model,features=list(features),fit_years=[2021,2022]),md/f'{level}.joblib',compress=3)
  for split in ['CAL','VALIDATION','CHECK']:
   q=valid[valid.split==split];p=q['score_'+level].to_numpy();y=q.success.to_numpy();loss=(p-y)**2;delta=lo=hi=np.nan
   if split in previous:
    diff=loss-previous[split];wk=pd.DataFrame({'week':q.week,'diff':diff}).groupby('week')['diff'].agg(['sum','count']);a=wk.to_numpy();rng=np.random.default_rng(166);bs=[]
    for _ in range(500):
     z=a[rng.integers(len(a),size=len(a))].sum(axis=0);bs.append(z[0]/z[1])
    delta=diff.mean();lo,hi=np.percentile(bs,[2.5,97.5])
   metrics.append(dict(model=level,split=split,n=len(q),base_success_pct=100*y.mean(),brier=brier_score_loss(y,p),constant_brier=brier_score_loss(y,np.full(len(y),fit.success.mean())),auc=roc_auc_score(y,p),average_precision=average_precision_score(y,p),delta_vs_previous=delta,delta_ci_low=lo,delta_ci_high=hi));previous[split]=loss
  for retention in RETENTIONS:
   threshold=float(np.quantile(cv,1-retention));valid[f'pass_{level}_{int(retention*100)}']=valid['score_'+level]>=threshold
   for period,mask in [('CAL',valid.split=='CAL'),('VALIDATION',valid.split=='VALIDATION'),('CHECK',valid.split=='CHECK'),('CHECK_2025',valid.year==2025),('CHECK_2026',valid.year==2026)]:
    q=valid[mask];selected=q['score_'+level]>=threshold;z=q[selected];lo,hi=clustered_diff(q,selected);filters.append(dict(model=level,retention=retention,threshold=threshold,period=period,n=len(q),selected_n=len(z),actual_retention_pct=100*len(z)/len(q),base_success_pct=100*q.success.mean(),selected_success_pct=100*z.success.mean(),uplift_pp=100*(z.success.mean()-q.success.mean()),uplift_ci_low=lo,uplift_ci_high=hi))
 valid.to_csv(O/'scored_signals.csv.gz',index=False,compression='gzip');pd.DataFrame(metrics).to_csv(O/'ablation_metrics.csv',index=False);pd.DataFrame(filters).to_csv(O/'filter_metrics.csv',index=False)
 thresholds=pd.DataFrame(filters)[['model','retention','threshold']].drop_duplicates();thresholds.to_csv(O/'thresholds.csv',index=False);check=valid[valid.split=='CHECK'];assert fit.time.max()+pd.Timedelta(hours=24)<cal.time.min();assert cal.time.max()+pd.Timedelta(hours=24)<valid[valid.split=='VALIDATION'].time.min();assert valid[valid.split=='VALIDATION'].time.max()+pd.Timedelta(hours=24)<check.time.min()
 (O/'model_validation.json').write_text(json.dumps(dict(no_test_refit=True,no_test_threshold_selection=True,primary_filter='OBSTACLES_50',fit_end=str(fit.time.max()),cal_end=str(cal.time.max()),validation_end=str(valid[valid.split=='VALIDATION'].time.max()),check_start=str(check.time.min()),feature_groups=groups),indent=2));print(pd.DataFrame(metrics).to_string(index=False),flush=True);print(pd.DataFrame(filters).query("period=='CHECK' and retention==.5").to_string(index=False),flush=True)
if __name__=='__main__':main()
