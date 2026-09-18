from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
ROOT=Path('labs/CROWDFADE_DIRECTIONAL_EDGE_MFE_MAE_LAB_009');DATA=ROOT/'data';OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.5;CONF=.25;IMP=.60;CONF_TTL=3600;WAIT=1200
HORIZONS=[3600,10800,21600,43200,86400]
def extract(zname,out):
 d=DATA/out;d.mkdir(parents=True,exist_ok=True)
 if not list(d.rglob('*.csv')):
  with zipfile.ZipFile(DATA/zname) as z:z.extractall(d)
 return list(d.rglob('*.csv'))[0]
def prep():
 sf=extract('BTCUSDT_sec.csv.zip','sec');ff=extract('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
 s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
 ts=s.ts.to_numpy(np.int64);O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)
 bucket=(ts//900)*900;st=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1];en=np.r_[st[1:],len(ts)];bt=bucket[st];bh=np.maximum.reduceat(H,st);bl=np.minimum.reduceat(L,st);bc=C[en-1];pc=np.r_[bc[0],bc[:-1]];tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)));atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy();atr_av=bt+900
 f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio']);f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy();f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce');f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t');ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64);r=pd.to_numeric(f.count_long_short_ratio,errors='coerce');mu=r.rolling(72,min_periods=72).mean();sd=r.rolling(72,min_periods=72).std(ddof=0);z=((r-mu)/sd.replace(0,np.nan)).to_numpy()
 dt=np.arange(((ts[0]+299)//300)*300,ts[-1]+1,300,dtype=np.int64);di=np.searchsorted(ts,dt);ok=(di<len(ts))&(ts[np.minimum(di,len(ts)-1)]==dt);dt=dt[ok];di=di[ok];fi=np.searchsorted(ft,dt,'left')-1;ai=np.searchsorted(atr_av,dt,'right')-1;g=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
 return ts,O,H,L,C,dt[g],di[g],z[fi[g]],atr[ai[g]]
def exc(ts,H,L,entry_idx,entry,side,atr,seconds):
 end=min(len(ts),np.searchsorted(ts,int(ts[entry_idx])+seconds,'right'))
 hh=H[entry_idx:end];ll=L[entry_idx:end]
 fav=((hh-entry)/atr) if side>0 else ((entry-ll)/atr)
 adv=((entry-ll)/atr) if side>0 else ((hh-entry)/atr)
 imf=int(np.argmax(fav));ima=int(np.argmax(adv))
 return float(np.max(fav)),float(np.max(adv)),int(ts[entry_idx+imf]-ts[entry_idx]),int(ts[entry_idx+ima]-ts[entry_idx])
def stats(x):
 a=np.asarray(x,float)
 if not len(a): return {}
 qs=np.quantile(a,[.1,.25,.5,.75,.9,.95])
 return {'N':len(a),'mean':float(a.mean()),'p10':float(qs[0]),'p25':float(qs[1]),'median':float(qs[2]),'p75':float(qs[3]),'p90':float(qs[4]),'p95':float(qs[5])}
def main():
 ts,O,H,L,C,dts,di,zd,ad=prep();rows=[];k=0
 while k<len(dts):
  z=float(zd[k]);side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
  if side==0:k+=1;continue
  a=float(ad[k]);sig=float(O[di[k]]);level=sig+side*CONF*a;cs=int(di[k])+1;ce=min(len(ts)-1,np.searchsorted(ts,int(dts[k])+CONF_TTL,'left'));m=(H[cs:ce+1]>=level) if side>0 else (L[cs:ce+1]<=level);hh=np.flatnonzero(m)
  if not len(hh):k+=1;continue
  ci=cs+int(hh[0]);target=level-side*IMP*a;ps=ci+1;pe=min(len(ts)-1,np.searchsorted(ts,int(ts[ci])+WAIT,'left'));m=(L[ps:pe+1]<=target) if side>0 else (H[ps:pe+1]>=target);ff=np.flatnonzero(m)
  if not len(ff):k=np.searchsorted(dts,int(ts[pe])+1);continue
  ei=ps+int(ff[0]);entry=target
  rec={'signal_ts':int(dts[k]),'confirm_ts':int(ts[ci]),'entry_ts':int(ts[ei]),'side':int(side),'atr':a,'entry':entry,'signal_to_confirm_s':int(ts[ci]-dts[k]),'confirm_to_entry_s':int(ts[ei]-ts[ci])}
  for sec in HORIZONS:
   mfe,mae,tmfe,tmae=exc(ts,H,L,ei,entry,side,a,sec);tag=f'{sec//3600}h'
   rec[f'mfe_{tag}']=mfe;rec[f'mae_{tag}']=mae;rec[f'tmfe_{tag}']=tmfe;rec[f'tmae_{tag}']=tmae
  # vectorized path ordering thresholds over 12h
  end=min(len(ts),np.searchsorted(ts,int(ts[ei])+43200,'right'))
  hh=H[ei:end]; ll=L[ei:end]
  fav_arr=((hh-entry)/a) if side>0 else ((entry-ll)/a)
  adv_arr=((entry-ll)/a) if side>0 else ((hh-entry)/a)
  adv_hits=np.flatnonzero(adv_arr>=1.0); adv_first=int(adv_hits[0]) if len(adv_hits) else -1
  for th in [.25,.5,1.0,1.5,2.0,3.0]:
   fh=np.flatnonzero(fav_arr>=th); fav_first=int(fh[0]) if len(fh) else -1
   rec[f'fav{th}_before_mae1']=1 if fav_first>=0 and (adv_first<0 or fav_first<adv_first) else 0
  rows.append(rec);k=np.searchsorted(dts,int(ts[ei])+1)
 d=pd.DataFrame(rows);d.to_csv(OUT/'events.csv',index=False)
 out={'config':{'z':ZTH,'confirm':CONF,'retrace_entry':IMP,'confirm_ttl_h':1,'entry_wait_min':20},'N':len(d),'overall':{},'by_side':{},'monthly':{}}
 for tag in ['1h','3h','6h','12h','24h']:
  out['overall'][tag]={'MFE':stats(d[f'mfe_{tag}']),'MAE':stats(d[f'mae_{tag}']),'time_to_MFE_min':stats(d[f'tmfe_{tag}']/60)}
 for th in [.25,.5,1.0,1.5,2.0,3.0]:out['overall'][f'P_fav{th}_before_MAE1']=float(d[f'fav{th}_before_mae1'].mean())
 for side,name in [(1,'LONG'),(-1,'SHORT')]:
  q=d[d.side==side];out['by_side'][name]={}
  for tag in ['3h','6h','12h','24h']:out['by_side'][name][tag]={'MFE':stats(q[f'mfe_{tag}']),'MAE':stats(q[f'mae_{tag}'])}
 dt=pd.to_datetime(d.entry_ts,unit='s',utc=True);months=dt.dt.to_period('M').astype(str)
 for m in sorted(months.unique()):
  q=d[months==m];out['monthly'][m]={'N':len(q),'MFE12':stats(q.mfe_12h),'MAE12':stats(q.mae_12h)}
 (OUT/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
