#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC43=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043'/'output'/'short_response_router_stream.csv'
SRC35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'output'/'activation_stream.csv'
R35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab035',R35); L35=importlib.util.module_from_spec(spec); spec.loader.exec_module(L35); L35.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC'); AUG_END=pd.Timestamp('2026-09-01',tz='UTC')
STOP_GRID=[1.5,2.0,2.5,3.0]; TP_R=1.5; PRIMARY_BPS=5.0; RISK_PCT=0.25
WINS={'2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),'2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),'2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}


def load_inputs():
    r=pd.read_csv(SRC43); a=pd.read_csv(SRC35)
    for d in [r,a]:
        for c in ['signal_time','touch_time','class_time']:
            if c in d.columns:d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['flow_id','side','residual_atr']:
        if c in r.columns:r[c]=pd.to_numeric(r[c],errors='coerce')
    for c in ['flow_id','side','atr14','level','class_price','signal_close']:
        if c in a.columns:a[c]=pd.to_numeric(a[c],errors='coerce')
    r=r[(r.side==-1)&(r.response_router=='HIGH_RESPONSE')].copy()
    keep=['flow_id','signal_time','side','state','touch_time','class_time','atr14','level','class_price','signal_close']
    a=a[keep].copy()
    m=r.merge(a,on='flow_id',how='left',suffixes=('_r','_a'),validate='one_to_one')
    # exact frozen parity
    def tseq(x,y):
        return (x.isna()&y.isna()) | (x==y)
    m['parity_signal']=tseq(m.signal_time_r,m.signal_time_a)
    m['parity_touch']=tseq(m.touch_time_r,m.touch_time_a)
    m['parity_class']=tseq(m.class_time_r,m.class_time_a)
    m['parity_state']=m.state_r.astype(str).eq(m.state_a.astype(str))
    m['parity_all']=m[['parity_signal','parity_touch','parity_class','parity_state']].all(axis=1)
    m['signal_time']=m.signal_time_a; m['touch_time']=m.touch_time_a; m['class_time']=m.class_time_a; m['state']=m.state_a
    return m.sort_values('signal_time').reset_index(drop=True)


def barrier_path(fut, entry_time, horizon, clock):
    if pd.isna(entry_time) or pd.isna(horizon):return fut.iloc[0:0]
    if clock=='ACCEPT': return fut[(fut.index>entry_time)&(fut.index<=horizon)]
    return fut[(fut.index>=entry_time)&(fut.index<=horizon)]


def max_excursion(path,entry,atr):
    if path.empty or not np.isfinite(entry) or not np.isfinite(atr) or atr<=0:return (np.nan,np.nan)
    mae=max(0.0,float(path.high.max())-entry)/atr
    mfe=max(0.0,entry-float(path.low.min()))/atr
    return mae,mfe


def simulate_one(row,fut,clock,k):
    horizon=pd.Timestamp(row.signal_time)+pd.Timedelta(hours=12)
    eligible=True
    if clock=='ACCEPT' and row.state!='ACCEPT':eligible=False
    et=pd.Timestamp(row.touch_time) if clock=='TOUCH' and pd.notna(row.touch_time) else (pd.Timestamp(row.class_time) if clock=='ACCEPT' and pd.notna(row.class_time) else pd.NaT)
    ep=float(row.level) if clock=='TOUCH' and np.isfinite(row.level) else (float(row.class_price) if clock=='ACCEPT' and np.isfinite(row.class_price) else np.nan)
    atr=float(row.atr14) if np.isfinite(row.atr14) else np.nan
    covered=bool(eligible and pd.notna(et) and et<=horizon and et in fut.index and horizon in fut.index and np.isfinite(ep) and np.isfinite(atr) and atr>0)
    base=dict(flow_id=int(row.flow_id),signal_time=row.signal_time,state=row.state,clock=clock,stop_atr=k,eligible=eligible,traded=False,covered=covered,entry_time=et,entry_price=ep,horizon=horizon,exit_time=pd.NaT,exit_price=np.nan,exit_reason='NO_TRADE',gross_r=0.0,net_r_0bps=0.0,net_r_5bps=0.0,net_r_10bps=0.0,mae_atr=np.nan,mfe_atr=np.nan,eventual_winner=False,stop_kills_eventual_winner=False)
    if not covered:return base
    p=barrier_path(fut,et,horizon,clock); endpx=float(fut.loc[horizon,'close'])
    if p.empty:return base
    stop=ep+k*atr; tp=ep-TP_R*k*atr
    mae,mfe=max_excursion(p,ep,atr)
    # no-stop time-horizon winner used only for survival diagnostics
    eventual=bool(endpx<ep)
    stop_touch=bool((p.high>=stop).any())
    reason='TIME'; xt=horizon; xp=endpx
    for tt,b in p.iterrows():
        hs=float(b.high)>=stop; ht=float(b.low)<=tp
        # conservative M15 ordering: any ambiguous same-bar outcome is SL-first.
        if hs:
            reason='SL'; xt=tt; xp=stop; break
        if ht:
            reason='TP'; xt=tt; xp=tp; break
    gross=(ep-xp)/(k*atr)
    base.update(traded=True,exit_time=xt,exit_price=xp,exit_reason=reason,gross_r=float(gross),mae_atr=float(mae),mfe_atr=float(mfe),eventual_winner=eventual,stop_kills_eventual_winner=bool(eventual and stop_touch))
    for bps in [0.0,5.0,10.0]:
        costr=(bps/10000.0)*ep/(k*atr)
        base[f'net_r_{int(bps)}bps']=float(gross-costr)
    return base


def pf(v):
    v=np.asarray(v,float); pos=v[v>0].sum(); neg=-v[v<0].sum()
    return float(pos/neg) if neg>0 else (np.inf if pos>0 else np.nan)


def maxdd(v):
    v=np.asarray(v,float)
    if len(v)==0:return np.nan
    eq=np.r_[0.0,np.cumsum(v)]; peak=np.maximum.accumulate(eq); return float(np.max(peak-eq))


def concurrency(x):
    q=x[x.traded].dropna(subset=['entry_time','exit_time']).copy()
    marks=[]
    for r in q.itertuples(index=False):
        marks.append((pd.Timestamp(r.entry_time),1)); marks.append((pd.Timestamp(r.exit_time),-1))
    # exits before entries at identical timestamp
    marks=sorted(marks,key=lambda z:(z[0],z[1])); cur=mx=0
    for _,d in marks:cur+=d; mx=max(mx,cur)
    return int(mx)


def summarize_policy(x,orig_n):
    t=x[x.traded].copy(); v=t.net_r_5bps.to_numpy(float)
    winners=x[x.traded & x.eventual_winner]
    kill=float(winners.stop_kills_eventual_winner.mean()) if len(winners) else np.nan
    mx=concurrency(x)
    return dict(clock=str(x.clock.iloc[0]),stop_atr=float(x.stop_atr.iloc[0]),original_n=int(orig_n),eligible_n=int(x.eligible.sum()),traded_n=len(t),fill_share=float(len(t)/orig_n) if orig_n else np.nan,tp_share=float((t.exit_reason=='TP').mean()) if len(t) else np.nan,sl_share=float((t.exit_reason=='SL').mean()) if len(t) else np.nan,time_share=float((t.exit_reason=='TIME').mean()) if len(t) else np.nan,gross_ev=float(t.gross_r.mean()) if len(t) else np.nan,net_ev_5bps=float(t.net_r_5bps.mean()) if len(t) else np.nan,net_ev_0bps=float(t.net_r_0bps.mean()) if len(t) else np.nan,net_ev_10bps=float(t.net_r_10bps.mean()) if len(t) else np.nan,ev_per_original_5bps=float(x.net_r_5bps.sum()/orig_n) if orig_n else np.nan,pf_5bps=pf(v),cum_r_5bps=float(v.sum()) if len(v) else 0.0,max_dd_r_5bps=maxdd(v),max_dd_pct_025=float(maxdd(v)*RISK_PCT) if len(v) else np.nan,winner_kill_rate=kill,median_mae_atr=float(t.mae_atr.median()) if len(t) else np.nan,median_mfe_atr=float(t.mfe_atr.median()) if len(t) else np.nan,max_concurrent=mx,max_concurrent_risk_pct=float(mx*RISK_PCT))


def transfer(out,events,clock,k):
    p=out[(out.clock==clock)&(out.stop_atr==k)].copy(); rows=[]
    for name,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); ids=events[(events.signal_time>=a)&(events.signal_time<b)].flow_id.astype(int)
        q=p[p.flow_id.isin(ids)]; t=q[q.traded]; orig=len(ids)
        rows.append(dict(clock=clock,stop_atr=k,slice=name,original_n=orig,traded_n=len(t),ev_per_original_5bps=float(q.net_r_5bps.sum()/orig) if orig else np.nan,trade_ev_5bps=float(t.net_r_5bps.mean()) if len(t) else np.nan,pf_5bps=pf(t.net_r_5bps.to_numpy(float)) if len(t) else np.nan,cum_r_5bps=float(t.net_r_5bps.sum()) if len(t) else 0.0))
    return pd.DataFrame(rows)


def getrow(s,clock,k):
    q=s[(s.clock==clock)&(s.stop_atr==k)]; return q.iloc[0]

def tval(tr,clock,name,col):
    q=tr[(tr.clock==clock)&(tr['slice']==name)]; return float(q.iloc[0][col]) if len(q) and pd.notna(q.iloc[0][col]) else np.nan

def tn(tr,clock,name,col='original_n'):
    q=tr[(tr.clock==clock)&(tr['slice']==name)]; return int(q.iloc[0][col]) if len(q) else 0

def py(x):
    if isinstance(x,(np.bool_,)):return bool(x)
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.floating,)):return None if not np.isfinite(x) else float(x)
    if isinstance(x,pd.Timestamp):return x.isoformat()
    raise TypeError(type(x).__name__)


def main():
    events=load_inputs(); fut=L35.download_futures()
    formal=events[events.signal_time<PRE].copy(); aug=events[(events.signal_time>=PRE)&(events.signal_time<AUG_END)].copy()
    rows=[]
    for r in events.itertuples(index=False):
        for clock in ['TOUCH','ACCEPT']:
            for k in STOP_GRID:rows.append(simulate_one(r,fut,clock,k))
    out=pd.DataFrame(rows); out.to_csv(OUT/'execution_stream.csv',index=False)
    formal_out=out[out.flow_id.isin(formal.flow_id.astype(int))].copy(); summaries=[]
    for clock in ['TOUCH','ACCEPT']:
        for k in STOP_GRID:
            q=formal_out[(formal_out.clock==clock)&(formal_out.stop_atr==k)].sort_values('entry_time')
            summaries.append(summarize_policy(q,len(formal)))
    sm=pd.DataFrame(summaries); sm.to_csv(OUT/'policy_summary.csv',index=False)
    tr=pd.concat([transfer(out,events,'TOUCH',2.5),transfer(out,events,'ACCEPT',2.5)],ignore_index=True); tr.to_csv(OUT/'transfer.csv',index=False)
    parity=float(formal.parity_all.mean()) if len(formal) else 0.0
    # coverage is per original formal event: TOUCH must cover all; ACCEPT non-ACCEPT rows are legitimate no-trades and excluded from coverage denominator.
    touch_cov=float(formal_out[(formal_out.clock=='TOUCH')&(formal_out.stop_atr==2.5)].covered.mean())
    aq=formal_out[(formal_out.clock=='ACCEPT')&(formal_out.stop_atr==2.5)]; ae=aq[aq.eligible]; accept_cov=float(ae.covered.mean()) if len(ae) else 0.0
    path_cov=min(touch_cov,accept_cov)
    acc=getrow(sm,'ACCEPT',2.5); tou=getrow(sm,'TOUCH',2.5)
    ak=sm[sm.clock=='ACCEPT'].sort_values('stop_atr').winner_kill_rate.to_numpy(float); tk=sm[sm.clock=='TOUCH'].sort_values('stop_atr').winner_kill_rate.to_numpy(float)
    mono_a=bool(np.all(np.diff(ak)<=1e-12)); mono_t=bool(np.all(np.diff(tk)<=1e-12))
    gates={
      'exact_high_response_preaug_n_475':len(formal)==475,
      'lab035_join_timestamp_state_parity_100pct':parity==1.0,
      'm15_path_coverage_ge_99pct':path_cov>=.99,
      'touch_trades_ge_450':int(tou.traded_n)>=450,
      'accept_trades_ge_300':int(acc.traded_n)>=300,
      'accept_winner_kill_monotonic_1_5_to_3':mono_a,
      'touch_winner_kill_monotonic_1_5_to_3':mono_t,
      'primary_accept_2_5_net_ev_positive':float(acc.net_ev_5bps)>0,
      'primary_accept_2_5_pf_ge_1_10':float(acc.pf_5bps)>=1.10,
      'primary_accept_2_5_ev_per_original_ge_0_05':float(acc.ev_per_original_5bps)>=.05,
      'primary_accept_2_5_dd_025_le_4pct':float(acc.max_dd_pct_025)<=4.0,
      'primary_accept_2_5_concurrent_risk_le_2pct':float(acc.max_concurrent_risk_pct)<=2.0,
      'primary_accept_2_5_10bps_ev_positive':float(acc.net_ev_10bps)>0,
      'primary_accept_2_5_2025h2_ev_per_original_positive':tval(tr,'ACCEPT','2025_H2','ev_per_original_5bps')>0,
      'primary_accept_2_5_2026_ev_per_original_positive':tval(tr,'ACCEPT','2026_JAN_JUL','ev_per_original_5bps')>0,
      'primary_accept_2_5_pooled_recent_positive_n50':tn(tr,'ACCEPT','POOLED_RECENT')>=50 and tval(tr,'ACCEPT','POOLED_RECENT','ev_per_original_5bps')>0,
      'primary_accept_2_5_2022_stress_positive':tval(tr,'ACCEPT','2022','ev_per_original_5bps')>0,
      'touch_2_5_net_ev_positive':float(tou.net_ev_5bps)>0,
      'touch_2_5_pf_ge_1_10':float(tou.pf_5bps)>=1.10,
      'touch_2_5_pooled_recent_ev_per_original_positive':tval(tr,'TOUCH','POOLED_RECENT','ev_per_original_5bps')>0,
      'accept_ev_per_original_not_worse_touch_by_0_15':float(acc.ev_per_original_5bps)>=float(tou.ev_per_original_5bps)-.15,
      'august_not_used_for_selection':True}
    score=sum(bool(v) for v in gates.values()); critical=['exact_high_response_preaug_n_475','lab035_join_timestamp_state_parity_100pct','m15_path_coverage_ge_99pct','primary_accept_2_5_net_ev_positive','primary_accept_2_5_pf_ge_1_10','primary_accept_2_5_ev_per_original_ge_0_05','primary_accept_2_5_dd_025_le_4pct','primary_accept_2_5_10bps_ev_positive','primary_accept_2_5_2025h2_ev_per_original_positive','primary_accept_2_5_2026_ev_per_original_positive','primary_accept_2_5_pooled_recent_positive_n50']
    if score>=18 and all(gates[k] for k in critical):verdict='PASS_SHORT_HIGH_RESPONSE_BOUNDED_EXECUTION_BRIDGE'
    elif score>=12 or (gates['touch_2_5_net_ev_positive'] and not gates['primary_accept_2_5_net_ev_positive']):verdict='WATCH_EXECUTION_SURVIVES_PARTIALLY_OR_ENTRY_CLOCK_MISMATCH'
    else:verdict='FAIL_BOUNDED_EXECUTION_DESTROYS_HIGH_RESPONSE_EDGE'
    meta=dict(verdict=verdict,score=score,formal_n=len(formal),aug_n=len(aug),parity=parity,touch_cov=touch_cov,accept_cov=accept_cov,primary_accept=acc.to_dict(),primary_touch=tou.to_dict())
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')
    L=[f'# {LAB}','',f'**Verdict: {verdict} — {score}/{len(gates)}**','', '## Frozen execution lineage',f'- exact HIGH_RESPONSE SHORT pre-Aug: **{len(formal)}**; August audit: **{len(aug)}**',f'- LAB035 timestamp/state parity: **{parity:.1%}**',f'- M15 path coverage TOUCH/ACCEPT-eligible: **{touch_cov:.1%} / {accept_cov:.1%}**','', '## Policy grid (TP=1.5R, cost=5bps RT)','', '| Clock | SL ATR | Trades | TP | SL | Time | EV R | PF | EV/original | CumR | MaxDD R | DD@0.25% | Winner killed | MAE ATR | MFE ATR | Max conc | Risk conc |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in sm.iterrows():L.append(f'| {r.clock} | {r.stop_atr:.1f} | {int(r.traded_n)} | {r.tp_share:.3f} | {r.sl_share:.3f} | {r.time_share:.3f} | {r.net_ev_5bps:+.3f} | {r.pf_5bps:.3f} | {r.ev_per_original_5bps:+.3f} | {r.cum_r_5bps:+.1f} | {r.max_dd_r_5bps:.2f} | {r.max_dd_pct_025:.2f}% | {r.winner_kill_rate:.3f} | {r.median_mae_atr:.2f} | {r.median_mfe_atr:.2f} | {int(r.max_concurrent)} | {r.max_concurrent_risk_pct:.2f}% |')
    L+=['','## Cost sensitivity for preregistered 2.5 ATR policies','',f'- ACCEPT 2.5: EV 0/5/10bps = **{acc.net_ev_0bps:+.3f} / {acc.net_ev_5bps:+.3f} / {acc.net_ev_10bps:+.3f} R**',f'- TOUCH 2.5: EV 0/5/10bps = **{tou.net_ev_0bps:+.3f} / {tou.net_ev_5bps:+.3f} / {tou.net_ev_10bps:+.3f} R**','', '## 2.5 ATR transfer (EV per original HIGH_RESPONSE signal)','', '| Clock | Slice | Original N | Trades | EV/original | Trade EV | PF | CumR |','|---|---|---:|---:|---:|---:|---:|---:|']
    for _,r in tr.iterrows():L.append(f'| {r.clock} | {r["slice"]} | {int(r.original_n)} | {int(r.traded_n)} | {r.ev_per_original_5bps:+.3f} | {r.trade_ev_5bps:+.3f} | {r.pf_5bps:.3f} | {r.cum_r_5bps:+.2f} |')
    L+=['','## Gates']+[f'- {"PASS" if v else "FAIL"} — `{k}`' for k,v in gates.items()]+['','## Guardrail','Frozen LAB043 SHORT HIGH_RESPONSE universe; same Binance USD-M M15 price lineage as LAB035. No signal/threshold/entry-price improvement after results. TOUCH same-bar ambiguity is SL-first; ACCEPT begins barrier checking on the next M15 bar. 5bps is a research friction assumption with 0/10bps sensitivity, not a claim of exact current FTMO BTC CFD costs. Reused historical execution research, not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':verdict,'score':score,'gates':gates,'primary_accept':acc.to_dict(),'primary_touch':tou.to_dict()},indent=2,default=py))

if __name__=='__main__':main()
