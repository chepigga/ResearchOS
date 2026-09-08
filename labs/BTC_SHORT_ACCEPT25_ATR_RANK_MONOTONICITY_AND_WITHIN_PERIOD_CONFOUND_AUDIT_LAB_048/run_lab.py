#!/usr/bin/env python3
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

LAB='BTC_SHORT_ACCEPT25_ATR_RANK_MONOTONICITY_AND_WITHIN_PERIOD_CONFOUND_AUDIT_LAB_048'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC=LABS/'BTC_SHORT_HIGH_RESPONSE_ACCEPT25_BAD_REGIME_AND_YEARLY_FAILURE_STATE_LAB_045'/'output'/'failure_state_stream.csv'
SEED=20260908; BOOT_N=5000
PERIODS=['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']


def pf(x):
    x=np.asarray(x,float); gp=x[x>0].sum(); gl=-x[x<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def safe_spear(x,y):
    z=pd.DataFrame({'x':pd.to_numeric(x,errors='coerce'),'y':pd.to_numeric(y,errors='coerce')}).dropna()
    if len(z)<3 or z.x.nunique()<2 or z.y.nunique()<2:return np.nan,np.nan,len(z)
    r,p=spearmanr(z.x,z.y); return float(r),float(p),len(z)

def cluster_id(t):
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    return (((t-epoch).dt.total_seconds())//(7*86400)).astype('int64')

def state_summary(d,label):
    x=d.net_r_5bps.to_numpy(float)
    return dict(state=label,n=len(d),ev=float(np.mean(x)) if len(x) else np.nan,pf=pf(x),cum_r=float(np.sum(x)) if len(x) else np.nan)

def fixed_bin_table(d,nbins):
    edges=np.linspace(0,1,nbins+1); edges[-1]=1.0000000001
    b=pd.cut(d.atr_rank_90d,edges,right=False,labels=False,include_lowest=True)
    rows=[]
    for i in range(nbins):
        q=d[b==i]
        rows.append(dict(nbins=nbins,bin=i+1,lo=float(edges[i]),hi=float(min(edges[i+1],1.0)),mid=float((edges[i]+min(edges[i+1],1.0))/2),n=len(q),ev=float(q.net_r_5bps.mean()) if len(q) else np.nan,pf=pf(q.net_r_5bps) if len(q) else np.nan,cum_r=float(q.net_r_5bps.sum()) if len(q) else np.nan))
    return pd.DataFrame(rows),b

def q5q1_boot(d,qbin):
    z=d.copy(); z['bin']=qbin.to_numpy(); z['cluster']=cluster_id(z.regime_time)
    arr=[]
    for _,g in z.groupby('cluster'):
        q1=g[g.bin==0].net_r_5bps.to_numpy(float); q5=g[g.bin==4].net_r_5bps.to_numpy(float)
        arr.append((q5.sum(),len(q5),q1.sum(),len(q1)))
    a=np.asarray(arr,float); rng=np.random.default_rng(SEED); vals=[]; m=len(a)
    for _ in range(BOOT_N):
        s=a[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0: vals.append(float(s[0]/s[1]-s[2]/s[3]))
    vals=np.asarray(vals,float)
    point=float(z[z.bin==4].net_r_5bps.mean()-z[z.bin==0].net_r_5bps.mean())
    return dict(point=point,ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),clusters=m,draws=len(vals))

def fe_beta(df):
    z=df[['atr_rank_90d','net_r_5bps','period']].dropna().copy()
    cats=[p for p in PERIODS if p in set(z.period)]
    X=[np.ones(len(z)),z.atr_rank_90d.to_numpy(float)]
    for p in cats[1:]: X.append((z.period==p).astype(float).to_numpy())
    X=np.column_stack(X); y=z.net_r_5bps.to_numpy(float)
    beta=np.linalg.lstsq(X,y,rcond=None)[0]
    return float(beta[1])

def fe_boot(d):
    z=d.copy(); z['cluster']=cluster_id(z.regime_time)
    groups=[g.drop(columns='cluster') for _,g in z.groupby('cluster')]
    point=fe_beta(z.drop(columns='cluster'))
    rng=np.random.default_rng(SEED+48); vals=[]; m=len(groups)
    for _ in range(BOOT_N):
        samp=pd.concat([groups[i] for i in rng.integers(0,m,size=m)],ignore_index=True)
        try: vals.append(fe_beta(samp))
        except Exception: pass
    vals=np.asarray(vals,float)
    return dict(point=point,ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),clusters=m,draws=len(vals))

def main():
    d=pd.read_csv(SRC)
    d['signal_time']=pd.to_datetime(d.signal_time,errors='coerce',utc=True)
    d['entry_time']=pd.to_datetime(d.entry_time,errors='coerce',utc=True)
    d['regime_time']=pd.to_datetime(d.regime_time,errors='coerce',utc=True)
    for c in ['net_r_5bps','atr_rank_90d']: d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d[d.period.isin(PERIODS)].dropna(subset=['regime_time','net_r_5bps','atr_rank_90d']).sort_values('regime_time').reset_index(drop=True)
    if len(d)!=327: raise RuntimeError(f'Frozen ACCEPT2.5 parity failed: {len(d)} != 327')

    global_rho,global_p,global_n=safe_spear(d.atr_rank_90d,d.net_r_5bps)
    qtab,qbin=fixed_bin_table(d,5); dtab,dbin=fixed_bin_table(d,10)
    fixed=pd.concat([qtab,dtab],ignore_index=True); fixed.to_csv(OUT/'fixed_absolute_bins.csv',index=False)
    qb=q5q1_boot(d,qbin)
    q_ev=qtab.ev.to_numpy(float); q_mid=qtab.mid.to_numpy(float); q_rho,q_p,_=safe_spear(q_mid,q_ev)
    d_ev=dtab.ev.to_numpy(float); d_mid=dtab.mid.to_numpy(float); d_rho,d_p,_=safe_spear(d_mid,d_ev)
    d10d1=float(dtab.loc[dtab.bin==10,'ev'].iloc[0]-dtab.loc[dtab.bin==1,'ev'].iloc[0])

    feb=fe_boot(d)
    within=[]
    for p in PERIODS:
        z=d[d.period==p]; r,pv,n=safe_spear(z.atr_rank_90d,z.net_r_5bps)
        within.append(dict(period=p,n=n,rho=r,p=pv,ev=float(z.net_r_5bps.mean()) if len(z) else np.nan,atr_mean=float(z.atr_rank_90d.mean()) if len(z) else np.nan))
    within=pd.DataFrame(within); within.to_csv(OUT/'within_period.csv',index=False)

    half=pd.DataFrame([state_summary(d,'ALL'),state_summary(d[d.atr_rank_90d>=.5],'HIGH_ATR'),state_summary(d[d.atr_rank_90d<.5],'LOW_ATR')])
    half['ev_per_original']=half.cum_r/475.0; half.to_csv(OUT/'half_split_parity.csv',index=False)

    eligible=within[within.n>=20]
    pos_signs=int((eligible.rho>0).sum())
    rho_25h2=float(within.loc[within.period=='2025_H2','rho'].iloc[0])
    rho_26=float(within.loc[within.period=='2026_JAN_JUL','rho'].iloc[0])
    high=half[half.state=='HIGH_ATR'].iloc[0]; low=half[half.state=='LOW_ATR'].iloc[0]
    parity=(int(high.n)==187 and int(low.n)==140 and abs(float(high.ev)-0.098)<0.003 and abs(float(low.ev)-0.071)<0.003)

    gates={
      'exact_frozen_accept25_n327':len(d)==327,
      'atr_rank_coverage_ge99pct':d.atr_rank_90d.notna().mean()>=.99,
      'fixed_absolute_bins_only':True,
      'global_atr_rho_positive':global_rho>0,
      'global_rho_p_le_005':global_p<=.05,
      'q5_q1_ev_gap_positive':qb['point']>0,
      'q5_q1_boot_lower_gt0':qb['ci_lo']>0,
      'quintile_mid_ev_rho_ge_070':q_rho>=.70,
      'd10_d1_ev_gap_positive':d10d1>0,
      'decile_mid_ev_rho_ge_050':d_rho>=.50,
      'fixed_effect_atr_beta_positive':feb['point']>0,
      'fixed_effect_boot_lower_gt0':feb['ci_lo']>0,
      'at_least_5_of_7_period_rhos_positive':pos_signs>=5,
      '2025h2_within_rho_nonnegative':pd.notna(rho_25h2) and rho_25h2>=0,
      '2026_within_rho_nonnegative':pd.notna(rho_26) and rho_26>=0,
      'lab047_half_split_parity':parity,
      'august_not_used_for_selection':True,
    }
    first12=all(list(gates.values())[:12]); last5=sum(list(gates.values())[12:])
    if first12 and last5>=4: verdict='PASS_ATR_RANK_MONOTONIC_WITHIN_PERIOD_EFFECT'
    elif feb['point']<=0 or (q_rho<0 and d_rho<0): verdict='FAIL_ATR_RANK_ASSOCIATION_EXPLAINED_BY_CONFOUND_OR_NONMONOTONICITY'
    else: verdict='WATCH_ATR_RANK_NONLINEAR_OR_PARTIAL_WITHIN_PERIOD'

    boot={'q5_q1':qb,'fixed_effect_beta':feb,'global_rho':global_rho,'global_p':global_p,'quintile_mid_ev_rho':q_rho,'quintile_mid_ev_p':q_p,'decile_mid_ev_rho':d_rho,'decile_mid_ev_p':d_p,'d10_d1_gap':d10d1}
    (OUT/'bootstrap_and_tests.json').write_text(json.dumps(boot,indent=2))
    (OUT/'gates.json').write_text(json.dumps(gates,indent=2))
    d[['flow_id','signal_time','entry_time','regime_time','period','net_r_5bps','atr_rank_90d']].to_csv(OUT/'audit_stream.csv',index=False)

    def f(x):
        if pd.isna(x):return '—'
        return f'{x:+.3f}' if isinstance(x,(float,np.floating)) else str(x)
    L=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(gates.values())}/{len(gates)}**','', '## Frozen parity',f'- ACCEPT2.5 trades: **{len(d)}**; ATR-rank coverage: **{d.atr_rank_90d.notna().mean():.1%}**',f'- Global Spearman ATR-rank -> netR: **rho {global_rho:+.3f}, p={global_p:.4f}**','', '## Fixed absolute ATR-rank quintiles','', '| Bin | Range | N | EV | PF | CumR |','|---:|---|---:|---:|---:|---:|']
    for _,r in qtab.iterrows(): L.append(f"| Q{int(r.bin)} | {r.lo:.1f}-{r.hi:.1f} | {int(r.n)} | {r.ev:+.3f} | {r.pf:.3f} | {r.cum_r:+.2f} |")
    L += ['',f"Q5-Q1 EV gap: **{qb['point']:+.3f}R**, 7d bootstrap 95% CI **[{qb['ci_lo']:+.3f}, {qb['ci_hi']:+.3f}]**",f'Quintile midpoint-vs-EV Spearman: **{q_rho:+.3f}**','', '## Fixed absolute ATR-rank deciles','', '| Bin | N | EV | PF |','|---:|---:|---:|---:|']
    for _,r in dtab.iterrows(): L.append(f"| D{int(r.bin)} | {int(r.n)} | {r.ev:+.3f} | {r.pf:.3f} |")
    L += ['',f'D10-D1 EV gap: **{d10d1:+.3f}R**; decile midpoint-vs-EV Spearman: **{d_rho:+.3f}**','', '## Within-period fixed-effects audit',f"- Fixed-effects ATR beta: **{feb['point']:+.3f} R per full 0->1 ATR-rank move**",f"- 7d cluster bootstrap 95% CI: **[{feb['ci_lo']:+.3f}, {feb['ci_hi']:+.3f}]**, clusters={feb['clusters']}",'', '| Period | N | rho ATR->netR | p | EV | ATR mean |','|---|---:|---:|---:|---:|---:|']
    for _,r in within.iterrows(): L.append(f"| {r.period} | {int(r.n)} | {f(r.rho)} | {r.p:.3f} | {r.ev:+.3f} | {r.atr_mean:.3f} |")
    L += ['',f'Positive within-period rho signs (N>=20): **{pos_signs}/{len(eligible)}**','', '## LAB047 half-split parity','', '| State | N | Trade EV | PF | CumR | EV/original |','|---|---:|---:|---:|---:|---:|']
    for _,r in half.iterrows(): L.append(f"| {r.state} | {int(r.n)} | {r.ev:+.3f} | {r.pf:.3f} | {r.cum_r:+.2f} | {r.ev_per_original:+.3f} |")
    L += ['','## Gates']
    for k,v in gates.items(): L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    L += ['','## Guardrail','Audit only. No ATR cutoff/router is promoted here. Fixed absolute bins and frozen execution/payoff only; reused historical lineage, not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n')
    print(verdict, sum(gates.values()), '/', len(gates))

if __name__=='__main__': main()
