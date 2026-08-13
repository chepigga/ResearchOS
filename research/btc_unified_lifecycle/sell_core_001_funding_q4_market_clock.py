#!/usr/bin/env python3
"""SELL_CORE_001 — FUNDING Q4 x canonical H4 market-clock decomposition.

Frozen before outcomes:
- Funding source: Binance BTCUSDT perpetual funding, 8h observations, UTC.
- Slow context is computed BEFORE any market-clock filtering.
- funding_3d = trailing mean of 9 funding observations (3 days).
- causal percentile = current funding_3d versus PREVIOUS 2000 funding_3d observations.
  Primary tie convention: inclusive ECDF mean(prev <= current).
  Sensitivity: midrank ECDF ((prev < current)+0.5*(prev == current))/2000.
- Q1 <=25%, Q4 >=75%. No calendar-year normalization, no FVG conditioning.
- Canonical market clock: H4 Supertrend ATR10 x3, U05 BAR_OPEN lag1 convention.
- Generic buckets: B1 age 0..11, B2 12..27, B3 28..58, B4 >58.
- Prior SELL_B3 range 27..50 is reported as a frozen special diagnostic; not tuned here.
- Signal clock: funding timestamps (00/08/16 UTC), naturally aligned to H4 boundaries.
- Entry: next M1 open (+1 minute convention).
- SELL exit: SL=1.5 x completed H1 ATR14 OR 48h time exit; NO TP; $27.5/BTC cost proxy.
- Primary unit: first Q4/non-Q4 funding observation inside each continuous market-clock episode.
- Raw funding observations are diagnostic only because 48h holds overlap heavily.
- Inference: cluster bootstrap by market-clock episode for Q4 minus non-Q4 EV.

This lab is a 2024-2026 recent market-clock decomposition because the frozen unified
M1/M5 price assets start in 2024. The older 8/8 funding result is a separate broad
finding and is not re-labeled as a result of this lab.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base

OUT=Path('sell_core_001_out'); OUT.mkdir(exist_ok=True)
M1ZIP='btc_1m.zip'; M5ZIP='btc_5m.zip'; FUNDING='binance_btc_funding.csv'
START=pd.Timestamp('2024-01-01')
STOP_ATR=1.5; EXIT_H=48; COST_USD=27.5
BOOT=20000; SEED=401001


def pf(x):
    z=pd.Series(x).dropna(); gp=z[z>0].sum(); gl=-z[z<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def load_funding():
    f=pd.read_csv(FUNDING)
    f['time']=pd.to_datetime(f.time,format='%Y.%m.%d %H:%M',errors='coerce',utc=True).dt.tz_localize(None)
    f['funding']=pd.to_numeric(f.funding,errors='coerce')
    f=f.dropna().sort_values('time').drop_duplicates('time').reset_index(drop=True)
    f['funding_3d']=f.funding.rolling(9,min_periods=9).mean()
    n=len(f); inc=np.full(n,np.nan); mid=np.full(n,np.nan)
    v=f.funding_3d.to_numpy(float)
    for i in range(n):
        if i<2008 or not np.isfinite(v[i]): continue
        prev=v[i-2000:i]
        if np.isfinite(prev).sum()!=2000: continue
        cur=v[i]
        inc[i]=np.mean(prev<=cur)
        mid[i]=(np.sum(prev<cur)+0.5*np.sum(prev==cur))/2000.0
    f['pct_inclusive']=inc; f['pct_midrank']=mid
    return f


def build_clock(m5):
    h4=base.h4_supertrend(m5)
    c=h4[['time','st_dir','st_age','st_dist_atr']].copy()
    for col in ['st_dir','st_age','st_dist_atr']:
        c[col]=c[col].shift(1)
    c=c.dropna(subset=['st_dir','st_age']).copy()
    c['st_dir']=c.st_dir.astype(int); c['st_age']=c.st_age.astype(int)
    c['bucket']=np.select([c.st_age<=11,c.st_age<=27,c.st_age<=58],['B1','B2','B3'],default='B4')
    c['sell_relation']=np.where(c.st_dir==-1,'ALIGNED','OPPOSITE')
    c['sell_b3_27_50']=((c.st_age>=27)&(c.st_age<=50)).astype(int)
    prev_t=c.time.shift(); prev_b=c.bucket.shift(); prev_d=c.st_dir.shift()
    new=(c.bucket.ne(prev_b))|(c.st_dir.ne(prev_d))|((c.time-prev_t)>pd.Timedelta(hours=4,minutes=1))
    c['clock_episode_id']=new.cumsum().astype(int)
    return c


def attach_clock(f,clock):
    x=f.sort_values('time').copy(); c=clock.sort_values('time').copy()
    z=pd.merge_asof(x,c,on='time',direction='backward')
    # Funding timestamps are H4 boundaries; require exact H4 clock alignment to avoid silent drift.
    z['clock_exact']=(z.time.dt.floor('4h')==z.time)
    return z.dropna(subset=['st_age','st_dir']).copy()


def h1_atr(m1):
    return base.h1_atr_from_m1(m1)


def replay_sell(rows,m1,h1):
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float)
    hct=h1.close_time.to_numpy('datetime64[ns]'); HA=h1.atr14.to_numpy(float)
    out=[]
    for r in rows.itertuples(index=False):
        sig=pd.Timestamp(r.time); et=sig+pd.Timedelta(minutes=1)
        j=int(np.searchsorted(mt,np.datetime64(et),'left')); q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1)
        if j>=len(O) or q<0 or not np.isfinite(HA[q]) or HA[q]<=0: continue
        tend=sig+pd.Timedelta(hours=EXIT_H); je=int(np.searchsorted(mt,np.datetime64(tend),'left'))
        if je<=j or je>=len(O): continue
        entry=float(O[j]); sd=STOP_ATR*float(HA[q]); sl=entry+sd
        hit=np.flatnonzero(H[j:je]>=sl)
        if hit.size:
            rr=-1.0-COST_USD/sd; pct=-(sd/entry*100.0)-COST_USD/entry*100.0; ex='SL'; exitp=sl
        else:
            exitp=float(O[je]); rr=(entry-exitp)/sd-COST_USD/sd; pct=(entry-exitp)/entry*100.0-COST_USD/entry*100.0; ex='TIME'
        mfe=(entry-float(L[j:je].min()))/sd; mae=(float(H[j:je].max())-entry)/sd
        d=r._asdict(); d.update(signal_time=sig,entry_time=et,entry=entry,atr_h1=float(HA[q]),stop_dist=sd,
                                 exit_price=exitp,exit_type=ex,R=rr,pct=pct,MFE_R=mfe,MAE_R=mae,year=sig.year)
        out.append(d)
    return pd.DataFrame(out)


def class_from_pct(p):
    return np.select([p<=.25,p<=.50,p<.75],['Q1','Q2','Q3'],default='Q4')


def episode_first(x):
    # One observation for each funding class inside a continuous market-clock episode.
    z=x.sort_values('time').copy()
    return z.groupby(['clock_episode_id','funding_bin'],as_index=False).first()


def cell_mask(x,cell):
    if cell=='ALL': return np.ones(len(x),dtype=bool)
    if cell=='SELL_B3_27_50': return x.sell_b3_27_50.eq(1).to_numpy()
    return x.bucket.eq(cell).to_numpy()


def metrics(g):
    z=g.R.dropna()
    return {'N':len(g),'N_clock_episodes':g.clock_episode_id.nunique(),'EV_R':float(z.mean()) if len(z) else np.nan,
            'PF_R':pf(z),'WR':float((z>0).mean()) if len(z) else np.nan,'SL_rate':float((g.exit_type=='SL').mean()) if len(g) else np.nan,
            'EV_pct':float(g.pct.mean()) if len(g) else np.nan,'MFE_med_R':float(g.MFE_R.median()) if len(g) else np.nan,
            'MAE_med_R':float(g.MAE_R.median()) if len(g) else np.nan}


def cluster_boot_delta(g,seed):
    # Preserve Q4/nonQ4 rows from the same clock episode together.
    z=g[['clock_episode_id','q4','R','pct']].dropna().copy(); ids=z.clock_episode_id.unique()
    obs_q=z[z.q4==1]; obs_n=z[z.q4==0]
    if len(ids)<4 or len(obs_q)<2 or len(obs_n)<2:
        return {'delta_R':np.nan,'CI_R_lo':np.nan,'CI_R_hi':np.nan,'P_R_gt0':np.nan,
                'delta_pct':np.nan,'CI_pct_lo':np.nan,'CI_pct_hi':np.nan,'P_pct_gt0':np.nan}
    dR=obs_q.R.mean()-obs_n.R.mean(); dP=obs_q.pct.mean()-obs_n.pct.mean()
    rng=np.random.default_rng(seed); br=[]; bp=[]
    groups={eid:z[z.clock_episode_id==eid] for eid in ids}
    for _ in range(BOOT):
        samp=rng.choice(ids,size=len(ids),replace=True)
        parts=[groups[e] for e in samp]; b=pd.concat(parts,ignore_index=True)
        q=b[b.q4==1]; n=b[b.q4==0]
        if len(q) and len(n):
            br.append(q.R.mean()-n.R.mean()); bp.append(q.pct.mean()-n.pct.mean())
    br=np.asarray(br); bp=np.asarray(bp)
    return {'delta_R':float(dR),'CI_R_lo':float(np.quantile(br,.025)),'CI_R_hi':float(np.quantile(br,.975)),'P_R_gt0':float((br>0).mean()),
            'delta_pct':float(dP),'CI_pct_lo':float(np.quantile(bp,.025)),'CI_pct_hi':float(np.quantile(bp,.975)),'P_pct_gt0':float((bp>0).mean())}


def summarize_method(x,method):
    cells=['ALL','B1','B2','B3','B4','SELL_B3_27_50']
    rows=[]; years=[]; rel=[]
    for cell in cells:
        g=x[cell_mask(x,cell)].copy()
        for label,sub in [('Q4',g[g.q4==1]),('Q1_Q3',g[g.q4==0])]:
            m=metrics(sub); rows.append({'method':method,'cell':cell,'funding':label,**m})
        d=cluster_boot_delta(g,SEED+sum(map(ord,cell))+ (0 if method=='inclusive' else 5000))
        rows.append({'method':method,'cell':cell,'funding':'DELTA_Q4_MINUS_Q1Q3',**d})
        for y,gy in g.groupby('year'):
            for label,sub in [('Q4',gy[gy.q4==1]),('Q1_Q3',gy[gy.q4==0])]:
                m=metrics(sub); years.append({'method':method,'cell':cell,'year':int(y),'funding':label,**m})
            d2=cluster_boot_delta(gy,SEED+int(y)+sum(map(ord,cell)))
            years.append({'method':method,'cell':cell,'year':int(y),'funding':'DELTA_Q4_MINUS_Q1Q3',**d2})
    # Relation diagnostic, not used to choose the market bucket.
    for (b,r,q),g in x.groupby(['bucket','sell_relation','q4']):
        rel.append({'method':method,'bucket':b,'relation':r,'funding':'Q4' if q else 'Q1_Q3',**metrics(g)})
    return pd.DataFrame(rows),pd.DataFrame(years),pd.DataFrame(rel)


def run_method(attached,m1,h1,pct_col,method):
    x=attached.dropna(subset=[pct_col]).copy(); x=x[(x.time>=START)&(x.clock_exact)].copy()
    x['pctile']=x[pct_col]; x['quartile']=class_from_pct(x.pctile)
    x['q4']=(x.pctile>=.75).astype(int); x['funding_bin']=np.where(x.q4==1,'Q4','Q1_Q3')
    raw=replay_sell(x,m1,h1); raw.to_csv(OUT/f'raw_funding_clock_{method}.csv',index=False)
    ep=episode_first(x); ep=replay_sell(ep,m1,h1); ep.to_csv(OUT/f'episode_first_{method}.csv',index=False)
    s,y,r=summarize_method(ep,method)
    return raw,ep,s,y,r


def main():
    f=load_funding(); f.to_csv(OUT/'funding_context_full_history.csv',index=False)
    m1=base.load_zip(M1ZIP); m5=base.load_zip(M5ZIP); h1=h1_atr(m1); clock=build_clock(m5)
    attached=attach_clock(f,clock); attached.to_csv(OUT/'funding_market_clock_attached.csv',index=False)
    summaries=[]; yearlies=[]; relations=[]; census=[]
    for pct_col,method in [('pct_inclusive','inclusive'),('pct_midrank','midrank')]:
        raw,ep,s,y,r=run_method(attached,m1,h1,pct_col,method)
        summaries.append(s); yearlies.append(y); relations.append(r)
        census.append({'method':method,'raw_N':len(raw),'episode_first_N':len(ep),'Q4_raw':int(raw.q4.sum()),'Q4_episode_first':int(ep.q4.sum()),
                       'start':str(raw.time.min()),'end':str(raw.time.max()),'clock_exact_rate':float(attached.loc[attached[pct_col].notna(),'clock_exact'].mean())})
    S=pd.concat(summaries,ignore_index=True); Y=pd.concat(yearlies,ignore_index=True); R=pd.concat(relations,ignore_index=True); C=pd.DataFrame(census)
    S.to_csv(OUT/'decomposition_summary.csv',index=False);Y.to_csv(OUT/'decomposition_yearly.csv',index=False);R.to_csv(OUT/'relation_diagnostic.csv',index=False);C.to_csv(OUT/'census.csv',index=False)
    primary=S[S.method=='inclusive'].copy(); primary.to_csv(OUT/'primary_inclusive.csv',index=False)
    # Compact tables for report.
    mtab=primary[primary.funding.isin(['Q4','Q1_Q3'])][['cell','funding','N','N_clock_episodes','EV_R','PF_R','WR','SL_rate','EV_pct']]
    dtab=primary[primary.funding=='DELTA_Q4_MINUS_Q1Q3'][['cell','delta_R','CI_R_lo','CI_R_hi','P_R_gt0','delta_pct','CI_pct_lo','CI_pct_hi','P_pct_gt0']]
    ytab=Y[(Y.method=='inclusive')&(Y.funding.isin(['Q4','DELTA_Q4_MINUS_Q1Q3']))][['cell','year','funding','N','EV_R','PF_R','EV_pct','delta_R','P_R_gt0']]
    stab=[]
    for cell in ['ALL','B1','B2','B3','B4','SELL_B3_27_50']:
        q=Y[(Y.method=='inclusive')&(Y.cell==cell)&(Y.funding=='Q4')]
        stab.append({'cell':cell,'years_with_Q4':len(q),'positive_EV_R_years':int((q.EV_R>0).sum()),'positive_EV_pct_years':int((q.EV_pct>0).sum()),'min_year_N':int(q.N.min()) if len(q) else 0})
    ST=pd.DataFrame(stab); ST.to_csv(OUT/'year_stability.csv',index=False)
    sens=S[S.method=='midrank']; sens=sens[sens.funding.isin(['Q4','DELTA_Q4_MINUS_Q1Q3'])][['cell','funding','N','EV_R','PF_R','EV_pct','delta_R','P_R_gt0']]
    report=['# SELL_CORE_001 — FUNDING Q4 × MARKET-CLOCK DECOMPOSITION','',
            '**Status:** recent 2024–2026 decomposition on frozen unified BTC price data. This does not recreate the older 8/8 oracle-population benchmark.','',
            '## Frozen funding construction','',
            '- trailing 3-day mean = 9 consecutive 8h Binance perpetual funding observations;',
            '- causal percentile versus previous 2,000 funding observations, computed before market-clock filtering;',
            '- primary tie convention: inclusive ECDF; midrank is a fixed sensitivity;',
            '- Q4 >= 75th percentile, Q1-Q3 otherwise;',
            '- no FVG conditioning and no outcome-driven threshold tuning.','',
            '## Common SELL outcome','',
            '- signal = Binance funding timestamp (00/08/16 UTC, H4 boundary);',
            '- entry = next M1 open;',
            '- SL = 1.5 × completed H1 ATR14;',
            '- no TP; 48h time exit; $27.5/BTC cost proxy.','',
            'Primary unit = first funding-class observation inside a continuous H4 market-clock episode; raw 8h observations are diagnostic because 48h holds overlap.','',
            '## Primary inclusive-ECDF metrics','',mtab.to_markdown(index=False),'',
            '## Incremental Q4 minus Q1-Q3, cluster bootstrap by market-clock episode','',dtab.to_markdown(index=False),'',
            '## Year stability','',ST.to_markdown(index=False),'',
            '## Q4 yearly detail','',ytab.to_markdown(index=False),'',
            '## Tie sensitivity: midrank percentile','',sens.to_markdown(index=False),'',
            '## Interpretation rule','',
            'A market bucket is a SELL-core context candidate only if Q4 is positive in R and price space with useful sample size, the Q4-minus-nonQ4 delta is directionally supportive, and the sign is not carried by one year. The frozen prior SELL_B3 27–50 range is reported separately and is not optimized here.']
    (OUT/'REPORT.md').write_text('\n'.join(report))
    (OUT/'summary.json').write_text(json.dumps({'funding':'3d trailing mean; causal rolling percentile previous 2000 observations','primary_ties':'inclusive ECDF','sensitivity_ties':'midrank','clock':'H4 ST ATR10x3 BAR_OPEN lag1','exit':'SELL SL1.5 H1 ATR; no TP; 48h','period':'2024-2026 recent unified price window'},indent=2))
    print('\nCENSUS\n',C.to_string(index=False)); print('\nMETRICS\n',mtab.to_string(index=False)); print('\nDELTA\n',dtab.to_string(index=False)); print('\nSTABILITY\n',ST.to_string(index=False)); print('\nYEARLY\n',ytab.to_string(index=False)); print('\nSENSITIVITY\n',sens.to_string(index=False))

if __name__=='__main__': main()
