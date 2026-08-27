#!/usr/bin/env python3
"""XAU_CAUSAL_ADAPTIVE_REGIME_ROUTER_OOS_LAB004

Walk-forward causal market-regime router for the fixed LAB001 barrier target.
This is a risk gate, not a trading setup generator.

Target: BUY/SELL independently, SL=1.25 ATR, TP=2R, H=240m.
Protocol for every OOS calendar month from 2024 onward:
  - rolling 12m history only
  - first ~9m: fit two regularized logistic models
  - last 90d: choose only a FAVORABLE/HOSTILE score percentile
  - require the selected percentile to have the same EV sign in fit + calibration
  - refit on the full past 12m
  - freeze model + percentile for the next month
  - current/future month labels are never used by the router

The two-stage model estimates:
  P(resolve within H | state) and P(TP first | resolved,state)
and combines them into an expected-R routing score.
NONE is conservatively valued as -commission (flat time-exit assumption).
Ambiguous/censored labels are excluded from evaluation.
"""
from __future__ import annotations

import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

SL_ATR=1.25
RR=2.0
H=240
COMMISSION_RATE_SIDE=0.000007
LABEL={"BUY":"BUY_S1.25_R2_H240","SELL":"SELL_S1.25_R2_H240"}
FAV_Q=(0.50,0.60,0.70,0.80,0.90,0.95)
HOST_Q=(0.05,0.10,0.20,0.30,0.40,0.50)
MIN_FIT=250
MIN_CAL=40

FEATURES=[
    "atr_pct","atr_ratio_4h","atr_ratio_1d","atr_accel_15","atr_accel_60",
    "prev_range_atr","rv15_atr","rv60_atr","eff15","eff60",
    "tick_ratio_60","spread_ratio_60","spread_atr","trend15_atr","trend60_atr",
    "hour_sin","hour_cos",
]


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--bars',type=Path,required=True)
    p.add_argument('--labels',type=Path,required=True)
    p.add_argument('--outdir',type=Path,required=True)
    return p.parse_args()


def add_features(d: pd.DataFrame) -> pd.DataFrame:
    x=d.sort_values('minute').copy()
    atr=x['atr14_causal'].astype(float)
    prev_close=x['mid_close'].shift(1).astype(float)
    prev_ret=x['mid_close'].pct_change().shift(1)
    prev_abs_change=x['mid_close'].diff().abs().shift(1)
    prev_range=(x['mid_high'].shift(1)-x['mid_low'].shift(1)).astype(float)
    prev_ticks=x['tick_count'].shift(1).astype(float)
    prev_spread=x['spread_mean'].shift(1).astype(float)

    x['atr_pct']=atr/prev_close
    x['atr_ratio_4h']=atr/atr.rolling(240,min_periods=120).median()
    x['atr_ratio_1d']=atr/atr.rolling(1440,min_periods=720).median()
    x['atr_accel_15']=atr/atr.shift(15)
    x['atr_accel_60']=atr/atr.shift(60)
    x['prev_range_atr']=prev_range/atr

    # Prior realized variation only. At observation t these windows end at t-1.
    x['rv15_atr']=(prev_ret.rolling(15,min_periods=10).std()*prev_close)/atr
    x['rv60_atr']=(prev_ret.rolling(60,min_periods=40).std()*prev_close)/atr
    for lb in (15,60):
        denom=prev_abs_change.rolling(lb,min_periods=max(10,lb//2)).sum()
        x[f'eff{lb}']=(prev_close-prev_close.shift(lb)).abs()/denom
        x[f'trend{lb}_atr']=(prev_close-prev_close.shift(lb))/atr

    x['tick_ratio_60']=prev_ticks/prev_ticks.rolling(60,min_periods=30).median()
    x['spread_ratio_60']=prev_spread/prev_spread.rolling(60,min_periods=30).median()
    x['spread_atr']=prev_spread/atr

    ts=pd.to_datetime(x['timestamp_from_time_msc'])
    hour=ts.dt.hour+ts.dt.minute/60.0
    x['hour_sin']=np.sin(2*np.pi*hour/24.0)
    x['hour_cos']=np.cos(2*np.pi*hour/24.0)
    x.replace([np.inf,-np.inf],np.nan,inplace=True)
    return x


def commission_r(df: pd.DataFrame, side: str) -> np.ndarray:
    entry=df['first_ask' if side=='BUY' else 'first_bid'].to_numpy(float)
    atr=df['atr14_causal'].to_numpy(float)
    return np.divide(2.0*COMMISSION_RATE_SIDE*entry,SL_ATR*atr,
                     out=np.full(len(df),np.nan),where=atr>0)


def actual_r(df: pd.DataFrame, side: str) -> np.ndarray:
    lab=df[LABEL[side]].to_numpy()
    c=commission_r(df,side)
    r=np.full(len(df),np.nan)
    r[lab==1]=RR-c[lab==1]
    r[lab==-1]=-1.0-c[lab==-1]
    r[lab==0]=-c[lab==0]
    return r


def make_model() -> Pipeline:
    return Pipeline([
        ('imputer',SimpleImputer(strategy='median')),
        ('scale',StandardScaler()),
        ('lr',LogisticRegression(C=0.20,max_iter=1000,solver='lbfgs')),
    ])


def fit_pair(df: pd.DataFrame, side: str):
    lab=df[LABEL[side]].to_numpy()
    valid=np.isin(lab,[-1,0,1])
    if valid.sum()<MIN_FIT:
        return None
    X=df.loc[valid,FEATURES]
    y_res=(lab[valid]!=0).astype(int)
    if len(np.unique(y_res))<2:
        return None
    resolve=make_model().fit(X,y_res)
    resolved=valid & np.isin(lab,[-1,1])
    if resolved.sum()<MIN_FIT or len(np.unique((lab[resolved]==1).astype(int)))<2:
        return None
    win=make_model().fit(df.loc[resolved,FEATURES],(lab[resolved]==1).astype(int))
    return resolve,win


def score_pair(models, df: pd.DataFrame, side: str) -> np.ndarray:
    if models is None:
        return np.full(len(df),np.nan)
    resolve,win=models
    X=df[FEATURES]
    p_res=resolve.predict_proba(X)[:,1]
    p_win=win.predict_proba(X)[:,1]
    c=commission_r(df,side)
    return p_res*((RR+1.0)*p_win-1.0)-c


def clean_eval(df: pd.DataFrame, side: str, mask: np.ndarray):
    r=actual_r(df,side)
    valid=mask & np.isfinite(r)
    return r[valid]


def mean_ev(df,side,mask):
    r=clean_eval(df,side,mask)
    return (float(np.mean(r)),len(r)) if len(r) else (None,0)


def choose_quantiles(fit_df,cal_df,side,fit_score,cal_score):
    fav=None; host=None
    fit_r=actual_r(fit_df,side); cal_r=actual_r(cal_df,side)
    finite_fit=np.isfinite(fit_score)&np.isfinite(fit_r)
    finite_cal=np.isfinite(cal_score)&np.isfinite(cal_r)
    if finite_fit.sum()<MIN_FIT or finite_cal.sum()<MIN_CAL:
        return fav,host,[]
    rows=[]
    for q in FAV_Q:
        thr=float(np.quantile(fit_score[finite_fit],q))
        fm=finite_fit&(fit_score>=thr); cm=finite_cal&(cal_score>=thr)
        fe=float(np.mean(fit_r[fm])) if fm.sum() else np.nan
        ce=float(np.mean(cal_r[cm])) if cm.sum() else np.nan
        rows.append({'kind':'FAVORABLE','q':q,'threshold_fit_model':thr,'fit_n':int(fm.sum()),'fit_ev':fe,'cal_n':int(cm.sum()),'cal_ev':ce})
        if fm.sum()>=MIN_FIT and cm.sum()>=MIN_CAL and fe>0 and ce>0:
            key=(min(fe,ce),ce,cm.sum())
            if fav is None or key>fav[0]: fav=(key,q)
    for q in HOST_Q:
        thr=float(np.quantile(fit_score[finite_fit],q))
        fm=finite_fit&(fit_score<=thr); cm=finite_cal&(cal_score<=thr)
        fe=float(np.mean(fit_r[fm])) if fm.sum() else np.nan
        ce=float(np.mean(cal_r[cm])) if cm.sum() else np.nan
        rows.append({'kind':'HOSTILE','q':q,'threshold_fit_model':thr,'fit_n':int(fm.sum()),'fit_ev':fe,'cal_n':int(cm.sum()),'cal_ev':ce})
        if fm.sum()>=MIN_FIT and cm.sum()>=MIN_CAL and fe<0 and ce<0:
            key=(max(fe,ce),ce,-cm.sum())  # more negative max() is better
            if host is None or key<host[0]: host=(key,q)
    return (fav[1] if fav else None),(host[1] if host else None),rows


def summarize(df,side,state,source):
    if df.empty:
        return {'source':source,'side':side,'state':state,'n':0}
    lab=df[LABEL[side]].to_numpy(); r=actual_r(df,side); ok=np.isfinite(r); r=r[ok]; lab=lab[ok]
    n=len(r); tp=int(np.sum(lab==1)); sl=int(np.sum(lab==-1)); none=int(np.sum(lab==0)); res=tp+sl
    wr=tp/res if res else None
    m=float(np.mean(r)) if n else None; sd=float(np.std(r,ddof=1)) if n>1 else None
    se=(sd/math.sqrt(n)) if n>1 else None
    lo=(m-1.96*se) if se is not None else None; hi=(m+1.96*se) if se is not None else None
    gp=float(np.sum(r[r>0])); gl=float(-np.sum(r[r<0])); pf=(gp/gl if gl>0 else None)
    return {'source':source,'side':side,'state':state,'n':n,'tp':tp,'sl':sl,'none':none,
            'resolved_n':res,'resolved_win_rate':wr,'mean_R':m,'mean_R_ci95_low':lo,'mean_R_ci95_high':hi,
            'profit_factor_R':pf,'none_rate':(none/n if n else None)}


def main():
    a=parse_args(); a.outdir.mkdir(parents=True,exist_ok=True)
    bars=pd.read_parquet(a.bars)
    labels=pd.read_parquet(a.labels)
    needb=['minute','mid_close','mid_high','mid_low']
    needl=['minute','timestamp_from_time_msc','first_bid','first_ask','atr14_causal','tick_count','spread_mean',LABEL['BUY'],LABEL['SELL']]
    d=labels[needl].merge(bars[needb],on='minute',how='inner',validate='one_to_one').sort_values('minute').reset_index(drop=True)
    d=add_features(d)
    ts=pd.to_datetime(d['timestamp_from_time_msc'])
    d['month']=ts.dt.to_period('M').astype(str)
    d['year']=ts.dt.year
    d['grid_bucket']=d['minute']//H
    d['is_grid']=~d['grid_bucket'].duplicated()

    start=max(pd.Timestamp('2024-01-01'),ts.min().normalize()+pd.Timedelta(days=365))
    start=start.to_period('M').to_timestamp()
    end=ts.max().to_period('M').to_timestamp()
    months=pd.date_range(start,end,freq='MS')

    decisions=[]; grid_parts=[]; live_parts=[]; selection_surface=[]
    last_trade={'BUY':-10**18,'SELL':-10**18}

    for m0 in months:
        m1=m0+pd.offsets.MonthBegin(1)
        tr0=m0-pd.Timedelta(days=365)
        cal0=m0-pd.Timedelta(days=90)
        full=(ts>=tr0)&(ts<m0)&d['is_grid']
        fit=(ts>=tr0)&(ts<cal0)&d['is_grid']
        cal=(ts>=cal0)&(ts<m0)&d['is_grid']
        test=(ts>=m0)&(ts<m1)
        if fit.sum()<500 or cal.sum()<100 or test.sum()==0: continue
        full_df=d.loc[full].reset_index(drop=True); fit_df=d.loc[fit].reset_index(drop=True); cal_df=d.loc[cal].reset_index(drop=True)
        test_df=d.loc[test].copy().reset_index(drop=True)
        test_grid=test_df[test_df['is_grid']].copy().reset_index(drop=True)

        for side in ('BUY','SELL'):
            base_models=fit_pair(fit_df,side)
            if base_models is None: continue
            fs=score_pair(base_models,fit_df,side); cs=score_pair(base_models,cal_df,side)
            fav_q,host_q,surf=choose_quantiles(fit_df,cal_df,side,fs,cs)
            for row in surf: selection_surface.append({'test_month':str(m0.date()),'side':side,**row})

            full_models=fit_pair(full_df,side)
            if full_models is None: continue
            train_score=score_pair(full_models,full_df,side)
            finite=np.isfinite(train_score)
            fav_thr=float(np.quantile(train_score[finite],fav_q)) if fav_q is not None and finite.any() else None
            host_thr=float(np.quantile(train_score[finite],host_q)) if host_q is not None and finite.any() else None

            gscore=score_pair(full_models,test_grid,side)
            state=np.full(len(test_grid),'NEUTRAL',dtype=object)
            if host_thr is not None: state[gscore<=host_thr]='HOSTILE'
            if fav_thr is not None: state[gscore>=fav_thr]='FAVORABLE'
            test_grid['router_state']=state; test_grid['router_score']=gscore
            test_grid['router_side']=side; grid_parts.append(test_grid.copy())

            # Live-like gate: scan every minute, take first FAVORABLE state after a 240m cooldown.
            allscore=score_pair(full_models,test_df,side)
            favmask=np.zeros(len(test_df),bool)
            if fav_thr is not None: favmask=np.isfinite(allscore)&(allscore>=fav_thr)
            chosen=[]
            for i in np.flatnonzero(favmask):
                minute=int(test_df.loc[i,'minute'])
                if minute>=last_trade[side]+H:
                    chosen.append(i); last_trade[side]=minute
            if chosen:
                z=test_df.loc[chosen].copy(); z['router_score']=allscore[chosen]; z['router_state']='FAVORABLE'; z['router_side']=side; live_parts.append(z)

            decisions.append({'test_month':str(m0.date()),'side':side,'train_start':str(tr0.date()),'train_end':str(m0.date()),
                              'fit_grid_n':int(fit.sum()),'cal_grid_n':int(cal.sum()),'full_grid_n':int(full.sum()),
                              'favorable_q':fav_q,'hostile_q':host_q,'favorable_threshold':fav_thr,'hostile_threshold':host_thr,
                              'favorable_enabled':fav_q is not None,'hostile_enabled':host_q is not None})

    dec=pd.DataFrame(decisions); dec.to_csv(a.outdir/'monthly_router_decisions.csv',index=False)
    pd.DataFrame(selection_surface).to_csv(a.outdir/'inner_selection_surface.csv',index=False)
    grid=pd.concat(grid_parts,ignore_index=True) if grid_parts else pd.DataFrame()
    live=pd.concat(live_parts,ignore_index=True) if live_parts else pd.DataFrame()
    if not grid.empty: grid.to_parquet(a.outdir/'router_grid_oos.parquet',index=False)
    if not live.empty: live.to_parquet(a.outdir/'router_live_favorable_events.parquet',index=False)

    summaries=[]; yearly=[]
    if not grid.empty:
        for side in ('BUY','SELL'):
            gs=grid[grid['router_side']==side]
            summaries.append(summarize(gs,side,'ALL_GRID','GRID'))
            for st in ('FAVORABLE','NEUTRAL','HOSTILE'):
                summaries.append(summarize(gs[gs['router_state']==st],side,st,'GRID'))
            for y in sorted(gs['year'].unique()):
                yy=gs[gs['year']==y]
                for st in ('FAVORABLE','NEUTRAL','HOSTILE'):
                    yearly.append({'year':int(y),**summarize(yy[yy['router_state']==st],side,st,'GRID')})
    if not live.empty:
        for side in ('BUY','SELL'):
            ls=live[live['router_side']==side]
            summaries.append(summarize(ls,side,'FAVORABLE','LIVE_GATE'))
            for y in sorted(ls['year'].unique()): yearly.append({'year':int(y),**summarize(ls[ls['year']==y],side,'FAVORABLE','LIVE_GATE')})

    S=pd.DataFrame(summaries); Y=pd.DataFrame(yearly)
    S.to_csv(a.outdir/'router_summary.csv',index=False); Y.to_csv(a.outdir/'router_yearly_summary.csv',index=False)

    side_verdict={}
    for side in ('BUY','SELL'):
        z=S[(S['side']==side)&(S['source']=='LIVE_GATE')] if not S.empty else pd.DataFrame()
        yy=Y[(Y['side']==side)&(Y['source']=='LIVE_GATE')] if not Y.empty else pd.DataFrame()
        if z.empty or int(z.iloc[0].get('n',0))<50:
            side_verdict[side]={'status':'NO_USABLE_FAVORABLE_GATE','n':0 if z.empty else int(z.iloc[0]['n'])}; continue
        r=z.iloc[0]; usable=yy[yy['n']>=20] if not yy.empty else yy
        pos_years=int((usable['mean_R']>0).sum()) if not usable.empty else 0; years=int(len(usable))
        strong=(r['n']>=150 and r['mean_R']>0 and r['mean_R_ci95_low']>0 and years>=2 and pos_years==years)
        weak=(r['n']>=100 and r['mean_R']>0 and years>=2 and pos_years>=max(2,years-1))
        side_verdict[side]={'status':'PASS_STRONG_ROUTER' if strong else ('PASS_WEAK_ROUTER' if weak else 'FAIL_ROUTER'),
                            'favorable_n':int(r['n']),'favorable_mean_R':float(r['mean_R']),
                            'favorable_ci95_low':float(r['mean_R_ci95_low']) if pd.notna(r['mean_R_ci95_low']) else None,
                            'favorable_PF_R':float(r['profit_factor_R']) if pd.notna(r['profit_factor_R']) else None,
                            'positive_years':pos_years,'usable_years':years}

    status='PROMOTE_ROUTER' if any(v['status']=='PASS_STRONG_ROUTER' for v in side_verdict.values()) else ('REPLICATE_WEAK_ROUTER' if any(v['status']=='PASS_WEAK_ROUTER' for v in side_verdict.values()) else 'REJECT_ROUTER_V1')
    verdict={'lab':'XAU_CAUSAL_ADAPTIVE_REGIME_ROUTER_OOS_LAB004','status':status,
             'purpose':'adaptive risk gate FAVORABLE/NEUTRAL/HOSTILE; not a standalone entry pattern',
             'target':{'sl_atr':SL_ATR,'tp_R':RR,'horizon_min':H},
             'walk_forward':'rolling 12m; first ~9m model fit + last 90d percentile selection; next month pure OOS; monthly refit',
             'features':FEATURES,
             'future_leakage_guard':'all state features end at t-1 or are known clock variables at t; all thresholds/models use only dates before each OOS month',
             'none_handling':'NONE valued as -commission (flat time-exit approximation); ambiguous/censored excluded',
             'side_verdicts':side_verdict,
             'next_step':'If promoted: freeze router mechanics and test barrier geometry/cost stress plus event-entry engines inside FAVORABLE only. If rejected: simplify/replace state representation rather than mining entry patterns.'}
    (a.outdir/'verdict.json').write_text(json.dumps(verdict,indent=2),encoding='utf-8')
    print('===== ROUTER SUMMARY ====='); print(S.to_string(index=False) if not S.empty else 'EMPTY')
    print('===== YEARLY ====='); print(Y.to_string(index=False) if not Y.empty else 'EMPTY')
    print('===== MONTHLY DECISIONS ====='); print(dec.to_string(index=False) if not dec.empty else 'EMPTY')
    print('===== VERDICT ====='); print(json.dumps(verdict,indent=2))

if __name__=='__main__': main()
