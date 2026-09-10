#!/usr/bin/env python3
"""Diagnostic only: localize M5 REST-vs-frozen mismatches. Does not change LAB064 gates."""
import importlib.util
from pathlib import Path
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'output'; OUT.mkdir(parents=True,exist_ok=True)
base_path=ROOT/'research'/'btc_unified_lifecycle'/'u02c2_v283_market_clock_conditional.py'
spec=importlib.util.spec_from_file_location('base064diag',base_path); base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
frozen=base.load_zip(str(ROOT/'btc_5m.zip'))[['time','open','high','low','close']]
start=pd.Timestamp('2026-08-08 00:00:00'); end=pd.Timestamp('2026-08-10 23:59:59')
rows=[]; cur=int(start.tz_localize('UTC').timestamp()*1000); endms=int(end.tz_localize('UTC').timestamp()*1000)
while cur<=endms:
    r=requests.get('https://www.binance.com/fapi/v1/klines',params={'symbol':'BTCUSDT','interval':'5m','startTime':cur,'endTime':endms,'limit':1000},timeout=30); r.raise_for_status(); d=r.json()
    if not d: break
    rows += d; cur=int(d[-1][0])+300000
    if len(d)<1000: break
z=pd.DataFrame(rows,columns=['ms','open','high','low','close','volume','cms','qv','n','tb','tq','ig'])
z['time']=pd.to_datetime(z.ms.astype('int64'),unit='ms',utc=True).dt.tz_localize(None)
for c in ['open','high','low','close']: z[c]=pd.to_numeric(z[c])
z=z[['time','open','high','low','close']]
m=frozen.merge(z,on='time',suffixes=('_frozen','_rest'))
mask=pd.Series(False,index=m.index)
for c in ['open','high','low','close']: mask |= m[f'{c}_frozen'].ne(m[f'{c}_rest'])
mm=m[mask].copy()
for c in ['open','high','low','close']: mm[f'{c}_diff']=mm[f'{c}_rest']-mm[f'{c}_frozen']
mm.to_csv(OUT/'m5_parity_mismatches.csv',index=False)
print(mm.to_string(index=False))
