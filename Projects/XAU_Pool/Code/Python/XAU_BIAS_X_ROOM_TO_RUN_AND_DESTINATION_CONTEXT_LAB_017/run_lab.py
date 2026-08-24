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

LAB='XAU_BIAS_X_ROOM_TO_RUN_AND_DESTINATION_CONTEXT_LAB_017'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
BREAK_SHA='c9cba1459a60ef9c3bb308e751ebae95840f48a24f94754808862a180832ccdb'
PARENT_RUNNER_SHA='09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a'
PARENT_EVENTS_SHA='83be6298befc9c016c7aec297d3e48a3040258c6d070bae25af4e3c3c11481c2'
DISC_END=pd.Timestamp('2024-01-01'); HOLDOUT=pd.Timestamp('2025-07-01'); P_GATE=0.55; OPEN_SPACE_CAP=5.0; MAX_T=35; BOOT_N=4000; SEED=20260824; TP15_ATR=0.75
LEVELS=('MID','HIGH','LOW')
BIAS_CAT=['level','digestion_state']
BIAS_NUM=['p_accept','elapsed_min','x_decision','peak_x_since_break','spent_from_break_atr','peak_spent_atr','drawdown_from_peak_atr','path_efficiency','elapsed_per_atr']
ROOM_CAT=['nearest_type']
ROOM_NUM=['room_vwap_atr','exists_vwap','room_prev_session_atr','exists_prev_session','room_current_session_atr','exists_current_session','room_m15_atr','exists_m15','room_h1_atr','exists_h1','nearest_room_atr','nearest_room_R','clearance_vs_tp15_atr','known_levels_inside_tp15','known_levels_inside_1p5atr','open_space_0p75','open_space_1p5','prev_session_range_pos','current_session_range_pos','m15_4h_range_pos','h1_24h_range_pos','m15_dir_to_roll_extreme_atr','h1_dir_to_roll_extreme_atr','m15_ema20_dist_atr','m15_ema20_slope4_atr','h1_ema20_dist_atr','h1_ema20_slope4_atr','m15_structure_score','h1_structure_score']
RAW_NUM=[]
for t in range(1,MAX_T+1): RAW_NUM += [f'x_t{t}',f'ret_t{t}',f'dd_t{t}',f'body_t{t}',f'mask_t{t}']

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def load_module(path:Path):
    sp=importlib.util.spec_from_file_location('lab012_parent',path); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
def load_parent_events(path:Path)->pd.DataFrame:
    x=pd.read_csv(path,compression='gzip')
    for c in ['break_time','digestion_end_time','baseline_entry_time','baseline_exit_time_1p5','baseline_exit_time_2p0','lifecycle_end_time']:
        if c in x: x[c]=pd.to_datetime(x[c],errors='coerce')
    z=x[(x.strong_accept.astype(bool))&(x.digestion_found.astype(bool))&(x.baseline_entry_i>=0)&(~x.causality_violation.astype(bool))&(x.break_time<HOLDOUT)].copy(); z=z[z.baseline_outcome_1p5.notna()].copy(); z['residual_tp15']=(z.baseline_outcome_1p5=='TP').astype(int); z['residual_tp20']=(z.baseline_outcome_2p0=='TP').astype(int); return z.reset_index(drop=True)
def make_tf_bars(df:pd.DataFrame,tf:str):
    mins=15 if tf=='15min' else 60
    b=df.set_index('time').resample(tf,label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index(); b['avail']=b['time']+pd.Timedelta(minutes=mins); b['ema20']=b['close'].ewm(span=20,adjust=False,min_periods=20).mean(); b['ema_slope4']=b['ema20']-b['ema20'].shift(4); look=16 if mins==15 else 24; b['roll_high']=b['high'].rolling(look,min_periods=look).max(); b['roll_low']=b['low'].rolling(look,min_periods=look).min(); b['range_pos']=(b['close']-b['roll_low'])/(b['roll_high']-b['roll_low']).replace(0,np.nan)
    ph=np.zeros(len(b),bool); pl=np.zeros(len(b),bool); h=b.high.to_numpy(float); l=b.low.to_numpy(float)
    for i in range(2,len(b)-2): ph[i]=h[i]>=np.max(h[i-2:i+3]); pl[i]=l[i]<=np.min(l[i-2:i+3])
    piv=[]
    for i in range(2,len(b)-2):
        conf=b.at[i+2,'avail']
        if ph[i]: piv.append({'pivot_time':b.at[i,'time'],'confirm_time':conf,'price':h[i],'kind':'HIGH'})
        if pl[i]: piv.append({'pivot_time':b.at[i,'time'],'confirm_time':conf,'price':l[i],'kind':'LOW'})
    piv=pd.DataFrame(piv)
    if len(piv): piv=piv.sort_values(['confirm_time','pivot_time']).reset_index(drop=True)
    return b,piv
def last_completed_row(bars,decision):
    arr=bars['avail'].to_numpy(dtype='datetime64[ns]'); j=np.searchsorted(arr,np.datetime64(decision),side='right')-1; return int(j) if j>=0 else -1
def nearest_ahead(prices,close,d,a):
    vals=[d*(float(p)-close)/a for p in prices if p is not None and np.isfinite(p) and d*(float(p)-close)/a>1e-12]; return min(vals) if vals else np.nan
def swing_context(piv,decision,close,d,a,lookback_days):
    if piv is None or piv.empty: return np.nan,0,0.0
    q=piv[(piv.confirm_time<=decision)&(piv.pivot_time>=decision-pd.Timedelta(days=lookback_days))]
    if q.empty: return np.nan,0,0.0
    dist=d*(q.price.to_numpy(float)-close)/a; pos=dist[dist>1e-12]; room=float(pos.min()) if len(pos) else np.nan
    hs=q[q.kind=='HIGH'].sort_values('pivot_time').tail(2).price.to_numpy(float); ls=q[q.kind=='LOW'].sort_values('pivot_time').tail(2).price.to_numpy(float); score=0.0
    if len(hs)==2 and len(ls)==2:
        up=(hs[-1]>hs[-2]) and (ls[-1]>ls[-2]); dn=(hs[-1]<hs[-2]) and (ls[-1]<ls[-2]); score=(1.0 if up else (-1.0 if dn else 0.0))*d
    return room,1 if np.isfinite(room) else 0,float(score)
def add_features(ev,df):
    close=df.close.to_numpy(float); op=df.open.to_numpy(float); lines={lev:df[lev].to_numpy(float) for lev in LEVELS}; run_hi=df.groupby('session').high.cummax().to_numpy(float); run_lo=df.groupby('session').low.cummin().to_numpy(float); ss=df.groupby('session').agg(sess_high=('high','max'),sess_low=('low','min')).sort_index(); ss['prev_high']=ss.sess_high.shift(1); ss['prev_low']=ss.sess_low.shift(1); prev_map=ss[['prev_high','prev_low']]; m15,p15=make_tf_bars(df,'15min'); h1,p60=make_tf_bars(df,'60min'); rows=[]; violations=0
    for r in ev.itertuples(index=False):
        bi=int(r.break_i); de=int(r.digestion_end_i); ent=int(r.baseline_entry_i); a=float(r.atr0); d=int(r.dir)
        if de<bi+1 or de>=len(df) or ent<=de or not np.isfinite(a) or a<=0: violations+=1; continue
        dec=pd.Timestamp(df.at[de,'time']); c=float(close[de]); bc=float(close[bi]); line=lines[str(r.level)]; idx=np.arange(bi+1,de+1); lv=line[idx]
        if dec>=HOLDOUT or not np.isfinite(lv).all(): violations+=1; continue
        x=d*(close[idx]-lv)/a; peakx=float(np.max(x)); xdec=float(x[-1]); spent=float(d*(c-bc)/a); dir_prices=d*(close[idx]-bc)/a; peakspent=float(np.max(dir_prices)); dd=float(peakx-xdec); pathabs=float(np.abs(np.diff(np.r_[bc,close[idx]])).sum()/a); eff=float(abs(spent)/pathabs) if pathabs>1e-12 else 0.0; elapsed=int(de-bi); elapsed_per=float(elapsed/max(abs(peakspent),0.25))
        ses=df.at[de,'session']; prev=prev_map.loc[ses] if ses in prev_map.index else pd.Series({'prev_high':np.nan,'prev_low':np.nan}); prevh=float(prev.prev_high) if np.isfinite(prev.prev_high) else np.nan; prevl=float(prev.prev_low) if np.isfinite(prev.prev_low) else np.nan; curh=float(run_hi[de]); curl=float(run_lo[de])
        room_v=nearest_ahead([float(df.at[de,lev]) for lev in LEVELS if lev!=str(r.level)],c,d,a); room_ps=nearest_ahead([prevh,prevl],c,d,a); room_cs=nearest_ahead([curh,curl],c,d,a); room15,ex15,score15=swing_context(p15,dec,c,d,a,5); room60,ex60,score60=swing_context(p60,dec,c,d,a,20)
        cand=[]
        for name,val in [('VWAP',room_v),('PREV_SESSION',room_ps),('CURRENT_SESSION',room_cs),('M15_SWING',room15),('H1_SWING',room60)]:
            if np.isfinite(val) and val>0: cand.append((name,float(val)))
        if cand: nearest_type,nearest=min(cand,key=lambda z:z[1])
        else: nearest_type,nearest='OPEN_SPACE',OPEN_SPACE_CAP
        known_inside=sum(1 for _,v in cand if v<=TP15_ATR); known_inside15=sum(1 for _,v in cand if v<=1.50); prevpos=(c-prevl)/(prevh-prevl) if np.isfinite(prevh) and np.isfinite(prevl) and prevh>prevl else np.nan; curpos=(c-curl)/(curh-curl) if curh>curl else np.nan
        j15=last_completed_row(m15,dec); j60=last_completed_row(h1,dec)
        def tfvals(b,j):
            if j<0: return (np.nan,)*4
            row=b.iloc[j]; rp=float(row.range_pos) if np.isfinite(row.range_pos) else np.nan; ext=float(row.roll_high if d>0 else row.roll_low) if np.isfinite(row.roll_high if d>0 else row.roll_low) else np.nan; dext=float(d*(ext-c)/a) if np.isfinite(ext) else np.nan; ed=float(d*(c-float(row.ema20))/a) if np.isfinite(row.ema20) else np.nan; sl=float(d*float(row.ema_slope4)/a) if np.isfinite(row.ema_slope4) else np.nan; return rp,dext,ed,sl
        rp15,exr15,ema15,sl15=tfvals(m15,j15); rp60,exr60,ema60,sl60=tfvals(h1,j60)
        rec=r._asdict(); rec.update({'residual_tp15':int(r.baseline_outcome_1p5=='TP'),'residual_tp20':int(r.baseline_outcome_2p0=='TP'),'elapsed_min':elapsed,'x_decision':xdec,'peak_x_since_break':peakx,'spent_from_break_atr':spent,'peak_spent_atr':peakspent,'drawdown_from_peak_atr':dd,'path_efficiency':eff,'elapsed_per_atr':elapsed_per,'room_vwap_atr':room_v,'exists_vwap':int(np.isfinite(room_v)),'room_prev_session_atr':room_ps,'exists_prev_session':int(np.isfinite(room_ps)),'room_current_session_atr':room_cs,'exists_current_session':int(np.isfinite(room_cs)),'room_m15_atr':room15,'exists_m15':ex15,'room_h1_atr':room60,'exists_h1':ex60,'nearest_room_atr':nearest,'nearest_room_R':2*nearest,'nearest_type':nearest_type,'clearance_vs_tp15_atr':nearest-TP15_ATR,'known_levels_inside_tp15':known_inside,'known_levels_inside_1p5atr':known_inside15,'open_space_0p75':int(known_inside==0),'open_space_1p5':int(known_inside15==0),'prev_session_range_pos':prevpos,'current_session_range_pos':curpos,'m15_4h_range_pos':rp15,'h1_24h_range_pos':rp60,'m15_dir_to_roll_extreme_atr':exr15,'h1_dir_to_roll_extreme_atr':exr60,'m15_ema20_dist_atr':ema15,'m15_ema20_slope4_atr':sl15,'h1_ema20_dist_atr':ema60,'h1_ema20_slope4_atr':sl60,'m15_structure_score':score15,'h1_structure_score':score60,'feature_max_i':de,'feature_max_time':dec,'feature_causality_violation':bool(de>=ent)})
        prevclose=np.r_[close[bi],close[bi+1:de]]; rets=d*(close[idx]-prevclose)/a; dds=np.maximum.accumulate(x)-x; bodies=d*(close[idx]-op[idx])/a
        for t in range(1,MAX_T+1):
            q=t-1; obs=q<len(idx); rec[f'x_t{t}']=float(x[q]) if obs else 0.0; rec[f'ret_t{t}']=float(rets[q]) if obs else 0.0; rec[f'dd_t{t}']=float(dds[q]) if obs else 0.0; rec[f'body_t{t}']=float(bodies[q]) if obs else 0.0; rec[f'mask_t{t}']=1.0 if obs else 0.0
        rows.append(rec)
    return pd.DataFrame(rows),violations
def make_model(cat,num):
    pre=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=np.float32),cat),('num','passthrough',num)],remainder='drop',sparse_threshold=0.0); clf=HistGradientBoostingClassifier(learning_rate=0.05,max_iter=200,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=1.0,max_bins=64,early_stopping=False,random_state=SEED); return Pipeline([('pre',pre),('clf',clf)])
def fit_prob(train,test,cat,num,pcol):
    m=make_model(cat,num); m.fit(train[cat+num],train.residual_tp15.astype(int)); z=test.copy(); z[pcol]=m.predict_proba(z[cat+num])[:,1]; return m,z
def score_all(train,test):
    mb,b=fit_prob(train,test,BIAS_CAT,BIAS_NUM,'p_bias_location'); mr,r=fit_prob(train,test,ROOM_CAT,ROOM_NUM,'p_room_only'); cat=BIAS_CAT+ROOM_CAT; num=BIAS_NUM+ROOM_NUM; mx,x=fit_prob(train,test,cat,num,'p_bias_x_room'); mz,z=fit_prob(train,test,cat,num+RAW_NUM,'p_bias_x_room_raw'); out=b.copy(); out['p_room_only']=r.p_room_only.to_numpy(); out['p_bias_x_room']=x.p_bias_x_room.to_numpy(); out['p_bias_x_room_raw']=z.p_bias_x_room_raw.to_numpy(); out['room_armed']=out.p_bias_x_room>=P_GATE; return {'bias':mb,'room':mr,'primary':mx,'raw':mz},out
def auc(y,p): return float(roc_auc_score(y,p)) if pd.Series(y).nunique()>1 else np.nan
def pred_metrics(z,pcol):
    y=z.residual_tp15.astype(int); p=z[pcol].astype(float); return {'n':int(len(z)),'base_rate':float(y.mean()),'auc':auc(y,p),'brier':float(brier_score_loss(y,p)),'logloss':float(log_loss(y,np.clip(p,1e-8,1-1e-8),labels=[0,1]))}
def boot_mean(a,seed):
    a=np.asarray(pd.Series(a).dropna(),float)
    if len(a)<8:return {'n':int(len(a)),'mean':float(a.mean()) if len(a) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(a,size=len(a),replace=True).mean() for _ in range(BOOT_N)]); return {'n':int(len(a)),'mean':float(a.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}
def weekly_auc_diff(z):
    q=z.copy(); q['week']=q.break_time.dt.to_period('W-MON').astype(str); rows=[]
    for w,g in q.groupby('week'):
        if len(g)>=20 and g.residual_tp15.nunique()>1: rows.append({'week':w,'diff':auc(g.residual_tp15,g.p_bias_x_room)-auc(g.residual_tp15,g.p_bias_location)})
    return pd.DataFrame(rows)
def selection_gap(z):
    q=z.copy(); q['week']=q.break_time.dt.to_period('W-MON').astype(str); vals=[]
    for _,g in q.groupby('week'):
        a=g[g.room_armed].residual_tp15; b=g[~g.room_armed].residual_tp15
        if len(a)>=5 and len(b)>=5: vals.append(a.mean()-b.mean())
    return boot_mean(vals,SEED+3)
def calibration(z):
    q=z.copy(); q['rank']=q.p_bias_x_room.rank(method='first',pct=True); q['quintile']=pd.cut(q['rank'],[0,.2,.4,.6,.8,1],labels=['Q1','Q2','Q3','Q4','Q5'],include_lowest=True); return q.groupby('quintile',observed=True).agg(n=('residual_tp15','size'),mean_p=('p_bias_x_room','mean'),actual_tp15=('residual_tp15','mean'),ev=('baseline_net_R_1p5','mean')).reset_index()
def clear_room_diag(z): return z.groupby('open_space_0p75').agg(n=('residual_tp15','size'),tp15_rate=('residual_tp15','mean'),ind_ev=('baseline_net_R_1p5','mean'),mean_nearest_room_atr=('nearest_room_atr','mean')).reset_index().rename(columns={'open_space_0p75':'clear_room'})
def nearest_diag(z): return z.groupby('nearest_type').agg(n=('residual_tp15','size'),tp15_rate=('residual_tp15','mean'),ind_ev=('baseline_net_R_1p5','mean'),mean_room=('nearest_room_atr','mean')).reset_index().sort_values('n',ascending=False)
def grouped_perm(model,z,groups):
    X=z[BIAS_CAT+ROOM_CAT+BIAS_NUM+ROOM_NUM].copy(); base=auc(z.residual_tp15,model.predict_proba(X)[:,1]); rng=np.random.default_rng(SEED); rows=[]
    for name,cols in groups.items():
        vals=[]
        for _ in range(5):
            xp=X.copy(); perm=rng.permutation(len(xp))
            for c in cols:
                if c in xp: xp[c]=xp[c].to_numpy()[perm]
            vals.append(base-auc(z.residual_tp15,model.predict_proba(xp)[:,1]))
        rows.append({'group':name,'auc_drop_mean':float(np.mean(vals)),'auc_drop_sd':float(np.std(vals))})
    return pd.DataFrame(rows).sort_values('auc_drop_mean',ascending=False)
def weekly_strategy_diff(a,b):
    def wm(x):
        if x is None or x.empty:return pd.Series(dtype=float)
        q=x.copy(); q['week']=pd.to_datetime(q.baseline_entry_time).dt.to_period('W-MON').astype(str); return q.groupby('week').baseline_net_R_1p5.mean()
    wa,wb=wm(a),wm(b); idx=wa.index.union(wb.index); return boot_mean((wa.reindex(idx,fill_value=0)-wb.reindex(idx,fill_value=0)).to_numpy(float),SEED+1)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--canonical',type=Path,required=True); ap.add_argument('--break-census',type=Path,required=True); ap.add_argument('--parent-runner',type=Path,required=True); ap.add_argument('--parent-events',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    ch,bh,rh,eh=sha256(a.canonical),sha256(a.break_census),sha256(a.parent_runner),sha256(a.parent_events)
    if (ch,bh,rh,eh)!=(CANONICAL_SHA,BREAK_SHA,PARENT_RUNNER_SHA,PARENT_EVENTS_SHA): raise RuntimeError('hash mismatch')
    parent=load_module(a.parent_runner); df=parent.add_atr_vwap(parent.load_prices(a.canonical)); pe=load_parent_events(a.parent_events); ev,featviol=add_features(pe,df); violations=int(featviol+ev.feature_causality_violation.astype(bool).sum()+ev.causality_violation.astype(bool).sum()); disc=ev[ev.break_time<DISC_END].copy(); conf=ev[(ev.break_time>=DISC_END)&(ev.break_time<HOLDOUT)].copy(); models,sc=score_all(disc,conf); dtrain=disc[disc.break_time<pd.Timestamp('2023-01-01')].copy(); d23=disc[(disc.break_time>=pd.Timestamp('2023-01-01'))&(disc.break_time<DISC_END)].copy(); _,sd23=score_all(dtrain,d23)
    pairs=[('BIAS_LOCATION','p_bias_location'),('ROOM_DESTINATION_ONLY','p_room_only'),('BIAS_X_ROOM','p_bias_x_room'),('BIAS_X_ROOM_PLUS_FIXED_RAW','p_bias_x_room_raw')]; pd.DataFrame([{'split':s,'model':n,**pred_metrics(z,p)} for s,z in [('DISCOVERY_2023',sd23),('CONFIRMATION',sc)] for n,p in pairs]).to_csv(out/'model_summary.csv',index=False); sc.to_csv(out/'confirmation_scored.csv.gz',index=False,compression='gzip'); sd23.to_csv(out/'discovery_2023_scored.csv.gz',index=False,compression='gzip'); calibration(sc).to_csv(out/'calibration.csv',index=False); clear_room_diag(sc).to_csv(out/'clear_room_diagnostic.csv',index=False); nearest_diag(sc).to_csv(out/'nearest_destination_diagnostic.csv',index=False)
    wk=weekly_auc_diff(sc); wk.to_csv(out/'weekly_auc_diffs.csv',index=False); aucboot=boot_mean(wk['diff'] if len(wk) else [],SEED+2); selboot=selection_gap(sc); groups={'BIAS_LOCATION':BIAS_NUM+BIAS_CAT,'VWAP_ROOM':['room_vwap_atr','exists_vwap'],'SESSION_ROOM':['room_prev_session_atr','exists_prev_session','room_current_session_atr','exists_current_session','prev_session_range_pos','current_session_range_pos'],'ROOM_AGGREGATE':['nearest_room_atr','nearest_room_R','clearance_vs_tp15_atr','known_levels_inside_tp15','known_levels_inside_1p5atr','open_space_0p75','open_space_1p5','nearest_type'],'M15_ROOM':['room_m15_atr','exists_m15','m15_4h_range_pos','m15_dir_to_roll_extreme_atr'],'H1_ROOM':['room_h1_atr','exists_h1','h1_24h_range_pos','h1_dir_to_roll_extreme_atr'],'M15_STRUCTURE':['m15_ema20_dist_atr','m15_ema20_slope4_atr','m15_structure_score'],'H1_STRUCTURE':['h1_ema20_dist_atr','h1_ema20_slope4_atr','h1_structure_score']}; grouped_perm(models['primary'],sc,groups).to_csv(out/'group_permutation_importance.csv',index=False)
    routed=sc[sc.room_armed].copy(); rejected=sc[~sc.room_armed].copy(); base=sc.copy(); r23=sd23[sd23.room_armed].copy(); sr=parent.build_serial(routed,'BASELINE',1.5); sb=parent.build_serial(base,'BASELINE',1.5); sr2=parent.build_serial(routed,'BASELINE',2.0); stats_r=parent.stats(sr,'BASELINE',1.5); stats_b=parent.stats(sb,'BASELINE',1.5); stats_r2=parent.stats(sr2,'BASELINE',2.0); ind_r=parent.stats(routed,'BASELINE',1.5); ind23=parent.stats(r23,'BASELINE',1.5); wb=parent.bootstrap_week_mean(sr,'BASELINE',1.5,SEED) if not sr.empty else {'n_weeks':0,'mean':None,'ci95':[None,None]}; lift=weekly_strategy_diff(sr,sb)
    pm_bias=pred_metrics(sc,'p_bias_location'); pm_room=pred_metrics(sc,'p_room_only'); pm=pred_metrics(sc,'p_bias_x_room'); pm_raw=pred_metrics(sc,'p_bias_x_room_raw'); precision=float(routed.residual_tp15.mean()) if len(routed) else np.nan; rejrate=float(rejected.residual_tp15.mean()) if len(rejected) else np.nan; coverage=len(routed)/len(sc); seqdiff=pm['auc']-pm_bias['auc']; gates={'G0_DATA_CAUSALITY':violations==0,'G1_POWER':len(sc)>=1500 and stats_r.get('n',0)>=250 and stats_r.get('trades_per_week',0)>=2,'G2_ROOM_RESIDUAL_AUC':pm['auc']>=0.60,'G3_ROOM_ADDS_OVER_LOCATION':seqdiff>=0.03 and aucboot['ci95'][0] is not None and aucboot['ci95'][0]>0,'G4_SELECTION_QUALITY':precision>=0.48 and (precision-rejrate)>=0.12 and selboot['ci95'][0] is not None and selboot['ci95'][0]>0,'G5_CONFIRMATION_EV':stats_r.get('ev',-9)>0 and stats_r.get('pf',0)>1,'G6_WEEK_CLUSTER_CI':wb['ci95'][0] is not None and wb['ci95'][0]>0,'G7_DISCOVERY_TRANSFER':ind23.get('ev',-9)>0 and ind_r.get('ev',-9)>0,'G8_2R_SURVIVAL':stats_r2.get('ev',-9)>=0,'G9_DIRECTION_BREADTH':stats_r.get('buy_ev',-9)>0 and stats_r.get('sell_ev',-9)>0,'G10_PROP_DD_PROXY':stats_r.get('max_dd_R',999)<=20 and stats_r.get('worst_day_R',-999)>-16,'G11_COST_STRESS':stats_r.get('stress10_ev',-9)>0,'G12_ROUTER_LIFT':stats_r.get('ev',-9)>stats_b.get('ev',9) and lift['ci95'][0] is not None and lift['ci95'][0]>0}
    if not gates['G0_DATA_CAUSALITY']: verdict='INVALID_DATA_CAUSALITY'
    elif all(gates.values()): verdict='BIAS_X_ROOM_RESIDUAL_EXECUTABLE_EDGE'
    elif gates['G2_ROOM_RESIDUAL_AUC'] and gates['G3_ROOM_ADDS_OVER_LOCATION'] and gates['G4_SELECTION_QUALITY'] and not gates['G5_CONFIRMATION_EV']: verdict='ROOM_CONTEXT_PREDICTS_RESIDUAL_BUT_EXECUTION_FAILS'
    elif gates['G2_ROOM_RESIDUAL_AUC'] and gates['G3_ROOM_ADDS_OVER_LOCATION'] and gates['G4_SELECTION_QUALITY'] and gates['G5_CONFIRMATION_EV']: verdict='ROOM_CONTEXT_SELECTS_EDGE_WITHOUT_FULL_ROBUSTNESS'
    elif gates['G2_ROOM_RESIDUAL_AUC'] and gates['G3_ROOM_ADDS_OVER_LOCATION']: verdict='ROOM_CONTEXT_ADDS_INFORMATION_BUT_NO_ECONOMIC_SELECTION'
    else: verdict='NO_BIAS_X_ROOM_RESIDUAL_EDGE'
    result={'lab':LAB,'version':VERSION,'verdict':verdict,'holdout_opened':False,'causality_violations':violations,'confirmation':{'n':len(sc),'bias_location':pm_bias,'room_only':pm_room,'bias_x_room':pm,'bias_x_room_raw':pm_raw,'auc_increment':seqdiff,'auc_increment_weekly_bootstrap':aucboot,'coverage':coverage,'precision':precision,'rejected_rate':rejrate,'selection_gap':precision-rejrate,'selection_gap_weekly_bootstrap':selboot,'serial_routed_1p5':stats_r,'serial_baseline_1p5':stats_b,'serial_routed_2p0':stats_r2,'weekly_ev_bootstrap':wb,'routed_minus_baseline':lift},'discovery_2023':{'bias_x_room':pred_metrics(sd23,'p_bias_x_room'),'routed_independent':ind23},'gates':gates}; (out/'verdict.json').write_text(json.dumps(result,indent=2,default=str)); (out/'audit.json').write_text(json.dumps({'canonical_last_read_time':str(df.time.max()),'holdout_cutoff':str(HOLDOUT),'causality_violations':violations,'events_total':len(ev),'discovery':len(disc),'confirmation':len(conf),'open_space_cap_atr':OPEN_SPACE_CAP},indent=2)); print(json.dumps(result,indent=2,default=str))
if __name__=='__main__': main()
