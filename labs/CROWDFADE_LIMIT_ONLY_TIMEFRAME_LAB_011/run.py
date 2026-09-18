from pathlib import Path
import zipfile,json,itertools
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_LIMIT_ONLY_TIMEFRAME_LAB_011')
DATA=ROOT/'data'; KDIR=DATA/'klines1m'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Frozen signal/exit from LAB010
ZTH=2.5; CONF=.25; CONF_TTL_MIN=60; PASSIVE_TTL_MIN=20; MAKER_BPS=.50; MAXDAY=3
SL=4.0; TP=6.0; HOLD_MIN=24*60
TFS=[1,3,5,15,30,60]
RETRACES=[.40,.50,.60,.70]

def load_1m():
 ps=[]
 for zp in sorted(KDIR.glob('BTCUSDT-1m-*.zip')):
  with zipfile.ZipFile(zp) as z:
   with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
  x=pd.DataFrame({'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')}).dropna()
  ps.append(x)
 p=pd.concat(ps,ignore_index=True).drop_duplicates('ms').sort_values('ms')
 p['time']=pd.to_datetime(p.ms.astype('int64'),unit='ms',utc=True).astype('datetime64[ns, UTC]')
 return p[['time','o','h','l','c']].reset_index(drop=True)

def load_flow():
 d=DATA/'flow'; d.mkdir(exist_ok=True); zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
 if not list(d.glob('*.csv')):
  with zipfile.ZipFile(zp) as z:z.extractall(d)
 r=pd.read_csv(list(d.glob('*.csv'))[0],usecols=['create_time','sum_open_interest','count_long_short_ratio'])
 r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
 r['time']=pd.to_datetime(r.create_time,utc=True,errors='coerce').astype('datetime64[ns, UTC]')
 r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
 r=r.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time')
 mu=r.ratio.rolling(72,min_periods=72).mean(); sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
 r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
 return r[['time','z']].dropna()

def prep():
 p=load_1m(); f=load_flow()
 # ATR remains frozen M15 ATR14, causally available after bar close
 q=p.set_index('time').resample('15min',label='left',closed='left').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna()
 pc=q.c.shift(); tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs()))
 q['atr']=tr.rolling(14,min_periods=14).mean(); q['av']=(q.index+pd.Timedelta(minutes=15)).astype('datetime64[ns, UTC]')
 a=q[['av','atr']].dropna().reset_index(drop=True)
 p=pd.merge_asof(p.sort_values('time'),a,left_on='time',right_on='av',direction='backward')
 p=pd.merge_asof(p.sort_values('time'),f,on='time',direction='backward',tolerance=pd.Timedelta(minutes=10))
 p=p.dropna(subset=['atr','z'])
 p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy().reset_index(drop=True)
 p['ts']=(p.time.astype('int64')//10**9).astype('int64'); p['yr']=p.time.dt.year.astype('int64'); p['day']=(p.time.dt.year*10000+p.time.dt.month*100+p.time.dt.day).astype('int64')
 return p

def make_tf(p,tf):
 q=p.set_index('time').resample(f'{tf}min',label='left',closed='left').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last'),z=('z','last'),atr=('atr','last')).dropna().reset_index()
 q['close_ts']=(q.time.astype('int64')//10**9).astype('int64')+tf*60
 q['yr']=q.time.dt.year.astype('int64'); q['day']=(q.time.dt.year*10000+q.time.dt.month*100+q.time.dt.day).astype('int64')
 return q

@njit(cache=True)
def sim(base_ts,BO,BH,BL,BC,tf_ts,TO,TC,TZ,TA,TY,TD,retrace):
 sums=np.zeros(5); cnt=np.zeros(5,np.int64); n=0; wins=0;eq=0.;pk=0.;dd=0.;pos=0.;neg=0.;slh=0;tph=0;timeh=0
 i=0;N=len(tf_ts);last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
 while i<N-3:
  t=tf_ts[i]
  if t<nextts:i+=1;continue
  if TD[i]!=day:day=TD[i];dc=0
  if dc>=MAXDAY:i+=1;continue
  z=TZ[i];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
  if side==0:i+=1;continue
  # signal price is just-closed TF close
  sig=TC[i]; a=TA[i]
  if has and abs(sig-last)<la:i+=1;continue

  # Confirmation requires a TF BAR CLOSE beyond confirm level, within 1h.
  confirm_level=sig+side*CONF*a; ci=-1
  maxbars=max(1,CONF_TTL_MIN//max(1,(tf_ts[1]-tf_ts[0])//60))
  for j in range(i+1,min(N-3,i+maxbars)+1):
   if (side>0 and TC[j]>=confirm_level) or (side<0 and TC[j]<=confirm_level):
    ci=j;break
  if ci<0:i+=1;continue

  confirm_px=TC[ci]
  entry=confirm_px-side*retrace*a
  start= np.searchsorted(base_ts,tf_ts[ci])+1
  endt=tf_ts[ci]+PASSIVE_TTL_MIN*60
  end=np.searchsorted(base_ts,endt,'right')
  ei=-1
  for j in range(start,min(len(base_ts),end)):
   if (side>0 and BL[j]<=entry) or (side<0 and BH[j]>=entry):
    ei=j;break
  if ei<0:
   i=ci+1;continue

  if TD[ci]!=day: day=TD[ci];dc=0
  if dc>=MAXDAY:i=ci+1;continue
  sl=entry-side*SL*a;tp=entry+side*TP*a
  xe=min(len(base_ts)-1,np.searchsorted(base_ts,base_ts[ei]+HOLD_MIN*60,'left'))
  xp=BC[xe];ex=xe;reason=0
  for j in range(ei+1,xe+1):
   sh=(side>0 and BL[j]<=sl) or (side<0 and BH[j]>=sl)
   th=(side>0 and BH[j]>=tp) or (side<0 and BL[j]<=tp)
   if sh:xp=sl;ex=j;reason=-1;break
   if th:xp=tp;ex=j;reason=1;break
  if reason<0:slh+=1
  elif reason>0:tph+=1
  else:timeh+=1
  R=side*(xp-entry)/(SL*a)-(MAKER_BPS/10000.)*entry/(SL*a)
  yi=TY[ci]-2021
  if 0<=yi<5:sums[yi]+=R;cnt[yi]+=1
  n+=1
  if R>0:wins+=1;pos+=R
  elif R<0:neg-=R
  eq+=R;pk=max(pk,eq);dd=max(dd,pk-eq)
  dc+=1;last=entry;la=a;has=True;nextts=base_ts[ex]+60
  i=np.searchsorted(tf_ts,nextts)
 return sums,cnt,n,eq,eq/n if n else -999.,pos/neg if neg>0 else 99.,dd,wins/n if n else 0.,slh,tph,timeh

def rec(tf,retrace,r):
 s,c,n,total,ev,pf,dd,wr,slh,tph,timeh=r
 annual={str(2021+k):{'SumR':float(s[k]),'N':int(c[k]),'EV':float(s[k]/c[k]) if c[k] else 0.} for k in range(5)}
 return {'entry_tf_min':tf,'retrace_atr':retrace,'N':int(n),'positive_years':int(np.sum(s>0)),'annual':annual,
 'exit_mix':{'SL':int(slh),'TP':int(tph),'TIME':int(timeh)},
 'agg':{'SumR':float(total),'EV':float(ev),'PF':float(pf),'MaxDD_R':float(dd),'R_DD':float(total/max(dd,1e-9)),'WR':float(wr)},
 'score':[int(np.sum(s>0)),float(np.min(s)),float(total/max(dd,1e-9)),float(ev)]}

def main():
 p=prep();base=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float)]
 rows=[]
 for tf in TFS:
  q=make_tf(p,tf)
  arr=base+[q.close_ts.to_numpy(np.int64),q.o.to_numpy(float),q.c.to_numpy(float),q.z.to_numpy(float),q.atr.to_numpy(float),q.yr.to_numpy(np.int64),q.day.to_numpy(np.int64)]
  sim(*[x[:min(1000,len(x))] for x in arr],.6)
  for r in RETRACES:rows.append(rec(tf,r,sim(*arr,r)))
 rows.sort(key=lambda x:x['score'],reverse=True)
 five=[x for x in rows if x['positive_years']==5]
 out={'frozen':{'Z':ZTH,'ConfirmATR':CONF,'ConfirmTTL_min':CONF_TTL_MIN,'PassiveTTL_min':PASSIVE_TTL_MIN,'MakerCost_bps':MAKER_BPS,'SL':SL,'TP':TP,'Hold_h':24,'MaxTradesDay':MAXDAY},
 'definition':'signal on completed TF bar; confirmation requires completed TF close beyond 0.25 ATR; then maker-only retrace limit, no market fallback',
 'tested':len(rows),'five_of_five':len(five),'top_all':rows[:30],
 'top_5of5_EV':sorted(five,key=lambda x:x['agg']['EV'],reverse=True)[:20],
 'top_5of5_lowDD':sorted(five,key=lambda x:x['agg']['MaxDD_R'])[:20],
 'all_results':rows}
 (OUT/'summary.json').write_text(json.dumps(out,indent=2))
 pd.DataFrame([{'tf':x['entry_tf_min'],'retrace':x['retrace_atr'],'N':x['N'],'pos_years':x['positive_years'],'EV':x['agg']['EV'],'PF':x['agg']['PF'],'DD':x['agg']['MaxDD_R'],'SumR':x['agg']['SumR'],**{f'Y{y}':x['annual'][str(y)]['SumR'] for y in range(2021,2026)}} for x in rows]).to_csv(OUT/'grid.csv',index=False)
 print(json.dumps({'five_of_five':len(five),'top_5of5_EV':out['top_5of5_EV'],'top_5of5_lowDD':out['top_5of5_lowDD']},indent=2))
if __name__=='__main__':main()
