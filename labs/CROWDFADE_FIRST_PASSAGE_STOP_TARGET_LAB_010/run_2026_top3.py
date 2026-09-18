from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
ROOT=Path('labs/CROWDFADE_FIRST_PASSAGE_STOP_TARGET_LAB_010');DATA=ROOT/'stress_data';OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.5;CONF=.25;CONF_TTL=3600;RETRACE=.60;WAIT=1200;COST=.5;MAXDAY=3
CANDS=[
 {'id':'SL4_TP6_H24','sl':4.0,'tp':6.0,'hold':24},
 {'id':'SL2.5_TP8_H18','sl':2.5,'tp':8.0,'hold':18},
 {'id':'SL3_TP8_H18','sl':3.0,'tp':8.0,'hold':18},
]
def ex(z,o):
 d=DATA/o;d.mkdir(parents=True,exist_ok=True)
 if not list(d.rglob('*.csv')):
  with zipfile.ZipFile(DATA/z) as q:q.extractall(d)
 return list(d.rglob('*.csv'))[0]
def prep():
 sf=ex('BTCUSDT_sec.csv.zip','sec');ff=ex('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
 s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts');ts=s.ts.to_numpy(np.int64);O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)
 bucket=(ts//900)*900;st=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1];en=np.r_[st[1:],len(ts)];bt=bucket[st];bh=np.maximum.reduceat(H,st);bl=np.minimum.reduceat(L,st);bc=C[en-1];pc=np.r_[bc[0],bc[:-1]];tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)));atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy();av=bt+900
 f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio']);f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy();f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce');f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t');ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64);r=pd.to_numeric(f.count_long_short_ratio,errors='coerce');mu=r.rolling(72,min_periods=72).mean();sd=r.rolling(72,min_periods=72).std(ddof=0);z=((r-mu)/sd.replace(0,np.nan)).to_numpy()
 dt=np.arange(((ts[0]+299)//300)*300,ts[-1]+1,300,dtype=np.int64);di=np.searchsorted(ts,dt);ok=(di<len(ts))&(ts[np.minimum(di,len(ts)-1)]==dt);dt=dt[ok];di=di[ok];fi=np.searchsorted(ft,dt,'left')-1;ai=np.searchsorted(av,dt,'right')-1;g=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
 return ts,O,H,L,C,dt[g],di[g],z[fi[g]],atr[ai[g]]
def stats(a):
 a=np.asarray(a,float)
 if not len(a):return {'N':0}
 eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max());p=a[a>0].sum();n=abs(a[a<0].sum())
 return {'N':len(a),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),'PF':float(p/n) if n else 99.,'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}
def sim(arr,cfg):
 ts,O,H,L,C,dts,di,zd,ad=arr;rows=[];k=0;last=None;la=None;day=-1;dc=0
 while k<len(dts):
  t=int(dts[k]);d=t//86400
  if d!=day:day=d;dc=0
  if dc>=MAXDAY:k+=1;continue
  z=float(zd[k]);side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
  if side==0:k+=1;continue
  if last is not None and abs(float(O[di[k]])-last)<la:k+=1;continue
  a=float(ad[k]);conf=float(O[di[k]])+side*CONF*a;cs=int(di[k])+1;ce=min(len(ts)-1,np.searchsorted(ts,t+CONF_TTL,'left'));m=(H[cs:ce+1]>=conf) if side>0 else (L[cs:ce+1]<=conf);h=np.flatnonzero(m)
  if not len(h):k+=1;continue
  ci=cs+int(h[0]);entry=conf-side*RETRACE*a;ps=ci+1;pe=min(len(ts)-1,np.searchsorted(ts,int(ts[ci])+WAIT,'left'));m=(L[ps:pe+1]<=entry) if side>0 else (H[ps:pe+1]>=entry);f=np.flatnonzero(m)
  if not len(f):k=np.searchsorted(dts,int(ts[pe])+1);continue
  ei=ps+int(f[0]);sl=entry-side*cfg['sl']*a;tp=entry+side*cfg['tp']*a;xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+cfg['hold']*3600,'left'));xp=float(C[xe]);xi=xe;reason='TIME'
  for j in range(ei+1,xe+1):
   sh=(side>0 and L[j]<=sl) or (side<0 and H[j]>=sl);th=(side>0 and H[j]>=tp) or (side<0 and L[j]<=tp)
   if sh:xp=sl;xi=j;reason='SL';break
   if th:xp=tp;xi=j;reason='TP';break
  R=side*(xp-entry)/(cfg['sl']*a)-(COST/10000.)*entry/(cfg['sl']*a);rows.append({'entry_ts':int(ts[ei]),'R':R,'reason':reason});dc+=1;last=entry;la=a;k=np.searchsorted(dts,int(ts[xi])+1)
 return pd.DataFrame(rows)
def main():
 arr=prep();out={}
 for c in CANDS:
  d=sim(arr,c);dt=pd.to_datetime(d.entry_ts,unit='s',utc=True);mo={}
  for m in sorted(dt.dt.to_period('M').astype(str).unique()):mo[m]=stats(d.loc[dt.dt.to_period('M').astype(str)==m,'R'])
  out[c['id']]={'config':c,'all':stats(d.R),'exit_mix':d.reason.value_counts().to_dict(),'monthly':mo}
 (OUT/'stress_2026_top3.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
