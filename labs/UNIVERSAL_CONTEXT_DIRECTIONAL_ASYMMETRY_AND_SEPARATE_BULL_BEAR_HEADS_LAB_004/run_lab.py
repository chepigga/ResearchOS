#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='UNIVERSAL_CONTEXT_DIRECTIONAL_ASYMMETRY_AND_SEPARATE_BULL_BEAR_HEADS_LAB_004'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB002_PATH=ROOT/'labs'/'UNIVERSAL_CONTEXT_STATE_GEOMETRY_AND_DIRECTION_DECOUPLING_LAB_002'/'run_lab.py'
BOOT_N=5000
SEED=2026091304
COMMON_START=pd.Timestamp('2023-06-01')
COMMON_END=pd.Timestamp('2026-07-17 23:59:59')


def load_lab002():
    spec=importlib.util.spec_from_file_location('lab002',LAB002_PATH)
    mod=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(mod)
    return mod


def add_heads(d: pd.DataFrame) -> pd.DataFrame:
    z=d.copy().sort_index()
    rng=(z.high-z.low).replace(0,np.nan)
    body_hi=pd.concat([z.open,z.close],axis=1).max(axis=1)
    body_lo=pd.concat([z.open,z.close],axis=1).min(axis=1)
    z['clv']=((z.close-z.low)/rng).clip(0,1)
    z['upper_wick_frac']=(z.high-body_hi)/rng
    z['lower_wick_frac']=(body_lo-z.low)/rng
    z['prior24_hi']=z.high.rolling(24,min_periods=24).max().shift(1)
    z['prior24_lo']=z.low.rolling(24,min_periods=24).min().shift(1)
    den=(z.prior24_hi-z.prior24_lo).replace(0,np.nan)
    z['range_pos24']=(2*(z.close-z.prior24_lo)/den-1).clip(-1,1)
    z['bull_pressure']=(z.pressure.clip(lower=0)/100).clip(0,1)
    z['bear_pressure']=((-z.pressure).clip(lower=0)/100).clip(0,1)
    z['bull_range_pos']=((z.range_pos24+1)/2).clip(0,1)
    z['bear_range_pos']=((1-z.range_pos24)/2).clip(0,1)

    # EXPANSION separate heads.
    z['exp_bull_score']=(30*z.bull_pressure + 20*z.breakout_up.astype(float) +
                         15*z.trend_dir.eq(1).astype(float) + 15*z.clv + 10*z.p_er + 10*z.p_adx)
    z['exp_bear_score']=(25*z.bear_pressure + 25*z.breakout_dn.astype(float) +
                         20*z.trend_dir.eq(-1).astype(float) + 10*(1-z.clv) + 10*z.p_er + 10*z.p_adx)
    z['exp_bull_signal']=(z.regime.eq('EXPANSION') & (z.exp_bull_score>=55))
    z['exp_bear_signal']=(z.regime.eq('EXPANSION') & (z.exp_bear_score>=65))

    # RETRACEMENT separate continuation heads.
    bull_slope=((z.slope50_atr>0).astype(float)*z.p_slope)
    bear_slope=((z.slope50_atr<0).astype(float)*z.p_slope)
    z['ret_bull_score']=(25*z.ordered_up.astype(float)+20*z.close.ge(z.ema50).astype(float)+
                         20*z.lower_wick_frac.gt(z.upper_wick_frac).astype(float)+15*bull_slope+
                         10*z.p_adx+10*(1-z.p_dist20))
    z['ret_bear_score']=(25*z.ordered_dn.astype(float)+20*z.close.le(z.ema50).astype(float)+
                         20*z.upper_wick_frac.gt(z.lower_wick_frac).astype(float)+15*bear_slope+
                         10*z.p_adx+10*(1-z.p_dist20))
    rb=(z.regime.eq('RETRACEMENT') & (z.ret_bull_score>=60))
    rs=(z.regime.eq('RETRACEMENT') & (z.ret_bear_score>=65))
    z['ret_conflict']=rb&rs
    z['ret_bull_signal']=rb&~z.ret_conflict
    z['ret_bear_signal']=rs&~z.ret_conflict

    # COMPRESSION separate first-passage heads.
    z['comp_bull_score']=(30*z.bull_pressure+20*z.bull_range_pos+
                          20*z.ema20.gt(z.ema50).astype(float)*z.p_spread+
                          15*z.slope50_atr.gt(0).astype(float)*z.p_slope+
                          15*z.close.gt(z.ema20).astype(float))
    z['comp_bear_score']=(30*z.bear_pressure+25*z.bear_range_pos+
                          20*z.ema20.lt(z.ema50).astype(float)*z.p_spread+
                          15*z.slope50_atr.lt(0).astype(float)*z.p_slope+
                          10*z.close.lt(z.ema20).astype(float))
    cb=(z.regime.eq('COMPRESSION') & (z.comp_bull_score>=55))
    cs=(z.regime.eq('COMPRESSION') & (z.comp_bear_score>=60))
    z['comp_conflict']=cb&cs
    z['comp_bull_signal']=cb&~z.comp_conflict
    z['comp_bear_signal']=cs&~z.comp_conflict
    return z


def add_outcomes(d: pd.DataFrame) -> pd.DataFrame:
    z=d.copy().sort_index(); idx=pd.Series(z.index,index=z.index); atr=z.atr14.replace(0,np.nan)
    z['bull_signed8']=z.close_ret_8h_atr
    z['bear_signed8']=-z.close_ret_8h_atr
    z['bull_signed24']=z.close_ret_24h_atr
    z['bear_signed24']=-z.close_ret_24h_atr
    up_t=z.close+atr; dn_t=z.close-atr
    fp=np.zeros(len(z),dtype=int); active=np.ones(len(z),dtype=bool)
    for step in range(1,7):
        contiguous=idx.shift(-step).eq(idx+pd.Timedelta(hours=4*step)).to_numpy()
        hi=z.high.shift(-step).to_numpy(float); lo=z.low.shift(-step).to_numpy(float)
        up=(hi>=up_t.to_numpy(float))&contiguous&active
        dn=(lo<=dn_t.to_numpy(float))&contiguous&active
        both=up&dn; only_up=up&~dn; only_dn=dn&~up
        fp[both]=2; fp[only_up]=1; fp[only_dn]=-1
        active &= ~(up|dn)
    z['fp_dir']=fp; z['fp_resolved']=z.fp_dir.isin([1,-1])
    z['comp_bull_correct']=np.where(z.fp_resolved,(z.fp_dir==1).astype(float),np.nan)
    z['comp_bear_correct']=np.where(z.fp_resolved,(z.fp_dir==-1).astype(float),np.nan)
    return z


def week_key(df):
    return df.market.astype(str)+'|'+pd.to_datetime(df.available_time).dt.to_period('W-SUN').astype(str)


def boot_mean(q,metric,seed):
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


def boot_side_diff(bull,bear,bull_metric,bear_metric,seed):
    a=bull[['market','available_time',bull_metric]].rename(columns={bull_metric:'v'}).copy(); a['side']='BULL'
    b=bear[['market','available_time',bear_metric]].rename(columns={bear_metric:'v'}).copy(); b['side']='BEAR'
    q=pd.concat([a,b],ignore_index=True).dropna(subset=['v']); q['cluster']=week_key(q)
    av=q.loc[q.side.eq('BULL'),'v']; bv=q.loc[q.side.eq('BEAR'),'v']; obs=float(av.mean()-bv.mean()) if len(av) and len(bv) else np.nan
    stats=[]
    for _,g in q.groupby('cluster'):
        aa=g.loc[g.side.eq('BULL'),'v'].to_numpy(float); bb=g.loc[g.side.eq('BEAR'),'v'].to_numpy(float)
        stats.append([len(aa),np.nansum(aa),len(bb),np.nansum(bb)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        x=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0 and x[2]>0: draws.append(x[1]/x[0]-x[3]/x[2])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)) if len(dr) else np.nan,'ci_hi':float(np.quantile(dr,.975)) if len(dr) else np.nan,'n_bull':len(av),'n_bear':len(bv),'clusters':m}


def market_rows(df,metric):
    rows=[]
    for m,g in df.groupby('market'):
        v=pd.to_numeric(g[metric],errors='coerce').dropna(); rows.append({'market':m,'n':len(v),'mean':float(v.mean()) if len(v) else np.nan})
    return pd.DataFrame(rows)


def accuracy_rows(df,metric):
    rows=[]
    for m,g in df.groupby('market'):
        v=pd.to_numeric(g[metric],errors='coerce').dropna(); rows.append({'market':m,'n':len(v),'accuracy':float(v.mean()) if len(v) else np.nan})
    return pd.DataFrame(rows)


def coverage(all_df):
    rows=[]
    for m,z in all_df.groupby('market'):
        ex=z[z.regime.eq('EXPANSION')]; rt=z[z.regime.eq('RETRACEMENT')]; cp=z[z.regime.eq('COMPRESSION')]
        rows.append({'market':m,
          'exp_n':len(ex),'exp_bull_cov':float(ex.exp_bull_signal.mean()) if len(ex) else np.nan,'exp_bear_cov':float(ex.exp_bear_signal.mean()) if len(ex) else np.nan,
          'ret_n':len(rt),'ret_bull_cov':float(rt.ret_bull_signal.mean()) if len(rt) else np.nan,'ret_bear_cov':float(rt.ret_bear_signal.mean()) if len(rt) else np.nan,'ret_conflict':float(rt.ret_conflict.mean()) if len(rt) else np.nan,
          'comp_n':len(cp),'comp_bull_cov':float(cp.comp_bull_signal.mean()) if len(cp) else np.nan,'comp_bear_cov':float(cp.comp_bear_signal.mean()) if len(cp) else np.nan,'comp_conflict':float(cp.comp_conflict.mean()) if len(cp) else np.nan})
    return pd.DataFrame(rows)


def evaluate(markets,out,lab2):
    frames=[]; meta=[]; base=lab2.load_base()
    for market,h4 in markets.items():
        z=lab2.add_forward(lab2.add_engine(h4,base)); z=add_outcomes(add_heads(z)); z['market']=market
        ready=z[z.regime.isin(['EXPANSION','RETRACEMENT','COMPRESSION','TRANSITION'])].copy(); frames.append(ready)
        meta.append({'market':market,'h4_rows':len(h4),'ready_bars':len(ready),'first':str(h4.index.min()),'last':str(h4.index.max())})
    all_df=pd.concat(frames).sort_values(['market','available_time']); meta_df=pd.DataFrame(meta)

    eb=all_df[all_df.exp_bull_signal].copy(); es=all_df[all_df.exp_bear_signal].copy()
    rb=all_df[all_df.ret_bull_signal].copy(); rs=all_df[all_df.ret_bear_signal].copy()
    cb=all_df[all_df.comp_bull_signal & all_df.fp_resolved].copy(); cs=all_df[all_df.comp_bear_signal & all_df.fp_resolved].copy()

    eb_r=market_rows(eb,'bull_signed8'); es_r=market_rows(es,'bear_signed8'); rb_r=market_rows(rb,'bull_signed24'); rs_r=market_rows(rs,'bear_signed24')
    cb_r=accuracy_rows(cb,'comp_bull_correct'); cs_r=accuracy_rows(cs,'comp_bear_correct')
    p_eb=boot_mean(eb,'bull_signed8',SEED+1); p_es=boot_mean(es,'bear_signed8',SEED+2); p_asym=boot_side_diff(eb,es,'bull_signed8','bear_signed8',SEED+3)
    p_rb=boot_mean(rb,'bull_signed24',SEED+4); p_rs=boot_mean(rs,'bear_signed24',SEED+5)
    p_cb=boot_mean(cb,'comp_bull_correct',SEED+6); p_cs=boot_mean(cs,'comp_bear_correct',SEED+7)

    h1=bool(len(eb_r)==3 and (eb_r.n>=100).all() and (eb_r['mean']>0).all() and np.isfinite(p_eb['ci_lo']) and p_eb['ci_lo']>0)
    h2=bool(len(es_r)==3 and (es_r.n>=100).all() and int((es_r['mean']>0).sum())>=2 and not (es_r['mean']<-.03).any() and np.isfinite(p_es['ci_lo']) and p_es['ci_lo']>0)
    h3=bool(p_asym['n_bull']>=300 and p_asym['n_bear']>=300 and np.isfinite(p_asym['ci_lo']) and p_asym['ci_lo']>0)
    h4=bool(len(rb_r)==3 and (rb_r.n>=100).all() and int((rb_r['mean']>0).sum())>=2 and not (rb_r.loc[rb_r.n>=100,'mean']<-.05).any() and np.isfinite(p_rb['ci_lo']) and p_rb['ci_lo']>0)
    h5=bool(len(rs_r)==3 and (rs_r.n>=100).all() and int((rs_r['mean']>0).sum())>=2 and not (rs_r.loc[rs_r.n>=100,'mean']<-.05).any() and np.isfinite(p_rs['ci_lo']) and p_rs['ci_lo']>0)
    h6=bool(len(cb_r)==3 and (cb_r.n>=100).all() and (cb_r.accuracy>.5).all() and np.isfinite(p_cb['ci_lo']) and p_cb['ci_lo']>.5)
    h7=bool(len(cs_r)==3 and (cs_r.n>=100).all() and int((cs_r.accuracy>.5).sum())>=2 and not (cs_r.accuracy<.47).any() and np.isfinite(p_cs['ci_lo']) and p_cs['ci_lo']>.5)

    cov=coverage(all_df); h8=True
    for _,r in cov.iterrows():
        h8 &= (.05<=r.exp_bull_cov<=.70 and .03<=r.exp_bear_cov<=.60 and .05<=r.ret_bull_cov<=.70 and .05<=r.ret_bear_cov<=.70 and .05<=r.comp_bull_cov<=.70 and .05<=r.comp_bear_cov<=.70 and r.ret_conflict<=.10 and r.comp_conflict<=.10)
    h8=bool(h8)

    if h1 and h2 and h4 and h5 and h6 and h7 and h8:
        verdict='SEPARATE_BULL_BEAR_HEADS_SUPPORTED'
    elif h1 and (h4 or h6) and h8 and sum([not h2,not h5,not h7])>=2:
        verdict='DIRECTIONAL_ASYMMETRY_CONFIRMED_BULL_HEADS_SUPPORTED_BEAR_NOT_SUPPORTED'
    elif h8 and sum([h1,h2,h3,h4,h5,h6,h7])>=4:
        verdict='DIRECTIONAL_ASYMMETRY_PARTIAL_SUPPORT'
    else:
        verdict='SEPARATE_BULL_BEAR_HEADS_NOT_SUPPORTED'

    # Diagnostics.
    asym_market=[]
    for m in sorted(all_df.market.unique()):
        a=eb.loc[eb.market.eq(m),'bull_signed8'].dropna(); b=es.loc[es.market.eq(m),'bear_signed8'].dropna()
        asym_market.append({'market':m,'bull_n':len(a),'bull_mean':float(a.mean()) if len(a) else np.nan,'bear_n':len(b),'bear_mean':float(b.mean()) if len(b) else np.nan,'bull_minus_bear':float(a.mean()-b.mean()) if len(a) and len(b) else np.nan})
    asym_market=pd.DataFrame(asym_market)

    cw=all_df[(all_df.available_time>=COMMON_START)&(all_df.available_time<=COMMON_END)].copy(); cw_rows=[]
    for m,g in cw.groupby('market'):
        def mm(mask,metric):
            v=g.loc[mask,metric].dropna(); return (len(v),float(v.mean()) if len(v) else np.nan)
        ebn,ebm=mm(g.exp_bull_signal,'bull_signed8'); esn,esm=mm(g.exp_bear_signal,'bear_signed8'); rbn,rbm=mm(g.ret_bull_signal,'bull_signed24'); rsn,rsm=mm(g.ret_bear_signal,'bear_signed24')
        cbb=g[g.comp_bull_signal & g.fp_resolved].comp_bull_correct.dropna(); css=g[g.comp_bear_signal & g.fp_resolved].comp_bear_correct.dropna()
        cw_rows.append({'market':m,'exp_bull_n':ebn,'exp_bull_mean':ebm,'exp_bear_n':esn,'exp_bear_mean':esm,'ret_bull_n':rbn,'ret_bull_mean':rbm,'ret_bear_n':rsn,'ret_bear_mean':rsm,'comp_bull_n':len(cbb),'comp_bull_acc':float(cbb.mean()) if len(cbb) else np.nan,'comp_bear_n':len(css),'comp_bear_acc':float(css.mean()) if len(css) else np.nan})
    cw_df=pd.DataFrame(cw_rows)

    yearly=[]; yy=all_df.copy(); yy['year']=pd.to_datetime(yy.available_time).dt.year
    for (m,y),g in yy.groupby(['market','year']):
        for name,mask,metric in [('EXP_BULL',g.exp_bull_signal,'bull_signed8'),('EXP_BEAR',g.exp_bear_signal,'bear_signed8'),('RET_BULL',g.ret_bull_signal,'bull_signed24'),('RET_BEAR',g.ret_bear_signal,'bear_signed24')]:
            v=g.loc[mask,metric].dropna(); yearly.append({'market':m,'year':int(y),'head':name,'n':len(v),'mean':float(v.mean()) if len(v) else np.nan})
        for name,mask,metric in [('COMP_BULL',g.comp_bull_signal & g.fp_resolved,'comp_bull_correct'),('COMP_BEAR',g.comp_bear_signal & g.fp_resolved,'comp_bear_correct')]:
            v=g.loc[mask,metric].dropna(); yearly.append({'market':m,'year':int(y),'head':name,'n':len(v),'mean':float(v.mean()) if len(v) else np.nan})
    yearly=pd.DataFrame(yearly)

    summary={'lab':LAB,'verdict':verdict,'h1_expansion_bull':h1,'h2_expansion_bear':h2,'h3_expansion_asymmetry':h3,'h4_retracement_bull':h4,'h5_retracement_bear':h5,'h6_compression_bull':h6,'h7_compression_bear':h7,'h8_coverage':h8,
             'pool_exp_bull':p_eb,'pool_exp_bear':p_es,'pool_exp_asymmetry':p_asym,'pool_ret_bull':p_rb,'pool_ret_bear':p_rs,'pool_comp_bull_accuracy':p_cb,'pool_comp_bear_accuracy':p_cs}
    out.mkdir(parents=True,exist_ok=True)
    meta_df.to_csv(out/'market_meta.csv',index=False); eb_r.to_csv(out/'expansion_bull.csv',index=False); es_r.to_csv(out/'expansion_bear.csv',index=False)
    rb_r.to_csv(out/'retracement_bull.csv',index=False); rs_r.to_csv(out/'retracement_bear.csv',index=False); cb_r.to_csv(out/'compression_bull.csv',index=False); cs_r.to_csv(out/'compression_bear.csv',index=False)
    cov.to_csv(out/'coverage.csv',index=False); asym_market.to_csv(out/'expansion_asymmetry_by_market.csv',index=False); cw_df.to_csv(out/'common_window.csv',index=False); yearly.to_csv(out/'yearly.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    def gate(x): return 'PASS' if x else 'FAIL'
    lines=[f'# {LAB}',f'**Verdict: {verdict}**','', '## Primary gates',
      f'- H1 EXPANSION_BULL: **{gate(h1)}** — pooled {p_eb["observed"]:+.4f} ATR, CI [{p_eb["ci_lo"]:+.4f}, {p_eb["ci_hi"]:+.4f}], N={p_eb["n"]}.',
      f'- H2 EXPANSION_BEAR: **{gate(h2)}** — pooled {p_es["observed"]:+.4f} ATR, CI [{p_es["ci_lo"]:+.4f}, {p_es["ci_hi"]:+.4f}], N={p_es["n"]}.',
      f'- H3 EXPANSION asymmetry BULL-BEAR: **{gate(h3)}** — {p_asym["observed"]:+.4f} ATR, CI [{p_asym["ci_lo"]:+.4f}, {p_asym["ci_hi"]:+.4f}].',
      f'- H4 RETRACEMENT_BULL: **{gate(h4)}** — pooled {p_rb["observed"]:+.4f} ATR, CI [{p_rb["ci_lo"]:+.4f}, {p_rb["ci_hi"]:+.4f}], N={p_rb["n"]}.',
      f'- H5 RETRACEMENT_BEAR: **{gate(h5)}** — pooled {p_rs["observed"]:+.4f} ATR, CI [{p_rs["ci_lo"]:+.4f}, {p_rs["ci_hi"]:+.4f}], N={p_rs["n"]}.',
      f'- H6 COMPRESSION_BULL: **{gate(h6)}** — pooled accuracy {100*p_cb["observed"]:.2f}%, CI [{100*p_cb["ci_lo"]:.2f}%, {100*p_cb["ci_hi"]:.2f}%], N={p_cb["n"]}.',
      f'- H7 COMPRESSION_BEAR: **{gate(h7)}** — pooled accuracy {100*p_cs["observed"]:.2f}%, CI [{100*p_cs["ci_lo"]:.2f}%, {100*p_cs["ci_hi"]:.2f}%], N={p_cs["n"]}.',
      f'- H8 coverage/conflict sanity: **{gate(h8)}**.','', '## Market data','',meta_df.to_markdown(index=False),'',
      '## Expansion BULL','',eb_r.to_markdown(index=False,floatfmt='.4f'),'', '## Expansion BEAR','',es_r.to_markdown(index=False,floatfmt='.4f'),'',
      '## Expansion asymmetry by market','',asym_market.to_markdown(index=False,floatfmt='.4f'),'', '## Retracement BULL','',rb_r.to_markdown(index=False,floatfmt='.4f'),'',
      '## Retracement BEAR','',rs_r.to_markdown(index=False,floatfmt='.4f'),'', '## Compression BULL','',cb_r.to_markdown(index=False,floatfmt='.4f'),'',
      '## Compression BEAR','',cs_r.to_markdown(index=False,floatfmt='.4f'),'', '## Coverage / conflicts','',cov.to_markdown(index=False,floatfmt='.4f'),'',
      '## Common-window diagnostic','',cw_df.to_markdown(index=False,floatfmt='.4f'),'',
      '## Boundary','LAB002 geometry is unchanged. LAB004 is discovery/confirmation on reused XAU/BTC/EUR markets. Any accepted side-specific head requires unseen-market replication before production confidence or profit-probability claims.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2,default=str))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau',required=True); ap.add_argument('--eur',required=True); ap.add_argument('--out',required=True); args=ap.parse_args()
    lab2=load_lab002(); base=lab2.load_base()
    xau=base.read_generic_m1(Path(args.xau),'XAUUSD'); eur=base.read_generic_m1(Path(args.eur),'EURUSD'); btc_h1,btc_meta=base.fetch_btc_h1()
    if btc_meta['missing_months']: raise RuntimeError(f'BTC missing months: {btc_meta["missing_months"][:5]}')
    markets={'XAUUSD':base.to_h4(xau),'BTCUSDT':base.btc_to_h4(btc_h1),'EURUSD':base.to_h4(eur)}
    if any(len(v)<500 for v in markets.values()): raise RuntimeError({k:len(v) for k,v in markets.items()})
    evaluate(markets,Path(args.out),lab2)

if __name__=='__main__': main()
