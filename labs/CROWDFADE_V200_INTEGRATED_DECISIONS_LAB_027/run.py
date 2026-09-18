from pathlib import Path
import importlib.util,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_V200_INTEGRATED_DECISIONS_LAB_027')
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Exit modes
# 0 = TP10, no trail
# 1 = TP10 + 2.5R trail
# 2 = no TP, no trail
# 3 = no TP + 2.5R trail  <-- v200 exit engine
TRAIL_ARM_R=1.0
TRAIL_DIST_R=2.5

def load_base():
    path=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025/run.py')
    spec=importlib.util.spec_from_file_location('lab025_hist',path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.ROOT=ROOT; m.DATA=ROOT/'data'; m.KDIR=m.DATA/'klines1m'; m.OUT=OUT
    return m

@njit(cache=True)
def sim(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,Y,DAY,exit_mode):
    cap=len(dt)
    rs=np.zeros(cap); ets=np.zeros(cap,np.int64); yrs=np.zeros(cap,np.int16)
    qualities=np.zeros(cap,np.int8); crowdexc=np.zeros(cap)
    reasons=np.zeros(cap,np.int8) # -1 SL, -2 TRAIL, 0 TIME, 1 TP
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        if DAY[k]!=day:day=DAY[k];dc=0
        if dc>=3:k+=1;continue
        z=Z[k];side=-1 if z>=2.5 else (1 if z<=-2.5 else 0)
        if side==0:k+=1;continue
        sig=QC[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue

        crowd=-side
        lev=sig+side*.25*a;ci=-1;mx=0.
        for j in range(k+1,min(len(dt)-2,k+4)+1):
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/a
            if exc>mx:mx=exc
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j;break
        if ci<0:k+=1;continue

        aligned=(H1[k]!=0 and H4[k]!=0 and H1[k]==H4[k])
        quality=0
        if aligned and side==H1[k] and mx<=.75: quality=1
        elif aligned and mx>.75: quality=-1

        entry=QC[ci]-side*.60*a
        ps=np.searchsorted(ts,dt[ci])+1;pe=np.searchsorted(ts,dt[ci]+20*60,'right');ei=-1
        for j in range(ps,min(len(ts),pe)):
            if (side>0 and L[j]<=entry) or (side<0 and H[j]>=entry):ei=j;break
        if ei<0:k=ci+1;continue

        risk=4.5*a;stop=entry-side*risk;tp=entry+side*10.0*a
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+24*3600,'left'))
        xp=C[xe];ex=xe;reason=0;peak=entry
        for j in range(ei+1,xe+1):
            sh=(side>0 and L[j]<=stop) or (side<0 and H[j]>=stop)
            th=(exit_mode<=1) and ((side>0 and H[j]>=tp) or (side<0 and L[j]<=tp))
            if sh:
                xp=stop;ex=j
                initial=entry-side*risk
                # If stop has improved materially above/below original hard stop, classify as trail.
                improved=(side>0 and stop>initial+1e-12) or (side<0 and stop<initial-1e-12)
                reason=-2 if improved else -1
                break
            if th:
                xp=tp;ex=j;reason=1;break

            if exit_mode==1 or exit_mode==3:
                cand=H[j] if side>0 else L[j]
                if (side>0 and cand>peak) or (side<0 and cand<peak):peak=cand
                mfe=side*(peak-entry)/risk
                if mfe>=TRAIL_ARM_R:
                    tr=peak-side*TRAIL_DIST_R*risk
                    if side>0:
                        if tr>stop:stop=tr
                    else:
                        if tr<stop:stop=tr

        R=side*(xp-entry)/risk-(.50/10000.)*entry/risk
        rs[n]=R;ets[n]=ts[ei];yrs[n]=Y[k];qualities[n]=quality;crowdexc[n]=mx;reasons[n]=reason;n+=1
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
    return rs[:n],ets[:n],yrs[:n],qualities[:n],crowdexc[:n],reasons[:n]

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:return {'N':0}
    eq=np.cumsum(x);peak=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=peak-eq
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
    m=load_base();p,q=m.prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
         q.close_ts.to_numpy(np.int64),q.h.to_numpy(float),q.l.to_numpy(float),q.c.to_numpy(float),
         q.z.to_numpy(float),q.atr.to_numpy(float),q.h1.to_numpy(np.int64),q.h4.to_numpy(np.int64),
         q.yr.to_numpy(np.int64),q.daykey.to_numpy(np.int64)]
    sim(*[x[:1000] for x in arr],0)

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
    rows=[];seqs=[]
    cache={}
    for exit_mode in range(4):
        cache[exit_mode]=sim(*arr,exit_mode)

    for name,exit_mode,use_tiers in modes:
        raw,ets,yr,qual,cexc,reason=cache[exit_mode]
        mult=risk_weight(qual) if use_tiers else np.ones(len(raw))
        wr=raw*mult
        eq=np.cumsum(wr);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
        annual={str(y):metrics(wr[yr==y]) for y in range(2021,2026)}
        rows.append({
          'name':name,'exit_mode':int(exit_mode),'risk_tiers':bool(use_tiers),
          'all':metrics(wr),'positive_years':int(sum(v['SumR']>0 for v in annual.values())),
          'annual':annual,
          'state_counts':{'HIGH':int((qual>0).sum()),'NORMAL':int((qual==0).sum()),'LOW':int((qual<0).sum())},
          'exit_mix':{'SL':int((reason==-1).sum()),'TRAIL':int((reason==-2).sum()),
                      'TIME':int((reason==0).sum()),'TP':int((reason==1).sum())},
        })
        seqs.append(pd.DataFrame({
          'mode':name,'trade_index':np.arange(1,len(raw)+1),'entry_ts':ets,'year':yr,
          'quality':qual,'crowd_exc_atr':cexc,'raw_R':raw,'risk_mult':mult,'weighted_R':wr,
          'equity_R':eq,'drawdown_R':dd,'exit_reason':reason
        }))
    pd.concat(seqs,ignore_index=True).to_csv(OUT/'equity_sequence_2021_2025.csv',index=False)
    out={'lab':'CROWDFADE_V200_INTEGRATED_DECISIONS_LAB_027',
         'period':'2021-2025 historical',
         'definitions':{
           'TP10':'fixed TP 10 ATR = 2.222R',
           'NO_TP':'no profit ceiling; hard SL + 24h time exit',
           'TRAIL2P5':'trail distance 2.5 initial R, armed at +1R, applied next completed 1m bar',
           'LAB026':'HIGH 1.5x / NORMAL 1.0x / LOW 0.75x'
         },
         'results':rows}
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
