from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_H1_H4_TREND_CROWD_ALIGNMENT_LAB_022')
DATA=ROOT/'stress_data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.5
CONF=.25; CONF_TTL=3600; RETRACE=.60; PTTL=1200; COST=.5
SL=4.5; TP=10.; HOLD=86400; MAXDAY=3

def ex(z,o):
    d=DATA/o;d.mkdir(parents=True,exist_ok=True)
    if not list(d.rglob('*.csv')):
        with zipfile.ZipFile(DATA/z) as q:q.extractall(d)
    return list(d.rglob('*.csv'))[0]

def tf_states(ts,C,rule_sec):
    b=(ts//rule_sec)*rule_sec
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]; en=np.r_[st[1:],len(ts)]
    close=C[en-1]; bt=b[st]
    ema=pd.Series(close).ewm(span=50,adjust=False).mean().to_numpy()
    lag=pd.Series(ema).shift(4).to_numpy()
    state=np.where((close>ema)&(ema>lag),1,np.where((close<ema)&(ema<lag),-1,0))
    av=bt+rule_sec
    return av.astype(np.int64),state.astype(np.int64)

def prep():
    sf=ex('BTCUSDT_sec.csv.zip','sec'); ff=ex('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
    s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts')
    ts=s.ts.to_numpy(np.int64);O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)

    b=(ts//900)*900
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]; en=np.r_[st[1:],len(ts)]
    bt=b[st];bh=np.maximum.reduceat(H,st);bl=np.minimum.reduceat(L,st);bc=C[en-1];pc=np.r_[bc[0],bc[:-1]]
    tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); av=bt+900

    h1t,h1s=tf_states(ts,C,3600)
    h4t,h4s=tf_states(ts,C,14400)

    f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy()
    f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce')
    f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t')
    ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    r=pd.to_numeric(f.count_long_short_ratio,errors='coerce')
    mu=r.rolling(72,min_periods=72).mean();sd=r.rolling(72,min_periods=72).std(ddof=0)
    z=((r-mu)/sd.replace(0,np.nan)).to_numpy()

    starts=np.arange(((ts[0]+899)//900)*900,ts[-1]-900+1,900,dtype=np.int64)
    idx2=np.searchsorted(ts,starts+900)-1
    ok=(idx2>=0)&(idx2<len(ts));starts=starts[ok];idx2=idx2[ok]
    dt=starts+900;cl=C[idx2]
    fi=np.searchsorted(ft,dt,'left')-1; ai=np.searchsorted(av,dt,'right')-1
    h1i=np.searchsorted(h1t,dt,'right')-1; h4i=np.searchsorted(h4t,dt,'right')-1
    g=(fi>=0)&(ai>=0)&(h1i>=0)&(h4i>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    return ts,O,H,L,C,dt[g],cl[g],z[fi[g]],atr[ai[g]],h1s[h1i[g]],h4s[h4i[g]]

@njit(cache=True)
def sim(ts,O,H,L,C,dt,cl,zd,ad,h1,h4):
    cap=len(dt)
    rs=np.zeros(cap); sidea=np.zeros(cap,np.int8); crowda=np.zeros(cap,np.int8)
    h1a=np.zeros(cap,np.int8); h4a=np.zeros(cap,np.int8); etsa=np.zeros(cap,np.int64)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0
    while k<len(dt)-2:
        t=int(dt[k]);d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=zd[k];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        crowd=-side; sig=cl[k];a=ad[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a;ci=-1;j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            if (side>0 and cl[j]>=lev) or (side<0 and cl[j]<=lev):ci=j;break
            j+=1
        if ci<0:k+=1;continue

        entry=cl[ci]-side*RETRACE*a
        ps=np.searchsorted(ts,int(dt[ci])+1); pe=np.searchsorted(ts,int(dt[ci])+PTTL,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):ei=q;break
        if ei<0:k=ci+1;continue

        sl=entry-side*SL*a;tp=entry+side*TP*a
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+HOLD,'left'))
        xp=C[xe];xi=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;xi=q;break
            if th:xp=tp;xi=q;break

        R=side*(xp-entry)/(SL*a)-(COST/10000.)*entry/(SL*a
        )
        rs[n]=R;sidea[n]=side;crowda[n]=crowd;h1a[n]=h1[k];h4a[n]=h4[k];etsa[n]=ts[ei];n+=1
        dc+=1;last=entry;la=a;has=True;k=np.searchsorted(dt,int(ts[xi])+1)
    return rs[:n],sidea[:n],crowda[:n],h1a[:n],h4a[:n],etsa[:n]

def stats(a):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    p=a[a>0].sum();n=abs(a[a<0].sum())
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),
            'PF':float(p/n) if n else 99.,'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

def relation(side,trend):
    return np.where(trend==0,0,np.where(side==trend,1,-1))

def bucket(r,mask): return stats(r[mask])

def main():
    arr=prep(); sim(*[x[:2000] for x in arr])
    r,side,crowd,h1,h4,ets=sim(*arr)
    cr1=relation(crowd,h1);cr4=relation(crowd,h4)
    us1=relation(side,h1);us4=relation(side,h4)
    both=(h1!=0)&(h4!=0)&(h1==h4)
    strong=np.where(both,h1,0)
    crs=relation(crowd,strong)
    months=pd.to_datetime(ets,unit='s',utc=True).to_period('M').astype(str)
    out={
      'lab':'CROWDFADE_H1_H4_TREND_CROWD_ALIGNMENT_LAB_022',
      'period':'2026 seconds forward-shadow/stress',
      'trend_definition':{
        'H1':'close>EMA50 and EMA50>EMA50[-4] => UP; mirror => DOWN; else NEUTRAL',
        'H4':'same rule on H4; completed bars only',
        'strong':'H1 and H4 non-neutral and same direction'
      },
      'baseline':stats(r),
      'positive_months':int(sum(stats(r[months==m])['SumR']>0 for m in sorted(set(months)))),
      'counts':{
        'H1_UP':int((h1==1).sum()),'H1_DOWN':int((h1==-1).sum()),'H1_NEUTRAL':int((h1==0).sum()),
        'H4_UP':int((h4==1).sum()),'H4_DOWN':int((h4==-1).sum()),'H4_NEUTRAL':int((h4==0).sum()),
        'STRONG_UP':int((strong==1).sum()),'STRONG_DOWN':int((strong==-1).sum()),'MIXED_OR_NEUTRAL':int((strong==0).sum())
      },
      'crowd_vs_H1':{'WITH':bucket(r,cr1==1),'AGAINST':bucket(r,cr1==-1),'NEUTRAL':bucket(r,cr1==0)},
      'crowd_vs_H4':{'WITH':bucket(r,cr4==1),'AGAINST':bucket(r,cr4==-1),'NEUTRAL':bucket(r,cr4==0)},
      'our_trade_vs_H1':{'WITH':bucket(r,us1==1),'AGAINST':bucket(r,us1==-1),'NEUTRAL':bucket(r,us1==0)},
      'our_trade_vs_H4':{'WITH':bucket(r,us4==1),'AGAINST':bucket(r,us4==-1),'NEUTRAL':bucket(r,us4==0)},
      'strong_H1_H4':{
        'CROWD_WITH_TREND__WE_COUNTERTREND':bucket(r,(strong!=0)&(crs==1)),
        'CROWD_AGAINST_TREND__WE_WITH_TREND':bucket(r,(strong!=0)&(crs==-1)),
        'MIXED_OR_NEUTRAL':bucket(r,strong==0)
      },
      'directional_matrix':{
        'STRONG_UP_CROWD_LONG_WE_SHORT':bucket(r,(strong==1)&(crowd==1)),
        'STRONG_UP_CROWD_SHORT_WE_LONG':bucket(r,(strong==1)&(crowd==-1)),
        'STRONG_DOWN_CROWD_SHORT_WE_LONG':bucket(r,(strong==-1)&(crowd==-1)),
        'STRONG_DOWN_CROWD_LONG_WE_SHORT':bucket(r,(strong==-1)&(crowd==1))
      },
      'monthly':{m:stats(r[months==m]) for m in sorted(set(months))}
    }
    (OUT/'stress_2026.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
