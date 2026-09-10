#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='CONTEXT_REVERSAL_COMPONENT_TEMPORAL_SEQUENCE_AND_EVENT_TO_STATE_AGGREGATION_LAB_013'
ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'labs'/'CONTEXT_INDICATOR_PUBLIC_SPEC_GAP_CLOSURE_AND_NEXT_CONTEXT_LAB_010'/'run_lab.py'
WEIGHTS={'swing_sweep':30.0,'rsi_turn':20.0,'rsi_rhythm_turn':15.0,'ema20_cross':15.0,'adx_decay':10.0,'rejection_wick':10.0}
REGIMES=['EXPANSION','PULLBACK','REVERSAL','RANGE']

def load_parent():
    sp=importlib.util.spec_from_file_location('ctx010_for_013',PARENT)
    m=importlib.util.module_from_spec(sp); assert sp.loader is not None; sp.loader.exec_module(m); return m

def component_events(d):
    prev=d.rsi14.shift(1)
    turn=((prev<35)&(d.rsi14>prev))|((prev>65)&(d.rsi14<prev))
    rhythm=(d.rsi_rhythm_up.ne(d.rsi_rhythm_up.shift(1))) & d.rsi_ema9.notna() & d.rsi_wma45.notna()
    return pd.DataFrame({
        'swing_sweep':d.swing_sweep.fillna(False),
        'rsi_turn':turn.fillna(False),
        'rsi_rhythm_turn':rhythm.fillna(False),
        'ema20_cross':d.cross_ema20.fillna(False),
        'adx_decay':(d.adx14<d.adx14.shift(1)).fillna(False),
        'rejection_wick':(d.rejection_wick>=.45).fillna(False),
    },index=d.index).astype(bool)

def seq_features(ev, raw_scores):
    out={}
    nonrev=raw_scores[['EXPANSION','PULLBACK','RANGE']]
    for w in [1,2,3]:
        a=ev.rolling(w,min_periods=1).max().astype(bool)
        score=sum(a[c].astype(float)*WEIGHTS[c] for c in WEIGHTS).clip(0,100)
        count=a.sum(axis=1)
        comp=pd.concat([nonrev,score.rename('REVERSAL')],axis=1)
        rank=comp.rank(axis=1,ascending=False,method='min')['REVERSAL']
        out[w]=pd.DataFrame({'seq_score':score,'active_count':count,'rank':rank,'top2':rank<=2},index=ev.index)
    return out

def causal_equal(a,b):
    if len(a)!=len(b): return False
    aa=np.asarray(a); bb=np.asarray(b)
    if aa.dtype.kind in 'fci' or bb.dtype.kind in 'fci': return bool(np.allclose(aa.astype(float),bb.astype(float),rtol=0,atol=1e-10,equal_nan=True))
    return bool(pd.Series(a).fillna('__NA__').astype(str).equals(pd.Series(b).fillna('__NA__').astype(str)))

def build_all(p,h1):
    old=p.load_old(); h4=old.to_h4(h1); d1=p.build_d1(h1,old); ctx,sm=p.build_router(h4,d1,old); ind=p.indicators_enhanced(h4,d1,old)
    ev=component_events(ind)
    raw=ctx[[f'score_{r.lower()}' for r in REGIMES]].copy(); raw.columns=REGIMES
    seq=seq_features(ev,raw)
    return ctx,ind,ev,raw,seq

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    p=load_parent(); old=p.load_old(); h1,meta=old.fetch_binance_futures_h1('2020-01','2026-07')
    ctx,ind,ev,raw,seq=build_all(p,h1)

    expected={'PULLBACK':7641,'EXPANSION':4568,'RANGE':2184,'REVERSAL':29}
    counts={k:int(v) for k,v in ctx.regime.value_counts().items()}; parity=(counts==expected)
    reconstructed=sum(ev[c].astype(float)*WEIGHTS[c] for c in WEIGHTS).clip(0,100)
    score_parity=bool(np.allclose(reconstructed.to_numpy(),raw.REVERSAL.to_numpy(),rtol=0,atol=1e-10,equal_nan=True))

    # transition-conditioned rows
    tr=[]; rg=ctx.regime
    idx=np.flatnonzero(rg.ne(rg.shift(1)).fillna(False).to_numpy())
    for i in idx:
        if i<=3 or pd.isna(rg.iloc[i]): continue
        dest=str(rg.iloc[i])
        for lag in [1,2,3]:
            j=i-lag
            for w in [1,2,3]:
                f=seq[w].iloc[j]
                tr.append({'transition_time':ctx.index[i],'destination':dest,'lag':lag,'window':w,'seq_score':float(f.seq_score),'active_count':float(f.active_count),'rank':float(f['rank']),'top2':bool(f.top2)})
    tdf=pd.DataFrame(tr); tdf.to_csv(out/'transition_sequence_audit.csv',index=False)
    agg=tdf.groupby(['destination','lag','window']).agg(n=('rank','size'),mean_score=('seq_score','mean'),median_score=('seq_score','median'),mean_active=('active_count','mean'),median_active=('active_count','median'),top2_share=('top2','mean'),median_rank=('rank','median')).reset_index()
    agg.to_csv(out/'transition_sequence_summary.csv',index=False)

    # candidate conversion: rank<=2 at t, did frozen regime become REVERSAL in next 1..H bars?
    conv=[]
    for w in [1,2,3]:
        cand=seq[w]['top2'].fillna(False).to_numpy(); rr=rg.to_numpy()
        for h in [1,2,3]:
            n=hit=0
            for i in np.flatnonzero(cand):
                if i+h>=len(rr): continue
                n+=1
                if any(x=='REVERSAL' for x in rr[i+1:i+h+1]): hit+=1
            conv.append({'window':w,'horizon_bars':h,'candidates':n,'converted':hit,'conversion':hit/n if n else np.nan})
    pd.DataFrame(conv).to_csv(out/'candidate_conversion.csv',index=False)

    # nontransition W3 background, matched descriptively by year + volatility state
    trans_times=set(tdf.transition_time.astype(str)) if not tdf.empty else set()
    ar=ind.atr_ratio_public.reindex(ctx.index)
    vol=np.select([ar<.80,ar>1.35],['LOW','HIGH'],default='NORMAL')
    bg=pd.DataFrame({'time':ctx.index,'year':ctx.index.year,'vol_state':vol,'active_w3':seq[3].active_count,'score_w3':seq[3].seq_score,'is_transition':ctx.index.astype(str).isin(trans_times)})
    bg[~bg.is_transition].groupby(['year','vol_state']).agg(n=('active_w3','size'),median_active=('active_w3','median'),mean_active=('active_w3','mean'),median_score=('score_w3','median')).reset_index().to_csv(out/'nontransition_background.csv',index=False)

    # ordering around actual REVERSAL transitions; offsets -2,-1,0 relative to destination bar
    ordrows=[]
    rev_ix=[i for i in idx if i>=2 and rg.iloc[i]=='REVERSAL']
    for i in rev_ix:
        row={'transition_time':str(ctx.index[i])}
        for c in WEIGHTS:
            offs=[o for o in [-2,-1,0] if bool(ev[c].iloc[i+o])]
            row[c+'_first_offset']=min(offs) if offs else np.nan
        ordrows.append(row)
    odf=pd.DataFrame(ordrows); odf.to_csv(out/'reversal_event_ordering.csv',index=False)

    # causality: only bars whose available_time <= cutoff
    cut=int(len(h1)*.72); ct=h1.time.iloc[cut]
    hp=h1.copy(); fut=hp.time>ct
    for c in ['open','high','low','close']: hp.loc[fut,c]=hp.loc[fut,c]*np.linspace(1.5,3.0,int(fut.sum()))
    hp.loc[fut,'volume']=hp.loc[fut,'volume']*17+12345
    c2,i2,e2,r2,s2=build_all(p,hp)
    safe=ctx.index[(ctx.index+pd.Timedelta(hours=4))<=ct]
    bad=[]
    for w in [1,2,3]:
        for col in ['seq_score','active_count','rank','top2']:
            common=safe.intersection(s2[w].index)
            if not causal_equal(seq[w].loc[common,col].to_numpy(),s2[w].loc[common,col].to_numpy()): bad.append(f'W{w}_{col}')
    causal_pass=len(bad)==0

    # prereg classification using lag=1 REVERSAL rows
    def cell(w,col):
        z=agg[(agg.destination=='REVERSAL')&(agg.lag==1)&(agg.window==w)]
        return float(z.iloc[0][col]) if len(z) else np.nan
    A1=cell(1,'median_active'); A3=cell(3,'median_active'); T1=cell(1,'top2_share'); T3=cell(3,'top2_share')
    # global eligible non-transition background median as prereg conservative comparator
    nt=float(bg.loc[~bg.is_transition,'active_w3'].median())
    cond1=bool(np.isfinite(A3) and np.isfinite(A1) and A3>=A1+1)
    cond2=bool(np.isfinite(T3) and np.isfinite(T1) and T3>=T1+.15)
    cond3=bool(np.isfinite(A3) and A3>=nt+1)
    passed=sum([cond1,cond2,cond3])
    if not parity or not score_parity: verdict='PARENT_PARITY_FAIL'
    elif not causal_pass: verdict='CAUSALITY_FAIL'
    elif passed==3: verdict='TEMPORAL_SEQUENCE_SUPPORTED'
    elif passed>=2: verdict='WEAK_TEMPORAL_SEQUENCE_SIGNAL'
    else: verdict='SAME_BAR_MODEL_NOT_REJECTED'

    summary={'lab':LAB,'verdict':verdict,'parent_counts':counts,'parent_parity':parity,'reversal_score_parity':score_parity,'causality_pass':causal_pass,'causality_changed':bad,
             'reversal_transitions':len(rev_ix),'A1_rev_lag1':A1,'A3_rev_lag1':A3,'top2_W1_rev_lag1':T1,'top2_W3_rev_lag1':T3,'nontransition_W3_median_active':nt,
             'conditions':{'A3_ge_A1_plus1':cond1,'top2_W3_ge_W1_plus15pp':cond2,'A3_ge_background_plus1':cond3}}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    report=f'''# {LAB}\n\n**Verdict: {verdict}**\n\n- Parent parity: **{'PASS' if parity else 'FAIL'}** {counts}\n- Reversal score reconstruction: **{'PASS' if score_parity else 'FAIL'}**\n- Causality: **{'PASS' if causal_pass else 'FAIL'}** changed={bad}\n- Frozen Reversal transitions: **{len(rev_ix)}**\n- Lag1 median active components: W1 **{A1:.3f}** → W3 **{A3:.3f}**\n- Lag1 rank<=2 share: W1 **{T1:.3f}** → W3 **{T3:.3f}**\n- Non-transition W3 median active components: **{nt:.3f}**\n- Preregistered conditions: {summary['conditions']}\n\nNo score weights or state-machine constants were changed.\n'''
    (out/'REPORT.md').write_text(report,encoding='utf-8')
    print(json.dumps(summary,indent=2))
    if not parity or not score_parity or not causal_pass: raise SystemExit(2)

if __name__=='__main__': main()
