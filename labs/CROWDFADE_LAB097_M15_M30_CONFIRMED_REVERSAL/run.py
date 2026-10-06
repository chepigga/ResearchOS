from pathlib import Path
import json, zipfile, numpy as np, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
BARS_DIR=ROOT/'data'/'all_1m'
SRC=ROOT.parent/'CROWDFADE_LAB096_Z_PRICE_REVERSAL_PROBABILITY'/'output'/'probability_dataset.csv'

TFS=[15,30]
PULLBACKS=[0.10,0.20,0.30]
PROMINENCES=[0.30,0.50,0.75]
PRICE_CONFIRM_ATR=[0.00,0.10,0.20]
COOLDOWN_MIN=30
HOLD_MIN=120
TARGET_R=1.0

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
        q=q.dropna().copy(); q.ts=q.ts.astype(np.int64)
        rows.append(q[['ts','open','high','low','close']])
    b=pd.concat(rows,ignore_index=True).sort_values('ts').drop_duplicates('ts').reset_index(drop=True)

    x=b.copy(); x['dt']=pd.to_datetime(x.ts,unit='s',utc=True)
    m5=x.set_index('dt').resample('5min',label='left',closed='left').agg(
        high=('high','max'),low=('low','min'),close=('close','last')
    ).dropna()
    pc=m5.close.shift(1)
    tr=pd.concat([(m5.high-m5.low),(m5.high-pc).abs(),(m5.low-pc).abs()],axis=1).max(axis=1)
    m5['atr']=tr.rolling(14,min_periods=14).mean()
    m5['close_ts']=(m5.index.view('int64')//10**9)+300
    return b,m5.dropna().reset_index()

def next_tf_close(t,tf):
    sec=tf*60
    return ((int(t)//sec)+1)*sec

def asof_idx(a,t): return int(np.searchsorted(a,t,'right')-1)

def period(ts):
    y=pd.to_datetime(ts,unit='s',utc=True).year
    if y<=2024:return 'train_2021_24'
    if y==2025:return 'validation_2025'
    return 'diagnostic_2026'

def build_confirmed(base,b,m5):
    tsa=b.ts.to_numpy(np.int64)
    m5ts=m5.close_ts.to_numpy(np.int64); m5atr=m5.atr.to_numpy(float)
    rows=[]
    # one pass over broad causal LAB096 universe; trajectory features already exist at setup
    for _,r in base.iterrows():
        t0=int(r.ts); sd=int(r.side)
        for tf in TFS:
            tc=next_tf_close(t0,tf)
            j=asof_idx(tsa,tc-60); k=asof_idx(tsa,tc-tf*60)
            ai=asof_idx(m5ts,tc)
            if k<0 or j<=k or ai<0: continue
            atr=float(m5atr[ai])
            if not np.isfinite(atr) or atr<=0: continue
            o=float(b.open.iloc[k]); c=float(b.close.iloc[j])
            hi=float(b.high.iloc[k:j+1].max()); lo=float(b.low.iloc[k:j+1].min())
            bodyR=sd*(c-o)/atr
            loc=(c-lo)/(hi-lo) if hi>lo else 0.5
            dirloc=loc if sd>0 else 1-loc

            # target starts at next 1m open after confirmation
            e0=int(np.searchsorted(tsa,tc,'left'))
            if e0>=len(b): continue
            ep=float(b.open.iloc[e0]); sl=ep-sd*atr; tp=ep+sd*TARGET_R*atr
            e1=int(np.searchsorted(tsa,tc+HOLD_MIN*60,'right'))
            y=0; mfe=0.0; mae=0.0
            for q in range(e0,min(e1,len(b))):
                bh=float(b.high.iloc[q]); bl=float(b.low.iloc[q])
                fav=(bh-ep)/atr if sd>0 else (ep-bl)/atr
                adv=(ep-bl)/atr if sd>0 else (bh-ep)/atr
                mfe=max(mfe,fav); mae=max(mae,adv)
                hs=(bl<=sl) if sd>0 else (bh>=sl)
                ht=(bh>=tp) if sd>0 else (bl<=tp)
                if hs: y=0; break
                if ht: y=1; break
            rows.append({
                'setup_ts':t0,'confirm_ts':tc,'side':sd,'tf':tf,'period':period(tc),
                'z_now':float(r.z),'abs_z':float(abs(r.z)),
                'z_pullback':float(r.traj_pullback),'z_prominence':float(r.traj_prominence),
                'z_peak_age_min':float(r.traj_peak_age_min),'z_slope':float(r.traj_pre_slope_per_min),
                'dls':float(r.dls),'doi':float(r.doi),'rejectATR':float(-r.price_crowd_R),
                'tf_bodyR':bodyR,'tf_rangeR':(hi-lo)/atr,'tf_dir_close_loc':dirloc,
                'atr':atr,'entry_price':ep,'y_1R':y,'mfeR':mfe,'maeR':mae
            })
    return pd.DataFrame(rows)

def dedup(q):
    if len(q)==0:return q
    q=q.sort_values('confirm_ts'); keep=[]; last={1:-10**18,-1:-10**18}
    for i,r in q.iterrows():
        sd=int(r.side); t=int(r.confirm_ts)
        if t-last[sd]>=COOLDOWN_MIN*60:
            keep.append(i); last[sd]=t
    return q.loc[keep].copy()

def freq_days(q):
    if len(q)<2:return np.nan
    days=max((pd.to_datetime(q.confirm_ts.max(),unit='s')-pd.to_datetime(q.confirm_ts.min(),unit='s')).days+1,1)
    return len(q)/days

def model_metrics(y,p):
    d={'N':len(y),'base_rate':float(np.mean(y)),'mean_pred':float(np.mean(p)),'brier':float(brier_score_loss(y,p))}
    d['auc']=float(roc_auc_score(y,p)) if len(np.unique(y))>1 else np.nan
    return d

def main():
    base=pd.read_csv(SRC)
    # LAB096 file contains one row per lookback; use 30m trajectory context only to avoid duplicates.
    base=base[base.lookback_min==30].copy().drop_duplicates(['ts','side']).reset_index(drop=True)
    b,m5=load_bars()
    allc=build_confirmed(base,b,m5)
    allc.to_csv(OUT/'confirmed_universe.csv',index=False)

    rows=[]; selected_frames=[]
    for tf in TFS:
      u=allc[allc.tf==tf]
      for pb in PULLBACKS:
       for pr in PROMINENCES:
        for pc in PRICE_CONFIRM_ATR:
            q=u[(u.z_pullback>=pb)&(u.z_prominence>=pr)&
                (u.tf_bodyR>=pc)&(u.tf_dir_close_loc>=0.55)].copy()
            q=dedup(q)
            q['pullback_thr']=pb;q['prominence_thr']=pr;q['price_confirm_thr']=pc
            selected_frames.append(q)
            for per in ['train_2021_24','validation_2025','diagnostic_2026']:
                z=q[q.period==per]
                if len(z)==0: continue
                rows.append({
                  'tf':tf,'pullback':pb,'prominence':pr,'price_confirm':pc,'period':per,
                  'N':len(z),'signals_per_day':freq_days(z),'hit_rate_1R':float(z.y_1R.mean()),
                  'BUY_N':int((z.side==1).sum()),'SELL_N':int((z.side==-1).sum())
                })
    grid=pd.DataFrame(rows);grid.to_csv(OUT/'frequency_quality_grid.csv',index=False)

    tr=grid[grid.period=='train_2021_24'].copy()
    tr['in_target_2_4_day']=(tr.signals_per_day>=2)&(tr.signals_per_day<=4)
    tr['score']=100*tr.in_target_2_4_day.astype(int)+20*tr.hit_rate_1R-abs(tr.signals_per_day-3)
    ranked=tr.sort_values(['score','hit_rate_1R'],ascending=False).reset_index(drop=True)
    ranked.to_csv(OUT/'train_ranked_configs.csv',index=False)

    best=ranked.iloc[0]
    # reconstruct best event set from universe, not concatenated duplicates
    d=allc[(allc.tf==best.tf)&
           (allc.z_pullback>=best.pullback)&
           (allc.z_prominence>=best.prominence)&
           (allc.tf_bodyR>=best.price_confirm)&
           (allc.tf_dir_close_loc>=0.55)].copy()
    d=dedup(d)
    d.to_csv(OUT/'best_config_events.csv',index=False)

    feats=['z_now','abs_z','z_pullback','z_prominence','z_peak_age_min','z_slope',
           'dls','doi','rejectATR','tf_bodyR','tf_rangeR','tf_dir_close_loc']
    mets=[]; preds=[]; coefs=[]
    for sd,name in [(1,'BUY'),(-1,'SELL')]:
        s=d[d.side==sd].copy(); train=s[s.period=='train_2021_24']
        if len(train)<100: continue
        mdl=Pipeline([('sc',StandardScaler()),('lr',LogisticRegression(C=0.5,max_iter=500))])
        mdl.fit(train[feats],train.y_1R)
        sc=mdl.named_steps['sc']; lr=mdl.named_steps['lr']
        for f,mu,scale,coef in zip(feats,sc.mean_,sc.scale_,lr.coef_[0]):
            coefs.append({'side':name,'feature':f,'mean':mu,'scale':scale,'coef':coef,'intercept':lr.intercept_[0]})
        for per in ['train_2021_24','validation_2025','diagnostic_2026']:
            q=s[s.period==per].copy()
            if len(q)==0: continue
            p=mdl.predict_proba(q[feats])[:,1]
            mets.append({'side':name,'period':per,**model_metrics(q.y_1R.to_numpy(),p)})
            qq=q[['confirm_ts','side','tf','y_1R']].copy(); qq['probability']=p; qq['period']=per; preds.append(qq)
    met=pd.DataFrame(mets);met.to_csv(OUT/'probability_metrics.csv',index=False)
    pd.DataFrame(coefs).to_csv(OUT/'model_coefficients.csv',index=False)
    pred=pd.concat(preds,ignore_index=True);pred.to_csv(OUT/'probability_predictions.csv',index=False)

    bins=[]
    for (sd,per),q in pred.groupby(['side','period']):
        q=q.copy();q['prob_bin']=pd.cut(q.probability,[0,.5,.55,.6,.65,.7,.75,.8,.85,.9,1.0001],right=False)
        z=q.groupby('prob_bin',observed=True).agg(N=('y_1R','size'),mean_pred=('probability','mean'),actual=('y_1R','mean')).reset_index()
        z['side']='BUY' if sd==1 else 'SELL';z['period']=per;bins.append(z)
    cal=pd.concat(bins,ignore_index=True);cal.to_csv(OUT/'probability_bins.csv',index=False)

    # day distribution for actual frequency
    dd=d.copy(); dd['date']=pd.to_datetime(dd.confirm_ts,unit='s',utc=True).dt.date
    daily=dd.groupby(['period','date']).agg(N=('side','size'),BUY=('side',lambda x:int((x==1).sum())),SELL=('side',lambda x:int((x==-1).sum()))).reset_index()
    daily.to_csv(OUT/'daily_signal_counts.csv',index=False)
    dist=daily.groupby('period').agg(days=('N','size'),mean_per_day=('N','mean'),median_per_day=('N','median'),p90_per_day=('N',lambda x:float(np.quantile(x,.9))),days_2_4=('N',lambda x:int(((x>=2)&(x<=4)).sum()))).reset_index()
    dist.to_csv(OUT/'daily_frequency_summary.csv',index=False)

    summary={
      'lab':'LAB097_M15_M30_CONFIRMED_Z_REVERSAL',
      'universe':'LAB096 broad causal non-Z setup universe, 30m Z-trajectory features; no fixed |Z| gate.',
      'arrow_timing':'Only at close of M15/M30 confirmation bar; never back-painted onto the Z peak/trough.',
      'confirmation':'Directional candle body >= fixed ATR threshold and directional close location >=0.55.',
      'grid':{'tf':TFS,'z_pullback':PULLBACKS,'z_prominence':PROMINENCES,'price_confirm_ATR':PRICE_CONFIRM_ATR},
      'target':'Hit +1R before -1R within 120m after confirmation.',
      'target_frequency':'2-4 confirmed independent arrows/day.',
      'selection':'Best config selected using 2021-2024 only; 2025 validation; 2026 reused diagnostic.',
      'best_train_config':best.to_dict(),
      'limitations':['2026 is reused diagnostic, not pristine OOS.','Binance 1m proxy, not broker-native execution.','Grid is discovery and must be frozen before future OOS.']
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB097 — M15/M30 CONFIRMED Z REVERSAL\n\n'+json.dumps(summary,indent=2,default=float)+
      '\n\n## Train ranked configs\n\n'+ranked.head(30).to_markdown(index=False)+
      '\n\n## Probability metrics\n\n'+met.to_markdown(index=False)+
      '\n\n## Daily frequency\n\n'+dist.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
