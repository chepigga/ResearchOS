from pathlib import Path
import zipfile,json,itertools
import numpy as np,pandas as pd
from numba import njit
ROOT=Path('labs/CROWDFADE_EXECUTION_PLATEAU_LAB_008');DATA=ROOT/'data';K=DATA/'klines';OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.5;EXITZ=.75;CONF=.25;STOP=1.75;HOLD=12;MAXDAY=3
IMPS=[.52,.55,.58,.60,.62,.65,.68,.70];WAITS=[3,4,5,6];COSTS=[.5,.75,1.0]
def p5():
 ps=[]
 for zp in sorted(K.glob('BTCUSDT-5m-*.zip')):
  with zipfile.ZipFile(zp) as z:
   with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
  ps.append(pd.DataFrame({'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')}).dropna())
 p=pd.concat(ps).drop_duplicates('ms').sort_values('ms');p['time']=pd.to_datetime(p.ms.astype('int64'),unit='ms',utc=True).astype('datetime64[ns, UTC]');return p[['time','o','h','l','c']]
def fl():
 d=DATA/'flow';d.mkdir(exist_ok=True)
 if not list(d.glob('*.csv')):
  with zipfile.ZipFile(DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip') as z:z.extractall(d)
 r=pd.read_csv(list(d.glob('*.csv'))[0],usecols=['create_time','sum_open_interest','count_long_short_ratio']);r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy();r['time']=pd.to_datetime(r.create_time,utc=True,errors='coerce').astype('datetime64[ns, UTC]');x=pd.to_numeric(r.count_long_short_ratio,errors='coerce');r['ratio']=x;r=r.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time');mu=r.ratio.rolling(72,min_periods=72).mean();sd=r.ratio.rolling(72,min_periods=72).std(ddof=0);r['z']=(r.ratio-mu)/sd.replace(0,np.nan);return r[['time','z']].dropna()
def prep():
 p=p5();f=fl();q=p.set_index('time').resample('15min',label='left',closed='left').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna();pc=q.c.shift();tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs()));q['atr']=tr.rolling(14,min_periods=14).mean();q['av']=(q.index+pd.Timedelta(minutes=15)).astype('datetime64[ns, UTC]');a=q[['av','atr']].dropna().reset_index(drop=True);p=pd.merge_asof(p.sort_values('time'),a,left_on='time',right_on='av',direction='backward');p=pd.merge_asof(p.sort_values('time'),f,on='time',direction='backward',tolerance=pd.Timedelta(minutes=10)).dropna(subset=['atr','z']);p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy();p['ts']=(p.time.astype('int64')//10**9).astype('int64');p['yr']=p.time.dt.year.astype('int64');p['day']=(p.time.dt.year*10000+p.time.dt.month*100+p.time.dt.day).astype('int64');return p.reset_index(drop=True)
@njit(cache=True)
def sim(ts,O,H,L,C,Z,A,Y,D,imp,wait,cost):
 s=np.zeros(5);c=np.zeros(5,np.int64);n=0;eq=0.;pos=0.;neg=0.;pk=0.;dd=0.;wins=0;i=0;N=len(ts);last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
 while i<N-20:
  if ts[i]<nextts:i+=1;continue
  if D[i]!=day:day=D[i];dc=0
  if dc>=MAXDAY:i+=1;continue
  z=Z[i];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
  if side==0:i+=1;continue
  if has and abs(O[i]-last)<la:i+=1;continue
  a=A[i];level=O[i]+side*CONF*a;ci=-1
  for j in range(i+1,min(N-20,i+12)+1):
   if (side>0 and H[j]>=level) or (side<0 and L[j]<=level):ci=j;break
  if ci<0:i+=1;continue
  target=level-side*imp*a;ei=-1
  for j in range(ci+1,min(N-20,ci+wait)+1):
   if (side>0 and L[j]<=target) or (side<0 and H[j]>=target):ei=j;break
  if ei<0:i=ci+wait+1;continue
  entry=target;sl=entry-side*STOP*a;xe=min(N-1,ei+HOLD*12);xp=C[xe];ex=xe
  for j in range(ei+1,xe+1):
   if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;ex=j;break
   if (side<0 and Z[j]<=-EXITZ) or (side>0 and Z[j]>=EXITZ):xp=C[j];ex=j;break
  R=side*(xp-entry)/(STOP*a)-(cost/10000.)*entry/(STOP*a);yi=Y[ei]-2021
  if 0<=yi<5:s[yi]+=R;c[yi]+=1
  n+=1
  if R>0:wins+=1;pos+=R
  elif R<0:neg-=R
  eq+=R;pk=max(pk,eq);dd=max(dd,pk-eq);dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+300;i=ex+1
 return s,c,n,eq,eq/n if n else -999.,pos/neg if neg else 99.,dd,wins/n if n else 0.
def main():
 p=prep();arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),p.z.to_numpy(float),p.atr.to_numpy(float),p.yr.to_numpy(np.int64),p.day.to_numpy(np.int64)];sim(*[x[:1000] for x in arr],.6,4,.5);rows=[]
 for imp,w,cost in itertools.product(IMPS,WAITS,COSTS):
  s,c,n,total,ev,pf,dd,wr=sim(*arr,imp,w,cost);ann={str(2021+k):{'SumR':float(s[k]),'N':int(c[k]),'EV':float(s[k]/c[k]) if c[k] else 0.} for k in range(5)};rows.append({'improve_atr':imp,'wait_min':w*5,'maker_cost_bps':cost,'N':int(n),'positive_years':int(np.sum(s>0)),'annual':ann,'agg':{'SumR':float(total),'EV':float(ev),'PF':float(pf),'MaxDD':float(dd),'R_DD':float(total/max(dd,1e-9)),'WR':float(wr)},'score':[int(np.sum(s>0)),float(np.min(s)),float(total/max(dd,1e-9)),float(ev)]})
 rows.sort(key=lambda x:x['score'],reverse=True);v=[x for x in rows if x['positive_years']==5 and x['N']>=1200];out={'tested':len(rows),'five_of_five':len(v),'top30':v[:30],'all':rows};(OUT/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
