#!/usr/bin/env python3
"""Fast exact-equivalent bootstrap runner for SELL_CORE_011.
Only computational implementation changes; frozen hypothesis/methodology is unchanged.
"""
import numpy as np, pandas as pd
import sell_core_011_b3_h4_sell_aligned as lab


def fast_cluster_boot_mean(g,seed):
    z=g.dropna(subset=['R','pct']).copy()
    a=z.groupby('episode_id').agg(sumR=('R','sum'),sumP=('pct','sum'),N=('R','size')).reset_index(drop=True)
    if len(a)<4:
        return {'CI_R_lo':np.nan,'CI_R_hi':np.nan,'P_EV_R_gt0':np.nan,'CI_pct_lo':np.nan,'CI_pct_hi':np.nan,'P_EV_pct_gt0':np.nan}
    ar=a[['sumR','sumP','N']].to_numpy(float); E=len(ar); rng=np.random.default_rng(seed)
    idx=rng.integers(0,E,size=(lab.BOOT,E)); s=ar[idx].sum(axis=1)
    br=s[:,0]/s[:,2]; bp=s[:,1]/s[:,2]
    return {'CI_R_lo':float(np.quantile(br,.025)),'CI_R_hi':float(np.quantile(br,.975)),'P_EV_R_gt0':float((br>0).mean()),
            'CI_pct_lo':float(np.quantile(bp,.025)),'CI_pct_hi':float(np.quantile(bp,.975)),'P_EV_pct_gt0':float((bp>0).mean())}


def fast_phase_pair(a,b,hold_h,view):
    aa=a[['episode_id','st_age','base_clock_time','R','pct']].copy(); bb=b[['episode_id','st_age','base_clock_time','R','pct']].copy()
    p=aa.merge(bb,on=['episode_id','st_age','base_clock_time'],suffixes=('_0','_2'))
    if len(p)==0:return p,{}
    p['dR']=p.R_2-p.R_0; p['dpct']=p.pct_2-p.pct_0
    ag=p.groupby('episode_id').agg(sumD=('dR','sum'),N=('dR','size')).to_numpy(float)
    E=len(ag); rng=np.random.default_rng(lab.SEED+hold_h+(0 if view=='FIRST' else 1000)); idx=rng.integers(0,E,size=(lab.BOOT,E)); s=ag[idx].sum(axis=1); bd=s[:,0]/s[:,1]
    return p,{'view':view,'hold_h':hold_h,'N_pairs':len(p),'episodes':E,'EV0_R':float(p.R_0.mean()),'EV2_R':float(p.R_2.mean()),'delta_2_minus_0_R':float(p.dR.mean()),'CI_lo':float(np.quantile(bd,.025)),'CI_hi':float(np.quantile(bd,.975)),'P_delta_gt0':float((bd>0).mean()),'corr_R':float(p.R_0.corr(p.R_2))}

lab.cluster_boot_mean=fast_cluster_boot_mean
lab.phase_pair=fast_phase_pair
lab.main()
