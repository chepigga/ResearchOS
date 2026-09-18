from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd

ROOT=Path('labs/CROWDFADE_COARSE_TIME_WINDOW_VETO_LAB_018')
DATA=ROOT/'stress_data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.5
CONF=.25; CONF_TTL=3600; RETRACE=.60; PTTL=1200; COST=.5
SL=4.5; TP=10.; HOLD=86400; MAXDAY=3

MODES=[
    ('BASELINE',0),
    ('VETO_04_07',1),
    ('VETO_18_20',2),
    ('VETO_BOTH',3),
]

def ex(z,o):
    d=DATA/o; d.mkdir(parents=True,exist_ok=True)
    if not list(d.rglob('*.csv')):
        with zipfile.ZipFile(DATA/z) as q:q.extractall(d)
    return list(d.rglob('*.csv'))[0]

def prep():
    sf=ex('BTCUSDT_sec.csv.zip','sec')
    ff=ex('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
    s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts')
    ts=s.ts.to_numpy(np.int64); O=s.o.to_numpy(float); H=s.h.to_numpy(float)
    L=s.l.to_numpy(float); C=s.c.to_numpy(float)

    b=(ts//900)*900
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]; en=np.r_[st[1:],len(ts)]
    bt=b[st]; bh=np.maximum.reduceat(H,st); bl=np.minimum.reduceat(L,st)
    bc=C[en-1]; pc=np.r_[bc[0],bc[:-1]]
    tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); av=bt+900

    f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy()
    f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce')
    f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t')
    ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    r=pd.to_numeric(f.count_long_short_ratio,errors='coerce')
    mu=r.rolling(72,min_periods=72).mean(); sd=r.rolling(72,min_periods=72).std(ddof=0)
    z=((r-mu)/sd.replace(0,np.nan)).to_numpy()

    starts=np.arange(((ts[0]+899)//900)*900,ts[-1]-900+1,900,dtype=np.int64)
    idx2=np.searchsorted(ts,starts+900)-1
    ok=(idx2>=0)&(idx2<len(ts)); starts=starts[ok]; idx2=idx2[ok]
    dt=starts+900; cl=C[idx2]
    fi=np.searchsorted(ft,dt,'left')-1; ai=np.searchsorted(av,dt,'right')-1
    g=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    dt=dt[g]
    # M15 signal bar start = close timestamp - 900 sec.
    hour=pd.to_datetime(dt-900,unit='s',utc=True).hour.to_numpy(np.int64)
    return ts,O,H,L,C,dt,cl[g],z[fi[g]],atr[ai[g]],hour

def stats(a,months_div=6.0):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max())
    p=a[a>0].sum(); n=abs(a[a<0].sum())
    return {'N':int(len(a)),'trades_per_month':float(len(a)/months_div),'WR':float((a>0).mean()),
            'EV':float(a.mean()),'SumR':float(a.sum()),'PF':float(p/n) if n else 99.,
            'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

def vetoed(hour,mode):
    a=4<=hour<=7; b=18<=hour<=20
    if mode==1:return a
    if mode==2:return b
    if mode==3:return a or b
    return False

def sim(arr,mode):
    ts,O,H,L,C,dt,cl,zd,ad,hour=arr
    rows=[]; k=0; last=None; la=None; day=-1; dc=0
    while k<len(dt)-2:
        t=int(dt[k]); d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        if vetoed(int(hour[k]),mode):k+=1;continue

        z=float(zd[k]); side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=float(cl[k]); a=float(ad[k])
        if last is not None and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a; ci=-1; j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            if (side>0 and cl[j]>=lev) or (side<0 and cl[j]<=lev):
                ci=j;break
            j+=1
        if ci<0:k+=1;continue

        entry=float(cl[ci])-side*RETRACE*a
        ps=np.searchsorted(ts,int(dt[ci])+1); pe=np.searchsorted(ts,int(dt[ci])+PTTL,'right')
        ff=np.flatnonzero((L[ps:pe]<=entry) if side>0 else (H[ps:pe]>=entry))
        if not len(ff):k=ci+1;continue
        ei=ps+int(ff[0]); sl=entry-side*SL*a; tp=entry+side*TP*a
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+HOLD,'left'))
        xp=float(C[xe]); xi=xe; reason='TIME'
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;xi=q;reason='SL';break
            if th:xp=tp;xi=q;reason='TP';break

        R=side*(xp-entry)/(SL*a)-(COST/10000.)*entry/(SL*a)
        rows.append({'signal_ts':int(dt[k]),'entry_ts':int(ts[ei]),'signal_hour':int(hour[k]),
                     'side':'LONG' if side>0 else 'SHORT','R':float(R),'reason':reason})
        dc+=1;last=entry;la=a;k=np.searchsorted(dt,int(ts[xi])+1)

    return pd.DataFrame(rows)

def summarize(d):
    if d.empty:return {'all':{'N':0},'positive_months':0,'monthly':{},'by_side':{}}
    m=pd.to_datetime(d.entry_ts,unit='s',utc=True).dt.to_period('M').astype(str)
    months=sorted(m.unique())
    return {'all':stats(d.R),'exit_mix':d.reason.value_counts().to_dict(),
            'positive_months':int(sum(stats(d.loc[m==x,'R'],1.0)['SumR']>0 for x in months)),
            'monthly':{x:stats(d.loc[m==x,'R'],1.0) for x in months},
            'by_side':{side:stats(d.loc[d.side==side,'R']) for side in ['LONG','SHORT']}}

def main():
    arr=prep(); rows=[]
    for name,mode in MODES:
        d=sim(arr,mode); rows.append({'mode':name,'mode_id':mode,**summarize(d)})
    b=rows[0]
    for x in rows:
        a=x['all']
        x['vs_baseline']={'dEV':float(a.get('EV',0)-b['all'].get('EV',0)),
                          'dPF':float(a.get('PF',0)-b['all'].get('PF',0)),
                          'dMaxDD_R':float(a.get('MaxDD_R',0)-b['all'].get('MaxDD_R',0)),
                          'dSumR':float(a.get('SumR',0)-b['all'].get('SumR',0)),
                          'dN':int(a.get('N',0)-b['all'].get('N',0))}
    out={'lab':'CROWDFADE_COARSE_TIME_WINDOW_VETO_LAB_018',
         'period':'2026 seconds forward-shadow/stress',
         'frozen_signal':{'ZLong':ZTH,'ZShort':ZTH},
         'frozen_execution':{'TF':'M15','ConfirmATR':CONF,'ConfirmTTL_sec':CONF_TTL,'RetraceATR':RETRACE,
                             'LimitOnly':True,'LimitTTL_sec':PTTL,'SL_ATR':SL,'TP_ATR':TP,'Hold_sec':HOLD,
                             'Cost_bps':COST,'MaxTradesDay':MAXDAY,'InheritedAntiRepeatATR':1.0},
         'time_semantics':'UTC hour of original M15 signal bar start, matching LAB015 hour buckets',
         'windows':{'A':'04:00-07:59 UTC','B':'18:00-20:59 UTC'},
         'results':rows,
         'rank_RDD':sorted(rows,key=lambda x:x['all'].get('R_DD',-999),reverse=True),
         'rank_EV':sorted(rows,key=lambda x:x['all'].get('EV',-999),reverse=True)}
    (OUT/'stress_2026.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':
    main()
