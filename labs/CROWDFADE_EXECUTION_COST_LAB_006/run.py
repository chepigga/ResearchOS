from pathlib import Path
import zipfile,json,itertools
import numpy as np,pandas as pd
from numba import njit
ROOT=Path('labs/CROWDFADE_EXECUTION_COST_LAB_006'); DATA=ROOT/'data'; KDIR=DATA/'klines'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.50; EXIT_Z=0.75; CONFIRM=0.25; CONFIRM_TTL_H=1; STOP_ATR=1.75; HOLD_H=12; MAXDAY=3
IMPROVE=[0.0,0.05,0.10,0.15,0.25,0.35,0.50]
WAIT_BARS=[1,3,6,12]  # 5/15/30/60m
MAKER_COST=[0.5,1.0,2.0]
FALLBACK=[0,1] # 0 maker-only; 1 taker fallback at next bar open, 5bps
TAKER_BPS=5.0
def read_klines():
 p=[]
 for zp in sorted(KDIR.glob('BTCUSDT-5m-*.zip')):
  with zipfile.ZipFile(zp) as z:
   with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
  x=pd.DataFrame({'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')}).dropna();p.append(x)
 q=pd.concat(p,ignore_index=True).drop_duplicates('ms').sort_values('ms');q['time']=pd.to_datetime(q.ms.astype('int64'),unit='ms',utc=True).astype('datetime64[ns, UTC]');return q[['time','o','h','l','c']].reset_index(drop=True)
def load_flow():
 zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'; d=DATA/'flow_unz';d.mkdir(exist_ok=True)
 if not list(d.glob('*.csv')):
  with zipfile.ZipFile(zp) as z:z.extractall(d)
 r=pd.read_csv(list(d.glob('*.csv'))[0],usecols=['create_time','sum_open_interest','count_long_short_ratio']);r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy();r['time']=pd.to_datetime(r.create_time,utc=True,errors='coerce').astype('datetime64[ns, UTC]');r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce');r=r.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time');mu=r.ratio.rolling(72,min_periods=72).mean();sd=r.ratio.rolling(72,min_periods=72).std(ddof=0);r['z']=(r.ratio-mu)/sd.replace(0,np.nan);return r[['time','z']].dropna()
def prep():
 p=read_klines();f=load_flow();q=p.set_index('time').resample('15min',label='left',closed='left').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna();pc=q.c.shift();tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs()));q['atr']=tr.rolling(14,min_periods=14).mean();q['avail']=(q.index+pd.Timedelta(minutes=15)).astype('datetime64[ns, UTC]');a=q[['avail','atr']].dropna().reset_index(drop=True);p=pd.merge_asof(p.sort_values('time'),a.sort_values('avail'),left_on='time',right_on='avail',direction='backward');p=pd.merge_asof(p.sort_values('time'),f.sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta(minutes=10));p=p.dropna(subset=['atr','z']);p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy();p['ts']=(p.time.astype('int64')//10**9).astype('int64');p['year']=p.time.dt.year.astype('int64');p['day']=(p.time.dt.year*10000+p.time.dt.month*100+p.time.dt.day).astype('int64');return p.reset_index(drop=True)
@njit(cache=True)
def sim(ts,O,H,L,C,Z,A,Y,D,improve,wait_bars,maker_bps,fallback):
 sums=np.zeros(5);cnt=np.zeros(5,np.int64);n=0;maker_n=0;taker_n=0;wins=0;eq=0.;pos=0.;neg=0.;pk=0.;ddmax=0.;costsum=0.;i=0;N=len(ts);last_entry=0.;last_atr=0.;has_last=False;curday=-1;daycnt=0;nextts=0
 while i<N-20:
  if ts[i]<nextts:i+=1;continue
  if D[i]!=curday:curday=D[i];daycnt=0
  if daycnt>=MAXDAY:i+=1;continue
  z=Z[i];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
  if side==0:i+=1;continue
  if has_last and abs(O[i]-last_entry)<last_atr:i+=1;continue
  atr=A[i]; level=O[i]+side*CONFIRM*atr; ci=-1
  for j in range(i+1,min(N-20,i+12)+1):
   if (side>0 and H[j]>=level) or (side<0 and L[j]<=level):ci=j;break
  if ci<0:i+=1;continue
  target=level-side*improve*atr; ei=-1; entry=0.; cbps=0.; kind=0
  # post-confirm passive order starts next M5 bar: no same-bar fill credit
  pend_end=min(N-20,ci+wait_bars)
  for j in range(ci+1,pend_end+1):
   if (side>0 and L[j]<=target) or (side<0 and H[j]>=target):
    ei=j;entry=target;cbps=maker_bps;kind=1;break
  if ei<0:
   if fallback==0:
    i=pend_end+1;continue
   ei=pend_end+1
   if ei>=N-2:break
   entry=O[ei];cbps=TAKER_BPS;kind=2
  if D[ei]!=curday:curday=D[ei];daycnt=0
  if daycnt>=MAXDAY:i=ei+1;continue
  sl=entry-side*STOP_ATR*atr; xe=min(N-1,ei+HOLD_H*12);xp=C[xe];ex=xe
  for j in range(ei+1,xe+1):
   if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;ex=j;break
   if (side<0 and Z[j]<=-EXIT_Z) or (side>0 and Z[j]>=EXIT_Z):xp=C[j];ex=j;break
  R=side*(xp-entry)/(STOP_ATR*atr)-(cbps/10000.)*entry/(STOP_ATR*atr); yi=Y[ei]-2021
  if 0<=yi<5:sums[yi]+=R;cnt[yi]+=1
  n+=1;maker_n+=1 if kind==1 else 0;taker_n+=1 if kind==2 else 0;costsum+=cbps
  if R>0:wins+=1;pos+=R
  elif R<0:neg-=R
  eq+=R;pk=max(pk,eq);ddmax=max(ddmax,pk-eq);daycnt+=1;last_entry=entry;last_atr=atr;has_last=True;nextts=ts[ex]+300;i=ex+1
 return sums,cnt,n,maker_n,taker_n,eq,eq/n if n else -999.,pos/neg if neg>0 else 99.,ddmax,wins/n if n else 0.,costsum/n if n else 99.
def rec(params,r):
 imp,wb,mb,fb=params;s,c,n,mn,tn,total,ev,pf,dd,wr,eff=r; annual={str(2021+k):{'SumR':float(s[k]),'N':int(c[k]),'EV':float(s[k]/c[k]) if c[k] else 0.} for k in range(5)};return {'improve_atr':imp,'wait_min':wb*5,'maker_cost_bps':mb,'fallback':'taker5' if fb else 'none','effective_cost_bps':float(eff),'maker_share':float(mn/n) if n else 0.,'N':int(n),'positive_years':int(np.sum(s>0)),'annual':annual,'agg':{'SumR':float(total),'EV':float(ev),'PF':float(pf),'MaxDD':float(dd),'R_DD':float(total/max(dd,1e-9)),'WR':float(wr)},'score':[int(np.sum(s>0)),float(np.min(s)),float(total/max(dd,1e-9)),float(ev)]}
def main():
 p=prep();print('prepared',len(p),p.time.min(),p.time.max());arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),p.z.to_numpy(float),p.atr.to_numpy(float),p.year.to_numpy(np.int64),p.day.to_numpy(np.int64)]
 sim(*[x[:1000] for x in arr],0.1,3,1.,0)
 rows=[]
 for par in itertools.product(IMPROVE,WAIT_BARS,MAKER_COST,FALLBACK):rows.append(rec(par,sim(*arr,*par)))
 rows.sort(key=lambda x:x['score'],reverse=True)
 valid=[x for x in rows if x['positive_years']==5 and x['effective_cost_bps']<3 and x['N']>=1200]
 # robustness: retain configs that are 5/5 at maker cost +1bp too when possible
 robust=[]
 for x in valid:
  bumped=min(3.,x['maker_cost_bps']+1.0);par=(x['improve_atr'],x['wait_min']//5,bumped,1 if x['fallback']=='taker5' else 0);rr=rec(par,sim(*arr,*par))
  if rr['positive_years']==5 and rr['effective_cost_bps']<3.5:robust.append({'base':x,'maker_cost_plus1bp':rr})
 out={'frozen_core':{'Z':ZTH,'ExitZ':EXIT_Z,'confirm':CONFIRM,'confirm_ttl_h':CONFIRM_TTL_H,'stop_atr':STOP_ATR,'hold_h':HOLD_H,'pause':'ATR1','max_day':MAXDAY},'tested':len(rows),'valid_5y_cost_lt3_n1200':len(valid),'robust_plus1bp':len(robust),'top30':valid[:30],'robust_top20':robust[:20],'all_top50':rows[:50]};(OUT/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
