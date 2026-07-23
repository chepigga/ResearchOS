from pathlib import Path
import sys,pickle,json,zipfile,multiprocessing as mp
import numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
ROOT=Path('/mnt/data'); OUT=ROOT/'FXArena_GEOxx_Validation_AB_v001_output'; OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT)); import FXArena_GeoSweepLab_v009_sessionAB as geo
W=pickle.load(open(ROOT/'weights_schedule_C2(1).pkl','rb')); FEATURES=W['features']; MONTHS=W['months']
X=np.load(ROOT/'FXArena_GeoSweep_v009_sessionAB/X48.npy',mmap_mode='r').astype(np.float64)
meta=pd.read_pickle(ROOT/'FXArena_GeoSweep_v009_sessionAB/meta.pkl'); o120=np.load(ROOT/'FXArena_GeoSweep_v009_sessionAB/outcomes.npz',mmap_mode='r')
zdir=OUT/'v009b_extracted'; zdir.mkdir(exist_ok=True)
if not (zdir/'outcomes.npz').exists():
 with zipfile.ZipFile(ROOT/'FXArena_TimeoutSweep_v009b_FINAL_results.zip') as z:
  for n in ['X48.npy','meta.pkl','outcomes.npz']:z.extract(n,zdir)
ob=np.load(zdir/'outcomes.npz',mmap_mode='r')
dec=meta.decision_3bar_time_unix.to_numpy(np.int64); month_arr=pd.to_datetime(dec,unit='s').to_period('M').astype(str).to_numpy()

def fit_one(args):
 mo,net,xt,reverse=args
 start=int(pd.Period(mo).start_time.timestamp());end=int((pd.Period(mo)+1).start_time.timestamp())
 tr=(dec>=end) if reverse else (xt<start);te=(month_arr==mo)
 sc=StandardScaler().fit(X[tr]);lr=LogisticRegression(C=.5,max_iter=500,solver='lbfgs',tol=1e-5).fit(sc.transform(X[tr]),(net[tr]>0).astype(np.int8))
 p=lr.predict_proba(sc.transform(X[te]))[:,1]
 return mo,np.where(te)[0],p,lr.coef_[0],float(lr.intercept_[0]),sc.mean_,sc.scale_,int(tr.sum()),int(te.sum())

def train(name,net,xt,reverse=False):
 args=[(mo,net,xt,reverse) for mo in MONTHS]
 ctx=mp.get_context('fork')
 with ctx.Pool(processes=8) as pool: res=pool.map(fit_one,args)
 pred=np.full(len(meta),np.nan);sched=[];log=[]
 for mo,ii,p,co,it,me,sc,ntr,nte in res:
  pred[ii]=p;sched.append((mo,co,it,me,sc));log.append({'month':mo,'train_n':ntr,'test_n':nte})
 if not reverse:
  pickle.dump({'version':'FXArena_GEO_weights_v1.1','geometry':name,'features':FEATURES,'schedule':sched,'model':'LogisticRegression(C=0.5)+StandardScaler','label':'net_R>0','train_boundary':'exit_t < test_month_start','selection':'monthly top-4% then frozen risk v1.00'},open(OUT/f'weights_schedule_{name}.pkl','wb'),protocol=4)
 np.save(OUT/f'pred_{name}.npy',pred);json.dump(log,open(OUT/f'fitlog_{name}.json','w'),indent=2)
 return pred
if __name__=='__main__':
 net120=np.asarray(o120['net'][:,1,2,0],float);xt120=np.asarray(o120['exit_t'][:,1,2,0],np.int64)
 net60=np.asarray(ob['net'][:,1,1,1],float);xt60=np.asarray(ob['exit_t'][:,1,1,1],np.int64)
 train('GEOstar_MICRO30_TP2_TO120',net120,xt120,False)
 train('GEOstarstar_PROV_MICRO30_TP2_TO60',net60,xt60,False)
 train('REV_GEOstarstar_PROV_MICRO30_TP2_TO60',net60,xt60,True)
 print('TRAIN_DONE')
