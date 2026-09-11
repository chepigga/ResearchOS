#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='CONTEXT_REVERSAL_SEMANTIC_DEFINITION_AND_COMPETING_MODE_BOUNDARY_AUDIT_LAB_015'
ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'labs'/'CONTEXT_INDICATOR_PUBLIC_SPEC_GAP_CLOSURE_AND_NEXT_CONTEXT_LAB_010'/'run_lab.py'
LAB013=ROOT/'labs'/'CONTEXT_REVERSAL_COMPONENT_TEMPORAL_SEQUENCE_AND_EVENT_TO_STATE_AGGREGATION_LAB_013'/'run_lab.py'
REGIMES=['EXPANSION','PULLBACK','REVERSAL','RANGE']
WEIGHTS={'swing_sweep':30.0,'rsi_turn':20.0,'rsi_rhythm_turn':15.0,'ema20_cross':15.0,'adx_decay':10.0,'rejection_wick':10.0}

def loadmod(path,name):
    sp=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(sp)
    assert sp.loader is not None; sp.loader.exec_module(m); return m

def build(p,l13,h1):
    old=p.load_old(); h4=old.to_h4(h1); d1=p.build_d1(h1,old)
    ctx,sm=p.build_router(h4,d1,old); ind=p.indicators_enhanced(h4,d1,old)
    ev=l13.component_events(ind)
    scores=ctx[[f'score_{r.lower()}' for r in REGIMES]].copy(); scores.columns=REGIMES
    sms=scores.rolling(3,min_periods=3).mean()
    return ctx,ind,ev,scores,sms

def audit_frame(ctx,ind,ev,sms):
    x=pd.DataFrame(index=ctx.index)
    x['regime']=ctx.regime; x['prev_regime']=ctx.regime.shift(1)
    for c in ev.columns: x[c]=ev[c].astype(bool)
    x['event_count']=ev.sum(axis=1).astype(float)
    bull=(ind.ema20>ind.ema50)&(ind.ema50>ind.ema200)
    bear=(ind.ema20<ind.ema50)&(ind.ema50<ind.ema200)
    prev_bull=bull.shift(1).fillna(False); prev_bear=bear.shift(1).fillna(False)
    x['bull_stack']=bull; x['bear_stack']=bear
    x['d1_bias']=ind.d1_bias
    x['d1_conflict']=((ind.d1_bias=='BULL')&bear)|((ind.d1_bias=='BEAR')&bull)
    x['stack_break_change']=(prev_bull & (~bull)) | (prev_bear & (~bear)) | (prev_bull & bear) | (prev_bear & bull)
    x['bos_against_control']=((ind.d1_bias=='BULL')&ind.bos_dn.fillna(False))|((ind.d1_bias=='BEAR')&ind.bos_up.fillna(False))
    x['control_change']=x[['d1_conflict','stack_break_change','bos_against_control']].any(axis=1)
    x['close_above_ema20']=(ind.close>ind.ema20)
    x['close_above_ema50']=(ind.close>ind.ema50)
    x['ema20_gt_ema50']=(ind.ema20>ind.ema50)
    x['ema50_slope']=ind.ema50_slope
    x['atr_ratio']=ind.atr_ratio_public
    x['adx14']=ind.adx14
    x['range24_ratio']=ind.range24_ratio
    x['ema_spread_atr']=ind.ema_spread_atr
    x['relvol20']=ind.relvol20_public
    x['vol_state']=np.select([x.atr_ratio<.80,x.atr_ratio>1.35],['LOW','HIGH'],default='NORMAL')
    for r in REGIMES: x[f'sm_{r}']=sms[r]
    x['rev_rank']=sms.rank(axis=1,ascending=False,method='min')['REVERSAL']
    srt=np.sort(sms.to_numpy(dtype=float),axis=1)
    x['winner_margin']=srt[:,-1]-srt[:,-2]
    x['rev_vs_pullback']=sms.REVERSAL-sms.PULLBACK
    x['rev_vs_expansion']=sms.REVERSAL-sms.EXPANSION
    x['rev_vs_range']=sms.REVERSAL-sms.RANGE
    return x

def transitions(x):
    m=x.regime.notna() & x.prev_regime.notna() & x.regime.ne(x.prev_regime)
    return x.loc[m].copy()

def safe_median(s):
    s=pd.to_numeric(s,errors='coerce').dropna(); return float(s.median()) if len(s) else np.nan

def safe_mean(s):
    s=pd.to_numeric(s,errors='coerce').dropna(); return float(s.mean()) if len(s) else np.nan

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    p=loadmod(PARENT,'ctx010_015'); l13=loadmod(LAB013,'ctx013_015'); old=p.load_old()
    h1,meta=old.fetch_binance_futures_h1('2020-01','2026-07')
    ctx,ind,ev,scores,sms=build(p,l13,h1); x=audit_frame(ctx,ind,ev,sms); tr=transitions(x)
    expected={'PULLBACK':7641,'EXPANSION':4568,'RANGE':2184,'REVERSAL':29}
    counts={k:int(v) for k,v in ctx.regime.value_counts().items()}; parity=(counts==expected)
    reconstructed=sum(ev[c].astype(float)*WEIGHTS[c] for c in WEIGHTS).clip(0,100)
    score_parity=bool(np.allclose(reconstructed.to_numpy(),scores.REVERSAL.to_numpy(),rtol=0,atol=1e-10,equal_nan=True))

    # t-2/t-1/t0 transition characterization
    rows=[]
    for t,row in tr.iterrows():
        i=x.index.get_loc(t)
        for lag in [-2,-1,0]:
            if i+lag<0: continue
            q=x.iloc[i+lag]
            rows.append({'transition_time':str(t),'destination':row.regime,'origin':row.prev_regime,'lag':lag,
                         'event_count':q.event_count,'control_change':bool(q.control_change),'d1_conflict':bool(q.d1_conflict),
                         'stack_break_change':bool(q.stack_break_change),'bos_against_control':bool(q.bos_against_control),
                         'rev_rank':q.rev_rank,'winner_margin':q.winner_margin,
                         'rev_vs_pullback':q.rev_vs_pullback,'rev_vs_expansion':q.rev_vs_expansion,'rev_vs_range':q.rev_vs_range,
                         'atr_ratio':q.atr_ratio,'adx14':q.adx14,'range24_ratio':q.range24_ratio,'ema_spread_atr':q.ema_spread_atr,'relvol20':q.relvol20})
    detail=pd.DataFrame(rows); detail.to_csv(out/'transition_semantic_detail.csv',index=False)
    summary=detail.groupby(['destination','lag']).agg(n=('event_count','size'),median_event_count=('event_count','median'),control_change_share=('control_change','mean'),median_rev_rank=('rev_rank','median'),median_winner_margin=('winner_margin','median'),median_atr_ratio=('atr_ratio','median'),median_adx=('adx14','median')).reset_index()
    summary.to_csv(out/'transition_semantic_summary.csv',index=False)

    rev0=detail[(detail.destination=='REVERSAL')&(detail.lag==0)].copy()
    rev_times=pd.to_datetime(rev0.transition_time,utc=True)
    # matched same-year + same volatility-state controls
    controls=[]
    tr0=tr.copy(); tr0['year']=tr0.index.year
    for j,t in enumerate(rev_times):
        if t not in x.index: continue
        vs=x.loc[t,'vol_state']; yr=t.year
        c=tr0[(tr0.index.year==yr)&(tr0.vol_state==vs)&(tr0.regime!='REVERSAL')]
        for ct,r in c.iterrows(): controls.append({'match_id':j,'rev_time':str(t),'control_time':str(ct),'destination':r.regime,'event_count':r.event_count,'control_change':bool(r.control_change),'winner_margin':r.winner_margin})
    mc=pd.DataFrame(controls); mc.to_csv(out/'matched_transition_controls.csv',index=False)

    rev_event=safe_median(rev0.event_count); ctrl_event=safe_median(mc.event_count) if len(mc) else np.nan
    rev_control=safe_mean(rev0.control_change.astype(float)); ctrl_control=safe_mean(mc.control_change.astype(float)) if len(mc) else np.nan
    others=detail[(detail.destination!='REVERSAL')&(detail.lag==0)]
    rev_margin=safe_median(rev0.winner_margin); other_margin=safe_median(others.winner_margin)
    origins=tr[tr.regime=='REVERSAL'].prev_regime.value_counts(); rev_n=int(origins.sum()); directional_origin=int(origins.get('PULLBACK',0)+origins.get('EXPANSION',0)); directional_share=directional_origin/rev_n if rev_n else np.nan

    # Near-miss boundary: rank<=2, not Reversal state. Standardized distance to Reversal-transition centroid vs broad non-Reversal background.
    feats=['event_count','control_change','d1_conflict','stack_break_change','bos_against_control','atr_ratio','adx14','range24_ratio','ema_spread_atr','relvol20','rev_vs_pullback','rev_vs_expansion','rev_vs_range']
    z=x[feats].astype(float).copy(); mu=z.mean(); sd=z.std().replace(0,np.nan); zz=(z-mu)/sd
    rev_idx=tr[(tr.regime=='REVERSAL')].index
    centroid=zz.loc[rev_idx].mean(axis=0)
    dist=np.sqrt(((zz-centroid)**2).mean(axis=1)); x['semantic_distance']=dist
    near=x[(x.regime!='REVERSAL')&(x.rev_rank<=2)&x.regime.notna()]
    broad=x[(x.regime!='REVERSAL')&x.regime.notna()]
    nd={'near_n':int(len(near)),'near_median_distance':safe_median(near.semantic_distance),'broad_n':int(len(broad)),'broad_median_distance':safe_median(broad.semantic_distance)}
    pd.DataFrame([nd]).to_csv(out/'near_miss_similarity.csv',index=False)

    # causality perturbation
    cut=int(len(h1)*.72); ct=h1.time.iloc[cut]; hp=h1.copy(); fut=hp.time>ct
    for c in ['open','high','low','close']: hp.loc[fut,c]=hp.loc[fut,c]*np.linspace(1.5,3.0,int(fut.sum()))
    hp.loc[fut,'volume']=hp.loc[fut,'volume']*17+12345
    c2,i2,e2,s2,sm2=build(p,l13,hp); x2=audit_frame(c2,i2,e2,sm2)
    safe=x.index[(x.index+pd.Timedelta(hours=4))<=ct]
    audit_cols=['regime','event_count','control_change','d1_conflict','stack_break_change','bos_against_control','rev_rank','winner_margin','rev_vs_pullback','rev_vs_expansion','rev_vs_range','atr_ratio','adx14','range24_ratio','ema_spread_atr','relvol20']
    changed=[]
    for col in audit_cols:
        common=safe.intersection(x2.index)
        aa=x.loc[common,col]; bb=x2.loc[common,col]
        if aa.dtype.kind in 'biufc' and bb.dtype.kind in 'biufc': ok=np.allclose(aa.astype(float),bb.astype(float),rtol=0,atol=1e-10,equal_nan=True)
        else: ok=aa.fillna('__NA__').astype(str).equals(bb.fillna('__NA__').astype(str))
        if not ok: changed.append(col)
    causal=(len(changed)==0)

    A=bool(np.isfinite(rev_event) and np.isfinite(ctrl_event) and rev_event>=ctrl_event+1.0)
    B=bool(np.isfinite(rev_control) and np.isfinite(ctrl_control) and rev_control>=ctrl_control+.20)
    C=bool(np.isfinite(rev_margin) and np.isfinite(other_margin) and rev_margin<other_margin)
    D=bool(np.isfinite(directional_share) and directional_share>=.70)
    if not parity or not score_parity: verdict='PARENT_PARITY_FAIL'
    elif not causal: verdict='CAUSALITY_FAIL'
    elif A and not B: verdict='EVENT_REVERSAL_SEMANTICS_SUPPORTED'
    elif B and C and D and not A: verdict='CONTROL_CHANGE_BOUNDARY_SEMANTICS_SUPPORTED'
    elif A and B: verdict='MIXED_REVERSAL_SEMANTICS'
    else: verdict='REVERSAL_SEMANTICS_UNRESOLVED'

    result={'lab':LAB,'verdict':verdict,'parent_counts':counts,'parent_parity':parity,'reversal_score_parity':score_parity,'causality_pass':causal,'causality_changed':changed,
            'reversal_transitions':rev_n,'reversal_origin_counts':{str(k):int(v) for k,v in origins.items()},'directional_origin_share':directional_share,
            'reversal_median_event_count':rev_event,'matched_control_median_event_count':ctrl_event,'reversal_control_change_share':rev_control,'matched_control_control_change_share':ctrl_control,
            'reversal_median_winning_margin':rev_margin,'other_transition_median_winning_margin':other_margin,'near_miss':nd,
            'gates':{'A_event_enrichment':A,'B_control_change_enrichment':B,'C_boundary_margin':C,'D_directional_origin':D}}
    (out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    report=f'''# {LAB}\n\n**Verdict: {verdict}**\n\n- Parent parity: **{'PASS' if parity else 'FAIL'}** {counts}\n- Reversal score reconstruction: **{'PASS' if score_parity else 'FAIL'}**\n- Causality: **{'PASS' if causal else 'FAIL'}** changed={changed}\n- Frozen Reversal transitions: **{rev_n}**\n- Origin counts: **{dict(origins)}**; directional-origin share **{directional_share:.3f}**\n- Event-count median: Reversal **{rev_event:.3f}** vs matched controls **{ctrl_event:.3f}**\n- Control-change share: Reversal **{rev_control:.3f}** vs matched controls **{ctrl_control:.3f}**\n- Winning-margin median: Reversal **{rev_margin:.3f}** vs other transitions **{other_margin:.3f}**\n- Near-miss semantic distance median **{nd['near_median_distance']:.3f}** vs broad non-Reversal **{nd['broad_median_distance']:.3f}**\n- Gates: {result['gates']}\n\nNo PnL or edge metrics were used. No frozen Context weights or state-machine constants were changed.\n'''
    (out/'REPORT.md').write_text(report,encoding='utf-8')
    print(json.dumps(result,indent=2))
    if not parity or not score_parity or not causal: raise SystemExit(2)

if __name__=='__main__': main()
