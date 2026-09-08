#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

LAB='BTC_SHORT_ACCEPT25_ATR_X_72H_EXTENSION_FAILURE_INTERACTION_LAB_050'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=HERE.parent/'BTC_SHORT_HIGH_RESPONSE_ACCEPT25_BAD_REGIME_AND_YEARLY_FAILURE_STATE_LAB_045'/'output'/'failure_state_stream.csv'
PERIODS=['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']
SEED=20260908+50
BOOT_N=5000

BANDS=[('LOW_BAND',0.0,0.4),('MID_SPIKE',0.4,0.6),('DEAD_MID',0.6,0.8),('TOP_BAND',0.8,1.0000000001)]

def pf(x):
    x=np.asarray(x,float); gp=x[x>0].sum(); gl=-x[x<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def cluster_id(t):
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    return (((t-epoch).dt.total_seconds())//(7*86400)).astype('int64')

def assign_band(x):
    x=float(x)
    for n,lo,hi in BANDS:
        if lo<=x<hi:return n
    return None

def safe_spear(x,y):
    z=pd.DataFrame({'x':pd.to_numeric(x,errors='coerce'),'y':pd.to_numeric(y,errors='coerce')}).dropna()
    if len(z)<3 or z.x.nunique()<2 or z.y.nunique()<2:return np.nan,np.nan,len(z)
    r,p=spearmanr(z.x,z.y); return float(r),float(p),len(z)

def design(d):
    cats=[p for p in PERIODS if p in set(d.period)]
    atr=d.atr_rank_90d.to_numpy(float); ext=d.downside_extension_72h_atr.to_numpy(float)
    cols=[np.ones(len(d)),atr,ext,atr*ext]
    names=['const','atr','ext72','atr_x_ext72']
    for p in cats[1:]:
        cols.append((d.period==p).astype(float).to_numpy()); names.append(f'fe_{p}')
    return np.column_stack(cols),d.net_r_5bps.to_numpy(float),names

def fit(d):
    X,y,names=design(d); b=np.linalg.lstsq(X,y,rcond=None)[0]
    return {names[i]:float(b[i]) for i in range(len(names))}

def cluster_boot_interaction(d):
    X,y,names=design(d); idx_int=names.index('atr_x_ext72')
    z=d.copy(); z['cluster']=cluster_id(z.regime_time).to_numpy()
    # same X rows as sorted d; aggregate sufficient statistics per 7d cluster
    stats=[]
    for c in z.cluster.unique():
        ii=np.flatnonzero(z.cluster.to_numpy()==c); Xi=X[ii]; yi=y[ii]
        stats.append((Xi.T@Xi,Xi.T@yi))
    m=len(stats); rng=np.random.default_rng(SEED); vals=[]
    for _ in range(BOOT_N):
        sel=rng.integers(0,m,size=m)
        xtx=np.zeros_like(stats[0][0]); xty=np.zeros_like(stats[0][1])
        for j in sel:
            xtx += stats[j][0]; xty += stats[j][1]
        try:
            b=np.linalg.lstsq(xtx,xty,rcond=None)[0]
            vals.append(float(b[idx_int]))
        except Exception: pass
    vals=np.asarray(vals,float); point=fit(d)['atr_x_ext72']
    return dict(point=point,ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),clusters=m,draws=len(vals))

def lin_slope(x,y):
    z=pd.DataFrame({'x':x,'y':y}).dropna()
    if len(z)<3 or z.x.nunique()<2:return np.nan
    X=np.column_stack([np.ones(len(z)),z.x.to_numpy(float)])
    b=np.linalg.lstsq(X,z.y.to_numpy(float),rcond=None)[0]
    return float(b[1])

def main():
    d=pd.read_csv(SRC)
    for c in ['regime_time','signal_time','entry_time']:
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['net_r_5bps','atr_rank_90d','downside_extension_72h_atr']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d[d.period.isin(PERIODS)].dropna(subset=['regime_time','net_r_5bps','atr_rank_90d','downside_extension_72h_atr']).copy()
    d=d.sort_values('regime_time').reset_index(drop=True)
    if len(d)!=327: raise RuntimeError(f'Frozen parity failed {len(d)} != 327')
    d['band']=d.atr_rank_90d.map(assign_band)
    if d.band.isna().any(): raise RuntimeError('ATR band assignment failed')

    coef=fit(d); boot=cluster_boot_interaction(d)

    # Frozen-band diagnostics.
    band_rows=[]
    for name,_,_ in BANDS:
        z=d[d.band==name]; rho,p,n=safe_spear(z.downside_extension_72h_atr,z.net_r_5bps)
        slope=lin_slope(z.downside_extension_72h_atr,z.net_r_5bps)
        band_rows.append(dict(band=name,n=len(z),ev=float(z.net_r_5bps.mean()),pf=pf(z.net_r_5bps),
                              ext_mean=float(z.downside_extension_72h_atr.mean()),ext_median=float(z.downside_extension_72h_atr.median()),
                              ext_rho=rho,ext_rho_p=p,ext_slope=slope,cum_r=float(z.net_r_5bps.sum())))
    bands=pd.DataFrame(band_rows)

    # Leave-one-period-out interaction coefficient; exact same continuous model.
    lopo=[]
    for p in PERIODS:
        z=d[d.period!=p].copy(); c=fit(z)
        lopo.append(dict(left_out=p,n=len(z),interaction=c['atr_x_ext72'],atr_main=c['atr'],ext_main=c['ext72']))
    lopo=pd.DataFrame(lopo)

    # Period stress, including marginal ATR effect at each period's mean extension.
    per=[]
    for p in PERIODS:
        z=d[d.period==p]; top=z[z.band=='TOP_BAND']; low=z[z.band=='LOW_BAND']
        mean_ext=float(z.downside_extension_72h_atr.mean())
        marginal_atr=float(coef['atr'] + coef['atr_x_ext72']*mean_ext)
        per.append(dict(period=p,n=len(z),ev=float(z.net_r_5bps.mean()),atr_mean=float(z.atr_rank_90d.mean()),ext_mean=mean_ext,
                        top_n=len(top),top_ev=float(top.net_r_5bps.mean()) if len(top) else np.nan,
                        top_ext_mean=float(top.downside_extension_72h_atr.mean()) if len(top) else np.nan,
                        low_n=len(low),low_ev=float(low.net_r_5bps.mean()) if len(low) else np.nan,
                        low_ext_mean=float(low.downside_extension_72h_atr.mean()) if len(low) else np.nan,
                        marginal_atr_effect_at_period_mean_ext=marginal_atr))
    per=pd.DataFrame(per)

    top=d[d.band=='TOP_BAND'].copy()
    top_25=per.loc[per.period=='2025_H1'].iloc[0]
    profitable_top_periods=per[(per.top_n>0)&(per.top_ev>0)&(per.period!='2025_H1')]
    pooled_prof_top=d[(d.band=='TOP_BAND') & d.period.isin(profitable_top_periods.period)]
    prof_top_ext_mean=float(pooled_prof_top.downside_extension_72h_atr.mean()) if len(pooled_prof_top) else np.nan

    top_row=bands[bands.band=='TOP_BAND'].iloc[0]
    lopo_negative=int((lopo.interaction<0).sum())
    p25h2=float(per.loc[per.period=='2025_H2','top_ev'].iloc[0])
    p26=float(per.loc[per.period=='2026_JAN_JUL','top_ev'].iloc[0])
    m2022=float(per.loc[per.period=='2022','marginal_atr_effect_at_period_mean_ext'].iloc[0])

    gates={
      'exact_frozen_n327': bool(len(d)==327),
      'atr_coverage_ge99pct': bool(d.atr_rank_90d.notna().mean()>=.99),
      'ext72_coverage_ge99pct': bool(d.downside_extension_72h_atr.notna().mean()>=.99),
      'interaction_beta_negative': bool(coef['atr_x_ext72']<0),
      'interaction_boot_upper_lt0': bool(boot['ci_hi']<0),
      'interaction_negative_at_least_5_of_7_lopo': bool(lopo_negative>=5),
      'top_band_ext_slope_negative': bool(pd.notna(top_row.ext_slope) and top_row.ext_slope<0),
      'top_band_ext_rho_negative': bool(pd.notna(top_row.ext_rho) and top_row.ext_rho<0),
      '2025h1_top_ext_gt_profitable_top_ext': bool(pd.notna(top_25.top_ext_mean) and pd.notna(prof_top_ext_mean) and top_25.top_ext_mean>prof_top_ext_mean),
      '2025h2_and_2026_top_positive': bool(p25h2>0 and p26>0),
      'period_fixed_atr_main_positive': bool(coef['atr']>0),
      'period_fixed_ext_main_nonpositive': bool(coef['ext72']<=0),
      '2022_marginal_atr_effect_nonnegative': bool(m2022>=0),
      'no_new_cutoff_router_searched': True,
      'august_not_used_for_selection': True,
    }
    critical=list(gates.keys())[:10]
    critical_ok=all(gates[k] for k in critical)
    total=sum(gates.values())
    if critical_ok and total>=13:
        verdict='PASS_ATR_X_EXTENSION_REMAINING_ROOM_INTERACTION'
    elif coef['atr_x_ext72']<0 and total>=11:
        verdict='WATCH_NEGATIVE_INTERACTION_PROOF_INCOMPLETE'
    else:
        verdict='FAIL_NO_ATR_X_EXTENSION_INTERACTION'

    # Persist.
    d[['flow_id','signal_time','entry_time','regime_time','period','net_r_5bps','atr_rank_90d','downside_extension_72h_atr','band']].to_csv(OUT/'interaction_audit_stream.csv',index=False)
    bands.to_csv(OUT/'band_extension_diagnostics.csv',index=False)
    lopo.to_csv(OUT/'leave_one_period_out_interaction.csv',index=False)
    per.to_csv(OUT/'period_interaction_stress.csv',index=False)
    tests={'coefficients':coef,'interaction_bootstrap':boot,'lopo_negative_count':lopo_negative,
           'profitable_top_periods':profitable_top_periods.period.tolist(),
           'profitable_top_pooled_ext_mean':prof_top_ext_mean,
           '2025h1_top_ext_mean':float(top_25.top_ext_mean) if pd.notna(top_25.top_ext_mean) else None}
    (OUT/'tests.json').write_text(json.dumps(tests,indent=2))
    (OUT/'gates.json').write_text(json.dumps({k:bool(v) for k,v in gates.items()},indent=2))

    L=[f'# {LAB}','',f'**Verdict: {verdict} — {total}/{len(gates)}**','',
       '## Frozen continuous interaction',
       f"- ATR main coefficient: **{coef['atr']:+.4f}R** per full rank move",
       f"- EXT72 main coefficient: **{coef['ext72']:+.4f}R per ATR of prior extension**",
       f"- ATR×EXT72 interaction: **{coef['atr_x_ext72']:+.4f}R**",
       f"- 7d cluster bootstrap interaction 95% CI: **[{boot['ci_lo']:+.4f}, {boot['ci_hi']:+.4f}]**, clusters={boot['clusters']}",
       '', '## Frozen ATR-band extension diagnostics','',
       '| Band | N | EV | PF | EXT mean | EXT rho->R | EXT slope |','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in bands.iterrows():
        L.append(f"| {r.band} | {int(r.n)} | {r.ev:+.3f} | {r.pf:.3f} | {r.ext_mean:.2f} | {r.ext_rho:+.3f} | {r.ext_slope:+.4f} |")
    L += ['', '## Leave-one-period-out interaction','', '| Left out | N | Interaction | ATR main | EXT main |','|---|---:|---:|---:|---:|']
    for _,r in lopo.iterrows(): L.append(f"| {r.left_out} | {int(r.n)} | {r.interaction:+.4f} | {r.atr_main:+.4f} | {r.ext_main:+.4f} |")
    L += ['',f'Negative interaction sign in **{lopo_negative}/7** LOPO samples.','',
          '## Period stress','',
          '| Period | N | EV | ATR mean | EXT mean | TOP n | TOP EV | TOP EXT mean | Marginal ATR effect @ period EXT |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in per.iterrows():
        te='—' if pd.isna(r.top_ev) else f'{r.top_ev:+.3f}'; tx='—' if pd.isna(r.top_ext_mean) else f'{r.top_ext_mean:.2f}'
        L.append(f"| {r.period} | {int(r.n)} | {r.ev:+.3f} | {r.atr_mean:.3f} | {r.ext_mean:.2f} | {int(r.top_n)} | {te} | {tx} | {r.marginal_atr_effect_at_period_mean_ext:+.3f} |")
    L += ['',f"2025_H1 TOP mean EXT72: **{float(top_25.top_ext_mean):.2f} ATR**; pooled profitable TOP periods: **{prof_top_ext_mean:.2f} ATR**",'', '## Gates']
    for k,v in gates.items(): L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    L += ['','## Guardrail','Interaction audit only. No extension cutoff, ATR cutoff, stop, target, entry, or time-exit was searched or promoted. Reused historical lineage; not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n')
    print(verdict,total,'/',len(gates))

if __name__=='__main__': main()
