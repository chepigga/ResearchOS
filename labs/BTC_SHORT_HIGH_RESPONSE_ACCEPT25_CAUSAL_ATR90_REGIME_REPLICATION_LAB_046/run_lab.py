#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_HIGH_RESPONSE_ACCEPT25_CAUSAL_ATR90_REGIME_REPLICATION_LAB_046'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC45=LABS/'BTC_SHORT_HIGH_RESPONSE_ACCEPT25_BAD_REGIME_AND_YEARLY_FAILURE_STATE_LAB_045'/'output'/'failure_state_stream.csv'
SRC44=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044'/'output'/'execution_stream.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC'); SEED=20260909; BOOT_N=5000; RISK_PCT=0.25; ORIGINAL_HIGH_RESPONSE_N=475
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01')}


def load():
    a=pd.read_csv(SRC45); e=pd.read_csv(SRC44)
    for d in [a,e]:
        for c in ['signal_time','entry_time','regime_time','exit_time']:
            if c in d.columns:d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['flow_id','net_r_5bps','atr_rank_90d']:
        if c in a.columns:a[c]=pd.to_numeric(a[c],errors='coerce')
    for c in ['flow_id','stop_atr','net_r_0bps','net_r_5bps','net_r_10bps']:
        if c in e.columns:e[c]=pd.to_numeric(e[c],errors='coerce')
    a=a[a.signal_time<PRE].copy().sort_values('signal_time').reset_index(drop=True)
    e=e[(e.signal_time<PRE)&(e.clock=='ACCEPT')&(e.stop_atr==2.5)&(e.traded.astype(str).str.lower().isin(['true','1']))].copy()
    e=e[['flow_id','entry_time','net_r_0bps','net_r_5bps','net_r_10bps']].drop_duplicates('flow_id')
    m=a.merge(e,on='flow_id',how='left',suffixes=('_45','_44'),validate='one_to_one')
    m['payoff_parity']=(m.net_r_5bps_45-m.net_r_5bps_44).abs()<=1e-10
    m['entry_parity']=(m.entry_time_45==m.entry_time_44)
    m['frozen_parity']=m.payoff_parity&m.entry_parity&m.net_r_0bps.notna()&m.net_r_10bps.notna()
    m['signal_time']=m.signal_time
    m['entry_time']=m.entry_time_45
    m['net_r_5bps']=m.net_r_5bps_44
    m['atr_state']=np.where(m.atr_rank_90d>=0.50,'HIGH_ATR90','LOW_ATR90')
    return m.sort_values('signal_time').reset_index(drop=True)


def pf(v):
    v=np.asarray(v,float); pos=v[v>0].sum(); neg=-v[v<0].sum()
    return float(pos/neg) if neg>0 else (np.inf if pos>0 else np.nan)


def maxdd(v):
    v=np.asarray(v,float)
    if not len(v):return np.nan
    eq=np.r_[0.0,np.cumsum(v)]; pk=np.maximum.accumulate(eq); return float(np.max(pk-eq))


def summarize(q,label,full_sum):
    q=q.sort_values('signal_time'); v=q.net_r_5bps.to_numpy(float); dd=maxdd(v); s=float(v.sum()) if len(v) else 0.0
    return dict(state=label,n=len(q),share=float(len(q)/327),ev0=float(q.net_r_0bps.mean()) if len(q) else np.nan,
                ev5=float(q.net_r_5bps.mean()) if len(q) else np.nan,ev10=float(q.net_r_10bps.mean()) if len(q) else np.nan,
                pf5=pf(v),win_rate=float((v>0).mean()) if len(v) else np.nan,cum_r5=s,max_dd_r5=dd,
                dd_pct_025=float(dd*RISK_PCT) if np.isfinite(dd) else np.nan,
                contribution_full=float(s/full_sum) if full_sum!=0 else np.nan,
                ev_per_original475=float(s/ORIGINAL_HIGH_RESPONSE_N))


def bootstrap(d):
    q=d.dropna(subset=['net_r_5bps','signal_time']).copy(); epoch=pd.Timestamp('1970-01-01',tz='UTC')
    q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    arr=[]
    for _,g in q.groupby('cluster'):
        h=g[g.atr_state=='HIGH_ATR90'].net_r_5bps.to_numpy(float); l=g[g.atr_state=='LOW_ATR90'].net_r_5bps.to_numpy(float)
        arr.append((h.sum(),len(h),l.sum(),len(l)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        z=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if z[1]>0 and z[3]>0: vals.append(float(z[0]/z[1]-z[2]/z[3]))
    v=np.asarray(vals,float); hi=q[q.atr_state=='HIGH_ATR90'].net_r_5bps.mean(); lo=q[q.atr_state=='LOW_ATR90'].net_r_5bps.mean()
    return dict(point=float(hi-lo),clusters=m,draws=len(v),ci_lo=float(np.quantile(v,.025)),ci_hi=float(np.quantile(v,.975)))


def transfer(d):
    rows=[]
    for name,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); z=d[(d.signal_time>=a)&(d.signal_time<b)]
        for st in ['HIGH_ATR90','LOW_ATR90']:
            q=z[z.atr_state==st].sort_values('signal_time'); v=q.net_r_5bps.to_numpy(float)
            rows.append(dict(slice=name,state=st,n=len(q),ev5=float(v.mean()) if len(v) else np.nan,pf5=pf(v),cum_r5=float(v.sum()) if len(v) else 0.0,win=float((v>0).mean()) if len(v) else np.nan))
    # Fixed BAD composite from LAB045 labels: 2022 + 2023 + 2025H1.
    bad=d[d.period_state=='BAD']
    for st in ['HIGH_ATR90','LOW_ATR90']:
        q=bad[bad.atr_state==st].sort_values('signal_time'); v=q.net_r_5bps.to_numpy(float)
        rows.append(dict(slice='BAD_COMPOSITE',state=st,n=len(q),ev5=float(v.mean()) if len(v) else np.nan,pf5=pf(v),cum_r5=float(v.sum()) if len(v) else 0.0,win=float((v>0).mean()) if len(v) else np.nan))
    return pd.DataFrame(rows)


def trval(tr,sl,st,col):
    q=tr[(tr['slice']==sl)&(tr.state==st)]; return float(q.iloc[0][col]) if len(q) and pd.notna(q.iloc[0][col]) else np.nan

def trn(tr,sl,st):
    q=tr[(tr['slice']==sl)&(tr.state==st)]; return int(q.iloc[0].n) if len(q) else 0

def py(x):
    if isinstance(x,np.bool_):return bool(x)
    if isinstance(x,np.integer):return int(x)
    if isinstance(x,np.floating):return None if not np.isfinite(x) else float(x)
    raise TypeError(type(x).__name__)


def main():
    d=load(); d.to_csv(OUT/'atr90_router_stream.csv',index=False)
    full_sum=float(d.net_r_5bps.sum())
    sm=pd.DataFrame([summarize(d,'ALL',full_sum),summarize(d[d.atr_state=='HIGH_ATR90'],'HIGH_ATR90',full_sum),summarize(d[d.atr_state=='LOW_ATR90'],'LOW_ATR90',full_sum)])
    sm.to_csv(OUT/'router_summary.csv',index=False)
    bt=bootstrap(d); (OUT/'bootstrap.json').write_text(json.dumps(bt,indent=2),encoding='utf-8')
    tr=transfer(d); tr.to_csv(OUT/'transfer.csv',index=False)
    hi=sm[sm.state=='HIGH_ATR90'].iloc[0]; lo=sm[sm.state=='LOW_ATR90'].iloc[0]
    parity=float(d.frozen_parity.mean()) if len(d) else 0.0; cov=float(d.atr_rank_90d.notna().mean()) if len(d) else 0.0
    gates={
      'exact_formal_accept25_n_327':len(d)==327,
      'atr_rank_90d_coverage_100pct':cov==1.0,
      'frozen_lab044_payoff_entry_parity_100pct':parity==1.0,
      'high_atr_n_ge_130':int(hi.n)>=130,
      'low_atr_n_ge_130':int(lo.n)>=130,
      'high_atr_ev5_positive':float(hi.ev5)>0,
      'high_atr_pf5_ge_1_20':float(hi.pf5)>=1.20,
      'low_atr_ev5_le_zero':float(lo.ev5)<=0,
      'high_minus_low_gap_ge_0_20r':bt['point']>=.20,
      'cluster_boot_ci_lower_gt_zero':bt['ci_lo']>0,
      'high_atr_ev10_positive':float(hi.ev10)>0,
      'high_atr_dd_025_le_4pct':float(hi.dd_pct_025)<=4.0,
      'high_atr_ev_per_original475_ge_0_05':float(hi.ev_per_original475)>=.05,
      'high_atr_captures_ge_75pct_full_cumr':float(hi.contribution_full)>=.75,
      '2021_high_ev_positive':trval(tr,'2021','HIGH_ATR90','ev5')>0,
      '2022_high_ev_positive':trval(tr,'2022','HIGH_ATR90','ev5')>0,
      '2023_high_ev_positive':trval(tr,'2023','HIGH_ATR90','ev5')>0,
      '2024_high_ev_positive':trval(tr,'2024','HIGH_ATR90','ev5')>0,
      '2025h1_high_ev_positive':trval(tr,'2025_H1','HIGH_ATR90','ev5')>0,
      '2025h2_high_ev_positive':trval(tr,'2025_H2','HIGH_ATR90','ev5')>0,
      '2026_high_ev_positive':trval(tr,'2026_JAN_JUL','HIGH_ATR90','ev5')>0,
      'pooled_recent_high_positive_n30':trn(tr,'POOLED_RECENT','HIGH_ATR90')>=30 and trval(tr,'POOLED_RECENT','HIGH_ATR90','ev5')>0,
      'bad_composite_high_ev_gt_low':trval(tr,'BAD_COMPOSITE','HIGH_ATR90','ev5')>trval(tr,'BAD_COMPOSITE','LOW_ATR90','ev5'),
      'august_not_used_for_selection':True}
    score=sum(bool(v) for v in gates.values())
    critical=['exact_formal_accept25_n_327','atr_rank_90d_coverage_100pct','frozen_lab044_payoff_entry_parity_100pct','high_atr_ev5_positive','high_atr_pf5_ge_1_20','high_minus_low_gap_ge_0_20r','cluster_boot_ci_lower_gt_zero','high_atr_ev10_positive','high_atr_dd_025_le_4pct','high_atr_ev_per_original475_ge_0_05','2025h2_high_ev_positive','2026_high_ev_positive','pooled_recent_high_positive_n30']
    if score>=20 and all(gates[k] for k in critical): verdict='PASS_CAUSAL_ATR90_REGIME_ROUTER_REPLICATION'
    elif score>=14 or gates['high_atr_ev5_positive']: verdict='WATCH_ATR90_REGIME_POSITIVE_PROOF_INCOMPLETE'
    else: verdict='FAIL_ATR90_REGIME_NO_REPLICATION'
    meta=dict(verdict=verdict,score=score,n=len(d),coverage=cov,parity=parity,bootstrap=bt)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')
    L=[f'# {LAB}','',f'**Verdict: {verdict} — {score}/{len(gates)}**','', '## Frozen router summary','',
       '| State | N | Share | EV0 | EV5 | EV10 | PF5 | Win | CumR5 | MaxDD R | DD@0.25% | Contribution | EV/orig475 |',
       '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in sm.iterrows():
        L.append(f'| {r.state} | {int(r.n)} | {r.share:.3f} | {r.ev0:+.3f} | {r.ev5:+.3f} | {r.ev10:+.3f} | {r.pf5:.3f} | {r.win_rate:.3f} | {r.cum_r5:+.2f} | {r.max_dd_r5:.2f} | {r.dd_pct_025:.2f}% | {r.contribution_full:.3f} | {r.ev_per_original475:+.3f} |')
    L+=['','## 7d cluster bootstrap',f'- HIGH_ATR90 − LOW_ATR90 EV5: **{bt["point"]:+.3f} R**, 95% CI **[{bt["ci_lo"]:+.3f}, {bt["ci_hi"]:+.3f}]**, clusters={bt["clusters"]}','', '## Fixed transfer','',
        '| Slice | State | N | EV5 | PF5 | CumR5 | Win |','|---|---|---:|---:|---:|---:|---:|']
    for _,r in tr.iterrows():L.append(f'| {r["slice"]} | {r.state} | {int(r.n)} | {r.ev5:+.3f} | {r.pf5:.3f} | {r.cum_r5:+.2f} | {r.win:.3f} |')
    L+=['','## Gates']+[f'- {"PASS" if v else "FAIL"} — `{k}`' for k,v in gates.items()]+['','## Guardrail','Single fixed ATR90 rank boundary = 0.50, reused exactly from LAB045 causal pre-entry regime clock. No alternate threshold/feature/execution search. Reused historical replication, not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':verdict,'score':score,'bootstrap':bt,'high':hi.to_dict(),'low':lo.to_dict(),'gates':gates},indent=2,default=py))

if __name__=='__main__':main()
