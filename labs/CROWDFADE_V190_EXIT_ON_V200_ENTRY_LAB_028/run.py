from pathlib import Path
import importlib.util,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_V190_EXIT_ON_V200_ENTRY_LAB_028')
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

def load_base():
    path=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025/run.py')
    spec=importlib.util.spec_from_file_location('lab025_hist',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.ROOT=ROOT;m.DATA=ROOT/'data';m.KDIR=m.DATA/'klines1m';m.OUT=OUT
    return m

@njit(cache=True)
def sim_v190(ts,O,H,L,C,ZPX,dt,QH,QL,QC,Z,A,H1,H4,Y,DAY,signal_exit_on,hold_hours):
    cap=len(dt)
    rs=np.zeros(cap);ets=np.zeros(cap,np.int64);yrs=np.zeros(cap,np.int16)
    qual=np.zeros(cap,np.int8);reasons=np.zeros(cap,np.int8)
    # -1 SL, -2 BE/TRAIL stop, -3 SIGNAL, -4 TIME
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

        crowd=-side;lev=sig+side*.25*a;ci=-1;mx=0.
        for j in range(k+1,min(len(dt)-2,k+4)+1):
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/a
            if exc>mx:mx=exc
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j;break
        if ci<0:k+=1;continue

        aligned=(H1[k]!=0 and H4[k]!=0 and H1[k]==H4[k])
        qstate=0
        if aligned and side==H1[k] and mx<=.75:qstate=1
        elif aligned and mx>.75:qstate=-1

        entry=QC[ci]-side*.60*a
        ps=np.searchsorted(ts,dt[ci])+1;pe=np.searchsorted(ts,dt[ci]+20*60,'right');ei=-1
        for j in range(ps,min(len(ts),pe)):
            if (side>0 and L[j]<=entry) or (side<0 and H[j]>=entry):ei=j;break
        if ei<0:k=ci+1;continue

        initial_stop=entry-side*4.5*a
        stop=initial_stop
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+hold_hours*3600,'left'))
        xp=C[xe];ex=xe;reason=-4
        peak=entry

        for j in range(ei+1,xe+1):
            # Existing protective stop is active during this bar.
            hit=(side>0 and L[j]<=stop) or (side<0 and H[j]>=stop)
            if hit:
                xp=stop;ex=j
                improved=(side>0 and stop>initial_stop+1e-12) or (side<0 and stop<initial_stop-1e-12)
                reason=-2 if improved else -1
                break

            # v190 REAL-PEAK logic approximated with 1m H/L.
            cand=H[j] if side>0 else L[j]
            if (side>0 and cand>peak) or (side<0 and cand<peak):peak=cand

            # v190 BE: current price move >= +0.50 ATR, lock +0.15 ATR.
            prof=side*(C[j]-entry)
            if prof>=.50*a:
                be=entry+side*.15*a
                if (side>0 and be>stop) or (side<0 and be<stop):stop=be

            # v190 trail: arm +2.50 ATR MFE, distance 0.50 ATR from real peak.
            mfe=side*(peak-entry)/a
            if mfe>=2.50:
                tr=peak-side*.50*a
                if (side>0 and tr>stop) or (side<0 and tr<stop):stop=tr

            # v190 signal exit after stop management.
            if signal_exit_on:
                znow=ZPX[j]
                if np.isfinite(znow) and side*znow>=1.0:
                    xp=C[j];ex=j;reason=-3;break

            if ts[j]>=ts[ei]+hold_hours*3600:
                xp=C[j];ex=j;reason=-4;break

        R=side*(xp-entry)/(4.5*a)-(.50/10000.)*entry/(4.5*a)
        rs[n]=R;ets[n]=ts[ei];yrs[n]=Y[k];qual[n]=qstate;reasons[n]=reason;n+=1
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
    return rs[:n],ets[:n],yrs[:n],qual[:n],reasons[:n]

def metrics(x):
    x=np.asarray(x,float)
    if not len(x):return {'N':0}
    eq=np.cumsum(x);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
    pos=x[x>0].sum();neg=abs(x[x<0].sum());cur=mx=0
    for v in x:
        if v<0:cur+=1;mx=max(mx,cur)
        else:cur=0
    return {'N':int(len(x)),'WR':float((x>0).mean()),'EV':float(x.mean()),'SumR':float(x.sum()),
            'PF':float(pos/neg) if neg else 99.,'MaxDD_R':float(dd.max()),'R_DD':float(x.sum()/dd.max()) if dd.max()>0 else 99.,
            'MaxConsecutiveLosses':int(mx)}

def weights(q):
    w=np.ones(len(q));w[q>0]=1.5;w[q<0]=.75;return w

def main():
    m=load_base();p,q=m.prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
         p.z.to_numpy(float),
         q.close_ts.to_numpy(np.int64),q.h.to_numpy(float),q.l.to_numpy(float),q.c.to_numpy(float),
         q.z.to_numpy(float),q.atr.to_numpy(float),q.h1.to_numpy(np.int64),q.h4.to_numpy(np.int64),
         q.yr.to_numpy(np.int64),q.daykey.to_numpy(np.int64)]
    sim_v190(*[x[:1000] for x in arr],True,6)

    modes=[('V190_EXIT_EXACT_LAB026',True,6),('V190_EXIT_NO_SIGNAL_LAB026',False,6),
           ('V190_EXIT_24H_SIGNAL_LAB026',True,24)]
    rows=[];seqs=[]
    for name,sigexit,hold in modes:
        raw,ets,yr,qual,reason=sim_v190(*arr,sigexit,hold)
        mult=weights(qual);wr=raw*mult
        eq=np.cumsum(wr);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
        annual={str(y):metrics(wr[yr==y]) for y in range(2021,2026)}
        rows.append({'name':name,'signal_exit':sigexit,'hold_hours':hold,'all':metrics(wr),
                     'positive_years':int(sum(v['SumR']>0 for v in annual.values())),'annual':annual,
                     'exit_mix':{'SL':int((reason==-1).sum()),'BE_TRAIL_STOP':int((reason==-2).sum()),
                                 'SIGNAL':int((reason==-3).sum()),'TIME':int((reason==-4).sum())}})
        seqs.append(pd.DataFrame({'mode':name,'trade_index':np.arange(1,len(raw)+1),'entry_ts':ets,'year':yr,
                                  'quality':qual,'raw_R':raw,'risk_mult':mult,'weighted_R':wr,
                                  'equity_R':eq,'drawdown_R':dd,'exit_reason':reason}))
    pd.concat(seqs,ignore_index=True).to_csv(OUT/'equity_sequence_2021_2025.csv',index=False)
    out={'lab':'CROWDFADE_V190_EXIT_ON_V200_ENTRY_LAB_028','period':'2021-2025 historical',
         'v190_exit_exact':{'BE_at_ATR':.50,'BE_lock_ATR':.15,'trail_arm_ATR':2.50,'trail_dist_ATR':.50,
                            'signal_exit_absZ_opposite':1.0,'hold_hours':6},
         'important':'Entry and hard stop are v200 frozen: Z2.5, M15 confirm0.25ATR, passive0.60ATR, SL4.5ATR, LAB026 sizing.',
         'results':rows}
    (OUT/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
