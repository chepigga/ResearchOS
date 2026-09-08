#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

LAB='BTC_RETAIL_FLOW_REACCEPTANCE_EXTENSION_SEQUENCE_LATENCY_AND_CYCLE_DURATION_REGIME_SPLIT_LAB_033'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC32=LABS/'BTC_RETAIL_FLOW_REACCEPTANCE_EXTENSION050_VS_SECOND_FAILURE_FIRST_PASSAGE_LAB_032'/'output'/'extension_vs_second_failure_stream.csv'
SRC30=LABS/'BTC_RETAIL_FLOW_ACCEPTANCE_ORIGIN_CLOSE2_FAILURE_RECOVERY_AND_REACCEPTANCE_LAB_030'/'output'/'failure_recovery_stream.csv'
SRC26=LABS/'BTC_RETAIL_FLOW_EARLY_DIRECTIONAL_ACCEPTANCE_VS_ADVERSE_FAILURE_FIRST_PASSAGE_LAB_026'/'output'/'first_passage_2h.csv'
SRC23=LABS/'BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab023',SRC23); L23=importlib.util.module_from_spec(spec); spec.loader.exec_module(L23)
UTC='UTC'; PRE=pd.Timestamp('2026-08-01',tz=UTC); SEED=20260908; BOOT_N=5000
H25A=pd.Timestamp('2025-07-01',tz=UTC); H25B=pd.Timestamp('2026-01-01',tz=UTC)
Y26A=pd.Timestamp('2026-01-01',tz=UTC); Y26B=pd.Timestamp('2026-08-01',tz=UTC)
FEATURES=[
 'signal_to_accept_h','accept_to_failure_h','failure_to_origin_reclaim_h','failure_to_full_reaccept_h',
 'reaccept_to_extension_h','signal_to_extension_h','accept_to_extension_h','extra_bad_closes_before_reaccept',
 'cycle_count_accept_to_extension','origin_bad_close_count_accept_to_extension'
]

def load_inputs():
    e=pd.read_csv(SRC32); f=pd.read_csv(SRC30); a=pd.read_csv(SRC26)
    for d,cols in [(e,['signal_time','reaccept_time','class_time']),(f,['signal_time','failure_time','origin_reclaim_time','full_reaccept_time']),(a,['signal_time','passage_time'])]:
        for c in cols:d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for d,cols in [(e,['flow_id','side','origin','entry','atr14','residual_atr']),(f,['flow_id','side','signal_close','entry','atr14','extra_bad_closes_before_reaccept']),(a,['flow_id','side'])]:
        for c in cols:d[c]=pd.to_numeric(d[c],errors='coerce')
    e=e[e.state=='EXTENSION050_FIRST'].copy()
    a=a[a.state=='ACCEPT_FIRST'].copy()
    # one row per flow_id on frozen primary 2h clock
    a=a.sort_values('signal_time').drop_duplicates('flow_id',keep='first')
    f=f.sort_values('signal_time').drop_duplicates('flow_id',keep='first')
    e=e.sort_values('signal_time').drop_duplicates('flow_id',keep='first')
    return e,f,a

def hours(t1,t0):
    if pd.isna(t1) or pd.isna(t0):return np.nan
    return float((t1-t0).total_seconds()/3600.0)

def reconstruct_cycles(price,row):
    at=row['accept_time']; xt=row['extension_time']; side=int(row['side']); origin=float(row['origin']); entry=float(row['entry'])
    if pd.isna(at) or pd.isna(xt) or at not in price.index or xt not in price.index or xt<=at:
        return dict(recon_failure_time=pd.NaT,recon_reaccept_time=pd.NaT,cycle_count=np.nan,bad_closes=np.nan)
    path=price.loc[(price.index>at)&(price.index<=xt)]
    consec=0; failed=False; cycles=0; bad_count=0; first_fail=pd.NaT; first_reaccept=pd.NaT
    for t,z in path.iterrows():
        close=float(z.close)
        bad=side*(close-origin)<=0
        if bad: bad_count+=1
        if not failed:
            consec=consec+1 if bad else 0
            if consec>=2:
                failed=True
                if pd.isna(first_fail):first_fail=t
        else:
            reaccepted=side*(close-entry)>=0
            if reaccepted:
                cycles+=1; failed=False; consec=0
                if pd.isna(first_reaccept):first_reaccept=t
    return dict(recon_failure_time=first_fail,recon_reaccept_time=first_reaccept,cycle_count=float(cycles),bad_closes=float(bad_count))

def build_dataset(price,e,f,a):
    q=e[['flow_id','signal_time','side','origin','entry','atr14','reaccept_time','class_time','residual_atr']].copy()
    q=q.rename(columns={'reaccept_time':'extension_parent_reaccept_time','class_time':'extension_time'})
    q=q.merge(f[['flow_id','failure_time','origin_reclaim_time','full_reaccept_time','extra_bad_closes_before_reaccept']],on='flow_id',how='left',validate='1:1')
    q=q.merge(a[['flow_id','passage_time']],on='flow_id',how='left',validate='1:1').rename(columns={'passage_time':'accept_time'})
    rows=[]
    for _,r in q.iterrows():
        rec=reconstruct_cycles(price,r)
        d=r.to_dict(); d.update(rec); rows.append(d)
    q=pd.DataFrame(rows)
    q['signal_to_accept_h']=[hours(x,y) for x,y in zip(q.accept_time,q.signal_time)]
    q['accept_to_failure_h']=[hours(x,y) for x,y in zip(q.failure_time,q.accept_time)]
    q['failure_to_origin_reclaim_h']=[hours(x,y) for x,y in zip(q.origin_reclaim_time,q.failure_time)]
    q['failure_to_full_reaccept_h']=[hours(x,y) for x,y in zip(q.full_reaccept_time,q.failure_time)]
    q['reaccept_to_extension_h']=[hours(x,y) for x,y in zip(q.extension_time,q.full_reaccept_time)]
    q['signal_to_extension_h']=[hours(x,y) for x,y in zip(q.extension_time,q.signal_time)]
    q['accept_to_extension_h']=[hours(x,y) for x,y in zip(q.extension_time,q.accept_time)]
    q['cycle_count_accept_to_extension']=q.cycle_count
    q['origin_bad_close_count_accept_to_extension']=q.bad_closes
    q['clock_order_valid']=(q.signal_time<=q.accept_time)&(q.accept_time<=q.failure_time)&(q.failure_time<=q.full_reaccept_time)&(q.full_reaccept_time<=q.extension_time)
    q['failure_parity']=q.failure_time.notna()&q.recon_failure_time.notna()&(q.failure_time==q.recon_failure_time)
    q['reaccept_parity']=q.full_reaccept_time.notna()&q.recon_reaccept_time.notna()&(q.full_reaccept_time==q.recon_reaccept_time)
    return q

def bh_fdr(pvals):
    p=np.asarray(pvals,float); n=len(p); order=np.argsort(p); q=np.full(n,np.nan); running=1.0
    for rank_idx in range(n-1,-1,-1):
        i=order[rank_idx]; rank=rank_idx+1; running=min(running,p[i]*n/rank); q[i]=min(1.0,running)
    return q

def feature_tests(d):
    h=d[(d.signal_time>=H25A)&(d.signal_time<H25B)]
    y=d[(d.signal_time>=Y26A)&(d.signal_time<Y26B)]
    pre=d[d.signal_time<PRE]
    rows=[]
    for feat in FEATURES:
        x=pd.to_numeric(y[feat],errors='coerce').dropna().to_numpy(float)
        z=pd.to_numeric(h[feat],errors='coerce').dropna().to_numpy(float)
        if len(x)>=2 and len(z)>=2:
            u,p=mannwhitneyu(x,z,alternative='two-sided',method='asymptotic'); auc=float(u/(len(x)*len(z))); rbc=2*auc-1
        else:p=np.nan; rbc=np.nan
        tmp=pre[[feat,'residual_atr']].apply(pd.to_numeric,errors='coerce').dropna()
        if len(tmp)>=3:
            rho,rp=spearmanr(tmp[feat],tmp.residual_atr); rho=float(rho); rp=float(rp)
        else:rho=rp=np.nan
        rows.append(dict(feature=feat,n_2025h2=len(z),median_2025h2=float(np.median(z)) if len(z) else np.nan,n_2026=len(x),median_2026=float(np.median(x)) if len(x) else np.nan,
                         rbc_2026_vs_2025h2=float(rbc),p_mwu=float(p),spearman_pre=float(rho),p_spearman=float(rp),missing_pre=float(pre[feat].isna().mean())))
    out=pd.DataFrame(rows); valid=out.p_mwu.fillna(1.0).to_numpy(float); out['q_bh']=bh_fdr(valid)
    out['aligned']=(out.q_bh<=.10)&(out.rbc_2026_vs_2025h2.abs()>=.30)&(out.spearman_pre.abs()>=.10)&(out.p_spearman<=.05)&((out.rbc_2026_vs_2025h2*out.spearman_pre)>0)
    return out

def side_audit(d):
    rows=[]
    for side,name in [(1,'LONG'),(-1,'SHORT')]:
        h=d[(d.signal_time>=H25A)&(d.signal_time<H25B)&(d.side==side)]
        y=d[(d.signal_time>=Y26A)&(d.signal_time<Y26B)&(d.side==side)]
        for feat in FEATURES:
            x=pd.to_numeric(y[feat],errors='coerce').dropna().to_numpy(float); z=pd.to_numeric(h[feat],errors='coerce').dropna().to_numpy(float)
            if len(x)>=2 and len(z)>=2:
                u,p=mannwhitneyu(x,z,alternative='two-sided',method='asymptotic'); rbc=2*float(u/(len(x)*len(z)))-1
            else:rbc=p=np.nan
            rows.append(dict(side=name,feature=feat,n_2025h2=len(z),median_2025h2=float(np.median(z)) if len(z) else np.nan,n_2026=len(x),median_2026=float(np.median(x)) if len(x) else np.nan,rbc=float(rbc),p=float(p)))
    return pd.DataFrame(rows)

def cluster_boot_feature(d,feat):
    rng=np.random.default_rng(SEED); epoch=pd.Timestamp('1970-01-01',tz=UTC)
    h=d[(d.signal_time>=H25A)&(d.signal_time<H25B)][['signal_time',feat]].dropna().copy()
    y=d[(d.signal_time>=Y26A)&(d.signal_time<Y26B)][['signal_time',feat]].dropna().copy()
    for z in [h,y]: z['cluster']=(((z.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    hc=[g[feat].to_numpy(float) for _,g in h.groupby('cluster')]; yc=[g[feat].to_numpy(float) for _,g in y.groupby('cluster')]
    vals=[]
    if not hc or not yc:return dict(feature=feat,n_clusters_2025h2=len(hc),n_clusters_2026=len(yc),point=np.nan,ci_lo=np.nan,ci_hi=np.nan)
    for _ in range(BOOT_N):
        hs=np.concatenate([hc[i] for i in rng.integers(0,len(hc),size=len(hc))]); ys=np.concatenate([yc[i] for i in rng.integers(0,len(yc),size=len(yc))])
        vals.append(float(np.median(ys)-np.median(hs)))
    vals=np.asarray(vals,float); point=float(np.median(y[feat])-np.median(h[feat]))
    return dict(feature=feat,n_clusters_2025h2=len(hc),n_clusters_2026=len(yc),point=point,ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)))

def yearly_aligned(d,aligned):
    rows=[]
    for feat in aligned:
        for year in range(2021,2027):
            a=pd.Timestamp(f'{year}-01-01',tz=UTC); b=pd.Timestamp(f'{year+1}-01-01',tz=UTC) if year<2026 else PRE
            q=pd.to_numeric(d.loc[(d.signal_time>=a)&(d.signal_time<b),feat],errors='coerce').dropna()
            rows.append(dict(feature=feat,year=year,n=len(q),median=float(q.median()) if len(q) else np.nan))
    return pd.DataFrame(rows)

def report(ft,side,boots,gates,meta,yearly):
    def f(x):
        if pd.isna(x):return '—'
        return f'{x:.3f}'
    L=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
       '## Lineage / parity',f"- EXTENSION050 pre-Aug: **{meta['lineage_pre']}**; 2025H2 **{meta['n_h25']}**, 2026 Jan-Jul **{meta['n_26']}**",
       f"- Clock ordering: **{meta['clock_valid']:.3%}**",f"- First failure timestamp parity: **{meta['failure_parity']:.3%}**",f"- Full reaccept timestamp parity: **{meta['reaccept_parity']:.3%}**",'',
       '## Fixed feature tests: 2026 vs 2025H2','',
       '| Feature | Med 2025H2 | Med 2026 | RBC | p | BH q | rho→residual | p(rho) | Aligned |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in ft.iterrows():L.append(f"| {r.feature} | {f(r.median_2025h2)} | {f(r.median_2026)} | {f(r.rbc_2026_vs_2025h2)} | {f(r.p_mwu)} | {f(r.q_bh)} | {f(r.spearman_pre)} | {f(r.p_spearman)} | {'YES' if r.aligned else 'no'} |")
    L+=['','## Aligned-feature 7d cluster bootstrap','','| Feature | 2026-2025H2 median diff | 95% CI |','|---|---:|---:|']
    if len(boots):
        for _,r in boots.iterrows():L.append(f"| {r.feature} | {f(r.point)} | [{f(r.ci_lo)}, {f(r.ci_hi)}] |")
    else:L.append('| none | — | — |')
    L+=['','## Side composition',f"- 2025H2 LONG/SHORT: **{meta['h25_long']}/{meta['h25_short']}**",f"- 2026 LONG/SHORT: **{meta['y26_long']}/{meta['y26_short']}**",'', '## Gates']
    for k,v in gates.items():L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    if len(yearly):
        L+=['','## Yearly medians for aligned features','','| Feature | Year | N | Median |','|---|---:|---:|---:|']
        for _,r in yearly.iterrows():L.append(f"| {r.feature} | {int(r.year)} | {int(r.n)} | {f(r['median'])} |")
    L+=['','## Guardrail','This is a regime-mechanism audit only. No sequence cutoff/router is promoted from reused data. August 2026 is audit-only. Live allocation = **0**.']
    return '\n'.join(L)+'\n'

def main():
    price=L23.load_price(); e,f,a=load_inputs(); d=build_dataset(price,e,f,a); d.to_csv(OUT/'sequence_feature_stream.csv',index=False)
    pre=d[d.signal_time<PRE].copy(); h=pre[(pre.signal_time>=H25A)&(pre.signal_time<H25B)]; y=pre[(pre.signal_time>=Y26A)&(pre.signal_time<Y26B)]
    ft=feature_tests(d); ft.to_csv(OUT/'feature_tests.csv',index=False); side=side_audit(d); side.to_csv(OUT/'side_audit.csv',index=False)
    aligned=ft.loc[ft.aligned,'feature'].tolist(); boots=pd.DataFrame([cluster_boot_feature(d,x) for x in aligned]); boots.to_csv(OUT/'aligned_bootstrap.csv',index=False)
    yearly=yearly_aligned(d,aligned); yearly.to_csv(OUT/'aligned_yearly_medians.csv',index=False)
    clock_valid=float(pre.clock_order_valid.mean()) if len(pre) else 0.0
    elig_fail=pre[pre.failure_time.notna()&pre.recon_failure_time.notna()]; failure_parity=float(elig_fail.failure_parity.mean()) if len(elig_fail) else 0.0
    elig_re=pre[pre.full_reaccept_time.notna()&pre.recon_reaccept_time.notna()]; reaccept_parity=float(elig_re.reaccept_parity.mean()) if len(elig_re) else 0.0
    any_q=bool((ft.q_bh<=.10).any()); any_effect=bool((ft.rbc_2026_vs_2025h2.abs()>=.30).any()); any_aligned=bool(len(aligned)>0)
    boot_supported=False
    if len(boots):
        for _,r in boots.iterrows():
            rr=ft[ft.feature==r.feature].iloc[0]
            if rr.rbc_2026_vs_2025h2>0 and r.ci_lo>0:boot_supported=True
            if rr.rbc_2026_vs_2025h2<0 and r.ci_hi<0:boot_supported=True
    side_supported=False
    for feat in aligned:
        overall=float(ft.loc[ft.feature==feat,'rbc_2026_vs_2025h2'].iloc[0])
        q=side[(side.feature==feat)&(side.n_2025h2>=15)&(side.n_2026>=15)]
        if len(q) and any((np.sign(q.rbc.dropna())==np.sign(overall)) & (q.rbc.dropna().abs()>=.15)):side_supported=True
    missing_bad=int((ft.missing_pre>.10).sum())
    gates={
      'exact_lab032_extension050_pre_aug_ge_590':len(pre)>=590,
      '2025h2_n45_and_2026_n45':len(h)>=45 and len(y)>=45,
      'clock_ordering_ge_99pct':clock_valid>=.99,
      'reconstructed_failure_parity_ge_99pct':failure_parity>=.99,
      'reconstructed_reaccept_parity_ge_99pct':reaccept_parity>=.99,
      'at_least_one_feature_bh_q_le_0_10':any_q,
      'at_least_one_feature_abs_rbc_ge_0_30':any_effect,
      'at_least_one_full_aligned_feature':any_aligned,
      'aligned_feature_cluster_boot_ci_excludes_zero':boot_supported,
      'aligned_feature_same_direction_within_side':side_supported,
      'no_more_than_2_features_gt10pct_missing':missing_bad<=2,
      'august_not_used_for_selection':True,
    }
    score=sum(gates.values()); critical=['exact_lab032_extension050_pre_aug_ge_590','2025h2_n45_and_2026_n45','clock_ordering_ge_99pct','reconstructed_failure_parity_ge_99pct','reconstructed_reaccept_parity_ge_99pct','at_least_one_full_aligned_feature']
    if score>=9 and all(gates[k] for k in critical):verdict='PASS_SEQUENCE_LATENCY_REGIME_SPLIT_MECHANISM'
    elif all(gates[k] for k in critical[:5]) and any_q:verdict='WATCH_SEQUENCE_REGIME_SEPARATION_ALIGNMENT_INCOMPLETE'
    else:verdict='FAIL_NO_CAUSAL_SEQUENCE_REGIME_SPLIT'
    meta=dict(verdict=verdict,lineage_pre=len(pre),n_h25=len(h),n_26=len(y),clock_valid=clock_valid,failure_parity=failure_parity,reaccept_parity=reaccept_parity,
              h25_long=int((h.side==1).sum()),h25_short=int((h.side==-1).sum()),y26_long=int((y.side==1).sum()),y26_short=int((y.side==-1).sum()),aligned_features=aligned,missing_bad=missing_bad)
    def conv(o):
        if isinstance(o,np.bool_):return bool(o)
        if isinstance(o,np.integer):return int(o)
        if isinstance(o,np.floating):return float(o)
        raise TypeError
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,allow_nan=True,default=conv),encoding='utf-8')
    rep=report(ft,side,boots,gates,meta,yearly); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__':main()
