#!/usr/bin/env python3
"""SELL_CORE_014 — B3_LHBOS_LONG_HISTORY_EXTENSION.

Purpose: increase independent sample for the exact 013 construction without adding any rescue filter.
Frozen rule:
- exact LH+BOS from user parity: calendar-equivalent 60-row H1, LR=2, lb=120,
  LH = latest confirmed swing high < prior swing high; BOS_dn = previous H1 close < latest confirmed swing low.
- canonical H4 Supertrend ATR10x3, BAR_OPEN lag1; B3 = ST DOWN and age 27..50 inclusive.
- intersection = B3 AND LH+BOS.
- candidate grid: one point/hour; primary phase :20, sensitivities :40 and :00.
- native view: entry minute close; stop 1.5*(SMA M1 TR60 * 60), no TP, 48h, cost 0.096% of price.
- canonical view: next M1 open; stop 1.5*completed H1 ATR14, no TP, 48h primary / 72h sensitivity, $27.5/BTC.
- no funding/RV/topology/FVG/v283/extra structure filters.
- inference by continuous H4 ST episodes; yearly and fixed 12m/18m rolling diagnostics.

Data:
- pre-2024: Binance USD-M futures monthly archives from data.binance.vision.
- 2024+: frozen ResearchOS BTC release assets (same venue; H1 OHLCV/trades parity proven exactly).
The long series is trimmed to the first full UTC hour so row-block H1 remains calendar-aligned.
"""
from pathlib import Path
import numpy as np, pandas as pd
import u02c2_v283_market_clock_conditional as base

OUT=Path('sell_core_014_out'); OUT.mkdir(exist_ok=True)
LR=2; LB=120; START_WARMUP=20000; TAIL=6000; STEP=60
COST_PCT=.096; COST_USD=27.5; BOOT=20000; SEED=414014
PHASES=(0,20,40); HOLDS=(48,72)


def pf(z):
    x=np.asarray(pd.Series(z).dropna(),float)
    gp=x[x>0].sum(); gl=-x[x<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def read_monthly_dir(path, tf):
    parts=[]
    for fn in sorted(Path(path).glob('*.csv')):
        # ResearchOS frozen files have named columns; Binance archive files may be headerless.
        with open(fn,'r',encoding='utf-8') as f: first=f.readline().strip().split(',')[0]
        if first.lower() in ('time','open_time'):
            d=pd.read_csv(fn)
            if 'time' in d.columns:
                t=pd.to_datetime(d['time'],format='%Y.%m.%d %H:%M',errors='coerce')
                q=pd.DataFrame({'time':t,'open':pd.to_numeric(d.open,errors='coerce'),'high':pd.to_numeric(d.high,errors='coerce'),'low':pd.to_numeric(d.low,errors='coerce'),'close':pd.to_numeric(d.close,errors='coerce'),'volume':pd.to_numeric(d.get('volume'),errors='coerce')})
            else:
                # Official archive with header.
                t=pd.to_datetime(pd.to_numeric(d.iloc[:,0],errors='coerce'),unit='ms',errors='coerce')
                q=pd.DataFrame({'time':t,'open':pd.to_numeric(d.iloc[:,1],errors='coerce'),'high':pd.to_numeric(d.iloc[:,2],errors='coerce'),'low':pd.to_numeric(d.iloc[:,3],errors='coerce'),'close':pd.to_numeric(d.iloc[:,4],errors='coerce'),'volume':pd.to_numeric(d.iloc[:,5],errors='coerce')})
        else:
            d=pd.read_csv(fn,header=None)
            ts=pd.to_numeric(d.iloc[:,0],errors='coerce')
            # Old Binance archives use ms. Defensive fallback for microsecond timestamps.
            unit='us' if np.nanmedian(ts.to_numpy(float))>1e14 else 'ms'
            t=pd.to_datetime(ts,unit=unit,errors='coerce')
            q=pd.DataFrame({'time':t,'open':pd.to_numeric(d.iloc[:,1],errors='coerce'),'high':pd.to_numeric(d.iloc[:,2],errors='coerce'),'low':pd.to_numeric(d.iloc[:,3],errors='coerce'),'close':pd.to_numeric(d.iloc[:,4],errors='coerce'),'volume':pd.to_numeric(d.iloc[:,5],errors='coerce')})
        q=q.dropna(subset=['time','open','high','low','close'])
        parts.append(q)
    if not parts: raise RuntimeError(f'no csv files in {path}')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    return x


def load_long():
    pre1=read_monthly_dir('hist_1m','1m'); fr1=read_monthly_dir('frozen_1m','1m')
    pre5=read_monthly_dir('hist_5m','5m'); fr5=read_monthly_dir('frozen_5m','5m')
    m1=pd.concat([pre1,fr1],ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    m5=pd.concat([pre5,fr5],ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    # Trim to first complete UTC hour so user's row-block H1 remains calendar H1.
    start=m1.time.min().ceil('h')
    m1=m1[m1.time>=start].reset_index(drop=True); m5=m5[m5.time>=start.floor('5min')].reset_index(drop=True)
    # Exact continuity is mandatory for row-block parity.
    dt=m1.time.diff().dropna(); gaps=dt.ne(pd.Timedelta(minutes=1))
    gap_rows=pd.DataFrame({'time':m1.time.iloc[1:].to_numpy()[gaps.to_numpy()], 'delta':dt[gaps].astype(str).to_numpy()}) if gaps.any() else pd.DataFrame(columns=['time','delta'])
    gap_rows.to_csv(OUT/'m1_gaps.csv',index=False)
    if gaps.any(): raise RuntimeError(f'M1 continuity failure: {int(gaps.sum())} gaps; cannot preserve exact 60-row H1 parity')
    return m1,m5,start,len(pre1),len(fr1)


def prep(m1,m5):
    N=len(m1); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float); C=m1.close.to_numpy(float)
    nb=(N+59)//60; hh=np.empty(nb); hl=np.empty(nb); hc=np.empty(nb)
    for k in range(nb):
        a=k*60; b=min(a+60,N); hh[k]=H[a:b].max(); hl[k]=L[a:b].min(); hc[k]=C[b-1]
    prev=np.r_[np.nan,C[:-1]]
    tr=np.nanmax(np.vstack([H-L,np.abs(H-prev),np.abs(L-prev)]),axis=0); tr[0]=H[0]-L[0]
    a60=pd.Series(tr).rolling(60,min_periods=60).mean().to_numpy()
    labels={}
    def swings(k):
        hs=[]; ls=[]
        for b in range(k-LR,max(k-LB,LR),-1):
            if len(hs)<3 and all(hh[b]>=hh[b+d] for d in range(-LR,LR+1)): hs.append((b,hh[b]))
            if len(ls)<3 and all(hl[b]<=hl[b+d] for d in range(-LR,LR+1)): ls.append((b,hl[b]))
            if len(hs)>=3 and len(ls)>=3: break
        return hs,ls
    for k in range(3,nb):
        hs,ls=swings(k)
        labels[k]=bool(len(hs)>=2 and len(ls)>=1 and hs[0][1]<hs[1][1] and hc[k-1]<ls[0][1])
    h4=base.h4_supertrend(m5)[['time','st_dir','st_age']].copy()
    h4['st_dir']=h4.st_dir.shift(1); h4['st_age']=h4.st_age.shift(1); h4=h4.dropna().copy()
    h4.st_dir=h4.st_dir.astype(int); h4.st_age=h4.st_age.astype(int)
    h4['episode_id']=(h4.st_dir.ne(h4.st_dir.shift())|((h4.time-h4.time.shift())>pd.Timedelta(hours=4,minutes=1))).cumsum().astype(int)
    return H,L,C,a60,labels,h4,base.h1_atr_from_m1(m1)


def clocks(m1,labels,h4,phase):
    # Base dataset begins exactly at :00. phase=20 reproduces user's original :20 hourly grid.
    idx=np.arange(START_WARMUP+phase,len(m1)-TAIL,STEP,dtype=int)
    x=pd.DataFrame({'i':idx}); x['time']=m1.time.iloc[idx].to_numpy(); x['k']=idx//60
    x['lhbos']=[labels.get(int(k),False) for k in x.k]
    x=pd.merge_asof(x.sort_values('time'),h4.sort_values('time'),on='time',direction='backward').dropna(subset=['st_dir','st_age']).copy()
    x['st_dir']=x.st_dir.astype(int); x['st_age']=x.st_age.astype(int); x['episode_id']=x.episode_id.astype(int)
    x['b3']=x.st_dir.eq(-1)&x.st_age.between(27,50); x['intersection']=x.lhbos&x.b3
    x['year']=pd.to_datetime(x.time).dt.year; x['phase_min']=phase
    return x


def native_replay(x,m1,H,C,a60):
    out=[]; N=len(m1)
    # Only intersection trades are needed for long-history validation.
    for r in x[x.intersection].itertuples(index=False):
        i=int(r.i); sd=1.5*a60[i]*60
        if not np.isfinite(sd) or sd<=0: continue
        entry=C[i]; sl=entry+sd; end=min(i+2880,N-1)
        hit=np.flatnonzero(H[i+1:end+1]>=sl); xp=sl if hit.size else C[end]
        gross=(entry-xp)/entry*100; net=gross-COST_PCT
        d=r._asdict(); d.update(view='NATIVE',hold_h=48,R=np.nan,pct=net,gross_pct=gross,exit_type='SL' if hit.size else 'TIME')
        out.append(d)
    return pd.DataFrame(out)


def canonical_replay(x,m1,H,h1,hold):
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); hct=h1.close_time.to_numpy('datetime64[ns]'); HA=h1.atr14.to_numpy(float)
    out=[]
    for r in x[x.intersection].itertuples(index=False):
        sig=pd.Timestamp(r.time); j=int(r.i)+1; q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1); je=int(np.searchsorted(mt,np.datetime64(sig+pd.Timedelta(hours=hold)),'left'))
        if j>=len(O) or q<0 or je<=j or je>=len(O) or not np.isfinite(HA[q]) or HA[q]<=0: continue
        entry=float(O[j]); sd=1.5*float(HA[q]); sl=entry+sd; hit=np.flatnonzero(H[j:je]>=sl)
        if hit.size: rr=-1-COST_USD/sd; pct=-(sd/entry*100)-COST_USD/entry*100; ex='SL'
        else:
            xp=float(O[je]); rr=(entry-xp)/sd-COST_USD/sd; pct=(entry-xp)/entry*100-COST_USD/entry*100; ex='TIME'
        d=r._asdict(); d.update(view='CANONICAL',hold_h=hold,R=rr,pct=pct,gross_pct=np.nan,exit_type=ex)
        out.append(d)
    return pd.DataFrame(out)


def met(g):
    if len(g)==0:return {'N':0,'episodes':0,'EV_pct':np.nan,'PF_pct':np.nan,'WR_pct':np.nan,'EV_R':np.nan,'PF_R':np.nan,'SL_rate':np.nan}
    z=g.pct.dropna(); r=g.R.dropna() if 'R' in g else pd.Series(dtype=float)
    return {'N':len(g),'episodes':g.episode_id.nunique(),'EV_pct':float(z.mean()),'PF_pct':pf(z),'WR_pct':float((z>0).mean()),'EV_R':float(r.mean()) if len(r) else np.nan,'PF_R':pf(r) if len(r) else np.nan,'SL_rate':float((g.exit_type=='SL').mean())}


def cluster_boot(g,value,seed):
    z=g.dropna(subset=[value]).copy(); ids=z.episode_id.unique()
    if len(ids)<4:return {'CI_lo':np.nan,'CI_hi':np.nan,'P_gt0':np.nan}
    a=z.groupby('episode_id')[value].agg(['sum','count']).to_numpy(float); E=len(a); rng=np.random.default_rng(seed)
    idx=rng.integers(0,E,size=(BOOT,E)); s=a[idx].sum(axis=1); b=s[:,0]/s[:,1]
    return {'CI_lo':float(np.quantile(b,.025)),'CI_hi':float(np.quantile(b,.975)),'P_gt0':float((b>0).mean())}


def rolling_diag(g,months):
    if len(g)==0:return pd.DataFrame()
    x=g.sort_values('time').copy(); t=pd.to_datetime(x.time)
    start=t.min().to_period('M').to_timestamp()+pd.offsets.MonthEnd(0)
    end=t.max().to_period('M').to_timestamp()+pd.offsets.MonthEnd(0)
    rows=[]
    for e in pd.date_range(start,end,freq='ME'):
        s=e-pd.DateOffset(months=months)
        q=x[(pd.to_datetime(x.time)>s)&(pd.to_datetime(x.time)<=e)]
        if len(q): rows.append({'view':x.view.iloc[0],'hold_h':int(x.hold_h.iloc[0]),'window_months':months,'end':e,'N':len(q),'episodes':q.episode_id.nunique(),'EV_pct':float(q.pct.mean()),'EV_R':float(q.R.mean()) if q.R.notna().any() else np.nan})
    return pd.DataFrame(rows)


def main():
    m1,m5,start,npre,nfr=load_long(); H,L,C,a60,labels,h4,h1=prep(m1,m5)
    # Dataset/census.
    census=[]; alltr=[]; yearly=[]; summaries=[]; boots=[]; rolling=[]
    for ph in PHASES:
        c=clocks(m1,labels,h4,ph)
        census.append({'phase_min':ph,'clocks':len(c),'LH_BOS':int(c.lhbos.sum()),'B3':int(c.b3.sum()),'intersection':int(c.intersection.sum()),'episodes_intersection':int(c[c.intersection].episode_id.nunique()),'first_clock':c.time.min(),'last_clock':c.time.max()})
        views=[native_replay(c,m1,H,C,a60),canonical_replay(c,m1,H,h1,48),canonical_replay(c,m1,H,h1,72)]
        for tr in views:
            if len(tr)==0: continue
            alltr.append(tr); v=tr.view.iloc[0]; hh=int(tr.hold_h.iloc[0])
            s={'phase_min':ph,'view':v,'hold_h':hh,**met(tr)}
            for val in ['pct']+(['R'] if v=='CANONICAL' else []):
                b=cluster_boot(tr,val,SEED+ph+hh+(1000 if val=='R' else 0)); boots.append({'phase_min':ph,'view':v,'hold_h':hh,'metric':val,'episodes':tr.episode_id.nunique(),'EV':float(tr[val].mean()),**b})
            summaries.append(s)
            for y,g in tr.groupby('year'): yearly.append({'phase_min':ph,'view':v,'hold_h':hh,'year':int(y),**met(g)})
            if ph==20 and ((v=='NATIVE' and hh==48) or (v=='CANONICAL' and hh==48)):
                rolling += [rolling_diag(tr,12),rolling_diag(tr,18)]
    A=pd.concat(alltr,ignore_index=True); CEN=pd.DataFrame(census); S=pd.DataFrame(summaries); Y=pd.DataFrame(yearly); B=pd.DataFrame(boots); R=pd.concat(rolling,ignore_index=True) if rolling else pd.DataFrame()
    A.to_csv(OUT/'intersection_trades.csv',index=False); CEN.to_csv(OUT/'census.csv',index=False); S.to_csv(OUT/'summary.csv',index=False); Y.to_csv(OUT/'yearly.csv',index=False); B.to_csv(OUT/'episode_bootstrap.csv',index=False); R.to_csv(OUT/'rolling_12_18m.csv',index=False)
    # 013 overlap benchmark for primary 2024+ phase :20 canonical/native.
    overlap=A[(A.phase_min==20)&(pd.to_datetime(A.time)>=pd.Timestamp('2024-01-01'))]
    overlap_rows=[]
    for (v,hh),g in overlap.groupby(['view','hold_h']): overlap_rows.append({'view':v,'hold_h':hh,**met(g)})
    OV=pd.DataFrame(overlap_rows); OV.to_csv(OUT/'overlap_2024plus.csv',index=False)
    prim=S[(S.phase_min==20)&(((S.view=='NATIVE')&(S.hold_h==48))|((S.view=='CANONICAL')&(S.hold_h.isin([48,72])))]
    yp=Y[(Y.phase_min==20)&(((Y.view=='NATIVE')&(Y.hold_h==48))|((Y.view=='CANONICAL')&(Y.hold_h==48)))]
    bp=B[(B.phase_min==20)&(((B.view=='NATIVE')&(B.hold_h==48))|((B.view=='CANONICAL')&(B.hold_h==48)))]
    phase=S[((S.view=='NATIVE')&(S.hold_h==48))|((S.view=='CANONICAL')&(S.hold_h==48))]
    rollsum=[]
    if len(R):
        for (v,hh,w),g in R.groupby(['view','hold_h','window_months']):
            col='EV_R' if v=='CANONICAL' else 'EV_pct'; z=g[col].dropna(); rollsum.append({'view':v,'hold_h':hh,'window_months':w,'points':len(z),'min_EV':float(z.min()),'median_EV':float(z.median()),'max_EV':float(z.max()),'positive_fraction':float((z>0).mean())})
    RS=pd.DataFrame(rollsum); RS.to_csv(OUT/'rolling_summary.csv',index=False)
    report=['# SELL_CORE_014 — B3_LHBOS_LONG_HISTORY_EXTENSION','',
            '## Data parity / coverage','',
            f'- combined M1: **{len(m1):,}** rows, {m1.time.min()} .. {m1.time.max()} UTC; first full-hour anchor **{start}**.',
            f'- pre-2024 archive rows loaded before trim: **{npre:,}**; frozen 2024+ rows: **{nfr:,}**.',
            '- M1 continuity gate: **PASS (0 gaps)**.','- Venue: Binance USD-M BTCUSDT perpetual; 2024 frozen M1 aggregates exactly to frozen futures H1 OHLCV/trades.','',
            '## Census','',CEN.to_markdown(index=False),'',
            '## Primary long-history metrics','',prim.to_markdown(index=False),'',
            '## Yearly primary','',yp.to_markdown(index=False),'',
            '## Episode bootstrap','',bp.to_markdown(index=False),'',
            '## Phase robustness','',phase.to_markdown(index=False),'',
            '## 2024+ overlap after full-history H4 warm-start','',OV.to_markdown(index=False),'',
            '## Rolling 12m / 18m diagnostic summary','',RS.to_markdown(index=False),'',
            '## Frozen interpretation','',
            '- This lab does not optimize any threshold or add a selector.','- If long-history episode count rises materially and aggregate/CI/year transfer improve, the 013 underpowered-sample thesis gains support.','- If pre-2024 years are mostly negative while 2026 remains dominant, classify B3×LH+BOS as regime-migrating rather than a universal SELL core.']
    (OUT/'REPORT.md').write_text('\n'.join(report)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
