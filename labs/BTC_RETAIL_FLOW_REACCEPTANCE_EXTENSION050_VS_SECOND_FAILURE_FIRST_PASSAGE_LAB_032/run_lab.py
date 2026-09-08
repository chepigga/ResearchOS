#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_REACCEPTANCE_EXTENSION050_VS_SECOND_FAILURE_FIRST_PASSAGE_LAB_032'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC=LABS/'BTC_RETAIL_FLOW_ACCEPTANCE_ORIGIN_CLOSE2_FAILURE_RECOVERY_AND_REACCEPTANCE_LAB_030'/'output'/'failure_recovery_stream.csv'
SRC23=LABS/'BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab023',SRC23); L23=importlib.util.module_from_spec(spec); spec.loader.exec_module(L23)
UTC='UTC'; PRE=pd.Timestamp('2026-08-01',tz=UTC); SEED=20260908; BOOT_N=5000
WINS={
'2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),'2024':('2024-01-01','2025-01-01'),
'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),'2026_JAN_JUL':('2026-01-01','2026-08-01'),
'AUG2026_REUSED_AUDIT':('2026-08-01','2026-09-01'),'HIST':('2021-01-01','2025-07-01'),'RECENT':('2025-07-01','2026-08-01'),'ALL_PRE_AUG':('2021-01-01','2026-08-01')}

def tstat(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if len(a)<2:return np.nan
    s=a.std(ddof=1); return float(a.mean()/(s/math.sqrt(len(a)))) if s>0 else np.nan

def pf(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]; p=float(a[a>0].sum()); n=float(-a[a<0].sum())
    if n==0:return np.inf if p>0 else np.nan
    return p/n

def load_lineage():
    d=pd.read_csv(SRC)
    for c in ['signal_time','failure_time','full_reaccept_time']: d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','signal_close','entry','atr14']: d[c]=pd.to_numeric(d[c],errors='coerce')
    d['full_reaccept']=d.full_reaccept.astype(str).str.lower().isin(['true','1','yes'])
    return d[d.full_reaccept].sort_values('signal_time').reset_index(drop=True)

def excursion(price, start_t, end_t, side, base, atr):
    p=price.loc[(price.index>start_t)&(price.index<=end_t)]
    if p.empty:return 0.0,0.0
    mae=mfe=0.0
    for _,z in p.iterrows():
        adv=(base-float(z.low)) if side>0 else (float(z.high)-base)
        fav=(float(z.high)-base) if side>0 else (base-float(z.low))
        mae=max(mae,max(0.0,adv)/atr); mfe=max(mfe,max(0.0,fav)/atr)
    return float(mae),float(mfe)

def simulate(price,d):
    pos=pd.Series(np.arange(len(price),dtype=int),index=price.index); rows=[]
    for r in d.itertuples():
        sig_t=pd.Timestamp(r.signal_time); rt=pd.Timestamp(r.full_reaccept_time); end=sig_t+pd.Timedelta(hours=12)
        side=int(r.side); origin=float(r.signal_close); entry=float(r.entry); atr=float(r.atr14); ext=entry+side*.5*atr
        base=dict(flow_id=int(r.flow_id),signal_time=sig_t,side=side,origin=origin,entry=entry,extension050=ext,atr14=atr,reaccept_time=rt)
        if rt not in pos.index or end not in pos.index or rt>=end or not np.isfinite(atr) or atr<=0:
            rows.append({**base,'state':'NONE','class_time':end,'class_price':np.nan,'residual_atr':np.nan,'class_delay_h':max(0.0,(end-rt).total_seconds()/3600),'post_class_mae_atr':0.0,'post_class_mfe_atr':0.0}); continue
        i=int(pos.loc[rt])+1; post=price.iloc[i:]; post=post[post.index<=end]
        if post.empty:
            rows.append({**base,'state':'NONE','class_time':end,'class_price':np.nan,'residual_atr':np.nan,'class_delay_h':(end-rt).total_seconds()/3600,'post_class_mae_atr':0.0,'post_class_mfe_atr':0.0}); continue
        consec=0; state='NONE'; ct=end; cp=np.nan
        for t,z in post.iterrows():
            ext_hit=(float(z.high)>=ext) if side>0 else (float(z.low)<=ext)
            bad=side*(float(z.close)-origin)<=0; consec=consec+1 if bad else 0; sf_hit=consec>=2
            if ext_hit and sf_hit: state='AMBIGUOUS'; ct=t; cp=np.nan; break
            if ext_hit: state='EXTENSION050_FIRST'; ct=t; cp=ext; break
            if sf_hit: state='SECOND_FAIL_FIRST'; ct=t; cp=float(z.close); break
        end_close=float(price.loc[end,'close'])
        residual=float(side*(end_close-cp)/atr) if np.isfinite(cp) else np.nan
        mae,mfe=excursion(price,ct,end,side,cp,atr) if np.isfinite(cp) else (0.0,0.0)
        rows.append({**base,'state':state,'class_time':ct,'class_price':cp,'residual_atr':residual,'class_delay_h':float((ct-rt).total_seconds()/3600),'post_class_mae_atr':mae,'post_class_mfe_atr':mfe})
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)

def metrics(q,label):
    e=q[q.state=='EXTENSION050_FIRST']; s=q[q.state=='SECOND_FAIL_FIRST']; a=q[q.state=='AMBIGUOUS']; n=q[q.state=='NONE']; classified=len(e)+len(s)+len(a)
    return dict(sample=label,n=len(q),ext_n=len(e),ext_rate=len(e)/len(q) if len(q) else np.nan,ext_resid=float(e.residual_atr.mean()) if len(e) else np.nan,
      ext_t=tstat(e.residual_atr) if len(e) else np.nan,ext_pf=pf(e.residual_atr) if len(e) else np.nan,ext_win=float((e.residual_atr>0).mean()) if len(e) else np.nan,
      second_n=len(s),second_resid=float(s.residual_atr.mean()) if len(s) else np.nan,second_pf=pf(s.residual_atr) if len(s) else np.nan,
      gap=float(e.residual_atr.mean()-s.residual_atr.mean()) if len(e) and len(s) else np.nan,ambiguous_n=len(a),ambiguous_rate=len(a)/classified if classified else 0.0,
      none_n=len(n),median_ext_h=float(e.class_delay_h.median()) if len(e) else np.nan,ext_mae=float(e.post_class_mae_atr.median()) if len(e) else np.nan,ext_mfe=float(e.post_class_mfe_atr.median()) if len(e) else np.nan)

def bootstrap(d):
    q=d[(d.signal_time<PRE)&d.state.isin(['EXTENSION050_FIRST','SECOND_FAIL_FIRST'])].copy(); epoch=pd.Timestamp('1970-01-01',tz=UTC)
    q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64'); rows=[]
    for _,z in q.groupby('cluster'):
        a=z.loc[z.state=='EXTENSION050_FIRST','residual_atr'].dropna().to_numpy(float); b=z.loc[z.state=='SECOND_FAIL_FIRST','residual_atr'].dropna().to_numpy(float)
        rows.append((a.sum(),len(a),b.sum(),len(b)))
    arr=np.asarray(rows,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0: vals.append(float(s[0]/s[1]-s[2]/s[3]))
    vals=np.asarray(vals,float); e=q[q.state=='EXTENSION050_FIRST'].residual_atr; f=q[q.state=='SECOND_FAIL_FIRST'].residual_atr
    return dict(n_clusters=m,draws=len(vals),point=float(e.mean()-f.mean()),ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)))

def report(tab,side,boot,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    L=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',f"- FULL_REACCEPT total: **{meta['lineage_total']}**, pre-Aug: **{meta['lineage_pre']}**",'',
       '## First-passage states by window','', '| Window | N | Ext050 first | Ext residual | PF | Win | Second fail first | Second residual | Gap | Ambig | None |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in tab.iterrows():L.append(f"| {r['sample']} | {int(r.n)} | {int(r.ext_n)} | {f(r.ext_resid)} | {f(r.ext_pf)} | {f(r.ext_win)} | {int(r.second_n)} | {f(r.second_resid)} | {f(r.gap)} | {int(r.ambiguous_n)} | {int(r.none_n)} |")
    L+=['','## By side pre-Aug','','| Side | N | Ext050 first | Ext residual | Second residual | Gap | PF | Win |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in side.iterrows():L.append(f"| {r['sample']} | {int(r.n)} | {int(r.ext_n)} | {f(r.ext_resid)} | {f(r.second_resid)} | {f(r.gap)} | {f(r.ext_pf)} | {f(r.ext_win)} |")
    L+=['','## 7d cluster bootstrap',f"- clusters: **{boot['n_clusters']}**, draws: **{boot['draws']}**",f"- EXTENSION050_FIRST minus SECOND_FAIL_FIRST residual: **{f(boot['point'])} ATR**, 95% CI **[{f(boot['ci_lo'])}, {f(boot['ci_hi'])}]**",'',
        '## Anatomy',f"- median reaccept→extension classification: **{f(meta['median_ext_h'])} h**",f"- EXTENSION050 post-class median MAE/MFE: **{f(meta['ext_mae'])} / {f(meta['ext_mfe'])} ATR**",'', '## Gates']
    for k,v in gates.items():L.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    L+=['','## Guardrail','Extension threshold is frozen at exactly +0.5 ATR beyond the acceptance entry. Same-bar extension/second-failure is AMBIGUOUS and excluded. No threshold/horizon/side rescue. August 2026 reused audit only. Live allocation = **0**.']
    return '\n'.join(L)+'\n'

def main():
    price=L23.load_price(); lin=load_lineage(); d=simulate(price,lin); d.to_csv(OUT/'extension_vs_second_failure_stream.csv',index=False)
    tabs=[]
    for name,(a,b) in WINS.items():
        q=d[(d.signal_time>=pd.Timestamp(a,tz=UTC))&(d.signal_time<pd.Timestamp(b,tz=UTC))]; tabs.append(metrics(q,name))
    tab=pd.DataFrame(tabs); tab.to_csv(OUT/'state_by_window.csv',index=False); pre=d[d.signal_time<PRE]
    sides=[]
    for s,name in [(1,'LONG'),(-1,'SHORT')]:sides.append(metrics(pre[pre.side==s],name))
    side=pd.DataFrame(sides); side.to_csv(OUT/'state_by_side.csv',index=False); boot=bootstrap(d); (OUT/'bootstrap_7d.json').write_text(json.dumps(boot,indent=2),encoding='utf-8')
    get=lambda n:tab[tab['sample']==n].iloc[0]; allm=get('ALL_PRE_AUG'); rec=get('RECENT'); h25=get('2025_H2'); y26=get('2026_JAN_JUL')
    y22s=metrics(d[(d.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(d.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(d.side==-1)],'2022_SHORT')
    lm=side[side['sample']=='LONG'].iloc[0]; sm=side[side['sample']=='SHORT'].iloc[0]; lineage_pre=int((lin.signal_time<PRE).sum())
    gates={
      'exact_lab030_full_reaccept_lineage_ge_690':lineage_pre>=690,
      'extension050_n_ge_200':allm.ext_n>=200,
      'second_fail_n_ge_50':allm.second_n>=50,
      'ambiguous_rate_le_10pct':bool(allm.ambiguous_rate<=.10),
      'extension050_residual_positive':bool(allm.ext_resid>0),
      'second_fail_residual_lt_extension':bool(allm.second_resid<allm.ext_resid),
      'residual_gap_ge_0_50atr':bool(allm.gap>=.50),
      'bootstrap_ci_lower_gt_zero':bool(boot['ci_lo']>0),
      'recent_extension_n_ge_40':rec.ext_n>=40,
      'recent_extension_residual_positive':bool(rec.ext_resid>0),
      '2025h2_and_2026_extension_positive':bool(h25.ext_resid>0 and y26.ext_resid>0),
      '2022_short_extension_n15_residual_positive':bool(y22s['ext_n']>=15 and y22s['ext_resid']>0),
      'long_and_short_extension_positive':bool(lm.ext_resid>0 and sm.ext_resid>0),
      'extension_win_rate_gt_55pct':bool(allm.ext_win>.55),
    }
    critical=['exact_lab030_full_reaccept_lineage_ge_690','extension050_residual_positive','bootstrap_ci_lower_gt_zero','recent_extension_n_ge_40','recent_extension_residual_positive','2025h2_and_2026_extension_positive']
    score=sum(gates.values())
    if score>=11 and all(gates[k] for k in critical):verdict='PASS_REACCEPT_EXTENSION050_FIRST_PASSAGE_DISCRIMINATOR'
    elif allm.ext_resid>0 and rec.ext_n>=40:verdict='WATCH_EXTENSION050_POSITIVE_TRANSFER_INCOMPLETE'
    else:verdict='FAIL_NO_REACCEPT_EXTENSION_FIRST_PASSAGE_EDGE'
    meta=dict(verdict=verdict,lineage_total=len(lin),lineage_pre=lineage_pre,median_ext_h=float(pre.loc[pre.state=='EXTENSION050_FIRST','class_delay_h'].median()) if (pre.state=='EXTENSION050_FIRST').any() else np.nan,ext_mae=float(pre.loc[pre.state=='EXTENSION050_FIRST','post_class_mae_atr'].median()) if (pre.state=='EXTENSION050_FIRST').any() else np.nan,ext_mfe=float(pre.loc[pre.state=='EXTENSION050_FIRST','post_class_mfe_atr'].median()) if (pre.state=='EXTENSION050_FIRST').any() else np.nan,y22_short=y22s)
    def conv(o):
        if isinstance(o,(np.bool_,)):return bool(o)
        if isinstance(o,(np.integer,)):return int(o)
        if isinstance(o,(np.floating,)):return float(o)
        raise TypeError
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'bootstrap':boot,'gates':gates},indent=2,allow_nan=True,default=conv),encoding='utf-8')
    rep=report(tab,side,boot,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__': main()
