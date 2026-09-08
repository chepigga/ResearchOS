#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

LAB='BTC_SHORT_HIGH_RESPONSE_ACCEPT25_BAD_REGIME_AND_YEARLY_FAILURE_STATE_LAB_045'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC44=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044'/'output'/'execution_stream.csv'
TR44=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044'/'output'/'transfer.csv'
R35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'run_lab.py'
R34=LABS/'BTC_FUTURES_RETAIL_CROWDING_X_SPOT_FLOW_DIVERGENCE_AND_OI_PROFITABILITY_MAP_LAB_034'/'run_lab.py'
for name,path in [('l35',R35),('l34',R34)]:
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    if name=='l35': L35=mod
    else: L34=mod
L35.OUT=OUT; L34.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC'); SEED=20260908; BOOT_N=5000
FEATURES=['downside_extension_72h_atr','bear_trend_eff_24h','flow_persist_12h','bear_trend_24h_atr','bear_trend_72h_atr','downside_extension_24h_atr','atr_rank_90d','flow_persist_3h','oi_logchg_3h','oi_logchg_12h']
PRIMARY=['downside_extension_72h_atr','bear_trend_eff_24h','flow_persist_12h']
BAD={'2022','2023','2025_H1'}; GOOD={'2021','2024','2025_H2','2026_JAN_JUL'}
PERIODS=[('2021','2021-01-01','2022-01-01'),('2022','2022-01-01','2023-01-01'),('2023','2023-01-01','2024-01-01'),('2024','2024-01-01','2025-01-01'),('2025_H1','2025-01-01','2025-07-01'),('2025_H2','2025-07-01','2026-01-01'),('2026_JAN_JUL','2026-01-01','2026-08-01')]


def load_exec():
    d=pd.read_csv(SRC44)
    for c in ['signal_time','entry_time','exit_time','horizon']:
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['stop_atr','net_r_5bps','gross_r','flow_id','entry_price']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    for c in ['traded','covered','eligible']:
        if c in d.columns:
            d[c]=d[c].astype(str).str.lower().isin(['true','1']) if d[c].dtype==object else d[c].astype(bool)
    q=d[(d.clock=='ACCEPT')&(d.stop_atr==2.5)&d.traded&(d.signal_time<PRE)].copy()
    q['regime_time']=q.entry_time-pd.Timedelta(minutes=15)
    return q.sort_values('signal_time').reset_index(drop=True)


def period_label(t):
    for name,a,b in PERIODS:
        if pd.Timestamp(a,tz='UTC')<=t<pd.Timestamp(b,tz='UTC'): return name
    return 'OTHER'


def causal_atr_rank(fut,t,atr):
    hist=fut.loc[(fut.index>=t-pd.Timedelta(days=90))&(fut.index<t),'atr14'].dropna().to_numpy(float)
    if len(hist)<30*96 or not np.isfinite(atr): return np.nan
    return float((hist<=atr).mean())


def build_features(execd,fut,metrics):
    # Precompute causal rolling price quantities at every M15 bar.
    close=pd.to_numeric(fut.close,errors='coerce'); high=pd.to_numeric(fut.high,errors='coerce'); atr=pd.to_numeric(fut.atr14,errors='coerce')
    abschg=close.diff().abs()
    roll_abs24=abschg.rolling(96,min_periods=96).sum()
    high24=high.rolling(96,min_periods=96).max(); high72=high.rolling(288,min_periods=288).max()
    rows=[]
    for r in execd.itertuples(index=False):
        t=pd.Timestamp(r.regime_time); row=dict(flow_id=int(r.flow_id),signal_time=r.signal_time,entry_time=r.entry_time,regime_time=t,net_r_5bps=float(r.net_r_5bps),exit_reason=r.exit_reason,period=period_label(r.signal_time))
        row['period_state']='BAD' if row['period'] in BAD else ('GOOD' if row['period'] in GOOD else 'OTHER')
        for f in FEATURES: row[f]=np.nan
        if t in fut.index:
            a=float(atr.loc[t]); c=float(close.loc[t]); t24=t-pd.Timedelta(hours=24); t72=t-pd.Timedelta(hours=72)
            if np.isfinite(a) and a>0:
                if t24 in fut.index:
                    c24=float(close.loc[t24]); row['bear_trend_24h_atr']=(c24-c)/a
                    denom=float(roll_abs24.loc[t]) if np.isfinite(roll_abs24.loc[t]) else np.nan
                    row['bear_trend_eff_24h']=(c24-c)/denom if np.isfinite(denom) and denom>0 else np.nan
                if t72 in fut.index: row['bear_trend_72h_atr']=(float(close.loc[t72])-c)/a
                h24=float(high24.loc[t]) if np.isfinite(high24.loc[t]) else np.nan; h72=float(high72.loc[t]) if np.isfinite(high72.loc[t]) else np.nan
                row['downside_extension_24h_atr']=(h24-c)/a if np.isfinite(h24) else np.nan
                row['downside_extension_72h_atr']=(h72-c)/a if np.isfinite(h72) else np.nan
                row['atr_rank_90d']=causal_atr_rank(fut,t,a)
        if t in metrics.index:
            for n,name in [(12,'flow_persist_3h'),(48,'flow_persist_12h')]:
                z=metrics.loc[(metrics.index<=t)&(metrics.index>t-pd.Timedelta(minutes=15*n)),'delta_ls_12'].dropna()
                row[name]=float((z>0).mean()) if len(z)>=max(6,n//2) else np.nan
            oi=float(metrics.loc[t,'sum_open_interest']) if 'sum_open_interest' in metrics.columns else np.nan
            for h,name in [(3,'oi_logchg_3h'),(12,'oi_logchg_12h')]:
                tt=t-pd.Timedelta(hours=h)
                if tt in metrics.index and oi>0:
                    p=float(metrics.loc[tt,'sum_open_interest'])
                    row[name]=float(np.log(oi)-np.log(p)) if p>0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)


def bh(p):
    p=np.asarray(p,float); n=len(p); order=np.argsort(p); q=np.ones(n); run=1.0
    for j in range(n-1,-1,-1):
        i=order[j]; run=min(run,p[i]*n/(j+1)); q[i]=min(1.0,run)
    return q


def discrimination(d):
    rows=[]
    for feat in FEATURES:
        b=pd.to_numeric(d.loc[d.period_state=='BAD',feat],errors='coerce').dropna().to_numpy(float)
        g=pd.to_numeric(d.loc[d.period_state=='GOOD',feat],errors='coerce').dropna().to_numpy(float)
        if len(b)>=3 and len(g)>=3:
            u,p=mannwhitneyu(b,g,alternative='two-sided'); rbc=2*float(u)/(len(b)*len(g))-1
        else: p=rbc=np.nan
        rows.append(dict(feature=feat,bad_n=len(b),good_n=len(g),bad_mean=float(np.mean(b)) if len(b) else np.nan,good_mean=float(np.mean(g)) if len(g) else np.nan,bad_median=float(np.median(b)) if len(b) else np.nan,good_median=float(np.median(g)) if len(g) else np.nan,rbc=float(rbc) if np.isfinite(rbc) else np.nan,p=float(p) if np.isfinite(p) else np.nan))
    x=pd.DataFrame(rows); x['q_bh']=bh(x.p.fillna(1).to_numpy(float)); return x


def payoff_alignment(d):
    rows=[]
    for feat in FEATURES:
        z=d[[feat,'net_r_5bps']].apply(pd.to_numeric,errors='coerce').dropna()
        if len(z)>=3:
            rho,p=spearmanr(z[feat],z.net_r_5bps); rho=float(rho); p=float(p)
        else: rho=p=np.nan
        rows.append(dict(feature=feat,n=len(z),rho=rho,p=p))
    x=pd.DataFrame(rows); x['q_bh']=bh(x.p.fillna(1).to_numpy(float)); return x


def cluster_boot(d,feat):
    q=d[d.period_state.isin(['BAD','GOOD'])].dropna(subset=[feat]).copy()
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    arr=[]
    for _,g in q.groupby('cluster'):
        b=g.loc[g.period_state=='BAD',feat].to_numpy(float); a=g.loc[g.period_state=='GOOD',feat].to_numpy(float)
        arr.append((b.sum(),len(b),a.sum(),len(a)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        z=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if z[1]>0 and z[3]>0: vals.append(float(z[0]/z[1]-z[2]/z[3]))
    v=np.asarray(vals,float); b=q[q.period_state=='BAD'][feat].mean(); g=q[q.period_state=='GOOD'][feat].mean()
    return dict(feature=feat,point=float(b-g),clusters=m,draws=len(v),ci_lo=float(np.quantile(v,.025)) if len(v) else np.nan,ci_hi=float(np.quantile(v,.975)) if len(v) else np.nan)


def period_map(d):
    tr=pd.read_csv(TR44)
    tr=tr[(tr.clock=='ACCEPT')&(pd.to_numeric(tr.stop_atr,errors='coerce')==2.5)]
    rows=[]
    for name,a,b in PERIODS:
        q=d[d.period==name]; rec=dict(period=name,state='BAD' if name in BAD else 'GOOD',n=len(q),trade_ev=float(q.net_r_5bps.mean()) if len(q) else np.nan)
        z=tr[tr['slice']==name]
        rec['ev_per_original']=float(z.iloc[0].ev_per_original_5bps) if len(z) else np.nan
        rec['pf']=float(z.iloc[0].pf_5bps) if len(z) else np.nan
        for feat in FEATURES: rec[feat]=float(q[feat].mean()) if len(q) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def period_correlations(pm):
    rows=[]
    for feat in FEATURES:
        z=pm[[feat,'ev_per_original']].dropna()
        if len(z)>=3:
            rho,p=spearmanr(z[feat],z.ev_per_original); rho=float(rho); p=float(p)
        else: rho=p=np.nan
        rows.append(dict(feature=feat,n_periods=len(z),rho_vs_period_ev=rho,p=p))
    return pd.DataFrame(rows)


def row(df,feat): return df[df.feature==feat].iloc[0]
def bootrow(boots,feat): return next(x for x in boots if x['feature']==feat)
def py(x):
    if isinstance(x,(np.bool_,)): return bool(x)
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,)): return None if not np.isfinite(x) else float(x)
    raise TypeError(type(x).__name__)


def main():
    e=load_exec(); fut=L35.download_futures(); metrics=L34.download_metrics(); d=build_features(e,fut,metrics); d.to_csv(OUT/'failure_state_stream.csv',index=False)
    disc=discrimination(d); pay=payoff_alignment(d); boots=[cluster_boot(d,f) for f in PRIMARY]; pm=period_map(d); pc=period_correlations(pm)
    disc.to_csv(OUT/'bad_good_discrimination.csv',index=False); pay.to_csv(OUT/'payoff_alignment.csv',index=False); pm.to_csv(OUT/'period_map.csv',index=False); pc.to_csv(OUT/'period_correlations.csv',index=False); (OUT/'primary_bootstrap.json').write_text(json.dumps(boots,indent=2),encoding='utf-8')
    fut_cov=float(d[['downside_extension_72h_atr','bear_trend_eff_24h','bear_trend_24h_atr','bear_trend_72h_atr','downside_extension_24h_atr','atr_rank_90d']].notna().all(axis=1).mean())
    met_cov=float(d[['flow_persist_12h','flow_persist_3h','oi_logchg_3h','oi_logchg_12h']].notna().all(axis=1).mean())
    h1=row(disc,'downside_extension_72h_atr'); h2=row(disc,'bear_trend_eff_24h'); h3=row(disc,'flow_persist_12h')
    p1=row(pay,'downside_extension_72h_atr'); p2=row(pay,'bear_trend_eff_24h'); p3=row(pay,'flow_persist_12h')
    b1=bootrow(boots,'downside_extension_72h_atr'); b2=bootrow(boots,'bear_trend_eff_24h'); b3=bootrow(boots,'flow_persist_12h')
    gates={
      'exact_frozen_accept25_preaug_trades_327':len(e)==327,
      'frozen_execution_payoff_timestamp_coverage_100pct':bool(e.entry_time.notna().all() and e.net_r_5bps.notna().all()),
      'futures_regime_feature_coverage_ge_99pct':fut_cov>=.99,
      'metrics_regime_feature_coverage_ge_95pct':met_cov>=.95,
      'h1_bad_extension72_gt_good':bool(h1.rbc>0),
      'h1_abs_rbc_ge_0_15':bool(abs(h1.rbc)>=.15),
      'h1_bh_q_le_0_10':bool(h1.q_bh<=.10),
      'h1_trade_rho_negative':bool(p1.rho<0),
      'h2_bad_bear_eff24_lt_good':bool(h2.rbc<0),
      'h2_abs_rbc_ge_0_15':bool(abs(h2.rbc)>=.15),
      'h2_bh_q_le_0_10':bool(h2.q_bh<=.10),
      'h2_trade_rho_positive':bool(p2.rho>0),
      'h3_bad_flowpersist12_lt_good':bool(h3.rbc<0),
      'h3_abs_rbc_ge_0_15':bool(abs(h3.rbc)>=.15),
      'h3_bh_q_le_0_10':bool(h3.q_bh<=.10),
      'h3_trade_rho_positive':bool(p3.rho>0),
      'at_least_2_primary_discrimination_q_le_0_10':sum([h1.q_bh<=.10,h2.q_bh<=.10,h3.q_bh<=.10])>=2,
      'at_least_1_primary_boot_ci_expected_excludes_zero':bool(b1['ci_lo']>0 or b2['ci_hi']<0 or b3['ci_hi']<0),
      'any_feature_discrimination_bh_q_le_0_10':bool((disc.q_bh<=.10).any()),
      'any_feature_trade_payoff_bh_q_le_0_10':bool((pay.q_bh<=.10).any()),
      'recent_periods_not_used_for_threshold_weight_tuning':True,
      'august_not_used_for_selection':True}
    primary_dirs=sum([gates['h1_bad_extension72_gt_good'],gates['h2_bad_bear_eff24_lt_good'],gates['h3_bad_flowpersist12_lt_good']])
    score=sum(bool(v) for v in gates.values())
    if score>=17 and primary_dirs>=2 and gates['at_least_2_primary_discrimination_q_le_0_10'] and gates['at_least_1_primary_boot_ci_expected_excludes_zero']:
        verdict='PASS_CAUSAL_BAD_REGIME_STATE_FOUND_REUSED'
    elif score>=11 or any([gates['h1_bh_q_le_0_10'],gates['h2_bh_q_le_0_10'],gates['h3_bh_q_le_0_10']]): verdict='WATCH_FAILURE_STATE_PARTIAL_REUSED'
    else: verdict='FAIL_NO_CAUSAL_YEARLY_FAILURE_STATE'
    meta=dict(verdict=verdict,n=len(e),futures_coverage=fut_cov,metrics_coverage=met_cov,bad_n=int((d.period_state=='BAD').sum()),good_n=int((d.period_state=='GOOD').sum()),score=score)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')
    def f(x): return '—' if pd.isna(x) else f'{float(x):.3f}'
    L=[f'# {LAB}','',f'**Verdict: {verdict} — {score}/{len(gates)}**','', '## Frozen lineage',f'- ACCEPT2.5 trades: **{len(e)}**; BAD **{meta["bad_n"]}**, GOOD **{meta["good_n"]}**',f'- futures/metrics feature coverage: **{fut_cov:.1%} / {met_cov:.1%}**',f'- regime clock: **entry_time - 15m**','', '## BAD vs GOOD causal regime features','', '| Feature | Bad N | Good N | Bad mean | Good mean | RBC | p | BH q |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in disc.iterrows(): L.append(f'| {r.feature} | {int(r.bad_n)} | {int(r.good_n)} | {f(r.bad_mean)} | {f(r.good_mean)} | {f(r.rbc)} | {f(r.p)} | {f(r.q_bh)} |')
    L+=['','## Feature → frozen trade payoff','', '| Feature | N | rho→netR | p | BH q |','|---|---:|---:|---:|---:|']
    for _,r in pay.iterrows(): L.append(f'| {r.feature} | {int(r.n)} | {f(r.rho)} | {f(r.p)} | {f(r.q_bh)} |')
    L+=['','## Primary 7d cluster bootstrap (BAD − GOOD)']
    for b in boots: L.append(f'- `{b["feature"]}`: **{b["point"]:+.3f}**, 95% CI **[{b["ci_lo"]:+.3f}, {b["ci_hi"]:+.3f}]**, clusters={b["clusters"]}')
    L+=['','## Fixed yearly/period map','', '| Period | State | N | Trade EV | EV/original | PF | Ext72 | BearEff24 | FlowPersist12 | ATRrank | OI3h |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in pm.iterrows(): L.append(f'| {r.period} | {r.state} | {int(r.n)} | {f(r.trade_ev)} | {f(r.ev_per_original)} | {f(r.pf)} | {f(r.downside_extension_72h_atr)} | {f(r.bear_trend_eff_24h)} | {f(r.flow_persist_12h)} | {f(r.atr_rank_90d)} | {f(r.oi_logchg_3h)} |')
    L+=['','## Period-level descriptive correlations (N=7)','', '| Feature | rho vs EV/original | p |','|---|---:|---:|']
    for _,r in pc.iterrows(): L.append(f'| {r.feature} | {f(r.rho_vs_period_ev)} | {f(r.p)} |')
    L+=['','## Gates']+[f'- {"PASS" if v else "FAIL"} — `{k}`' for k,v in gates.items()]+['','## Guardrail','BAD/GOOD labels come from reused LAB044 yearly execution and are descriptive. No cutoff/router/weight was searched. Any apparent failure-state must be independently converted into a preregistered causal router and replicated before use. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':verdict,'score':score,'meta':meta,'gates':gates},indent=2,default=py))

if __name__=='__main__': main()
