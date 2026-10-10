import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from pathlib import Path
import json,time,platform
import numpy as np,pandas as pd,sklearn,joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss,average_precision_score,roc_auc_score
from numba import njit
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/LAB161_20261010'
RATES=[.5,1.,2.];MODELS=['PRICE','PRICE_CROWD','PRICE_CROWD_OI','PRICE_CROWD_OI_PROFILE']
@njit
def emit(t,score,threshold):
 ans=[];last=-10**18
 for i in range(len(t)):
  if score[i]>=threshold and t[i]-last>=360:ans.append(i);last=t[i]
 return np.array(ans,dtype=np.int64)
def choose(t,score,days,rate):
 thresholds=np.unique(np.r_[np.quantile(score,np.linspace(0,.999,201)),1.000001]);records=[]
 for th in thresholds:records.append((abs(len(emit(t,score,th))/days-rate),-th,th,len(emit(t,score,th))))
 _,_,threshold,n=min(records);return threshold,n/days

def main():
 d=pd.read_pickle(OUT/'LAB161_dataset.pkl');g=json.loads((OUT/'LAB161_features.json').read_text());eligible=d[d.eligible];signals=[];cal=[];stats=[];weeklies=[];folds=[];modelsdir=OUT/'models';modelsdir.mkdir(exist_ok=True);pred_dir=OUT/'predictions';pred_dir.mkdir(exist_ok=True)
 for year in [2024,2025,2026]:
  start=pd.Timestamp(f'{year}-01-01',tz='UTC');end=min(pd.Timestamp(f'{year+1}-01-01',tz='UTC'),d.index.max()+pd.Timedelta(minutes=5));calstart=pd.Timestamp(f'{year-1}-01-01',tz='UTC');trainend=calstart-pd.Timedelta(hours=24);calend=start-pd.Timedelta(hours=24);testend=end-pd.Timedelta(hours=24)
  train=eligible[(eligible.index<trainend)&(eligible.index.minute%15==0)];valid=eligible[(eligible.index>=calstart)&(eligible.index<calend)];test=eligible[(eligible.index>=start)&(eligible.index<testend)];days=(testend-start).total_seconds()/86400;caldays=(calend-calstart).total_seconds()/86400
  meta=dict(year=year,train_n=len(train),cal_n=len(valid),test_n=len(test),train_last=str(train.index.max()),cal_start=str(calstart),cal_last=str(valid.index.max()),test_start=str(start),test_end=str(testend),test_last=str(test.index.max()),test_days=days)
  assert train.index.max()+pd.Timedelta(hours=24)<calstart and valid.index.max()+pd.Timedelta(hours=24)<start
  folds.append(meta);y=train.target.astype(int).to_numpy();yt=test.target.astype(int).to_numpy();base=np.bincount(y,minlength=3)/len(y);one=np.eye(3)[yt];tt=test.index.asi8//(60*10**9);vt=valid.index.asi8//(60*10**9)
  preds={'BASE_RATE':np.tile(base,(len(test),1))};features=[]
  for name,group in zip(MODELS,['PRICE','CROWD','OI','PROFILE']):
   features+=g[group];print('FIT',year,name,len(train),len(features),flush=True);tm=time.time();model=HistGradientBoostingClassifier(max_iter=120,max_leaf_nodes=15,learning_rate=.05,min_samples_leaf=300,l2_regularization=10,early_stopping=False,random_state=161)
   model.fit(train[features].to_numpy(dtype=np.float32),y);pv=model.predict_proba(valid[features].to_numpy(dtype=np.float32));pt=model.predict_proba(test[features].to_numpy(dtype=np.float32));assert (model.classes_==[0,1,2]).all();preds[name]=pt;joblib.dump(dict(model=model,features=list(features),fold=meta),modelsdir/f'{year}_{name}.joblib',compress=3)
   side=np.where(pt[:,1]>=pt[:,2],1,-1);sc=np.max(pt[:,1:],axis=1);vs=np.max(pv[:,1:],axis=1)
   for rate in RATES:
    th,actual=choose(vt,vs,caldays,rate);ix=emit(tt,sc,th);cal.append(dict(year=year,model=name,requested_per_day=rate,threshold=th,cal_actual_per_day=actual,test_actual_per_day=len(ix)/days))
    q=test.iloc[ix][['close','atr','target','up_mfe','down_mfe','terminal','up_hit_minutes','down_hit_minutes']].copy();q['time']=q.index;q['year']=year;q['model']=name;q['requested_per_day']=rate;q['side']=side[ix];q['score']=sc[ix];q['threshold']=th;signals.append(q.reset_index(drop=True))
   print('DONE',year,name,round(time.time()-tm,1),flush=True)
  # Descriptive causal scheduled momentum reference: no fitted score, comparable requested rate.
  for rate in RATES:
   every=int(1440/rate);ix=np.flatnonzero((tt%every)==0);q=test.iloc[ix][['close','atr','target','up_mfe','down_mfe','terminal','up_hit_minutes','down_hit_minutes']].copy();q['time']=q.index;q['year']=year;q['model']='SCHEDULE_MOMENTUM';q['requested_per_day']=rate;q['side']=np.where(test.iloc[ix].ret_72>=0,1,-1);q['score']=np.nan;q['threshold']=np.nan;signals.append(q.reset_index(drop=True))
  np.savez_compressed(pred_dir/f'{year}.npz',time_ns=test.index.asi8,target=yt,**preds)
  for name,pt in preds.items():
   br=((pt-one)**2).sum(axis=1)
   for sampling,mask in [('ALL_M5',np.ones(len(test),bool)),('DAILY_ANCHOR',tt%1440==0)]:
    yy=yt[mask];pp=pt[mask];stats.append(dict(year=year,model=name,sampling=sampling,n=int(mask.sum()),brier=float(br[mask].mean()),logloss=log_loss(yy,pp,labels=[0,1,2]),up_ap=average_precision_score(yy==1,pp[:,1]),down_ap=average_precision_score(yy==2,pp[:,2]),up_base=float((yy==1).mean()),down_base=float((yy==2).mean())))
   w=pd.DataFrame({'week':test.index.strftime('%G-%V'),'brier':br});w=w.groupby('week').brier.agg(['sum','count']).reset_index();w['year']=year;w['model']=name;weeklies.append(w)
 pd.concat(signals,ignore_index=True).to_csv(OUT/'LAB161_signals.csv',index=False);pd.DataFrame(cal).to_csv(OUT/'LAB161_thresholds.csv',index=False);pd.DataFrame(stats).to_csv(OUT/'LAB161_probability_metrics.csv',index=False);pd.concat(weeklies).to_csv(OUT/'LAB161_weekly_errors.csv',index=False);(OUT/'LAB161_folds.json').write_text(json.dumps(folds,indent=2));(OUT/'LAB161_versions.json').write_text(json.dumps(dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__),indent=2));print('MODELS COMPLETE',flush=True)
if __name__=='__main__':main()
