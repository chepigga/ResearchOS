#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_ACCEPTANCE_ORIGIN_CLOSE2_FAILURE_RECOVERY_AND_REACCEPTANCE_LAB_030'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC=LABS/'BTC_RETAIL_FLOW_ACCEPTANCE_TWO_CLOSE_FAILURE_PERSISTENCE_AND_SURVIVAL_EXECUTION_LAB_029'/'output'/'origin_close2_execution_stream.csv'
SRC23=LABS/'BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab023',SRC23)
L23=importlib.util.module_from_spec(spec); spec.loader.exec_module(L23)
UTC='UTC'; PRE=pd.Timestamp('2026-08-01',tz=UTC)
SEED=20260907; BOOT_N=5000; COST_BPS=5.0
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),
 '2023':('2023-01-01','2024-01-01'),'2024':('2024-01-01','2025-01-01'),
 '2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'AUG2026_REUSED_AUDIT':('2026-08-01','2026-09-01'),
 'HIST':('2021-01-01','2025-07-01'),'RECENT':('2025-07-01','2026-08-01'),
 'ALL_PRE_AUG':('2021-01-01','2026-08-01')}

def tstat(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if len(a)<2:return np.nan
    s=a.std(ddof=1); return float(a.mean()/(s/math.sqrt(len(a)))) if s>0 else np.nan

def pf(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    p=float(a[a>0].sum()); n=float(-a[a<0].sum())
    if n==0:return np.inf if p>0 else np.nan
    return p/n

def load_lineage():
    d=pd.read_csv(SRC)
    for c in ['signal_time','passage_time','origin_close2_time']:
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','signal_close','entry','atr14','origin_close2_net_atr','time_only_net_atr','frozen_residual12_atr']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    for c in ['origin_close2_trigger']:
        d[c]=d[c].astype(str).str.lower().isin(['true','1','yes'])
    return d.sort_values('signal_time').reset_index(drop=True)

def first_close(path,side,level):
    for t,z in path.iterrows():
        if side*(float(z.close)-level)>0:return t,float(z.close)
    return pd.NaT,np.nan

def simulate(price,d):
    pos=pd.Series(np.arange(len(price),dtype=int),index=price.index)
    rows=[]
    for r in d.itertuples():
        if not bool(r.origin_close2_trigger) or pd.isna(r.origin_close2_time):continue
        sig_t=pd.Timestamp(r.signal_time); fail_t=pd.Timestamp(r.origin_close2_time)
        end_t=sig_t+pd.Timedelta(hours=12)
        if fail_t not in pos.index or end_t not in pos.index or fail_t>=end_t:continue
        side=int(r.side); sig=float(r.signal_close); entry=float(r.entry); atr=float(r.atr14)
        if not np.isfinite(atr) or atr<=0:continue
        fail_close=float(price.loc[fail_t,'close']); end_close=float(price.loc[end_t,'close'])
        i=int(pos.loc[fail_t])+1
        if i>=len(price):continue
        start=price.index[i]
        path=price.loc[(price.index>=start)&(price.index<=end_t)]
        if path.empty:continue
        rec_t,rec_px=first_close(path,side,sig)
        rea_t,rea_px=first_close(path,side,entry)
        origin_reclaim=bool(pd.notna(rec_t)); full_reaccept=bool(pd.notna(rea_t))
        # FULL_REACCEPT necessarily also implies origin reclaim; enforce causal ordering naturally.
        if full_reaccept and origin_reclaim and rea_t<rec_t:
            raise RuntimeError('Reaccept before origin reclaim geometry impossible')
        # residuals exclude the move needed to recover/reaccept.
        reaccept_resid=float(side*(end_close-rea_px)/atr) if full_reaccept else np.nan
        failure_to_end=float(side*(end_close-fail_close)/atr)
        origin_reclaim_resid=float(side*(end_close-rec_px)/atr) if origin_reclaim else np.nan
        reentry_net=np.nan
        if full_reaccept:
            reentry_net=float(reaccept_resid-(rea_px*(COST_BPS/10000.0))/atr)
        # Post-failure path anatomy relative to failure close.
        adv=[]; fav=[]
        for t,z in path.iterrows():
            a=max(0.0,fail_close-float(z.low)) if side>0 else max(0.0,float(z.high)-fail_close)
            f=max(0.0,float(z.high)-fail_close) if side>0 else max(0.0,fail_close-float(z.low))
            adv.append(a/atr); fav.append(f/atr)
        # Count completed closes still through origin before full reaccept; includes bars after failure only.
        extra_bad=0
        for t,z in path.iterrows():
            if full_reaccept and t>rea_t:break
            if side*(float(z.close)-sig)<=0:extra_bad+=1
        rows.append(dict(flow_id=int(r.flow_id),signal_time=sig_t,side=side,signal_close=sig,entry=entry,atr14=atr,
          failure_time=fail_t,failure_close=fail_close,origin_reclaim=origin_reclaim,origin_reclaim_time=rec_t,
          full_reaccept=full_reaccept,full_reaccept_time=rea_t,origin_reclaim_h=float((rec_t-fail_t).total_seconds()/3600) if origin_reclaim else np.nan,
          full_reaccept_h=float((rea_t-fail_t).total_seconds()/3600) if full_reaccept else np.nan,
          failure_to_end_atr=failure_to_end,origin_reclaim_residual_atr=origin_reclaim_resid,reaccept_residual_atr=reaccept_resid,
          reentry_net_atr=reentry_net,post_failure_mae_atr=float(max(adv)) if adv else np.nan,post_failure_mfe_atr=float(max(fav)) if fav else np.nan,
          extra_bad_closes_before_reaccept=int(extra_bad),frozen_time_only_net_atr=float(r.time_only_net_atr),frozen_close2_net_atr=float(r.origin_close2_net_atr)))
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)

def state_metrics(q,label):
    n=len(q); fr=q[q.full_reaccept]; no=q[~q.full_reaccept]
    return dict(sample=label,n=n,origin_reclaim_n=int(q.origin_reclaim.sum()),origin_reclaim_rate=float(q.origin_reclaim.mean()) if n else np.nan,
      full_reaccept_n=int(q.full_reaccept.sum()),full_reaccept_rate=float(q.full_reaccept.mean()) if n else np.nan,
      reaccept_resid=float(fr.reaccept_residual_atr.mean()) if len(fr) else np.nan,reaccept_t=tstat(fr.reaccept_residual_atr) if len(fr) else np.nan,
      reaccept_pf=pf(fr.reaccept_residual_atr) if len(fr) else np.nan,no_reaccept_resid=float(no.failure_to_end_atr.mean()) if len(no) else np.nan,
      residual_gap=float(fr.reaccept_residual_atr.mean()-no.failure_to_end_atr.mean()) if len(fr) and len(no) else np.nan,
      median_reclaim_h=float(q.loc[q.origin_reclaim,'origin_reclaim_h'].median()) if q.origin_reclaim.any() else np.nan,
      median_reaccept_h=float(fr.full_reaccept_h.median()) if len(fr) else np.nan,median_extra_bad=float(fr.extra_bad_closes_before_reaccept.median()) if len(fr) else np.nan,
      reentry_net=float(fr.reentry_net_atr.mean()) if len(fr) else np.nan,long_reaccept=int(((q.side==1)&q.full_reaccept).sum()),short_reaccept=int(((q.side==-1)&q.full_reaccept).sum()))

def bootstrap(d):
    q=d[d.signal_time<PRE].copy(); epoch=pd.Timestamp('1970-01-01',tz=UTC)
    q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    rows=[]
    for c,z in q.groupby('cluster'):
        a=z.loc[z.full_reaccept,'reaccept_residual_atr'].dropna().to_numpy(float)
        b=z.loc[~z.full_reaccept,'failure_to_end_atr'].dropna().to_numpy(float)
        rows.append((a.sum(),len(a),b.sum(),len(b)))
    arr=np.asarray(rows,float); m=len(arr); rng=np.random.default_rng(SEED); vals=[]
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0:vals.append(float(s[0]/s[1]-s[2]/s[3]))
    vals=np.asarray(vals,float)
    fr=q[q.full_reaccept].reaccept_residual_atr.dropna(); no=q[~q.full_reaccept].failure_to_end_atr.dropna()
    point=float(fr.mean()-no.mean())
    return dict(n_clusters=m,draws=len(vals),point=point,ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)))

def report(tab,side,boot,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
      '## Frozen lineage',f"- LAB029 rows: **{meta['lineage_n']}**; triggered failures pre-Aug: **{meta['failure_n_pre']}**",'',
      '## Failure recovery by window','',
      '| Window | N fail | Origin reclaim | Full reaccept | Rate | Reaccept residual | No-reaccept residual | Gap | Reaccept PF | Median reaccept h | Reentry net |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in tab.iterrows():lines.append(f"| {r['sample']} | {int(r.n)} | {int(r.origin_reclaim_n)} | {int(r.full_reaccept_n)} | {f(r.full_reaccept_rate)} | {f(r.reaccept_resid)} | {f(r.no_reaccept_resid)} | {f(r.residual_gap)} | {f(r.reaccept_pf)} | {f(r.median_reaccept_h)} | {f(r.reentry_net)} |")
    lines += ['', '## By side pre-Aug','', '| Side | N fail | Full reaccept | Rate | Reaccept residual | No-reaccept residual | Gap | PF |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in side.iterrows():lines.append(f"| {r['sample']} | {int(r.n)} | {int(r.full_reaccept_n)} | {f(r.full_reaccept_rate)} | {f(r.reaccept_resid)} | {f(r.no_reaccept_resid)} | {f(r.residual_gap)} | {f(r.reaccept_pf)} |")
    lines += ['', '## 7d cluster bootstrap',f"- clusters: **{boot['n_clusters']}**, draws: **{boot['draws']}**",f"- FULL_REACCEPT residual minus NO_REACCEPT residual: **{f(boot['point'])} ATR**, 95% CI **[{f(boot['ci_lo'])}, {f(boot['ci_hi'])}]**",'',
      '## Recovery anatomy',f"- pre-Aug median failure→origin reclaim: **{f(meta['median_reclaim_h'])} h**",f"- pre-Aug median failure→full reaccept: **{f(meta['median_reaccept_h'])} h**",f"- median extra bad closes before reaccept: **{f(meta['median_extra_bad'])}**",'', '## Gates']
    for k,v in gates.items():lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## Guardrail','FULL_REACCEPT is a state audit, not a promoted re-entry rule. Recovery levels are frozen from the original signal price and +0.5 ATR acceptance entry. No threshold/horizon/side rescue. August 2026 reused audit only. Live allocation = **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price=L23.load_price(); lin=load_lineage(); d=simulate(price,lin); d.to_csv(OUT/'failure_recovery_stream.csv',index=False)
    pre=d[d.signal_time<PRE];
    tabs=[]
    for name,(a,b) in WINS.items():
        q=d[(d.signal_time>=pd.Timestamp(a,tz=UTC))&(d.signal_time<pd.Timestamp(b,tz=UTC))]
        tabs.append(state_metrics(q,name))
    tab=pd.DataFrame(tabs); tab.to_csv(OUT/'recovery_by_window.csv',index=False)
    sides=[]
    for s,name in [(1,'LONG'),(-1,'SHORT')]:sides.append(state_metrics(pre[pre.side==s],name))
    side=pd.DataFrame(sides); side.to_csv(OUT/'recovery_by_side.csv',index=False)
    boot=bootstrap(d); (OUT/'bootstrap_7d.json').write_text(json.dumps(boot,indent=2),encoding='utf-8')
    get=lambda n: tab[tab['sample']==n].iloc[0]
    allm=get('ALL_PRE_AUG'); hist=get('HIST'); rec=get('RECENT'); y22=d[(d.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(d.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(d.side==-1)]
    y22m=state_metrics(y22,'2022_SHORT')
    longm=side[side['sample']=='LONG'].iloc[0]; shortm=side[side['sample']=='SHORT'].iloc[0]
    recent_condition=(rec.full_reaccept_rate>=hist.full_reaccept_rate+.05) or (rec.reaccept_resid>=hist.reaccept_resid+.25)
    gates={
      'exact_lab029_lineage_and_failure_n_ge_900':bool(len(lin)==1496 and len(pre)>=900),
      'full_reaccept_n_ge_200':bool(allm.full_reaccept_n>=200),
      'full_reaccept_residual_positive':bool(allm.reaccept_resid>0),
      'residual_gap_ge_0_50atr':bool(allm.residual_gap>=.50),
      'bootstrap_ci_lower_gt_zero':bool(boot['ci_lo']>0),
      'no_reaccept_nonpositive_or_gap_ge_0_50':bool(allm.no_reaccept_resid<=0 or allm.residual_gap>=.50),
      'recent_full_reaccept_n_ge_40':bool(rec.full_reaccept_n>=40),
      'recent_full_reaccept_residual_positive':bool(rec.reaccept_resid>0),
      'recent_reaccept_gt_no_reaccept':bool(rec.reaccept_resid>rec.no_reaccept_resid),
      'recent_recovery_shift_support':bool(recent_condition),
      'stress_2022_short_reaccept_n20_residual_positive':bool(y22m['full_reaccept_n']>=20 and y22m['reaccept_resid']>0),
      'long_and_short_reaccept_residual_positive':bool(longm.reaccept_resid>0 and shortm.reaccept_resid>0),
    }
    critical=['exact_lab029_lineage_and_failure_n_ge_900','full_reaccept_residual_positive','residual_gap_ge_0_50atr','bootstrap_ci_lower_gt_zero','recent_full_reaccept_n_ge_40','recent_full_reaccept_residual_positive','recent_reaccept_gt_no_reaccept']
    score=sum(gates.values())
    if score>=10 and all(gates[k] for k in critical):verdict='PASS_FAILURE_RECOVERY_REACCEPTANCE_MECHANISM'
    elif gates['full_reaccept_residual_positive'] and gates['residual_gap_ge_0_50atr']:verdict='WATCH_REACCEPTANCE_DISCRIMINATIVE_BUT_TRANSFER_INCOMPLETE'
    else:verdict='FAIL_NO_ROBUST_FAILURE_RECOVERY_MECHANISM'
    meta=dict(verdict=verdict,lineage_n=len(lin),failure_n_pre=len(pre),median_reclaim_h=float(pre.loc[pre.origin_reclaim,'origin_reclaim_h'].median()),median_reaccept_h=float(pre.loc[pre.full_reaccept,'full_reaccept_h'].median()),median_extra_bad=float(pre.loc[pre.full_reaccept,'extra_bad_closes_before_reaccept'].median()),y22_short=y22m)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'bootstrap':boot,'gates':gates},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(tab,side,boot,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__':main()
