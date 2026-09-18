from pathlib import Path
import importlib.util,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_V200_INTEGRATED_DECISIONS_LAB_027')
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
TRAIL_ARM_R=1.0
TRAIL_DIST_R=2.5

def load_base():
    path=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025/run_2026.py')
    spec=importlib.util.spec_from_file_location('lab025_2026',path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.ROOT=ROOT; m.DATA=ROOT/'stress_data'; m.OUT=OUT
    return m

@njit(cache=True)
def sim(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,exit_mode):
    cap=len(dt)
    rs=np.zeros(cap);ets=np.zeros(cap,np.int64);qualities=np.zeros(cap,np.int8)
    cexc=np.zeros(cap);reasons=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0
    while k<len(dt)-2:
        t=int(dt[k]);d=t//86400
        if d!=day:day=d;dc=0
        if dc>=3:k+=1;continue
        z=Z[k];side=-1 if z>=2.5 else (1 if z<=-2.5 else 0)
        if side==0:k+=1;continue
        sig=QC[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue

        crowd=-side;lev=sig+side*.25*a;ci=-1;mx=0.;j=k+1
        while j<len(dt) and dt[j]<=t+3600:
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/a
            if exc>mx:mx=exc
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):ci=j;break
            j+=1
        if ci<0:k+=1;continue

        aligned=(H1[k]!=0 and H4[k]!=0 and H1[k]==H4[k])
        quality=0
        if aligned and side==H1[k] and mx<=.75: quality=1
        elif aligned and mx>.75: quality=-1

        entry=QC[ci]-side*.60*a
        ps=np.searchsorted(ts,int(dt[ci])+1);pe=np.searchsorted(ts,int(dt[ci])+1200,'right');ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):ei=q;break
        if ei<0:k=ci+1;continue

        risk=4.5*a;stop=entry-side*risk;tp=entry+side*10*a
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+86400,'left'))
        xp=C[xe];xi=xe;reason=0;peak=entry
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=stop) or (side<0 and H[q]>=stop)
            th=(exit_mode<=1) and ((side>0 and H[q]>=tp) or (side<0 and L[q]<=tp))
            if sh:
                xp=stop;xi=q
                orig=entry-side*risk
                improved=(side>0 and stop>orig+1e-12) or (side<0 and stop<orig-1e-12)
                reason=-2 if improved else -1
                break
            if th:
                xp=tp;xi=q;reason=1;break

            if exit_mode==1 or exit_mode==3:
                cand=H[q] if side>0 else L[q]
                if (side>0 and cand>peak) or (side<0 and cand<peak):peak=cand
                mfe=side*(peak-entry)/risk
                if mfe>=TRAIL_ARM_R:
                    tr=peak-side*TRAIL_DIST_R*risk
                    if side>0:
                        if tr>stop:stop=tr
                    else:
                        if tr<stop:stop=tr

        R=side*(xp-entry)/risk-(.50/10000.)*entry/risk
        rs[n]=R;ets[n]=ts[ei];qualities[n]=quality;cexc[n]=mx;reasons[n]=reason;n+=1
        dc+=1;last=entry;la=a;has=True;k=np.searchsorted(dt,int(ts[xi])+1)
    return rs[:n],ets[:n],qualities[:n],cexc[:n],reasons[:n]

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:return {'N':0}
    eq=np.cumsum(x);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
    pos=x[x>0].sum();neg=abs(x[x<0].sum())
    cur=mx=0
    for v in x:
        if v<0:cur+=1;mx=max(mx,cur)
        else:cur=0
    return {'N':int(len(x)),'WR':float((x>0).mean()),'EV':float(x.mean()),'SumR':float(x.sum()),
            'PF':float(pos/neg) if neg else 99.,'MaxDD_R':float(dd.max()) if len(dd) else 0.,
            'R_DD':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else 99.,
            'MaxConsecutiveLosses':int(mx)}

def risk_weight(q):
    w=np.ones(len(q),float);w[q>0]=1.5;w[q<0]=.75;return w

def main():
    m=load_base();arr=m.prep()
    sim(*[x[:2000] for x in arr],0)

    modes=[
      ('TP10_FLAT',0,False),
      ('TP10_LAB026',0,True),
      ('TP10_TRAIL2P5_FLAT',1,False),
      ('TP10_TRAIL2P5_LAB026',1,True),
      ('NO_TP_NO_TRAIL_FLAT',2,False),
      ('NO_TP_NO_TRAIL_LAB026',2,True),
      ('NO_TP_TRAIL2P5_FLAT',3,False),
      ('V200_FULL',3,True),
    ]
    cache={i:sim(*arr,i) for i in range(4)}
    rows=[];seqs=[]
    for name,exit_mode,use_tiers in modes:
        raw,ets,qual,cexc,reason=cache[exit_mode]
        mult=risk_weight(qual) if use_tiers else np.ones(len(raw))
        wr=raw*mult
        months=pd.to_datetime(ets,unit='s',utc=True).to_period('M').astype(str)
        eq=np.cumsum(wr);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
        monthly={mo:metrics(wr[months==mo]) for mo in sorted(set(months))}
        rows.append({
          'name':name,'exit_mode':int(exit_mode),'risk_tiers':bool(use_tiers),
          'all':metrics(wr),'positive_months':int(sum(v['SumR']>0 for v in monthly.values())),
          'monthly':monthly,
          'state_counts':{'HIGH':int((qual>0).sum()),'NORMAL':int((qual==0).sum()),'LOW':int((qual<0).sum())},
          'exit_mix':{'SL':int((reason==-1).sum()),'TRAIL':int((reason==-2).sum()),
                      'TIME':int((reason==0).sum()),'TP':int((reason==1).sum())},
        })
        seqs.append(pd.DataFrame({
          'mode':name,'entry_time_utc':pd.to_datetime(ets,unit='s',utc=True).astype(str),
          'month':months,'quality':qual,'crowd_exc_atr':cexc,'raw_R':raw,'risk_mult':mult,
          'weighted_R':wr,'equity_R':eq,'drawdown_R':dd,'exit_reason':reason
        }))
    pd.concat(seqs,ignore_index=True).to_csv(OUT/'equity_sequence_2026.csv',index=False)
    out={'lab':'CROWDFADE_V200_INTEGRATED_DECISIONS_LAB_027',
         'period':'2026 seconds forward-shadow/stress',
         'warning':'1-second OHLC is not true exchange tick sequence; trailing becomes effective next second.',
         'results':rows}
    (OUT/'stress_2026.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
