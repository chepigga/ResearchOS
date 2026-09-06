#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import pandas as pd
import requests

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab022_base',HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

START=pd.Timestamp('2020-10-01')
END=pd.Timestamp('2026-08-31')
BASE='https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT'

def one_day(ts):
    ds=ts.strftime('%Y-%m-%d'); fn=f'BTCUSDT-metrics-{ds}.zip'; url=f'{BASE}/{fn}'
    last=''
    for attempt in range(2):
        try:
            r=requests.get(url,timeout=15)
            if r.status_code==200:
                d=L.parse_metrics_zip(r.content,fn)
                return d,dict(date=ds,status=200,rows=len(d),note='daily')
            return None,dict(date=ds,status=r.status_code,rows=0,note='daily_missing')
        except Exception as e:
            last=str(e)
    return None,dict(date=ds,status='EXC',rows=0,note=last)

def download_metrics_daily():
    days=list(pd.date_range(START,END,freq='D'))
    parts=[]; manifest=[]
    with ThreadPoolExecutor(max_workers=16) as ex:
        fut={ex.submit(one_day,d):d for d in days}
        for f in as_completed(fut):
            d,m=f.result(); manifest.append(m)
            if d is not None and len(d):parts.append(d)
    man=pd.DataFrame(manifest).sort_values('date')
    man.to_csv(L.OUT/'metrics_download_manifest.csv',index=False)
    if not parts:
        raise RuntimeError('No Binance daily metrics archives loaded')
    d=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last')
    d=d.set_index('time')['ratio'].resample('15min',label='left',closed='left').last().ffill(limit=2).dropna().to_frame()
    d['delta_ls_12']=d.ratio-d.ratio.shift(12)
    return d

L.download_metrics=download_metrics_daily
if __name__=='__main__':
    L.main()
