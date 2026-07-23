#!/usr/bin/env python3

import math
import numpy as np

def maxdd(r):
    r=np.asarray(r,float)
    eq=np.cumsum(r)
    peak=np.maximum.accumulate(np.r_[0.0,eq])
    return float(np.max(peak[1:]-eq))

def paired_moving_block(base_net,base_gross,candidate_net,candidate_gross,*,block=20,n_iter=5000,seed=2026072404):
    # Shared indices preserve pairing between E0 and the candidate.
    n=len(base_net); n_blocks=math.ceil(n/block)
    rng=np.random.default_rng(seed)
    rows=[]
    for i in range(n_iter):
        starts=rng.integers(0,n-block+1,size=n_blocks)
        idx=np.concatenate([np.arange(s,s+block) for s in starts])[:n]
        rows.append((i,float(np.asarray(base_net)[idx].sum()),float(np.asarray(candidate_net)[idx].sum()),
                     maxdd(np.asarray(base_gross)[idx]),maxdd(np.asarray(candidate_gross)[idx])))
    return rows
