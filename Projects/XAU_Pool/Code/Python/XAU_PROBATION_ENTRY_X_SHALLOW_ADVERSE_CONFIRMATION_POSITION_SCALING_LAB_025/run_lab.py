#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_PROBATION_ENTRY_X_SHALLOW_ADVERSE_CONFIRMATION_POSITION_SCALING_LAB_025'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
PARENT_SHA='09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a'
HOLDOUT=pd.Timestamp('2025-07-01'); DISC_END=pd.Timestamp('2024-01-01')
RISK_ATR=0.50; COMMISSION_PRICE=0.05; HOLD_MIN=60; BOOT_N=4000; SEED=20260825
PRIMARY_F=0.25; PRIMARY_PROB=5; ADVERSE_DEPTH=0.10


def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def load_module(path:Path):
    sp=importlib.util.spec_from_file_location('lab012_parent',path); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
def pf(v):
    s=pd.Series(v).dropna(); pos=s[s>0].sum(); neg=-s[s<0].sum(); return float(pos/neg) if neg>0 else (float('inf') if pos>0 else np.nan)
def maxdd(v):
    a=np.asarray(pd.Series(v).dropna(),float)
    if not len(a): return np.nan
    c=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0,c]); return float((pk[1:]-c).max())
def max_consec(v):
    m=c=0
    for x in pd.Series(v).dropna():
        if x<0: c+=1; m=max(m,c)
        else: c=0
    return int(m)
def span_weeks(t):
    x=pd.to_datetime(pd.Series(t).dropna())
    if len(x)<2:return np.nan
    return max(1.0,(x.max()-x.min()).total_seconds()/(7*86400))
def dedupe(x,parent): return parent.dedupe_serial_universe(x)
def build_serial(x, prefix, parent):
    z=dedupe(x,parent); rows=[]; busy=pd.Timestamp.min
    for r in z.itertuples(index=False):
        et=r.baseline_entry_time; ex=getattr(r,f'{prefix}_exit_time')
        if pd.isna(et): busy=r.lifecycle_end_time; continue
        if et<=busy: continue
        if pd.notna(ex): rows.append(r._asdict()); busy=ex
        else: busy=r.lifecycle_end_time
    return pd.DataFrame(rows)
def stats(x,prefix):
    if x is None or x.empty:return {'n':0}
    col=f'{prefix}_net_R'; v=x[col].dropna(); z=x.loc[v.index]
    daily=z.assign(day=pd.to_datetime(z.baseline_entry_time).dt.date).groupby('day')[col].sum()
    risk=z[f'{prefix}_risk_budget_used'].sum() if f'{prefix}_risk_budget_used' in z else np.nan
    return {'n':int(len(v)),'trades_per_week':float(len(v)/span_weeks(z.baseline_entry_time)) if len(v)>1 else np.nan,'ev':float(v.mean()),'pf':pf(v),'positive_rate':float((v>0).mean()),'total_R':float(v.sum()),'gross_ev':float(z[f'{prefix}_gross_R'].mean()),'tp_rate':float((z[f'{prefix}_outcome']=='TP').mean()),'max_dd_R':maxdd(v),'worst_day_R':float(daily.min()) if len(daily) else np.nan,'max_consec_losses':max_consec(v),'stress10_ev':float(z[f'{prefix}_stress10_R'].mean()),'buy_ev':float(z.loc[z.dir==1,col].mean()),'sell_ev':float(z.loc[z.dir==-1,col].mean()),'promotion_rate':float(z[f'{prefix}_promoted'].mean()) if f'{prefix}_promoted' in z else 0.0,'adverse_exit_rate':float((z[f'{prefix}_outcome'].isin(['ADVERSE_EXIT','DEGRADE_EXIT'])).mean()) if f'{prefix}_outcome' in z else np.nan,'mean_risk_budget_used':float(z[f'{prefix}_risk_budget_used'].mean()) if f'{prefix}_risk_budget_used' in z else np.nan,'risk_efficiency':float(v.sum()/risk) if risk and risk>0 else np.nan}
def bootstrap_week_ev(x,prefix,seed):
    z=x.copy(); z['week']=pd.to_datetime(z.baseline_entry_time).dt.to_period('W-MON').astype(str); w=z.groupby('week')[f'{prefix}_net_R'].mean().dropna().to_numpy(float)
    if len(w)<8:return {'n_weeks':len(w),'mean':float(w.mean()) if len(w) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(w,size=len(w),replace=True).mean() for _ in range(BOOT_N)])
    return {'n_weeks':int(len(w)),'mean':float(w.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}
def bootstrap_paired(x,prefix,parent,seed):
    z=dedupe(x,parent).copy(); z['diff']=z[f'{prefix}_net_R']-z['baseline_net_R_1p5']; z['week']=pd.to_datetime(z.baseline_entry_time).dt.to_period('W-MON').astype(str); w=z.groupby('week')['diff'].mean().dropna().to_numpy(float)
    if len(w)<8:return {'n_weeks':len(w),'mean':float(w.mean()) if len(w) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(w,size=len(w),replace=True).mean() for _ in range(BOOT_N)])
    return {'n_weeks':int(len(w)),'mean':float(w.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}
def prep_parent(parent,input_path,break_path):
    df=parent.add_atr_vwap(parent.load_prices(input_path)); br=parent.load_breaks(break_path); ev=parent.score_bias(parent.build_bias_events(br,df)); strong=ev[ev.strong_accept].copy(); setups=parent.build_setups(strong,df)
    setups=parent.simulate_branch(setups,df,'BASELINE',1.5); setups=parent.simulate_branch(setups,df,'BASELINE',2.0)
    base=setups[(setups.strong_accept.astype(bool))&(setups.digestion_found.astype(bool))&(setups.baseline_entry_i>=0)&(~setups.causality_violation.astype(bool))&(setups.break_time<HOLDOUT)].copy().reset_index(drop=True)
    return df,base,br,strong
def simulate_scaled(base,df,starter_frac=0.25,probation=5,target=1.5,prefix='scaled'):
    y=base.copy(); times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    bo=df.open.to_numpy(float); bh=df.high.to_numpy(float); bl=df.low.to_numpy(float); bc=df.close.to_numpy(float)
    ao=df.ask_open.to_numpy(float); ah=df.ask_high.to_numpy(float); al=df.ask_low.to_numpy(float); ac=df.ask_close.to_numpy(float)
    cl=df.close.to_numpy(float); lines={lev:df[lev].to_numpy(float) for lev in ('MID','HIGH','LOW')}
    out=[]; violations=0
    for r in y.itertuples(index=False):
        ei=int(r.baseline_entry_i); d=int(r.dir); a=float(r.atr0); e=float(r.baseline_entry); orig_risk=RISK_ATR*a
        sl=e-d*orig_risk; tp=e+d*target*orig_risk; end_t=times[ei]+HOLD_MIN; f=float(starter_frac)
        if ei<0 or not np.isfinite(e) or orig_risk<=0:
            out.append((np.nan,np.nan,np.nan,'NO_ENTRY',pd.NaT,False,np.nan,0.0,False,False)); continue
        gross=None; outcome=None; xi=None; promoted=False; add_factor=0.0; add_entry=np.nan; risk_used=f; adverse_seen=False; degrade_seen=False
        alive=True
        for step in range(probation):
            j=ei+step
            if j>=len(df) or times[j]!=times[ei]+step or times[j]>end_t:
                violations+=1; alive=False; gross=0.0; outcome='CLOCK_FAIL'; xi=j if j<len(df) else ei; break
            line=lines[str(r.level)][j]
            adverse=(al[j] <= e-ADVERSE_DEPTH*a) if d>0 else (bh[j] >= e+ADVERSE_DEPTH*a)
            x=d*(cl[j]-line)/a; degrade=bool(x<=0.05)
            adverse_seen |= bool(adverse); degrade_seen |= bool(degrade)
            slhit=(bl[j]<=sl) if d>0 else (ah[j]>=sl)
            tphit=(bh[j]>=tp) if d>0 else (al[j]<=tp)
            if slhit:
                gross=-f; outcome='SL'; xi=j; alive=False; break
            if adverse or degrade:
                nx=j+1
                if nx>=len(df) or times[nx]!=times[j]+1:
                    violations+=1; exitp=bc[j] if d>0 else ac[j]; xi=j
                else:
                    exitp=bo[nx] if d>0 else ao[nx]; xi=nx
                gross=f*d*(exitp-e)/orig_risk; outcome='ADVERSE_EXIT' if adverse else 'DEGRADE_EXIT'; alive=False; break
            if tphit:
                gross=f*target; outcome='TP'; xi=j; alive=False; break
        if alive:
            pi=ei+probation
            if pi>=len(df) or times[pi]!=times[ei]+probation:
                violations+=1; exitp=bc[ei+probation-1] if d>0 else ac[ei+probation-1]; gross=f*d*(exitp-e)/orig_risk; outcome='CLOCK_FAIL'; xi=ei+probation-1
            else:
                add_entry=ao[pi] if d>0 else bo[pi]
                add_risk=d*(add_entry-sl)
                if add_risk<=0:
                    violations+=1; gross=-f; outcome='ADD_INVALID'; xi=pi
                else:
                    add_factor=(1.0-f)*orig_risk/add_risk; promoted=True; risk_used=1.0
                    last=pi
                    for j in range(pi,len(df)):
                        if times[j]>end_t: break
                        last=j
                        slhit=(bl[j]<=sl) if d>0 else (ah[j]>=sl)
                        tphit=(bh[j]>=tp) if d>0 else (al[j]<=tp)
                        if slhit:
                            gross=-1.0; outcome='SL'; xi=j; break
                        if tphit:
                            g1=f*target; g2=add_factor*d*(tp-add_entry)/orig_risk
                            gross=g1+g2; outcome='TP'; xi=j; break
                    if gross is None:
                        exitp=bc[last] if d>0 else ac[last]
                        g1=f*d*(exitp-e)/orig_risk; g2=add_factor*d*(exitp-add_entry)/orig_risk
                        gross=g1+g2; outcome='TIME'; xi=last
        lot_factor=f+add_factor
        comm=COMMISSION_PRICE/orig_risk*lot_factor; net=float(gross-comm); stress=float(net-0.10/orig_risk*lot_factor)
        out.append((float(gross),net,stress,outcome,df.at[int(xi),'time'],bool(promoted),float(add_entry) if np.isfinite(add_entry) else np.nan,float(risk_used),bool(adverse_seen),bool(degrade_seen)))
    cols=['gross_R','net_R','stress10_R','outcome','exit_time','promoted','promotion_entry','risk_budget_used','adverse_seen','degrade_seen']
    for k,c in enumerate(cols): y[f'{prefix}_{c}']=[row[k] for row in out]
    return y,violations
def signal_parity(base,df):
    al=df.ask_low.to_numpy(float); bh=df.high.to_numpy(float); times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    vals=[]
    for r in base.itertuples(index=False):
        ei=int(r.baseline_entry_i); d=int(r.dir); e=float(r.baseline_entry); a=float(r.atr0); hit=False
        for s in range(5):
            j=ei+s
            if j>=len(df) or times[j]!=times[ei]+s: break
            if (al[j]<=e-ADVERSE_DEPTH*a) if d>0 else (bh[j]>=e+ADVERSE_DEPTH*a): hit=True; break
        vals.append(hit)
    z=base.copy(); z['signal5']=vals; return z
def cohort_diag(z,parent):
    q=dedupe(z,parent); rows=[]
    for label,g in q.groupby('signal5'):
        rows.append({'signal5':bool(label),'n':len(g),'baseline_ev':g.baseline_net_R_1p5.mean(),'baseline_tp':(g.baseline_outcome_1p5=='TP').mean(),'mean_p_accept':g.p_accept.mean()})
    return pd.DataFrame(rows)
def promotion_diag(z,parent):
    q=dedupe(z,parent); rows=[]
    for label,g in q.groupby('primary_promoted'):
        rows.append({'promoted':bool(label),'n':len(g),'baseline_ev':g.baseline_net_R_1p5.mean(),'baseline_tp':(g.baseline_outcome_1p5=='TP').mean(),'staged_ev':g.primary_net_R.mean(),'mean_p_accept':g.p_accept.mean()})
    return pd.DataFrame(rows)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input',type=Path); ap.add_argument('--break-census',type=Path,required=True); ap.add_argument('--parent-runner',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    if sha256(a.input)!=CANONICAL_SHA: raise RuntimeError('canonical SHA mismatch')
    if sha256(a.parent_runner)!=PARENT_SHA: raise RuntimeError('parent runner SHA mismatch')
    parent=load_module(a.parent_runner); df,base,br,strong=prep_parent(parent,a.input,a.break_census)
    parity=signal_parity(base,df); confpar=parity[parity.split=='CONFIRMATION']; pdiag=cohort_diag(confpar,parent); pdiag.to_csv(out/'lab023_signal_parity.csv',index=False)
    p15,v15=simulate_scaled(base,df,PRIMARY_F,PRIMARY_PROB,1.5,'primary'); p20,v20=simulate_scaled(base,df,PRIMARY_F,PRIMARY_PROB,2.0,'primary2')
    for c in [x for x in p20.columns if x.startswith('primary2_')]: p15[c]=p20[c]
    disc=p15[p15.split=='DISCOVERY'].copy(); conf=p15[p15.split=='CONFIRMATION'].copy()
    cs=build_serial(conf,'primary',parent); ds=build_serial(disc,'primary',parent); c2=build_serial(conf,'primary2',parent)
    cm=stats(cs,'primary'); dm=stats(ds,'primary'); c2m=stats(c2,'primary2')
    bcs=parent.build_serial(conf,'BASELINE',1.5); bm=parent.stats(bcs,'BASELINE',1.5)
    weekly=bootstrap_week_ev(cs,'primary',SEED); paired=bootstrap_paired(conf,'primary',parent,SEED+1)
    promo=promotion_diag(conf,parent); promo.to_csv(out/'promotion_cohort.csv',index=False)
    dq=dedupe(conf,parent); pg=dq[dq.primary_promoted].copy(); promoted_actual={'n':len(pg),'staged_ev':float(pg.primary_net_R.mean()) if len(pg) else None,'baseline_ev':float(pg.baseline_net_R_1p5.mean()) if len(pg) else None,'tp_rate':float((pg.primary_outcome=='TP').mean()) if len(pg) else None}
    dconf=dedupe(conf,parent); starter_net=PRIMARY_F*dconf.baseline_net_R_1p5; starter_stats={'n':len(dconf),'ev':float(starter_net.mean()),'pf':pf(starter_net),'total_R':float(starter_net.sum()),'risk_efficiency':float(starter_net.sum()/(PRIMARY_F*len(dconf))) if len(dconf) else None}
    sens=[]
    for f in (0.10,0.25,0.50):
        for pr in (3,5,10):
            nm=f's{int(f*100)}_p{pr}'; zz,v=simulate_scaled(base,df,f,pr,1.5,nm); cc=zz[zz.split=='CONFIRMATION']; ss=build_serial(cc,nm,parent); sm=stats(ss,nm); sens.append({'starter_frac':f,'probation_min':pr,'violations':v,**sm})
    pd.DataFrame(sens).to_csv(out/'sensitivity.csv',index=False)
    parity_counts=confpar.signal5.value_counts().to_dict(); parity_ok=(int(parity_counts.get(True,0))==1839 and int(parity_counts.get(False,0))==515)
    pc=promo.set_index('promoted') if len(promo) else pd.DataFrame(); prom_base=float(pc.loc[True,'baseline_ev']) if (not pc.empty and True in pc.index) else np.nan; non_base=float(pc.loc[False,'baseline_ev']) if (not pc.empty and False in pc.index) else np.nan
    gates={'G0_DATA_CAUSALITY': bool(v15==0 and v20==0 and parity_ok),'G1_POWER': bool(cm.get('n',0)>=300 and cm.get('trades_per_week',0)>=3),'G2_POSITIVE_ECONOMICS': bool(cm.get('ev',-9)>0 and cm.get('pf',0)>1),'G3_WEEKLY_ROBUSTNESS': bool(weekly['ci95'][0] is not None and weekly['ci95'][0]>0),'G4_RISK_EFFICIENCY': bool(cm.get('risk_efficiency',-9)>0),'G5_PROMOTION_SELECTIVITY': bool(np.isfinite(prom_base) and np.isfinite(non_base) and prom_base>0 and prom_base>non_base),'G6_PROMOTED_EXECUTION': bool(promoted_actual['staged_ev'] is not None and promoted_actual['staged_ev']>0),'G7_DISCOVERY_TRANSFER': bool(dm.get('ev',-9)>0 and cm.get('ev',-9)>0),'G8_DIRECTION_BREADTH': bool(cm.get('buy_ev',-9)>0 and cm.get('sell_ev',-9)>0),'G9_2R_SURVIVAL': bool(c2m.get('ev',-9)>0),'G10_COST_STRESS': bool(cm.get('stress10_ev',-9)>0),'G11_PROP_DD_PROXY': bool(cm.get('worst_day_R',-99)>-4 and cm.get('max_dd_R',999)<bm.get('max_dd_R',999)),'G12_BEATS_FULL_IMMEDIATE': bool((paired['ci95'][0] is not None and paired['ci95'][0]>0) or (cm.get('ev',-9)>0 and cm.get('risk_efficiency',-9)>0 and cm.get('max_dd_R',999)<bm.get('max_dd_R',999)))}
    status='PROBATION_SCALING_EDGE' if all(gates.values()) else ('PROBATION_SELECTS_HEALTH_BUT_EXECUTION_NOT_POSITIVE' if gates['G5_PROMOTION_SELECTIVITY'] else 'NO_PROBATION_SCALING_EDGE')
    verdict={'status':status,'gates':gates,'primary_confirmation':cm,'primary_discovery':dm,'confirmation_2R':c2m,'full_immediate_baseline':bm,'starter_only_25_independent':starter_stats,'weekly_ev_bootstrap':weekly,'paired_staged_minus_full':paired,'promoted_actual':promoted_actual,'parity_counts':{'event':int(parity_counts.get(True,0)),'no_event':int(parity_counts.get(False,0)),'pass':parity_ok},'causality_violations':int(v15+v20),'holdout_opened':False}
    pd.DataFrame([{'split':'CONFIRMATION','strategy':'PROBATION_25_TO_100',**cm},{'split':'DISCOVERY','strategy':'PROBATION_25_TO_100',**dm},{'split':'CONFIRMATION','strategy':'PROBATION_25_TO_100_2R',**c2m},{'split':'CONFIRMATION','strategy':'FULL_IMMEDIATE',**bm}]).to_csv(out/'summary.csv',index=False)
    p15.to_csv(out/'events.csv.gz',index=False,compression='gzip')
    report=f'''# {LAB} — {VERSION} REPORT\n\n**Verdict:** `{status}`  \n**Holdout opened:** `false`\n\n## LAB023 signal parity\n- Confirmation same-side 0.10ATR event: **{int(parity_counts.get(True,0))}**\n- no-event: **{int(parity_counts.get(False,0))}**\n- exact parity expected 1839 / 515: **{parity_ok}**\n\n## Primary Confirmation — starter 25% -> promote to 100% after healthy 5m probation\n- N **{cm.get('n')}**, trades/week **{cm.get('trades_per_week'):.2f}**\n- EV **{cm.get('ev'):+.4f}R**, PF **{cm.get('pf'):.3f}**, TP **{cm.get('tp_rate'):.2%}**\n- promotion rate **{cm.get('promotion_rate'):.2%}**, mean risk budget used **{cm.get('mean_risk_budget_used'):.3f}R**\n- risk-efficiency **{cm.get('risk_efficiency'):+.4f} R per risk-budget-R**\n- BUY **{cm.get('buy_ev'):+.4f}R**, SELL **{cm.get('sell_ev'):+.4f}R**\n- stress10 **{cm.get('stress10_ev'):+.4f}R**\n- max DD **{cm.get('max_dd_R'):.2f}R**, worst day **{cm.get('worst_day_R'):.2f}R**\n- weekly EV CI **{weekly['ci95']}**\n\n## Baseline / lift\n- FULL_IMMEDIATE serial EV **{bm.get('ev'):+.4f}R**, PF **{bm.get('pf'):.3f}**, max DD **{bm.get('max_dd_R'):.2f}R**\n- staged-minus-full paired weekly mean **{paired['mean']:+.4f}R**, CI **{paired['ci95']}**\n- STARTER_ONLY_25 independent EV **{starter_stats['ev']:+.4f}R**, risk-efficiency **{starter_stats['risk_efficiency']:+.4f}**\n\n## Promotion selectivity\n{promo.to_string(index=False)}\n\n## Actual promoted cohort\n- N **{promoted_actual['n']}**, staged EV **{promoted_actual['staged_ev']:+.4f}R**, baseline EV **{promoted_actual['baseline_ev']:+.4f}R**, TP **{promoted_actual['tp_rate']:.2%}**\n\n## Transfer / 2R\n- Discovery EV **{dm.get('ev'):+.4f}R**\n- Confirmation 2R EV **{c2m.get('ev'):+.4f}R**, PF **{c2m.get('pf'):.3f}**\n\n## Frozen gates\n''' + '\n'.join([f'- {k}: **{"PASS" if v else "FAIL"}**' for k,v in gates.items()]) + '\n\nNo sensitivity rescue, no holdout opening, no EA/live authorization.\n'
    (out/'REPORT.md').write_text(report); (out/'verdict.json').write_text(json.dumps(verdict,indent=2,default=str))
    audit={'canonical_sha':sha256(a.input),'parent_runner_sha':sha256(a.parent_runner),'raw_rows':len(df),'break_events':len(br),'strong_bias_events':len(strong),'early_entry_events':len(base),'confirmation_events':len(conf),'max_price_time_read':str(df.time.max()),'holdout_opened':False,'causality_violations':int(v15+v20),'lab023_signal_parity_pass':parity_ok}
    (out/'audit.json').write_text(json.dumps(audit,indent=2)); print(json.dumps(verdict,indent=2,default=str))
if __name__=='__main__': main()
