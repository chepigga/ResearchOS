#!/usr/bin/env python3
"""SELL_CORE_013B — B3 x exact-parity LH+BOS incremental edge.
013A parity passed on common frozen data: LH+BOS N=1609, gross WR=49.534%, gross EV=+0.094974%, net EV=-0.001026%.
Frozen before 013B outcomes:
- exact user LH+BOS detector (60-row H1, LR=2, lb=120, LH + previous-H1 BOS down)
- canonical H4 ST ATR10x3 BAR_OPEN lag1; B3 aligned = DOWN and age 27..50
- common hourly candidate grid; phase offsets 0/20/40 minutes from user's START=20000 (:20/:40/:00)
- groups: ALL, LHBOS, B3, B3_LHBOS, B3_NO_LHBOS, LHBOS_NO_B3
- native view: user stop 1.5*(SMA M1 TR60*60), 48h, cost 0.096%
- canonical view: next M1 open, SL 1.5*completed H1 ATR14, noTP, 48h primary/72h sensitivity, $27.5/BTC
- yearly and H4-episode cluster bootstrap. No topology/funding/FVG/v283 rescue gates.
"""
from pathlib import Path
import numpy as np, pandas as pd
import u02c2_v283_market_clock_conditional as base
OUT=Path('sell_core_013b_out'); OUT.mkdir(exist_ok=True)
START=20000; TAIL=6000; STEP=60; LR=2; LB=120; COST_PCT=.096; COST_USD=27.5; BOOT=20000; SEED=413013
PHASES=(0,20,40); HOLDS=(48,72)

def pf(z):
    x=np.asarray(pd.Series(z).dropna(),float); gp=x[x>0].sum(); gl=-x[x<0].sum(); return gp/gl if gl>0 else np.nan

def prep(m1,m5):
    N=len(m1); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float); C=m1.close.to_numpy(float)
    nb=(N+59)//60; hh=np.empty(nb); hl=np.empty(nb); hc=np.empty(nb)
    for k in range(nb):
        a=k*60;b=min(a+60,N);hh[k]=H[a:b].max();hl[k]=L[a:b].min();hc[k]=C[b-1]
    prev=np.r_[np.nan,C[:-1]]; tr=np.nanmax(np.vstack([H-L,np.abs(H-prev),np.abs(L-prev)]),axis=0);tr[0]=H[0]-L[0]
    a60=pd.Series(tr).rolling(60,min_periods=60).mean().to_numpy()
    labels={}
    def swings(k):
        hs=[];ls=[]
        for b in range(k-LR,max(k-LB,LR),-1):
            if len(hs)<3 and all(hh[b]>=hh[b+d] for d in range(-LR,LR+1)):hs.append((b,hh[b]))
            if len(ls)<3 and all(hl[b]<=hl[b+d] for d in range(-LR,LR+1)):ls.append((b,hl[b]))
            if len(hs)>=3 and len(ls)>=3:break
        return hs,ls
    for k in range(3,nb):
        hs,ls=swings(k)
        labels[k]=bool(len(hs)>=2 and len(ls)>=1 and hs[0][1]<hs[1][1] and hc[k-1]<ls[0][1])
    h4=base.h4_supertrend(m5)[['time','st_dir','st_age']].copy();h4['st_dir']=h4.st_dir.shift(1);h4['st_age']=h4.st_age.shift(1);h4=h4.dropna().copy();h4.st_dir=h4.st_dir.astype(int);h4.st_age=h4.st_age.astype(int)
    h4['episode_id']=(h4.st_dir.ne(h4.st_dir.shift())|((h4.time-h4.time.shift())>pd.Timedelta(hours=4,minutes=1))).cumsum().astype(int)
    return H,L,C,a60,labels,h4,base.h1_atr_from_m1(m1)

def clocks(m1,labels,h4,phase):
    idx=np.arange(START+phase,len(m1)-TAIL,STEP,dtype=int); x=pd.DataFrame({'i':idx});x['time']=m1.time.iloc[idx].to_numpy();x['k']=idx//60;x['lhbos']=[labels.get(int(k),False) for k in x.k]
    x=pd.merge_asof(x.sort_values('time'),h4.sort_values('time'),on='time',direction='backward');x=x.dropna(subset=['st_dir','st_age']).copy();x['st_dir']=x.st_dir.astype(int);x['st_age']=x.st_age.astype(int);x['episode_id']=x.episode_id.astype(int);x['b3']=x.st_dir.eq(-1)&x.st_age.between(27,50);x['year']=pd.to_datetime(x.time).dt.year;x['phase_min']=phase
    return x

def native_replay(x,m1,H,C,a60):
    out=[];N=len(m1)
    for r in x.itertuples(index=False):
        i=int(r.i);sd=1.5*a60[i]*60
        if not np.isfinite(sd) or sd<=0:continue
        entry=C[i];sl=entry+sd;end=min(i+2880,N-1);hit=np.flatnonzero(H[i+1:end+1]>=sl);xp=sl if hit.size else C[end]
        gross=(entry-xp)/entry*100;net=gross-COST_PCT;d=r._asdict();d.update(view='NATIVE',hold_h=48,R=np.nan,pct=net,gross_pct=gross,exit_type='SL' if hit.size else 'TIME');out.append(d)
    return pd.DataFrame(out)

def canonical_replay(x,m1,H,h1,hold):
    mt=m1.time.to_numpy('datetime64[ns]');O=m1.open.to_numpy(float);hct=h1.close_time.to_numpy('datetime64[ns]');HA=h1.atr14.to_numpy(float);out=[]
    for r in x.itertuples(index=False):
        sig=pd.Timestamp(r.time);j=int(r.i)+1;q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1);je=int(np.searchsorted(mt,np.datetime64(sig+pd.Timedelta(hours=hold)),'left'))
        if j>=len(O) or q<0 or je<=j or je>=len(O) or not np.isfinite(HA[q]) or HA[q]<=0:continue
        entry=float(O[j]);sd=1.5*float(HA[q]);sl=entry+sd;hit=np.flatnonzero(H[j:je]>=sl)
        if hit.size:rr=-1-COST_USD/sd;pct=-(sd/entry*100)-COST_USD/entry*100;ex='SL'
        else:xp=float(O[je]);rr=(entry-xp)/sd-COST_USD/sd;pct=(entry-xp)/entry*100-COST_USD/entry*100;ex='TIME'
        d=r._asdict();d.update(view='CANONICAL',hold_h=hold,R=rr,pct=pct,gross_pct=np.nan,exit_type=ex);out.append(d)
    return pd.DataFrame(out)

def group_mask(x,name):
    if name=='ALL':return np.ones(len(x),bool)
    if name=='LHBOS':return x.lhbos.to_numpy(bool)
    if name=='B3':return x.b3.to_numpy(bool)
    if name=='B3_LHBOS':return (x.b3&x.lhbos).to_numpy(bool)
    if name=='B3_NO_LHBOS':return (x.b3&~x.lhbos).to_numpy(bool)
    if name=='LHBOS_NO_B3':return (~x.b3&x.lhbos).to_numpy(bool)

def met(g):
    z=g.pct.dropna();r=g.R.dropna() if 'R' in g else pd.Series(dtype=float)
    return {'N':len(g),'episodes':g.episode_id.nunique(),'EV_pct':float(z.mean()) if len(z) else np.nan,'PF_pct':pf(z),'WR_pct':float((z>0).mean()) if len(z) else np.nan,'EV_R':float(r.mean()) if len(r) else np.nan,'PF_R':pf(r) if len(r) else np.nan,'SL_rate':float((g.exit_type=='SL').mean())}

def boot_delta(x,a,b,value,seed):
    aa=x[group_mask(x,a)].copy();bb=x[group_mask(x,b)].copy();ids=np.union1d(aa.episode_id.unique(),bb.episode_id.unique());rng=np.random.default_rng(seed);vals=[]
    A={e:aa[aa.episode_id==e][value].dropna().to_numpy(float) for e in ids};B={e:bb[bb.episode_id==e][value].dropna().to_numpy(float) for e in ids}
    for _ in range(BOOT):
        s=rng.choice(ids,size=len(ids),replace=True);va=np.concatenate([A[e] for e in s if len(A[e])]) if any(len(A[e]) for e in s) else np.array([]);vb=np.concatenate([B[e] for e in s if len(B[e])]) if any(len(B[e]) for e in s) else np.array([])
        if len(va) and len(vb):vals.append(va.mean()-vb.mean())
    v=np.asarray(vals);obs=aa[value].mean()-bb[value].mean();return obs,float(np.quantile(v,.025)),float(np.quantile(v,.975)),float((v>0).mean())

def main():
    m1=base.load_zip('btc_1m.zip').reset_index(drop=True);m5=base.load_zip('btc_5m.zip');H,L,C,a60,labels,h4,h1=prep(m1,m5)
    alltr=[];metrics=[];years=[];deltas=[];overlap=[]
    for ph in PHASES:
        c=clocks(m1,labels,h4,ph);overlap.append({'phase_min':ph,'N':len(c),'LHBOS':int(c.lhbos.sum()),'B3':int(c.b3.sum()),'INTERSECTION':int((c.lhbos&c.b3).sum()),'P_LHBOS_given_B3':float(c[c.b3].lhbos.mean()),'P_LHBOS_given_notB3':float(c[~c.b3].lhbos.mean()),'phi':float(c[['lhbos','b3']].astype(int).corr().iloc[0,1])})
        views=[native_replay(c,m1,H,C,a60)]+[canonical_replay(c,m1,H,h1,h) for h in HOLDS]
        for tr in views:
            alltr.append(tr);v=tr.view.iloc[0];hh=int(tr.hold_h.iloc[0])
            for name in ['ALL','LHBOS','B3','B3_LHBOS','B3_NO_LHBOS','LHBOS_NO_B3']:
                g=tr[group_mask(tr,name)];metrics.append({'phase_min':ph,'view':v,'hold_h':hh,'group':name,**met(g)})
                for y,gy in g.groupby('year'):years.append({'phase_min':ph,'view':v,'hold_h':hh,'group':name,'year':int(y),**met(gy)})
            for val in ['pct']+(['R'] if v=='CANONICAL' else []):
                for a,b,label in [('B3_LHBOS','B3_NO_LHBOS','within_B3_LHBOS_uplift'),('B3_LHBOS','LHBOS_NO_B3','within_LHBOS_B3_uplift')]:
                    o,lo,hi,p=boot_delta(tr,a,b,val,SEED+ph+hh+(0 if val=='pct' else 1000)+(0 if a=='B3_LHBOS' and b=='B3_NO_LHBOS' else 2000));deltas.append({'phase_min':ph,'view':v,'hold_h':hh,'contrast':label,'metric':val,'delta':o,'CI_lo':lo,'CI_hi':hi,'P_gt0':p})
    A=pd.concat(alltr,ignore_index=True);M=pd.DataFrame(metrics);Y=pd.DataFrame(years);D=pd.DataFrame(deltas);O=pd.DataFrame(overlap)
    A.to_csv(OUT/'all_trades.csv',index=False);M.to_csv(OUT/'metrics.csv',index=False);Y.to_csv(OUT/'yearly.csv',index=False);D.to_csv(OUT/'incremental_deltas.csv',index=False);O.to_csv(OUT/'overlap.csv',index=False)
    prim=M[(M.phase_min==0)&(((M.view=='NATIVE')&(M.hold_h==48))|((M.view=='CANONICAL')&(M.hold_h==48)))];yp=Y[(Y.phase_min==0)&(Y.group.isin(['LHBOS','B3','B3_LHBOS','B3_NO_LHBOS']))&(((Y.view=='NATIVE')&(Y.hold_h==48))|((Y.view=='CANONICAL')&(Y.hold_h==48)))];dp=D[(D.phase_min==0)&(D.hold_h==48)]
    report=['# SELL_CORE_013B — B3 × exact LH+BOS INCREMENTAL EDGE','', '## Overlap / dependence','',O.to_markdown(index=False),'','## Primary phase :20, 48h','',prim.to_markdown(index=False),'','## Yearly primary','',yp.to_markdown(index=False),'','## Incremental contrasts','',dp.to_markdown(index=False),'','## Phase robustness — intersection','',M[(M.group=='B3_LHBOS')].to_markdown(index=False),'','## Boundary','', '- PASS requires B3+LH+BOS positive after costs in both native and canonical views, no phase collapse, and material positive uplift versus B3_NO_LHBOS.','- No topology/funding/FVG/v283 filters are used.']
    (OUT/'REPORT.md').write_text('\n'.join(report));print((OUT/'REPORT.md').read_text())
if __name__=='__main__':main()
