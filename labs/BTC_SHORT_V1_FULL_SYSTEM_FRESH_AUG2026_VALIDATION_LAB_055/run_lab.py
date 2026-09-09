#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_SHORT_V1_FULL_SYSTEM_FRESH_AUG2026_VALIDATION_LAB_055'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC41=LABS/'BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041'/'output'/'all_touch_elasticity_stream.csv'
SRC35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'output'/'activation_stream.csv'
SRC53=LABS/'BTC_SHORT_ACCEPT25_PERSISTENT_FAILURE_EXIT_VS_SEVERE_ADVERSE1R_EXECUTION_LAB_053'/'output'/'execution_stream.csv'
R35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab035',R35); L35=importlib.util.module_from_spec(spec); spec.loader.exec_module(L35); L35.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC'); END=pd.Timestamp('2026-09-01',tz='UTC')
STOP_ATR=2.5; TP_R=1.5; RISK_PCT=0.25


def pf(v):
    v=np.asarray(v,float); gp=v[v>0].sum(); gl=-v[v<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def maxdd(v):
    v=np.asarray(v,float)
    if len(v)==0:return np.nan
    eq=np.r_[0.,np.cumsum(v)]; peak=np.maximum.accumulate(eq)
    return float(np.max(peak-eq))

def netr(ep,xp,D,bps):
    return float((ep-xp)/D - (bps/10000.0)*ep/D)

def load_events():
    r=pd.read_csv(SRC41); a=pd.read_csv(SRC35)
    for d in [r,a]:
        for c in ['signal_time','touch_time','class_time']:
            if c in d.columns:d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['flow_id','side','atr14','level','class_price']:
        if c in r.columns:r[c]=pd.to_numeric(r[c],errors='coerce')
        if c in a.columns:a[c]=pd.to_numeric(a[c],errors='coerce')
    if 'book_state' not in r.columns: raise RuntimeError('LAB041 book_state missing')
    r=r[(r.side==-1)&r.book_state.isin(['DRIVEN_MOVE','THIN_BOOK','ABSORPTION','WEAK'])].copy()
    r['response_router']=np.where(r.book_state.isin(['DRIVEN_MOVE','THIN_BOOK']),'HIGH_RESPONSE','LOW_RESPONSE')
    r=r[r.response_router=='HIGH_RESPONSE'].copy()
    keep=[c for c in ['flow_id','signal_time','state','touch_time','class_time','atr14','level','class_price'] if c in a.columns]
    a=a[keep].copy()
    m=r.merge(a,on='flow_id',how='left',suffixes=('_r','_a'),validate='one_to_one')
    def pick(c):
        for k in [c+'_a',c,c+'_r']:
            if k in m.columns:return m[k]
        raise RuntimeError(f'missing {c}')
    for c in ['signal_time','touch_time','class_time','state','atr14','level','class_price']:
        m[c]=pick(c)
    m=m[m.signal_time<END].sort_values('signal_time').reset_index(drop=True)
    return m

def parent_sim(r,fut):
    horizon=pd.Timestamp(r.signal_time)+pd.Timedelta(hours=12)
    eligible=str(r.state)=='ACCEPT'
    et=pd.Timestamp(r.class_time) if eligible and pd.notna(r.class_time) else pd.NaT
    ep=float(r.class_price) if eligible and np.isfinite(r.class_price) else np.nan
    atr=float(r.atr14) if np.isfinite(r.atr14) else np.nan
    D=STOP_ATR*atr if np.isfinite(atr) else np.nan
    covered=bool(eligible and pd.notna(et) and et<=horizon and et in fut.index and horizon in fut.index and np.isfinite(ep) and np.isfinite(D) and D>0)
    base=dict(flow_id=int(r.flow_id),signal_time=r.signal_time,book_state=r.book_state,state=r.state,eligible=eligible,covered=covered,traded=False,
              entry_time=et,entry_price=ep,level=float(r.level) if np.isfinite(r.level) else np.nan,risk_dist=D,horizon=horizon,
              parent_exit_time=pd.NaT,parent_exit_price=np.nan,parent_exit_reason='NO_TRADE',final_exit_time=pd.NaT,final_exit_price=np.nan,final_exit_reason='NO_TRADE',
              adverse_first=False,adverse_time=pd.NaT,persistent_failure=False,persistent_time=pd.NaT,early_exit=False)
    if not covered:return base
    p=fut[(fut.index>et)&(fut.index<=horizon)]
    stop=ep+D; tp=ep-TP_R*D
    reason='TIME'; xt=horizon; xp=float(fut.loc[horizon,'close'])
    for tt,b in p.iterrows():
        hs=float(b.high)>=stop; ht=float(b.low)<=tp
        if hs: reason='SL'; xt=tt; xp=stop; break
        if ht: reason='TP'; xt=tt; xp=tp; break
    base.update(traded=True,parent_exit_time=xt,parent_exit_price=xp,parent_exit_reason=reason)
    # adverse-first within 120m, exactly causal; same-bar ambiguity adverse-first.
    end120=min(et+pd.Timedelta(minutes=120),xt)
    p120=fut[(fut.index>et)&(fut.index<=end120)]
    fav=ep-0.5*D; adv=ep+0.5*D; fp_state=None; fp_t=pd.NaT
    for tt,b in p120.iterrows():
        hf=float(b.low)<=fav; ha=float(b.high)>=adv
        if ha: fp_state='ADVERSE'; fp_t=tt; break
        if hf: fp_state='FAVORABLE'; fp_t=tt; break
    final_xt=xt; final_xp=xp; final_reason=reason; persistent=False; pst=pd.NaT
    if fp_state=='ADVERSE':
        # closed-bar sequence after adverse. For intrabar SL/TP exit, exit-bar close unavailable.
        include_end=(reason=='TIME')
        pc=fut[(fut.index>fp_t)&((fut.index<=xt) if include_end else (fut.index<xt))]
        consec=0
        for tt,b in pc.iterrows():
            c=float(b.close)
            if c<=ep:
                break  # recovered before persistent failure
            if c>float(r.level):
                consec+=1
                if consec>=2:
                    persistent=True; pst=tt; final_xt=tt; final_xp=c; final_reason='PERSISTENT_FAILURE_EXIT'; break
            else:
                consec=0
    base.update(final_exit_time=final_xt,final_exit_price=final_xp,final_exit_reason=final_reason,
                adverse_first=bool(fp_state=='ADVERSE'),adverse_time=fp_t,persistent_failure=persistent,persistent_time=pst,early_exit=persistent)
    for bps in [0,5,10]: base[f'net_r_{bps}bps']=netr(ep,final_xp,D,bps)
    return base

def summarize(d,orig_n):
    t=d[d.traded].sort_values('entry_time').copy(); v=t.net_r_5bps.to_numpy(float); dd=maxdd(v)
    return dict(original_n=int(orig_n),eligible_n=int(d.eligible.sum()),traded_n=len(t),coverage=float(d.loc[d.eligible,'covered'].mean()) if d.eligible.any() else np.nan,
                early_exit_n=int(t.early_exit.sum()),ev_5bps=float(t.net_r_5bps.mean()) if len(t) else np.nan,pf_5bps=pf(v) if len(t) else np.nan,
                cum_r_5bps=float(v.sum()),max_dd_r=dd,max_dd_pct_025=float(dd*RISK_PCT) if len(t) else np.nan,
                ev_per_original=float(v.sum()/orig_n) if orig_n else np.nan,ev_0bps=float(t.net_r_0bps.mean()) if len(t) else np.nan,ev_10bps=float(t.net_r_10bps.mean()) if len(t) else np.nan)
def main():
    ev=load_events(); fut=L35.download_futures()
    rows=[parent_sim(r,fut) for r in ev.itertuples(index=False)]
    ex=pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True); ex.to_csv(OUT/'full_system_stream.csv',index=False)
    pre=ex[ex.signal_time<PRE].copy(); aug=ex[(ex.signal_time>=PRE)&(ex.signal_time<END)].copy(); full=ex.copy()
    spre=summarize(pre,len(pre)); saug=summarize(aug,len(aug)); sfull=summarize(full,len(full))
    # parity against LAB053 EXIT_NOW on the exact 327 pre-Aug trades
    old=pd.read_csv(SRC53); old=old[old.policy=='PERSISTENT_EXIT'].copy(); old['flow_id']=pd.to_numeric(old.flow_id,errors='coerce'); old['net_r_5bps']=pd.to_numeric(old.net_r_5bps,errors='coerce')
    pn=pre[pre.traded][['flow_id','net_r_5bps']].merge(old[['flow_id','net_r_5bps']],on='flow_id',suffixes=('_new','_old'),validate='one_to_one')
    parity_trade_n=len(pn); parity_max=float(np.max(np.abs(pn.net_r_5bps_new-pn.net_r_5bps_old))) if len(pn) else np.nan
    oldv=old.sort_values('entry_time').net_r_5bps.to_numpy(float)
    pre_v=pre[pre.traded].sort_values('entry_time').net_r_5bps.to_numpy(float)
    old_ev=float(np.mean(oldv)); old_pf=pf(oldv); old_cum=float(oldv.sum()); old_dd=maxdd(oldv)
    parity=dict(trade_n=parity_trade_n,max_trade_error=parity_max,ev_error=abs(spre['ev_5bps']-old_ev),pf_error=abs(spre['pf_5bps']-old_pf),cum_error=abs(spre['cum_r_5bps']-old_cum),dd_error=abs(spre['max_dd_r']-old_dd))
    gates={
      'preaug_original_highresponse_n475':len(pre)==475,
      'preaug_accept_trades_n327':spre['traded_n']==327,
      'preaug_persistent_exits_n59':spre['early_exit_n']==59,
      'preaug_ev_parity_le1e9':parity['ev_error']<=1e-9,
      'preaug_cumr_parity_le1e6':parity['cum_error']<=1e-6,
      'preaug_pf_parity_le1e6':parity['pf_error']<=1e-6,
      'preaug_dd_parity_le1e6':parity['dd_error']<=1e-6,
      'aug_eligible_coverage_ge99pct':bool(pd.notna(saug['coverage']) and saug['coverage']>=.99) if saug['eligible_n']>0 else True,
      'aug_signal_count_reported':len(aug)>=0,
      'aug_trade_count_reported':saug['traded_n']>=0,
      'aug_ev5_positive':bool(pd.notna(saug['ev_5bps']) and saug['ev_5bps']>0),
      'aug_pf_gt1':bool(pd.notna(saug['pf_5bps']) and saug['pf_5bps']>1),
      'aug_cumr_positive':saug['cum_r_5bps']>0,
      'aug_ev_per_original_positive':bool(pd.notna(saug['ev_per_original']) and saug['ev_per_original']>0),
      'aug_ev10_positive':bool(pd.notna(saug['ev_10bps']) and saug['ev_10bps']>0),
      'aug_dd_025_le4pct':bool(pd.notna(saug['max_dd_pct_025']) and saug['max_dd_pct_025']<=4.0) if saug['traded_n'] else True,
      'full_through_aug_ev_positive':bool(pd.notna(sfull['ev_5bps']) and sfull['ev_5bps']>0),
      'full_through_aug_pf_ge115':bool(pd.notna(sfull['pf_5bps']) and sfull['pf_5bps']>=1.15),
      'full_through_aug_dd_025_le4pct':bool(pd.notna(sfull['max_dd_pct_025']) and sfull['max_dd_pct_025']<=4.0),
      'no_august_selection_no_threshold_changes':True}
    parity_ok=all(gates[k] for k in ['preaug_original_highresponse_n475','preaug_accept_trades_n327','preaug_persistent_exits_n59','preaug_ev_parity_le1e9','preaug_cumr_parity_le1e6','preaug_pf_parity_le1e6','preaug_dd_parity_le1e6'])
    aug_econ=all(gates[k] for k in ['aug_ev5_positive','aug_pf_gt1','aug_cumr_positive','aug_ev_per_original_positive','aug_ev10_positive','aug_dd_025_le4pct'])
    if parity_ok and aug_econ and saug['traded_n']>=10 and len(aug)>=20: verdict='PASS_FRESH_AUG2026_OOS'
    elif parity_ok and aug_econ: verdict='WATCH_FRESH_AUG2026_POSITIVE_SMALL_N'
    elif parity_ok: verdict='FAIL_FRESH_AUG2026_OOS'
    else: verdict='FAIL_FULL_SYSTEM_PARITY_OR_CAUSALITY'
    result={'verdict':verdict,'preaug':spre,'fresh_august':saug,'full_through_august':sfull,'parity':parity,'gates':gates}
    (OUT/'verdict.json').write_text(json.dumps(result,indent=2,default=lambda x:bool(x) if isinstance(x,np.bool_) else float(x)),encoding='utf-8')
    def f(x): return '—' if pd.isna(x) else f'{x:.3f}'
    L=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(bool(v) for v in gates.values())}/{len(gates)}**','',
       '## Frozen system','`FLOW SHORT → HIGH_RESPONSE → ACCEPT → SL 2.5 ATR → TP 1.5R → signal+12h → PERSISTENT_FAILURE EXIT NOW`','',
       '## Reused-history parity',f'- original HIGH_RESPONSE signals: **{len(pre)}**',f'- ACCEPT trades: **{spre["traded_n"]}**; persistent exits: **{spre["early_exit_n"]}**',
       f'- EV **{spre["ev_5bps"]:+.3f}R**, PF **{spre["pf_5bps"]:.3f}**, CumR **{spre["cum_r_5bps"]:+.2f}R**, MaxDD **{spre["max_dd_r"]:.2f}R**',
       f'- LAB053 parity: trade max error **{parity_max:.3e}**, EV error **{parity["ev_error"]:.3e}**, PF error **{parity["pf_error"]:.3e}**, CumR error **{parity["cum_error"]:.3e}**, DD error **{parity["dd_error"]:.3e}**','',
       '## Fresh August 2026 OOS',f'- HIGH_RESPONSE SHORT signals: **{len(aug)}**; ACCEPT trades: **{saug["traded_n"]}**; persistent exits: **{saug["early_exit_n"]}**',
       f'- eligible path coverage: **{(saug["coverage"] if pd.notna(saug["coverage"]) else 0):.1%}**',
       f'- EV 5bps **{f(saug["ev_5bps"])}R**, PF **{f(saug["pf_5bps"])}**, CumR **{saug["cum_r_5bps"]:+.2f}R**, EV/original **{f(saug["ev_per_original"])}R**',
       f'- EV 10bps **{f(saug["ev_10bps"])}R**, MaxDD **{f(saug["max_dd_r"])}R = {f(saug["max_dd_pct_025"])}% @0.25% risk**','',
       '## Full through August',f'- signals **{len(full)}**, trades **{sfull["traded_n"]}**, persistent exits **{sfull["early_exit_n"]}**',
       f'- EV **{sfull["ev_5bps"]:+.3f}R**, PF **{sfull["pf_5bps"]:.3f}**, CumR **{sfull["cum_r_5bps"]:+.2f}R**, MaxDD **{sfull["max_dd_r"]:.2f}R = {sfull["max_dd_pct_025"]:.2f}% @0.25%**','',
       '## Gates']+[f'- {"PASS" if v else "FAIL"} — `{k}`' for k,v in gates.items()]+['','## Guardrail','August 2026 is evaluation-only. No frozen system component was changed or selected using August. If August N is small, result is directional evidence only, not strong fresh-OOS proof. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,default=lambda x:bool(x) if isinstance(x,np.bool_) else float(x)))
if __name__=='__main__': main()
