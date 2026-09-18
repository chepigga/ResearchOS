from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd

ROOT=Path('labs/CROWDFADE_EXIT_RISK_DIAGNOSTICS_LAB_020')
DATA=ROOT/'stress_data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.5
CONF=.25; CONF_TTL=3600; RETRACE=.60; PTTL=1200; COST=.5
TP_ATR=10.; HOLD=86400; MAXDAY=3
STOP_MODES=[('WIDE_4P5',0),('NARROW_2P5',1),('ADAPTIVE_3_TO_4P5',2)]
BE_LEVELS=[0.5,1.0,1.5,2.0]
TRAIL_MODES=[('NO_TRAIL',0),('TRAIL_1R_AFTER_1R',1),('TRAIL_2R_AFTER_1R',2)]

def ex(z,o):
    d=DATA/o;d.mkdir(parents=True,exist_ok=True)
    if not list(d.rglob('*.csv')):
        with zipfile.ZipFile(DATA/z) as q:q.extractall(d)
    return list(d.rglob('*.csv'))[0]

def prep():
    sf=ex('BTCUSDT_sec.csv.zip','sec'); ff=ex('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
    s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts')
    ts=s.ts.to_numpy(np.int64);O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)

    b=(ts//900)*900;st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1];en=np.r_[st[1:],len(ts)]
    bt=b[st];bh=np.maximum.reduceat(H,st);bl=np.minimum.reduceat(L,st);bc=C[en-1];pc=np.r_[bc[0],bc[:-1]]
    tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); av=bt+900

    f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy()
    f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce')
    f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t')
    ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    r=pd.to_numeric(f.count_long_short_ratio,errors='coerce')
    mu=r.rolling(72,min_periods=72).mean();sd=r.rolling(72,min_periods=72).std(ddof=0)
    z=((r-mu)/sd.replace(0,np.nan)).to_numpy()

    starts=np.arange(((ts[0]+899)//900)*900,ts[-1]-900+1,900,dtype=np.int64)
    idx2=np.searchsorted(ts,starts+900)-1;ok=(idx2>=0)&(idx2<len(ts));starts=starts[ok];idx2=idx2[ok]
    dt=starts+900;cl=C[idx2];fi=np.searchsorted(ft,dt,'left')-1;ai=np.searchsorted(av,dt,'right')-1
    g=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    dt=dt[g]; cl=cl[g]; zd=z[fi[g]]; ad=atr[ai[g]]
    am=pd.Series(ad).rolling(96,min_periods=96).median().to_numpy()
    g2=np.isfinite(am)
    return ts,O,H,L,C,dt[g2],cl[g2],zd[g2],ad[g2],am[g2]

def stats(a):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    p=a[a>0].sum();n=abs(a[a<0].sum())
    return {'N':int(len(a)),'trades_per_month':float(len(a)/6.0),'WR':float((a>0).mean()),'EV':float(a.mean()),
            'SumR':float(a.sum()),'PF':float(p/n) if n else 99.,'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

def sl_mult(mode,a,amed):
    if mode==0:return 4.5
    if mode==1:return 2.5
    return 4.5 if a>amed else 3.0

def sim(arr,stop_mode=0,be_trigger=0.,trail_mode=0):
    ts,O,H,L,C,dt,cl,zd,ad,amed=arr
    rows=[];k=0;last=None;la=None;day=-1;dc=0
    while k<len(dt)-2:
        t=int(dt[k]);d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=float(zd[k]);side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=float(cl[k]);a=float(ad[k])
        if last is not None and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a;ci=-1;j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            if (side>0 and cl[j]>=lev) or (side<0 and cl[j]<=lev):ci=j;break
            j+=1
        if ci<0:k+=1;continue

        entry=float(cl[ci])-side*RETRACE*a
        ps=np.searchsorted(ts,int(dt[ci])+1);pe=np.searchsorted(ts,int(dt[ci])+PTTL,'right')
        ff=np.flatnonzero((L[ps:pe]<=entry) if side>0 else (H[ps:pe]>=entry))
        if not len(ff):k=ci+1;continue
        ei=ps+int(ff[0])

        sm=sl_mult(stop_mode,a,float(amed[k]));risk=sm*a
        stop=entry-side*risk;tp=entry+side*TP_ATR*a
        be_price=entry+side*(COST/10000.)*entry
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+HOLD,'left'))
        xp=float(C[xe]);xi=xe;reason='TIME';best=entry;activated_be=False;activated_tr=False
        maxfav=0.;maxadv=0.

        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=stop) or (side<0 and H[q]>=stop)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:
                xp=stop;xi=q;reason='TRAIL' if activated_tr else ('BE' if activated_be else 'SL');break
            if th:xp=tp;xi=q;reason='TP';break

            fav=((H[q]-entry) if side>0 else (entry-L[q]))/risk
            adv=((entry-L[q]) if side>0 else (H[q]-entry))/risk
            if fav>maxfav:maxfav=fav
            if adv>maxadv:maxadv=adv

            cand=H[q] if side>0 else L[q]
            if (side>0 and cand>best) or (side<0 and cand<best):best=cand
            mfe=side*(best-entry)/risk

            if be_trigger>0 and (not activated_be) and mfe>=be_trigger:
                activated_be=True
                stop=max(stop,be_price) if side>0 else min(stop,be_price)
            if trail_mode>0 and mfe>=1.0:
                activated_tr=True
                dist=(1.0 if trail_mode==1 else 2.0)*risk
                trstop=best-side*dist
                stop=max(stop,trstop) if side>0 else min(stop,trstop)

        if xi>ei:
            lo=float(np.min(L[ei+1:xi+1]));hi=float(np.max(H[ei+1:xi+1]))
            maxadv=max(maxadv,((entry-lo) if side>0 else (hi-entry))/risk)
            maxfav=max(maxfav,((hi-entry) if side>0 else (entry-lo))/risk)

        R=side*(xp-entry)/risk-(COST/10000.)*entry/risk
        rows.append({'entry_ts':int(ts[ei]),'side':'LONG' if side>0 else 'SHORT','R':float(R),'reason':reason,
                     'MAE_R':float(maxadv),'MFE_R':float(maxfav),'stop_mult':float(sm)})
        dc+=1;last=entry;la=a;k=np.searchsorted(dt,int(ts[xi])+1)
    return pd.DataFrame(rows)

def summarize(d):
    a=stats(d.R)
    return {'all':a,'exit_mix':d.reason.value_counts().to_dict(),
            'path':{'went_negative':int((d.MAE_R>0).sum()),'went_negative_pct':float((d.MAE_R>0).mean()),
                    'reached_0P5R':int((d.MFE_R>=0.5).sum()),'reached_1R':int((d.MFE_R>=1).sum()),
                    'reached_1P5R':int((d.MFE_R>=1.5).sum()),'reached_2R':int((d.MFE_R>=2).sum()),
                    'reached_3R':int((d.MFE_R>=3).sum())},
            'by_side':{s:stats(d.loc[d.side==s,'R']) for s in ['LONG','SHORT']}}

def main():
    arr=prep()
    stops=[{'name':name,**summarize(sim(arr,mode,0.,0))} for name,mode in STOP_MODES]
    bes=[{'name':'BE_'+str(x).replace('.','P')+'R',**summarize(sim(arr,0,x,0))} for x in BE_LEVELS]
    trails=[{'name':name,**summarize(sim(arr,0,0.,mode))} for name,mode in TRAIL_MODES]
    out={'lab':'CROWDFADE_EXIT_RISK_DIAGNOSTICS_LAB_020','period':'2026 seconds forward-shadow/stress',
         'warning':'1-second OHLC is not true tick sequence; protective updates are effective on the next second to avoid same-second hindsight',
         'stop_test':{'wide':'4.5 ATR','narrow':'2.5 ATR','adaptive':'3.0 ATR when ATR<=rolling96 M15 median, else 4.5 ATR','results':stops},
         'be_test':{'definition':'cost-adjusted BE; update effective next second','triggers_R':BE_LEVELS,'results':bes},
         'trailing_test':{'activation':'1R MFE','update':'every completed second, effective next second','results':trails}}
    (OUT/'stress_2026.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
