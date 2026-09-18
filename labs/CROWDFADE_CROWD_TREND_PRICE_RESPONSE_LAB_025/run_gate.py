from pathlib import Path
import importlib.util,json
import numpy as np

ROOT=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025')
OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)

def load_base():
    path=ROOT/'run.py'
    spec=importlib.util.spec_from_file_location('lab025_hist',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.DATA=ROOT/'data';m.KDIR=m.DATA/'klines1m'
    return m

def stats(a):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    p=a[a>0].sum();n=abs(a[a<0].sum())
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),
            'PF':float(p/n) if n else 99.,'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

from numba import njit
@njit(cache=True)
def sim_gate(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,Y,DAY,mode):
    cap=len(dt);rs=np.zeros(cap);yrs=np.zeros(cap,np.int16);n=0
    k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    rejected=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        if DAY[k]!=day:day=DAY[k];dc=0
        if dc>=3:k+=1;continue
        z=Z[k];side=-1 if z>=2.5 else (1 if z<=-2.5 else 0)
        if side==0:k+=1;continue
        crowd=-side;sig=QC[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue
        lev=sig+side*.25*a;ci=-1;mx=0.
        for j in range(k+1,min(len(dt)-2,k+4)+1):
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/a
            if exc>mx:mx=exc
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j;break
        if ci<0:k+=1;continue

        aligned=(H1[k]!=0 and H4[k]!=0 and H1[k]==H4[k])
        withtrend=aligned and side==H1[k]
        counter=aligned and side!=H1[k]
        veto=False
        if mode==1 and aligned and mx>.75:veto=True
        elif mode==2 and withtrend and mx>.75:veto=True
        elif mode==3 and counter and mx>.75:veto=True
        if veto:
            rejected+=1;k=ci+1;continue

        entry=QC[ci]-side*.60*a
        ps=np.searchsorted(ts,dt[ci])+1;pe=np.searchsorted(ts,dt[ci]+20*60,'right');ei=-1
        for j in range(ps,min(len(ts),pe)):
            if (side>0 and L[j]<=entry) or (side<0 and H[j]>=entry):ei=j;break
        if ei<0:k=ci+1;continue

        risk=4.5*a;sl=entry-side*risk;tp=entry+side*10*a
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+24*3600,'left'));xp=C[xe];ex=xe
        for j in range(ei+1,xe+1):
            if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;ex=j;break
            if (side>0 and H[j]>=tp) or (side<0 and L[j]<=tp):xp=tp;ex=j;break
        R=side*(xp-entry)/risk-(.5/10000.)*entry/risk
        rs[n]=R;yrs[n]=Y[ci];n+=1
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
    return rs[:n],yrs[:n],rejected

def main():
    m=load_base();p,q=m.prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
         q.close_ts.to_numpy(np.int64),q.h.to_numpy(float),q.l.to_numpy(float),q.c.to_numpy(float),
         q.z.to_numpy(float),q.atr.to_numpy(float),q.h1.to_numpy(np.int64),q.h4.to_numpy(np.int64),
         q.yr.to_numpy(np.int64),q.daykey.to_numpy(np.int64)]
    sim_gate(*[x[:1000] for x in arr],0)
    modes=[('BASELINE',0),('VETO_ALIGNED_GT_0P75',1),('VETO_WITH_TREND_GT_0P75',2),('VETO_COUNTERTREND_GT_0P75',3)]
    rows=[]
    for name,mode in modes:
        r,yr,rejected=sim_gate(*arr,mode)
        annual={str(y):stats(r[yr==y]) for y in range(2021,2026)}
        rows.append({'name':name,'all':stats(r),'rejected_signals':int(rejected),
                     'positive_years':int(sum(v['SumR']>0 for v in annual.values())),'annual':annual})
    out={'stage':'LAB025_B_CAUSAL_GATE','period':'2021-2025 historical',
         'rule':'veto after frozen confirmation, before limit entry, when causal crowd-direction excursion >0.75 ATR in specified aligned H1/H4 context',
         'results':rows,'exploratory_after_stage_A':True}
    (OUT/'gate_summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
