#!/usr/bin/env python3
# Computational-only optimization of the same preregistered 7-day cluster bootstrap.
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab026',HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

def bootstrap_diff_fast(d,pre_cut):
    q=d[(d.signal_time<pre_cut)&(d.state.isin(['ACCEPT_FIRST','ADVERSE_FIRST']))].copy()
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    clusters=np.sort(q.cluster.unique())
    # Aggregate exact sufficient statistics by 7d cluster/state.
    arr=[]
    for c in clusters:
        z=q[q.cluster==c]
        a=z.loc[z.state=='ACCEPT_FIRST','residual12_atr'].dropna().to_numpy(float)
        b=z.loc[z.state=='ADVERSE_FIRST','residual12_atr'].dropna().to_numpy(float)
        arr.append((a.sum(),len(a),b.sum(),len(b)))
    arr=np.asarray(arr,float)
    rng=np.random.default_rng(L.SEED); vals=np.empty(L.BOOT_N,float)
    vals[:]=np.nan
    ncl=len(clusters)
    for j in range(L.BOOT_N):
        idx=rng.integers(0,ncl,size=ncl)
        s=arr[idx].sum(axis=0)
        if s[1]>0 and s[3]>0: vals[j]=s[0]/s[1]-s[2]/s[3]
    vals=vals[np.isfinite(vals)]
    acc=q[q.state=='ACCEPT_FIRST'].residual12_atr.dropna().to_numpy(float)
    adv=q[q.state=='ADVERSE_FIRST'].residual12_atr.dropna().to_numpy(float)
    point=float(acc.mean()-adv.mean()) if len(acc) and len(adv) else np.nan
    return dict(n_clusters=int(ncl),draws=int(len(vals)),point_diff=point,
                ci_lo=float(np.quantile(vals,.025)) if len(vals) else np.nan,
                ci_hi=float(np.quantile(vals,.975)) if len(vals) else np.nan)

L.bootstrap_diff=bootstrap_diff_fast
L.main()
