#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

LAB='XAU_EVENT_ALIGNED_POST_BREAK_PHASE_PATH_RESIDUAL_LAB_016'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
BREAK_SHA='c9cba1459a60ef9c3bb308e751ebae95840f48a24f94754808862a180832ccdb'
PARENT_RUNNER_SHA='09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a'
PARENT_EVENTS_SHA='a6ab0ece5ad2cdfff0b306a4de8d0a8932f6787dfad485441e57f6fe50b68c89'
DISC_END=pd.Timestamp('2024-01-01')
HOLDOUT=pd.Timestamp('2025-07-01')
P_GATE=0.55
PIVOT_REVERSAL=0.15
BOOT_N=4000
SEED=20260824
MAX_T=35
PHASE_SLOTS=5
LEVELS=('MID','HIGH','LOW')
PHASES=('INITIAL_EXPANSION','FIRST_PULLBACK','RECOVERY','POST_RECOVERY','DIGESTION')
INTERNAL_POS=('internal_A','internal_B','internal_C','internal_D')

MIN_CAT=['digestion_state','level']
MIN_NUM=['p_accept','elapsed_min']
COMPACT_CAT=['digestion_state','level','bias_s1','bias_s2','bias_s3']+list(INTERNAL_POS)
COMPACT_NUM=['p_accept','elapsed_min','digestion_block_index','pre_expand_count','x_end','drawdown_end','digestion_change','digestion_range_atr']+[f'{p}_{i}' for i in range(1,6) for p in ('digx','digdd','digret')]
FIXED_RAW_NUM=[]
for t in range(1,MAX_T+1):
    FIXED_RAW_NUM += [f'x_t{t}',f'ret_t{t}',f'dd_t{t}',f'body_t{t}',f'mask_t{t}']
PHASE_NUM=[]
for ph in PHASES:
    PHASE_NUM += [f'{ph}_duration',f'{ph}_exists',f'{ph}_amplitude',f'{ph}_fallback']
    for s in range(1,PHASE_SLOTS+1):
        PHASE_NUM += [f'{ph}_x_s{s}',f'{ph}_ret_s{s}',f'{ph}_dd_s{s}',f'{ph}_body_s{s}']


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load_module(path:Path):
    sp=importlib.util.spec_from_file_location('lab012_parent',path)
    m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def internal_state(block:np.ndarray,prior_peak:float)->str:
    mn=float(block.min()); mx=float(block.max()); end=float(block[-1]); dd=prior_peak-mn; rec=end-mn
    if mn<=0.05: return 'LEVEL_RETEST'
    if (mx-prior_peak)>=0.15 and (end-prior_peak)>=0.05: return 'EXPAND'
    if dd>=0.10 and dd<0.25 and mn>0.10 and rec>=0.05 and end>=prior_peak-0.10: return 'SHALLOW_PULLBACK'
    if dd>=0.25 and mn>0.05: return 'DEEP_PULLBACK'
    if (mx-mn)<=0.20 and mn>0.10: return 'BASE'
    return 'HOLD'


def load_parent_events(path:Path)->pd.DataFrame:
    x=pd.read_csv(path,compression='gzip')
    dtcols=['break_time','digestion_end_time','baseline_entry_time','baseline_exit_time_1p5','baseline_exit_time_2p0','lifecycle_end_time']
    for c in dtcols:
        if c in x: x[c]=pd.to_datetime(x[c],errors='coerce')
    req=['strong_accept','digestion_found','baseline_entry_i','baseline_outcome_1p5','baseline_outcome_2p0','baseline_net_R_1p5','baseline_net_R_2p0','baseline_stress10_R_1p5','causality_violation','break_i','digestion_end_i','digestion_start_i','atr0','p_accept','ordered_path','level','dir','split','level_rank']
    miss=[c for c in req if c not in x.columns]
    if miss: raise ValueError(f'missing parent cols {miss}')
    z=x[(x.strong_accept.astype(bool))&(x.digestion_found.astype(bool))&(x.baseline_entry_i>=0)&(~x.causality_violation.astype(bool))&(x.break_time<HOLDOUT)].copy()
    z=z[z.baseline_outcome_1p5.notna()].copy()
    z['residual_tp15']=(z.baseline_outcome_1p5=='TP').astype(int)
    z['residual_tp20']=(z.baseline_outcome_2p0=='TP').astype(int)
    return z.reset_index(drop=True)


def _first_peak(xs:np.ndarray, absidx:np.ndarray, pre_end_pos:int, x0:float):
    if pre_end_pos < 1:
        return 0,1
    mx=float(xs[1]); mi=1
    for q in range(2,pre_end_pos+1):
        if xs[q] > mx:
            mx=float(xs[q]); mi=q
        if (mx-float(xs[q]))>=PIVOT_REVERSAL and (mx-x0)>=PIVOT_REVERSAL:
            return mi,0
    seg=xs[1:pre_end_pos+1]
    return 1+int(np.argmax(seg)),1


def _first_trough(xs:np.ndarray, p1:int, pre_end_pos:int):
    if p1>=pre_end_pos:
        return p1,1
    mn=float(xs[p1]); mi=p1
    for q in range(p1+1,pre_end_pos+1):
        if xs[q] < mn:
            mn=float(xs[q]); mi=q
        if (float(xs[q])-mn)>=PIVOT_REVERSAL:
            return mi,0
    seg=xs[p1:pre_end_pos+1]
    return p1+int(np.argmin(seg)),1


def _recovery_peak(xs:np.ndarray, p2:int, pre_end_pos:int):
    if p2>=pre_end_pos:
        return p2,1
    mx=float(xs[p2]); mi=p2
    for q in range(p2+1,pre_end_pos+1):
        if xs[q] > mx:
            mx=float(xs[q]); mi=q
        if (mx-float(xs[q]))>=PIVOT_REVERSAL:
            return mi,0
    seg=xs[p2:pre_end_pos+1]
    return p2+int(np.argmax(seg)),1


def phase_landmarks(xs:np.ndarray, bi:int, ds:int, de:int):
    p4=ds-bi; p5=de-bi
    pre_end=p4-1
    p1,fb1=_first_peak(xs,np.arange(bi,de+1),pre_end,float(xs[0]))
    p2,fb2=_first_trough(xs,p1,pre_end)
    p3,fb3=_recovery_peak(xs,p2,pre_end)
    p1=max(0,min(p1,p4)); p2=max(p1,min(p2,p4)); p3=max(p2,min(p3,p4))
    return [0,p1,p2,p3,p4,p5],[fb1,fb2,fb3]


def nearest_relative_positions(start:int,end:int,n:int=PHASE_SLOTS):
    if end<start: end=start
    if end==start: return np.full(n,start,dtype=int)
    vals=np.linspace(start,end,n)
    return np.rint(vals).astype(int)


def add_features(ev:pd.DataFrame,df:pd.DataFrame):
    op=df.open.to_numpy(float); cl=df.close.to_numpy(float)
    lines={lev:df[lev].to_numpy(float) for lev in LEVELS}
    rows=[]; violations=0
    phase_meta=[]
    for r in ev.itertuples(index=False):
        bi=int(r.break_i); de=int(r.digestion_end_i); ds=int(r.digestion_start_i); ent=int(r.baseline_entry_i); d=int(r.dir); a=float(r.atr0); line=lines[str(r.level)]
        elapsed=de-bi
        if bi<1 or elapsed<1 or elapsed>MAX_T or de>=len(df) or ds<bi or ds>de or not np.isfinite(a) or a<=0:
            violations+=1; continue
        all_idx=np.arange(bi,de+1)
        lv=line[all_idx]
        if not np.isfinite(lv).all(): violations+=1; continue
        xs=d*(cl[all_idx]-lv)/a
        prev=np.r_[cl[bi-1],cl[all_idx[:-1]]]
        rets=d*(cl[all_idx]-prev)/a
        dds=np.maximum.accumulate(xs)-xs
        bodies=d*(cl[all_idx]-op[all_idx])/a
        lm,fb=phase_landmarks(xs,bi,ds,de)
        if any(q<0 or q>=len(xs) for q in lm) or lm!=sorted(lm):
            violations+=1; continue
        post_x=xs[1:]; post_ret=rets[1:]; post_dd=dds[1:]; post_body=bodies[1:]
        toks=str(r.ordered_path).split('>')
        while len(toks)<3:toks.append('NOT_OBSERVED')
        intern=['NOT_OBSERVED']*4; pre_expand=0
        for j,start_off in enumerate((16,21,26,31)):
            bend=start_off+4
            if bend>elapsed: break
            block=post_x[start_off-1:bend]; prior=post_x[:start_off-1]
            if len(block)==5 and len(prior):
                st=internal_state(block,float(prior.max())); intern[j]=st
                if bend<elapsed and st=='EXPAND': pre_expand+=1
        dig_abs=np.arange(ds,de+1); digx=d*(cl[dig_abs]-line[dig_abs])/a
        pclose=np.r_[cl[ds-1],cl[ds:de]]; digret=d*(cl[dig_abs]-pclose)/a
        priorx=d*(cl[bi+1:ds]-line[bi+1:ds])/a
        prior_peak=float(priorx.max()) if len(priorx) else float(digx[0])
        digdd=np.maximum.accumulate(np.r_[prior_peak,digx])[1:]-digx
        rec=r._asdict()
        rec.update({
            'bias_s1':toks[0],'bias_s2':toks[1],'bias_s3':toks[2],
            'internal_A':intern[0],'internal_B':intern[1],'internal_C':intern[2],'internal_D':intern[3],
            'elapsed_min':int(elapsed),'digestion_block_index':int((elapsed-15)//5),'pre_expand_count':int(pre_expand),
            'x_end':float(post_x[-1]),'drawdown_end':float(post_dd[-1]),'digestion_change':float(digx[-1]-digx[0]),'digestion_range_atr':float(digx.max()-digx.min()),
            'feature_max_i':de,'feature_max_time':df.at[de,'time'],'feature_causality_violation':bool(de>=ent),
            'p1_i':bi+lm[1],'p2_i':bi+lm[2],'p3_i':bi+lm[3],
            'p1_fallback':int(fb[0]),'p2_fallback':int(fb[1]),'p3_fallback':int(fb[2])
        })
        for i in range(5):
            rec[f'digx_{i+1}']=float(digx[i]); rec[f'digdd_{i+1}']=float(digdd[i]); rec[f'digret_{i+1}']=float(digret[i])
        for t in range(1,MAX_T+1):
            q=t-1; obs=q<len(post_x)
            rec[f'x_t{t}']=float(post_x[q]) if obs else 0.0
            rec[f'ret_t{t}']=float(post_ret[q]) if obs else 0.0
            rec[f'dd_t{t}']=float(post_dd[q]) if obs else 0.0
            rec[f'body_t{t}']=float(post_body[q]) if obs else 0.0
            rec[f'mask_t{t}']=1.0 if obs else 0.0
        phase_bounds=list(zip(lm[:-1],lm[1:]))
        phase_fallback=[fb[0],fb[1],fb[2],fb[2],0]
        for ph,(s0,s1),fallback in zip(PHASES,phase_bounds,phase_fallback):
            pos=nearest_relative_positions(s0,s1)
            rec[f'{ph}_duration']=float(s1-s0)
            rec[f'{ph}_exists']=1.0 if s1>s0 else 0.0
            rec[f'{ph}_amplitude']=float(xs[s1]-xs[s0])
            rec[f'{ph}_fallback']=float(fallback)
            for j,q in enumerate(pos,1):
                rec[f'{ph}_x_s{j}']=float(xs[q])
                rec[f'{ph}_ret_s{j}']=float(rets[q])
                rec[f'{ph}_dd_s{j}']=float(dds[q])
                rec[f'{ph}_body_s{j}']=float(bodies[q])
        rows.append(rec)
        phase_meta.append({
            'break_time':r.break_time,'dir':d,'level':r.level,
            'P1_fallback':fb[0],'P2_fallback':fb[1],'P3_fallback':fb[2],
            **{f'{ph}_duration':float(e-s) for ph,(s,e) in zip(PHASES,phase_bounds)}
        })
    return pd.DataFrame(rows),pd.DataFrame(phase_meta),violations


def make_model(cat,num):
    enc=OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=np.float32)
    pre=ColumnTransformer([('cat',enc,cat),('num','passthrough',num)],remainder='drop',sparse_threshold=0.0)
    clf=HistGradientBoostingClassifier(learning_rate=0.05,max_iter=200,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=1.0,max_bins=64,early_stopping=False,random_state=SEED)
    return Pipeline([('pre',pre),('clf',clf)])


def fit_prob(train,test,cat,num,pcol):
    m=make_model(cat,num); m.fit(train[cat+num],train.residual_tp15.astype(int)); z=test.copy(); z[pcol]=m.predict_proba(z[cat+num])[:,1]; return m,z


def auc(y,p): return float(roc_auc_score(y,p)) if pd.Series(y).nunique()>1 else np.nan

def pred_metrics(z,pcol):
    y=z.residual_tp15.astype(int); p=z[pcol].astype(float)
    return {'n':int(len(z)),'base_rate':float(y.mean()),'auc':auc(y,p),'brier':float(brier_score_loss(y,p)),'logloss':float(log_loss(y,np.clip(p,1e-8,1-1e-8),labels=[0,1]))}


def score_all(train,test):
    mf,f=fit_prob(train,test,MIN_CAT,MIN_NUM+FIXED_RAW_NUM,'p_fixed')
    mp,p=fit_prob(train,test,MIN_CAT,MIN_NUM+PHASE_NUM,'p_phase')
    mi,i=fit_prob(train,test,COMPACT_CAT,COMPACT_NUM+PHASE_NUM,'p_phase_compact')
    z=f.copy(); z['p_phase']=p.p_phase.to_numpy(); z['p_phase_compact']=i.p_phase_compact.to_numpy(); z['phase_armed']=z.p_phase>=P_GATE
    return {'fixed':mf,'phase':mp,'phase_compact':mi},z


def weekly_auc_diff(z):
    q=z.copy(); q['week']=q.break_time.dt.to_period('W-MON').astype(str); rows=[]
    for w,g in q.groupby('week'):
        if len(g)>=20 and g.residual_tp15.nunique()>1:
            rows.append({'week':w,'diff':auc(g.residual_tp15,g.p_phase)-auc(g.residual_tp15,g.p_fixed)})
    return pd.DataFrame(rows)


def boot_mean(vals,seed):
    a=np.asarray(pd.Series(vals).dropna(),float)
    if len(a)<8:return {'n':int(len(a)),'mean':float(a.mean()) if len(a) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(a,size=len(a),replace=True).mean() for _ in range(BOOT_N)])
    return {'n':int(len(a)),'mean':float(a.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}


def boot_selection_gap(z,seed):
    q=z.copy(); q['week']=q.break_time.dt.to_period('W-MON').astype(str); vals=[]
    for _,g in q.groupby('week'):
        a=g[g.phase_armed].residual_tp15; b=g[~g.phase_armed].residual_tp15
        if len(a)>=5 and len(b)>=5: vals.append(float(a.mean()-b.mean()))
    return boot_mean(vals,seed)


def calibration(z):
    q=z.copy(); q['rank']=q.p_phase.rank(method='first',pct=True); q['quintile']=pd.cut(q['rank'],[0,.2,.4,.6,.8,1],labels=['Q1','Q2','Q3','Q4','Q5'],include_lowest=True)
    return q.groupby('quintile',observed=True).agg(n=('residual_tp15','size'),mean_p=('p_phase','mean'),actual_tp15=('residual_tp15','mean'),ev=('baseline_net_R_1p5','mean')).reset_index()


def threshold_table(z):
    rows=[]
    for th in [0.45,0.50,0.55,0.60,0.65]:
        g=z[z.p_phase>=th]
        rows.append({'threshold':th,'n':len(g),'coverage':len(g)/len(z) if len(z) else np.nan,'tp15_rate':g.residual_tp15.mean() if len(g) else np.nan,'ind_ev':g.baseline_net_R_1p5.mean() if len(g) else np.nan})
    return pd.DataFrame(rows)


def subgroup(z,col):
    rows=[]
    for k,g in z.groupby(col):
        ar=g[g.phase_armed]
        rows.append({col:k,'n':len(g),'auc':auc(g.residual_tp15,g.p_phase),'armed_n':len(ar),'armed_tp15':ar.residual_tp15.mean() if len(ar) else np.nan,'armed_ev':ar.baseline_net_R_1p5.mean() if len(ar) else np.nan})
    return pd.DataFrame(rows)


def weekly_strategy_diff(sel,base,seed):
    def wm(x):
        if x is None or x.empty:return pd.Series(dtype=float)
        q=x.copy(); q['week']=pd.to_datetime(q.baseline_entry_time).dt.to_period('W-MON').astype(str); return q.groupby('week').baseline_net_R_1p5.mean()
    a,b=wm(sel),wm(base); idx=a.index.union(b.index); d=a.reindex(idx,fill_value=0)-b.reindex(idx,fill_value=0); return boot_mean(d.to_numpy(float),seed)


def permutation_groups(model,z,base_auc,kind='phase'):
    rng=np.random.default_rng(SEED+99); rows=[]; feats=MIN_CAT+MIN_NUM+PHASE_NUM; base=z[feats].copy(); y=z.residual_tp15.to_numpy(int)
    if kind=='phase':
        groups=[(ph,[c for c in PHASE_NUM if c.startswith(ph+'_')]) for ph in PHASES]
    else:
        groups=[]
        for ch in ('x','ret','dd','body'):
            cols=[c for c in PHASE_NUM if f'_{ch}_s' in c]
            groups.append((ch,cols))
        groups.append(('phase_tempo',[c for c in PHASE_NUM if c.endswith('_duration') or c.endswith('_amplitude') or c.endswith('_exists') or c.endswith('_fallback')]))
    for name,cols in groups:
        q=base.copy(); perm=rng.permutation(len(q)); q.loc[:,cols]=q[cols].to_numpy()[perm]
        p=model.predict_proba(q)[:,1]; rows.append({'group':name,'auc_drop':float(base_auc-auc(y,p))})
    return pd.DataFrame(rows).sort_values('auc_drop',ascending=False)


def phase_diagnostics(meta:pd.DataFrame):
    rows=[]
    bt=pd.to_datetime(meta.break_time)
    for splitname,g in [('DISCOVERY',meta[bt<DISC_END]),('CONFIRMATION',meta[(bt>=DISC_END)&(bt<HOLDOUT)])]:
        r={'split':splitname,'n':len(g)}
        for k in ('P1','P2','P3'):
            r[f'{k}_fallback_rate']=float(g[f'{k}_fallback'].mean()) if len(g) else np.nan
        for ph in PHASES:
            s=g[f'{ph}_duration']
            r[f'{ph}_median_duration']=float(s.median()) if len(s) else np.nan
            r[f'{ph}_p90_duration']=float(s.quantile(.9)) if len(s) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--canonical',type=Path,required=True); ap.add_argument('--break-census',type=Path,required=True); ap.add_argument('--events',type=Path,required=True); ap.add_argument('--parent-runner',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args()
    out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    ch,bh,ph,eh=sha256(a.canonical),sha256(a.break_census),sha256(a.parent_runner),sha256(a.events)
    if ch!=CANONICAL_SHA: raise RuntimeError(f'canonical SHA mismatch {ch}')
    if bh!=BREAK_SHA: raise RuntimeError(f'break SHA mismatch {bh}')
    if ph!=PARENT_RUNNER_SHA: raise RuntimeError(f'parent runner SHA mismatch {ph}')
    if eh!=PARENT_EVENTS_SHA: raise RuntimeError(f'parent events SHA mismatch {eh}')
    parent=load_module(a.parent_runner)
    df=parent.add_atr_vwap(parent.load_prices(a.canonical))
    ev0=load_parent_events(a.events); ev,meta,build_viol=add_features(ev0,df)
    if len(ev)==0: raise RuntimeError('no eligible events')
    ev['break_time']=pd.to_datetime(ev.break_time); ev['baseline_entry_time']=pd.to_datetime(ev.baseline_entry_time); ev['lifecycle_end_time']=pd.to_datetime(ev.lifecycle_end_time)
    for c in set(COMPACT_CAT+MIN_CAT): ev[c]=ev[c].fillna('NOT_OBSERVED').astype(str)
    disc=ev[ev.break_time<DISC_END].copy(); conf=ev[(ev.break_time>=DISC_END)&(ev.break_time<HOLDOUT)].copy()
    models,sc=score_all(disc,conf)
    pre23=disc[disc.break_time<pd.Timestamp('2023-01-01')].copy(); d23=disc[(disc.break_time>=pd.Timestamp('2023-01-01'))&(disc.break_time<DISC_END)].copy(); _,sd23=score_all(pre23,d23)
    metrics_conf={k:pred_metrics(sc,{'fixed':'p_fixed','phase':'p_phase','phase_compact':'p_phase_compact'}[k]) for k in models}
    metrics_23={k:pred_metrics(sd23,{'fixed':'p_fixed','phase':'p_phase','phase_compact':'p_phase_compact'}[k]) for k in models}
    pd.DataFrame([{'split':'DISCOVERY_2023','model':k,**v} for k,v in metrics_23.items()]+[{'split':'CONFIRMATION','model':k,**v} for k,v in metrics_conf.items()]).to_csv(out/'model_summary.csv',index=False)
    sc.to_csv(out/'confirmation_scored.csv.gz',index=False,compression='gzip'); sd23.to_csv(out/'discovery_2023_scored.csv.gz',index=False,compression='gzip')
    calibration(sc).to_csv(out/'calibration.csv',index=False); threshold_table(sc).to_csv(out/'threshold_diagnostics.csv',index=False)
    subgroup(sc.assign(direction=np.where(sc.dir>0,'BUY','SELL')),'direction').to_csv(out/'direction_diagnostics.csv',index=False); subgroup(sc,'level').to_csv(out/'level_diagnostics.csv',index=False); subgroup(sc,'digestion_state').to_csv(out/'digestion_state_diagnostics.csv',index=False)
    phase_diagnostics(meta).to_csv(out/'phase_diagnostics.csv',index=False)
    routed=sc[sc.phase_armed].copy(); rejected=sc[~sc.phase_armed].copy(); base=sc.copy(); r23=sd23[sd23.phase_armed].copy()
    sr=parent.build_serial(routed,'BASELINE',1.5); sb=parent.build_serial(base,'BASELINE',1.5); sr2=parent.build_serial(routed,'BASELINE',2.0)
    stats_r=parent.stats(sr,'BASELINE',1.5); stats_b=parent.stats(sb,'BASELINE',1.5); stats_r2=parent.stats(sr2,'BASELINE',2.0); ind_r=parent.stats(routed,'BASELINE',1.5); ind23=parent.stats(r23,'BASELINE',1.5)
    pd.DataFrame([
        {'split':'CONFIRMATION','router':'PHASE_ROUTED','portfolio':'INDEPENDENT','target':1.5,**ind_r},
        {'split':'CONFIRMATION','router':'PHASE_ROUTED','portfolio':'SERIAL','target':1.5,**stats_r},
        {'split':'CONFIRMATION','router':'BASELINE','portfolio':'SERIAL','target':1.5,**stats_b},
        {'split':'CONFIRMATION','router':'PHASE_ROUTED','portfolio':'SERIAL','target':2.0,**stats_r2},
        {'split':'DISCOVERY_2023','router':'PHASE_ROUTED','portfolio':'INDEPENDENT','target':1.5,**ind23}
    ]).to_csv(out/'summary.csv',index=False)
    auw=weekly_auc_diff(sc); auw.to_csv(out/'weekly_auc_diffs.csv',index=False); aucboot=boot_mean(auw['diff'] if len(auw) else [],SEED)
    selgap=boot_selection_gap(sc,SEED+1)
    sw=sr.copy(); sw['week']=pd.to_datetime(sw.baseline_entry_time).dt.to_period('W-MON').astype(str); evboot=boot_mean(sw.groupby('week').baseline_net_R_1p5.mean().to_numpy(float),SEED+2)
    lift=weekly_strategy_diff(sr,sb,SEED+3)
    base_auc=metrics_conf['phase']['auc']; permutation_groups(models['phase'],sc,base_auc,'phase').to_csv(out/'phase_permutation_importance.csv',index=False); permutation_groups(models['phase'],sc,base_auc,'channel').to_csv(out/'channel_permutation_importance.csv',index=False)
    precision=float(routed.residual_tp15.mean()) if len(routed) else np.nan; rej_rate=float(rejected.residual_tp15.mean()) if len(rejected) else np.nan; recall=float(routed.residual_tp15.sum()/sc.residual_tp15.sum()) if sc.residual_tp15.sum() else np.nan; coverage=len(routed)/len(sc) if len(sc) else np.nan
    phasediff=metrics_conf['phase']['auc']-metrics_conf['fixed']['auc']; integrate_diff=metrics_conf['phase_compact']['auc']-metrics_conf['phase']['auc']
    violations=int(build_viol + ev.feature_causality_violation.astype(bool).sum()+ev.causality_violation.astype(bool).sum()+((ev.feature_max_i>=ev.baseline_entry_i)&(ev.baseline_entry_i>=0)).sum()+((ev[['p1_i','p2_i','p3_i']].max(axis=1)>ev.digestion_end_i)).sum())
    gates={
        'G0_DATA_CAUSALITY':bool(ch==CANONICAL_SHA and bh==BREAK_SHA and ph==PARENT_RUNNER_SHA and eh==PARENT_EVENTS_SHA and violations==0 and (ev.break_time<HOLDOUT).all()),
        'G1_POWER':bool(len(sc)>=1500 and stats_r.get('n',0)>=250 and stats_r.get('trades_per_week',0)>=2),
        'G2_PHASE_RESIDUAL_AUC':bool(metrics_conf['phase']['auc']>=0.60),
        'G3_PHASE_BEATS_FIXED_CLOCK':bool(phasediff>=0.03 and aucboot['ci95'][0] is not None and aucboot['ci95'][0]>0),
        'G4_SELECTION_QUALITY':bool(precision>=0.48 and (precision-rej_rate)>=0.12 and selgap['ci95'][0] is not None and selgap['ci95'][0]>0),
        'G5_CONFIRMATION_EV':bool(stats_r.get('ev',-9)>0 and stats_r.get('pf',0)>1),
        'G6_WEEK_CLUSTER_CI':bool(evboot['ci95'][0] is not None and evboot['ci95'][0]>0),
        'G7_DISCOVERY_TRANSFER':bool(ind23.get('ev',-9)>0 and ind_r.get('ev',-9)>0),
        'G8_2R_SURVIVAL':bool(stats_r2.get('ev',-9)>=0),
        'G9_DIRECTION_BREADTH':bool(stats_r.get('buy_ev',-9)>0 and stats_r.get('sell_ev',-9)>0),
        'G10_PROP_DD_PROXY':bool(stats_r.get('max_dd_R',999)<=20 and stats_r.get('worst_day_R',-999)>-16),
        'G11_COST_STRESS':bool(stats_r.get('stress10_ev',-9)>0),
        'G12_ROUTER_LIFT':bool(stats_r.get('ev',-9)>stats_b.get('ev',9) and lift['ci95'][0] is not None and lift['ci95'][0]>0)
    }
    if not gates['G0_DATA_CAUSALITY']: verdict='INVALID_DATA_CAUSALITY'
    elif all(gates.values()): verdict='EVENT_ALIGNED_RESIDUAL_EXECUTABLE_EDGE'
    elif all(gates[k] for k in ['G2_PHASE_RESIDUAL_AUC','G3_PHASE_BEATS_FIXED_CLOCK','G4_SELECTION_QUALITY','G5_CONFIRMATION_EV','G7_DISCOVERY_TRANSFER','G12_ROUTER_LIFT']): verdict='EVENT_ALIGNMENT_ADDS_RESIDUAL_INFORMATION_BUT_NOT_PROP_READY'
    elif gates['G2_PHASE_RESIDUAL_AUC'] and gates['G3_PHASE_BEATS_FIXED_CLOCK'] and gates['G4_SELECTION_QUALITY'] and not gates['G5_CONFIRMATION_EV']: verdict='EVENT_ALIGNMENT_PREDICTS_BUT_EXECUTION_FAILS'
    elif gates['G2_PHASE_RESIDUAL_AUC'] and gates['G3_PHASE_BEATS_FIXED_CLOCK'] and (not gates['G4_SELECTION_QUALITY'] or not gates['G5_CONFIRMATION_EV']): verdict='EVENT_ALIGNMENT_ADDS_INFORMATION_BUT_NO_SELECTION_EDGE'
    else: verdict='NO_EVENT_ALIGNED_RESIDUAL_EDGE'
    result={
        'status':verdict,'gates':gates,'holdout_opened':False,'primary_confirmation':metrics_conf['phase'],'fixed_confirmation':metrics_conf['fixed'],'phase_compact_confirmation':metrics_conf['phase_compact'],
        'phase_minus_fixed_auc':phasediff,'phase_compact_minus_phase_auc':integrate_diff,'weekly_phase_minus_fixed':aucboot,
        'primary_selection':{'coverage':coverage,'precision':precision,'recall':recall,'rejected_tp_rate':rej_rate,'gap':precision-rej_rate if np.isfinite(precision) and np.isfinite(rej_rate) else None,'weekly_gap':selgap},
        'primary_serial':stats_r,'baseline_serial':stats_b,'primary_2R_serial':stats_r2,'discovery_2023_independent':ind23,'confirmation_independent':ind_r,'weekly_ev':evboot,'weekly_router_lift':lift,'causality_violations':violations
    }
    (out/'verdict.json').write_text(json.dumps(result,indent=2,default=str))
    audit={'canonical_sha':ch,'break_sha':bh,'parent_runner_sha':ph,'parent_events_sha':eh,'eligible_n':int(len(ev)),'discovery_n':int(len(disc)),'confirmation_n':int(len(conf)),'causality_violations':violations,'latest_feature_time':str(ev.feature_max_time.max()),'holdout_opened':False}
    (out/'audit.json').write_text(json.dumps(audit,indent=2))
    pdg=phase_diagnostics(meta)
    lines=[f'# {LAB} — {VERSION} REPORT','',f'**Verdict:** `{verdict}`  ','**Holdout opened:** `false`','',
        '## OOS residual prediction — Confirmation',
        f"- FIXED_CLOCK_RAW AUC **{metrics_conf['fixed']['auc']:.4f}**, Brier **{metrics_conf['fixed']['brier']:.4f}**, N **{metrics_conf['fixed']['n']}**",
        f"- EVENT_ALIGNED_PRICE AUC **{metrics_conf['phase']['auc']:.4f}**, Brier **{metrics_conf['phase']['brier']:.4f}**",
        f"- EVENT_ALIGNED_PLUS_COMPACT AUC **{metrics_conf['phase_compact']['auc']:.4f}**, Brier **{metrics_conf['phase_compact']['brier']:.4f}**",
        f"- EVENT_ALIGNED minus FIXED_CLOCK AUC **{phasediff:+.4f}**, weekly CI **{aucboot['ci95']}**",
        f"- phase+compact increment **{integrate_diff:+.4f}**",'',
        '## Primary p>=0.55 selection',f'- coverage **{coverage*100:.2f}%**',f'- TP1.5 precision **{precision*100:.2f}%**',f'- rejected TP1.5 **{rej_rate*100:.2f}%**',f'- gap **{(precision-rej_rate)*100:+.2f} pp**','',
        '## Executable economics — Confirmation / 1.5R / serial',f"- N **{stats_r.get('n',0)}**, trades/week **{stats_r.get('trades_per_week',np.nan):.2f}**",f"- EV **{stats_r.get('ev',np.nan):+.4f}R**, PF **{stats_r.get('pf',np.nan):.3f}**, TP **{stats_r.get('tp_rate',np.nan)*100:.2f}%**",f"- BUY **{stats_r.get('buy_ev',np.nan):+.4f}R**, SELL **{stats_r.get('sell_ev',np.nan):+.4f}R**",f"- +$0.10 stress EV **{stats_r.get('stress10_ev',np.nan):+.4f}R**",f"- weekly EV CI **{evboot['ci95']}**",'',
        '## Baseline / transfer',f"- all-digestion serial EV **{stats_b.get('ev',np.nan):+.4f}R**, PF **{stats_b.get('pf',np.nan):.3f}**",f"- routed-minus-baseline weekly diff **{lift['mean']:+.4f}R**, CI **{lift['ci95']}**",f"- Discovery-2023 routed independent EV **{ind23.get('ev',np.nan):+.4f}R**",f"- Confirmation routed independent EV **{ind_r.get('ev',np.nan):+.4f}R**",f"- Confirmation 2R serial EV **{stats_r2.get('ev',np.nan):+.4f}R**",'',
        '## Phase construction diagnostics']
    if len(pdg):
        for _,rr in pdg.iterrows():
            lines.append(f"- {rr['split']}: P1/P2/P3 fallback {rr['P1_fallback_rate']*100:.1f}% / {rr['P2_fallback_rate']*100:.1f}% / {rr['P3_fallback_rate']*100:.1f}%; median durations expansion/pullback/recovery/post/digestion = {rr['INITIAL_EXPANSION_median_duration']:.1f}/{rr['FIRST_PULLBACK_median_duration']:.1f}/{rr['RECOVERY_median_duration']:.1f}/{rr['POST_RECOVERY_median_duration']:.1f}/{rr['DIGESTION_median_duration']:.1f} min")
    lines += ['', '## Frozen gates']+[f"- {k}: **{'PASS' if v else 'FAIL'}**" for k,v in gates.items()]+['','No holdout opening, EA authorization or live allocation is authorized.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(result,indent=2,default=str))

if __name__=='__main__': main()
