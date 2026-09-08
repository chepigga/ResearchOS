#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ACCEPT25_6H_VS_12H_TIME_EXIT_ABLATION_LAB_046'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
R44=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044'/'run_lab.py'
P44=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044'/'output'/'policy_summary.csv'
spec=importlib.util.spec_from_file_location('lab044',R44); B=importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
PRE=pd.Timestamp('2026-08-01',tz='UTC'); AUG_END=pd.Timestamp('2026-09-01',tz='UTC')
K=2.5; TP_R=1.5; RISK_PCT=0.25; SEED=20260908; BOOT_N=5000
POLICIES=['ENTRY_PLUS_6H','SIGNAL_PLUS_6H','SIGNAL_PLUS_12H']
WINS={'2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),'2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),'2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}

def load_events():
    m=B.load_inputs()
    if 'atr14' not in m.columns and 'atr14_a' in m.columns:m['atr14']=m['atr14_a']
    return m.sort_values('signal_time').reset_index(drop=True)

def horizon_for(r,policy):
    if policy=='ENTRY_PLUS_6H':return pd.Timestamp(r.class_time)+pd.Timedelta(hours=6)
    if policy=='SIGNAL_PLUS_6H':return pd.Timestamp(r.signal_time)+pd.Timedelta(hours=6)
    return pd.Timestamp(r.signal_time)+pd.Timedelta(hours=12)

def simulate(r,fut,policy):
    base=dict(flow_id=int(r.flow_id),signal_time=r.signal_time,state=r.state,policy=policy,eligible=False,traded=False,covered=False,entry_time=pd.NaT,entry_price=np.nan,horizon=pd.NaT,exit_time=pd.NaT,exit_price=np.nan,exit_reason='NO_TRADE',gross_r=0.0,net_r_0bps=0.0,net_r_5bps=0.0,net_r_10bps=0.0,holding_h=np.nan)
    if r.state!='ACCEPT' or pd.isna(r.class_time) or not np.isfinite(r.class_price):return base
    et=pd.Timestamp(r.class_time); ep=float(r.class_price); atr=float(r.atr14) if np.isfinite(r.atr14) else np.nan; hz=horizon_for(r,policy)
    base.update(eligible=True,entry_time=et,entry_price=ep,horizon=hz)
    if et>=hz:
        base['exit_reason']='LATE_ACCEPT'; return base
    covered=bool(et in fut.index and hz in fut.index and np.isfinite(atr) and atr>0)
    base['covered']=covered
    if not covered:return base
    p=fut[(fut.index>et)&(fut.index<=hz)]
    if p.empty:return base
    stop=ep+K*atr; tp=ep-TP_R*K*atr
    reason='TIME'; xt=hz; xp=float(fut.loc[hz,'close'])
    for tt,b in p.iterrows():
        hs=float(b.high)>=stop; ht=float(b.low)<=tp
        if hs:
            reason='SL'; xt=tt; xp=stop; break
        if ht:
            reason='TP'; xt=tt; xp=tp; break
    gross=(ep-xp)/(K*atr)
    base.update(traded=True,exit_time=xt,exit_price=xp,exit_reason=reason,gross_r=float(gross),holding_h=float((xt-et).total_seconds()/3600.0))
    for bps in [0.0,5.0,10.0]:
        cost=(bps/10000.0)*ep/(K*atr)
        base[f'net_r_{int(bps)}bps']=float(gross-cost)
    return base

def pf(v):
    v=np.asarray(v,float); pos=v[v>0].sum(); neg=-v[v<0].sum()
    return float(pos/neg) if neg>0 else (np.inf if pos>0 else np.nan)

def maxdd(v):
    v=np.asarray(v,float)
    if len(v)==0:return np.nan
    eq=np.r_[0.0,np.cumsum(v)]; peak=np.maximum.accumulate(eq); return float(np.max(peak-eq))

def summarize(q,orig_n):
    t=q[q.traded].sort_values('entry_time'); v=t.net_r_5bps.to_numpy(float); dd=maxdd(v)
    return dict(policy=str(q.policy.iloc[0]),original_n=int(orig_n),eligible_n=int(q.eligible.sum()),traded_n=len(t),coverage=float(q.loc[q.eligible & (q.entry_time<q.horizon),'covered'].mean()) if ((q.eligible)&(q.entry_time<q.horizon)).any() else np.nan,tp_share=float((t.exit_reason=='TP').mean()) if len(t) else np.nan,sl_share=float((t.exit_reason=='SL').mean()) if len(t) else np.nan,time_share=float((t.exit_reason=='TIME').mean()) if len(t) else np.nan,late_accept_n=int((q.exit_reason=='LATE_ACCEPT').sum()),net_ev_0bps=float(t.net_r_0bps.mean()) if len(t) else np.nan,net_ev_5bps=float(t.net_r_5bps.mean()) if len(t) else np.nan,net_ev_10bps=float(t.net_r_10bps.mean()) if len(t) else np.nan,ev_per_original_5bps=float(q.net_r_5bps.sum()/orig_n) if orig_n else np.nan,pf_5bps=pf(v),cum_r_5bps=float(v.sum()),max_dd_r_5bps=dd,max_dd_pct_025=float(dd*RISK_PCT),median_holding_h=float(t.holding_h.median()) if len(t) else np.nan)

def transfer(out,events):
    rows=[]
    for pol in POLICIES:
      q=out[out.policy==pol]
      for name,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); ids=events[(events.signal_time>=a)&(events.signal_time<b)].flow_id.astype(int); z=q[q.flow_id.isin(ids)]; t=z[z.traded]
        rows.append(dict(policy=pol,slice=name,original_n=len(ids),traded_n=len(t),ev_per_original_5bps=float(z.net_r_5bps.sum()/len(ids)) if len(ids) else np.nan,trade_ev_5bps=float(t.net_r_5bps.mean()) if len(t) else np.nan,pf_5bps=pf(t.net_r_5bps.to_numpy(float)) if len(t) else np.nan,cum_r_5bps=float(t.net_r_5bps.sum())))
    return pd.DataFrame(rows)

def paired_boot(out,formal):
    p=out[out.flow_id.isin(formal.flow_id.astype(int))].pivot(index='flow_id',columns='policy',values='net_r_5bps').fillna(0.0)
    tm=formal.set_index('flow_id').signal_time
    z=pd.DataFrame({'signal_time':tm.loc[p.index],'diff':p['ENTRY_PLUS_6H']-p['SIGNAL_PLUS_12H']}).reset_index(drop=True)
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); z['cluster']=(((z.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    arr=[]
    for _,g in z.groupby('cluster'):arr.append((g['diff'].sum(),len(g)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0); vals.append(float(s[0]/s[1]))
    v=np.asarray(vals,float)
    return dict(point=float(z['diff'].mean()),clusters=m,ci_lo=float(np.quantile(v,.025)),ci_hi=float(np.quantile(v,.975)))
def row(sm,p):return sm[sm.policy==p].iloc[0]
def tv(tr,p,s,col):
    q=tr[(tr.policy==p)&(tr['slice']==s)]; return float(q.iloc[0][col]) if len(q) and pd.notna(q.iloc[0][col]) else np.nan
def tn(tr,p,s):
    q=tr[(tr.policy==p)&(tr['slice']==s)]; return int(q.iloc[0].original_n) if len(q) else 0

def main():
    events=load_events(); fut=B.L35.download_futures(); formal=events[events.signal_time<PRE].copy()
    rows=[]
    for r in events.itertuples(index=False):
        for p in POLICIES:rows.append(simulate(r,fut,p))
    out=pd.DataFrame(rows); out.to_csv(OUT/'execution_stream.csv',index=False)
    fo=out[out.flow_id.isin(formal.flow_id.astype(int))]
    sm=pd.DataFrame([summarize(fo[fo.policy==p],len(formal)) for p in POLICIES]); sm.to_csv(OUT/'policy_summary.csv',index=False)
    tr=transfer(out,events); tr.to_csv(OUT/'transfer.csv',index=False)
    bt=paired_boot(out,formal); (OUT/'paired_bootstrap.json').write_text(json.dumps(bt,indent=2),encoding='utf-8')
    parent=pd.read_csv(P44); pr=parent[(parent.clock=='ACCEPT')&(parent.stop_atr==2.5)].iloc[0]
    s6=row(sm,'ENTRY_PLUS_6H'); sg6=row(sm,'SIGNAL_PLUS_6H'); s12=row(sm,'SIGNAL_PLUS_12H')
    parity_n=int(s12.traded_n)==int(pr.traded_n); parity_ev=abs(float(s12.net_ev_5bps)-float(pr.net_ev_5bps))<=1e-9
    gates={
      'parent_formal_n475_accept327':len(formal)==475 and int(s6.traded_n)==327,
      'signal12_parent_trade_ev_parity':parity_n and parity_ev,
      'm15_path_coverage_ge_99pct':float(s6.coverage)>=.99,
      'entry6_net_ev_positive':float(s6.net_ev_5bps)>0,
      'entry6_pf_ge_1_10':float(s6.pf_5bps)>=1.10,
      'entry6_ev_per_original_ge_0_05':float(s6.ev_per_original_5bps)>=.05,
      'entry6_10bps_ev_positive':float(s6.net_ev_10bps)>0,
      'entry6_dd_025_le_4pct':float(s6.max_dd_pct_025)<=4.0,
      'entry6_2025h2_positive':tv(tr,'ENTRY_PLUS_6H','2025_H2','ev_per_original_5bps')>0,
      'entry6_2026_positive':tv(tr,'ENTRY_PLUS_6H','2026_JAN_JUL','ev_per_original_5bps')>0,
      'entry6_pooled_recent_positive_n50':tn(tr,'ENTRY_PLUS_6H','POOLED_RECENT')>=50 and tv(tr,'ENTRY_PLUS_6H','POOLED_RECENT','ev_per_original_5bps')>0,
      'entry6_not_worse_12h_by_0_05':float(s6.ev_per_original_5bps)>=float(s12.ev_per_original_5bps)-.05,
      'entry6_pf_not_worse_12h_by_0_10':float(s6.pf_5bps)>=float(s12.pf_5bps)-.10,
      'august_not_used_for_selection':True}
    score=sum(bool(x) for x in gates.values()); critical=list(gates.keys())[:11]
    if score>=12 and all(gates[k] for k in critical): verdict='PASS_ACCEPT25_ENTRY6H_TIME_EXIT_SURVIVES'
    elif float(s6.net_ev_5bps)>0: verdict='WATCH_ACCEPT25_ENTRY6H_POSITIVE_BUT_DEGRADES'
    else: verdict='FAIL_ACCEPT25_ENTRY6H_KILLS_EDGE'
    meta=dict(verdict=verdict,score=score,gates_total=len(gates),paired_entry6_minus_signal12=bt,parent_ev=float(pr.net_ev_5bps))
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2),encoding='utf-8')
    L=[f'# {LAB}','',f'**Verdict: {verdict} — {score}/{len(gates)}**','', '## Fixed ACCEPT2.5 time-exit ablation','', '| Policy | Trades | TP | SL | Time | Late | EV 0bps | EV 5bps | EV 10bps | PF | EV/original | CumR | MaxDD R | DD@0.25% | Median hold h |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in sm.iterrows():L.append(f"| {r.policy} | {int(r.traded_n)} | {r.tp_share:.3f} | {r.sl_share:.3f} | {r.time_share:.3f} | {int(r.late_accept_n)} | {r.net_ev_0bps:+.3f} | {r.net_ev_5bps:+.3f} | {r.net_ev_10bps:+.3f} | {r.pf_5bps:.3f} | {r.ev_per_original_5bps:+.3f} | {r.cum_r_5bps:+.2f} | {r.max_dd_r_5bps:.2f} | {r.max_dd_pct_025:.2f}% | {r.median_holding_h:.2f} |")
    L+=['','## Paired diagnostic',f"- ENTRY_PLUS_6H minus SIGNAL_PLUS_12H EV/original: **{bt['point']:+.3f}R**, 7d cluster bootstrap 95% CI **[{bt['ci_lo']:+.3f}, {bt['ci_hi']:+.3f}]**, clusters={bt['clusters']}",'','## Transfer (EV/original)','', '| Slice | ENTRY+6h | SIGNAL+6h | SIGNAL+12h |','|---|---:|---:|---:|']
    for s in WINS:L.append(f"| {s} | {tv(tr,'ENTRY_PLUS_6H',s,'ev_per_original_5bps'):+.3f} | {tv(tr,'SIGNAL_PLUS_6H',s,'ev_per_original_5bps'):+.3f} | {tv(tr,'SIGNAL_PLUS_12H',s,'ev_per_original_5bps'):+.3f} |")
    L+=['','## Gates']+[f'- {"PASS" if v else "FAIL"} — `{k}`' for k,v in gates.items()]+['','## Guardrail','Only time exit changed. Frozen HIGH_RESPONSE -> ACCEPT, SL 2.5 ATR, TP 1.5R, M15 path ordering and costs retained. Reused historical lineage; not fresh OOS. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':verdict,'score':score,'gates':gates,'entry6':s6.to_dict(),'signal6':sg6.to_dict(),'signal12':s12.to_dict(),'bootstrap':bt},indent=2,default=str))
if __name__=='__main__':main()
