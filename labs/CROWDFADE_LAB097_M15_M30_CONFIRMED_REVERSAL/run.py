from pathlib import Path
import json, zipfile, numpy as np, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'
FLOW_ZIP=ROOT.parent/'CROWDFADE_LAB095_CAUSAL_Z_TRAJECTORY'/'data'/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
if not FLOW_ZIP.exists():
    FLOW_ZIP=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
BARS_DIR=DATA/'all_1m'

TFS=[15,30]
LOOKBACKS=[30,60]
PULLBACKS=[0.10,0.20,0.30]
PROMINENCES=[0.30,0.50,0.75]
PRICE_CONFIRM_ATR=[0.00,0.10,0.20]
COOLDOWN_MIN=30
HOLD_MIN=120
TARGET_R=1.0

def load_flow():
    with zipfile.ZipFile(FLOW_ZIP) as z:
        n=[x for x in z.namelist() if x.endswith('.csv')][0]
        with z.open(n) as f:
            q=pd.read_csv(f,usecols=['create_time','count_long_short_ratio','sum_open_interest'])
    q['t']=pd.to_datetime(q.create_time,utc=True,errors='coerce')
    q['ratio']=pd.to_numeric(q.count_long_short_ratio,errors='coerce')
    q['oi']=pd.to_numeric(q.sum_open_interest,errors='coerce')
    q=q.dropna(subset=['t','ratio']).sort_values('t').drop_duplicates('t').reset_index(drop=True)
    mu=q.ratio.rolling(72,min_periods=72).mean()
    sd=q.ratio.rolling(72,min_periods=72).std(ddof=0)
    q['z']=(q.ratio-mu)/sd.replace(0,np.nan)
    q['ts']=q.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    return q[['ts','ratio','oi','z']].dropna().reset_index(drop=True)

def load_bars():
    rows=[]
    for zp in sorted(BARS_DIR.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
        q.columns=['open_ms','open','high','low','close']
        q['ts']=(pd.to_numeric(q.open_ms,errors='coerce')//1000).astype('Int64')
        for c in ['open','high','low','close']:q[c]=pd.to_numeric(q[c],errors='coerce')
        q=q.dropna().copy();q.ts=q.ts.astype(np.int64)
        rows.append(q[['ts','open','high','low','close']])
    b=pd.concat(rows,ignore_index=True).sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
    # ATR14 on M5, causal completed-bar mapping
    x=b.copy()
    x['dt']=pd.to_datetime(x.ts,unit='s',utc=True)
    m5=x.set_index('dt').resample('5min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna()
    pc=m5.close.shift(1)
    tr=pd.concat([(m5.high-m5.low),(m5.high-pc).abs(),(m5.low-pc).abs()],axis=1).max(axis=1)
    m5['atr']=tr.rolling(14,min_periods=14).mean()
    m5['close_ts']=(m5.index.view('int64')//10**9)+300
    return b,m5.dropna().reset_index()

def period(ts):
    y=pd.to_datetime(ts,unit='s',utc=True).year
    if y<=2024:return 'train_2021_24'
    if y==2025:return 'validation_2025'
    return 'diagnostic_2026'

def asof_idx(a,t):
    return int(np.searchsorted(a,t,'right')-1)

def make_traj_candidates(flow,lb,pb,pr):
    ts=flow.ts.to_numpy(np.int64); z=flow.z.to_numpy(float)
    rows=[]
    for i in range(2,len(flow)):
        t=int(ts[i]); zi=float(z[i])
        a=np.searchsorted(ts,t-lb*60,'left')
        if i-a<3:continue
        hist=z[a:i]  # strictly before current
        # SELL: prior local high, current has pulled down
        imx=int(np.argmax(hist)); peak=float(hist[imx]); prior_min=float(np.min(hist[:imx+1]))
        prom_sell=peak-prior_min; pull_sell=peak-zi
        # BUY: prior local low, current has rebounded
        imn=int(np.argmin(hist)); trough=float(hist[imn]); prior_max=float(np.max(hist[:imn+1]))
        prom_buy=prior_max-trough; pull_buy=zi-trough
        if pull_sell>=pb and prom_sell>=pr:
            rows.append({'setup_ts':t,'side':-1,'z_now':zi,'z_extreme':peak,'z_pullback':pull_sell,'z_prominence':prom_sell,
                         'z_slope':(peak-float(hist[0]))/max((ts[a+imx]-ts[a])/60,5)})
        if pull_buy>=pb and prom_buy>=pr:
            rows.append({'setup_ts':t,'side':1,'z_now':zi,'z_extreme':trough,'z_pullback':pull_buy,'z_prominence':prom_buy,
                         'z_slope':(float(hist[0])-trough)/max((ts[a+imn]-ts[a])/60,5)})
    if not rows:return pd.DataFrame()
    g=pd.DataFrame(rows).sort_values('setup_ts')
    keep=[];last={1:-10**18,-1:-10**18}
    for i,r in g.iterrows():
        sd=int(r.side);t=int(r.setup_ts)
        if t-last[sd]>=COOLDOWN_MIN*60:
            keep.append(i);last[sd]=t
    return g.loc[keep].reset_index(drop=True)

def next_tf_close(t,tf):
    sec=tf*60
    return ((t//sec)+1)*sec

def confirm_event(r,tf,pc,b,m5):
    t0=int(r.setup_ts); tc=next_tf_close(t0,tf)
    tsa=b.ts.to_numpy(np.int64)
    j=asof_idx(tsa,tc-60)
    k=asof_idx(tsa,tc-tf*60)
    if k<0 or j<=k:return None
    # ATR from last completed M5 as of confirmation
    ma=m5[m5.close_ts<=tc]
    if len(ma)==0:return None
    atr=float(ma.atr.iloc[-1])
    if not np.isfinite(atr) or atr<=0:return None
    o=float(b.open.iloc[k]); c=float(b.close.iloc[j]); hi=float(b.high.iloc[k:j+1].max()); lo=float(b.low.iloc[k:j+1].min())
    sd=int(r.side)
    bodyR=sd*(c-o)/atr
    closeLoc=(c-lo)/(hi-lo) if hi>lo else .5
    dirCloseLoc=closeLoc if sd>0 else 1-closeLoc
    return {'confirm_ts':tc,'atr':atr,'tf_bodyR':bodyR,'tf_rangeR':(hi-lo)/atr,'tf_dir_close_loc':dirCloseLoc,'confirm_price':c}

def label_event(ev,b):
    tsa=b.ts.to_numpy(np.int64); t=int(ev.confirm_ts); sd=int(ev.side); atr=float(ev.atr)
    k=int(np.searchsorted(tsa,t,'left'))
    if k>=len(b):return None
    ep=float(b.open.iloc[k]); sl=ep-sd*atr; tp=ep+sd*TARGET_R*atr
    e=int(np.searchsorted(tsa,t+HOLD_MIN*60,'right'))
    y=0; mfe=0; mae=0
    for q in range(k,min(e,len(b))):
        hi=float(b.high.iloc[q]);lo=float(b.low.iloc[q])
        fav=(hi-ep)/atr if sd>0 else (ep-lo)/atr
        adv=(ep-lo)/atr if sd>0 else (hi-ep)/atr
        mfe=max(mfe,fav);mae=max(mae,adv)
        hs=(lo<=sl) if sd>0 else (hi>=sl)
        ht=(hi>=tp) if sd>0 else (lo<=tp)
        if hs: y=0;break
        if ht: y=1;break
    return {'y_1R':y,'mfeR':mfe,'maeR':mae}

def metrics(y,p):
    if len(y)==0:return {}
    d={'N':len(y),'base_rate':float(np.mean(y)),'mean_pred':float(np.mean(p)),'brier':float(brier_score_loss(y,p))}
    d['auc']=float(roc_auc_score(y,p)) if len(np.unique(y))>1 else np.nan
    return d

def main():
    flow=load_flow(); b,m5=load_bars()
    all_events=[]
    configs=[]
    for tf in TFS:
      for lb in LOOKBACKS:
       for pb in PULLBACKS:
        for pr in PROMINENCES:
         cand=make_traj_candidates(flow,lb,pb,pr)
         if len(cand)==0:continue
         evs=[]
         for _,r in cand.iterrows():
            ce=confirm_event(r,tf,0,b,m5)
            if ce is None:continue
            d={**r.to_dict(),**ce}
            lab=label_event(pd.Series(d),b)
            if lab is None:continue
            d.update(lab);d['tf']=tf;d['lookback']=lb;d['pullback_thr']=pb;d['prominence_thr']=pr;d['period']=period(int(d['confirm_ts']))
            evs.append(d)
         e=pd.DataFrame(evs)
         if len(e)==0:continue
         for pc in PRICE_CONFIRM_ATR:
            q=e[(e.tf_bodyR>=pc)&(e.tf_dir_close_loc>=0.55)].copy()
            # dedup at confirmed-signal level
            q=q.sort_values('confirm_ts');keep=[];last={1:-10**18,-1:-10**18}
            for i,r in q.iterrows():
                sd=int(r.side);t=int(r.confirm_ts)
                if t-last[sd]>=COOLDOWN_MIN*60:
                    keep.append(i);last[sd]=t
            q=q.loc[keep].copy()
            q['price_confirm_thr']=pc
            all_events.append(q)
            # frequency summaries
            for per in ['train_2021_24','validation_2025','diagnostic_2026']:
                z=q[q.period==per]
                if len(z)==0:continue
                days=max((pd.to_datetime(z.confirm_ts.max(),unit='s')-pd.to_datetime(z.confirm_ts.min(),unit='s')).days+1,1)
                configs.append({'tf':tf,'lookback':lb,'pullback':pb,'prominence':pr,'price_confirm':pc,'period':per,
                                'N':len(z),'signals_per_day':len(z)/days,'hit_rate_1R':float(z.y_1R.mean()),
                                'BUY_N':int((z.side==1).sum()),'SELL_N':int((z.side==-1).sum())})
    events=pd.concat(all_events,ignore_index=True)
    events.to_csv(OUT/'confirmed_events.csv',index=False)
    cfg=pd.DataFrame(configs);cfg.to_csv(OUT/'frequency_quality_grid.csv',index=False)

    # Pick configs on train only: target 2-4 signals/day, then highest 1R hit rate.
    tr=cfg[cfg.period=='train_2021_24'].copy()
    tr['in_target_2_4_day']=(tr.signals_per_day>=2)&(tr.signals_per_day<=4)
    tr['score']=100*tr.in_target_2_4_day.astype(int)+20*tr.hit_rate_1R-abs(tr.signals_per_day-3)
    ranked=tr.sort_values(['score','hit_rate_1R'],ascending=False)
    ranked.to_csv(OUT/'train_ranked_configs.csv',index=False)

    # Fit probability model on best TRAIN-selected config only; validate untouched 2025, diagnose 2026.
    best=ranked.iloc[0]
    mask=(events.tf==best.tf)&(events.lookback==best.lookback)&(events.pullback_thr==best.pullback)&(events.prominence_thr==best.prominence)&(events.price_confirm_thr==best.price_confirm)
    d=events[mask].copy()
    feats=['z_now','z_extreme','z_pullback','z_prominence','z_slope','tf_bodyR','tf_rangeR','tf_dir_close_loc']
    outmet=[];preds=[]
    for sd,name in [(1,'BUY'),(-1,'SELL')]:
        s=d[d.side==sd].copy(); train=s[s.period=='train_2021_24']
        if len(train)<50:continue
        model=Pipeline([('sc',StandardScaler()),('lr',LogisticRegression(C=0.5,max_iter=500))])
        model.fit(train[feats],train.y_1R)
        for per in ['train_2021_24','validation_2025','diagnostic_2026']:
            q=s[s.period==per].copy()
            if len(q)==0:continue
            p=model.predict_proba(q[feats])[:,1]
            outmet.append({'side':name,'period':per,**metrics(q.y_1R.to_numpy(),p)})
            qq=q[['confirm_ts','side','tf','y_1R']].copy();qq['probability']=p;qq['period']=per;preds.append(qq)
    met=pd.DataFrame(outmet);met.to_csv(OUT/'probability_metrics.csv',index=False)
    pred=pd.concat(preds,ignore_index=True);pred.to_csv(OUT/'probability_predictions.csv',index=False)

    bins=[]
    for (sd,per),q in pred.groupby(['side','period']):
        q=q.copy();q['bin']=pd.cut(q.probability,[0,.5,.55,.6,.65,.7,.75,.8,.85,.9,1.0001],right=False)
        z=q.groupby('bin',observed=True).agg(N=('y_1R','size'),mean_pred=('probability','mean'),actual=('y_1R','mean')).reset_index()
        z['side']='BUY' if sd==1 else 'SELL';z['period']=per;bins.append(z)
    pd.concat(bins,ignore_index=True).to_csv(OUT/'probability_bins.csv',index=False)

    # Current-day diagnostic for latest date present (2026-08 dataset end), analogous to "today".
    latest=pd.to_datetime(d.confirm_ts.max(),unit='s',utc=True).date()
    day=d[pd.to_datetime(d.confirm_ts,unit='s',utc=True).dt.date==latest].copy()
    day.to_csv(OUT/'latest_day_signals.csv',index=False)

    summary={
      'lab':'LAB097_M15_M30_CONFIRMED_Z_REVERSAL',
      'principle':'Z trajectory creates setup; arrow appears only at close of M15/M30 confirmation bar.',
      'confirmation':'Directional timeframe body >= threshold ATR and close in directional 45% of bar or better (dir close location >=0.55).',
      'grid':{'tf':TFS,'lookback':LOOKBACKS,'z_pullback':PULLBACKS,'z_prominence':PROMINENCES,'price_confirm_atr':PRICE_CONFIRM_ATR},
      'target_frequency':'2-4 independent confirmed signals/day',
      'probability_target':'hit +1R before -1R within 120m after confirmation',
      'selection':'Configuration chosen on 2021-2024 only; 2025 validation; 2026 reused diagnostic.',
      'best_train_config':best.to_dict(),
      'limitations':['2026 reused diagnostic, not pristine OOS.','Binance price proxy, not broker-native.','Grid is discovery; selected configuration must be frozen before future OOS.']
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB097 — M15/M30 CONFIRMED Z REVERSAL\n\n'+json.dumps(summary,indent=2,default=float)+
                                 '\n\n## Top train configs\n\n'+ranked.head(30).to_markdown(index=False)+
                                 '\n\n## Probability metrics\n\n'+met.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
