#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_FLOW_LEVEL_PREBREAK_VOLUME_IGNITION_VS_ABSORPTION_AND_OI_CONTINUATION_LAB_036'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'output'/'activation_stream.csv'
SRC34=LABS/'BTC_FUTURES_RETAIL_CROWDING_X_SPOT_FLOW_DIVERGENCE_AND_OI_PROFITABILITY_MAP_LAB_034'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab034',SRC34); L34=importlib.util.module_from_spec(spec); spec.loader.exec_module(L34)
L34.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC'); AUG_END=pd.Timestamp('2026-09-01',tz='UTC')
SEED=20260908; BOOT_N=5000; BARS90=90*96; MINHIST=30*96
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01')}

def load_activation():
    d=pd.read_csv(SRC35)
    for c in ['signal_time','touch_time','class_time']:
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','atr14','residual_atr','frozen_signed12_atr']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    return d.sort_values('signal_time').reset_index(drop=True)

def augment_volume(x,prefix):
    q=pd.to_numeric(x['quote'],errors='coerce'); tb=pd.to_numeric(x['taker_buy_quote'],errors='coerce')
    for n,b in [(15,1),(30,2),(60,4)]:
        s=q.rolling(b,min_periods=b).sum().shift(1)
        med=s.shift(1).rolling(BARS90,min_periods=MINHIST).median()
        x[f'{prefix}_vol{n}_pre']=s
        x[f'{prefix}_vol{n}_logexp']=np.log(s.where(s>0)/med.where(med>0))
    q60=q.rolling(4,min_periods=4).sum().shift(1); tb60=tb.rolling(4,min_periods=4).sum().shift(1)
    x[f'{prefix}_imb60_pre']=(2*tb60-q60)/q60.replace(0,np.nan)
    if prefix=='fut':
        x['fut_vol60_q80_prior90']=q60.shift(1).rolling(BARS90,min_periods=MINHIST).quantile(.80)
    return x

def build_events(act,spot,fut,metrics):
    spot=augment_volume(spot.copy(),'spot'); fut=augment_volume(fut.copy(),'fut')
    rows=[]
    for r in act.itertuples(index=False):
        if r.state not in ('ACCEPT','REJECT') or pd.isna(r.touch_time):
            continue
        t=pd.Timestamp(r.touch_time); ct=pd.Timestamp(r.class_time) if pd.notna(r.class_time) else pd.NaT
        if t not in fut.index or t not in spot.index: continue
        fr=fut.loc[t]; sr=spot.loc[t]; side=int(r.side)
        fv=float(fr.get('fut_vol60_pre',np.nan)); fq=float(fr.get('fut_vol60_q80_prior90',np.nan))
        high=bool(np.isfinite(fv) and np.isfinite(fq) and fv>fq)
        fimb=float(fr.get('fut_imb60_pre',np.nan)); simb=float(sr.get('spot_imb60_pre',np.nan))
        row=dict(flow_id=int(r.flow_id),signal_time=r.signal_time,side=side,state=r.state,touch_time=t,class_time=ct,
                 atr14=float(r.atr14),lab035_residual_atr=float(r.residual_atr) if np.isfinite(r.residual_atr) else np.nan,
                 high_volume=high,high_volume_resolved=bool(np.isfinite(fv) and np.isfinite(fq)),
                 fut_vol15_logexp=float(fr.get('fut_vol15_logexp',np.nan)),fut_vol30_logexp=float(fr.get('fut_vol30_logexp',np.nan)),fut_vol60_logexp=float(fr.get('fut_vol60_logexp',np.nan)),
                 spot_vol15_logexp=float(sr.get('spot_vol15_logexp',np.nan)),spot_vol30_logexp=float(sr.get('spot_vol30_logexp',np.nan)),spot_vol60_logexp=float(sr.get('spot_vol60_logexp',np.nan)),
                 fut_imb60_pre=fimb,spot_imb60_pre=simb,fut_taker_aligned_60=side*fimb if np.isfinite(fimb) else np.nan,spot_taker_aligned_60=side*simb if np.isfinite(simb) else np.nan,
                 fut_minus_spot_vol60=float(fr.get('fut_vol60_logexp',np.nan)-sr.get('spot_vol60_logexp',np.nan)) if np.isfinite(fr.get('fut_vol60_logexp',np.nan)) and np.isfinite(sr.get('spot_vol60_logexp',np.nan)) else np.nan)
        row['activation_state']='IGNITION' if high and r.state=='ACCEPT' else ('ABSORPTION' if high and r.state=='REJECT' else ('LOWVOL_ACCEPT' if (not high) and r.state=='ACCEPT' else 'LOWVOL_REJECT'))
        row['oi_state']='UNRESOLVED'; row['oi_logchg_1h']=np.nan; row['oi_post1h_residual_atr']=np.nan
        if pd.notna(ct):
            c1=ct+pd.Timedelta(hours=1); endt=pd.Timestamp(r.signal_time)+pd.Timedelta(hours=12)
            if ct in metrics.index and c1 in metrics.index and c1 in fut.index and endt in fut.index and c1<=endt:
                a=float(metrics.loc[ct,'sum_open_interest']); b=float(metrics.loc[c1,'sum_open_interest'])
                if a>0 and b>0:
                    ch=float(np.log(b)-np.log(a)); row['oi_logchg_1h']=ch; row['oi_state']='OI_PERSIST' if ch>=0 else 'OI_FLUSH'
                    px1=float(fut.loc[c1,'close']); px2=float(fut.loc[endt,'close']); atr=float(r.atr14)
                    if atr>0: row['oi_post1h_residual_atr']=side*(px2-px1)/atr
        rows.append(row)
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)

def mean_hit(q,col):
    a=pd.to_numeric(q[col],errors='coerce').dropna().to_numpy(float)
    return (len(a),float(a.mean()) if len(a) else np.nan,float((a>0).mean()) if len(a) else np.nan)

def summary_states(d):
    rows=[]
    for name in ['IGNITION','ABSORPTION','LOWVOL_ACCEPT','LOWVOL_REJECT']:
        q=d[d.activation_state==name]; n,m,h=mean_hit(q,'lab035_residual_atr')
        rows.append(dict(state=name,n=len(q),resid_n=n,residual_mean=m,residual_hit=h,fut_vol60_logexp=float(q.fut_vol60_logexp.mean()),fut_taker_aligned=float(q.fut_taker_aligned_60.mean()),spot_taker_aligned=float(q.spot_taker_aligned_60.mean())))
    return pd.DataFrame(rows)

def oi_summary(d):
    q=d[d.state=='ACCEPT']; rows=[]
    for s in ['OI_PERSIST','OI_FLUSH','UNRESOLVED']:
        z=q[q.oi_state==s]; n,m,h=mean_hit(z,'oi_post1h_residual_atr')
        rows.append(dict(oi_state=s,n=len(z),resid_n=n,residual_mean=m,residual_hit=h,oi_logchg_mean=float(z.oi_logchg_1h.mean()) if len(z) else np.nan))
    return pd.DataFrame(rows)

def window_summary(d):
    rows=[]
    for w,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); q=d[(d.signal_time>=a)&(d.signal_time<b)&(d.activation_state=='IGNITION')]
        n,m,h=mean_hit(q,'lab035_residual_atr'); rows.append(dict(window=w,n=len(q),resid_n=n,residual_mean=m,residual_hit=h,long_n=int((q.side==1).sum()),short_n=int((q.side==-1).sum())))
    # fixed stress slice
    q=d[(d.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(d.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(d.side==-1)&(d.activation_state=='IGNITION')]
    n,m,h=mean_hit(q,'lab035_residual_atr'); rows.append(dict(window='2022_SHORT',n=len(q),resid_n=n,residual_mean=m,residual_hit=h,long_n=0,short_n=len(q)))
    return pd.DataFrame(rows)

def diag_summary(d):
    rows=[]
    for state in ['ACCEPT','REJECT']:
      for hv in [True,False]:
        q=d[(d.state==state)&(d.high_volume_resolved)&(d.high_volume==hv)]
        rows.append(dict(state=state,high_volume=hv,n=len(q),fut_vol15=float(q.fut_vol15_logexp.mean()),fut_vol30=float(q.fut_vol30_logexp.mean()),fut_vol60=float(q.fut_vol60_logexp.mean()),spot_vol60=float(q.spot_vol60_logexp.mean()),fut_taker_aligned=float(q.fut_taker_aligned_60.mean()),spot_taker_aligned=float(q.spot_taker_aligned_60.mean()),fut_minus_spot=float(q.fut_minus_spot_vol60.mean())))
    return pd.DataFrame(rows)

def boot_gap(d,group_col,a_name,b_name,pay_col):
    q=d[(d.signal_time<PRE)&(d[group_col].isin([a_name,b_name]))].copy(); q[pay_col]=pd.to_numeric(q[pay_col],errors='coerce'); q=q.dropna(subset=[pay_col])
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    arr=[]
    for _,g in q.groupby('cluster'):
        a=g.loc[g[group_col]==a_name,pay_col].to_numpy(float); b=g.loc[g[group_col]==b_name,pay_col].to_numpy(float); arr.append((a.sum(),len(a),b.sum(),len(b)))
    arr=np.asarray(arr,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        z=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if z[1]>0 and z[3]>0: vals.append(float(z[0]/z[1]-z[2]/z[3]))
    va=q.loc[q[group_col]==a_name,pay_col].mean(); vb=q.loc[q[group_col]==b_name,pay_col].mean(); v=np.asarray(vals,float)
    return dict(comparison=f'{a_name}-{b_name}',point=float(va-vb),clusters=m,draws=len(v),ci_lo=float(np.quantile(v,.025)) if len(v) else np.nan,ci_hi=float(np.quantile(v,.975)) if len(v) else np.nan)

def py(x):
    if isinstance(x,(np.bool_,)): return bool(x)
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,)): return None if not np.isfinite(x) else float(x)
    if isinstance(x,pd.Timestamp): return x.isoformat()
    raise TypeError(type(x).__name__)

def report(meta,ss,ois,ws,diag,boots,gates):
    def f(x): return '—' if pd.isna(x) else f'{float(x):.3f}'
    L=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'', '## Coverage',f"- LAB035 classified pre-Aug: **{meta['pre_classified']}**",f"- volume resolved pre-Aug: **{meta['vol_resolved']}** ({meta['vol_cov']:.1%})",f"- HIGH_VOLUME: **{meta['high_n']}**, ignition: **{meta['ign_n']}**, absorption: **{meta['abs_n']}**",f"- ACCEPT rate HIGH vs LOW: **{meta['high_accept_rate']:.3f} vs {meta['low_accept_rate']:.3f}** (gap {meta['accept_rate_gap']:+.3f})",'', '## Activation states','', '| State | N | Residual ATR | Hit | Fut vol60 exp | Fut taker aligned | Spot taker aligned |','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in ss.iterrows(): L.append(f"| {r['state']} | {int(r.n)} | {f(r.residual_mean)} | {f(r.residual_hit)} | {f(r.fut_vol60_logexp)} | {f(r.fut_taker_aligned)} | {f(r.spot_taker_aligned)} |")
    L+=['', '## OI continuation after ACCEPT (+1h classification)','', '| OI state | N | Post-1h residual | Hit | Mean OI logchg |','|---|---:|---:|---:|---:|']
    for _,r in ois.iterrows(): L.append(f"| {r.oi_state} | {int(r.n)} | {f(r.residual_mean)} | {f(r.residual_hit)} | {f(r.oi_logchg_mean)} |")
    L+=['','## Bootstrap','']
    for b in boots: L.append(f"- {b['comparison']}: **{b['point']:+.3f} ATR**, 7d bootstrap 95% CI **[{b['ci_lo']:+.3f}, {b['ci_hi']:+.3f}]**, clusters={b['clusters']}")
    L+=['','## IGNITION transfer','', '| Window | N | Residual | Hit | L/S |','|---|---:|---:|---:|---:|']
    for _,r in ws.iterrows(): L.append(f"| {r.window} | {int(r.n)} | {f(r.residual_mean)} | {f(r.residual_hit)} | {int(r.long_n)}/{int(r.short_n)} |")
    L+=['','## Volume diagnostics','', '| LAB035 state | High vol | N | Fut15 | Fut30 | Fut60 | Spot60 | Fut taker aligned | Spot taker aligned |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in diag.iterrows(): L.append(f"| {r['state']} | {int(r.high_volume)} | {int(r.n)} | {f(r.fut_vol15)} | {f(r.fut_vol30)} | {f(r.fut_vol60)} | {f(r.spot_vol60)} | {f(r.fut_taker_aligned)} | {f(r.spot_taker_aligned)} |")
    L+=['','## Gates']
    for k,v in gates.items(): L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    L+=['','## Guardrail','Frozen LAB035 flow/level/acceptance lineage. Pre-touch volume excludes touch bar. OI state is known only +1h after ACCEPT and its payoff starts after that classification. No entry/SL/TP optimization. August reused audit only. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n',encoding='utf-8')

def main():
    act=load_activation(); spot=L34.download_klines('spot'); fut=L34.download_klines('futures'); metrics=L34.download_metrics()
    d=build_events(act,spot,fut,metrics); d.to_csv(OUT/'volume_activation_stream.csv',index=False)
    pre=d[d.signal_time<PRE].copy(); pre_cls=act[(act.signal_time<PRE)&act.state.isin(['ACCEPT','REJECT'])]
    resolved=pre[pre.high_volume_resolved]; high=resolved[resolved.high_volume]; low=resolved[~resolved.high_volume]
    hi_acc=float((high.state=='ACCEPT').mean()) if len(high) else np.nan; lo_acc=float((low.state=='ACCEPT').mean()) if len(low) else np.nan
    ss=summary_states(pre); ois=oi_summary(pre); ws=window_summary(d); diag=diag_summary(pre)
    ss.to_csv(OUT/'activation_state_summary.csv',index=False); ois.to_csv(OUT/'oi_continuation_summary.csv',index=False); ws.to_csv(OUT/'ignition_window_summary.csv',index=False); diag.to_csv(OUT/'volume_diagnostics.csv',index=False)
    b1=boot_gap(d,'activation_state','IGNITION','ABSORPTION','lab035_residual_atr'); b2=boot_gap(d[d.state=='ACCEPT'],'oi_state','OI_PERSIST','OI_FLUSH','oi_post1h_residual_atr'); pd.DataFrame([b1,b2]).to_csv(OUT/'bootstrap.csv',index=False)
    def sm(state,col='residual_mean',table=ss):
        z=table[table.iloc[:,0]==state]; return float(z.iloc[0][col]) if len(z) else np.nan
    ign=sm('IGNITION'); abso=sm('ABSORPTION'); lowacc=sm('LOWVOL_ACCEPT')
    op=float(ois.loc[ois.oi_state=='OI_PERSIST','residual_mean'].iloc[0]) if (ois.oi_state=='OI_PERSIST').any() else np.nan
    of=float(ois.loc[ois.oi_state=='OI_FLUSH','residual_mean'].iloc[0]) if (ois.oi_state=='OI_FLUSH').any() else np.nan
    def wm(w):
        z=ws[ws.window==w]; return (int(z.n.iloc[0]),float(z.residual_mean.iloc[0])) if len(z) else (0,np.nan)
    n22s,m22s=wm('2022_SHORT'); nr,mr=wm('POOLED_RECENT'); n25,m25=wm('2025_H2'); n26,m26=wm('2026_JAN_JUL')
    meta=dict(pre_classified=len(pre_cls),vol_resolved=len(resolved),vol_cov=len(resolved)/len(pre_cls) if len(pre_cls) else 0,high_n=len(high),ign_n=int(((resolved.high_volume)&(resolved.state=='ACCEPT')).sum()),abs_n=int(((resolved.high_volume)&(resolved.state=='REJECT')).sum()),high_accept_rate=hi_acc,low_accept_rate=lo_acc,accept_rate_gap=hi_acc-lo_acc if np.isfinite(hi_acc) and np.isfinite(lo_acc) else np.nan)
    gates={
      'frozen_lab035_classified_ge_1900':len(pre_cls)>=1900,
      'futures_volume_coverage_ge_95pct':meta['vol_cov']>=.95,
      'spot_volume_coverage_ge_95pct':pre[['spot_vol60_logexp']].notna().mean().iloc[0]>=.95,
      'high_volume_n_ge_250':meta['high_n']>=250,
      'ignition_n_ge_150':meta['ign_n']>=150,
      'high_volume_accept_rate_gap_ge_0_05':np.isfinite(meta['accept_rate_gap']) and meta['accept_rate_gap']>=.05,
      'ignition_residual_positive':np.isfinite(ign) and ign>0,
      'ignition_minus_absorption_ge_0_20':np.isfinite(ign) and np.isfinite(abso) and ign-abso>=.20,
      'ignition_absorption_boot_ci_lower_gt_zero':np.isfinite(b1['ci_lo']) and b1['ci_lo']>0,
      'ignition_beats_lowvol_accept_ge_0_10':np.isfinite(ign) and np.isfinite(lowacc) and ign-lowacc>=.10,
      'oi_persist_post1h_residual_positive':np.isfinite(op) and op>0,
      'oi_persist_minus_flush_ge_0_30':np.isfinite(op) and np.isfinite(of) and op-of>=.30,
      'oi_boot_ci_lower_gt_zero':np.isfinite(b2['ci_lo']) and b2['ci_lo']>0,
      'stress_2022_short_ignition_positive_n20':n22s>=20 and np.isfinite(m22s) and m22s>0,
      'pooled_recent_ignition_positive_n40':nr>=40 and np.isfinite(mr) and mr>0,
      'both_2025h2_2026_ignition_positive':n25>0 and n26>0 and m25>0 and m26>0,
      'august_not_used_for_selection':True}
    gates={k:bool(v) for k,v in gates.items()}; core=all(gates[k] for k in ['high_volume_accept_rate_gap_ge_0_05','ignition_residual_positive','ignition_minus_absorption_ge_0_20','ignition_absorption_boot_ci_lower_gt_zero','oi_persist_post1h_residual_positive','oi_persist_minus_flush_ge_0_30','oi_boot_ci_lower_gt_zero'])
    score=sum(gates.values()); verdict='PASS_VOLUME_IGNITION_AND_OI_CONTINUATION_MECHANISM' if score>=14 and core else ('WATCH_VOLUME_OR_OI_MECHANISM_PARTIAL' if score>=10 else 'FAIL_NO_VOLUME_IGNITION_MECHANISM')
    meta['verdict']=verdict; meta.update(dict(ignition_residual=ign,absorption_residual=abso,lowvol_accept_residual=lowacc,oi_persist_residual=op,oi_flush_residual=of))
    report(meta,ss,ois,ws,diag,[b1,b2],gates)
    with open(OUT/'verdict.json','w') as f: json.dump({'meta':meta,'gates':gates},f,indent=2,default=py)
    print(json.dumps({'verdict':verdict,'score':score,'meta':meta},default=py))

if __name__=='__main__': main()
