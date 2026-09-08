#!/usr/bin/env python3
from __future__ import annotations
import io, json, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from scipy.stats import spearmanr

LAB='BTC_FUTURES_RETAIL_CROWDING_X_SPOT_FLOW_DIVERGENCE_AND_OI_PROFITABILITY_MAP_LAB_034'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
FLOW=LABS/'BTC_BINANCE_RETAIL_FLOW_DIRECTION_X_H4_PIVOT_M15_PRICE_TIMING_LAB_022'/'output'/'flow_only_nonoverlap.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC'); AUG_END=pd.Timestamp('2026-09-01',tz='UTC')
START_MONTH='2020-12'; END_MONTH='2026-08'; METRIC_START='2020-12-01'; METRIC_END='2026-08-31'
SEED=20260908; BOOT_N=5000
FEATURES=['retail_ratio_level','crowd_change_strength','oi_logchg_3h','futures_taker_imb_3h','spot_taker_imb_3h','spot_trade_confirmation','futures_trade_confirmation','leveraged_vs_spot_divergence','top_count_vs_retail_logdiv','top_position_vs_retail_logdiv']


def ts_from_num(s):
    v=pd.to_numeric(s,errors='coerce'); med=v.dropna().abs().median() if v.notna().any() else np.nan
    unit='us' if pd.notna(med) and med>1e14 else ('ms' if pd.notna(med) and med>1e11 else 's')
    return pd.to_datetime(v,unit=unit,errors='coerce',utc=True)


def load_flow():
    d=pd.read_csv(FLOW); d['signal_time']=pd.to_datetime(d.signal_time,errors='coerce',utc=True)
    d['side']=pd.to_numeric(d.side,errors='coerce').astype('Int64'); d['signed12_atr']=pd.to_numeric(d.signed12_atr,errors='coerce')
    d=d.dropna().sort_values('signal_time').reset_index(drop=True); d['flow_id']=np.arange(len(d),dtype=int)
    return d


def parse_kline_zip(content,label):
    z=zipfile.ZipFile(io.BytesIO(content)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:return pd.DataFrame()
    d=pd.read_csv(z.open(names[0]),header=None)
    if len(d.columns)<11: raise RuntimeError(f'Bad kline schema {label}: {d.shape}')
    # Header rows exist in some archives; numeric coercion removes them safely.
    out=pd.DataFrame({'time':ts_from_num(d.iloc[:,0]),'quote':pd.to_numeric(d.iloc[:,7],errors='coerce'),'taker_buy_quote':pd.to_numeric(d.iloc[:,10],errors='coerce'),'close':pd.to_numeric(d.iloc[:,4],errors='coerce')}).dropna()
    return out


def get_zip(url,parser,label):
    last=''
    for _ in range(2):
        try:
            r=requests.get(url,timeout=25)
            if r.status_code==200:return parser(r.content,label),200,''
            return None,r.status_code,'missing'
        except Exception as e:last=str(e)
    return None,'EXC',last


def download_klines(kind):
    periods=list(pd.period_range(START_MONTH,END_MONTH,freq='M')); parts=[]; manifest=[]
    if kind=='spot': base='https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/15m'
    else: base='https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m'
    def one(p):
        ym=f'{p.year}-{p.month:02d}'; fn=f'BTCUSDT-15m-{ym}.zip'; url=f'{base}/{fn}'
        d,s,n=get_zip(url,parse_kline_zip,fn); return d,dict(month=ym,status=s,rows=0 if d is None else len(d),note=n)
    with ThreadPoolExecutor(max_workers=12) as ex:
        fut=[ex.submit(one,p) for p in periods]
        for f in as_completed(fut):
            d,m=f.result(); manifest.append(m)
            if d is not None and len(d):parts.append(d)
    pd.DataFrame(manifest).sort_values('month').to_csv(OUT/f'{kind}_kline_manifest.csv',index=False)
    if not parts: raise RuntimeError(f'No {kind} klines')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').set_index('time')
    x['q12']=x.quote.rolling(12,min_periods=12).sum(); x['tb12']=x.taker_buy_quote.rolling(12,min_periods=12).sum()
    x['imb3h']=(2*x.tb12-x.q12)/x.q12.replace(0,np.nan)
    return x


def parse_metrics_zip(content,label):
    z=zipfile.ZipFile(io.BytesIO(content)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:return pd.DataFrame()
    d=pd.read_csv(z.open(names[0])); d.columns=[str(c).strip() for c in d.columns]
    tc='create_time' if 'create_time' in d.columns else ('timestamp' if 'timestamp' in d.columns else None)
    if tc is None: raise RuntimeError(f'No metrics time {label}: {list(d.columns)}')
    want=['count_long_short_ratio','sum_open_interest','count_toptrader_long_short_ratio','sum_toptrader_long_short_ratio','sum_taker_long_short_vol_ratio']
    keep=[c for c in want if c in d.columns]
    if 'count_long_short_ratio' not in keep or 'sum_open_interest' not in keep: raise RuntimeError(f'Missing required metrics {label}: {list(d.columns)}')
    t=d[tc]
    if pd.api.types.is_numeric_dtype(t): time=ts_from_num(t)
    else: time=pd.to_datetime(t.astype(str).str.strip(),errors='coerce',utc=True)
    out=pd.DataFrame({'time':time})
    for c in keep:out[c]=pd.to_numeric(d[c],errors='coerce')
    return out.dropna(subset=['time'])


def download_metrics():
    days=list(pd.date_range(METRIC_START,METRIC_END,freq='D')); parts=[]; manifest=[]; base='https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT'
    def one(t):
        ds=t.strftime('%Y-%m-%d'); fn=f'BTCUSDT-metrics-{ds}.zip'; d,s,n=get_zip(f'{base}/{fn}',parse_metrics_zip,fn)
        return d,dict(date=ds,status=s,rows=0 if d is None else len(d),note=n)
    with ThreadPoolExecutor(max_workers=24) as ex:
        fut=[ex.submit(one,t) for t in days]
        for f in as_completed(fut):
            d,m=f.result(); manifest.append(m)
            if d is not None and len(d):parts.append(d)
    pd.DataFrame(manifest).sort_values('date').to_csv(OUT/'metrics_manifest.csv',index=False)
    if not parts: raise RuntimeError('No metrics')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').set_index('time')
    x=x.resample('15min',label='left',closed='left').last().ffill(limit=2)
    x['delta_ls_12']=x.count_long_short_ratio-x.count_long_short_ratio.shift(12)
    x['oi_logchg_3h']=np.log(x.sum_open_interest.where(x.sum_open_interest>0))-np.log(x.sum_open_interest.shift(12).where(x.sum_open_interest.shift(12)>0))
    return x


def build(flow,metrics,spot,fut):
    rows=[]
    for r in flow.itertuples():
        t=r.signal_time
        if t not in metrics.index or t not in spot.index or t not in fut.index:continue
        m=metrics.loc[t]; si=float(spot.loc[t,'imb3h']); fi=float(fut.loc[t,'imb3h']); side=int(r.side)
        ratio=float(m.get('count_long_short_ratio',np.nan)); delta=float(m.get('delta_ls_12',np.nan)); oi=float(m.get('oi_logchg_3h',np.nan))
        tc=float(m.get('count_toptrader_long_short_ratio',np.nan)); tp=float(m.get('sum_toptrader_long_short_ratio',np.nan))
        d=dict(flow_id=int(r.flow_id),signal_time=t,side=side,signed12_atr=float(r.signed12_atr),retail_ratio_level=ratio,crowd_change_strength=-side*delta,oi_logchg_3h=oi,futures_taker_imb_3h=fi,spot_taker_imb_3h=si,spot_trade_confirmation=side*si,futures_trade_confirmation=side*fi,leveraged_vs_spot_divergence=-side*(fi-si),top_count_vs_retail_logdiv=np.log(tc)-np.log(ratio) if tc>0 and ratio>0 else np.nan,top_position_vs_retail_logdiv=np.log(tp)-np.log(ratio) if tp>0 and ratio>0 else np.nan,metrics_taker_ratio=float(m.get('sum_taker_long_short_vol_ratio',np.nan)))
        rows.append(d)
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)


def bh(p):
    p=np.asarray(p,float); n=len(p); order=np.argsort(p); q=np.ones(n); run=1.0
    for j in range(n-1,-1,-1):
        i=order[j]; run=min(run,p[i]*n/(j+1)); q[i]=min(1.0,run)
    return q


def feature_tests(d):
    pre=d[d.signal_time<PRE]; rows=[]; qrows=[]
    for feat in FEATURES:
        z=pre[[feat,'signed12_atr']].apply(pd.to_numeric,errors='coerce').dropna()
        if len(z)>=3: rho,p=spearmanr(z[feat],z.signed12_atr); rho=float(rho); p=float(p)
        else:rho=p=np.nan
        rows.append(dict(feature=feat,n=len(z),rho=rho,p=p,missing=1-len(z)/len(pre)))
        if len(z)>=20:
            ranks=pd.qcut(z[feat].rank(method='first'),5,labels=False)+1
            for qi in range(1,6):
                a=z.loc[ranks==qi,'signed12_atr']; qrows.append(dict(feature=feat,quintile=qi,n=len(a),mean_atr=float(a.mean()),hit=float((a>0).mean())))
    ft=pd.DataFrame(rows); ft['q_bh']=bh(ft.p.fillna(1).to_numpy(float)); return ft,pd.DataFrame(qrows)


def rho_slice(d,mask,label):
    z=d.loc[mask,['leveraged_vs_spot_divergence','signed12_atr']].dropna()
    if len(z)<3:return dict(sample=label,n=len(z),rho=np.nan,p=np.nan,mean=np.nan)
    rho,p=spearmanr(z.leveraged_vs_spot_divergence,z.signed12_atr); return dict(sample=label,n=len(z),rho=float(rho),p=float(p),mean=float(z.signed12_atr.mean()))


def cell_map(d):
    pre=d[d.signal_time<PRE].dropna(subset=['oi_logchg_3h','leveraged_vs_spot_divergence','spot_trade_confirmation'])
    rows=[]
    for oi in [0,1]:
      for div in [0,1]:
       for sp in [0,1]:
        q=pre[((pre.oi_logchg_3h>0).astype(int)==oi)&((pre.leveraged_vs_spot_divergence>0).astype(int)==div)&((pre.spot_trade_confirmation>0).astype(int)==sp)]
        rows.append(dict(oi_up=oi,div_positive=div,spot_trade_confirm=sp,n=len(q),mean_atr=float(q.signed12_atr.mean()) if len(q) else np.nan,hit=float((q.signed12_atr>0).mean()) if len(q) else np.nan))
    return pd.DataFrame(rows)


def divergence_boot(d):
    pre=d[d.signal_time<PRE].dropna(subset=['leveraged_vs_spot_divergence','signed12_atr']).copy(); pre['rank']=pre.leveraged_vs_spot_divergence.rank(method='first'); pre['q']=pd.qcut(pre['rank'],5,labels=False)+1
    q1=pre[pre.q==1]; q5=pre[pre.q==5]; point=float(q5.signed12_atr.mean()-q1.signed12_atr.mean())
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); pre['cluster']=(((pre.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    groups=[]
    for _,g in pre.groupby('cluster'):
        a=g.loc[g.q==5,'signed12_atr'].to_numpy(float); b=g.loc[g.q==1,'signed12_atr'].to_numpy(float); groups.append((a.sum(),len(a),b.sum(),len(b)))
    arr=np.asarray(groups,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0:vals.append(float(s[0]/s[1]-s[2]/s[3]))
    vals=np.asarray(vals,float); return dict(n_clusters=m,draws=len(vals),point=point,ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),q20=float(pre.leveraged_vs_spot_divergence.quantile(.2)),q80=float(pre.leveraged_vs_spot_divergence.quantile(.8)),q1_mean=float(q1.signed12_atr.mean()),q5_mean=float(q5.signed12_atr.mean()))


def report(meta,ft,qmap,cells,slices,boot,gates):
    def f(x):
        if pd.isna(x):return '—'
        return f'{x:.3f}'
    L=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'', '## Coverage',f"- frozen flow rows: **{meta['flow_n']}**; joined: **{meta['joined_n']}**",f"- pre-Aug spot/futures/metrics coverage: **{meta['spot_cov']:.1%} / {meta['fut_cov']:.1%} / {meta['metric_cov']:.1%}**",'', '## Threshold-free feature tests','', '| Feature | N | rho→12h | p | BH q | Missing |','|---|---:|---:|---:|---:|---:|']
    for _,r in ft.iterrows():L.append(f"| {r.feature} | {int(r.n)} | {f(r.rho)} | {f(r.p)} | {f(r.q_bh)} | {f(r.missing)} |")
    L+=['','## leveraged_vs_spot_divergence quintiles','', '| Q | N | Mean ATR | Hit |','|---|---:|---:|---:|']
    z=qmap[qmap.feature=='leveraged_vs_spot_divergence']
    for _,r in z.iterrows():L.append(f"| Q{int(r.quintile)} | {int(r.n)} | {f(r.mean_atr)} | {f(r.hit)} |")
    L+=['',f"Q5-Q1 = **{f(boot['point'])} ATR**, 7d bootstrap 95% CI **[{f(boot['ci_lo'])}, {f(boot['ci_hi'])}]**",'', '## Fixed OI × divergence × spot confirmation map','', '| OI up | Div+ | Spot confirms trade | N | Mean ATR | Hit |','|---:|---:|---:|---:|---:|---:|']
    for _,r in cells.iterrows():L.append(f"| {int(r.oi_up)} | {int(r.div_positive)} | {int(r.spot_trade_confirm)} | {int(r.n)} | {f(r.mean_atr)} | {f(r.hit)} |")
    L+=['','## Transfer / side divergence rho','', '| Slice | N | rho | p | Mean ATR |','|---|---:|---:|---:|---:|']
    for _,r in slices.iterrows():L.append(f"| {r['sample']} | {int(r.n)} | {f(r.rho)} | {f(r.p)} | {f(r['mean'])} |")
    L+=['','## Gates']
    for k,v in gates.items():L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    L+=['','## Guardrail','This LAB maps quality on reused frozen signals only. No quintile/cell/feature cutoff is promoted. No entry/stop/TP optimization. August 2026 is audit-only. Live allocation = **0**.']
    return '\n'.join(L)+'\n'


def main():
    flow=load_flow(); spot=download_klines('spot'); fut=download_klines('futures'); metrics=download_metrics()
    preflow=flow[flow.signal_time<PRE]
    spot_cov=float(preflow.signal_time.isin(spot.index).mean()); fut_cov=float(preflow.signal_time.isin(fut.index).mean()); metric_cov=float(preflow.signal_time.isin(metrics.index).mean())
    d=build(flow,metrics,spot,fut); d.to_csv(OUT/'joined_external_state_stream.csv',index=False)
    ft,qmap=feature_tests(d); ft.to_csv(OUT/'feature_tests.csv',index=False); qmap.to_csv(OUT/'quintile_map.csv',index=False)
    cells=cell_map(d); cells.to_csv(OUT/'interaction_cells.csv',index=False); boot=divergence_boot(d); (OUT/'divergence_bootstrap.json').write_text(json.dumps(boot,indent=2),encoding='utf-8')
    slices=pd.DataFrame([
      rho_slice(d,d.signal_time<PRE,'ALL_PRE_AUG'),rho_slice(d,(d.signal_time<PRE)&(d.side==1),'LONG'),rho_slice(d,(d.signal_time<PRE)&(d.side==-1),'SHORT'),
      rho_slice(d,(d.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(d.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(d.side==-1),'2022_SHORT'),
      rho_slice(d,(d.signal_time>=pd.Timestamp('2025-07-01',tz='UTC'))&(d.signal_time<pd.Timestamp('2026-01-01',tz='UTC')),'2025_H2'),rho_slice(d,(d.signal_time>=pd.Timestamp('2026-01-01',tz='UTC'))&(d.signal_time<PRE),'2026_JAN_JUL'),
      rho_slice(d,(d.signal_time>=PRE)&(d.signal_time<AUG_END),'AUG_REUSED')]); slices.to_csv(OUT/'divergence_transfer.csv',index=False)
    base=float(d.loc[d.signal_time<PRE,'signed12_atr'].mean()); cell=cells[(cells.oi_up==1)&(cells.div_positive==1)]; best_oi_div=float(cell.mean_atr.mean()) if len(cell) else np.nan
    divrow=ft[ft.feature=='leveraged_vs_spot_divergence'].iloc[0]; pre=d[d.signal_time<PRE].dropna(subset=['leveraged_vs_spot_divergence']); q80=boot['q80']; y22=pre[(pre.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(pre.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(pre.side==-1)&(pre.leveraged_vs_spot_divergence>=q80)]
    sr={r['sample']:r for _,r in slices.iterrows()}
    gates={
      'exact_frozen_flow_lineage_ge_3200':len(flow)>=3200,
      'spot_kline_coverage_ge_90pct':spot_cov>=.90,
      'futures_kline_coverage_ge_90pct':fut_cov>=.90,
      'metrics_oi_coverage_ge_90pct':metric_cov>=.90,
      'at_least_one_feature_bh_q_le_0_10':bool((ft.q_bh<=.10).any()),
      'at_least_one_feature_abs_rho_ge_0_05':bool((ft.rho.abs()>=.05).any()),
      'divergence_rho_positive':bool(divrow.rho>0),
      'divergence_q5_minus_q1_ge_0_20':bool(boot['point']>=.20),
      'divergence_boot_ci_lower_gt_zero':bool(boot['ci_lo']>0),
      'oi_up_positive_div_cell_beats_baseline_0_15':bool(best_oi_div>=base+.15),
      'stress_2022_short_high_div_positive':bool(len(y22)>=20 and y22.signed12_atr.mean()>0),
      'long_short_divergence_rho_same_sign':bool(np.sign(sr['LONG']['rho'])==np.sign(sr['SHORT']['rho']) and sr['LONG']['rho']!=0),
      '2025h2_2026_divergence_rho_same_sign':bool(np.sign(sr['2025_H2']['rho'])==np.sign(sr['2026_JAN_JUL']['rho']) and sr['2025_H2']['rho']!=0),
      'august_not_used_for_selection':True,
    }
    score=sum(gates.values()); critical=['exact_frozen_flow_lineage_ge_3200','spot_kline_coverage_ge_90pct','futures_kline_coverage_ge_90pct','metrics_oi_coverage_ge_90pct']; mech=gates['divergence_rho_positive'] or gates['divergence_q5_minus_q1_ge_0_20'] or gates['divergence_boot_ci_lower_gt_zero']
    if score>=11 and all(gates[k] for k in critical) and mech:verdict='PASS_FUTURES_SPOT_DIVERGENCE_QUALITY_LAYER'
    elif mech and all(gates[k] for k in critical):verdict='WATCH_EXTERNAL_STATE_SIGNAL_TRANSFER_INCOMPLETE'
    else:verdict='FAIL_NO_FUTURES_SPOT_DIVERGENCE_QUALITY_EDGE'
    meta=dict(verdict=verdict,flow_n=len(flow),joined_n=len(d),spot_cov=spot_cov,fut_cov=fut_cov,metric_cov=metric_cov,baseline_mean=base,oi_div_mean=best_oi_div)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'bootstrap':boot,'gates':gates},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(meta,ft,qmap,cells,slices,boot,gates); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__':main()
