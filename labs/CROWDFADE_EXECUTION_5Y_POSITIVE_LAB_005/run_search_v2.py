from pathlib import Path
import zipfile, json, itertools, hashlib
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_EXECUTION_5Y_POSITIVE_LAB_005')
DATA=ROOT/'data'; KDIR=DATA/'klines'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.50; EXIT_Z=0.75; MAXDAY=3; COST_BPS=5.0
YEARS=np.array([2021,2022,2023,2024,2025],dtype=np.int64)
CONFIRMS=[0.25,0.35,0.50,0.65]
TTLS=[1,3,6]
# 0 touch, 1 confirm close, 2 next open, 3 pullback .25, 4 pullback .50
MODES=[0,1,2,3,4]; MODE_NAMES=['touch','confirm_close','next_open','pullback_025','pullback_050']
STOPS=[1.0,1.25,1.50,1.75,2.0]
HOLDS=[3,6,12]
PAUSES=[0,1,2]; PAUSE_NAMES=['none','time3h','atr1']
EXITS=[(0,0.0,0.0,0.0,0.0,'none'),(1,0.50,0.15,0.0,0.0,'be05'),(1,0.75,0.15,0.0,0.0,'be075'),(1,1.00,0.25,0.0,0.0,'be10'),(2,0.50,0.15,2.00,0.50,'be05_tr20'),(2,0.50,0.15,2.50,0.50,'be05_tr25'),(2,0.75,0.15,2.00,0.50,'be075_tr20')]

def read_klines():
    parts=[]
    for zp in sorted(KDIR.glob('BTCUSDT-5m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            name=z.namelist()[0]
            with z.open(name) as f:
                r=pd.read_csv(f,header=None)
        # Binance kline format; possible header row is coerced away.
        x=pd.DataFrame({'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')}).dropna()
        parts.append(x)
    if not parts: raise RuntimeError('no monthly klines')
    p=pd.concat(parts,ignore_index=True).drop_duplicates('ms').sort_values('ms')
    p['time']=pd.to_datetime(p.ms.astype('int64'),unit='ms',utc=True)
    return p[['time','o','h','l','c']].reset_index(drop=True)

def load_flow():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'; d=DATA/'flow_unz';d.mkdir(exist_ok=True)
    if not list(d.glob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(d)
    raw=pd.read_csv(list(d.glob('*.csv'))[0],usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    raw=raw[pd.to_numeric(raw.sum_open_interest,errors='coerce')>0].copy(); raw['time']=pd.to_datetime(raw.create_time,utc=True,errors='coerce'); raw['ratio']=pd.to_numeric(raw.count_long_short_ratio,errors='coerce'); raw=raw.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time')
    mu=raw.ratio.rolling(72,min_periods=72).mean();sd=raw.ratio.rolling(72,min_periods=72).std(ddof=0);raw['z']=(raw.ratio-mu)/sd.replace(0,np.nan)
    return raw[['time','z']].dropna()

def prepare():
    p=read_klines();f=load_flow()
    q=p.set_index('time').resample('15min',label='left',closed='left').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna();pc=q.c.shift(1);tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs()));q['atr']=tr.rolling(14,min_periods=14).mean();q['avail']=q.index+pd.Timedelta(minutes=15)
    a=q[['avail','atr']].dropna().reset_index(drop=True)
    p=pd.merge_asof(p.sort_values('time'),a.sort_values('avail'),left_on='time',right_on='avail',direction='backward');p=pd.merge_asof(p.sort_values('time'),f.sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta(minutes=10));p=p.dropna(subset=['atr','z']).reset_index(drop=True)
    p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy();p['ts']=(p.time.astype('int64')//10**9).astype('int64');p['year']=p.time.dt.year.astype('int64');p['day']=(p.time.dt.year*10000+p.time.dt.month*100+p.time.dt.day).astype('int64')
    return p

@njit(cache=True)
def run_sim(ts,O,H,L,C,Z,A,Y,D,confirm,ttl_h,mode,stop_atr,hold_h,pause,exit_kind,be_at,be_lock,tr_arm,tr_dist):
    sums=np.zeros(5); counts=np.zeros(5,np.int64); n=0; wins=0; pos_sum=0.0; neg_sum=0.0; eq=0.0; peak_eq=0.0; maxdd=0.0
    i=0; next_ts=0; last_entry=0.0; last_atr=0.0; has_last=False; cur_day=-1; day_count=0; N=len(ts)
    while i<N-3:
        if ts[i]<next_ts:i+=1;continue
        if D[i]!=cur_day:cur_day=D[i];day_count=0
        if day_count>=MAXDAY:i+=1;continue
        z=Z[i]; side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:i+=1;continue
        if pause==2 and has_last and abs(O[i]-last_entry)<last_atr:i+=1;continue
        atr=A[i]; level=O[i]+side*confirm*atr; end=min(N-3,i+int(ttl_h*12));ci=-1
        for j in range(i+1,end+1):
            if (side>0 and H[j]>=level) or (side<0 and L[j]<=level):ci=j;break
        if ci<0:i+=1;continue
        ei=ci;entry=level
        if mode==1:entry=C[ci]
        elif mode==2:
            ei=ci+1;entry=O[ei]
        elif mode==3 or mode==4:
            retr=0.25 if mode==3 else 0.50; target=level-side*retr*atr;ei=-1
            pend=min(N-3,ci+12)
            for j in range(ci,pend+1):
                if (side>0 and L[j]<=target) or (side<0 and H[j]>=target):ei=j;entry=target;break
            if ei<0:i=ci+1;continue
        if D[ei]!=cur_day:cur_day=D[ei];day_count=0
        if day_count>=MAXDAY:i=ei+1;continue
        sl=entry-side*stop_atr*atr; xe=min(N-1,ei+int(hold_h*12));peak=entry;xp=C[xe];exit_i=xe
        for j in range(ei+1,xe+1):
            if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;exit_i=j;break
            px=C[j];fav=side*(px-entry)
            if exit_kind>=1 and fav>=be_at*atr:
                ns=entry+side*be_lock*atr
                if (side>0 and ns>sl) or (side<0 and ns<sl):sl=ns
            if side>0:
                if px>peak:peak=px
            else:
                if px<peak:peak=px
            mfe=side*(peak-entry)/atr
            if exit_kind==2 and mfe>=tr_arm:
                ns=peak-side*tr_dist*atr
                if (side>0 and ns>sl) or (side<0 and ns<sl):sl=ns
            if (side<0 and Z[j]<=-EXIT_Z) or (side>0 and Z[j]>=EXIT_Z):xp=px;exit_i=j;break
        R=side*(xp-entry)/(stop_atr*atr)-(COST_BPS/10000.0)*entry/(stop_atr*atr)
        yi=Y[ei]-2021
        if 0<=yi<5:sums[yi]+=R;counts[yi]+=1
        n+=1
        if R>0:wins+=1;pos_sum+=R
        elif R<0:neg_sum-=R
        eq+=R
        if eq>peak_eq:peak_eq=eq
        dd=peak_eq-eq
        if dd>maxdd:maxdd=dd
        day_count+=1;last_entry=entry;last_atr=atr;has_last=True
        next_ts=ts[exit_i]+(10800 if pause==1 else 300);i=exit_i+1
    pf=pos_sum/neg_sum if neg_sum>0 else 99.0;ev=eq/n if n>0 else -999.0;wr=wins/n if n>0 else 0.0
    return sums,counts,n,eq,ev,pf,maxdd,wr

def rec_from(params,res,exit_name):
    confirm,ttl,mode,stop,hold,pause=params;sums,counts,n,total,ev,pf,dd,wr=res;annual={str(2021+i):{'SumR':float(sums[i]),'N':int(counts[i]),'EV':float(sums[i]/counts[i]) if counts[i]>0 else 0.0} for i in range(5)};pos=int(np.sum(sums>0));score=[float(np.min(sums)),float(np.median(sums)),float(total/max(dd,1e-9)),float(ev)]
    return {'confirm':confirm,'ttl_h':ttl,'mode':MODE_NAMES[mode],'stop':stop,'hold_h':hold,'pause':PAUSE_NAMES[pause],'exit':exit_name,'positive_years':pos,'annual':annual,'agg':{'N':int(n),'SumR':float(total),'EV':float(ev),'PF':float(pf),'MaxDD':float(dd),'WR':float(wr)},'score':score}

def main():
    p=prepare();print('prepared',len(p),p.time.min(),p.time.max())
    ts=p.ts.to_numpy(np.int64);O=p.o.to_numpy(float);H=p.h.to_numpy(float);L=p.l.to_numpy(float);C=p.c.to_numpy(float);Z=p.z.to_numpy(float);A=p.atr.to_numpy(float);Y=p.year.to_numpy(np.int64);D=p.day.to_numpy(np.int64)
    # compile
    run_sim(ts[:1000],O[:1000],H[:1000],L[:1000],C[:1000],Z[:1000],A[:1000],Y[:1000],D[:1000],0.5,3,0,1.5,6,0,0,0,0,0,0)
    coarse=[];perfect=[];tested=0
    for params in itertools.product(CONFIRMS,TTLS,MODES,STOPS,HOLDS,PAUSES):
        r=run_sim(ts,O,H,L,C,Z,A,Y,D,*params,0,0,0,0,0);rec=rec_from(params,r,'none');coarse.append(rec);tested+=1
        if rec['positive_years']==5 and rec['agg']['N']>=150:perfect.append(rec)
    coarse.sort(key=lambda x:(x['positive_years'],x['score']),reverse=True);print('coarse',tested,'perfect',len(perfect));(OUT/'coarse_top200.json').write_text(json.dumps(coarse[:200],indent=2))
    seeds=(perfect if perfect else coarse[:80])[:80];refined=[]
    for s in seeds:
        params=(s['confirm'],s['ttl_h'],MODE_NAMES.index(s['mode']),s['stop'],s['hold_h'],PAUSE_NAMES.index(s['pause']))
        for ek,ba,bl,ta,td,en in EXITS:
            rr=run_sim(ts,O,H,L,C,Z,A,Y,D,*params,ek,ba,bl,ta,td);refined.append(rec_from(params,rr,en))
    refined.sort(key=lambda x:(x['positive_years'],x['score']),reverse=True);perfect2=[r for r in refined if r['positive_years']==5 and r['agg']['N']>=150]
    out={'signal_frozen':{'ZThreshold':ZTH,'ExitZ':EXIT_Z},'cost_rt_bps':COST_BPS,'price_source':'Binance Vision UM BTCUSDT 5m monthly','flow_source':'ResearchOS btc release','coarse_tested':tested,'coarse_5y_positive':len(perfect),'refined_tested':len(refined),'refined_5y_positive':len(perfect2),'best':refined[0],'perfect_top30':perfect2[:30],'near_top30':[r for r in refined if r['positive_years']<5][:30]};(OUT/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
