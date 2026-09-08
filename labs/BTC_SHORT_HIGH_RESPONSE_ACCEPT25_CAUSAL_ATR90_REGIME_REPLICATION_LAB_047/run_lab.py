#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_HIGH_RESPONSE_ACCEPT25_CAUSAL_ATR90_REGIME_REPLICATION_LAB_047'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
FAIL=LABS/'BTC_SHORT_HIGH_RESPONSE_ACCEPT25_BAD_REGIME_AND_YEARLY_FAILURE_STATE_LAB_045'/'output'/'failure_state_stream.csv'
ROUTER=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043'/'output'/'short_response_router_stream.csv'
PRE=pd.Timestamp('2026-08-01',tz='UTC')
AUG_END=pd.Timestamp('2026-09-01',tz='UTC')
SEED=20260908; BOOT_N=5000; RISK_PCT=0.25
WINS={
 '2021':('2021-01-01','2022-01-01'),
 '2022':('2022-01-01','2023-01-01'),
 '2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),
 '2025_H1':('2025-01-01','2025-07-01'),
 '2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),
 'POOLED_RECENT':('2025-07-01','2026-08-01'),
 'AUG_REUSED':('2026-08-01','2026-09-01')}


def load_inputs():
    d=pd.read_csv(FAIL); r=pd.read_csv(ROUTER)
    for c in ['signal_time','entry_time','regime_time']:
        if c in d.columns:d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['signal_time','touch_time','class_time']:
        if c in r.columns:r[c]=pd.to_datetime(r[c],errors='coerce',utc=True)
    for c in ['flow_id','net_r_5bps','atr_rank_90d']:
        if c in d.columns:d[c]=pd.to_numeric(d[c],errors='coerce')
    for c in ['flow_id','side']:
        if c in r.columns:r[c]=pd.to_numeric(r[c],errors='coerce')
    d=d[d.signal_time<PRE].copy().sort_values('entry_time').reset_index(drop=True)
    orig=r[(r.signal_time<PRE)&(r.side==-1)&(r.response_router.astype(str)=='HIGH_RESPONSE')].copy().sort_values('signal_time').reset_index(drop=True)
    aug=r[(r.signal_time>=PRE)&(r.signal_time<AUG_END)&(r.side==-1)&(r.response_router.astype(str)=='HIGH_RESPONSE')].copy()
    return d,orig,aug


def pf(v):
    v=np.asarray(v,float); pos=v[v>0].sum(); neg=-v[v<0].sum()
    return float(pos/neg) if neg>0 else (np.inf if pos>0 else np.nan)

def maxdd(v):
    v=np.asarray(v,float)
    if len(v)==0:return np.nan
    eq=np.r_[0.0,np.cumsum(v)]; peak=np.maximum.accumulate(eq)
    return float(np.max(peak-eq))

def state_summary(q,original_n,months):
    q=q.sort_values('entry_time'); v=q.net_r_5bps.to_numpy(float)
    n=len(q)
    return dict(n=n,trade_ev=float(np.mean(v)) if n else np.nan,pf=pf(v),cum_r=float(np.sum(v)) if n else 0.0,max_dd_r=maxdd(v),dd_pct_025=float(maxdd(v)*RISK_PCT) if n else np.nan,win_share=float((v>0).mean()) if n else np.nan,tp_share=float((q.exit_reason.astype(str)=='TP').mean()) if n else np.nan,sl_share=float((q.exit_reason.astype(str)=='SL').mean()) if n else np.nan,time_share=float((q.exit_reason.astype(str)=='TIME').mean()) if n else np.nan,ev_per_original=float(np.sum(v)/original_n) if original_n else np.nan,frequency_per_month=float(n/months) if months>0 else np.nan)

def bootstrap_gap(d):
    x=d.dropna(subset=['atr_rank_90d','net_r_5bps','signal_time']).copy()
    x['high']=(x.atr_rank_90d>=0.50)
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    x['cluster']=(((x.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    rows=[]
    for _,g in x.groupby('cluster'):
        h=g[g.high].net_r_5bps.to_numpy(float); l=g[~g.high].net_r_5bps.to_numpy(float)
        rows.append((h.sum(),len(h),l.sum(),len(l)))
    arr=np.asarray(rows,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0:vals.append(float(s[0]/s[1]-s[2]/s[3]))
    vals=np.asarray(vals,float)
    hi=x[x.high].net_r_5bps.mean(); lo=x[~x.high].net_r_5bps.mean(); point=float(hi-lo)
    return dict(point=point,ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)),clusters=m,draws=len(vals))

def period_of(t):
    for name,(aa,bb) in WINS.items():
        if name=='AUG_REUSED':continue
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC')
        if a<=t<b:return name
    return 'OTHER'

def transfer(d,orig):
    rows=[]
    for name,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC')
        od=orig[(orig.signal_time>=a)&(orig.signal_time<b)]
        q=d[(d.signal_time>=a)&(d.signal_time<b)]
        on=len(od)
        for state,mask in [('ALL',pd.Series(True,index=q.index)),('HIGH_ATR',q.atr_rank_90d>=0.50),('LOW_ATR',q.atr_rank_90d<0.50)]:
            z=q[mask].sort_values('entry_time'); v=z.net_r_5bps.to_numpy(float)
            rows.append(dict(slice=name,state=state,original_n=on,trade_n=len(z),trade_ev=float(v.mean()) if len(v) else np.nan,pf=pf(v) if len(v) else np.nan,cum_r=float(v.sum()) if len(v) else 0.0,ev_per_original=float(v.sum()/on) if on else np.nan,max_dd_r=maxdd(v) if len(v) else np.nan))
    return pd.DataFrame(rows)
def tv(tr,slice_,state,col):
    q=tr[(tr['slice']==slice_)&(tr.state==state)]
    return float(q.iloc[0][col]) if len(q) and pd.notna(q.iloc[0][col]) else np.nan
def tn(tr,slice_,state):
    q=tr[(tr['slice']==slice_)&(tr.state==state)]
    return int(q.iloc[0].trade_n) if len(q) else 0

def main():
    d,orig,aug=load_inputs()
    d['atr_state']=np.where(d.atr_rank_90d>=0.50,'HIGH_ATR','LOW_ATR')
    d.to_csv(OUT/'atr90_regime_stream.csv',index=False)
    months=(PRE-d.signal_time.min())/pd.Timedelta(days=30.4375)
    hi=d[d.atr_state=='HIGH_ATR']; lo=d[d.atr_state=='LOW_ATR']
    summ=[]
    for state,q in [('ALL',d),('HIGH_ATR',hi),('LOW_ATR',lo)]:
        z=state_summary(q,len(orig),float(months)); z['state']=state; summ.append(z)
    sm=pd.DataFrame(summ); sm.to_csv(OUT/'state_summary.csv',index=False)
    boot=bootstrap_gap(d); (OUT/'bootstrap.json').write_text(json.dumps(boot,indent=2))
    tr=transfer(d,orig); tr.to_csv(OUT/'transfer.csv',index=False)
    S={r.state:r for r in sm.itertuples(index=False)}
    gates={
      'exact_frozen_accept25_preaug_n327':len(d)==327,
      'atr_rank_coverage_ge99pct':float(d.atr_rank_90d.notna().mean())>=.99,
      'exact_high_response_original_preaug_n475':len(orig)==475,
      'high_atr_n_ge120':len(hi)>=120,
      'low_atr_n_ge100':len(lo)>=100,
      'high_atr_trade_ev_positive':S['HIGH_ATR'].trade_ev>0,
      'high_atr_pf_ge1_15':S['HIGH_ATR'].pf>=1.15,
      'high_atr_ev_gt_low_atr':S['HIGH_ATR'].trade_ev>S['LOW_ATR'].trade_ev,
      'high_low_gap_ge0_15r':boot['point']>=.15,
      'bootstrap_lower_gt0':boot['ci_lo']>0,
      'high_atr_ev_per_original_ge0_055':S['HIGH_ATR'].ev_per_original>=.055,
      'high_atr_dd025_le4pct':S['HIGH_ATR'].dd_pct_025<=4.0,
      'high_atr_2022_not_worse_parent':tv(tr,'2022','HIGH_ATR','ev_per_original')>=tv(tr,'2022','ALL','ev_per_original'),
      'high_atr_2023_not_worse_parent':tv(tr,'2023','HIGH_ATR','ev_per_original')>=tv(tr,'2023','ALL','ev_per_original'),
      'high_atr_2025h1_not_worse_parent':tv(tr,'2025_H1','HIGH_ATR','ev_per_original')>=tv(tr,'2025_H1','ALL','ev_per_original'),
      'high_atr_2025h2_positive':tv(tr,'2025_H2','HIGH_ATR','ev_per_original')>0,
      'high_atr_2026_positive':tv(tr,'2026_JAN_JUL','HIGH_ATR','ev_per_original')>0,
      'high_atr_recent_positive_n30':tn(tr,'POOLED_RECENT','HIGH_ATR')>=30 and tv(tr,'POOLED_RECENT','HIGH_ATR','ev_per_original')>0,
      'low_atr_ev_le_high_atr':S['LOW_ATR'].trade_ev<=S['HIGH_ATR'].trade_ev,
      'august_not_used_for_selection':True}
    critical=['exact_frozen_accept25_preaug_n327','atr_rank_coverage_ge99pct','exact_high_response_original_preaug_n475','high_atr_trade_ev_positive','high_atr_pf_ge1_15','high_atr_ev_gt_low_atr','bootstrap_lower_gt0','high_atr_2025h2_positive','high_atr_2026_positive']
    score=sum(bool(v) for v in gates.values())
    if score>=16 and all(gates[k] for k in critical): verdict='PASS_CAUSAL_ATR90_REGIME_REPLICATION'
    elif score>=11 or (S['HIGH_ATR'].trade_ev>0 and S['HIGH_ATR'].trade_ev>S['LOW_ATR'].trade_ev): verdict='WATCH_ATR90_REGIME_POSITIVE_PROOF_INCOMPLETE'
    else: verdict='FAIL_ATR90_REGIME_NO_REPLICATION'
    meta=dict(verdict=verdict,score=score,total=len(gates),formal_n=len(d),original_n=len(orig),aug_original_n=len(aug),bootstrap=boot,gates=gates)
    (OUT/'metrics.json').write_text(json.dumps(meta,indent=2))
    def f(x,n=3): return '—' if pd.isna(x) else f'{x:+.{n}f}'
    L=[f'# {LAB}','',f'**Verdict: {verdict} — {score}/{len(gates)}**','', '## Frozen parity',f'- ACCEPT2.5 pre-Aug trades: **{len(d)}**; original HIGH_RESPONSE SHORT signals: **{len(orig)}**',f'- ATR-rank coverage: **{d.atr_rank_90d.notna().mean():.1%}**; August original audit signals: **{len(aug)}**','', '## Fixed ATR90 split','', '| State | N | Trade EV | PF | CumR | MaxDD R | DD@0.25% | EV/original | Freq/mo |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in sm.iterrows():
        L.append(f"| {r.state} | {int(r.n)} | {f(r.trade_ev)} | {r.pf:.3f} | {f(r.cum_r,2)} | {r.max_dd_r:.2f} | {r.dd_pct_025:.2f}% | {f(r.ev_per_original)} | {r.frequency_per_month:.2f} |")
    L+=['', '## Primary separation',f"- HIGH_ATR − LOW_ATR trade EV gap: **{f(boot['point'])}R**",f"- 7d cluster bootstrap 95% CI: **[{f(boot['ci_lo'])}, {f(boot['ci_hi'])}]**, clusters={boot['clusters']}, draws={boot['draws']}",'', '## Fixed transfer (EV per original HIGH_RESPONSE signal)','', '| Slice | ALL | HIGH_ATR | LOW_ATR | High N | Low N |','|---|---:|---:|---:|---:|---:|']
    for name in WINS:
        if name=='AUG_REUSED' and len(aug)==0: continue
        L.append(f"| {name} | {f(tv(tr,name,'ALL','ev_per_original'))} | {f(tv(tr,name,'HIGH_ATR','ev_per_original'))} | {f(tv(tr,name,'LOW_ATR','ev_per_original'))} | {tn(tr,name,'HIGH_ATR')} | {tn(tr,name,'LOW_ATR')} |")
    L+=['','## Gates']
    for k,v in gates.items():L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    L+=['','## Guardrail','Fixed 0.50 ATR-rank split only. No alternative percentile, stop, target, entry, or time-exit searched. Reused historical lineage; not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L))
    print(verdict,score,'/',len(gates)); print('HIGH',S['HIGH_ATR'].trade_ev,S['HIGH_ATR'].pf,'LOW',S['LOW_ATR'].trade_ev,S['LOW_ATR'].pf,'GAP',boot)

if __name__=='__main__': main()
