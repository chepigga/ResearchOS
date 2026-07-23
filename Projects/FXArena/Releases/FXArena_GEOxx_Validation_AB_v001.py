from pathlib import Path
import sys, pickle, json, math, hashlib, zipfile
import numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from scipy.special import expit

ROOT=Path('/mnt/data')
OUT=ROOT/'FXArena_GEOxx_Validation_AB_v001_output'; OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT))
import FXArena_GeoSweepLab_v009_sessionAB as geo

# frozen inputs
W=pickle.load(open(ROOT/'weights_schedule_C2(1).pkl','rb'))
X=np.load(ROOT/'FXArena_GeoSweep_v009_sessionAB/X48.npy',mmap_mode='r').astype(np.float64)
meta=pd.read_pickle(ROOT/'FXArena_GeoSweep_v009_sessionAB/meta.pkl')
o120=np.load(ROOT/'FXArena_GeoSweep_v009_sessionAB/outcomes.npz',mmap_mode='r')

# extract v009b prep arrays (same universe) for TO60
zdir=OUT/'v009b_extracted'; zdir.mkdir(exist_ok=True)
with zipfile.ZipFile(ROOT/'FXArena_TimeoutSweep_v009b_FINAL_results.zip') as z:
    for n in ['X48.npy','meta.pkl','outcomes.npz']:
        z.extract(n,zdir)
Xb=np.load(zdir/'X48.npy',mmap_mode='r').astype(np.float64)
metab=pd.read_pickle(zdir/'meta.pkl')
ob=np.load(zdir/'outcomes.npz',mmap_mode='r')
assert len(meta)==len(metab) and np.array_equal(meta.episode_id.to_numpy(),metab.episode_id.to_numpy())
assert np.allclose(X,Xb,atol=0,rtol=0)

FEATURES=W['features']; MONTHS=W.get('months',[s[0] for s in W.get('schedule',[])])

def maxdd(x):
    x=np.asarray(x,float); eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0.,eq]); return float(np.max(pk[1:]-eq))

def metrics(tr):
    tr=tr.sort_values(['entry_t','episode_id'],kind='mergesort').copy()
    tr['month']=pd.to_datetime(tr.entry_t,unit='s').dt.to_period('M'); tr['year']=pd.to_datetime(tr.entry_t,unit='s').dt.year
    mo=tr.groupby('month').net.sum(); yr=tr.groupby('year').net.agg(['sum','mean','size'])
    pos=tr.loc[tr.net>0,'net'].sum(); neg=-tr.loc[tr.net<0,'net'].sum()
    return dict(N=int(len(tr)),total_R=float(tr.net.sum()),EV=float(tr.net.mean()),PF=float(pos/neg),WR=float((tr.net>0).mean()),MaxDD_gross_R=maxdd(tr.gross),MaxDD_net_R=maxdd(tr.net),negative_months=int((mo<0).sum()),worst_month_R=float(mo.min()),all_years_positive=bool((yr['sum']>0).all()),monthly={str(k):float(v) for k,v in mo.items()},yearly={str(k):{'total_R':float(v['sum']),'EV':float(v['mean']),'N':int(v['size'])} for k,v in yr.iterrows()})

def apply_risk(pred,gross,net,xt,hold):
    return geo.apply_risk(meta,pred,gross,net,xt,hold,top_frac=.04)

# Part 0a: canonical C2 pinned from canonical weights/p and canonical C2 geometry micro_raw TP1 TO120
pfile=pd.read_csv(ROOT/'C2_p_by_episode.csv',sep=';')
pmap=pfile.set_index('episode_id').p
pred_c2=meta.episode_id.map(pmap).to_numpy(float)
gross_c2=np.asarray(o120['gross'][:,0,0,0],float)
net_c2=np.asarray(o120['net'][:,0,0,0],float)
xt_c2=np.asarray(o120['exit_t'][:,0,0,0],np.int64)
hold_c2=np.asarray(o120['hold'][:,0,0,0],float)
c2=apply_risk(pred_c2,gross_c2,net_c2,xt_c2,hold_c2)
c2.to_pickle(OUT/'c2_trades_loop_PINNED.pkl')
c2.to_csv(OUT/'c2_trades_loop_PINNED.csv.gz',index=False,compression='gzip')
c2m=metrics(c2)

# exact retraining and schedule export
def fit_geometry(name, net, gross, xt, hold, reverse=False):
    dec=meta.decision_3bar_time_unix.to_numpy(np.int64)
    month_arr=pd.to_datetime(dec,unit='s').to_period('M').astype(str)
    pred=np.full(len(meta),np.nan); schedule=[]; fitlog=[]
    for mo in MONTHS:
        start=int(pd.Period(mo).start_time.timestamp()); end=int((pd.Period(mo)+1).start_time.timestamp())
        tr=(dec>=end) if reverse else (xt<start)
        te=(month_arr==mo)
        if tr.sum()<1000 or te.sum()==0:
            fitlog.append({'month':mo,'train_n':int(tr.sum()),'test_n':int(te.sum()),'status':'SKIP'}); continue
        sc=StandardScaler().fit(X[tr])
        lr=LogisticRegression(C=.5,max_iter=500,solver='lbfgs',tol=1e-5).fit(sc.transform(X[tr]),(net[tr]>0).astype(np.int8))
        pred[te]=lr.predict_proba(sc.transform(X[te]))[:,1]
        schedule.append((mo,lr.coef_[0].copy(),float(lr.intercept_[0]),sc.mean_.copy(),sc.scale_.copy()))
        fitlog.append({'month':mo,'train_n':int(tr.sum()),'test_n':int(te.sum()),'positive_rate':float((net[tr]>0).mean())})
    trd=apply_risk(pred,gross,net,xt,hold)
    if not reverse:
        artifact={'version':'FXArena_GEO_weights_v1.1','geometry':name,'features':FEATURES,'schedule':schedule,'model':'LogisticRegression(C=0.5)+StandardScaler','label':'net_R>0','train_boundary':'exit_t < test_month_start','selection':'monthly top-4% then frozen risk v1.00'}
        pickle.dump(artifact,open(OUT/f'weights_schedule_{name}.pkl','wb'),protocol=4)
        trd.to_csv(OUT/f'trades_{name}_PINNED.csv.gz',index=False,compression='gzip')
    return pred,trd,metrics(trd),fitlog

# GEO* TP2/120 from v009 arrays: stop micro30 index1, tp2 index2, to120 index0
net120=np.asarray(o120['net'][:,1,2,0],float); gross120=np.asarray(o120['gross'][:,1,2,0],float); xt120=np.asarray(o120['exit_t'][:,1,2,0],np.int64); hold120=np.asarray(o120['hold'][:,1,2,0],float)
# GEO** TP2/60 from v009b arrays: stop micro30 index1, tp2 index1, to60 index1 (TOS 45,60,90,120)
net60=np.asarray(ob['net'][:,1,1,1],float); gross60=np.asarray(ob['gross'][:,1,1,1],float); xt60=np.asarray(ob['exit_t'][:,1,1,1],np.int64); hold60=np.asarray(ob['hold'][:,1,1,1],float)

p120,t120,m120,log120=fit_geometry('GEOstar_MICRO30_TP2_TO120',net120,gross120,xt120,hold120)
p60,t60,m60,log60=fit_geometry('GEOstarstar_PROV_MICRO30_TP2_TO60',net60,gross60,xt60,hold60)
_,r60,mr60,_=fit_geometry('REV_GEOstarstar_PROV_MICRO30_TP2_TO60',net60,gross60,xt60,hold60,reverse=True)
rev_deg=1-mr60['total_R']/m60['total_R']

# GS6 permutation 200 using fixed p60 and full risk layer
rng=np.random.default_rng(20260723); month_arr=pd.to_datetime(meta.decision_3bar_time_unix,unit='s').dt.to_period('M').astype(str).to_numpy(); perm=[]
for b in range(200):
    pp=p60.copy()
    for mo in np.unique(month_arr):
        ii=np.where((month_arr==mo)&np.isfinite(pp))[0]
        if len(ii): pp[ii]=rng.permutation(pp[ii])
    q=apply_risk(pp,gross60,net60,xt60,hold60)
    perm.append({'iter':b,'N':len(q),'EV':float(q.net.mean()),'total_R':float(q.net.sum()),'MaxDD_gross_R':maxdd(q.gross)})
pd.DataFrame(perm).to_csv(OUT/'GS6_permutation200_GEOstarstar_PROV.csv',index=False)
pa=pd.DataFrame(perm)
gs6={'real_EV':m60['EV'],'null_median_EV':float(pa.EV.median()),'null_p95_EV':float(pa.EV.quantile(.95)),'null_max_EV':float(pa.EV.max()),'p_empirical':float((1+(pa.EV>=m60['EV']).sum())/201)}

# GS7 monthly-block bootstrap. Resample 42 monthly blocks with replacement; preserve within-month order.
def month_blocks(tr):
    x=tr.sort_values(['entry_t','episode_id']).copy(); x['month']=pd.to_datetime(x.entry_t,unit='s').dt.to_period('M').astype(str); return {m:g.copy() for m,g in x.groupby('month',sort=True)}
b120=month_blocks(t120); b60=month_blocks(t60); common=sorted(set(b120)&set(b60)); rng=np.random.default_rng(2026072307); boots=[]
for i in range(5000):
    draw=rng.choice(common,size=len(common),replace=True)
    a=np.concatenate([b120[m].gross.to_numpy(float) for m in draw]); ar=np.concatenate([b120[m].net.to_numpy(float) for m in draw])
    b=np.concatenate([b60[m].gross.to_numpy(float) for m in draw]); br=np.concatenate([b60[m].net.to_numpy(float) for m in draw])
    boots.append((i,ar.sum(),br.sum(),maxdd(a),maxdd(b)))
bt=pd.DataFrame(boots,columns=['iter','total_GEOstar','total_GEOstarstar','DD_GEOstar','DD_GEOstarstar']); bt.to_csv(OUT/'GS7_block_bootstrap_5000.csv',index=False)
gs7={'n_boot':5000,'P_DD_geo2_gt_geo1_plus_0_5':float((bt.DD_GEOstarstar>bt.DD_GEOstar+.5).mean()),'P_total_geo2_gt_geo1':float((bt.total_GEOstarstar>bt.total_GEOstar).mean()),'pass_i':bool((bt.DD_GEOstarstar>bt.DD_GEOstar+.5).mean()<.05),'pass_ii':bool((bt.total_GEOstarstar>bt.total_GEOstar).mean()>=.95)}

# Pillar B / NM on same pinned instance
limit=m120['MaxDD_gross_R']+.5
nm1=(m60['MaxDD_gross_R']-limit)<=.01*limit
nm2=(m60['total_R']-m120['total_R'])/m120['total_R']>=.03
pillarB={'baseline':m120,'candidate':m60,'DD_limit':limit,'DD_excess':m60['MaxDD_gross_R']-limit,'NM1_pass':bool(nm1),'NM2_pass':bool(nm2),'total_advantage_pct':float((m60['total_R']-m120['total_R'])/m120['total_R'])}

report={'part0':{'c2_pinned':c2m,'geo_weights_exported':['weights_schedule_GEOstar_MICRO30_TP2_TO120.pkl','weights_schedule_GEOstarstar_PROV_MICRO30_TP2_TO60.pkl'],'trade_fixtures_exported':['c2_trades_loop_PINNED.pkl','trades_GEOstar_MICRO30_TP2_TO120_PINNED.csv.gz','trades_GEOstarstar_PROV_MICRO30_TP2_TO60_PINNED.csv.gz']},'pillarA':{'GS5_reverse':mr60,'GS5_degradation':rev_deg,'GS5_pass':bool(rev_deg<=.20),'GS6':gs6,'GS6_pass':bool(gs6['p_empirical']<=.05),'GS7':gs7,'GS7_pass':bool(gs7['pass_i'] and gs7['pass_ii'])},'pillarB':pillarB}
report['verdict_AB']='PASS' if report['pillarA']['GS5_pass'] and report['pillarA']['GS6_pass'] and report['pillarA']['GS7_pass'] and nm1 and nm2 else 'FAIL'
json.dump(report,open(OUT/'GEOxx_Validation_AB_report.json','w'),indent=2)
pd.DataFrame([{'object':'C2_PINNED',**{k:v for k,v in c2m.items() if k not in ['monthly','yearly']}},{'object':'GEO* TP2/120',**{k:v for k,v in m120.items() if k not in ['monthly','yearly']}},{'object':'GEO**-PROV TP2/60',**{k:v for k,v in m60.items() if k not in ['monthly','yearly']}},{'object':'GEO** reverse',**{k:v for k,v in mr60.items() if k not in ['monthly','yearly']}}]).to_csv(OUT/'validation_summary.csv',index=False)
print(json.dumps(report,indent=2))
