#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, io, zipfile
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab022_v2',HERE/'run_lab_v2.py')
V2=importlib.util.module_from_spec(spec); spec.loader.exec_module(V2)
L=V2.L


def robust_parse_metrics_zip(content,label):
    z=zipfile.ZipFile(io.BytesIO(content))
    names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:
        return pd.DataFrame()
    d=pd.read_csv(z.open(names[0]))
    d.columns=[str(c).strip() for c in d.columns]
    tc='create_time' if 'create_time' in d.columns else ('timestamp' if 'timestamp' in d.columns else None)
    rc='count_long_short_ratio' if 'count_long_short_ratio' in d.columns else None
    if tc is None or rc is None:
        raise RuntimeError(f'Unexpected metrics schema {label}: {list(d.columns)}')
    d=d[[tc,rc]].rename(columns={tc:'time',rc:'ratio'})
    if pd.api.types.is_numeric_dtype(d['time']):
        vals=pd.to_numeric(d['time'],errors='coerce')
        med=vals.dropna().abs().median() if vals.notna().any() else float('nan')
        unit='ms' if pd.notna(med) and med>1e11 else 's'
        d['time']=pd.to_datetime(vals,unit=unit,errors='coerce',utc=True)
    else:
        d['time']=pd.to_datetime(d['time'].astype(str).str.strip(),errors='coerce',utc=True)
    d['ratio']=pd.to_numeric(d['ratio'],errors='coerce')
    return d.dropna(subset=['time','ratio'])

L.parse_metrics_zip=robust_parse_metrics_zip
V2.L.parse_metrics_zip=robust_parse_metrics_zip
L.download_metrics=V2.download_metrics_daily

if __name__=='__main__':
    L.main()
