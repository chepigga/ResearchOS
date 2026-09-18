from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
ROOT=Path('labs/CROWDFADE_EXECUTION_EXTENSION_VETO_LAB_007');DATA=ROOT/'stress_data';OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.5;EXIT_Z=.75;CONF=.25;CONF_TTL=3600;STOP=1.75;HOLD=43200;MAXDAY=3
CANDS=[
 {'id':'B050_W15_NO','imp':.50,'wait':900,'ext':99.,'cost':.5},
 {'id':'V050_W15_E15','imp':.50,'wait':900,'ext':1.5,'cost':.5},
 {'id':'V045_W10_E10','imp':.45,'wait':600,'ext':1.0,'cost':.5},
 {'id':'B060_W20_NO','imp':.60,'wait':1200,'ext':99.,'cost':.5},
]
def extract(z,o):
 d=DATA/o;d.mkdir(parents=True,exist_ok=True)
 if not list(d.rglob('*.csv')):
  with zipfile.ZipFile(DATA/z) as q:q.extractall(d)
 return list(d.rglob('*.csv'))[0]
def prep():
 sf=extract('BTCUSDT_sec.csv.zip','sec');ff=extract('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow');s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts');ts=s.ts.to_numpy(np.int64);O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)
 bucket=(ts//900)*900;st=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1];en=np.r_[st[1:],len(ts)];bt=bucket[st];bh=np.maximum.reduceat(H,st);bl=np.minimum.reduceat(L,st);bc=C[en-1];pc=np.r_[bc[0],bc[:-1]];tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)));atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy();atr_av=bt+900
 f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio']);f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy();f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce');f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t');ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64);r=pd.to_numeric(f.count_long_short_ratio,errors='coerce');mu=r.rolling(72,min_periods=72).mean();sd=r.rolling(72,min_periods=72).std(ddof=0);z=((r-mu)/sd.replace(0,np.nan)).to_numpy()
 dt=np.arange(((ts[0]+299)//300)*300,ts[-1]+1,300,dtype=np.int64);di=np.searchsorted(ts,dt);ok=(di<len(ts))&(ts[np.minimum(di,len(ts)-1)]==dt);dt=dt[ok];di=di[ok];fi=np.searchsorted(ft,dt,'left')-1;ai=np.searchsorted(atr_av,dt,'right')-1;g=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
 return ts,O,H,L,C,ft,z,dt[g],di[g],z[fi[g]],atr[ai[g]]
def stats(a):
 a=np.asarray(a,float)
 if not len(a):return {'N':0}
 eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max());p=a[a>0].sum();n=abs(a[a<0].sum());return {'N':len(a),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),'PF':float(p/n) if n else 99.,'MaxDD':dd,'R_DD':float(a.sum()/dd) if dd else 99.}
def sim(arr,cfg):
 ts,O,H,L,C,ft,z,dts,di,zd,ad=arr;rows=[];k=0;last=None;la=None;day=-1;dc=0;confirms=0;vetoes=0
 while k<len(dts):
  t=int(dts[k]);d=t//86400
  if d!=day:day=d;dc=0
  if dc>=MAXDAY:k+=1;continue
  zz=float(zd[k]);side=-1 if zz>=ZTH else (1 if zz<=-ZTH else 0)
  if side==0:k+=1;continue
  if last is not None and abs(float(O[di[k]])-last)<la:k+=1;continue
  a=float(ad[k]);level=float(O[di[k]])+side*CONF*a;cs=int(di[k])+1;ce=min(len(ts)-1,np.searchsorted(ts,t+CONF_TTL,'left'));m=(H[cs:ce+1]>=level) if side>0 else (L[cs:ce+1]<=level);hh=np.flatnonzero(m)
  if not len(hh):k+=1;continue
  ci=cs+int(hh[0]);confirms+=1;target=level-side*cfg['imp']*a;ext=level+side*cfg['ext']*a;ps=ci+1;pe=min(len(ts)-1,np.searchsorted(ts,int(ts[ci])+cfg['wait'],'left'));ei=-1
  for j in range(ps,pe+1):
   toxic=(side>0 and H[j]>=ext) or (side<0 and L[j]<=ext)
   if toxic:vetoes+=1;ei=-2;break
   fill=(side>0 and L[j]<=target) or (side<0 and H[j]>=target)
   if fill:ei=j;break
  if ei<0:k=np.searchsorted(dts,int(ts[pe])+1);continue
  entry=target;sl=entry-side*STOP*a;xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+HOLD,'left'));xp=float(C[xe]);xi=xe
  for j in range(ei+1,xe+1):
   if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;xi=j;break
   if ts[j]%300==0:
    q=np.searchsorted(ft,ts[j],'left')-1
    if q>=0 and np.isfinite(z[q]) and ((side<0 and z[q]<=-EXIT_Z) or (side>0 and z[q]>=EXIT_Z)):xp=float(C[j]);xi=j;break
  R=side*(xp-entry)/(STOP*a)-(cfg['cost']/10000.)*entry/(STOP*a);rows.append({'entry_ts':int(ts[ei]),'R':R});dc+=1;last=entry;la=a;k=np.searchsorted(dts,int(ts[xi])+1)
 return pd.DataFrame(rows),confirms,vetoes
def main():
 arr=prep();out={}
 for c in CANDS:
  d,cf,ve=sim(arr,c);dt=pd.to_datetime(d.entry_ts,unit='s',utc=True);mo={}
  for m in sorted(dt.dt.to_period('M').astype(str).unique()):mo[m]=stats(d.loc[dt.dt.to_period('M').astype(str)==m,'R'])
  out[c['id']]={'config':c,'all':stats(d.R),'fill_rate':float(len(d)/cf) if cf else 0.,'veto_rate':float(ve/cf) if cf else 0.,'monthly':mo}
 (OUT/'stress_2026_extension_veto.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
