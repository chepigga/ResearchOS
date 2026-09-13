#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB='UNIVERSAL_CONTEXT_STATE_SPECIFIC_PREDICTIVE_HEADS_LAB_003'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB002_PATH=ROOT/'labs'/'UNIVERSAL_CONTEXT_STATE_GEOMETRY_AND_DIRECTION_DECOUPLING_LAB_002'/'run_lab.py'
BOOT_N=5000
SEED=2026091303
COMMON_START=pd.Timestamp('2023-06-01')
COMMON_END=pd.Timestamp('2026-07-17 23:59:59')


def load_lab002():
    spec=importlib.util.spec_from_file_location('universal_context_lab002_base',LAB002_PATH)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def add_heads(d: pd.DataFrame) -> pd.DataFrame:
    z=d.copy().sort_index()
    rng=(z.high-z.low).replace(0,np.nan)
    body_hi=pd.concat([z.open,z.close],axis=1).max(axis=1)
    body_lo=pd.concat([z.open,z.close],axis=1).min(axis=1)
    z['upper_wick_frac']=(z.high-body_hi)/rng
    z['lower_wick_frac']=(body_lo-z.low)/rng
    z['bar_dir']=np.sign(z.close-z.open).fillna(0).astype(int)

    z['prior24_hi']=z.high.rolling(24,min_periods=24).max().shift(1)
    z['prior24_lo']=z.low.rolling(24,min_periods=24).min().shift(1)
    den=(z.prior24_hi-z.prior24_lo).replace(0,np.nan)
    z['range_pos24']=(2*(z.close-z.prior24_lo)/den-1).clip(-1,1)
    z['ema20_side']=np.sign(z.close-z.ema20).fillna(0).astype(int)
    z['ema50_side']=np.sign(z.close-z.ema50).fillna(0).astype(int)

    # A. Expansion head.
    z['exp_dir']=z.pressure_dir.astype(int)
    exp_align_break=((z.breakout_dir==z.exp_dir)&z.breakout_dir.ne(0)).astype(float)
    exp_align_trend=((z.trend_dir==z.exp_dir)&z.trend_dir.ne(0)).astype(float)
    z['exp_score']=(30*(z.pressure.abs()/100).clip(0,1)+25*exp_align_break+20*exp_align_trend+15*z.p_er+10*z.p_adx)
    z['exp_class']=np.select([z.exp_score>=60,z.exp_score>=40],['HIGH','MODERATE'],default='LOW')

    # B. Retracement head.
    z['parent_dir']=z.trend_dir.astype(int)
    parent=z.parent_dir
    parent_wick=np.where(parent>0,z.lower_wick_frac,np.where(parent<0,z.upper_wick_frac,np.nan))
    opp_wick=np.where(parent>0,z.upper_wick_frac,np.where(parent<0,z.lower_wick_frac,np.nan))
    z['parent_wick']=pd.Series(parent_wick,index=z.index,dtype=float)
    z['opp_wick']=pd.Series(opp_wick,index=z.index,dtype=float)
    reclaim20=(parent*(z.close-z.ema20)>=0).astype(float)
    intact50=(parent*(z.close-z.ema50)>=0).astype(float)
    reject_parent=(z.parent_wick>z.opp_wick).astype(float)
    reject_opp=(z.opp_wick>z.parent_wick).astype(float)

    prev_rel=z.parent_dir.shift(1)*(z.close.shift(1)-z.ema20.shift(1))
    curr_rel=parent*(z.close-z.ema20)
    z['cross_against_parent']=((prev_rel>=0)&(curr_rel<0)&parent.ne(0))
    z['against_parent_sweep']=(((parent>0)&(z.high>z.prior_hi20)&(z.close<z.prior_hi20))|
                               ((parent<0)&(z.low<z.prior_lo20)&(z.close>z.prior_lo20)))

    z['ret_cont_score']=(25*reclaim20+20*intact50+20*reject_parent+15*z.p_slope+10*z.p_adx+10*(1-z.p_dist20))
    z['ret_rev_score']=(30*(parent*(z.close-z.ema50)<0).astype(float)+25*z.cross_against_parent.astype(float)+
                        20*z.against_parent_sweep.astype(float)+15*reject_opp+10*z.rsi_turn.astype(float))
    z['ret_class']=np.select([(z.ret_cont_score>=60)&(z.ret_rev_score<50),
                              (z.ret_rev_score>=50)&(z.ret_cont_score<60)],
                             ['CONTINUATION','REVERSAL'],default='ABSTAIN')

    # C. Compression head.
    ema_dir=np.sign(z.ema20-z.ema50).fillna(0)
    slope_dir=np.sign(z.slope50_atr).fillna(0)
    comp_raw=35*(z.pressure/100)+25*z.range_pos24+20*ema_dir*z.p_spread+20*slope_dir*z.p_slope
    z['comp_score']=comp_raw.rolling(3,min_periods=3).mean().clip(-100,100)
    z['comp_dir']=np.select([z.comp_score>=20,z.comp_score<=-20],[1,-1],default=0).astype(int)
    z['comp_class']=np.select([z.comp_score.abs()>=50,z.comp_score.abs()>=20],['HIGH','MODERATE'],default='NEUTRAL')
    return z


def add_head_outcomes(d: pd.DataFrame) -> pd.DataFrame:
    z=d.copy().sort_index(); idx=pd.Series(z.index,index=z.index); atr=z.atr14.replace(0,np.nan)
    z['exp_signed8']=(z.exp_dir*z.close_ret_8h_atr).where(z.exp_dir.ne(0))
    z['parent_signed24']=(z.parent_dir*z.close_ret_24h_atr).where(z.parent_dir.ne(0))
    z['reverse_parent_signed24']=(-z.parent_dir*z.close_ret_24h_atr).where(z.parent_dir.ne(0))

    up_t=z.close+atr; dn_t=z.close-atr
    fp=np.zeros(len(z),dtype=int)       # +1 up, -1 down, 2 ambiguous, 0 none
    active=np.ones(len(z),dtype=bool)
    for step in range(1,7):
        contiguous=idx.shift(-step).eq(idx+pd.Timedelta(hours=4*step)).to_numpy()
        hi=z.high.shift(-step).to_numpy(float); lo=z.low.shift(-step).to_numpy(float)
        up=(hi>=up_t.to_numpy(float)) & contiguous & active
        dn=(lo<=dn_t.to_numpy(float)) & contiguous & active
        both=up&dn
        only_up=up&~dn
        only_dn=dn&~up
        fp[both]=2; fp[only_up]=1; fp[only_dn]=-1
        active &= ~(up|dn)
    z['fp_dir']=fp
    z['comp_fp_resolved']=z.fp_dir.isin([1,-1])
    z['comp_correct']=np.where(z.comp_fp_resolved & z.comp_dir.ne(0),(z.fp_dir==z.comp_dir).astype(float),np.nan)
    z['comp_signed24']=(z.comp_dir*z.close_ret_24h_atr).where(z.comp_dir.ne(0))
    return z


def week_key(df: pd.DataFrame) -> pd.Series:
    return df.market.astype(str)+'|'+pd.to_datetime(df.available_time).dt.to_period('W-SUN').astype(str)


def boot_mean(q: pd.DataFrame, metric: str, seed: int) -> dict:
    q=q[['market','available_time',metric]].copy(); q[metric]=pd.to_numeric(q[metric],errors='coerce'); q=q.dropna(subset=[metric])
    obs=float(q[metric].mean()) if len(q) else np.nan
    if q.empty: return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n':0,'clusters':0}
    q['cluster']=week_key(q); st=q.groupby('cluster')[metric].agg(['count','sum']).to_numpy(float)
    rng=np.random.default_rng(seed); draws=[]; m=len(st)
    for _ in range(BOOT_N):
        x=st[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0: draws.append(x[1]/x[0])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)),'ci_hi':float(np.quantile(dr,.975)),'n':len(q),'clusters':m}


def boot_group_diff(q: pd.DataFrame, metric: str, group_col: str, a_name: str, b_name: str, seed: int) -> dict:
    q=q[['market','available_time',group_col,metric]].copy(); q[metric]=pd.to_numeric(q[metric],errors='coerce'); q=q.dropna(subset=[metric]); q=q[q[group_col].isin([a_name,b_name])].copy()
    a=q[q[group_col].eq(a_name)][metric]; b=q[q[group_col].eq(b_name)][metric]
    obs=float(a.mean()-b.mean()) if len(a) and len(b) else np.nan
    if q.empty: return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n_a':len(a),'n_b':len(b),'clusters':0}
    q['cluster']=week_key(q); stats=[]
    for _,g in q.groupby('cluster'):
        aa=g[g[group_col].eq(a_name)][metric].to_numpy(float); bb=g[g[group_col].eq(b_name)][metric].to_numpy(float)
        stats.append([len(aa),np.nansum(aa),len(bb),np.nansum(bb)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        x=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0 and x[2]>0: draws.append(x[1]/x[0]-x[3]/x[2])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)) if len(dr) else np.nan,
            'ci_hi':float(np.quantile(dr,.975)) if len(dr) else np.nan,'n_a':len(a),'n_b':len(b),'clusters':m}


def market_mean(df: pd.DataFrame, market: str, metric: str) -> dict:
    v=pd.to_numeric(df[metric],errors='coerce').dropna()
    return {'market':market,'n':len(v),'mean':float(v.mean()) if len(v) else np.nan}


def market_diff(df: pd.DataFrame, market: str, metric: str, group_col: str, a_name: str, b_name: str) -> dict:
    a=pd.to_numeric(df.loc[df[group_col].eq(a_name),metric],errors='coerce').dropna()
    b=pd.to_numeric(df.loc[df[group_col].eq(b_name),metric],errors='coerce').dropna()
    return {'market':market,'n_a':len(a),'n_b':len(b),'mean_a':float(a.mean()) if len(a) else np.nan,
            'mean_b':float(b.mean()) if len(b) else np.nan,'effect':float(a.mean()-b.mean()) if len(a) and len(b) else np.nan}


def coverage_rows(all_df: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for market,z in all_df.groupby('market'):
        ex=z[(z.regime=='EXPANSION')&z.exp_dir.ne(0)]; rt=z[(z.regime=='RETRACEMENT')&z.parent_dir.ne(0)]; cp=z[z.regime=='COMPRESSION']
        rows.append({'market':market,
                     'exp_eligible':len(ex),'exp_high':int(ex.exp_class.eq('HIGH').sum()),'exp_high_cov':float(ex.exp_class.eq('HIGH').mean()) if len(ex) else np.nan,
                     'ret_eligible':len(rt),'ret_nonabstain':int(~rt.ret_class.eq('ABSTAIN').sum()) if False else int(rt.ret_class.ne('ABSTAIN').sum()),
                     'ret_nonabstain_cov':float(rt.ret_class.ne('ABSTAIN').mean()) if len(rt) else np.nan,
                     'comp_eligible':len(cp),'comp_resolved_head':int(cp.comp_dir.ne(0).sum()),'comp_resolved_cov':float(cp.comp_dir.ne(0).mean()) if len(cp) else np.nan})
    return pd.DataFrame(rows)


def evaluate(markets: dict[str,pd.DataFrame], out: Path, lab2):
    frames=[]; meta=[]
    for market,h4 in markets.items():
        z=lab2.add_forward(lab2.add_engine(h4,lab2.load_base()))
        z=add_head_outcomes(add_heads(z)); z['market']=market
        ready=z[z.regime.isin(['EXPANSION','RETRACEMENT','COMPRESSION','TRANSITION'])].copy()
        frames.append(ready)
        meta.append({'market':market,'h4_rows':len(h4),'ready_bars':len(ready),'first':str(h4.index.min()),'last':str(h4.index.max())})
    all_df=pd.concat(frames).sort_values(['market','available_time']); meta_df=pd.DataFrame(meta)

    # H1 expansion high.
    exp_hi=all_df[(all_df.regime=='EXPANSION')&all_df.exp_dir.ne(0)&all_df.exp_class.eq('HIGH')].copy()
    exp_rows=pd.DataFrame([market_mean(g,m,'exp_signed8') for m,g in exp_hi.groupby('market')])
    pool_exp=boot_mean(exp_hi,'exp_signed8',SEED+1)
    h1=bool(len(exp_rows)==3 and (exp_rows.n>=100).all() and (exp_rows['mean']>0).all() and np.isfinite(pool_exp['ci_lo']) and pool_exp['ci_lo']>0)

    # H2 expansion HIGH vs non-HIGH resolved.
    exp_all=all_df[(all_df.regime=='EXPANSION')&all_df.exp_dir.ne(0)].copy(); exp_all['exp_tier']=np.where(exp_all.exp_class.eq('HIGH'),'HIGH','NON_HIGH')
    exp_diff=pd.DataFrame([market_diff(g,m,'exp_signed8','exp_tier','HIGH','NON_HIGH') for m,g in exp_all.groupby('market')])
    pool_exp_diff=boot_group_diff(exp_all,'exp_signed8','exp_tier','HIGH','NON_HIGH',SEED+2)
    h2=bool(len(exp_diff)==3 and int((exp_diff.effect>0).sum())>=2 and np.isfinite(pool_exp_diff['ci_lo']) and pool_exp_diff['ci_lo']>0)

    # H3 retracement continuation.
    ret_cont=all_df[(all_df.regime=='RETRACEMENT')&all_df.ret_class.eq('CONTINUATION')].copy()
    ret_cont_rows=pd.DataFrame([market_mean(g,m,'parent_signed24') for m,g in ret_cont.groupby('market')])
    pool_ret_cont=boot_mean(ret_cont,'parent_signed24',SEED+3)
    eligible_neg=ret_cont_rows[ret_cont_rows.n>=100]
    h3=bool(len(ret_cont_rows)==3 and int((ret_cont_rows['mean']>0).sum())>=2 and
            not ((eligible_neg['mean']<-.05).any()) and np.isfinite(pool_ret_cont['ci_lo']) and pool_ret_cont['ci_lo']>0)

    # H4 retracement reversal.
    ret_rev=all_df[(all_df.regime=='RETRACEMENT')&all_df.ret_class.eq('REVERSAL')].copy()
    ret_rev_rows=pd.DataFrame([market_mean(g,m,'reverse_parent_signed24') for m,g in ret_rev.groupby('market')])
    pool_ret_rev=boot_mean(ret_rev,'reverse_parent_signed24',SEED+4)
    h4=bool(len(ret_rev_rows)>=2 and int(((ret_rev_rows.n>=50)&(ret_rev_rows['mean']>0)).sum())>=2 and
            pool_ret_rev['n']>=200 and np.isfinite(pool_ret_rev['ci_lo']) and pool_ret_rev['ci_lo']>0)

    # H5 compression first-passage direction.
    comp=all_df[(all_df.regime=='COMPRESSION')&all_df.comp_dir.ne(0)&all_df.comp_fp_resolved].copy()
    comp_rows=[]
    for m,g in comp.groupby('market'):
        v=g.comp_correct.dropna(); comp_rows.append({'market':m,'n':len(v),'accuracy':float(v.mean()) if len(v) else np.nan})
    comp_rows=pd.DataFrame(comp_rows); pool_comp=boot_mean(comp,'comp_correct',SEED+5)
    h5=bool(len(comp_rows)==3 and (comp_rows.n>=100).all() and (comp_rows.accuracy>.5).all() and np.isfinite(pool_comp['ci_lo']) and pool_comp['ci_lo']>.5)

    # H6 coverage.
    cov=coverage_rows(all_df)
    h6=bool(len(cov)==3 and ((cov.exp_high_cov>=.10)&(cov.exp_high_cov<=.80)).all() and
            ((cov.ret_nonabstain_cov>=.10)&(cov.ret_nonabstain_cov<=.80)).all() and
            ((cov.comp_resolved_cov>=.20)&(cov.comp_resolved_cov<=.90)).all())

    passes=[h1,h2,h3,h4,h5,h6]
    if h1 and h3 and h5 and h6 and sum(passes)>=5: verdict='STATE_SPECIFIC_HEADS_SUPPORTED'
    elif h6 and sum([h1,h3,h5])>=2 and sum(passes)>=4: verdict='STATE_SPECIFIC_HEADS_PARTIAL_SUPPORT'
    else: verdict='STATE_SPECIFIC_HEADS_NOT_SUPPORTED'

    # Secondary diagnostics.
    asym=[]
    for m,z in all_df.groupby('market'):
        for head,sub,dircol,metric in [
            ('EXPANSION',z[(z.regime=='EXPANSION')&z.exp_dir.ne(0)],'exp_dir','exp_signed8'),
            ('COMPRESSION',z[(z.regime=='COMPRESSION')&z.comp_dir.ne(0)&z.comp_fp_resolved],'comp_dir','comp_correct')]:
            for direction,name in [(1,'BULL'),(-1,'BEAR')]:
                v=pd.to_numeric(sub.loc[sub[dircol].eq(direction),metric],errors='coerce').dropna()
                asym.append({'market':m,'head':head,'side':name,'n':len(v),'mean':float(v.mean()) if len(v) else np.nan})
    asym=pd.DataFrame(asym)

    comp_tier=comp.copy(); comp_tier=comp_tier[comp_tier.comp_class.isin(['HIGH','MODERATE'])]
    comp_tier_diff=boot_group_diff(comp_tier,'comp_correct','comp_class','HIGH','MODERATE',SEED+6)

    yy=all_df.copy(); yy['year']=pd.to_datetime(yy.available_time).dt.year
    yearly=[]
    for (m,y),g in yy.groupby(['market','year']):
        e=g[(g.regime=='EXPANSION')&g.exp_class.eq('HIGH')&g.exp_dir.ne(0)].exp_signed8.dropna()
        r=g[(g.regime=='RETRACEMENT')&g.ret_class.eq('CONTINUATION')].parent_signed24.dropna()
        c=g[(g.regime=='COMPRESSION')&g.comp_dir.ne(0)&g.comp_fp_resolved].comp_correct.dropna()
        yearly.append({'market':m,'year':int(y),'exp_high_n':len(e),'exp_high_mean':float(e.mean()) if len(e) else np.nan,
                       'ret_cont_n':len(r),'ret_cont_mean':float(r.mean()) if len(r) else np.nan,
                       'comp_n':len(c),'comp_accuracy':float(c.mean()) if len(c) else np.nan})
    yearly=pd.DataFrame(yearly)

    cw=all_df[(all_df.available_time>=COMMON_START)&(all_df.available_time<=COMMON_END)].copy()
    common=[]
    for m,g in cw.groupby('market'):
        e=g[(g.regime=='EXPANSION')&g.exp_class.eq('HIGH')&g.exp_dir.ne(0)].exp_signed8.dropna()
        r=g[(g.regime=='RETRACEMENT')&g.ret_class.eq('CONTINUATION')].parent_signed24.dropna()
        c=g[(g.regime=='COMPRESSION')&g.comp_dir.ne(0)&g.comp_fp_resolved].comp_correct.dropna()
        common.append({'market':m,'exp_high_n':len(e),'exp_high_mean':float(e.mean()) if len(e) else np.nan,
                       'ret_cont_n':len(r),'ret_cont_mean':float(r.mean()) if len(r) else np.nan,
                       'comp_n':len(c),'comp_accuracy':float(c.mean()) if len(c) else np.nan})
    common=pd.DataFrame(common)

    summary={'lab':LAB,'verdict':verdict,'h1_expansion_high_pass':h1,'h2_expansion_increment_pass':h2,
             'h3_retracement_continuation_pass':h3,'h4_retracement_reversal_pass':h4,
             'h5_compression_direction_pass':h5,'h6_coverage_pass':h6,'primary_pass_count':int(sum(passes)),
             'pool_expansion_high':pool_exp,'pool_expansion_high_minus_nonhigh':pool_exp_diff,
             'pool_retracement_continuation':pool_ret_cont,'pool_retracement_reversal':pool_ret_rev,
             'pool_compression_accuracy':pool_comp,'compression_high_minus_moderate_accuracy':comp_tier_diff}

    out.mkdir(parents=True,exist_ok=True)
    meta_df.to_csv(out/'market_meta.csv',index=False); exp_rows.to_csv(out/'expansion_high.csv',index=False)
    exp_diff.to_csv(out/'expansion_high_vs_nonhigh.csv',index=False); ret_cont_rows.to_csv(out/'retracement_continuation.csv',index=False)
    ret_rev_rows.to_csv(out/'retracement_reversal.csv',index=False); comp_rows.to_csv(out/'compression_first_passage.csv',index=False)
    cov.to_csv(out/'coverage.csv',index=False); asym.to_csv(out/'side_asymmetry.csv',index=False)
    yearly.to_csv(out/'yearly.csv',index=False); common.to_csv(out/'common_window.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    lines=[f'# {LAB}',f'**Verdict: {verdict}**','', '## Primary gates',
           f'- H1 EXPANSION HIGH continuation: **{"PASS" if h1 else "FAIL"}** — pooled {pool_exp["observed"]:+.4f} ATR, CI [{pool_exp["ci_lo"]:+.4f}, {pool_exp["ci_hi"]:+.4f}], N={pool_exp["n"]}.',
           f'- H2 EXPANSION HIGH vs non-HIGH: **{"PASS" if h2 else "FAIL"}** — delta {pool_exp_diff["observed"]:+.4f} ATR, CI [{pool_exp_diff["ci_lo"]:+.4f}, {pool_exp_diff["ci_hi"]:+.4f}].',
           f'- H3 RETRACEMENT continuation: **{"PASS" if h3 else "FAIL"}** — pooled {pool_ret_cont["observed"]:+.4f} ATR, CI [{pool_ret_cont["ci_lo"]:+.4f}, {pool_ret_cont["ci_hi"]:+.4f}], N={pool_ret_cont["n"]}.',
           f'- H4 RETRACEMENT reversal: **{"PASS" if h4 else "FAIL"}** — pooled {pool_ret_rev["observed"]:+.4f} ATR, CI [{pool_ret_rev["ci_lo"]:+.4f}, {pool_ret_rev["ci_hi"]:+.4f}], N={pool_ret_rev["n"]}.',
           f'- H5 COMPRESSION breakout direction: **{"PASS" if h5 else "FAIL"}** — pooled accuracy {100*pool_comp["observed"]:.2f}%, CI [{100*pool_comp["ci_lo"]:.2f}%, {100*pool_comp["ci_hi"]:.2f}%], N={pool_comp["n"]}.',
           f'- H6 coverage sanity: **{"PASS" if h6 else "FAIL"}**.','',
           '## Market data','',meta_df.to_markdown(index=False),'',
           '## EXPANSION HIGH','',exp_rows.to_markdown(index=False,floatfmt='.4f'),'','## EXPANSION HIGH vs non-HIGH','',exp_diff.to_markdown(index=False,floatfmt='.4f'),'',
           '## RETRACEMENT continuation','',ret_cont_rows.to_markdown(index=False,floatfmt='.4f'),'','## RETRACEMENT reversal','',ret_rev_rows.to_markdown(index=False,floatfmt='.4f'),'',
           '## COMPRESSION first-passage','',comp_rows.to_markdown(index=False,floatfmt='.4f'),'','## Coverage','',cov.to_markdown(index=False,floatfmt='.4f'),'',
           '## Side asymmetry diagnostic','',asym.to_markdown(index=False,floatfmt='.4f'),'',
           f'Compression HIGH minus MODERATE accuracy: {comp_tier_diff["observed"]:+.4f}, CI [{comp_tier_diff["ci_lo"]:+.4f}, {comp_tier_diff["ci_hi"]:+.4f}].','',
           '## Common-window diagnostic','',common.to_markdown(index=False,floatfmt='.4f'),'','## Boundary',
           'Frozen LAB002 geometry was not changed. LAB003 tests predictive heads only; it does not establish executable entry/SL/TP, profit probability, or broker economics.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2,default=str))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau',required=True); ap.add_argument('--eur',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); lab2=load_lab002(); base=lab2.load_base()
    xau=base.read_generic_m1(Path(args.xau),'XAUUSD'); eur=base.read_generic_m1(Path(args.eur),'EURUSD')
    btc_h1,btc_meta=base.fetch_btc_h1()
    if btc_meta['missing_months']:
        raise RuntimeError(f'BTC missing months: {btc_meta["missing_months"][:5]}')
    markets={'XAUUSD':base.to_h4(xau),'BTCUSDT':base.btc_to_h4(btc_h1),'EURUSD':base.to_h4(eur)}
    if any(len(v)<500 for v in markets.values()): raise RuntimeError({k:len(v) for k,v in markets.items()})
    evaluate(markets,Path(args.out),lab2)

if __name__=='__main__':
    main()
