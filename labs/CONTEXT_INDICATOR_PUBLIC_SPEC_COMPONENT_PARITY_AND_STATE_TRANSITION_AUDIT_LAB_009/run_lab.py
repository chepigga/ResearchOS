#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, inspect, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='CONTEXT_INDICATOR_PUBLIC_SPEC_COMPONENT_PARITY_AND_STATE_TRANSITION_AUDIT_LAB_009'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ROUTER_PATH=ROOT/'labs'/'CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001'/'run_lab.py'


def load_router():
    spec=importlib.util.spec_from_file_location('router009',ROUTER_PATH)
    m=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(m); return m


def eq_series(a,b):
    if len(a)!=len(b): return False
    aa=np.asarray(a,dtype=object); bb=np.asarray(b,dtype=object)
    out=[]
    for x,y in zip(aa,bb):
        if pd.isna(x) and pd.isna(y): out.append(True)
        elif isinstance(x,(float,np.floating)) or isinstance(y,(float,np.floating)):
            try: out.append(bool(np.isclose(float(x),float(y),equal_nan=True,rtol=0,atol=1e-12)))
            except: out.append(x==y)
        else: out.append(x==y)
    return bool(all(out))


def reconstruct_machine(ctx):
    score_cols=['score_expansion','score_pullback','score_reversal','score_range']
    names=['EXPANSION','PULLBACK','REVERSAL','RANGE']
    sm=ctx[score_cols].rolling(3,min_periods=3).mean(); sm.columns=names
    states=[]; meta=[]; cur=None; held=0
    for idx,row in sm.iterrows():
        if row.isna().all(): states.append(None); meta.append((None,None,None,None)); continue
        scores=row.fillna(-1e9).to_dict()
        if cur is None:
            cur=max(scores,key=scores.get); held=1; meta.append(('INIT',held,np.nan,np.nan))
        else:
            atrr=ctx.loc[idx,'atr_ratio']; atrr=1.0 if pd.isna(atrr) else atrr
            if atrr<0.80: min_hold,gap=4,12
            elif atrr>1.35: min_hold,gap=2,5
            else: min_hold,gap=3,8
            held_before=held
            adjusted=scores.copy(); adjusted[cur]=adjusted.get(cur,-1e9)+5
            ch=max(adjusted,key=adjusted.get)
            should=(ch!=cur and held>=min_hold and adjusted[ch]>adjusted[cur]+gap)
            old=cur
            if should: cur=ch; held=1
            else: held+=1
            meta.append((f'{old}->{cur}',held_before,min_hold,gap))
        states.append(cur)
    return pd.Series(states,index=ctx.index),sm,meta


def static_statuses():
    # Exact means the literal public-described item exists. Proxy means related substitute exists.
    return {
      'EMA20_50_200_structure':'IMPLEMENTED_EXACT',
      'EMA_slope':'IMPLEMENTED_PROXY',
      'ATR14_relative_volatility':'IMPLEMENTED_PROXY',
      'D1_HTF_bias':'NOT_IMPLEMENTED',
      'daily_inside_bar':'NOT_IMPLEMENTED',
      'range24_compression':'IMPLEMENTED_EXACT',
      'swing_pivots':'NOT_IMPLEMENTED',
      'BOS':'IMPLEMENTED_PROXY',
      'liquidity_sweep_failed_sweep':'IMPLEMENTED_PROXY',
      'RSI14_EMA9_WMA45_rhythm':'NOT_IMPLEMENTED',
      'ADX14_level':'IMPLEMENTED_EXACT',
      'ADX_decay':'IMPLEMENTED_EXACT',
      'relative_volume_20bar_average':'IMPLEMENTED_PROXY',
      'session_contribution':'NOT_IMPLEMENTED',
      'Expansion_score':'IMPLEMENTED_PROXY',
      'Pullback_score':'IMPLEMENTED_PROXY',
      'Reversal_score':'IMPLEMENTED_PROXY',
      'Range_score':'IMPLEMENTED_PROXY',
      'three_bar_smoothing':'IMPLEMENTED_EXACT',
      'current_mode_inertia_bonus':'IMPLEMENTED_PROXY',
      'minimum_hold':'IMPLEMENTED_PROXY',
      'switch_gap':'IMPLEMENTED_PROXY',
      'low_vol_wider_gap':'IMPLEMENTED_PROXY',
      'high_vol_shorter_hold':'IMPLEMENTED_PROXY',
      'public_TF_mapping_M1_M15_M5_H1_M15_H4_H1_D1':'NOT_IMPLEMENTED',
      'closed_HTF_availability_clock':'IMPLEMENTED_EXACT',
      'Current_Context_output':'IMPLEMENTED_EXACT',
      'Next_Context_runner_up_output':'NOT_IMPLEMENTED',
      'direction_compatibility_layer':'IMPLEMENTED_EXACT',
    }


def activation(ind,ctx):
    mindist=pd.concat([ind.dist20_atr,ind.dist50_atr],axis=1).min(axis=1)
    prev_rsi=ind.rsi14.shift(1)
    rsi_turn=((prev_rsi<35)&(ind.rsi14>prev_rsi))|((prev_rsi>65)&(ind.rsi14<prev_rsi))
    act={
      'EMA20_50_200_structure':ind.stack,
      'EMA_slope':ind.slope50_atr.abs()>0,
      'ATR14_relative_volatility':ind.atr_ratio.notna(),
      'range24_compression':ind.range24_ratio<0.85,
      'BOS':ind.breakout,
      'liquidity_sweep_failed_sweep':ind.sweep,
      'ADX14_level':ind.adx14>=20,
      'ADX_decay':ind.adx14<ind.adx14.shift(1),
      'relative_volume_20bar_average':ind.relvol20>=1.05,
      'Expansion_score':ctx.score_expansion>0,
      'Pullback_score':ctx.score_pullback>0,
      'Reversal_score':ctx.score_reversal>0,
      'Range_score':ctx.score_range>0,
      'three_bar_smoothing':ctx[['score_expansion','score_pullback','score_reversal','score_range']].rolling(3,min_periods=3).mean().notna().all(axis=1),
    }
    rows=[]
    for k,v in act.items():
        vv=pd.Series(v,index=ctx.index).fillna(False).astype(bool)
        rows.append({'component':k,'activation_n':int(vv.sum()),'activation_rate':float(vv.mean())})
    return pd.DataFrame(rows)


def next_context_stats(ctx,sm):
    reg=ctx.regime
    trans=np.flatnonzero(reg.ne(reg.shift(1)).fillna(False).to_numpy())
    rows=[]
    for i in trans:
        if i<=0 or pd.isna(reg.iloc[i-1]) or pd.isna(reg.iloc[i]): continue
        cur=reg.iloc[i-1]; new=reg.iloc[i]
        r=sm.iloc[i-1].dropna().sort_values(ascending=False)
        r=r[r.index!=cur]
        runner=r.index[0] if len(r) else None
        rows.append({'transition_time':str(ctx.index[i]),'old':cur,'new':new,'runner_up_prior_bar':runner,'match':runner==new})
    d=pd.DataFrame(rows)
    if d.empty: return d, {'n':0,'match_rate':np.nan,'baseline':np.nan,'lift':np.nan}
    # baseline: modal probability of realized next state conditional only on old state
    base=[]
    for old,g in d.groupby('old'):
        p=g.new.value_counts(normalize=True).max(); base.extend([p]*len(g))
    baseline=float(np.mean(base)) if base else np.nan
    mr=float(d.match.mean())
    return d,{'n':int(len(d)),'match_rate':mr,'baseline':baseline,'lift':float(mr-baseline)}


def causality_test(router,h4,ctx):
    cut=int(len(h4)*0.72)
    cutidx=h4.index[cut]
    p=h4.copy()
    fut=p.index>cutidx
    # Extreme perturbation strictly after cutoff.
    for c in ['open','high','low','close']:
        p.loc[fut,c]=p.loc[fut,c]*np.linspace(1.5,3.0,int(fut.sum()))
    p.loc[fut,'volume']=p.loc[fut,'volume']*17+12345
    c2=router.add_router(p)
    cols=['atr14','atr_ratio','ema20','ema50','ema200','slope50_atr','rsi14','adx14','range24_ratio','relvol20','regime','regime_confidence','bias','score_expansion','score_pullback','score_reversal','score_range','available_time']
    sub=ctx.loc[ctx.index<=cutidx]; sub2=c2.loc[c2.index<=cutidx]
    bad=[]
    for c in cols:
        if not eq_series(sub[c],sub2[c]): bad.append(c)
    return {'cutoff':str(cutidx),'rows_checked':int(len(sub)),'changed_columns':bad,'pass':len(bad)==0}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    router=load_router()
    h1,meta=router.fetch_binance_futures_h1('2020-01','2026-07'); h4=router.to_h4(h1)
    ctx=router.add_router(h4); ind=router.indicators(h4)

    statuses=static_statuses(); act=activation(ind,ctx)
    recon,sm,mmeta=reconstruct_machine(ctx)
    state_match=np.array([(pd.isna(x) and pd.isna(y)) or x==y for x,y in zip(recon,ctx.regime)])
    state_machine={'rows':int(len(ctx)),'mismatch_n':int((~state_match).sum()),'pass':bool(state_match.all())}

    # transition parameter usage reconstructed from the exact state machine
    mm=pd.DataFrame(mmeta,columns=['transition','held_before','min_hold','gap'],index=ctx.index)
    param_counts=mm.dropna(subset=['min_hold','gap']).groupby(['min_hold','gap']).size().reset_index(name='n')
    param_counts.to_csv(out/'state_machine_parameter_usage.csv',index=False)

    score_cols=['score_expansion','score_pullback','score_reversal','score_range']
    score_activation={c:int((ctx[c]>0).sum()) for c in score_cols}
    regime_counts=ctx.regime.value_counts(dropna=True).to_dict()
    activation_gate=all(v>0 for v in score_activation.values()) and all(regime_counts.get(r,0)>0 for r in ['EXPANSION','PULLBACK','REVERSAL','RANGE'])

    closed=((ctx.available_time-ctx.index)==pd.Timedelta(hours=4)).dropna()
    closed_clock={'checked':int(len(closed)),'pass':bool(closed.all()),'violations':int((~closed).sum())}
    causal=causality_test(router,h4,ctx)
    nxt,nxts=next_context_stats(ctx,sm); nxt.to_csv(out/'next_context_transition_audit.csv',index=False)

    # Sanity tests for implemented direction relationships.
    sanity={
      'bull_bias_requires_stack_up':bool((ind.loc[ctx.bias.eq('BULL'),'stack_up']).all()),
      'bear_bias_requires_stack_dn':bool((ind.loc[ctx.bias.eq('BEAR'),'stack_dn']).all()),
      'breakout_contributes_expansion':bool(((ind.breakout)&(ctx.score_expansion>=20)).sum()==int(ind.breakout.sum())),
      'sweep_contributes_reversal':bool(((ind.sweep)&(ctx.score_reversal>=30)).sum()==int(ind.sweep.sum())),
      'lowvol_param_present':bool(((param_counts.min_hold==4)&(param_counts.gap==12)).any()),
      'normal_param_present':bool(((param_counts.min_hold==3)&(param_counts.gap==8)).any()),
      'highvol_param_present':bool(((param_counts.min_hold==2)&(param_counts.gap==5)).any()),
    }

    exact=[k for k,v in statuses.items() if v=='IMPLEMENTED_EXACT']
    proxy=[k for k,v in statuses.items() if v=='IMPLEMENTED_PROXY']
    missing=[k for k,v in statuses.items() if v=='NOT_IMPLEMENTED']
    dynamic_core=bool(causal['pass'] and closed_clock['pass'] and activation_gate and state_machine['pass'] and all(sanity.values()))
    if not dynamic_core: verdict='STATE_MACHINE_AUDIT_FAILED'
    elif len(proxy)==0 and len(missing)==0: verdict='FULL_PUBLIC_SPEC_PARITY'
    else: verdict='FUNCTIONAL_PROXY_WITH_PUBLIC_SPEC_GAPS'

    checklist=[]; amap=act.set_index('component').to_dict('index')
    for i,(k,v) in enumerate(statuses.items(),1):
        rec={'id':i,'component':k,'status':v,'public_parity_pass':bool(v=='IMPLEMENTED_EXACT')}
        rec.update(amap.get(k,{})); checklist.append(rec)
    pd.DataFrame(checklist).to_csv(out/'public_spec_checklist.csv',index=False)

    summary={'lab':LAB,'verdict':verdict,'dataset':meta,'h4_rows':int(len(h4)),
      'checklist_total':len(statuses),'implemented_exact_n':len(exact),'implemented_proxy_n':len(proxy),'not_implemented_n':len(missing),
      'exact_components':exact,'proxy_components':proxy,'missing_components':missing,
      'causality':causal,'closed_clock':closed_clock,'score_activation':score_activation,'regime_counts':{str(k):int(v) for k,v in regime_counts.items()},
      'score_and_regime_activation_gate':bool(activation_gate),'state_machine_reconstruction':state_machine,'sanity':sanity,'next_context_descriptive':nxts,
      'full_public_spec_parity':bool(verdict=='FULL_PUBLIC_SPEC_PARITY')}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',
      f"- Public checklist: **{len(statuses)}** items — exact **{len(exact)}**, proxy **{len(proxy)}**, missing **{len(missing)}**.",
      f"- Causality: **{'PASS' if causal['pass'] else 'FAIL'}**; pre-cutoff changed columns: {causal['changed_columns']}",
      f"- Closed H4 clock: **{'PASS' if closed_clock['pass'] else 'FAIL'}**",
      f"- Four-score + four-regime activation: **{'PASS' if activation_gate else 'FAIL'}**",
      f"- State-machine exact reconstruction: **{'PASS' if state_machine['pass'] else 'FAIL'}**, mismatches={state_machine['mismatch_n']}",
      f"- Next-context runner-up before transitions: N={nxts['n']}, match={nxts['match_rate']:.3f}, unconditional-old-state baseline={nxts['baseline']:.3f}, lift={nxts['lift']:+.3f}",'',
      '## Exact public items']
    lines += [f'- PASS — {x}' for x in exact]
    lines += ['', '## Implemented only as proxies']+[f'- PROXY — {x}' for x in proxy]
    lines += ['', '## Missing public items']+[f'- GAP — {x}' for x in missing]
    lines += ['', '## Regime counts']+[f'- {k}: {int(v)}' for k,v in regime_counts.items()]
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
