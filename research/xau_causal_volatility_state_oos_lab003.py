#!/usr/bin/env python3
"""XAU_CAUSAL_VOLATILITY_STATE_OOS_LAB003

Single-family causal test of volatility state using LAB001 M1 bars + labels.
Protocol:
- 2023: fit feature thresholds only
- 2024: internal model/config selection only
- 2025: untouched validation
- 2026: final OOS
Canonical target is fixed: SL=1.25 ATR, TP=2R, horizon=240m, cooldown=240m.
Features are strictly causal at t and use only completed information available by t.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd

SL_ATR=1.25; RR=2.0; H=240; COOLDOWN=240
COMMISSION_RATE_SIDE=0.000007
LABEL={"BUY":"BUY_S1.25_R2_H240","SELL":"SELL_S1.25_R2_H240"}
QUANTS=(0.50,0.60,0.70,0.80,0.90,0.95,0.975,0.99)


def args():
    p=argparse.ArgumentParser(); p.add_argument('--bars',type=Path,required=True); p.add_argument('--labels',type=Path,required=True); p.add_argument('--outdir',type=Path,required=True); return p.parse_args()

def wilson(k,n,z=1.96):
    if n<=0:return (None,None)
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den; return c-h,c+h

def decluster(mask,minutes):
    out=np.zeros(len(mask),bool); last=-10**18
    for i in np.flatnonzero(mask):
        m=int(minutes[i])
        if m>=last+COOLDOWN: out[i]=True; last=m
    return out

def add_features(d):
    x=d.copy(); atr=x['atr14_causal'].astype(float); px=x['mid_close'].shift(1).astype(float)
    # All inputs here are known at observation time t. atr14_causal itself was shifted in LAB001.
    x['atr_pct']=atr/px
    x['atr_ratio_4h']=atr/atr.rolling(240,min_periods=120).median()
    x['atr_ratio_1d']=atr/atr.rolling(1440,min_periods=720).median()
    x['atr_accel_15']=atr/atr.shift(15)
    x['atr_accel_60']=atr/atr.shift(60)
    # prior completed M1 range state, normalized by causal ATR
    prev_range=(x['mid_high'].shift(1)-x['mid_low'].shift(1))
    x['prev_range_atr']=prev_range/atr
    return x

def split_masks(t):
    t=pd.to_datetime(t)
    return {
      'FIT_2023':(t<pd.Timestamp('2024-01-01')),
      'SELECT_2024':((t>=pd.Timestamp('2024-01-01'))&(t<pd.Timestamp('2025-01-01'))),
      'VALID_2025':((t>=pd.Timestamp('2025-01-01'))&(t<pd.Timestamp('2026-01-01'))),
      'OOS_2026':(t>=pd.Timestamp('2026-01-01')),
    }

def metrics(df,side,raw,split):
    lab=df[LABEL[side]].to_numpy(); mins=df['minute'].to_numpy(np.int64); sel=decluster(raw,mins)
    res=sel & np.isin(lab,[-1,1]); n=int(sel.sum()); nr=int(res.sum()); tp=int(np.sum(sel&(lab==1))); sl=int(np.sum(sel&(lab==-1))); none=int(np.sum(sel&(lab==0))); amb=int(np.sum(sel&(lab==2)))
    wr=tp/nr if nr else None; lo,hi=wilson(tp,nr)
    entry=df['first_ask' if side=='BUY' else 'first_bid'].to_numpy(float); atr=df['atr14_causal'].to_numpy(float)
    cr=np.divide(2*COMMISSION_RATE_SIDE*entry,SL_ATR*atr,out=np.full_like(entry,np.nan),where=atr>0)
    cm=float(np.nanmean(cr[res])) if nr else None; be=((1+cm)/(1+RR)) if cm is not None else None; ev=(wr*RR-(1-wr)-cm) if wr is not None and cm is not None else None
    span=max(1e-9,(pd.to_datetime(df['timestamp_from_time_msc']).max()-pd.to_datetime(df['timestamp_from_time_msc']).min()).total_seconds()/(365.25*86400))
    return {'split':split,'side':side,'selected_n':n,'resolved_n':nr,'tp':tp,'sl':sl,'none':none,'ambiguous':amb,'resolved_win_rate':wr,'wr_ci95_low':lo,'wr_ci95_high':hi,'mean_commission_R':cm,'breakeven_win_rate_after_commission':be,'EV_R_after_commission':ev,'events_per_year':n/span}

def main():
    a=args(); a.outdir.mkdir(parents=True,exist_ok=True)
    b=pd.read_parquet(a.bars); l=pd.read_parquet(a.labels)
    needb=['minute','mid_close','mid_high','mid_low']; needl=['minute','timestamp_from_time_msc','first_bid','first_ask','atr14_causal',LABEL['BUY'],LABEL['SELL']]
    d=l[needl].merge(b[needb],on='minute',how='inner',validate='one_to_one').sort_values('minute').reset_index(drop=True)
    d=add_features(d); masks=split_masks(d['timestamp_from_time_msc']); fit=masks['FIT_2023'].to_numpy(bool)
    features=['atr_pct','atr_ratio_4h','atr_ratio_1d','atr_accel_15','atr_accel_60','prev_range_atr']
    surface=[]; locked=[]; yearly=[]; selected={}
    for side in ('BUY','SELL'):
        cand=[]
        for feat in features:
            v=d[feat].to_numpy(float); vf=v[fit & np.isfinite(v)]
            if len(vf)<10000: continue
            for mode in ('HIGH','LOW'):
                for q in QUANTS:
                    thr=float(np.quantile(vf,q if mode=='HIGH' else 1-q))
                    raw=np.isfinite(v) & ((v>=thr) if mode=='HIGH' else (v<=thr))
                    per={}
                    for sn,sm in masks.items():
                        ix=sm.to_numpy(bool); m=metrics(d.loc[ix].reset_index(drop=True),side,raw[ix],sn); surface.append({'feature':feat,'mode':mode,'fit_quantile':q,'threshold':thr,**m}); per[sn]=m
                    f=per['FIT_2023']; s=per['SELECT_2024']
                    # Candidate must not be negative in FIT and must have enough independent events in both years.
                    if f['resolved_n']>=150 and s['resolved_n']>=150 and f['EV_R_after_commission'] is not None and s['EV_R_after_commission'] is not None and f['EV_R_after_commission']>0:
                        cand.append((s['EV_R_after_commission'],min(f['resolved_n'],s['resolved_n']),feat,mode,q,thr))
        if not cand:
            selected[side]=None; continue
        cand.sort(key=lambda z:(z[0],z[1]),reverse=True); _,_,feat,mode,q,thr=cand[0]
        selected[side]={'feature':feat,'mode':mode,'fit_quantile':q,'threshold':thr}
        v=d[feat].to_numpy(float); raw=np.isfinite(v)&((v>=thr) if mode=='HIGH' else (v<=thr))
        for sn,sm in masks.items():
            ix=sm.to_numpy(bool); locked.append({**selected[side],**metrics(d.loc[ix].reset_index(drop=True),side,raw[ix],sn)})
        yrs=pd.to_datetime(d['timestamp_from_time_msc']).dt.year
        for y in sorted(yrs.unique()):
            ix=(yrs==y).to_numpy(bool); yearly.append({**selected[side],**metrics(d.loc[ix].reset_index(drop=True),side,raw[ix],str(y))})
    pd.DataFrame(surface).to_csv(a.outdir/'feature_surface.csv',index=False); L=pd.DataFrame(locked); Y=pd.DataFrame(yearly); L.to_csv(a.outdir/'locked_oos_summary.csv',index=False); Y.to_csv(a.outdir/'locked_yearly_summary.csv',index=False)
    verdict_side={}
    for side in ('BUY','SELL'):
        z=L[L.side==side] if not L.empty else pd.DataFrame()
        if z.empty: verdict_side[side]={'status':'NO_ROBUST_2023_2024_CANDIDATE'}; continue
        f=z[z.split=='FIT_2023'].iloc[0]; s=z[z.split=='SELECT_2024'].iloc[0]; v=z[z.split=='VALID_2025'].iloc[0]; o=z[z.split=='OOS_2026'].iloc[0]
        strong=(v.resolved_n>=30 and o.resolved_n>=30 and v.EV_R_after_commission>0 and o.EV_R_after_commission>0 and v.wr_ci95_low>v.breakeven_win_rate_after_commission and o.wr_ci95_low>o.breakeven_win_rate_after_commission)
        weak=(v.resolved_n>=30 and o.resolved_n>=30 and v.EV_R_after_commission>0 and o.EV_R_after_commission>0)
        verdict_side[side]={'status':'PASS_STRONG_OOS' if strong else ('PASS_WEAK_OOS' if weak else 'FAIL_OOS'),'locked_config':selected[side],'fit_2023_EV_R':float(f.EV_R_after_commission),'select_2024_EV_R':float(s.EV_R_after_commission),'validation_2025_EV_R':float(v.EV_R_after_commission),'oos_2026_EV_R':float(o.EV_R_after_commission),'validation_2025_n':int(v.resolved_n),'oos_2026_n':int(o.resolved_n)}
    statuses=[x.get('status','') for x in verdict_side.values()]; status='PROMOTE_FAMILY' if 'PASS_STRONG_OOS' in statuses else ('WEAK_REPLICATE_ONLY' if 'PASS_WEAK_OOS' in statuses else 'REJECT_FAMILY_AS_STANDALONE')
    verdict={'lab':'XAU_CAUSAL_VOLATILITY_STATE_OOS_LAB003','family':'causal volatility state only','target':{'sl_atr':SL_ATR,'rr':RR,'horizon_min':H,'cooldown_min':COOLDOWN},'protocol':'2023 fit thresholds -> 2024 select one config/side -> 2025 untouched validation -> 2026 final OOS','features':features,'side_verdicts':verdict_side,'status':status,'next_step':'If promoted, freeze exact rule and stress costs/execution. If rejected, move to another single causal family; do not combine failed volatility states.'}
    (a.outdir/'selected_configs.json').write_text(json.dumps(selected,indent=2)); (a.outdir/'verdict.json').write_text(json.dumps(verdict,indent=2))
    print('===== LOCKED ====='); print(L.to_string(index=False) if not L.empty else 'EMPTY'); print('===== YEARLY ====='); print(Y.to_string(index=False) if not Y.empty else 'EMPTY'); print('===== VERDICT ====='); print(json.dumps(verdict,indent=2))
if __name__=='__main__': main()
