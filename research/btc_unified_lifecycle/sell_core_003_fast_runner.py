#!/usr/bin/env python3
"""Compute-equivalent fast runner for SELL_CORE_003.
Only replaces cluster bootstrap implementation with episode×(age,year) sufficient statistics.
BOOT=20000, seed, feature, outcomes and inference model remain frozen.
"""
import numpy as np
import pandas as pd
import sell_core_003_b3_flipcount7d as m


def fast_cluster_boot_fe(g,seed):
    z=g.dropna(subset=['flip_cnt_7d','R','pct']).copy()
    obsR,obsP=m.fe_beta(z)
    ids=np.sort(z.episode_id.unique())
    if len(ids)<8 or not np.isfinite(obsR):
        return dict(beta_R=obsR,CI_R_lo=np.nan,CI_R_hi=np.nan,P_beta_R_gt0=np.nan,beta_pct=obsP,CI_pct_lo=np.nan,CI_pct_hi=np.nan,P_beta_pct_gt0=np.nan)
    cells=sorted(set(zip(z.st_age.astype(int),z.year.astype(int))))
    epi={e:i for i,e in enumerate(ids)}; cel={c:i for i,c in enumerate(cells)}
    # n, sx, syR, syP, sxx, sxyR, sxyP per episode x exact(age,year) cell
    A=np.zeros((len(ids),len(cells),7),float)
    for r in z.itertuples(index=False):
        i=epi[r.episode_id]; j=cel[(int(r.st_age),int(r.year))]; x=float(r.flip_cnt_7d); yr=float(r.R); yp=float(r.pct)
        A[i,j,0]+=1; A[i,j,1]+=x; A[i,j,2]+=yr; A[i,j,3]+=yp; A[i,j,4]+=x*x; A[i,j,5]+=x*yr; A[i,j,6]+=x*yp
    rng=np.random.default_rng(seed); br=[]; bp=[]; left=m.BOOT; batch=1000
    while left>0:
        b=min(batch,left); idx=rng.choice(len(ids),size=(b,len(ids)),replace=True); S=A[idx].sum(axis=1)
        n=S[:,:,0]; sx=S[:,:,1]; syR=S[:,:,2]; syP=S[:,:,3]; sxx=S[:,:,4]; sxyR=S[:,:,5]; sxyP=S[:,:,6]
        valid=n>0
        den=np.where(valid,sxx-sx*sx/np.where(valid,n,1),0).sum(axis=1)
        nr=np.where(valid,sxyR-sx*syR/np.where(valid,n,1),0).sum(axis=1)
        npct=np.where(valid,sxyP-sx*syP/np.where(valid,n,1),0).sum(axis=1)
        ok=den>1e-12
        br.extend((nr[ok]/den[ok]).tolist()); bp.extend((npct[ok]/den[ok]).tolist()); left-=b
    br=np.asarray(br); bp=np.asarray(bp)
    return dict(beta_R=obsR,CI_R_lo=float(np.quantile(br,.025)),CI_R_hi=float(np.quantile(br,.975)),P_beta_R_gt0=float((br>0).mean()),beta_pct=obsP,CI_pct_lo=float(np.quantile(bp,.025)),CI_pct_hi=float(np.quantile(bp,.975)),P_beta_pct_gt0=float((bp>0).mean()))

m.cluster_boot_fe=fast_cluster_boot_fe
m.main()
