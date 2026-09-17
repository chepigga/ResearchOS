from pathlib import Path
import zipfile, json
import numpy as np
import pandas as pd
ROOT=Path('labs/CROWDFADE_V190_HISTORICAL_REPLAY_001'); DATA=ROOT/'secdata'; OUT=ROOT/'sec_diag_output'; OUT.mkdir(parents=True,exist_ok=True)

def extract(zname):
    zp=DATA/zname; out=DATA/(zp.stem+'_unz'); out.mkdir(parents=True,exist_ok=True)
    if not list(out.rglob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(out)
    return list(out.rglob('*.csv'))[0]

secf=extract('BTCUSDT_sec.csv.zip'); flowf=extract('BTCUSDT_flow_2021-01-2026-08.csv.zip')
s=pd.read_csv(secf,usecols=['ts','o','h','l','c'],dtype={'ts':'int64','o':'float32','h':'float32','l':'float32','c':'float32'})
s=s.sort_values('ts').drop_duplicates('ts',keep='last').reset_index(drop=True)
ts=s.ts.to_numpy(np.int64); H=s.h.to_numpy(float); L=s.l.to_numpy(float); C=s.c.to_numpy(float)
bucket=(ts//900)*900
starts=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1]; ends=np.r_[starts[1:],len(ts)]
bt=bucket[starts]; bh=np.maximum.reduceat(H,starts); bl=np.minimum.reduceat(L,starts); bc=C[ends-1]
pc=np.r_[bc[0],bc[:-1]]; tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); atr_available=bt+900
f=pd.read_csv(flowf,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
f=f[f.sum_open_interest>0].copy(); f['time']=pd.to_datetime(f.create_time,utc=True,errors='coerce'); f=f.dropna(subset=['time']).sort_values('time').drop_duplicates('time',keep='last')
# IMPORTANT diagnostic: use .view('int64') and compare to astype route
ft_view=f.time.array.asi8//10**9
ft_ast=(f.time.astype('int64')//10**9).to_numpy(np.int64)
r=f.count_long_short_ratio.to_numpy(float); rr=pd.Series(r)
m=rr.rolling(72,min_periods=72).mean(); sd=rr.rolling(72,min_periods=72).std(ddof=0); fz=((rr-m)/sd.replace(0,np.nan)).to_numpy()
dts=np.arange(((ts[0]+299)//300)*300,ts[-1]+1,300,dtype=np.int64)
di=np.searchsorted(ts,dts,'left'); ok=(di<len(ts)) & (ts[np.minimum(di,len(ts)-1)]==dts); dts2=dts[ok]; di2=di[ok]
fi=np.searchsorted(ft_view,dts2,'left')-1; ai=np.searchsorted(atr_available,dts2,'right')-1
valid_idx=np.maximum(fi,0); valid_ai=np.maximum(ai,0)
good=(fi>=0)&(ai>=0)&np.isfinite(fz[valid_idx])&np.isfinite(atr[valid_ai])
zgood=fz[fi[good]] if good.any() else np.array([])
res={
 'sec_file':str(secf),'flow_file':str(flowf),
 'sec_rows':int(len(s)),'sec_min_ts':int(ts[0]),'sec_max_ts':int(ts[-1]),
 'sec_min_utc':str(pd.to_datetime(ts[0],unit='s',utc=True)),'sec_max_utc':str(pd.to_datetime(ts[-1],unit='s',utc=True)),
 'flow_rows':int(len(f)),'flow_min_utc':str(f.time.min()),'flow_max_utc':str(f.time.max()),
 'flow_min_ts':int(ft_view[0]),'flow_max_ts':int(ft_view[-1]),'ft_equal':bool(np.array_equal(ft_view,ft_ast)),
 'finite_z_total':int(np.isfinite(fz).sum()),'z_min':float(np.nanmin(fz)),'z_max':float(np.nanmax(fz)),
 'm15_bars':int(len(bt)),'finite_atr':int(np.isfinite(atr).sum()),'atr_min':float(np.nanmin(atr)),'atr_max':float(np.nanmax(atr)),
 'decision_grid':int(len(dts)),'exact_m5_seconds':int(len(dts2)),'good_decisions':int(good.sum()),
 'z_abs_ge1_good':int((np.abs(zgood)>=1).sum()) if len(zgood) else 0,
 'zgood_min':float(np.nanmin(zgood)) if len(zgood) else None,'zgood_max':float(np.nanmax(zgood)) if len(zgood) else None,
 'sample_good':[]
}
for idx in np.flatnonzero(good)[:10]:
    res['sample_good'].append({'t':str(pd.to_datetime(dts2[idx],unit='s',utc=True)),'z':float(fz[fi[idx]]),'atr':float(atr[ai[idx]])})
(OUT/'diag.json').write_text(json.dumps(res,indent=2))
print(json.dumps(res,indent=2))
