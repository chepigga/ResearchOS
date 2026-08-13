#!/usr/bin/env python3
"""Compute-equivalent fast runner for SELL_CORE_001.
Only replaces cluster-bootstrap implementation; methodology, BOOT=20000 and seed stay frozen.
"""
import numpy as np
import pandas as pd
import sell_core_001_funding_q4_market_clock as m


def fast_cluster_boot_delta(g,seed):
    z=g[['clock_episode_id','q4','R','pct']].dropna().copy()
    ids=np.sort(z.clock_episode_id.unique())
    q=z[z.q4==1]; n=z[z.q4==0]
    if len(ids)<4 or len(q)<2 or len(n)<2:
        return {'delta_R':np.nan,'CI_R_lo':np.nan,'CI_R_hi':np.nan,'P_R_gt0':np.nan,
                'delta_pct':np.nan,'CI_pct_lo':np.nan,'CI_pct_hi':np.nan,'P_pct_gt0':np.nan}
    pos={eid:i for i,eid in enumerate(ids)}; A=np.zeros((len(ids),8),float)
    # qRsum,qN,nRsum,nN,qPsum,qPN,nPsum,nPN
    for r in z.itertuples(index=False):
        i=pos[r.clock_episode_id]
        if int(r.q4)==1:
            A[i,0]+=r.R; A[i,1]+=1; A[i,4]+=r.pct; A[i,5]+=1
        else:
            A[i,2]+=r.R; A[i,3]+=1; A[i,6]+=r.pct; A[i,7]+=1
    dR=float(q.R.mean()-n.R.mean()); dP=float(q.pct.mean()-n.pct.mean())
    rng=np.random.default_rng(seed); br=[]; bp=[]; batch=2000
    left=m.BOOT
    while left>0:
        b=min(batch,left); idx=rng.integers(0,len(ids),size=(b,len(ids))); S=A[idx].sum(axis=1)
        vr=(S[:,1]>0)&(S[:,3]>0); vp=(S[:,5]>0)&(S[:,7]>0)
        br.extend((S[vr,0]/S[vr,1]-S[vr,2]/S[vr,3]).tolist())
        bp.extend((S[vp,4]/S[vp,5]-S[vp,6]/S[vp,7]).tolist())
        left-=b
    br=np.asarray(br); bp=np.asarray(bp)
    return {'delta_R':dR,'CI_R_lo':float(np.quantile(br,.025)),'CI_R_hi':float(np.quantile(br,.975)),'P_R_gt0':float((br>0).mean()),
            'delta_pct':dP,'CI_pct_lo':float(np.quantile(bp,.025)),'CI_pct_hi':float(np.quantile(bp,.975)),'P_pct_gt0':float((bp>0).mean())}

m.cluster_boot_delta=fast_cluster_boot_delta
m.main()
