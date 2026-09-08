#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

LAB='BTC_FLOW_LEVEL_PRETOUCH_NET_TAKER_DELTA_PRICE_RESPONSE_AND_CVD_ABSORPTION_LAB_038'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC37=LABS/'BTC_FLOW_LEVEL_PRETOUCH_VOLUME_PRICE_IMPACT_EFFICIENCY_AND_ABSORPTION_LAB_037'/'output'/'impact_stream.csv'
SRC34=LABS/'BTC_FUTURES_RETAIL_CROWDING_X_SPOT_FLOW_DIVERGENCE_AND_OI_PROFITABILITY_MAP_LAB_034'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab034',SRC34); L34=importlib.util.module_from_spec(spec); spec.loader.exec_module(L34)
L34.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC'); SEED=20260908; BOOT_N=5000; BARS90=90*96; MINHIST=30*96
FEATURES=['fut_netdelta_norm_15','fut_netdelta_norm_30','fut_netdelta_norm_60','spot_netdelta_norm_15','spot_netdelta_norm_30','spot_netdelta_norm_60','fut_response_eff_60','spot_response_eff_60','fut_absorption_gap_60','spot_absorption_gap_60','fut_minus_spot_netdelta_60','fut_minus_spot_absorption_gap_60']
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}


def load37():
    d=pd.read_csv(SRC37)
    for c in ['signal_time','touch_time','class_time']:
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','atr14','residual_atr']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    if d['high_volume'].dtype==object:
        d['high_volume']=d.high_volume.astype(str).str.lower().isin(['true','1'])
    else: d['high_volume']=d.high_volume.astype(bool)
    return d.sort_values('signal_time').reset_index(drop=True)


def augment(x,prefix):
    q=pd.to_numeric(x.quote,errors='coerce'); buy=pd.to_numeric(x.taker_buy_quote,errors='coerce'); close=pd.to_numeric(x.close,errors='coerce')
    delta=2*buy-q
    for n,b in [(15,1),(30,2),(60,4)]:
        ds=delta.rolling(b,min_periods=b).sum().shift(1)
        medabs=ds.abs().shift(1).rolling(BARS90,min_periods=MINHIST).median()
        x[f'{prefix}_netdelta_raw_{n}']=ds
        x[f'{prefix}_netdelta_medabs_{n}']=medabs
        x[f'{prefix}_disp_px_{n}']=close.shift(1)-close.shift(b+1)
    return x


def build(d37,spot,fut):
    spot=augment(spot.copy(),'spot'); fut=augment(fut.copy(),'fut'); rows=[]
    for r in d37.itertuples(index=False):
        if r.state not in ('ACCEPT','REJECT') or pd.isna(r.touch_time): continue
        t=pd.Timestamp(r.touch_time); side=int(r.side); atr=float(r.atr14)
        if t not in fut.index or t not in spot.index or not np.isfinite(atr) or atr<=0: continue
        row=dict(flow_id=int(r.flow_id),signal_time=r.signal_time,touch_time=t,class_time=r.class_time,side=side,state=r.state,activation_state=r.activation_state,high_volume=bool(r.high_volume),atr14=atr,residual_atr=float(r.residual_atr) if np.isfinite(r.residual_atr) else np.nan)
        for prefix,z in [('fut',fut.loc[t]),('spot',spot.loc[t])]:
            for n in [15,30,60]:
                raw=float(z.get(f'{prefix}_netdelta_raw_{n}',np.nan)); med=float(z.get(f'{prefix}_netdelta_medabs_{n}',np.nan)); disp=side*float(z.get(f'{prefix}_disp_px_{n}',np.nan))/atr
                norm=side*raw/med if np.isfinite(raw) and np.isfinite(med) and med>0 else np.nan
                eff=disp/max(abs(norm),0.25) if np.isfinite(disp) and np.isfinite(norm) else np.nan
                gap=norm-disp if np.isfinite(norm) and np.isfinite(disp) else np.nan
                row[f'{prefix}_netdelta_norm_{n}']=norm; row[f'{prefix}_disp_atr_{n}']=disp; row[f'{prefix}_response_eff_{n}']=eff; row[f'{prefix}_absorption_gap_{n}']=gap
        a=row.get('fut_netdelta_norm_60',np.nan); b=row.get('spot_netdelta_norm_60',np.nan)
        row['fut_minus_spot_netdelta_60']=a-b if np.isfinite(a) and np.isfinite(b) else np.nan
        a=row.get('fut_absorption_gap_60',np.nan); b=row.get('spot_absorption_gap_60',np.nan)
        row['fut_minus_spot_absorption_gap_60']=a-b if np.isfinite(a) and np.isfinite(b) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)


def bh(p):
    p=np.asarray(p,float); n=len(p); order=np.argsort(p); q=np.ones(n); run=1.0
    for j in range(n-1,-1,-1):
        i=order[j]; run=min(run,p[i]*n/(j+1)); q[i]=min(1.0,run)
    return q


def state_tests(d):
    q=d[(d.signal_time<PRE)&d.high_volume]; rows=[]
    for feat in FEATURES:
        a=pd.to_numeric(q.loc[q.activation_state=='IGNITION',feat],errors='coerce').dropna().to_numpy(float)
        b=pd.to_numeric(q.loc[q.activation_state=='ABSORPTION',feat],errors='coerce').dropna().to_numpy(float)
        if len(a)>=3 and len(b)>=3:
            u,p=mannwhitneyu(a,b,alternative='two-sided'); rbc=2*float(u)/(len(a)*len(b))-1
        else: p=rbc=np.nan
        rows.append(dict(feature=feat,n_ign=len(a),n_abs=len(b),ign_median=float(np.median(a)) if len(a) else np.nan,abs_median=float(np.median(b)) if len(b) else np.nan,rbc=float(rbc) if np.isfinite(rbc) else np.nan,p=float(p) if np.isfinite(p) else np.nan))
    x=pd.DataFrame(rows); x['q_bh']=bh(x.p.fillna(1).to_numpy(float)); return x


def residual_tests(d):
    q=d[(d.signal_time<PRE)&(d.state=='ACCEPT')]; rows=[]
    for feat in FEATURES:
        z=q[[feat,'residual_atr']].apply(pd.to_numeric,errors='coerce').dropna()
        if len(z)>=3:
            rho,p=spearmanr(z[feat],z.residual_atr); rho=float(rho); p=float(p)
        else: rho=p=np.nan
        rows.append(dict(feature=feat,n=len(z),rho=rho,p=p))
    x=pd.DataFrame(rows); x['q_bh']=bh(x.p.fillna(1).to_numpy(float)); return x


def assign_cells(d):
    pre=d[(d.signal_time<PRE)&d.high_volume].dropna(subset=['fut_netdelta_norm_60','fut_disp_atr_60']).copy()
    pm=float(pre.fut_netdelta_norm_60.median()); rm=float(pre.fut_disp_atr_60.median())
    def lab(q):
        hp=q.fut_netdelta_norm_60>pm; hr=q.fut_disp_atr_60>rm
        return np.select([hp&hr,hp&~hr,~hp&hr],["EFFICIENT_IGNITION","ABSORPTION","THIN_LIQUIDITY"],default="WEAK")
    z=d.copy(); z['mechanism_cell']=lab(z); return z,pm,rm


def cell_summary(d):
    q=d[(d.signal_time<PRE)&d.high_volume]; rows=[]
    for c in ['EFFICIENT_IGNITION','ABSORPTION','THIN_LIQUIDITY','WEAK']:
        z=q[q.mechanism_cell==c]; rr=z.residual_atr.dropna();
        rows.append(dict(cell=c,n=len(z),accept_n=int((z.state=='ACCEPT').sum()),accept_rate=float((z.state=='ACCEPT').mean()) if len(z) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,residual_hit=float((rr>0).mean()) if len(rr) else np.nan,netdelta=float(z.fut_netdelta_norm_60.mean()) if len(z) else np.nan,response=float(z.fut_disp_atr_60.mean()) if len(z) else np.nan,abs_gap=float(z.fut_absorption_gap_60.mean()) if len(z) else np.nan))
    return pd.DataFrame(rows)


def bootstrap_cells(d):
    q=d[(d.signal_time<PRE)&d.high_volume&d.mechanism_cell.isin(['EFFICIENT_IGNITION','ABSORPTION'])].copy(); q=q.dropna(subset=['residual_atr'])
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    arr=[]
    for _,g in q.groupby('cluster'):
        e=g[g.mechanism_cell=='EFFICIENT_IGNITION']; a=g[g.mechanism_cell=='ABSORPTION']
        arr.append((int((e.state=='ACCEPT').sum()),len(e),int((a.state=='ACCEPT').sum()),len(a),e.residual_atr.sum(),len(e),a.residual_atr.sum(),len(a)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); rate=[]; resid=[]; m=len(arr)
    for _ in range(BOOT_N):
        z=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if z[1]>0 and z[3]>0: rate.append(z[0]/z[1]-z[2]/z[3])
        if z[5]>0 and z[7]>0: resid.append(z[4]/z[5]-z[6]/z[7])
    e=q[q.mechanism_cell=='EFFICIENT_IGNITION']; a=q[q.mechanism_cell=='ABSORPTION']; vr=np.asarray(rate,float); vv=np.asarray(resid,float)
    return dict(clusters=m,draws_rate=len(vr),draws_resid=len(vv),rate_point=float((e.state=='ACCEPT').mean()-(a.state=='ACCEPT').mean()),rate_ci_lo=float(np.quantile(vr,.025)),rate_ci_hi=float(np.quantile(vr,.975)),resid_point=float(e.residual_atr.mean()-a.residual_atr.mean()),resid_ci_lo=float(np.quantile(vv,.025)),resid_ci_hi=float(np.quantile(vv,.975)))


def transfer(d):
    q=d[d.high_volume & (d.mechanism_cell=='EFFICIENT_IGNITION')]; rows=[]
    for w,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); z=q[(q.signal_time>=a)&(q.signal_time<b)]; rr=z.residual_atr.dropna()
        rows.append(dict(window=w,n=len(z),accept_rate=float((z.state=='ACCEPT').mean()) if len(z) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,long_n=int((z.side==1).sum()),short_n=int((z.side==-1).sum())))
    for label,mask in [('LONG',q.side==1),('SHORT',q.side==-1)]:
        z=q[(q.signal_time<PRE)&mask]; rr=z.residual_atr.dropna(); rows.append(dict(window=label,n=len(z),accept_rate=float((z.state=='ACCEPT').mean()) if len(z) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,long_n=int((z.side==1).sum()),short_n=int((z.side==-1).sum())))
    z=q[(q.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(q.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(q.side==-1)]; rr=z.residual_atr.dropna(); rows.append(dict(window='2022_SHORT',n=len(z),accept_rate=float((z.state=='ACCEPT').mean()) if len(z) else np.nan,residual_mean=float(rr.mean()) if len(rr) else np.nan,hit=float((rr>0).mean()) if len(rr) else np.nan,long_n=0,short_n=len(z)))
    return pd.DataFrame(rows)


def py(x):
    if isinstance(x,(np.bool_,)): return bool(x)
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,)): return None if not np.isfinite(x) else float(x)
    if isinstance(x,pd.Timestamp): return x.isoformat()
    raise TypeError(type(x).__name__)


def report(meta,st,rt,cs,bt,tr,gates):
    def f(x): return '—' if pd.isna(x) else f'{float(x):.3f}'
    L=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'', '## Coverage',f"- frozen HIGH_VOLUME pre-Aug: **{meta['high_n']}**; IGNITION **{meta['ign_n']}**, ABSORPTION **{meta['abs_n']}**",f"- futures/spot primary coverage: **{meta['fut_cov']:.1%} / {meta['spot_cov']:.1%}**",f"- 2x2 frozen medians: net pressure **{meta['pressure_median']:.3f}**, directional response **{meta['response_median']:.3f} ATR**",'', '## HIGH_VOLUME state discrimination','', '| Feature | Ign N | Abs N | Ign med | Abs med | RBC | p | BH q |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in st.iterrows(): L.append(f"| {r.feature} | {int(r.n_ign)} | {int(r.n_abs)} | {f(r.ign_median)} | {f(r.abs_median)} | {f(r.rbc)} | {f(r.p)} | {f(r.q_bh)} |")
    L+=['','## ACCEPT feature → residual','', '| Feature | N | rho | p | BH q |','|---|---:|---:|---:|---:|']
    for _,r in rt.iterrows(): L.append(f"| {r.feature} | {int(r.n)} | {f(r.rho)} | {f(r.p)} | {f(r.q_bh)} |")
    L+=['','## Fixed 2x2 pressure × response map','', '| Cell | N | Accept rate | Residual | Hit | Net Δ norm | Response ATR | Abs gap |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in cs.iterrows(): L.append(f"| {r.cell} | {int(r.n)} | {f(r.accept_rate)} | {f(r.residual_mean)} | {f(r.residual_hit)} | {f(r.netdelta)} | {f(r.response)} | {f(r.abs_gap)} |")
    L+=['','## 7d cluster bootstrap',f"- EFFICIENT_IGNITION − ABSORPTION ACCEPT-rate: **{bt['rate_point']:+.3f}**, 95% CI **[{bt['rate_ci_lo']:+.3f}, {bt['rate_ci_hi']:+.3f}]**",f"- residual difference: **{bt['resid_point']:+.3f} ATR**, 95% CI **[{bt['resid_ci_lo']:+.3f}, {bt['resid_ci_hi']:+.3f}]**, clusters={bt['clusters']}",'','## Efficient-ignition transfer','', '| Slice | N | Accept | Residual | Hit | L/S |','|---|---:|---:|---:|---:|---:|']
    for _,r in tr.iterrows(): L.append(f"| {r.window} | {int(r.n)} | {f(r.accept_rate)} | {f(r.residual_mean)} | {f(r.hit)} | {int(r.long_n)}/{int(r.short_n)} |")
    L+=['','## Gates']
    for k,v in gates.items(): L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    L+=['','## Guardrail','Frozen FLOW/LEVEL/TOUCH/HIGH_VOLUME lineage from LAB035–037. Touch bar excluded. Net-delta normalization uses strictly prior 90d history. 2x2 median map is diagnostic-only. No entry/SL/TP optimization. August audit-only. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')


def main():
    d37=load37(); spot=L34.download_klines('spot'); fut=L34.download_klines('futures'); d=build(d37,spot,fut); d,pm,rm=assign_cells(d); d.to_csv(OUT/'cvd_absorption_stream.csv',index=False)
    pre=d[d.signal_time<PRE]; high=pre[pre.high_volume]; st=state_tests(d); rt=residual_tests(d); cs=cell_summary(d); bt=bootstrap_cells(d); tr=transfer(d)
    st.to_csv(OUT/'state_tests.csv',index=False); rt.to_csv(OUT/'residual_tests.csv',index=False); cs.to_csv(OUT/'mechanism_map.csv',index=False); tr.to_csv(OUT/'transfer.csv',index=False); (OUT/'bootstrap.json').write_text(json.dumps(bt,indent=2,default=py),encoding='utf-8')
    resp=st[st.feature=='fut_response_eff_60'].iloc[0]; gap=st[st.feature=='fut_absorption_gap_60'].iloc[0]; rresp=rt[rt.feature=='fut_response_eff_60'].iloc[0]; rgap=rt[rt.feature=='fut_absorption_gap_60'].iloc[0]
    fut_cov=float(high.fut_netdelta_norm_60.notna().mean()) if len(high) else 0; spot_cov=float(high.spot_netdelta_norm_60.notna().mean()) if len(high) else 0
    def row(name): z=tr[tr.window==name]; return z.iloc[0] if len(z) else None
    s22=row('2022_SHORT'); rec=row('POOLED_RECENT'); h2=row('2025_H2'); y26=row('2026_JAN_JUL')
    ec=cs[cs.cell=='EFFICIENT_IGNITION'].iloc[0]; ac=cs[cs.cell=='ABSORPTION'].iloc[0]
    gates={
      'frozen_high_volume_ge_500':len(high)>=500,
      'futures_netdelta_coverage_ge_95pct':fut_cov>=.95,
      'spot_netdelta_coverage_ge_95pct':spot_cov>=.95,
      'ignition_ge_150_absorption_ge_100':int((high.activation_state=='IGNITION').sum())>=150 and int((high.activation_state=='ABSORPTION').sum())>=100,
      'response_eff_ignition_gt_absorption':bool(resp.ign_median>resp.abs_median),
      'response_eff_rbc_ge_0_10':bool(resp.rbc>=.10),
      'response_eff_bh_q_le_0_10':bool(resp.q_bh<=.10),
      'absorption_gap_absorption_gt_ignition':bool(gap.abs_median>gap.ign_median),
      'absorption_gap_state_bh_q_le_0_10':bool(gap.q_bh<=.10),
      'any_state_feature_bh_q_le_0_10':bool((st.q_bh<=.10).any()),
      'accept_residual_rho_response_positive':bool(rresp.rho>0),
      'accept_residual_rho_gap_negative':bool(rgap.rho<0),
      'any_residual_feature_bh_q_le_0_10':bool((rt.q_bh<=.10).any()),
      'efficient_accept_rate_beats_absorption_0_05':bool(ec.accept_rate-ac.accept_rate>=.05),
      'efficient_residual_beats_absorption_0_20':bool(ec.residual_mean-ac.residual_mean>=.20),
      'cluster_accept_rate_ci_lower_gt_zero':bt['rate_ci_lo']>0,
      'cluster_residual_ci_lower_gt_zero':bt['resid_ci_lo']>0,
      'stress_2022_short_efficient_positive_n20':bool(s22 is not None and s22.n>=20 and s22.residual_mean>0),
      'pooled_recent_efficient_positive_n40':bool(rec is not None and rec.n>=40 and rec.residual_mean>0),
      'both_2025h2_2026_efficient_positive':bool(h2 is not None and y26 is not None and h2.residual_mean>0 and y26.residual_mean>0),
      'august_not_used_for_selection':True}
    critical=['response_eff_ignition_gt_absorption','response_eff_bh_q_le_0_10','absorption_gap_absorption_gt_ignition','absorption_gap_state_bh_q_le_0_10','cluster_accept_rate_ci_lower_gt_zero','cluster_residual_ci_lower_gt_zero','both_2025h2_2026_efficient_positive']
    score=sum(gates.values())
    if score>=17 and all(gates[k] for k in critical): verdict='PASS_NET_TAKER_DELTA_CVD_ABSORPTION_MECHANISM'
    elif score>=11 or (gates['response_eff_ignition_gt_absorption'] and gates['absorption_gap_absorption_gt_ignition']): verdict='WATCH_NET_TAKER_DELTA_ABSORPTION_PARTIAL'
    else: verdict='FAIL_NO_NET_TAKER_DELTA_ABSORPTION_EDGE'
    meta=dict(verdict=verdict,high_n=len(high),ign_n=int((high.activation_state=='IGNITION').sum()),abs_n=int((high.activation_state=='ABSORPTION').sum()),fut_cov=fut_cov,spot_cov=spot_cov,pressure_median=pm,response_median=rm,bootstrap=bt)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8'); report(meta,st,rt,cs,bt,tr,gates)
    print(json.dumps({'verdict':verdict,'score':score,'gates':gates,'bootstrap':bt},indent=2,default=py))

if __name__=='__main__': main()
