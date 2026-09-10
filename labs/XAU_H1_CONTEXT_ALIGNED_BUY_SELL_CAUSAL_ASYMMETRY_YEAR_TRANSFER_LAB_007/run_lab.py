#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB='XAU_H1_CONTEXT_ALIGNED_BUY_SELL_CAUSAL_ASYMMETRY_YEAR_TRANSFER_LAB_007'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB006_PATH=ROOT/'labs'/'XAU_H1_CONTEXT_ALIGNED_EXECUTABLE_RR15_COST_YEAR_TRANSFER_LAB_006'/'run_lab.py'
PRIMARY_BPS=2.0
COST_BPS=[1.0,2.0,3.0,5.0]
YEARS=['2023','2024','2025','2026']
BOOT_N=5000
SEED=2026091007
RISK_PCT=0.25
EXPECTED_CONTEXT=263405
EXPECTED_ALIGNED=1195
EXPECTED_COMBINED_PRIMARY=488


def load_lab006():
    spec=importlib.util.spec_from_file_location('lab006_for_007',LAB006_PATH)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def branch_metrics(lab006, ledger:pd.DataFrame, bps:float)->dict:
    return lab006.metrics(ledger,bps)


def year_table(lab006, ledger:pd.DataFrame, bps:float)->pd.DataFrame:
    rows=[]
    for y in YEARS:
        g=ledger[ledger.year.astype(str).eq(y)].copy()
        m=lab006.metrics(g,bps)
        eligible=bool(m['n']>=20)
        rows.append({'year':y,**m,'eligible':eligible,
                     'positive':bool(eligible and np.isfinite(m['ev_r']) and m['ev_r']>0 and np.isfinite(m['pf']) and m['pf']>1.0)})
    return pd.DataFrame(rows)


def loyo_table(lab006,ledger:pd.DataFrame,bps:float)->pd.DataFrame:
    rows=[]
    for y in YEARS:
        g=ledger[~ledger.year.astype(str).eq(y)].copy(); m=lab006.metrics(g,bps)
        rows.append({'left_out':y,**m,'positive':bool(np.isfinite(m['ev_r']) and m['ev_r']>0)})
    return pd.DataFrame(rows)


def weekly_stats(ledger:pd.DataFrame,bps:float,dir_filter:int|None=None)->pd.DataFrame:
    col=f'net_r_{bps:g}bps'
    z=ledger.copy()
    if dir_filter is not None:
        z=z[z.dir.eq(dir_filter)].copy()
    z[col]=pd.to_numeric(z[col],errors='coerce')
    tt=pd.to_datetime(z.entry_time,errors='coerce',utc=True)
    z=z.loc[tt.notna() & z[col].notna()].copy(); tt=tt.loc[z.index]
    z['_week']=tt.dt.to_period('W-SUN').astype(str).values
    if z.empty:
        return pd.DataFrame(columns=['week','n','sum'])
    q=z.groupby('_week')[col].agg(['count','sum']).reset_index().rename(columns={'_week':'week','count':'n'})
    return q


def paired_bootstrap_diff(a_ledger:pd.DataFrame,b_ledger:pd.DataFrame,bps:float,a_dir:int|None=None,b_dir:int|None=None)->dict:
    a=weekly_stats(a_ledger,bps,a_dir).rename(columns={'n':'an','sum':'asum'})
    b=weekly_stats(b_ledger,bps,b_dir).rename(columns={'n':'bn','sum':'bsum'})
    q=a.merge(b,on='week',how='outer').fillna(0).sort_values('week')
    arr=q[['an','asum','bn','bsum']].to_numpy(float)
    rng=np.random.default_rng(SEED); vals=np.full(BOOT_N,np.nan)
    for k in range(BOOT_N):
        s=arr[rng.integers(0,len(arr),size=len(arr))].sum(axis=0)
        an,asum,bn,bsum=s
        if an>0 and bn>0:
            vals[k]=asum/an-bsum/bn
    vals=vals[np.isfinite(vals)]
    return {'weeks':int(len(arr)),'draws':BOOT_N,'ci_lo':float(np.quantile(vals,.025)),
            'ci_hi':float(np.quantile(vals,.975)),'p_positive':float(np.mean(vals>0))}


def weekly_bootstrap_ev(ledger:pd.DataFrame,bps:float)->dict:
    q=weekly_stats(ledger,bps)
    arr=q[['n','sum']].to_numpy(float)
    rng=np.random.default_rng(SEED+1); vals=np.full(BOOT_N,np.nan)
    for k in range(BOOT_N):
        s=arr[rng.integers(0,len(arr),size=len(arr))].sum(axis=0)
        if s[0]>0: vals[k]=s[1]/s[0]
    vals=vals[np.isfinite(vals)]
    return {'weeks':int(len(arr)),'draws':BOOT_N,'ci_lo':float(np.quantile(vals,.025)),
            'ci_hi':float(np.quantile(vals,.975)),'p_positive':float(np.mean(vals>0))}


def cost_table(lab006,buy:pd.DataFrame,sell:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for b in COST_BPS:
        rows.append({'branch':'BUY_ONLY',**lab006.metrics(buy,b)})
        rows.append({'branch':'SELL_ONLY',**lab006.metrics(sell,b)})
    return pd.DataFrame(rows)


def monthly_table(lab006,ledger:pd.DataFrame,bps:float)->pd.DataFrame:
    z=ledger.copy(); z['month']=pd.to_datetime(z.entry_time).dt.to_period('M').astype(str)
    rows=[]
    for mo,g in z.groupby('month',sort=True):
        rows.append({'month':mo,**lab006.metrics(g,bps)})
    return pd.DataFrame(rows)


def concentration(ledger:pd.DataFrame,bps:float)->dict:
    col=f'net_r_{bps:g}bps'; z=ledger.copy(); z[col]=pd.to_numeric(z[col],errors='coerce').fillna(0)
    t=pd.to_datetime(z.entry_time,utc=True,errors='coerce'); z=z.loc[t.notna()].copy(); t=t.loc[z.index]
    z['_year']=t.dt.year.astype(str).values; z['_month']=t.dt.to_period('M').astype(str).values; z['_week']=t.dt.to_period('W-SUN').astype(str).values
    def share_best(key):
        s=z.groupby(key)[col].sum(); p=s[s>0]
        return float(p.max()/p.sum()) if len(p) and p.sum()>0 else np.nan
    w=z.groupby('_week')[col].sum(); wp=w[w>0].sort_values(ascending=False)
    top10=float(wp.head(10).sum()/wp.sum()) if len(wp) and wp.sum()>0 else np.nan
    return {'best_positive_year_share':share_best('_year'),'best_positive_month_share':share_best('_month'),
            'top10_positive_weeks_share':top10,'positive_weeks':int((w>0).sum()),'total_weeks':int(len(w))}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--xau-pool',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    lab006=load_lab006(); lab002=lab006.load_lab002(); router=lab002.load_router_module()
    x,meta=lab002.build_xau_join(Path(a.xau_m1),Path(a.xau_pool),router)
    if len(x)!=EXPECTED_CONTEXT: raise RuntimeError(f'Context parity {len(x)} != {EXPECTED_CONTEXT}')
    m1=lab002.read_xau_native(Path(a.xau_m1))
    aligned=lab006.prepare_aligned(x,m1)
    if len(aligned)!=EXPECTED_ALIGNED: raise RuntimeError(f'Aligned parity {len(aligned)} != {EXPECTED_ALIGNED}')
    dedup=lab006.dedup_signals(aligned)
    events=lab006.simulate_event_ledger(dedup,m1)
    combined,combined_skipped=lab006.single_position_ledger(events)
    if len(combined)!=EXPECTED_COMBINED_PRIMARY: raise RuntimeError(f'LAB006 combined primary parity {len(combined)} != {EXPECTED_COMBINED_PRIMARY}')

    # Counterfactual ledgers: filter direction first, then independently apply one-position rule.
    buy_events=events[events.dir.eq(1)].copy(); sell_events=events[events.dir.eq(-1)].copy()
    buy,buy_skipped=lab006.single_position_ledger(buy_events)
    sell,sell_skipped=lab006.single_position_ledger(sell_events)

    # Attribution on exact frozen LAB006 combined ledger.
    attr_buy=combined[combined.dir.eq(1)].copy(); attr_sell=combined[combined.dir.eq(-1)].copy()
    mab=lab006.metrics(attr_buy,PRIMARY_BPS); mas=lab006.metrics(attr_sell,PRIMARY_BPS)
    attr_diff=float(mab['ev_r']-mas['ev_r'])
    attr_boot=paired_bootstrap_diff(combined,combined,PRIMARY_BPS,a_dir=1,b_dir=-1)

    # Counterfactual direction branches.
    mb=lab006.metrics(buy,PRIMARY_BPS); ms=lab006.metrics(sell,PRIMARY_BPS)
    cf_diff=float(mb['ev_r']-ms['ev_r'])
    cf_boot=paired_bootstrap_diff(buy,sell,PRIMARY_BPS)
    buy_boot=weekly_bootstrap_ev(buy,PRIMARY_BPS)

    costs=cost_table(lab006,buy,sell); costs.to_csv(out/'cost_branch_sensitivity.csv',index=False)
    by=year_table(lab006,buy,PRIMARY_BPS); sy=year_table(lab006,sell,PRIMARY_BPS)
    by.to_csv(out/'buy_year_transfer_2bps.csv',index=False); sy.to_csv(out/'sell_year_transfer_2bps.csv',index=False)
    blo=loyo_table(lab006,buy,PRIMARY_BPS); slo=loyo_table(lab006,sell,PRIMARY_BPS)
    blo.to_csv(out/'buy_loyo_2bps.csv',index=False); slo.to_csv(out/'sell_loyo_2bps.csv',index=False)
    mo=monthly_table(lab006,buy,PRIMARY_BPS); mo.to_csv(out/'buy_monthly_2bps.csv',index=False)
    combined.to_csv(out/'combined_lab006_parity_ledger.csv',index=False)
    buy.to_csv(out/'buy_only_ledger.csv',index=False); sell.to_csv(out/'sell_only_ledger.csv',index=False)
    conc=concentration(buy,PRIMARY_BPS)

    m5b=costs[(costs.branch.eq('BUY_ONLY')) & (costs.bps.eq(5.0))].iloc[0].to_dict()
    gates={
      'A1_attribution_ev_diff_gt_zero':bool(attr_diff>0),
      'A2_attribution_boot_ci_lo_gt_zero':bool(attr_boot['ci_lo']>0),
      'A3_counterfactual_ev_diff_gt_zero':bool(cf_diff>0),
      'A4_counterfactual_boot_ci_lo_gt_zero':bool(cf_boot['ci_lo']>0),
      'B1_buy_2bps_ev_gt_zero':bool(mb['ev_r']>0),
      'B2_buy_2bps_pf_ge_1_20':bool(mb['pf']>=1.20),
      'B3_buy_boot_ci_lo_gt_zero':bool(buy_boot['ci_lo']>0),
      'B4_buy_all4_years_positive':bool(len(by)==4 and by.eligible.all() and by.positive.all()),
      'B5_buy_loyo_4of4_positive':bool(len(blo)==4 and blo.positive.all()),
      'B6_buy_5bps_ev_gt_zero_pf_gt_1_05':bool(m5b['ev_r']>0 and m5b['pf']>1.05),
      'B7_buy_dd_at_025_le_4pct':bool(mb['max_dd_proxy_pct_at_025']<=4.0),
      'B8_buy_recovery_ge_2':bool(np.isfinite(mb['recovery_factor']) and mb['recovery_factor']>=2.0),
      'B9_buy_n_ge_100':bool(mb['n']>=100),
    }
    A=all(gates[k] for k in ['A1_attribution_ev_diff_gt_zero','A2_attribution_boot_ci_lo_gt_zero','A3_counterfactual_ev_diff_gt_zero','A4_counterfactual_boot_ci_lo_gt_zero'])
    B=all(v for k,v in gates.items() if k.startswith('B'))
    if A and B: verdict='BUY_ONLY_EXECUTABLE_TRANSFER_SUPPORTED_DISCOVERY_ONLY'
    elif A: verdict='BUY_SELL_ASYMMETRY_SUPPORTED_BUY_NOT_TRANSFER_READY'
    elif gates['A1_attribution_ev_diff_gt_zero'] and gates['A3_counterfactual_ev_diff_gt_zero']:
        verdict='BUY_SELL_ASYMMETRY_MIXED'
    else: verdict='BUY_SELL_ASYMMETRY_NOT_SUPPORTED'

    summary={
      'lab':LAB,'status':'REUSED_HISTORY_PREREGISTERED_DIRECTION_ASYMMETRY_DIAGNOSTIC','verdict':verdict,
      'selector':'H1 AND context_score>0.55 AND ALIGNED','sl_atr':1.5,'tp_atr':2.25,'gross_rr':1.5,'max_hours':120,
      'primary_bps':PRIMARY_BPS,'stress_bps':COST_BPS,'risk_pct_proxy':RISK_PCT,
      'xau_meta':meta,'aligned_rows':int(len(aligned)),'dedup_events':int(len(events)),
      'combined_primary_n':int(len(combined)),'combined_overlap_skipped':int(combined_skipped),
      'attribution':{'buy':mab,'sell':mas,'ev_diff':attr_diff,'bootstrap':attr_boot},
      'counterfactual':{'buy_only':mb,'sell_only':ms,'ev_diff':cf_diff,'bootstrap_diff':cf_boot,
                        'buy_bootstrap_ev':buy_boot,'buy_events':int(len(buy_events)),'sell_events':int(len(sell_events)),
                        'buy_overlap_skipped':int(buy_skipped),'sell_overlap_skipped':int(sell_skipped)},
      'buy_concentration':conc,'gates':gates,'promotion_authorized':False
    }
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',
           '> Reused-history diagnostic. BUY-only was motivated by LAB006; no production promotion is authorized.','',
           '## Frozen parity',f'- Context eligible: **{len(x)}**',f'- H1 HIGH ALIGNED rows: **{len(aligned)}**',
           f'- Combined LAB006 primary: **{len(combined)}**',f'- BUY-only primary: **{len(buy)}** (from {len(buy_events)} events; skipped {buy_skipped})',
           f'- SELL-only primary: **{len(sell)}** (from {len(sell_events)} events; skipped {sell_skipped})','',
           '## Attribution asymmetry — exact LAB006 combined ledger',
           f"- BUY: N={mab['n']}, EV **{mab['ev_r']:+.5f}R**, PF **{mab['pf']:.3f}**",
           f"- SELL: N={mas['n']}, EV **{mas['ev_r']:+.5f}R**, PF **{mas['pf']:.3f}**",
           f'- EV BUY-SELL: **{attr_diff:+.5f}R**',f"- Weekly bootstrap 95% CI: **[{attr_boot['ci_lo']:+.5f}, {attr_boot['ci_hi']:+.5f}]R**, P>0={attr_boot['p_positive']:.3f}",'',
           '## Counterfactual separate ledgers',
           f"- BUY-only: N={mb['n']}, EV **{mb['ev_r']:+.5f}R**, PF **{mb['pf']:.3f}**, CumR {mb['cum_r']:+.2f}R, DD {mb['max_dd_r']:.2f}R = {mb['max_dd_proxy_pct_at_025']:.2f}% @0.25%, Recovery {mb['recovery_factor']:.2f}",
           f"- SELL-only: N={ms['n']}, EV **{ms['ev_r']:+.5f}R**, PF **{ms['pf']:.3f}**, CumR {ms['cum_r']:+.2f}R",
           f'- EV BUY_ONLY-SELL_ONLY: **{cf_diff:+.5f}R**',f"- Difference bootstrap 95% CI: **[{cf_boot['ci_lo']:+.5f}, {cf_boot['ci_hi']:+.5f}]R**, P>0={cf_boot['p_positive']:.3f}",
           f"- BUY-only EV bootstrap 95% CI: **[{buy_boot['ci_lo']:+.5f}, {buy_boot['ci_hi']:+.5f}]R**, P>0={buy_boot['p_positive']:.3f}",'',
           '## BUY-only year transfer (2 bps)']
    for _,r in by.iterrows():
        lines.append(f"- {r.year}: N={int(r.n)}, EV **{r.ev_r:+.5f}R**, PF **{r.pf:.3f}**, CumR {r.cum_r:+.2f}R, DD {r.max_dd_r:.2f}R")
    lines += ['', '## BUY-only cost stress']
    for _,r in costs[costs.branch.eq('BUY_ONLY')].iterrows():
        lines.append(f"- {r.bps:g} bps: N={int(r.n)}, EV **{r.ev_r:+.5f}R**, PF **{r.pf:.3f}**, CumR {r.cum_r:+.2f}R, DD {r.max_dd_r:.2f}R")
    lines += ['', '## BUY-only concentration diagnostics',
              f"- Best positive year share: {conc['best_positive_year_share']:.3f}",
              f"- Best positive month share: {conc['best_positive_month_share']:.3f}",
              f"- Top-10 positive weeks share: {conc['top10_positive_weeks_share']:.3f}",'', '## Gates']
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines)); print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
