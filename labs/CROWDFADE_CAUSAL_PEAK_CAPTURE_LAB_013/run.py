from pathlib import Path
import zipfile,json,itertools
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_CAUSAL_PEAK_CAPTURE_LAB_013')
DATA=ROOT/'data'; KDIR=DATA/'klines1m'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Frozen signal + entry from LAB011/012
ZTH=2.5; CONF=.25; CONF_TTL_MIN=60; RETRACE=.60; PASSIVE_TTL_MIN=20; COST=.50; MAXDAY=3
SL=4.5; HOLD_H=24

# modes:
# HARD: fixed TP only
# TRAIL: optional fixed TP cap + causal trailing activated after arm ATR favorable excursion
CONFIGS=[
 ('HARD_TP10','HARD',10.0,0.0,0.0),
 ('TP6_TRAIL_1','TRAIL',6.0,4.0,1.0),
 ('TP6_TRAIL_1.5','TRAIL',6.0,4.0,1.5),
 ('TP8_TRAIL_1','TRAIL',8.0,5.0,1.0),
 ('TP8_TRAIL_1.5','TRAIL',8.0,5.0,1.5),
 ('NOTP_ARM6_D1','TRAIL',99.0,6.0,1.0),
 ('NOTP_ARM6_D1.5','TRAIL',99.0,6.0,1.5),
 ('NOTP_ARM6_D2','TRAIL',99.0,6.0,2.0),
 ('NOTP_ARM8_D1','TRAIL',99.0,8.0,1.0),
 ('NOTP_ARM8_D1.5','TRAIL',99.0,8.0,1.5),
 ('NOTP_ARM8_D2','TRAIL',99.0,8.0,2.0),
]

def load_1m():
 ps=[]
 for zp in sorted(KDIR.glob('BTCUSDT-1m-*.zip')):
  with zipfile.ZipFile(zp) as z:
   with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
  ps.append(pd.DataFrame({'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')}).dropna())
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
 mu=r.ratio.rolling(72,min_periods=72).mean();sd=r.ratio.rolling(72,min_periods=72).std(ddof=0);r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
 return r[['time','z']].dropna()

def prep():
 p=load_1m();f=load_flow()
 q=p.set_index('time').resample('15min',label='left',closed='left').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna()
 pc=q.c.shift();tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs()))
 q['atr']=tr.rolling(14,min_periods=14).mean();q['av']=(q.index+pd.Timedelta(minutes=15)).astype('datetime64[ns, UTC]')
 a=q[['av','atr']].dropna().reset_index(drop=True)
 p=pd.merge_asof(p.sort_values('time'),a,left_on='time',right_on='av',direction='backward')
 p=pd.merge_asof(p.sort_values('time'),f,on='time',direction='backward',tolerance=pd.Timedelta(minutes=10)).dropna(subset=['atr','z'])
 p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy().reset_index(drop=True)
 p['ts']=(p.time.astype('int64')//10**9).astype('int64')
 q=p.set_index('time').resample('15min',label='left',closed='left').agg(c=('c','last'),z=('z','last'),atr=('atr','last')).dropna().reset_index()
 q['close_ts']=(q.time.astype('int64')//10**9).astype('int64')+900
 q['yr']=q.time.dt.year.astype('int64');q['day']=(q.time.dt.year*10000+q.time.dt.month*100+q.time.dt.day).astype('int64')
 return p,q

@njit(cache=True)
def sim(ts,O,H,L,C,dt,CL,Z,A,Y,D,tp_cap,arm,dist,use_trail):
 sums=np.zeros(5);cnt=np.zeros(5,np.int64);n=0;eq=0.;pk=0.;dd=0.;pos=0.;neg=0.;wins=0
 slh=0;tph=0;trh=0;timeh=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
 while k<len(dt)-3:
  t=dt[k]
  if t<nextts:k+=1;continue
  if D[k]!=day:day=D[k];dc=0
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

  sl=entry-side*SL*a
  tp=entry+side*tp_cap*a
  xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD_H*3600,'left'))
  xp=C[xe];ex=xe;reason=0
  trail_on=False;best=entry;trail_level=0.
  for j in range(ei+1,xe+1):
   # hard SL always first for conservative same-bar handling
   sh=(side>0 and L[j]<=sl) or (side<0 and H[j]>=sl)
   if sh:xp=sl;ex=j;reason=-1;break

   # hard TP cap, if finite
   if tp_cap<90.0:
    th=(side>0 and H[j]>=tp) or (side<0 and L[j]<=tp)
    if th:xp=tp;ex=j;reason=1;break

   if use_trail==1:
    if side>0:
     if H[j]>best:best=H[j]
     if (not trail_on) and best>=entry+arm*a:
      trail_on=True;trail_level=best-dist*a
     elif trail_on:
      nl=best-dist*a
      if nl>trail_level:trail_level=nl
     # conservative: once armed intrabar, allow same bar low to trigger
     if trail_on and L[j]<=trail_level:
      xp=trail_level;ex=j;reason=2;break
    else:
     if L[j]<best:best=L[j]
     if (not trail_on) and best<=entry-arm*a:
      trail_on=True;trail_level=best+dist*a
     elif trail_on:
      nl=best+dist*a
      if nl<trail_level:trail_level=nl
     if trail_on and H[j]>=trail_level:
      xp=trail_level;ex=j;reason=2;break

  if reason<0:slh+=1
  elif reason==1:tph+=1
  elif reason==2:trh+=1
  else:timeh+=1
  R=side*(xp-entry)/(SL*a)-(COST/10000.)*entry/(SL*a)
  yi=Y[ci]-2021
  if 0<=yi<5:sums[yi]+=R;cnt[yi]+=1
  n+=1
  if R>0:wins+=1;pos+=R
  elif R<0:neg-=R
  eq+=R;pk=max(pk,eq);dd=max(dd,pk-eq);dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
 return sums,cnt,n,eq,eq/n if n else -999.,pos/neg if neg>0 else 99.,dd,wins/n if n else 0.,slh,tph,trh,timeh

def rec(name,mode,tp,arm,dist,r):
 s,c,n,total,ev,pf,dd,wr,slh,tph,trh,timeh=r
 annual={str(2021+i):{'SumR':float(s[i]),'N':int(c[i]),'EV':float(s[i]/c[i]) if c[i] else 0.} for i in range(5)}
 return {'id':name,'mode':mode,'TP_cap_ATR':None if tp>90 else tp,'trail_arm_ATR':None if arm==0 else arm,'trail_dist_ATR':None if dist==0 else dist,'N':int(n),'positive_years':int(np.sum(s>0)),'annual':annual,'exit_mix':{'SL':int(slh),'TP':int(tph),'TRAIL':int(trh),'TIME':int(timeh)},'agg':{'SumR':float(total),'EV':float(ev),'PF':float(pf),'MaxDD_R':float(dd),'R_DD':float(total/max(dd,1e-9)),'WR':float(wr)},'score':[int(np.sum(s>0)),float(np.min(s)),float(total/max(dd,1e-9)),float(ev)]}

def main():
 p,q=prep();arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),q.close_ts.to_numpy(np.int64),q.c.to_numpy(float),q.z.to_numpy(float),q.atr.to_numpy(float),q.yr.to_numpy(np.int64),q.day.to_numpy(np.int64)]
 sim(*[x[:1000] for x in arr],10.,0.,0.,0)
 rows=[]
 for name,mode,tp,arm,dist in CONFIGS:
  rows.append(rec(name,mode,tp,arm,dist,sim(*arr,tp,arm,dist,0 if mode=='HARD' else 1)))
 rows.sort(key=lambda x:x['score'],reverse=True)
 out={'frozen':{'entry':'M15 close confirm + limit-only retrace 0.60 ATR','SL_ATR':SL,'hold_h':HOLD_H,'cost_bps':COST},'tested':len(rows),'results':rows}
 (OUT/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
