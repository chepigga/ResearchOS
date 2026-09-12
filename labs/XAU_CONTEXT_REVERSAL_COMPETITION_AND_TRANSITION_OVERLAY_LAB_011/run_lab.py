#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = 'XAU_CONTEXT_REVERSAL_COMPETITION_AND_TRANSITION_OVERLAY_LAB_011'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAB8_PATH = ROOT / 'labs' / 'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008' / 'run_lab.py'
LAB9_PATH = ROOT / 'labs' / 'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009' / 'run_lab.py'
LAB10_PATH = ROOT / 'labs' / 'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010' / 'run_lab.py'
XAU_SHA = 'db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
YEARS = [2023, 2024, 2025, 2026]
BOOT_N = 5000
SEED = 2026091211
MAIN_REV_STATES = ['PULLBACK', 'EXPANSION', 'RANGE']
MAIN_COMP_STATES = ['PULLBACK', 'EXPANSION']


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def week_col(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).dt.to_period('W-SUN').astype(str)


def add_competition_fields(d: pd.DataFrame) -> pd.DataFrame:
    z = d.copy().sort_index()
    score_cols = ['score_expansion', 'score_pullback', 'score_reversal', 'score_range']
    scores = z[score_cols].apply(pd.to_numeric, errors='coerce')
    sm = scores.rolling(3, min_periods=3).mean()
    for c in score_cols:
        z[f'sm_{c}'] = sm[c]

    z['SM_REV_WINNER'] = sm['score_reversal'].ge(sm.max(axis=1)).fillna(False)
    ev = z['R3_RAW_REVERSAL_WINNER'].fillna(False).astype(bool)
    admitted = ev & z['regime'].eq('REVERSAL')
    smooth_supp = ev & (~z['regime'].eq('REVERSAL')) & (~z['SM_REV_WINNER'])
    hyst_supp = ev & (~z['regime'].eq('REVERSAL')) & z['SM_REV_WINNER']
    z['competition_class'] = np.select(
        [admitted, smooth_supp, hyst_supp],
        ['ADMITTED_REVERSAL', 'SMOOTHING_SUPPRESSED', 'HYSTERESIS_SUPPRESSED'],
        default='NO_R3_EVENT'
    )
    if int((ev & z['competition_class'].eq('NO_R3_EVENT')).sum()) != 0:
        raise RuntimeError('Unclassified R3 events')

    state_score = {
        'PULLBACK': 'score_pullback', 'EXPANSION': 'score_expansion',
        'RANGE': 'score_range', 'REVERSAL': 'score_reversal'
    }
    z['raw_current_state_score'] = np.nan
    z['sm_current_state_score'] = np.nan
    for state, col in state_score.items():
        m = z['regime'].eq(state)
        z.loc[m, 'raw_current_state_score'] = scores.loc[m, col]
        z.loc[m, 'sm_current_state_score'] = sm.loc[m, col]
    z['raw_rev_lead_vs_state'] = scores['score_reversal'] - z['raw_current_state_score']
    z['sm_rev_lead_vs_state'] = sm['score_reversal'] - z['sm_current_state_score']
    z['breakout_1atr_4h'] = 1.0 - pd.to_numeric(z['contained_1atr_4h'], errors='coerce')
    z['breakout_1atr_8h'] = 1.0 - pd.to_numeric(z['contained_1atr_8h'], errors='coerce')
    z['breakout_1atr_12h'] = 1.0 - pd.to_numeric(z['contained_1atr_12h'], errors='coerce')
    return z


def strat_effect(x: pd.DataFrame, metric: str, mask_a: pd.Series, mask_b: pd.Series, states: list[str]):
    q = x[['regime', metric]].copy()
    q[metric] = pd.to_numeric(q[metric], errors='coerce')
    q['A'] = mask_a.reindex(q.index).fillna(False).astype(bool)
    q['B'] = mask_b.reindex(q.index).fillna(False).astype(bool)
    q = q[q['regime'].isin(states)].dropna(subset=[metric])
    rows = []
    total_a = 0
    for s in states:
        g = q[q.regime.eq(s)]
        va = g.loc[g.A, metric]
        vb = g.loc[g.B, metric]
        if len(va) and len(vb):
            rows.append((s, len(va), len(vb), float(va.mean() - vb.mean())))
            total_a += len(va)
    if total_a == 0:
        return np.nan, rows
    obs = sum(na / total_a * eff for _, na, _, eff in rows)
    return float(obs), rows


def strat_bootstrap(x: pd.DataFrame, metric: str, mask_a: pd.Series, mask_b: pd.Series,
                    states: list[str], seed: int) -> dict:
    q = x[['available_time', 'regime', metric]].copy()
    q[metric] = pd.to_numeric(q[metric], errors='coerce')
    q['A'] = mask_a.reindex(q.index).fillna(False).astype(bool)
    q['B'] = mask_b.reindex(q.index).fillna(False).astype(bool)
    q = q[q.regime.isin(states)].dropna(subset=['available_time', metric])
    obs, strata = strat_effect(q, metric, q['A'], q['B'], states)
    n_a = int(q.A.sum()); n_b = int(q.B.sum())
    q['week'] = week_col(q.available_time)
    weeks = sorted(q.week.unique())
    sidx = {s:i for i,s in enumerate(states)}
    arr = np.zeros((len(weeks), len(states), 4), float)  # nA,sumA,nB,sumB
    for wi, w in enumerate(weeks):
        g = q[q.week.eq(w)]
        for s in states:
            h = g[g.regime.eq(s)]
            a = h.loc[h.A, metric].to_numpy(float)
            b = h.loc[h.B, metric].to_numpy(float)
            arr[wi, sidx[s], :] = [len(a), np.nansum(a), len(b), np.nansum(b)]
    rng = np.random.default_rng(seed)
    draws = []
    m = len(weeks)
    for _ in range(BOOT_N):
        t = arr[rng.integers(0, m, size=m)].sum(axis=0)
        effects = []
        total_a = 0.0
        for si, s in enumerate(states):
            na, sa, nb, sb = t[si]
            if na > 0 and nb > 0:
                effects.append((na, sa/na - sb/nb))
                total_a += na
        if total_a > 0:
            draws.append(sum(na/total_a * e for na,e in effects))
    draws = np.asarray(draws, float)
    return {
        'observed': obs,
        'ci_lo': float(np.quantile(draws, .025)) if len(draws) else np.nan,
        'ci_hi': float(np.quantile(draws, .975)) if len(draws) else np.nan,
        'p_positive': float(np.mean(draws > 0)) if len(draws) else np.nan,
        'n_a': n_a, 'n_b': n_b, 'weeks': int(m),
        'strata': [{'state':s,'n_a':int(na),'n_b':int(nb),'effect':eff} for s,na,nb,eff in strata]
    }


def annual_stratified(d: pd.DataFrame, metric: str, a_col: str, states: list[str], min_a: int) -> pd.DataFrame:
    y = pd.to_datetime(d.available_time).dt.year
    rows = []
    for year in YEARS:
        g = d[y.eq(year)].copy()
        valid = pd.to_numeric(g[metric], errors='coerce').notna()
        a = g[a_col].fillna(False).astype(bool) & valid & g.regime.isin(states)
        b = (~g[a_col].fillna(False).astype(bool)) & valid & g.regime.isin(states)
        obs, strata = strat_effect(g, metric, a, b, states)
        n_a = int(a.sum())
        eligible = bool(n_a >= min_a and np.isfinite(obs))
        rows.append({'year':year,'metric':metric,'n_a':n_a,'n_b':int(b.sum()),'effect':obs,
                     'eligible':eligible,'positive':bool(eligible and obs > 0),
                     'strata_json':json.dumps([{'state':s,'n_a':int(na),'n_b':int(nb),'effect':eff} for s,na,nb,eff in strata])})
    return pd.DataFrame(rows)


def per_state_premiums(d: pd.DataFrame, metric: str, a_col: str, states: list[str]) -> pd.DataFrame:
    rows=[]
    for s in states:
        g=d[d.regime.eq(s)]
        v=pd.to_numeric(g[metric],errors='coerce')
        a=g[a_col].fillna(False).astype(bool) & v.notna()
        b=(~g[a_col].fillna(False).astype(bool)) & v.notna()
        va=v[a]; vb=v[b]
        rows.append({'state':s,'metric':metric,'n_a':int(len(va)),'n_b':int(len(vb)),
                     'effect':float(va.mean()-vb.mean()) if len(va) and len(vb) else np.nan})
    return pd.DataFrame(rows)


def first_touch_proxy(d: pd.DataFrame) -> pd.DataFrame:
    z=d.copy().sort_index()
    out=np.full(len(z), np.nan)
    idx=pd.Series(z.index,index=z.index)
    for k,h in [(1,4),(2,8),(3,12)]:
        valid=(idx.shift(-k)-idx).eq(pd.Timedelta(hours=h))
        hi=z.high.shift(-k); lo=z.low.shift(-k)
        up=z.close+z.atr14; dn=z.close-z.atr14
        hit=valid & ((hi>=up)|(lo<=dn))
        out[(np.isnan(out)) & hit.to_numpy()] = h
    z['first_touch_1atr_h_proxy']=out
    return z


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1); actual=sha256(p)
    if actual != XAU_SHA: raise RuntimeError(f'Canonical XAU SHA mismatch: {actual}')

    lab8=load_module(LAB8_PATH,'lab8_overlay11'); lab9=load_module(LAB9_PATH,'lab9_overlay11'); lab10=load_module(LAB10_PATH,'lab10_overlay11')
    m1=lab8.read_xau_native(p); h4=lab8.to_h4(m1); router=lab8.load_router_module()
    ctx=router.add_router(h4); ctx=lab8.add_forward_metrics(ctx); ctx=ctx.dropna(subset=['available_time','atr14']).copy()
    allbars,onset=lab8.make_episodes(ctx)
    if len(allbars)!=6216 or len(onset)!=610: raise RuntimeError(f'Parity failed bars={len(allbars)} onset={len(onset)}')
    d=lab9.add_roles(allbars); d=lab10.add_components_and_candidates(d); d=add_competition_fields(d); d=first_touch_proxy(d)

    # Reversal overlay: suppressed R3 events only.
    suppressed=d.competition_class.isin(['SMOOTHING_SUPPRESSED','HYSTERESIS_SUPPRESSED']) & d.regime.isin(MAIN_REV_STATES)
    d['R_SUPPRESSED_OVERLAY']=suppressed
    valid24=pd.to_numeric(d.momentum_flip_24h,errors='coerce').notna()
    ra=suppressed & valid24; rb=(~d.R3_RAW_REVERSAL_WINNER) & d.regime.isin(MAIN_REV_STATES) & valid24
    r_primary=strat_bootstrap(d,'momentum_flip_24h',ra,rb,MAIN_REV_STATES,SEED+1)
    r_year=annual_stratified(d,'momentum_flip_24h','R_SUPPRESSED_OVERLAY',MAIN_REV_STATES,10)
    r_state=per_state_premiums(d,'momentum_flip_24h','R_SUPPRESSED_OVERLAY',MAIN_REV_STATES)
    r_n2025=int(r_year.loc[r_year.year.eq(2025),'n_a'].iloc[0]); r_n2026=int(r_year.loc[r_year.year.eq(2026),'n_a'].iloc[0])
    eligible_strata=int((r_state.n_a>=10).sum())
    r_eligible=bool(r_primary['n_a']>=50 and r_n2025>=10 and r_n2026>=10 and eligible_strata>=2)
    r_transfer=bool(len(r_year)==4 and r_year.eligible.all() and int(r_year.positive.sum())>=3)
    r_h1=bool(r_eligible and r_primary['observed']>0 and np.isfinite(r_primary['ci_lo']) and r_primary['ci_lo']>0 and r_transfer)
    elig20=r_state[r_state.n_a>=20]
    r_h2=bool(len(elig20)>=2 and int((elig20.effect>0).sum())>=2 and not (elig20.effect<=-0.05).any())

    # Reversal secondary horizons/classes.
    r_secondary=[]
    for i,h in enumerate([8,12]):
        metric=f'momentum_flip_{h}h'; valid=pd.to_numeric(d[metric],errors='coerce').notna()
        a=suppressed & valid; b=(~d.R3_RAW_REVERSAL_WINNER) & d.regime.isin(MAIN_REV_STATES) & valid
        rec=strat_bootstrap(d,metric,a,b,MAIN_REV_STATES,SEED+10+i); rec.update(horizon_h=h,metric=metric); r_secondary.append(rec)
    class_rows=[]
    for cls in ['SMOOTHING_SUPPRESSED','HYSTERESIS_SUPPRESSED']:
        a=d.competition_class.eq(cls) & valid24 & d.regime.isin(MAIN_REV_STATES)
        rec=strat_bootstrap(d,'momentum_flip_24h',a,rb,MAIN_REV_STATES,SEED+20+len(class_rows)); rec.update(competition_class=cls); class_rows.append(rec)

    comp_diag=(d[d.R3_RAW_REVERSAL_WINNER].groupby(['competition_class','regime']).agg(
        events=('R3_RAW_REVERSAL_WINNER','sum'),raw_lead_mean=('raw_rev_lead_vs_state','mean'),sm_lead_mean=('sm_rev_lead_vs_state','mean')).reset_index())
    comp_year=(d[d.R3_RAW_REVERSAL_WINNER].assign(year=pd.to_datetime(d.loc[d.R3_RAW_REVERSAL_WINNER,'available_time']).dt.year)
               .groupby(['year','competition_class']).size().rename('events').reset_index())

    # Compression overlay inside Pullback/Expansion.
    d['C_G1_OVERLAY']=d.G1_VOL_COMPRESSION & d.regime.isin(MAIN_COMP_STATES)
    c_results=[]; c_year_tables=[]
    for j,(name,metric,min_year) in enumerate([('C_H1','breakout_1atr_8h',50),('C_H2','range_atr_24h',50)]):
        valid=pd.to_numeric(d[metric],errors='coerce').notna()
        a=d.C_G1_OVERLAY & valid; b=(~d.G1_VOL_COMPRESSION) & d.regime.isin(MAIN_COMP_STATES) & valid
        rec=strat_bootstrap(d,metric,a,b,MAIN_COMP_STATES,SEED+100+j)
        yr=annual_stratified(d,metric,'C_G1_OVERLAY',MAIN_COMP_STATES,min_year)
        transfer=bool(len(yr)==4 and yr.eligible.all() and int(yr.positive.sum())>=3)
        state=per_state_premiums(d,metric,'C_G1_OVERLAY',MAIN_COMP_STATES)
        n25=int(yr.loc[yr.year.eq(2025),'n_a'].iloc[0]); n26=int(yr.loc[yr.year.eq(2026),'n_a'].iloc[0])
        if name=='C_H1':
            eligible=bool(rec['n_a']>=200 and (state.n_a>=50).all() and n25>=50 and n26>=50)
        else:
            eligible=bool(rec['n_a']>=200 and (state.n_a>=50).all())
        passed=bool(eligible and rec['observed']>0 and np.isfinite(rec['ci_lo']) and rec['ci_lo']>0 and transfer)
        c_results.append({'gate':name,'metric':metric,'eligible':eligible,'transfer':transfer,'passed':passed,**{k:v for k,v in rec.items() if k!='strata'}})
        yr.insert(0,'gate',name); c_year_tables.append(yr)
        state.to_csv(out/f'{name.lower()}_state_premiums.csv',index=False)

    c_h1=bool(c_results[0]['passed']); c_h2=bool(c_results[1]['passed'])
    c_secondary=[]
    for i,h in enumerate([4,12]):
        metric=f'breakout_1atr_{h}h'; valid=pd.to_numeric(d[metric],errors='coerce').notna()
        a=d.C_G1_OVERLAY & valid; b=(~d.G1_VOL_COMPRESSION) & d.regime.isin(MAIN_COMP_STATES) & valid
        rec=strat_bootstrap(d,metric,a,b,MAIN_COMP_STATES,SEED+120+i); rec.update(horizon_h=h,metric=metric); c_secondary.append(rec)

    touch=(d[d.C_G1_OVERLAY & d.first_touch_1atr_h_proxy.notna()].groupby('regime').first_touch_1atr_h_proxy.describe().reset_index())

    gates={'R_H1':r_h1,'R_H2':r_h2,'C_H1':c_h1,'C_H2':c_h2}
    passed=sum(gates.values())
    if r_h1 and r_h2 and c_h1 and c_h2:
        verdict='TRANSITION_OVERLAY_ARCHITECTURE_SUPPORTED_DISCOVERY_ONLY'
    elif (r_h1 and r_h2) or (c_h1 and c_h2) or (passed>=2 and (r_h1 or r_h2) and (c_h1 or c_h2)):
        verdict='PARTIAL_TRANSITION_OVERLAY_SUPPORT'
    elif (not r_eligible) and (not c_results[0]['eligible']):
        verdict='TRANSITION_OVERLAY_ARCHITECTURE_UNDERPOWERED'
    else:
        verdict='TRANSITION_OVERLAY_ARCHITECTURE_NOT_SUPPORTED'

    pd.DataFrame([{'gate':'R_H1','eligible':r_eligible,'transfer':r_transfer,'passed':r_h1,**{k:v for k,v in r_primary.items() if k!='strata'}},
                  {'gate':'R_H2','eligible':len(elig20)>=2,'transfer':np.nan,'passed':r_h2,'observed':np.nan,'ci_lo':np.nan,'ci_hi':np.nan,'p_positive':np.nan,'n_a':int(r_state.n_a.sum()),'n_b':int(r_state.n_b.sum()),'weeks':np.nan}]+c_results).to_csv(out/'primary_gates.csv',index=False)
    r_year.to_csv(out/'reversal_year_transfer.csv',index=False); r_state.to_csv(out/'reversal_state_premiums.csv',index=False)
    pd.DataFrame(r_secondary).drop(columns=['strata'],errors='ignore').to_csv(out/'reversal_secondary_horizons.csv',index=False)
    pd.DataFrame(class_rows).drop(columns=['strata'],errors='ignore').to_csv(out/'reversal_competition_class_semantics.csv',index=False)
    comp_diag.to_csv(out/'reversal_competition_diagnostic.csv',index=False); comp_year.to_csv(out/'reversal_competition_year_counts.csv',index=False)
    pd.concat(c_year_tables,ignore_index=True).to_csv(out/'compression_year_transfer.csv',index=False)
    pd.DataFrame(c_secondary).drop(columns=['strata'],errors='ignore').to_csv(out/'compression_secondary_horizons.csv',index=False)
    touch.to_csv(out/'compression_first_touch_proxy.csv',index=False)

    summary={'lab':LAB,'status':'REUSED_HISTORY_PREREGISTERED_OVERLAY_ARCHITECTURE_DIAGNOSTIC','verdict':verdict,
             'xau_sha256':actual,'valid_context_bars':int(len(allbars)),'episode_onsets':int(len(onset)),
             'r3_events':int(d.R3_RAW_REVERSAL_WINNER.sum()),'suppressed_r3_events':int(suppressed.sum()),
             'competition_counts':d.loc[d.R3_RAW_REVERSAL_WINNER,'competition_class'].value_counts().to_dict(),
             'g1_main_state_bars':int(d.C_G1_OVERLAY.sum()),'gates':gates,
             'reversal_primary':{**{k:v for k,v in r_primary.items() if k!='strata'},'eligible':r_eligible,'transfer':r_transfer},
             'compression_primary':c_results,'promotion_authorized':False,'trading_edge_tested':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',
           '> Persistent-state + transition-overlay diagnostic only. No trading edge or execution claim.','',
           f'- Valid Context H4 bars: **{len(allbars):,}**',f'- Frozen episodes: **{len(onset):,}**',
           f'- R3 raw-reversal events: **{int(d.R3_RAW_REVERSAL_WINNER.sum())}**',f'- Suppressed R3 overlay events: **{int(suppressed.sum())}**',
           f'- G1 compression bars inside Pullback/Expansion: **{int(d.C_G1_OVERLAY.sum())}**','',
           '## Primary gates','', '| Gate | Eligible | Effect | 95% CI | Transfer | Pass |','|---|---|---:|---:|---|---|',
           f"| R-H1 suppressed reversal overlay | {'YES' if r_eligible else 'NO'} | {r_primary['observed']:+.4f} | [{r_primary['ci_lo']:+.4f}, {r_primary['ci_hi']:+.4f}] | {'PASS' if r_transfer else 'FAIL'} | {'PASS' if r_h1 else 'FAIL'} |",
           f"| R-H2 cross-main-state robustness | {'YES' if len(elig20)>=2 else 'NO'} | — | — | — | {'PASS' if r_h2 else 'FAIL'} |"]
    for c in c_results:
        lines.append(f"| {c['gate']} {c['metric']} | {'YES' if c['eligible'] else 'NO'} | {c['observed']:+.4f} | [{c['ci_lo']:+.4f}, {c['ci_hi']:+.4f}] | {'PASS' if c['transfer'] else 'FAIL'} | {'PASS' if c['passed'] else 'FAIL'} |")
    lines += ['', '## Reversal competition', '', '| Class | Events |', '|---|---:|']
    for k,v in summary['competition_counts'].items(): lines.append(f'| {k} | {v} |')
    lines += ['', '## Reversal overlay by main state', '', '| State | N overlay | N control | 24h flip premium |','|---|---:|---:|---:|']
    for r in r_state.itertuples(): lines.append(f'| {r.state} | {r.n_a} | {r.n_b} | {r.effect:+.4f} |')
    lines += ['', '## Interpretation constraints','',
              '- R3 and G1 were frozen before outcomes; LAB011 does not search new thresholds.',
              '- Primary comparisons are state-stratified: an overlay must add information beyond the persistent main state.',
              '- Suppressed reversal events are precisely the events a parallel overlay could show while the main state remains unchanged.',
              '- Reused history: even a pass remains discovery-only and cannot authorize automated entries or risk changes.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print((out/'REPORT.md').read_text())


if __name__=='__main__':
    main()
