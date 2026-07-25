#!/usr/bin/env python3
"""Optimized frozen replay for TZ-FT-DEEP-001.

This is a computational optimization of FT_DEEP_Oracle_v001.py. Trading rules,
parameter defaults, state ordering, reject ordering, execution conventions and
costs are inherited unchanged. Only level construction/selection is replaced by
an equivalent numba-compiled implementation so long M5 histories are practical.
"""
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit

BASE_PATH = Path(__file__).with_name('FT_DEEP_Oracle_v001.py')
spec = importlib.util.spec_from_file_location('ftdeep_base', BASE_PATH)
base = importlib.util.module_from_spec(spec)
sys.modules['ftdeep_base']=base
assert spec.loader is not None
spec.loader.exec_module(base)

TYPE_NAMES = {
    1:'PDH', 2:'PDL', 3:'ASIA_H', 4:'ASIA_L', 5:'DAY_PRE_H', 6:'DAY_PRE_L',
    7:'DAY_H', 8:'DAY_L', 9:'H1_PH', 10:'H1_PL', 11:'M5_PH', 12:'M5_PL'
}

@njit(cache=True)
def pivot_flags(high, low, lr):
    n=len(high); ph=np.zeros(n,np.uint8); pl=np.zeros(n,np.uint8)
    for i in range(lr,n-lr):
        hi=high[i]; lo=low[i]; okh=True; okl=True
        for k in range(1,lr+1):
            if high[i-k]>=hi or high[i+k]>=hi: okh=False
            if low[i-k]<=lo or low[i+k]<=lo: okl=False
        if okh: ph[i]=1
        if okl: pl[i]=1
    return ph,pl

@njit(cache=True)
def count_touches(price, typ, i, high, low, tmin, atr_i):
    tol=max(base.MIN_TOUCH_PTS*base.POINT, atr_i*base.TOUCH_TOL_ATR)
    start=max(0,i-base.M5_LOOKBACK+1)
    clusters=0; last_time=-10**18
    highside=typ in (1,3,7,9,11)
    for j in range(start,i+1):
        value=high[j] if highside else low[j]
        if abs(value-price)<=tol:
            if last_time < -10**17 or abs((tmin[j]-last_time)//5)>=base.CLUSTER_GAP:
                clusters+=1
            last_time=tmin[j]
    return clusters

@njit(cache=True)
def best_level(i,module,high,low,atr,tmin,etmin,d1_idx,d1_high,d1_low,
               h1_idx,h1_high,h1_low,h1_ph,h1_pl,m5_ph,m5_pl):
    prices=np.empty(64,np.float64); types=np.empty(64,np.int16)
    touches=np.empty(64,np.int16); valid=np.empty(64,np.uint8)
    n=0; a=atr[i]; dedup=a*.05 if a>0 else 5*base.POINT

    di=d1_idx[i]
    raw_prices=np.empty(64,np.float64); raw_types=np.empty(64,np.int16); rn=0
    if di>=0:
        raw_prices[rn]=d1_high[di];raw_types[rn]=1;rn+=1
        raw_prices[rn]=d1_low[di];raw_types[rn]=2;rn+=1

    day=etmin[i]//1440
    asia_h=0.0;asia_l=1e100;day_h=0.0;day_l=1e100
    j=i
    while j>=0 and tmin[j]//1440==day:
        if high[j]>day_h:day_h=high[j]
        if low[j]<day_l:day_l=low[j]
        uh=((tmin[j]//60)-base.SERVER_UTC_OFFSET)%24
        if base.ASIA_START<=uh<base.ASIA_END:
            if high[j]>asia_h:asia_h=high[j]
            if low[j]<asia_l:asia_l=low[j]
        j-=1
    if asia_h>0:raw_prices[rn]=asia_h;raw_types[rn]=3;rn+=1
    if asia_l<1e99:raw_prices[rn]=asia_l;raw_types[rn]=4;rn+=1
    pre_h=0.0;pre_l=1e100;j=i-1
    while j>=0 and tmin[j]//1440==day:
        if high[j]>pre_h:pre_h=high[j]
        if low[j]<pre_l:pre_l=low[j]
        j-=1
    if pre_h>0:raw_prices[rn]=pre_h;raw_types[rn]=5;rn+=1
    if pre_l<1e99:raw_prices[rn]=pre_l;raw_types[rn]=6;rn+=1
    if day_h>0:raw_prices[rn]=day_h;raw_types[rn]=7;rn+=1
    if day_l<1e99:raw_prices[rn]=day_l;raw_types[rn]=8;rn+=1

    hj=h1_idx[i];hc=0;lc=0;p=hj-base.H1_LR
    while p>=base.H1_LR and (hc<base.MAX_H1_PIV or lc<base.MAX_H1_PIV):
        if hc<base.MAX_H1_PIV and h1_ph[p]==1:
            raw_prices[rn]=h1_high[p];raw_types[rn]=9;rn+=1;hc+=1
        if lc<base.MAX_H1_PIV and h1_pl[p]==1:
            raw_prices[rn]=h1_low[p];raw_types[rn]=10;rn+=1;lc+=1
        p-=1

    hc=0;lc=0;p=i-base.M5_LR;oldest=max(base.M5_LR,i-(base.M5_LOOKBACK+base.M5_LR)+2)
    while p>=oldest and (hc<base.MAX_M5_PIV or lc<base.MAX_M5_PIV):
        if hc<base.MAX_M5_PIV and m5_ph[p]==1:
            raw_prices[rn]=high[p];raw_types[rn]=11;rn+=1;hc+=1
        if lc<base.MAX_M5_PIV and m5_pl[p]==1:
            raw_prices[rn]=low[p];raw_types[rn]=12;rn+=1;lc+=1
        p-=1

    for r in range(rn):
        price=raw_prices[r];typ=raw_types[r]
        if not (price>0 and price<=999999) or n>=64:continue
        duplicate=False
        for q in range(n):
            if abs(prices[q]-price)<dedup:
                duplicate=True;break
        if duplicate:continue
        prices[n]=price;types[n]=typ;touches[n]=0;valid[n]=0;n+=1

    for q in range(n):
        tc=count_touches(prices[q],types[q],i,high,low,tmin,a)
        touches[q]=tc;typ=types[q]
        valid[q]=1 if typ in (1,2,3,4,11,12) or tc>=base.TOUCH_MAJOR else 0

    min_sweep=max(base.MIN_SWEEP_PTS*base.POINT,a*base.MIN_SWEEP_ATR)
    current_low=low[i];best=-1
    if module==0:
        best_tier=-1;best_touches=0
        for q in range(n):
            if valid[q]==0:continue
            typ=types[q]
            if typ not in (2,4,8,6,10,12):continue
            if current_low>prices[q]-min_sweep:continue
            tier=3 if typ in (2,4) else (2 if typ in (10,6) else 1)
            if tier>best_tier or (tier==best_tier and touches[q]>best_touches):
                best_tier=tier;best_touches=touches[q];best=q
    else:
        best_touches=0
        for q in range(n):
            if valid[q]==0:continue
            typ=types[q]
            if typ not in (2,4,8,10):continue
            if current_low<=prices[q]-min_sweep and touches[q]>best_touches:
                best_touches=touches[q];best=q
    if best<0:return np.nan,0,0
    return prices[best],int(types[best]),int(touches[best])

class FastOracle(base.Oracle):
    def __init__(self,m5):
        super().__init__(m5)
        self._high=self.m.high.to_numpy(float);self._low=self.m.low.to_numpy(float)
        self._atr=self.m.atr14.to_numpy(float)
        self._tmin=(self.m.time.astype('int64')//(60*10**9)).to_numpy(np.int64)
        self._etmin=self._tmin+5
        eval_times=(self.m.time+pd.Timedelta(minutes=5)).to_numpy('datetime64[ns]')
        self._d1_idx=np.searchsorted(self.d1.end.to_numpy('datetime64[ns]'),eval_times,side='right')-1
        self._h1_idx=np.searchsorted(self.h1.end.to_numpy('datetime64[ns]'),eval_times,side='right')-1
        self._m5_ph,self._m5_pl=pivot_flags(self._high,self._low,base.M5_LR)
        self._h1_ph,self._h1_pl=pivot_flags(self.h1.high.to_numpy(float),self.h1.low.to_numpy(float),base.H1_LR)
    def levels(self,i):
        return []
    def select(self,levels,i,module):
        module_id=0 if module=='NYBUY' else 1
        price,typ,touches=best_level(i,module_id,self._high,self._low,self._atr,self._tmin,self._etmin,
                                     self._d1_idx,self.d1.high.to_numpy(float),self.d1.low.to_numpy(float),
                                     self._h1_idx,self.h1.high.to_numpy(float),self.h1.low.to_numpy(float),
                                     self._h1_ph,self._h1_pl,self._m5_ph,self._m5_pl)
        if not np.isfinite(price):return None
        return base.Level(float(price),TYPE_NAMES[int(typ)],int(touches),True)

def read_input(path):
    first=Path(path).read_text(encoding='utf-8-sig',errors='replace').splitlines()[0]
    sep=';' if first.count(';')>first.count(',') else ','
    df=pd.read_csv(path,sep=sep)
    df['time']=pd.to_datetime(df['time'],format='%Y.%m.%d %H:%M')
    return df.sort_values('time').drop_duplicates('time').reset_index(drop=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('csv');ap.add_argument('--out',default='FT_DEEP')
    args=ap.parse_args();df=read_input(args.csv)
    oracle=FastOracle(df);tr,rej,htf,cand=oracle.simulate();out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    tr.to_csv(str(out)+'_trades.csv',index=False);rej.to_csv(str(out)+'_rejects.csv',index=False)
    htf.to_csv(str(out)+'_htf_blocks.csv',index=False);cand.to_csv(str(out)+'_candidates.csv',index=False)
    summary={'rows':len(df),'first':str(df.time.min()),'last':str(df.time.max()),
             'months':round((df.time.max()-df.time.min()).days/30.4375,2),'N':len(tr),
             'EV_net':float(tr.R_net.mean()) if len(tr) else None,'sumR':float(tr.R_net.sum()) if len(tr) else 0,
             'modules':tr.groupby('module').R_net.agg(['count','mean','sum']).reset_index().to_dict('records') if len(tr) else []}
    Path(str(out)+'_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
