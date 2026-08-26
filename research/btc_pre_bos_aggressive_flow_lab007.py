import os, glob, json, math, zipfile
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

START = pd.Timestamp('2023-01-01 00:00:00')
PIV_L=PIV_R=2
ATR_P=14
BREAK_BUF=.05
STOP_BUF=.15
MIN_STOP=.25
MAX_STOP=3.0
PATH_BARS=32
LARGE_R=2.5
EXTREME_R=4.0
FAIL_R=1.0
BASE=96
WINDOWS=(3,6,12,24)
MIN_NEUTRAL=15


def load_m15(folder):
    parts=[]
    for p in sorted(glob.glob(os.path.join(folder,'**','*.csv'),recursive=True)):
        d=pd.read_csv(p)
        if not {'time','open','high','low','close','volume','trades','taker_ratio','avg_trade'}.issubset(d.columns):
            continue
        d['time']=pd.to_datetime(d.time,format='%Y.%m.%d %H:%M',errors='coerce')
        parts.append(d)
    d=pd.concat(parts,ignore_index=True).dropna(subset=['time']).sort_values('time')
    d=d.drop_duplicates('time',keep='last').reset_index(drop=True)
    for c in ['open','high','low','close','volume','trades','taker_ratio','avg_trade']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna().reset_index(drop=True)
    return d


def atr_sma(d,p=14):
    pc=d.close.shift(1)
    tr=pd.concat([(d.high-d.low),(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1)
    return tr.rolling(p,min_periods=p).mean().to_numpy(float)


def make_h1(m):
    z=m.set_index('time')
    h=z.resample('1h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'))
    return h.dropna().reset_index()


def build_pivots(d,sec,left=2,right=2):
    H=d.high.to_numpy(float); L=d.low.to_numpy(float); T=d.time.to_numpy('datetime64[ns]')
    out=[]
    dt=np.timedelta64(sec,'s')
    n=len(d)
    for i in range(left,n-right):
        hi=all(H[i]>H[i-k] for k in range(1,left+1)) and all(H[i]>H[i+k] for k in range(1,right+1))
        lo=all(L[i]<L[i-k] for k in range(1,left+1)) and all(L[i]<L[i+k] for k in range(1,right+1))
        ct=T[i+right]+dt
        if hi: out.append((ct,T[i],H[i],1,i))
        if lo: out.append((ct,T[i],L[i],0,i))
    return out


def state(hc,ph,lh,lc,pl,ll):
    if hc<2 or lc<2:return 0
    if lh>ph and ll>pl:return 1
    if lh<ph and ll<pl:return -1
    return 0


def generate_signals(m,atr,hp,lp):
    T=m.time.to_numpy('datetime64[ns]'); C=m.close.to_numpy(float)
    hptr=lptr=0; hc=lc=l_hc=l_lc=0
    ph=lh=pl=ll=l_ph=l_lh=l_pl=l_ll=0.0
    buycorr=sellcorr=False; buybreak=sellbreak=buystop=sellstop=0.0
    sig=[]; dt=np.timedelta64(15,'m')
    for i in range(len(m)):
        bc=T[i]+dt
        while hptr<len(hp) and hp[hptr][0]<=bc:
            p=hp[hptr]
            if p[3]:
                if hc>=1: ph=lh
                lh=p[2]; hc+=1
            else:
                if lc>=1: pl=ll
                ll=p[2]; lc+=1
            hptr+=1
        while lptr<len(lp) and lp[lptr][0]<=bc:
            p=lp[lptr]
            if p[3]:
                if l_hc>=1:l_ph=l_lh
                l_lh=p[2]; l_hc+=1
                if buycorr: buybreak=p[2]
                if sellcorr: sellstop=p[2]
            else:
                if l_lc>=1:l_pl=l_ll
                l_ll=p[2]; l_lc+=1
                if buycorr: buystop=p[2]
                if sellcorr: sellbreak=p[2]
            lptr+=1
        hs=state(hc,ph,lh,lc,pl,ll); ls=state(l_hc,l_ph,l_lh,l_lc,l_pl,l_ll)
        if hs!=1: buycorr=False
        if hs!=-1: sellcorr=False
        if hs==1 and ls==-1 and l_hc>=1 and l_lc>=1:
            buycorr=True; buybreak=l_lh; buystop=l_ll
        if hs==-1 and ls==1 and l_hc>=1 and l_lc>=1:
            sellcorr=True; sellbreak=l_ll; sellstop=l_lh
        if pd.Timestamp(T[i])<START or not np.isfinite(atr[i]) or atr[i]<=0: continue
        a=atr[i]
        if buycorr and hs==1 and buybreak>0 and buystop>0 and C[i]>buybreak+BREAK_BUF*a:
            sig.append(dict(signal_time=pd.Timestamp(bc),bar_index=i,direction=1,break_level=buybreak,protected_stop=buystop,atr=a,year=pd.Timestamp(bc).year)); buycorr=False
        if sellcorr and hs==-1 and sellbreak>0 and sellstop>0 and C[i]<sellbreak-BREAK_BUF*a:
            sig.append(dict(signal_time=pd.Timestamp(bc),bar_index=i,direction=-1,break_level=sellbreak,protected_stop=sellstop,atr=a,year=pd.Timestamp(bc).year)); sellcorr=False
    return sig


def mean_sd(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)<5:return (np.nan,np.nan)
    return float(x.mean()),float(x.std(ddof=0))

def zmean(feature, baseline):
    mu,sd=mean_sd(baseline)
    if not np.isfinite(sd) or sd<=0:return 0.0
    return (float(np.mean(feature))-mu)/sd


def win_features(m,i,direction,atr,n):
    a=i-n; b=i
    if a<BASE+1:return {}
    x=m.iloc[a:b]
    base=m.iloc[a-BASE:a]
    start=float(x.close.iloc[0]); end=float(x.close.iloc[-1])
    prog=direction*(end-start)/atr
    path=float(np.abs(np.diff(x.close.to_numpy(float))).sum()/atr)
    eff=prog/path if path>0 else 0.0
    counter_prog=max(0.0,-prog)
    vol=x.volume.to_numpy(float); tr=x.trades.to_numpy(float); ratio=x.taker_ratio.clip(0,1).to_numpy(float)
    buy=vol*ratio; sell=vol-buy
    fut=buy if direction>0 else sell; ctr=sell if direction>0 else buy
    tot=max(float(vol.sum()),1e-12)
    fut_share=float(fut.sum()/tot); ctr_share=float(ctr.sum()/tot); delta=float((fut.sum()-ctr.sum())/tot)
    bvol=base.volume.to_numpy(float); brat=base.taker_ratio.clip(0,1).to_numpy(float); bbuy=bvol*brat; bsell=bvol-bbuy
    bfut=bbuy if direction>0 else bsell; bctr=bsell if direction>0 else bbuy
    ctr_excess=max(0.0,ctr_share-.5)
    absorb=ctr_excess/(0.10+counter_prog)
    signed_body=direction*(x.close.to_numpy(float)-x.open.to_numpy(float))
    against=float(np.mean(signed_body<0))
    ranges=(x.high-x.low).to_numpy(float); branges=(base.high-base.low).to_numpy(float)
    return {
      f'progress_{n}':prog,f'efficiency_{n}':eff,f'counter_progress_{n}':counter_prog,
      f'effort_without_progress_{n}':min(20.0,path/max(abs(prog),.10)),f'against_ratio_{n}':against,
      f'flow_delta_{n}':delta,f'future_share_{n}':fut_share,f'counter_share_{n}':ctr_share,
      f'counter_volume_z_{n}':zmean(ctr,bctr),f'future_volume_z_{n}':zmean(fut,bfut),
      f'total_volume_z_{n}':zmean(vol,bvol),f'trades_z_{n}':zmean(tr,base.trades.to_numpy(float)),
      f'avg_trade_z_{n}':zmean(x.avg_trade.to_numpy(float),base.avg_trade.to_numpy(float)),
      f'range_z_{n}':zmean(ranges,branges),f'counter_absorption_{n}':min(10.0,absorb)
    }


def build_event(m,atr,s):
    i=s['bar_index']; a=s['atr']
    if i-24-BASE<1:return None
    entry=float(m.close.iloc[i]); sl=s['protected_stop']-STOP_BUF*a if s['direction']>0 else s['protected_stop']+STOP_BUF*a
    risk=abs(entry-sl)
    if risk<=0:return None
    stop_atr=risk/a
    if stop_atr<MIN_STOP or stop_atr>MAX_STOP:return None
    br=(entry-s['break_level'])/a if s['direction']>0 else (s['break_level']-entry)/a
    am=np.nanmean(atr[max(0,i-BASE):i]); atr_reg=a/am if am>0 else 0
    raw_mfe=raw_mae=clean=0.0; alive=True; first_sl=-1; first_1r=-1
    last=min(len(m)-1,i+PATH_BARS)
    for j in range(i+1,last+1):
        k=j-i; hi=float(m.high.iloc[j]); lo=float(m.low.iloc[j])
        fav=max(0.0,hi-entry) if s['direction']>0 else max(0.0,entry-lo)
        adv=max(0.0,entry-lo) if s['direction']>0 else max(0.0,hi-entry)
        raw_mfe=max(raw_mfe,fav); raw_mae=max(raw_mae,adv)
        hit_sl=(lo<=sl) if s['direction']>0 else (hi>=sl)
        tgt=entry+s['direction']*FAIL_R*risk
        hit1=(hi>=tgt) if s['direction']>0 else (lo<=tgt)
        if alive and first_1r<0 and hit1 and not hit_sl: first_1r=k
        if alive and not hit_sl: clean=max(clean,fav)
        if alive and hit_sl: first_sl=k; alive=False
    e={**s,'entry':entry,'sl':sl,'risk':risk,'stop_atr':stop_atr,'break_distance_atr':br,'atr_regime_ratio':atr_reg,
       'clean_mfe_r':clean/risk,'raw_mfe_r':raw_mfe/risk,'raw_mae_r':raw_mae/risk,
       'is_large':int(clean/risk>=LARGE_R),'is_extreme':int(clean/risk>=EXTREME_R),'is_fail':int(first_sl>0 and first_1r<0)}
    for n in WINDOWS:e.update(win_features(m,i,s['direction'],a,n))
    def weighted_delta(a0,b0):
        x=m.iloc[a0:b0]; v=x.volume.to_numpy(float); q=x.taker_ratio.clip(0,1).to_numpy(float); buy=v*q; sell=v-buy
        fut=buy if s['direction']>0 else sell; ctr=sell if s['direction']>0 else buy; tot=max(v.sum(),1e-12)
        return float((fut.sum()-ctr.sum())/tot)
    if i>=12:
        d3=weighted_delta(i-3,i); p3=weighted_delta(i-6,i-3); p9=weighted_delta(i-12,i-3)
        e['flow_flip_3v3']=d3-p3; e['flow_flip_3v9']=d3-p9
        e['counter_share_decay_3v3']=-(d3-p3)/2.0
    return e


def bbreak(x):
    return 'B0' if x<.10 else 'B1' if x<.20 else 'B2' if x<.35 else 'B3' if x<.60 else 'B4' if x<.80 else 'B5'
def bstop(x):
    return 'S0' if x<.75 else 'S1' if x<1.25 else 'S2' if x<1.75 else 'S3' if x<2.5 else 'S4'
def bvol(x):return 'V0' if x<.8 else 'V1' if x<1.2 else 'V2'

def assign_expected(e):
    e=e.copy(); e['fullkey']=[f"{d}|{y}|{bbreak(b)}|{bstop(s)}|{bvol(v)}" for d,y,b,s,v in zip(e.direction,e.year,e.break_distance_atr,e.stop_atr,e.atr_regime_ratio)]
    e['coarsekey']=[f"{d}|{y}" for d,y in zip(e.direction,e.year)]
    full=e.groupby('fullkey').is_large.agg(['mean','size']); coarse=e.groupby('coarsekey').is_large.mean(); globalr=e.is_large.mean()
    ex=[]
    for r in e.itertuples():
        f=full.loc[r.fullkey]; ex.append(float(f['mean']) if f['size']>=MIN_NEUTRAL else float(coarse.get(r.coarsekey,globalr)))
    e['expected']=ex
    return e


def metric_row(name,g):
    if len(g)==0:return dict(name=name,n=0,large=0,rate=np.nan,expected=np.nan,lift_pp=np.nan)
    rate=g.is_large.mean(); exp=g.expected.mean()
    return dict(name=name,n=len(g),large=int(g.is_large.sum()),rate=rate,expected=exp,lift_pp=100*(rate-exp))


def eval_model(train,test,features):
    Xtr=train[features]; ytr=train.is_large; Xte=test[features]; yte=test.is_large
    model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(C=.35,max_iter=3000,class_weight=None))
    model.fit(Xtr,ytr); p=model.predict_proba(Xte)[:,1]
    return dict(auc=roc_auc_score(yte,p),ap=average_precision_score(yte,p),brier=brier_score_loss(yte,p),top20_rate=float(yte[p>=np.quantile(p,.80)].mean()),top20_n=int((p>=np.quantile(p,.80)).sum()))


def main():
    m=load_m15('btc15')
    print('M15',len(m),m.time.min(),m.time.max())
    h=make_h1(m); atr=atr_sma(m); hp=build_pivots(h,3600); lp=build_pivots(m,900)
    sig=generate_signals(m,atr,hp,lp)
    ev=[]
    for s in sig:
        e=build_event(m,atr,s)
        if e is not None:ev.append(e)
    e=assign_expected(pd.DataFrame(ev))
    print('NATIVE_BINANCE_CORE signals',len(sig),'events',len(e),'LARGE',int(e.is_large.sum()),'rate',round(100*e.is_large.mean(),3),'EXTREME',int(e.is_extreme.sum()),'FAIL',int(e.is_fail.sum()))
    for y,g in e.groupby('year'):print('YEAR',y,'N',len(g),'LARGE_RATE',round(100*g.is_large.mean(),2))
    print('DIR',e.groupby('direction').is_large.agg(['size','sum','mean']).to_string())

    flow=[c for c in e.columns if c.startswith(('flow_','future_share_','counter_share_','counter_volume_z_','future_volume_z_','total_volume_z_','trades_z_','avg_trade_z_','counter_absorption_'))]
    rows=[]
    for c in flow:
        a=e.loc[e.is_large==1,c].mean(); b=e.loc[e.is_large==0,c].mean(); sd=e[c].std(ddof=0); rows.append((c,a,b,a-b,(a-b)/sd if sd>0 else 0))
    means=pd.DataFrame(rows,columns=['feature','large_mean','nonlarge_mean','diff','std_effect']).sort_values('std_effect',key=lambda x:x.abs(),ascending=False)
    print('\nFLOW LARGE VS NONLARGE MEANS\n',means.head(20).to_string(index=False))

    train=e[e.year<=2025].copy(); test=e[e.year==2026].copy()
    print('\nSPLIT train',len(train),'test2026',len(test),'train_large',train.is_large.mean(),'test_large',test.is_large.mean())

    q_cs=float(train.counter_share_6.quantile(.65)); q_cp=float(train.counter_progress_6.quantile(.50)); q_flip=float(train.flow_flip_3v3.quantile(.55))
    rules={
      'ABSORB_6': lambda d:(d.counter_share_6>=q_cs)&(d.counter_progress_6<=q_cp),
      'ABSORB_6_X_FLIP':lambda d:(d.counter_share_6>=q_cs)&(d.counter_progress_6<=q_cp)&(d.flow_flip_3v3>=q_flip),
      'FLOW_FLIP_ONLY':lambda d:d.flow_flip_3v3>=q_flip,
      'COUNTER_SHARE_HIGH':lambda d:d.counter_share_6>=q_cs,
    }
    rr=[]
    print('\nFROZEN RULES thresholds counter_share6>=',q_cs,'counter_progress6<=',q_cp,'flip3v3>=',q_flip)
    for name,fn in rules.items():
        tr=train[fn(train)]; te=test[fn(test)]; rtr=metric_row(name+'_TRAIN',tr); rte=metric_row(name+'_2026',te); rr.extend([rtr,rte]); print(rtr); print(rte)
    rulesdf=pd.DataFrame(rr)

    price_features=['break_distance_atr','stop_atr','atr_regime_ratio','direction']
    for n in WINDOWS: price_features += [f'progress_{n}',f'efficiency_{n}',f'effort_without_progress_{n}',f'against_ratio_{n}',f'range_z_{n}']
    flow_features=flow
    pm=eval_model(train,test,price_features); fm=eval_model(train,test,price_features+flow_features)
    print('\nMODEL 2026 PRICE_ONLY',pm)
    print('MODEL 2026 PRICE_PLUS_FLOW',fm)
    print('FLOW_INCREMENT AUC',fm['auc']-pm['auc'],'AP',fm['ap']-pm['ap'],'BRIER_IMPROVEMENT',pm['brier']-fm['brier'])

    surf=[]
    for c in flow:
        try: qs=np.unique(train[c].quantile([0,.2,.4,.6,.8,1]).to_numpy(float))
        except: continue
        if len(qs)<3:continue
        for k in range(len(qs)-1):
            lo,hi=qs[k],qs[k+1]
            mt=(train[c]>=lo)&(train[c]<=hi if k==len(qs)-2 else train[c]<hi)
            ms=(test[c]>=lo)&(test[c]<=hi if k==len(qs)-2 else test[c]<hi)
            g=train[mt]
            if len(g)<60 or g.is_large.sum()<8:continue
            rt=metric_row(f'{c}|Q{k+1}',g); ro=metric_row(f'{c}|Q{k+1}',test[ms])
            surf.append(dict(feature=c,bin=k+1,lo=lo,hi=hi,train_n=rt['n'],train_rate=rt['rate'],train_exp=rt['expected'],train_lift_pp=rt['lift_pp'],test_n=ro['n'],test_rate=ro['rate'],test_exp=ro['expected'],test_lift_pp=ro['lift_pp']))
    surf=pd.DataFrame(surf)
    stable=surf[(surf.train_lift_pp>2.0)&(surf.test_n>=15)].sort_values(['test_lift_pp','train_lift_pp'],ascending=False)
    print('\nTOP FROZEN FLOW QUINTILES POSITIVE TRAIN -> 2026\n',stable.head(20).to_string(index=False))

    os.makedirs('lab007',exist_ok=True)
    e.to_csv('lab007/BTC_PRE_BOS_AGGRESSIVE_FLOW_X_LARGE_BREAKOUT_LAB_007_EVENTS.csv',index=False)
    means.to_csv('lab007/BTC_PRE_BOS_AGGRESSIVE_FLOW_X_LARGE_BREAKOUT_LAB_007_MEANS.csv',index=False)
    rulesdf.to_csv('lab007/BTC_PRE_BOS_AGGRESSIVE_FLOW_X_LARGE_BREAKOUT_LAB_007_RULES.csv',index=False)
    surf.to_csv('lab007/BTC_PRE_BOS_AGGRESSIVE_FLOW_X_LARGE_BREAKOUT_LAB_007_SURFACE.csv',index=False)
    verdict={
      'native_binance':True,'source':'BTCUSDT Binance 15m release asset','start':str(e.signal_time.min()),'end':str(e.signal_time.max()),
      'signals':len(sig),'events':len(e),'large':int(e.is_large.sum()),'large_rate':float(e.is_large.mean()),'extreme':int(e.is_extreme.sum()),'fail':int(e.is_fail.sum()),
      'mt5_reference':{'events':1601,'large':234,'large_rate':0.1462},'rules':rr,'price_model_2026':pm,'price_plus_flow_model_2026':fm,
      'flow_auc_increment':fm['auc']-pm['auc'],'flow_ap_increment':fm['ap']-pm['ap'],'flow_brier_improvement':pm['brier']-fm['brier']
    }
    with open('lab007/verdict.json','w') as f:json.dump(verdict,f,indent=2)
    lines=['# BTC_PRE_BOS_AGGRESSIVE_FLOW_X_LARGE_BREAKOUT_LAB_007','',
      'Native Binance replication. LAB005/006 event logic was ported from the frozen MQL5 research script; BTCUSDT 15m Binance bars provide taker-ratio aggressive-flow proxies.','',
      f"Signals: {len(sig)} | executable: {len(e)} | LARGE: {int(e.is_large.sum())} ({100*e.is_large.mean():.2f}%) | EXTREME: {int(e.is_extreme.sum())}",
      f"MT5 reference: 1601 executable, 234 LARGE (14.62%). Coverage ends {e.signal_time.max()} because the frozen Binance release ends Aug 9.",'',
      '## Frozen 2026 model test','',
      f"Price-only AUC {pm['auc']:.4f}, AP {pm['ap']:.4f}, Brier {pm['brier']:.4f}.",
      f"Price+flow AUC {fm['auc']:.4f}, AP {fm['ap']:.4f}, Brier {fm['brier']:.4f}.",
      f"Increment: AUC {fm['auc']-pm['auc']:+.4f}, AP {fm['ap']-pm['ap']:+.4f}, Brier improvement {pm['brier']-fm['brier']:+.4f}.",'',
      '## Frozen participant rules','',rulesdf.to_markdown(index=False),'','## Strongest flow means','',means.head(15).to_markdown(index=False),'','## Positive train quintiles and 2026 replication','',stable.head(15).to_markdown(index=False)]
    with open('lab007/BTC_PRE_BOS_AGGRESSIVE_FLOW_X_LARGE_BREAKOUT_LAB_007_REPORT.md','w') as f:f.write('\n'.join(lines))

if __name__=='__main__':main()
