#!/usr/bin/env python3
"""SELL_CORE_003 — B3 × HTF_FLIP_COUNT_7D.

Frozen interpretation (old exact implementation not found in repo):
- canonical market clock = H4 Supertrend ATR10×3, U05 BAR_OPEN lag1;
- flip_cnt_7d = number of direction changes in the causal lagged H4 ST state over the last 42 H4 observations (7d);
- primary SELL_B3 = age 27..50 (frozen recent SELL range); generic B3 age 28..58 is sensitivity;
- signal clocks = every H4 boundary satisfying B3; entry = next M1 open;
- outcomes = SELL, SL 1.5×completed H1 ATR14, no TP, 48h PRIMARY and 72h SENSITIVITY, $27.5/BTC cost proxy;
- raw quintiles are descriptive only;
- primary inference controls exact ST age + calendar year and cluster-bootstraps by continuous H4 ST episode.
"""
from pathlib import Path
import json, numpy as np, pandas as pd
import u02c2_v283_market_clock_conditional as base

OUT=Path('sell_core_003_out'); OUT.mkdir(exist_ok=True)
M1ZIP='btc_1m.zip'; M5ZIP='btc_5m.zip'; COST=27.5; STOP_ATR=1.5; BOOT=20000; SEED=403003


def pf(x):
    z=pd.Series(x).dropna(); gp=z[z>0].sum(); gl=-z[z<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def build_clock(m5):
    h4=base.h4_supertrend(m5)[['time','st_dir','st_age']].copy()
    # decision-available state at H4 bar open = previous completed H4 state
    h4['st_dir']=h4.st_dir.shift(1); h4['st_age']=h4.st_age.shift(1)
    h4=h4.dropna().copy(); h4.st_dir=h4.st_dir.astype(int); h4.st_age=h4.st_age.astype(int)
    # continuous canonical ST episode
    h4['episode_id']=(h4.st_dir.ne(h4.st_dir.shift()) | ((h4.time-h4.time.shift())>pd.Timedelta(hours=4,minutes=1))).cumsum().astype(int)
    # causal flip known at this H4 open; transition occurred in the last completed bar
    h4['flip_event']=h4.st_dir.ne(h4.st_dir.shift()).astype(int)
    h4.loc[h4.index[0],'flip_event']=0
    h4['flip_cnt_7d']=h4.flip_event.rolling(42,min_periods=42).sum()
    h4['sell_relation']=np.where(h4.st_dir.eq(-1),'ALIGNED','OPPOSITE')
    h4['b3_primary']=h4.st_age.between(27,50)
    h4['b3_generic']=h4.st_age.between(28,58)
    return h4


def replay(rows,m1,h1,hours):
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float)
    hct=h1.close_time.to_numpy('datetime64[ns]'); HA=h1.atr14.to_numpy(float)
    out=[]
    for r in rows.itertuples(index=False):
        sig=pd.Timestamp(r.time); et=sig+pd.Timedelta(minutes=1)
        j=int(np.searchsorted(mt,np.datetime64(et),'left')); q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1)
        if j>=len(O) or q<0 or not np.isfinite(HA[q]) or HA[q]<=0: continue
        je=int(np.searchsorted(mt,np.datetime64(sig+pd.Timedelta(hours=hours)),'left'))
        if je<=j or je>=len(O): continue
        entry=float(O[j]); sd=STOP_ATR*float(HA[q]); sl=entry+sd
        hit=np.flatnonzero(H[j:je]>=sl)
        if hit.size:
            rr=-1-COST/sd; pct=-(sd/entry*100)-COST/entry*100; ex='SL'
        else:
            xp=float(O[je]); rr=(entry-xp)/sd-COST/sd; pct=(entry-xp)/entry*100-COST/entry*100; ex='TIME'
        d=r._asdict(); d.update(entry=entry,atr_h1=float(HA[q]),R=rr,pct=pct,exit_type=ex,hold_h=hours,year=sig.year)
        out.append(d)
    return pd.DataFrame(out)


def quintiles_rank(x):
    # equal-count descriptive bins despite discrete ties; no inference uses qcut thresholds
    rk=x.rank(method='first',pct=True)
    return pd.cut(rk,[0,.2,.4,.6,.8,1.0000001],labels=['Q1','Q2','Q3','Q4','Q5'],include_lowest=True)


def metrics(g):
    return dict(N=len(g),episodes=g.episode_id.nunique(),EV_R=float(g.R.mean()) if len(g) else np.nan,PF=pf(g.R),WR=float((g.R>0).mean()) if len(g) else np.nan,EV_pct=float(g.pct.mean()) if len(g) else np.nan,SL_rate=float((g.exit_type=='SL').mean()) if len(g) else np.nan,flip_mean=float(g.flip_cnt_7d.mean()) if len(g) else np.nan,age_mean=float(g.st_age.mean()) if len(g) else np.nan)


def fe_beta(g):
    # residualize R and pct by exact age + year; beta on flip_cnt_7d is incremental association beyond B3 age/year.
    z=g.dropna(subset=['flip_cnt_7d','R','pct']).copy()
    if len(z)<20 or z.flip_cnt_7d.nunique()<2: return (np.nan,np.nan)
    for col in ['R','pct','flip_cnt_7d']:
        z[col+'_res']=z[col]-z.groupby(['st_age','year'])[col].transform('mean')
    den=float((z.flip_cnt_7d_res**2).sum())
    if den<=0:return (np.nan,np.nan)
    return float((z.flip_cnt_7d_res*z.R_res).sum()/den), float((z.flip_cnt_7d_res*z.pct_res).sum()/den)


def cluster_boot_fe(g,seed):
    z=g.dropna(subset=['flip_cnt_7d','R']).copy(); ids=z.episode_id.unique(); obsR,obsP=fe_beta(z)
    if len(ids)<8 or not np.isfinite(obsR): return dict(beta_R=obsR,CI_R_lo=np.nan,CI_R_hi=np.nan,P_beta_R_gt0=np.nan,beta_pct=obsP,CI_pct_lo=np.nan,CI_pct_hi=np.nan,P_beta_pct_gt0=np.nan)
    groups={eid:z[z.episode_id==eid] for eid in ids}; rng=np.random.default_rng(seed); br=[]; bp=[]
    for _ in range(BOOT):
        samp=rng.choice(ids,size=len(ids),replace=True)
        b=pd.concat([groups[e].assign(boot_ep=i) for i,e in enumerate(samp)],ignore_index=True)
        # unique boot episode IDs only matter for resampling, FE is age/year
        r,p=fe_beta(b)
        if np.isfinite(r): br.append(r)
        if np.isfinite(p): bp.append(p)
    br=np.asarray(br);bp=np.asarray(bp)
    return dict(beta_R=obsR,CI_R_lo=float(np.quantile(br,.025)),CI_R_hi=float(np.quantile(br,.975)),P_beta_R_gt0=float((br>0).mean()),beta_pct=obsP,CI_pct_lo=float(np.quantile(bp,.025)),CI_pct_hi=float(np.quantile(bp,.975)),P_beta_pct_gt0=float((bp>0).mean()))


def run_universe(clock,m1,h1,flag,name):
    rows=clock[clock[flag]&clock.flip_cnt_7d.notna()].copy()
    outs=[]; quints=[]; raws=[]; years=[]; rels=[]; tests=[]
    for hh in [48,72]:
        x=replay(rows,m1,h1,hh); x['universe']=name; x['q5']=quintiles_rank(x.flip_cnt_7d); raws.append(x)
        for q,g in x.groupby('q5',observed=True): quints.append({'universe':name,'hold_h':hh,'quintile':str(q),**metrics(g)})
        for fc,g in x.groupby('flip_cnt_7d'): outs.append({'universe':name,'hold_h':hh,'flip_cnt_7d':int(fc),**metrics(g)})
        for y,g in x.groupby('year'):
            yy=metrics(g); years.append({'universe':name,'hold_h':hh,'year':int(y),**yy})
        for r,g in x.groupby('sell_relation'): rels.append({'universe':name,'hold_h':hh,'relation':r,**metrics(g)})
        t=cluster_boot_fe(x,SEED+hh+(0 if name=='SELL_B3_27_50' else 1000)); tests.append({'universe':name,'hold_h':hh,**t})
    return pd.concat(raws,ignore_index=True),pd.DataFrame(quints),pd.DataFrame(outs),pd.DataFrame(years),pd.DataFrame(rels),pd.DataFrame(tests)


def main():
    m1=base.load_zip(M1ZIP); m5=base.load_zip(M5ZIP); h1=base.h1_atr_from_m1(m1); clock=build_clock(m5)
    allparts=[]; qs=[]; cs=[]; ys=[]; rs=[]; ts=[]
    for flag,name in [('b3_primary','SELL_B3_27_50'),('b3_generic','B3_28_58')]:
        a,b,c,d,e,f=run_universe(clock,m1,h1,flag,name); allparts.append(a);qs.append(b);cs.append(c);ys.append(d);rs.append(e);ts.append(f)
    A=pd.concat(allparts,ignore_index=True);Q=pd.concat(qs,ignore_index=True);C=pd.concat(cs,ignore_index=True);Y=pd.concat(ys,ignore_index=True);R=pd.concat(rs,ignore_index=True);T=pd.concat(ts,ignore_index=True)
    A.to_csv(OUT/'events.csv',index=False);Q.to_csv(OUT/'quintiles.csv',index=False);C.to_csv(OUT/'count_buckets.csv',index=False);Y.to_csv(OUT/'yearly.csv',index=False);R.to_csv(OUT/'relation.csv',index=False);T.to_csv(OUT/'age_year_controlled_test.csv',index=False)
    primQ=Q[Q.universe.eq('SELL_B3_27_50')]; primT=T[T.universe.eq('SELL_B3_27_50')]; primY=Y[Y.universe.eq('SELL_B3_27_50')]
    report=['# SELL_CORE_003 — B3 × HTF_FLIP_COUNT_7D','',
            '**Feature definition:** count of causal canonical H4 ST direction changes over the previous 42 H4 observations (7 days). Old exact feature code was not present in the repository, so this literal definition was frozen before outcomes.','',
            '**Primary B3:** SELL age 27–50. Generic age 28–58 is sensitivity.','',
            '**Outcome:** SL=1.5×completed H1 ATR14; no TP; 48h primary / 72h sensitivity; $27.5/BTC cost proxy.','',
            '## Descriptive rank quintiles — primary SELL B3','',primQ.to_markdown(index=False),'',
            '## Age + year controlled incremental test','',primT.to_markdown(index=False),'',
            'The coefficient is R (or price %) per one additional HTF flip after demeaning within exact B3 age and calendar year. Cluster bootstrap resamples continuous ST episodes.','',
            '## Year aggregate','',primY.to_markdown(index=False),'',
            '## Interpretation rule','',
            'Raw Q1→Q5 improvement is not enough because flip count is mechanically related to ST age. Promote flip_cnt_7d only if the age/year-controlled beta is positive with useful uncertainty at 48h, directionally survives 72h, and price-% agrees with R.']
    (OUT/'REPORT.md').write_text('\n'.join(report))
    print('QUINTILES\n',primQ.to_string(index=False));print('\nCONTROLLED\n',primT.to_string(index=False));print('\nYEARLY\n',primY.to_string(index=False));print('\nCOUNT BUCKETS\n',C[C.universe.eq('SELL_B3_27_50')].to_string(index=False));print('\nRELATION\n',R[R.universe.eq('SELL_B3_27_50')].to_string(index=False));print('\nREPORT\n', (OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
