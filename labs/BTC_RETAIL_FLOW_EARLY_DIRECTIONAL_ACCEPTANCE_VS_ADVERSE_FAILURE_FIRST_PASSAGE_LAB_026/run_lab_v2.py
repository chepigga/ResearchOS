#!/usr/bin/env python3
# Reporting/support-only parity fix: pandas datetime integer resolution made the original
# ns-based cluster division collapse all events into one cluster. Signal construction,
# first-passage thresholds, horizons, outcomes, gates, and seed are unchanged.
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab026',HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

def bootstrap_diff_fixed(d,pre_cut):
    q=d[(d.signal_time<pre_cut)&(d.state.isin(['ACCEPT_FIRST','ADVERSE_FIRST']))].copy()
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    clusters=q.cluster.unique(); rng=np.random.default_rng(L.SEED); vals=[]
    for _ in range(L.BOOT_N):
        pick=rng.choice(clusters,size=len(clusters),replace=True)
        parts=[q[q.cluster==c] for c in pick]
        z=pd.concat(parts,ignore_index=True) if parts else q.iloc[0:0]
        a=z.loc[z.state=='ACCEPT_FIRST','residual12_atr'].dropna()
        b=z.loc[z.state=='ADVERSE_FIRST','residual12_atr'].dropna()
        if len(a) and len(b): vals.append(float(a.mean()-b.mean()))
    acc=q[q.state=='ACCEPT_FIRST'].residual12_atr.dropna()
    adv=q[q.state=='ADVERSE_FIRST'].residual12_atr.dropna()
    point=float(acc.mean()-adv.mean()) if len(acc) and len(adv) else np.nan
    return dict(n_clusters=int(len(clusters)),draws=int(len(vals)),point_diff=point,
                ci_lo=float(np.quantile(vals,.025)) if vals else np.nan,
                ci_hi=float(np.quantile(vals,.975)) if vals else np.nan)

L.bootstrap_diff=bootstrap_diff_fixed
L.main()
