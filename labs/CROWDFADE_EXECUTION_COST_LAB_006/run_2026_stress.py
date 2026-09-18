from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
ROOT=Path('labs/CROWDFADE_EXECUTION_COST_LAB_006'); DATA=ROOT/'stress_data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.5; EXIT_Z=.75; CONFIRM=.25; CONFIRM_TTL=3600; STOP=1.75; HOLD=12*3600; MAXDAY=3; TAKER_BPS=5.
CANDS=[
 {'id':'M050_W15_C05','improve':.50,'wait':15*60,'maker':.5,'fallback':False},
 {'id':'M050_W15_C10','improve':.50,'wait':15*60,'maker':1.0,'fallback':False},
 {'id':'M050_W60_C05_FB5','improve':.50,'wait':60*60,'maker':.5,'fallback':True},
]
def extract(zname,out):
 d=DATA/out;d.mkdir(parents=True,exist_ok=True)
 if not list(d.rglob('*.csv')):
  with zipfile.ZipFile(DATA/zname) as z:z.extractall(d)
 return list(d.rglob('*.csv'))[0]
def prep():
 sf=extract('BTCUSDT_sec.csv.zip','sec');ff=extract('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
 s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts');ts=s.ts.to_numpy(np.int64);O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)
 bucket=(ts//900)*900;starts=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1];ends=np.r_[starts[1:],len(ts)];bt=bucket[starts];bh=np.maximum.reduceat(H,starts);bl=np.minimum.reduceat(L,starts);bc=C[ends-1];pc=np.r_[bc[0],bc[:-1]];tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)));atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy();atr_av=bt+900
 f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio']);f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy();f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce');f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t');ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64);rr=pd.to_numeric(f.count_long_short_ratio,errors='coerce');mu=rr.rolling(72,min_periods=72).mean();sd=rr.rolling(72,min_periods=72).std(ddof=0);zz=((rr-mu)/sd.replace(0,np.nan)).to_numpy()
 dt=np.arange(((ts[0]+299)//300)*300,ts[-1]+1,300,dtype=np.int64);di=np.searchsorted(ts,dt);ok=(di<len(ts))&(ts[np.minimum(di,len(ts)-1)]==dt);dt=dt[ok];di=di[ok];fi=np.searchsorted(ft,dt,'left')-1;ai=np.searchsorted(atr_av,dt,'right')-1;good=(fi>=0)&(ai>=0)&np.isfinite(zz[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
 return ts,O,H,L,C,ft,zz,dt[good],di[good],zz[fi[good]],atr[ai[good]]
def stats(a):
 a=np.asarray(a,float)
 if not len(a):return {'N':0}
 eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max());p=a[a>0].sum();n=abs(a[a<0].sum());return {'N':len(a),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),'PF':float(p/n) if n else 99.,'MaxDD':dd,'R_DD':float(a.sum()/dd) if dd else 99.}
def sim(arr,cfg):
 ts,O,H,L,C,ft,z,dts,di,zdec,adec=arr;rows=[];k=0;last_entry=None;last_atr=None;day=-1;daily=0
 while k<len(dts):
  t=int(dts[k]);d=t//86400
  if d!=day:day=d;daily=0
  if daily>=MAXDAY:k+=1;continue
  zz=float(zdec[k]);side=-1 if zz>=ZTH else (1 if zz<=-ZTH else 0)
  if side==0:k+=1;continue
  if last_entry is not None and abs(float(O[di[k]])-last_entry)<last_atr:k+=1;continue
  a=float(adec[k]);sig=float(O[di[k]]);level=sig+side*CONFIRM*a;st=int(di[k])+1;ce=min(len(ts),np.searchsorted(ts,t+CONFIRM_TTL,'left'));mask=(H[st:ce]>=level) if side>0 else (L[st:ce]<=level);hh=np.flatnonzero(mask)
  if not len(hh):k+=1;continue
  ci=st+int(hh[0]);target=level-side*cfg['improve']*a;ps=ci+1;pe=min(len(ts)-1,np.searchsorted(ts,int(ts[ci])+cfg['wait'],'left'));mask=(L[ps:pe+1]<=target) if side>0 else (H[ps:pe+1]>=target);ff=np.flatnonzero(mask);kind='maker'
  if len(ff):
   ei=ps+int(ff[0]);entry=target;cbps=cfg['maker']
  elif cfg['fallback']:
   ei=min(len(ts)-2,pe+1);entry=float(O[ei]);cbps=TAKER_BPS;kind='taker'
  else:
   k=np.searchsorted(dts,int(ts[pe])+1);continue
  sl=entry-side*STOP*a;exend=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+HOLD,'left'));xp=float(C[exend]);xi=exend
  for j in range(ei+1,exend+1):
   if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;xi=j;break
   if ts[j]%300==0:
    q=np.searchsorted(ft,ts[j],'left')-1
    if q>=0 and np.isfinite(z[q]) and ((side<0 and z[q]<=-EXIT_Z) or (side>0 and z[q]>=EXIT_Z)):xp=float(C[j]);xi=j;break
  R=side*(xp-entry)/(STOP*a)-(cbps/10000.)*entry/(STOP*a);rows.append({'entry_ts':int(ts[ei]),'R':R,'kind':kind,'cost_bps':cbps});daily+=1;last_entry=entry;last_atr=a;k=np.searchsorted(dts,int(ts[xi])+1)
 return pd.DataFrame(rows)
def main():
 arr=prep();out={}
 for cfg in CANDS:
  d=sim(arr,cfg);dt=pd.to_datetime(d.entry_ts,unit='s',utc=True);mons={}
  for m in sorted(dt.dt.to_period('M').astype(str).unique()):mons[m]=stats(d.loc[dt.dt.to_period('M').astype(str)==m,'R'])
  out[cfg['id']]={'config':cfg,'all':stats(d.R),'effective_cost_bps':float(d.cost_bps.mean()) if len(d) else None,'maker_share':float((d.kind=='maker').mean()) if len(d) else None,'monthly':mons}
 (OUT/'stress_2026_passive.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
