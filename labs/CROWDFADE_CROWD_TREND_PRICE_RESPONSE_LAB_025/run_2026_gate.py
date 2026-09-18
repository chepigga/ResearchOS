from pathlib import Path
import importlib.util,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025')
OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)

def load_base():
    path=ROOT/'run_2026.py'
    spec=importlib.util.spec_from_file_location('lab025_2026',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.DATA=ROOT/'stress_data'
    return m

def stats(a):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    p=a[a>0].sum();n=abs(a[a<0].sum())
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),
            'PF':float(p/n) if n else 99.,'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

@njit(cache=True)
def sim_gate(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,mode):
    cap=len(dt);rs=np.zeros(cap);ets=np.zeros(cap,np.int64);n=0
    k=0;last=0.;la=0.;has=False;day=-1;dc=0;rejected=0
    while k<len(dt)-2:
        t=int(dt[k]);d=t//86400
        if d!=day:day=d;dc=0
        if dc>=3:k+=1;continue
        z=Z[k];side=-1 if z>=2.5 else (1 if z<=-2.5 else 0)
        if side==0:k+=1;continue
        crowd=-side;sig=QC[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*.25*a;ci=-1;mx=0.;j=k+1
        while j<len(dt) and dt[j]<=t+3600:
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/a
            if exc>mx:mx=exc
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):ci=j;break
            j+=1
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
        ps=np.searchsorted(ts,int(dt[ci])+1);pe=np.searchsorted(ts,int(dt[ci])+1200,'right');ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):ei=q;break
        if ei<0:k=ci+1;continue

        risk=4.5*a;sl=entry-side*risk;tp=entry+side*10*a
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+86400,'left'));xp=C[xe];xi=xe
        for q in range(ei+1,xe+1):
            if (side>0 and L[q]<=sl) or (side<0 and H[q]>=sl):xp=sl;xi=q;break
            if (side>0 and H[q]>=tp) or (side<0 and L[q]<=tp):xp=tp;xi=q;break
        R=side*(xp-entry)/risk-(.5/10000.)*entry/risk
        rs[n]=R;ets[n]=ts[ei];n+=1
        dc+=1;last=entry;la=a;has=True;k=np.searchsorted(dt,int(ts[xi])+1)
    return rs[:n],ets[:n],rejected

def main():
    m=load_base();arr=m.prep();sim_gate(*[x[:2000] for x in arr],0)
    modes=[('BASELINE',0),('VETO_ALIGNED_GT_0P75',1),('VETO_WITH_TREND_GT_0P75',2),('VETO_COUNTERTREND_GT_0P75',3)]
    rows=[]
    for name,mode in modes:
        r,ets,rejected=sim_gate(*arr,mode)
        months=pd.to_datetime(ets,unit='s',utc=True).to_period('M').astype(str)
        monthly={mo:stats(r[months==mo]) for mo in sorted(set(months))}
        rows.append({'name':name,'all':stats(r),'rejected_signals':int(rejected),
                     'positive_months':int(sum(v['SumR']>0 for v in monthly.values())),'monthly':monthly})
    out={'stage':'LAB025_B_CAUSAL_GATE','period':'2026 seconds forward-shadow/stress',
         'rule':'veto after frozen confirmation, before limit entry, when causal crowd-direction excursion >0.75 ATR in specified aligned H1/H4 context',
         'results':rows,'exploratory_after_stage_A':True}
    (OUT/'gate_stress_2026.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
