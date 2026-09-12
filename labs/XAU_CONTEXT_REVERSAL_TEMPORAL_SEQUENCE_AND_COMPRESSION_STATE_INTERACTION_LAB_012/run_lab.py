#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_REVERSAL_TEMPORAL_SEQUENCE_AND_COMPRESSION_STATE_INTERACTION_LAB_012'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
LAB11_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_COMPETITION_AND_TRANSITION_OVERLAY_LAB_011'/'run_lab.py'
XAU_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
YEARS=[2023,2024,2025,2026]
BOOT_N=5000
SEED=2026091212
REV_STATES=['PULLBACK','EXPANSION','RANGE']


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


def add_future_close_24h(d:pd.DataFrame)->pd.DataFrame:
    z=d.copy().sort_index()
    idx=pd.Series(z.index,index=z.index)
    fut_idx=idx.shift(-6)
    valid=(fut_idx-idx).eq(pd.Timedelta(hours=24))
    z['close_fwd_24h']=z['close'].shift(-6).where(valid)
    return z


def add_directional_crosses(d:pd.DataFrame)->pd.DataFrame:
    z=d.copy().sort_index()
    idx=pd.Series(z.index,index=z.index)
    prev_ok=idx.shift(1).eq(idx-pd.Timedelta(hours=4))
    prev_close=z['close'].shift(1)
    prev_ema=z['ema20'].shift(1)
    z['BULL_EMA20_CROSS']=((z['close']>z['ema20'])&(prev_close<=prev_ema)&prev_ok).fillna(False)
    z['BEAR_EMA20_CROSS']=((z['close']<z['ema20'])&(prev_close>=prev_ema)&prev_ok).fillna(False)
    mom12=z['close']-z['close'].shift(3)
    mom_ok=idx.shift(3).eq(idx-pd.Timedelta(hours=12))
    z['PRE_MOM12_ANCHOR']=mom12.where(mom_ok)
    z['LOCATION']=(z['SWEEP']|z['REJECTION']).fillna(False)
    z['TRANSITION']=(z['RSI_TURN']|z['ADX_FALLING']).fillna(False)
    return z


def build_sequence(d:pd.DataFrame)->pd.DataFrame:
    z=d.copy().sort_index()
    n=len(z)
    event=np.zeros(n,dtype=bool)
    seq_dir=np.full(n,np.nan)
    anchor_pos=np.full(n,-1,dtype=int)
    trans_pos=np.full(n,-1,dtype=int)
    idx=z.index
    loc=z['LOCATION'].to_numpy(bool)
    trans=z['TRANSITION'].to_numpy(bool)
    bull=z['BULL_EMA20_CROSS'].to_numpy(bool)
    bear=z['BEAR_EMA20_CROSS'].to_numpy(bool)
    mom=z['PRE_MOM12_ANCHOR'].to_numpy(float)

    for c in range(n):
        if not (bull[c] or bear[c]):
            continue
        direction=1 if bull[c] else -1
        candidates=[]
        for a in range(max(0,c-3),c):
            dt=idx[c]-idx[a]
            if dt not in (pd.Timedelta(hours=4),pd.Timedelta(hours=8),pd.Timedelta(hours=12)):
                continue
            if not loc[a] or not np.isfinite(mom[a]) or mom[a]==0:
                continue
            if direction==1 and not (mom[a]<0):
                continue
            if direction==-1 and not (mom[a]>0):
                continue
            bmax=min(c,a+2)
            bs=[]
            for b in range(a+1,bmax+1):
                dtb=idx[b]-idx[a]
                if dtb not in (pd.Timedelta(hours=4),pd.Timedelta(hours=8)):
                    continue
                if trans[b]:
                    bs.append(b)
            if bs:
                candidates.append((a,min(bs)))
        if candidates:
            a,b=sorted(candidates,key=lambda x:(x[0],x[1]))[0]
            event[c]=True
            seq_dir[c]=direction
            anchor_pos[c]=a
            trans_pos[c]=b

    z['RSEQ_PRIMARY']=event
    z['RSEQ_DIR']=seq_dir
    z['RSEQ_ANCHOR_TIME']=pd.NaT
    z['RSEQ_TRANSITION_TIME']=pd.NaT
    z['RSEQ_A_TO_B_H']=np.nan
    z['RSEQ_A_TO_C_H']=np.nan
    evpos=np.flatnonzero(event)
    for c in evpos:
        a=anchor_pos[c]; b=trans_pos[c]
        z.iloc[c,z.columns.get_loc('RSEQ_ANCHOR_TIME')]=idx[a]
        z.iloc[c,z.columns.get_loc('RSEQ_TRANSITION_TIME')]=idx[b]
        z.iloc[c,z.columns.get_loc('RSEQ_A_TO_B_H')]=(idx[b]-idx[a]).total_seconds()/3600.0
        z.iloc[c,z.columns.get_loc('RSEQ_A_TO_C_H')]=(idx[c]-idx[a]).total_seconds()/3600.0
    z['SEQ_SIGNED_CLOSE_ATR_24H']=z['RSEQ_DIR']*(z['close_fwd_24h']-z['close'])/z['atr14'].replace(0,np.nan)
    return z


def bootstrap_one_events(d:pd.DataFrame,metric:str,mask:pd.Series,seed:int)->dict:
    q=d[['available_time',metric]].copy()
    q[metric]=pd.to_numeric(q[metric],errors='coerce')
    q['A']=mask.reindex(q.index).fillna(False).astype(bool)
    q=q[q.A].dropna(subset=['available_time',metric])
    obs=float(q[metric].mean()) if len(q) else np.nan
    if q.empty:
        return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'p_positive':np.nan,'n':0,'weeks':0}
    q['week']=week_col(q.available_time)
    stats=q.groupby('week')[metric].agg(['count','sum']).to_numpy(float)
    rng=np.random.default_rng(seed); draws=[]; m=len(stats)
    for _ in range(BOOT_N):
        s=stats[rng.integers(0,m,size=m)].sum(axis=0)
        if s[0]>0: draws.append(s[1]/s[0])
    draws=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(draws,.025)),'ci_hi':float(np.quantile(draws,.975)),
            'p_positive':float(np.mean(draws>0)),'n':int(len(q)),'weeks':int(m)}


def annual_one(d:pd.DataFrame,metric:str,mask:pd.Series,min_n:int)->pd.DataFrame:
    y=pd.to_datetime(d.available_time).dt.year
    rows=[]
    for year in YEARS:
        g=d[y.eq(year)]
        m=mask.reindex(g.index).fillna(False).astype(bool)
        v=pd.to_numeric(g.loc[m,metric],errors='coerce').dropna()
        obs=float(v.mean()) if len(v) else np.nan
        eligible=bool(len(v)>=min_n and np.isfinite(obs))
        rows.append({'year':year,'metric':metric,'n':int(len(v)),'effect':obs,
                     'eligible':eligible,'positive':bool(eligible and obs>0)})
    return pd.DataFrame(rows)


def pair_bootstrap_state(d:pd.DataFrame,metric:str,state:str,a_col:str,seed:int)->dict:
    valid=pd.to_numeric(d[metric],errors='coerce').notna()
    a=d[a_col].fillna(False).astype(bool)&d.regime.eq(state)&valid
    b=(~d[a_col].fillna(False).astype(bool))&d.regime.eq(state)&valid
    lab10=pair_bootstrap_state.lab10
    r=lab10.cluster_bootstrap_masks(d,metric,a,b,seed)
    r.update(state=state,metric=metric,n_a=int(a.sum()),n_b=int(b.sum()))
    return r


def annual_pair_state(d:pd.DataFrame,metric:str,state:str,a_col:str,min_a:int)->pd.DataFrame:
    y=pd.to_datetime(d.available_time).dt.year
    rows=[]
    for year in YEARS:
        g=d[y.eq(year)]
        v=pd.to_numeric(g[metric],errors='coerce')
        a=g[a_col].fillna(False).astype(bool)&g.regime.eq(state)&v.notna()
        b=(~g[a_col].fillna(False).astype(bool))&g.regime.eq(state)&v.notna()
        va=v[a]; vb=v[b]
        eff=float(va.mean()-vb.mean()) if len(va) and len(vb) else np.nan
        elig=bool(len(va)>=min_a and len(vb)>0 and np.isfinite(eff))
        rows.append({'year':year,'state':state,'metric':metric,'n_a':int(len(va)),'n_b':int(len(vb)),
                     'effect':eff,'eligible':elig,'positive':bool(elig and eff>0)})
    return pd.DataFrame(rows)


def interaction_bootstrap(d:pd.DataFrame,metric:str,a_col:str,seed:int)->dict:
    q=d[['available_time','regime',metric]].copy()
    q[metric]=pd.to_numeric(q[metric],errors='coerce')
    q['A']=d[a_col].reindex(q.index).fillna(False).astype(bool)
    q=q[q.regime.isin(['PULLBACK','EXPANSION'])].dropna(subset=['available_time',metric])

    def premium(g,state):
        h=g[g.regime.eq(state)]
        va=h.loc[h.A,metric]; vb=h.loc[~h.A,metric]
        return float(va.mean()-vb.mean()) if len(va) and len(vb) else np.nan
    p_pb=premium(q,'PULLBACK'); p_ex=premium(q,'EXPANSION')
    obs=float(p_pb-p_ex) if np.isfinite(p_pb) and np.isfinite(p_ex) else np.nan
    counts={s:{'n_a':int((q.regime.eq(s)&q.A).sum()),'n_b':int((q.regime.eq(s)&(~q.A)).sum())} for s in ['PULLBACK','EXPANSION']}
    q['week']=week_col(q.available_time); weeks=sorted(q.week.unique())
    arr=np.zeros((len(weeks),2,4),float); states=['PULLBACK','EXPANSION']
    for wi,w in enumerate(weeks):
        g=q[q.week.eq(w)]
        for si,s in enumerate(states):
            h=g[g.regime.eq(s)]; a=h.loc[h.A,metric].to_numpy(float); b=h.loc[~h.A,metric].to_numpy(float)
            arr[wi,si]=[len(a),np.nansum(a),len(b),np.nansum(b)]
    rng=np.random.default_rng(seed); draws=[]; m=len(weeks)
    for _ in range(BOOT_N):
        t=arr[rng.integers(0,m,size=m)].sum(axis=0); prem=[]
        for si in range(2):
            na,sa,nb,sb=t[si]
            prem.append(sa/na-sb/nb if na>0 and nb>0 else np.nan)
        if np.isfinite(prem[0]) and np.isfinite(prem[1]): draws.append(prem[0]-prem[1])
    draws=np.asarray(draws,float)
    return {'observed':obs,'pullback_premium':p_pb,'expansion_premium':p_ex,
            'ci_lo':float(np.quantile(draws,.025)) if len(draws) else np.nan,
            'ci_hi':float(np.quantile(draws,.975)) if len(draws) else np.nan,
            'p_positive':float(np.mean(draws>0)) if len(draws) else np.nan,
            'weeks':int(m),'counts':counts}


def future_expansion_12h(d:pd.DataFrame)->pd.Series:
    z=d.sort_index(); idx=pd.Series(z.index,index=z.index); out=pd.Series(False,index=z.index,dtype=bool)
    valid_any=pd.Series(False,index=z.index,dtype=bool)
    for k in [1,2,3]:
        ok=(idx.shift(-k)-idx).eq(pd.Timedelta(hours=4*k))
        valid_any|=ok
        out|=(ok & z.regime.shift(-k).eq('EXPANSION'))
    return out.where(valid_any,np.nan)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1)
    if sha256(p)!=XAU_SHA: raise RuntimeError('Canonical XAU SHA mismatch')

    lab8=load_module(LAB8_PATH,'lab8_012'); lab9=load_module(LAB9_PATH,'lab9_012')
    lab10=load_module(LAB10_PATH,'lab10_012'); lab11=load_module(LAB11_PATH,'lab11_012')
    pair_bootstrap_state.lab10=lab10

    m1=lab8.read_xau_native(p); h4=lab8.to_h4(m1); router=lab8.load_router_module()
    ctx=router.add_router(h4); ctx=lab8.add_forward_metrics(ctx); ctx=ctx.dropna(subset=['available_time','atr14']).copy()
    allbars,onset=lab8.make_episodes(ctx)
    if len(allbars)!=6216 or len(onset)!=610:
        raise RuntimeError(f'Parity failed bars={len(allbars)} episodes={len(onset)}')
    d=lab9.add_roles(allbars); d=lab10.add_components_and_candidates(d); d=lab11.add_competition_fields(d)
    d=add_future_close_24h(d); d=add_directional_crosses(d); d=build_sequence(d)
    d['FUTURE_EXPANSION_12H']=future_expansion_12h(d)

    # ---------------- Reversal sequence ----------------
    seq=d.RSEQ_PRIMARY & d.regime.isin(REV_STATES)
    valid24=pd.to_numeric(d.momentum_flip_24h,errors='coerce').notna()
    ra=seq&valid24; rb=(~d.RSEQ_PRIMARY)&d.regime.isin(REV_STATES)&valid24
    r_h1_raw=lab11.strat_bootstrap(d,'momentum_flip_24h',ra,rb,REV_STATES,SEED+1)
    d['RSEQ_MAIN_EVENT']=seq
    r_h1_year=lab11.annual_stratified(d,'momentum_flip_24h','RSEQ_MAIN_EVENT',REV_STATES,5)
    r_state=lab11.per_state_premiums(d,'momentum_flip_24h','RSEQ_MAIN_EVENT',REV_STATES)
    r_n2025=int(r_h1_year.loc[r_h1_year.year.eq(2025),'n_a'].iloc[0]); r_n2026=int(r_h1_year.loc[r_h1_year.year.eq(2026),'n_a'].iloc[0])
    r_eligible=bool(r_h1_raw['n_a']>=30 and r_n2025>=5 and r_n2026>=5 and int((r_state.n_a>=5).sum())>=2)
    r_transfer=bool(int(r_h1_year.eligible.sum())>=3 and int(r_h1_year.positive.sum())>=3)
    r_h1_pass=bool(r_eligible and r_h1_raw['observed']>0 and np.isfinite(r_h1_raw['ci_lo']) and r_h1_raw['ci_lo']>0 and r_transfer)

    r_h2_raw=bootstrap_one_events(d,'SEQ_SIGNED_CLOSE_ATR_24H',seq,SEED+2)
    r_h2_year=annual_one(d,'SEQ_SIGNED_CLOSE_ATR_24H',seq,5)
    r_h2_transfer=bool(int(r_h2_year.eligible.sum())>=3 and int(r_h2_year.positive.sum())>=3)
    r_h2_pass=bool(r_eligible and r_h2_raw['observed']>0 and np.isfinite(r_h2_raw['ci_lo']) and r_h2_raw['ci_lo']>0 and r_h2_transfer)

    r_secondary=[]
    for i,h in enumerate([8,12]):
        metric=f'momentum_flip_{h}h'; valid=pd.to_numeric(d[metric],errors='coerce').notna()
        a=seq&valid; b=(~d.RSEQ_PRIMARY)&d.regime.isin(REV_STATES)&valid
        rec=lab11.strat_bootstrap(d,metric,a,b,REV_STATES,SEED+10+i); rec.update(horizon_h=h,metric=metric); r_secondary.append(rec)

    seq_events=d[seq].copy()
    seq_diag=seq_events[['available_time','regime','RSEQ_DIR','RSEQ_ANCHOR_TIME','RSEQ_TRANSITION_TIME','RSEQ_A_TO_B_H','RSEQ_A_TO_C_H','momentum_flip_24h','SEQ_SIGNED_CLOSE_ATR_24H','R3_RAW_REVERSAL_WINNER','competition_class']].copy()
    seq_diag['year']=pd.to_datetime(seq_diag.available_time).dt.year
    seq_diag['direction']=np.where(seq_diag.RSEQ_DIR>0,'BULL','BEAR')
    overlap={
        'sequence_events':int(seq.sum()),
        'overlap_r3':int((seq&d.R3_RAW_REVERSAL_WINNER).sum()),
        'overlap_r3_suppressed':int((seq&d.competition_class.isin(['SMOOTHING_SUPPRESSED','HYSTERESIS_SUPPRESSED'])).sum()),
        'bull':int((seq&d.RSEQ_DIR.eq(1)).sum()),
        'bear':int((seq&d.RSEQ_DIR.eq(-1)).sum()),
    }

    # ---------------- Compression interaction ----------------
    d['C_G1']=d.G1_VOL_COMPRESSION.fillna(False).astype(bool)
    c_h1=pair_bootstrap_state(d,'breakout_1atr_8h','PULLBACK','C_G1',SEED+100)
    c_h1_year=annual_pair_state(d,'breakout_1atr_8h','PULLBACK','C_G1',50)
    c_h1_elig=bool(c_h1['n_a']>=300 and int(c_h1_year.loc[c_h1_year.year.eq(2025),'n_a'].iloc[0])>=50 and int(c_h1_year.loc[c_h1_year.year.eq(2026),'n_a'].iloc[0])>=50)
    c_h1_transfer=bool(c_h1_year.eligible.all() and int(c_h1_year.positive.sum())>=3)
    c_h1_pass=bool(c_h1_elig and c_h1['observed']>0 and np.isfinite(c_h1['ci_lo']) and c_h1['ci_lo']>0 and c_h1_transfer)

    c_h2=pair_bootstrap_state(d,'range_atr_24h','PULLBACK','C_G1',SEED+101)
    c_h2_year=annual_pair_state(d,'range_atr_24h','PULLBACK','C_G1',50)
    c_h2_elig=bool(c_h2['n_a']>=300 and int(c_h2_year.loc[c_h2_year.year.eq(2025),'n_a'].iloc[0])>=50 and int(c_h2_year.loc[c_h2_year.year.eq(2026),'n_a'].iloc[0])>=50)
    c_h2_transfer=bool(c_h2_year.eligible.all() and int(c_h2_year.positive.sum())>=3)
    c_h2_pass=bool(c_h2_elig and c_h2['observed']>0 and np.isfinite(c_h2['ci_lo']) and c_h2['ci_lo']>0 and c_h2_transfer)

    c_h3=interaction_bootstrap(d,'breakout_1atr_8h','C_G1',SEED+102)
    pb_na=c_h3['counts']['PULLBACK']['n_a']; ex_na=c_h3['counts']['EXPANSION']['n_a']
    c_h3_elig=bool(pb_na>=300 and ex_na>=20 and c_h3['counts']['PULLBACK']['n_b']>0 and c_h3['counts']['EXPANSION']['n_b']>0)
    c_h3_pass=bool(c_h3_elig and c_h3['observed']>0 and np.isfinite(c_h3['ci_lo']) and c_h3['ci_lo']>0)

    comp_secondary=[]
    for state in ['PULLBACK','EXPANSION','RANGE']:
        for h in [4,8,12]:
            metric=f'breakout_1atr_{h}h'
            if metric not in d.columns:
                d[metric]=1.0-pd.to_numeric(d[f'contained_1atr_{h}h'],errors='coerce')
            rec=pair_bootstrap_state(d,metric,state,'C_G1',SEED+200+len(comp_secondary)); rec.update(horizon_h=h); comp_secondary.append(rec)
    exp24=pair_bootstrap_state(d,'range_atr_24h','EXPANSION','C_G1',SEED+230)
    range24=pair_bootstrap_state(d,'range_atr_24h','RANGE','C_G1',SEED+231)
    futexp=pair_bootstrap_state(d,'FUTURE_EXPANSION_12H','PULLBACK','C_G1',SEED+232)

    prevalence=(d.assign(year=pd.to_datetime(d.available_time).dt.year)
                  .groupby(['year','regime']).agg(bars=('regime','size'),g1=('C_G1','sum')).reset_index())
    prevalence['g1_prevalence']=prevalence.g1/prevalence.bars

    gates={
        'R_H1':{'eligible':r_eligible,'pass':r_h1_pass,'effect':r_h1_raw['observed'],'ci_lo':r_h1_raw['ci_lo'],'ci_hi':r_h1_raw['ci_hi'],'transfer':r_transfer},
        'R_H2':{'eligible':r_eligible,'pass':r_h2_pass,'effect':r_h2_raw['observed'],'ci_lo':r_h2_raw['ci_lo'],'ci_hi':r_h2_raw['ci_hi'],'transfer':r_h2_transfer},
        'C_H1':{'eligible':c_h1_elig,'pass':c_h1_pass,'effect':c_h1['observed'],'ci_lo':c_h1['ci_lo'],'ci_hi':c_h1['ci_hi'],'transfer':c_h1_transfer},
        'C_H2':{'eligible':c_h2_elig,'pass':c_h2_pass,'effect':c_h2['observed'],'ci_lo':c_h2['ci_lo'],'ci_hi':c_h2['ci_hi'],'transfer':c_h2_transfer},
        'C_H3':{'eligible':c_h3_elig,'pass':c_h3_pass,'effect':c_h3['observed'],'ci_lo':c_h3['ci_lo'],'ci_hi':c_h3['ci_hi'],'transfer':None},
    }
    passes=sum(int(v['pass']) for v in gates.values())
    reversal_pass=r_h1_pass and r_h2_pass; compression_primary=c_h1_pass and c_h2_pass
    if passes==5:
        verdict='TEMPORAL_SEQUENCE_AND_COMPRESSION_INTERACTION_SUPPORTED_DISCOVERY_ONLY'
    elif compression_primary and not (r_h1_pass or r_h2_pass):
        verdict='COMPRESSION_INTERACTION_SUPPORTED_REVERSAL_SEQUENCE_NOT_CONFIRMED'
    elif reversal_pass and not (c_h1_pass or c_h2_pass):
        verdict='REVERSAL_SEQUENCE_SUPPORTED_COMPRESSION_INTERACTION_NOT_CONFIRMED'
    elif 2<=passes<=4 and (r_h1_pass or r_h2_pass) and (c_h1_pass or c_h2_pass or c_h3_pass):
        verdict='PARTIAL_TEMPORAL_SEQUENCE_COMPRESSION_SUPPORT'
    elif (not r_eligible) and (not c_h1_elig):
        verdict='LAB012_UNDERPOWERED'
    else:
        verdict='TEMPORAL_SEQUENCE_AND_COMPRESSION_INTERACTION_NOT_SUPPORTED'

    # outputs
    pd.DataFrame(r_secondary).drop(columns=['strata'],errors='ignore').to_csv(out/'reversal_secondary_horizons.csv',index=False)
    r_h1_year.to_csv(out/'reversal_sequence_year_transfer.csv',index=False)
    r_h2_year.to_csv(out/'reversal_followthrough_year_transfer.csv',index=False)
    r_state.to_csv(out/'reversal_sequence_state_premiums.csv',index=False)
    seq_diag.to_csv(out/'reversal_sequence_events.csv',index=False)
    c_h1_year.to_csv(out/'compression_pullback_breakout_year_transfer.csv',index=False)
    c_h2_year.to_csv(out/'compression_pullback_range_year_transfer.csv',index=False)
    pd.DataFrame(comp_secondary).to_csv(out/'compression_state_horizon_semantics.csv',index=False)
    prevalence.to_csv(out/'compression_prevalence_by_state_year.csv',index=False)

    summary={
        'lab':LAB,'verdict':verdict,'valid_context_bars':int(len(d)),'episode_onsets':int(len(onset)),
        'sequence_overlap':overlap,'gates':gates,
        'r_h1':r_h1_raw,'r_h2':r_h2_raw,'r_state':r_state.to_dict('records'),
        'c_h1':c_h1,'c_h2':c_h2,'c_h3':c_h3,
        'compression_expansion_24h':exp24,'compression_range_24h':range24,'compression_future_expansion_12h':futexp,
    }
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    def f(x): return 'NA' if x is None or not np.isfinite(x) else f'{x:+.4f}'
    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',
           '> Indicator temporal-sequence / state-interaction diagnostic only. No trading edge or execution claim.','',
           f'- Valid Context H4 bars: **{len(d):,}**',f'- Frozen episodes: **{len(onset):,}**',
           f'- RSEQ events: **{overlap["sequence_events"]}** (BULL {overlap["bull"]}, BEAR {overlap["bear"]})',
           f'- RSEQ overlap with raw R3: **{overlap["overlap_r3"]}**; suppressed R3 overlap: **{overlap["overlap_r3_suppressed"]}**','',
           '## Primary gates','','| Gate | Eligible | Effect | 95% CI | Transfer | Pass |','|---|---|---:|---:|---|---|']
    for k,v in gates.items():
        lines.append(f'| {k} | {"YES" if v["eligible"] else "NO"} | {f(v["effect"])} | [{f(v["ci_lo"])}, {f(v["ci_hi"])}] | {"NA" if v["transfer"] is None else ("PASS" if v["transfer"] else "FAIL")} | {"PASS" if v["pass"] else "FAIL"} |')
    lines += ['', '## Reversal sequence by main state','', '| State | N event | N control | 24h flip premium |','|---|---:|---:|---:|']
    for r in r_state.to_dict('records'):
        lines.append(f'| {r["state"]} | {r["n_a"]} | {r["n_b"]} | {f(r["effect"])} |')
    lines += ['', '## Compression interaction','',
              f'- Pullback 8h breakout premium: **{f(c_h1["observed"])}**, CI [{f(c_h1["ci_lo"])}, {f(c_h1["ci_hi"])}].',
              f'- Pullback 24h range premium: **{f(c_h2["observed"])} ATR**, CI [{f(c_h2["ci_lo"])}, {f(c_h2["ci_hi"])}].',
              f'- Pullback minus Expansion 8h breakout interaction: **{f(c_h3["observed"])}**, CI [{f(c_h3["ci_lo"])}, {f(c_h3["ci_hi"])}].',
              f'- G1 valid counts in interaction: Pullback **{pb_na}**, Expansion **{ex_na}**.','',
              '## Interpretation constraints','',
              '- One ordered reversal sequence and frozen G1 compression were preregistered before outcomes; no variant/threshold search is allowed.',
              '- Positive reused-history findings remain DISCOVERY_ONLY until fresh post-freeze replication.',
              '- This lab supports display semantics only; it cannot authorize automated entries or risk changes.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'verdict':verdict,'passes':passes,'sequence_events':overlap['sequence_events'],'C_H1':c_h1['observed'],'C_H2':c_h2['observed'],'C_H3':c_h3['observed']},indent=2))

if __name__=='__main__':
    main()
