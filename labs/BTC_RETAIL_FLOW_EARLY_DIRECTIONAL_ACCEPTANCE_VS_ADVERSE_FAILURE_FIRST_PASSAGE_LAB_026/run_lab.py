#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_EARLY_DIRECTIONAL_ACCEPTANCE_VS_ADVERSE_FAILURE_FIRST_PASSAGE_LAB_026'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC23=LABS/'BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab023',SRC23)
L23=importlib.util.module_from_spec(spec); spec.loader.exec_module(L23)
EXPECTED_FLOW_N=3209
THR_ATR=0.5
EXIT_BARS=48
HORIZONS={4:'1H',8:'2H',16:'4H'}
PRIMARY_BARS=8
SEED=20260907
BOOT_N=5000
UTC='UTC'
WINS={
 '2021':('2021-01-01','2022-01-01'),
 '2022':('2022-01-01','2023-01-01'),
 '2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),
 '2025_H1':('2025-01-01','2025-07-01'),
 '2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),
 'AUG2026_REUSED_AUDIT':('2026-08-01','2026-09-01'),
 'ALL_PRE_AUG':('2021-01-01','2026-08-01'),
 'POOLED_RECENT':('2025-07-01','2026-08-01'),
}

def tstat(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if len(a)<2:return np.nan
    s=a.std(ddof=1)
    return float(a.mean()/(s/math.sqrt(len(a)))) if s>0 else np.nan

def pf(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    p=float(a[a>0].sum()); n=float(-a[a<0].sum())
    if n==0:return np.inf if p>0 else np.nan
    return p/n

def passage_state(price,i,side,entry,atr,bars):
    fav=entry+side*THR_ATR*atr
    adv=entry-side*THR_ATR*atr
    for k in range(i+1,min(i+1+bars,len(price))):
        hi=float(price.high.iloc[k]); lo=float(price.low.iloc[k])
        fav_hit=(hi>=fav) if side>0 else (lo<=fav)
        adv_hit=(lo<=adv) if side>0 else (hi>=adv)
        if fav_hit and adv_hit:
            return 'AMBIGUOUS_SAME_BAR',k,np.nan
        if fav_hit:
            return 'ACCEPT_FIRST',k,fav
        if adv_hit:
            return 'ADVERSE_FIRST',k,adv
    return 'NONE',None,np.nan

def build(price,flow,bars,label):
    pos=pd.Series(np.arange(len(price),dtype=int),index=price.index)
    rows=[]
    for fid,r in flow.iterrows():
        t=pd.Timestamp(r.signal_time)
        if t not in pos.index:continue
        i=int(pos.loc[t])
        if i<14 or i+EXIT_BARS>=len(price):continue
        side=int(r.side); entry=float(price.close.iloc[i]); atr=float(price.atr14.iloc[i])
        if not np.isfinite(atr) or atr<=0:continue
        state,k,pass_px=passage_state(price,i,side,entry,atr,bars)
        end=i+EXIT_BARS; end_close=float(price.close.iloc[end])
        total=float(side*(end_close-entry)/atr)
        mae=0.0; mfe=0.0
        for j in range(i+1,end+1):
            hi=float(price.high.iloc[j]); lo=float(price.low.iloc[j])
            fav=max(0.0,hi-entry) if side>0 else max(0.0,entry-lo)
            adv=max(0.0,entry-lo) if side>0 else max(0.0,hi-entry)
            mfe=max(mfe,fav/atr); mae=max(mae,adv/atr)
        residual=np.nan; delay_h=np.nan; passage_time=pd.NaT
        if state in {'ACCEPT_FIRST','ADVERSE_FIRST'}:
            residual=float(side*(end_close-pass_px)/atr)
            delay_h=float((k-i)*0.25); passage_time=price.index[k]
        rows.append(dict(flow_id=int(fid),signal_time=t,side=side,horizon=label,state=state,signal_close=entry,atr14=atr,passage_time=passage_time,delay_h=delay_h,total12_atr=total,residual12_atr=residual,mae12_atr=float(mae),mfe12_atr=float(mfe),stop15_touch=bool(mae>=1.5),frozen_signed12_atr=float(r.signed12_atr)))
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)

def metrics(q):
    a=pd.to_numeric(q.residual12_atr,errors='coerce').dropna().to_numpy(float)
    tot=pd.to_numeric(q.total12_atr,errors='coerce').dropna().to_numpy(float)
    return dict(n=int(len(q)),resid_n=int(len(a)),mean_residual=float(a.mean()) if len(a) else np.nan,cum_residual=float(a.sum()) if len(a) else 0.0,t_residual=tstat(a),pf_residual=pf(a),mean_total=float(tot.mean()) if len(tot) else np.nan,t_total=tstat(tot),median_mae=float(q.mae12_atr.median()) if len(q) else np.nan,stop15_touch=float(q.stop15_touch.mean()) if len(q) else np.nan,median_delay_h=float(q.delay_h.median()) if len(q) and q.delay_h.notna().any() else np.nan,long_n=int((q.side==1).sum()) if len(q) else 0,short_n=int((q.side==-1).sum()) if len(q) else 0)

def horizon_summary(frames,pre_cut):
    rows=[]
    for label,d in frames.items():
        q=d[d.signal_time<pre_cut]
        base=float(q.total12_atr.mean()) if len(q) else np.nan
        for st in ['ACCEPT_FIRST','ADVERSE_FIRST','AMBIGUOUS_SAME_BAR','NONE']:
            g=q[q.state==st]; m=metrics(g); m.update(horizon=label,state=st,baseline_mean=base); rows.append(m)
    return pd.DataFrame(rows)

def window_summary(d):
    rows=[]
    for w,(a,b) in WINS.items():
        a=pd.Timestamp(a,tz=UTC); b=pd.Timestamp(b,tz=UTC); q=d[(d.signal_time>=a)&(d.signal_time<b)]
        for st in ['ACCEPT_FIRST','ADVERSE_FIRST','AMBIGUOUS_SAME_BAR','NONE']:
            g=q[q.state==st]; m=metrics(g); m.update(window=w,state=st); rows.append(m)
    return pd.DataFrame(rows)

def side_summary(d,pre_cut):
    q=d[d.signal_time<pre_cut]; rows=[]
    for side,name in [(1,'LONG'),(-1,'SHORT')]:
        z=q[q.side==side]
        for st in ['ACCEPT_FIRST','ADVERSE_FIRST']:
            g=z[z.state==st]; m=metrics(g); m.update(side_name=name,state=st); rows.append(m)
    return pd.DataFrame(rows)

def bootstrap_diff(d,pre_cut):
    q=d[(d.signal_time<pre_cut)&(d.state.isin(['ACCEPT_FIRST','ADVERSE_FIRST']))].copy()
    q['cluster']=(q.signal_time.astype('int64')//int(pd.Timedelta(days=7).value)).astype('int64')
    clusters=q.cluster.unique(); rng=np.random.default_rng(SEED); vals=[]
    for _ in range(BOOT_N):
        pick=rng.choice(clusters,size=len(clusters),replace=True)
        parts=[]
        for new_id,c in enumerate(pick):
            z=q[q.cluster==c].copy(); z['boot_id']=new_id; parts.append(z)
        z=pd.concat(parts,ignore_index=True) if parts else q.iloc[0:0]
        a=z.loc[z.state=='ACCEPT_FIRST','residual12_atr'].dropna(); b=z.loc[z.state=='ADVERSE_FIRST','residual12_atr'].dropna()
        if len(a) and len(b): vals.append(float(a.mean()-b.mean()))
    acc=q[q.state=='ACCEPT_FIRST'].residual12_atr.dropna(); adv=q[q.state=='ADVERSE_FIRST'].residual12_atr.dropna()
    point=float(acc.mean()-adv.mean()) if len(acc) and len(adv) else np.nan
    return dict(n_clusters=int(len(clusters)),draws=int(len(vals)),point_diff=point,ci_lo=float(np.quantile(vals,.025)) if vals else np.nan,ci_hi=float(np.quantile(vals,.975)) if vals else np.nan)

def getrow(tab,h,st):
    q=tab[(tab.horizon==h)&(tab.state==st)]; return q.iloc[0] if len(q) else None

def getwin(tab,w,st):
    q=tab[(tab.window==w)&(tab.state==st)]; return q.iloc[0] if len(q) else None

def report(hs,ws,ss,boot,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
      '## Frozen parity',f"- flow lineage: **{meta['flow_n']}**",f"- pre-Aug eligible: **{meta['pre_aug_n']}**",f"- timestamp parity: **{meta['timestamp_parity']:.2%}**",f"- payoff parity median abs error: **{meta['payoff_parity_mae']:.6f} ATR**",'',
      '## First-passage by fixed horizon (pre-Aug)','', '| Horizon | State | N | Residual EV | t(resid) | Total12 EV | MAE | Stop1.5 | Delay h |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in hs.iterrows():lines.append(f"| {r.horizon} | {r.state} | {int(r.n)} | {f(r.mean_residual)} | {f(r.t_residual)} | {f(r.mean_total)} | {f(r.median_mae)} | {f(r.stop15_touch)} | {f(r.median_delay_h)} |")
    lines += ['', '## Primary 2h by window','', '| Window | State | N | Residual EV | Total12 EV | t(resid) | MAE | L/S |','|---|---|---:|---:|---:|---:|---:|---:|']
    for _,r in ws.iterrows():
        if r.state not in {'ACCEPT_FIRST','ADVERSE_FIRST'}:continue
        lines.append(f"| {r.window} | {r.state} | {int(r.n)} | {f(r.mean_residual)} | {f(r.mean_total)} | {f(r.t_residual)} | {f(r.median_mae)} | {int(r.long_n)}/{int(r.short_n)} |")
    lines += ['', '## Primary 2h pre-Aug by side','', '| Side | State | N | Residual EV | Total12 EV | t(resid) |','|---|---|---:|---:|---:|---:|']
    for _,r in ss.iterrows():lines.append(f"| {r.side_name} | {r.state} | {int(r.n)} | {f(r.mean_residual)} | {f(r.mean_total)} | {f(r.t_residual)} |")
    lines += ['', '## 7d cluster bootstrap',f"- clusters: **{boot['n_clusters']}**, valid draws: **{boot['draws']}**",f"- ACCEPT minus ADVERSE residual: **{f(boot['point_diff'])} ATR**, 95% CI **[{f(boot['ci_lo'])}, {f(boot['ci_hi'])}]**",'', '## Gates']
    for k,v in gates.items():lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## Guardrail','Primary comparison uses residual return after the first-passage threshold, preventing the +0.5/-0.5 classification move from mechanically creating the result. Same-bar double hits are ambiguous and excluded. No threshold/horizon optimization. August 2026 is reused audit. Live allocation = **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price=L23.load_price(); flow=L23.load_flow()
    if len(flow)!=EXPECTED_FLOW_N:raise RuntimeError(f'flow lineage {len(flow)} != {EXPECTED_FLOW_N}')
    parity=float(flow.signal_time.isin(price.index).mean())
    if parity<.99:raise RuntimeError(f'timestamp parity {parity:.3%}')
    frames={}
    for bars,label in HORIZONS.items():
        d=build(price,flow,bars,label); d.to_csv(OUT/f'first_passage_{label.lower()}.csv',index=False); frames[label]=d
    primary=frames['2H']; pre_cut=pd.Timestamp('2026-08-01',tz=UTC); pre=primary[primary.signal_time<pre_cut]
    payoff_parity=float(np.median(np.abs(primary.total12_atr-primary.frozen_signed12_atr)))
    if not np.isfinite(payoff_parity) or payoff_parity>.02:raise RuntimeError(f'payoff parity failed {payoff_parity}')
    hs=horizon_summary(frames,pre_cut); hs.to_csv(OUT/'horizon_summary.csv',index=False)
    ws=window_summary(primary); ws.to_csv(OUT/'primary_2h_by_window.csv',index=False)
    ss=side_summary(primary,pre_cut); ss.to_csv(OUT/'primary_2h_by_side.csv',index=False)
    boot=bootstrap_diff(primary,pre_cut); (OUT/'bootstrap_7d.json').write_text(json.dumps(boot,indent=2,allow_nan=True))
    a2=getrow(hs,'2H','ACCEPT_FIRST'); d2=getrow(hs,'2H','ADVERSE_FIRST'); amb2=getrow(hs,'2H','AMBIGUOUS_SAME_BAR')
    a1=getrow(hs,'1H','ACCEPT_FIRST'); d1=getrow(hs,'1H','ADVERSE_FIRST'); a4=getrow(hs,'4H','ACCEPT_FIRST'); d4=getrow(hs,'4H','ADVERSE_FIRST')
    baseline=float(pre.total12_atr.mean())
    y22=primary[(primary.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(primary.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(primary.side==-1)]
    y22a=metrics(y22[y22.state=='ACCEPT_FIRST']); y22d=metrics(y22[y22.state=='ADVERSE_FIRST'])
    rec=primary[(primary.signal_time>=pd.Timestamp('2025-07-01',tz=UTC))&(primary.signal_time<pre_cut)]
    reca=metrics(rec[rec.state=='ACCEPT_FIRST']); recd=metrics(rec[rec.state=='ADVERSE_FIRST'])
    amb_frac=float(amb2.n/len(pre)) if len(pre) else np.nan
    diff=float(a2.mean_residual-d2.mean_residual)
    gates={
      'lineage_3209_and_timestamp_parity':bool(len(flow)==3209 and parity>=.99),
      'eligible_pre_aug_ge_3000':bool(len(pre)>=3000),
      'primary_ambiguous_fraction_le_20pct':bool(amb_frac<=.20),
      'primary_accept_n_ge_400':bool(a2.n>=400),
      'primary_adverse_n_ge_400':bool(d2.n>=400),
      'primary_accept_residual_positive':bool(a2.mean_residual>0),
      'primary_adverse_residual_nonpositive':bool(d2.mean_residual<=0),
      'primary_residual_diff_ge_0_25atr':bool(diff>=.25),
      'bootstrap_residual_diff_ci_lower_gt_zero':bool(boot['ci_lo']>0),
      'primary_accept_total_gt_baseline':bool(a2.mean_total>baseline),
      'sensitivity_1h_accept_resid_gt_adverse':bool(a1.mean_residual>d1.mean_residual),
      'sensitivity_4h_accept_resid_gt_adverse':bool(a4.mean_residual>d4.mean_residual),
      'stress_2022_short_each_n30_accept_gt_adverse':bool(y22a['n']>=30 and y22d['n']>=30 and y22a['mean_residual']>y22d['mean_residual']),
      'recent_accept_resid_gt_adverse':bool(reca['n']>0 and recd['n']>0 and reca['mean_residual']>recd['mean_residual']),
    }
    score=sum(gates.values()); critical=['lineage_3209_and_timestamp_parity','primary_accept_n_ge_400','primary_adverse_n_ge_400','primary_accept_residual_positive','primary_residual_diff_ge_0_25atr','bootstrap_residual_diff_ci_lower_gt_zero','stress_2022_short_each_n30_accept_gt_adverse','recent_accept_resid_gt_adverse']
    if score>=11 and all(gates[k] for k in critical):verdict='PASS_EARLY_ACCEPTANCE_RESIDUAL_DISCRIMINATOR'
    elif score>=8 and diff>0 and a2.mean_residual>0:verdict='WATCH_ACCEPTANCE_SEPARATION_PARTIAL'
    else:verdict='FAIL_NO_EARLY_ACCEPTANCE_RESIDUAL_EDGE'
    meta=dict(verdict=verdict,flow_n=len(flow),pre_aug_n=len(pre),timestamp_parity=parity,payoff_parity_mae=payoff_parity,primary_horizon='2H',threshold_atr=THR_ATR,ambiguous_fraction=amb_frac,baseline_total12_mean=baseline,primary_residual_diff=diff,aug_reused_audit=True)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates,'2022_short_accept':y22a,'2022_short_adverse':y22d,'recent_accept':reca,'recent_adverse':recd},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(hs,ws,ss,boot,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__': main()
