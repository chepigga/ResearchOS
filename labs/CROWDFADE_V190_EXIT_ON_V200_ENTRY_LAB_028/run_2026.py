from pathlib import Path
import importlib.util,zipfile,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_V190_EXIT_ON_V200_ENTRY_LAB_028')
DATA=ROOT/'stress_data';OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)

def load_base():
    path=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025/run_2026.py')
    spec=importlib.util.spec_from_file_location('lab025_2026',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.ROOT=ROOT;m.DATA=DATA;m.OUT=OUT
    return m

def load_flow_z():
    d=DATA/'flow';d.mkdir(parents=True,exist_ok=True)
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    if not list(d.glob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(d)
    f=pd.read_csv(list(d.glob('*.csv'))[0],usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy()
    f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce')
    f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t')
    rr=pd.to_numeric(f.count_long_short_ratio,errors='coerce')
    mu=rr.rolling(72,min_periods=72).mean();sd=rr.rolling(72,min_periods=72).std(ddof=0)
    z=((rr-mu)/sd.replace(0,np.nan)).to_numpy(float)
    ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    good=np.isfinite(z)
    return ft[good],z[good]

@njit(cache=True)
def z_at(ft,fz,t):
    i=np.searchsorted(ft,t,'right')-1
    if i<0:return np.nan
    if t-ft[i]>900:return np.nan
    return fz[i]

@njit(cache=True)
def sim_v190(ts,O,H,L,C,ft,fz,dt,QH,QL,QC,Z,A,H1,H4,signal_exit_on,hold_hours):
    cap=len(dt)
    rs=np.zeros(cap);ets=np.zeros(cap,np.int64);qual=np.zeros(cap,np.int8);reasons=np.zeros(cap,np.int8)
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
        qstate=0
        if aligned and side==H1[k] and mx<=.75:qstate=1
        elif aligned and mx>.75:qstate=-1

        entry=QC[ci]-side*.60*a
        ps=np.searchsorted(ts,int(dt[ci])+1);pe=np.searchsorted(ts,int(dt[ci])+1200,'right');ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):ei=q;break
        if ei<0:k=ci+1;continue

        initial_stop=entry-side*4.5*a;stop=initial_stop
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+hold_hours*3600,'left'))
        xp=C[xe];xi=xe;reason=-4;peak=entry

        for q in range(ei+1,xe+1):
            hit=(side>0 and L[q]<=stop) or (side<0 and H[q]>=stop)
            if hit:
                xp=stop;xi=q
                improved=(side>0 and stop>initial_stop+1e-12) or (side<0 and stop<initial_stop-1e-12)
                reason=-2 if improved else -1;break

            cand=H[q] if side>0 else L[q]
            if (side>0 and cand>peak) or (side<0 and cand<peak):peak=cand

            prof=side*(C[q]-entry)
            if prof>=.50*a:
                be=entry+side*.15*a
                if (side>0 and be>stop) or (side<0 and be<stop):stop=be

            mfe=side*(peak-entry)/a
            if mfe>=2.50:
                tr=peak-side*.50*a
                if (side>0 and tr>stop) or (side<0 and tr<stop):stop=tr

            if signal_exit_on:
                znow=z_at(ft,fz,int(ts[q]))
                if np.isfinite(znow) and side*znow>=1.0:
                    xp=C[q];xi=q;reason=-3;break

            if ts[q]>=ts[ei]+hold_hours*3600:
                xp=C[q];xi=q;reason=-4;break

        R=side*(xp-entry)/(4.5*a)-(.50/10000.)*entry/(4.5*a)
        rs[n]=R;ets[n]=ts[ei];qual[n]=qstate;reasons[n]=reason;n+=1
        dc+=1;last=entry;la=a;has=True;k=np.searchsorted(dt,int(ts[xi])+1)
    return rs[:n],ets[:n],qual[:n],reasons[:n]

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
    m=load_base();arr=m.prep();ft,fz=load_flow_z()
    warm=tuple(x[:2000] for x in arr[:5])+(ft[:5000],fz[:5000])+tuple(x[:2000] for x in arr[5:])
    sim_v190(*warm,True,6)
    modes=[('V190_EXIT_EXACT_LAB026',True,6),('V190_EXIT_NO_SIGNAL_LAB026',False,6),
           ('V190_EXIT_24H_SIGNAL_LAB026',True,24)]
    rows=[];seqs=[]
    for name,sigexit,hold in modes:
        args=tuple(arr[:5])+(ft,fz)+tuple(arr[5:])
        raw,ets,qual,reason=sim_v190(*args,sigexit,hold)
        mult=weights(qual);wr=raw*mult
        months=pd.to_datetime(ets,unit='s',utc=True).to_period('M').astype(str)
        eq=np.cumsum(wr);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
        monthly={mo:metrics(wr[months==mo]) for mo in sorted(set(months))}
        rows.append({'name':name,'signal_exit':sigexit,'hold_hours':hold,'all':metrics(wr),
                     'positive_months':int(sum(v['SumR']>0 for v in monthly.values())),'monthly':monthly,
                     'exit_mix':{'SL':int((reason==-1).sum()),'BE_TRAIL_STOP':int((reason==-2).sum()),
                                 'SIGNAL':int((reason==-3).sum()),'TIME':int((reason==-4).sum())}})
        seqs.append(pd.DataFrame({'mode':name,'entry_time_utc':pd.to_datetime(ets,unit='s',utc=True).astype(str),
                                  'month':months,'quality':qual,'raw_R':raw,'risk_mult':mult,'weighted_R':wr,
                                  'equity_R':eq,'drawdown_R':dd,'exit_reason':reason}))
    pd.concat(seqs,ignore_index=True).to_csv(OUT/'equity_sequence_2026.csv',index=False)
    out={'lab':'CROWDFADE_V190_EXIT_ON_V200_ENTRY_LAB_028','period':'2026 seconds forward-shadow/stress',
         'warning':'Second OHLC approximates v190 1-second timer; protective stop changes effective next second.',
         'v190_exit_exact':{'BE_at_ATR':.50,'BE_lock_ATR':.15,'trail_arm_ATR':2.50,'trail_dist_ATR':.50,
                            'signal_exit_absZ_opposite':1.0,'hold_hours':6},
         'results':rows}
    (OUT/'stress_2026.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
