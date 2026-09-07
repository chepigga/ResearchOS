#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_ADVERSE_EXCURSION_FIRST_PASSAGE_LIMIT_ENTRY_AND_TIME_EXIT_LAB_025'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC23=LABS/'BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab023',SRC23)
L23=importlib.util.module_from_spec(spec); spec.loader.exec_module(L23)

EXPECTED_FLOW_N=3209
DEPTHS=[0.5,1.0,1.5,2.0]
PRIMARY_DEPTH=1.0
EXIT_BARS=48
STOP_ATR=1.5
COST_BPS=5.0
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
    sd=a.std(ddof=1)
    return float(a.mean()/(sd/math.sqrt(len(a)))) if sd>0 else np.nan

def pf(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    pos=float(a[a>0].sum()); neg=float(-a[a<0].sum())
    if neg==0:return np.inf if pos>0 else np.nan
    return pos/neg

def maxdd(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if not len(a):return 0.0
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq]); return float(np.max(peak[1:]-eq))

def load_inputs():
    price=L23.load_price(); flow=L23.load_flow()
    if len(flow)!=EXPECTED_FLOW_N:raise RuntimeError(f'Flow lineage mismatch {len(flow)} != {EXPECTED_FLOW_N}')
    parity=float(flow.signal_time.isin(price.index).mean())
    if parity<.99:raise RuntimeError(f'Flow/price timestamp parity {parity:.3%}')
    return price,flow,parity

def cost_atr(entry,atr):
    return float(entry*(COST_BPS/10000.0)/atr)

def immediate_table(price,flow):
    pos=pd.Series(np.arange(len(price),dtype=int),index=price.index)
    rows=[]
    for fid,r in flow.iterrows():
        t=pd.Timestamp(r.signal_time)
        if t not in pos.index:continue
        i=int(pos.loc[t]); end=i+EXIT_BARS
        if end>=len(price):continue
        atr=float(price.atr14.iloc[i]); p0=float(price.close.iloc[i]); side=int(r.side)
        if not np.isfinite(atr) or atr<=0:continue
        endpx=float(price.close.iloc[end])
        gross=float(side*(endpx-p0)/atr); cost=cost_atr(p0,atr)
        rows.append(dict(flow_id=int(fid),signal_time=t,side=side,signal_i=i,signal_close=p0,atr0=atr,horizon_time=price.index[end],horizon_close=endpx,gross_atr=gross,cost_atr=cost,net_atr=gross-cost))
    return pd.DataFrame(rows)

def first_passage_one(price,r,depth):
    i=int(r.signal_i); side=int(r.side); p0=float(r.signal_close); atr=float(r.atr0); end=i+EXIT_BARS
    limit=float(p0-side*depth*atr)
    fill_i=None
    for k in range(i+1,end+1):
        lo=float(price.low.iloc[k]); hi=float(price.high.iloc[k])
        hit=(lo<=limit) if side>0 else (hi>=limit)
        if hit:
            fill_i=k; break
    if fill_i is None:
        return dict(filled=False,depth_atr=depth,limit_price=limit,fill_i=np.nan,fill_time=pd.NaT,delay_bars=np.nan,delay_hours=np.nan,net_atr=np.nan,bounded_net_atr=np.nan,stopped=np.nan,postfill_mae_atr=np.nan,postfill_mfe_atr=np.nan)
    endpx=float(price.close.iloc[end]); gross=float(side*(endpx-limit)/atr); cost=cost_atr(limit,atr); net=gross-cost
    mae=0.0; mfe=0.0; stop_price=float(limit-side*STOP_ATR*atr); stopped=False; bounded_gross=None
    for k in range(fill_i,end+1):
        lo=float(price.low.iloc[k]); hi=float(price.high.iloc[k])
        fav=max(0.0,hi-limit) if side>0 else max(0.0,limit-lo)
        adv=max(0.0,limit-lo) if side>0 else max(0.0,hi-limit)
        mfe=max(mfe,fav/atr); mae=max(mae,adv/atr)
        stop_hit=(lo<=stop_price) if side>0 else (hi>=stop_price)
        if stop_hit and not stopped:
            stopped=True; bounded_gross=-STOP_ATR
            # conservative same-bar ambiguity is automatically STOP because this loop includes fill bar.
            break
    if not stopped: bounded_gross=gross
    bounded_net=float(bounded_gross-cost)
    return dict(filled=True,depth_atr=depth,limit_price=limit,fill_i=int(fill_i),fill_time=price.index[fill_i],delay_bars=int(fill_i-i),delay_hours=float((fill_i-i)*.25),net_atr=float(net),bounded_net_atr=bounded_net,stopped=bool(stopped),postfill_mae_atr=float(mae),postfill_mfe_atr=float(mfe))

def build_depth(price,imm,depth):
    rows=[]
    for r in imm.itertuples():
        z=first_passage_one(price,r,depth)
        d=r._asdict(); d.update(z)
        rows.append(d)
    return pd.DataFrame(rows)

def summarize_policy(d,label,metric_col='net_atr'):
    n_sig=len(d); f=d[d.filled].copy(); vals=pd.to_numeric(f[metric_col],errors='coerce').dropna().to_numpy(float)
    policy_total=float(np.nansum(vals)); policy_ev=float(policy_total/n_sig) if n_sig else np.nan
    return dict(sample=label,signals=n_sig,fills=len(f),fill_rate=float(len(f)/n_sig) if n_sig else np.nan,ev_per_fill=float(np.mean(vals)) if len(vals) else np.nan,policy_ev_per_signal=policy_ev,cum_atr=policy_total,t_fill=tstat(vals),pf_fill=pf(vals),dd_fill=maxdd(vals),median_delay_h=float(f.delay_hours.median()) if len(f) else np.nan,mean_delay_h=float(f.delay_hours.mean()) if len(f) else np.nan,median_postfill_mae=float(f.postfill_mae_atr.median()) if len(f) else np.nan,median_postfill_mfe=float(f.postfill_mfe_atr.median()) if len(f) else np.nan,stop_rate=float(f.stopped.mean()) if len(f) and 'stopped' in f else np.nan,long_fills=int((f.side==1).sum()) if len(f) else 0,short_fills=int((f.side==-1).sum()) if len(f) else 0)

def summarize_immediate(imm,label='IMMEDIATE_NOSTOP'):
    a=imm.net_atr.to_numpy(float) if len(imm) else np.array([])
    return dict(sample=label,signals=len(imm),fills=len(imm),fill_rate=1.0 if len(imm) else np.nan,ev_per_fill=float(a.mean()) if len(a) else np.nan,policy_ev_per_signal=float(a.mean()) if len(a) else np.nan,cum_atr=float(a.sum()) if len(a) else 0.0,t_fill=tstat(a),pf_fill=pf(a),dd_fill=maxdd(a),median_delay_h=0.0,mean_delay_h=0.0,median_postfill_mae=np.nan,median_postfill_mfe=np.nan,stop_rate=np.nan,long_fills=int((imm.side==1).sum()) if len(imm) else 0,short_fills=int((imm.side==-1).sum()) if len(imm) else 0)

def matched_immediate(depth_df):
    q=depth_df[depth_df.filled].copy()
    a=q.net_atr_x.to_numpy(float) if 'net_atr_x' in q.columns else q['net_atr'].to_numpy(float)
    return float(np.mean(a)) if len(a) else np.nan

def normalize_columns(d):
    # Immediate net arrives as net_atr; passive result from first_passage also uses net_atr.
    # Rename immediate columns before merge semantics become ambiguous.
    if 'net_atr' in d.columns and 'immediate_net_atr' not in d.columns:
        pass
    return d

def window_mask(d,a,b):
    a=pd.Timestamp(a,tz=UTC); b=pd.Timestamp(b,tz=UTC)
    return (d.signal_time>=a)&(d.signal_time<b)

def window_summary(d,depth):
    rows=[]
    for w,(a,b) in WINS.items():
        q=d[window_mask(d,a,b)].copy(); m=summarize_policy(q,w,'limit_net_atr'); m.update(window=w,depth_atr=depth); rows.append(m)
    return pd.DataFrame(rows)

def side_summary(d):
    pre=d[d.signal_time<pd.Timestamp('2026-08-01',tz=UTC)].copy(); rows=[]
    for side,name in [(1,'LONG'),(-1,'SHORT')]:
        q=pre[pre.side==side].copy(); m=summarize_policy(q,name,'limit_net_atr'); m.update(side=name); rows.append(m)
    return pd.DataFrame(rows)

def prepare_depth(price,imm,depth):
    rows=[]
    for r in imm.itertuples():
        z=first_passage_one(price,r,depth)
        d=r._asdict()
        # preserve immediate economics explicitly
        d['immediate_net_atr']=float(r.net_atr); d['immediate_gross_atr']=float(r.gross_atr)
        d.pop('net_atr',None); d.pop('gross_atr',None)
        d.update(z)
        d['limit_net_atr']=d.pop('net_atr')
        d['limit_bounded_net_atr']=d.pop('bounded_net_atr')
        rows.append(d)
    return pd.DataFrame(rows)

def matched_stats(d):
    q=d[d.filled].copy()
    if not len(q):return dict(n=0,limit_ev=np.nan,immediate_ev=np.nan,increment=np.nan)
    return dict(n=len(q),limit_ev=float(q.limit_net_atr.mean()),immediate_ev=float(q.immediate_net_atr.mean()),increment=float((q.limit_net_atr-q.immediate_net_atr).mean()))

def report(overall,matched,windows,sides,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
           '## Frozen parity',f"- flow lineage: **{meta['flow_n']}**",f"- eligible pre-Aug signals: **{meta['pre_aug_signals']}**",f"- timestamp parity: **{meta['timestamp_parity']:.2%}**",'',
           '## Policy economics by adverse depth','', '| Sample | Signals | Fills | Fill% | EV/fill | Policy EV/signal | Cum ATR | PF fill | Delay h | Post-fill MAE | Stop rate |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in overall.iterrows():
        lines.append(f"| {r['sample']} | {int(r.signals)} | {int(r.fills)} | {f(r.fill_rate)} | {f(r.ev_per_fill)} | {f(r.policy_ev_per_signal)} | {f(r.cum_atr)} | {f(r.pf_fill)} | {f(r.median_delay_h)} | {f(r.median_postfill_mae)} | {f(r.stop_rate)} |")
    lines += ['', '## Matched immediate comparison','', '| Depth | N filled | Limit EV | Immediate EV same signals | Increment |','|---:|---:|---:|---:|---:|']
    for _,r in matched.iterrows(): lines.append(f"| {f(r.depth_atr)} | {int(r.n)} | {f(r.limit_ev)} | {f(r.immediate_ev)} | {f(r.increment)} |")
    lines += ['', '## Primary 1.0 ATR by window','', '| Window | Signals | Fills | Fill% | EV/fill | Policy EV/signal | Cum ATR | PF fill | Stop | L/S fills |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in windows.iterrows():lines.append(f"| {r.window} | {int(r.signals)} | {int(r.fills)} | {f(r.fill_rate)} | {f(r.ev_per_fill)} | {f(r.policy_ev_per_signal)} | {f(r.cum_atr)} | {f(r.pf_fill)} | {f(r.stop_rate)} | {int(r.long_fills)}/{int(r.short_fills)} |")
    lines += ['', '## Primary 1.0 ATR pre-Aug by side','', '| Side | Signals | Fills | Fill% | EV/fill | Policy EV/signal | Cum ATR | PF fill |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in sides.iterrows():lines.append(f"| {r.side} | {int(r.signals)} | {int(r.fills)} | {f(r.fill_rate)} | {f(r.ev_per_fill)} | {f(r.policy_ev_per_signal)} | {f(r.cum_atr)} | {f(r.pf_fill)} |")
    lines += ['', '## Gates']
    for k,v in gates.items():lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## Guardrail','Primary depth is frozen at 1.0 ATR. Unfilled orders contribute zero to policy EV. No H4 direction, price-pattern filter, TP, depth optimization, or market fallback is used. August 2026 is reused audit only. Live allocation = **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price,flow,parity=load_inputs(); imm=immediate_table(price,flow)
    # hard parity with frozen LAB024 payoff convention before cost
    if len(imm)<3000:raise RuntimeError(f'Eligible immediate rows too low {len(imm)}')
    pre_cut=pd.Timestamp('2026-08-01',tz=UTC)
    imm_pre=imm[imm.signal_time<pre_cut].copy()
    overall_rows=[summarize_immediate(imm_pre,'IMMEDIATE_NOSTOP_ALL_SIGNALS')]
    depth_map={}; match_rows=[]
    for depth in DEPTHS:
        d=prepare_depth(price,imm,depth); depth_map[depth]=d; d.to_csv(OUT/f'depth_{str(depth).replace(".","p")}_events.csv',index=False)
        pre=d[d.signal_time<pre_cut].copy()
        no=summarize_policy(pre,f'LIMIT_{depth:.1f}ATR_NOSTOP','limit_net_atr'); overall_rows.append(no)
        bd=summarize_policy(pre,f'LIMIT_{depth:.1f}ATR_STOP15','limit_bounded_net_atr'); overall_rows.append(bd)
        ms=matched_stats(pre); ms['depth_atr']=depth; match_rows.append(ms)
    overall=pd.DataFrame(overall_rows); matched=pd.DataFrame(match_rows)
    overall.to_csv(OUT/'overall_summary.csv',index=False); matched.to_csv(OUT/'matched_immediate.csv',index=False)

    primary=depth_map[PRIMARY_DEPTH]; primary_pre=primary[primary.signal_time<pre_cut].copy()
    win_no=window_summary(primary,PRIMARY_DEPTH); win_no.to_csv(OUT/'primary_by_window_nostop.csv',index=False)
    side_no=side_summary(primary); side_no.to_csv(OUT/'primary_by_side_nostop.csv',index=False)

    # bounded window/side diagnostics
    rows=[]
    for w,(a,b) in WINS.items():
        q=primary[window_mask(primary,a,b)].copy(); m=summarize_policy(q,w,'limit_bounded_net_atr'); m.update(window=w); rows.append(m)
    win_bd=pd.DataFrame(rows); win_bd.to_csv(OUT/'primary_by_window_bounded.csv',index=False)
    rows=[]
    for side,name in [(1,'LONG'),(-1,'SHORT')]:
        q=primary_pre[primary_pre.side==side].copy(); m=summarize_policy(q,name,'limit_bounded_net_atr'); m.update(side=name); rows.append(m)
    side_bd=pd.DataFrame(rows); side_bd.to_csv(OUT/'primary_by_side_bounded.csv',index=False)

    def o(label):return overall[overall['sample']==label].iloc[0]
    imm_o=o('IMMEDIATE_NOSTOP_ALL_SIGNALS'); p_no=o('LIMIT_1.0ATR_NOSTOP'); p_bd=o('LIMIT_1.0ATR_STOP15')
    m1=matched[matched.depth_atr==1.0].iloc[0]
    y22_no=win_no[win_no.window=='2022'].iloc[0]; y22_bd=win_bd[win_bd.window=='2022'].iloc[0]
    # 2022 SHORT specifically
    a=pd.Timestamp('2022-01-01',tz=UTC); b=pd.Timestamp('2023-01-01',tz=UTC)
    y22s=primary[(primary.signal_time>=a)&(primary.signal_time<b)&(primary.side==-1)].copy()
    y22s_no=summarize_policy(y22s,'2022_SHORT','limit_net_atr'); y22s_bd=summarize_policy(y22s,'2022_SHORT_BD','limit_bounded_net_atr')
    recent=primary[(primary.signal_time>=pd.Timestamp('2025-07-01',tz=UTC))&(primary.signal_time<pre_cut)].copy(); recent_no=summarize_policy(recent,'RECENT','limit_net_atr')
    s_long=side_no[side_no.side=='LONG'].iloc[0]; s_short=side_no[side_no.side=='SHORT'].iloc[0]
    sens_positive=0
    for depth in [0.5,1.5,2.0]:
        if o(f'LIMIT_{depth:.1f}ATR_NOSTOP').policy_ev_per_signal>0:sens_positive+=1

    gates={
      'frozen_flow_lineage_3209_and_timestamp_parity':bool(len(flow)==3209 and parity>=.99),
      'pre_aug_eligible_signals_ge_3000':bool(len(imm_pre)>=3000),
      'primary_fill_rate_ge_35pct':bool(p_no.fill_rate>=.35),
      'primary_policy_ev_gt_immediate':bool(p_no.policy_ev_per_signal>imm_o.policy_ev_per_signal),
      'primary_policy_ev_ge_0_10atr':bool(p_no.policy_ev_per_signal>=.10),
      'matched_limit_improves_by_ge_0_50atr':bool(m1.increment>=.50),
      'primary_nostop_cum_positive':bool(p_no.cum_atr>0),
      'primary_bounded_policy_ev_positive':bool(p_bd.policy_ev_per_signal>0),
      'primary_bounded_pf_gt_1_20':bool(np.isfinite(p_bd.pf_fill) and p_bd.pf_fill>1.20),
      'primary_bounded_stop_rate_le_60pct':bool(p_bd.stop_rate<=.60),
      'stress_2022_short_nfill_ge60_and_nostop_cum_positive':bool(y22s_no.fills>=60 and y22s_no.cum_atr>0),
      'stress_2022_short_bounded_cum_positive':bool(y22s_bd.cum_atr>0),
      'long_and_short_nostop_policy_ev_positive':bool(s_long.policy_ev_per_signal>0 and s_short.policy_ev_per_signal>0),
      'recent_primary_nostop_policy_ev_positive':bool(recent_no.policy_ev_per_signal>0),
      'sensitivity_at_least_two_positive':bool(sens_positive>=2),
    }
    score=sum(gates.values()); critical=['frozen_flow_lineage_3209_and_timestamp_parity','primary_fill_rate_ge_35pct','primary_policy_ev_gt_immediate','primary_policy_ev_ge_0_10atr','primary_nostop_cum_positive','primary_bounded_policy_ev_positive','stress_2022_short_nfill_ge60_and_nostop_cum_positive','recent_primary_nostop_policy_ev_positive']
    if score>=12 and all(gates[k] for k in critical):verdict='PASS_ADVERSE_LIMIT_FIRST_PASSAGE_POLICY_EDGE'
    elif gates['matched_limit_improves_by_ge_0_50atr'] and gates['primary_nostop_cum_positive']:
        verdict='WATCH_ENTRY_PRICE_IMPROVES_BUT_POLICY_NOT_ROBUST'
    else:verdict='FAIL_ADVERSE_LIMIT_NO_POLICY_TRANSFER'
    meta=dict(verdict=verdict,flow_n=len(flow),timestamp_parity=parity,eligible_signals=len(imm),pre_aug_signals=len(imm_pre),primary_depth_atr=PRIMARY_DEPTH,aug_reused_audit=True)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates,'stress_2022_short_nostop':y22s_no,'stress_2022_short_bounded':y22s_bd},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(overall,matched,win_no,side_no,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__': main()
