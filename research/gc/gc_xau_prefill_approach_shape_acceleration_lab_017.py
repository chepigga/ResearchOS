#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT=Path('research/gc')
FEAT=ROOT/'GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016_FEATURES.csv'
SEQ=ROOT/'GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H_SEQUENCES.csv'
OUTJ=ROOT/'GC_XAU_PREFILL_APPROACH_SHAPE_ACCELERATION_LAB_017.json'
OUTM=ROOT/'GC_XAU_PREFILL_APPROACH_SHAPE_ACCELERATION_LAB_017.md'
OUTO=ROOT/'GC_XAU_PREFILL_APPROACH_SHAPE_ACCELERATION_LAB_017_OOF.csv'
INIT=45; BLOCK=12; Q=0.75

def as_bool(s):
    if s.dtype==bool: return s
    return s.astype(str).str.lower().isin(['true','1','yes'])

def maxdd(v):
    v=np.nan_to_num(np.asarray(v,float),nan=0.0)
    eq=np.cumsum(v); peak=np.maximum.accumulate(np.r_[0.0,eq]); return float((peak[1:]-eq).max()) if len(eq) else 0.0

def load_seq():
    s=pd.read_csv(SEQ,low_memory=False)
    s=s[s.cohort.eq('AMP_ALL')].copy()
    s['signal_time_utc']=pd.to_datetime(s.signal_time_utc,utc=True)
    s['adj_r_corrected']=pd.to_numeric(s.adj_r_corrected,errors='coerce').fillna(0.0)
    return s.sort_values('signal_time_utc').reset_index(drop=True)

def main():
    d=pd.read_csv(FEAT,low_memory=False)
    d['signal_time_utc']=pd.to_datetime(d.signal_time_utc,utc=True)
    d['warning_available']=as_bool(d.warning_available)
    d=d[d.warning_available].copy().reset_index(drop=True)
    rw=np.minimum(30.0,pd.to_numeric(d.warning_delay_sec,errors='coerce').to_numpy(float))
    rw=np.maximum(rw,1.0)
    d['recent_down_velocity30']= -pd.to_numeric(d.xau_mom_30s_warning_atr,errors='coerce').to_numpy(float)/rw
    d['lifetime_down_velocity']=pd.to_numeric(d.xau_approach_velocity_atr_per_sec,errors='coerce')
    d['acceleration_delta']=d.recent_down_velocity30-d.lifetime_down_velocity
    if d.acceleration_delta.isna().any(): raise SystemExit('NaN acceleration score')
    rows=[]; start=INIT; fold=0
    while start<len(d):
        end=min(start+BLOCK,len(d)); tr=d.iloc[:start]; te=d.iloc[start:end]
        thr=float(np.quantile(tr.acceleration_delta,Q))
        for _,r in te.iterrows():
            rows.append({'signal_time_utc':r.signal_time_utc.isoformat(),'status':r.status,'net_r':float(r.net_r),'sl_label':int(r.sl_label),'fold':fold,'acceleration_delta':float(r.acceleration_delta),'threshold':thr,'veto':bool(r.acceleration_delta>=thr)})
        fold+=1; start=end
    o=pd.DataFrame(rows); o.to_csv(OUTO,index=False)
    y=o.sl_label.to_numpy(int); score=o.acceleration_delta.to_numpy(float)
    auc=float(roc_auc_score(y,score)) if len(np.unique(y))==2 else np.nan
    veto=o.veto.astype(bool); base_sl=float(o.sl_label.mean()); veto_sl=float(o.loc[veto,'sl_label'].mean()) if veto.any() else np.nan
    enrich=float(veto_sl/base_sl) if np.isfinite(veto_sl) and base_sl>0 else np.nan
    seq=load_seq(); t0=o.signal_time_utc.min(); t1=o.signal_time_utc.max(); t0=pd.Timestamp(t0); t1=pd.Timestamp(t1)
    s=seq[(seq.signal_time_utc>=t0)&(seq.signal_time_utc<=t1)].copy().sort_values('signal_time_utc')
    veto_times=set(pd.to_datetime(o.loc[veto,'signal_time_utc'],utc=True))
    s['base_r']=s.adj_r_corrected
    s['overlay_r']=[0.0 if t in veto_times else float(r) for t,r in zip(s.signal_time_utc,s.base_r)]
    late=s.iloc[len(s)//2:]
    m={'original_signals_oof_period':int(len(s)),'baseline_sum_r':float(s.base_r.sum()),'overlay_sum_r':float(s.overlay_r.sum()),'baseline_ev_r_per_signal':float(s.base_r.mean()),'overlay_ev_r_per_signal':float(s.overlay_r.mean()),'baseline_maxdd_r':maxdd(s.base_r),'overlay_maxdd_r':maxdd(s.overlay_r),'late_half_baseline_ev_r':float(late.base_r.mean()),'late_half_overlay_ev_r':float(late.overlay_r.mean())}
    share=float(veto.mean())
    gates={'oof_auc_ge0_60':bool(np.isfinite(auc) and auc>=0.60),'veto_share_10_to_40pct':bool(0.10<=share<=0.40),'veto_sl_enrichment_ge1_25x':bool(np.isfinite(enrich) and enrich>=1.25),'overlay_sum_gt_baseline':m['overlay_sum_r']>m['baseline_sum_r'],'overlay_ev_gt_baseline':m['overlay_ev_r_per_signal']>m['baseline_ev_r_per_signal'],'overlay_maxdd_le_baseline':m['overlay_maxdd_r']<=m['baseline_maxdd_r']+1e-12,'late_half_overlay_ev_pos':m['late_half_overlay_ev_r']>0}
    passed=all(gates.values()); status='HISTORICAL_CAUSAL_ACCELERATION_GATE_PASS_NOT_OOS' if passed else 'HISTORICAL_CAUSAL_ACCELERATION_GATE_FAIL_NOT_OOS'
    result={'lab':'GC_XAU_PREFILL_APPROACH_SHAPE_ACCELERATION_LAB_017','status':status,'population':{'warning_eligible':int(len(d)),'oof':int(len(o)),'oof_sl':int(o.sl_label.sum())},'primary':{'auc_sl':auc,'vetoed':int(veto.sum()),'veto_share':share,'baseline_sl_rate':base_sl,'veto_sl_rate':veto_sl,'veto_sl_enrichment_x':enrich},'overlay':m,'gates':gates,'governance':{'new_market_data':False,'threshold_search':False,'warning_depth_search':False,'reclaimed_signals_simulated':False}}
    OUTJ.write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=[f"# GC_XAU_PREFILL_APPROACH_SHAPE_ACCELERATION_LAB_017\n\n**Status: {status}**\n",f"- OOF: **{len(o)}** | AUC: **{auc:.3f}**",f"- Veto: **{int(veto.sum())}/{len(o)} ({share:.1%})**",f"- SL rate baseline/veto: **{base_sl:.1%} / {veto_sl:.1%}** | enrichment **{enrich:.2f}x**",f"- SumR baseline -> overlay: **{m['baseline_sum_r']:+.2f}R -> {m['overlay_sum_r']:+.2f}R**",f"- EV/signal: **{m['baseline_ev_r_per_signal']:+.5f} -> {m['overlay_ev_r_per_signal']:+.5f}R**",f"- MaxDD: **{m['baseline_maxdd_r']:.2f}R -> {m['overlay_maxdd_r']:.2f}R**",f"- Late-half overlay EV/signal: **{m['late_half_overlay_ev_r']:+.5f}R**\n","## Gates"]
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    if not passed: lines.append('\nAcceleration overlay is rejected. Bare corrected D1/E3 remains the candidate.')
    OUTM.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
