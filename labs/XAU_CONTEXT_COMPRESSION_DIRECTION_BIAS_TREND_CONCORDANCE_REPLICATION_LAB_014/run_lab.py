#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_COMPRESSION_DIRECTION_BIAS_TREND_CONCORDANCE_REPLICATION_LAB_014'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
LAB13_PATH=ROOT/'labs'/'XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013'/'run_lab.py'
XAU_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
YEARS=[2023,2024,2025,2026]
BOOT_N=5000
SEED=2026091214


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def week_col(s:pd.Series)->pd.Series:
    return pd.to_datetime(s).dt.to_period('W-SUN').astype(str)


def annual_accuracy(q:pd.DataFrame,pred_col:str,min_n:int=25)->pd.DataFrame:
    y=pd.to_datetime(q.available_time).dt.year
    rows=[]
    for year in YEARS:
        g=q[y.eq(year)]
        h=g[g[pred_col].ne(0)&g.target_dir.isin([-1,1])]
        acc=float((h[pred_col]==h.target_dir).mean()) if len(h) else np.nan
        elig=bool(len(h)>=min_n and np.isfinite(acc))
        rows.append({'year':year,'n':int(len(h)),'accuracy':acc,'eligible':elig,'positive':bool(elig and acc>0.5)})
    return pd.DataFrame(rows)


def annual_follow(q:pd.DataFrame,metric:str,min_n:int=25)->pd.DataFrame:
    y=pd.to_datetime(q.available_time).dt.year
    rows=[]
    for year in YEARS:
        v=pd.to_numeric(q.loc[y.eq(year),metric],errors='coerce').dropna()
        mean=float(v.mean()) if len(v) else np.nan
        elig=bool(len(v)>=min_n and np.isfinite(mean))
        rows.append({'year':year,'n':int(len(v)),'mean_signed24_atr':mean,'eligible':elig,'positive':bool(elig and mean>0)})
    return pd.DataFrame(rows)


def bootstrap_accuracy_diff(q:pd.DataFrame,seed:int)->dict:
    # Compare concordant D14 correctness against D2 directional cases where frozen D1 bias is neutral.
    z=q[['available_time','D1_HTF_BIAS','D2_TREND_PRESSURE','D14_CONCORDANCE','target_dir']].copy()
    z=z[z.target_dir.isin([-1,1])]
    z['A']=z.D14_CONCORDANCE.ne(0)
    z['B']=z.D2_TREND_PRESSURE.ne(0)&z.D1_HTF_BIAS.eq(0)
    z['corrA']=(z.D14_CONCORDANCE==z.target_dir).astype(float)
    z['corrB']=(z.D2_TREND_PRESSURE==z.target_dir).astype(float)
    a=z[z.A]; b=z[z.B]
    obs=float(a.corrA.mean()-b.corrB.mean()) if len(a) and len(b) else np.nan
    z['week']=week_col(z.available_time)
    weeks=sorted(z.week.unique())
    arr=[]
    for w in weeks:
        g=z[z.week.eq(w)]
        aa=g[g.A].corrA.to_numpy(float); bb=g[g.B].corrB.to_numpy(float)
        arr.append([len(aa),np.nansum(aa),len(bb),np.nansum(bb)])
    arr=np.asarray(arr,float)
    rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[0]>0 and s[2]>0:
            draws.append(s[1]/s[0]-s[3]/s[2])
    draws=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(draws,.025)) if len(draws) else np.nan,
            'ci_hi':float(np.quantile(draws,.975)) if len(draws) else np.nan,
            'p_positive':float(np.mean(draws>0)) if len(draws) else np.nan,
            'n_concordant':int(len(a)),'n_d2_no_bias':int(len(b)),'weeks':int(m),
            'acc_concordant':float(a.corrA.mean()) if len(a) else np.nan,
            'acc_d2_no_bias':float(b.corrB.mean()) if len(b) else np.nan}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1)
    if sha256(p)!=XAU_SHA: raise RuntimeError('Canonical XAU SHA mismatch')

    lab8=load_module(LAB8_PATH,'lab8_014'); lab9=load_module(LAB9_PATH,'lab9_014')
    lab10=load_module(LAB10_PATH,'lab10_014'); lab13=load_module(LAB13_PATH,'lab13_014')

    m1=lab8.read_xau_native(p); h4=lab8.to_h4(m1); router=lab8.load_router_module()
    ctx=router.add_router(h4); ctx=lab8.add_forward_metrics(ctx); ctx=ctx.dropna(subset=['available_time','atr14']).copy()
    allbars,onset=lab8.make_episodes(ctx)
    if len(allbars)!=6216 or len(onset)!=610:
        raise RuntimeError(f'Parity failed bars={len(allbars)} episodes={len(onset)}')
    d=lab9.add_roles(allbars); d=lab10.add_components_and_candidates(d); d=lab13.add_prediction_candidates(d)
    d['D14_CONCORDANCE']=np.where((d.D1_HTF_BIAS==d.D2_TREND_PRESSURE)&d.D1_HTF_BIAS.ne(0),d.D1_HTF_BIAS,0).astype(int)
    pop=d.regime.eq('PULLBACK')&d.G1_VOL_COMPRESSION.fillna(False)

    fp=lab13.exact_first_passage(m1,d,pop)
    d=d.join(fp,how='left')
    q=d.loc[pop].copy()
    total=int(len(q)); directional=q.D14_CONCORDANCE.ne(0); resolved=q.target_dir.isin([-1,1])
    primary=q[directional&resolved].copy(); primary['correct']=(primary.D14_CONCORDANCE==primary.target_dir).astype(float)
    acc_boot=lab13.cluster_boot_mean(primary,'correct',SEED+1)
    coverage=float(directional.mean()) if total else np.nan
    years=annual_accuracy(q,'D14_CONCORDANCE',25)
    n2025=int(years.loc[years.year.eq(2025),'n'].iloc[0]); n2026=int(years.loc[years.year.eq(2026),'n'].iloc[0])
    h1_eligible=bool(len(primary)>=150 and coverage>=0.40 and n2025>=30 and n2026>=30)
    h1_transfer=bool(int(years.eligible.sum())>=3 and int(years.positive.sum())>=3)
    h1=bool(h1_eligible and acc_boot['observed']>0.5 and np.isfinite(acc_boot['ci_lo']) and acc_boot['ci_lo']>0.5 and h1_transfer)

    q['D14_signed24']=q.D14_CONCORDANCE*pd.to_numeric(q.close_ret_atr_24h,errors='coerce')
    follow=q[q.D14_CONCORDANCE.ne(0)][['available_time','D14_signed24']].copy()
    follow_boot=lab13.cluster_boot_mean(follow,'D14_signed24',SEED+2)
    follow_year=annual_follow(q.loc[q.D14_CONCORDANCE.ne(0)],'D14_signed24',25)
    h2_transfer=bool(int(follow_year.eligible.sum())>=3 and int(follow_year.positive.sum())>=3)
    h2=bool(follow_boot['n']>=200 and follow_boot['observed']>0 and np.isfinite(follow_boot['ci_lo']) and follow_boot['ci_lo']>0 and h2_transfer)

    side_rows=[]
    for sign,name in [(1,'BULL'),(-1,'BEAR')]:
        s=primary[primary.D14_CONCORDANCE.eq(sign)]
        acc=float(s.correct.mean()) if len(s) else np.nan
        signed=(s.D14_CONCORDANCE*pd.to_numeric(s.close_ret_atr_24h,errors='coerce'))
        side_rows.append({'side':name,'n_resolved':int(len(s)),'accuracy':acc,
                          'mean_signed24_atr':float(signed.mean()) if signed.notna().any() else np.nan})
    side=pd.DataFrame(side_rows)
    bull=side[side.side.eq('BULL')].iloc[0]; bear=side[side.side.eq('BEAR')].iloc[0]
    h3_eligible=bool(bull.n_resolved>=60 and bear.n_resolved>=60)
    h3=bool(h3_eligible and bull.accuracy>0.5 and bear.accuracy>0.5 and
            bull.accuracy>=0.475 and bear.accuracy>=0.475 and abs(bull.accuracy-bear.accuracy)<=0.10)

    h4raw=bootstrap_accuracy_diff(q,SEED+3)
    h4_eligible=bool(h4raw['n_concordant']>=150 and h4raw['n_d2_no_bias']>=30)
    h4=bool(h4_eligible and h4raw['observed']>0 and np.isfinite(h4raw['ci_lo']) and h4raw['ci_lo']>0)

    # diagnostics
    resolution_counts=q.resolution.value_counts(dropna=False).to_dict()
    target=q[q.target_dir.isin([-1,1])]
    target_balance={'bull_first':int((target.target_dir==1).sum()),'bear_first':int((target.target_dir==-1).sum()),
                    'bull_share':float((target.target_dir==1).mean()) if len(target) else np.nan,
                    'resolved_total':int(len(target)),
                    'no_breakout':int((q.resolution=='NO_BREAKOUT').sum()),'ambiguous':int((q.resolution=='AMBIGUOUS').sum())}
    timing=[]
    for flag,label in [(True,'CORRECT'),(False,'INCORRECT')]:
        s=primary[primary.correct.eq(float(flag))]
        timing.append({'class':label,'n':int(len(s)),'median_time_to_touch_min':float(pd.to_numeric(s.time_to_touch_min,errors='coerce').median()) if len(s) else np.nan})
    timing=pd.DataFrame(timing)

    if h1 and h2 and h3 and h4:
        verdict='BIAS_TREND_CONCORDANCE_REPLICATED_DISCOVERY_ONLY'
    elif h1 and h2 and h3:
        verdict='BIAS_TREND_CONCORDANCE_SEMANTICS_SUPPORTED_INCREMENT_NOT_CONFIRMED'
    elif h1 and h3 and not h2:
        verdict='BIAS_TREND_CONCORDANCE_DIRECTION_ONLY_NOT_PERSISTENT'
    elif not h1_eligible:
        verdict='BIAS_TREND_CONCORDANCE_UNDERPOWERED'
    else:
        verdict='BIAS_TREND_CONCORDANCE_NOT_REPLICATED'

    years.to_csv(out/'direction_year_transfer.csv',index=False)
    follow_year.to_csv(out/'followthrough_year_transfer.csv',index=False)
    side.to_csv(out/'side_symmetry.csv',index=False)
    timing.to_csv(out/'touch_timing.csv',index=False)
    q[['available_time','close','atr14','bias','D1_HTF_BIAS','D2_TREND_PRESSURE','D14_CONCORDANCE','resolution','target_dir','touch_time','time_to_touch_min','close_ret_atr_24h']].to_csv(out/'concordance_events.csv',index=False)

    summary={'lab':LAB,'verdict':verdict,'valid_context_bars':int(len(allbars)),'episode_onsets':int(len(onset)),
             'population_pullback_g1':total,'directional_predictions':int(directional.sum()),'coverage':coverage,
             'resolved_directional_n':int(len(primary)),'accuracy':float(acc_boot['observed']),'accuracy_ci_lo':float(acc_boot['ci_lo']),
             'accuracy_ci_hi':float(acc_boot['ci_hi']),'h1_eligible':h1_eligible,'h1_transfer':h1_transfer,'h1_pass':h1,
             'follow_n':int(follow_boot['n']),'mean_signed24_atr':float(follow_boot['observed']),
             'signed24_ci_lo':float(follow_boot['ci_lo']),'signed24_ci_hi':float(follow_boot['ci_hi']),
             'h2_transfer':h2_transfer,'h2_pass':h2,'h3_eligible':h3_eligible,'h3_pass':h3,
             'h4':h4raw,'h4_eligible':h4_eligible,'h4_pass':h4,'target_balance':target_balance,
             'resolution_counts':{str(k):int(v) for k,v in resolution_counts.items()}}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    report=[f'# {LAB}','',f'**Verdict: {verdict}**','',
            '> Concordance replication for human-facing compression direction only. No trading edge or execution claim.','',
            f'- Valid Context H4 bars: **{len(allbars):,}**',f'- Frozen episodes: **{len(onset):,}**',
            f'- Pullback + G1 bars: **{total:,}**',f'- D14 directional coverage: **{coverage:.1%}** ({int(directional.sum()):,}/{total:,})',
            f'- Exact resolved D14 predictions: **{len(primary):,}**',
            f'- Exact target balance: BULL **{target_balance["bull_first"]}**, BEAR **{target_balance["bear_first"]}**, bull share **{target_balance["bull_share"]:.3f}**','',
            '## Primary gates','',
            '| Gate | Eligible | Effect | 95% CI | Transfer | Pass |','|---|---|---:|---:|---|---|',
            f'| H1 first-passage accuracy | {"YES" if h1_eligible else "NO"} | {acc_boot["observed"]:.3f} | [{acc_boot["ci_lo"]:+.3f}, {acc_boot["ci_hi"]:+.3f}] | {"PASS" if h1_transfer else "FAIL"} | {"PASS" if h1 else "FAIL"} |',
            f'| H2 signed 24h ATR | {"YES" if follow_boot["n"]>=200 else "NO"} | {follow_boot["observed"]:+.3f} | [{follow_boot["ci_lo"]:+.3f}, {follow_boot["ci_hi"]:+.3f}] | {"PASS" if h2_transfer else "FAIL"} | {"PASS" if h2 else "FAIL"} |',
            f'| H3 BULL/BEAR symmetry | {"YES" if h3_eligible else "NO"} | {bull.accuracy:.3f} / {bear.accuracy:.3f} | — | — | {"PASS" if h3 else "FAIL"} |',
            f'| H4 concordance uplift vs D2 no-bias | {"YES" if h4_eligible else "NO"} | {h4raw["observed"]:+.3f} | [{h4raw["ci_lo"]:+.3f}, {h4raw["ci_hi"]:+.3f}] | — | {"PASS" if h4 else "FAIL"} |','',
            '## Side symmetry','',side.to_markdown(index=False),'',
            '## Incremental concordance diagnostic','',
            f'- Concordant accuracy: **{h4raw["acc_concordant"]:.3f}** (N={h4raw["n_concordant"]}).',
            f'- D2 with neutral HTF bias accuracy: **{h4raw["acc_d2_no_bias"]:.3f}** (N={h4raw["n_d2_no_bias"]}).',
            f'- Difference: **{h4raw["observed"]:+.3f}**, CI [{h4raw["ci_lo"]:+.3f}, {h4raw["ci_hi"]:+.3f}].','',
            '## Interpretation constraints','',
            '- D14 agreement rule, exact M1 ±1 ATR target, gates and bootstrap were frozen before outcomes.',
            '- No disagreement or neutral-bias cases may be reclassified after results.',
            '- Reused history: positive findings remain DISCOVERY_ONLY pending genuinely fresh post-freeze data.',
            '- This lab cannot authorize automated entries, BUY/SELL signals, sizing or prop-risk changes.']
    (out/'REPORT.md').write_text('\n'.join(report))
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
