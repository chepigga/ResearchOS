#!/usr/bin/env python3
# Reporting/robustness-only fix: same preregistered 7-calendar-day cluster bootstrap,
# with explicit epoch-seconds clock to avoid pandas datetime-resolution unit ambiguity.
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab027',HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

def bootstrap_diff_fixed(d):
    q=d[d.signal_time<L.PRE_CUT].copy()
    q['acc']=pd.to_numeric(q.accept_bounded_net_atr,errors='coerce').fillna(0.0)
    q['imm']=pd.to_numeric(q.immediate_bounded_net_atr,errors='coerce').fillna(0.0)
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    g=q.groupby('cluster').agg(n=('flow_id','size'),acc_sum=('acc','sum'),imm_sum=('imm','sum')).reset_index(drop=True)
    rng=np.random.default_rng(L.SEED); vals=np.empty(L.BOOT_N,float); vals[:]=np.nan
    m=len(g)
    for j in range(L.BOOT_N):
        ix=rng.integers(0,m,size=m); z=g.iloc[ix]; den=float(z.n.sum())
        if den>0: vals[j]=float((z.acc_sum.sum()-z.imm_sum.sum())/den)
    vals=vals[np.isfinite(vals)]
    point=float(q.acc.mean()-q.imm.mean())
    return dict(n_clusters=int(m),draws=int(len(vals)),point_diff=point,
                ci_lo=float(np.quantile(vals,.025)) if len(vals) else np.nan,
                ci_hi=float(np.quantile(vals,.975)) if len(vals) else np.nan)

L.bootstrap_diff=bootstrap_diff_fixed
L.main()
