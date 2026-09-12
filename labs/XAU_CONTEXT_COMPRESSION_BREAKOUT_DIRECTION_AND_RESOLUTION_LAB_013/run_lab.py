#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
XAU_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
YEARS=[2023,2024,2025,2026]
BOOT_N=5000
SEED=2026091213
CANDS=['D1_HTF_BIAS','D2_TREND_PRESSURE','D3_PRE12H_MOMENTUM','D4_CONSENSUS_2OF3']


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


def add_prediction_candidates(d:pd.DataFrame)->pd.DataFrame:
    z=d.copy().sort_index()
    z['D1_HTF_BIAS']=z['bias'].map({'BULL':1,'BEAR':-1}).fillna(0).astype(int)
    bull=(z['close']>z['ema20'])&(z['ema20']>z['ema50'])&(z['slope50_atr']>0)
    bear=(z['close']<z['ema20'])&(z['ema20']<z['ema50'])&(z['slope50_atr']<0)
    z['D2_TREND_PRESSURE']=np.select([bull,bear],[1,-1],default=0).astype(int)
    z['D3_PRE12H_MOMENTUM']=np.sign(pd.to_numeric(z['pre_mom_dir'],errors='coerce')).fillna(0).astype(int)
    votes=z[['D1_HTF_BIAS','D2_TREND_PRESSURE','D3_PRE12H_MOMENTUM']]
    bull_n=(votes==1).sum(axis=1); bear_n=(votes==-1).sum(axis=1)
    z['D4_CONSENSUS_2OF3']=np.select([bull_n>=2,bear_n>=2],[1,-1],default=0).astype(int)
    return z


def exact_first_passage(m1:pd.DataFrame,d:pd.DataFrame,pop:pd.Series)->pd.DataFrame:
    mt=pd.to_datetime(m1['time']).to_numpy(dtype='datetime64[ns]')
    mh=m1['high'].to_numpy(float); ml=m1['low'].to_numpy(float)
    rows=[]
    for idx,r in d.loc[pop].iterrows():
        t0=np.datetime64(pd.Timestamp(r['available_time']).to_datetime64(),'ns')
        t1=t0+np.timedelta64(8,'h')
        a=int(np.searchsorted(mt,t0,side='left')); b=int(np.searchsorted(mt,t1,side='left'))
        up=float(r['close']+r['atr14']); dn=float(r['close']-r['atr14'])
        label='NO_BREAKOUT'; direction=0; touch_time=pd.NaT; mins=np.nan
        for j in range(a,b):
            hu=mh[j]>=up; hd=ml[j]<=dn
            if hu and hd:
                label='AMBIGUOUS'; direction=0; touch_time=pd.Timestamp(mt[j]); mins=float((mt[j]-t0)/np.timedelta64(1,'m')); break
            if hu:
                label='BULL_FIRST'; direction=1; touch_time=pd.Timestamp(mt[j]); mins=float((mt[j]-t0)/np.timedelta64(1,'m')); break
            if hd:
                label='BEAR_FIRST'; direction=-1; touch_time=pd.Timestamp(mt[j]); mins=float((mt[j]-t0)/np.timedelta64(1,'m')); break
        rows.append({'h4_index':idx,'resolution':label,'target_dir':direction,'touch_time':touch_time,'time_to_touch_min':mins})
    return pd.DataFrame(rows).set_index('h4_index')


def cluster_boot_mean(q:pd.DataFrame,metric:str,seed:int)->dict:
    z=q[['available_time',metric]].copy()
    z[metric]=pd.to_numeric(z[metric],errors='coerce')
    z=z.dropna(subset=['available_time',metric])
    obs=float(z[metric].mean()) if len(z) else np.nan
    if z.empty:
        return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'p_positive':np.nan,'n':0,'weeks':0}
    z['week']=week_col(z.available_time)
    arr=z.groupby('week')[metric].agg(['count','sum']).to_numpy(float)
    rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[0]>0: draws.append(s[1]/s[0])
    draws=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(draws,.025)),'ci_hi':float(np.quantile(draws,.975)),
            'p_positive':float(np.mean(draws>0)),'n':int(len(z)),'weeks':int(m)}


def annual_accuracy(q:pd.DataFrame,pred_col:str)->pd.DataFrame:
    y=pd.to_datetime(q.available_time).dt.year
    rows=[]
    for year in YEARS:
        g=q[y.eq(year)]
        m=(g[pred_col]!=0)&g.target_dir.isin([-1,1])
        h=g[m]
        acc=float((h[pred_col]==h.target_dir).mean()) if len(h) else np.nan
        eligible=bool(len(h)>=20 and np.isfinite(acc))
        rows.append({'candidate':pred_col,'year':year,'n':int(len(h)),'accuracy':acc,
                     'eligible':eligible,'positive':bool(eligible and acc>0.5)})
    return pd.DataFrame(rows)


def annual_follow(q:pd.DataFrame,pred_col:str)->pd.DataFrame:
    y=pd.to_datetime(q.available_time).dt.year
    rows=[]
    for year in YEARS:
        g=q[y.eq(year)]
        metric=f'{pred_col}_signed24'
        v=pd.to_numeric(g.loc[g[pred_col]!=0,metric],errors='coerce').dropna()
        mean=float(v.mean()) if len(v) else np.nan
        eligible=bool(len(v)>=20 and np.isfinite(mean))
        rows.append({'candidate':pred_col,'year':year,'n':int(len(v)),'mean_signed24_atr':mean,
                     'eligible':eligible,'positive':bool(eligible and mean>0)})
    return pd.DataFrame(rows)


def evaluate_candidate(d:pd.DataFrame,pop:pd.Series,c:str,seed:int)->tuple[dict,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    q=d.loc[pop].copy()
    pred=q[c].astype(int)
    directional=pred.ne(0)
    resolved=q.target_dir.isin([-1,1])
    primary=q[directional&resolved].copy()
    primary['correct']=(primary[c]==primary.target_dir).astype(float)
    boot=cluster_boot_mean(primary,'correct',seed)
    years=annual_accuracy(q,c)
    coverage=float(directional.mean()) if len(q) else np.nan
    resolved_coverage=float((directional&resolved).sum()/resolved.sum()) if int(resolved.sum()) else np.nan
    n2025=int(years.loc[years.year.eq(2025),'n'].iloc[0]); n2026=int(years.loc[years.year.eq(2026),'n'].iloc[0])
    eligible=bool(len(primary)>=100 and coverage>=0.30 and n2025>=20 and n2026>=20)
    transfer=bool(int(years.eligible.sum())>=3 and int(years.positive.sum())>=3)
    h1=bool(eligible and boot['observed']>0.5 and np.isfinite(boot['ci_lo']) and boot['ci_lo']>0.5 and transfer)

    q[f'{c}_signed24']=q[c]*pd.to_numeric(q['close_ret_atr_24h'],errors='coerce')
    follow_q=q[q[c]!=0][['available_time',f'{c}_signed24']].copy()
    fboot=cluster_boot_mean(follow_q,f'{c}_signed24',seed+100)
    # attach metric for year table
    q[f'{c}_signed24']=q[c]*pd.to_numeric(q['close_ret_atr_24h'],errors='coerce')
    fyears=annual_follow(q,c)
    ftransfer=bool(int(fyears.eligible.sum())>=3 and int(fyears.positive.sum())>=3)
    h2=bool(fboot['n']>=150 and fboot['observed']>0 and np.isfinite(fboot['ci_lo']) and fboot['ci_lo']>0 and ftransfer)

    sides=[]
    for sign,name in [(1,'BULL'),(-1,'BEAR')]:
        s=primary[primary[c].eq(sign)]
        sides.append({'candidate':c,'prediction':name,'n':int(len(s)),
                      'accuracy':float(s.correct.mean()) if len(s) else np.nan,
                      'mean_signed24_atr':float((s[c]*pd.to_numeric(s.close_ret_atr_24h,errors='coerce')).mean()) if len(s) else np.nan})
    diag=pd.DataFrame(sides)

    with_bias=q.bias.map({'BULL':1,'BEAR':-1}).fillna(0).astype(int)
    align=[]
    cls=np.select([(with_bias!=0)&(q[c]==with_bias),(with_bias!=0)&(q[c]==-with_bias),with_bias==0],['WITH_BIAS','AGAINST_BIAS','NO_BIAS'],default='UNRESOLVED')
    q['_align']=cls
    for a in ['WITH_BIAS','AGAINST_BIAS','NO_BIAS']:
        s=q[(q._align==a)&q[c].ne(0)&q.target_dir.isin([-1,1])]
        align.append({'candidate':c,'alignment':a,'n':int(len(s)),
                      'accuracy':float((s[c]==s.target_dir).mean()) if len(s) else np.nan})

    rec={'candidate':c,'eligible_h1':eligible,'coverage_all':coverage,'coverage_resolved':resolved_coverage,
         'n_resolved_predictions':int(len(primary)),'accuracy':float(boot['observed']),'acc_ci_lo':float(boot['ci_lo']),
         'acc_ci_hi':float(boot['ci_hi']),'positive_years_h1':int(years.positive.sum()),'eligible_years_h1':int(years.eligible.sum()),
         'transfer_h1':transfer,'pass_h1':h1,'n_follow24':int(fboot['n']),'mean_signed24_atr':float(fboot['observed']),
         'signed24_ci_lo':float(fboot['ci_lo']),'signed24_ci_hi':float(fboot['ci_hi']),
         'positive_years_h2':int(fyears.positive.sum()),'eligible_years_h2':int(fyears.eligible.sum()),
         'transfer_h2':ftransfer,'pass_h2':h2,'pass_both':bool(h1 and h2)}
    return rec,years,fyears,pd.DataFrame(align),diag


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1)
    if sha256(p)!=XAU_SHA: raise RuntimeError('Canonical XAU SHA mismatch')

    lab8=load_module(LAB8_PATH,'lab8_013'); lab9=load_module(LAB9_PATH,'lab9_013'); lab10=load_module(LAB10_PATH,'lab10_013')
    m1=lab8.read_xau_native(p); h4=lab8.to_h4(m1); router=lab8.load_router_module()
    ctx=router.add_router(h4); ctx=lab8.add_forward_metrics(ctx); ctx=ctx.dropna(subset=['available_time','atr14']).copy()
    allbars,onset=lab8.make_episodes(ctx)
    if len(allbars)!=6216 or len(onset)!=610: raise RuntimeError(f'Parity failed bars={len(allbars)} episodes={len(onset)}')
    d=lab9.add_roles(allbars); d=lab10.add_components_and_candidates(d); d=add_prediction_candidates(d)
    pop=d.regime.eq('PULLBACK')&d.G1_VOL_COMPRESSION.fillna(False)

    fp=exact_first_passage(m1,d,pop)
    d=d.join(fp,how='left')
    # exact target population and descriptive balance
    qp=d.loc[pop].copy()
    counts=qp.resolution.value_counts(dropna=False).to_dict()
    resolved=qp[qp.target_dir.isin([-1,1])]
    target_balance={'bull_first':int((resolved.target_dir==1).sum()),'bear_first':int((resolved.target_dir==-1).sum()),
                    'bull_share':float((resolved.target_dir==1).mean()) if len(resolved) else np.nan,
                    'resolved_total':int(len(resolved)),
                    'no_breakout':int((qp.resolution=='NO_BREAKOUT').sum()),'ambiguous':int((qp.resolution=='AMBIGUOUS').sum())}

    summaries=[]; y1=[]; y2=[]; aligns=[]; sides=[]
    for i,c in enumerate(CANDS):
        rec,a,b,al,sd=evaluate_candidate(d,pop,c,SEED+i*10)
        summaries.append(rec); y1.append(a); y2.append(b); aligns.append(al); sides.append(sd)
    sm=pd.DataFrame(summaries)
    h1y=pd.concat(y1,ignore_index=True); h2y=pd.concat(y2,ignore_index=True)
    align_df=pd.concat(aligns,ignore_index=True); side_df=pd.concat(sides,ignore_index=True)

    winners=sm[sm.pass_both].copy()
    if len(winners):
        order={c:i for i,c in enumerate(CANDS)}; winners['ord']=winners.candidate.map(order)
        winners=winners.sort_values(['accuracy','coverage_all','mean_signed24_atr','ord'],ascending=[False,False,False,True])
        winner=str(winners.iloc[0].candidate)
        verdict='COMPRESSION_DIRECTION_AND_RESOLUTION_SUPPORTED_DISCOVERY_ONLY'
    elif bool(sm.pass_h1.any()):
        winner='NONE'; verdict='FIRST_BREAK_DIRECTION_ONLY_NOT_PERSISTENT'
    elif bool(sm.eligible_h1.any()):
        winner='NONE'; verdict='DIRECTION_UNRESOLVED_BREAKOUT_RISK_ONLY'
    else:
        winner='NONE'; verdict='COMPRESSION_DIRECTION_UNDERPOWERED'

    # Touch timing diagnostics for correctly/incorrectly predicted exact resolutions.
    timing=[]
    for c in CANDS:
        q=d.loc[pop & d[c].ne(0) & d.target_dir.isin([-1,1])].copy()
        q['correct']=q[c].eq(q.target_dir)
        for flag,label in [(True,'CORRECT'),(False,'INCORRECT')]:
            s=q[q.correct.eq(flag)]
            timing.append({'candidate':c,'class':label,'n':int(len(s)),
                           'median_time_to_touch_min':float(pd.to_numeric(s.time_to_touch_min,errors='coerce').median()) if len(s) else np.nan})
    timing_df=pd.DataFrame(timing)

    sm.to_csv(out/'candidate_summary.csv',index=False)
    h1y.to_csv(out/'direction_year_transfer.csv',index=False)
    h2y.to_csv(out/'followthrough_year_transfer.csv',index=False)
    align_df.to_csv(out/'bias_alignment_diagnostic.csv',index=False)
    side_df.to_csv(out/'prediction_side_diagnostic.csv',index=False)
    timing_df.to_csv(out/'touch_timing_diagnostic.csv',index=False)
    qp[['available_time','close','atr14','bias','resolution','target_dir','touch_time','time_to_touch_min']+CANDS].to_csv(out/'compression_resolution_events.csv',index=False)

    report=[f'# {LAB}','',f'**Verdict: {verdict}**','',
            '> Human-facing compression direction/resolution diagnostic only. No trading edge or execution claim.','',
            f'- Valid Context H4 bars: **{len(allbars):,}**',f'- Frozen episodes: **{len(onset):,}**',
            f'- Pullback + G1 compression bars: **{int(pop.sum()):,}**',
            f'- Exact 8h resolved first passages: **{target_balance["resolved_total"]:,}**',
            f'- Exact target balance: BULL **{target_balance["bull_first"]}**, BEAR **{target_balance["bear_first"]}**, bull share **{target_balance["bull_share"]:.3f}**',
            f'- NO_BREAKOUT: **{target_balance["no_breakout"]}**; AMBIGUOUS: **{target_balance["ambiguous"]}**',
            f'- Direction winner: **{winner}**','',
            '## Candidate gates','',
            '| Candidate | Coverage | N resolved predicted | Accuracy | 95% CI | H1 | Signed24 ATR | 95% CI | H2 | Both |',
            '|---|---:|---:|---:|---:|---|---:|---:|---|---|']
    for _,r in sm.iterrows():
        report.append(f"| {r.candidate} | {r.coverage_all:.1%} | {int(r.n_resolved_predictions)} | {r.accuracy:.3f} | [{r.acc_ci_lo:.3f}, {r.acc_ci_hi:.3f}] | {'PASS' if r.pass_h1 else 'FAIL'} | {r.mean_signed24_atr:+.3f} | [{r.signed24_ci_lo:+.3f}, {r.signed24_ci_hi:+.3f}] | {'PASS' if r.pass_h2 else 'FAIL'} | {'PASS' if r.pass_both else 'FAIL'} |")
    report += ['', '## Interpretation constraints','',
               '- D1–D4, exact M1 ±1 ATR first-passage target, 8h horizon, 24h follow-through metric and gates were preregistered before outcomes.',
               '- `NO_BREAKOUT` and same-M1 `AMBIGUOUS` outcomes are never forced into a direction.',
               '- Reused history: any positive result remains DISCOVERY_ONLY pending fresh post-freeze replication.',
               '- This lab cannot authorize automated entries, BUY/SELL signals, sizing or prop-risk changes.']
    (out/'REPORT.md').write_text('\n'.join(report)+'\n')
    summary={'lab':LAB,'verdict':verdict,'winner':winner,'valid_context_bars':int(len(allbars)),'episode_onsets':int(len(onset)),
             'pullback_g1_bars':int(pop.sum()),'target_balance':target_balance,'resolution_counts':{str(k):int(v) for k,v in counts.items()},
             'candidates':sm.to_dict(orient='records')}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
