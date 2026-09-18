from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
ROOT=Path('labs/CROWDFADE_LIMIT_ONLY_TIMEFRAME_LAB_011');DATA=ROOT/'stress_data';OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.5;CONF=.25;CONF_TTL=3600;PTTL=1200;COST=.5;SL=4.;TP=6.;HOLD=86400;MAXDAY=3
CANDS=[('M1_R070',1,.70),('M5_R070',5,.70),('M15_R060',15,.60),('M5_R040',5,.40)]
def ex(z,o):
 d=DATA/o;d.mkdir(parents=True,exist_ok=True)
 if not list(d.rglob('*.csv')):
  with zipfile.ZipFile(DATA/z) as q:q.extractall(d)
 return list(d.rglob('*.csv'))[0]
def prep():
 sf=ex('BTCUSDT_sec.csv.zip','sec');ff=ex('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
 s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
 ts=s.ts.to_numpy(np.int64);O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)
 # M15 ATR14 from seconds
 b=(ts//900)*900;st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1];en=np.r_[st[1:],len(ts)];bt=b[st];bh=np.maximum.reduceat(H,st);bl=np.minimum.reduceat(L,st);bc=C[en-1];pc=np.r_[bc[0],bc[:-1]];tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)));atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy();av=bt+900
 f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio']);f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy();f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce');f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t');ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64);r=pd.to_numeric(f.count_long_short_ratio,errors='coerce');mu=r.rolling(72,min_periods=72).mean();sd=r.rolling(72,min_periods=72).std(ddof=0);z=((r-mu)/sd.replace(0,np.nan)).to_numpy()
 return ts,O,H,L,C,ft,z,av,atr
def decisions(arr,tf):
 ts,O,H,L,C,ft,z,av,atr=arr
 sec=tf*60; starts=np.arange(((ts[0]+sec-1)//sec)*sec,ts[-1]-sec+1,sec,dtype=np.int64);idx=np.searchsorted(ts,starts);idx2=np.searchsorted(ts,starts+sec)-1;ok=(idx<len(ts))&(idx2>=idx)&(idx2<len(ts));starts=starts[ok];idx=idx[ok];idx2=idx2[ok];close_ts=starts+sec;close=C[idx2]
 fi=np.searchsorted(ft,close_ts,'left')-1;ai=np.searchsorted(av,close_ts,'right')-1;g=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
 return close_ts[g],close[g],z[fi[g]],atr[ai[g]]
def stats(a):
 a=np.asarray(a,float)
 if not len(a):return {'N':0}
 eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max());p=a[a>0].sum();n=abs(a[a<0].sum())
 return {'N':len(a),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),'PF':float(p/n) if n else 99.,'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}
def sim(arr,tf,retrace):
 ts,O,H,L,C,ft,z,av,atr=arr;dt,cl,zd,ad=decisions(arr,tf);rows=[];k=0;last=None;la=None;day=-1;dc=0
 while k<len(dt)-2:
  t=int(dt[k]);d=t//86400
  if d!=day:day=d;dc=0
  if dc>=MAXDAY:k+=1;continue
  zz=float(zd[k]);side=-1 if zz>=ZTH else (1 if zz<=-ZTH else 0)
  if side==0:k+=1;continue
  sig=float(cl[k]);a=float(ad[k])
  if last is not None and abs(sig-last)<la:k+=1;continue
  level=sig+side*CONF*a;max_t=t+CONF_TTL;ci=-1
  j=k+1
  while j<len(dt) and dt[j]<=max_t:
   if (side>0 and cl[j]>=level) or (side<0 and cl[j]<=level):ci=j;break
   j+=1
  if ci<0:k+=1;continue
  confirm_px=float(cl[ci]);entry=confirm_px-side*retrace*a
  ps=np.searchsorted(ts,int(dt[ci])+1);pe=np.searchsorted(ts,int(dt[ci])+PTTL,'right');ff=np.flatnonzero((L[ps:pe]<=entry) if side>0 else (H[ps:pe]>=entry))
  if not len(ff):k=ci+1;continue
  ei=ps+int(ff[0]);sl=entry-side*SL*a;tp=entry+side*TP*a;xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+HOLD,'left'));xp=float(C[xe]);xi=xe;reason='TIME'
  for q in range(ei+1,xe+1):
   sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl);th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
   if sh:xp=sl;xi=q;reason='SL';break
   if th:xp=tp;xi=q;reason='TP';break
  R=side*(xp-entry)/(SL*a)-(COST/10000.)*entry/(SL*a);rows.append({'entry_ts':int(ts[ei]),'R':R,'reason':reason});dc+=1;last=entry;la=a;k=np.searchsorted(dt,int(ts[xi])+1)
 return pd.DataFrame(rows)
def main():
 arr=prep();out={}
 for name,tf,r in CANDS:
  d=sim(arr,tf,r);m=pd.to_datetime(d.entry_ts,unit='s',utc=True).dt.to_period('M').astype(str);mo={x:stats(d.loc[m==x,'R']) for x in sorted(m.unique())}
  out[name]={'tf_min':tf,'retrace':r,'all':stats(d.R),'exit_mix':d.reason.value_counts().to_dict(),'monthly':mo}
 (OUT/'stress_2026_top4.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
