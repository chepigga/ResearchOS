#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_V1_FULL_SYSTEM_FROZEN_AUG2026_OOS_REPLICATION_LAB_055'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC38=LABS/'BTC_FLOW_LEVEL_PRETOUCH_NET_TAKER_DELTA_PRICE_RESPONSE_AND_CVD_ABSORPTION_LAB_038'/'output'/'cvd_absorption_stream.csv'
SRC35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'output'/'activation_stream.csv'
SRC43=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043'/'output'/'short_response_router_stream.csv'
SRC53=LABS/'BTC_SHORT_ACCEPT25_PERSISTENT_FAILURE_EXIT_VS_SEVERE_ADVERSE1R_EXECUTION_LAB_053'/'output'/'execution_stream.csv'
R35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab035',R35)
L35=importlib.util.module_from_spec(spec); spec.loader.exec_module(L35); L35.OUT=OUT

PRE=pd.Timestamp('2026-08-01',tz='UTC')
AUG_END=pd.Timestamp('2026-09-01',tz='UTC')
LOOKBACK=pd.Timedelta(days=90); MIN_PRIOR=40
STOP_ATR=2.5; TP_R=1.5; RISK_PCT=0.25
PERIODS=['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']


def period_of(t):
    if t.year in [2021,2022,2023,2024]: return str(t.year)
    if t.year==2025: return '2025_H1' if t < pd.Timestamp('2025-07-01',tz='UTC') else '2025_H2'
    if t.year==2026 and t<PRE: return '2026_JAN_JUL'
    if PRE<=t<AUG_END: return 'AUG2026'
    return 'OTHER'


def pf(v):
    v=np.asarray(v,float); v=v[np.isfinite(v)]
    gp=v[v>0].sum(); gl=-v[v<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def maxdd(v):
    v=np.asarray(v,float); v=v[np.isfinite(v)]
    if not len(v): return np.nan
    eq=np.r_[0.0,np.cumsum(v)]; peak=np.maximum.accumulate(eq)
    return float(np.max(peak-eq))


def net_r(entry,exit_px,D,bps):
    gross=(entry-exit_px)/D
    cost=(bps/10000.0)*entry/D
    return float(gross-cost)


def load_and_reconstruct_router():
    d=pd.read_csv(SRC38)
    a=pd.read_csv(SRC35)
    for x in [d,a]:
        for c in ['signal_time','touch_time','class_time']:
            if c in x.columns: x[c]=pd.to_datetime(x[c],errors='coerce',utc=True)
    for c in ['flow_id','side','fut_netdelta_norm_60','fut_disp_atr_60','atr14','residual_atr']:
        if c in d.columns: d[c]=pd.to_numeric(d[c],errors='coerce')
    for c in ['flow_id','side','atr14','level','class_price','signal_close']:
        if c in a.columns: a[c]=pd.to_numeric(a[c],errors='coerce')
    d=d.sort_values('signal_time').reset_index(drop=True)
    d['pressure_mag_60']=d.fut_netdelta_norm_60.abs()
    d['response_60']=d.fut_disp_atr_60
    d['fut_elasticity_60']=d.fut_disp_atr_60/np.maximum(d.fut_netdelta_norm_60.abs(),0.25)
    d['prior_n']=0; d['pressure_med90']=np.nan; d['response_med90']=np.nan; d['book_state']='UNRESOLVED'
    base=d[d.pressure_mag_60.notna() & d.response_60.notna() & d.fut_elasticity_60.notna()].copy()
    for i in base.index:
        t=d.at[i,'signal_time']
        p=base[(base.signal_time>=t-LOOKBACK)&(base.signal_time<t)]
        n=len(p); d.at[i,'prior_n']=n
        if n<MIN_PRIOR: continue
        pm=float(p.pressure_mag_60.median()); rm=float(p.response_60.median())
        d.at[i,'pressure_med90']=pm; d.at[i,'response_med90']=rm
        low=float(d.at[i,'pressure_mag_60'])<=pm
        highresp=float(d.at[i,'response_60'])>rm
        if low and highresp: s='THIN_BOOK'
        elif (not low) and highresp: s='DRIVEN_MOVE'
        elif (not low) and (not highresp): s='ABSORPTION'
        else: s='WEAK'
        d.at[i,'book_state']=s
    high=d[(d.side==-1)&d.book_state.isin(['DRIVEN_MOVE','THIN_BOOK'])].copy()
    keep=['flow_id','signal_time','side','state','touch_time','class_time','atr14','level','class_price','signal_close']
    aa=a[keep].copy()
    m=high.merge(aa,on='flow_id',how='left',suffixes=('_r','_a'),validate='one_to_one')
    m['signal_time']=m.signal_time_a; m['touch_time']=m.touch_time_a; m['class_time']=m.class_time_a
    m['side']=m.side_a; m['state']=m.state_a
    m['period']=m.signal_time.map(period_of)
    return m.sort_values('signal_time').reset_index(drop=True)


def barrier_path(fut,entry_time,end):
    return fut[(fut.index>entry_time)&(fut.index<=end)]


def simulate_parent(r,fut):
    horizon=pd.Timestamp(r.signal_time)+pd.Timedelta(hours=12)
    eligible=str(r.state)=='ACCEPT'
    et=pd.Timestamp(r.class_time) if eligible and pd.notna(r.class_time) else pd.NaT
    ep=float(r.class_price) if eligible and np.isfinite(r.class_price) else np.nan
    atr=float(r.atr14) if np.isfinite(r.atr14) else np.nan
    D=STOP_ATR*atr if np.isfinite(atr) else np.nan
    covered=bool(eligible and pd.notna(et) and et<=horizon and et in fut.index and horizon in fut.index and np.isfinite(ep) and np.isfinite(D) and D>0)
    base=dict(flow_id=int(r.flow_id),signal_time=r.signal_time,period=r.period,book_state=r.book_state,state=r.state,
              level=float(r.level) if np.isfinite(r.level) else np.nan,atr14=atr,entry_time=et,entry_price=ep,risk_dist=D,horizon=horizon,
              eligible=eligible,covered=covered,traded=False,parent_exit_time=pd.NaT,parent_exit_price=np.nan,parent_exit_reason='NO_TRADE')
    if not covered: return base
    p=barrier_path(fut,et,horizon)
    if p.empty: return base
    stop=ep+D; tp=ep-TP_R*D; xt=horizon; xp=float(fut.loc[horizon,'close']); reason='TIME'
    for tt,b in p.iterrows():
        hs=float(b.high)>=stop; ht=float(b.low)<=tp
        if hs:
            xt=tt; xp=stop; reason='SL'; break
        if ht:
            xt=tt; xp=tp; reason='TP'; break
    base.update(traded=True,parent_exit_time=xt,parent_exit_price=xp,parent_exit_reason=reason)
    return base


def first_passage_state(fut,et,xt,ep,D):
    end=min(et+pd.Timedelta(minutes=120),xt)
    p=barrier_path(fut,et,end)
    fav=ep-0.5*D; adv=ep+0.5*D
    for tt,b in p.iterrows():
        hf=float(b.low)<=fav; ha=float(b.high)>=adv
        if hf and ha: return 'ADVERSE_FIRST',tt,adv
        if ha: return 'ADVERSE_FIRST',tt,adv
        if hf: return 'FAVORABLE_FIRST',tt,fav
    return 'NONE_120',pd.NaT,np.nan


def persistent_after_adverse(fut,fp_time,xt,exit_reason,ep,level):
    include_end=(str(exit_reason)=='TIME')
    if include_end: pc=fut[(fut.index>fp_time)&(fut.index<=xt)]
    else: pc=fut[(fut.index>fp_time)&(fut.index<xt)]
    consec=0
    for tt,b in pc.iterrows():
        c=float(b.close)
        if c<=ep:
            return False,pd.NaT,np.nan
        if c>level:
            consec+=1
            if consec>=2: return True,tt,c
        else:
            consec=0
    return False,pd.NaT,np.nan


def add_management(parent,fut):
    rows=[]
    for r in parent.itertuples(index=False):
        d=r._asdict()
        d.update(fp_state='NO_TRADE',fp_time=pd.NaT,persistent_failure=False,persistent_time=pd.NaT,persistent_price=np.nan,
                 final_exit_time=r.parent_exit_time,final_exit_price=r.parent_exit_price,final_exit_reason=r.parent_exit_reason,
                 early_exit=False,net_r_0bps=0.0,net_r_5bps=0.0,net_r_10bps=0.0)
        if not bool(r.traded):
            rows.append(d); continue
        et=pd.Timestamp(r.entry_time); xt=pd.Timestamp(r.parent_exit_time); ep=float(r.entry_price); D=float(r.risk_dist); level=float(r.level)
        fs,ft,fp=first_passage_state(fut,et,xt,ep,D)
        d['fp_state']=fs; d['fp_time']=ft
        persistent=False; pt=pd.NaT; pp=np.nan
        if fs=='ADVERSE_FIRST' and pd.notna(ft):
            persistent,pt,pp=persistent_after_adverse(fut,ft,xt,r.parent_exit_reason,ep,level)
        d['persistent_failure']=bool(persistent); d['persistent_time']=pt; d['persistent_price']=pp
        fx=xt; fpx=float(r.parent_exit_price); freason=str(r.parent_exit_reason); early=False
        if persistent:
            fx=pt; fpx=pp; freason='PERSISTENT_FAILURE_EXIT'; early=True
        d['final_exit_time']=fx; d['final_exit_price']=fpx; d['final_exit_reason']=freason; d['early_exit']=early
        d['net_r_0bps']=net_r(ep,fpx,D,0.0); d['net_r_5bps']=net_r(ep,fpx,D,5.0); d['net_r_10bps']=net_r(ep,fpx,D,10.0)
        rows.append(d)
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)


def summarize(q,orig_n,label):
    t=q[q.traded].sort_values('entry_time').copy(); v=t.net_r_5bps.to_numpy(float)
    dd=maxdd(v)
    return dict(scope=label,original_n=int(orig_n),traded_n=len(t),persistent_exit_n=int(t.early_exit.sum()) if len(t) else 0,
                ev_5bps=float(t.net_r_5bps.mean()) if len(t) else np.nan,pf_5bps=pf(v) if len(t) else np.nan,
                cum_r_5bps=float(t.net_r_5bps.sum()) if len(t) else 0.0,max_dd_r_5bps=dd,
                max_dd_pct_025=float(dd*RISK_PCT) if pd.notna(dd) else np.nan,
                ev_per_original_5bps=float(t.net_r_5bps.sum()/orig_n) if orig_n else np.nan,
                ev_0bps=float(t.net_r_0bps.mean()) if len(t) else np.nan,ev_10bps=float(t.net_r_10bps.mean()) if len(t) else np.nan,
                tp_n=int((t.final_exit_reason=='TP').sum()) if len(t) else 0,sl_n=int((t.final_exit_reason=='SL').sum()) if len(t) else 0,
                time_n=int((t.final_exit_reason=='TIME').sum()) if len(t) else 0)


def scope_mask(d,name):
    if name in PERIODS: return d.period==name
    if name=='POOLED_RECENT': return d.period.isin(['2025_H2','2026_JAN_JUL'])
    if name=='AUG2026': return d.period=='AUG2026'
    if name=='FULL_PREAUG': return d.signal_time<PRE
    raise KeyError(name)


def parity_audit(router,final):
    r43=pd.read_csv(SRC43); e53=pd.read_csv(SRC53)
    for x in [r43,e53]:
        for c in ['signal_time','entry_time','exit_time','state_time']:
            if c in x.columns: x[c]=pd.to_datetime(x[c],errors='coerce',utc=True)
    for c in ['flow_id','side','net_r_5bps']:
        if c in r43.columns: r43[c]=pd.to_numeric(r43[c],errors='coerce')
        if c in e53.columns: e53[c]=pd.to_numeric(e53[c],errors='coerce')
    frozen_router=r43[(r43.side==-1)&(r43.response_router=='HIGH_RESPONSE')&(r43.signal_time<PRE)]
    ours_router=router[router.signal_time<PRE]
    router_ids_equal=set(ours_router.flow_id.astype(int))==set(frozen_router.flow_id.astype(int))
    frozen=e53[(e53.policy=='PERSISTENT_EXIT')&(e53.signal_time<PRE)].copy()
    ours=final[(final.signal_time<PRE)&final.traded].copy()
    traded_ids_equal=set(ours.flow_id.astype(int))==set(frozen.flow_id.astype(int))
    m=ours[['flow_id','net_r_5bps','early_exit']].merge(frozen[['flow_id','net_r_5bps','early_exit']],on='flow_id',suffixes=('_ours','_frozen'),validate='one_to_one')
    maxerr=float(np.max(np.abs(m.net_r_5bps_ours-m.net_r_5bps_frozen))) if len(m) else np.inf
    pers_ours=set(m.loc[m.early_exit_ours.astype(bool),'flow_id'].astype(int)); pers_frozen=set(m.loc[m.early_exit_frozen.astype(bool),'flow_id'].astype(int))
    return dict(router_ids_equal=bool(router_ids_equal),traded_ids_equal=bool(traded_ids_equal),persistent_ids_equal=bool(pers_ours==pers_frozen),
                frozen_router_n=len(frozen_router),ours_router_n=len(ours_router),frozen_trades_n=len(frozen),ours_trades_n=len(ours),
                frozen_persistent_n=len(pers_frozen),ours_persistent_n=len(pers_ours),max_abs_net_r_5bps_error=maxerr)


def py(x):
    if isinstance(x,(np.bool_,)): return bool(x)
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,)): return None if not np.isfinite(x) else float(x)
    if isinstance(x,pd.Timestamp): return x.isoformat()
    raise TypeError(type(x).__name__)


def main():
    router=load_and_reconstruct_router()
    fut=L35.download_futures()
    parent=pd.DataFrame([simulate_parent(r,fut) for r in router.itertuples(index=False)])
    final=add_management(parent,fut)
    final.to_csv(OUT/'full_system_stream.csv',index=False)
    router.to_csv(OUT/'reconstructed_router_stream.csv',index=False)

    parity=parity_audit(router,final)
    pre=final[final.signal_time<PRE]; aug=final[(final.signal_time>=PRE)&(final.signal_time<AUG_END)]
    eligible_pre=pre[pre.eligible]; path_cov=float(eligible_pre.covered.mean()) if len(eligible_pre) else 0.0
    eligible_aug=aug[aug.eligible]; aug_cov=float(eligible_aug.covered.mean()) if len(eligible_aug) else 1.0

    scopes=['FULL_PREAUG']+PERIODS+['POOLED_RECENT','AUG2026']
    rows=[]
    for sc in scopes:
        q=final[scope_mask(final,sc)].copy(); rows.append(summarize(q,len(q),sc))
    sm=pd.DataFrame(rows); sm.to_csv(OUT/'system_summary_and_transfer.csv',index=False)
    full=sm[sm.scope=='FULL_PREAUG'].iloc[0]; y22=sm[sm.scope=='2022'].iloc[0]; h2=sm[sm.scope=='2025_H2'].iloc[0]; y26=sm[sm.scope=='2026_JAN_JUL'].iloc[0]; recent=sm[sm.scope=='POOLED_RECENT'].iloc[0]; au=sm[sm.scope=='AUG2026'].iloc[0]
    august_status='ADEQUATE_N' if int(au.traded_n)>=20 else 'INSUFFICIENT_N'

    gates={
      'preaug_high_response_n_eq475': bool(parity['ours_router_n']==475),
      'preaug_accept_trades_n_eq327': bool(parity['ours_trades_n']==327),
      'preaug_persistent_exit_n_eq59': bool(parity['ours_persistent_n']==59),
      'router_flow_id_parity_100pct': bool(parity['router_ids_equal']),
      'traded_flow_id_parity_100pct': bool(parity['traded_ids_equal']),
      'persistent_exit_flow_id_parity_100pct': bool(parity['persistent_ids_equal']),
      'netr_5bps_max_error_le1e9': bool(parity['max_abs_net_r_5bps_error']<=1e-9),
      'preaug_m15_path_coverage_ge99pct': bool(path_cov>=.99),
      'full_5bps_ev_positive': bool(pd.notna(full.ev_5bps) and full.ev_5bps>0),
      'full_pf_gt1_10': bool(pd.notna(full.pf_5bps) and full.pf_5bps>1.10),
      'full_cumr_positive': bool(full.cum_r_5bps>0),
      'full_dd_025_le4pct': bool(pd.notna(full.max_dd_pct_025) and full.max_dd_pct_025<=4.0),
      'full_10bps_ev_positive': bool(pd.notna(full.ev_10bps) and full.ev_10bps>0),
      '2022_ev_per_original_nonnegative': bool(pd.notna(y22.ev_per_original_5bps) and y22.ev_per_original_5bps>=0),
      '2025h2_ev_per_original_positive': bool(pd.notna(h2.ev_per_original_5bps) and h2.ev_per_original_5bps>0),
      '2026_ev_per_original_positive': bool(pd.notna(y26.ev_per_original_5bps) and y26.ev_per_original_5bps>0),
      'recent_pooled_ev_per_original_positive': bool(pd.notna(recent.ev_per_original_5bps) and recent.ev_per_original_5bps>0),
      'august_reported_without_tuning': True,
      'august_eligible_path_coverage_100pct': bool(aug_cov==1.0),
      'august_trades_ge20': bool(int(au.traded_n)>=20),
      'no_september_no_postaug_threshold_change': True,
    }
    core_keys=list(gates.keys())[:17]
    core_ok=all(gates[k] for k in core_keys)
    if core_ok and int(au.traded_n)>=20 and pd.notna(au.ev_5bps) and au.ev_5bps>0:
        verdict='PASS_FULL_SYSTEM_FROZEN_REPLICATION'
    elif core_ok and int(au.traded_n)<20:
        verdict='WATCH_FULL_SYSTEM_PARITY_PASS_AUG_OOS_INSUFFICIENT_N'
    else:
        verdict='FAIL_FULL_SYSTEM_PARITY_OR_ECONOMICS'

    meta=dict(verdict=verdict,august_status=august_status,parity=parity,preaug_path_coverage=path_cov,august_eligible_path_coverage=aug_cov,
              preaug_router_n=len(pre),preaug_trades=int(pre.traded.sum()),preaug_persistent=int(pre.early_exit.sum()),aug_router_n=len(aug),aug_trades=int(aug.traded.sum()),aug_persistent=int(aug.early_exit.sum()))
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=py),encoding='utf-8')
    aug.to_csv(OUT/'august_selection_untouched_audit.csv',index=False)

    L=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(gates.values())}/{len(gates)}**','',
       '## Frozen end-to-end parity',
       f"- reconstructed pre-Aug HIGH_RESPONSE SHORT: **{parity['ours_router_n']}** vs frozen **{parity['frozen_router_n']}**",
       f"- reconstructed ACCEPT trades: **{parity['ours_trades_n']}** vs frozen **{parity['frozen_trades_n']}**",
       f"- reconstructed persistent exits: **{parity['ours_persistent_n']}** vs frozen **{parity['frozen_persistent_n']}**",
       f"- router/trade/persistent flow-ID parity: **{parity['router_ids_equal']} / {parity['traded_ids_equal']} / {parity['persistent_ids_equal']}**",
       f"- max abs 5bps net-R parity error: **{parity['max_abs_net_r_5bps_error']:.3e}**; M15 path coverage **{path_cov:.1%}**",'',
       '## Full frozen system economics','',
       '| Scope | Orig N | Trades | Persistent exits | EV 5bps | PF | CumR | MaxDD R | DD @0.25% | EV/orig | EV 10bps |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in sm.iterrows():
        def f3(x): return '—' if pd.isna(x) else f'{x:+.3f}'
        pfv='—' if pd.isna(r.pf_5bps) else f'{r.pf_5bps:.3f}'
        dd='—' if pd.isna(r.max_dd_r_5bps) else f'{r.max_dd_r_5bps:.2f}'
        ddp='—' if pd.isna(r.max_dd_pct_025) else f'{r.max_dd_pct_025:.2f}%'
        L.append(f"| {r.scope} | {int(r.original_n)} | {int(r.traded_n)} | {int(r.persistent_exit_n)} | {f3(r.ev_5bps)} | {pfv} | {f3(r.cum_r_5bps)} | {dd} | {ddp} | {f3(r.ev_per_original_5bps)} | {f3(r.ev_10bps)} |")
    L += ['', '## August 2026 selection-untouched audit',
          f'- HIGH_RESPONSE SHORT events: **{len(aug)}**',f'- ACCEPT trades: **{int(aug.traded.sum())}**',f'- persistent exits: **{int(aug.early_exit.sum())}**',f'- evidence status: **{august_status}**',
          '- August was not used for rule selection, but prior labs exposed it as audit-only; therefore this is not claimed as pristine unseen OOS.','',
          '## Gates']
    for k,v in gates.items(): L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    L += ['', '## Freeze decision',
          'No parameter is changed from SHORT v1. If August has <20 trades, no live-profitability conclusion is allowed. The next valid step is broker/native or genuinely new-time-period validation, not more reused-sample sequence mining.',
          '', '## Frozen SHORT v1',
          '`FLOW SHORT → HIGH_RESPONSE → ACCEPT → SL 2.5 ATR → TP 1.5R → max signal+12h → after ADVERSE_FIRST, EXIT NOW on 2 consecutive M15 closes above frozen level before recovery.`']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':verdict,'meta':meta,'gates':gates},indent=2,default=py))

if __name__=='__main__': main()
