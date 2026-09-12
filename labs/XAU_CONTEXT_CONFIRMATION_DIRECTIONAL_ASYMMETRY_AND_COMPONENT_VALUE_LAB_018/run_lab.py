#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_CONFIRMATION_DIRECTIONAL_ASYMMETRY_AND_COMPONENT_VALUE_LAB_018'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
LAB13_PATH=ROOT/'labs'/'XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013'/'run_lab.py'
LAB16_PATH=ROOT/'labs'/'XAU_CONTEXT_SETUP_CONFIRMATION_OB_IMBALANCE_LIQUIDITY_PRICE_ACTION_LAB_016'/'run_lab.py'
XAU_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
BOOT_N=5000
SEED=2026091218
COMPONENTS=['OB_CONFIRM','IMBALANCE_CONFIRM','LIQUIDITY_CONFIRM','PRICE_ACTION_CONFIRM']
SIDES=[(1,'BULL'),(-1,'BEAR')]


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


def boot_mean(q:pd.DataFrame,metric:str,seed:int)->dict:
    z=q[['available_time',metric]].copy()
    z[metric]=pd.to_numeric(z[metric],errors='coerce')
    z=z.dropna(subset=['available_time',metric])
    obs=float(z[metric].mean()) if len(z) else np.nan
    if z.empty:
        return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n':0,'weeks':0}
    z['week']=week_col(z.available_time)
    arr=z.groupby('week')[metric].agg(['count','sum']).to_numpy(float)
    rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[0]>0: draws.append(s[1]/s[0])
    draws=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(draws,.025)),'ci_hi':float(np.quantile(draws,.975)),
            'n':int(len(z)),'weeks':int(m)}


def boot_binary_diff(q:pd.DataFrame,metric:str,group:str,seed:int)->dict:
    z=q[['available_time',metric,group]].copy()
    z[metric]=pd.to_numeric(z[metric],errors='coerce')
    z=z.dropna(subset=['available_time',metric,group])
    a=z[z[group].astype(bool)]; b=z[~z[group].astype(bool)]
    obs=float(a[metric].mean()-b[metric].mean()) if len(a) and len(b) else np.nan
    if z.empty or not len(a) or not len(b):
        return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n_present':int(len(a)),'n_absent':int(len(b)),'weeks':0}
    z['week']=week_col(z.available_time)
    stats=[]
    for _,g in z.groupby('week'):
        aa=g[g[group].astype(bool)][metric].to_numpy(float); bb=g[~g[group].astype(bool)][metric].to_numpy(float)
        stats.append([len(aa),np.nansum(aa),len(bb),np.nansum(bb)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[0]>0 and s[2]>0: draws.append(s[1]/s[0]-s[3]/s[2])
    draws=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(draws,.025)) if len(draws) else np.nan,
            'ci_hi':float(np.quantile(draws,.975)) if len(draws) else np.nan,
            'n_present':int(len(a)),'n_absent':int(len(b)),'weeks':int(m)}


def boot_side_diff(q:pd.DataFrame,seed:int)->dict:
    z=q[['available_time','D14_CONCORDANCE','correct']].dropna().copy()
    bull=z[z.D14_CONCORDANCE.eq(1)]; bear=z[z.D14_CONCORDANCE.eq(-1)]
    obs=float(bull.correct.mean()-bear.correct.mean()) if len(bull) and len(bear) else np.nan
    if z.empty or not len(bull) or not len(bear):
        return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n_bull':len(bull),'n_bear':len(bear),'weeks':0}
    z['week']=week_col(z.available_time); stats=[]
    for _,g in z.groupby('week'):
        b=g[g.D14_CONCORDANCE.eq(1)].correct.to_numpy(float); s=g[g.D14_CONCORDANCE.eq(-1)].correct.to_numpy(float)
        stats.append([len(b),np.nansum(b),len(s),np.nansum(s)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        x=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0 and x[2]>0: draws.append(x[1]/x[0]-x[3]/x[2])
    draws=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(draws,.025)) if len(draws) else np.nan,
            'ci_hi':float(np.quantile(draws,.975)) if len(draws) else np.nan,
            'n_bull':int(len(bull)),'n_bear':int(len(bear)),'weeks':int(m)}


def conditional_component(q:pd.DataFrame,side:int,component:str)->dict:
    z=q[q.D14_CONCORDANCE.eq(side)].copy()
    other=[c for c in COMPONENTS if c!=component]
    z['_pattern']=z[other].astype(int).astype(str).agg(''.join,axis=1)
    rows=[]
    for pat,g in z.groupby('_pattern'):
        a=g[g[component]]; b=g[~g[component]]
        if len(a)>=4 and len(b)>=4:
            eff=float(a.correct.mean()-b.correct.mean()); w=int(min(len(a),len(b)))
            rows.append({'pattern':pat,'n_present':len(a),'n_absent':len(b),'effect':eff,'weight':w})
    if rows:
        rr=pd.DataFrame(rows); prem=float(np.average(rr.effect,weights=rr.weight)); tw=int(rr.weight.sum())
    else:
        prem=np.nan; tw=0
    return {'conditional_premium':prem,'eligible_strata':len(rows),'conditional_weight':tw,'strata':rows}


def exact_combo_name(r:pd.Series)->str:
    vals={c:bool(r[c]) for c in COMPONENTS}
    n=sum(vals.values())
    if n==4: return 'ALL4'
    if n==3:
        missing=[c for c,v in vals.items() if not v][0]
        return {'OB_CONFIRM':'NO_OB','IMBALANCE_CONFIRM':'NO_IMBALANCE','LIQUIDITY_CONFIRM':'NO_LIQUIDITY','PRICE_ACTION_CONFIRM':'NO_PRICE_ACTION'}[missing]
    return f'OTHER_{n}'


def candidate_masks(q:pd.DataFrame)->dict[str,pd.Series]:
    high75=q.SETUP_CONFIRMATION_PCT.ge(75)
    return {
        'HIGH75':high75,
        'HIGH75_AND_OB':high75&q.OB_CONFIRM,
        'HIGH75_AND_LIQUIDITY':high75&q.LIQUIDITY_CONFIRM,
        'HIGH75_AND_IMBALANCE':high75&q.IMBALANCE_CONFIRM,
        'HIGH75_AND_PRICE_ACTION':high75&q.PRICE_ACTION_CONFIRM,
        'COREPAIR_PLUS_AUX':q.OB_CONFIRM&q.LIQUIDITY_CONFIRM&(q.IMBALANCE_CONFIRM|q.PRICE_ACTION_CONFIRM),
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1)
    if sha256(p)!=XAU_SHA: raise RuntimeError('Canonical XAU SHA mismatch')

    lab8=load_module(LAB8_PATH,'lab8_018'); lab9=load_module(LAB9_PATH,'lab9_018'); lab10=load_module(LAB10_PATH,'lab10_018')
    lab13=load_module(LAB13_PATH,'lab13_018'); lab16=load_module(LAB16_PATH,'lab16_018')
    m1=lab8.read_xau_native(p); m15=lab16.to_m15(m1); h4=lab8.to_h4(m1); router=lab8.load_router_module()
    ctx=router.add_router(h4); ctx=lab8.add_forward_metrics(ctx); ctx=ctx.dropna(subset=['available_time','atr14']).copy()
    allbars,onset=lab8.make_episodes(ctx)
    if len(allbars)!=6216 or len(onset)!=610: raise RuntimeError(f'Parity failed bars={len(allbars)} episodes={len(onset)}')
    d=lab9.add_roles(allbars); d=lab10.add_components_and_candidates(d); d=lab13.add_prediction_candidates(d)
    d['D14_CONCORDANCE']=np.where((d.D1_HTF_BIAS==d.D2_TREND_PRESSURE)&d.D1_HTF_BIAS.ne(0),d.D1_HTF_BIAS,0).astype(int)
    pop=d.regime.eq('PULLBACK')&d.G1_VOL_COMPRESSION.fillna(False)&d.D14_CONCORDANCE.ne(0)
    d=lab16.add_confirmation(d,m15,pop)
    fp=lab13.exact_first_passage(m1,d,pop); d=d.join(fp,how='left')
    q=d.loc[pop].copy(); q['HIGH75']=q.SETUP_CONFIRMATION_PCT.ge(75)
    q['D14_signed24']=q.D14_CONCORDANCE*pd.to_numeric(q.close_ret_atr_24h,errors='coerce')
    resolved=q[q.target_dir.isin([-1,1])].copy(); resolved['correct']=(resolved.D14_CONCORDANCE==resolved.target_dir).astype(float)
    if len(q)!=397 or len(resolved)!=220: raise RuntimeError(f'LAB016/17 parity failed population={len(q)} resolved={len(resolved)}')

    high=resolved[resolved.HIGH75].copy()
    h1raw=boot_side_diff(high,SEED+1)
    h1=bool(h1raw['n_bull']>=25 and h1raw['n_bear']>=25 and h1raw['observed']>0 and np.isfinite(h1raw['ci_lo']) and h1raw['ci_lo']>0)

    side_rows=[]; side_boot={}
    for i,(sgn,name) in enumerate(SIDES):
        g=high[high.D14_CONCORDANCE.eq(sgn)].copy(); b=boot_mean(g,'correct',SEED+10+i)
        follow=q[q.HIGH75&q.D14_CONCORDANCE.eq(sgn)].D14_signed24.dropna()
        side_rows.append({'side':name,'n_resolved':len(g),'accuracy':b['observed'],'ci_lo':b['ci_lo'],'ci_hi':b['ci_hi'],
                          'n_follow24':len(follow),'mean_signed24_atr':float(follow.mean()) if len(follow) else np.nan})
        side_boot[name]=b
    side_df=pd.DataFrame(side_rows)
    bull=side_boot['BULL']; bear=side_boot['BEAR']
    h2=bool(bull['n']>=30 and bull['observed']>0.60 and np.isfinite(bull['ci_lo']) and bull['ci_lo']>0.55)
    h3=bool(bear['n']>=25 and bear['observed']>0.55 and np.isfinite(bear['ci_lo']) and bear['ci_lo']>0.50)

    comp_rows=[]; strata_rows=[]
    for si,(sgn,name) in enumerate(SIDES):
        sr=resolved[resolved.D14_CONCORDANCE.eq(sgn)].copy()
        for ci,c in enumerate(COMPONENTS):
            marg=boot_binary_diff(sr,'correct',c,SEED+100+si*20+ci)
            cond=conditional_component(resolved,sgn,c)
            supportive=bool(np.isfinite(marg['observed']) and marg['observed']>0 and np.isfinite(cond['conditional_premium']) and cond['conditional_premium']>0 and max(marg['n_present']+marg['n_absent'],cond['conditional_weight'])>=20)
            comp_rows.append({'side':name,'component':c,'n_present':marg['n_present'],'n_absent':marg['n_absent'],
                              'accuracy_present':float(sr.loc[sr[c],'correct'].mean()) if int(sr[c].sum()) else np.nan,
                              'accuracy_absent':float(sr.loc[~sr[c],'correct'].mean()) if int((~sr[c]).sum()) else np.nan,
                              'marginal_premium':marg['observed'],'marginal_ci_lo':marg['ci_lo'],'marginal_ci_hi':marg['ci_hi'],
                              'conditional_premium':cond['conditional_premium'],'conditional_weight':cond['conditional_weight'],
                              'eligible_strata':cond['eligible_strata'],'directionally_supportive':supportive})
            for x in cond['strata']:
                strata_rows.append({'side':name,'component':c,**x})
    comp_df=pd.DataFrame(comp_rows); strata_df=pd.DataFrame(strata_rows)

    resolved['combo']=resolved.apply(exact_combo_name,axis=1)
    combos=[]
    for sgn,name in SIDES:
        for combo in ['NO_OB','NO_IMBALANCE','NO_LIQUIDITY','NO_PRICE_ACTION','ALL4']:
            g=resolved[(resolved.D14_CONCORDANCE==sgn)&resolved.combo.eq(combo)]
            combos.append({'side':name,'combination':combo,'n_resolved':len(g),'accuracy':float(g.correct.mean()) if len(g) else np.nan,
                           'eligible':bool(len(g)>=10)})
    combo_df=pd.DataFrame(combos)

    cand_rows=[]
    masks=candidate_masks(resolved)
    for ci,(c,m) in enumerate(masks.items()):
        for si,(sgn,name) in enumerate(SIDES):
            g=resolved[m & resolved.D14_CONCORDANCE.eq(sgn)].copy(); b=boot_mean(g,'correct',SEED+200+ci*10+si)
            capable=bool(b['n']>=25 and b['observed']>0.60 and np.isfinite(b['ci_lo']) and b['ci_lo']>0.50)
            cand_rows.append({'candidate':c,'side':name,'n_resolved':b['n'],'accuracy':b['observed'],'ci_lo':b['ci_lo'],'ci_hi':b['ci_hi'],'quality_capable':capable})
    cand_df=pd.DataFrame(cand_rows)

    verdict='DIRECTIONAL_ASYMMETRY_CONFIRMED' if h1 else 'DIRECTIONAL_ASYMMETRY_NOT_CONFIRMED'
    summary={'lab':LAB,'verdict':verdict,'population':len(q),'resolved_n':len(resolved),'high75_n':len(high),
             'h1_asymmetry_pass':h1,'h1_effect':h1raw['observed'],'h1_ci_lo':h1raw['ci_lo'],'h1_ci_hi':h1raw['ci_hi'],
             'h2_bull_high75_pass':h2,'h3_bear_high75_pass':h3,
             'bull_high75_accuracy':bull['observed'],'bull_high75_ci_lo':bull['ci_lo'],'bull_high75_n':bull['n'],
             'bear_high75_accuracy':bear['observed'],'bear_high75_ci_lo':bear['ci_lo'],'bear_high75_n':bear['n'],
             'valid_context_bars':len(allbars),'episode_onsets':len(onset)}

    side_df.to_csv(out/'high75_side_metrics.csv',index=False)
    comp_df.to_csv(out/'component_direction_metrics.csv',index=False)
    strata_df.to_csv(out/'conditional_component_strata.csv',index=False)
    combo_df.to_csv(out/'exact_composition_direction.csv',index=False)
    cand_df.to_csv(out/'candidate_direction_metrics.csv',index=False)
    resolved[['available_time','D14_CONCORDANCE','SETUP_CONFIRMATION_PCT','correct','combo']+COMPONENTS].to_csv(out/'resolved_direction_events.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=lambda x: None if pd.isna(x) else x))

    report=[f'# {LAB}','',f'**Verdict: {verdict}**','',
            f'- Population: **{len(q)}**; exact resolved: **{len(resolved)}**; HIGH75: **{len(high)}**',
            f"- H1 BULL-BEAR HIGH75 accuracy gap: **{h1raw['observed']:+.3f}**, 95% CI **[{h1raw['ci_lo']:+.3f}, {h1raw['ci_hi']:+.3f}]** — {'PASS' if h1 else 'FAIL'}",
            f"- H2 BULL HIGH75: **{bull['observed']:.3f}**, CI **[{bull['ci_lo']:.3f}, {bull['ci_hi']:.3f}]**, N={bull['n']} — {'PASS' if h2 else 'FAIL'}",
            f"- H3 BEAR HIGH75: **{bear['observed']:.3f}**, CI **[{bear['ci_lo']:.3f}, {bear['ci_hi']:.3f}]**, N={bear['n']} — {'PASS' if h3 else 'FAIL'}",'',
            '## HIGH75 side metrics','',side_df.to_markdown(index=False,floatfmt='.3f'),'',
            '## Component value by direction','',comp_df.to_markdown(index=False,floatfmt='.3f'),'',
            '## Exact 3-of-4 / 4-of-4 compositions','',combo_df.to_markdown(index=False,floatfmt='.3f'),'',
            '## Predeclared candidate diagnostics','',cand_df.to_markdown(index=False,floatfmt='.3f'),'',
            '## Constraints','',
            '- Frozen LAB016 definitions and equal 25% weights; no tuning in LAB018.',
            '- Reused-history directional robustness audit, not fresh OOS validation.',
            '- Confirmation % is evidence coverage, NOT probability of profit and NOT automatic-entry permission.']
    (out/'REPORT.md').write_text('\n'.join(report))
    print('\n'.join(report[:12]))

if __name__=='__main__': main()
