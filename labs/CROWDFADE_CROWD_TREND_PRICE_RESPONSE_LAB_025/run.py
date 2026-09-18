from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025')
DATA=ROOT/'data'; KDIR=DATA/'klines1m'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.5
CONF=.25; CONF_TTL_MIN=60; RETRACE=.60; PTTL_MIN=20; COST=.50; MAXDAY=3
SL=4.5; TP=10.; HOLD_H=24

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
    d=DATA/'flow';d.mkdir(exist_ok=True);zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    if not list(d.glob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(d)
    r=pd.read_csv(list(d.glob('*.csv'))[0],usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
    r['time']=pd.to_datetime(r.create_time,utc=True,errors='coerce').astype('datetime64[ns, UTC]')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time')
    mu=r.ratio.rolling(72,min_periods=72).mean();sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    return r[['time','z']].dropna()

def tf_state(p,rule):
    q=p.set_index('time').resample(rule,label='left',closed='left').agg(c=('c','last')).dropna()
    q['ema50']=q.c.ewm(span=50,adjust=False).mean();q['lag4']=q.ema50.shift(4)
    q['close_time']=q.index+pd.Timedelta(rule)
    q['state']=np.where((q.c>q.ema50)&(q.ema50>q.lag4),1,
                 np.where((q.c<q.ema50)&(q.ema50<q.lag4),-1,0))
    return q[['close_time','state']].reset_index(drop=True)

def prep():
    p=load_1m();f=load_flow()
    m=p.set_index('time').resample('15min',label='left',closed='left').agg(
        o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna()
    pc=m.c.shift();tr=np.maximum(m.h-m.l,np.maximum((m.h-pc).abs(),(m.l-pc).abs()))
    m['atr']=tr.rolling(14,min_periods=14).mean()
    m['av']=m.index+pd.Timedelta(minutes=15)
    a=m[['av','atr']].dropna().reset_index(drop=True)

    h1=tf_state(p,'1h');h4=tf_state(p,'4h')
    p=pd.merge_asof(p.sort_values('time'),a,left_on='time',right_on='av',direction='backward')
    p=pd.merge_asof(p.sort_values('time'),f,on='time',direction='backward',
                    tolerance=pd.Timedelta(minutes=10)).dropna(subset=['atr','z'])
    p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy().reset_index(drop=True)
    p['ts']=(p.time.astype('int64')//10**9).astype('int64')

    q=p.set_index('time').resample('15min',label='left',closed='left').agg(
        h=('h','max'),l=('l','min'),c=('c','last'),z=('z','last'),atr=('atr','last')).dropna().reset_index()
    q['close_time']=q.time+pd.Timedelta(minutes=15)
    q=pd.merge_asof(q.sort_values('close_time'),h1.sort_values('close_time'),
                    on='close_time',direction='backward').rename(columns={'state':'h1'})
    q=pd.merge_asof(q.sort_values('close_time'),h4.sort_values('close_time'),
                    on='close_time',direction='backward').rename(columns={'state':'h4'})
    q['h1']=q.h1.fillna(0).astype('int64');q['h4']=q.h4.fillna(0).astype('int64')
    q['close_ts']=(q.close_time.astype('int64')//10**9).astype('int64')
    q['yr']=q.time.dt.year.astype('int64');q['daykey']=(q.time.dt.year*10000+q.time.dt.month*100+q.time.dt.day).astype('int64')
    return p,q

@njit(cache=True)
def sim(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,Y,DAY):
    cap=len(dt)
    rs=np.zeros(cap);sidea=np.zeros(cap,np.int8);crowda=np.zeros(cap,np.int8)
    h1a=np.zeros(cap,np.int8);h4a=np.zeros(cap,np.int8);yra=np.zeros(cap,np.int16)
    cexc=np.zeros(cap); cbars=np.zeros(cap,np.int8); zabs=np.zeros(cap)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        if DAY[k]!=day:day=DAY[k];dc=0
        if dc>=MAXDAY:k+=1;continue
        z=Z[k];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        crowd=-side;sig=QC[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a;ci=-1
        max_crowd_exc=0.
        for j in range(k+1,min(len(dt)-2,k+CONF_TTL_MIN//15)+1):
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/a
            if exc>max_crowd_exc:max_crowd_exc=exc
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j;break
        if ci<0:k+=1;continue

        entry=QC[ci]-side*RETRACE*a
        ps=np.searchsorted(ts,dt[ci])+1;pe=np.searchsorted(ts,dt[ci]+PTTL_MIN*60,'right');ei=-1
        for j in range(ps,min(len(ts),pe)):
            if (side>0 and L[j]<=entry) or (side<0 and H[j]>=entry):ei=j;break
        if ei<0:k=ci+1;continue

        risk=SL*a;sl=entry-side*risk;tp=entry+side*TP*a
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD_H*3600,'left'))
        xp=C[xe];ex=xe
        for j in range(ei+1,xe+1):
            sh=(side>0 and L[j]<=sl) or (side<0 and H[j]>=sl)
            th=(side>0 and H[j]>=tp) or (side<0 and L[j]<=tp)
            if sh:xp=sl;ex=j;break
            if th:xp=tp;ex=j;break

        R=side*(xp-entry)/risk-(COST/10000.)*entry/risk
        rs[n]=R;sidea[n]=side;crowda[n]=crowd;h1a[n]=H1[k];h4a[n]=H4[k];yra[n]=Y[k]
        cexc[n]=max_crowd_exc;cbars[n]=ci-k;zabs[n]=abs(z);n+=1
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
    return rs[:n],sidea[:n],crowda[:n],h1a[:n],h4a[:n],yra[:n],cexc[:n],cbars[:n],zabs[:n]

def stats(a):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    p=a[a>0].sum();n=abs(a[a<0].sum())
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),
            'PF':float(p/n) if n else 99.,'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

def main():
    p,q=prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
         q.close_ts.to_numpy(np.int64),q.h.to_numpy(float),q.l.to_numpy(float),q.c.to_numpy(float),
         q.z.to_numpy(float),q.atr.to_numpy(float),q.h1.to_numpy(np.int64),q.h4.to_numpy(np.int64),
         q.yr.to_numpy(np.int64),q.daykey.to_numpy(np.int64)]
    sim(*[x[:1000] for x in arr])
    r,side,crowd,h1,h4,yr,cexc,cbars,zabs=sim(*arr)

    aligned=(h1!=0)&(h4!=0)&(h1==h4)
    strong=h1
    relation=np.where(~aligned,0,np.where(side==strong,1,-1)) # +1 we with trend / crowd against
    response=np.where(cexc<=.25,0,np.where(cexc<=.75,1,2)) # 0 failed,1 contested,2 strong crowd continuation
    speed=np.where(cbars==1,0,np.where(cbars==2,1,2))

    def B(mask):return stats(r[mask])
    buckets={}
    for rel_name,relv in [('WITH_TREND',1),('COUNTERTREND',-1),('MIXED',0)]:
        base=relation==relv
        buckets[rel_name]={
          'ALL':B(base),
          'PRICE_FAIL_LE_0P25_ATR':B(base&(response==0)),
          'PRICE_CONTESTED_0P25_TO_0P75':B(base&(response==1)),
          'PRICE_CROWD_CONT_GT_0P75':B(base&(response==2)),
          'CONFIRM_1_BAR':B(base&(speed==0)),
          'CONFIRM_2_BARS':B(base&(speed==1)),
          'CONFIRM_3_4_BARS':B(base&(speed==2))
        }

    directional={
      'UP_WITH_TREND_CROWD_SHORT_WE_LONG':B(aligned&(strong==1)&(side==1)),
      'UP_COUNTERTREND_CROWD_LONG_WE_SHORT':B(aligned&(strong==1)&(side==-1)),
      'DOWN_WITH_TREND_CROWD_LONG_WE_SHORT':B(aligned&(strong==-1)&(side==-1)),
      'DOWN_COUNTERTREND_CROWD_SHORT_WE_LONG':B(aligned&(strong==-1)&(side==1))
    }

    # 3x3 interaction matrix: trend relation x price-response
    matrix={}
    for rel_name,relv in [('WITH_TREND',1),('COUNTERTREND',-1),('MIXED',0)]:
        for resp_name,respv in [('FAIL',0),('CONTESTED',1),('CONTINUATION',2)]:
            matrix[rel_name+'__'+resp_name]=B((relation==relv)&(response==respv))

    annual={}
    for y in range(2021,2026):
        annual[str(y)]={}
        ym=yr==y
        for key in matrix:
            rel_name,resp_name=key.split('__')
            relv={'WITH_TREND':1,'COUNTERTREND':-1,'MIXED':0}[rel_name]
            respv={'FAIL':0,'CONTESTED':1,'CONTINUATION':2}[resp_name]
            annual[str(y)][key]=B(ym&(relation==relv)&(response==respv))

    out={
      'lab':'CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025',
      'period':'2021-2025 historical',
      'baseline':stats(r),
      'definitions':{
        'trend':'H1/H4 completed-bar EMA50 + 4-bar EMA slope, aligned only when both non-neutral and same direction',
        'price_response':'maximum M15 excursion in CROWD direction from signal until causal CrowdFade confirmation',
        'FAIL':'crowd-direction excursion <=0.25 ATR before contrarian confirmation',
        'CONTESTED':'crowd-direction excursion >0.25 and <=0.75 ATR',
        'CONTINUATION':'crowd-direction excursion >0.75 ATR',
        'confirmation_speed':'1, 2, or 3-4 M15 bars from signal to frozen 0.25 ATR confirmation'
      },
      'trend_price_buckets':buckets,
      'interaction_matrix':matrix,
      'directional':directional,
      'annual_interaction':annual,
      'diagnostic_only':True
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    pd.DataFrame({'R':r,'side':side,'crowd':crowd,'h1':h1,'h4':h4,'year':yr,
                  'crowd_excursion_atr':cexc,'confirm_bars':cbars,'abs_z':zabs,
                  'trend_relation':relation,'response_bucket':response}).to_csv(OUT/'trades_diagnostic.csv',index=False)
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
