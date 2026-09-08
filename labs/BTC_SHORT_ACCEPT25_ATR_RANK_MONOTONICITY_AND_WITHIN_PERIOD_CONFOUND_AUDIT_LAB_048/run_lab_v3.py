#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab048_base',HERE/'run_lab.py')
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

# Plumbing-only JSON fix.
_orig_dumps=base.json.dumps
def _safe_dumps(obj,*args,**kwargs):
    def _default(o):
        if isinstance(o,np.bool_): return bool(o)
        if isinstance(o,np.integer): return int(o)
        if isinstance(o,np.floating): return float(o)
        raise TypeError(f'Object of type {o.__class__.__name__} is not JSON serializable')
    kwargs.setdefault('default',_default)
    return _orig_dumps(obj,*args,**kwargs)
base.json.dumps=_safe_dumps

# Computational-only acceleration: identical 7d cluster bootstrap using
# per-cluster X'X and X'y sufficient statistics rather than pandas concat.
def _design(df):
    z=df[['atr_rank_90d','net_r_5bps','period']].dropna().copy()
    X=[np.ones(len(z)),z.atr_rank_90d.to_numpy(float)]
    for p in base.PERIODS[1:]:
        X.append((z.period==p).astype(float).to_numpy())
    return z,np.column_stack(X),z.net_r_5bps.to_numpy(float)

def _fast_fe_boot(d):
    z=d.copy(); z['cluster']=base.cluster_id(z.regime_time)
    _,X,y=_design(z)
    point=float(np.linalg.lstsq(X,y,rcond=None)[0][1])
    stats=[]
    for _,g in z.groupby('cluster'):
        _,Xg,yg=_design(g)
        stats.append((Xg.T@Xg, Xg.T@yg))
    sxx=np.stack([s[0] for s in stats]); sxy=np.stack([s[1] for s in stats])
    m=len(stats); rng=np.random.default_rng(base.SEED+48); vals=[]
    for _ in range(base.BOOT_N):
        ids=rng.integers(0,m,size=m)
        counts=np.bincount(ids,minlength=m).astype(float)
        A=np.tensordot(counts,sxx,axes=(0,0)); b=np.tensordot(counts,sxy,axes=(0,0))
        beta=np.linalg.pinv(A)@b
        vals.append(float(beta[1]))
    vals=np.asarray(vals,float)
    return dict(point=point,ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),clusters=m,draws=len(vals))

base.fe_boot=_fast_fe_boot
base.main()
