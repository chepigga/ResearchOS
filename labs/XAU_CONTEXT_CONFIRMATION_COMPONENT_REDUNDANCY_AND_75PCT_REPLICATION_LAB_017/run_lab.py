#!/usr/bin/env python3
from __future__ import annotations

import argparse, importlib.util, json, math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_CONFIRMATION_COMPONENT_REDUNDANCY_AND_75PCT_REPLICATION_LAB_017'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB16_PATH=ROOT/'labs'/'XAU_CONTEXT_SETUP_CONFIRMATION_OB_IMBALANCE_LIQUIDITY_PRICE_ACTION_LAB_016'/'run_lab.py'
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
LAB13_PATH=ROOT/'labs'/'XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013'/'run_lab.py'
XAU_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
COMPONENTS=['OB_CONFIRM','IMBALANCE_CONFIRM','LIQUIDITY_CONFIRM','PRICE_ACTION_CONFIRM']
BOOT_N=5000
SEED=2026091217


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def pair_stats(q:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for a,b in combinations(COMPONENTS,2):
        x=q[a].astype(bool).to_numpy(); y=q[b].astype(bool).to_numpy()
        n11=int(np.sum(x&y)); n10=int(np.sum(x&~y)); n01=int(np.sum(~x&y)); n00=int(np.sum(~x&~y)); n=len(q)
        den=math.sqrt((n11+n10)*(n01+n00)*(n11+n01)*(n10+n00))
        phi=((n11*n00-n10*n01)/den) if den>0 else np.nan
        jac=(n11/(n11+n10+n01)) if (n11+n10+n01)>0 else np.nan
        agreement=(n11+n00)/n if n else np.nan
        critical=bool(np.isfinite(phi) and np.isfinite(jac) and abs(phi)>=0.80 and jac>=0.80)
        rows.append({'component_a':a,'component_b':b,'n11':n11,'n10':n10,'n01':n01,'n00':n00,
                     'phi':phi,'jaccard_positive':jac,'agreement':agreement,'critically_redundant':critical})
    return pd.DataFrame(rows)


def conditional_incremental(resolved:pd.DataFrame)->tuple[pd.DataFrame,pd.DataFrame]:
    details=[]; summary=[]
    for c in COMPONENTS:
        others=[x for x in COMPONENTS if x!=c]
        z=resolved.copy()
        z['_stratum']=z[others].astype(int).astype(str).agg(''.join,axis=1)
        effects=[]; weights=[]
        for pattern,g in z.groupby('_stratum'):
            p=g[g[c]]; a=g[~g[c]]
            if len(p)>=5 and len(a)>=5:
                ep=float(p.correct.mean()-a.correct.mean()); w=min(len(p),len(a))
                effects.append(ep); weights.append(w)
                details.append({'component':c,'other_pattern':pattern,'n_present':len(p),'n_absent':len(a),
                                'accuracy_present':float(p.correct.mean()),'accuracy_absent':float(a.correct.mean()),
                                'effect':ep,'weight':w})
        agg=float(np.average(effects,weights=weights)) if weights else np.nan
        summary.append({'component':c,'eligible_strata':len(effects),'weighted_conditional_accuracy_premium':agg,
                        'total_weight':int(sum(weights))})
    return pd.DataFrame(summary),pd.DataFrame(details)


def union_domains(pairdf:pd.DataFrame)->list[list[str]]:
    parent={c:c for c in COMPONENTS}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[rb]=ra
    for _,r in pairdf[pairdf.critically_redundant].iterrows():
        union(str(r.component_a),str(r.component_b))
    groups={}
    for c in COMPONENTS: groups.setdefault(find(c),[]).append(c)
    return list(groups.values())


def bootstrap_mean(lab16,q:pd.DataFrame,metric:str,seed:int)->dict:
    return lab16.cluster_boot_mean(q,metric,seed)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1)

    lab16=load_module(LAB16_PATH,'lab16_017')
    if lab16.sha256(p)!=XAU_SHA: raise RuntimeError('Canonical XAU SHA mismatch')
    lab8=load_module(LAB8_PATH,'lab8_017'); lab9=load_module(LAB9_PATH,'lab9_017')
    lab10=load_module(LAB10_PATH,'lab10_017'); lab13=load_module(LAB13_PATH,'lab13_017')

    m1=lab8.read_xau_native(p); m15=lab16.to_m15(m1); h4=lab8.to_h4(m1); router=lab8.load_router_module()
    ctx=router.add_router(h4); ctx=lab8.add_forward_metrics(ctx); ctx=ctx.dropna(subset=['available_time','atr14']).copy()
    allbars,onset=lab8.make_episodes(ctx)
    if len(allbars)!=6216 or len(onset)!=610: raise RuntimeError(f'Parity failed bars={len(allbars)} episodes={len(onset)}')
    d=lab9.add_roles(allbars); d=lab10.add_components_and_candidates(d); d=lab13.add_prediction_candidates(d)
    d['D14_CONCORDANCE']=np.where((d.D1_HTF_BIAS==d.D2_TREND_PRESSURE)&d.D1_HTF_BIAS.ne(0),d.D1_HTF_BIAS,0).astype(int)
    pop=d.regime.eq('PULLBACK')&d.G1_VOL_COMPRESSION.fillna(False)&d.D14_CONCORDANCE.ne(0)
    d=lab16.add_confirmation(d,m15,pop)
    fp=lab13.exact_first_passage(m1,d,pop); d=d.join(fp,how='left')
    q=d.loc[pop].copy()
    q['HIGH75']=q.SETUP_CONFIRMATION_PCT.ge(75)
    resolved=q[q.target_dir.isin([-1,1])].copy()
    resolved['correct']=(resolved.D14_CONCORDANCE==resolved.target_dir).astype(float)

    # Redundancy diagnostics on full population.
    pairs=pair_stats(q)
    critical=pairs[pairs.critically_redundant].copy()
    domains=union_domains(pairs)

    # Conditional incremental diagnostics on exact-resolved population.
    cond_summary,cond_detail=conditional_incremental(resolved)

    # H1 absolute HIGH75 replication.
    hi75=resolved[resolved.HIGH75].copy()
    h1raw=bootstrap_mean(lab16,hi75,'correct',SEED+1)
    h1=bool(len(hi75)>=60 and h1raw['observed']>0.55 and np.isfinite(h1raw['ci_lo']) and h1raw['ci_lo']>0.50)

    # H2 exact 3/4 composition robustness.
    combo_rows=[]
    exact3=resolved[resolved[COMPONENTS].astype(int).sum(axis=1).eq(3)].copy()
    for missing in COMPONENTS:
        mask=(~exact3[missing])
        for c in [x for x in COMPONENTS if x!=missing]: mask &= exact3[c]
        g=exact3[mask].copy(); n=len(g); acc=float(g.correct.mean()) if n else np.nan
        combo_rows.append({'combination':'NO_'+missing.replace('_CONFIRM',''),'missing_component':missing,
                           'n_resolved':n,'accuracy':acc,'eligible':bool(n>=15),'positive':bool(n>=15 and acc>0.50),
                           'fragile_low':bool(n>=15 and acc<0.45)})
    combos=pd.DataFrame(combo_rows)
    eligible_combos=int(combos.eligible.sum()); positive_combos=int(combos.positive.sum()); fragile_any=bool(combos.fragile_low.any())
    h2=bool(eligible_combos>=3 and positive_combos>=3 and not fragile_any)

    all4=resolved[resolved[COMPONENTS].all(axis=1)].copy()
    all4_acc=float(all4.correct.mean()) if len(all4) else np.nan

    # H3 collapsed-domain robustness only when critical redundancy exists.
    h3_applicable=bool(len(critical)>0); h3=False; h3raw={'observed':np.nan,'ci_lo':np.nan,'ci_hi':np.nan,'n':0,'weeks':0}
    collapsed_n=0
    if h3_applicable:
        strong=pd.Series(True,index=resolved.index)
        for members in domains:
            strong &= resolved[members].any(axis=1)
        cres=resolved[strong].copy(); collapsed_n=len(cres); h3raw=bootstrap_mean(lab16,cres,'correct',SEED+3)
        h3=bool(collapsed_n>=40 and h3raw['observed']>0.55 and np.isfinite(h3raw['ci_lo']) and h3raw['ci_lo']>0.50)

    # H4 BULL / BEAR side symmetry at HIGH75.
    side_rows=[]
    for sign,name in [(1,'BULL'),(-1,'BEAR')]:
        g=hi75[hi75.D14_CONCORDANCE.eq(sign)]; n=len(g); acc=float(g.correct.mean()) if n else np.nan
        side_rows.append({'side':name,'n_resolved':n,'accuracy':acc})
    sides=pd.DataFrame(side_rows)
    bull=sides[sides.side.eq('BULL')].iloc[0]; bear=sides[sides.side.eq('BEAR')].iloc[0]
    h4=bool(bull.n_resolved>=20 and bear.n_resolved>=20 and bull.accuracy>0.50 and bear.accuracy>0.50 and abs(bull.accuracy-bear.accuracy)<=0.15)

    if not h1:
        verdict='75PCT_NOT_REPLICATED'
    elif not h2 or not h4 or (h3_applicable and not h3):
        verdict='75PCT_COMPOSITION_FRAGILE'
    elif h3_applicable:
        verdict='75PCT_ROBUST_WITH_REDUNDANCY'
    else:
        verdict='75PCT_ROBUST_NO_CRITICAL_REDUNDANCY'

    pairs.to_csv(out/'pairwise_redundancy.csv',index=False)
    cond_summary.to_csv(out/'conditional_incremental_summary.csv',index=False)
    cond_detail.to_csv(out/'conditional_incremental_strata.csv',index=False)
    combos.to_csv(out/'exact75_combinations.csv',index=False)
    sides.to_csv(out/'high75_side_symmetry.csv',index=False)

    summary={
        'lab':LAB,'verdict':verdict,'population':int(len(q)),'resolved_n':int(len(resolved)),
        'high75_n':int(len(hi75)),'high75_accuracy':float(h1raw['observed']),'high75_ci_lo':float(h1raw['ci_lo']),
        'high75_ci_hi':float(h1raw['ci_hi']),'h1_pass':h1,'h2_pass':h2,'eligible_3of4_combinations':eligible_combos,
        'positive_3of4_combinations':positive_combos,'critical_redundancy_pairs':int(len(critical)),
        'critical_pairs':[f"{r.component_a}__{r.component_b}" for _,r in critical.iterrows()],
        'collapsed_domains':domains,'h3_applicable':h3_applicable,'h3_n':int(collapsed_n),
        'h3_accuracy':float(h3raw['observed']) if np.isfinite(h3raw['observed']) else None,
        'h3_ci_lo':float(h3raw['ci_lo']) if np.isfinite(h3raw['ci_lo']) else None,'h3_pass':h3 if h3_applicable else None,
        'h4_pass':h4,'all4_n':int(len(all4)),'all4_accuracy':all4_acc,
        'valid_context_bars':int(len(allbars)),'episode_onsets':int(len(onset))
    }
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    def fmt(x,d=3):
        return 'NA' if x is None or not np.isfinite(float(x)) else f'{float(x):.{d}f}'
    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',
           f'- Population: **{len(q)}**; exact resolved: **{len(resolved)}**',
           f'- HIGH75: **N={len(hi75)}**, accuracy **{fmt(h1raw["observed"],3)}**, 95% CI **[{fmt(h1raw["ci_lo"],3)}, {fmt(h1raw["ci_hi"],3)}]** — H1 **{"PASS" if h1 else "FAIL"}**',
           f'- Critical redundancy pairs: **{len(critical)}**',
           f'- H2 composition robustness: **{"PASS" if h2 else "FAIL"}** ({positive_combos}/{eligible_combos} eligible combinations >50%)',
           f'- H3 collapsed-domain robustness: **{"N/A" if not h3_applicable else ("PASS" if h3 else "FAIL")}**',
           f'- H4 BULL/BEAR symmetry: **{"PASS" if h4 else "FAIL"}**','',
           '## Pairwise redundancy','',pairs.to_markdown(index=False,floatfmt='.3f'),'','## Exact 75% combinations','',
           combos.to_markdown(index=False,floatfmt='.3f'),'','## 100% bucket','',
           f'- N_resolved: **{len(all4)}**; accuracy: **{fmt(all4_acc,3)}**','',
           '## Conditional incremental value','',cond_summary.to_markdown(index=False,floatfmt='.3f'),'','## HIGH75 side symmetry','',
           sides.to_markdown(index=False,floatfmt='.3f'),'','## Constraints','',
           '- Frozen LAB016 confirmation definitions and equal 25% weights.','- Reused-history robustness audit, not fresh OOS validation.',
           '- Confirmation % is evidence coverage, NOT probability of profit and NOT automatic-entry permission.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print('\n'.join(lines[:12]))

if __name__=='__main__': main()
