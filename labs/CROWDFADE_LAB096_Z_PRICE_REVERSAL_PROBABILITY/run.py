from pathlib import Path
import json, zipfile, numpy as np, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, log_loss

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
BARS_DIR=ROOT/'data'/'all_1m'
SRC=ROOT.parent/'CROWDFADE_LAB095_CAUSAL_Z_TRAJECTORY'/'output'/'trajectory_features.csv'

TARGETS=[0.5,1.0,1.5]
HOLD_MIN=120
FEATURES=[
 'abs_z','z_signed_crowd','dls','doi','rejectATR',
 'traj_prominence','traj_pullback','traj_peak_age_min','traj_pre_slope_per_min',
 'price_ret_5R','price_ret_15R','price_ret_30R',
 'price_turn_15R','price_turn_30R','price_range_15R','price_range_30R'
]

def load_bars():
    rows=[]
    for zp in sorted(BARS_DIR.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
        q.columns=['open_ms','open','high','low','close']
        q['ts']=(pd.to_numeric(q.open_ms,errors='coerce')//1000).astype('Int64')
        for c in ['open','high','low','close']: q[c]=pd.to_numeric(q[c],errors='coerce')
        q=q.dropna().copy(); q['ts']=q.ts.astype(np.int64)
        rows.append(q[['ts','open','high','low','close']])
    return pd.concat(rows,ignore_index=True).sort_values('ts').drop_duplicates('ts').reset_index(drop=True)

def idx_at_or_before(tsa,t):
    return int(np.searchsorted(tsa,t,'right')-1)

def price_features(row,bars,tsa):
    t=int(row.ts); sd=int(row.side); atr=float(row.atr)
    j=idx_at_or_before(tsa,t-60)
    if j<35 or atr<=0:return None
    c=float(bars.close.iloc[j])
    out={}
    for m in [5,15,30]:
        k=idx_at_or_before(tsa,t-m*60-60)
        if k<0:return None
        out[f'price_ret_{m}R']=sd*(c-float(bars.close.iloc[k]))/atr
        seg=bars.iloc[k:j+1]
        if sd>0:
            turn=(c-float(seg.low.min()))/atr
        else:
            turn=(float(seg.high.max())-c)/atr
        out[f'price_turn_{m}R']=turn
        out[f'price_range_{m}R']=(float(seg.high.max())-float(seg.low.min()))/atr
    return out

def label_targets(row,bars,tsa):
    t=int(row.ts); sd=int(row.side); atr=float(row.atr)
    k=int(np.searchsorted(tsa,t,'left'))
    if k>=len(bars):return None
    ep=float(bars.open.iloc[k]); sl=ep-sd*atr
    e=int(np.searchsorted(tsa,t+HOLD_MIN*60,'right'))
    hit={r:0 for r in TARGETS}; alive=True
    for q in range(k,min(e,len(bars))):
        hi=float(bars.high.iloc[q]); lo=float(bars.low.iloc[q])
        hs=(lo<=sl) if sd>0 else (hi>=sl)
        # same-bar ambiguity conservative: stop wins
        if hs: break
        for r in TARGETS:
            if not hit[r]:
                tp=ep+sd*r*atr
                ht=(hi>=tp) if sd>0 else (lo<=tp)
                if ht: hit[r]=1
    return {f'y_{str(r).replace(".","p")}R':hit[r] for r in TARGETS}

def period(ts):
    y=pd.to_datetime(ts,unit='s',utc=True).year
    if y<=2024:return 'train_2021_24'
    if y==2025:return 'validation_2025'
    return 'diagnostic_2026'

def metrics(y,p):
    if len(np.unique(y))<2:return {'N':len(y),'base_rate':float(np.mean(y)),'brier':np.nan,'auc':np.nan,'logloss':np.nan}
    return {'N':len(y),'base_rate':float(np.mean(y)),
            'brier':float(brier_score_loss(y,p)),
            'auc':float(roc_auc_score(y,p)),
            'logloss':float(log_loss(y,p,labels=[0,1]))}

def bins(df,pcol,ycol):
    edges=[0,.5,.55,.6,.65,.7,.75,.8,.85,.9,1.000001]
    labs=['<50','50-55','55-60','60-65','65-70','70-75','75-80','80-85','85-90','90+']
    z=df.copy()
    z['prob_bin']=pd.cut(z[pcol],bins=edges,labels=labs,right=False,include_lowest=True)
    return z.groupby('prob_bin',observed=True).agg(
        N=(ycol,'size'),mean_pred=(pcol,'mean'),actual=(ycol,'mean')
    ).reset_index()

def main():
    feat=pd.read_csv(SRC)
    feat=feat[feat.lookback_min==30].copy()
    feat['rejectATR']=-feat['price_crowd_R']
    feat['z_signed_crowd']=feat['abs_z']  # crowd-direction magnitude by construction

    bars=load_bars(); tsa=bars.ts.to_numpy(np.int64)
    prows=[]; lrows=[]
    for _,r in feat.iterrows():
        pf=price_features(r,bars,tsa)
        lb=label_targets(r,bars,tsa)
        if pf is None or lb is None: continue
        d=r.to_dict(); d.update(pf); d.update(lb); d['period']=period(int(r.ts))
        prows.append(d)
    d=pd.DataFrame(prows)
    d=d.replace([np.inf,-np.inf],np.nan).dropna(subset=FEATURES).reset_index(drop=True)
    d.to_csv(OUT/'probability_dataset.csv',index=False)

    coeff_rows=[]; metric_rows=[]; pred_frames=[]; bin_frames=[]
    for sd,name in [(1,'BUY'),(-1,'SELL')]:
      ds=d[d.side==sd].copy()
      tr=ds[ds.period=='train_2021_24'].copy()
      for R in TARGETS:
        ycol=f'y_{str(R).replace(".","p")}R'
        pipe=Pipeline([('scaler',StandardScaler()),('lr',LogisticRegression(C=0.5,max_iter=500,class_weight=None))])
        pipe.fit(tr[FEATURES],tr[ycol].astype(int))
        scaler=pipe.named_steps['scaler']; lr=pipe.named_steps['lr']
        for f,mu,sc,co in zip(FEATURES,scaler.mean_,scaler.scale_,lr.coef_[0]):
            coeff_rows.append({'side':name,'target_R':R,'feature':f,'mean':mu,'scale':sc,'coef':co,'intercept':lr.intercept_[0]})
        for per in ['train_2021_24','validation_2025','diagnostic_2026']:
            q=ds[ds.period==per].copy()
            if len(q)==0: continue
            p=pipe.predict_proba(q[FEATURES])[:,1]
            q[f'prob_{R}R']=p
            m=metrics(q[ycol].astype(int).to_numpy(),p)
            metric_rows.append({'side':name,'target_R':R,'period':per,**m})
            bb=bins(q,f'prob_{R}R',ycol); bb['side']=name;bb['target_R']=R;bb['period']=per
            bin_frames.append(bb)
            pred_frames.append(q[['dataset','ts','side','period',ycol]].assign(target_R=R,probability=p))
    pd.DataFrame(coeff_rows).to_csv(OUT/'model_coefficients.csv',index=False)
    met=pd.DataFrame(metric_rows); met.to_csv(OUT/'model_metrics.csv',index=False)
    cal=pd.concat(bin_frames,ignore_index=True); cal.to_csv(OUT/'probability_calibration_bins.csv',index=False)
    preds=pd.concat(pred_frames,ignore_index=True); preds.to_csv(OUT/'predictions.csv',index=False)

    # Practical indicator thresholds: evaluate target +1R probability buckets on validation and 2026.
    p1=preds[preds.target_R==1.0].copy()
    practical=[]
    for sd,name in [(1,'BUY'),(-1,'SELL')]:
      for th in [0.50,0.55,0.60,0.65,0.70,0.75]:
        for per in ['validation_2025','diagnostic_2026']:
            q=p1[(p1.side==sd)&(p1.period==per)&(p1.probability>=th)]
            practical.append({'side':name,'threshold':th,'period':per,'N':len(q),
                              'actual_hit_rate_1R':float(q['y_1p0R'].mean()) if len(q) else np.nan,
                              'mean_pred':float(q.probability.mean()) if len(q) else np.nan})
    pd.DataFrame(practical).to_csv(OUT/'indicator_threshold_check.csv',index=False)

    summary={
      'lab':'LAB096_Z_TRAJECTORY_X_PRICE_REVERSAL_PROBABILITY',
      'universe':'LAB089 non-Z base candidates from LAB095 30m trajectory dataset; no fixed |Z| gate.',
      'features':FEATURES,
      'targets':['hit +0.5R before -1R within 120m','hit +1.0R before -1R within 120m','hit +1.5R before -1R within 120m'],
      'model':'Separate BUY/SELL standardized logistic regression, C=0.5.',
      'split':'Train 2021-2024; validation 2025; reused diagnostic 2026.',
      'causal':'All Z and price features use data available at or before decision timestamp; target path begins at next 1m open.',
      'limitations':['2026 is reused diagnostic, not pristine OOS.','LAB096 is discovery; probability values require calibration validation before production use.','Binance 1m proxy, not broker-native execution.']
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    (OUT/'REPORT.md').write_text('# LAB096 — Z TRAJECTORY × PRICE REVERSAL PROBABILITY\n\n'+json.dumps(summary,indent=2)+
                                 '\n\n## Metrics\n\n'+met.to_markdown(index=False)+
                                 '\n\n## Calibration\n\n'+cal.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
