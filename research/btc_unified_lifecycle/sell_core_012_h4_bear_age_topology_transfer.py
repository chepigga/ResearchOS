#!/usr/bin/env python3
"""SELL_CORE_012 — H4_BEAR_AGE_TOPOLOGY_TRANSFER.
Frozen: canonical H4 ST DOWN; ages 0..80 primary; every H4 clock; SELL next M1 open;
SL 1.5 H1 ATR14, no TP, 48h primary/72h sensitivity, $27.5 cost.
LOYO 2024/25/26: train Gaussian-smoothed EV(age) on 2 years, sigma=4 H4 bars primary,
sigma=8 sensitivity; rank TRAIN ages into fixed-count TOP/MID/BOTTOM terciles; test held-year
TOP-BOTTOM in R and price%, cluster-bootstrap by bearish ST episode. No age subrange promotion.
"""
from pathlib import Path
import numpy as np, pandas as pd
import sell_core_011_b3_h4_sell_aligned as lab

OUT=Path('sell_core_012_out'); OUT.mkdir(exist_ok=True)
YEARS=(2024,2025,2026); AGE_MAX=80; SIGMAS=(4.0,8.0); HOLDS=(48,72); BOOT=20000; SEED=412012

def pf(x):
 z=pd.Series(x).dropna(); gp=z[z>0].sum(); gl=-z[z<0].sum(); return float(gp/gl) if gl>0 else np.nan

def smooth(train,sigma):
 idx=np.arange(AGE_MAX+1); a=train.groupby('st_age').agg(sumR=('R','sum'),sumP=('pct','sum'),N=('R','size')).reindex(idx,fill_value=0)
 n=a.N.to_numpy(float); sr=a.sumR.to_numpy(float); sp=a.sumP.to_numpy(float); pr=[]; pp=[]
 for age in idx:
  k=np.exp(-.5*((idx-age)/sigma)**2); den=(k*n).sum(); pr.append((k*sr).sum()/den); pp.append((k*sp).sum()/den)
 z=pd.DataFrame({'st_age':idx,'pred_R':pr,'pred_pct':pp}).sort_values(['pred_R','st_age']).reset_index(drop=True)
 z['bucket']=np.array(['BOTTOM']*27+['MID']*27+['TOP']*27)
 return z.sort_values('st_age')

def metrics(g):
 return {'N':len(g),'episodes':g.episode_id.nunique(),'EV_R':g.R.mean(),'PF':pf(g.R),'EV_pct':g.pct.mean(),'SL_rate':(g.exit_type=='SL').mean()}

def boot_delta(z,seed,pooled=False):
 z=z[z.bucket.isin(['TOP','BOTTOM'])].copy(); t=z[z.bucket=='TOP']; b=z[z.bucket=='BOTTOM']
 obsR=t.R.mean()-b.R.mean(); obsP=t.pct.mean()-b.pct.mean(); keys=['year','episode_id'] if pooled else ['episode_id']
 arr=[]
 for _,g in z.groupby(keys):
  T=g[g.bucket=='TOP']; B=g[g.bucket=='BOTTOM']; arr.append([T.R.sum(),len(T),B.R.sum(),len(B),T.pct.sum(),B.pct.sum()])
 arr=np.asarray(arr,float); rng=np.random.default_rng(seed); br=[]; bp=[]
 for _ in range(BOOT):
  s=arr[rng.integers(0,len(arr),len(arr))].sum(0)
  if s[1] and s[3]: br.append(s[0]/s[1]-s[2]/s[3]); bp.append(s[4]/s[1]-s[5]/s[3])
 br=np.asarray(br); bp=np.asarray(bp)
 return {'delta_R':obsR,'CI_R_lo':np.quantile(br,.025),'CI_R_hi':np.quantile(br,.975),'P_R_gt0':(br>0).mean(),'delta_pct':obsP,'CI_pct_lo':np.quantile(bp,.025),'CI_pct_hi':np.quantile(bp,.975),'P_pct_gt0':(bp>0).mean()}

def loyo(tr,hh,sigma):
 folds=[]; bm=[]; cr=[]; labs=[]; curves=[]
 for hy in YEARS:
  train=tr[(tr.year!=hy)&tr.st_age.between(0,AGE_MAX)]; held=tr[(tr.year==hy)&tr.st_age.between(0,AGE_MAX)]
  cv=smooth(train,sigma); cv['held_year']=hy; cv['hold_h']=hh; cv['sigma']=sigma; curves.append(cv)
  x=held.merge(cv,on='st_age'); x['held_year']=hy; x['sigma']=sigma; labs.append(x)
  for buck,g in x.groupby('bucket'): bm.append({'held_year':hy,'hold_h':hh,'sigma':sigma,'bucket':buck,**metrics(g)})
  d=boot_delta(x,SEED+hy+hh+int(sigma*10)); folds.append({'held_year':str(hy),'hold_h':hh,'sigma':sigma,**d})
  raw=held.groupby('st_age').agg(obsR=('R','mean'),obsP=('pct','mean')).reset_index().merge(cv,on='st_age')
  cr.append({'held_year':hy,'hold_h':hh,'sigma':sigma,'pearson_R':raw.pred_R.corr(raw.obsR),'spearman_R':raw.pred_R.rank().corr(raw.obsR.rank()),'pearson_pct':raw.pred_pct.corr(raw.obsP),'spearman_pct':raw.pred_pct.rank().corr(raw.obsP.rank())})
 L=pd.concat(labs,ignore_index=True); d=boot_delta(L,SEED+9000+hh+int(sigma*10),True); folds.append({'held_year':'POOLED_OOS','hold_h':hh,'sigma':sigma,**d})
 return pd.DataFrame(folds),pd.DataFrame(bm),pd.DataFrame(cr),L,pd.concat(curves,ignore_index=True)

def main():
 m1=lab.base.load_zip(lab.M1ZIP); m5=lab.base.load_zip(lab.M5ZIP); h1=lab.base.h1_atr_from_m1(m1); clock=lab.build_clock(m5)
 clock.to_csv(OUT/'canonical_h4_clock.csv',index=False)
 rows=clock[(clock.st_dir==-1)&clock.time.dt.year.isin(YEARS)].copy(); rows['base_clock_time']=rows.time; rows['signal_time']=rows.time; rows['view']='PERIODIC_4H'; rows['phase_h']=0
 F=[];B=[];C=[];L=[];CV=[]; raw=[]; broad=[]
 for hh in HOLDS:
  tr=lab.replay(rows,m1,h1,hh); tr.to_csv(OUT/f'all_bear_trades_{hh}h.csv',index=False)
  ar=tr[tr.st_age.between(0,AGE_MAX)].groupby(['year','st_age']).agg(N=('R','size'),EV_R=('R','mean'),EV_pct=('pct','mean')).reset_index(); ar['hold_h']=hh; raw.append(ar)
  bins=pd.cut(tr.st_age,[-1,11,27,50,80,10**9],labels=['0_11','12_27','28_50','51_80','81_PLUS']); tr2=tr.assign(age_bin=bins)
  for (y,b),g in tr2.groupby(['year','age_bin'],observed=True): broad.append({'year':int(y),'hold_h':hh,'bin':str(b),**metrics(g)})
  for s in SIGMAS:
   f,b,c,l,cv=loyo(tr,hh,s); F.append(f);B.append(b);C.append(c);L.append(l);CV.append(cv)
 F=pd.concat(F);B=pd.concat(B);C=pd.concat(C);L=pd.concat(L);CV=pd.concat(CV);RAW=pd.concat(raw);BR=pd.DataFrame(broad)
 F.to_csv(OUT/'loyo_top_bottom.csv',index=False);B.to_csv(OUT/'loyo_bucket_metrics.csv',index=False);C.to_csv(OUT/'loyo_curve_correlations.csv',index=False);L.to_csv(OUT/'loyo_labeled_trades.csv',index=False);CV.to_csv(OUT/'loyo_train_curves.csv',index=False);RAW.to_csv(OUT/'year_age_raw.csv',index=False);BR.to_csv(OUT/'broad_age_bins.csv',index=False)
 p=F[(F.hold_h==48)&(F.sigma==4)]; ps=B[(B.hold_h==48)&(B.sigma==4)]; co=C[(C.hold_h==48)&(C.sigma==4)]; s8=F[(F.hold_h==48)&(F.sigma==8)]
 rep=['# SELL_CORE_012 — H4_BEAR_AGE_TOPOLOGY_TRANSFER','','## Primary LOYO TOP-BOTTOM',p.to_markdown(index=False),'','## Held-year buckets',ps.to_markdown(index=False),'','## Curve correlations',co.to_markdown(index=False),'','## Sigma=8 sensitivity',s8.to_markdown(index=False),'','## 72h',F[F.hold_h==72].to_markdown(index=False),'','## Fixed broad bins — descriptive only',BR[BR.hold_h==48].to_markdown(index=False),'','## Boundary','PASS requires TOP-BOTTOM >0 in R and price% in every held-out year and pooled OOS, with sigma=8 directionally consistent. No age window may be promoted here.']
 (OUT/'REPORT.md').write_text('\n'.join(rep)); print((OUT/'REPORT.md').read_text())
if __name__=='__main__': main()
