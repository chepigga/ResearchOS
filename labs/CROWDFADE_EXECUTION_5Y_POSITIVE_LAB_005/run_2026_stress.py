from pathlib import Path
import zipfile, json
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_EXECUTION_5Y_POSITIVE_LAB_005'); DATA=ROOT/'stress_data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.5; EXIT_Z=.75; COST_BPS=5.0; MAXDAY=3
CANDS=[
 {'id':'A_touch_ttl6_sl100','confirm':.25,'ttl':6,'mode':'touch','stop':1.0,'hold':12,'be':None},
 {'id':'B_touch_ttl6_sl175','confirm':.25,'ttl':6,'mode':'touch','stop':1.75,'hold':12,'be':None},
 {'id':'C_touch_ttl1_sl175','confirm':.25,'ttl':1,'mode':'touch','stop':1.75,'hold':12,'be':None},
 {'id':'D_pb050_ttl3_sl100_be05','confirm':.25,'ttl':3,'mode':'pb050','stop':1.0,'hold':12,'be':(.5,.15)},
 {'id':'E_pb050_ttl1_sl100_be05','confirm':.25,'ttl':1,'mode':'pb050','stop':1.0,'hold':12,'be':(.5,.15)},
]

def extract(zname,outname):
    z=DATA/zname; d=DATA/outname; d.mkdir(parents=True,exist_ok=True)
    if not list(d.rglob('*.csv')):
        with zipfile.ZipFile(z) as f:f.extractall(d)
    return list(d.rglob('*.csv'))[0]

def prep():
    sf=extract('BTCUSDT_sec.csv.zip','sec'); ff=extract('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
    s=pd.read_csv(sf,usecols=['ts','o','h','l','c']);s=s.sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
    ts=s.ts.to_numpy(np.int64); O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)
    # causal M15 ATR14 available only after completed M15 bar
    bucket=(ts//900)*900;starts=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1];ends=np.r_[starts[1:],len(ts)];bt=bucket[starts];bh=np.maximum.reduceat(H,starts);bl=np.minimum.reduceat(L,starts);bc=C[ends-1];pc=np.r_[bc[0],bc[:-1]];tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)));atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy();atr_av=bt+900
    f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio']);f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy();f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce');f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t');ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64);rr=pd.to_numeric(f.count_long_short_ratio,errors='coerce');mu=rr.rolling(72,min_periods=72).mean();sd=rr.rolling(72,min_periods=72).std(ddof=0);z=((rr-mu)/sd.replace(0,np.nan)).to_numpy()
    # decision every 5m, exact second exists
    dt=np.arange(((ts[0]+299)//300)*300,ts[-1]+1,300,dtype=np.int64);di=np.searchsorted(ts,dt);ok=(di<len(ts))&(ts[np.minimum(di,len(ts)-1)]==dt);dt=dt[ok];di=di[ok];fi=np.searchsorted(ft,dt,'left')-1;ai=np.searchsorted(atr_av,dt,'right')-1;good=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    return ts,O,H,L,C,ft,z,dt[good],di[good],z[fi[good]],atr[ai[good]]

def stats(rs):
    a=np.asarray(rs,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max());p=a[a>0].sum();n=abs(a[a<0].sum())
    return {'N':len(a),'WR':float((a>0).mean()),'EV':float(a.mean()),'SumR':float(a.sum()),'PF':float(p/n) if n else 99.0,'MaxDD':dd,'R_DD':float(a.sum()/dd) if dd else 99.0}

def sim(arr,cfg):
    ts,O,H,L,C,ft,z,dts,di,zdec,adec=arr;rows=[];k=0;last_entry=None;last_atr=None;day=-1;daily=0
    while k<len(dts):
        t=int(dts[k]);d=t//86400
        if d!=day:day=d;daily=0
        if daily>=MAXDAY:k+=1;continue
        zz=float(zdec[k]);side=-1 if zz>=ZTH else (1 if zz<=-ZTH else 0)
        if side==0:k+=1;continue
        if last_entry is not None and abs(float(O[di[k]])-last_entry)<last_atr:k+=1;continue
        a=float(adec[k]);sig=float(O[di[k]]);level=sig+side*cfg['confirm']*a;end=min(len(ts),int(np.searchsorted(ts,t+cfg['ttl']*3600,'left')));st=int(di[k])+1;mask=(H[st:end]>=level) if side>0 else (L[st:end]<=level);hit=np.flatnonzero(mask)
        if not len(hit):k+=1;continue
        ci=st+int(hit[0]);ei=ci;entry=level
        if cfg['mode']=='pb050':
            target=level-side*.5*a;pe=min(len(ts),int(np.searchsorted(ts,ts[ci]+3600,'left')));mask=(L[ci:pe]<=target) if side>0 else (H[ci:pe]>=target);hh=np.flatnonzero(mask)
            if not len(hh):k=np.searchsorted(dts,int(ts[ci])+1);continue
            ei=ci+int(hh[0]);entry=target
        sl=entry-side*cfg['stop']*a;endx=min(len(ts)-1,int(np.searchsorted(ts,int(ts[ei])+cfg['hold']*3600,'left')));xp=float(C[endx]);xi=endx;peak=entry;reason='time'
        for j in range(ei+1,endx+1):
            if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;xi=j;reason='stop';break
            px=float(C[j]);fav=side*(px-entry)
            if cfg['be'] and fav>=cfg['be'][0]*a:
                ns=entry+side*cfg['be'][1]*a
                if (side>0 and ns>sl) or (side<0 and ns<sl):sl=ns
            if ts[j]%300==0:
                q=np.searchsorted(ft,ts[j],'left')-1
                if q>=0 and np.isfinite(z[q]) and ((side<0 and z[q]<=-EXIT_Z) or (side>0 and z[q]>=EXIT_Z)):
                    xp=px;xi=j;reason='zexit';break
        gross=side*(xp-entry)/(cfg['stop']*a);cost=(COST_BPS/10000)*entry/(cfg['stop']*a);R=gross-cost;rows.append({'entry_ts':int(ts[ei]),'R':R,'reason':reason});daily+=1;last_entry=entry;last_atr=a;k=np.searchsorted(dts,int(ts[xi])+1)
    return pd.DataFrame(rows)

def main():
    arr=prep();out={}
    for c in CANDS:
        d=sim(arr,c);allm=stats(d.R.values);monthly={}
        dt=pd.to_datetime(d.entry_ts,unit='s',utc=True)
        for m in sorted(dt.dt.to_period('M').astype(str).unique()):monthly[m]=stats(d.loc[dt.dt.to_period('M').astype(str)==m,'R'].values)
        out[c['id']]={'config':c,'all':allm,'monthly':monthly};print(c['id'],allm)
    (OUT/'stress_2026_seconds.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
