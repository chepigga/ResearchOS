#!/usr/bin/env python3
"""SELL_CORE_016 — 2026_EDGE_SOURCE_DECOMPOSITION, exact frozen 2024-2026 runtime.
No selector search. Exact LR=2 LH+BOS and canonical H4 ST/B3. H2 age<=2 remains an external benchmark only.
"""
from pathlib import Path
import numpy as np, pandas as pd
import u02c2_v283_market_clock_conditional as base

OUT=Path('sell_core_016_out'); OUT.mkdir(exist_ok=True)
LR=2; LB=120; START=20000; TAIL=6000; COST=27.5; BOOT=20000; SEED=416016

def pf(x):
    z=np.asarray(pd.Series(x).dropna(),float); gp=z[z>0].sum(); gl=-z[z<0].sum()
    return gp/gl if gl>0 else np.nan

def prep(m1,m5):
    N=len(m1); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float); C=m1.close.to_numpy(float)
    nb=(N+59)//60; hh=np.empty(nb); hl=np.empty(nb); hc=np.empty(nb)
    for k in range(nb):
        a=k*60; b=min(a+60,N); hh[k]=H[a:b].max(); hl[k]=L[a:b].min(); hc[k]=C[b-1]
    labels={}
    def swings(k):
        hs=[]; ls=[]
        for b in range(k-LR,max(k-LB,LR),-1):
            if len(hs)<3 and all(hh[b]>=hh[b+d] for d in range(-LR,LR+1)): hs.append((b,hh[b]))
            if len(ls)<3 and all(hl[b]<=hl[b+d] for d in range(-LR,LR+1)): ls.append((b,hl[b]))
            if len(hs)>=3 and len(ls)>=3: break
        return hs,ls
    for k in range(3,nb):
        hs,ls=swings(k); labels[k]=bool(len(hs)>=2 and len(ls)>=1 and hs[0][1]<hs[1][1] and hc[k-1]<ls[0][1])
    h4=base.h4_supertrend(m5)[['time','st_dir','st_age']].copy()
    h4['st_dir']=h4.st_dir.shift(1); h4['st_age']=h4.st_age.shift(1); h4=h4.dropna().copy()
    h4.st_dir=h4.st_dir.astype(int); h4.st_age=h4.st_age.astype(int)
    h4['episode_id']=(h4.st_dir.ne(h4.st_dir.shift())|((h4.time-h4.time.shift())>pd.Timedelta(hours=4,minutes=1))).cumsum().astype(int)
    return H,labels,h4,base.h1_atr_from_m1(m1)

def hourly_grid(m1,labels,h4):
    idx=np.arange(START,len(m1)-TAIL,60,dtype=int); x=pd.DataFrame({'i':idx})
    x['time']=m1.time.iloc[idx].to_numpy(); x['k']=idx//60; x['lhbos']=[labels.get(int(k),False) for k in x.k]
    x=pd.merge_asof(x.sort_values('time'),h4.sort_values('time'),on='time',direction='backward').dropna().copy()
    x.st_dir=x.st_dir.astype(int); x.st_age=x.st_age.astype(int); x.episode_id=x.episode_id.astype(int)
    x['b3']=x.st_dir.eq(-1)&x.st_age.between(27,50); x['intersection']=x.lhbos&x.b3; x['year']=x.time.dt.year
    return x

def replay(events,m1,H,h1):
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); hct=h1.close_time.to_numpy('datetime64[ns]'); HA=h1.atr14.to_numpy(float)
    out=[]
    for r in events.sort_values('time').itertuples(index=False):
        t=pd.Timestamp(r.time); j=int(np.searchsorted(mt,np.datetime64(t),'right')); q=int(np.searchsorted(hct,np.datetime64(t),'right')-1)
        if j>=len(O) or q<0 or not np.isfinite(HA[q]) or HA[q]<=0: continue
        entry=float(O[j]); sd=1.5*float(HA[q]); sl=entry+sd; d=r._asdict()
        for hh in (48,72):
            je=int(np.searchsorted(mt,np.datetime64(t+pd.Timedelta(hours=hh)),'left'))
            if je<=j or je>=len(O): d[f'R{hh}']=np.nan; d[f'pct{hh}']=np.nan; d[f'exit{hh}']='NA'; continue
            hit=np.flatnonzero(H[j:je]>=sl)
            if hit.size: rr=-1-COST/sd; px=-(sd/entry*100)-COST/entry*100; ex='SL'
            else:
                xp=float(O[je]); rr=(entry-xp)/sd-COST/sd; px=(entry-xp)/entry*100-COST/entry*100; ex='TIME'
            d[f'R{hh}']=rr; d[f'pct{hh}']=px; d[f'exit{hh}']=ex
        out.append(d)
    return pd.DataFrame(out)

def metric(g,src,y):
    r={'source':src,'year':y,'N':len(g),'episodes':g.episode_id.nunique() if len(g) else 0}
    for h in (48,72):
        r[f'EV_R{h}']=g[f'R{h}'].mean() if len(g) else np.nan; r[f'PF{h}']=pf(g[f'R{h}']) if len(g) else np.nan; r[f'EV_pct{h}']=g[f'pct{h}'].mean() if len(g) else np.nan
    return r

def paired(a,b,col,seed):
    p=a[['episode_id',col]].merge(b[['episode_id',col]],on='episode_id',suffixes=('_a','_b')); d=(p[f'{col}_a']-p[f'{col}_b']).to_numpy(float)
    if len(d)<3:return {'N':len(d),'delta':np.nan,'lo':np.nan,'hi':np.nan,'P':np.nan}
    rng=np.random.default_rng(seed); v=rng.choice(d,(BOOT,len(d)),True).mean(1)
    return {'N':len(d),'delta':d.mean(),'lo':np.quantile(v,.025),'hi':np.quantile(v,.975),'P':(v>0).mean()}

def main():
    m1=base.load_zip(base.M1ZIP); m5=base.load_zip(base.M5ZIP); H,labels,h4,h1=prep(m1,m5); hr=hourly_grid(m1,labels,h4)
    h4c=h4.copy(); h4c['year']=h4c.time.dt.year
    pops={'A_GLOBAL_H4_CLOCK':h4c,'B_H4_BEAR':h4c[h4c.st_dir==-1],'C_B3':h4c[(h4c.st_dir==-1)&h4c.st_age.between(27,50)],'D_LH_BOS':hr[hr.lhbos],'E_B3_X_LH_BOS':hr[hr.intersection]}
    led={}; rows=[]
    for s,e in pops.items():
        tr=replay(e,m1,H,h1); led[s]=tr; tr.to_csv(OUT/f'{s}.csv',index=False)
        for y,g in tr.groupby('year'): rows.append(metric(g,s,int(y)))
    Y=pd.DataFrame(rows); Y.to_csv(OUT/'source_yearly.csv',index=False)
    E=led['E_B3_X_LH_BOS'].sort_values('time').groupby('episode_id',as_index=False).first(); E.to_csv(OUT/'E_first.csv',index=False)
    ctrl=[]; onset=[]
    for r in E.itertuples(index=False):
        q=hr[(hr.episode_id==r.episode_id)&(hr.st_age==r.st_age)&(hr.time!=r.time)]
        if len(q): ctrl.append(q)
        q=hr[(hr.episode_id==r.episode_id)&hr.b3].sort_values('time')
        if len(q): onset.append(q.iloc[[0]])
    C=replay(pd.concat(ctrl,ignore_index=True),m1,H,h1); O=replay(pd.concat(onset,ignore_index=True),m1,H,h1)
    C.to_csv(OUT/'same_age_other_clocks.csv',index=False); O.to_csv(OUT/'b3_onset_occurrence_episodes.csv',index=False)
    tt=[]
    for y in [2024,2025,2026]:
        a=E[E.year==y]; c=C[C.year==y].groupby('episode_id',as_index=False)[['R48','R72']].mean(); o=O[O.year==y]
        for h in (48,72):
            z=paired(a,c,f'R{h}',SEED+y+h); z.update(year=y,comparison='ACTUAL_MINUS_SAME_AGE',hold=h); tt.append(z)
            z=paired(a,o,f'R{h}',SEED+500+y+h); z.update(year=y,comparison='ACTUAL_MINUS_B3_ONSET',hold=h); tt.append(z)
    a=E[E.year.isin([2024,2025,2026])]; c=C.groupby('episode_id',as_index=False)[['R48','R72']].mean(); o=O
    for h in (48,72):
        z=paired(a,c,f'R{h}',SEED+1000+h); z.update(year='POOLED',comparison='ACTUAL_MINUS_SAME_AGE',hold=h); tt.append(z)
        z=paired(a,o,f'R{h}',SEED+1500+h); z.update(year='POOLED',comparison='ACTUAL_MINUS_B3_ONSET',hold=h); tt.append(z)
    T=pd.DataFrame(tt); T.to_csv(OUT/'timing.csv',index=False)
    b3first=h4c[(h4c.st_dir==-1)&h4c.st_age.between(27,50)].sort_values('time').groupby('episode_id',as_index=False).first(); b3first['occ']=b3first.episode_id.isin(E.episode_id).astype(int)
    BO=replay(b3first,m1,H,h1); BO['occ']=BO.episode_id.isin(E.episode_id).astype(int); oo=[]
    for y,g in BO.groupby('year'):
        for f,gg in g.groupby('occ'): oo.append(metric(gg,'OCCURRENCE_B3_ONSET' if f else 'NON_OCCURRENCE_B3_ONSET',int(y)))
    OO=pd.DataFrame(oo); OO.to_csv(OUT/'occurrence_attribution.csv',index=False)
    report=['# SELL_CORE_016 — 2026_EDGE_SOURCE_DECOMPOSITION','', '## Source ladder by year','',Y.to_markdown(index=False),'','## Exact timing tests','',T.to_markdown(index=False),'','## B3-onset occurrence attribution (future-conditioned, descriptive only)','',OO.to_markdown(index=False),'','## External benchmark','- H2 age<=2: user-confirmed EV +0.073%, 2/3 years, ~12/week; exact detector not reconstructed in this LAB.']
    (OUT/'REPORT.md').write_text('\n'.join(report)); print((OUT/'REPORT.md').read_text())
if __name__=='__main__': main()
