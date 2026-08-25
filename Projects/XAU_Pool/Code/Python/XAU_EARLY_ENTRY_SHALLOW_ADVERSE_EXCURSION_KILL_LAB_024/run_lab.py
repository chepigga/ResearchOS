#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_EARLY_ENTRY_SHALLOW_ADVERSE_EXCURSION_KILL_LAB_024'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
PARENT_RUNNER_SHA='09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a'
HOLDOUT=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
RISK_ATR=0.50
COMMISSION_PRICE=0.05
HOLD_MIN=60
BOOT_N=4000
SEED=20260825
PRIMARY_DEPTH=0.10
DEPTHS=(0.05,0.10,0.15,0.20)

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load_module(path:Path):
    sp=importlib.util.spec_from_file_location('lab012_parent',path)
    m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def pf(v):
    s=pd.Series(v).dropna(); pos=s[s>0].sum(); neg=-s[s<0].sum()
    return float(pos/neg) if neg>0 else (float('inf') if pos>0 else np.nan)

def maxdd(v):
    a=np.asarray(pd.Series(v).dropna(),float)
    if not len(a): return np.nan
    c=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0,c]); return float((pk[1:]-c).max())

def max_consec(v):
    m=c=0
    for z in pd.Series(v).dropna():
        if z<0:c+=1;m=max(m,c)
        else:c=0
    return int(m)

def span_weeks(t):
    x=pd.to_datetime(pd.Series(t).dropna())
    if len(x)<2:return np.nan
    return max(1.0,(x.max()-x.min()).total_seconds()/(7*86400))

def sim_trade(r,df,target:float,depth:float,ctx):
    ei=int(r.baseline_entry_i); d=int(r.dir); a=float(r.atr0); entry=float(r.baseline_entry)
    if ei<0 or not np.isfinite(entry) or not np.isfinite(a) or a<=0:return None
    times,bh,bl,bc,bo,ah,al,ac,ao=ctx
    risk=RISK_ATR*a; tp=entry+d*target*risk; sl=entry-d*risk; kill=entry-d*depth*a
    end_time=times[ei]+HOLD_MIN
    last=ei; triggered=False; trigger_i=-1
    for j in range(ei,len(df)):
        if times[j]>end_time:break
        last=j
        if d>0:
            hs=bl[j]<=sl; hk=bl[j]<=kill; ht=bh[j]>=tp
            if bo[j]<=sl:
                gr=-1.0; reason='SL_GAP'; xi=j; break
            if bo[j]<=kill:
                exitp=bo[j]; gr=max(-1.0,d*(exitp-entry)/risk); reason='AE_KILL_GAP'; xi=j; triggered=True; trigger_i=j; break
        else:
            hs=ah[j]>=sl; hk=ah[j]>=kill; ht=al[j]<=tp
            if ao[j]>=sl:
                gr=-1.0; reason='SL_GAP'; xi=j; break
            if ao[j]>=kill:
                exitp=ao[j]; gr=max(-1.0,d*(exitp-entry)/risk); reason='AE_KILL_GAP'; xi=j; triggered=True; trigger_i=j; break
        if hs:
            gr=-1.0; reason='SL'; xi=j; break
        if hk:
            gr=d*(kill-entry)/risk; reason='AE_KILL'; xi=j; triggered=True; trigger_i=j; break
        if ht:
            gr=target; reason='TP'; xi=j; break
    else:
        xi=last; exitp=bc[last] if d>0 else ac[last]; gr=d*(exitp-entry)/risk; reason='TIME_STOP'; gr=max(-1.0,min(target,float(gr)))
    if 'reason' not in locals():
        xi=last; exitp=bc[last] if d>0 else ac[last]; gr=d*(exitp-entry)/risk; reason='TIME_STOP'; gr=max(-1.0,min(target,float(gr)))
    comm=COMMISSION_PRICE/risk; net=float(gr-comm); stress=float(net-0.10/risk)
    return {'gross_R':float(gr),'net_R':net,'stress10_R':stress,'exit_i':int(xi),'exit_time':df.at[int(xi),'time'],'outcome':reason,'triggered':bool(triggered),'trigger_i':int(trigger_i),'duration_min':float((df.at[int(xi),'time']-df.at[ei,'time']).total_seconds()/60)}

def add_branch(x,df,target,depth,ctx):
    y=x.copy(); tag=f'ae{int(round(depth*100)):03d}'; key=str(target).replace('.','p')
    out=[sim_trade(r,df,target,depth,ctx) for r in y.itertuples(index=False)]
    for f in ('gross_R','net_R','stress10_R','exit_i','exit_time','outcome','triggered','trigger_i','duration_min'):
        vals=[o[f] if o else (pd.NaT if f=='exit_time' else np.nan) for o in out]
        y[f'{tag}_{f}_{key}']=vals
    return y

def dedupe(x,parent):return parent.dedupe_serial_universe(x)

def build_serial(x,depth,target,parent):
    tag=f'ae{int(round(depth*100)):03d}'; key=str(target).replace('.','p'); ex=f'{tag}_exit_time_{key}'
    rows=[]; busy=pd.Timestamp.min
    for r in dedupe(x,parent).itertuples(index=False):
        if r.break_time<=busy:continue
        et=r.baseline_entry_time; xt=getattr(r,ex)
        if pd.notna(et) and pd.notna(xt):rows.append(r._asdict());busy=xt
        else:busy=r.lifecycle_end_time
    return pd.DataFrame(rows)

def stats(x,depth,target):
    if x is None or x.empty:return {'n':0}
    tag=f'ae{int(round(depth*100)):03d}'; key=str(target).replace('.','p'); col=f'{tag}_net_R_{key}'; gc=f'{tag}_gross_R_{key}'; sc=f'{tag}_stress10_R_{key}'; oc=f'{tag}_outcome_{key}'
    v=x[col].dropna(); z=x.loc[v.index]; daily=z.assign(day=pd.to_datetime(z.baseline_entry_time).dt.date).groupby('day')[col].sum()
    return {'n':int(len(v)),'trades_per_week':float(len(v)/span_weeks(z.baseline_entry_time)) if len(v)>1 else np.nan,'ev':float(v.mean()),'pf':pf(v),'positive_rate':float((v>0).mean()),'gross_ev':float(z[gc].mean()),'total_R':float(v.sum()),'tp_rate':float((z[oc]=='TP').mean()),'kill_rate':float(z[oc].isin(['AE_KILL','AE_KILL_GAP']).mean()),'max_dd_R':maxdd(v),'worst_day_R':float(daily.min()) if len(daily) else np.nan,'max_consec_losses':max_consec(v),'stress10_ev':float(z[sc].mean()),'buy_ev':float(z.loc[z.dir==1,col].mean()),'sell_ev':float(z.loc[z.dir==-1,col].mean()),'median_duration_min':float(z[f'{tag}_duration_min_{key}'].median())}

def boot_week_ev(x,depth,target,seed):
    tag=f'ae{int(round(depth*100)):03d}'; key=str(target).replace('.','p'); col=f'{tag}_net_R_{key}'; z=x.copy(); z['week']=pd.to_datetime(z.baseline_entry_time).dt.to_period('W-MON').astype(str); w=z.groupby('week')[col].mean().dropna().to_numpy(float)
    if len(w)<8:return {'n_weeks':len(w),'mean':float(w.mean()) if len(w) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(w,size=len(w),replace=True).mean() for _ in range(BOOT_N)])
    return {'n_weeks':int(len(w)),'mean':float(w.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}

def boot_paired(x,depth,target,seed):
    tag=f'ae{int(round(depth*100)):03d}'; key=str(target).replace('.','p'); mc=f'{tag}_net_R_{key}'; bc=f'baseline_net_R_{key}'
    z=x[[mc,bc,'baseline_entry_time']].dropna().copy(); z['diff']=z[mc]-z[bc]; z['week']=pd.to_datetime(z.baseline_entry_time).dt.to_period('W-MON').astype(str); w=z.groupby('week')['diff'].mean().to_numpy(float)
    if len(w)<8:return {'n':len(z),'mean':float(z['diff'].mean()) if len(z) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(w,size=len(w),replace=True).mean() for _ in range(BOOT_N)])
    return {'n':int(len(z)),'mean':float(z['diff'].mean()),'weekly_mean':float(w.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--canonical',type=Path,required=True); ap.add_argument('--break-census',type=Path,required=True); ap.add_argument('--parent-runner',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args()
    out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    if sha256(a.canonical)!=CANONICAL_SHA:raise RuntimeError('canonical SHA mismatch')
    if sha256(a.parent_runner)!=PARENT_RUNNER_SHA:raise RuntimeError('parent runner SHA mismatch')
    parent=load_module(a.parent_runner)
    df=parent.add_atr_vwap(parent.load_prices(a.canonical)); br=parent.load_breaks(a.break_census); ev=parent.score_bias(parent.build_bias_events(br,df)); strong=ev[ev.strong_accept].copy(); setups=parent.build_setups(strong,df)
    setups=parent.simulate_branch(setups,df,'BASELINE',1.5); setups=parent.simulate_branch(setups,df,'BASELINE',2.0)
    base=setups[(setups.digestion_found.astype(bool))&(setups.baseline_entry_i>=0)&(~setups.causality_violation.astype(bool))].copy()
    if (base.break_time>=HOLDOUT).any():raise RuntimeError('holdout opened')
    ctx=(df.time.to_numpy(dtype='datetime64[ns]'),df.high.to_numpy(float),df.low.to_numpy(float),df.close.to_numpy(float),df.open.to_numpy(float),df.ask_high.to_numpy(float),df.ask_low.to_numpy(float),df.ask_close.to_numpy(float),df.ask_open.to_numpy(float))
    z=base.copy()
    for depth in DEPTHS:
        for target in (1.5,2.0):z=add_branch(z,df,target,depth,ctx)
    rows=[]
    for split in ('DISCOVERY','CONFIRMATION'):
        xs=z[z.split==split].copy()
        for target in (1.5,2.0):
            bi=parent.stats(xs,'BASELINE',target); bs=parent.stats(parent.build_serial(xs,'BASELINE',target),'BASELINE',target)
            rows.append({'split':split,'strategy':'BASELINE','depth_atr':0.0,'target':target,'portfolio':'INDEPENDENT',**bi}); rows.append({'split':split,'strategy':'BASELINE','depth_atr':0.0,'target':target,'portfolio':'SERIAL',**bs})
            for depth in DEPTHS:
                rows.append({'split':split,'strategy':'AE_KILL','depth_atr':depth,'target':target,'portfolio':'INDEPENDENT',**stats(xs,depth,target)})
                rows.append({'split':split,'strategy':'AE_KILL','depth_atr':depth,'target':target,'portfolio':'SERIAL',**stats(build_serial(xs,depth,target,parent),depth,target)})
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    conf=z[z.split=='CONFIRMATION'].copy(); disc=z[z.split=='DISCOVERY'].copy(); d=PRIMARY_DEPTH
    cs=build_serial(conf,d,1.5,parent); cm=stats(cs,d,1.5); ci=stats(conf,d,1.5); di=stats(disc,d,1.5); c2=stats(build_serial(conf,d,2.0,parent),d,2.0); bb=parent.stats(parent.build_serial(conf,'BASELINE',1.5),'BASELINE',1.5)
    wk=boot_week_ev(cs,d,1.5,SEED); paired=boot_paired(conf,d,1.5,SEED+1)
    tag='ae010'; key='1p5'; tc=f'{tag}_triggered_{key}'; mc=f'{tag}_net_R_{key}'; bc='baseline_net_R_1p5'; bo='baseline_outcome_1p5'
    cohort=[]
    for flag,label in [(True,'TRIGGERED'),(False,'NOT_TRIGGERED')]:
        g=conf[conf[tc].astype(bool)==flag].copy(); cohort.append({'group':label,'n':len(g),'trigger_rate':len(g)/len(conf),'baseline_ev':float(g[bc].mean()),'baseline_tp_rate':float((g[bo]=='TP').mean()),'managed_ev':float(g[mc].mean()),'managed_minus_baseline':float((g[mc]-g[bc]).mean())})
    cohort=pd.DataFrame(cohort); cohort.to_csv(out/'trigger_cohort.csv',index=False)
    od=[]
    for oc,g in conf.groupby(bo):od.append({'baseline_outcome':oc,'n':len(g),'baseline_ev':float(g[bc].mean()),'managed_ev':float(g[mc].mean()),'managed_minus_baseline':float((g[mc]-g[bc]).mean()),'trigger_rate':float(g[tc].astype(bool).mean())})
    pd.DataFrame(od).to_csv(out/'baseline_outcome_balance.csv',index=False)
    fr=[]
    for depth in DEPTHS:
        s=stats(build_serial(conf,depth,1.5,parent),depth,1.5); pr=boot_paired(conf,depth,1.5,SEED+10+len(fr)); fr.append({'depth_atr':depth,**s,'paired_lift':pr.get('mean'),'paired_ci_low':pr['ci95'][0],'paired_ci_high':pr['ci95'][1]})
    pd.DataFrame(fr).to_csv(out/'depth_sensitivity.csv',index=False)
    trg=cohort[cohort.group=='TRIGGERED'].iloc[0]; ntr=cohort[cohort.group=='NOT_TRIGGERED'].iloc[0]
    violations=int(base.causality_violation.astype(bool).sum())
    gates={'G0_DATA_CAUSALITY':bool(violations==0 and (base.break_time<HOLDOUT).all()),'G1_POWER':bool(cm.get('n',0)>=500 and cm.get('trades_per_week',0)>=5),'G2_CONFIRMATION_EV':bool(cm.get('ev',-9)>0 and cm.get('pf',0)>1),'G3_WEEK_CLUSTER_CI':bool(wk['ci95'][0] is not None and wk['ci95'][0]>0),'G4_MANAGEMENT_LIFT':bool(paired.get('mean',-9)>0 and paired['ci95'][0] is not None and paired['ci95'][0]>0),'G5_SPLIT_TRANSFER':bool(ci.get('ev',-9)>0 and di.get('ev',-9)>0),'G6_DIRECTION_BREADTH':bool(cm.get('buy_ev',-9)>0 and cm.get('sell_ev',-9)>0),'G7_2R_SURVIVAL':bool(c2.get('ev',-9)>=0),'G8_COST_STRESS':bool(cm.get('stress10_ev',-9)>0),'G9_PROP_DD_PROXY':bool(cm.get('max_dd_R',999)<=20 and cm.get('worst_day_R',-999)>-16),'G10_TRIGGERED_COHORT_SAVING':bool(float(trg.managed_minus_baseline)>=0.20),'G11_NON_TRIGGERED_RETENTION':bool(float(ntr.baseline_ev)>0 and float(ntr.managed_ev)>0 and abs(float(ntr.managed_minus_baseline))<0.05)}
    if not gates['G0_DATA_CAUSALITY']:verdict='INVALID_DATA_CAUSALITY'
    elif all(gates.values()):verdict='SHALLOW_ADVERSE_EXCURSION_KILL_EDGE'
    elif gates['G2_CONFIRMATION_EV'] and gates['G4_MANAGEMENT_LIFT'] and (not gates['G3_WEEK_CLUSTER_CI'] or not gates['G5_SPLIT_TRANSFER']):verdict='SHALLOW_KILL_POSITIVE_BUT_NOT_ROBUST'
    elif gates['G4_MANAGEMENT_LIFT'] and cm.get('ev',-9)<=0:verdict='SHALLOW_KILL_IMPROVES_BUT_NOT_POSITIVE'
    elif gates['G10_TRIGGERED_COHORT_SAVING'] and not gates['G11_NON_TRIGGERED_RETENTION']:verdict='SHALLOW_KILL_SAVES_LOSERS_BUT_DESTROYS_WINNERS'
    else:verdict='NO_SHALLOW_ADVERSE_EXCURSION_KILL_EDGE'
    vo={'status':verdict,'gates':gates,'primary_depth_atr':PRIMARY_DEPTH,'primary_confirmation_serial':cm,'primary_confirmation_independent':ci,'primary_discovery_independent':di,'confirmation_2R_serial':c2,'baseline_confirmation_serial':bb,'weekly_ev_bootstrap':wk,'paired_management_minus_baseline':paired,'trigger_cohort':cohort.to_dict(orient='records'),'causality_violations':violations,'holdout_opened':False}
    (out/'verdict.json').write_text(json.dumps(vo,indent=2),encoding='utf-8')
    audit={'canonical_sha':sha256(a.canonical),'parent_runner_sha':sha256(a.parent_runner),'raw_rows':len(df),'break_events':len(br),'strong_bias_events':len(strong),'early_entry_events':len(base),'max_price_time_read':str(df.time.max()),'max_event_break_time':str(base.break_time.max()),'holdout_opened':False,'causality_violations':violations}
    (out/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    report=f'''# {LAB} — {VERSION} REPORT\n\n**Verdict:** `{verdict}`  \n**Holdout opened:** `false`\n\n## Primary Confirmation — 0.10 ATR adverse-excursion kill / 1.5R / serial\n- N **{cm.get('n')}**, trades/week **{cm.get('trades_per_week'):.2f}**\n- EV **{cm.get('ev'):+.4f}R**, PF **{cm.get('pf'):.3f}**, TP **{cm.get('tp_rate'):.2%}**\n- kill rate **{cm.get('kill_rate'):.2%}**\n- BUY **{cm.get('buy_ev'):+.4f}R**, SELL **{cm.get('sell_ev'):+.4f}R**\n- max DD **{cm.get('max_dd_R'):.2f}R**, worst day **{cm.get('worst_day_R'):.2f}R**\n- stress10 **{cm.get('stress10_ev'):+.4f}R**\n- weekly EV CI **{wk['ci95']}**\n\n## Baseline / paired lift\n- frozen baseline serial EV **{bb.get('ev'):+.4f}R**, PF **{bb.get('pf'):.3f}**\n- paired manager-minus-baseline **{paired.get('mean'):+.4f}R**, weekly CI **{paired['ci95']}**\n- Discovery independent EV **{di.get('ev'):+.4f}R**\n- Confirmation independent EV **{ci.get('ev'):+.4f}R**\n- Confirmation 2R serial EV **{c2.get('ev'):+.4f}R**, PF **{c2.get('pf'):.3f}**\n\n## Trigger cohort\n- TRIGGERED: N **{int(trg.n)}**, baseline EV **{trg.baseline_ev:+.4f}R**, baseline TP **{trg.baseline_tp_rate:.2%}**, managed EV **{trg.managed_ev:+.4f}R**, delta **{trg.managed_minus_baseline:+.4f}R**\n- NOT_TRIGGERED: N **{int(ntr.n)}**, baseline EV **{ntr.baseline_ev:+.4f}R**, baseline TP **{ntr.baseline_tp_rate:.2%}**, managed EV **{ntr.managed_ev:+.4f}R**, delta **{ntr.managed_minus_baseline:+.4f}R**\n\n## Frozen gates\n'''+''.join([f'- {k}: **{"PASS" if v else "FAIL"}**\n' for k,v in gates.items()])+'''\nNo threshold rescue, holdout opening, EA authorization or live allocation is authorized by LAB024.\n'''
    (out/'REPORT.md').write_text(report,encoding='utf-8')
    print(json.dumps({'verdict':verdict,'primary':cm,'baseline':bb,'paired':paired,'triggered':trg.to_dict(),'not_triggered':ntr.to_dict(),'gates':gates},indent=2))
if __name__=='__main__':main()
