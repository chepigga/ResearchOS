#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

LAB='BTC_FLOW_LEVEL_PRETOUCH_VOLUME_PRICE_IMPACT_EFFICIENCY_AND_ABSORPTION_LAB_037'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC36=LABS/'BTC_FLOW_LEVEL_PREBREAK_VOLUME_IGNITION_VS_ABSORPTION_AND_OI_CONTINUATION_LAB_036'/'output'/'volume_activation_stream.csv'
SRC34=LABS/'BTC_FUTURES_RETAIL_CROWDING_X_SPOT_FLOW_DIVERGENCE_AND_OI_PROFITABILITY_MAP_LAB_034'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab034',SRC34); L34=importlib.util.module_from_spec(spec); spec.loader.exec_module(L34)
L34.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC'); AUG_END=pd.Timestamp('2026-09-01',tz='UTC')
SEED=20260908; BOOT_N=5000; BARS90=90*96; MINHIST=30*96
FEATURES=['fut_impact_eff_15','fut_impact_eff_30','fut_impact_eff_60','spot_impact_eff_15','spot_impact_eff_30','spot_impact_eff_60','fut_minus_spot_impact_60']
PRIMARY='fut_impact_eff_60'
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}


def load36():
    d=pd.read_csv(SRC36)
    for c in ['signal_time','touch_time','class_time']:
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','atr14','lab035_residual_atr']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d['high_volume']=d['high_volume'].astype(str).str.lower().isin(['true','1']) if d['high_volume'].dtype==object else d['high_volume'].astype(bool)
    return d.sort_values('signal_time').reset_index(drop=True)


def augment_impact(x,prefix):
    q=pd.to_numeric(x['quote'],errors='coerce')
    buy=pd.to_numeric(x['taker_buy_quote'],errors='coerce')
    sell=q-buy
    close=pd.to_numeric(x['close'],errors='coerce')
    for n,b in [(15,1),(30,2),(60,4)]:
        bs=buy.rolling(b,min_periods=b).sum().shift(1)
        ss=sell.rolling(b,min_periods=b).sum().shift(1)
        bm=bs.shift(1).rolling(BARS90,min_periods=MINHIST).median()
        sm=ss.shift(1).rolling(BARS90,min_periods=MINHIST).median()
        x[f'{prefix}_buy_norm_{n}']=bs/bm.replace(0,np.nan)
        x[f'{prefix}_sell_norm_{n}']=ss/sm.replace(0,np.nan)
        # Last fully closed pre-touch close versus the close before the frozen window.
        x[f'{prefix}_disp_px_{n}']=close.shift(1)-close.shift(b+1)
    return x


def build_events(d36,spot,fut):
    spot=augment_impact(spot.copy(),'spot'); fut=augment_impact(fut.copy(),'fut')
    rows=[]
    for r in d36.itertuples(index=False):
        if r.state not in ('ACCEPT','REJECT') or pd.isna(r.touch_time): continue
        t=pd.Timestamp(r.touch_time); side=int(r.side); atr=float(r.atr14)
        if t not in fut.index or t not in spot.index or not np.isfinite(atr) or atr<=0: continue
        fr=fut.loc[t]; sr=spot.loc[t]
        row=dict(flow_id=int(r.flow_id),signal_time=r.signal_time,touch_time=t,class_time=r.class_time,side=side,state=r.state,
                 activation_state=r.activation_state,high_volume=bool(r.high_volume),atr14=atr,
                 residual_atr=float(r.lab035_residual_atr) if np.isfinite(r.lab035_residual_atr) else np.nan)
        for prefix,z in [('fut',fr),('spot',sr)]:
            for n in [15,30,60]:
                disp=side*float(z.get(f'{prefix}_disp_px_{n}',np.nan))/atr
                norm=float(z.get(f'{prefix}_buy_norm_{n}',np.nan) if side>0 else z.get(f'{prefix}_sell_norm_{n}',np.nan))
                eff=disp/norm if np.isfinite(disp) and np.isfinite(norm) and norm>0 else np.nan
                row[f'{prefix}_disp_atr_{n}']=disp
                row[f'{prefix}_aligned_aggr_norm_{n}']=norm
                row[f'{prefix}_impact_eff_{n}']=eff
        a=row.get('fut_impact_eff_60',np.nan); b=row.get('spot_impact_eff_60',np.nan)
        row['fut_minus_spot_impact_60']=a-b if np.isfinite(a) and np.isfinite(b) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)


def bh(p):
    p=np.asarray(p,float); n=len(p); order=np.argsort(p); q=np.ones(n); run=1.0
    for j in range(n-1,-1,-1):
        i=order[j]; run=min(run,p[i]*n/(j+1)); q[i]=min(1.0,run)
    return q


def state_tests(d):
    q=d[(d.signal_time<PRE)&d.high_volume].copy(); rows=[]
    for feat in FEATURES:
        a=pd.to_numeric(q.loc[q.activation_state=='IGNITION',feat],errors='coerce').dropna().to_numpy(float)
        b=pd.to_numeric(q.loc[q.activation_state=='ABSORPTION',feat],errors='coerce').dropna().to_numpy(float)
        if len(a)>=3 and len(b)>=3:
            u,p=mannwhitneyu(a,b,alternative='two-sided'); rbc=2*float(u)/(len(a)*len(b))-1
        else: u=p=rbc=np.nan
        rows.append(dict(feature=feat,n_ign=len(a),n_abs=len(b),ign_median=float(np.median(a)) if len(a) else np.nan,abs_median=float(np.median(b)) if len(b) else np.nan,rbc=float(rbc) if np.isfinite(rbc) else np.nan,p=float(p) if np.isfinite(p) else np.nan))
    x=pd.DataFrame(rows); x['q_bh']=bh(x.p.fillna(1).to_numpy(float)); return x


def residual_tests(d):
    q=d[(d.signal_time<PRE)&(d.state=='ACCEPT')].copy(); rows=[]
    for feat in FEATURES:
        z=q[[feat,'residual_atr']].apply(pd.to_numeric,errors='coerce').dropna()
        if len(z)>=3:
            rho,p=spearmanr(z[feat],z.residual_atr); rho=float(rho); p=float(p)
        else: rho=p=np.nan
        rows.append(dict(feature=feat,n=len(z),rho=rho,p=p))
    x=pd.DataFrame(rows); x['q_bh']=bh(x.p.fillna(1).to_numpy(float)); return x


def bootstrap_half(d):
    q=d[(d.signal_time<PRE)&d.high_volume].dropna(subset=[PRIMARY,'residual_atr']).copy()
    med=float(q[PRIMARY].median()); q['impact_half']=np.where(q[PRIMARY]>med,'HIGH_IMPACT','LOW_IMPACT')
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    arr=[]
    for _,g in q.groupby('cluster'):
        a=g.loc[g.impact_half=='HIGH_IMPACT','residual_atr'].to_numpy(float); b=g.loc[g.impact_half=='LOW_IMPACT','residual_atr'].to_numpy(float)
        arr.append((a.sum(),len(a),b.sum(),len(b)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        z=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if z[1]>0 and z[3]>0: vals.append(float(z[0]/z[1]-z[2]/z[3]))
    v=np.asarray(vals,float)
    hi=q[q.impact_half=='HIGH_IMPACT']; lo=q[q.impact_half=='LOW_IMPACT']
    return dict(median=med,high_n=len(hi),low_n=len(lo),high_mean=float(hi.residual_atr.mean()),low_mean=float(lo.residual_atr.mean()),point=float(hi.residual_atr.mean()-lo.residual_atr.mean()),clusters=m,draws=len(v),ci_lo=float(np.quantile(v,.025)) if len(v) else np.nan,ci_hi=float(np.quantile(v,.975)) if len(v) else np.nan)


def transfer(d,med):
    rows=[]
    high=d[d.high_volume & (d[PRIMARY]>med)].copy()
    for w,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); q=high[(high.signal_time>=a)&(high.signal_time<b)]
        rr=pd.to_numeric(q.residual_atr,errors='coerce').dropna()
        rows.append(dict(window=w,n=len(q),resid_n=len(rr),residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,impact_median=float(q[PRIMARY].median()) if len(q) else np.nan,long_n=int((q.side==1).sum()),short_n=int((q.side==-1).sum())))
    for label,mask in [('LONG',high.side==1),('SHORT',high.side==-1)]:
        q=high[(high.signal_time<PRE)&mask]; rr=q.residual_atr.dropna(); rows.append(dict(window=label,n=len(q),resid_n=len(rr),residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,impact_median=float(q[PRIMARY].median()) if len(q) else np.nan,long_n=int((q.side==1).sum()),short_n=int((q.side==-1).sum())))
    q=high[(high.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(high.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(high.side==-1)]
    rr=q.residual_atr.dropna(); rows.append(dict(window='2022_SHORT',n=len(q),resid_n=len(rr),residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,impact_median=float(q[PRIMARY].median()) if len(q) else np.nan,long_n=0,short_n=len(q)))
    return pd.DataFrame(rows)


def py(x):
    if isinstance(x,(np.bool_,)): return bool(x)
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,)): return None if not np.isfinite(x) else float(x)
    if isinstance(x,pd.Timestamp): return x.isoformat()
    raise TypeError(type(x).__name__)


def report(meta,st,rt,bt,tr,gates):
    def f(x): return '—' if pd.isna(x) else f'{float(x):.3f}'
    L=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'', '## Coverage',
       f"- frozen HIGH_VOLUME pre-Aug: **{meta['high_n']}**; IGNITION **{meta['ign_n']}**, ABSORPTION **{meta['abs_n']}**",
       f"- futures primary impact coverage: **{meta['fut_cov']:.1%}**; spot primary impact coverage: **{meta['spot_cov']:.1%}**",'',
       '## HIGH_VOLUME ignition vs absorption impact','', '| Feature | Ign N | Abs N | Ign median | Abs median | RBC | p | BH q |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in st.iterrows(): L.append(f"| {r.feature} | {int(r.n_ign)} | {int(r.n_abs)} | {f(r.ign_median)} | {f(r.abs_median)} | {f(r.rbc)} | {f(r.p)} | {f(r.q_bh)} |")
    L+=['','## ACCEPT impact → post-classification residual','', '| Feature | N | rho | p | BH q |','|---|---:|---:|---:|---:|']
    for _,r in rt.iterrows(): L.append(f"| {r.feature} | {int(r.n)} | {f(r.rho)} | {f(r.p)} | {f(r.q_bh)} |")
    L+=['','## Primary median-half cluster audit',
        f"- frozen pre-Aug HIGH_VOLUME median `{PRIMARY}` = **{bt['median']:.4f}**",
        f"- HIGH impact N={bt['high_n']} residual **{bt['high_mean']:+.3f} ATR**; LOW impact N={bt['low_n']} residual **{bt['low_mean']:+.3f} ATR**",
        f"- difference **{bt['point']:+.3f} ATR**, 7d bootstrap 95% CI **[{bt['ci_lo']:+.3f}, {bt['ci_hi']:+.3f}]**, clusters={bt['clusters']}",'',
        '## High-impact HIGH_VOLUME transfer','', '| Slice | N | Residual | Hit | Impact median | L/S |','|---|---:|---:|---:|---:|---:|']
    for _,r in tr.iterrows(): L.append(f"| {r.window} | {int(r.n)} | {f(r.residual_mean)} | {f(r.hit)} | {f(r.impact_median)} | {int(r.long_n)}/{int(r.short_n)} |")
    L+=['','## Gates']
    for k,v in gates.items(): L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    L+=['','## Guardrail','Frozen LAB035–036 FLOW/level/touch/acceptance/high-volume lineage. All impact features exclude the touch bar and use only strictly prior rolling normalization. Median split is diagnostic-only and cannot be promoted without independent replication. No entry/SL/TP optimization. August 2026 audit-only. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')


def main():
    d36=load36(); spot=L34.download_klines('spot'); fut=L34.download_klines('futures')
    d=build_events(d36,spot,fut); d.to_csv(OUT/'impact_stream.csv',index=False)
    pre=d[d.signal_time<PRE]; high=pre[pre.high_volume]
    st=state_tests(d); rt=residual_tests(d); bt=bootstrap_half(d); tr=transfer(d,bt['median'])
    st.to_csv(OUT/'state_tests.csv',index=False); rt.to_csv(OUT/'residual_tests.csv',index=False); tr.to_csv(OUT/'transfer.csv',index=False)
    (OUT/'bootstrap.json').write_text(json.dumps(bt,indent=2,default=py),encoding='utf-8')
    pstate=st[st.feature==PRIMARY].iloc[0]; presid=rt[rt.feature==PRIMARY].iloc[0]
    fut_cov=float(high[PRIMARY].notna().mean()) if len(high) else 0; spot_cov=float(high['spot_impact_eff_60'].notna().mean()) if len(high) else 0
    def trow(name):
        z=tr[tr.window==name]; return z.iloc[0] if len(z) else None
    s22=trow('2022_SHORT'); recent=trow('POOLED_RECENT'); h2=trow('2025_H2'); y26=trow('2026_JAN_JUL')
    gates={
      'frozen_lab036_high_volume_ge_500':len(high)>=500,
      'futures_impact_coverage_ge_95pct':fut_cov>=.95,
      'spot_impact_coverage_ge_95pct':spot_cov>=.95,
      'ignition_ge_150_absorption_ge_100':int((high.activation_state=='IGNITION').sum())>=150 and int((high.activation_state=='ABSORPTION').sum())>=100,
      'primary_ignition_gt_absorption':bool(pstate.ign_median>pstate.abs_median),
      'primary_rbc_ge_0_10':bool(pstate.rbc>=.10),
      'primary_state_bh_q_le_0_10':bool(pstate.q_bh<=.10),
      'any_state_feature_bh_q_le_0_10':bool((st.q_bh<=.10).any()),
      'primary_accept_residual_rho_positive':bool(presid.rho>0),
      'primary_accept_residual_absrho_ge_0_05':bool(abs(presid.rho)>=.05),
      'primary_residual_bh_q_le_0_10':bool(presid.q_bh<=.10),
      'high_minus_low_residual_ge_0_15':bt['point']>=.15,
      'cluster_boot_ci_lower_gt_zero':bt['ci_lo']>0,
      'stress_2022_short_highimpact_positive_n20':bool(s22 is not None and s22.n>=20 and s22.residual_mean>0),
      'pooled_recent_highimpact_positive_n40':bool(recent is not None and recent.n>=40 and recent.residual_mean>0),
      'both_2025h2_2026_highimpact_positive':bool(h2 is not None and y26 is not None and h2.residual_mean>0 and y26.residual_mean>0),
      'august_not_used_for_selection':True}
    critical=['primary_ignition_gt_absorption','primary_state_bh_q_le_0_10','primary_accept_residual_rho_positive','cluster_boot_ci_lower_gt_zero','both_2025h2_2026_highimpact_positive']
    score=sum(gates.values())
    if score>=14 and all(gates[k] for k in critical): verdict='PASS_PRICE_IMPACT_ABSORPTION_MECHANISM'
    elif score>=9 or (gates['primary_ignition_gt_absorption'] and gates['primary_accept_residual_rho_positive']): verdict='WATCH_PRICE_IMPACT_DIRECTIONALLY_USEFUL_TRANSFER_INCOMPLETE'
    else: verdict='FAIL_NO_PRETOUCH_PRICE_IMPACT_QUALITY_EDGE'
    meta=dict(verdict=verdict,high_n=len(high),ign_n=int((high.activation_state=='IGNITION').sum()),abs_n=int((high.activation_state=='ABSORPTION').sum()),fut_cov=fut_cov,spot_cov=spot_cov,primary_state=pstate.to_dict(),primary_residual=presid.to_dict(),bootstrap=bt)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')
    report(meta,st,rt,bt,tr,gates)
    print(json.dumps({'verdict':verdict,'score':score,'gates':gates,'primary_state':pstate.to_dict(),'primary_residual':presid.to_dict(),'bootstrap':bt},indent=2,default=py))

if __name__=='__main__': main()
