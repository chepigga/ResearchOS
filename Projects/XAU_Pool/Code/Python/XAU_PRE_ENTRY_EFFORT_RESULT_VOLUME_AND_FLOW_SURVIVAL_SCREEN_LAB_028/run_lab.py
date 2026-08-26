#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss

LAB='XAU_PRE_ENTRY_EFFORT_RESULT_VOLUME_AND_FLOW_SURVIVAL_SCREEN_LAB_028'; VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
PARENT_SHA='09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a'
HOLDOUT=pd.Timestamp('2025-07-01'); ADVERSE_DEPTH=.10; RISK_ATR=.50; SEED=20260826; BOOT=2000
FAM_ORDER=['PRICE_ONLY','PLUS_ACTIVITY','PLUS_EFFORT','PLUS_SPREAD','FULL']

def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def loadmod(p):
 sp=importlib.util.spec_from_file_location('parent',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

def rebuild(parent,input_path,break_path):
 df=parent.add_atr_vwap(parent.load_prices(input_path)); br=parent.load_breaks(break_path); ev=parent.score_bias(parent.build_bias_events(br,df)); strong=ev[ev.strong_accept].copy(); s=parent.build_setups(strong,df)
 s=parent.simulate_branch(s,df,'BASELINE',1.5)
 base=s[(s.strong_accept.astype(bool))&(s.digestion_found.astype(bool))&(s.baseline_entry_i>=0)&(~s.causality_violation.astype(bool))&(s.break_time<HOLDOUT)].copy()
 return df,parent.dedupe_serial_universe(base),br

def attach_market_fields(df,input_path):
 extra=pd.read_csv(input_path,sep=';',usecols=['time','tick_volume','spread','spread_min','spread_max','spread_mean','spread_close','real_volume'])
 extra['time']=pd.to_datetime(extra.time,format='%Y.%m.%d %H:%M',errors='coerce'); extra=extra[extra.time<HOLDOUT].sort_values('time').drop_duplicates('time',keep='last')
 cols=['spread','spread_min','spread_max','spread_mean','spread_close','real_volume']
 x=df.merge(extra[['time']+cols],on='time',how='left',validate='one_to_one')
 return x

def label_survival(base,df):
 times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64); cl=df.close.to_numpy(float); bl=df.low.to_numpy(float); ah=df.ask_high.to_numpy(float); al=df.ask_low.to_numpy(float); bh=df.high.to_numpy(float); lines={k:df[k].to_numpy(float) for k in ('MID','HIGH','LOW')}
 y=[]; reason=[]; vio=0
 for r in base.itertuples(index=False):
  ei=int(r.baseline_entry_i); d=int(r.dir); e=float(r.baseline_entry); a=float(r.atr0); sl=e-d*RISK_ATR*a; tp=e+d*1.5*RISK_ATR*a; ok=True; rs='SURVIVE'
  for step in range(5):
   j=ei+step
   if j>=len(df) or times[j]!=times[ei]+step: ok=False; rs='CLOCK_FAIL'; vio+=1; break
   slh=(bl[j]<=sl) if d>0 else (ah[j]>=sl); tph=(bh[j]>=tp) if d>0 else (al[j]<=tp)
   adv=(al[j]<=e-ADVERSE_DEPTH*a) if d>0 else (bh[j]>=e+ADVERSE_DEPTH*a)
   line=lines[str(r.level)][j]; degr=(d*(cl[j]-line)/a)<=0.05
   if slh: ok=False; rs='SL'; break
   if adv: ok=False; rs='ADVERSE'; break
   if degr: ok=False; rs='DEGRADE'; break
   if tph: ok=False; rs='TP_EARLY'; break
  y.append(int(ok)); reason.append(rs)
 z=base.copy(); z['survive5']=y; z['fail_reason']=reason
 return z,vio

def safe_div(a,b,eps=1e-9): return a/(np.abs(b)+eps)
def feature_frame(base,df):
 close=df.close.to_numpy(float); hi=df.high.to_numpy(float); lo=df.low.to_numpy(float); tv=df.tick_volume.to_numpy(float); sm=df.spread_mean.to_numpy(float); sx=df.spread_max.to_numpy(float); sc=df.spread_close.to_numpy(float)
 rows=[]
 for r in base.itertuples(index=False):
  ei=int(r.baseline_entry_i); d=int(r.dir); a=float(r.atr0); row={'p_accept':float(r.p_accept),'dir':d,'level_rank':float(r.level_rank),'atr0':a}
  for w in (3,5,15,30):
   i0=ei-w; i1=ei
   c=close[i0:i1]; h=hi[i0:i1]; l=lo[i0:i1]; v=tv[i0:i1]; smean=sm[i0:i1]; smax=sx[i0:i1]; sclose=sc[i0:i1]
   disp=d*(c[-1]-c[0])/a if len(c)>=2 and a>0 else np.nan
   path=np.abs(np.diff(c)).sum()/a if len(c)>=2 and a>0 else np.nan
   eff=disp/(path+1e-9) if np.isfinite(path) else np.nan
   rng=(np.nanmax(h)-np.nanmin(l))/a if len(c) and a>0 else np.nan
   cloc=(c[-1]-np.nanmin(l))/(np.nanmax(h)-np.nanmin(l)+1e-9) if len(c) else np.nan
   vs=np.nansum(v); vm=np.nanmean(v); vx=np.nanmax(v)
   row.update({f'disp_{w}':disp,f'path_{w}':path,f'eff_{w}':eff,f'range_{w}':rng,f'cloc_{w}':cloc,
               f'tv_sum_{w}':vs,f'tv_mean_{w}':vm,f'tv_max_{w}':vx,
               f'effort_disp_{w}':vs/(abs(disp)+.02),f'disp_per_tv_{w}':disp/(vs+1.0),f'range_per_tv_{w}':rng/(vs+1.0),f'effort_eff_{w}':vs/(abs(eff)+.05),
               f'spread_mean_{w}':np.nanmean(smean),f'spread_max_{w}':np.nanmax(smax),f'spread_close_{w}':np.nanmean(sclose),f'tv_x_spread_{w}':vm*np.nanmean(smean)})
  row['tv_ratio_3_15']=safe_div(row['tv_mean_3'],row['tv_mean_15']); row['tv_ratio_5_30']=safe_div(row['tv_mean_5'],row['tv_mean_30'])
  row['spread_ratio_3_15']=safe_div(row['spread_mean_3'],row['spread_mean_15']); row['spread_ratio_5_30']=safe_div(row['spread_mean_5'],row['spread_mean_30'])
  row['move_spent_break_entry']=d*(close[ei-1]-close[int(r.break_i)])/a if ei>0 and a>0 else np.nan
  row['break_to_entry_min']=float(ei-int(r.break_i))
  rows.append(row)
 return pd.DataFrame(rows,index=base.index)

def families(cols):
 price=[c for c in cols if c in ['p_accept','dir','level_rank','atr0','move_spent_break_entry','break_to_entry_min'] or c.startswith(('disp_','path_','eff_','range_','cloc_'))]
 activity=[c for c in cols if c.startswith(('tv_sum_','tv_mean_','tv_max_','tv_ratio_'))]
 effort=[c for c in cols if c.startswith(('effort_','disp_per_tv_','range_per_tv_'))]
 spread=[c for c in cols if c.startswith(('spread_mean_','spread_max_','spread_close_','spread_ratio_','tv_x_spread_'))]
 return {'PRICE_ONLY':price,'PLUS_ACTIVITY':price+activity,'PLUS_EFFORT':price+activity+effort,'PLUS_SPREAD':price+activity+effort+spread,'FULL':price+activity+effort+spread}

def fit_predict(train,test,X,feat):
 med=X.loc[train.index,feat].median(); Xtr=X.loc[train.index,feat].fillna(med); Xte=X.loc[test.index,feat].fillna(med)
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=15,min_samples_leaf=40,l2_regularization=1.0,random_state=SEED)
 m.fit(Xtr,train.survive5); ptr=m.predict_proba(Xtr)[:,1]; pte=m.predict_proba(Xte)[:,1]
 thr=float(np.quantile(ptr,.70)); return m,pte,thr

def eval_family(conf,p,thr):
 y=conf.survive5.to_numpy(int); sel=p>=thr; base=y.mean(); cov=sel.mean(); prec=y[sel].mean() if sel.any() else np.nan; ret=y[sel].sum()/max(1,y.sum()); fail=(~sel & (y==0)).sum()/max(1,(y==0).sum())
 out={'n':len(y),'survivors':int(y.sum()),'base_rate':float(base),'auc':float(roc_auc_score(y,p)),'brier':float(brier_score_loss(y,p)),'threshold':thr,'coverage':float(cov),'precision':float(prec),'precision_lift':float(prec/base) if base>0 else np.nan,'survivor_retention':float(ret),'failure_rejection':float(fail)}
 for dval,name in [(1,'BUY'),(-1,'SELL')]:
  q=(conf.dir.to_numpy()==dval); ys=y[q]; ss=sel[q]
  out[f'{name.lower()}_base']=float(ys.mean()) if len(ys) else np.nan; out[f'{name.lower()}_precision']=float(ys[ss].mean()) if ss.any() else np.nan
 return out,sel

def weekly_auc_diff(conf,pfull,pbase):
 z=conf[['baseline_entry_time','survive5']].copy(); z['pf']=pfull;z['pb']=pbase;z['week']=pd.to_datetime(z.baseline_entry_time).dt.to_period('W-MON').astype(str)
 weeks=z.week.unique(); rng=np.random.default_rng(SEED+1); vals=[]
 for _ in range(BOOT):
  ws=rng.choice(weeks,len(weeks),replace=True); zz=pd.concat([z[z.week==w] for w in ws],ignore_index=True); y=zz.survive5.values
  if len(np.unique(y))<2: continue
  vals.append(roc_auc_score(y,zz.pf)-roc_auc_score(y,zz.pb))
 return {'mean':float(np.mean(vals)),'ci95':[float(np.quantile(vals,.025)),float(np.quantile(vals,.975))],'n_boot':len(vals)}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--break-census',type=Path,required=True);ap.add_argument('--parent-runner',type=Path,required=True);ap.add_argument('--outdir',type=Path,required=True);a=ap.parse_args();o=a.outdir;o.mkdir(parents=True,exist_ok=True)
 if sha256(a.input)!=CANONICAL_SHA: raise RuntimeError('canonical sha mismatch')
 if sha256(a.parent_runner)!=PARENT_SHA: raise RuntimeError('parent sha mismatch')
 parent=loadmod(a.parent_runner); df,base,br=rebuild(parent,a.input,a.break_census); df=attach_market_fields(df,a.input)
 rv_nonzero=int((df.real_volume.fillna(0)!=0).sum()); rv_total=int(df.real_volume.notna().sum())
 lab,vio=label_survival(base,df); X=feature_frame(lab,df); fam=families(X.columns)
 disc=lab[lab.split=='DISCOVERY'].copy(); conf=lab[lab.split=='CONFIRMATION'].copy()
 results=[]; preds={}; sels={}
 for name in FAM_ORDER:
  m,p,thr=fit_predict(disc,conf,X,fam[name]); met,sel=eval_family(conf,p,thr); met['family']=name;met['n_features']=len(fam[name]); results.append(met);preds[name]=p;sels[name]=sel
 res=pd.DataFrame(results);res.to_csv(o/'model_summary.csv',index=False)
 wd=weekly_auc_diff(conf,preds['FULL'],preds['PRICE_ONLY']); (o/'weekly_auc_diff.json').write_text(json.dumps(wd,indent=2))
 cf=conf.copy(); cf['p_full']=preds['FULL'];cf['selected']=sels['FULL'];cf['starter_control_R']=.25*cf.baseline_net_R_1p5
 econ=[]
 for label,g in cf.groupby('selected'):
  econ.append({'selected':bool(label),'n':len(g),'survival_rate':float(g.survive5.mean()),'starter_control_ev':float(g.starter_control_R.mean()),'baseline_full_ev':float(g.baseline_net_R_1p5.mean()),'baseline_tp_rate':float((g.baseline_outcome_1p5=='TP').mean()),'buy_n':int((g.dir==1).sum()),'sell_n':int((g.dir==-1).sum())})
 pd.DataFrame(econ).to_csv(o/'router_economics.csv',index=False)
 cf[['break_time','baseline_entry_time','dir','level','p_accept','survive5','fail_reason','p_full','selected','baseline_net_R_1p5','baseline_outcome_1p5']].to_csv(o/'scored_events.csv.gz',index=False,compression='gzip')
 full=res[res.family=='FULL'].iloc[0]; price=res[res.family=='PRICE_ONLY'].iloc[0]; se=cf[cf.selected].starter_control_R.mean() if cf.selected.any() else np.nan; ue=cf[~cf.selected].starter_control_R.mean() if (~cf.selected).any() else np.nan
 gates={'G0_DATA_CAUSALITY':bool(vio==0 and rv_nonzero==0),'G1_POWER':bool(len(conf)>=300 and conf.survive5.sum()>=50),'G2_RANK_INFORMATION':bool(full.auc>=.60),'G3_ACTIVITY_ADDS':bool((full.auc-price.auc)>0 and wd['ci95'][0]>0),'G4_OPERATIONAL_PRECISION':bool(full.precision>=1.5*full.base_rate),'G5_USEFUL_RETENTION':bool(full.survivor_retention>=.50 and full.coverage<=.40),'G6_FAILURE_REJECTION':bool(full.failure_rejection>=.65),'G7_BREADTH':bool(full.buy_precision>full.buy_base and full.sell_precision>full.sell_base),'G8_STARTER_ECONOMICS':bool(np.isfinite(se) and se>0 and se>ue)}
 if all(gates.values()): status='PRE_ENTRY_SURVIVAL_ROUTER_EDGE'
 elif gates['G2_RANK_INFORMATION'] and gates['G4_OPERATIONAL_PRECISION']: status='PRE_ENTRY_SURVIVAL_SIGNAL_BUT_NOT_ECONOMIC'
 else: status='NO_PRE_ENTRY_SURVIVAL_SIGNAL'
 verdict={'status':status,'gates':gates,'full':full.to_dict(),'price_only':price.to_dict(),'weekly_auc_diff':wd,'selected_starter_ev':float(se),'unselected_starter_ev':float(ue),'real_volume_nonzero_rows':rv_nonzero,'real_volume_rows':rv_total,'causality_violations':vio,'holdout_opened':False}
 (o/'verdict.json').write_text(json.dumps(verdict,indent=2,default=str))
 audit={'canonical_sha':sha256(a.input),'parent_sha':sha256(a.parent_runner),'break_census_sha':sha256(a.break_census),'base_rows':len(lab),'discovery_n':len(disc),'confirmation_n':len(conf),'confirmation_survivors':int(conf.survive5.sum()),'real_volume_nonzero_rows':rv_nonzero,'causality_violations':vio,'holdout_opened':False,'max_price_time':str(df.time.max())}
 (o/'audit.json').write_text(json.dumps(audit,indent=2))
 rep=f'''# {LAB} — {VERSION} REPORT\n\n**Verdict:** `{status}`  \n**Holdout opened:** `false`\n\n## Data reality\n- canonical real_volume nonzero rows: **{rv_nonzero}** / {rv_total}; therefore v001 uses tick activity, not exchange volume.\n- Confirmation N **{len(conf)}**, survivors **{int(conf.survive5.sum())}**, base survival **{conf.survive5.mean():.2%}**\n\n## Confirmation model family\n{res.to_markdown(index=False)}\n\n## Primary FULL router\n- AUC **{full.auc:.4f}** vs PRICE_ONLY **{price.auc:.4f}**; delta **{full.auc-price.auc:+.4f}**, weekly CI **{wd['ci95']}**\n- fixed Discovery top-30% threshold -> Confirmation coverage **{full.coverage:.2%}**\n- selected survival precision **{full.precision:.2%}** vs base **{full.base_rate:.2%}**, lift **{full.precision_lift:.2f}x**\n- survivor retention **{full.survivor_retention:.2%}**, failure rejection **{full.failure_rejection:.2%}**\n- BUY precision/base **{full.buy_precision:.2%}/{full.buy_base:.2%}**; SELL **{full.sell_precision:.2%}/{full.sell_base:.2%}**\n\n## Starter economics diagnostic\n- selected 0.25x frozen baseline EV **{se:+.4f}R**\n- unselected **{ue:+.4f}R**\n\n## Frozen gates\n'''+ '\n'.join(f'- {k}: **{"PASS" if v else "FAIL"}**' for k,v in gates.items())+'\n\nNo Confirmation threshold tuning, no external GC data, no holdout opening, no EA/live authorization.\n'
 (o/'REPORT.md').write_text(rep)
 print(json.dumps(verdict,indent=2,default=str))
if __name__=='__main__': main()
