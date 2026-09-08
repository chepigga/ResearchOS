#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_RETAIL_FLOW_REACCEPTANCE_POST_RECOVERY_PERSISTENCE_AND_SECOND_FAILURE_LAB_031'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC=LABS/'BTC_RETAIL_FLOW_ACCEPTANCE_ORIGIN_CLOSE2_FAILURE_RECOVERY_AND_REACCEPTANCE_LAB_030'/'output'/'failure_recovery_stream.csv'
SRC23=LABS/'BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab023',SRC23)
L23=importlib.util.module_from_spec(spec); spec.loader.exec_module(L23)
UTC='UTC'; PRE=pd.Timestamp('2026-08-01',tz=UTC)
SEED=20260908; BOOT_N=5000
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),
 '2023':('2023-01-01','2024-01-01'),'2024':('2024-01-01','2025-01-01'),
 '2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'AUG2026_REUSED_AUDIT':('2026-08-01','2026-09-01'),
 'HIST':('2021-01-01','2025-07-01'),'RECENT':('2025-07-01','2026-08-01'),
 'ALL_PRE_AUG':('2021-01-01','2026-08-01')}

def tstat(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if len(a)<2:return np.nan
    s=a.std(ddof=1); return float(a.mean()/(s/math.sqrt(len(a)))) if s>0 else np.nan

def pf(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    p=float(a[a>0].sum()); n=float(-a[a<0].sum())
    if n==0:return np.inf if p>0 else np.nan
    return p/n

def load_lineage():
    d=pd.read_csv(SRC)
    for c in ['signal_time','failure_time','full_reaccept_time']:
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    for c in ['side','signal_close','entry','atr14','reaccept_residual_atr']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d['full_reaccept']=d.full_reaccept.astype(str).str.lower().isin(['true','1','yes'])
    return d.sort_values('signal_time').reset_index(drop=True)

def path_excursion(path,side,base,atr):
    mae=mfe=0.0
    for _,z in path.iterrows():
        adv=(base-float(z.low)) if side>0 else (float(z.high)-base)
        fav=(float(z.high)-base) if side>0 else (base-float(z.low))
        mae=max(mae,max(0.0,adv)/atr); mfe=max(mfe,max(0.0,fav)/atr)
    return float(mae),float(mfe)

def simulate(price,d):
    pos=pd.Series(np.arange(len(price),dtype=int),index=price.index)
    rows=[]
    for r in d.itertuples():
        if not bool(r.full_reaccept) or pd.isna(r.full_reaccept_time):continue
        sig_t=pd.Timestamp(r.signal_time); rt=pd.Timestamp(r.full_reaccept_time); end=sig_t+pd.Timedelta(hours=12)
        if rt not in pos.index or end not in pos.index or rt>=end:continue
        side=int(r.side); origin=float(r.signal_close); entry=float(r.entry); atr=float(r.atr14)
        i=int(pos.loc[rt])+1
        if i>=len(price):continue
        post=price.iloc[i:]
        post=post[post.index<=end]
        if post.empty:continue
        first_times=list(post.index[:2])
        persist=False; persist_t=pd.NaT; persist_px=np.nan
        if len(first_times)>=2:
            z1=price.loc[first_times[0]]; z2=price.loc[first_times[1]]
            if side*(float(z1.close)-entry)>0 and side*(float(z2.close)-entry)>0:
                persist=True; persist_t=first_times[1]; persist_px=float(z2.close)
        # SECOND_FAIL: two consecutive closes through origin, only if PERSIST2 was not achieved.
        sf=False; sf_t=pd.NaT; sf_px=np.nan
        if not persist:
            consec=0
            for t,z in post.iterrows():
                bad=side*(float(z.close)-origin)<=0
                consec=consec+1 if bad else 0
                if consec>=2:
                    sf=True; sf_t=t; sf_px=float(z.close); break
        state='PERSIST2' if persist else ('SECOND_FAIL' if sf else 'UNRESOLVED')
        ct=persist_t if persist else (sf_t if sf else first_times[0])
        cp=persist_px if persist else (sf_px if sf else float(price.loc[first_times[0],'close']))
        end_close=float(price.loc[end,'close'])
        residual=float(side*(end_close-cp)/atr)
        rem=price.loc[(price.index>=ct)&(price.index<=end)]
        mae,mfe=path_excursion(rem,side,cp,atr)
        # Secondary fixed audit: +0.5 ATR further from frozen acceptance level vs second fail through origin.
        plus_lvl=entry+side*.5*atr; plus_t=pd.NaT
        sf2_t=pd.NaT; consec=0
        for t,z in post.iterrows():
            hit_plus=(float(z.high)>=plus_lvl) if side>0 else (float(z.low)<=plus_lvl)
            bad=side*(float(z.close)-origin)<=0
            if pd.isna(plus_t) and hit_plus: plus_t=t
            consec=consec+1 if bad else 0
            if pd.isna(sf2_t) and consec>=2: sf2_t=t
            if pd.notna(plus_t) and pd.notna(sf2_t):break
        if pd.notna(plus_t) and pd.notna(sf2_t) and plus_t==sf2_t: audit='AMBIGUOUS'
        elif pd.notna(plus_t) and (pd.isna(sf2_t) or plus_t<sf2_t): audit='PLUS05_FIRST'
        elif pd.notna(sf2_t): audit='SECOND_FAIL_FIRST'
        else:audit='NONE'
        rows.append(dict(flow_id=int(r.flow_id),signal_time=sig_t,side=side,origin=origin,entry=entry,atr14=atr,
          reaccept_time=rt,state=state,class_time=ct,class_close=cp,residual_atr=residual,
          class_delay_h=float((ct-rt).total_seconds()/3600),post_class_mae_atr=mae,post_class_mfe_atr=mfe,
          audit_first_passage=audit,plus05_time=plus_t,second_fail_time=sf2_t))
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)

def metrics(q,label):
    p=q[q.state=='PERSIST2']; s=q[q.state=='SECOND_FAIL']; u=q[q.state=='UNRESOLVED']
    return dict(sample=label,n=len(q),persist_n=len(p),persist_rate=len(p)/len(q) if len(q) else np.nan,
      persist_resid=float(p.residual_atr.mean()) if len(p) else np.nan,persist_t=tstat(p.residual_atr) if len(p) else np.nan,
      persist_pf=pf(p.residual_atr) if len(p) else np.nan,persist_win=float((p.residual_atr>0).mean()) if len(p) else np.nan,
      second_n=len(s),second_resid=float(s.residual_atr.mean()) if len(s) else np.nan,second_pf=pf(s.residual_atr) if len(s) else np.nan,
      unresolved_n=len(u),unresolved_resid=float(u.residual_atr.mean()) if len(u) else np.nan,
      gap=float(p.residual_atr.mean()-s.residual_atr.mean()) if len(p) and len(s) else np.nan,
      median_persist_h=float(p.class_delay_h.median()) if len(p) else np.nan,
      persist_mae=float(p.post_class_mae_atr.median()) if len(p) else np.nan,persist_mfe=float(p.post_class_mfe_atr.median()) if len(p) else np.nan,
      plus05_first=int((q.audit_first_passage=='PLUS05_FIRST').sum()),second_first=int((q.audit_first_passage=='SECOND_FAIL_FIRST').sum()))

def bootstrap(d):
    q=d[(d.signal_time<PRE)&(d.state.isin(['PERSIST2','SECOND_FAIL']))].copy()
    epoch=pd.Timestamp('1970-01-01',tz=UTC); q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    rows=[]
    for _,z in q.groupby('cluster'):
        a=z.loc[z.state=='PERSIST2','residual_atr'].dropna().to_numpy(float)
        b=z.loc[z.state=='SECOND_FAIL','residual_atr'].dropna().to_numpy(float)
        rows.append((a.sum(),len(a),b.sum(),len(b)))
    arr=np.asarray(rows,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[1]>0 and s[3]>0: vals.append(float(s[0]/s[1]-s[2]/s[3]))
    vals=np.asarray(vals,float)
    p=q[q.state=='PERSIST2'].residual_atr; f=q[q.state=='SECOND_FAIL'].residual_atr
    return dict(n_clusters=m,draws=len(vals),point=float(p.mean()-f.mean()),ci_lo=float(np.quantile(vals,.025)),ci_hi=float(np.quantile(vals,.975)))

def report(tab,side,boot,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
      '## Frozen lineage',f"- FULL_REACCEPT total: **{meta['lineage_total']}**, pre-Aug: **{meta['lineage_pre']}**",'',
      '## Post-reaccept states by window','',
      '| Window | N | Persist2 | Rate | Persist residual | PF | Win | Second fail | Second residual | Gap | Unresolved |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in tab.iterrows():lines.append(f"| {r['sample']} | {int(r.n)} | {int(r.persist_n)} | {f(r.persist_rate)} | {f(r.persist_resid)} | {f(r.persist_pf)} | {f(r.persist_win)} | {int(r.second_n)} | {f(r.second_resid)} | {f(r.gap)} | {int(r.unresolved_n)} |")
    lines += ['', '## By side pre-Aug','', '| Side | N | Persist2 | Persist residual | Second residual | Gap | PF | Win |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in side.iterrows():lines.append(f"| {r['sample']} | {int(r.n)} | {int(r.persist_n)} | {f(r.persist_resid)} | {f(r.second_resid)} | {f(r.gap)} | {f(r.persist_pf)} | {f(r.persist_win)} |")
    lines += ['', '## 7d cluster bootstrap',f"- clusters: **{boot['n_clusters']}**, draws: **{boot['draws']}**",f"- PERSIST2 minus SECOND_FAIL residual: **{f(boot['point'])} ATR**, 95% CI **[{f(boot['ci_lo'])}, {f(boot['ci_hi'])}]**",'',
      '## Primary anatomy',f"- pre-Aug median reaccept→PERSIST2 classification: **{f(meta['median_persist_h'])} h**",f"- PERSIST2 median post-class MAE/MFE: **{f(meta['persist_mae'])} / {f(meta['persist_mfe'])} ATR**",'',
      '## Secondary first-passage audit',f"- +0.5 ATR first: **{meta['plus05_first']}**",f"- SECOND_FAIL first: **{meta['second_first']}**",'', '## Gates']
    for k,v in gates.items():lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## Guardrail','PERSIST2 uses only the first two completed M15 closes after FULL_REACCEPT. No later qualifying pair can rescue it. No threshold/horizon/side optimization. August 2026 reused audit only. Live allocation = **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price=L23.load_price(); lin=load_lineage(); full=lin[lin.full_reaccept].copy(); d=simulate(price,full); d.to_csv(OUT/'post_reaccept_state_stream.csv',index=False)
    tabs=[]
    for name,(a,b) in WINS.items():
        q=d[(d.signal_time>=pd.Timestamp(a,tz=UTC))&(d.signal_time<pd.Timestamp(b,tz=UTC))]; tabs.append(metrics(q,name))
    tab=pd.DataFrame(tabs); tab.to_csv(OUT/'state_by_window.csv',index=False)
    pre=d[d.signal_time<PRE]; sides=[]
    for s,name in [(1,'LONG'),(-1,'SHORT')]: sides.append(metrics(pre[pre.side==s],name))
    side=pd.DataFrame(sides); side.to_csv(OUT/'state_by_side.csv',index=False)
    boot=bootstrap(d); (OUT/'bootstrap_7d.json').write_text(json.dumps(boot,indent=2),encoding='utf-8')
    get=lambda n: tab[tab['sample']==n].iloc[0]
    allm=get('ALL_PRE_AUG'); rec=get('RECENT'); h25=get('2025_H2'); y26=get('2026_JAN_JUL')
    y22s=metrics(d[(d.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(d.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(d.side==-1)],'2022_SHORT')
    lm=side[side['sample']=='LONG'].iloc[0]; sm=side[side['sample']=='SHORT'].iloc[0]
    lineage_pre=int(((full.signal_time<PRE)).sum())
    gates={
      'exact_lab030_full_reaccept_lineage_ge_690':lineage_pre>=690,
      'persist2_n_ge_150':allm.persist_n>=150,
      'second_fail_n_ge_80':allm.second_n>=80,
      'persist2_residual_positive':bool(allm.persist_resid>0),
      'second_fail_residual_lt_persist2':bool(allm.second_resid<allm.persist_resid),
      'residual_gap_ge_0_50atr':bool(allm.gap>=.50),
      'bootstrap_ci_lower_gt_zero':bool(boot['ci_lo']>0),
      'recent_persist2_n_ge_30':rec.persist_n>=30,
      'recent_persist2_residual_positive':bool(rec.persist_resid>0),
      'recent_persist_gt_second_fail':bool(rec.persist_resid>rec.second_resid),
      '2025h2_and_2026_persist_positive':bool(h25.persist_resid>0 and y26.persist_resid>0),
      '2022_short_persist_n15_residual_positive':bool(y22s['persist_n']>=15 and y22s['persist_resid']>0),
      'long_and_short_persist_positive':bool(lm.persist_resid>0 and sm.persist_resid>0),
      'persist_win_rate_gt_55pct':bool(allm.persist_win>.55),
    }
    critical=['exact_lab030_full_reaccept_lineage_ge_690','persist2_residual_positive','bootstrap_ci_lower_gt_zero','recent_persist2_n_ge_30','recent_persist2_residual_positive','recent_persist_gt_second_fail']
    score=sum(gates.values())
    if score>=11 and all(gates[k] for k in critical):verdict='PASS_POST_REACCEPT_PERSISTENCE_DISCRIMINATOR'
    elif allm.gap>0 and rec.persist_n>=30:verdict='WATCH_PERSISTENCE_DISCRIMINATIVE_TRANSFER_INCOMPLETE'
    else:verdict='FAIL_NO_POST_REACCEPT_PERSISTENCE_EDGE'
    meta=dict(verdict=verdict,lineage_total=len(full),lineage_pre=lineage_pre,median_persist_h=float(pre.loc[pre.state=='PERSIST2','class_delay_h'].median()) if (pre.state=='PERSIST2').any() else np.nan,
      persist_mae=float(pre.loc[pre.state=='PERSIST2','post_class_mae_atr'].median()) if (pre.state=='PERSIST2').any() else np.nan,
      persist_mfe=float(pre.loc[pre.state=='PERSIST2','post_class_mfe_atr'].median()) if (pre.state=='PERSIST2').any() else np.nan,
      plus05_first=int((pre.audit_first_passage=='PLUS05_FIRST').sum()),second_first=int((pre.audit_first_passage=='SECOND_FAIL_FIRST').sum()),y22_short=y22s)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'bootstrap':boot,'gates':gates},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(tab,side,boot,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__':main()
