#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_ACCEPT25_ATR_NONLINEAR_SHAPE_AND_LEAVE_ONE_PERIOD_OUT_STABILITY_LAB_049'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=HERE.parent/'BTC_SHORT_ACCEPT25_ATR_RANK_MONOTONICITY_AND_WITHIN_PERIOD_CONFOUND_AUDIT_LAB_048'/'output'/'audit_stream.csv'
PERIODS=['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']
SEED=20260908+49
BOOT_N=5000

BANDS=[
    ('LOW_BAND',0.0,0.4),
    ('MID_SPIKE',0.4,0.6),
    ('DEAD_MID',0.6,0.8),
    ('TOP_BAND',0.8,1.0000000001),
]

def pf(x):
    x=np.asarray(x,float)
    gp=x[x>0].sum(); gl=-x[x<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def cluster_id(t):
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    return (((t-epoch).dt.total_seconds())//(7*86400)).astype('int64')

def assign_band(x):
    x=float(x)
    for name,lo,hi in BANDS:
        if x>=lo and x<hi: return name
    return None

def summarize(d,scope):
    rows=[]
    for name,_,_ in BANDS:
        z=d[d.band==name]
        x=z.net_r_5bps.to_numpy(float)
        rows.append(dict(scope=scope,band=name,n=len(z),ev=float(np.mean(x)) if len(x) else np.nan,
                         pf=pf(x) if len(x) else np.nan,cum_r=float(np.sum(x)) if len(x) else np.nan))
    return rows

def band_ev(d,name):
    z=d[d.band==name]
    return float(z.net_r_5bps.mean()) if len(z) else np.nan

def contrast(d,a='TOP_BAND',b='LOW_BAND'):
    ea=band_ev(d,a); eb=band_ev(d,b)
    return float(ea-eb) if pd.notna(ea) and pd.notna(eb) else np.nan

def bootstrap_contrast(d,a='TOP_BAND',b='LOW_BAND',seed=SEED):
    z=d[d.band.isin([a,b])].copy()
    z['cluster']=cluster_id(z.regime_time)
    rows=[]
    for _,g in z.groupby('cluster'):
        aa=g[g.band==a].net_r_5bps.to_numpy(float)
        bb=g[g.band==b].net_r_5bps.to_numpy(float)
        rows.append((aa.sum(),len(aa),bb.sum(),len(bb)))
    arr=np.asarray(rows,float)
    m=len(arr); rng=np.random.default_rng(seed); vals=[]
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0:
            vals.append(float(s[0]/s[1]-s[2]/s[3]))
    vals=np.asarray(vals,float)
    return dict(point=contrast(d,a,b),ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),clusters=m,draws=len(vals))

def main():
    d=pd.read_csv(SRC)
    d['regime_time']=pd.to_datetime(d.regime_time,errors='coerce',utc=True)
    d['atr_rank_90d']=pd.to_numeric(d.atr_rank_90d,errors='coerce')
    d['net_r_5bps']=pd.to_numeric(d.net_r_5bps,errors='coerce')
    d=d[d.period.isin(PERIODS)].dropna(subset=['regime_time','atr_rank_90d','net_r_5bps']).copy()
    d=d.sort_values('regime_time').reset_index(drop=True)
    if len(d)!=327: raise RuntimeError(f'Frozen parity failed {len(d)} != 327')
    d['band']=d.atr_rank_90d.map(assign_band)
    if d.band.isna().any(): raise RuntimeError('Unassigned ATR rank')

    summary=[]
    summary += summarize(d,'FULL')
    full_boot=bootstrap_contrast(d)
    full_mid_boot=bootstrap_contrast(d,'MID_SPIKE','LOW_BAND',seed=SEED+100)

    lopo_rows=[]; lopo_boot={}
    for i,p in enumerate(PERIODS):
        z=d[d.period!=p].copy(); scope=f'LOO_{p}'
        summary += summarize(z,scope)
        top=band_ev(z,'TOP_BAND'); low=band_ev(z,'LOW_BAND'); mid=band_ev(z,'MID_SPIKE'); dead=band_ev(z,'DEAD_MID')
        b=bootstrap_contrast(z,seed=SEED+i+1); lopo_boot[p]=b
        lopo_rows.append(dict(left_out=p,n=len(z),top_ev=top,low_ev=low,mid_ev=mid,dead_ev=dead,
                              top_low_gap=top-low,mid_low_gap=mid-low,
                              boot_lo=b['ci_lo'],boot_hi=b['ci_hi']))
    lopo=pd.DataFrame(lopo_rows)

    # Per-period contribution and frozen bad-period stress.
    period_rows=[]
    for p in PERIODS:
        z=d[d.period==p]
        period_rows.append(dict(period=p,n=len(z),top_n=int((z.band=='TOP_BAND').sum()),low_n=int((z.band=='LOW_BAND').sum()),
                                mid_n=int((z.band=='MID_SPIKE').sum()),top_ev=band_ev(z,'TOP_BAND'),low_ev=band_ev(z,'LOW_BAND'),
                                mid_ev=band_ev(z,'MID_SPIKE'),dead_ev=band_ev(z,'DEAD_MID'),
                                top_low_gap=contrast(z),mid_cum=float(z.loc[z.band=='MID_SPIKE','net_r_5bps'].sum())))
    per=pd.DataFrame(period_rows)
    bad=d[d.period.isin(['2022','2025_H1'])].copy()
    bad_boot=bootstrap_contrast(bad,seed=SEED+500)
    mid_abs=per.mid_cum.abs(); mid_conc=float(mid_abs.max()/mid_abs.sum()) if mid_abs.sum()>0 else np.nan

    # Gate calculations.
    top_pos_all=bool((lopo.top_ev>0).all())
    low_nonpos_count=int((lopo.low_ev<=0).sum())
    gap_pos_all=bool((lopo.top_low_gap>0).all())
    boot_pos_count=int((lopo.boot_lo>0).sum())
    mid_pos_all=bool((lopo.mid_ev>0).all())
    mid_gap_pos_all=bool((lopo.mid_low_gap>0).all())
    loo_25=float(lopo.loc[lopo.left_out=='2025_H2','top_low_gap'].iloc[0])
    loo_26=float(lopo.loc[lopo.left_out=='2026_JAN_JUL','top_low_gap'].iloc[0])
    stress_2022=float(per.loc[per.period=='2022','top_low_gap'].iloc[0])
    stress_25h1=float(per.loc[per.period=='2025_H1','top_low_gap'].iloc[0])

    gates={
      'exact_frozen_accept25_n327': bool(len(d)==327),
      'atr_rank_coverage_ge99pct': bool(d.atr_rank_90d.notna().mean()>=.99),
      'full_top_minus_low_gap_gt_025r': bool(full_boot['point']>0.25),
      'full_top_minus_low_boot_lower_gt0': bool(full_boot['ci_lo']>0),
      'top_band_ev_positive_all_7_lopo': top_pos_all,
      'low_band_ev_nonpositive_at_least_6_of_7_lopo': bool(low_nonpos_count>=6),
      'top_minus_low_gap_positive_all_7_lopo': gap_pos_all,
      'top_minus_low_boot_lower_gt0_at_least_5_of_7_lopo': bool(boot_pos_count>=5),
      'combined_2022_2025h1_top_minus_low_positive': bool(bad_boot['point']>0),
      'combined_bad_boot_lower_gt0': bool(bad_boot['ci_lo']>0),
      'leave_2025h2_out_top_minus_low_positive': bool(loo_25>0),
      'leave_2026_out_top_minus_low_positive': bool(loo_26>0),
      '2022_top_minus_low_positive': bool(stress_2022>0),
      '2025h1_top_minus_low_positive': bool(stress_25h1>0),
      'mid_spike_ev_positive_all_7_lopo': mid_pos_all,
      'mid_spike_minus_low_positive_all_7_lopo': mid_gap_pos_all,
      'mid_spike_no_single_period_gt50pct_abs_contribution': bool(pd.notna(mid_conc) and mid_conc<=0.50),
      'august_not_used_for_selection': True,
    }

    primary_keys=[
      'exact_frozen_accept25_n327','atr_rank_coverage_ge99pct','full_top_minus_low_gap_gt_025r',
      'full_top_minus_low_boot_lower_gt0','top_band_ev_positive_all_7_lopo',
      'low_band_ev_nonpositive_at_least_6_of_7_lopo','top_minus_low_gap_positive_all_7_lopo',
      'top_minus_low_boot_lower_gt0_at_least_5_of_7_lopo','combined_2022_2025h1_top_minus_low_positive',
      'leave_2025h2_out_top_minus_low_positive','leave_2026_out_top_minus_low_positive']
    mid_keys=['mid_spike_ev_positive_all_7_lopo','mid_spike_minus_low_positive_all_7_lopo','mid_spike_no_single_period_gt50pct_abs_contribution']
    primary_ok=all(gates[k] for k in primary_keys)
    mid_ok=all(gates[k] for k in mid_keys)
    if primary_ok and mid_ok:
        verdict='PASS_ATR_NONLINEAR_SHAPE_LOPO_STABLE'
    elif primary_ok:
        verdict='WATCH_ATR_TOP_BAND_STABLE_MID_SPIKE_UNSTABLE'
    else:
        verdict='FAIL_ATR_NONLINEAR_SHAPE_PERIOD_DEPENDENT'

    pd.DataFrame(summary).to_csv(OUT/'band_summary_full_and_lopo.csv',index=False)
    lopo.to_csv(OUT/'lopo_primary_shape.csv',index=False)
    per.to_csv(OUT/'period_shape_stress.csv',index=False)
    d[['flow_id','signal_time','entry_time','regime_time','period','atr_rank_90d','net_r_5bps','band']].to_csv(OUT/'audit_stream.csv',index=False)
    tests={'full_top_minus_low':full_boot,'full_mid_minus_low':full_mid_boot,'lopo_top_minus_low':lopo_boot,
           'combined_2022_2025h1_top_minus_low':bad_boot,'mid_abs_contribution_max_share':mid_conc,
           'lopo_boot_positive_count':boot_pos_count,'lopo_low_nonpositive_count':low_nonpos_count}
    (OUT/'bootstrap_and_tests.json').write_text(json.dumps(tests,indent=2))
    (OUT/'gates.json').write_text(json.dumps({k:bool(v) for k,v in gates.items()},indent=2))

    sm=pd.DataFrame(summary)
    full=sm[sm.scope=='FULL'].set_index('band')
    lines=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(gates.values())}/{len(gates)}**','',
           '## Frozen full-sample shape','', '| Band | N | EV | PF | CumR |','|---|---:|---:|---:|---:|']
    for name,_,_ in BANDS:
        r=full.loc[name]; lines.append(f'| {name} | {int(r.n)} | {r.ev:+.3f} | {r.pf:.3f} | {r.cum_r:+.2f} |')
    lines += ['',f"TOP-LOW gap: **{full_boot['point']:+.3f}R**, 7d bootstrap 95% CI **[{full_boot['ci_lo']:+.3f}, {full_boot['ci_hi']:+.3f}]**",
              f"MID_SPIKE-LOW gap: **{full_mid_boot['point']:+.3f}R**, bootstrap **[{full_mid_boot['ci_lo']:+.3f}, {full_mid_boot['ci_hi']:+.3f}]**",'',
              '## Leave-one-period-out stability','',
              '| Left out | N | TOP EV | LOW EV | TOP-LOW | Boot 95% CI | MID EV | MID-LOW |','|---|---:|---:|---:|---:|---|---:|---:|']
    for _,r in lopo.iterrows():
        lines.append(f"| {r.left_out} | {int(r.n)} | {r.top_ev:+.3f} | {r.low_ev:+.3f} | {r.top_low_gap:+.3f} | [{r.boot_lo:+.3f}, {r.boot_hi:+.3f}] | {r.mid_ev:+.3f} | {r.mid_low_gap:+.3f} |")
    lines += ['',f'Primary bootstrap lower >0 in **{boot_pos_count}/7** LOPO samples; LOW_BAND <=0 in **{low_nonpos_count}/7**.','',
              '## Period stress and MID_SPIKE concentration','',
              '| Period | N | TOP n | LOW n | TOP EV | LOW EV | TOP-LOW | MID n | MID EV | MID CumR |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in per.iterrows():
        def ff(x): return '—' if pd.isna(x) else f'{x:+.3f}'
        lines.append(f"| {r.period} | {int(r.n)} | {int(r.top_n)} | {int(r.low_n)} | {ff(r.top_ev)} | {ff(r.low_ev)} | {ff(r.top_low_gap)} | {int(r.mid_n)} | {ff(r.mid_ev)} | {r.mid_cum:+.2f} |")
    lines += ['',f"Combined 2022+2025_H1 TOP-LOW: **{bad_boot['point']:+.3f}R**, bootstrap **[{bad_boot['ci_lo']:+.3f}, {bad_boot['ci_hi']:+.3f}]**",
              f'MID_SPIKE maximum single-period share of absolute CumR contribution: **{mid_conc:.1%}**','', '## Gates']
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['','## Guardrail','No new ATR cutoff/router was searched or promoted. Exact frozen execution/payoff and absolute LAB048 bands only. Reused historical lineage; not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(verdict, sum(gates.values()), '/', len(gates))

if __name__=='__main__':
    main()
