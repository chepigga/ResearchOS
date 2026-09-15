#!/usr/bin/env python3
"""Computationally optimized runner for AUDIT_005.
Replaces only the day-cluster bootstrap implementation with the mathematically
equivalent sum/count resampling form. Research rules and random seed unchanged.
"""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
P=HERE/'gc_m1_buyer_breakout_incremental_orderflow_audit_005.py'
spec=importlib.util.spec_from_file_location('audit005',P)
m=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(m)

def fast_delta_bootstrap(z,col,n=10000):
    q=z.dropna(subset=[col]).copy()
    days=sorted(q.day.unique())
    if len(days)<2:
        return [None,None]
    # For each cluster/day retain candidate/complement sum and count. Resampling
    # these sufficient statistics is exactly equivalent to concatenating the
    # sampled daily DataFrames and recomputing the two pooled means.
    a_sum=[]; a_n=[]; c_sum=[]; c_n=[]
    for d in days:
        g=q[q.day==d]
        a=g[g.buyer_a][col].to_numpy(float)
        c=g[~g.buyer_a][col].to_numpy(float)
        a_sum.append(float(a.sum())); a_n.append(int(len(a)))
        c_sum.append(float(c.sum())); c_n.append(int(len(c)))
    a_sum=np.asarray(a_sum); a_n=np.asarray(a_n)
    c_sum=np.asarray(c_sum); c_n=np.asarray(c_n)
    rng=np.random.default_rng(m.SEED)
    k=len(days)
    picks=rng.integers(0,k,size=(n,k))
    AS=a_sum[picks].sum(axis=1); AN=a_n[picks].sum(axis=1)
    CS=c_sum[picks].sum(axis=1); CN=c_n[picks].sum(axis=1)
    ok=(AN>0)&(CN>0)
    if not ok.any():
        return [None,None]
    vals=AS[ok]/AN[ok]-CS[ok]/CN[ok]
    return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]

m.delta_bootstrap=fast_delta_bootstrap
m.main()
