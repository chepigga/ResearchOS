#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss

LAB='XAU_PRE_ENTRY_TICK_ACTIVITY_SURVIVAL_TRANSFER_LAB_029'; VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
PARENT_SHA='09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a'
HOLDOUT=pd.Timestamp('2025-07-01'); DISC_END=pd.Timestamp('2024-01-01')
ADVERSE_DEPTH=.10; RISK_ATR=.50; SEED=20260826

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def loadmod(p):
    sp=importlib.util.spec_from_file_location('parent',p); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def rebuild(parent,input_path,break_path):
    df=parent.add_atr_vwap(parent.load_prices(input_path)); br=parent.load_breaks(break_path)
    ev=parent.score_bias(parent.build_bias_events(br,df)); strong=ev[ev.strong_accept].copy(); s=parent.build_setups(strong,df)
    s=parent.simulate_branch(s,df,'BASELINE',1.5)
    base=s[(s.strong_accept.astype(bool))&(s.digestion_found.astype(bool))&(s.baseline_entry_i>=0)&(~s.causality_violation.astype(bool))&(s.break_time<HOLDOUT)].copy()
    return df,parent.dedupe_serial_universe(base)

def attach_tick_volume(df,input_path):
    extra=pd.read_csv(input_path,sep=';',usecols=['time','tick_volume'])
    extra['time']=pd.to_datetime(extra.time,format='%Y.%m.%d %H:%M',errors='coerce')
    extra=extra[extra.time<HOLDOUT].sort_values('time').drop_duplicates('time',keep='last')
    return df.merge(extra,on='time',how='left',validate='one_to_one')

def label_survival(base,df):
    times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    cl=df.close.to_numpy(float); bl=df.low.to_numpy(float); ah=df.ask_high.to_numpy(float); al=df.ask_low.to_numpy(float); bh=df.high.to_numpy(float)
    lines={k:df[k].to_numpy(float) for k in ('MID','HIGH','LOW')}
    ys=[]; reasons=[]; vio=0
    for r in base.itertuples(index=False):
        ei=int(r.baseline_entry_i); d=int(r.dir); e=float(r.baseline_entry); a=float(r.atr0); sl=e-d*RISK_ATR*a; tp=e+d*1.5*RISK_ATR*a
        ok=True; rs='SURVIVE'
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
        ys.append(int(ok)); reasons.append(rs)
    z=base.copy(); z['survive5']=ys; z['fail_reason']=reasons
    return z,vio

def safe_div(a,b): return a/(abs(b)+1e-9)

def features(base,df):
    close=df.close.to_numpy(float); hi=df.high.to_numpy(float); lo=df.low.to_numpy(float); tv=df.tick_volume.to_numpy(float)
    rows=[]
    for r in base.itertuples(index=False):
        ei=int(r.baseline_entry_i); d=int(r.dir); a=float(r.atr0)
        row={'p_accept':float(r.p_accept),'dir':d,'level_rank':float(r.level_rank),'atr0':a}
        for w in (3,5,15,30):
            i0=ei-w; i1=ei
            c=close[i0:i1]; h=hi[i0:i1]; l=lo[i0:i1]; v=tv[i0:i1]
            disp=d*(c[-1]-c[0])/a if len(c)>=2 and a>0 else np.nan
            path=np.abs(np.diff(c)).sum()/a if len(c)>=2 and a>0 else np.nan
            eff=disp/(path+1e-9) if np.isfinite(path) else np.nan
            rng=(np.nanmax(h)-np.nanmin(l))/a if len(c) and a>0 else np.nan
            cloc=(c[-1]-np.nanmin(l))/(np.nanmax(h)-np.nanmin(l)+1e-9) if len(c) else np.nan
            row.update({f'disp_{w}':disp,f'path_{w}':path,f'eff_{w}':eff,f'range_{w}':rng,f'cloc_{w}':cloc,
                        f'tv_sum_{w}':np.nansum(v),f'tv_mean_{w}':np.nanmean(v),f'tv_max_{w}':np.nanmax(v)})
        row['tv_ratio_3_15']=safe_div(row['tv_mean_3'],row['tv_mean_15'])
        row['tv_ratio_5_30']=safe_div(row['tv_mean_5'],row['tv_mean_30'])
        row['move_spent_break_entry']=d*(close[ei-1]-close[int(r.break_i)])/a if ei>0 and a>0 else np.nan
        row['break_to_entry_min']=float(ei-int(r.break_i))
        rows.append(row)
    return pd.DataFrame(rows,index=base.index)

def family_cols(cols):
    price=[c for c in cols if c in ['p_accept','dir','level_rank','atr0','move_spent_break_entry','break_to_entry_min'] or c.startswith(('disp_','path_','eff_','range_','cloc_'))]
    activity=[c for c in cols if c.startswith(('tv_sum_','tv_mean_','tv_max_','tv_ratio_'))]
    return price, price+activity

def fit_predict(train,test,X,feat):
    med=X.loc[train.index,feat].median(); xtr=X.loc[train.index,feat].fillna(med); xte=X.loc[test.index,feat].fillna(med)
    m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=15,min_samples_leaf=40,l2_regularization=1.0,random_state=SEED)
    m.fit(xtr,train.survive5)
    ptr=m.predict_proba(xtr)[:,1]; pte=m.predict_proba(xte)[:,1]; thr=float(np.quantile(ptr,.70))
    return pte,thr

def metrics(df,p,thr):
    y=df.survive5.to_numpy(int); sel=p>=thr; base=float(y.mean())
    out={'n':len(df),'survivors':int(y.sum()),'base_rate':base,'auc':float(roc_auc_score(y,p)),'brier':float(brier_score_loss(y,p)),
         'threshold':float(thr),'coverage':float(sel.mean()),'precision':float(y[sel].mean()) if sel.any() else np.nan,
         'survivor_retention':float(y[sel].sum()/max(1,y.sum())),'failure_rejection':float((~sel & (y==0)).sum()/max(1,(y==0).sum()))}
    out['precision_lift']=out['precision']/base if base>0 else np.nan
    for dval,nm in [(1,'buy'),(-1,'sell')]:
        q=df.dir.to_numpy()==dval; yy=y[q]; ss=sel[q]
        out[f'{nm}_base']=float(yy.mean()) if len(yy) else np.nan; out[f'{nm}_precision']=float(yy[ss].mean()) if ss.any() else np.nan
    return out,sel

def period_metrics(conf,p,thr,label,start,end):
    q=(pd.to_datetime(conf.baseline_entry_time)>=pd.Timestamp(start))&(pd.to_datetime(conf.baseline_entry_time)<pd.Timestamp(end))
    d=conf.loc[q].copy(); pp=p[q.to_numpy()]
    m,s=metrics(d,pp,thr); m['period']=label; return m

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--break-census',type=Path,required=True); ap.add_argument('--parent-runner',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); o=a.outdir; o.mkdir(parents=True,exist_ok=True)
    if sha256(a.input)!=CANONICAL_SHA: raise RuntimeError('canonical sha mismatch')
    if sha256(a.parent_runner)!=PARENT_SHA: raise RuntimeError('parent sha mismatch')
    parent=loadmod(a.parent_runner); df,base=rebuild(parent,a.input,a.break_census); df=attach_tick_volume(df,a.input)
    lab,vio=label_survival(base,df); X=features(lab,df); price_cols,act_cols=family_cols(X.columns)
    disc=lab[lab.split=='DISCOVERY'].copy(); conf=lab[lab.split=='CONFIRMATION'].copy()
    p0,t0=fit_predict(disc,conf,X,price_cols); p1,t1=fit_predict(disc,conf,X,act_cols)
    m0,s0=metrics(conf,p0,t0); m1,s1=metrics(conf,p1,t1)
    pd.DataFrame([{'family':'PRICE_ONLY','n_features':len(price_cols),**m0},{'family':'PRICE_PLUS_ACTIVITY','n_features':len(act_cols),**m1}]).to_csv(o/'model_summary.csv',index=False)
    yearly=pd.DataFrame([period_metrics(conf,p1,t1,'2024','2024-01-01','2025-01-01'),period_metrics(conf,p1,t1,'2025H1','2025-01-01','2025-07-01')])
    yearly.to_csv(o/'yearly_transfer.csv',index=False)
    cf=conf.copy(); cf['p_activity']=p1; cf['selected']=s1; cf['starter_control_R']=.25*cf.baseline_net_R_1p5
    econ=[]
    for label,g in cf.groupby('selected'):
        econ.append({'selected':bool(label),'n':len(g),'survival_rate':float(g.survive5.mean()),'starter_control_ev':float(g.starter_control_R.mean()),'baseline_full_ev':float(g.baseline_net_R_1p5.mean()),'baseline_tp_rate':float((g.baseline_outcome_1p5=='TP').mean())})
    pd.DataFrame(econ).to_csv(o/'router_economics.csv',index=False)
    cf['decile']=pd.qcut(cf.p_activity.rank(method='first'),10,labels=False)+1
    dec=cf.groupby('decile').agg(n=('survive5','size'),survival_rate=('survive5','mean'),score_mean=('p_activity','mean'),starter_control_ev=('starter_control_R','mean'),baseline_full_ev=('baseline_net_R_1p5','mean')).reset_index()
    dec.to_csv(o/'score_deciles.csv',index=False)
    sel_e=float(cf.loc[cf.selected,'starter_control_R'].mean()); rej_e=float(cf.loc[~cf.selected,'starter_control_R'].mean())
    top=float(dec.loc[dec.decile==10,'survival_rate'].iloc[0]); bot=float(dec.loc[dec.decile==1,'survival_rate'].iloc[0])
    y24=yearly[yearly.period=='2024'].iloc[0]; y25=yearly[yearly.period=='2025H1'].iloc[0]
    gates={'G0_CAUSALITY':vio==0,'G1_POWER':len(conf)>=300 and int(conf.survive5.sum())>=50,'G2_ACTIVITY_ADDS':m1['auc']>m0['auc'],'G3_ACTIVITY_AUC':m1['auc']>=.62,'G4_YEARLY_TRANSFER':y24.auc>.58 and y25.auc>.58,'G5_YEARLY_PRECISION_LIFT':y24.precision_lift>1.15 and y25.precision_lift>1.15,'G6_DIRECTION_BREADTH':m1['buy_precision']>m1['buy_base'] and m1['sell_precision']>m1['sell_base'],'G7_USEFUL_OPERATIONS':.15<=m1['coverage']<=.40 and m1['survivor_retention']>=.40,'G8_FAILURE_REJECTION':m1['failure_rejection']>=.65,'G9_STARTER_ECONOMICS':sel_e>rej_e,'G10_DECILE_SPREAD':top>bot and top>=1.5*m1['base_rate']}
    if all(gates.values()): status='TICK_ACTIVITY_SURVIVAL_ROUTER_TRANSFERABLE'
    elif all(gates[k] for k in ['G0_CAUSALITY','G1_POWER','G2_ACTIVITY_ADDS','G3_ACTIVITY_AUC','G4_YEARLY_TRANSFER','G5_YEARLY_PRECISION_LIFT','G6_DIRECTION_BREADTH','G7_USEFUL_OPERATIONS','G8_FAILURE_REJECTION','G10_DECILE_SPREAD']): status='TICK_ACTIVITY_SIGNAL_TRANSFERABLE_NOT_ECONOMIC'
    else: status='TICK_ACTIVITY_SIGNAL_WEAK_OR_UNSTABLE'
    verdict={'status':status,'gates':gates,'price_only':m0,'activity':m1,'yearly':yearly.to_dict('records'),'selected_starter_ev':sel_e,'rejected_starter_ev':rej_e,'decile_top_survival':top,'decile_bottom_survival':bot,'causality_violations':vio,'holdout_opened':False}
    (o/'verdict.json').write_text(json.dumps(verdict,indent=2,default=str))
    (o/'audit.json').write_text(json.dumps({'canonical_sha':sha256(a.input),'parent_sha':sha256(a.parent_runner),'break_census_sha':sha256(a.break_census),'confirmation_n':len(conf),'confirmation_survivors':int(conf.survive5.sum()),'causality_violations':vio,'holdout_opened':False,'max_price_time':str(df.time.max())},indent=2))
    rep=f'''# {LAB} — {VERSION} REPORT\n\n**Verdict:** `{status}`  \n**Holdout opened:** `false`\n\n## Confirmation\n- Base survival **{m1['base_rate']:.2%}**; N **{len(conf)}**, survivors **{int(conf.survive5.sum())}**\n- PRICE_ONLY AUC **{m0['auc']:.4f}**\n- PRICE+TICK_ACTIVITY AUC **{m1['auc']:.4f}**; delta **{m1['auc']-m0['auc']:+.4f}**\n- coverage **{m1['coverage']:.2%}**, precision **{m1['precision']:.2%}**, lift **{m1['precision_lift']:.2f}x**\n- survivor retention **{m1['survivor_retention']:.2%}**, failure rejection **{m1['failure_rejection']:.2%}**\n- BUY precision/base **{m1['buy_precision']:.2%}/{m1['buy_base']:.2%}**; SELL **{m1['sell_precision']:.2%}/{m1['sell_base']:.2%}**\n\n## Yearly transfer\n{yearly.to_markdown(index=False)}\n\n## Score-decile diagnostic\n- bottom decile survival **{bot:.2%}**\n- top decile survival **{top:.2%}**\n\n## Starter-control economics\n- selected 0.25x baseline EV **{sel_e:+.4f}R**\n- rejected **{rej_e:+.4f}R**\n\n## Frozen gates\n'''+ '\n'.join(f'- {k}: **{"PASS" if v else "FAIL"}**' for k,v in gates.items())+'\n\nNo threshold rescue, no holdout opening, no EA/live authorization.\n'
    (o/'REPORT.md').write_text(rep)
    print(json.dumps(verdict,indent=2,default=str))
if __name__=='__main__': main()
