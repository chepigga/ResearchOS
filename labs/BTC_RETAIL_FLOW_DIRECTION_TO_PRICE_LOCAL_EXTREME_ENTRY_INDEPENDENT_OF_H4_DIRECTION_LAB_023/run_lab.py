#!/usr/bin/env python3
from __future__ import annotations
import json, math, glob
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
FLOW_PATH=LABS/'BTC_BINANCE_RETAIL_FLOW_DIRECTION_X_H4_PIVOT_M15_PRICE_TIMING_LAB_022'/'output'/'flow_only_nonoverlap.csv'
EXPECTED_FLOW_N=3209
STOP_ATR=1.5
COST_BPS=5.0
SEARCH_BARS=48
EXIT12=48
EXIT24=96
PRIMARY='SWEEP_RECLAIM_4'
AUDITS=['EXTREME4_COLOR','PIVOT2X2_CONFIRMED']

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
UTC='UTC'

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
    eq=np.cumsum(a); peaks=np.maximum.accumulate(np.r_[0.0,eq]); return float(np.max(peaks[1:]-eq))

def load_price():
    parts=[]
    for p in sorted(glob.glob('btc15/**/*.csv',recursive=True)):
        d=pd.read_csv(p)
        if not {'time','open','high','low','close'}.issubset(d.columns):continue
        d=d[['time','open','high','low','close']].copy()
        d['time']=pd.to_datetime(d.time,errors='coerce',utc=True)
        for c in ['open','high','low','close']:d[c]=pd.to_numeric(d[c],errors='coerce')
        parts.append(d.dropna())
    if not parts:raise RuntimeError('No frozen btc15 CSVs loaded')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    pc=x.close.shift(1)
    tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr14']=tr.rolling(14,min_periods=14).mean()
    return x.set_index('time')

def load_flow():
    f=pd.read_csv(FLOW_PATH)
    f['signal_time']=pd.to_datetime(f.signal_time,errors='coerce',utc=True)
    f['side']=pd.to_numeric(f.side,errors='coerce').astype('Int64')
    f['signed12_atr']=pd.to_numeric(f.signed12_atr,errors='coerce')
    f=f.dropna(subset=['signal_time','side']).sort_values('signal_time').reset_index(drop=True)
    if len(f)!=EXPECTED_FLOW_N:raise RuntimeError(f'Frozen LAB022 flow parity failed: {len(f)} != {EXPECTED_FLOW_N}')
    if not set(f.side.astype(int).unique()).issubset({-1,1}):raise RuntimeError('Unexpected flow side')
    return f

def index_pos(price):
    return pd.Series(np.arange(len(price),dtype=int),index=price.index)

def trigger_at(price,k,side,rule):
    if k<4 or k>=len(price):return False,np.nan
    op=float(price.open.iloc[k]); cl=float(price.close.iloc[k]); hi=float(price.high.iloc[k]); lo=float(price.low.iloc[k])
    if rule in {'SWEEP_RECLAIM_4','EXTREME4_COLOR'}:
        if side<0:
            level=float(price.high.iloc[k-4:k].max())
            extreme=hi>level; color=cl<op
            reclaim=cl<level
        else:
            level=float(price.low.iloc[k-4:k].min())
            extreme=lo<level; color=cl>op
            reclaim=cl>level
        ok=extreme and color and (reclaim if rule=='SWEEP_RECLAIM_4' else True)
        return bool(ok),level
    if rule=='PIVOT2X2_CONFIRMED':
        if k<4:return False,np.nan
        p=k-2
        if side<0:
            pivot=float(price.high.iloc[p])>float(price.high.iloc[p-2:p].max()) and float(price.high.iloc[p])>float(price.high.iloc[p+1:p+3].max())
            confirm=cl<float(price.close.iloc[p]) and cl<op
            return bool(pivot and confirm),float(price.high.iloc[p])
        else:
            pivot=float(price.low.iloc[p])<float(price.low.iloc[p-2:p].min()) and float(price.low.iloc[p])<float(price.low.iloc[p+1:p+3].min())
            confirm=cl>float(price.close.iloc[p]) and cl>op
            return bool(pivot and confirm),float(price.low.iloc[p])
    raise KeyError(rule)

def find_triggers(price,flow,rule):
    pos=index_pos(price); rows=[]
    for fid,r in flow.iterrows():
        t=r.signal_time
        if t not in pos.index:continue
        i=int(pos.loc[t]); found=None; level=np.nan
        for k in range(i+1,min(i+1+SEARCH_BARS,len(price))):
            ok,lvl=trigger_at(price,k,int(r.side),rule)
            if ok:found=k; level=lvl; break
        if found is None:continue
        atr=float(price.atr14.iloc[found])
        if not np.isfinite(atr) or atr<=0:continue
        rows.append(dict(flow_id=int(fid),flow_signal_time=t,flow_i=i,side=int(r.side),frozen_flow_signed12_atr=float(r.signed12_atr),trigger_rule=rule,trigger_time=price.index[found],trigger_i=int(found),trigger_level=float(level),entry=float(price.close.iloc[found]),entry_atr=atr,delay_bars=int(found-i),delay_hours=float((found-i)*.25)))
    return pd.DataFrame(rows)

def simulate(price,entry_i,side,entry,atr,exit_bars=EXIT12,use_stop=True):
    end_i=entry_i+exit_bars
    if end_i>=len(price):return None
    stop=entry-side*STOP_ATR*atr
    actual=end_i; stopped=False; gross=None; mae=0.0; mfe=0.0
    for k in range(entry_i+1,end_i+1):
        hi=float(price.high.iloc[k]); lo=float(price.low.iloc[k])
        fav=max(0.0,hi-entry) if side>0 else max(0.0,entry-lo)
        adv=max(0.0,entry-lo) if side>0 else max(0.0,hi-entry)
        mfe=max(mfe,fav/atr); mae=max(mae,adv/atr)
        if use_stop:
            hit=(lo<=stop) if side>0 else (hi>=stop)
            if hit:
                actual=k; stopped=True; gross=-STOP_ATR; mae=max(mae,STOP_ATR); break
    if not stopped:
        exit_px=float(price.close.iloc[end_i]); gross=float(side*(exit_px-entry)/atr)
    cost=float(entry*(COST_BPS/10000.0)/atr)
    return dict(exit_time=price.index[actual],stopped=stopped,gross_atr=float(gross),cost_atr=cost,net_atr=float(gross-cost),mae_atr=float(mae),mfe_atr=float(mfe))

def execute_triggers(price,triggers,exit_bars=EXIT12,use_stop=True):
    rows=[]
    for r in triggers.itertuples():
        z=simulate(price,int(r.trigger_i),int(r.side),float(r.entry),float(r.entry_atr),exit_bars,use_stop)
        if z is None:continue
        d=r._asdict(); d.update(z); rows.append(d)
    return pd.DataFrame(rows)

def execute_immediate(price,flow):
    pos=index_pos(price); rows=[]
    for fid,r in flow.iterrows():
        t=r.signal_time
        if t not in pos.index:continue
        i=int(pos.loc[t]); atr=float(price.atr14.iloc[i])
        if not np.isfinite(atr) or atr<=0:continue
        entry=float(price.close.iloc[i])
        z=simulate(price,i,int(r.side),entry,atr,EXIT12,True)
        if z is None:continue
        rows.append(dict(flow_id=int(fid),flow_signal_time=t,side=int(r.side),entry_time=t,entry_i=i,entry=entry,entry_atr=atr,**z))
    return pd.DataFrame(rows)

def metrics(d,label):
    a=pd.to_numeric(d.net_atr,errors='coerce').dropna().to_numpy(float) if len(d) else np.array([])
    return dict(sample=label,n=int(len(a)),mean_net_atr=float(a.mean()) if len(a) else np.nan,cum_net_atr=float(a.sum()) if len(a) else 0.0,t=tstat(a),pf=pf(a),hit_rate=float((a>0).mean()) if len(a) else np.nan,max_dd_atr=maxdd(a),stop_rate=float(d.stopped.mean()) if len(d) and 'stopped' in d else np.nan,median_mae_atr=float(d.mae_atr.median()) if len(d) and 'mae_atr' in d else np.nan,median_mfe_atr=float(d.mfe_atr.median()) if len(d) and 'mfe_atr' in d else np.nan,long_n=int((d.side==1).sum()) if len(d) else 0,short_n=int((d.side==-1).sum()) if len(d) else 0)

def window_summary(d,label):
    rows=[]
    for w,(a,b) in WINS.items():
        a=pd.Timestamp(a,tz=UTC); b=pd.Timestamp(b,tz=UTC)
        q=d[(d.flow_signal_time>=a)&(d.flow_signal_time<b)].copy()
        m=metrics(q,label); m['window']=w; rows.append(m)
    return pd.DataFrame(rows)

def side_year_summary(d,label):
    rows=[]
    for y in range(2021,2027):
        a=pd.Timestamp(f'{y}-01-01',tz=UTC); b=pd.Timestamp(f'{y+1}-01-01',tz=UTC)
        if y==2026:b=pd.Timestamp('2026-08-01',tz=UTC)
        for side,name in [(1,'LONG'),(-1,'SHORT')]:
            q=d[(d.flow_signal_time>=a)&(d.flow_signal_time<b)&(d.side==side)].copy()
            m=metrics(q,label); m.update(year=y,side=name); rows.append(m)
    return pd.DataFrame(rows)

def flow_coverage(flow,triggers,end='2026-08-01'):
    end=pd.Timestamp(end,tz=UTC); f=flow[flow.signal_time<end]; t=triggers[triggers.flow_signal_time<end]
    return float(len(t)/len(f)) if len(f) else np.nan,len(t),len(f)

def report(overall,windows,sides,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
           '## Frozen lineage',f"- LAB022 flow events: **{meta['flow_n']}** (asserted exact).",f"- H4 fields read: **0**.",f"- Primary trigger coverage pre-Aug: **{meta['primary_coverage']:.1%}** ({meta['primary_trigger_n']}/{meta['pre_aug_flow_n']}).",'',
           '## Overall execution comparison','', '| Sample | N | Mean net ATR | Cum ATR | t | PF | Stop | Median MAE | Long/Short |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in overall.iterrows():
        lines.append(f"| {r['sample']} | {int(r.n)} | {f(r.mean_net_atr)} | {f(r.cum_net_atr)} | {f(r.t)} | {f(r.pf)} | {f(r.stop_rate)} | {f(r.median_mae_atr)} | {int(r.long_n)}/{int(r.short_n)} |")
    lines += ['', '## Primary by window','', '| Window | N | Mean net ATR | Cum ATR | PF | Stop | DD | Long/Short |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in windows.iterrows():
        lines.append(f"| {r.window} | {int(r.n)} | {f(r.mean_net_atr)} | {f(r.cum_net_atr)} | {f(r.pf)} | {f(r.stop_rate)} | {f(r.max_dd_atr)} | {int(r.long_n)}/{int(r.short_n)} |")
    lines += ['', '## Primary side/year','', '| Year | Side | N | Mean | Cum | PF | Stop |','|---:|---|---:|---:|---:|---:|---:|']
    for _,r in sides.iterrows():lines.append(f"| {int(r.year)} | {r.side} | {int(r.n)} | {f(r.mean_net_atr)} | {f(r.cum_net_atr)} | {f(r.pf)} | {f(r.stop_rate)} |")
    lines += ['', '## Gates']
    for k,v in gates.items():lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## Guardrail','Primary uses frozen LAB022 flow direction only. No H4 direction/context is read. Audits are diagnostics and cannot rescue the primary. August 2026 remains reused audit; live allocation = **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price=load_price(); flow=load_flow()
    # hard price parity: >99% frozen flow event timestamps must exist in M15 archive
    hit=flow.signal_time.isin(price.index).mean()
    if hit<.99:raise RuntimeError(f'Flow/price timestamp parity too low: {hit:.3%}')

    immediate=execute_immediate(price,flow); immediate['sample']='IMMEDIATE_FLOW_SL15_TIME12'
    primary_tr=find_triggers(price,flow,PRIMARY); primary=execute_triggers(price,primary_tr,EXIT12,True); primary['sample']='PRIMARY_SWEEP_RECLAIM4_SL15_TIME12'
    nostop=execute_triggers(price,primary_tr,EXIT12,False); nostop['sample']='AUDIT_PRIMARY_NOSTOP_TIME12'
    time24=execute_triggers(price,primary_tr,EXIT24,True); time24['sample']='AUDIT_PRIMARY_SL15_TIME24'
    audit_frames=[]
    for rule in AUDITS:
        tr=find_triggers(price,flow,rule); ex=execute_triggers(price,tr,EXIT12,True); ex['sample']=f'AUDIT_{rule}_SL15_TIME12'; audit_frames.append(ex); tr.to_csv(OUT/f'triggers_{rule.lower()}.csv',index=False)
    primary_tr.to_csv(OUT/'triggers_sweep_reclaim_4.csv',index=False)
    immediate.to_csv(OUT/'immediate_flow_trades.csv',index=False); primary.to_csv(OUT/'primary_trades.csv',index=False); nostop.to_csv(OUT/'primary_nostop_audit.csv',index=False); time24.to_csv(OUT/'primary_time24_audit.csv',index=False)

    pre=lambda d:d[d.flow_signal_time<pd.Timestamp('2026-08-01',tz=UTC)].copy()
    frames=[pre(immediate),pre(primary),pre(nostop),pre(time24)]+[pre(x) for x in audit_frames]
    overall=pd.DataFrame([metrics(d,d['sample'].iloc[0] if len(d) else name) for d,name in zip(frames,['IMMEDIATE_FLOW_SL15_TIME12','PRIMARY_SWEEP_RECLAIM4_SL15_TIME12','AUDIT_PRIMARY_NOSTOP_TIME12','AUDIT_PRIMARY_SL15_TIME24']+[f'AUDIT_{r}_SL15_TIME12' for r in AUDITS])])
    overall.to_csv(OUT/'overall_summary.csv',index=False)
    windows=window_summary(primary,'PRIMARY'); windows.to_csv(OUT/'primary_by_window.csv',index=False)
    sides=side_year_summary(primary,'PRIMARY'); sides.to_csv(OUT/'primary_side_year.csv',index=False)

    cov,trn,fn=flow_coverage(flow,primary_tr)
    pim=metrics(pre(immediate),'immediate'); ppm=metrics(pre(primary),'primary'); pns=metrics(pre(nostop),'nostop')
    y22=pre(primary); y22=y22[(y22.flow_signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(y22.flow_signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(y22.side==-1)]
    short=pre(primary)[pre(primary).side==-1]; long=pre(primary)[pre(primary).side==1]
    short_year=sides[(sides.side=='SHORT')&(sides.year<=2025)]
    positive_short_years=int((short_year.cum_net_atr>0).sum())
    recent=pre(primary)[pre(primary).flow_signal_time>=pd.Timestamp('2025-07-01',tz=UTC)]
    gates={
      'frozen_flow_lineage_exact_3209':len(flow)==EXPECTED_FLOW_N,
      'primary_trigger_coverage_ge_30pct':bool(cov>=.30),
      'primary_pre_aug_n_ge_700':len(pre(primary))>=700,
      'primary_mean_net_atr_positive':bool(np.isfinite(ppm['mean_net_atr']) and ppm['mean_net_atr']>0),
      'primary_pf_gt_1_20':bool(np.isfinite(ppm['pf']) and ppm['pf']>1.20),
      'primary_improves_immediate_by_ge_0_10atr':bool(np.isfinite(ppm['mean_net_atr']) and np.isfinite(pim['mean_net_atr']) and ppm['mean_net_atr']>=pim['mean_net_atr']+.10),
      'primary_stop_rate_reduced_ge_10pp':bool(np.isfinite(ppm['stop_rate']) and np.isfinite(pim['stop_rate']) and ppm['stop_rate']<=pim['stop_rate']-.10),
      'stress_2022_short_n_ge_40_and_cum_positive':bool(len(y22)>=40 and y22.net_atr.sum()>0),
      'short_pooled_positive_and_ge4_of5_years_positive':bool(len(short) and short.net_atr.mean()>0 and positive_short_years>=4),
      'long_pooled_mean_positive':bool(len(long) and long.net_atr.mean()>0),
      'recent_cum_positive':bool(len(recent) and recent.net_atr.sum()>0),
      'primary_nostop_time12_mean_positive':bool(np.isfinite(pns['mean_net_atr']) and pns['mean_net_atr']>0),
    }
    score=int(sum(bool(v) for v in gates.values())); critical=['frozen_flow_lineage_exact_3209','primary_trigger_coverage_ge_30pct','primary_pre_aug_n_ge_700','primary_mean_net_atr_positive','primary_pf_gt_1_20','primary_improves_immediate_by_ge_0_10atr','stress_2022_short_n_ge_40_and_cum_positive']
    if score>=9 and all(gates[k] for k in critical):verdict='PASS_FLOW_DIRECTION_X_LOCAL_EXTREME_TIMING'
    elif gates['primary_mean_net_atr_positive'] and (gates['primary_improves_immediate_by_ge_0_10atr'] or gates['primary_stop_rate_reduced_ge_10pp']):verdict='WATCH_LOCAL_EXTREME_TIMING_PARTIAL'
    else:verdict='FAIL_LOCAL_EXTREME_TIMING_NO_TRANSFER'
    meta=dict(verdict=verdict,flow_n=len(flow),price_timestamp_coverage=float(hit),primary_coverage=cov,primary_trigger_n=trn,pre_aug_flow_n=fn,positive_short_years_2021_2025=positive_short_years,primary_minus_immediate_mean_atr=float(ppm['mean_net_atr']-pim['mean_net_atr']) if np.isfinite(ppm['mean_net_atr']) and np.isfinite(pim['mean_net_atr']) else np.nan,stop_rate_improvement_pp=float(100*(pim['stop_rate']-ppm['stop_rate'])) if np.isfinite(ppm['stop_rate']) and np.isfinite(pim['stop_rate']) else np.nan)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(overall,windows,sides,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__':main()
