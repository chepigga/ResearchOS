from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
from numba import njit

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

    b=(ts//900)*900
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]; en=np.r_[st[1:],len(ts)]
    bt=b[st];bh=np.maximum.reduceat(H,st);bl=np.minimum.reduceat(L,st);bc=C[en-1];pc=np.r_[bc[0],bc[:-1]]
    tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    atr_med96=pd.Series(atr).rolling(96,min_periods=96).median().to_numpy()
    av=bt+900

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
    ok=(idx2>=0)&(idx2<len(ts)); starts=starts[ok]; idx2=idx2[ok]
    dt=starts+900;cl=C[idx2]
    fi=np.searchsorted(ft,dt,'left')-1; ai=np.searchsorted(av,dt,'right')-1
    g=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    return ts,O,H,L,C,dt[g],cl[g],z[fi[g]],atr[ai[g]],atr_med96[ai[g]]

@njit(cache=True)
def sl_mult(mode,a,amed):
    if mode==0:return 4.5
    if mode==1:return 2.5
    if not np.isfinite(amed):return 4.5
    return 4.5 if a>amed else 3.0

@njit(cache=True)
def sim(ts,O,H,L,C,dt,cl,zd,ad,amed,stop_mode,be_trigger,trail_mode):
    cap=len(dt)
    ets=np.zeros(cap,np.int64); sides=np.zeros(cap,np.int8); rs=np.zeros(cap)
    reasons=np.zeros(cap,np.int8); maes=np.zeros(cap); mfes=np.zeros(cap)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0

    while k<len(dt)-2:
        t=int(dt[k]);d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=zd[k];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=cl[k];a=ad[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a;ci=-1;j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            if (side>0 and cl[j]>=lev) or (side<0 and cl[j]<=lev):ci=j;break
            j+=1
        if ci<0:k+=1;continue

        entry=cl[ci]-side*RETRACE*a
        ps=np.searchsorted(ts,int(dt[ci])+1);pe=np.searchsorted(ts,int(dt[ci])+PTTL,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):
                ei=q;break
        if ei<0:k=ci+1;continue

        sm=sl_mult(stop_mode,a,amed[k]);risk=sm*a
        stop=entry-side*risk;tp=entry+side*TP_ATR*a
        be_price=entry+side*(COST/10000.)*entry
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+HOLD,'left'))
        xp=C[xe];xi=xe;reason=0;best=entry;activated_be=False;activated_tr=False
        maxfav=0.;maxadv=0.

        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=stop) or (side<0 and H[q]>=stop)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:
                xp=stop;xi=q
                reason=-3 if activated_tr else (-2 if activated_be else -1)
                break
            if th:
                xp=tp;xi=q;reason=1;break

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
            lo=np.min(L[ei+1:xi+1]);hi=np.max(H[ei+1:xi+1])
            adv=((entry-lo) if side>0 else (hi-entry))/risk
            fav=((hi-entry) if side>0 else (entry-lo))/risk
            if adv>maxadv:maxadv=adv
            if fav>maxfav:maxfav=fav

        R=side*(xp-entry)/risk-(COST/10000.)*entry/risk
        ets[n]=ts[ei];sides[n]=side;rs[n]=R;reasons[n]=reason;maes[n]=maxadv;mfes[n]=maxfav;n+=1
        dc+=1;last=entry;la=a;has=True;k=np.searchsorted(dt,int(ts[xi])+1)

    return ets[:n],sides[:n],rs[:n],reasons[:n],maes[:n],mfes[:n]

def stats(a,months_div=6.0):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    p=a[a>0].sum();n=abs(a[a<0].sum())
    return {'N':int(len(a)),'trades_per_month':float(len(a)/months_div),'WR':float((a>0).mean()),
            'EV':float(a.mean()),'SumR':float(a.sum()),'PF':float(p/n) if n else 99.,
            'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

def summarize(res):
    ets,sides,r,reasons,mae,mfe=res
    months=pd.to_datetime(ets,unit='s',utc=True).to_period('M').astype(str) if len(ets) else np.array([])
    um=sorted(set(months))
    names={-3:'TRAIL',-2:'BE',-1:'SL',0:'TIME',1:'TP'}
    return {
      'all':stats(r),
      'exit_mix':{names[x]:int((reasons==x).sum()) for x in [-3,-2,-1,0,1] if int((reasons==x).sum())>0},
      'positive_months':int(sum(stats(r[months==m],1.0)['SumR']>0 for m in um)) if len(r) else 0,
      'monthly':{m:stats(r[months==m],1.0) for m in um},
      'path':{'went_negative':int((mae>0).sum()),'went_negative_pct':float((mae>0).mean()) if len(mae) else 0.,
              'reached_0P5R':int((mfe>=.5).sum()),'reached_1R':int((mfe>=1).sum()),
              'reached_1P5R':int((mfe>=1.5).sum()),'reached_2R':int((mfe>=2).sum()),'reached_3R':int((mfe>=3).sum())},
      'by_side':{'LONG':stats(r[sides>0]),'SHORT':stats(r[sides<0])}
    }

def main():
    arr=prep()
    sim(*[x[:2000] for x in arr],0,0.,0) # numba warmup
    stops=[{'name':name,**summarize(sim(*arr,mode,0.,0))} for name,mode in STOP_MODES]
    bes=[{'name':'BE_'+str(x).replace('.','P')+'R',**summarize(sim(*arr,0,x,0))} for x in BE_LEVELS]
    trails=[{'name':name,**summarize(sim(*arr,0,0.,mode))} for name,mode in TRAIL_MODES]
    out={'lab':'CROWDFADE_EXIT_RISK_DIAGNOSTICS_LAB_020','period':'2026 seconds forward-shadow/stress',
         'warning':'1-second OHLC is not true tick sequence; protective updates are effective on the next second to avoid same-second hindsight',
         'stop_test':{'wide':'4.5 ATR','narrow':'2.5 ATR','adaptive':'3.0 ATR when ATR<=rolling96 M15 median, else 4.5 ATR','results':stops},
         'be_test':{'definition':'cost-adjusted BE; update effective next second','triggers_R':BE_LEVELS,'results':bes},
         'trailing_test':{'activation':'1R MFE','update':'every completed second, effective next second','results':trails}}
    (OUT/'stress_2026.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
