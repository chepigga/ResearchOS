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
Z_PULLBACKS=[0.10,0.20,0.30]
Z_PROM=[0.30,0.50,0.75]
SWING_BARS=[2,3,4]
BREAK_BUF_ATR=[0.00,0.05,0.10]
COOLDOWN_MIN=30
HOLD_MIN=120

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
    m5=x.set_index('dt').resample('5min',label='left',closed='left').agg(high=('high','max'),low=('low','min'),close=('close','last')).dropna()
    pc=m5.close.shift(1)
    tr=pd.concat([(m5.high-m5.low),(m5.high-pc).abs(),(m5.low-pc).abs()],axis=1).max(axis=1)
    m5['atr']=tr.rolling(14,min_periods=14).mean()
    m5['close_ts']=(m5.index.view('int64')//10**9)+300
    return b,m5.dropna().reset_index()

def make_tf(b,tf):
    x=b.copy(); x['dt']=pd.to_datetime(x.ts,unit='s',utc=True)
    q=x.set_index('dt').resample(f'{tf}min',label='left',closed='left').agg(
        open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    q['open_ts']=q['dt'].to_numpy(dtype='datetime64[s]').astype('int64')
    q['close_ts']=q.open_ts+tf*60
    return q

def asof_idx(a,t): return int(np.searchsorted(a,t,'right')-1)

def period(ts):
    y=pd.to_datetime(ts,unit='s',utc=True).year
    if y<=2024:return 'train_2021_24'
    if y==2025:return 'validation_2025'
    return 'diagnostic_2026'

def label_after(t,side,atr,b):
    tsa=b.ts.to_numpy(np.int64)
    k=int(np.searchsorted(tsa,t,'left'))
    if k>=len(b): return None
    ep=float(b.open.iloc[k]); sl=ep-side*atr; tp=ep+side*1.0*atr
    e=int(np.searchsorted(tsa,t+HOLD_MIN*60,'right'))
    y=0;mfe=0.;mae=0.
    for q in range(k,min(e,len(b))):
        hi=float(b.high.iloc[q]); lo=float(b.low.iloc[q])
        fav=(hi-ep)/atr if side>0 else (ep-lo)/atr
        adv=(ep-lo)/atr if side>0 else (hi-ep)/atr
        mfe=max(mfe,fav);mae=max(mae,adv)
        hs=(lo<=sl) if side>0 else (hi>=sl)
        ht=(hi>=tp) if side>0 else (lo<=tp)
        if hs: y=0;break
        if ht: y=1;break
    return y,mfe,mae,ep

def build_events(base,b,m5):
    m5ts=m5.close_ts.to_numpy(np.int64); m5atr=m5.atr.to_numpy(float)
    out=[]
    for tf in TFS:
        tb=make_tf(b,tf)
        tclose=tb.close_ts.to_numpy(np.int64)
        for _,r in base.iterrows():
            setup=int(r.ts); side=int(r.side)
            # first fully closed TF bar after setup
            ci=int(np.searchsorted(tclose,setup,side='right'))
            if ci>=len(tb): continue
            # allow confirmation within next 3 TF bars
            for confirm_i in range(ci,min(ci+3,len(tb))):
                confirm_ts=int(tb.close_ts.iloc[confirm_i])
                ai=asof_idx(m5ts,confirm_ts)
                if ai<0: continue
                atr=float(m5atr[ai])
                if not np.isfinite(atr) or atr<=0: continue
                for sb in SWING_BARS:
                    start=confirm_i-sb
                    if start<0: continue
                    prev=tb.iloc[start:confirm_i]
                    cur=tb.iloc[confirm_i]
                    if len(prev)<sb: continue
                    if side>0:
                        # exhaustion over the trailing swing window, but micro-BOS is causal
                        # break of the immediately preceding closed TF bar high
                        swing_ext=float(prev.low.min())
                        micro_break=float(prev.high.iloc[-1])
                        failed_extend=float(cur.low)>=swing_ext-0.05*atr
                        structure_distance=(float(cur.close)-micro_break)/atr
                    else:
                        swing_ext=float(prev.high.max())
                        micro_break=float(prev.low.iloc[-1])
                        failed_extend=float(cur.high)<=swing_ext+0.05*atr
                        structure_distance=(micro_break-float(cur.close))/atr
                    for buf in BREAK_BUF_ATR:
                        pass_break=structure_distance>=buf
                        if not (failed_extend and pass_break): continue
                        lab=label_after(confirm_ts,side,atr,b)
                        if lab is None: continue
                        y,mfe,mae,ep=lab
                        out.append({
                            'setup_ts':setup,'confirm_ts':confirm_ts,'side':side,'tf':tf,'swing_bars':sb,'break_buf_atr':buf,
                            'z_pullback':float(r.traj_pullback),'z_prominence':float(r.traj_prominence),
                            'z_peak_age_min':float(r.traj_peak_age_min),'z_slope':float(r.traj_pre_slope_per_min),
                            'abs_z':float(abs(r.z)),'dls':float(r.dls),'doi':float(r.doi),'rejectATR':float(-r.price_crowd_R),
                            'structure_distanceR':structure_distance,'failed_extend':1,'atr':atr,'entry_price':ep,
                            'y_1R':y,'mfeR':mfe,'maeR':mae,'period':period(confirm_ts)
                        })
                        break
                    # first confirmation for this swing_bars is enough
    return pd.DataFrame(out)

def dedup(q):
    if len(q)==0:return q
    q=q.sort_values('confirm_ts')
    keep=[];last={1:-10**18,-1:-10**18}
    for i,r in q.iterrows():
        sd=int(r.side);t=int(r.confirm_ts)
        if t-last[sd]>=COOLDOWN_MIN*60:
            keep.append(i);last[sd]=t
    return q.loc[keep].copy()

def sig_per_day(q):
    if len(q)<2:return np.nan
    d=max((pd.to_datetime(q.confirm_ts.max(),unit='s')-pd.to_datetime(q.confirm_ts.min(),unit='s')).days+1,1)
    return len(q)/d

def model_metrics(y,p):
    o={'N':len(y),'base_rate':float(np.mean(y)),'mean_pred':float(np.mean(p)),'brier':float(brier_score_loss(y,p))}
    o['auc']=float(roc_auc_score(y,p)) if len(np.unique(y))>1 else np.nan
    return o

def main():
    base=pd.read_csv(SRC)
    base=base[base.lookback_min==30].copy().drop_duplicates(['ts','side']).reset_index(drop=True)
    b,m5=load_bars()
    ev=build_events(base,b,m5)
    ev.to_csv(OUT/'structure_break_universe.csv',index=False)
    if len(ev)==0:
        raise RuntimeError("LAB098 produced zero structure-break events; inspect confirmation definition before interpreting results.")

    rows=[]
    for tf in TFS:
      for zp in Z_PULLBACKS:
       for zprom in Z_PROM:
        for sb in SWING_BARS:
         for buf in BREAK_BUF_ATR:
            q=ev[(ev.tf==tf)&(ev.z_pullback>=zp)&(ev.z_prominence>=zprom)&(ev.swing_bars==sb)&(ev.break_buf_atr==buf)].copy()
            q=dedup(q)
            for per in ['train_2021_24','validation_2025','diagnostic_2026']:
                z=q[q.period==per]
                if len(z)==0:continue
                rows.append({'tf':tf,'z_pullback':zp,'z_prominence':zprom,'swing_bars':sb,'break_buf_atr':buf,
                             'period':per,'N':len(z),'signals_per_day':sig_per_day(z),
                             'hit_rate_1R':float(z.y_1R.mean()),
                             'BUY_N':int((z.side==1).sum()),'SELL_N':int((z.side==-1).sum())})
    grid=pd.DataFrame(rows);grid.to_csv(OUT/'structure_grid.csv',index=False)

    tr=grid[grid.period=='train_2021_24'].copy()
    tr['in_target_1_4_day']=(tr.signals_per_day>=1)&(tr.signals_per_day<=4)
    tr['score']=100*tr.in_target_1_4_day.astype(int)+25*tr.hit_rate_1R-abs(tr.signals_per_day-2)
    ranked=tr.sort_values(['score','hit_rate_1R'],ascending=False).reset_index(drop=True)
    ranked.to_csv(OUT/'train_ranked_configs.csv',index=False)
    best=ranked.iloc[0]

    d=ev[(ev.tf==best.tf)&(ev.z_pullback>=best.z_pullback)&(ev.z_prominence>=best.z_prominence)&
         (ev.swing_bars==best.swing_bars)&(ev.break_buf_atr==best.break_buf_atr)].copy()
    d=dedup(d); d.to_csv(OUT/'best_config_events.csv',index=False)

    feats=['abs_z','z_pullback','z_prominence','z_peak_age_min','z_slope','dls','doi','rejectATR','structure_distanceR']
    mets=[];preds=[];coefs=[]
    for sd,name in [(1,'BUY'),(-1,'SELL')]:
        s=d[d.side==sd].copy(); train=s[s.period=='train_2021_24']
        if len(train)<100:continue
        mdl=Pipeline([('sc',StandardScaler()),('lr',LogisticRegression(C=0.5,max_iter=500))])
        mdl.fit(train[feats],train.y_1R)
        sc=mdl.named_steps['sc'];lr=mdl.named_steps['lr']
        for f,mu,scale,coef in zip(feats,sc.mean_,sc.scale_,lr.coef_[0]):
            coefs.append({'side':name,'feature':f,'mean':mu,'scale':scale,'coef':coef,'intercept':lr.intercept_[0]})
        for per in ['train_2021_24','validation_2025','diagnostic_2026']:
            q=s[s.period==per].copy()
            if len(q)==0:continue
            p=mdl.predict_proba(q[feats])[:,1]
            mets.append({'side':name,'period':per,**model_metrics(q.y_1R.to_numpy(),p)})
            qq=q[['confirm_ts','side','tf','y_1R']].copy();qq['probability']=p;qq['period']=per;preds.append(qq)
    met=pd.DataFrame(mets);met.to_csv(OUT/'probability_metrics.csv',index=False)
    pd.DataFrame(coefs).to_csv(OUT/'model_coefficients.csv',index=False)
    pred=pd.concat(preds,ignore_index=True);pred.to_csv(OUT/'probability_predictions.csv',index=False)

    bins=[]
    for (sd,per),q in pred.groupby(['side','period']):
        q=q.copy();q['prob_bin']=pd.cut(q.probability,[0,.5,.55,.6,.65,.7,.75,.8,.85,.9,1.0001],right=False)
        z=q.groupby('prob_bin',observed=True).agg(N=('y_1R','size'),mean_pred=('probability','mean'),actual=('y_1R','mean')).reset_index()
        z['side']='BUY' if sd==1 else 'SELL';z['period']=per;bins.append(z)
    pd.concat(bins,ignore_index=True).to_csv(OUT/'probability_bins.csv',index=False)

    dd=d.copy();dd['date']=pd.to_datetime(dd.confirm_ts,unit='s',utc=True).dt.date
    daily=dd.groupby(['period','date']).agg(N=('side','size'),BUY=('side',lambda x:int((x==1).sum())),SELL=('side',lambda x:int((x==-1).sum()))).reset_index()
    daily.to_csv(OUT/'daily_signal_counts.csv',index=False)
    dist=daily.groupby('period').agg(days=('N','size'),mean_per_day=('N','mean'),median_per_day=('N','median'),
                                     p90_per_day=('N',lambda x:float(np.quantile(x,.9))),days_1_4=('N',lambda x:int(((x>=1)&(x<=4)).sum()))).reset_index()
    dist.to_csv(OUT/'daily_frequency_summary.csv',index=False)

    summary={
      'lab':'LAB098_Z_TRAJECTORY_X_PRICE_STRUCTURE_BREAK',
      'principle':'Z turn creates setup; price must fail to extend old extreme and then close through prior micro-structure before arrow.',
      'arrow_timing':'At confirmation close only; no backpainting.',
      'grid':{'tf':TFS,'z_pullback':Z_PULLBACKS,'z_prominence':Z_PROM,'swing_bars':SWING_BARS,'break_buffer_ATR':BREAK_BUF_ATR},
      'target':'Hit +1R before -1R within 120m after structure-break confirmation.',
      'selection':'2021-2024 train only; 2025 validation; 2026 reused diagnostic.',
      'best_train_config':best.to_dict(),
      'limitations':['2026 reused diagnostic, not pristine OOS.','Structure proxy is algorithmic simplification of discretionary swing reading.','Binance 1m proxy, not broker-native.']
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB098 — Z TRAJECTORY × PRICE STRUCTURE BREAK\n\n'+json.dumps(summary,indent=2,default=float)+
      '\n\n## Top configs\n\n'+ranked.head(30).to_markdown(index=False)+
      '\n\n## Probability metrics\n\n'+met.to_markdown(index=False)+
      '\n\n## Daily frequency\n\n'+dist.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
