#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math, glob
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_ACCEPTANCE_TWO_CLOSE_FAILURE_PERSISTENCE_AND_SURVIVAL_EXECUTION_LAB_029'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC28=LABS/'BTC_RETAIL_FLOW_ACCEPTANCE_POST_CONFIRM_MAE_SURVIVAL_AND_CAUSAL_FAILURE_EXIT_LAB_028'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab028',SRC28)
L28=importlib.util.module_from_spec(spec); spec.loader.exec_module(L28)
EXPECTED_FLOW_N=3209
EXPECTED_ACCEPT_PRE=1496
PRE_CUT=pd.Timestamp('2026-08-01',tz='UTC')
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
    return float(p/n)

def maxdd(a):
    a=np.asarray(a,float); a=np.where(np.isfinite(a),a,0.0)
    if not len(a):return 0.0
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.,eq]); return float(np.max(peak[1:]-eq))

def load_m1_to_m15():
    parts=[]
    for p in sorted(glob.glob('btc1/**/*.csv',recursive=True)):
        try:d=pd.read_csv(p)
        except Exception:continue
        req={'time','open','high','low','close'}
        if not req.issubset(d.columns):continue
        d=d[['time','open','high','low','close']].copy()
        d['time']=pd.to_datetime(d.time,errors='coerce',utc=True)
        for c in ['open','high','low','close']:d[c]=pd.to_numeric(d[c],errors='coerce')
        d=d.dropna()
        if len(d):parts.append(d)
    if not parts:raise RuntimeError('No btc1 M1 price CSVs loaded')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').set_index('time')
    m=x.resample('15min',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    return m

def metric(q,col,label,trigger_col=None,original_signals=None):
    a=pd.to_numeric(q[col],errors='coerce').dropna().to_numpy(float)
    den=int(original_signals) if original_signals is not None else len(q)
    return dict(sample=label,accept_trades=int(len(a)),original_signals=den,
      ev_trade=float(a.mean()) if len(a) else np.nan,policy_ev_original_signal=float(a.sum()/den) if den else np.nan,
      cum_atr=float(a.sum()),t=tstat(a),pf=pf(a),dd_atr=maxdd(a),
      trigger_rate=float(q[trigger_col].mean()) if trigger_col and len(q) else np.nan,
      median_hold_h=float(q['origin_close2_hold_h'].median()) if col=='origin_close2_net_atr' and len(q) else np.nan,
      long_n=int((q.side==1).sum()),short_n=int((q.side==-1).sum()))

def add_hold(d):
    x=d.copy()
    end=x.signal_time+pd.Timedelta(hours=12)
    et=pd.to_datetime(x.origin_close2_time,errors='coerce',utc=True)
    x['origin_close2_hold_h']=((et-x.passage_time).dt.total_seconds()/3600.0).where(x.origin_close2_trigger,((end-x.passage_time).dt.total_seconds()/3600.0))
    return x

def original_n(allp,a,b,side=None):
    q=allp[(allp.signal_time>=a)&(allp.signal_time<b)]
    if side is not None:q=q[q.side==side]
    return len(q)

def policy_summary(d,allp):
    pre=d[d.signal_time<PRE_CUT]; n0=len(allp[allp.signal_time<PRE_CUT])
    return pd.DataFrame([
      metric(pre,'origin_close2_net_atr','ORIGIN_CLOSE2','origin_close2_trigger',n0),
      metric(pre,'hard_sl15_net_atr','HARD_SL15','hard_sl15_trigger',n0),
      metric(pre,'time_only_net_atr','TIME_ONLY',None,n0),
      metric(pre,'origin_close1_net_atr','ORIGIN_CLOSE1','origin_close1_trigger',n0),
    ])

def window_summary(d,allp):
    rows=[]
    for w,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz=UTC); b=pd.Timestamp(bb,tz=UTC); q=d[(d.signal_time>=a)&(d.signal_time<b)]
        m=metric(q,'origin_close2_net_atr',w,'origin_close2_trigger',original_n(allp,a,b));m['window']=w;rows.append(m)
    return pd.DataFrame(rows)

def side_summary(d,allp):
    rows=[]; pre=d[d.signal_time<PRE_CUT]; ap=allp[allp.signal_time<PRE_CUT]
    for side,name in [(1,'LONG'),(-1,'SHORT')]:
        q=pre[pre.side==side]; m=metric(q,'origin_close2_net_atr',name,'origin_close2_trigger',len(ap[ap.side==side]));m['side_name']=name;rows.append(m)
    return pd.DataFrame(rows)

def state_summary(d):
    pre=d[d.signal_time<PRE_CUT]; rows=[]
    for name,mask in [('TRIGGER',pre.origin_close2_trigger),('NO_TRIGGER',~pre.origin_close2_trigger)]:
        q=pre[mask]
        rows.append(dict(group=name,n=len(q),time_only_ev=float(q.time_only_net_atr.mean()),primary_ev=float(q.origin_close2_net_atr.mean()),median_mae=float(q.post_mae_atr.median()),win_rate=float((q.time_only_net_atr>0).mean()),median_mfe=float(q.post_mfe_atr.median())))
    return pd.DataFrame(rows)

def bootstrap(d,allp):
    q=d[d.signal_time<PRE_CUT].copy(); n0=len(allp[allp.signal_time<PRE_CUT])
    epoch=pd.Timestamp('1970-01-01',tz=UTC)
    q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    q['diff']=q.origin_close2_net_atr-q.hard_sl15_net_atr
    g=q.groupby('cluster').agg(n=('flow_id','size'),s=('diff','sum')).reset_index(drop=True)
    rng=np.random.default_rng(SEED); m=len(g); ev=[]; pol=[]
    for _ in range(BOOT_N):
        ix=rng.integers(0,m,size=m); z=g.iloc[ix]
        ev.append(float(z.s.sum()/z.n.sum()))
        # original-signal denominator approximated by resampled ACCEPT population share times frozen global signal denominator.
        # Since both policies act on identical ACCEPT trades, sign/inference is identical; report scaled policy effect separately.
        pol.append(float((z.s.sum()/z.n.sum())*(len(q)/n0)))
    point=float(q['diff'].mean()); point_pol=float(point*len(q)/n0)
    return dict(n_clusters=int(m),draws=BOOT_N,point_ev_trade=point,ci_ev_lo=float(np.quantile(ev,.025)),ci_ev_hi=float(np.quantile(ev,.975)),point_policy_ev_signal=point_pol,ci_policy_lo=float(np.quantile(pol,.025)),ci_policy_hi=float(np.quantile(pol,.975)))

def first_close2_from_close(close_series,start_t,end_t,side,level):
    q=close_series.loc[(close_series.index>=start_t)&(close_series.index<=end_t)]
    consec=0
    for t,v in q.items():
        bad=side*(float(v)-level)<=0
        consec=consec+1 if bad else 0
        if consec>=2:return True,t
    return False,pd.NaT

def m1_parity(native,m1m15):
    # price close parity on all overlapping M15 labels in the ACCEPT paths
    times=[]
    for r in native.itertuples():
        end=r.signal_time+pd.Timedelta(hours=12)
        times.extend(pd.date_range(r.passage_time,end,freq='15min'))
    ti=pd.DatetimeIndex(times).unique()
    common=ti.intersection(L28.L23.load_price().index).intersection(m1m15.index)
    native_price=L28.L23.load_price()
    rel=((native_price.loc[common,'close']-m1m15.loc[common,'close']).abs()/native_price.loc[common,'close'].abs().clip(lower=1e-9)) if len(common) else pd.Series(dtype=float)
    close_med=float(rel.median()) if len(rel) else np.nan
    rows=[]
    for r in native.itertuples():
        end=r.signal_time+pd.Timedelta(hours=12)
        if r.passage_time not in m1m15.index or end not in m1m15.index:continue
        trig,t=first_close2_from_close(m1m15.close,r.passage_time,end,int(r.side),float(r.signal_close))
        rows.append((bool(r.origin_close2_trigger),trig,pd.Timestamp(r.origin_close2_time) if bool(r.origin_close2_trigger) else pd.NaT,t))
    if not rows:return dict(matched_events=0,close_med_rel=close_med,trigger_parity=np.nan,time_parity=np.nan)
    trig_eq=[a==b for a,b,_,_ in rows]
    both=[(t1==t2) for a,b,t1,t2 in rows if a and b]
    return dict(matched_events=len(rows),close_med_rel=close_med,trigger_parity=float(np.mean(trig_eq)),time_parity=float(np.mean(both)) if both else np.nan)

def report(pol,win,side,state,boot,par,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
      '## Frozen lineage',f"- flow rows: **{meta['flow_n']}**, pre-Aug ACCEPT: **{meta['accept_pre']}**",'',
      '## M1 -> M15 parity',f"- matched ACCEPT events: **{par['matched_events']}**",f"- median close relative error: **{par['close_med_rel']:.10f}**",f"- trigger parity: **{par['trigger_parity']:.3%}**",f"- trigger-time parity: **{par['time_parity']:.3%}**",'',
      '## Pre-Aug policies','', '| Policy | Trades | EV/trade | Policy EV/orig | Cum ATR | PF | DD | Trigger | Hold h |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in pol.iterrows():lines.append(f"| {r['sample']} | {int(r.accept_trades)} | {f(r.ev_trade)} | {f(r.policy_ev_original_signal)} | {f(r.cum_atr)} | {f(r.pf)} | {f(r.dd_atr)} | {f(r.trigger_rate)} | {f(r.median_hold_h)} |")
    lines += ['', '## ORIGIN_CLOSE2 by window','', '| Window | Trades | EV | Cum | PF | DD | Trigger | L/S |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in win.iterrows():lines.append(f"| {r.window} | {int(r.accept_trades)} | {f(r.ev_trade)} | {f(r.cum_atr)} | {f(r.pf)} | {f(r.dd_atr)} | {f(r.trigger_rate)} | {int(r.long_n)}/{int(r.short_n)} |")
    lines += ['', '## By side','', '| Side | Trades | EV | Cum | PF | DD |','|---|---:|---:|---:|---:|---:|']
    for _,r in side.iterrows():lines.append(f"| {r.side_name} | {int(r.accept_trades)} | {f(r.ev_trade)} | {f(r.cum_atr)} | {f(r.pf)} | {f(r.dd_atr)} |")
    lines += ['', '## Failure persistence states','', '| State | N | Time-only EV | Primary EV | MAE | MFE | Win rate |','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in state.iterrows():lines.append(f"| {r.group} | {int(r.n)} | {f(r.time_only_ev)} | {f(r.primary_ev)} | {f(r.median_mae)} | {f(r.median_mfe)} | {f(r.win_rate)} |")
    lines += ['', '## 7d cluster bootstrap vs HARD_SL15',f"- clusters: **{boot['n_clusters']}**, draws **{boot['draws']}**",f"- EV/trade diff: **{f(boot['point_ev_trade'])} ATR**, 95% CI **[{f(boot['ci_ev_lo'])}, {f(boot['ci_ev_hi'])}]**",f"- policy EV/original-signal diff: **{f(boot['point_policy_ev_signal'])} ATR**, 95% CI **[{f(boot['ci_policy_lo'])}, {f(boot['ci_policy_hi'])}]**",'', '## Gates']
    for k,v in gates.items():lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## Guardrail','ORIGIN_CLOSE2 is frozen from LAB028 audit: two consecutive completed M15 closes through original signal price. No rule/threshold/horizon/side rescue. M1 is parity-only. August 2026 reused audit. Live allocation = **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price=L28.L23.load_price(); allp=L28.load_passage()
    if len(allp)!=EXPECTED_FLOW_N:raise RuntimeError(f'flow lineage {len(allp)} != {EXPECTED_FLOW_N}')
    d=L28.simulate_accept_paths(price,allp); d=add_hold(d)
    pre=d[d.signal_time<PRE_CUT]
    if len(pre)!=EXPECTED_ACCEPT_PRE:raise RuntimeError(f'pre-Aug ACCEPT {len(pre)} != {EXPECTED_ACCEPT_PRE}')
    d.to_csv(OUT/'origin_close2_execution_stream.csv',index=False)
    m1=load_m1_to_m15(); par=m1_parity(d,m1); (OUT/'m1_parity.json').write_text(json.dumps(par,indent=2,allow_nan=True))
    pol=policy_summary(d,allp); pol.to_csv(OUT/'policy_summary.csv',index=False)
    win=window_summary(d,allp); win.to_csv(OUT/'window_summary.csv',index=False)
    side=side_summary(d,allp); side.to_csv(OUT/'side_summary.csv',index=False)
    state=state_summary(d); state.to_csv(OUT/'failure_persistence_state_summary.csv',index=False)
    boot=bootstrap(d,allp); (OUT/'bootstrap_7d.json').write_text(json.dumps(boot,indent=2,allow_nan=True))
    p2=pol[pol['sample']=='ORIGIN_CLOSE2'].iloc[0]; sl=pol[pol['sample']=='HARD_SL15'].iloc[0]; tm=pol[pol['sample']=='TIME_ONLY'].iloc[0]
    retention=float(p2.cum_atr/tm.cum_atr) if tm.cum_atr!=0 else np.nan
    y22=d[(d.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(d.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(d.side==-1)]
    y22m=metric(y22,'origin_close2_net_atr','2022_SHORT','origin_close2_trigger',original_n(allp,pd.Timestamp('2022-01-01',tz=UTC),pd.Timestamp('2023-01-01',tz=UTC),-1))
    recent=d[(d.signal_time>=pd.Timestamp('2025-07-01',tz=UTC))&(d.signal_time<PRE_CUT)]
    recentm=metric(recent,'origin_close2_net_atr','RECENT','origin_close2_trigger',original_n(allp,pd.Timestamp('2025-07-01',tz=UTC),PRE_CUT))
    sL=side[side.side_name=='LONG'].iloc[0]; sS=side[side.side_name=='SHORT'].iloc[0]
    subwins=win[win.window.isin(['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL'])]
    pos_windows=int((subwins.cum_atr>0).sum())
    gates={
      'exact_lineage_and_accept_n':bool(len(allp)==3209 and len(pre)>=1490),
      'm1_m15_close_parity':bool(par['matched_events']>=1400 and np.isfinite(par['close_med_rel']) and par['close_med_rel']<=1e-8),
      'origin_close2_trigger_parity_ge_99pct':bool(np.isfinite(par['trigger_parity']) and par['trigger_parity']>=.99 and np.isfinite(par['time_parity']) and par['time_parity']>=.99),
      'origin_close2_ev_positive':bool(p2.ev_trade>0),
      'origin_close2_pf_gt_1_20':bool(p2.pf>1.20),
      'origin_close2_ev_gt_hardsl15':bool(p2.ev_trade>sl.ev_trade),
      'origin_close2_policy_ev_gt_hardsl15':bool(p2.policy_ev_original_signal>sl.policy_ev_original_signal),
      'origin_close2_dd_le_1_20x_hardsl':bool(p2.dd_atr<=1.20*sl.dd_atr),
      'right_tail_retention_ge_55pct':bool(retention>=.55),
      'bootstrap_point_ev_diff_positive':bool(boot['point_ev_trade']>0),
      'bootstrap_noninferiority_ci_lo_ge_minus_0_05':bool(boot['ci_ev_lo']>=-.05),
      'stress_2022_short_n80_cum_positive_pf_gt_1_25':bool(y22m['accept_trades']>=80 and y22m['cum_atr']>0 and y22m['pf']>1.25),
      'pooled_recent_cum_positive':bool(recentm['cum_atr']>0),
      'long_and_short_ev_positive':bool(sL.ev_trade>0 and sS.ev_trade>0),
      'positive_subwindows_ge_5_of_7':bool(pos_windows>=5),
    }
    score=sum(gates.values()); critical=['exact_lineage_and_accept_n','origin_close2_ev_positive','origin_close2_ev_gt_hardsl15','origin_close2_dd_le_1_20x_hardsl','stress_2022_short_n80_cum_positive_pf_gt_1_25','pooled_recent_cum_positive']
    if score>=12 and all(gates[k] for k in critical):verdict='PASS_TWO_CLOSE_FAILURE_PERSISTENCE_EXECUTION'
    elif score>=9 and p2.ev_trade>0:verdict='WATCH_TWO_CLOSE_EXECUTION_POSITIVE_BUT_NOT_TRANSFERABLE'
    else:verdict='FAIL_TWO_CLOSE_FAILURE_RULE_NOT_ROBUST'
    meta=dict(verdict=verdict,flow_n=len(allp),accept_pre=len(pre),right_tail_retention=retention,positive_subwindows=pos_windows,aug_reused=True,
      y22_short=y22m,recent=recentm)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'m1_parity':par,'bootstrap':boot,'gates':gates},indent=2,allow_nan=True))
    rep=report(pol,win,side,state,boot,par,gates,meta);(OUT/'REPORT.md').write_text(rep,encoding='utf-8');print(rep)

if __name__=='__main__':main()
