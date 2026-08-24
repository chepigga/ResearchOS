#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, pickle
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.metrics import log_loss

LAB='XAU_TEMPORAL_DISCOVERY_ONLY_PROBABILITY_CALIBRATION_X_PAYOFF_MANAGEMENT_LAB_022'
VERSION='v001'
DF_SHA='ec05163508f6f69c9688e5e50e1f418f6ca64aba42f17cf8d6504775df147ef8'
SETUPS_SHA='83526be03cb66ff596c3949138e7e8935cd12b9f8783a41adaf5f2c04d4ccfda'
PARENT_SHA='09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a'
LAB020_SHA='8e0cd8dc09d5a9d48fab7b951091e836e8d4f276943cd1663192314f8f0ae78d'
LAB021_SHA='3e38dd164f61e36e5e5b30a39b303e50fe585e150f15a804e034a01a79a733f3'
SPEC_SHA='c7b5552bbfd6c68484ff6d62ee91a9244df35f7a4f231393b04164dc2b54a32e'
HOLDOUT=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
FOLD_A_TRAIN_END=pd.Timestamp('2023-01-01')
FOLD_A_CAL_END=pd.Timestamp('2023-07-01')
Y2025=pd.Timestamp('2025-01-01')
T_BOUNDS=(0.50,5.00)
SEED=20260824
BOOT_N=4000
CLASSES=['SL','TIME','TP']

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load_module(path:Path,name:str):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def softmax(a):
    a=np.asarray(a,float)
    a=a-np.max(a,axis=1,keepdims=True)
    e=np.exp(a)
    return e/e.sum(axis=1,keepdims=True)

def temperature_scale(p,T):
    p=np.clip(np.asarray(p,float),1e-12,1.0)
    return softmax(np.log(p)/float(T))

def matrix_from(z,prefix):
    return z[[f'{prefix}_{c}' for c in CLASSES]].to_numpy(float)

def fit_temporal_temperature(discovery, lab021, target):
    blocks=[]
    folds=[
      ('FOLD_A', discovery.break_time<FOLD_A_TRAIN_END,
       (discovery.break_time>=FOLD_A_TRAIN_END)&(discovery.break_time<FOLD_A_CAL_END)),
      ('FOLD_B', discovery.break_time<FOLD_A_CAL_END,
       (discovery.break_time>=FOLD_A_CAL_END)&(discovery.break_time<DISC_END)),
    ]
    fold_meta=[]
    for name,trmask,vmask in folds:
        tr=discovery[trmask].copy(); va=discovery[vmask].copy()
        if len(tr)==0 or len(va)==0 or tr.terminal_outcome.nunique()<2:
            raise RuntimeError(f'bad temporal fold {name}: train={len(tr)} val={len(va)}')
        _,sc=lab021.fit_prob(tr,va,lab021.CAT_FULL,lab021.NUM_FULL,'oot')
        sc['cal_fold']=name
        blocks.append(sc[['trade_id','break_time','terminal_outcome','oot_SL','oot_TIME','oot_TP','cal_fold']].copy())
        fold_meta.append({'fold':name,'train_snapshots':len(tr),'train_trades':tr.trade_id.nunique(),
                          'cal_snapshots':len(va),'cal_trades':va.trade_id.nunique(),
                          'train_max_break':str(tr.break_time.max()),'cal_min_break':str(va.break_time.min()),
                          'cal_max_break':str(va.break_time.max())})
    oof=pd.concat(blocks,ignore_index=True)
    y=oof.terminal_outcome.astype(str).to_numpy()
    p=matrix_from(oof,'oot')
    def objective(T):
        pc=temperature_scale(p,float(T))
        return float(log_loss(y,np.clip(pc,1e-12,1-1e-12),labels=CLASSES))
    opt=minimize_scalar(objective,bounds=T_BOUNDS,method='bounded',options={'xatol':1e-7})
    if not opt.success: raise RuntimeError(f'temperature optimization failed: {opt}')
    T=float(opt.x)
    pc=temperature_scale(p,T)
    raw_ll=float(log_loss(y,np.clip(p,1e-12,1-1e-12),labels=CLASSES))
    cal_ll=float(log_loss(y,np.clip(pc,1e-12,1-1e-12),labels=CLASSES))
    y1=pd.get_dummies(pd.Categorical(y,categories=CLASSES)).to_numpy(float)
    raw_br=float(np.mean(np.sum((p-y1)**2,axis=1)))
    cal_br=float(np.mean(np.sum((pc-y1)**2,axis=1)))
    for j,c in enumerate(CLASSES): oof[f'cal_{c}']=pc[:,j]
    meta={'target_R':float(target),'temperature':T,'bounds':list(T_BOUNDS),
          'oof_snapshots':int(len(oof)),'oof_trades':int(oof.trade_id.nunique()),
          'raw_logloss':raw_ll,'cal_logloss':cal_ll,
          'raw_brier':raw_br,'cal_brier':cal_br,'folds':fold_meta}
    return T,oof,meta

def apply_calibration(raw,T,target,time_mean):
    z=raw.copy()
    p=matrix_from(z,'raw')
    pc=temperature_scale(p,T)
    for j,c in enumerate(CLASSES): z[f'cal_{c}']=pc[:,j]
    z['raw_ev_terminal']=z['raw_TP']*target + z['raw_SL']*(-1.0) + z['raw_TIME']*time_mean
    z['raw_ev_remaining']=z['raw_ev_terminal']-z.current_R
    z['cal_ev_terminal']=z['cal_TP']*target + z['cal_SL']*(-1.0) + z['cal_TIME']*time_mean
    z['cal_ev_remaining']=z['cal_ev_terminal']-z.current_R
    return z

def score_final(discovery, confirmation, lab021, target, time_mean, T):
    m,raw=lab021.fit_prob(discovery,confirmation,lab021.CAT_FULL,lab021.NUM_FULL,'raw')
    z=apply_calibration(raw,T,target,time_mean)
    return m,z

def calibration_table(z,prefix):
    rows=[]
    for cls in CLASSES:
        q=z.copy()
        q['rank']=q[f'{prefix}_{cls}'].rank(method='first',pct=True)
        q['quintile']=pd.cut(q['rank'],[0,.2,.4,.6,.8,1],
                             labels=['Q1','Q2','Q3','Q4','Q5'],include_lowest=True)
        for quint,g in q.groupby('quintile',observed=True):
            rows.append({'model':prefix,'class':cls,'quintile':str(quint),'n':int(len(g)),
                         'mean_p':float(g[f'{prefix}_{cls}'].mean()),
                         'actual_rate':float((g.terminal_outcome==cls).mean())})
    return pd.DataFrame(rows)

def paired_between(x,col_a,col_b,seed):
    z=x[[col_a,col_b,'baseline_entry_time']].dropna().copy()
    z['diff']=z[col_a]-z[col_b]
    z['week']=pd.to_datetime(z.baseline_entry_time).dt.to_period('W-MON').astype(str)
    w=z.groupby('week')['diff'].mean().to_numpy(float)
    a=np.asarray(w,float)
    if len(a)<8:
        ci=[None,None]
    else:
        rng=np.random.default_rng(seed)
        b=np.array([rng.choice(a,size=len(a),replace=True).mean() for _ in range(BOOT_N)])
        ci=[float(np.quantile(b,.025)),float(np.quantile(b,.975))]
    return {'trade_mean':float(z['diff'].mean()),'n_trades':int(len(z)),
            'n_weeks':int(len(a)),'week_mean':float(a.mean()) if len(a) else None,'ci95':ci}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--df-cache',type=Path,required=True)
    ap.add_argument('--setups-cache',type=Path,required=True)
    ap.add_argument('--parent-runner',type=Path,required=True)
    ap.add_argument('--lab020-runner',type=Path,required=True)
    ap.add_argument('--lab021-runner',type=Path,required=True)
    ap.add_argument('--spec',type=Path,required=True)
    ap.add_argument('--outdir',type=Path,required=True)
    a=ap.parse_args(); out=a.outdir; out.mkdir(parents=True,exist_ok=True)

    hashes={
      'df_cache':sha256(a.df_cache),'setups_cache':sha256(a.setups_cache),
      'parent_runner':sha256(a.parent_runner),'lab020_runner':sha256(a.lab020_runner),
      'lab021_runner':sha256(a.lab021_runner),'spec':sha256(a.spec)}
    expected={'df_cache':DF_SHA,'setups_cache':SETUPS_SHA,'parent_runner':PARENT_SHA,
              'lab020_runner':LAB020_SHA,'lab021_runner':LAB021_SHA,'spec':SPEC_SHA}
    if hashes!=expected: raise RuntimeError(f'hash mismatch {hashes}')

    parent=load_module(a.parent_runner,'parent012')
    lab020=load_module(a.lab020_runner,'parent020')
    lab021=load_module(a.lab021_runner,'parent021')
    df=pickle.load(open(a.df_cache,'rb')); setups=pickle.load(open(a.setups_cache,'rb'))
    df,base=lab021.prep_base(df,setups,lab020)
    if (base.break_time>=HOLDOUT).any() or df.time.max()>=HOLDOUT: raise RuntimeError('holdout opened')

    results={}
    temps={}
    scored={}
    oofs={}
    violations=0
    for target in (1.5,2.0):
        snaps,viol=lab020.build_snapshots(base,df,target); violations+=int(viol)
        snaps=lab021.add_labels(snaps,base,target)
        disc=snaps[snaps.break_time<DISC_END].copy()
        conf=snaps[(snaps.break_time>=DISC_END)&(snaps.break_time<HOLDOUT)].copy()
        time_mean=lab021.time_mean_discovery(base,target)
        T,oof,tmeta=fit_temporal_temperature(disc,lab021,target)
        model,z=score_final(disc,conf,lab021,target,time_mean,T)
        temps[target]=tmeta; scored[target]=z; oofs[target]=oof
        rawdiag=lab021.model_diag(z,'raw'); caldiag=lab021.model_diag(z,'cal')
        results[target]={'raw':rawdiag,'cal':caldiag,'time_mean':time_mean}

    conftr=base[(base.break_time>=DISC_END)&(base.break_time<HOLDOUT)].copy()
    z15=scored[1.5]; z20=scored[2.0]
    rawman=lab021.apply_manager(conftr,z15,df,1.5,'raw','RAW_PAYOFF')
    calman=lab021.apply_manager(conftr,z15,df,1.5,'cal','CAL_PAYOFF')
    calman=lab021.apply_manager(calman,z20,df,2.0,'cal','CAL_PAYOFF')

    rawserial=lab021.build_serial(rawman,'RAW_PAYOFF',1.5,parent)
    calserial=lab021.build_serial(calman,'CAL_PAYOFF',1.5,parent)
    cal2serial=lab021.build_serial(calman,'CAL_PAYOFF',2.0,parent)
    baseserial=lab021.build_serial(calman,'BASELINE',1.5,parent)

    rawstats=lab021.stats(rawserial,'RAW_PAYOFF',1.5)
    calstats=lab021.stats(calserial,'CAL_PAYOFF',1.5)
    cal2stats=lab021.stats(cal2serial,'CAL_PAYOFF',2.0)
    basestats=lab021.stats(baseserial,'BASELINE',1.5)
    calind=lab021.stats(calman,'CAL_PAYOFF',1.5)
    y24=lab021.stats(calman[(calman.break_time>=DISC_END)&(calman.break_time<Y2025)],'CAL_PAYOFF',1.5)
    y25=lab021.stats(calman[(calman.break_time>=Y2025)&(calman.break_time<HOLDOUT)],'CAL_PAYOFF',1.5)

    weekly=lab021.boot_week_ev(calserial,'CAL_PAYOFF',1.5,SEED+1)
    paired_base=lab021.boot_paired(calman,'CAL_PAYOFF',1.5,SEED+2)
    rawcols=rawman[['trade_id','raw_payoff_net_R_1p5']].copy()
    cmp=calman[['trade_id','cal_payoff_net_R_1p5','baseline_entry_time']].merge(rawcols,on='trade_id',how='inner')
    paired_raw=paired_between(cmp,'cal_payoff_net_R_1p5','raw_payoff_net_R_1p5',SEED+3)

    caltab=pd.concat([calibration_table(z15,'raw'),calibration_table(z15,'cal')],ignore_index=True)
    caltab.to_csv(out/'calibration.csv',index=False)
    oofsum=pd.DataFrame([temps[1.5],temps[2.0]])
    oofsum['folds_json']=oofsum['folds'].apply(json.dumps); oofsum=oofsum.drop(columns=['folds'])
    oofsum.to_csv(out/'temperature_summary.csv',index=False)
    pd.concat([oofs[1.5].assign(target_R=1.5),oofs[2.0].assign(target_R=2.0)],ignore_index=True).to_csv(out/'temporal_oof_predictions.csv.gz',index=False,compression='gzip')
    pd.DataFrame([
      {'target_R':1.5,'model':'RAW_FULL',**results[1.5]['raw']},
      {'target_R':1.5,'model':'TEMP_CAL_FULL',**results[1.5]['cal']},
      {'target_R':2.0,'model':'RAW_FULL',**results[2.0]['raw']},
      {'target_R':2.0,'model':'TEMP_CAL_FULL',**results[2.0]['cal']},
    ]).to_csv(out/'model_summary.csv',index=False)
    pd.DataFrame([
      {'strategy':'BASELINE','target_R':1.5,'portfolio':'SERIAL',**basestats},
      {'strategy':'RAW_PAYOFF','target_R':1.5,'portfolio':'SERIAL',**rawstats},
      {'strategy':'TEMP_CAL_PAYOFF','target_R':1.5,'portfolio':'SERIAL',**calstats},
      {'strategy':'TEMP_CAL_PAYOFF','target_R':1.5,'portfolio':'INDEPENDENT',**calind},
      {'strategy':'TEMP_CAL_PAYOFF','target_R':2.0,'portfolio':'SERIAL',**cal2stats},
      {'strategy':'TEMP_CAL_PAYOFF_2024','target_R':1.5,'portfolio':'INDEPENDENT',**y24},
      {'strategy':'TEMP_CAL_PAYOFF_2025H1','target_R':1.5,'portfolio':'INDEPENDENT',**y25},
    ]).to_csv(out/'summary.csv',index=False)

    ex=calman[calman.cal_payoff_outcome_1p5=='MODEL_EXIT'].copy()
    keep=['trade_id','break_time','dir','level','digestion_state','cal_payoff_net_R_1p5','baseline_net_R_1p5',
          'cal_payoff_exit_ev_remaining_1p5','cal_payoff_exit_pTP_1p5','cal_payoff_exit_pSL_1p5',
          'cal_payoff_exit_pTIME_1p5','cal_payoff_exit_current_R_1p5']
    ex[keep].to_csv(out/'model_exit_diagnostic.csv',index=False)

    rawd=results[1.5]['raw']; cald=results[1.5]['cal']
    rel_ll=(rawd['logloss']-cald['logloss'])/rawd['logloss']
    rel_br=(rawd['multiclass_brier']-cald['multiclass_brier'])/rawd['multiclass_brier']
    gates={
      'G0_DATA_CAUSALITY':bool(violations==0 and df.time.max()<HOLDOUT and (base.break_time<HOLDOUT).all()),
      'G1_POWER':bool(calstats.get('n',0)>=500 and calstats.get('trades_per_week',0)>=5),
      'G2_RANK_INFORMATION':bool(rawd['macro_ovr_auc']>=0.60),
      'G3_CALIBRATION_IMPROVES':bool(cald['logloss']<rawd['logloss'] and cald['multiclass_brier']<rawd['multiclass_brier']),
      'G4_CALIBRATION_MATERIAL':bool(rel_ll>=0.02 and rel_br>=0.02),
      'G5_CONFIRMATION_EV':bool(calstats.get('ev',-9)>0 and calstats.get('pf',0)>1),
      'G6_WEEK_CLUSTER_CI':bool(weekly['ci95'][0] is not None and weekly['ci95'][0]>0),
      'G7_MANAGEMENT_LIFT':bool(paired_base.get('trade_mean',-9)>0 and paired_base['ci95'][0] is not None and paired_base['ci95'][0]>0),
      'G8_BEATS_RAW_MANAGER':bool(paired_raw.get('trade_mean',-9)>0 and paired_raw['ci95'][0] is not None and paired_raw['ci95'][0]>0),
      'G9_TEMPORAL_TRANSFER':bool(y24.get('ev',-9)>0 and y25.get('ev',-9)>0),
      'G10_2R_SURVIVAL':bool(cal2stats.get('ev',-9)>=0),
      'G11_DIRECTION_BREADTH':bool(calstats.get('buy_ev',-9)>0 and calstats.get('sell_ev',-9)>0),
      'G12_PROP_DD_PROXY':bool(calstats.get('max_dd_R',999)<=20 and calstats.get('worst_day_R',-999)>-16),
      'G13_COST_STRESS':bool(calstats.get('stress10_ev',-9)>0),
    }
    if not gates['G0_DATA_CAUSALITY']:
        verdict='INVALID_DATA_CAUSALITY'
    elif all(gates.values()):
        verdict='CALIBRATED_OUTCOME_X_PAYOFF_MANAGEMENT_EXECUTABLE_EDGE'
    elif gates['G3_CALIBRATION_IMPROVES'] and gates['G4_CALIBRATION_MATERIAL'] and not gates['G5_CONFIRMATION_EV']:
        verdict='CALIBRATION_FIXES_PROBABILITIES_NOT_ECONOMICS'
    elif gates['G3_CALIBRATION_IMPROVES'] and gates['G5_CONFIRMATION_EV'] and not gates['G9_TEMPORAL_TRANSFER']:
        verdict='CALIBRATION_IMPROVES_BUT_NOT_TRANSFERABLE'
    else:
        verdict='NO_TEMPORAL_CALIBRATION_MANAGEMENT_EDGE'

    audit={'lab':LAB,'version':VERSION,'holdout_opened':False,'violations':int(violations),
           'hashes':hashes,'expected_hashes':expected,'temperature_1p5':temps[1.5],
           'temperature_2p0':temps[2.0],'time_mean_1p5':results[1.5]['time_mean'],
           'time_mean_2p0':results[2.0]['time_mean']}
    verdict_obj={'lab':LAB,'version':VERSION,'verdict':verdict,'holdout_opened':False,
                 'gates':gates,'relative_logloss_improvement':rel_ll,'relative_brier_improvement':rel_br,
                 'paired_vs_baseline':paired_base,'paired_vs_raw_manager':paired_raw,
                 'weekly_ev':weekly,'temperature_1p5':temps[1.5]['temperature'],'temperature_2p0':temps[2.0]['temperature']}
    (out/'audit.json').write_text(json.dumps(audit,indent=2))
    (out/'verdict.json').write_text(json.dumps(verdict_obj,indent=2))

    report=f"""# {LAB} — v001 REPORT

**Verdict:** `{verdict}`  
**Holdout opened:** `false`

## Discovery-only temporal calibration
- 1.5R temperature T **{temps[1.5]['temperature']:.4f}**
- 1.5R OOT raw logloss **{temps[1.5]['raw_logloss']:.4f}** -> calibrated **{temps[1.5]['cal_logloss']:.4f}**
- 1.5R OOT raw Brier **{temps[1.5]['raw_brier']:.4f}** -> calibrated **{temps[1.5]['cal_brier']:.4f}**
- 2R temperature T **{temps[2.0]['temperature']:.4f}**

## Confirmation probability quality — 1.5R
- RAW FULL macro AUC **{rawd['macro_ovr_auc']:.4f}**, logloss **{rawd['logloss']:.4f}**, Brier **{rawd['multiclass_brier']:.4f}**
- TEMP-CAL macro AUC **{cald['macro_ovr_auc']:.4f}**, logloss **{cald['logloss']:.4f}**, Brier **{cald['multiclass_brier']:.4f}**
- relative logloss improvement **{rel_ll*100:.2f}%**
- relative Brier improvement **{rel_br*100:.2f}%**

## Primary Confirmation — TEMP_CAL_PAYOFF / 1.5R / serial
- N **{calstats.get('n')}**, trades/week **{calstats.get('trades_per_week'):.2f}**
- EV **{calstats.get('ev'):+.4f}R**, PF **{calstats.get('pf'):.3f}**
- TP rate **{calstats.get('tp_rate'):.2%}**, model-exit rate **{calstats.get('model_exit_rate'):.2%}**
- BUY **{calstats.get('buy_ev'):+.4f}R**, SELL **{calstats.get('sell_ev'):+.4f}R**
- stress10 EV **{calstats.get('stress10_ev'):+.4f}R**
- median duration **{calstats.get('median_duration_min'):.1f} min**
- weekly EV CI **{weekly['ci95']}**

## Baseline / raw-manager comparison
- baseline serial EV **{basestats.get('ev'):+.4f}R**, PF **{basestats.get('pf'):.3f}**
- LAB021-style RAW payoff manager serial EV **{rawstats.get('ev'):+.4f}R**, PF **{rawstats.get('pf'):.3f}**
- calibrated minus baseline paired trade mean **{paired_base.get('trade_mean'):+.4f}R**, week CI **{paired_base.get('ci95')}**
- calibrated minus raw manager paired trade mean **{paired_raw.get('trade_mean'):+.4f}R**, week CI **{paired_raw.get('ci95')}**

## Transfer / 2R
- 2024 calibrated independent EV **{y24.get('ev'):+.4f}R**
- 2025H1 calibrated independent EV **{y25.get('ev'):+.4f}R**
- 2R calibrated serial EV **{cal2stats.get('ev'):+.4f}R**, PF **{cal2stats.get('pf'):.3f}**

## Frozen gates
""" + "\n".join([f"- {k}: **{'PASS' if v else 'FAIL'}**" for k,v in gates.items()]) + """

No Confirmation calibration, no threshold rescue, no holdout opening, no EA/live authorization.
"""
    (out/'REPORT.md').write_text(report)
    print(json.dumps({'verdict':verdict,'temperature_1p5':temps[1.5]['temperature'],
                      'raw_logloss':rawd['logloss'],'cal_logloss':cald['logloss'],
                      'raw_brier':rawd['multiclass_brier'],'cal_brier':cald['multiclass_brier'],
                      'cal_serial_ev':calstats.get('ev'),'raw_serial_ev':rawstats.get('ev'),
                      'baseline_ev':basestats.get('ev'),'paired_vs_baseline':paired_base,
                      'paired_vs_raw':paired_raw,'gates':gates},indent=2))

if __name__=='__main__':
    main()
