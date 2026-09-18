from pathlib import Path
import importlib.util,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_TRAIL_DISTANCE_LAB_024')
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
TRAILS=[('NO_TRAIL',0.0),('TRAIL_0P5R',0.5),('TRAIL_1P0R',1.0),('TRAIL_2P5R',2.5)]
ACTIVATE_R=1.0

def load_base():
    path=Path('labs/CROWDFADE_EXIT_RISK_DIAGNOSTICS_LAB_020/run_2026.py')
    spec=importlib.util.spec_from_file_location('lab020_2026',path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.ROOT=ROOT; m.DATA=ROOT/'stress_data'; m.OUT=OUT
    return m

@njit(cache=True)
def sim(ts,O,H,L,C,dt,cl,zd,ad,amed,trail_dist):
    cap=len(dt)
    rs=np.zeros(cap); ets=np.zeros(cap,np.int64); reasons=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0
    while k<len(dt)-2:
        t=int(dt[k]);d=t//86400
        if d!=day:day=d;dc=0
        if dc>=3:k+=1;continue
        z=zd[k];side=-1 if z>=2.5 else (1 if z<=-2.5 else 0)
        if side==0:k+=1;continue
        sig=cl[k];a=ad[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*.25*a;ci=-1;j=k+1
        while j<len(dt) and dt[j]<=t+3600:
            if (side>0 and cl[j]>=lev) or (side<0 and cl[j]<=lev):ci=j;break
            j+=1
        if ci<0:k+=1;continue

        entry=cl[ci]-side*.60*a
        ps=np.searchsorted(ts,int(dt[ci])+1);pe=np.searchsorted(ts,int(dt[ci])+1200,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):ei=q;break
        if ei<0:k=ci+1;continue

        risk=4.5*a;stop=entry-side*risk;tp=entry+side*10.0*a
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+86400,'left'))
        xp=C[xe];xi=xe;reason=0;best=entry;active=False
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=stop) or (side<0 and H[q]>=stop)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:
                xp=stop;xi=q;reason=-3 if active else -1;break
            if th:
                xp=tp;xi=q;reason=1;break

            if trail_dist>0:
                cand=H[q] if side>0 else L[q]
                if (side>0 and cand>best) or (side<0 and cand<best):best=cand
                mfe=side*(best-entry)/risk
                if mfe>=ACTIVATE_R:
                    active=True
                    trstop=best-side*trail_dist*risk
                    stop=max(stop,trstop) if side>0 else min(stop,trstop)

        R=side*(xp-entry)/risk-(.50/10000.)*entry/risk
        rs[n]=R;ets[n]=ts[ei];reasons[n]=reason;n+=1
        dc+=1;last=entry;la=a;has=True;k=np.searchsorted(dt,int(ts[xi])+1)
    return rs[:n],ets[:n],reasons[:n]

def metrics(x):
    x=np.asarray(x,float)
    eq=np.cumsum(x);peak=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=peak-eq
    pos=x[x>0].sum();neg=abs(x[x<0].sum())
    return {'N':int(len(x)),'WR':float((x>0).mean()),'EV':float(x.mean()),'SumR':float(x.sum()),
            'PF':float(pos/neg) if neg else 99.,'MaxDD_R':float(dd.max()) if len(dd) else 0.,
            'R_DD':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else 99.}

def main():
    m=load_base();arr=m.prep()
    sim(*[x[:2000] for x in arr],0.0)

    rows=[];seqs=[]
    for name,dist in TRAILS:
        r,ets,reason=sim(*arr,dist)
        months=pd.to_datetime(ets,unit='s',utc=True).to_period('M').astype(str)
        eq=np.cumsum(r);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
        seqs.append(pd.DataFrame({'mode':name,'entry_time_utc':pd.to_datetime(ets,unit='s',utc=True).astype(str),
                                  'month':months,'R':r,'equity':eq,'drawdown':dd}))
        monthly={mo:metrics(r[months==mo]) for mo in sorted(set(months))}
        rows.append({'name':name,'trail_distance_R':dist,'activation_R':ACTIVATE_R,
                     'all':metrics(r),'positive_months':int(sum(v['SumR']>0 for v in monthly.values())),
                     'monthly':monthly,
                     'exit_mix':{'SL':int((reason==-1).sum()),'TRAIL':int((reason==-3).sum()),
                                 'TP':int((reason==1).sum()),'TIME':int((reason==0).sum())}})
    pd.concat(seqs,ignore_index=True).to_csv(OUT/'equity_sequence_2026.csv',index=False)
    out={'lab':'CROWDFADE_TRAIL_DISTANCE_LAB_024','period':'2026 seconds forward-shadow/stress',
         'definition':'4.5 ATR hard SL. Trailing activates at +1R MFE. Trail distance 0.5R / 1R / 2.5R. Stop updates after completed second and is effective next second.',
         'warning':'1-second OHLC is not a true exchange tick sequence.','results':rows}
    (OUT/'stress_2026.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
