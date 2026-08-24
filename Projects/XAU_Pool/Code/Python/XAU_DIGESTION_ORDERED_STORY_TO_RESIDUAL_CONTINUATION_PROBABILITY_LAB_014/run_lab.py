#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

LAB='XAU_DIGESTION_ORDERED_STORY_TO_RESIDUAL_CONTINUATION_PROBABILITY_LAB_014'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
PARENT_EVENTS_SHA='6a1ab06285b84003e284fb683058806629e0760089c681f6327d29d6348b7fd8'
DISC_END=pd.Timestamp('2024-01-01'); HOLDOUT=pd.Timestamp('2025-07-01')
P_GATE=0.55; BOOT_N=4000; SEED=20260824

SNAP_CAT=['digestion_state','level','bias_s3']
SNAP_NUM=['p_accept','elapsed_min','digestion_block_index','pre_expand_count','x_end','drawdown_end','digestion_change','digestion_range_atr']
ORD_CAT=SNAP_CAT+['bias_s1','bias_s2','internal_A','internal_B','internal_C','internal_D']
ORD_NUM=SNAP_NUM+[f'{p}_{i}' for i in range(1,6) for p in ('x','dd','ret')]
ACT_NUM=ORD_NUM+[f'{p}_{i}' for i in range(1,6) for p in ('volr','range')]

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def load_parent_module(path:Path):
    sp=importlib.util.spec_from_file_location('lab012_parent',path); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
def load_events(path:Path):
    x=pd.read_csv(path,compression='gzip')
    for c in ['break_time','digestion_end_time','baseline_entry_time','baseline_exit_time_1p5','baseline_exit_time_2p0','lifecycle_end_time','feature_max_time']:
        if c in x: x[c]=pd.to_datetime(x[c],errors='coerce')
    for c in ORD_CAT:
        if c in x: x[c]=x[c].fillna('NOT_OBSERVED').astype(str)
    req=['strong_accept','digestion_found','baseline_entry_i','baseline_outcome_1p5','baseline_outcome_2p0','feature_causality_violation','causality_violation']
    miss=[c for c in req if c not in x]
    if miss: raise ValueError(miss)
    z=x[(x.strong_accept.astype(bool))&(x.digestion_found.astype(bool))&(x.baseline_entry_i>=0)&(~x.feature_causality_violation.astype(bool))&(~x.causality_violation.astype(bool))&(x.break_time<HOLDOUT)].copy()
    z=z[z.baseline_outcome_1p5.notna()].copy(); z['residual_tp15']=(z.baseline_outcome_1p5=='TP').astype(int); z['residual_tp20']=(z.baseline_outcome_2p0=='TP').astype(int)
    return z.reset_index(drop=True)
def make_model(cat,num):
    pre=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore'),cat),('num',StandardScaler(),num)],remainder='drop')
    return Pipeline([('pre',pre),('clf',LogisticRegression(C=1.0,penalty='l2',solver='liblinear',max_iter=2000))])
def fit_predict(train,test,cat,num,name):
    m=make_model(cat,num); m.fit(train[cat+num],train.residual_tp15); out=test.copy(); out[name]=m.predict_proba(out[cat+num])[:,1]; return m,out
def auc(y,p): return float(roc_auc_score(y,p)) if pd.Series(y).nunique()>1 else np.nan
def pred_metrics(x,pcol):
    y=x.residual_tp15.to_numpy(int); p=x[pcol].to_numpy(float); return {'n':int(len(x)),'base_rate':float(y.mean()),'auc':auc(y,p),'brier':float(brier_score_loss(y,p)),'logloss':float(log_loss(y,np.clip(p,1e-8,1-1e-8),labels=[0,1]))}
def model_all(train,test):
    ms,s=fit_predict(train,test,SNAP_CAT,SNAP_NUM,'p_snapshot'); mo,o=fit_predict(train,test,ORD_CAT,ORD_NUM,'p_residual'); ma,a=fit_predict(train,test,ORD_CAT,ACT_NUM,'p_activity')
    z=s.copy(); z['p_residual']=o.p_residual.to_numpy(); z['p_activity']=a.p_activity.to_numpy(); z['residual_armed']=z.p_residual>=P_GATE; return ms,mo,ma,z
def coef_table(model):
    pre=model.named_steps['pre']; names=list(pre.get_feature_names_out()); co=model.named_steps['clf'].coef_[0]; return pd.DataFrame({'feature':names,'coef':co}).assign(abscoef=lambda d:d.coef.abs()).sort_values('abscoef',ascending=False)
def weekly_auc_diff(x):
    z=x.copy(); z['week']=z.break_time.dt.to_period('W-MON').astype(str); rows=[]
    for w,g in z.groupby('week'):
        if len(g)>=20 and g.residual_tp15.nunique()>1: rows.append({'week':w,'diff':auc(g.residual_tp15,g.p_residual)-auc(g.residual_tp15,g.p_snapshot)})
    return pd.DataFrame(rows)
def boot_mean(a,seed):
    a=np.asarray(pd.Series(a).dropna(),float)
    if len(a)<8:return {'n':int(len(a)),'mean':float(a.mean()) if len(a) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(a,size=len(a),replace=True).mean() for _ in range(BOOT_N)]); return {'n':int(len(a)),'mean':float(a.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}
def boot_selection_gap(x,seed):
    z=x.copy(); z['week']=z.break_time.dt.to_period('W-MON').astype(str); vals=[]
    for _,g in z.groupby('week'):
        a=g[g.residual_armed].residual_tp15; b=g[~g.residual_armed].residual_tp15
        if len(a)>=5 and len(b)>=5: vals.append(a.mean()-b.mean())
    return boot_mean(vals,seed)
def calibration(x):
    z=x.copy(); z['rank']=z.p_residual.rank(method='first',pct=True); z['quintile']=pd.cut(z['rank'],[0,.2,.4,.6,.8,1],labels=['Q1','Q2','Q3','Q4','Q5'],include_lowest=True)
    return z.groupby('quintile',observed=True).agg(n=('residual_tp15','size'),mean_p=('p_residual','mean'),actual_tp15=('residual_tp15','mean'),ev=('baseline_net_R_1p5','mean')).reset_index()
def thresholds(x):
    rows=[]
    for th in [0.45,0.50,0.55,0.60,0.65]:
        g=x[x.p_residual>=th]; rows.append({'threshold':th,'n':len(g),'coverage':len(g)/len(x) if len(x) else np.nan,'tp15_rate':g.residual_tp15.mean() if len(g) else np.nan,'ind_ev':g.baseline_net_R_1p5.mean() if len(g) else np.nan})
    return pd.DataFrame(rows)
def subgroup(x,col):
    return pd.DataFrame([{col:k,'n':len(g),'auc':auc(g.residual_tp15,g.p_residual),'armed_n':int(g.residual_armed.sum()),'armed_tp15':g.loc[g.residual_armed,'residual_tp15'].mean(),'armed_ev':g.loc[g.residual_armed,'baseline_net_R_1p5'].mean()} for k,g in x.groupby(col)])
def weekly_strategy_diff(sel,base,seed):
    def wm(x):
        if x is None or x.empty:return pd.Series(dtype=float)
        z=x.copy(); z['week']=pd.to_datetime(z.baseline_entry_time).dt.to_period('W-MON').astype(str); return z.groupby('week').baseline_net_R_1p5.mean()
    a,b=wm(sel),wm(base); idx=a.index.union(b.index); d=a.reindex(idx,fill_value=0)-b.reindex(idx,fill_value=0); return boot_mean(d.to_numpy(float),seed)
def serial_stats(x,parent,target=1.5): return parent.stats(x,'BASELINE',target)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--canonical',type=Path,required=True); ap.add_argument('--events',type=Path,required=True); ap.add_argument('--parent-runner',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    ch=sha256(a.canonical); eh=sha256(a.events)
    if ch!=CANONICAL_SHA: raise RuntimeError(f'canonical SHA {ch}')
    if eh!=PARENT_EVENTS_SHA: raise RuntimeError(f'parent events SHA {eh}')
    parent=load_parent_module(a.parent_runner); ev=load_events(a.events)
    if (ev.break_time>=HOLDOUT).any(): raise RuntimeError('holdout opened')
    disc=ev[ev.break_time<DISC_END].copy(); conf=ev[(ev.break_time>=DISC_END)&(ev.break_time<HOLDOUT)].copy(); ms,mo,ma,sc=model_all(disc,conf)
    dtrain=disc[disc.break_time<pd.Timestamp('2023-01-01')].copy(); d23=disc[(disc.break_time>=pd.Timestamp('2023-01-01'))&(disc.break_time<DISC_END)].copy(); _,_,_,sd23=model_all(dtrain,d23)
    pm={'snapshot':pred_metrics(sc,'p_snapshot'),'ordered':pred_metrics(sc,'p_residual'),'activity':pred_metrics(sc,'p_activity')}; pm23={'snapshot':pred_metrics(sd23,'p_snapshot'),'ordered':pred_metrics(sd23,'p_residual'),'activity':pred_metrics(sd23,'p_activity')}
    sc.to_csv(out/'confirmation_scored.csv.gz',index=False,compression='gzip'); sd23.to_csv(out/'discovery_2023_scored.csv.gz',index=False,compression='gzip')
    pd.DataFrame([{'split':'DISCOVERY_2023','model':k,**v} for k,v in pm23.items()]+[{'split':'CONFIRMATION','model':k,**v} for k,v in pm.items()]).to_csv(out/'model_summary.csv',index=False)
    calibration(sc).to_csv(out/'calibration.csv',index=False); thresholds(sc).to_csv(out/'threshold_diagnostics.csv',index=False); coef_table(mo).to_csv(out/'coefficients.csv',index=False)
    subgroup(sc.assign(direction=np.where(sc.dir>0,'BUY','SELL')),'direction').to_csv(out/'direction_diagnostics.csv',index=False); subgroup(sc,'level').to_csv(out/'level_diagnostics.csv',index=False); subgroup(sc,'digestion_state').to_csv(out/'digestion_state_diagnostics.csv',index=False)
    pd.DataFrame({'p_reaccel':sc.p_ordered,'p_residual':sc.p_residual,'tp15':sc.residual_tp15,'net_R':sc.baseline_net_R_1p5}).to_csv(out/'reaccel_vs_residual.csv',index=False)
    routed=sc[sc.residual_armed].copy(); rejected=sc[~sc.residual_armed].copy(); base=sc.copy(); r23=sd23[sd23.residual_armed].copy(); sr=parent.build_serial(routed,'BASELINE',1.5); sb=parent.build_serial(base,'BASELINE',1.5); sr2=parent.build_serial(routed,'BASELINE',2.0)
    stats_r=serial_stats(sr,parent,1.5); stats_b=serial_stats(sb,parent,1.5); stats_r2=serial_stats(sr2,parent,2.0); ind_r=parent.stats(routed,'BASELINE',1.5); ind23=parent.stats(r23,'BASELINE',1.5)
    pd.DataFrame([{'split':'CONFIRMATION','router':'ROUTED','portfolio':'INDEPENDENT','target':1.5,**ind_r},{'split':'CONFIRMATION','router':'ROUTED','portfolio':'SERIAL','target':1.5,**stats_r},{'split':'CONFIRMATION','router':'BASELINE','portfolio':'SERIAL','target':1.5,**stats_b},{'split':'CONFIRMATION','router':'ROUTED','portfolio':'SERIAL','target':2.0,**stats_r2},{'split':'DISCOVERY_2023','router':'ROUTED','portfolio':'INDEPENDENT','target':1.5,**ind23}]).to_csv(out/'summary.csv',index=False)
    wk=sr.copy(); wk['week']=pd.to_datetime(wk.baseline_entry_time).dt.to_period('W-MON').astype(str); wb=boot_mean(wk.groupby('week').baseline_net_R_1p5.mean().to_numpy(float),SEED); lift=weekly_strategy_diff(sr,sb,SEED+1); ad=weekly_auc_diff(sc); aucboot=boot_mean(ad['diff'] if len(ad) else [],SEED+2); selgap=boot_selection_gap(sc,SEED+3); ad.to_csv(out/'weekly_auc_diffs.csv',index=False)
    sel_rate=float(routed.residual_tp15.mean()) if len(routed) else np.nan; rej_rate=float(rejected.residual_tp15.mean()) if len(rejected) else np.nan; precision=sel_rate; recall=float(routed.residual_tp15.sum()/sc.residual_tp15.sum()) if sc.residual_tp15.sum() else np.nan; coverage=len(routed)/len(sc) if len(sc) else np.nan; seqdiff=pm['ordered']['auc']-pm['snapshot']['auc']
    violations=int(ev.feature_causality_violation.astype(bool).sum()+ev.causality_violation.astype(bool).sum()+((ev.feature_max_i>=ev.baseline_entry_i)&(ev.baseline_entry_i>=0)).sum())
    gates={'G0_DATA_CAUSALITY':bool(ch==CANONICAL_SHA and eh==PARENT_EVENTS_SHA and violations==0 and (ev.break_time<HOLDOUT).all()),'G1_POWER':bool(len(sc)>=1500 and stats_r.get('n',0)>=250 and stats_r.get('trades_per_week',0)>=2),'G2_RESIDUAL_AUC':bool(pm['ordered']['auc']>=0.65),'G3_SEQUENCE_INCREMENTAL':bool(seqdiff>=0.01 and aucboot['ci95'][0] is not None and aucboot['ci95'][0]>0),'G4_SELECTION_QUALITY':bool(precision>=0.50 and (precision-rej_rate)>=0.15 and selgap['ci95'][0] is not None and selgap['ci95'][0]>0),'G5_CONFIRMATION_EV':bool(stats_r.get('ev',-9)>0 and stats_r.get('pf',0)>1),'G6_WEEK_CLUSTER_CI':bool(wb['ci95'][0] is not None and wb['ci95'][0]>0),'G7_DISCOVERY_TRANSFER':bool(ind23.get('ev',-9)>0 and ind_r.get('ev',-9)>0),'G8_2R_SURVIVAL':bool(stats_r2.get('ev',-9)>=0),'G9_DIRECTION_BREADTH':bool(stats_r.get('buy_ev',-9)>0 and stats_r.get('sell_ev',-9)>0),'G10_PROP_DD_PROXY':bool(stats_r.get('max_dd_R',999)<=20 and stats_r.get('worst_day_R',-999)>-16),'G11_COST_STRESS':bool(stats_r.get('stress10_ev',-9)>0),'G12_ROUTER_LIFT':bool(stats_r.get('ev',-9)>stats_b.get('ev',9) and lift['ci95'][0] is not None and lift['ci95'][0]>0)}
    if not gates['G0_DATA_CAUSALITY']: verdict='INVALID_DATA_CAUSALITY'
    elif all(gates.values()): verdict='RESIDUAL_CONTINUATION_EXECUTABLE_EDGE'
    elif all(gates[k] for k in ['G2_RESIDUAL_AUC','G3_SEQUENCE_INCREMENTAL','G4_SELECTION_QUALITY','G5_CONFIRMATION_EV','G6_WEEK_CLUSTER_CI','G7_DISCOVERY_TRANSFER','G12_ROUTER_LIFT']): verdict='RESIDUAL_EDGE_NOT_PROP_READY'
    elif gates['G2_RESIDUAL_AUC'] and gates['G4_SELECTION_QUALITY'] and gates['G5_CONFIRMATION_EV'] and (not gates['G6_WEEK_CLUSTER_CI'] or not gates['G7_DISCOVERY_TRANSFER'] or not gates['G12_ROUTER_LIFT']): verdict='RESIDUAL_PROBABILITY_SELECTS_EDGE_BUT_NOT_ROBUST'
    elif gates['G2_RESIDUAL_AUC'] and gates['G3_SEQUENCE_INCREMENTAL'] and gates['G4_SELECTION_QUALITY'] and not gates['G5_CONFIRMATION_EV']: verdict='SEQUENCE_PREDICTS_RESIDUAL_BUT_ECONOMICS_FAIL'
    elif gates['G2_RESIDUAL_AUC'] and gates['G4_SELECTION_QUALITY'] and gates['G5_CONFIRMATION_EV'] and not gates['G3_SEQUENCE_INCREMENTAL']: verdict='RESIDUAL_EDGE_WITHOUT_SEQUENCE_INCREMENT'
    else: verdict='NO_RESIDUAL_CONTINUATION_EDGE'
    audit={'canonical_sha':ch,'parent_events_sha':eh,'eligible_n':len(ev),'discovery_n':len(disc),'confirmation_n':len(conf),'holdout_opened':False,'causality_violations':violations,'last_break_time':str(ev.break_time.max())}; result={'status':verdict,'gates':gates,'primary_confirmation':stats_r,'baseline_confirmation':stats_b,'confirmation_2R':stats_r2,'predictive_confirmation':pm,'predictive_discovery_2023':pm23,'selection':{'threshold':P_GATE,'coverage':coverage,'precision':precision,'recall':recall,'rejected_tp15_rate':rej_rate,'gap_pp':100*(precision-rej_rate)},'weekly_ev_bootstrap':wb,'router_lift_bootstrap':lift,'auc_increment_bootstrap':aucboot,'selection_gap_bootstrap':selgap,'holdout_opened':False}
    (out/'audit.json').write_text(json.dumps(audit,indent=2,default=str)); (out/'verdict.json').write_text(json.dumps(result,indent=2,default=str))
    report=[f'# {LAB} — {VERSION} REPORT','',f'**Verdict:** `{verdict}`  ',f'**Holdout opened:** `false`','', '## Residual probability — Confirmation',f"- N: **{len(sc)}**, TP1.5 base rate: **{sc.residual_tp15.mean():.3f}**",f"- LOCATION_SNAPSHOT AUC: **{pm['snapshot']['auc']:.4f}**",f"- ORDERED_STORY AUC: **{pm['ordered']['auc']:.4f}**",f"- ORDERED_STORY_PLUS_ACTIVITY AUC: **{pm['activity']['auc']:.4f}**",f"- ordered - snapshot: **{seqdiff:+.4f}**, weekly CI **{aucboot['ci95']}**",f"- p>=0.55 coverage: **{coverage:.2%}**, TP precision: **{precision:.2%}**, rejected TP rate: **{rej_rate:.2%}**, gap **{100*(precision-rej_rate):+.2f} pp**",'', '## Executable economics — Confirmation / 1.5R / serial',f"- N: **{stats_r.get('n')}**, trades/week **{stats_r.get('trades_per_week'):.2f}**",f"- EV **{stats_r.get('ev'):.4f}R**, PF **{stats_r.get('pf'):.3f}**, TP **{stats_r.get('tp_rate'):.2%}**",f"- BUY **{stats_r.get('buy_ev'):.4f}R**, SELL **{stats_r.get('sell_ev'):.4f}R**",f"- max DD **{stats_r.get('max_dd_R'):.2f}R**, worst day **{stats_r.get('worst_day_R'):.2f}R**",f"- +$0.10 stress EV **{stats_r.get('stress10_ev'):.4f}R**",f"- weekly mean-R CI **{wb['ci95']}**",'', '## Baseline / lift',f"- all-digestion serial EV **{stats_b.get('ev'):.4f}R**, PF **{stats_b.get('pf'):.3f}**",f"- routed-minus-baseline weekly diff **{lift['mean']:.4f}R**, CI **{lift['ci95']}**",f"- Discovery-2023 routed independent EV **{ind23.get('ev'):.4f}R**",f"- Confirmation routed independent EV **{ind_r.get('ev'):.4f}R**",f"- Confirmation routed 2R EV **{stats_r2.get('ev'):.4f}R**, PF **{stats_r2.get('pf'):.3f}**",'', '## Frozen gates']+[f"- {k}: **{'PASS' if v else 'FAIL'}**" for k,v in gates.items()]+['','No holdout opening, EA authorization, or live allocation is authorized by LAB014.']; (out/'REPORT.md').write_text('\n'.join(report)); print(json.dumps({'status':verdict,'outdir':str(out),'primary_ev':stats_r.get('ev'),'primary_pf':stats_r.get('pf'),'auc':pm['ordered']['auc'],'coverage':coverage,'precision':precision,'holdout_opened':False},indent=2))
if __name__=='__main__': main()
