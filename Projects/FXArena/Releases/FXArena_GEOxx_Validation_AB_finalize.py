from pathlib import Path
import sys,json,zipfile,pickle,hashlib,multiprocessing as mp,shutil,os
import numpy as np,pandas as pd
ROOT=Path('/mnt/data'); OUT=ROOT/'FXArena_GEOxx_Validation_AB_v001_output'; REL=ROOT/'FXArena_Release_v1.1_COMPLETE'
sys.path.insert(0,str(ROOT)); import FXArena_GeoSweepLab_v009_sessionAB as geo
meta=pd.read_pickle(ROOT/'FXArena_GeoSweep_v009_sessionAB/meta.pkl'); o120=np.load(ROOT/'FXArena_GeoSweep_v009_sessionAB/outcomes.npz',mmap_mode='r')
ob=np.load(OUT/'v009b_extracted/outcomes.npz',mmap_mode='r')
p120=np.load(OUT/'pred_GEOstar_MICRO30_TP2_TO120.npy');p60=np.load(OUT/'pred_GEOstarstar_PROV_MICRO30_TP2_TO60.npy');prev=np.load(OUT/'pred_REV_GEOstarstar_PROV_MICRO30_TP2_TO60.npy')
net120=np.asarray(o120['net'][:,1,2,0],float);gross120=np.asarray(o120['gross'][:,1,2,0],float);xt120=np.asarray(o120['exit_t'][:,1,2,0],np.int64);hold120=np.asarray(o120['hold'][:,1,2,0],float)
net60=np.asarray(ob['net'][:,1,1,1],float);gross60=np.asarray(ob['gross'][:,1,1,1],float);xt60=np.asarray(ob['exit_t'][:,1,1,1],np.int64);hold60=np.asarray(ob['hold'][:,1,1,1],float)

def maxdd(x):
 x=np.asarray(x,float);e=np.cumsum(x);p=np.maximum.accumulate(np.r_[0.,e]);return float(np.max(p[1:]-e))
def apply(pred,gross,net,xt,hold):return geo.apply_risk(meta,pred,gross,net,xt,hold,.04)
def metrics(t):
 t=t.sort_values(['entry_t','episode_id'],kind='mergesort').copy();t['month']=pd.to_datetime(t.entry_t,unit='s').dt.to_period('M');t['year']=pd.to_datetime(t.entry_t,unit='s').dt.year
 mo=t.groupby('month').net.sum();yr=t.groupby('year').net.agg(['sum','mean','size']);pos=t.loc[t.net>0,'net'].sum();neg=-t.loc[t.net<0,'net'].sum()
 return {'N':int(len(t)),'total_R':float(t.net.sum()),'EV':float(t.net.mean()),'PF':float(pos/neg),'WR':float((t.net>0).mean()),'MaxDD_gross_R':maxdd(t.gross),'MaxDD_net_R':maxdd(t.net),'negative_months':int((mo<0).sum()),'worst_month_R':float(mo.min()),'all_years_positive':bool((yr['sum']>0).all()),'monthly':{str(k):float(v) for k,v in mo.items()},'yearly':{str(k):{'total_R':float(v['sum']),'EV':float(v['mean']),'N':int(v['size'])} for k,v in yr.iterrows()}}
t120=apply(p120,gross120,net120,xt120,hold120);t60=apply(p60,gross60,net60,xt60,hold60);tr=apply(prev,gross60,net60,xt60,hold60)
t120.to_csv(OUT/'trades_GEOstar_MICRO30_TP2_TO120_PINNED.csv.gz',index=False,compression='gzip');t60.to_csv(OUT/'trades_GEOstarstar_PROV_MICRO30_TP2_TO60_PINNED.csv.gz',index=False,compression='gzip');tr.to_csv(OUT/'trades_REV_GEOstarstar_PROV.csv.gz',index=False,compression='gzip')
m120,m60,mr=metrics(t120),metrics(t60),metrics(tr)
month_arr=pd.to_datetime(meta.decision_3bar_time_unix,unit='s').dt.to_period('M').astype(str).to_numpy(); months=np.unique(month_arr)
# multiprocessing permutation
G={}
def init_perm():
 global G;G={'meta':meta,'p':p60,'gross':gross60,'net':net60,'xt':xt60,'hold':hold60,'months':month_arr,'uniq':months}
def one_perm(i):
 rng=np.random.default_rng(20260723+i);pp=G['p'].copy()
 for mo in G['uniq']:
  ii=np.where((G['months']==mo)&np.isfinite(pp))[0]
  if len(ii):pp[ii]=rng.permutation(pp[ii])
 q=geo.apply_risk(G['meta'],pp,G['gross'],G['net'],G['xt'],G['hold'],.04)
 return i,len(q),float(q.net.mean()),float(q.net.sum()),maxdd(q.gross)
ctx=mp.get_context('fork')
with ctx.Pool(8,initializer=init_perm) as pool: vals=pool.map(one_perm,range(200))
pa=pd.DataFrame(vals,columns=['iter','N','EV','total_R','MaxDD_gross_R']);pa.to_csv(OUT/'GS6_permutation200_GEOstarstar_PROV.csv',index=False)
gs6={'real_EV':m60['EV'],'null_median_EV':float(pa.EV.median()),'null_p95_EV':float(pa.EV.quantile(.95)),'null_max_EV':float(pa.EV.max()),'p_empirical':float((1+(pa.EV>=m60['EV']).sum())/201)}
# GS7 paired monthly-block bootstrap

def blocks(t):
 x=t.sort_values(['entry_t','episode_id']).copy();x['month']=pd.to_datetime(x.entry_t,unit='s').dt.to_period('M').astype(str);return {m:g for m,g in x.groupby('month',sort=True)}
a,b=blocks(t120),blocks(t60);common=sorted(set(a)&set(b));rng=np.random.default_rng(2026072307);rows=[]
for i in range(5000):
 draw=rng.choice(common,len(common),replace=True);ag=np.concatenate([a[m].gross.to_numpy() for m in draw]);an=np.concatenate([a[m].net.to_numpy() for m in draw]);bg=np.concatenate([b[m].gross.to_numpy() for m in draw]);bn=np.concatenate([b[m].net.to_numpy() for m in draw]);rows.append((i,an.sum(),bn.sum(),maxdd(ag),maxdd(bg)))
bt=pd.DataFrame(rows,columns=['iter','total_GEOstar','total_GEOstarstar','DD_GEOstar','DD_GEOstarstar']);bt.to_csv(OUT/'GS7_block_bootstrap_5000.csv',index=False)
pdd=float((bt.DD_GEOstarstar>bt.DD_GEOstar+.5).mean());ptot=float((bt.total_GEOstarstar>bt.total_GEOstar).mean());gs7={'n_boot':5000,'P_DD_geo2_gt_geo1_plus_0_5':pdd,'P_total_geo2_gt_geo1':ptot,'pass_i':pdd<.05,'pass_ii':ptot>=.95}
revdeg=1-mr['total_R']/m60['total_R'];limit=m120['MaxDD_gross_R']+.5;excess=m60['MaxDD_gross_R']-limit;adv=(m60['total_R']-m120['total_R'])/m120['total_R'];nm1=excess<=.01*limit;nm2=adv>=.03
c2=pickle.load(open(OUT/'c2_trades_loop_PINNED.pkl','rb'));mc2=metrics(c2)
rep={'part0':{'C2_PINNED':mc2,'GEOstar':m120,'GEOstarstar_PROV':m60},'pillarA':{'GS5_reverse':mr,'GS5_degradation':revdeg,'GS5_pass':revdeg<=.20,'GS6':gs6,'GS6_pass':gs6['p_empirical']<=.05,'GS7':gs7,'GS7_pass':gs7['pass_i'] and gs7['pass_ii']},'pillarB':{'NM1_pass':nm1,'NM2_pass':nm2,'DD_limit':limit,'DD_excess':excess,'total_advantage_pct':adv}}
rep['verdict_AB']='PASS' if rep['pillarA']['GS5_pass'] and rep['pillarA']['GS6_pass'] and rep['pillarA']['GS7_pass'] and nm1 and nm2 else 'FAIL'
json.dump(rep,open(OUT/'GEOxx_Validation_AB_report.json','w'),indent=2)
# md report
md=f'''# FXArena GEO**-PROV Validation A+B\n\n## Verdict\n\n**{rep['verdict_AB']}**\n\n## Part 0 pinned fixtures\n\n- C2: N={mc2['N']}, EV={mc2['EV']:.6f}, total={mc2['total_R']:.2f}R, DD={mc2['MaxDD_gross_R']:.3f}R\n- GEO*: N={m120['N']}, EV={m120['EV']:.6f}, total={m120['total_R']:.2f}R, DD={m120['MaxDD_gross_R']:.3f}R\n- GEO**-PROV: N={m60['N']}, EV={m60['EV']:.6f}, total={m60['total_R']:.2f}R, DD={m60['MaxDD_gross_R']:.3f}R\n\n## Pillar A\n\n- GS5 reverse degradation: {revdeg:.4%} — {'PASS' if revdeg<=.20 else 'FAIL'}\n- GS6 permutation p: {gs6['p_empirical']:.6f}, null max EV {gs6['null_max_EV']:.6f} — {'PASS' if gs6['p_empirical']<=.05 else 'FAIL'}\n- GS7 P(DD2 > DD1+0.5): {pdd:.6f}; P(total2 > total1): {ptot:.6f} — {'PASS' if gs7['pass_i'] and gs7['pass_ii'] else 'FAIL'}\n\n## Pillar B\n\n- NM1: DD excess {excess:.6f}R vs limit {limit:.6f}R — {'PASS' if nm1 else 'FAIL'}\n- NM2: total advantage {adv:.4%} — {'PASS' if nm2 else 'FAIL'}\n\nPillar C remains the August forward A/B test.\n'''
open(OUT/'FXArena_GEOxx_Validation_AB_report.md','w').write(md)
# release assembly
if REL.exists():shutil.rmtree(REL)
REL.mkdir()
# core C2
for src,dst in [(ROOT/'weights_schedule_C2(1).pkl','weights_schedule_C2.pkl'),(ROOT/'FXArena_ContPrimary_v121.mq5','FXArena_ContPrimary_v121.mq5'),(ROOT/'C2_SPEC_FROZEN.md','C2_SPEC_FROZEN.md'),(ROOT/'C2_p_by_episode.csv','C2_p_by_episode.csv'),(ROOT/'C2_frozen_livewindow(1).csv','C2_frozen_livewindow.csv'),(OUT/'c2_trades_loop_PINNED.pkl','c2_trades_loop_PINNED.pkl'),(OUT/'c2_trades_loop_PINNED.csv.gz','c2_trades_loop_PINNED.csv.gz')]:shutil.copy2(src,REL/dst)
# validation outputs
for f in OUT.iterdir():
 if f.is_file() and f.suffix not in ['.npy'] and f.name not in ['c2_trades_loop_PINNED.pkl','c2_trades_loop_PINNED.csv.gz']:shutil.copy2(f,REL/f.name)
# frozen reports/results and TB
for zpath in [ROOT/'FXArena_GeoSweep_v009_results.zip',ROOT/'FXArena_TimeoutSweep_v009b_FINAL_results.zip',ROOT/'FXArena_TrendBirthExecution_v002_results.zip']:
 shutil.copy2(zpath,REL/zpath.name)
for f in [ROOT/'FXArena_RESULTS_REGISTRY_v2.md',ROOT/'FXArena_Backlog-2026-07-23_v8.md',ROOT/'FXArena_Protocol_NearMiss_GEOxx_2026-07-23.md',ROOT/'FXArena_TimeoutSweep_TZ_v009b_2026-07-22.md',ROOT/'wf_toolkit.py',ROOT/'FXArena_GEOxx_Validation_AB_v001.py',ROOT/'FXArena_GEOxx_Validation_AB_parallel.py',ROOT/'FXArena_GEOxx_Validation_AB_finalize.py']:
 shutil.copy2(f,REL/f.name)
# manifest
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as x:
  for c in iter(lambda:x.read(1<<20),b''):h.update(c)
 return h.hexdigest()
rows=[]
for f in sorted(REL.iterdir()):
 if f.is_file():rows.append({'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f)})
pd.DataFrame(rows).to_csv(REL/'MANIFEST_SHA256.csv',index=False)
open(REL/'README.md','w').write('# FXArena Release v1.1\n\nFrozen C2, GEO*, GEO**-PROV fixtures and Validation A+B outputs. Pillar C remains pending August forward A/B.\n')
zipout=ROOT/'FXArena_Release_v1.1_COMPLETE.zip'
if zipout.exists():zipout.unlink()
shutil.make_archive(str(zipout.with_suffix('')),'zip',REL)
print(json.dumps(rep,indent=2));print('ZIP',zipout,zipout.stat().st_size)
