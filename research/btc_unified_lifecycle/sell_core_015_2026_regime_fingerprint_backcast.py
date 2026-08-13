#!/usr/bin/env python3
"""SELL_CORE_015 — 2026_REGIME_FINGERPRINT_AND_BACKCAST.

Question: what causal market state makes the frozen B3 x exact-LH+BOS construction behave
very differently in 2026, and did the same state ever work in older years?

No P/L enters the fingerprint model. 2026 is a regime CLASS LABEL, never a feature.
Primary unit = first B3xLH+BOS event per continuous H4 Supertrend episode on the original
:20 hourly grid. This prevents repeated entries from pretending to be independent regimes.

Frozen causal features at the first event:
1 st_age
2 h4_bear_ema20_dist_atr
3 h4_ema20_bear_slope_6
4 h4_bear_efficiency_6
5 h1_bear_ema20_dist_atr
6 h1_ema20_bear_slope_4
7 lh_depth_atr
8 bos_depth_atr
9 swing_high_spacing_h
10 rv168

Model = StandardScaler + LogisticRegression(L2, C=1, class_weight='balanced').
Backcast = leave-one-old-year-out (2020..2025). In each fold train 2026 vs all OTHER old
years, score the held-out old year, rank held-out episodes into TOP/MID/BOTTOM terciles of
2026-likeness, then inspect frozen canonical 48h SELL P/L. The classifier never sees P/L.

Primary transfer question: does TOP outperform BOTTOM in held-out old years, and is TOP
itself positive? Full-sample coefficients/effect sizes are descriptive fingerprint only.
"""
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

OUT=Path('sell_core_015_out'); OUT.mkdir(exist_ok=True)
FEATURES=['st_age','h4_bear_ema20_dist_atr','h4_ema20_bear_slope_6','h4_bear_efficiency_6',
          'h1_bear_ema20_dist_atr','h1_ema20_bear_slope_4','lh_depth_atr','bos_depth_atr',
          'swing_high_spacing_h','rv168']
SEED=415015; BOOT=20000


def load014():
    p=Path('sell_core_014_b3_lhbos_long_history.py'); s=p.read_text()
    bad="prim=S[(S.phase_min==20)&(((S.view=='NATIVE')&(S.hold_h==48))|((S.view=='CANONICAL')&(S.hold_h.isin([48,72])))]"
    good="prim=S[(S.phase_min==20)&(((S.view=='NATIVE')&(S.hold_h==48))|((S.view=='CANONICAL')&(S.hold_h.isin([48,72]))))]"
    if bad in s: s=s.replace(bad,good,1)
    ns={'__name__':'sell014','__file__':str(p)}; exec(compile(s,str(p),'exec'),ns); return ns


def ema(s,n): return pd.Series(s).ewm(span=n,adjust=False,min_periods=n).mean().to_numpy()

def wilder(s,n): return pd.Series(s).ewm(alpha=1/n,adjust=False,min_periods=n).mean().to_numpy()


def build_h1_exact(m1):
    N=len(m1); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float); C=m1.close.to_numpy(float); O=m1.open.to_numpy(float)
    nb=(N+59)//60; rows=[]
    for k in range(nb):
        a=k*60; b=min(a+60,N)
        rows.append((k,m1.time.iloc[a],O[a],H[a:b].max(),L[a:b].min(),C[b-1]))
    h=pd.DataFrame(rows,columns=['k','time','open','high','low','close'])
    pc=h.close.shift(1); tr=pd.concat([h.high-h.low,(h.high-pc).abs(),(h.low-pc).abs()],axis=1).max(axis=1)
    h['atr14']=pd.Series(tr).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    h['ema20']=pd.Series(h.close).ewm(span=20,adjust=False,min_periods=20).mean()
    lr=np.log(h.close/h.close.shift(1)); h['rv168']=np.sqrt((lr*lr).rolling(168,min_periods=168).sum())
    return h


def swing_detail(h,k,LR=2,LB=120):
    hh=h.high.to_numpy(float); hl=h.low.to_numpy(float); hs=[]; ls=[]
    for b in range(k-LR,max(k-LB,LR),-1):
        if len(hs)<3 and all(hh[b]>=hh[b+d] for d in range(-LR,LR+1)): hs.append((b,hh[b]))
        if len(ls)<3 and all(hl[b]<=hl[b+d] for d in range(-LR,LR+1)): ls.append((b,hl[b]))
        if len(hs)>=3 and len(ls)>=3: break
    return hs,ls


def build_h4_features(m5,base):
    x=base.resample(m5,'4h'); pc=x.close.shift(1)
    tr=pd.concat([x.high-x.low,(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr10']=pd.Series(tr).ewm(alpha=1/10,adjust=False,min_periods=10).mean()
    x['ema20']=pd.Series(x.close).ewm(span=20,adjust=False,min_periods=20).mean()
    x['h4_bear_ema20_dist_atr']=(x.ema20-x.close)/x.atr10
    x['h4_ema20_bear_slope_6']=(x.ema20.shift(6)-x.ema20)/x.atr10
    path=x.close.diff().abs().rolling(6,min_periods=6).sum()
    x['h4_bear_efficiency_6']=(x.close.shift(6)-x.close)/path
    # BAR_OPEN lag1: feature known at H4-open t is previous completed raw H4 bar.
    cols=['h4_bear_ema20_dist_atr','h4_ema20_bear_slope_6','h4_bear_efficiency_6']
    for c in cols: x[c]=x[c].shift(1)
    return x[['time']+cols].dropna().sort_values('time')


def make_episode_table(m1,m5,mod):
    H,L,C,a60,labels,h4,h1_mod=mod['prep'](m1,m5)
    # In SELL_CORE_014 START_WARMUP=20000 => phase=0 timestamps are :20, the original user grid.
    c=mod['clocks'](m1,labels,h4,0)
    q=c[c.intersection].sort_values('time').groupby('episode_id',as_index=False).first()
    # frozen canonical 48h P/L on the same first events
    pnl=mod['canonical_replay'](q,m1,H,h1_mod,48)[['episode_id','time','R','pct','exit_type']].rename(columns={'R':'R48','pct':'pct48'})
    h1=build_h1_exact(m1); h4f=build_h4_features(m5,mod['base'])
    q=pd.merge_asof(q.sort_values('time'),h4f,on='time',direction='backward')
    feats=[]
    for r in q.itertuples(index=False):
        k=int(r.k); p=k-1
        if p<10 or p>=len(h1): continue
        atr=float(h1.atr14.iloc[p]); e20=float(h1.ema20.iloc[p]); cl=float(h1.close.iloc[p]); rv=float(h1.rv168.iloc[p])
        if not np.isfinite(atr) or atr<=0 or not np.isfinite(e20) or not np.isfinite(rv): continue
        hs,ls=swing_detail(h1,k)
        if len(hs)<2 or len(ls)<1: continue
        # exact detector conditions must still hold
        if not (hs[0][1]<hs[1][1] and cl<ls[0][1]): continue
        slope=(float(h1.ema20.iloc[p-4])-e20)/atr if p>=4 and np.isfinite(h1.ema20.iloc[p-4]) else np.nan
        d=r._asdict(); d.update(
            h1_bear_ema20_dist_atr=(e20-cl)/atr,
            h1_ema20_bear_slope_4=slope,
            lh_depth_atr=(hs[1][1]-hs[0][1])/atr,
            bos_depth_atr=(ls[0][1]-cl)/atr,
            swing_high_spacing_h=float(hs[0][0]-hs[1][0]),
            rv168=rv,
            regime_2026=int(pd.Timestamp(r.time).year==2026),
            year=int(pd.Timestamp(r.time).year),
        ); feats.append(d)
    F=pd.DataFrame(feats).merge(pnl,on=['episode_id','time'],how='inner')
    F=F.dropna(subset=FEATURES+['R48','pct48']).sort_values('time').reset_index(drop=True)
    return F,c


def cohend(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    va=np.var(a,ddof=1); vb=np.var(b,ddof=1); sp=np.sqrt(((len(a)-1)*va+(len(b)-1)*vb)/(len(a)+len(b)-2))
    return float((np.mean(a)-np.mean(b))/sp) if sp>0 else np.nan


def fit_model(train):
    X=train[FEATURES].to_numpy(float); y=train.regime_2026.to_numpy(int)
    sc=StandardScaler().fit(X); Z=sc.transform(X)
    lr=LogisticRegression(C=1.0,penalty='l2',class_weight='balanced',solver='liblinear',random_state=SEED,max_iter=5000).fit(Z,y)
    return sc,lr


def score(model,df):
    sc,lr=model; return lr.predict_proba(sc.transform(df[FEATURES].to_numpy(float)))[:,1]


def tercile_labels(s):
    # deterministic rank terciles; avoids threshold tuning and tie problems
    n=len(s); order=np.argsort(np.argsort(np.asarray(s,float),kind='mergesort'),kind='mergesort')
    frac=(order+0.5)/n
    return np.where(frac<1/3,'BOTTOM',np.where(frac<2/3,'MID','TOP'))


def metrics(g):
    if len(g)==0:return {'N':0,'EV_R':np.nan,'PF_R':np.nan,'EV_pct':np.nan}
    z=g.R48.to_numpy(float); gp=z[z>0].sum(); gl=-z[z<0].sum(); pf=gp/gl if gl>0 else np.nan
    return {'N':len(g),'EV_R':float(np.mean(z)),'PF_R':float(pf),'EV_pct':float(g.pct48.mean())}


def boot_delta(top,bot,seed):
    a=top.R48.to_numpy(float); b=bot.R48.to_numpy(float)
    if len(a)<2 or len(b)<2:return (np.nan,np.nan,np.nan)
    rng=np.random.default_rng(seed); v=np.empty(BOOT)
    for i in range(BOOT): v[i]=rng.choice(a,len(a),True).mean()-rng.choice(b,len(b),True).mean()
    return float(np.quantile(v,.025)),float(np.quantile(v,.975)),float((v>0).mean())


def loeo_backcast(F):
    oldyears=sorted(y for y in F.year.unique() if y<2026); rows=[]; scored=[]
    for y in oldyears:
        train=F[(F.year==2026)|((F.year<2026)&(F.year!=y))].copy(); test=F[F.year==y].copy()
        if train.regime_2026.sum()<2 or len(test)<3: continue
        mdl=fit_model(train); test['score_2026like']=score(mdl,test); test['rank']=tercile_labels(test.score_2026like)
        scored.append(test)
        top=test[test['rank']=='TOP']; bot=test[test['rank']=='BOTTOM']
        lo,hi,p=boot_delta(top,bot,SEED+y)
        r={'holdout_year':int(y),'episodes':len(test),'top_minus_bottom_R':float(top.R48.mean()-bot.R48.mean()),'CI_lo':lo,'CI_hi':hi,'P_delta_gt0':p}
        for lab,g in test.groupby('rank'):
            for k,v in metrics(g).items(): r[f'{lab}_{k}']=v
        rows.append(r)
    return pd.DataFrame(rows),pd.concat(scored,ignore_index=True)


def loo_auc(F):
    # episode-level leave-one-out separability diagnostic; no P/L involved
    pr=[]; yy=[]
    for i in range(len(F)):
        tr=F.drop(index=F.index[i]); te=F.iloc[[i]]
        if tr.regime_2026.nunique()<2: continue
        mdl=fit_model(tr); pr.append(score(mdl,te)[0]); yy.append(int(te.regime_2026.iloc[0]))
    return float(roc_auc_score(yy,pr)) if len(set(yy))==2 else np.nan


def main():
    mod=load014(); m1,m5,start,npre,nfr=mod['load_long'](); F,clocks=make_episode_table(m1,m5,mod)
    F.to_csv(OUT/'episode_fingerprints.csv',index=False)
    # descriptive full-sample fingerprint
    mdl=fit_model(F); sc,lr=mdl
    coef=pd.DataFrame({'feature':FEATURES,'coef_std':lr.coef_[0]})
    old=F[F.year<2026]; new=F[F.year==2026]
    shifts=[]
    for f in FEATURES:
        shifts.append({'feature':f,'old_mean':float(old[f].mean()),'y2026_mean':float(new[f].mean()),'cohen_d_2026_minus_old':cohend(new[f],old[f])})
    SHIFT=pd.DataFrame(shifts).merge(coef,on='feature'); SHIFT['abs_coef']=SHIFT.coef_std.abs(); SHIFT=SHIFT.sort_values('abs_coef',ascending=False)
    SHIFT.to_csv(OUT/'fingerprint_feature_shifts.csv',index=False)
    # primary LOYO backcast
    BC,SCORED=loeo_backcast(F); BC.to_csv(OUT/'loyo_backcast_yearly.csv',index=False); SCORED.to_csv(OUT/'loyo_scored_old_episodes.csv',index=False)
    pool=[]
    for lab,g in SCORED.groupby('rank'):
        x={'rank':lab,**metrics(g)}; pool.append(x)
    POOL=pd.DataFrame(pool); POOL.to_csv(OUT/'loyo_backcast_pooled.csv',index=False)
    top=SCORED[SCORED['rank']=='TOP']; bot=SCORED[SCORED['rank']=='BOTTOM']; lo,hi,p=boot_delta(top,bot,SEED+999)
    pooled_delta={'delta_R':float(top.R48.mean()-bot.R48.mean()),'CI_lo':lo,'CI_hi':hi,'P_gt0':p,'top_N':len(top),'bottom_N':len(bot)}
    # 2026 descriptive outcomes only, not used in fingerprint training objective
    y26=metrics(new)
    # classifier separability
    auc=loo_auc(F)
    # full sample score distribution diagnostic
    F['full_score_2026like']=score(mdl,F); F[['episode_id','time','year','regime_2026','R48','pct48','full_score_2026like']].to_csv(OUT/'full_model_scores_diagnostic.csv',index=False)
    lines=['# SELL_CORE_015 — 2026_REGIME_FINGERPRINT_AND_BACKCAST','',
           '## Causal design','',
           '- Primary unit: first B3×LH+BOS event per H4 ST episode on original :20 grid.',
           '- Fingerprint target: 2026 regime class vs 2020–2025; **P/L is never used to fit the classifier**.',
           '- Backcast: leave-one-old-year-out; TOP/MID/BOTTOM are within-held-year terciles of 2026-likeness.','',
           '## Census','',
           f'- Independent episodes with complete frozen features: **{len(F)}**.',
           f'- 2026 episodes: **{len(new)}**; 2020–2025 episodes: **{len(old)}**.',
           f'- Episode-level leave-one-out regime-classification AUC: **{auc:.3f}**.','',
           '## Descriptive 2026 fingerprint (NO P/L feature selection)','',SHIFT.to_markdown(index=False),'',
           '## Primary leave-one-old-year-out backcast','',BC.to_markdown(index=False),'',
           '## Pooled LOYO backcast','',POOL.to_markdown(index=False),'',
           f"TOP−BOTTOM pooled R = **{pooled_delta['delta_R']:+.4f}R**, CI [{pooled_delta['CI_lo']:+.4f}, {pooled_delta['CI_hi']:+.4f}], P(delta>0)={pooled_delta['P_gt0']:.3f}.",'',
           '## 2026 descriptive frozen outcome','',
           f"N={y26['N']}, EV48={y26['EV_R']:+.4f}R, PF={y26['PF_R']:.3f}, price EV={y26['EV_pct']:+.4f}%.",'',
           '## Interpretation boundary','',
           '- PASS for a transferable regime requires held-out old-year TOP to consistently beat BOTTOM and preferably be positive itself.',
           '- Strong 2026 classification with failed old-year backcast means the fingerprint describes 2026 but does not recover a historical tradable regime.',
           '- No threshold from coefficients or feature shifts may be promoted from this lab; any single-feature router needs separate preregistration.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
