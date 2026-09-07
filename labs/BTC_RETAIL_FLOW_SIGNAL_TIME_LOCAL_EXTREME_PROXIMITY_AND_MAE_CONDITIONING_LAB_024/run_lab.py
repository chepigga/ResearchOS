#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_SIGNAL_TIME_LOCAL_EXTREME_PROXIMITY_AND_MAE_CONDITIONING_LAB_024'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC23=LABS/'BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab023',SRC23)
L23=importlib.util.module_from_spec(spec); spec.loader.exec_module(L23)
EXPECTED_FLOW_N=3209
SEED=20260907
BOOT_N=5000
HORIZONS={4:'1H',8:'2H',16:'4H'}
EXIT_BARS=48
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
    sd=a.std(ddof=1)
    return float(a.mean()/(sd/math.sqrt(len(a)))) if sd>0 else np.nan

def payoff_ratio(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    pos=float(a[a>0].sum()); neg=float(-a[a<0].sum())
    if neg==0:return np.inf if pos>0 else np.nan
    return pos/neg

def spearman(x,y):
    q=pd.DataFrame({'x':pd.to_numeric(x,errors='coerce'),'y':pd.to_numeric(y,errors='coerce')}).dropna()
    if len(q)<3:return np.nan
    return float(q.x.rank(method='average').corr(q.y.rank(method='average')))

def sweep_at(price,j,side):
    if j<4:return False
    if side>0:
        lvl=float(price.low.iloc[j-4:j].min())
        return bool(float(price.low.iloc[j])<lvl and float(price.close.iloc[j])>lvl)
    lvl=float(price.high.iloc[j-4:j].max())
    return bool(float(price.high.iloc[j])>lvl and float(price.close.iloc[j])<lvl)

def build_features(price,flow):
    pos=pd.Series(np.arange(len(price),dtype=int),index=price.index)
    rows=[]; missing=0
    for fid,r in flow.iterrows():
        t=pd.Timestamp(r.signal_time)
        if t not in pos.index:
            missing+=1; continue
        i=int(pos.loc[t])
        if i<16 or i+EXIT_BARS>=len(price):continue
        atr=float(price.atr14.iloc[i]); cl=float(price.close.iloc[i]); side=int(r.side)
        if not np.isfinite(atr) or atr<=0:continue
        d={'flow_id':int(fid),'signal_time':t,'side':side,'frozen_signed12_atr':float(r.signed12_atr),'signal_close':cl,'atr14':atr}
        for h,name in HORIZONS.items():
            if side>0:
                lvl=float(price.low.iloc[i-h:i].min()); dist=(cl-lvl)/atr
            else:
                lvl=float(price.high.iloc[i-h:i].max()); dist=(lvl-cl)/atr
            d[f'prior_{name}_level']=lvl; d[f'dist_{name}_atr']=float(dist)
        d['signal_bar_sweep']=bool(sweep_at(price,i,side))
        d['recent_sweep_1to4']=bool(any(sweep_at(price,j,side) for j in range(max(4,i-3),i+1)))
        end=i+EXIT_BARS; end_close=float(price.close.iloc[end])
        signed=float(side*(end_close-cl)/atr)
        mae=0.0; mfe=0.0
        for k in range(i+1,end+1):
            hi=float(price.high.iloc[k]); lo=float(price.low.iloc[k])
            fav=max(0.0,hi-cl) if side>0 else max(0.0,cl-lo)
            adv=max(0.0,cl-lo) if side>0 else max(0.0,hi-cl)
            mfe=max(mfe,fav/atr); mae=max(mae,adv/atr)
        d.update(signed12_atr=signed,mae12_atr=float(mae),mfe12_atr=float(mfe),stop15_touch=bool(mae>=1.5))
        rows.append(d)
    z=pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)
    return z,missing

def bin_name(v):
    if v<=.25:return '<=0.25'
    if v<=.50:return '0.25-0.50'
    if v<=1.00:return '0.50-1.00'
    if v<=2.00:return '1.00-2.00'
    return '>2.00'

def metric(q):
    a=q.signed12_atr.to_numpy(float) if len(q) else np.array([])
    return dict(n=len(q),mean_signed12_atr=float(np.mean(a)) if len(a) else np.nan,cum_signed12_atr=float(np.sum(a)) if len(a) else 0.0,t=tstat(a),payoff_ratio=payoff_ratio(a),hit_rate=float(np.mean(a>0)) if len(a) else np.nan,median_mae_atr=float(q.mae12_atr.median()) if len(q) else np.nan,mean_mae_atr=float(q.mae12_atr.mean()) if len(q) else np.nan,median_mfe_atr=float(q.mfe12_atr.median()) if len(q) else np.nan,stop15_touch_rate=float(q.stop15_touch.mean()) if len(q) else np.nan)

def bin_table(z):
    rows=[]
    for h,name in HORIZONS.items():
        col=f'dist_{name}_atr'
        q=z.copy(); q['bin']=q[col].map(bin_name)
        for b in ['<=0.25','0.25-0.50','0.50-1.00','1.00-2.00','>2.00']:
            g=q[q.bin==b]; m=metric(g); m.update(horizon=name,bin=b); rows.append(m)
    return pd.DataFrame(rows)

def corr_table(z):
    rows=[]
    slices={'ALL_PRE_AUG':z[z.signal_time<pd.Timestamp('2026-08-01',tz=UTC)],
            'POOLED_RECENT':z[(z.signal_time>=pd.Timestamp('2025-07-01',tz=UTC))&(z.signal_time<pd.Timestamp('2026-08-01',tz=UTC))],
            'LONG_PRE_AUG':z[(z.signal_time<pd.Timestamp('2026-08-01',tz=UTC))&(z.side==1)],
            'SHORT_PRE_AUG':z[(z.signal_time<pd.Timestamp('2026-08-01',tz=UTC))&(z.side==-1)],
            '2022_SHORT':z[(z.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(z.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(z.side==-1)]}
    for sname,q in slices.items():
        for _,name in HORIZONS.items():
            c=f'dist_{name}_atr'; rows.append(dict(slice=sname,horizon=name,n=len(q),rho_return=spearman(q[c],q.signed12_atr),rho_mae=spearman(q[c],q.mae12_atr)))
    return pd.DataFrame(rows)

def near_far_table(z):
    rows=[]
    for w,(a,b) in WINS.items():
        a=pd.Timestamp(a,tz=UTC); b=pd.Timestamp(b,tz=UTC); q=z[(z.signal_time>=a)&(z.signal_time<b)].copy()
        groups={'ALL':q,'NEAR4H':q[q.dist_4H_atr<=.50],'FAR4H':q[q.dist_4H_atr>=1.50],'SWEEP1TO4':q[q.recent_sweep_1to4]}
        for name,g in groups.items():
            m=metric(g); m.update(window=w,group=name,long_n=int((g.side==1).sum()) if len(g) else 0,short_n=int((g.side==-1).sum()) if len(g) else 0); rows.append(m)
    return pd.DataFrame(rows)

def side_near(z):
    rows=[]; pre=z[z.signal_time<pd.Timestamp('2026-08-01',tz=UTC)]
    for side,name in [(1,'LONG'),(-1,'SHORT')]:
        q=pre[(pre.side==side)&(pre.dist_4H_atr<=.50)]; m=metric(q); m.update(side=name); rows.append(m)
    return pd.DataFrame(rows)

def bootstrap_near_far(z):
    pre=z[z.signal_time<pd.Timestamp('2026-08-01',tz=UTC)]
    near=pre[pre.dist_4H_atr<=.50]; far=pre[pre.dist_4H_atr>=1.50]
    rng=np.random.default_rng(SEED); ev=[]; mae=[]
    if len(near)==0 or len(far)==0:return dict(near_n=len(near),far_n=len(far),ev_diff=np.nan,ev_ci_lo=np.nan,ev_ci_hi=np.nan,mae_diff=np.nan,mae_ci_lo=np.nan,mae_ci_hi=np.nan)
    na=near.signed12_atr.to_numpy(float); fa=far.signed12_atr.to_numpy(float); nm=near.mae12_atr.to_numpy(float); fm=far.mae12_atr.to_numpy(float)
    for _ in range(BOOT_N):
        ni=rng.integers(0,len(na),len(na)); fi=rng.integers(0,len(fa),len(fa))
        ev.append(float(na[ni].mean()-fa[fi].mean())); mae.append(float(nm[ni].mean()-fm[fi].mean()))
    return dict(near_n=len(near),far_n=len(far),ev_diff=float(na.mean()-fa.mean()),ev_ci_lo=float(np.quantile(ev,.025)),ev_ci_hi=float(np.quantile(ev,.975)),mae_diff=float(nm.mean()-fm.mean()),mae_ci_lo=float(np.quantile(mae,.025)),mae_ci_hi=float(np.quantile(mae,.975)))

def row(tab,w,g):
    q=tab[(tab.window==w)&(tab.group==g)]; return q.iloc[0] if len(q) else None

def report(corr,bins,nf,side,boot,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
           '## Frozen parity',f"- flow lineage: **{meta['flow_n']}**",f"- feature rows: **{meta['feature_n']}**, pre-Aug **{meta['pre_aug_n']}**",f"- timestamp parity: **{meta['timestamp_parity']:.2%}**",f"- recomputed-vs-frozen 12h payoff median absolute error: **{meta['payoff_parity_mae']:.6f} ATR**",'',
           '## Threshold-free proximity correlations','', '| Slice | H | N | rho(distance, return) | rho(distance, MAE) |','|---|---|---:|---:|---:|']
    for _,r in corr.iterrows():lines.append(f"| {r['slice']} | {r.horizon} | {int(r.n)} | {f(r.rho_return)} | {f(r.rho_mae)} |")
    lines += ['', '## 4H fixed near/far by window','', '| Window | Group | N | EV ATR | t | Payoff ratio | Median MAE | Stop1.5 touch | L/S |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in nf.iterrows():
        if r.group not in {'ALL','NEAR4H','FAR4H','SWEEP1TO4'}:continue
        lines.append(f"| {r.window} | {r.group} | {int(r.n)} | {f(r.mean_signed12_atr)} | {f(r.t)} | {f(r.payoff_ratio)} | {f(r.median_mae_atr)} | {f(r.stop15_touch_rate)} | {int(r.long_n)}/{int(r.short_n)} |")
    lines += ['', '## Pre-Aug NEAR4H by side','', '| Side | N | EV ATR | t | Payoff ratio | Median MAE | Stop1.5 touch |','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in side.iterrows():lines.append(f"| {r.side} | {int(r.n)} | {f(r.mean_signed12_atr)} | {f(r.t)} | {f(r.payoff_ratio)} | {f(r.median_mae_atr)} | {f(r.stop15_touch_rate)} |")
    lines += ['', '## Bootstrap NEAR4H - FAR4H',f"- N near/far: **{boot['near_n']} / {boot['far_n']}**",f"- EV diff: **{f(boot['ev_diff'])} ATR**, 95% CI **[{f(boot['ev_ci_lo'])}, {f(boot['ev_ci_hi'])}]**",f"- mean MAE diff: **{f(boot['mae_diff'])} ATR**, 95% CI **[{f(boot['mae_ci_lo'])}, {f(boot['mae_ci_hi'])}]**",'',
              '## Gates']
    for k,v in gates.items():lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## Guardrail','This LAB conditions the frozen flow signal at the same signal-time close. It does not delay entry, optimize a threshold, or use H4 direction. August 2026 is reused audit. Live allocation = **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price=L23.load_price(); flow=L23.load_flow()
    if len(flow)!=EXPECTED_FLOW_N:raise RuntimeError('flow lineage mismatch')
    timestamp_parity=float(flow.signal_time.isin(price.index).mean())
    if timestamp_parity<.99:raise RuntimeError(f'timestamp parity {timestamp_parity:.3%}')
    z,missing=build_features(price,flow)
    pre=z[z.signal_time<pd.Timestamp('2026-08-01',tz=UTC)]
    payoff_parity=float(np.median(np.abs(z.signed12_atr-z.frozen_signed12_atr))) if len(z) else np.nan
    if not np.isfinite(payoff_parity) or payoff_parity>.02:raise RuntimeError(f'12h payoff parity failed: {payoff_parity}')
    z.to_csv(OUT/'signal_time_features.csv',index=False)
    corr=corr_table(z); corr.to_csv(OUT/'spearman_proximity.csv',index=False)
    bins=bin_table(pre); bins.to_csv(OUT/'fixed_bins_pre_aug.csv',index=False)
    nf=near_far_table(z); nf.to_csv(OUT/'near_far_by_window.csv',index=False)
    side=side_near(z); side.to_csv(OUT/'near4h_by_side.csv',index=False)
    boot=bootstrap_near_far(z); (OUT/'bootstrap_near_far.json').write_text(json.dumps(boot,indent=2,allow_nan=True))
    c4=corr[(corr['slice']=='ALL_PRE_AUG')&(corr.horizon=='4H')].iloc[0]
    allr=row(nf,'ALL_PRE_AUG','ALL'); near=row(nf,'ALL_PRE_AUG','NEAR4H'); far=row(nf,'ALL_PRE_AUG','FAR4H'); rec=row(nf,'POOLED_RECENT','NEAR4H'); sw=row(nf,'ALL_PRE_AUG','SWEEP1TO4')
    y22=z[(z.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(z.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(z.side==-1)&(z.dist_4H_atr<=.50)]
    sm={r.side:r for _,r in side.iterrows()}
    gates={
      'frozen_lineage_3209_and_timestamp_parity':len(flow)==3209 and timestamp_parity>=.99,
      'feature_rows_pre_aug_ge_3000':len(pre)>=3000,
      'rho4h_return_negative':bool(np.isfinite(c4.rho_return) and c4.rho_return<0),
      'rho4h_mae_positive':bool(np.isfinite(c4.rho_mae) and c4.rho_mae>0),
      'near4h_n_ge_500':int(near.n)>=500,
      'near4h_ev_baseline_plus_010':float(near.mean_signed12_atr)>=float(allr.mean_signed12_atr)+.10,
      'near4h_ev_gt_far4h':float(near.mean_signed12_atr)>float(far.mean_signed12_atr),
      'near4h_median_mae_lower_by_025':float(near.median_mae_atr)<=float(far.median_mae_atr)-.25,
      'near4h_stop_touch_lower_by_10pp':float(near.stop15_touch_rate)<=float(far.stop15_touch_rate)-.10,
      'bootstrap_ev_diff_ci_gt_zero':bool(np.isfinite(boot['ev_ci_lo']) and boot['ev_ci_lo']>0),
      'stress_2022_short_near_n40_ev_positive':len(y22)>=40 and float(y22.signed12_atr.mean())>0,
      'near4h_long_short_both_positive':float(sm['LONG'].mean_signed12_atr)>0 and float(sm['SHORT'].mean_signed12_atr)>0,
      'recent_near4h_ev_positive':float(rec.mean_signed12_atr)>0,
      'recent_sweep_ev_baseline_plus_010':int(sw.n)>0 and float(sw.mean_signed12_atr)>=float(allr.mean_signed12_atr)+.10,
    }
    score=sum(gates.values()); critical=['frozen_lineage_3209_and_timestamp_parity','rho4h_return_negative','rho4h_mae_positive','near4h_ev_baseline_plus_010','near4h_ev_gt_far4h','recent_near4h_ev_positive']
    if score>=11 and all(gates[k] for k in critical):verdict='PASS_MECHANISTIC_PROXIMITY'
    elif score>=7 and float(near.mean_signed12_atr)>0:verdict='WATCH_SIGNAL_TIME_PROXIMITY'
    else:verdict='FAIL_NO_SIGNAL_TIME_PROXIMITY_MECHANISM'
    meta=dict(verdict=verdict,flow_n=len(flow),feature_n=len(z),pre_aug_n=len(pre),missing_timestamps=missing,timestamp_parity=timestamp_parity,payoff_parity_mae=payoff_parity)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(corr,bins,nf,side,boot,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__':main()
