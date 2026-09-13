#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB='UNIVERSAL_CONTEXT_MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_LAB_006'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB004_PATH=ROOT/'labs'/'UNIVERSAL_CONTEXT_DIRECTIONAL_ASYMMETRY_AND_SEPARATE_BULL_BEAR_HEADS_LAB_004'/'run_lab.py'
LAB005_PATH=ROOT/'labs'/'UNIVERSAL_CONTEXT_FROZEN_HEADS_UNSEEN_MARKET_REPLICATION_LAB_005'/'run_lab.py'

RANK_LOOKBACK=252
RANK_MIN=100
CAL_LOOKBACK=504
CAL_MIN=30
BETA_A=12.0
BETA_B=12.0
EDGE_PSEUDO=24.0
P_MIN=0.55
EDGE_MIN=0.02
ARB_MARGIN=0.03
BOOT_N=5000
SEED=2026091306
EVAL_START=pd.Timestamp('2025-06-01 00:00:00')
EVAL_END=pd.Timestamp('2026-07-17 23:59:59')

HEADS={
    'EXPANSION':{
        'horizon_h':8,'kind':'return',
        'bull_score':'exp_bull_score','bear_score':'exp_bear_score',
        'bull_metric':'bull_signed8','bear_metric':'bear_signed8'},
    'RETRACEMENT':{
        'horizon_h':24,'kind':'return',
        'bull_score':'ret_bull_score','bear_score':'ret_bear_score',
        'bull_metric':'bull_signed24','bear_metric':'bear_signed24'},
    'COMPRESSION':{
        'horizon_h':24,'kind':'binary',
        'bull_score':'comp_bull_score','bear_score':'comp_bear_score',
        'bull_metric':'comp_bull_correct','bear_metric':'comp_bear_correct'},
}


def load_module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def rank_bin(q: float) -> int:
    if not np.isfinite(q): return -1
    if q < .50: return 0
    if q < .75: return 1
    if q < .90: return 2
    return 3


def calibrate_head(z: pd.DataFrame, state: str, score_col: str, metric_col: str,
                   horizon_h: int, kind: str, prefix: str) -> pd.DataFrame:
    out=z.copy()
    mask=out.regime.eq(state)
    sub=out.loc[mask,[score_col,metric_col,'available_time']].copy()
    n=len(sub)
    if n==0:
        for c in ['rank','bin','cal_n','p','edge','active']:
            out[f'{prefix}_{c}']=np.nan if c!='active' else False
        return out

    score=pd.to_numeric(sub[score_col],errors='coerce').to_numpy(float)
    metric=pd.to_numeric(sub[metric_col],errors='coerce').to_numpy(float)
    t=pd.to_datetime(sub.available_time).to_numpy(dtype='datetime64[ns]')
    rank=np.full(n,np.nan); bcode=np.full(n,-1,dtype=int)
    cal_n=np.zeros(n,dtype=int); phat=np.full(n,np.nan); edge=np.full(n,np.nan); active=np.zeros(n,dtype=bool)

    for j in range(n):
        if not np.isfinite(score[j]):
            continue
        a=max(0,j-RANK_LOOKBACK)
        hist=score[a:j]
        hist=hist[np.isfinite(hist)]
        if len(hist) < RANK_MIN:
            continue
        q=float(np.mean(hist<=score[j])); rank[j]=q; bcode[j]=rank_bin(q)

    lag=np.timedelta64(horizon_h,'h')
    for j in range(n):
        if bcode[j] < 2:
            continue
        a=max(0,j-CAL_LOOKBACK)
        jj=np.arange(a,j,dtype=int)
        if len(jj)==0: continue
        m=(bcode[jj]==bcode[j]) & np.isfinite(metric[jj]) & ((t[jj]+lag)<=t[j])
        vals=metric[jj][m]
        if len(vals) < CAL_MIN:
            continue
        nn=len(vals); cal_n[j]=nn
        if kind=='binary':
            wins=float(np.nansum(vals))
            p=(wins+BETA_A)/(nn+BETA_A+BETA_B)
            e=np.nan
            ok=(p>=P_MIN)
        else:
            wins=float(np.sum(vals>0))
            p=(wins+BETA_A)/(nn+BETA_A+BETA_B)
            mean=float(np.nanmean(vals))
            e=mean*nn/(nn+EDGE_PSEUDO)
            ok=(p>=P_MIN and e>=EDGE_MIN)
        phat[j]=p; edge[j]=e; active[j]=ok

    idx=sub.index
    out[f'{prefix}_rank']=pd.Series(rank,index=idx).reindex(out.index)
    out[f'{prefix}_bin']=pd.Series(bcode,index=idx).reindex(out.index)
    out[f'{prefix}_cal_n']=pd.Series(cal_n,index=idx).reindex(out.index).fillna(0).astype(int)
    out[f'{prefix}_p']=pd.Series(phat,index=idx).reindex(out.index)
    out[f'{prefix}_edge']=pd.Series(edge,index=idx).reindex(out.index)
    out[f'{prefix}_active']=pd.Series(active,index=idx).reindex(out.index).fillna(False).astype(bool)
    return out


def add_adaptive_layer(z: pd.DataFrame) -> pd.DataFrame:
    out=z.copy().sort_index()
    for state,s in HEADS.items():
        out=calibrate_head(out,state,s['bull_score'],s['bull_metric'],s['horizon_h'],s['kind'],f'{state.lower()}_bull')
        out=calibrate_head(out,state,s['bear_score'],s['bear_metric'],s['horizon_h'],s['kind'],f'{state.lower()}_bear')

    out['adaptive_state']=''
    out['adaptive_side']='WAIT'
    out['adaptive_p']=np.nan
    out['adaptive_perf']=np.nan
    out['adaptive_binary']=np.nan
    out['adaptive_conflict']=False
    out['baseline_side']='WAIT'
    out['baseline_perf']=np.nan
    out['baseline_binary']=np.nan

    for state,s in HEADS.items():
        sm=out.regime.eq(state)
        pfx=state.lower()
        ba=out[f'{pfx}_bull_active'].fillna(False)
        sa=out[f'{pfx}_bear_active'].fillna(False)
        bp=out[f'{pfx}_bull_p']; sp=out[f'{pfx}_bear_p']
        br=out[f'{pfx}_bull_rank']; sr=out[f'{pfx}_bear_rank']
        bmetric=pd.to_numeric(out[s['bull_metric']],errors='coerce')
        smetric=pd.to_numeric(out[s['bear_metric']],errors='coerce')

        both=sm & ba & sa
        bull_choose=sm & ((ba & ~sa) | (both & ((bp-sp)>=ARB_MARGIN)))
        bear_choose=sm & ((sa & ~ba) | (both & ((sp-bp)>=ARB_MARGIN)))
        conflict=both & ~(bull_choose|bear_choose)

        out.loc[sm,'adaptive_state']=state
        out.loc[conflict,'adaptive_conflict']=True
        out.loc[bull_choose,'adaptive_side']='BULL'; out.loc[bull_choose,'adaptive_p']=bp[bull_choose]
        out.loc[bear_choose,'adaptive_side']='BEAR'; out.loc[bear_choose,'adaptive_p']=sp[bear_choose]
        out.loc[bull_choose,'adaptive_perf']=bmetric[bull_choose]
        out.loc[bear_choose,'adaptive_perf']=smetric[bear_choose]
        if s['kind']=='binary':
            out.loc[bull_choose,'adaptive_binary']=bmetric[bull_choose]
            out.loc[bear_choose,'adaptive_binary']=smetric[bear_choose]
        else:
            out.loc[bull_choose,'adaptive_binary']=(bmetric[bull_choose]>0).astype(float)
            out.loc[bear_choose,'adaptive_binary']=(smetric[bear_choose]>0).astype(float)

        # Frozen rank-only baseline.
        be=sm & br.ge(.75); se=sm & sr.ge(.75); bb=be&se
        bpick=sm & ((be&~se) | (bb & (br>sr)))
        spick=sm & ((se&~be) | (bb & (sr>br)))
        out.loc[bpick,'baseline_side']='BULL'; out.loc[spick,'baseline_side']='BEAR'
        out.loc[bpick,'baseline_perf']=bmetric[bpick]; out.loc[spick,'baseline_perf']=smetric[spick]
        if s['kind']=='binary':
            out.loc[bpick,'baseline_binary']=bmetric[bpick]; out.loc[spick,'baseline_binary']=smetric[spick]
        else:
            out.loc[bpick,'baseline_binary']=(bmetric[bpick]>0).astype(float)
            out.loc[spick,'baseline_binary']=(smetric[spick]>0).astype(float)
    return out


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


def boot_diff(q: pd.DataFrame, a_col: str, b_col: str, seed: int) -> dict:
    q=q[['market','available_time',a_col,b_col]].copy(); q[a_col]=pd.to_numeric(q[a_col],errors='coerce'); q[b_col]=pd.to_numeric(q[b_col],errors='coerce')
    av=q[a_col].dropna(); bv=q[b_col].dropna(); obs=float(av.mean()-bv.mean()) if len(av) and len(bv) else np.nan
    q['cluster']=week_key(q); stats=[]
    for _,g in q.groupby('cluster'):
        a=g[a_col].dropna().to_numpy(float); b=g[b_col].dropna().to_numpy(float)
        stats.append([len(a),np.nansum(a),len(b),np.nansum(b)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    if m:
        for _ in range(BOOT_N):
            x=arr[rng.integers(0,m,size=m)].sum(axis=0)
            if x[0]>0 and x[2]>0: draws.append(x[1]/x[0]-x[3]/x[2])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)) if len(dr) else np.nan,'ci_hi':float(np.quantile(dr,.975)) if len(dr) else np.nan,'n_a':len(av),'n_b':len(bv),'clusters':m}


def state_market_table(ev: pd.DataFrame, state: str) -> pd.DataFrame:
    rows=[]
    q=ev[ev.regime.eq(state)]
    for m,g in q.groupby('market'):
        a=g.loc[g.adaptive_side.ne('WAIT'),'adaptive_perf'].dropna(); b=g.loc[g.baseline_side.ne('WAIT'),'baseline_perf'].dropna()
        rows.append({'market':m,'state':state,'adaptive_n':len(a),'adaptive_mean':float(a.mean()) if len(a) else np.nan,
                     'baseline_n':len(b),'baseline_mean':float(b.mean()) if len(b) else np.nan,
                     'state_bars':len(g),'adaptive_cov':float(g.adaptive_side.ne('WAIT').mean()) if len(g) else np.nan,
                     'conflict_rate':float(g.adaptive_conflict.mean()) if len(g) else np.nan})
    return pd.DataFrame(rows)


def calibration_stats(sel: pd.DataFrame) -> tuple[dict,pd.DataFrame]:
    q=sel[['adaptive_p','adaptive_binary']].dropna().copy()
    if q.empty: return {'n':0,'brier':np.nan,'ece':np.nan},pd.DataFrame()
    q['brier']=(q.adaptive_p-q.adaptive_binary)**2
    bins=[.55,.60,.70,1.0000001]; labels=['55-60','60-70','70-100']
    q['bucket']=pd.cut(q.adaptive_p,bins=bins,labels=labels,right=False,include_lowest=True)
    rows=[]; total_used=0; ece_num=0.0
    for label,g in q.groupby('bucket',observed=False):
        n=len(g); pred=float(g.adaptive_p.mean()) if n else np.nan; obs=float(g.adaptive_binary.mean()) if n else np.nan
        used=n>=30
        rows.append({'bucket':str(label),'n':n,'mean_p':pred,'observed':obs,'abs_gap':abs(pred-obs) if n else np.nan,'ece_used':used})
        if used:
            total_used+=n; ece_num+=n*abs(pred-obs)
    ece=ece_num/total_used if total_used else np.nan
    return {'n':len(q),'brier':float(q.brier.mean()),'ece':float(ece) if np.isfinite(ece) else np.nan,'ece_n':total_used},pd.DataFrame(rows)


def evaluate(markets: dict[str,pd.DataFrame], audits: list[dict], out: Path, lab4):
    lab2=lab4.load_lab002(); base=lab2.load_base(); frames=[]; meta=[]
    for market,h4 in markets.items():
        z=lab2.add_forward(lab2.add_engine(h4,base)); z=lab4.add_outcomes(lab4.add_heads(z)); z=add_adaptive_layer(z); z['market']=market
        ready=z[z.regime.isin(['EXPANSION','RETRACEMENT','COMPRESSION','TRANSITION'])].copy(); frames.append(ready)
        meta.append({'market':market,'h4_rows':len(h4),'ready_bars':len(ready),'first':str(h4.index.min()),'last':str(h4.index.max())})
    all_df=pd.concat(frames).sort_values(['market','available_time']); meta_df=pd.DataFrame(meta)
    if any(meta_df.ready_bars<500):
        verdict='DATA_BLOCKED'; out.mkdir(parents=True,exist_ok=True); meta_df.to_csv(out/'market_meta.csv',index=False)
        (out/'summary.json').write_text(json.dumps({'lab':LAB,'verdict':verdict},indent=2)); return

    ev=all_df[(all_df.available_time>=EVAL_START)&(all_df.available_time<=EVAL_END)].copy()
    tables={s:state_market_table(ev,s) for s in HEADS}
    pools={}; diffs={};
    for i,state in enumerate(HEADS):
        q=ev[ev.regime.eq(state)].copy(); sel=q[q.adaptive_side.ne('WAIT')].copy()
        pools[state]=boot_mean(sel,'adaptive_perf',SEED+10+i)
        diffs[state]=boot_diff(q,'adaptive_perf','baseline_perf',SEED+20+i)

    # H1 Expansion.
    ex=tables['EXPANSION']; ex_elig=ex[ex.adaptive_n>=20]
    h1=bool(len(ex_elig)>=5 and int((ex_elig.adaptive_mean>0).sum())>=5 and not (ex_elig.adaptive_mean<-.05).any() and
            pools['EXPANSION']['n']>=200 and np.isfinite(pools['EXPANSION']['ci_lo']) and pools['EXPANSION']['ci_lo']>0)
    # H2 Retracement.
    rt=tables['RETRACEMENT']; rt_elig=rt[rt.adaptive_n>=50]
    h2=bool(len(rt_elig)>=5 and int((rt_elig.adaptive_mean>0).sum())>=5 and not (rt_elig.adaptive_mean<-.05).any() and
            pools['RETRACEMENT']['n']>=400 and np.isfinite(pools['RETRACEMENT']['ci_lo']) and pools['RETRACEMENT']['ci_lo']>0)
    # H3 Compression.
    cp=tables['COMPRESSION']; cp_elig=cp[cp.adaptive_n>=15]
    cp_underpowered=bool(len(cp_elig)<5 or pools['COMPRESSION']['n']<150)
    if cp_underpowered:
        h3=False; h3_status='UNDERPOWERED'
    else:
        h3=bool(int((cp_elig.adaptive_mean>.5).sum())>=5 and not (cp_elig.adaptive_mean<.45).any() and np.isfinite(pools['COMPRESSION']['ci_lo']) and pools['COMPRESSION']['ci_lo']>.5)
        h3_status='PASS' if h3 else 'FAIL'

    selected=ev[ev.adaptive_side.ne('WAIT')].copy(); cal,cal_bins=calibration_stats(selected)
    h4=bool(cal['n']>0 and np.isfinite(cal['brier']) and cal['brier']<.245 and np.isfinite(cal['ece']) and cal['ece']<=.10)

    # H5 coverage and arbitration sanity.
    cov_pass={}
    bands={'EXPANSION':(.02,.45),'RETRACEMENT':(.05,.50),'COMPRESSION':(.01,.30)}
    h5=True
    for state,t in tables.items():
        lo,hi=bands[state]; within=((t.adaptive_cov>=lo)&(t.adaptive_cov<=hi))
        cov_pass[state]=int(within.sum())
        h5 &= int(within.sum())>=6 and bool((t.conflict_rate<=.15).all())
    h5=bool(h5)

    # H6 adaptation benefit.
    positive_states=sum(1 for s,d in diffs.items() if np.isfinite(d['observed']) and d['observed']>0)
    significant_states=sum(1 for s,d in diffs.items() if np.isfinite(d['ci_lo']) and d['ci_lo']>0)
    h6=bool(positive_states>=2 and significant_states>=1)

    strongly_negative=False
    for state,p in pools.items():
        if p['n']>=100 and np.isfinite(p['observed']) and p['observed']<-.05: strongly_negative=True

    if h1 and h2 and h4 and h5 and h6 and (h3 or cp_underpowered):
        verdict='MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_SUPPORTED'
    elif h4 and h5 and h6 and (h1 or h2) and not strongly_negative:
        verdict='MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_PARTIAL_SUPPORT'
    else:
        verdict='MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_NOT_SUPPORTED'

    # Diagnostics.
    side_rows=[]
    for (m,state),g in ev[ev.regime.isin(HEADS.keys())].groupby(['market','regime']):
        n=len(g); side_rows.append({'market':m,'state':state,'bars':n,'bull_n':int(g.adaptive_side.eq('BULL').sum()),'bear_n':int(g.adaptive_side.eq('BEAR').sum()),'wait_n':int(g.adaptive_side.eq('WAIT').sum())})
    side_df=pd.DataFrame(side_rows)
    yearly=[]; yy=selected.copy(); yy['year']=pd.to_datetime(yy.available_time).dt.year
    for (m,s,y),g in yy.groupby(['market','regime','year']):
        v=g.adaptive_perf.dropna(); yearly.append({'market':m,'state':s,'year':int(y),'n':len(v),'mean':float(v.mean()) if len(v) else np.nan})
    yearly_df=pd.DataFrame(yearly)

    summary={'lab':LAB,'verdict':verdict,'h1_expansion':h1,'h2_retracement':h2,'h3_compression_status':h3_status,'h3_compression_pass':h3,
             'h4_calibration':h4,'h5_coverage':h5,'h6_adaptation_benefit':h6,'coverage_markets_pass':cov_pass,
             'calibration':cal,'pools':pools,'adaptive_minus_rank_baseline':diffs,
             'evaluation_window':[str(EVAL_START),str(EVAL_END)]}

    out.mkdir(parents=True,exist_ok=True)
    meta_df.to_csv(out/'market_meta.csv',index=False); ev.to_csv(out/'evaluation_rows.csv',index=False)
    for s,t in tables.items(): t.to_csv(out/f'{s.lower()}_by_market.csv',index=False)
    cal_bins.to_csv(out/'calibration_bins.csv',index=False); side_df.to_csv(out/'side_mix.csv',index=False); yearly_df.to_csv(out/'yearly.csv',index=False)
    (out/'data_audit.json').write_text(json.dumps(audits,indent=2,default=str)); (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    def gate(x): return 'PASS' if x else 'FAIL'
    lines=[f'# {LAB}',f'**Verdict: {verdict}**','',
           '## Primary gates',
           f'- H1 adaptive EXPANSION: **{gate(h1)}** — pooled {pools["EXPANSION"]["observed"]:+.4f} ATR, CI [{pools["EXPANSION"]["ci_lo"]:+.4f}, {pools["EXPANSION"]["ci_hi"]:+.4f}], N={pools["EXPANSION"]["n"]}.',
           f'- H2 adaptive RETRACEMENT: **{gate(h2)}** — pooled {pools["RETRACEMENT"]["observed"]:+.4f} ATR, CI [{pools["RETRACEMENT"]["ci_lo"]:+.4f}, {pools["RETRACEMENT"]["ci_hi"]:+.4f}], N={pools["RETRACEMENT"]["n"]}.',
           f'- H3 adaptive COMPRESSION: **{h3_status}** — accuracy {100*pools["COMPRESSION"]["observed"]:.2f}%, CI [{100*pools["COMPRESSION"]["ci_lo"]:.2f}%, {100*pools["COMPRESSION"]["ci_hi"]:.2f}%], N={pools["COMPRESSION"]["n"]}.',
           f'- H4 confidence calibration: **{gate(h4)}** — Brier {cal["brier"]:.4f}, ECE {cal["ece"]:.4f}, N={cal["n"]}.',
           f'- H5 coverage / abstention sanity: **{gate(h5)}** — markets in-band {cov_pass}.',
           f'- H6 adaptive > rank-only baseline: **{gate(h6)}** — positive states {positive_states}/3, CI-positive states {significant_states}/3.','',
           '## Market data','',meta_df.to_markdown(index=False),'']
    for s in HEADS:
        lines += [f'## {s} by market','',tables[s].to_markdown(index=False,floatfmt='.4f'),'',
                  f'Adaptive minus rank-only: {diffs[s]}','']
    lines += ['## Calibration bins','',cal_bins.to_markdown(index=False,floatfmt='.4f'),'',
              '## Side mix','',side_df.to_markdown(index=False),'',
              '## Boundary','LAB006 is a causal adaptive-calibration design test on reused markets. It does not establish fresh unseen replication, executable entry/SL/TP profitability, or broker economics.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2,default=str))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau',required=True); ap.add_argument('--eur',required=True); ap.add_argument('--out',required=True); args=ap.parse_args()
    lab4=load_module(LAB004_PATH,'lab004'); lab5=load_module(LAB005_PATH,'lab005'); lab2=lab4.load_lab002(); base=lab2.load_base()
    xau=base.read_generic_m1(Path(args.xau),'XAUUSD'); eur=base.read_generic_m1(Path(args.eur),'EURUSD'); btc_h1,btc_meta=base.fetch_btc_h1()
    if btc_meta['missing_months']: raise RuntimeError(f'BTC missing months: {btc_meta["missing_months"][:5]}')
    markets={'XAUUSD':base.to_h4(xau),'BTCUSDT':base.btc_to_h4(btc_h1),'EURUSD':base.to_h4(eur)}
    audits=[{'market':'BTCUSDT','source':'Binance USD-M monthly 1h','meta':btc_meta}]
    for name,ticker in lab5.MARKETS.items():
        h1,meta=lab5.fetch_yahoo_h1(name,ticker); markets[name]=lab5.to_h4(h1); audits.append(meta)
    if any(len(v)<500 for v in markets.values()): raise RuntimeError({k:len(v) for k,v in markets.items()})
    evaluate(markets,audits,Path(args.out),lab4)

if __name__=='__main__':
    main()
