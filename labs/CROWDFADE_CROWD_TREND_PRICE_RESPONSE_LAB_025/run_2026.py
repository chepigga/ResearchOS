from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025')
DATA=ROOT/'stress_data';OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.5;CONF=.25;CONF_TTL=3600;RETRACE=.60;PTTL=1200;COST=.5
SL=4.5;TP=10.;HOLD=86400;MAXDAY=3

def ex(z,o):
    d=DATA/o;d.mkdir(parents=True,exist_ok=True)
    if not list(d.rglob('*.csv')):
        with zipfile.ZipFile(DATA/z) as q:q.extractall(d)
    return list(d.rglob('*.csv'))[0]

def tf_states(ts,C,sec):
    b=(ts//sec)*sec
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1];en=np.r_[st[1:],len(ts)]
    close=C[en-1];bt=b[st]
    ema=pd.Series(close).ewm(span=50,adjust=False).mean().to_numpy()
    lag=pd.Series(ema).shift(4).to_numpy()
    state=np.where((close>ema)&(ema>lag),1,np.where((close<ema)&(ema<lag),-1,0))
    return (bt+sec).astype(np.int64),state.astype(np.int64)

def prep():
    sf=ex('BTCUSDT_sec.csv.zip','sec');ff=ex('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
    s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts')
    ts=s.ts.to_numpy(np.int64);O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)

    b=(ts//900)*900
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1];en=np.r_[st[1:],len(ts)]
    bt=b[st];bh=np.maximum.reduceat(H,st);bl=np.minimum.reduceat(L,st);bc=C[en-1]
    pc=np.r_[bc[0],bc[:-1]]
    tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy();av=bt+900
    h1t,h1s=tf_states(ts,C,3600);h4t,h4s=tf_states(ts,C,14400)

    f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy()
    f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce')
    f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t')
    ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    rr=pd.to_numeric(f.count_long_short_ratio,errors='coerce')
    mu=rr.rolling(72,min_periods=72).mean();sd=rr.rolling(72,min_periods=72).std(ddof=0)
    z=((rr-mu)/sd.replace(0,np.nan)).to_numpy()

    starts=np.arange(((ts[0]+899)//900)*900,ts[-1]-900+1,900,dtype=np.int64)
    i=np.searchsorted(ts,starts+900)-1
    ok=(i>=0)&(i<len(ts));starts=starts[ok];i=i[ok]
    dt=starts+900;qc=C[i]
    fi=np.searchsorted(ft,dt,'left')-1;ai=np.searchsorted(av,dt,'right')-1
    h1i=np.searchsorted(h1t,dt,'right')-1;h4i=np.searchsorted(h4t,dt,'right')-1
    g=(fi>=0)&(ai>=0)&(h1i>=0)&(h4i>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    # completed M15 H/L corresponding to signal intervals
    mi=np.searchsorted(av,dt,'right')-1
    return ts,O,H,L,C,dt[g],bh[mi[g]],bl[mi[g]],qc[g],z[fi[g]],atr[ai[g]],h1s[h1i[g]],h4s[h4i[g]]

@njit(cache=True)
def sim(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4):
    cap=len(dt)
    rs=np.zeros(cap);sidea=np.zeros(cap,np.int8);crowda=np.zeros(cap,np.int8)
    h1a=np.zeros(cap,np.int8);h4a=np.zeros(cap,np.int8);etsa=np.zeros(cap,np.int64)
    cexc=np.zeros(cap);cbars=np.zeros(cap,np.int8);zabs=np.zeros(cap)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0
    while k<len(dt)-2:
        t=int(dt[k]);d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=Z[k];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        crowd=-side;sig=QC[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a;ci=-1;max_crowd_exc=0.;j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/a
            if exc>max_crowd_exc:max_crowd_exc=exc
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):ci=j;break
            j+=1
        if ci<0:k+=1;continue

        entry=QC[ci]-side*RETRACE*a
        ps=np.searchsorted(ts,int(dt[ci])+1);pe=np.searchsorted(ts,int(dt[ci])+PTTL,'right');ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):ei=q;break
        if ei<0:k=ci+1;continue

        risk=SL*a;sl=entry-side*risk;tp=entry+side*TP*a
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+HOLD,'left'))
        xp=C[xe];xi=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;xi=q;break
            if th:xp=tp;xi=q;break

        R=side*(xp-entry)/risk-(COST/10000.)*entry/risk
        rs[n]=R;sidea[n]=side;crowda[n]=crowd;h1a[n]=H1[k];h4a[n]=H4[k];etsa[n]=ts[ei]
        cexc[n]=max_crowd_exc;cbars[n]=ci-k;zabs[n]=abs(z);n+=1
        dc+=1;last=entry;la=a;has=True;k=np.searchsorted(dt,int(ts[xi])+1)
    return rs[:n],sidea[:n],crowda[:n],h1a[:n],h4a[:n],etsa[:n],cexc[:n],cbars[:n],zabs[:n]

def stats(a):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    p=a[a>0].sum();n=abs(a[a<0].sum())
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),
            'PF':float(p/n) if n else 99.,'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

def main():
    arr=prep();sim(*[x[:2000] for x in arr])
    r,side,crowd,h1,h4,ets,cexc,cbars,zabs=sim(*arr)
    aligned=(h1!=0)&(h4!=0)&(h1==h4);strong=h1
    relation=np.where(~aligned,0,np.where(side==strong,1,-1))
    response=np.where(cexc<=.25,0,np.where(cexc<=.75,1,2))
    speed=np.where(cbars==1,0,np.where(cbars==2,1,2))
    months=pd.to_datetime(ets,unit='s',utc=True).to_period('M').astype(str)

    def B(mask):return stats(r[mask])
    buckets={}
    for rn,rv in [('WITH_TREND',1),('COUNTERTREND',-1),('MIXED',0)]:
        base=relation==rv
        buckets[rn]={
          'ALL':B(base),
          'PRICE_FAIL_LE_0P25_ATR':B(base&(response==0)),
          'PRICE_CONTESTED_0P25_TO_0P75':B(base&(response==1)),
          'PRICE_CROWD_CONT_GT_0P75':B(base&(response==2)),
          'CONFIRM_1_BAR':B(base&(speed==0)),
          'CONFIRM_2_BARS':B(base&(speed==1)),
          'CONFIRM_3_4_BARS':B(base&(speed==2))
        }

    matrix={}
    for rn,rv in [('WITH_TREND',1),('COUNTERTREND',-1),('MIXED',0)]:
        for pn,pv in [('FAIL',0),('CONTESTED',1),('CONTINUATION',2)]:
            matrix[rn+'__'+pn]=B((relation==rv)&(response==pv))

    monthly={}
    for mo in sorted(set(months)):
        monthly[mo]={}
        mm=months==mo
        for key in matrix:
            rn,pn=key.split('__')
            rv={'WITH_TREND':1,'COUNTERTREND':-1,'MIXED':0}[rn]
            pv={'FAIL':0,'CONTESTED':1,'CONTINUATION':2}[pn]
            monthly[mo][key]=B(mm&(relation==rv)&(response==pv))

    out={
      'lab':'CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025',
      'period':'2026 seconds forward-shadow/stress',
      'baseline':stats(r),
      'definitions':{
        'trend':'H1/H4 completed-bar EMA50 + 4-bar EMA slope; aligned only if same non-neutral direction',
        'price_response':'maximum M15 excursion in crowd direction from signal until frozen contrarian confirmation',
        'FAIL':'<=0.25 ATR','CONTESTED':'>0.25 to <=0.75 ATR','CONTINUATION':'>0.75 ATR',
        'confirmation_speed':'1, 2, or 3-4 M15 bars'
      },
      'trend_price_buckets':buckets,
      'interaction_matrix':matrix,
      'monthly_interaction':monthly,
      'diagnostic_only':True,
      'warning':'2026 uses 1-second OHLC for execution but price-response state is defined on completed M15 bars.'
    }
    (OUT/'stress_2026.json').write_text(json.dumps(out,indent=2))
    pd.DataFrame({'entry_ts':ets,'R':r,'side':side,'crowd':crowd,'h1':h1,'h4':h4,
                  'crowd_excursion_atr':cexc,'confirm_bars':cbars,'abs_z':zabs,
                  'trend_relation':relation,'response_bucket':response}).to_csv(OUT/'trades_2026_diagnostic.csv',index=False)
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
