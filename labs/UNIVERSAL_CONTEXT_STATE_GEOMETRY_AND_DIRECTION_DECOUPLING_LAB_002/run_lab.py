#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB='UNIVERSAL_CONTEXT_STATE_GEOMETRY_AND_DIRECTION_DECOUPLING_LAB_002'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE_PATH=ROOT/'labs'/'UNIVERSAL_CONTEXT_NORMALIZED_CROSS_MARKET_STATE_ENGINE_LAB_001'/'run_lab.py'
STATES=['EXPANSION','RETRACEMENT','COMPRESSION']
ALL_STATES=STATES+['TRANSITION']
BOOT_N=5000
SEED=2026091202
COMMON_START=pd.Timestamp('2023-06-01')
COMMON_END=pd.Timestamp('2026-07-17 23:59:59')


def load_base():
    spec=importlib.util.spec_from_file_location('universal_context_lab001_base',BASE_PATH)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def add_engine(h4: pd.DataFrame, base) -> pd.DataFrame:
    d=base.add_features(h4)
    ready_cols=['ema200','atr14','rsi14','adx14','p_atr','p_adx','p_range','p_spread','p_dist20','p_er','p_slope','p_wick','p_rsi']
    ready=d[ready_cols].notna().all(axis=1)

    # Direction-agnostic geometry.
    d['ordered_up']=(d.ema20>d.ema50)&(d.ema50>d.ema200)
    d['ordered_dn']=(d.ema20<d.ema50)&(d.ema50<d.ema200)
    d['ordered_stack']=d.ordered_up|d.ordered_dn
    d['breakout_up']=d.close>d.prior_hi20
    d['breakout_dn']=d.close<d.prior_lo20
    d['breakout_dir']=np.select([d.breakout_up,d.breakout_dn],[1,-1],default=0).astype(int)

    s=pd.DataFrame(index=d.index,dtype=float)
    s['EXPANSION']=(25*d.breakout.astype(float)+20*d.p_atr+20*d.p_range+15*d.p_er+10*d.p_dist20+10*d.p_adx)
    s['RETRACEMENT']=(25*d['ordered_stack'].astype(float)+20*d.p_slope+20*(1-d.p_dist20)+15*d.p_adx+10*d.rsi_central+10*(~d.breakout).astype(float))
    s['COMPRESSION']=(25*(1-d.p_adx)+20*(1-d.p_spread)+20*(1-d.p_range)+15*(1-d.p_er)+10*(1-d.p_atr)+10*(~d['ordered_stack']).astype(float))
    s=s.where(ready,np.nan)
    sm=s.rolling(3,min_periods=3).mean()

    arr=sm.to_numpy(float); states=[]; gaps=[]; tops=[]; cols=list(sm.columns)
    for row in arr:
        if not np.isfinite(row).any():
            states.append(None); gaps.append(np.nan); tops.append(np.nan); continue
        vals=np.where(np.isfinite(row),row,-np.inf)
        order=np.argsort(vals); top_i=int(order[-1]); second_i=int(order[-2])
        top=float(vals[top_i]); gap=float(top-vals[second_i])
        states.append('TRANSITION' if (top<50 or gap<8) else cols[top_i])
        gaps.append(gap); tops.append(top)
    d['regime']=states; d['score_gap']=gaps; d['top_score']=tops
    for c in STATES:
        d[f'score_{c.lower()}']=sm[c]

    # Directional Pressure, explicitly independent of geometry state.
    ema_dir=np.sign(d.ema20-d.ema50).fillna(0)
    slope_dir=np.sign(d.slope50_atr).fillna(0)
    close_dir=np.sign(d.close-d.ema20).fillna(0)
    pressure=(30*d.trend_dir+20*ema_dir*d.p_spread+20*slope_dir*d.p_slope+
              15*close_dir*d.p_dist20+15*d.breakout_dir)
    d['pressure']=pressure.where(ready,np.nan).rolling(3,min_periods=3).mean().clip(-100,100)
    d['pressure_dir']=np.select([d.pressure>=20,d.pressure<=-20],[1,-1],default=0).astype(int)
    d['pressure_class']=np.select([d.pressure.abs()>=50,d.pressure.abs()>=20],['HIGH','MODERATE'],default='NEUTRAL')

    # REVERSAL is an event overlay, never a competitor state.
    event_score=(25*d.sweep.astype(float)+15*d.cross_ema20.astype(float)+20*d.p_wick+
                 20*d.rsi_turn.astype(float)+10*d.adx_falling.astype(float)+10*d.stack_exists.astype(float))
    d['reversal_score']=event_score.where(ready,np.nan)
    d['reversal_event']=(d.reversal_score>=50)&(d.sweep|d.cross_ema20|d.rsi_turn)
    d['available_time']=d.index+pd.Timedelta(hours=4)
    return d


def add_forward(d: pd.DataFrame) -> pd.DataFrame:
    z=d.copy().sort_index(); idx=pd.Series(z.index,index=z.index); atr=z.atr14.replace(0,np.nan)
    for n,hours in [(2,8),(3,12),(6,24)]:
        contiguous=pd.Series(True,index=z.index); highs=[]; lows=[]
        for i in range(1,n+1):
            contiguous &= idx.shift(-i).eq(idx+pd.Timedelta(hours=4*i))
            highs.append(z.high.shift(-i)); lows.append(z.low.shift(-i))
        fhi=pd.concat(highs,axis=1).max(axis=1).where(contiguous)
        flo=pd.concat(lows,axis=1).min(axis=1).where(contiguous)
        fclose=z.close.shift(-n).where(contiguous)
        ret=((fclose-z.close)/atr).where(contiguous)
        z[f'close_ret_{hours}h_atr']=ret
        z[f'range{hours}_atr']=((fhi-flo)/atr).where(contiguous)
        z[f'absclose{hours}_atr']=ret.abs()
    z['direction_signed8_atr']=(z.pressure_dir*z.close_ret_8h_atr).where(z.pressure_dir.ne(0))
    z['direction_signed24_atr']=(z.pressure_dir*z.close_ret_24h_atr).where(z.pressure_dir.ne(0))
    prior_dir=z.trend_dir.shift(1)
    z['reverse12_atr']=(-prior_dir*z.close_ret_12h_atr).where(z.reversal_event & prior_dir.ne(0))
    return z


def week_key(df: pd.DataFrame) -> pd.Series:
    return df.market.astype(str)+'|'+pd.to_datetime(df.available_time).dt.to_period('W-SUN').astype(str)


def boot_mean(q: pd.DataFrame, metric: str, seed: int) -> dict:
    q=q[['market','available_time',metric]].copy(); q[metric]=pd.to_numeric(q[metric],errors='coerce'); q=q.dropna(subset=[metric])
    obs=float(q[metric].mean()) if len(q) else np.nan
    if q.empty: return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n':0,'clusters':0}
    q['cluster']=week_key(q); stats=q.groupby('cluster')[metric].agg(['count','sum']).to_numpy(float)
    rng=np.random.default_rng(seed); draws=[]; m=len(stats)
    for _ in range(BOOT_N):
        x=stats[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0: draws.append(x[1]/x[0])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)),'ci_hi':float(np.quantile(dr,.975)),'n':len(q),'clusters':m}


def boot_state_diff(all_df: pd.DataFrame, state: str, metric: str, seed: int) -> dict:
    q=all_df[all_df.regime.isin(ALL_STATES)][['market','available_time','regime',metric]].copy()
    q[metric]=pd.to_numeric(q[metric],errors='coerce'); q=q.dropna(subset=[metric]); q['is_state']=q.regime.eq(state); q['cluster']=week_key(q)
    a=q[q.is_state][metric]; b=q[~q.is_state][metric]; obs=float(a.mean()-b.mean()) if len(a) and len(b) else np.nan
    stats=[]
    for _,g in q.groupby('cluster'):
        aa=g[g.is_state][metric].to_numpy(float); bb=g[~g.is_state][metric].to_numpy(float)
        stats.append([len(aa),np.nansum(aa),len(bb),np.nansum(bb)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        x=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0 and x[2]>0: draws.append(x[1]/x[0]-x[3]/x[2])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)) if len(dr) else np.nan,'ci_hi':float(np.quantile(dr,.975)) if len(dr) else np.nan,'n_state':len(a),'n_other':len(b),'clusters':m}


def boot_group_diff(q: pd.DataFrame, metric: str, group_col: str, a_name: str, b_name: str, seed: int) -> dict:
    q=q[['market','available_time',group_col,metric]].copy(); q[metric]=pd.to_numeric(q[metric],errors='coerce'); q=q.dropna(subset=[metric]); q=q[q[group_col].isin([a_name,b_name])].copy()
    a=q[q[group_col].eq(a_name)][metric]; b=q[q[group_col].eq(b_name)][metric]; obs=float(a.mean()-b.mean()) if len(a) and len(b) else np.nan
    q['cluster']=week_key(q); stats=[]
    for _,g in q.groupby('cluster'):
        aa=g[g[group_col].eq(a_name)][metric].to_numpy(float); bb=g[g[group_col].eq(b_name)][metric].to_numpy(float)
        stats.append([len(aa),np.nansum(aa),len(bb),np.nansum(bb)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        x=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0 and x[2]>0: draws.append(x[1]/x[0]-x[3]/x[2])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)) if len(dr) else np.nan,'ci_hi':float(np.quantile(dr,.975)) if len(dr) else np.nan,'n_a':len(a),'n_b':len(b),'clusters':m}


def state_effect(d: pd.DataFrame, market: str, state: str, metric: str) -> dict:
    q=d[d.regime.isin(ALL_STATES)][['regime',metric]].copy(); q[metric]=pd.to_numeric(q[metric],errors='coerce'); q=q.dropna(subset=[metric])
    a=q[q.regime.eq(state)][metric]; b=q[~q.regime.eq(state)][metric]
    return {'market':market,'state':state,'metric':metric,'n_state':len(a),'n_other':len(b),'mean_state':float(a.mean()) if len(a) else np.nan,'mean_other':float(b.mean()) if len(b) else np.nan,'effect':float(a.mean()-b.mean()) if len(a) and len(b) else np.nan}


def direction_market(d: pd.DataFrame, market: str) -> dict:
    q=d[d.pressure_dir.ne(0)].copy(); v=q.direction_signed8_atr.dropna()
    bull=q.loc[q.pressure_dir.eq(1),'direction_signed8_atr'].dropna(); bear=q.loc[q.pressure_dir.eq(-1),'direction_signed8_atr'].dropna()
    return {'market':market,'n':len(v),'mean_signed8':float(v.mean()) if len(v) else np.nan,'bull_n':len(bull),'bull_mean':float(bull.mean()) if len(bull) else np.nan,'bear_n':len(bear),'bear_mean':float(bear.mean()) if len(bear) else np.nan}


def magnitude_market(d: pd.DataFrame, market: str) -> dict:
    q=d[d.pressure_class.isin(['HIGH','MODERATE'])].copy(); a=q.loc[q.pressure_class.eq('HIGH'),'direction_signed8_atr'].dropna(); b=q.loc[q.pressure_class.eq('MODERATE'),'direction_signed8_atr'].dropna()
    return {'market':market,'high_n':len(a),'moderate_n':len(b),'high_mean':float(a.mean()) if len(a) else np.nan,'moderate_mean':float(b.mean()) if len(b) else np.nan,'effect':float(a.mean()-b.mean()) if len(a) and len(b) else np.nan}


def occupancy(d: pd.DataFrame, market: str) -> pd.DataFrame:
    q=d[d.regime.isin(ALL_STATES)].copy(); n=len(q)
    return pd.DataFrame([{'market':market,'state':st,'n':int(q.regime.eq(st).sum()),'occupancy':float(q.regime.eq(st).mean()) if n else np.nan} for st in ALL_STATES])


def evaluate(markets: dict[str,pd.DataFrame], out: Path, base):
    frames=[]; occs=[]; meta=[]
    for market,h4 in markets.items():
        z=add_forward(add_engine(h4,base)); z['market']=market; ready=z[z.regime.isin(ALL_STATES)].copy()
        frames.append(ready); occs.append(occupancy(z,market)); meta.append({'market':market,'h4_rows':len(h4),'ready_bars':len(ready),'first':str(h4.index.min()),'last':str(h4.index.max())})
    all_df=pd.concat(frames).sort_values(['market','available_time']); occ=pd.concat(occs,ignore_index=True); meta_df=pd.DataFrame(meta)

    semantic=[]; direction_rows=[]; magnitude_rows=[]
    for market,z in all_df.groupby('market'):
        for st,metric in [('EXPANSION','range8_atr'),('COMPRESSION','range8_atr'),('RETRACEMENT','range8_atr'),('RETRACEMENT','absclose8_atr')]: semantic.append(state_effect(z,market,st,metric))
        direction_rows.append(direction_market(z,market)); magnitude_rows.append(magnitude_market(z,market))
    semantic=pd.DataFrame(semantic); direction_df=pd.DataFrame(direction_rows); magnitude_df=pd.DataFrame(magnitude_rows)

    pool_exp=boot_state_diff(all_df,'EXPANSION','range8_atr',SEED+1); pool_comp=boot_state_diff(all_df,'COMPRESSION','range8_atr',SEED+2)
    resolved=all_df[all_df.pressure_dir.ne(0)].copy(); pool_dir=boot_mean(resolved,'direction_signed8_atr',SEED+3)
    pool_mag=boot_group_diff(resolved,'direction_signed8_atr','pressure_class','HIGH','MODERATE',SEED+4); pool_mag24=boot_group_diff(resolved,'direction_signed24_atr','pressure_class','HIGH','MODERATE',SEED+5)

    ex=semantic[(semantic.state=='EXPANSION')&(semantic.metric=='range8_atr')]; cp=semantic[(semantic.state=='COMPRESSION')&(semantic.metric=='range8_atr')]
    h1=bool(len(ex)==3 and (ex.n_state>=100).all() and (ex.effect>0).all() and np.isfinite(pool_exp['ci_lo']) and pool_exp['ci_lo']>0)
    h2=bool(len(cp)==3 and (cp.n_state>=100).all() and (cp.effect<0).all() and np.isfinite(pool_comp['ci_hi']) and pool_comp['ci_hi']<0)
    h3=bool(len(direction_df)==3 and (direction_df.n>=100).all() and (direction_df.mean_signed8>0).all() and np.isfinite(pool_dir['ci_lo']) and pool_dir['ci_lo']>0)
    h4=bool(len(magnitude_df)==3 and (magnitude_df.high_n>=100).all() and (magnitude_df.moderate_n>=100).all() and int((magnitude_df.effect>0).sum())>=2 and np.isfinite(pool_mag['ci_lo']) and pool_mag['ci_lo']>0)

    state_dir=[]; h5_pass_states=0; h5_remaining_nonnegative=True
    for i,st in enumerate(STATES):
        q=resolved[resolved.regime.eq(st)].copy(); b=boot_mean(q,'direction_signed8_atr',SEED+20+i); eligible=b['n']>=200; ci_pass=bool(eligible and np.isfinite(b['ci_lo']) and b['ci_lo']>0)
        if ci_pass: h5_pass_states+=1
        if eligible and not ci_pass and (not np.isfinite(b['observed']) or b['observed']<0): h5_remaining_nonnegative=False
        state_dir.append({'state':st,'eligible':bool(eligible),'pass_ci':ci_pass,**b})
    state_dir_df=pd.DataFrame(state_dir); h5=bool(h5_pass_states>=2 and h5_remaining_nonnegative and int(state_dir_df.eligible.sum())==3)

    h6_parts=[]
    for market,g in occ.groupby('market'):
        core=g[g.state.isin(STATES)].set_index('state').occupancy; tr=float(g.loc[g.state.eq('TRANSITION'),'occupancy'].iloc[0]); ok=(int((core>=.05).sum())>=2 and float(core.max())<=.80 and tr<=.50)
        h6_parts.append({'market':market,'pass':bool(ok),'core_states_ge5pct':int((core>=.05).sum()),'max_core_occ':float(core.max()),'transition_occ':tr})
    h6=bool(len(h6_parts)==3 and all(x['pass'] for x in h6_parts))

    rev=all_df[all_df.reversal_event & all_df.reverse12_atr.notna()].copy(); rev_pool=boot_mean(rev,'reverse12_atr',SEED+30) if len(rev) else {'observed':np.nan,'ci_lo':np.nan,'ci_hi':np.nan,'n':0,'clusters':0}
    rev_market=rev.groupby('market')['reverse12_atr'].agg(['count','mean']).reset_index() if len(rev) else pd.DataFrame(columns=['market','count','mean'])

    pdx=resolved[['market','available_time','pressure','direction_signed8_atr','direction_signed24_atr','regime']].dropna(subset=['pressure']).copy(); pdx['abs_pressure']=pdx.pressure.abs()
    try: pdx['pressure_decile']=pd.qcut(pdx.abs_pressure,10,labels=False,duplicates='drop')+1
    except Exception: pdx['pressure_decile']=np.nan
    pressure_deciles=pdx.groupby('pressure_decile')[['direction_signed8_atr','direction_signed24_atr']].agg(['count','mean']).reset_index()

    cw=all_df[(all_df.available_time>=COMMON_START)&(all_df.available_time<=COMMON_END)].copy(); common=[]
    for market,z in cw.groupby('market'):
        common.append(state_effect(z,market,'EXPANSION','range8_atr')); common.append(state_effect(z,market,'COMPRESSION','range8_atr')); dm=direction_market(z,market); dm['state']='DIRECTION'; dm['metric']='signed8'; common.append(dm)
    common_df=pd.DataFrame(common)

    gates=[h1,h2,h3,h4,h5,h6]
    if all(gates): verdict='GEOMETRY_DIRECTION_DECOUPLING_SUPPORTED'
    elif h3 and h6 and sum(gates)>=4: verdict='GEOMETRY_DIRECTION_DECOUPLING_PARTIAL_SUPPORT'
    else: verdict='GEOMETRY_DIRECTION_DECOUPLING_NOT_SUPPORTED'

    summary={'lab':LAB,'verdict':verdict,'h1_expansion_geometry_pass':h1,'h2_compression_geometry_pass':h2,'h3_direction_cross_market_pass':h3,'h4_pressure_magnitude_pass':h4,'h5_decoupling_cross_state_pass':h5,'h6_geometry_breadth_pass':h6,'primary_pass_count':int(sum(gates)),'pool_expansion_range':pool_exp,'pool_compression_range':pool_comp,'pool_direction_signed8':pool_dir,'pool_high_minus_moderate_signed8':pool_mag,'pool_high_minus_moderate_signed24_diagnostic':pool_mag24,'h5_by_state':state_dir,'h6_by_market':h6_parts,'reversal_overlay':rev_pool,'common_window_start':str(COMMON_START),'common_window_end':str(COMMON_END)}

    out.mkdir(parents=True,exist_ok=True); meta_df.to_csv(out/'market_meta.csv',index=False); occ.to_csv(out/'occupancy.csv',index=False); semantic.to_csv(out/'geometry_semantics.csv',index=False); direction_df.to_csv(out/'direction_by_market.csv',index=False); magnitude_df.to_csv(out/'pressure_magnitude_by_market.csv',index=False); state_dir_df.to_csv(out/'direction_by_geometry_state.csv',index=False); rev_market.to_csv(out/'reversal_overlay_by_market.csv',index=False); pressure_deciles.to_csv(out/'pressure_deciles.csv',index=False); common_df.to_csv(out/'common_window_diagnostic.csv',index=False); (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    gate=lambda ok:'PASS' if ok else 'FAIL'
    lines=[f'# {LAB}',f'**Verdict: {verdict}**','', '## Primary gates', f'- H1 EXPANSION geometry: **{gate(h1)}** — pooled range effect {pool_exp["observed"]:+.3f} ATR, CI [{pool_exp["ci_lo"]:+.3f}, {pool_exp["ci_hi"]:+.3f}].', f'- H2 COMPRESSION geometry: **{gate(h2)}** — pooled range effect {pool_comp["observed"]:+.3f} ATR, CI [{pool_comp["ci_lo"]:+.3f}, {pool_comp["ci_hi"]:+.3f}].', f'- H3 Directional Pressure cross-market: **{gate(h3)}** — pooled signed8 {pool_dir["observed"]:+.3f} ATR, CI [{pool_dir["ci_lo"]:+.3f}, {pool_dir["ci_hi"]:+.3f}].', f'- H4 HIGH vs MODERATE pressure: **{gate(h4)}** — pooled delta {pool_mag["observed"]:+.3f} ATR, CI [{pool_mag["ci_lo"]:+.3f}, {pool_mag["ci_hi"]:+.3f}].', f'- H5 Direction across geometry states: **{gate(h5)}**.', f'- H6 Geometry breadth: **{gate(h6)}**.','', '## Market data / ready bars','',meta_df.to_markdown(index=False),'', '## Geometry occupancy','',occ.pivot(index='market',columns='state',values='occupancy').to_markdown(floatfmt='.3f'),'', '## Geometry semantic effects','',semantic.to_markdown(index=False,floatfmt='.4f'),'', '## Direction by market','',direction_df.to_markdown(index=False,floatfmt='.4f'),'', '## Pressure magnitude by market','',magnitude_df.to_markdown(index=False,floatfmt='.4f'),'', '## H5 — direction by geometry state','',state_dir_df.to_markdown(index=False,floatfmt='.4f'),'', '## REVERSAL overlay diagnostic', f'- pooled reverse12: {rev_pool["observed"]:+.3f} ATR, CI [{rev_pool["ci_lo"]:+.3f}, {rev_pool["ci_hi"]:+.3f}], N={rev_pool["n"]}.','', rev_market.to_markdown(index=False,floatfmt='.4f') if len(rev_market) else 'No eligible reversal events.','', '## Pressure deciles diagnostic','',pressure_deciles.to_markdown(index=False,floatfmt='.4f'),'', '## Common-window diagnostic','',common_df.to_markdown(index=False,floatfmt='.4f'),'', '## Boundary','State geometry and direction use the frozen prereg formulas. No asset-specific thresholds or outcome-driven retuning are permitted in LAB002. This LAB does not establish entry, SL/TP, profit probability, or execution economics.']
    (out/'REPORT.md').write_text('\n'.join(lines)); print(json.dumps(summary,indent=2,default=str))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau',required=True); ap.add_argument('--eur',required=True); ap.add_argument('--out',required=True); args=ap.parse_args(); out=Path(args.out); base=load_base()
    xau=base.read_generic_m1(Path(args.xau),'XAUUSD'); eur=base.read_generic_m1(Path(args.eur),'EURUSD'); btc_h1,btc_meta=base.fetch_btc_h1()
    if btc_meta['missing_months']:
        out.mkdir(parents=True,exist_ok=True); (out/'btc_missing.json').write_text(json.dumps(btc_meta,indent=2)); raise RuntimeError(f'BTC missing months: {btc_meta["missing_months"][:5]}')
    markets={'XAUUSD':base.to_h4(xau),'BTCUSDT':base.btc_to_h4(btc_h1),'EURUSD':base.to_h4(eur)}
    if any(len(v)<500 for v in markets.values()): raise RuntimeError({k:len(v) for k,v in markets.items()})
    evaluate(markets,out,base)


if __name__=='__main__': main()
