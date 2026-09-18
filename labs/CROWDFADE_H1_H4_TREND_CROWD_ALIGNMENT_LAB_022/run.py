from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_H1_H4_TREND_CROWD_ALIGNMENT_LAB_022')
DATA=ROOT/'data'; KDIR=DATA/'klines1m'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.5
CONF=.25; CONF_TTL_MIN=60; RETRACE=.60; PASSIVE_TTL_MIN=20; COST=.50; MAXDAY=3
SL=4.5; TP=10.0; HOLD_H=24

def load_1m():
    ps=[]
    for zp in sorted(KDIR.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
        ps.append(pd.DataFrame({
            'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),
            'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),
            'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),
            'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),
            'c':pd.to_numeric(r.iloc[:,4],errors='coerce')
        }).dropna())
    p=pd.concat(ps,ignore_index=True).drop_duplicates('ms').sort_values('ms')
    p['time']=pd.to_datetime(p.ms.astype('int64'),unit='ms',utc=True).astype('datetime64[ns, UTC]')
    return p[['time','o','h','l','c']].reset_index(drop=True)

def load_flow():
    d=DATA/'flow'; d.mkdir(exist_ok=True); zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    if not list(d.glob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(d)
    r=pd.read_csv(list(d.glob('*.csv'))[0],usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
    r['time']=pd.to_datetime(r.create_time,utc=True,errors='coerce').astype('datetime64[ns, UTC]')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time')
    mu=r.ratio.rolling(72,min_periods=72).mean(); sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    return r[['time','z']].dropna()

def tf_state(p,rule):
    q=p.set_index('time').resample(rule,label='left',closed='left').agg(c=('c','last')).dropna()
    q['ema50']=q.c.ewm(span=50,adjust=False).mean()
    q['ema_lag4']=q.ema50.shift(4)
    q['close_ts']=(q.index+pd.Timedelta(rule)).astype('datetime64[ns, UTC]')
    q['state']=np.where((q.c>q.ema50)&(q.ema50>q.ema_lag4),1,
                 np.where((q.c<q.ema50)&(q.ema50<q.ema_lag4),-1,0))
    return q[['close_ts','state']].reset_index(drop=True)

def prep():
    p=load_1m(); f=load_flow()
    m15=p.set_index('time').resample('15min',label='left',closed='left').agg(
        o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna()
    pc=m15.c.shift(); tr=np.maximum(m15.h-m15.l,np.maximum((m15.h-pc).abs(),(m15.l-pc).abs()))
    m15['atr']=tr.rolling(14,min_periods=14).mean()
    m15['av']=(m15.index+pd.Timedelta(minutes=15)).astype('datetime64[ns, UTC]')
    a=m15[['av','atr']].dropna().reset_index(drop=True)

    h1=tf_state(p,'1h'); h4=tf_state(p,'4h')

    p=pd.merge_asof(p.sort_values('time'),a,left_on='time',right_on='av',direction='backward')
    p=pd.merge_asof(p.sort_values('time'),f,on='time',direction='backward',
                    tolerance=pd.Timedelta(minutes=10)).dropna(subset=['atr','z'])
    p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy().reset_index(drop=True)
    p['ts']=(p.time.astype('int64')//10**9).astype('int64')

    q=p.set_index('time').resample('15min',label='left',closed='left').agg(
        c=('c','last'),z=('z','last'),atr=('atr','last')).dropna().reset_index()
    q['close_time']=q.time+pd.Timedelta(minutes=15)
    q=pd.merge_asof(q.sort_values('close_time'),h1.sort_values('close_ts'),
                    left_on='close_time',right_on='close_ts',direction='backward').rename(columns={'state':'h1_state'})
    q=pd.merge_asof(q.sort_values('close_time'),h4.sort_values('close_ts'),
                    left_on='close_time',right_on='close_ts',direction='backward').rename(columns={'state':'h4_state'})
    q['h1_state']=q.h1_state.fillna(0).astype('int64')
    q['h4_state']=q.h4_state.fillna(0).astype('int64')
    q['close_ts']=(q.close_time.astype('int64')//10**9).astype('int64')
    q['yr']=q.time.dt.year.astype('int64')
    q['daykey']=(q.time.dt.year*10000+q.time.dt.month*100+q.time.dt.day).astype('int64')
    return p,q

@njit(cache=True)
def sim(ts,O,H,L,C,dt,CL,Z,A,H1,H4,Y,DAY):
    cap=len(dt)
    rs=np.zeros(cap); sidea=np.zeros(cap,np.int8); crowda=np.zeros(cap,np.int8)
    h1a=np.zeros(cap,np.int8); h4a=np.zeros(cap,np.int8); yra=np.zeros(cap,np.int16)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        if DAY[k]!=day:day=DAY[k];dc=0
        if dc>=MAXDAY:k+=1;continue

        z=Z[k];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        crowd=-side
        sig=CL[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a;ci=-1
        for j in range(k+1,min(len(dt)-2,k+CONF_TTL_MIN//15)+1):
            if (side>0 and CL[j]>=lev) or (side<0 and CL[j]<=lev):ci=j;break
        if ci<0:k+=1;continue

        entry=CL[ci]-side*RETRACE*a
        ps=np.searchsorted(ts,dt[ci])+1; pe=np.searchsorted(ts,dt[ci]+PASSIVE_TTL_MIN*60,'right'); ei=-1
        for j in range(ps,min(len(ts),pe)):
            if (side>0 and L[j]<=entry) or (side<0 and H[j]>=entry):ei=j;break
        if ei<0:k=ci+1;continue

        sl=entry-side*SL*a; tp=entry+side*TP*a
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD_H*3600,'left'))
        xp=C[xe];ex=xe
        for j in range(ei+1,xe+1):
            sh=(side>0 and L[j]<=sl) or (side<0 and H[j]>=sl)
            th=(side>0 and H[j]>=tp) or (side<0 and L[j]<=tp)
            if sh:xp=sl;ex=j;break
            if th:xp=tp;ex=j;break

        R=side*(xp-entry)/(SL*a)-(COST/10000.)*entry/(SL*a)
        rs[n]=R; sidea[n]=side; crowda[n]=crowd; h1a[n]=H1[k]; h4a[n]=H4[k]; yra[n]=Y[k]; n+=1
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
    return rs[:n],sidea[:n],crowda[:n],h1a[:n],h4a[:n],yra[:n]

def stats(a):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max())
    p=a[a>0].sum(); n=abs(a[a<0].sum())
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),
            'PF':float(p/n) if n else 99.,'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

def relation(side,trend):
    # +1 = side WITH trend, -1 = side AGAINST trend, 0 = neutral/no trend
    return np.where(trend==0,0,np.where(side==trend,1,-1))

def bucket(r,mask):
    return stats(r[mask])

def main():
    p,q=prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
         q.close_ts.to_numpy(np.int64),q.c.to_numpy(float),q.z.to_numpy(float),q.atr.to_numpy(float),
         q.h1_state.to_numpy(np.int64),q.h4_state.to_numpy(np.int64),
         q.yr.to_numpy(np.int64),q.daykey.to_numpy(np.int64)]
    sim(*[x[:1000] for x in arr])
    r,side,crowd,h1,h4,yr=sim(*arr)

    cr1=relation(crowd,h1); cr4=relation(crowd,h4)
    us1=relation(side,h1); us4=relation(side,h4)

    both_trend=(h1!=0)&(h4!=0)&(h1==h4)
    strong_dir=np.where(both_trend,h1,0)
    crowd_strong=relation(crowd,strong_dir)
    us_strong=relation(side,strong_dir)

    out={
      'lab':'CROWDFADE_H1_H4_TREND_CROWD_ALIGNMENT_LAB_022',
      'period':'2021-2025 baseline trades',
      'trend_definition':{
        'H1':'close>EMA50 and EMA50>EMA50[-4] => UP; mirror => DOWN; else NEUTRAL',
        'H4':'same rule on H4; only completed bars available at signal time',
        'strong':'H1 and H4 non-neutral and same direction'
      },
      'baseline':stats(r),
      'counts':{
        'H1_UP':int((h1==1).sum()),'H1_DOWN':int((h1==-1).sum()),'H1_NEUTRAL':int((h1==0).sum()),
        'H4_UP':int((h4==1).sum()),'H4_DOWN':int((h4==-1).sum()),'H4_NEUTRAL':int((h4==0).sum()),
        'STRONG_UP':int((strong_dir==1).sum()),'STRONG_DOWN':int((strong_dir==-1).sum()),'MIXED_OR_NEUTRAL':int((strong_dir==0).sum())
      },
      'crowd_vs_H1':{'WITH':bucket(r,cr1==1),'AGAINST':bucket(r,cr1==-1),'NEUTRAL':bucket(r,cr1==0)},
      'crowd_vs_H4':{'WITH':bucket(r,cr4==1),'AGAINST':bucket(r,cr4==-1),'NEUTRAL':bucket(r,cr4==0)},
      'our_trade_vs_H1':{'WITH':bucket(r,us1==1),'AGAINST':bucket(r,us1==-1),'NEUTRAL':bucket(r,us1==0)},
      'our_trade_vs_H4':{'WITH':bucket(r,us4==1),'AGAINST':bucket(r,us4==-1),'NEUTRAL':bucket(r,us4==0)},
      'strong_H1_H4':{
        'CROWD_WITH_TREND__WE_COUNTERTREND':bucket(r,(strong_dir!=0)&(crowd_strong==1)),
        'CROWD_AGAINST_TREND__WE_WITH_TREND':bucket(r,(strong_dir!=0)&(crowd_strong==-1)),
        'MIXED_OR_NEUTRAL':bucket(r,strong_dir==0)
      },
      'directional_matrix':{
        'STRONG_UP_CROWD_LONG_WE_SHORT':bucket(r,(strong_dir==1)&(crowd==1)),
        'STRONG_UP_CROWD_SHORT_WE_LONG':bucket(r,(strong_dir==1)&(crowd==-1)),
        'STRONG_DOWN_CROWD_SHORT_WE_LONG':bucket(r,(strong_dir==-1)&(crowd==-1)),
        'STRONG_DOWN_CROWD_LONG_WE_SHORT':bucket(r,(strong_dir==-1)&(crowd==1))
      },
      'annual':{str(y):stats(r[yr==y]) for y in range(2021,2026)}
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
