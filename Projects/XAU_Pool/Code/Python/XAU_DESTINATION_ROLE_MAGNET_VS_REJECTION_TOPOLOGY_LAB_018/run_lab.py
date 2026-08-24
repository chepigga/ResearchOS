#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

LAB='XAU_DESTINATION_ROLE_MAGNET_VS_REJECTION_TOPOLOGY_LAB_018'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
BREAK_SHA='c9cba1459a60ef9c3bb308e751ebae95840f48a24f94754808862a180832ccdb'
PARENT_RUNNER_SHA='09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a'
PARENT_EVENTS_SHA='83be6298befc9c016c7aec297d3e48a3040258c6d070bae25af4e3c3c11481c2'
LAB017_RUNNER_SHA='d459191f00435621d18a9e06bc3dc95ea51bb09a86406f6287ffb83495e3afe9'
DISC_END=pd.Timestamp('2024-01-01')
HOLDOUT=pd.Timestamp('2025-07-01')
P_GATE=0.55
TP15_ATR=0.75
LOOKBACK=240
TOUCH_TOL_ATR=0.05
BOOT_N=4000
SEED=20260824

TOPO_CAT=['nearest_type','tp_placement','destination_role','last_response','lifecycle_dest_status']
TOPO_NUM=[
    'destination_age_min','tp15_minus_destination_atr',
    'touch_episodes_60','touch_episodes_240','evaluable_touch_count','accept_count','reject_count','mixed_count','accept_rate','reject_rate',
    'last_touch_age_min','min_intertouch_min','repeated_approach_count','destination_fresh',
    'approach_progress_3','approach_progress_5','approach_progress_10','approach_progress_15',
    'approach_speed_3','approach_speed_5','approach_speed_10','approach_speed_15',
    'approach_eff_5','approach_eff_10','approach_eff_15','toward_closes_5','toward_closes_10',
    'pullback_from_closest_15','monotonic_compress_3','monotonic_compress_5','lifecycle_dest_touched',
]

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load_module(path:Path,name:str):
    sp=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def auc(y,p):
    return float(roc_auc_score(y,p)) if pd.Series(y).nunique()>1 else np.nan

def pred_metrics(z,pcol):
    y=z.residual_tp15.astype(int); p=z[pcol].astype(float)
    return {'n':int(len(z)),'base_rate':float(y.mean()),'auc':auc(y,p),'brier':float(brier_score_loss(y,p)),'logloss':float(log_loss(y,np.clip(p,1e-8,1-1e-8),labels=[0,1]))}

def boot_mean(a,seed):
    a=np.asarray(pd.Series(a).dropna(),float)
    if len(a)<8:return {'n':int(len(a)),'mean':float(a.mean()) if len(a) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(a,size=len(a),replace=True).mean() for _ in range(BOOT_N)])
    return {'n':int(len(a)),'mean':float(a.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}

def completed_touch_episodes(high,low,dest,tol,start,end):
    if end<start:return []
    touch=(high[start:end+1]>=dest-tol)&(low[start:end+1]<=dest+tol)
    idx=np.flatnonzero(touch)+start
    if len(idx)==0:return []
    eps=[]; cur=[int(idx[0])]
    for q in idx[1:]:
        q=int(q)
        if q-cur[-1]>=6:
            eps.append((cur[0],cur[-1])); cur=[q]
        else: cur.append(q)
    eps.append((cur[0],cur[-1]))
    return eps

def classify_response(close,dest,d,a,last_touch,de):
    if last_touch+10>de:return None
    vals=d*(close[last_touch+1:last_touch+11]-dest)/a
    if len(vals)!=10:return None
    accept=bool((vals>0).sum()>=7 and vals[-1]>=0.05)
    first_accept=np.flatnonzero(vals>=0.10)
    first_acc=int(first_accept[0]) if len(first_accept) else 999
    deep_rej=np.flatnonzero(vals<=-0.20)
    first_rej=int(deep_rej[0]) if len(deep_rej) else 999
    reject=bool(vals[-1]<=-0.15 or first_rej<first_acc)
    if accept and not reject:return 'ACCEPT'
    if reject and not accept:return 'REJECT'
    return 'MIXED'

def role_label(n_touch,n_eval,acc,rej,last_age):
    if n_touch==0:return 'FRESH'
    ar=acc/n_eval if n_eval else 0.0; rr=rej/n_eval if n_eval else 0.0
    if n_eval>=2 and ar>=0.60 and acc>rej:return 'ACCEPTANCE_DOMINANT'
    if n_eval>=2 and rr>=0.60 and rej>acc:return 'REJECTION_DOMINANT'
    if n_touch>=2 and rr<0.40 and np.isfinite(last_age) and last_age<=120:return 'REPEATED_MAGNET'
    return 'MIXED'

def tp_placement(room,typ):
    if typ=='OPEN_SPACE':return 'OPEN_SPACE'
    if room>0.90:return 'TP_BEFORE_DEST'
    if room>=0.60:return 'TP_NEAR_DEST'
    return 'TP_BEYOND_DEST'

def approach_features(close,dest,d,a,de):
    dist=d*(dest-close)/a
    rec={}
    for n in (3,5,10,15):
        if de-n<0:
            prog=np.nan; speed=np.nan
        else:
            prog=float(dist[de-n]-dist[de]); speed=prog/n
        rec[f'approach_progress_{n}']=prog; rec[f'approach_speed_{n}']=speed
    for n in (5,10,15):
        s=max(0,de-n); x=dist[s:de+1]
        total=float(np.abs(np.diff(x)).sum()) if len(x)>1 else 0.0
        net=float(x[0]-x[-1]) if len(x)>1 else 0.0
        rec[f'approach_eff_{n}']=net/total if total>1e-12 else 0.0
    for n in (5,10):
        s=max(1,de-n+1); rr=d*(close[s:de+1]-close[s-1:de])/a
        rec[f'toward_closes_{n}']=int((rr>0).sum())
    x=dist[max(0,de-15):de+1]
    rec['pullback_from_closest_15']=float(dist[de]-np.nanmin(x)) if len(x) else np.nan
    for n in (3,5):
        x=dist[max(0,de-n):de+1]
        rec[f'monotonic_compress_{n}']=int(len(x)>=n+1 and np.all(np.diff(x)<=1e-12))
    return rec

def nearest_swing_price(piv,decision,c,d,a,lookback_days):
    if piv is None or piv.empty:return (np.nan,np.nan)
    q=piv[(piv.confirm_time<=decision)&(piv.pivot_time>=decision-pd.Timedelta(days=lookback_days))].copy()
    if q.empty:return (np.nan,np.nan)
    q['dist']=d*(q.price.astype(float)-c)/a; q=q[q.dist>1e-12]
    if q.empty:return (np.nan,np.nan)
    r=q.sort_values(['dist','pivot_time']).iloc[0]
    return float(r.price),float((decision-pd.Timestamp(r.pivot_time)).total_seconds()/60.0)

def add_topology(ev,df,lab017):
    close=df.close.to_numpy(float); high=df.high.to_numpy(float); low=df.low.to_numpy(float)
    lines={lev:df[lev].to_numpy(float) for lev in lab017.LEVELS}
    run_hi=df.groupby('session').high.cummax().to_numpy(float); run_lo=df.groupby('session').low.cummin().to_numpy(float)
    ss=df.groupby('session').agg(sess_high=('high','max'),sess_low=('low','min')).sort_index(); ss['prev_high']=ss.sess_high.shift(1); ss['prev_low']=ss.sess_low.shift(1)
    m15,p15=lab017.make_tf_bars(df,'15min'); h1,p60=lab017.make_tf_bars(df,'60min')
    rows=[]; violations=0
    for r in ev.itertuples(index=False):
        de=int(r.digestion_end_i); bi=int(r.break_i); ent=int(r.baseline_entry_i); d=int(r.dir); a=float(r.atr0)
        if de<bi+1 or ent<=de or de>=len(df) or not np.isfinite(a) or a<=0:
            violations+=1; continue
        dec=pd.Timestamp(df.at[de,'time']); c=float(close[de]); ses=df.at[de,'session']
        if dec>=HOLDOUT: violations+=1; continue
        prev=ss.loc[ses] if ses in ss.index else None
        prevh=float(prev.prev_high) if prev is not None and np.isfinite(prev.prev_high) else np.nan
        prevl=float(prev.prev_low) if prev is not None and np.isfinite(prev.prev_low) else np.nan
        curh=float(run_hi[de]); curl=float(run_lo[de])
        cand=[]
        for lev in lab017.LEVELS:
            if lev==str(r.level): continue
            p=float(df.at[de,lev]); dist=d*(p-c)/a
            if np.isfinite(dist) and dist>1e-12:cand.append(('VWAP',p,float(dist),0.0))
        for typ,p in [('PREV_SESSION',prevh),('PREV_SESSION',prevl),('CURRENT_SESSION',curh),('CURRENT_SESSION',curl)]:
            if np.isfinite(p):
                dist=d*(p-c)/a
                if dist>1e-12:
                    if typ=='PREV_SESSION': age=1440.0
                    else:
                        sidx=np.flatnonzero((df.session.to_numpy()==ses)&(np.arange(len(df))<=de)&(np.isclose((high if d>0 else low),p,rtol=0,atol=1e-10)))
                        age=float(de-int(sidx[-1])) if len(sidx) else np.nan
                    cand.append((typ,float(p),float(dist),age))
        p,age=nearest_swing_price(p15,dec,c,d,a,5)
        if np.isfinite(p): cand.append(('M15_SWING',p,float(d*(p-c)/a),age))
        p,age=nearest_swing_price(p60,dec,c,d,a,20)
        if np.isfinite(p): cand.append(('H1_SWING',p,float(d*(p-c)/a),age))
        cand=[x for x in cand if np.isfinite(x[2]) and x[2]>1e-12]
        if cand:
            typ,dest,room,age=min(cand,key=lambda x:x[2])
        else:
            typ,dest,room,age='OPEN_SPACE',np.nan,lab017.OPEN_SPACE_CAP,np.nan
        rec=r._asdict(); rec['destination_price']=dest; rec['destination_age_min']=age; rec['nearest_type']=typ; rec['nearest_room_atr']=room
        rec['tp15_minus_destination_atr']=TP15_ATR-room; rec['tp_placement']=tp_placement(room,typ)
        if typ=='OPEN_SPACE':
            rec.update({'touch_episodes_60':0,'touch_episodes_240':0,'evaluable_touch_count':0,'accept_count':0,'reject_count':0,'mixed_count':0,'accept_rate':0.0,'reject_rate':0.0,'last_touch_age_min':np.nan,'min_intertouch_min':np.nan,'repeated_approach_count':0,'destination_fresh':1,'destination_role':'FRESH','last_response':'NONE','lifecycle_dest_touched':0,'lifecycle_dest_status':'OPEN_SPACE'})
            for k,v in approach_features(close,c+d*lab017.OPEN_SPACE_CAP*a,d,a,de).items(): rec[k]=v
            rows.append(rec); continue
        tol=TOUCH_TOL_ATR*a; st=max(0,de-LOOKBACK+1); eps=completed_touch_episodes(high,low,dest,tol,st,de)
        completed=[e for e in eps if e[1]<=de-5]
        evals=[]
        for e in completed:
            cls=classify_response(close,dest,d,a,e[1],de)
            if cls is not None: evals.append((e,cls))
        n60=sum(1 for e in completed if e[0]>=de-59); n240=len(completed); ne=len(evals)
        acc=sum(1 for _,x in evals if x=='ACCEPT'); rej=sum(1 for _,x in evals if x=='REJECT'); mix=sum(1 for _,x in evals if x=='MIXED')
        last_age=float(de-completed[-1][1]) if completed else np.nan
        starts=[e[0] for e in completed]; minint=float(np.min(np.diff(starts))) if len(starts)>=2 else np.nan
        last_resp=evals[-1][1] if evals else 'NONE'; role=role_label(n240,ne,acc,rej,last_age)
        life_touch=((high[bi:de+1]>=dest-tol)&(low[bi:de+1]<=dest+tol)); life=int(life_touch.any()); signed_now=float(d*(c-dest)/a)
        if not life: life_status='NOT_TOUCHED'
        elif signed_now>=0.05: life_status='ACCEPTED_BEYOND'
        elif signed_now<=-0.15: life_status='REJECTED_BACK'
        else: life_status='AT_DESTINATION'
        rec.update({'touch_episodes_60':n60,'touch_episodes_240':n240,'evaluable_touch_count':ne,'accept_count':acc,'reject_count':rej,'mixed_count':mix,'accept_rate':acc/ne if ne else 0.0,'reject_rate':rej/ne if ne else 0.0,'last_touch_age_min':last_age,'min_intertouch_min':minint,'repeated_approach_count':n240,'destination_fresh':int(n240==0),'destination_role':role,'last_response':last_resp,'lifecycle_dest_touched':life,'lifecycle_dest_status':life_status})
        rec.update(approach_features(close,dest,d,a,de)); rows.append(rec)
    z=pd.DataFrame(rows)
    for c in TOPO_CAT:
        if c in z:z[c]=z[c].fillna('NONE').astype(str)
    return z,violations

def score_all(train,test,lab017):
    basecat=lab017.BIAS_CAT+lab017.ROOM_CAT; basenum=lab017.BIAS_NUM+lab017.ROOM_NUM
    mb,b=lab017.fit_prob(train,test,basecat,basenum,'p_room_baseline')
    mt,t=lab017.fit_prob(train,test,TOPO_CAT,TOPO_NUM,'p_topology_only')
    mp,p=lab017.fit_prob(train,test,basecat+TOPO_CAT,basenum+TOPO_NUM,'p_topology')
    mr,r=lab017.fit_prob(train,test,basecat+TOPO_CAT,basenum+TOPO_NUM+lab017.RAW_NUM,'p_topology_raw')
    z=b.copy(); z['p_topology_only']=t.p_topology_only.to_numpy(); z['p_topology']=p.p_topology.to_numpy(); z['p_topology_raw']=r.p_topology_raw.to_numpy(); z['topology_armed']=z.p_topology>=P_GATE
    return {'baseline':mb,'only':mt,'primary':mp,'raw':mr},z

def weekly_auc_diff(z):
    q=z.copy(); q['week']=q.break_time.dt.to_period('W-MON').astype(str); rows=[]
    for w,g in q.groupby('week'):
        if len(g)>=20 and g.residual_tp15.nunique()>1: rows.append({'week':w,'diff':auc(g.residual_tp15,g.p_topology)-auc(g.residual_tp15,g.p_room_baseline)})
    return pd.DataFrame(rows)

def selection_gap(z):
    q=z.copy(); q['week']=q.break_time.dt.to_period('W-MON').astype(str); vals=[]
    for _,g in q.groupby('week'):
        a=g[g.topology_armed].residual_tp15; b=g[~g.topology_armed].residual_tp15
        if len(a)>=5 and len(b)>=5:vals.append(a.mean()-b.mean())
    return boot_mean(vals,SEED+3)

def calibration(z):
    q=z.copy(); q['rank']=q.p_topology.rank(method='first',pct=True); q['quintile']=pd.cut(q['rank'],[0,.2,.4,.6,.8,1],labels=['Q1','Q2','Q3','Q4','Q5'],include_lowest=True)
    return q.groupby('quintile',observed=True).agg(n=('residual_tp15','size'),mean_p=('p_topology','mean'),actual_tp15=('residual_tp15','mean'),ev=('baseline_net_R_1p5','mean')).reset_index()

def thresholds(z):
    rows=[]
    for th in [0.45,0.50,0.55,0.60,0.65]:
        g=z[z.p_topology>=th]; rows.append({'threshold':th,'n':len(g),'coverage':len(g)/len(z) if len(z) else np.nan,'tp15_rate':g.residual_tp15.mean() if len(g) else np.nan,'ind_ev':g.baseline_net_R_1p5.mean() if len(g) else np.nan})
    return pd.DataFrame(rows)

def subgroup(z,col):
    return z.groupby(col).agg(n=('residual_tp15','size'),tp15_rate=('residual_tp15','mean'),ind_ev=('baseline_net_R_1p5','mean'),mean_p=('p_topology','mean')).reset_index().sort_values('n',ascending=False)

def touch_bucket(z):
    q=z.copy(); q['touch_bucket']=pd.cut(q.touch_episodes_240,[-1,0,1,2,4,999],labels=['0','1','2','3-4','5+'])
    return subgroup(q,'touch_bucket')

def approach_quintiles(z):
    q=z.copy(); q['rank']=q.approach_speed_10.rank(method='first',pct=True); q['approach_q']=pd.cut(q['rank'],[0,.2,.4,.6,.8,1],labels=['Q1','Q2','Q3','Q4','Q5'],include_lowest=True)
    return subgroup(q,'approach_q')

def grouped_perm(model,z,lab017):
    cat=lab017.BIAS_CAT+lab017.ROOM_CAT+TOPO_CAT; num=lab017.BIAS_NUM+lab017.ROOM_NUM+TOPO_NUM; X=z[cat+num].copy(); base=auc(z.residual_tp15,model.predict_proba(X)[:,1]); rng=np.random.default_rng(SEED)
    groups={'LAB017_BASELINE':lab017.BIAS_CAT+lab017.ROOM_CAT+lab017.BIAS_NUM+lab017.ROOM_NUM,'DEST_ID_PLACEMENT':['nearest_type','tp_placement','destination_age_min','tp15_minus_destination_atr'],'HISTORICAL_ROLE':['destination_role','last_response','touch_episodes_60','touch_episodes_240','evaluable_touch_count','accept_count','reject_count','mixed_count','accept_rate','reject_rate','last_touch_age_min','min_intertouch_min','repeated_approach_count','destination_fresh'],'CURRENT_APPROACH':[c for c in TOPO_NUM if c.startswith('approach_') or c.startswith('toward_') or c.startswith('pullback_') or c.startswith('monotonic_')],'LIFECYCLE_INTERACTION':['lifecycle_dest_touched','lifecycle_dest_status']}
    rows=[]
    for name,cols in groups.items():
        vals=[]
        for _ in range(5):
            xp=X.copy(); perm=rng.permutation(len(xp))
            for c in cols:
                if c in xp:xp[c]=xp[c].to_numpy()[perm]
            vals.append(base-auc(z.residual_tp15,model.predict_proba(xp)[:,1]))
        rows.append({'group':name,'auc_drop_mean':float(np.mean(vals)),'auc_drop_sd':float(np.std(vals))})
    return pd.DataFrame(rows).sort_values('auc_drop_mean',ascending=False)

def weekly_strategy_diff(a,b,seed):
    def wm(x):
        if x is None or x.empty:return pd.Series(dtype=float)
        q=x.copy(); q['week']=pd.to_datetime(q.baseline_entry_time).dt.to_period('W-MON').astype(str); return q.groupby('week').baseline_net_R_1p5.mean()
    wa,wb=wm(a),wm(b); idx=wa.index.union(wb.index); return boot_mean((wa.reindex(idx,fill_value=0)-wb.reindex(idx,fill_value=0)).to_numpy(float),seed)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--canonical',type=Path,required=True); ap.add_argument('--break-census',type=Path,required=True); ap.add_argument('--parent-runner',type=Path,required=True); ap.add_argument('--parent-events',type=Path,required=True); ap.add_argument('--lab017-runner',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    hs=(sha256(a.canonical),sha256(a.break_census),sha256(a.parent_runner),sha256(a.parent_events),sha256(a.lab017_runner)); exp=(CANONICAL_SHA,BREAK_SHA,PARENT_RUNNER_SHA,PARENT_EVENTS_SHA,LAB017_RUNNER_SHA)
    if hs!=exp:raise RuntimeError(f'hash mismatch {hs}')
    parent=load_module(a.parent_runner,'lab012_parent'); lab017=load_module(a.lab017_runner,'lab017_frozen'); df=parent.add_atr_vwap(parent.load_prices(a.canonical)); pe=lab017.load_parent_events(a.parent_events); baseev,baseviol=lab017.add_features(pe,df); ev,topviol=add_topology(baseev,df,lab017)
    if ev.empty:raise RuntimeError('no events')
    violations=int(baseviol+topviol+ev.feature_causality_violation.astype(bool).sum()+ev.causality_violation.astype(bool).sum())
    if (ev.break_time>=HOLDOUT).any():raise RuntimeError('holdout opened')
    disc=ev[ev.break_time<DISC_END].copy(); conf=ev[(ev.break_time>=DISC_END)&(ev.break_time<HOLDOUT)].copy(); models,sc=score_all(disc,conf,lab017)
    dtrain=disc[disc.break_time<pd.Timestamp('2023-01-01')].copy(); d23=disc[(disc.break_time>=pd.Timestamp('2023-01-01'))&(disc.break_time<DISC_END)].copy(); _,sd23=score_all(dtrain,d23,lab017)
    model_cols=[('BIAS_X_ROOM_BASELINE','p_room_baseline'),('DESTINATION_TOPOLOGY_ONLY','p_topology_only'),('BIAS_X_DESTINATION_TOPOLOGY','p_topology'),('BIAS_X_DESTINATION_TOPOLOGY_PLUS_FIXED_RAW','p_topology_raw')]; ms=[]
    for split,z in [('DISCOVERY_2023',sd23),('CONFIRMATION',sc)]:
        for name,p in model_cols:ms.append({'split':split,'model':name,**pred_metrics(z,p)})
    pd.DataFrame(ms).to_csv(out/'model_summary.csv',index=False); sc.to_csv(out/'confirmation_scored.csv.gz',index=False,compression='gzip'); sd23.to_csv(out/'discovery_2023_scored.csv.gz',index=False,compression='gzip')
    calibration(sc).to_csv(out/'calibration.csv',index=False); thresholds(sc).to_csv(out/'threshold_diagnostics.csv',index=False); subgroup(sc,'destination_role').to_csv(out/'role_diagnostic.csv',index=False); subgroup(sc,'tp_placement').to_csv(out/'tp_placement_diagnostic.csv',index=False); subgroup(sc,'last_response').to_csv(out/'last_response_diagnostic.csv',index=False); touch_bucket(sc).to_csv(out/'touch_bucket_diagnostic.csv',index=False); approach_quintiles(sc).to_csv(out/'approach_speed_quintiles.csv',index=False)
    sc.groupby(['nearest_type','destination_role']).agg(n=('residual_tp15','size'),tp15_rate=('residual_tp15','mean'),ind_ev=('baseline_net_R_1p5','mean')).reset_index().to_csv(out/'destination_type_x_role.csv',index=False); grouped_perm(models['primary'],sc,lab017).to_csv(out/'group_permutation_importance.csv',index=False)
    wk=weekly_auc_diff(sc); wk.to_csv(out/'weekly_auc_diffs.csv',index=False); aucboot=boot_mean(wk['diff'] if len(wk) else [],SEED+2); selboot=selection_gap(sc)
    routed=sc[sc.topology_armed].copy(); rejected=sc[~sc.topology_armed].copy(); base=sc.copy(); r23=sd23[sd23.topology_armed].copy(); sr=parent.build_serial(routed,'BASELINE',1.5); sb=parent.build_serial(base,'BASELINE',1.5); sr2=parent.build_serial(routed,'BASELINE',2.0)
    stats_r=parent.stats(sr,'BASELINE',1.5); stats_b=parent.stats(sb,'BASELINE',1.5); stats_r2=parent.stats(sr2,'BASELINE',2.0); ind_r=parent.stats(routed,'BASELINE',1.5); ind23=parent.stats(r23,'BASELINE',1.5)
    pd.DataFrame([{'split':'CONFIRMATION','router':'ROUTED','portfolio':'INDEPENDENT','target':1.5,**ind_r},{'split':'CONFIRMATION','router':'ROUTED','portfolio':'SERIAL','target':1.5,**stats_r},{'split':'CONFIRMATION','router':'BASELINE','portfolio':'SERIAL','target':1.5,**stats_b},{'split':'CONFIRMATION','router':'ROUTED','portfolio':'SERIAL','target':2.0,**stats_r2},{'split':'DISCOVERY_2023','router':'ROUTED','portfolio':'INDEPENDENT','target':1.5,**ind23}]).to_csv(out/'summary.csv',index=False)
    wb=parent.bootstrap_week_mean(sr,'BASELINE',1.5,SEED) if not sr.empty else {'n_weeks':0,'mean':None,'ci95':[None,None]}; lift=weekly_strategy_diff(sr,sb,SEED+1)
    pm0=pred_metrics(sc,'p_room_baseline'); pm=pred_metrics(sc,'p_topology'); pmo=pred_metrics(sc,'p_topology_only'); pmr=pred_metrics(sc,'p_topology_raw'); pm23=pred_metrics(sd23,'p_topology'); precision=float(routed.residual_tp15.mean()) if len(routed) else np.nan; rejrate=float(rejected.residual_tp15.mean()) if len(rejected) else np.nan; coverage=len(routed)/len(sc) if len(sc) else np.nan; inc=pm['auc']-pm0['auc']
    gates={'G0_DATA_CAUSALITY':bool(hs==exp and violations==0 and (ev.break_time<HOLDOUT).all()),'G1_POWER':bool(len(sc)>=1500 and stats_r.get('n',0)>=250 and stats_r.get('trades_per_week',0)>=2),'G2_TOPOLOGY_RESIDUAL_AUC':bool(pm['auc']>=0.60),'G3_TOPOLOGY_ADDS_OVER_ROOM':bool(inc>=0.03 and aucboot['ci95'][0] is not None and aucboot['ci95'][0]>0),'G4_SELECTION_QUALITY':bool(precision>=0.48 and (precision-rejrate)>=0.12 and selboot['ci95'][0] is not None and selboot['ci95'][0]>0),'G5_CONFIRMATION_EV':bool(stats_r.get('ev',-9)>0 and stats_r.get('pf',0)>1),'G6_WEEK_CLUSTER_CI':bool(wb['ci95'][0] is not None and wb['ci95'][0]>0),'G7_DISCOVERY_TRANSFER':bool(ind23.get('ev',-9)>0 and ind_r.get('ev',-9)>0),'G8_2R_SURVIVAL':bool(stats_r2.get('ev',-9)>=0),'G9_DIRECTION_BREADTH':bool(stats_r.get('buy_ev',-9)>0 and stats_r.get('sell_ev',-9)>0),'G10_PROP_DD_PROXY':bool(stats_r.get('max_dd_R',999)<=20 and stats_r.get('worst_day_R',-999)>-16),'G11_COST_STRESS':bool(stats_r.get('stress10_ev',-9)>0),'G12_ROUTER_LIFT':bool(stats_r.get('ev',-9)>stats_b.get('ev',9) and lift['ci95'][0] is not None and lift['ci95'][0]>0)}
    if not gates['G0_DATA_CAUSALITY']:verdict='INVALID_DATA_CAUSALITY'
    elif all(gates.values()):verdict='DESTINATION_TOPOLOGY_RESIDUAL_EXECUTABLE_EDGE'
    elif all(gates[k] for k in ['G2_TOPOLOGY_RESIDUAL_AUC','G3_TOPOLOGY_ADDS_OVER_ROOM','G4_SELECTION_QUALITY','G5_CONFIRMATION_EV','G6_WEEK_CLUSTER_CI','G7_DISCOVERY_TRANSFER','G12_ROUTER_LIFT']):verdict='DESTINATION_TOPOLOGY_EDGE_NOT_PROP_READY'
    elif gates['G2_TOPOLOGY_RESIDUAL_AUC'] and gates['G3_TOPOLOGY_ADDS_OVER_ROOM'] and gates['G4_SELECTION_QUALITY'] and gates['G5_CONFIRMATION_EV']:verdict='DESTINATION_ROLE_SELECTS_EDGE_WITHOUT_FULL_ROBUSTNESS'
    elif gates['G2_TOPOLOGY_RESIDUAL_AUC'] and gates['G3_TOPOLOGY_ADDS_OVER_ROOM']:verdict='DESTINATION_ROLE_ADDS_INFORMATION_BUT_NO_ECONOMIC_SELECTION'
    else:verdict='NO_DESTINATION_ROLE_RESIDUAL_EDGE'
    result={'lab':LAB,'version':VERSION,'verdict':verdict,'holdout_opened':False,'hashes':{'canonical':hs[0],'break_census':hs[1],'parent_runner':hs[2],'parent_events':hs[3],'lab017_runner':hs[4]},'causality_violations':violations,'confirmation':{'n':len(sc),'room_baseline':pm0,'topology_only':pmo,'topology':pm,'topology_raw':pmr,'auc_increment':inc,'auc_increment_weekly_bootstrap':aucboot,'coverage':coverage,'precision':precision,'rejected_rate':rejrate,'selection_gap':precision-rejrate,'selection_gap_weekly_bootstrap':selboot,'serial_routed_1p5':stats_r,'serial_baseline_1p5':stats_b,'serial_routed_2p0':stats_r2,'weekly_ev_bootstrap':wb,'routed_minus_baseline':lift},'discovery_2023':{'topology':pm23,'routed_independent':ind23},'gates':gates}
    (out/'verdict.json').write_text(json.dumps(result,indent=2,default=str)); (out/'audit.json').write_text(json.dumps({'canonical_last_read_time':str(df.time.max()),'holdout_cutoff':str(HOLDOUT),'causality_violations':violations,'events_total':len(ev),'discovery':len(disc),'confirmation':len(conf),'touch_lookback_min':LOOKBACK,'touch_tolerance_atr':TOUCH_TOL_ATR},indent=2))
    role=subgroup(sc,'destination_role'); place=subgroup(sc,'tp_placement'); dtype=subgroup(sc,'nearest_type'); imp=grouped_perm(models['primary'],sc,lab017)
    lines=[f'# {LAB} — v001 REPORT','',f'**Verdict:** `{verdict}`  ','**Holdout opened:** `false`','', '## OOS residual prediction — Confirmation',f'- N **{len(sc)}**, TP1.5 base rate **{sc.residual_tp15.mean():.3f}**',f'- BIAS_X_ROOM_BASELINE AUC **{pm0["auc"]:.4f}**',f'- DESTINATION_TOPOLOGY_ONLY AUC **{pmo["auc"]:.4f}**',f'- BIAS_X_DESTINATION_TOPOLOGY AUC **{pm["auc"]:.4f}**',f'- TOPOLOGY_PLUS_FIXED_RAW AUC **{pmr["auc"]:.4f}**',f'- topology minus LAB017 baseline **{inc:+.4f}**, weekly CI **{aucboot["ci95"]}**','', '## Primary p>=0.55 selection',f'- coverage **{coverage*100:.2f}%**',f'- TP1.5 precision **{precision*100:.2f}%**',f'- rejected TP1.5 **{rejrate*100:.2f}%**',f'- gap **{(precision-rejrate)*100:+.2f} pp**, weekly CI **{selboot["ci95"]}**','', '## Executable economics — Confirmation / 1.5R / serial',f'- N **{stats_r.get("n",0)}**, trades/week **{stats_r.get("trades_per_week",np.nan):.2f}**',f'- EV **{stats_r.get("ev",np.nan):+.4f}R**, PF **{stats_r.get("pf",np.nan):.3f}**, TP **{stats_r.get("tp_rate",np.nan)*100:.2f}%**',f'- BUY **{stats_r.get("buy_ev",np.nan):+.4f}R**, SELL **{stats_r.get("sell_ev",np.nan):+.4f}R**',f'- max DD **{stats_r.get("max_dd_R",np.nan):.2f}R**, worst day **{stats_r.get("worst_day_R",np.nan):+.2f}R**, stress10 **{stats_r.get("stress10_ev",np.nan):+.4f}R**',f'- weekly EV CI **{wb["ci95"]}**','', '## Baseline / transfer',f'- baseline serial EV **{stats_b.get("ev",np.nan):+.4f}R**, PF **{stats_b.get("pf",np.nan):.3f}**',f'- routed-minus-baseline weekly **{lift["mean"]:+.4f}R**, CI **{lift["ci95"]}**',f'- Discovery-2023 routed independent EV **{ind23.get("ev",np.nan):+.4f}R**',f'- Confirmation routed independent EV **{ind_r.get("ev",np.nan):+.4f}R**',f'- Confirmation 2R serial EV **{stats_r2.get("ev",np.nan):+.4f}R**','', '## Destination roles']
    for rr in role.itertuples(index=False):lines.append(f'- {rr.destination_role}: N {rr.n}, TP1.5 {rr.tp15_rate*100:.2f}%, EV {rr.ind_ev:+.4f}R, mean p {rr.mean_p:.3f}')
    lines+=['','## TP placement']
    for rr in place.itertuples(index=False):lines.append(f'- {rr.tp_placement}: N {rr.n}, TP1.5 {rr.tp15_rate*100:.2f}%, EV {rr.ind_ev:+.4f}R')
    lines+=['','## Destination types']
    for rr in dtype.itertuples(index=False):lines.append(f'- {rr.nearest_type}: N {rr.n}, TP1.5 {rr.tp15_rate*100:.2f}%, EV {rr.ind_ev:+.4f}R')
    lines+=['','## Group permutation importance']
    for rr in imp.itertuples(index=False):lines.append(f'- {rr.group}: AUC drop {rr.auc_drop_mean:+.4f}')
    lines+=['','## Frozen gates']+[f'- {k}: **{"PASS" if v else "FAIL"}**' for k,v in gates.items()]+['','No holdout opening, EA authorization or live allocation is authorized by LAB018.']
    (out/'REPORT.md').write_text('\n'.join(lines)); print(json.dumps(result,indent=2,default=str))

if __name__=='__main__':main()
