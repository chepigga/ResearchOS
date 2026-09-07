#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_ACCEPTANCE_POST_CONFIRM_MAE_SURVIVAL_AND_CAUSAL_FAILURE_EXIT_LAB_028'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
PASSAGE=LABS/'BTC_RETAIL_FLOW_EARLY_DIRECTIONAL_ACCEPTANCE_VS_ADVERSE_FAILURE_FIRST_PASSAGE_LAB_026'/'output'/'first_passage_2h.csv'
SRC23=LABS/'BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab023',SRC23)
L23=importlib.util.module_from_spec(spec); spec.loader.exec_module(L23)
EXPECTED_N=3209
THR_ATR=0.5
STOP_ATR=1.5
COST_BPS=5.0
SEED=20260907
BOOT_N=5000
UTC='UTC'
PRE_CUT=pd.Timestamp('2026-08-01',tz=UTC)
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

def maxdd(a):
    a=np.asarray(a,float); a=np.where(np.isfinite(a),a,0.0)
    if not len(a):return 0.0
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq]); return float(np.max(peak[1:]-eq))

def load_passage():
    d=pd.read_csv(PASSAGE)
    for c in ['signal_time','passage_time']:
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','signal_close','atr14','total12_atr','residual12_atr','frozen_signed12_atr']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    return d.sort_values('signal_time').reset_index(drop=True)

def first_close_failure(path,side,level,n_consecutive):
    consec=0
    for t,z in path.iterrows():
        bad=side*(float(z.close)-level)<=0
        consec=consec+1 if bad else 0
        if consec>=n_consecutive:return t,float(z.close)
    return pd.NaT,np.nan

def hard_stop(path,side,stop):
    for t,z in path.iterrows():
        hit=(float(z.low)<=stop) if side>0 else (float(z.high)>=stop)
        if hit:return t,stop
    return pd.NaT,np.nan

def first_fav(path,side,entry,atr,mult):
    lvl=entry+side*mult*atr
    for t,z in path.iterrows():
        hit=(float(z.high)>=lvl) if side>0 else (float(z.low)<=lvl)
        if hit:return t
    return pd.NaT

def simulate_accept_paths(price,p):
    pos=pd.Series(np.arange(len(price),dtype=int),index=price.index)
    rows=[]
    for r in p.itertuples():
        if r.state!='ACCEPT_FIRST' or pd.isna(r.passage_time):continue
        sig_t=pd.Timestamp(r.signal_time); pt=pd.Timestamp(r.passage_time)
        if sig_t not in pos.index or pt not in pos.index:continue
        exit_t=sig_t+pd.Timedelta(hours=12)
        if exit_t not in pos.index or pt>exit_t:continue
        side=int(r.side); sig=float(r.signal_close); atr=float(r.atr14)
        if not np.isfinite(atr) or atr<=0:continue
        entry=sig+side*THR_ATR*atr
        path=price.loc[(price.index>=pt)&(price.index<=exit_t)].copy()
        if path.empty:continue
        end_close=float(price.loc[exit_t,'close'])
        cost=(entry*(COST_BPS/10000.0))/atr

        # Full path geometry from accepted threshold to original +12h exit.
        adv=[]; fav=[]
        for t,z in path.iterrows():
            a=max(0.0,entry-float(z.low)) if side>0 else max(0.0,float(z.high)-entry)
            f=max(0.0,float(z.high)-entry) if side>0 else max(0.0,entry-float(z.low))
            adv.append((t,a/atr)); fav.append((t,f/atr))
        mae_t,mae=max(adv,key=lambda x:x[1]); mfe_t,mfe=max(fav,key=lambda x:x[1])
        wick_origin=any((float(z.low)<=sig if side>0 else float(z.high)>=sig) for _,z in path.iterrows())

        o1_t,o1_px=first_close_failure(path,side,sig,1)
        o2_t,o2_px=first_close_failure(path,side,sig,2)
        e2_t,e2_px=first_close_failure(path,side,entry,2)
        sl_t,sl_px=hard_stop(path,side,entry-side*STOP_ATR*atr)

        def pnl(exit_time,exit_px):
            if pd.isna(exit_time): exit_time=exit_t; exit_px=end_close
            return float(side*(float(exit_px)-entry)/atr-cost), exit_time
        time_pnl=float(side*(end_close-entry)/atr-cost)
        o1_pnl,o1_et=pnl(o1_t,o1_px)
        o2_pnl,o2_et=pnl(o2_t,o2_px)
        e2_pnl,e2_et=pnl(e2_t,e2_px)
        sl_pnl,sl_et=pnl(sl_t,sl_px)
        fp05=first_fav(path,side,entry,atr,.5); fp10=first_fav(path,side,entry,atr,1.0); fp15=first_fav(path,side,entry,atr,1.5)
        rows.append(dict(
          flow_id=int(r.flow_id),signal_time=sig_t,passage_time=pt,side=side,signal_close=sig,entry=entry,atr14=atr,
          frozen_residual12_atr=float(r.residual12_atr),time_only_net_atr=time_pnl,
          post_mae_atr=float(mae),post_mfe_atr=float(mfe),time_to_mae_h=float((mae_t-pt).total_seconds()/3600),time_to_mfe_h=float((mfe_t-pt).total_seconds()/3600),
          fp_fav05_time=fp05,fp_fav10_time=fp10,fp_fav15_time=fp15,
          mae_ge_05=bool(mae>=.5),mae_ge_10=bool(mae>=1.0),mae_ge_15=bool(mae>=1.5),mae_ge_20=bool(mae>=2.0),
          wick_origin_any=bool(wick_origin),origin_close1_trigger=bool(pd.notna(o1_t)),origin_close1_time=o1_et,origin_close1_net_atr=o1_pnl,
          origin_close2_trigger=bool(pd.notna(o2_t)),origin_close2_time=o2_et,origin_close2_net_atr=o2_pnl,
          entry_close2_trigger=bool(pd.notna(e2_t)),entry_close2_time=e2_et,entry_close2_net_atr=e2_pnl,
          hard_sl15_trigger=bool(pd.notna(sl_t)),hard_sl15_time=sl_et,hard_sl15_net_atr=sl_pnl,
        ))
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)

def policy_metrics(q,col,label,trigger_col=None,total_original_signals=None):
    a=pd.to_numeric(q[col],errors='coerce').dropna().to_numpy(float)
    den=total_original_signals if total_original_signals is not None else len(q)
    return dict(sample=label,accept_trades=len(a),original_signals=int(den),ev_trade=float(a.mean()) if len(a) else np.nan,
      policy_ev_original_signal=float(a.sum()/den) if den else np.nan,cum_atr=float(a.sum()),t=tstat(a),pf=pf(a),dd_atr=maxdd(a),
      trigger_rate=float(q[trigger_col].mean()) if trigger_col and len(q) else np.nan,
      long_n=int((q.side==1).sum()),short_n=int((q.side==-1).sum()))

def original_count(allp,a,b):
    return int(((allp.signal_time>=a)&(allp.signal_time<b)).sum())

def window_summary(d,allp):
    rows=[]
    for w,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz=UTC); b=pd.Timestamp(bb,tz=UTC); q=d[(d.signal_time>=a)&(d.signal_time<b)]
        n0=original_count(allp,a,b)
        x=policy_metrics(q,'origin_close1_net_atr',w,'origin_close1_trigger',n0); x['window']=w; rows.append(x)
    return pd.DataFrame(rows)

def side_summary(d,allp):
    pre=d[d.signal_time<PRE_CUT]; ap=allp[allp.signal_time<PRE_CUT]; rows=[]
    for side,name in [(1,'LONG'),(-1,'SHORT')]:
        q=pre[pre.side==side]; n0=int((ap.side==side).sum())
        x=policy_metrics(q,'origin_close1_net_atr',name,'origin_close1_trigger',n0); x['side_name']=name; rows.append(x)
    return pd.DataFrame(rows)

def survival_summary(d):
    pre=d[d.signal_time<PRE_CUT].copy(); pre['winner']=pre.frozen_residual12_atr>0
    rows=[]
    for grp,mask in [('ALL',np.ones(len(pre),dtype=bool)),('WINNER',pre.winner),('LOSER',~pre.winner)]:
        q=pre[mask]
        rows.append(dict(group=grp,n=len(q),resid_mean=float(q.frozen_residual12_atr.mean()),median_mae=float(q.post_mae_atr.median()),median_mfe=float(q.post_mfe_atr.median()),
          mae_ge_05=float(q.mae_ge_05.mean()),mae_ge_10=float(q.mae_ge_10.mean()),mae_ge_15=float(q.mae_ge_15.mean()),mae_ge_20=float(q.mae_ge_20.mean()),
          fav05_rate=float(q.fp_fav05_time.notna().mean()),fav10_rate=float(q.fp_fav10_time.notna().mean()),fav15_rate=float(q.fp_fav15_time.notna().mean()),
          median_t_mae=float(q.time_to_mae_h.median()),median_t_mfe=float(q.time_to_mfe_h.median())))
    return pd.DataFrame(rows)

def failure_class_summary(d):
    pre=d[d.signal_time<PRE_CUT]
    classes={
      'ORIGIN_CLOSE1_TRIGGER':pre.origin_close1_trigger,
      'NO_ORIGIN_CLOSE1':~pre.origin_close1_trigger,
      'WICK_ONLY_NO_CLOSE':pre.wick_origin_any & ~pre.origin_close1_trigger,
      'NO_WICK_NO_CLOSE':~pre.wick_origin_any & ~pre.origin_close1_trigger,
    }
    rows=[]
    for name,m in classes.items():
        q=pre[m]
        rows.append(dict(group=name,n=len(q),frozen_resid_mean=float(q.frozen_residual12_atr.mean()) if len(q) else np.nan,time_net_mean=float(q.time_only_net_atr.mean()) if len(q) else np.nan,median_mae=float(q.post_mae_atr.median()) if len(q) else np.nan,win_rate=float((q.frozen_residual12_atr>0).mean()) if len(q) else np.nan))
    return pd.DataFrame(rows)

def bootstrap_diff(d):
    q=d[d.signal_time<PRE_CUT].copy()
    epoch=pd.Timestamp('1970-01-01',tz=UTC)
    q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    q['diff']=q.origin_close1_net_atr-q.hard_sl15_net_atr
    g=q.groupby('cluster').agg(n=('flow_id','size'),s=('diff','sum')).reset_index(drop=True)
    rng=np.random.default_rng(SEED); vals=np.empty(BOOT_N,float); m=len(g)
    for j in range(BOOT_N):
        ix=rng.integers(0,m,size=m); z=g.iloc[ix]; vals[j]=float(z.s.sum()/z.n.sum())
    return dict(n_clusters=int(m),draws=BOOT_N,point_diff=float(q['diff'].mean()),ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)))

def report(pol,win,side,surv,fc,boot,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
      '## Frozen parity',f"- flow lineage: **{meta['flow_n']}**, pre-Aug ACCEPT: **{meta['accept_pre_aug']}**",f"- timestamp parity: **{meta['timestamp_parity']:.2%}**",'',
      '## Post-acceptance survival map','', '| Group | N | Frozen residual | Median MAE | MAE>=.5 | >=1 | >=1.5 | >=2 | Fav+.5 | +1 | +1.5 | tMAE h | tMFE h |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in surv.iterrows():lines.append(f"| {r.group} | {int(r.n)} | {f(r.resid_mean)} | {f(r.median_mae)} | {f(r.mae_ge_05)} | {f(r.mae_ge_10)} | {f(r.mae_ge_15)} | {f(r.mae_ge_20)} | {f(r.fav05_rate)} | {f(r.fav10_rate)} | {f(r.fav15_rate)} | {f(r.median_t_mae)} | {f(r.median_t_mfe)} |")
    lines += ['', '## Failure-state discrimination','', '| Group | N | Frozen residual | Time-only net | MAE | Win rate |','|---|---:|---:|---:|---:|---:|']
    for _,r in fc.iterrows():lines.append(f"| {r.group} | {int(r.n)} | {f(r.frozen_resid_mean)} | {f(r.time_net_mean)} | {f(r.median_mae)} | {f(r.win_rate)} |")
    lines += ['', '## Execution policies pre-Aug','', '| Policy | Accept trades | EV/trade | Policy EV/orig signal | Cum ATR | PF | DD | Trigger |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in pol.iterrows():lines.append(f"| {r['sample']} | {int(r.accept_trades)} | {f(r.ev_trade)} | {f(r.policy_ev_original_signal)} | {f(r.cum_atr)} | {f(r.pf)} | {f(r.dd_atr)} | {f(r.trigger_rate)} |")
    lines += ['', '## Primary ORIGIN_CLOSE1 by window','', '| Window | Trades | EV | Cum | PF | DD | Trigger | L/S |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in win.iterrows():lines.append(f"| {r.window} | {int(r.accept_trades)} | {f(r.ev_trade)} | {f(r.cum_atr)} | {f(r.pf)} | {f(r.dd_atr)} | {f(r.trigger_rate)} | {int(r.long_n)}/{int(r.short_n)} |")
    lines += ['', '## Primary by side','', '| Side | Trades | EV | Cum | PF | DD |','|---|---:|---:|---:|---:|---:|']
    for _,r in side.iterrows():lines.append(f"| {r.side_name} | {int(r.accept_trades)} | {f(r.ev_trade)} | {f(r.cum_atr)} | {f(r.pf)} | {f(r.dd_atr)} |")
    lines += ['', '## 7d cluster bootstrap',f"- clusters: **{boot['n_clusters']}**, draws: **{boot['draws']}**",f"- ORIGIN_CLOSE1 minus HARD_SL15 EV/trade: **{f(boot['point_diff'])} ATR**, 95% CI **[{f(boot['ci_lo'])}, {f(boot['ci_hi'])}]**",'', '## Gates']
    for k,v in gates.items():lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## Guardrail','MAE bands are descriptive only and cannot become stops. Primary failure rule is frozen ORIGIN_CLOSE1: first completed M15 close back through original signal price. No threshold/stop/horizon optimization. August 2026 reused audit only. Live allocation = **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price=L23.load_price(); allp=load_passage()
    if len(allp)!=EXPECTED_N:raise RuntimeError(f'lineage {len(allp)} != {EXPECTED_N}')
    ts=float(allp.signal_time.isin(price.index).mean())
    if ts<.99:raise RuntimeError(f'timestamp parity {ts:.3%}')
    d=simulate_accept_paths(price,allp); d.to_csv(OUT/'accept_path_event_stream.csv',index=False)
    pre=d[d.signal_time<PRE_CUT]; allpre=allp[allp.signal_time<PRE_CUT]
    if len(pre)<1400:raise RuntimeError(f'pre-Aug ACCEPT only {len(pre)}')
    surv=survival_summary(d); surv.to_csv(OUT/'survival_summary.csv',index=False)
    fc=failure_class_summary(d); fc.to_csv(OUT/'failure_class_summary.csv',index=False)
    n0=len(allpre)
    pol=pd.DataFrame([
      policy_metrics(pre,'origin_close1_net_atr','ORIGIN_CLOSE1','origin_close1_trigger',n0),
      policy_metrics(pre,'origin_close2_net_atr','AUDIT_ORIGIN_CLOSE2','origin_close2_trigger',n0),
      policy_metrics(pre,'entry_close2_net_atr','AUDIT_ENTRY_CLOSE2','entry_close2_trigger',n0),
      policy_metrics(pre,'time_only_net_atr','TIME_ONLY',None,n0),
      policy_metrics(pre,'hard_sl15_net_atr','HARD_SL15','hard_sl15_trigger',n0),
    ]); pol.to_csv(OUT/'policy_summary.csv',index=False)
    win=window_summary(d,allp); win.to_csv(OUT/'primary_by_window.csv',index=False)
    side=side_summary(d,allp); side.to_csv(OUT/'primary_by_side.csv',index=False)
    boot=bootstrap_diff(d); (OUT/'bootstrap_7d.json').write_text(json.dumps(boot,indent=2,allow_nan=True))
    def row(tab,name,key='sample'):
        q=tab[tab[key]==name]; return q.iloc[0] if len(q) else None
    prim=row(pol,'ORIGIN_CLOSE1'); hard=row(pol,'HARD_SL15'); time=row(pol,'TIME_ONLY')
    trig=row(fc,'ORIGIN_CLOSE1_TRIGGER','group'); non=row(fc,'NO_ORIGIN_CLOSE1','group'); wick=row(fc,'WICK_ONLY_NO_CLOSE','group')
    y22=d[(d.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(d.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(d.side==-1)]
    y22m=policy_metrics(y22,'origin_close1_net_atr','2022_SHORT','origin_close1_trigger',int(((allp.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(allp.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(allp.side==-1)).sum()))
    recent=d[(d.signal_time>=pd.Timestamp('2025-07-01',tz=UTC))&(d.signal_time<PRE_CUT)]
    recm=policy_metrics(recent,'origin_close1_net_atr','RECENT','origin_close1_trigger',int(((allp.signal_time>=pd.Timestamp('2025-07-01',tz=UTC))&(allp.signal_time<PRE_CUT)).sum()))
    longm=row(side,'LONG','side_name'); shortm=row(side,'SHORT','side_name')
    fail_diff=float(non.frozen_resid_mean-trig.frozen_resid_mean)
    retention=float(prim.cum_atr/time.cum_atr) if time.cum_atr>0 else np.nan
    gates={
      'exact_lab026_lineage_and_accept_n_ge_1400':bool(len(allp)==3209 and ts>=.99 and len(pre)>=1400),
      'origin_close1_trigger_rate_20_to_85pct':bool(.20<=prim.trigger_rate<=.85),
      'triggered_failure_residual_gap_ge_0_50atr':bool(fail_diff>=.50),
      'wick_only_no_close_n_ge_100':bool(wick.n>=100),
      'wick_only_residual_gt_close_failure':bool(wick.n>0 and wick.frozen_resid_mean>trig.frozen_resid_mean),
      'origin_close1_ev_positive':bool(prim.ev_trade>0),
      'origin_close1_pf_gt_1_20':bool(prim.pf>1.20),
      'origin_close1_ev_gt_hard_sl15':bool(prim.ev_trade>hard.ev_trade),
      'origin_close1_dd_le_hard_sl15':bool(prim.dd_atr<=hard.dd_atr),
      'bootstrap_origin_minus_hard_ci_lower_gt_zero':bool(boot['ci_lo']>0),
      'stress_2022_short_n80_and_cum_positive':bool(y22m.accept_trades>=80 and y22m.cum_atr>0),
      'pooled_recent_cum_positive':bool(recm.cum_atr>0),
      'long_and_short_ev_positive':bool(longm.ev_trade>0 and shortm.ev_trade>0),
      'beats_time_dd_and_retains_70pct_cum':bool(prim.dd_atr<time.dd_atr and retention>=.70),
    }
    score=sum(gates.values()); critical=['triggered_failure_residual_gap_ge_0_50atr','origin_close1_ev_positive','origin_close1_ev_gt_hard_sl15','bootstrap_origin_minus_hard_ci_lower_gt_zero','pooled_recent_cum_positive']
    if score>=11 and all(gates[k] for k in critical):verdict='PASS_CAUSAL_ORIGIN_CLOSE_FAILURE_EXIT'
    elif gates['triggered_failure_residual_gap_ge_0_50atr'] and gates['wick_only_residual_gt_close_failure']:verdict='WATCH_FAILURE_STATE_DISCRIMINATIVE_EXECUTION_NOT_ROBUST'
    else:verdict='FAIL_NO_CAUSAL_POST_ACCEPTANCE_FAILURE_EXIT'
    aug=d[(d.signal_time>=pd.Timestamp('2026-08-01',tz=UTC))&(d.signal_time<pd.Timestamp('2026-09-01',tz=UTC))]
    meta=dict(verdict=verdict,flow_n=len(allp),accept_pre_aug=len(pre),timestamp_parity=ts,failure_gap=fail_diff,retention_vs_time=retention,aug_reused_n=len(aug),aug_primary_cum=float(aug.origin_close1_net_atr.sum()) if len(aug) else 0.0)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates,'bootstrap':boot,'stress_2022_short':y22m,'recent':recm},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(pol,win,side,surv,fc,boot,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__':main()
