#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='CONTEXT_REVERSAL_ORDERED_EVENT_CHAIN_AND_STAGE_STATE_MACHINE_LAB_014'
ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'labs'/'CONTEXT_INDICATOR_PUBLIC_SPEC_GAP_CLOSURE_AND_NEXT_CONTEXT_LAB_010'/'run_lab.py'
EXPECTED={'PULLBACK':7641,'EXPANSION':4568,'RANGE':2184,'REVERSAL':29}
WEIGHTS={'swing_sweep':30.0,'rsi_turn':20.0,'rsi_rhythm_turn':15.0,'ema20_cross':15.0,'adx_decay':10.0,'rejection_wick':10.0}


def load_parent():
    sp=importlib.util.spec_from_file_location('ctx010_for_014',PARENT)
    m=importlib.util.module_from_spec(sp); assert sp.loader is not None; sp.loader.exec_module(m); return m


def build_events(ind):
    prev=ind.rsi14.shift(1)
    rsi_turn=(((prev<35)&(ind.rsi14>prev))|((prev>65)&(ind.rsi14<prev))).fillna(False)
    rhythm=(ind.rsi_rhythm_up.ne(ind.rsi_rhythm_up.shift(1)) & ind.rsi_ema9.notna() & ind.rsi_wma45.notna()).fillna(False)
    structural=((ind.d1_bias=='BULL')&ind.bos_dn.fillna(False))|((ind.d1_bias=='BEAR')&ind.bos_up.fillna(False))
    ev=pd.DataFrame(index=ind.index)
    ev['swing_sweep']=ind.swing_sweep.fillna(False)
    ev['rejection_wick']=(ind.rejection_wick>=.45).fillna(False)
    ev['rsi_turn']=rsi_turn
    ev['rsi_rhythm_turn']=rhythm
    ev['adx_decay']=(ind.adx14<ind.adx14.shift(1)).fillna(False)
    ev['ema20_cross']=ind.cross_ema20.fillna(False)
    ev['structural_failure']=structural.fillna(False)
    ev['A']=ev.swing_sweep|ev.rejection_wick
    ev['B']=ev.rsi_turn|ev.rsi_rhythm_turn|ev.adx_decay
    ev['C']=ev.ema20_cross|ev.structural_failure
    return ev.astype(bool)


def stage_machine(ev):
    state='IDLE'; a_idx=None; b_idx=None; complete=[]; rows=[]
    for i,(t,r) in enumerate(ev.iterrows()):
        emitted=False
        # timeout before processing current bar
        if state=='WAIT_B' and a_idx is not None and i-a_idx>2:
            state='IDLE'; a_idx=None
        if state=='WAIT_C' and b_idx is not None and i-b_idx>2:
            state='IDLE'; a_idx=None; b_idx=None

        entering=state
        if entering=='IDLE':
            if bool(r.A):
                state='WAIT_B'; a_idx=i
        elif entering=='WAIT_B':
            if bool(r.B):
                state='WAIT_C'; b_idx=i
            elif bool(r.A):
                a_idx=i
        elif entering=='WAIT_C':
            if bool(r.C):
                emitted=True; complete.append(i); state='IDLE'; a_idx=None; b_idx=None
        rows.append({'time':t,'entering_state':entering,'exit_state':state,'chain_complete':emitted,'A':bool(r.A),'B':bool(r.B),'C':bool(r.C)})
    z=pd.DataFrame(rows).set_index('time')
    return z,complete


def transition_indices(regime):
    x=np.flatnonzero(regime.ne(regime.shift(1)).fillna(False).to_numpy())
    return [i for i in x if i>=3 and regime.iloc[i]=='REVERSAL']


def conversion_stats(signal, regime, horizon=3, include_current=True):
    sig=np.flatnonzero(pd.Series(signal,index=regime.index).fillna(False).to_numpy())
    rr=regime.to_numpy(); hit=0; leads=[]; eligible=0
    for i in sig:
        start=i if include_current else i+1
        end=min(len(rr),i+horizon+1)
        if start>=len(rr): continue
        eligible+=1
        found=None
        for j in range(start,end):
            if rr[j]=='REVERSAL': found=j-i; break
        if found is not None:
            hit+=1; leads.append(found)
    return {'candidates':eligible,'converted':hit,'precision':hit/eligible if eligible else np.nan,'median_lead':float(np.median(leads)) if leads else np.nan,'leads':leads}


def transition_recall(signal, regime, lookback=3):
    sig=np.asarray(pd.Series(signal,index=regime.index).fillna(False),dtype=bool)
    ix=transition_indices(regime); hits=0; leads=[]
    for i in ix:
        found=None
        for j in range(i,max(-1,i-lookback-1),-1):
            if sig[j]: found=i-j; break
        if found is not None: hits+=1; leads.append(found)
    return {'n_transitions':len(ix),'hits':hits,'recall':hits/len(ix) if ix else np.nan,'median_lead':float(np.median(leads)) if leads else np.nan,'leads':leads}


def stage_attrition(ev,machine):
    A=np.flatnonzero(ev.A.to_numpy()); B=np.flatnonzero(ev.B.to_numpy()); C=np.flatnonzero(ev.C.to_numpy())
    def next_within(src,target,maxlag=2):
        n=hit=0; lags=[]; targ=set(target.tolist())
        for i in src:
            n+=1
            f=None
            for j in range(i+1,min(len(ev),i+maxlag+1)):
                if j in targ: f=j-i; break
            if f is not None: hit+=1; lags.append(f)
        return n,hit,(hit/n if n else np.nan),(float(np.median(lags)) if lags else np.nan)
    a=next_within(A,B); b=next_within(B,C)
    return pd.DataFrame([
        {'stage':'A_to_B','source_n':a[0],'advanced_n':a[1],'advance_rate':a[2],'median_lag':a[3]},
        {'stage':'B_to_C','source_n':b[0],'advanced_n':b[1],'advance_rate':b[2],'median_lag':b[3]},
        {'stage':'CHAIN_COMPLETE','source_n':int(ev.A.sum()),'advanced_n':int(machine.chain_complete.sum()),'advance_rate':float(machine.chain_complete.sum()/ev.A.sum()) if ev.A.sum() else np.nan,'median_lag':np.nan},
    ])


def build_all(p,h1):
    old=p.load_old(); h4=old.to_h4(h1); d1=p.build_d1(h1,old); ctx,sm=p.build_router(h4,d1,old); ind=p.indicators_enhanced(h4,d1,old)
    ev=build_events(ind); mach,complete=stage_machine(ev)
    return ctx,ind,ev,mach


def eq_series(a,b):
    aa=pd.Series(a).reset_index(drop=True); bb=pd.Series(b).reset_index(drop=True)
    return aa.fillna('__NA__').astype(str).equals(bb.fillna('__NA__').astype(str))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=load_parent(); old=p.load_old(); h1,meta=old.fetch_binance_futures_h1('2020-01','2026-07')
    ctx,ind,ev,mach=build_all(p,h1)

    counts={k:int(v) for k,v in ctx.regime.value_counts().items()}; parity=counts==EXPECTED
    # exact frozen reversal score reconstruction
    prev=ind.rsi14.shift(1); turn=((prev<35)&(ind.rsi14>prev))|((prev>65)&(ind.rsi14<prev))
    rhythm=(ind.rsi_rhythm_up.ne(ind.rsi_rhythm_up.shift(1)))&ind.rsi_ema9.notna()&ind.rsi_wma45.notna()
    recon=(30*ind.swing_sweep.astype(float)+20*turn.astype(float)+15*rhythm.astype(float)+15*ind.cross_ema20.astype(float)+10*(ind.adx14<ind.adx14.shift(1)).astype(float)+10*(ind.rejection_wick>=.45).astype(float)).clip(0,100)
    score_parity=bool(np.allclose(recon.to_numpy(),ctx.score_reversal.to_numpy(),rtol=0,atol=1e-10,equal_nan=True))

    controls={
      'STAGE_A':ev.A,
      'STAGE_B':ev.B,
      'STAGE_C':ev.C,
      'CHAIN_COMPLETE':mach.chain_complete,
    }
    metrics=[]
    for name,sig in controls.items():
        c=conversion_stats(sig,ctx.regime,3,True); r=transition_recall(sig,ctx.regime,3)
        metrics.append({'signal':name,'candidates':c['candidates'],'converted':c['converted'],'precision_0_3':c['precision'],'median_lead_converted':c['median_lead'],'transition_hits':r['hits'],'transition_n':r['n_transitions'],'transition_recall':r['recall'],'transition_median_lead':r['median_lead']})
    mdf=pd.DataFrame(metrics); mdf.to_csv(out/'signal_conversion_and_recall.csv',index=False)

    # year stability for chain
    yr=[]
    for y,g in mach.groupby(mach.index.year):
        idx=g.index; sig=g.chain_complete
        subreg=ctx.regime.reindex(idx)
        c=conversion_stats(sig,subreg,3,True)
        yr.append({'year':int(y),'chain_completions':int(sig.sum()),'converted':c['converted'],'precision_0_3':c['precision']})
    ydf=pd.DataFrame(yr); ydf.to_csv(out/'year_chain_balance.csv',index=False)

    attr=stage_attrition(ev,mach); attr.to_csv(out/'stage_attrition.csv',index=False)
    mach.join(ev[['swing_sweep','rejection_wick','rsi_turn','rsi_rhythm_turn','adx_decay','ema20_cross','structural_failure']]).to_csv(out/'stage_machine_stream.csv')

    # causality via future perturbation; only fully closed H4 bars <= cutoff
    cut=int(len(h1)*.72); ct=h1.time.iloc[cut]
    hp=h1.copy(); fut=hp.time>ct
    for c in ['open','high','low','close']: hp.loc[fut,c]=hp.loc[fut,c]*np.linspace(1.5,3.0,int(fut.sum()))
    hp.loc[fut,'volume']=hp.loc[fut,'volume']*17+12345
    c2,i2,e2,m2=build_all(p,hp)
    safe=ctx.index[(ctx.index+pd.Timedelta(hours=4))<=ct]
    bad=[]
    for col in ['A','B','C','swing_sweep','rejection_wick','rsi_turn','rsi_rhythm_turn','adx_decay','ema20_cross','structural_failure']:
        common=safe.intersection(ev.index).intersection(e2.index)
        if not eq_series(ev.loc[common,col],e2.loc[common,col]): bad.append(col)
    common=safe.intersection(mach.index).intersection(m2.index)
    for col in ['entering_state','exit_state','chain_complete']:
        if not eq_series(mach.loc[common,col],m2.loc[common,col]): bad.append('machine_'+col)
    causal=len(bad)==0

    row=mdf.set_index('signal')
    ch=row.loc['CHAIN_COMPLETE']; a=row.loc['STAGE_A']
    precision_ratio=float(ch.precision_0_3/a.precision_0_3) if np.isfinite(a.precision_0_3) and a.precision_0_3>0 else np.nan
    years_with=int((ydf.chain_completions>0).sum())
    gates={
      'G1_parent_parity':parity,
      'G2_score_reconstruction':score_parity,
      'G3_causality':causal,
      'G4_recall_ge_4of9':bool(ch.transition_hits>=4),
      'G5_precision_ge_5pct':bool(ch.precision_0_3>=.05),
      'G6_precision_ratio_ge_2x':bool(np.isfinite(precision_ratio) and precision_ratio>=2.0),
      'G7_median_lead_le2':bool(np.isfinite(ch.median_lead_converted) and ch.median_lead_converted<=2.0),
      'G8_years_ge5':bool(years_with>=5),
    }
    core=all(gates[k] for k in ['G1_parent_parity','G2_score_reconstruction','G3_causality'])
    support=sum(gates[k] for k in ['G4_recall_ge_4of9','G5_precision_ge_5pct','G6_precision_ratio_ge_2x','G7_median_lead_le2','G8_years_ge5'])
    if not core: verdict='PARITY_OR_CAUSALITY_FAIL'
    elif support==5: verdict='ORDERED_STAGE_MACHINE_SUPPORTED'
    elif support>=2: verdict='WEAK_ORDERED_STAGE_SIGNAL'
    else: verdict='ORDERED_STAGE_MACHINE_NOT_SUPPORTED'

    summary={'lab':LAB,'verdict':verdict,'counts':counts,'causality_changed':bad,'precision_ratio_chain_vs_A':precision_ratio,'years_with_chain':years_with,'gates':gates}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    report=f'''# {LAB}\n\n**Verdict: {verdict}**\n\n- Parent parity: **{'PASS' if parity else 'FAIL'}** {counts}\n- Reversal score reconstruction: **{'PASS' if score_parity else 'FAIL'}**\n- Causality: **{'PASS' if causal else 'FAIL'}** changed={bad}\n- Frozen Reversal transitions: **{int(ch.transition_n)}**\n- Chain completions: **{int(ch.candidates)}**\n- Chain transition recall: **{ch.transition_hits:.0f}/{ch.transition_n:.0f} = {ch.transition_recall:.3f}**\n- Chain precision 0-3 bars: **{ch.precision_0_3:.3f}** vs Stage-A **{a.precision_0_3:.3f}**, ratio **{precision_ratio:.2f}x**\n- Median lead among converted chains: **{ch.median_lead_converted:.2f} H4 bars**\n- Calendar years with chain completions: **{years_with}**\n- Gates: {gates}\n\nNo frozen Context score weights or state-machine constants were changed. Structural failure is the preregistered causal proxy: BOS against available directional bias.\n'''
    (out/'REPORT.md').write_text(report,encoding='utf-8')
    print(json.dumps(summary,indent=2))
    if not core: raise SystemExit(2)

if __name__=='__main__': main()
