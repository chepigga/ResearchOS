from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_EXIT_RISK_DIAGNOSTICS_LAB_020')
DATA=ROOT/'data'; KDIR=DATA/'klines1m'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.5
CONF=.25; CONF_TTL_MIN=60; RETRACE=.60; PASSIVE_TTL_MIN=20; COST=.50; MAXDAY=3
TP_ATR=10.0; HOLD_H=24

STOP_MODES=[('WIDE_4P5',0),('NARROW_2P5',1),('ADAPTIVE_3_TO_4P5',2)]
BE_LEVELS=[0.5,1.0,1.5,2.0]
TRAIL_MODES=[('NO_TRAIL',0),('TRAIL_1R_AFTER_1R',1),('TRAIL_2R_AFTER_1R',2)]

def load_1m():
    ps=[]
    for zp in sorted(KDIR.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
        ps.append(pd.DataFrame({'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),
            'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),
            'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')}).dropna())
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

def prep():
    p=load_1m(); f=load_flow()
    q=p.set_index('time').resample('15min',label='left',closed='left').agg(
        o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna()
    pc=q.c.shift();tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs()))
    q['atr']=tr.rolling(14,min_periods=14).mean()
    q['atr_med96']=q.atr.rolling(96,min_periods=96).median()
    q['av']=(q.index+pd.Timedelta(minutes=15)).astype('datetime64[ns, UTC]')
    a=q[['av','atr','atr_med96']].dropna(subset=['atr']).reset_index(drop=True)
    p=pd.merge_asof(p.sort_values('time'),a,left_on='time',right_on='av',direction='backward')
    p=pd.merge_asof(p.sort_values('time'),f,on='time',direction='backward',
                    tolerance=pd.Timedelta(minutes=10)).dropna(subset=['atr','z'])
    p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy().reset_index(drop=True)
    p['ts']=(p.time.astype('int64')//10**9).astype('int64')
    q=p.set_index('time').resample('15min',label='left',closed='left').agg(
        c=('c','last'),z=('z','last'),atr=('atr','last'),atr_med96=('atr_med96','last')).dropna(subset=['c','z','atr']).reset_index()
    q['close_ts']=(q.time.astype('int64')//10**9).astype('int64')+900
    q['yr']=q.time.dt.year.astype('int64')
    q['daykey']=(q.time.dt.year*10000+q.time.dt.month*100+q.time.dt.day).astype('int64')
    return p,q

@njit(cache=True)
def sl_mult(mode,a,amed):
    if mode==0:return 4.5
    if mode==1:return 2.5
    if not np.isfinite(amed):return 4.5
    return 4.5 if a>amed else 3.0

@njit(cache=True)
def sim(ts,O,H,L,C,dt,CL,Z,A,AM,Y,DAY,stop_mode,be_trigger,trail_mode):
    sums=np.zeros(5);cnt=np.zeros(5,np.int64)
    n=0;eq=0.;pk=0.;dd=0.;pos=0.;neg=0.;wins=0
    slh=0;tph=0;timeh=0;beh=0;trailh=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    neg_exc=0; reached_be=0; reached_1r=0; reached_2r=0; reached_3r=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        if DAY[k]!=day:day=DAY[k];dc=0
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

        sm=sl_mult(stop_mode,a,AM[k]); risk=sm*a
        stop=entry-side*risk; tp=entry+side*TP_ATR*a
        be_price=entry+side*(COST/10000.)*entry
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD_H*3600,'left'))
        xp=C[xe];ex=xe;reason=0
        best=entry; activated_be=False; activated_tr=False; ever_neg=False
        for j in range(ei+1,xe+1):
            # Existing stop/TP are checked before any update from this bar: no same-bar hindsight.
            sh=(side>0 and L[j]<=stop) or (side<0 and H[j]>=stop)
            th=(side>0 and H[j]>=tp) or (side<0 and L[j]<=tp)
            if sh:
                xp=stop;ex=j
                if activated_tr:reason=-3
                elif activated_be:reason=-2
                else:reason=-1
                break
            if th:xp=tp;ex=j;reason=1;break

            adverse=(entry-L[j]) if side>0 else (H[j]-entry)
            if adverse>0:ever_neg=True
            fav=(H[j]-entry) if side>0 else (entry-L[j])
            if fav>=1*risk:reached_1r= reached_1r # numba placeholder; counted after loop by maxima

            # Update best and protective stop for NEXT microbar only.
            cand=H[j] if side>0 else L[j]
            if (side>0 and cand>best) or (side<0 and cand<best):best=cand
            mfe=side*(best-entry)/risk
            if be_trigger>0 and (not activated_be) and mfe>=be_trigger:
                activated_be=True
                if side>0:stop=max(stop,be_price)
                else:stop=min(stop,be_price)
            if trail_mode>0 and mfe>=1.0:
                activated_tr=True
                dist=(1.0 if trail_mode==1 else 2.0)*risk
                trstop=best-side*dist
                if side>0:stop=max(stop,trstop)
                else:stop=min(stop,trstop)

        # diagnostics from realized path to exit using path slice
        lo=np.min(L[ei+1:ex+1]) if ex>ei else entry
        hi=np.max(H[ei+1:ex+1]) if ex>ei else entry
        mae=((entry-lo) if side>0 else (hi-entry))/risk
        mfe=((hi-entry) if side>0 else (entry-lo))/risk
        if mae>0:neg_exc+=1
        if be_trigger>0 and mfe>=be_trigger:reached_be+=1
        if mfe>=1:reached_1r+=1
        if mfe>=2:reached_2r+=1
        if mfe>=3:reached_3r+=1

        if reason==-1:slh+=1
        elif reason==-2:beh+=1
        elif reason==-3:trailh+=1
        elif reason==1:tph+=1
        else:timeh+=1
        R=side*(xp-entry)/risk-(COST/10000.)*entry/risk
        yi=Y[ci]-2021
        if 0<=yi<5:sums[yi]+=R;cnt[yi]+=1
        if R>0:wins+=1;pos+=R
        elif R<0:neg-=R
        n+=1;eq+=R;pk=max(pk,eq);dd=max(dd,pk-eq)
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
    return sums,cnt,n,eq,eq/n if n else -999.,pos/neg if neg>0 else 99.,dd,wins/n if n else 0.,slh,tph,timeh,beh,trailh,neg_exc,reached_be,reached_1r,reached_2r,reached_3r

def rec(name,r):
    s,c,n,total,ev,pf,dd,wr,slh,tph,timeh,beh,trailh,neg_exc,rbe,r1,r2,r3=r
    return {'name':name,'N':int(n),'trades_per_month':float(n/60.0),'positive_years':int(np.sum(s>0)),
      'annual':{str(2021+i):{'SumR':float(s[i]),'N':int(c[i]),'EV':float(s[i]/c[i]) if c[i] else 0.} for i in range(5)},
      'agg':{'SumR':float(total),'EV':float(ev),'PF':float(pf),'MaxDD_R':float(dd),'R_DD':float(total/max(dd,1e-9)),'WR':float(wr)},
      'exit_mix':{'SL':int(slh),'TP':int(tph),'TIME':int(timeh),'BE':int(beh),'TRAIL':int(trailh)},
      'path':{'went_negative':int(neg_exc),'went_negative_pct':float(neg_exc/n) if n else 0.,
              'reached_be_trigger':int(rbe),'reached_1R':int(r1),'reached_2R':int(r2),'reached_3R':int(r3)}}

def main():
    p,q=prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
         q.close_ts.to_numpy(np.int64),q.c.to_numpy(float),q.z.to_numpy(float),q.atr.to_numpy(float),q.atr_med96.to_numpy(float),
         q.yr.to_numpy(np.int64),q.daykey.to_numpy(np.int64)]
    sim(*[x[:1000] for x in arr],0,0.,0)

    stops=[rec(name,sim(*arr,mode,0.,0)) for name,mode in STOP_MODES]
    bes=[rec('BE_'+str(level).replace('.','P')+'R',sim(*arr,0,level,0)) for level in BE_LEVELS]
    trails=[rec(name,sim(*arr,0,0.,mode)) for name,mode in TRAIL_MODES]

    out={'lab':'CROWDFADE_EXIT_RISK_DIAGNOSTICS_LAB_020',
         'period':'2021-2025 Binance 1m path diagnostics',
         'warning':'1m bars are not ticks; protective updates become effective on the next 1m bar to avoid intrabar ordering leakage',
         'frozen_signal_entry':{'ZLong':2.5,'ZShort':2.5,'ConfirmATR':CONF,'RetraceATR':RETRACE,'LimitTTL_min':PASSIVE_TTL_MIN},
         'stop_test':{'wide':'4.5 ATR','narrow':'2.5 ATR','adaptive':'3.0 ATR when ATR<=rolling96 M15 median, else 4.5 ATR','results':stops},
         'be_test':{'definition':'cost-adjusted breakeven; update effective next 1m bar','triggers_R':BE_LEVELS,'results':bes},
         'trailing_test':{'activation':'1R MFE','update':'every completed 1m bar, effective next bar','results':trails}}
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
