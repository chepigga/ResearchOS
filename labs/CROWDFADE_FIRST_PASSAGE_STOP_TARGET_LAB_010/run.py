from pathlib import Path
import zipfile,json,itertools
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_FIRST_PASSAGE_STOP_TARGET_LAB_010')
DATA=ROOT/'data'; KDIR=DATA/'klines'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Frozen signal + execution core from LAB008
ZTH=2.5; CONF=.25; CONF_TTL_BARS=12; RETRACE=.60; WAIT_BARS=4; MAKER_BPS=.50; MAXDAY=3
SLS=[1.5,1.75,2.0,2.5,3.0,4.0]
TPS=[1.5,2.0,3.0,4.0,6.0,8.0]
HOLDS=[6,12,18,24]

def load_price():
 ps=[]
 for zp in sorted(KDIR.glob('BTCUSDT-5m-*.zip')):
  with zipfile.ZipFile(zp) as z:
   with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
  ps.append(pd.DataFrame({'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')}).dropna())
 p=pd.concat(ps,ignore_index=True).drop_duplicates('ms').sort_values('ms')
 p['time']=pd.to_datetime(p.ms.astype('int64'),unit='ms',utc=True).astype('datetime64[ns, UTC]')
 return p[['time','o','h','l','c']].reset_index(drop=True)

def load_flow():
 zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip';d=DATA/'flow';d.mkdir(exist_ok=True)
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
 p=load_price();f=load_flow()
 q=p.set_index('time').resample('15min',label='left',closed='left').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna()
 pc=q.c.shift();tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs()));q['atr']=tr.rolling(14,min_periods=14).mean();q['av']=(q.index+pd.Timedelta(minutes=15)).astype('datetime64[ns, UTC]')
 a=q[['av','atr']].dropna().reset_index(drop=True)
 p=pd.merge_asof(p.sort_values('time'),a,left_on='time',right_on='av',direction='backward')
 p=pd.merge_asof(p.sort_values('time'),f,on='time',direction='backward',tolerance=pd.Timedelta(minutes=10)).dropna(subset=['atr','z'])
 p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy()
 p['ts']=(p.time.astype('int64')//10**9).astype('int64');p['yr']=p.time.dt.year.astype('int64');p['day']=(p.time.dt.year*10000+p.time.dt.month*100+p.time.dt.day).astype('int64')
 return p.reset_index(drop=True)

@njit(cache=True)
def sim(ts,O,H,L,C,Z,A,Y,D,sl_atr,tp_atr,hold_h):
 sums=np.zeros(5);cnt=np.zeros(5,np.int64);n=0;wins=0;eq=0.;pk=0.;dd=0.;pos=0.;neg=0.;i=0;N=len(ts)
 last=0.;la=0.;has=False;day=-1;dc=0;nextts=0;sl_hits=0;tp_hits=0;time_hits=0
 while i<N-50:
  if ts[i]<nextts:i+=1;continue
  if D[i]!=day:day=D[i];dc=0
  if dc>=MAXDAY:i+=1;continue
  z=Z[i];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
  if side==0:i+=1;continue
  if has and abs(O[i]-last)<la:i+=1;continue
  a=A[i];confirm=O[i]+side*CONF*a;ci=-1
  for j in range(i+1,min(N-50,i+CONF_TTL_BARS)+1):
   if (side>0 and H[j]>=confirm) or (side<0 and L[j]<=confirm):ci=j;break
  if ci<0:i+=1;continue
  entry=confirm-side*RETRACE*a;ei=-1
  for j in range(ci+1,min(N-50,ci+WAIT_BARS)+1):
   if (side>0 and L[j]<=entry) or (side<0 and H[j]>=entry):ei=j;break
  if ei<0:i=ci+WAIT_BARS+1;continue
  sl=entry-side*sl_atr*a;tp=entry+side*tp_atr*a;xe=min(N-1,ei+hold_h*12);xp=C[xe];ex=xe;reason=0
  for j in range(ei+1,xe+1):
   sh=(side>0 and L[j]<=sl) or (side<0 and H[j]>=sl)
   th=(side>0 and H[j]>=tp) or (side<0 and L[j]<=tp)
   # conservative same-bar ordering: SL first
   if sh:
    xp=sl;ex=j;reason=-1;break
   if th:
    xp=tp;ex=j;reason=1;break
  if reason==0:time_hits+=1
  elif reason>0:tp_hits+=1
  else:sl_hits+=1
  # Equal risk: divide price PnL and cost by SL distance, so 1 stop = -1R before cost.
  R=side*(xp-entry)/(sl_atr*a)-(MAKER_BPS/10000.)*entry/(sl_atr*a)
  yi=Y[ei]-2021
  if 0<=yi<5:sums[yi]+=R;cnt[yi]+=1
  n+=1
  if R>0:wins+=1;pos+=R
  elif R<0:neg-=R
  eq+=R;pk=max(pk,eq);dd=max(dd,pk-eq);dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+300;i=ex+1
 return sums,cnt,n,eq,eq/n if n else -999.,pos/neg if neg>0 else 99.,dd,wins/n if n else 0.,sl_hits,tp_hits,time_hits

def record(sl,tp,hold,r):
 s,c,n,total,ev,pf,dd,wr,slh,tph,th=r
 annual={str(2021+k):{'SumR':float(s[k]),'N':int(c[k]),'EV':float(s[k]/c[k]) if c[k] else 0.} for k in range(5)}
 return {'SL_ATR':sl,'TP_ATR':tp,'hold_h':hold,'RR':tp/sl,'N':int(n),'positive_years':int(np.sum(s>0)),'annual':annual,
 'exit_mix':{'SL':int(slh),'TP':int(tph),'TIME':int(th),'SL_pct':float(slh/n) if n else 0.,'TP_pct':float(tph/n) if n else 0.},
 'agg':{'SumR':float(total),'EV':float(ev),'PF':float(pf),'MaxDD_R':float(dd),'R_DD':float(total/max(dd,1e-9)),'WR':float(wr)},
 'score_robust':[int(np.sum(s>0)),float(np.min(s)),float(total/max(dd,1e-9)),float(ev)]}

def main():
 p=prep();arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),p.z.to_numpy(float),p.atr.to_numpy(float),p.yr.to_numpy(np.int64),p.day.to_numpy(np.int64)]
 sim(*[x[:1000] for x in arr],1.75,3.,12)
 rows=[]
 for sl,tp,hold in itertools.product(SLS,TPS,HOLDS):rows.append(record(sl,tp,hold,sim(*arr,sl,tp,hold)))
 by_ev=sorted(rows,key=lambda x:x['agg']['EV'],reverse=True)
 by_pf=sorted(rows,key=lambda x:x['agg']['PF'],reverse=True)
 by_dd=sorted(rows,key=lambda x:(-x['positive_years'],x['agg']['MaxDD_R']))
 by_rdd=sorted(rows,key=lambda x:x['agg']['R_DD'],reverse=True)
 by_rob=sorted(rows,key=lambda x:x['score_robust'],reverse=True)
 five=[x for x in rows if x['positive_years']==5]
 five_ev=sorted(five,key=lambda x:x['agg']['EV'],reverse=True)
 five_pf=sorted(five,key=lambda x:x['agg']['PF'],reverse=True)
 five_dd=sorted(five,key=lambda x:x['agg']['MaxDD_R'])
 five_rdd=sorted(five,key=lambda x:x['agg']['R_DD'],reverse=True)
 out={'frozen_execution':{'Z':ZTH,'ConfirmATR':CONF,'ConfirmTTL_h':1,'RetraceATR':RETRACE,'PassiveTTL_min':20,'MakerCost_bps_RT_proxy':MAKER_BPS,'MaxTradesDay':MAXDAY},
 'grid':{'SL':SLS,'TP':TPS,'hold_h':HOLDS,'tested':len(rows),'same_bar_rule':'SL first (conservative)','risk':'1R equalized by SL distance'},
 'five_of_five_count':len(five),
 'top_EV_all':by_ev[:15],'top_PF_all':by_pf[:15],'lowest_DD_with_year_priority':by_dd[:15],'top_RDD_all':by_rdd[:15],
 'top_5of5_EV':five_ev[:20],'top_5of5_PF':five_pf[:20],'top_5of5_lowDD':five_dd[:20],'top_5of5_RDD':five_rdd[:20],
 'all_results':rows}
 (OUT/'summary.json').write_text(json.dumps(out,indent=2));pd.DataFrame([{'SL':x['SL_ATR'],'TP':x['TP_ATR'],'hold':x['hold_h'],'RR':x['RR'],'N':x['N'],'pos_years':x['positive_years'],'EV':x['agg']['EV'],'PF':x['agg']['PF'],'MaxDD_R':x['agg']['MaxDD_R'],'SumR':x['agg']['SumR'],'R_DD':x['agg']['R_DD'],**{f'Y{y}':x['annual'][str(y)]['SumR'] for y in range(2021,2026)}} for x in rows]).to_csv(OUT/'grid.csv',index=False)
 print(json.dumps({k:out[k] for k in ['grid','five_of_five_count','top_5of5_EV','top_5of5_PF','top_5of5_lowDD','top_5of5_RDD']},indent=2))
if __name__=='__main__':main()
