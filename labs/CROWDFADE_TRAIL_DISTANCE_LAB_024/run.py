from pathlib import Path
import importlib.util,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_TRAIL_DISTANCE_LAB_024')
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
TRAILS=[('NO_TRAIL',0.0),('TRAIL_0P5R',0.5),('TRAIL_1P0R',1.0),('TRAIL_2P5R',2.5)]
ACTIVATE_R=1.0

def load_base():
    path=Path('labs/CROWDFADE_EXIT_RISK_DIAGNOSTICS_LAB_020/run.py')
    spec=importlib.util.spec_from_file_location('lab020_hist',path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.ROOT=ROOT; m.DATA=ROOT/'data'; m.KDIR=m.DATA/'klines1m'; m.OUT=OUT
    return m

@njit(cache=True)
def sim(ts,O,H,L,C,dt,CL,Z,A,AM,Y,DAY,trail_dist):
    cap=len(dt)
    rs=np.zeros(cap); yrs=np.zeros(cap,np.int16); reasons=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        if DAY[k]!=day:day=DAY[k];dc=0
        if dc>=3:k+=1;continue
        z=Z[k];side=-1 if z>=2.5 else (1 if z<=-2.5 else 0)
        if side==0:k+=1;continue
        sig=CL[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*.25*a;ci=-1
        for j in range(k+1,min(len(dt)-2,k+4)+1):
            if (side>0 and CL[j]>=lev) or (side<0 and CL[j]<=lev):ci=j;break
        if ci<0:k+=1;continue

        entry=CL[ci]-side*.60*a
        ps=np.searchsorted(ts,dt[ci])+1; pe=np.searchsorted(ts,dt[ci]+20*60,'right'); ei=-1
        for j in range(ps,min(len(ts),pe)):
            if (side>0 and L[j]<=entry) or (side<0 and H[j]>=entry):ei=j;break
        if ei<0:k=ci+1;continue

        risk=4.5*a; stop=entry-side*risk; tp=entry+side*10.0*a
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+24*3600,'left'))
        xp=C[xe]; ex=xe; reason=0; best=entry; active=False
        for j in range(ei+1,xe+1):
            sh=(side>0 and L[j]<=stop) or (side<0 and H[j]>=stop)
            th=(side>0 and H[j]>=tp) or (side<0 and L[j]<=tp)
            if sh:
                xp=stop;ex=j;reason=-3 if active else -1;break
            if th:
                xp=tp;ex=j;reason=1;break

            if trail_dist>0:
                cand=H[j] if side>0 else L[j]
                if (side>0 and cand>best) or (side<0 and cand<best):best=cand
                mfe=side*(best-entry)/risk
                if mfe>=ACTIVATE_R:
                    active=True
                    trstop=best-side*trail_dist*risk
                    if side>0: stop=max(stop,trstop)
                    else: stop=min(stop,trstop)

        R=side*(xp-entry)/risk-(.50/10000.)*entry/risk
        rs[n]=R; yrs[n]=Y[ci]; reasons[n]=reason; n+=1
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
    return rs[:n],yrs[:n],reasons[:n]

def metrics(x):
    x=np.asarray(x,float)
    eq=np.cumsum(x); peak=np.maximum.accumulate(np.r_[0.,eq])[1:]; dd=peak-eq
    pos=x[x>0].sum(); neg=abs(x[x<0].sum())
    return {'N':int(len(x)),'WR':float((x>0).mean()),'EV':float(x.mean()),'SumR':float(x.sum()),
            'PF':float(pos/neg) if neg else 99.,'MaxDD_R':float(dd.max()) if len(dd) else 0.,
            'R_DD':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else 99.}

def main():
    m=load_base(); p,q=m.prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
         q.close_ts.to_numpy(np.int64),q.c.to_numpy(float),q.z.to_numpy(float),q.atr.to_numpy(float),q.atr_med96.to_numpy(float),
         q.yr.to_numpy(np.int64),q.daykey.to_numpy(np.int64)]
    sim(*[x[:1000] for x in arr],0.0)

    rows=[]; seqs=[]
    for name,dist in TRAILS:
        r,yr,reason=sim(*arr,dist)
        eq=np.cumsum(r);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
        seqs.append(pd.DataFrame({'mode':name,'trade_index':np.arange(1,len(r)+1),'year':yr,
                                  'R':r,'equity':eq,'drawdown':dd}))
        annual={str(y):metrics(r[yr==y]) for y in range(2021,2026)}
        rows.append({'name':name,'trail_distance_R':dist,'activation_R':ACTIVATE_R,
                     'all':metrics(r),'positive_years':int(sum(v['SumR']>0 for v in annual.values())),
                     'annual':annual,
                     'exit_mix':{'SL':int((reason==-1).sum()),'TRAIL':int((reason==-3).sum()),
                                 'TP':int((reason==1).sum()),'TIME':int((reason==0).sum())}})
    pd.concat(seqs,ignore_index=True).to_csv(OUT/'equity_sequence_2021_2025.csv',index=False)
    out={'lab':'CROWDFADE_TRAIL_DISTANCE_LAB_024','period':'2021-2025 historical',
         'definition':'4.5 ATR hard SL. Trailing activates at +1R MFE. Trail distance is 0.5R / 1R / 2.5R. Stop updates after completed 1m bar and is effective next bar.',
         'warning':'Historical path uses 1m OHLC, not ticks.','results':rows}
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
