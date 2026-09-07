#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_ACCEPTANCE_CONFIRM_ENTRY_AND_ADVERSE_VETO_EXECUTION_LAB_027'
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
    sd=a.std(ddof=1)
    return float(a.mean()/(sd/math.sqrt(len(a)))) if sd>0 else np.nan

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

def stop_path(price,start_t,end_t,side,stop):
    q=price.loc[(price.index>=start_t)&(price.index<=end_t)]
    for t,z in q.iterrows():
        hit=(float(z.low)<=stop) if side>0 else (float(z.high)>=stop)
        if hit:return True,t
    return False,end_t

def simulate(price,d):
    pos=pd.Series(np.arange(len(price),dtype=int),index=price.index)
    rows=[]
    for r in d.itertuples():
        t=pd.Timestamp(r.signal_time); side=int(r.side); atr=float(r.atr14); sig=float(r.signal_close)
        if t not in pos.index or not np.isfinite(atr) or atr<=0:continue
        exit_t=t+pd.Timedelta(hours=12)
        if exit_t not in pos.index:continue
        exit_close=float(price.loc[exit_t,'close'])
        cost_imm=(sig*(COST_BPS/10000.0))/atr
        imm_no=float(side*(exit_close-sig)/atr-cost_imm)
        imm_stop=sig-side*STOP_ATR*atr
        # immediate stop starts on the next full M15 bar because signal entry is at signal-bar close.
        next_i=int(pos.loc[t])+1
        imm_start=price.index[next_i] if next_i<len(price) else exit_t
        hit_i,hit_t=stop_path(price,imm_start,exit_t,side,imm_stop)
        imm_exit=imm_stop if hit_i else exit_close
        imm_bd=float(side*(imm_exit-sig)/atr-cost_imm)

        accept_no=np.nan; accept_bd=np.nan; acc_stop=False; acc_hold=np.nan; entry_bar_amb=False; accept_entry=np.nan
        if r.state=='ACCEPT_FIRST' and pd.notna(r.passage_time):
            pt=pd.Timestamp(r.passage_time)
            if pt in pos.index and pt<=exit_t:
                accept_entry=float(sig+side*THR_ATR*atr)
                acc_stop_px=float(accept_entry-side*STOP_ATR*atr)
                z=price.loc[pt]
                entry_bar_amb=bool((float(z.low)<=acc_stop_px) if side>0 else (float(z.high)>=acc_stop_px))
                if not entry_bar_amb:
                    cost_acc=(accept_entry*(COST_BPS/10000.0))/atr
                    accept_no=float(side*(exit_close-accept_entry)/atr-cost_acc)
                    hit_a,hit_at=stop_path(price,pt,exit_t,side,acc_stop_px)
                    acc_stop=bool(hit_a)
                    acc_exit=acc_stop_px if hit_a else exit_close
                    accept_bd=float(side*(acc_exit-accept_entry)/atr-cost_acc)
                    acc_hold=float(((hit_at if hit_a else exit_t)-pt).total_seconds()/3600.0)
        rows.append(dict(
            flow_id=int(r.flow_id),signal_time=t,side=side,state=str(r.state),signal_close=sig,atr14=atr,
            passage_time=r.passage_time,accept_entry=accept_entry,entry_bar_ambiguous=entry_bar_amb,
            accept_nostop_net_atr=accept_no,accept_bounded_net_atr=accept_bd,accept_stopped=acc_stop,accept_hold_h=acc_hold,
            immediate_nostop_net_atr=imm_no,immediate_bounded_net_atr=imm_bd,immediate_stopped=bool(hit_i),
            frozen_total12_atr=float(r.total12_atr),frozen_residual12_atr=float(r.residual12_atr) if np.isfinite(r.residual12_atr) else np.nan
        ))
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)

def summarize(q,pnl_col,label,trade_col=None,stop_col=None,hold_col=None):
    n_sig=len(q)
    if trade_col is None:
        mask=pd.to_numeric(q[pnl_col],errors='coerce').notna()
    else:
        mask=q[trade_col].astype(bool)
    a=pd.to_numeric(q.loc[mask,pnl_col],errors='coerce').dropna().to_numpy(float)
    policy=pd.to_numeric(q[pnl_col],errors='coerce').fillna(0.0).to_numpy(float)
    return dict(sample=label,signals=n_sig,trades=len(a),utilization=float(len(a)/n_sig) if n_sig else np.nan,
                ev_trade=float(a.mean()) if len(a) else np.nan,policy_ev_signal=float(policy.mean()) if len(policy) else np.nan,
                cum_atr=float(policy.sum()),t_trade=tstat(a),pf_trade=pf(a),maxdd_policy_atr=maxdd(policy),
                stop_rate=float(q.loc[mask,stop_col].mean()) if stop_col and len(a) else np.nan,
                median_hold_h=float(q.loc[mask,hold_col].median()) if hold_col and len(a) else np.nan,
                long_trades=int(((q.side==1)&mask).sum()),short_trades=int(((q.side==-1)&mask).sum()))

def overall_summary(d):
    pre=d[d.signal_time<PRE_CUT].copy()
    return pd.DataFrame([
        summarize(pre,'accept_bounded_net_atr','ACCEPT_BOUNDED',stop_col='accept_stopped',hold_col='accept_hold_h'),
        summarize(pre,'accept_nostop_net_atr','ACCEPT_NOSTOP',hold_col='accept_hold_h'),
        summarize(pre,'immediate_bounded_net_atr','IMMEDIATE_BOUNDED',stop_col='immediate_stopped'),
        summarize(pre,'immediate_nostop_net_atr','IMMEDIATE_NOSTOP'),
    ])

def window_summary(d):
    rows=[]
    for w,(a,b) in WINS.items():
        a=pd.Timestamp(a,tz=UTC); b=pd.Timestamp(b,tz=UTC); q=d[(d.signal_time>=a)&(d.signal_time<b)].copy()
        x=summarize(q,'accept_bounded_net_atr',w,stop_col='accept_stopped',hold_col='accept_hold_h'); x['window']=w; rows.append(x)
    return pd.DataFrame(rows)

def side_summary(d):
    pre=d[d.signal_time<PRE_CUT]; rows=[]
    for side,name in [(1,'LONG'),(-1,'SHORT')]:
        q=pre[pre.side==side]; x=summarize(q,'accept_bounded_net_atr',name,stop_col='accept_stopped',hold_col='accept_hold_h'); x['side_name']=name; rows.append(x)
    return pd.DataFrame(rows)

def bootstrap_diff(d):
    q=d[d.signal_time<PRE_CUT].copy()
    q['acc']=pd.to_numeric(q.accept_bounded_net_atr,errors='coerce').fillna(0.0)
    q['imm']=pd.to_numeric(q.immediate_bounded_net_atr,errors='coerce').fillna(0.0)
    q['cluster']=(q.signal_time.astype('int64')//int(pd.Timedelta(days=7).value)).astype('int64')
    g=q.groupby('cluster').agg(n=('flow_id','size'),acc_sum=('acc','sum'),imm_sum=('imm','sum')).reset_index(drop=True)
    rng=np.random.default_rng(SEED); vals=[]; m=len(g)
    for _ in range(BOOT_N):
        ix=rng.integers(0,m,m); z=g.iloc[ix]; den=float(z.n.sum())
        if den>0:vals.append(float((z.acc_sum.sum()-z.imm_sum.sum())/den))
    point=float(q.acc.mean()-q.imm.mean())
    return dict(n_clusters=m,draws=len(vals),point_diff=point,ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)))

def get(tab,name):
    q=tab[tab['sample']==name]; return q.iloc[0] if len(q) else None

def getwin(tab,name):
    q=tab[tab.window==name]; return q.iloc[0] if len(q) else None

def report(ov,ws,ss,boot,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)} scored gates**",'',
           '## Frozen parity',f"- lineage rows: **{meta['lineage_n']}**, pre-Aug **{meta['pre_aug_n']}**",f"- timestamp parity: **{meta['timestamp_parity']:.2%}**",f"- acceptance-threshold parity max abs error: **{meta['threshold_parity_max']:.8f}**",f"- entry-bar ambiguous ACCEPT events: **{meta['entry_bar_ambiguous']}**",'',
           '## Pre-Aug policy economics','', '| Policy | Signals | Trades | Util | EV/trade | Policy EV/signal | Cum ATR | PF | DD ATR | Stop | Hold h |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in ov.iterrows():
        lines.append(f"| {r['sample']} | {int(r.signals)} | {int(r.trades)} | {f(r.utilization)} | {f(r.ev_trade)} | {f(r.policy_ev_signal)} | {f(r.cum_atr)} | {f(r.pf_trade)} | {f(r.maxdd_policy_atr)} | {f(r.stop_rate)} | {f(r.median_hold_h)} |")
    lines += ['', '## Primary bounded ACCEPT by window','', '| Window | Signals | Trades | Util | EV/trade | Policy EV/signal | Cum ATR | PF | DD | Stop | L/S |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in ws.iterrows():lines.append(f"| {r.window} | {int(r.signals)} | {int(r.trades)} | {f(r.utilization)} | {f(r.ev_trade)} | {f(r.policy_ev_signal)} | {f(r.cum_atr)} | {f(r.pf_trade)} | {f(r.maxdd_policy_atr)} | {f(r.stop_rate)} | {int(r.long_trades)}/{int(r.short_trades)} |")
    lines += ['', '## Primary bounded ACCEPT pre-Aug by side','', '| Side | Signals | Trades | EV/trade | Policy EV/signal | Cum ATR | PF | DD | Stop |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in ss.iterrows():lines.append(f"| {r.side_name} | {int(r.signals)} | {int(r.trades)} | {f(r.ev_trade)} | {f(r.policy_ev_signal)} | {f(r.cum_atr)} | {f(r.pf_trade)} | {f(r.maxdd_policy_atr)} | {f(r.stop_rate)} |")
    lines += ['', '## 7d cluster bootstrap',f"- clusters: **{boot['n_clusters']}**, draws: **{boot['draws']}**",f"- ACCEPT bounded policy EV/signal minus immediate bounded: **{f(boot['point_diff'])} ATR**, 95% CI **[{f(boot['ci_lo'])}, {f(boot['ci_hi'])}]**",'', '## Gates']
    for k,v in gates.items():lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## August 2026 reused audit',f"Reported separately; scientific verdict cannot be rescued or failed by August. Trades={meta['aug_trades']}, Cum={f(meta['aug_cum_atr'])} ATR, EV/trade={f(meta['aug_ev_trade'])}.",'',
              '## Guardrail','Primary is bounded: ACCEPT_FIRST only, market entry at frozen +0.5 ATR threshold, emergency SL 1.5 ATR from entry, no TP, original signal +12h time exit, 5 bps RT cost. ADVERSE_FIRST/AMBIGUOUS/NONE = veto. No threshold/stop/horizon optimization. This remains reused research lineage; no full floating-equity FTMO daily-DD simulation. Live allocation = **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price=L23.load_price(); p=load_passage()
    if len(p)!=EXPECTED_N:raise RuntimeError(f'LAB026 lineage {len(p)} != {EXPECTED_N}')
    ts_parity=float(p.signal_time.isin(price.index).mean())
    if ts_parity<.99:raise RuntimeError(f'timestamp parity {ts_parity:.3%}')
    # Frozen threshold relation must equal residual accounting identity for accepted events.
    a=p[p.state=='ACCEPT_FIRST'].copy()
    ident=(a.total12_atr-(THR_ATR+a.residual12_atr)).abs()
    thr_parity=float(ident.max()) if len(ident) else np.nan
    if not np.isfinite(thr_parity) or thr_parity>1e-8:raise RuntimeError(f'acceptance threshold parity failed {thr_parity}')
    d=simulate(price,p)
    d.to_csv(OUT/'execution_event_stream.csv',index=False)
    pre=d[d.signal_time<PRE_CUT]
    if len(pre)<3000:raise RuntimeError(f'pre-Aug rows only {len(pre)}')
    ov=overall_summary(d); ov.to_csv(OUT/'overall_policy_summary.csv',index=False)
    ws=window_summary(d); ws.to_csv(OUT/'primary_by_window.csv',index=False)
    ss=side_summary(d); ss.to_csv(OUT/'primary_by_side.csv',index=False)
    boot=bootstrap_diff(d); (OUT/'bootstrap_7d.json').write_text(json.dumps(boot,indent=2,allow_nan=True),encoding='utf-8')

    acc=get(ov,'ACCEPT_BOUNDED'); acc_no=get(ov,'ACCEPT_NOSTOP'); imm=get(ov,'IMMEDIATE_BOUNDED')
    y22=d[(d.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(d.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(d.side==-1)]
    y22s=summarize(y22,'accept_bounded_net_atr','2022_SHORT',stop_col='accept_stopped',hold_col='accept_hold_h')
    recent=d[(d.signal_time>=pd.Timestamp('2025-07-01',tz=UTC))&(d.signal_time<PRE_CUT)]
    rec=summarize(recent,'accept_bounded_net_atr','RECENT',stop_col='accept_stopped',hold_col='accept_hold_h')
    lng=ss[ss.side_name=='LONG'].iloc[0]; sht=ss[ss.side_name=='SHORT'].iloc[0]
    aug=d[(d.signal_time>=pd.Timestamp('2026-08-01',tz=UTC))&(d.signal_time<pd.Timestamp('2026-09-01',tz=UTC))]
    augs=summarize(aug,'accept_bounded_net_atr','AUG',stop_col='accept_stopped',hold_col='accept_hold_h')
    amb=int(((d.state=='ACCEPT_FIRST')&d.entry_bar_ambiguous).sum())
    gates={
      'exact_lab026_lineage_and_parity':bool(len(p)==3209 and len(pre)>=3000 and ts_parity>=.99 and thr_parity<=1e-8),
      'accept_executable_count_ge_1000':bool(acc.trades>=1000),
      'signal_utilization_ge_35pct':bool(acc.utilization>=.35),
      'bounded_accept_ev_trade_positive':bool(acc.ev_trade>0),
      'bounded_accept_pf_gt_1_20':bool(np.isfinite(acc.pf_trade) and acc.pf_trade>1.20),
      'bounded_accept_policy_ev_signal_positive':bool(acc.policy_ev_signal>0),
      'bounded_accept_policy_ev_gt_immediate':bool(acc.policy_ev_signal>imm.policy_ev_signal),
      'bounded_accept_dd_le_immediate':bool(acc.maxdd_policy_atr<=imm.maxdd_policy_atr),
      'nostop_accept_ev_trade_positive':bool(acc_no.ev_trade>0),
      'stress_2022_short_n80_and_cum_positive':bool(y22s['trades']>=80 and y22s['cum_atr']>0),
      'pooled_recent_cum_positive':bool(rec['cum_atr']>0),
      'long_bounded_accept_ev_positive':bool(lng.ev_trade>0),
      'short_bounded_accept_ev_positive':bool(sht.ev_trade>0),
      'bootstrap_accept_minus_immediate_ci_lower_gt_zero':bool(boot['ci_lo']>0),
    }
    score=sum(gates.values()); critical=['exact_lab026_lineage_and_parity','accept_executable_count_ge_1000','bounded_accept_ev_trade_positive','bounded_accept_policy_ev_signal_positive','stress_2022_short_n80_and_cum_positive','pooled_recent_cum_positive']
    if score>=11 and all(gates[k] for k in critical):verdict='PASS_ACCEPTANCE_GATED_BOUNDED_EXECUTION'
    elif acc_no.ev_trade>0 and (not all(gates[k] for k in critical) or not gates['bounded_accept_ev_trade_positive']):verdict='WATCH_ACCEPTANCE_DRIFT_SURVIVES_BUT_BOUNDED_EXECUTION_WEAK'
    elif acc_no.ev_trade>0:verdict='WATCH_ACCEPTANCE_EXECUTION_PARTIAL'
    else:verdict='FAIL_ACCEPTANCE_CONFIRM_EXECUTION_NO_TRANSFER'
    meta=dict(verdict=verdict,lineage_n=len(p),pre_aug_n=len(pre),timestamp_parity=ts_parity,threshold_parity_max=thr_parity,entry_bar_ambiguous=amb,aug_reused_audit=True,aug_trades=int(augs['trades']),aug_cum_atr=float(augs['cum_atr']),aug_ev_trade=float(augs['ev_trade']) if np.isfinite(augs['ev_trade']) else np.nan)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates,'2022_short':y22s,'recent':rec,'bootstrap':boot},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(ov,ws,ss,boot,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__':main()
