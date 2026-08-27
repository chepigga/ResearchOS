#!/usr/bin/env python3
"""XAU_CAUSAL_ADAPTIVE_REGIME_ROUTER_OOS_LAB004 V2.
Walk-forward causal risk gate. Fixes one-class H240 resolver: if all historical
observations resolve, p_resolve is causally fixed to 1 and win-probability model
continues normally.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

SL_ATR=1.25; RR=2.0; H=240; COMMISSION_RATE_SIDE=0.000007
LABEL={"BUY":"BUY_S1.25_R2_H240","SELL":"SELL_S1.25_R2_H240"}
FAV_Q=(0.50,0.60,0.70,0.80,0.90,0.95); HOST_Q=(0.05,0.10,0.20,0.30,0.40,0.50)
MIN_FIT=100; MIN_CAL=30
FEATURES=["atr_pct","atr_ratio_4h","atr_ratio_1d","atr_accel_15","atr_accel_60","prev_range_atr","rv15_atr","rv60_atr","eff15","eff60","tick_ratio_60","spread_ratio_60","spread_atr","trend15_atr","trend60_atr","hour_sin","hour_cos"]

def parse_args():
 p=argparse.ArgumentParser(); p.add_argument('--bars',type=Path,required=True); p.add_argument('--labels',type=Path,required=True); p.add_argument('--outdir',type=Path,required=True); return p.parse_args()

def add_features(d):
 x=d.sort_values('minute').copy(); atr=x.atr14_causal.astype(float); pc=x.mid_close.shift(1).astype(float); pret=x.mid_close.pct_change().shift(1); pac=x.mid_close.diff().abs().shift(1); pr=(x.mid_high.shift(1)-x.mid_low.shift(1)).astype(float); pt=x.tick_count.shift(1).astype(float); ps=x.spread_mean.shift(1).astype(float)
 x['atr_pct']=atr/pc; x['atr_ratio_4h']=atr/atr.rolling(240,min_periods=120).median(); x['atr_ratio_1d']=atr/atr.rolling(1440,min_periods=720).median(); x['atr_accel_15']=atr/atr.shift(15); x['atr_accel_60']=atr/atr.shift(60); x['prev_range_atr']=pr/atr
 x['rv15_atr']=(pret.rolling(15,min_periods=10).std()*pc)/atr; x['rv60_atr']=(pret.rolling(60,min_periods=40).std()*pc)/atr
 for lb in (15,60):
  den=pac.rolling(lb,min_periods=max(10,lb//2)).sum(); x[f'eff{lb}']=(pc-pc.shift(lb)).abs()/den; x[f'trend{lb}_atr']=(pc-pc.shift(lb))/atr
 x['tick_ratio_60']=pt/pt.rolling(60,min_periods=30).median(); x['spread_ratio_60']=ps/ps.rolling(60,min_periods=30).median(); x['spread_atr']=ps/atr
 ts=pd.to_datetime(x.timestamp_from_time_msc); hour=ts.dt.hour+ts.dt.minute/60.; x['hour_sin']=np.sin(2*np.pi*hour/24.); x['hour_cos']=np.cos(2*np.pi*hour/24.); x.replace([np.inf,-np.inf],np.nan,inplace=True); return x

def commission_r(df,side):
 e=df['first_ask' if side=='BUY' else 'first_bid'].to_numpy(float); a=df.atr14_causal.to_numpy(float); return np.divide(2*COMMISSION_RATE_SIDE*e,SL_ATR*a,out=np.full(len(df),np.nan),where=a>0)
def actual_r(df,side):
 lab=df[LABEL[side]].to_numpy(); c=commission_r(df,side); r=np.full(len(df),np.nan); r[lab==1]=RR-c[lab==1]; r[lab==-1]=-1-c[lab==-1]; r[lab==0]=-c[lab==0]; return r

def model(): return Pipeline([('imputer',SimpleImputer(strategy='median')),('scale',StandardScaler()),('lr',LogisticRegression(C=.20,max_iter=1000,solver='lbfgs'))])
def fit_pair(df,side):
 lab=df[LABEL[side]].to_numpy(); valid=np.isin(lab,[-1,0,1])
 if valid.sum()<MIN_FIT:return None
 yres=(lab[valid]!=0).astype(int); u=np.unique(yres)
 if len(u)==1:
  if u[0]!=1:return None
  resolve=None
 else: resolve=model().fit(df.loc[valid,FEATURES],yres)
 res=valid&np.isin(lab,[-1,1]); yw=(lab[res]==1).astype(int)
 if res.sum()<MIN_FIT or len(np.unique(yw))<2:return None
 win=model().fit(df.loc[res,FEATURES],yw); return resolve,win

def score_pair(ms,df,side):
 if ms is None:return np.full(len(df),np.nan)
 resolve,win=ms; X=df[FEATURES]; pres=np.ones(len(df)) if resolve is None else resolve.predict_proba(X)[:,1]; pw=win.predict_proba(X)[:,1]; return pres*((RR+1)*pw-1)-commission_r(df,side)

def choose(fdf,cdf,side,fs,cs):
 fr=actual_r(fdf,side); cr=actual_r(cdf,side); ff=np.isfinite(fs)&np.isfinite(fr); cf=np.isfinite(cs)&np.isfinite(cr); rows=[]; fav=None; host=None
 if ff.sum()<MIN_FIT or cf.sum()<MIN_CAL:return None,None,rows
 for q in FAV_Q:
  th=float(np.quantile(fs[ff],q)); fm=ff&(fs>=th); cm=cf&(cs>=th); fe=float(np.mean(fr[fm])) if fm.sum() else np.nan; ce=float(np.mean(cr[cm])) if cm.sum() else np.nan; rows.append({'kind':'FAVORABLE','q':q,'threshold_fit_model':th,'fit_n':int(fm.sum()),'fit_ev':fe,'cal_n':int(cm.sum()),'cal_ev':ce})
  if fm.sum()>=MIN_FIT and cm.sum()>=MIN_CAL and fe>0 and ce>0:
   key=(min(fe,ce),ce,int(cm.sum())); fav=(key,q) if fav is None or key>fav[0] else fav
 for q in HOST_Q:
  th=float(np.quantile(fs[ff],q)); fm=ff&(fs<=th); cm=cf&(cs<=th); fe=float(np.mean(fr[fm])) if fm.sum() else np.nan; ce=float(np.mean(cr[cm])) if cm.sum() else np.nan; rows.append({'kind':'HOSTILE','q':q,'threshold_fit_model':th,'fit_n':int(fm.sum()),'fit_ev':fe,'cal_n':int(cm.sum()),'cal_ev':ce})
  if fm.sum()>=MIN_FIT and cm.sum()>=MIN_CAL and fe<0 and ce<0:
   key=(max(fe,ce),ce,-int(cm.sum())); host=(key,q) if host is None or key<host[0] else host
 return (fav[1] if fav else None),(host[1] if host else None),rows

def summarize(df,side,state,source):
 if df.empty:return {'source':source,'side':side,'state':state,'n':0}
 lab=df[LABEL[side]].to_numpy(); r=actual_r(df,side); ok=np.isfinite(r); lab=lab[ok]; r=r[ok]; n=len(r); tp=int((lab==1).sum()); sl=int((lab==-1).sum()); none=int((lab==0).sum()); res=tp+sl; wr=tp/res if res else None; m=float(np.mean(r)) if n else None; sd=float(np.std(r,ddof=1)) if n>1 else None; se=sd/math.sqrt(n) if n>1 else None; gp=float(r[r>0].sum()); gl=float(-r[r<0].sum()); pf=gp/gl if gl>0 else None
 return {'source':source,'side':side,'state':state,'n':n,'tp':tp,'sl':sl,'none':none,'resolved_n':res,'resolved_win_rate':wr,'mean_R':m,'mean_R_ci95_low':m-1.96*se if se else None,'mean_R_ci95_high':m+1.96*se if se else None,'profit_factor_R':pf,'none_rate':none/n if n else None}

def main():
 a=parse_args(); a.outdir.mkdir(parents=True,exist_ok=True); b=pd.read_parquet(a.bars); l=pd.read_parquet(a.labels); nb=['minute','mid_close','mid_high','mid_low']; nl=['minute','timestamp_from_time_msc','first_bid','first_ask','atr14_causal','tick_count','spread_mean',LABEL['BUY'],LABEL['SELL']]; d=l[nl].merge(b[nb],on='minute',how='inner',validate='one_to_one').sort_values('minute').reset_index(drop=True); d=add_features(d); ts=pd.to_datetime(d.timestamp_from_time_msc); d['year']=ts.dt.year; d['grid_bucket']=d.minute//H; d['is_grid']=~d.grid_bucket.duplicated()
 start=max(pd.Timestamp('2024-01-01'),ts.min().normalize()+pd.Timedelta(days=365)).to_period('M').to_timestamp(); end=ts.max().to_period('M').to_timestamp(); months=pd.date_range(start,end,freq='MS'); decisions=[]; grids=[]; lives=[]; surf=[]; last={'BUY':-10**18,'SELL':-10**18}
 for m0 in months:
  m1=m0+pd.offsets.MonthBegin(1); tr0=m0-pd.Timedelta(days=365); cal0=m0-pd.Timedelta(days=90); full=(ts>=tr0)&(ts<m0)&d.is_grid; fit=(ts>=tr0)&(ts<cal0)&d.is_grid; cal=(ts>=cal0)&(ts<m0)&d.is_grid; test=(ts>=m0)&(ts<m1)
  if fit.sum()<500 or cal.sum()<100 or test.sum()==0:continue
  fdf=d.loc[fit].reset_index(drop=True); cdf=d.loc[cal].reset_index(drop=True); fulldf=d.loc[full].reset_index(drop=True); tdf=d.loc[test].copy().reset_index(drop=True); tg=tdf[tdf.is_grid].copy().reset_index(drop=True)
  for side in ('BUY','SELL'):
   base=fit_pair(fdf,side)
   if base is None:continue
   fs=score_pair(base,fdf,side); cs=score_pair(base,cdf,side); fq,hq,rows=choose(fdf,cdf,side,fs,cs)
   for row in rows:surf.append({'test_month':str(m0.date()),'side':side,**row})
   fm=fit_pair(fulldf,side)
   if fm is None:continue
   trscore=score_pair(fm,fulldf,side); finite=np.isfinite(trscore); fth=float(np.quantile(trscore[finite],fq)) if fq is not None and finite.any() else None; hth=float(np.quantile(trscore[finite],hq)) if hq is not None and finite.any() else None
   gs=score_pair(fm,tg,side); state=np.full(len(tg),'NEUTRAL',object)
   if hth is not None:state[gs<=hth]='HOSTILE'
   if fth is not None:state[gs>=fth]='FAVORABLE'
   tg2=tg.copy(); tg2['router_state']=state; tg2['router_score']=gs; tg2['router_side']=side; grids.append(tg2)
   alls=score_pair(fm,tdf,side); favmask=np.isfinite(alls)&(alls>=fth) if fth is not None else np.zeros(len(tdf),bool); chosen=[]
   for i in np.flatnonzero(favmask):
    minute=int(tdf.loc[i,'minute'])
    if minute>=last[side]+H: chosen.append(i); last[side]=minute
   if chosen:
    z=tdf.loc[chosen].copy(); z['router_score']=alls[chosen]; z['router_state']='FAVORABLE'; z['router_side']=side; lives.append(z)
   decisions.append({'test_month':str(m0.date()),'side':side,'train_start':str(tr0.date()),'train_end':str(m0.date()),'fit_grid_n':int(fit.sum()),'cal_grid_n':int(cal.sum()),'full_grid_n':int(full.sum()),'favorable_q':fq,'hostile_q':hq,'favorable_threshold':fth,'hostile_threshold':hth,'favorable_enabled':fq is not None,'hostile_enabled':hq is not None,'resolver_mode':'MODEL' if fm[0] is not None else 'CONSTANT_ONE'})
 dec=pd.DataFrame(decisions); dec.to_csv(a.outdir/'monthly_router_decisions.csv',index=False); pd.DataFrame(surf).to_csv(a.outdir/'inner_selection_surface.csv',index=False); grid=pd.concat(grids,ignore_index=True) if grids else pd.DataFrame(); live=pd.concat(lives,ignore_index=True) if lives else pd.DataFrame()
 if not grid.empty:grid.to_parquet(a.outdir/'router_grid_oos.parquet',index=False)
 if not live.empty:live.to_parquet(a.outdir/'router_live_favorable_events.parquet',index=False)
 S=[]; Y=[]
 if not grid.empty:
  for side in ('BUY','SELL'):
   g=grid[grid.router_side==side]; S.append(summarize(g,side,'ALL_GRID','GRID'))
   for st in ('FAVORABLE','NEUTRAL','HOSTILE'):S.append(summarize(g[g.router_state==st],side,st,'GRID'))
   for y in sorted(g.year.unique()):
    yy=g[g.year==y]
    for st in ('FAVORABLE','NEUTRAL','HOSTILE'):Y.append({'year':int(y),**summarize(yy[yy.router_state==st],side,st,'GRID')})
 if not live.empty:
  for side in ('BUY','SELL'):
   z=live[live.router_side==side]; S.append(summarize(z,side,'FAVORABLE','LIVE_GATE'))
   for y in sorted(z.year.unique()):Y.append({'year':int(y),**summarize(z[z.year==y],side,'FAVORABLE','LIVE_GATE')})
 S=pd.DataFrame(S); Y=pd.DataFrame(Y); S.to_csv(a.outdir/'router_summary.csv',index=False); Y.to_csv(a.outdir/'router_yearly_summary.csv',index=False)
 sv={}
 for side in ('BUY','SELL'):
  z=S[(S.side==side)&(S.source=='LIVE_GATE')] if not S.empty else pd.DataFrame(); yy=Y[(Y.side==side)&(Y.source=='LIVE_GATE')] if not Y.empty else pd.DataFrame()
  if z.empty or int(z.iloc[0].get('n',0))<50:sv[side]={'status':'NO_USABLE_FAVORABLE_GATE','n':0 if z.empty else int(z.iloc[0].n)}; continue
  r=z.iloc[0]; u=yy[yy.n>=20]; py=int((u.mean_R>0).sum()) if not u.empty else 0; yrs=len(u); strong=r.n>=150 and r.mean_R>0 and r.mean_R_ci95_low>0 and yrs>=2 and py==yrs; weak=r.n>=100 and r.mean_R>0 and yrs>=2 and py>=max(2,yrs-1); sv[side]={'status':'PASS_STRONG_ROUTER' if strong else ('PASS_WEAK_ROUTER' if weak else 'FAIL_ROUTER'),'favorable_n':int(r.n),'favorable_mean_R':float(r.mean_R),'favorable_ci95_low':float(r.mean_R_ci95_low) if pd.notna(r.mean_R_ci95_low) else None,'favorable_PF_R':float(r.profit_factor_R) if pd.notna(r.profit_factor_R) else None,'positive_years':py,'usable_years':int(yrs)}
 status='PROMOTE_ROUTER' if any(v['status']=='PASS_STRONG_ROUTER' for v in sv.values()) else ('REPLICATE_WEAK_ROUTER' if any(v['status']=='PASS_WEAK_ROUTER' for v in sv.values()) else 'REJECT_ROUTER_V2'); verdict={'lab':'XAU_CAUSAL_ADAPTIVE_REGIME_ROUTER_OOS_LAB004','build':'V2_DEGENERATE_RESOLVER_FIX','status':status,'purpose':'adaptive risk gate FAVORABLE/NEUTRAL/HOSTILE; not standalone entry','target':{'sl_atr':SL_ATR,'tp_R':RR,'horizon_min':H},'walk_forward':'rolling 12m; ~9m fit + 90d calibration; next month pure OOS; monthly refit','features':FEATURES,'future_leakage_guard':'features end t-1 or known clock at t; every model/threshold uses dates before OOS month','resolution_guard':'one-class RESOLVED => p_resolve=1','tail_sample_guard':{'min_fit':MIN_FIT,'min_cal':MIN_CAL},'none_handling':'NONE=-commission; ambiguous/censored excluded','side_verdicts':sv}; (a.outdir/'verdict.json').write_text(json.dumps(verdict,indent=2)); print('===== SUMMARY ====='); print(S.to_string(index=False)); print('===== YEARLY ====='); print(Y.to_string(index=False)); print('===== DECISIONS ====='); print(dec.to_string(index=False)); print('===== VERDICT ====='); print(json.dumps(verdict,indent=2))
if __name__=='__main__':main()
