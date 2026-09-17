import json
from pathlib import Path
import numpy as np
import pandas as pd
import run_2026_stress as s
OUT=Path(__file__).resolve().parent/'output'
LONG={'confirm':.65,'ttl':6,'mode':'pb050','stop':1.0,'hold':12}
SHORT={'confirm':.50,'ttl':1,'mode':'pb050','stop':1.0,'hold':12}

def sim_router(arr,cost_bps):
    ts,O,H,L,C,ft,z,dts,di,zdec,adec=arr;rows=[];k=0;last_entry=None;last_atr=None;day=-1;daily=0
    while k<len(dts):
        t=int(dts[k]);d=t//86400
        if d!=day:day=d;daily=0
        if daily>=3:k+=1;continue
        zz=float(zdec[k]);side=-1 if zz>=2.5 else (1 if zz<=-2.5 else 0)
        if side==0:k+=1;continue
        cfg=LONG if side>0 else SHORT
        if last_entry is not None and abs(float(O[di[k]])-last_entry)<last_atr:k+=1;continue
        a=float(adec[k]);sig=float(O[di[k]]);level=sig+side*cfg['confirm']*a;end=min(len(ts),int(np.searchsorted(ts,t+cfg['ttl']*3600,'left')));st=int(di[k])+1;mask=(H[st:end]>=level) if side>0 else (L[st:end]<=level);hit=np.flatnonzero(mask)
        if not len(hit):k+=1;continue
        ci=st+int(hit[0]);target=level-side*.5*a;pe=min(len(ts),int(np.searchsorted(ts,int(ts[ci])+3600,'left')));mask=(L[ci:pe]<=target) if side>0 else (H[ci:pe]>=target);hh=np.flatnonzero(mask)
        if not len(hh):k=np.searchsorted(dts,int(ts[ci])+1);continue
        ei=ci+int(hh[0]);entry=target;sl=entry-side*cfg['stop']*a;endx=min(len(ts)-1,int(np.searchsorted(ts,int(ts[ei])+cfg['hold']*3600,'left')));xp=float(C[endx]);xi=endx;reason='time'
        for j in range(ei+1,endx+1):
            if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;xi=j;reason='stop';break
            if ts[j]%300==0:
                q=np.searchsorted(ft,ts[j],'left')-1
                if q>=0 and np.isfinite(z[q]) and ((side<0 and z[q]<=-.75) or (side>0 and z[q]>=.75)):
                    xp=float(C[j]);xi=j;reason='zexit';break
        gross=side*(xp-entry)/(cfg['stop']*a);cost=(cost_bps/10000.)*entry/(cfg['stop']*a);rows.append({'entry_ts':int(ts[ei]),'side':'LONG' if side>0 else 'SHORT','gross_R':gross,'R':gross-cost,'reason':reason});daily+=1;last_entry=entry;last_atr=a;k=np.searchsorted(dts,int(ts[xi])+1)
    return pd.DataFrame(rows)

def main():
    arr=s.prep();out={'LONG':LONG,'SHORT':SHORT,'costs':{}}
    for bps in [0,1,2,3,4,5]:
        d=sim_router(arr,bps);allstat=s.stats(d.R.values);bys={q:s.stats(d.loc[d.side==q,'R'].values) for q in ['LONG','SHORT']};dt=pd.to_datetime(d.entry_ts,unit='s',utc=True);months={m:s.stats(d.loc[dt.dt.to_period('M').astype(str)==m,'R'].values) for m in sorted(dt.dt.to_period('M').astype(str).unique())};out['costs'][str(bps)]={'all':allstat,'by_side':bys,'months':months};print(bps,allstat,bys)
    (OUT/'stress_2026_side_router.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
