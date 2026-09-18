from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_SIDE_TIME_DECAY_LAB_015')
DATA=ROOT/'data'; KDIR=DATA/'klines1m'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Frozen production candidate from LAB014
ZTH=2.5; CONF=.25; CONF_TTL_MIN=60; RETRACE=.60; PASSIVE_TTL_MIN=20; COST=.50; MAXDAY=3
SL=4.5; TP=10.0; HOLD_H=24

def load_1m():
    ps=[]
    for zp in sorted(KDIR.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
        ps.append(pd.DataFrame({'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')}).dropna())
    p=pd.concat(ps,ignore_index=True).drop_duplicates('ms').sort_values('ms')
    p['time']=pd.to_datetime(p.ms.astype('int64'),unit='ms',utc=True).astype('datetime64[ns, UTC]')
    return p[['time','o','h','l','c']].reset_index(drop=True)

def load_flow():
    d=DATA/'flow';d.mkdir(exist_ok=True);zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    if not list(d.glob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(d)
    r=pd.read_csv(list(d.glob('*.csv'))[0],usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
    r['time']=pd.to_datetime(r.create_time,utc=True,errors='coerce').astype('datetime64[ns, UTC]')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time')
    mu=r.ratio.rolling(72,min_periods=72).mean();sd=r.ratio.rolling(72,min_periods=72).std(ddof=0);r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    return r[['time','z']].dropna()

def prep():
    p=load_1m();f=load_flow()
    q=p.set_index('time').resample('15min',label='left',closed='left').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna()
    pc=q.c.shift();tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs()))
    q['atr']=tr.rolling(14,min_periods=14).mean();q['av']=(q.index+pd.Timedelta(minutes=15)).astype('datetime64[ns, UTC]')
    a=q[['av','atr']].dropna().reset_index(drop=True)
    p=pd.merge_asof(p.sort_values('time'),a,left_on='time',right_on='av',direction='backward')
    p=pd.merge_asof(p.sort_values('time'),f,on='time',direction='backward',tolerance=pd.Timedelta(minutes=10)).dropna(subset=['atr','z'])
    p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy().reset_index(drop=True)
    p['ts']=(p.time.astype('int64')//10**9).astype('int64')
    q=p.set_index('time').resample('15min',label='left',closed='left').agg(c=('c','last'),z=('z','last'),atr=('atr','last')).dropna().reset_index()
    q['close_ts']=(q.time.astype('int64')//10**9).astype('int64')+900
    q['yr']=q.time.dt.year.astype('int64');q['day']=q.time.dt.dayofweek.astype('int64');q['hour']=q.time.dt.hour.astype('int64')
    return p,q

@njit(cache=True)
def sim(ts,O,H,L,C,dt,CL,Z,A,Y,DOW,HOUR):
    maxn=len(dt); side_arr=np.zeros(maxn,np.int8); sigts=np.zeros(maxn,np.int64); ents=np.zeros(maxn,np.int64); age=np.zeros(maxn,np.float64); rr=np.zeros(maxn,np.float64)
    dow=np.zeros(maxn,np.int8);hour=np.zeros(maxn,np.int8);yr=np.zeros(maxn,np.int16)
    n=0;k=0;last=0.;la=0.;has=False;daykey=-1;dc=0;nextts=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        dk=t//86400
        if dk!=daykey:daykey=dk;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=Z[k];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=CL[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue
        lev=sig+side*CONF*a;ci=-1
        for j in range(k+1,min(len(dt)-2,k+CONF_TTL_MIN//15)+1):
            if (side>0 and CL[j]>=lev) or (side<0 and CL[j]<=lev):ci=j;break
        if ci<0:k+=1;continue
        entry=CL[ci]-side*RETRACE*a
        ps=np.searchsorted(ts,dt[ci])+1;pe=np.searchsorted(ts,dt[ci]+PASSIVE_TTL_MIN*60,'right');ei=-1
        for j in range(ps,min(len(ts),pe)):
            if (side>0 and L[j]<=entry) or (side<0 and H[j]>=entry):ei=j;break
        if ei<0:k=ci+1;continue
        sl=entry-side*SL*a;tp=entry+side*TP*a;xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD_H*3600,'left'));xp=C[xe];ex=xe
        for j in range(ei+1,xe+1):
            sh=(side>0 and L[j]<=sl) or (side<0 and H[j]>=sl)
            th=(side>0 and H[j]>=tp) or (side<0 and L[j]<=tp)
            if sh:xp=sl;ex=j;break
            if th:xp=tp;ex=j;break
        R=side*(xp-entry)/(SL*a)-(COST/10000.)*entry/(SL*a)
        side_arr[n]=side;sigts[n]=dt[k];ents[n]=ts[ei];age[n]=(ts[ei]-dt[k])/60.0;rr[n]=R;dow[n]=DOW[k];hour[n]=HOUR[k];yr[n]=Y[k];n+=1
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
    return side_arr[:n],sigts[:n],ents[:n],age[:n],rr[:n],dow[:n],hour[:n],yr[:n]

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:return {'N':0}
    p=x[x>0].sum();n=abs(x[x<0].sum());eq=np.cumsum(x);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    return {'N':int(len(x)),'EV':float(x.mean()),'SumR':float(x.sum()),'PF':float(p/n) if n else 99.,'WR':float((x>0).mean()),'MaxDD_R':dd}

def main():
    p,q=prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),q.close_ts.to_numpy(np.int64),q.c.to_numpy(float),q.z.to_numpy(float),q.atr.to_numpy(float),q.yr.to_numpy(np.int64),q.day.to_numpy(np.int64),q.hour.to_numpy(np.int64)]
    side,sigts,ents,age,R,dow,hour,yr=sim(*arr)
    d=pd.DataFrame({'side':side,'signal_ts':sigts,'entry_ts':ents,'age_min':age,'R':R,'dow':dow,'hour':hour,'year':yr})
    d.to_csv(OUT/'events.csv',index=False)
    out={'frozen':{'Z':ZTH,'TF':'M15','retrace':RETRACE,'SL':SL,'TP':TP,'hold_h':HOLD_H},'overall':metrics(d.R)}
    out['by_side']={k:metrics(d.loc[d.side==v,'R']) for k,v in [('LONG',1),('SHORT',-1)]}
    out['by_hour_utc']={str(h):metrics(d.loc[d.hour==h,'R']) for h in range(24)}
    names=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    out['by_dow']={names[i]:metrics(d.loc[d.dow==i,'R']) for i in range(7)}
    bins=[0,15,30,45,60,90,120,180,1e9];labels=['0-15','15-30','30-45','45-60','60-90','90-120','120-180','180+']
    d['age_bucket']=pd.cut(d.age_min,bins=bins,labels=labels,right=False)
    out['by_signal_age_min']={lab:metrics(d.loc[d.age_bucket==lab,'R']) for lab in labels}
    out['side_x_hour']={}
    for name,v in [('LONG',1),('SHORT',-1)]:
        out['side_x_hour'][name]={str(h):metrics(d.loc[(d.side==v)&(d.hour==h),'R']) for h in range(24)}
    out['side_x_dow']={}
    for name,v in [('LONG',1),('SHORT',-1)]:
        out['side_x_dow'][name]={names[i]:metrics(d.loc[(d.side==v)&(d.dow==i),'R']) for i in range(7)}
    # annual stability for each bucket
    out['annual_side']={}
    for name,v in [('LONG',1),('SHORT',-1)]:
        out['annual_side'][name]={str(y):metrics(d.loc[(d.side==v)&(d.year==y),'R']) for y in range(2021,2026)}
    (OUT/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
