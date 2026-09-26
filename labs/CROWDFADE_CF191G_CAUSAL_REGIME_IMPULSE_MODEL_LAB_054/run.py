from pathlib import Path
import json, zipfile, importlib.util
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p53=ROOT.parent/'CROWDFADE_THREE_BOT_FIXES_HISTORICAL_REPLAY_LAB_053'/'run.py'
sp53=importlib.util.spec_from_file_location('lab53',p53)
lab53=importlib.util.module_from_spec(sp53); sp53.loader.exec_module(lab53)
lab43=lab53.lab43
lab53.DATA=DATA
lab43.DATA=DATA

EXPECT={
    'historical': {'N':5297,'SumR':700.3704107793633},
    'forward_2026': {'N':544,'SumR':35.49784078156513},
}

TREND_FEATURES=['h1_state','h4_state','h1_h4_aligned','with_h1','with_h4','with_aligned']
PRICE_FEATURES=['ret15_atr','ret30_atr','ret60_atr','eff30','eff60','range15_atr','range60_atr','close_loc15','close_loc60','pullback60_atr','atr_pct']
CONF_FEATURES=['confirm_age_min','pre_fav_atr','pre_adv_atr','response_ratio','signal_z','confirm_z','delta_abs_z']
FLOW_FEATURES=['oi_ch30','oi_ch60','taker_delta15','taker_delta30','taker_delta60','vol_exp15']
FAMILIES={
    'TREND_ONLY':TREND_FEATURES,
    'PRICE_ONLY':PRICE_FEATURES,
    'FLOW_ONLY':FLOW_FEATURES,
    'FULL':TREND_FEATURES+PRICE_FEATURES+CONF_FEATURES+FLOW_FEATURES,
}

def metrics_r(a):
    return lab43.metrics(np.asarray(a,float))

def load_flow_meta():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:
            r=pd.read_csv(f,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r['t']=pd.to_datetime(r.create_time,utc=True,errors='coerce')
    r['oi']=pd.to_numeric(r.sum_open_interest,errors='coerce')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['t','oi','ratio']).sort_values('t').drop_duplicates('t')
    r=r[r.oi>0].copy()
    mu=r.ratio.rolling(72,min_periods=72).mean()
    sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    r['ts']=r.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    return r[['ts','oi','ratio','z']].reset_index(drop=True)

def load_1m_microstructure():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,5,9])
        ts=(pd.to_numeric(q.iloc[:,0],errors='coerce')//1000).astype('Int64')
        vol=pd.to_numeric(q.iloc[:,1],errors='coerce')
        taker=pd.to_numeric(q.iloc[:,2],errors='coerce')
        x=pd.DataFrame({'ts_start':ts,'volume':vol,'taker_buy':taker}).dropna()
        x['ts']=x.ts_start.astype(np.int64)+60
        rows.append(x[['ts','volume','taker_buy']])
    m=pd.concat(rows,ignore_index=True).sort_values('ts').drop_duplicates('ts')
    m['delta']=2.0*m.taker_buy-m.volume
    for w in [15,30,60]:
        sv=m.volume.rolling(w,min_periods=w).sum()
        sd=m.delta.rolling(w,min_periods=w).sum()
        m[f'taker_delta{w}']=sd/sv.replace(0,np.nan)
    v15=m.volume.rolling(15,min_periods=15).sum()
    prior60=m.volume.shift(15).rolling(60,min_periods=60).sum()
    m['vol_exp15']=v15/(prior60/4.0).replace(0,np.nan)
    return m[['ts','taker_delta15','taker_delta30','taker_delta60','vol_exp15']].reset_index(drop=True)

def asof_indices(src_ts, query_ts):
    return np.searchsorted(src_ts,query_ts,'right')-1

def flow_features(flow, micro, entry_ts):
    ft=flow.ts.to_numpy(np.int64); oi=flow.oi.to_numpy(float)
    mt=micro.ts.to_numpy(np.int64)
    out={k:np.full(len(entry_ts),np.nan,float) for k in FLOW_FEATURES}
    fi=asof_indices(ft,entry_ts)
    f30=asof_indices(ft,entry_ts-1800)
    f60=asof_indices(ft,entry_ts-3600)
    g30=(fi>=0)&(f30>=0)&(oi[f30]>0)
    g60=(fi>=0)&(f60>=0)&(oi[f60]>0)
    out['oi_ch30'][g30]=oi[fi[g30]]/oi[f30[g30]]-1.0
    out['oi_ch60'][g60]=oi[fi[g60]]/oi[f60[g60]]-1.0
    mi=asof_indices(mt,entry_ts)
    for k in ['taker_delta15','taker_delta30','taker_delta60','vol_exp15']:
        a=micro[k].to_numpy(float);g=mi>=0;out[k][g]=a[mi[g]]
    return out

def completed_tf_state(dt5,H5,L5,C5,tf_sec):
    starts=dt5-300
    bucket=(starts//tf_sec)*tf_sec
    idx=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1]
    end=np.r_[idx[1:],len(dt5)]
    bstart=bucket[idx]
    avail=bstart+tf_sec
    C=C5[end-1]
    last_avail=dt5[end-1]
    complete=last_avail>=avail
    avail=avail[complete];C=C[complete]
    ema=pd.Series(C).ewm(span=50,adjust=False).mean().to_numpy()
    state=np.zeros(len(C),np.int8)
    for i in range(4,len(C)):
        if C[i]>ema[i] and ema[i]>ema[i-4]: state[i]=1
        elif C[i]<ema[i] and ema[i]<ema[i-4]: state[i]=-1
    j=np.searchsorted(avail,dt5,'right')-1
    out=np.zeros(len(dt5),np.int8)
    g=j>=0;out[g]=state[j[g]]
    return out

def rolling_price_features(dt5,H5,L5,C5,A5,entry_k,side):
    n=len(entry_k)
    out={k:np.full(n,np.nan,float) for k in PRICE_FEATURES}
    for ii,(k,sd) in enumerate(zip(entry_k,side)):
        a=A5[k]; ep=C5[k]
        if not np.isfinite(a) or a<=0: continue
        out['atr_pct'][ii]=a/ep
        for bars,key in [(3,'ret15_atr'),(6,'ret30_atr'),(12,'ret60_atr')]:
            if k-bars>=0:
                out[key][ii]=sd*(C5[k]-C5[k-bars])/a
        if k-6>=0:
            p=C5[k-6:k+1]
            out['eff30'][ii]=sd*(p[-1]-p[0])/(np.abs(np.diff(p)).sum()+1e-12)
        if k-12>=0:
            p=C5[k-12:k+1]
            out['eff60'][ii]=sd*(p[-1]-p[0])/(np.abs(np.diff(p)).sum()+1e-12)
        if k-2>=0:
            hh=np.max(H5[k-2:k+1]);ll=np.min(L5[k-2:k+1])
            out['range15_atr'][ii]=(hh-ll)/a
            loc=(ep-ll)/(hh-ll+1e-12)
            out['close_loc15'][ii]=(2*loc-1)*sd
        if k-11>=0:
            hh=np.max(H5[k-11:k+1]);ll=np.min(L5[k-11:k+1])
            out['range60_atr'][ii]=(hh-ll)/a
            loc=(ep-ll)/(hh-ll+1e-12)
            out['close_loc60'][ii]=(2*loc-1)*sd
            out['pullback60_atr'][ii]=((hh-ep)/a) if sd>0 else ((ep-ll)/a)
    return out

def extract_cf191g_events(p):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64)
    EIDX=np.zeros(cap,np.int64);SIDE=np.zeros(cap,np.int8)
    SIGZ=np.zeros(cap);CONFZ=np.zeros(cap);AGE=np.zeros(cap)
    MF=np.zeros(cap);MA=np.zeros(cap);RESP=np.zeros(cap)
    n=0;k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False
    conf=False;cs=0;cp=0.;ca=0.;ct=0;cb=0;mf=0.;ma=0.;sigz=0.
    while k<len(dt5)-3:
        t=dt5[k];z=Z5[k]
        if t<nextts:
            k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=lab53.MAXDAY:
            conf=False;k+=1;continue
        if conf:
            side=cs
            fav=((cp-L5[k]) if side<0 else (H5[k]-cp))/ca
            adv=((H5[k]-cp) if side<0 else (cp-L5[k]))/ca
            if fav<0:fav=0.
            if adv<0:adv=0.
            mf=max(mf,fav);ma=max(ma,adv)
            cb-=1
            age=t-ct
            if cb<=0 or age>2700:
                conf=False;k+=1;continue
            if ma>lab53.G_MAX_ADV:
                conf=False;k+=1;continue
            target=cp+side*lab53.CONF_ATR*ca
            confirmed=(C5[k]>=target) if side>0 else (C5[k]<=target)
            if not confirmed:
                k+=1;continue
            same=(z<0.0) if side>0 else (z>0.0)
            if not same:
                conf=False;k+=1;continue
            if abs(z)<lab53.G_MIN_ABS_Z:
                conf=False;k+=1;continue
            response=mf/(ma+1e-9)
            if response<lab53.G_MIN_RESPONSE:
                conf=False;k+=1;continue
            conf=False
            if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la:
                k+=1;continue
            entry=C5[k]
            rr,ex,reason=lab53.manage_cf191g(dt5,H5,L5,C5,k,side,entry,ca)
            R[n]=rr;ST[n]=ct;ET[n]=t;EIDX[n]=k;SIDE[n]=side
            SIGZ[n]=sigz;CONFZ[n]=z;AGE[n]=(t-ct)/60.0
            MF[n]=mf;MA[n]=ma;RESP[n]=response;n+=1
            dc+=1;last=entry;la=ca;has=True;nextts=dt5[ex]+1
            k+=1;continue
        side=-1 if z>=lab53.ZTH else (1 if z<=-lab53.ZTH else 0)
        if side==0:
            k+=1;continue
        if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la:
            k+=1;continue
        conf=True;cs=side;cp=C5[k];ca=A5[k];ct=t;cb=9;mf=0.;ma=0.;sigz=z
        k+=1
    return pd.DataFrame({
        'R':R[:n],'signal_ts':ST[:n],'entry_ts':ET[:n],'entry_k':EIDX[:n],
        'side':SIDE[:n],'signal_z':SIGZ[:n],'confirm_z':CONFZ[:n],
        'confirm_age_min':AGE[:n],'pre_fav_atr':MF[:n],'pre_adv_atr':MA[:n],
        'response_ratio':RESP[:n]
    })

def add_trend_and_price(df,p):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    h1=completed_tf_state(dt5,H5,L5,C5,3600)
    h4=completed_tf_state(dt5,H5,L5,C5,14400)
    k=df.entry_k.to_numpy(np.int64);sd=df.side.to_numpy(np.int8)
    df['h1_state']=h1[k].astype(float);df['h4_state']=h4[k].astype(float)
    df['h1_h4_aligned']=((h1[k]!=0)&(h1[k]==h4[k])).astype(float)
    df['with_h1']=(sd*h1[k]).astype(float);df['with_h4']=(sd*h4[k]).astype(float)
    df['with_aligned']=np.where((h1[k]!=0)&(h1[k]==h4[k]),sd*h1[k],0).astype(float)
    pf=rolling_price_features(dt5,H5,L5,C5,A5,k,sd)
    for key,val in pf.items():df[key]=val
    df['delta_abs_z']=np.abs(df.confirm_z)-np.abs(df.signal_z)
    regime=[]
    for a,b,s in zip(h1[k],h4[k],sd):
        if a!=0 and a==b:
            regime.append('ALIGNED_WITH' if s==a else 'ALIGNED_COUNTER')
        elif a!=0 and b!=0 and a==-b:
            regime.append('CONFLICT_FOLLOW_H1' if s==a else ('CONFLICT_FOLLOW_H4' if s==b else 'CONFLICT_OTHER'))
        else:
            regime.append('MIXED_NEUTRAL')
    df['regime']=regime
    return df

def add_flow(df,flow,micro):
    ff=flow_features(flow,micro,df.entry_ts.to_numpy(np.int64))
    for key,val in ff.items():df[key]=val
    return df

def add_targets(df,p):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    k=df.entry_k.to_numpy(np.int64)
    entry_ts=df.entry_ts.to_numpy(np.int64)
    side=df.side.to_numpy(np.int8)
    atr=A5[k];entry=C5[k]
    for h in [15,30,60,120]:
        ret=np.full(len(df),np.nan);mfe=np.full(len(df),np.nan);mae=np.full(len(df),np.nan)
        imp=np.zeros(len(df),np.int8)
        for i,(t0,sd,ep,a) in enumerate(zip(entry_ts,side,entry,atr)):
            s=np.searchsorted(ts,t0,'right')
            e=np.searchsorted(ts,t0+h*60,'right')
            if s>=len(ts) or e<=s:continue
            hh=H[s:e];ll=L[s:e]
            if sd>0:
                fav=(hh-ep)/a;adv=(ep-ll)/a
            else:
                fav=(ep-ll)/a;adv=(hh-ep)/a
            mfe[i]=np.nanmax(fav);mae[i]=np.nanmax(adv)
            for q in range(len(hh)):
                fh=fav[q]>=1.0;ah=adv[q]>=0.5
                if fh or ah:
                    imp[i]=1 if (fh and not ah) else 0
                    break
            close_idx=np.searchsorted(ts,t0+h*60,'right')-1
            if close_idx>=0:
                ret[i]=sd*(C[close_idx]-ep)/a
        df[f'ret_{h}m']=ret;df[f'mfe_{h}m']=mfe;df[f'mae_{h}m']=mae;df[f'impulse{h}']=imp
    return df

def build_dataset(label,p,flow,micro):
    df=extract_cf191g_events(p)
    rr,st,side,sk=lab53.sim_cf191g(*p,False)
    if len(df)!=len(rr) or not np.allclose(df.R.to_numpy(float),rr,atol=1e-12,rtol=0):
        raise RuntimeError(f'event extractor parity failed {label}')
    exp=EXPECT[label]
    if len(df)!=exp['N'] or abs(float(df.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'LAB053 parity failed {label}: N={len(df)} SumR={df.R.sum()}')
    df=add_trend_and_price(df,p)
    df=add_flow(df,flow,micro)
    df=add_targets(df,p)
    df['dataset']=label
    df['year']=pd.to_datetime(df.entry_ts,unit='s',utc=True).dt.year.astype(int)
    return df

def make_model():
    return Pipeline([
        ('impute',SimpleImputer(strategy='median')),
        ('scale',StandardScaler()),
        ('lr',LogisticRegression(C=1.0,penalty='l2',solver='lbfgs',max_iter=2000,class_weight=None))
    ])

def eval_predictions(d,prob,period,family):
    y=d.impulse60.to_numpy(int)
    auc=float(roc_auc_score(y,prob)) if len(np.unique(y))>1 else np.nan
    brier=float(brier_score_loss(y,prob))
    x=d.copy();x['prob']=prob
    x['q']=pd.qcut(x.prob.rank(method='first'),5,labels=['Q1','Q2','Q3','Q4','Q5'])
    qrows=[]
    for q,g in x.groupby('q',observed=True):
        m=metrics_r(g.R.to_numpy(float))
        qrows.append({
            'period':period,'family':family,'quintile':str(q),'N':len(g),
            'mean_prob':float(g.prob.mean()),'impulse_rate':float(g.impulse60.mean()),
            'EV_R':m.get('EV',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),
            'MaxDD_R':m.get('MaxDD_R',np.nan),
            'ret15':float(g.ret_15m.mean()),'ret30':float(g.ret_30m.mean()),
            'ret60':float(g.ret_60m.mean()),'ret120':float(g.ret_120m.mean()),
            'mfe60':float(g.mfe_60m.mean()),'mae60':float(g.mae_60m.mean())
        })
    return {'period':period,'family':family,'N':len(d),'AUC':auc,'Brier':brier,'base_rate':float(y.mean())},qrows,x

def walk_forward(all_df):
    folds=[
      ('2024',all_df[all_df.year<=2023],all_df[all_df.year==2024]),
      ('2025',all_df[all_df.year<=2024],all_df[all_df.year==2025]),
      ('2026',all_df[all_df.year<=2025],all_df[all_df.year==2026]),
    ]
    scores=[];qrows=[];predframes=[];coefrows=[]
    for family,features in FAMILIES.items():
        for period,tr,te in folds:
            model=make_model();model.fit(tr[features],tr.impulse60.astype(int))
            prob=model.predict_proba(te[features])[:,1]
            s,q,p=eval_predictions(te,prob,period,family)
            scores.append(s);qrows.extend(q)
            z=p[['dataset','year','entry_ts','side','R','regime','impulse60','ret_15m','ret_30m','ret_60m','ret_120m','mfe_60m','mae_60m','q']].copy()
            z['period']=period;z['family']=family;z['prob']=prob
            predframes.append(z)
            if family=='FULL' and period=='2026':
                lr=model.named_steps['lr']
                for f,c in zip(features,lr.coef_[0]):
                    coefrows.append({'feature':f,'std_logit_coef':float(c),'abs_coef':float(abs(c))})
    pred=pd.concat(predframes,ignore_index=True)
    score_df=pd.DataFrame(scores);q_df=pd.DataFrame(qrows)
    coef_df=pd.DataFrame(coefrows).sort_values('abs_coef',ascending=False)
    pooled=[]
    for family in FAMILIES:
        z=pred[pred.family==family]
        y=z.impulse60.to_numpy(int);pr=z.prob.to_numpy(float)
        pooled.append({'family':family,'N':len(z),'AUC':float(roc_auc_score(y,pr)),
                       'Brier':float(brier_score_loss(y,pr)),'base_rate':float(y.mean())})
    return score_df,q_df,pred,pd.DataFrame(pooled),coef_df

def success_check(score_df,q_df,pooled_df):
    full_pool=pooled_df[pooled_df.family=='FULL'].iloc[0]
    byp=score_df[score_df.family=='FULL'].set_index('period')
    cond1=full_pool.AUC>=0.58
    cond2=all(byp.loc[p,'AUC']>0.52 for p in ['2024','2025','2026'])
    cond3=True;cond4_count=0;comp=[]
    for p in ['2024','2025','2026']:
        q=q_df[(q_df.family=='FULL')&(q_df.period==p)]
        q1=q[q.quintile=='Q1'];q5=q[q.quintile=='Q5']
        if len(q1)==0 or len(q5)==0:
            cond3=False;continue
        ir1=float(q1.iloc[0].impulse_rate);ir5=float(q5.iloc[0].impulse_rate)
        ev1=float(q1.iloc[0].EV_R);ev5=float(q5.iloc[0].EV_R)
        if not (ir5>ir1):cond3=False
        if ev5>ev1:cond4_count+=1
        comp.append({'period':p,'Q1_impulse':ir1,'Q5_impulse':ir5,'Q1_EV':ev1,'Q5_EV':ev5})
    cond4=cond4_count>=2
    best=float(pooled_df.AUC.max())
    cond5=float(full_pool.AUC)>=best-0.02
    return {'pooled_AUC_ge_058':bool(cond1),'all_period_AUC_gt_052':bool(cond2),
            'Q5_impulse_gt_Q1_all_periods':bool(cond3),'Q5_EV_gt_Q1_at_least_2of3':bool(cond4),
            'FULL_within_002_of_best_family':bool(cond5),'PASS':bool(cond1 and cond2 and cond3 and cond4 and cond5),
            'period_Q1_Q5':comp}

def regime_table(pred):
    x=pred[pred.family=='FULL'].copy();rows=[]
    for period in ['2024','2025','2026']:
        d=x[x.period==period]
        for reg,g in d.groupby('regime'):
            m=metrics_r(g.R.to_numpy(float))
            rows.append({'period':period,'regime':reg,'N':len(g),'mean_prob':float(g.prob.mean()),
                         'impulse_rate':float(g.impulse60.mean()),'EV_R':m.get('EV',np.nan),
                         'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan)})
    return pd.DataFrame(rows)

def main():
    flow=load_flow_meta();micro=load_1m_microstructure()
    ft,fz=lab43.load_flow()
    hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    dh=build_dataset('historical',hist,flow,micro)
    df=build_dataset('forward_2026',fwd,flow,micro)
    all_df=pd.concat([dh,df],ignore_index=True)
    score_df,q_df,pred,pooled_df,coef_df=walk_forward(all_df)
    reg_df=regime_table(pred);success=success_check(score_df,q_df,pooled_df)

    all_df.to_csv(OUT/'cf191g_event_features_targets.csv',index=False)
    score_df.to_csv(OUT/'walkforward_scores.csv',index=False)
    pooled_df.to_csv(OUT/'pooled_scores.csv',index=False)
    q_df.to_csv(OUT/'probability_quintiles.csv',index=False)
    pred.to_csv(OUT/'walkforward_predictions.csv',index=False)
    coef_df.to_csv(OUT/'full_model_2026_coefficients.csv',index=False)
    reg_df.to_csv(OUT/'regime_diagnostics.csv',index=False)

    result={
      'lab':'CROWDFADE_CF191G_CAUSAL_REGIME_IMPULSE_MODEL_LAB_054',
      'parity':{'historical':{'N':len(dh),'SumR':float(dh.R.sum())},
                'forward_2026':{'N':len(df),'SumR':float(df.R.sum())}},
      'target':'IMPULSE60 = +1.0 ATR before -0.5 ATR within 60m; same raw bar both => failure',
      'families':FAMILIES,'walkforward_scores':score_df.to_dict('records'),
      'pooled_scores':pooled_df.to_dict('records'),'success':success,
      'top_2026_full_coefficients':coef_df.head(12).to_dict('records'),
      'limitations':['BTCUSDT only; ETH/SOL transfer not established.',
        '2021-2025 path uses 1m OHLC; same-bar target ambiguity is scored conservatively as failure.',
        '2026 Mar-Aug uses frozen 1-second price archive for CF191g path/targets and completed Binance 1m for flow features.',
        '2026 Mar-Aug is reused forward-shadow/stress, not pristine OOS.',
        'Flat 0.5bps research cost proxy; broker-specific CFD spread/slippage is not modeled.',
        'Shadow scoring only; no hard veto or risk multiplier is promoted.']
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))
    lines=['# LAB054 — CF191G CAUSAL REGIME IMPULSE MODEL','',
      'Signal core unchanged. Shadow/meta-model only.','',
      '## Parity','',
      f"- Historical 2021–2025: N={len(dh)}, SumR={dh.R.sum():+.6f}",
      f"- 2026 Mar–Aug: N={len(df)}, SumR={df.R.sum():+.6f}",'',
      '## Walk-forward scores','',score_df.to_markdown(index=False),'',
      '## Pooled walk-forward','',pooled_df.to_markdown(index=False),'',
      '## Pre-registered success criteria','',json.dumps(success,indent=2),'',
      '## FULL probability quintiles','',q_df[q_df.family=='FULL'].to_markdown(index=False),'',
      '## Regime diagnostics','',reg_df.to_markdown(index=False),'',
      '## Standardized FULL coefficients for 2026 fold','',coef_df.to_markdown(index=False),'',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
