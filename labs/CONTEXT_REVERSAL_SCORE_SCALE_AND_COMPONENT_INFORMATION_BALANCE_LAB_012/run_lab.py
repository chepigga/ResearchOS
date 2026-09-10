#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='CONTEXT_REVERSAL_SCORE_SCALE_AND_COMPONENT_INFORMATION_BALANCE_LAB_012'
ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'labs'/'CONTEXT_INDICATOR_PUBLIC_SPEC_GAP_CLOSURE_AND_NEXT_CONTEXT_LAB_010'/'run_lab.py'
REGIMES=['EXPANSION','PULLBACK','REVERSAL','RANGE']

def load_parent():
    sp=importlib.util.spec_from_file_location('ctx010_for_012',PARENT)
    m=importlib.util.module_from_spec(sp); assert sp.loader is not None; sp.loader.exec_module(m); return m

def components(d):
    stack=d['stack'].fillna(False)
    mindist=pd.concat([d.dist20_atr,d.dist50_atr],axis=1).min(axis=1)
    trend_d1=d.d1_bias.isin(['BULL','BEAR']); liquid=d.session.isin(['LONDON','OVERLAP','NEWYORK'])
    prev=d.rsi14.shift(1); turn=((prev<35)&(d.rsi14>prev))|((prev>65)&(d.rsi14<prev))
    rhythm=(d.rsi_rhythm_up.ne(d.rsi_rhythm_up.shift(1))) & d.rsi_ema9.notna() & d.rsi_wma45.notna()
    return {
      'EXPANSION':{'ema_stack':25*stack.astype(float),'bos':20*d.bos.astype(float),'atr_gt_1p05':10*(d.atr_ratio_public>1.05),'atr_gt_1p20':10*(d.atr_ratio_public>1.20),'adx_ge20':15*(d.adx14>=20),'relvol_ge1p05':10*(d.relvol20_public>=1.05),'d1_trend':5*trend_d1.astype(float),'liquid_session':5*liquid.astype(float)},
      'PULLBACK':{'ema_stack':30*stack.astype(float),'near_ema_le065':25*(mindist<=.65),'near_ema_065_1':15*((mindist>.65)&(mindist<=1.0)),'rsi_mid':10*((d.rsi14>=35)&(d.rsi14<=65)),'adx_ge18':10*(d.adx14>=18),'not_bos_atr_le140':10*((~d.bos)&(d.atr_ratio_public<=1.40)),'d1_trend':5*trend_d1.astype(float),'inside_day':5*d.daily_inside_bar.fillna(False).astype(float)},
      'REVERSAL':{'swing_sweep':30*d.swing_sweep.astype(float),'rsi_turn':20*turn.astype(float),'rsi_rhythm_turn':15*rhythm.astype(float),'ema20_cross':15*d.cross_ema20.astype(float),'adx_decay':10*(d.adx14<d.adx14.shift(1)),'rejection_wick':10*(d.rejection_wick>=.45)},
      'RANGE':{'adx_lt20':25*(d.adx14<20),'range24_compression':25*(d.range24_ratio<.85),'ema_spread_lt1':20*(d.ema_spread_atr<1.0),'atr_lt095':15*(d.atr_ratio_public<.95),'not_stack':10*(~stack).astype(float),'inside_day':5*d.daily_inside_bar.fillna(False).astype(float)} }

def qstats(s):
    x=pd.to_numeric(s,errors='coerce').dropna()
    return {'n':int(len(x)),'nonzero_share':float((x>0).mean()),'mean':float(x.mean()),'median':float(x.median()),'p75':float(x.quantile(.75)),'p90':float(x.quantile(.90)),'p95':float(x.quantile(.95)),'p99':float(x.quantile(.99)),'max':float(x.max())}

def safe_idxmax(df):
    out=pd.Series(index=df.index,dtype='object'); mask=df.notna().any(axis=1)
    out.loc[mask]=df.loc[mask].idxmax(axis=1); return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    p=load_parent(); old=p.load_old(); h1,meta=old.fetch_binance_futures_h1('2020-01','2026-07'); h4=old.to_h4(h1); d1=p.build_d1(h1,old)
    ctx,sm=p.build_router(h4,d1,old); ind=p.indicators_enhanced(h4,d1,old); C=components(ind)
    theoretical={'EXPANSION':100.0,'PULLBACK':95.0,'REVERSAL':100.0,'RANGE':100.0}
    score_rows=[]; comp_rows=[]; co_rows=[]; decomp_pass=True
    for r in REGIMES:
        raw=ctx[f'score_{r.lower()}'].astype(float); smoothed=raw.rolling(3,min_periods=3).mean(); cdf=pd.DataFrame(C[r],index=ind.index).fillna(0.0); summed=cdf.sum(axis=1).clip(0,100)
        common=raw.notna() & summed.notna(); ok=bool(np.allclose(raw[common].to_numpy(),summed[common].to_numpy(),rtol=0,atol=1e-10)); decomp_pass &= ok
        qs=qstats(raw); qsm=qstats(smoothed); t=theoretical[r]
        score_rows.append({'regime':r,'theoretical_max':t,**{f'raw_{k}':v for k,v in qs.items()},**{f'sm_{k}':v for k,v in qsm.items()},'p95_attainment':qs['p95']/t,'max_attainment':qs['max']/t,'decomposition_pass':ok})
        total_points=float(cdf.sum().sum()); largest=0.0
        for col in cdf.columns:
            x=cdf[col]; pts=float(x.sum()); share=(pts/total_points if total_points else np.nan); largest=max(largest,share if np.isfinite(share) else 0)
            comp_rows.append({'regime':r,'component':col,'weight':float(x.max()),'activation_rate':float((x>0).mean()),'mean_contribution':float(x.mean()),'total_points':pts,'share_total_points':share})
        active=(cdf>0).sum(axis=1); co_rows.append({'regime':r,'median_active_components':float(active.median()),'p75_active_components':float(active.quantile(.75)),'p90_active_components':float(active.quantile(.90)),'p95_active_components':float(active.quantile(.95)),'mean_active_components':float(active.mean()),'max_active_components':int(active.max()),'largest_component_point_share':largest})
    score_df=pd.DataFrame(score_rows); comp_df=pd.DataFrame(comp_rows); co_df=pd.DataFrame(co_rows)
    score_df.to_csv(out/'score_scale.csv',index=False); comp_df.to_csv(out/'component_information_balance.csv',index=False); co_df.to_csv(out/'coactivation_balance.csv',index=False)
    raw_scores=ctx[[f'score_{r.lower()}' for r in REGIMES]].copy(); raw_scores.columns=REGIMES; sm_scores=raw_scores.rolling(3,min_periods=3).mean()
    winner=pd.DataFrame({'raw_winner':safe_idxmax(raw_scores),'smoothed_winner':safe_idxmax(sm_scores),'state':ctx.regime})
    pd.DataFrame([{'regime':r,'raw_winner_share':float((winner.raw_winner==r).mean()),'smoothed_winner_share':float((winner.smoothed_winner==r).mean()),'state_share':float((winner.state==r).mean())} for r in REGIMES]).to_csv(out/'winner_shares.csv',index=False)
    tr=[]; rg=ctx.regime; ix=np.flatnonzero(rg.ne(rg.shift(1)).fillna(False).to_numpy())
    for i in ix:
        if i<=3 or pd.isna(rg.iloc[i]): continue
        dest=rg.iloc[i]
        for lag in [1,2,3]:
            row=sm_scores.iloc[i-lag]; val=row.get(dest,np.nan); rank=int(row.rank(method='min',ascending=False).get(dest,99)) if row.notna().any() else 99
            tr.append({'transition_time':str(ctx.index[i]),'destination':dest,'lag':lag,'score':val,'rank':rank,'is_top2':rank<=2})
    tdf=pd.DataFrame(tr); tdf.to_csv(out/'pretransition_information.csv',index=False); tdf.groupby(['destination','lag']).agg(n=('rank','size'),mean_score=('score','mean'),median_rank=('rank','median'),top2_share=('is_top2','mean')).reset_index().to_csv(out/'pretransition_summary.csv',index=False)
    expected={'PULLBACK':7641,'EXPANSION':4568,'RANGE':2184,'REVERSAL':29}; counts={k:int(v) for k,v in ctx.regime.value_counts().items()}; parity=(counts==expected)
    revs=score_df.set_index('regime').loc['REVERSAL']; others=score_df.set_index('regime').drop(index='REVERSAL')
    scale_cond1=theoretical['REVERSAL'] < sorted(theoretical[r] for r in REGIMES if r!='REVERSAL')[1]; scale_cond2=(float(others.p95_attainment.median())-float(revs.p95_attainment))>0.10
    revco=co_df.set_index('regime').loc['REVERSAL']; oco=co_df.set_index('regime').drop(index='REVERSAL'); co_sparse=(float(oco.median_active_components.median())-float(revco.median_active_components)>=1.0) and scale_cond2; scale_budget=bool(scale_cond1 or (scale_cond2 and not co_sparse))
    diagnosis='BOTH_SCALE_AND_COACTIVATION' if scale_budget and co_sparse else ('SCALE_BUDGET_IMBALANCE' if scale_budget else ('COACTIVATION_INFORMATION_SPARSE' if co_sparse else 'NO_CLEAR_STRUCTURAL_IMBALANCE'))
    rev_comp=comp_df[comp_df.regime=='REVERSAL'].sort_values('mean_contribution',ascending=False)
    summary={'lab':LAB,'diagnosis':diagnosis,'parent_regime_parity':parity,'parent_counts':counts,'decomposition_pass':decomp_pass,'reversal_theoretical_max':theoretical['REVERSAL'],'other_theoretical_max':{r:theoretical[r] for r in REGIMES if r!='REVERSAL'},'reversal_p95_attainment':float(revs.p95_attainment),'others_median_p95_attainment':float(others.p95_attainment.median()),'reversal_median_active_components':float(revco.median_active_components),'others_median_of_medians_active_components':float(oco.median_active_components.median()),'reversal_top_components':rev_comp[['component','activation_rate','mean_contribution']].head(6).to_dict('records')}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8'); (out/'REPORT.md').write_text(f"# {LAB}\n\n**Diagnosis: {diagnosis}**\n\n- Parent LAB010 regime parity: **{'PASS' if parity else 'FAIL'}** {counts}\n- Component decomposition exact sum: **{'PASS' if decomp_pass else 'FAIL'}**\n- Theoretical max: EXPANSION 100 / PULLBACK 95 / REVERSAL 100 / RANGE 100\n- Reversal p95 attainment: **{revs.p95_attainment:.3f}** vs other-regime median **{others.p95_attainment.median():.3f}**\n- Reversal median active components: **{revco.median_active_components:.1f}** vs other-regime median-of-medians **{oco.median_active_components.median():.1f}**\n\nThis LAB does not change any score weights or state-machine constants.\n",encoding='utf-8')
    print(json.dumps(summary,indent=2))
    if not parity or not decomp_pass: raise SystemExit(2)
if __name__=='__main__': main()
