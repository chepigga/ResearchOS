#!/usr/bin/env python3
from __future__ import annotations

import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_CAUSAL_CONTEXT_DIRECTION_M5_M15_VS_H1_STRUCTURAL_ASYMMETRY_LAB_004'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB002_PATH=ROOT/'labs'/'CROSS_MARKET_CAUSAL_CONTEXT_CONTINUOUS_SCORE_INTERACTION_LAB_002'/'run_lab.py'
THRESH=0.55
BOOT_N=5000
SEED=2026090904
YEARS=['2022','2023','2024','2025','2026']


def load_lab002():
    spec=importlib.util.spec_from_file_location('lab002', LAB002_PATH)
    mod=importlib.util.module_from_spec(spec); assert spec.loader is not None
    spec.loader.exec_module(mod); return mod


def meanv(s):
    v=pd.to_numeric(s,errors='coerce').dropna(); return float(v.mean()) if len(v) else np.nan


def premium(g, outcome='excess'):
    h=g[g.is_high & g.bias_compat_label.isin(['ALIGNED','OPPOSED'])]
    a=pd.to_numeric(h.loc[h.bias_compat_label.eq('ALIGNED'),outcome],errors='coerce').dropna()
    o=pd.to_numeric(h.loc[h.bias_compat_label.eq('OPPOSED'),outcome],errors='coerce').dropna()
    return {'aligned_n':int(len(a)),'opposed_n':int(len(o)),
            'aligned_mean':float(a.mean()) if len(a) else np.nan,
            'opposed_mean':float(o.mean()) if len(o) else np.nan,
            'premium':float(a.mean()-o.mean()) if len(a) and len(o) else np.nan}


def asym_stats(d, outcome='excess'):
    sm=premium(d[d.tf.isin(['M5','M15'])],outcome)
    h1=premium(d[d.tf.eq('H1')],outcome)
    asym=sm['premium']-h1['premium'] if np.isfinite(sm['premium']) and np.isfinite(h1['premium']) else np.nan
    return {'small':sm,'h1':h1,'asymmetry':float(asym) if np.isfinite(asym) else np.nan}


def weekly_bootstrap_asym(d, time_col='available_event_time', outcome='excess'):
    z=d[d.is_high & d.bias_compat_label.isin(['ALIGNED','OPPOSED'])].copy()
    t=pd.to_datetime(z[time_col],errors='coerce',utc=True)
    z=z.loc[t.notna()].copy(); t=t.loc[t.notna()]
    z['_week']=t.dt.to_period('W-SUN').astype(str).values
    z['_y']=pd.to_numeric(z[outcome],errors='coerce')
    z=z.dropna(subset=['_y'])
    rows=[]
    # SA,SO,HA,HO counts/sums
    for _,g in z.groupby('_week',sort=True):
        rec=[]
        for tfgrp,comp in [('SMALL','ALIGNED'),('SMALL','OPPOSED'),('H1','ALIGNED'),('H1','OPPOSED')]:
            m=(g.tf.isin(['M5','M15']) if tfgrp=='SMALL' else g.tf.eq('H1')) & g.bias_compat_label.eq(comp)
            v=g.loc[m,'_y'].to_numpy(float); rec.extend([len(v),float(v.sum())])
        rows.append(rec)
    a=np.asarray(rows,float); rng=np.random.default_rng(SEED); vals=np.full(BOOT_N,np.nan)
    for k in range(BOOT_N):
        s=a[rng.integers(0,len(a),size=len(a))].sum(axis=0)
        means=[]
        for j in range(0,8,2):
            n,sm=s[j],s[j+1]; means.append(sm/n if n>0 else np.nan)
        sa,so,ha,ho=means
        if np.all(np.isfinite(means)): vals[k]=(sa-so)-(ha-ho)
    vals=vals[np.isfinite(vals)]
    return {'weeks':int(len(a)),'draws':BOOT_N,
            'ci_lo':float(np.quantile(vals,.025)),'ci_hi':float(np.quantile(vals,.975)),
            'p_positive':float(np.mean(vals>0))}


def by_year(d):
    rows=[]
    for y in YEARS:
        g=d[d.year.astype(str).eq(y)]; s=asym_stats(g)
        eligible=min(s['small']['aligned_n'],s['small']['opposed_n'],s['h1']['aligned_n'],s['h1']['opposed_n'])>=100
        rows.append({'year':y,'n':int(len(g)),
                     'small_premium':s['small']['premium'],'h1_premium':s['h1']['premium'],'asymmetry':s['asymmetry'],
                     'small_aligned_n':s['small']['aligned_n'],'small_opposed_n':s['small']['opposed_n'],
                     'h1_aligned_n':s['h1']['aligned_n'],'h1_opposed_n':s['h1']['opposed_n'],
                     'eligible':bool(eligible),'positive':bool(eligible and np.isfinite(s['asymmetry']) and s['asymmetry']>0)})
    return pd.DataFrame(rows)


def loyo(d, eligible_years):
    rows=[]
    for y in eligible_years:
        s=asym_stats(d[~d.year.astype(str).eq(y)])
        rows.append({'left_out':y,'n':int((~d.year.astype(str).eq(y)).sum()),
                     'small_premium':s['small']['premium'],'h1_premium':s['h1']['premium'],
                     'asymmetry':s['asymmetry'],'positive':bool(np.isfinite(s['asymmetry']) and s['asymmetry']>0)})
    return pd.DataFrame(rows)


def tf_signal_features(m1):
    out=[]
    for tf,rule in [('M5','5min'),('M15','15min'),('H1','1h')]:
        g=m1.set_index('time').resample(rule,origin='epoch',label='left',closed='left').agg(
            open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
        pc=g.close.shift(1)
        tr=pd.concat([g.high-g.low,(g.high-pc).abs(),(g.low-pc).abs()],axis=1).max(axis=1)
        g['signal_atr']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
        g['signal_close']=g.close; g['tf']=tf
        out.append(g[['time','tf','signal_close','signal_atr']])
    return pd.concat(out,ignore_index=True)


def add_structural_features(x,m1):
    feats=tf_signal_features(m1)
    z=x.merge(feats,on=['time','tf'],how='left',validate='many_to_one')
    z['risk_pct']=1.5*z.signal_atr/z.signal_close
    z['context_age_hours']=(pd.to_datetime(z.available_event_time)-pd.to_datetime(z.available_time)).dt.total_seconds()/3600.0
    T=m1.time.to_numpy(dtype='datetime64[ns]'); C=m1.close.to_numpy(float)
    base=pd.to_datetime(z.available_event_time).to_numpy(dtype='datetime64[ns]')
    for h in [10,30,120]:
        target=base+np.timedelta64(h,'h')
        ix=np.searchsorted(T,target,side='right')-1
        ok=(ix>=0)&(ix<len(C))&np.isfinite(z.signal_atr.to_numpy(float))&(z.signal_atr.to_numpy(float)>0)
        fut=np.full(len(z),np.nan); fut[ok]=C[ix[ok]]
        z[f'fwd_{h}h_r']=z.dir*(fut-z.signal_close)/(1.5*z.signal_atr)
    return z


def horizon_table(z):
    rows=[]
    for h in [10,30,120]:
        for grp,mask in [('M5_M15',z.tf.isin(['M5','M15'])),('H1',z.tf.eq('H1'))]:
            p=premium(z[mask],f'fwd_{h}h_r')
            rows.append({'horizon_h':h,'tf_group':grp,**p})
    return pd.DataFrame(rows)


def risk_quartile_table(z):
    qbase=z[z.is_high & z.bias_compat_label.isin(['ALIGNED','OPPOSED']) & z.risk_pct.notna()].copy()
    qbase['risk_q'],edges=pd.qcut(qbase.risk_pct,q=4,labels=False,retbins=True,duplicates='drop')
    qbase['risk_q']=qbase.risk_q+1
    rows=[]
    for q in sorted(qbase.risk_q.dropna().unique()):
        g=qbase[qbase.risk_q.eq(q)]
        sm=premium(g[g.tf.isin(['M5','M15'])]); h1=premium(g[g.tf.eq('H1')])
        eligible=min(sm['aligned_n'],sm['opposed_n'],h1['aligned_n'],h1['opposed_n'])>=100
        rows.append({'risk_q':int(q),'risk_min':float(g.risk_pct.min()),'risk_max':float(g.risk_pct.max()),
                     'small_premium':sm['premium'],'h1_premium':h1['premium'],
                     'small_aligned_n':sm['aligned_n'],'small_opposed_n':sm['opposed_n'],
                     'h1_aligned_n':h1['aligned_n'],'h1_opposed_n':h1['opposed_n'],
                     'eligible':bool(eligible),'h1_nonnegative':bool(eligible and np.isfinite(h1['premium']) and h1['premium']>=0)})
    return pd.DataFrame(rows),[float(v) for v in edges]


def atr_ratio_table(z):
    h=z[z.tf.eq('H1') & z.is_high & z.bias_compat_label.isin(['ALIGNED','OPPOSED']) & z.atr_ratio.notna()].copy()
    h['atr_q'],edges=pd.qcut(h.atr_ratio,q=4,labels=False,retbins=True,duplicates='drop'); h['atr_q']=h.atr_q+1
    rows=[]
    for q,g in h.groupby('atr_q',sort=True):
        p=premium(g); rows.append({'atr_q':int(q),'atr_ratio_min':float(g.atr_ratio.min()),'atr_ratio_max':float(g.atr_ratio.max()),**p})
    return pd.DataFrame(rows),[float(v) for v in edges]


def age_table(z):
    h=z[z.tf.eq('H1')].copy()
    h['age_bucket']=pd.cut(h.context_age_hours,bins=[0,1,2,3,4.01],right=False,include_lowest=True,
                           labels=['0_1','1_2','2_3','3_4'])
    rows=[]
    for k,g in h.groupby('age_bucket',observed=True,sort=True): rows.append({'age_bucket':str(k),**premium(g)})
    # prereg aggregate young vs stale
    for k,m in [('LT2',h.context_age_hours<2),('GE2',h.context_age_hours>=2)]: rows.append({'age_bucket':k,**premium(h[m])})
    return pd.DataFrame(rows)


def mechanic_table(z):
    rows=[]
    for c in sorted(x for x in z.columns if x.startswith('f_')):
        g=z[pd.to_numeric(z[c],errors='coerce').fillna(0)>0]
        sm=premium(g[g.tf.isin(['M5','M15'])]); h1=premium(g[g.tf.eq('H1')])
        eligible=min(sm['aligned_n'],sm['opposed_n'],h1['aligned_n'],h1['opposed_n'])>=100
        rows.append({'mechanic':c,'n':int(len(g)),'small_premium':sm['premium'],'h1_premium':h1['premium'],
                     'small_aligned_n':sm['aligned_n'],'small_opposed_n':sm['opposed_n'],
                     'h1_aligned_n':h1['aligned_n'],'h1_opposed_n':h1['opposed_n'],
                     'eligible':bool(eligible),'h1_nonnegative':bool(eligible and np.isfinite(h1['premium']) and h1['premium']>=0)})
    return pd.DataFrame(rows)


def h1_direction_year(z):
    h=z[z.tf.eq('H1')]
    rows=[]
    for typ,key,mask in [('DIR','BUY',h.dir.eq(1)),('DIR','SELL',h.dir.eq(-1))]+[( 'YEAR',y,h.year.astype(str).eq(y)) for y in YEARS]:
        p=premium(h[mask]); rows.append({'type':typ,'key':key,'n':int(mask.sum()),**p})
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--xau-pool',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    lab002=load_lab002(); router=lab002.load_router_module()
    x,meta=lab002.build_xau_join(Path(a.xau_m1),Path(a.xau_pool),router)
    if len(x)!=263405: raise RuntimeError(f'Frozen XAU parity failed {len(x)} != 263405')
    x['is_high']=x.context_score>THRESH
    m1=lab002.read_xau_native(Path(a.xau_m1))
    z=add_structural_features(x,m1)

    primary=asym_stats(z); boot=weekly_bootstrap_asym(z)
    yr=by_year(z); yr.to_csv(out/'year_asymmetry.csv',index=False)
    eligible_years=yr.loc[yr.eligible,'year'].astype(str).tolist()
    lo=loyo(z,eligible_years); lo.to_csv(out/'leave_one_year_out.csv',index=False)
    ht=horizon_table(z); ht.to_csv(out/'horizon_common_clock.csv',index=False)
    rq,rq_edges=risk_quartile_table(z); rq.to_csv(out/'risk_pct_quartiles.csv',index=False)
    ar,ar_edges=atr_ratio_table(z); ar.to_csv(out/'h1_atr_ratio_quartiles.csv',index=False)
    ag=age_table(z); ag.to_csv(out/'h1_context_age.csv',index=False)
    mt=mechanic_table(z); mt.to_csv(out/'mechanic_matched.csv',index=False)
    dy=h1_direction_year(z); dy.to_csv(out/'h1_direction_year.csv',index=False)

    # Primary gates
    ey=yr[yr.eligible]; primary_gates={
      'P1_asym_gt_zero':bool(np.isfinite(primary['asymmetry']) and primary['asymmetry']>0),
      'P2_boot_ci_lo_gt_zero':bool(np.isfinite(boot['ci_lo']) and boot['ci_lo']>0),
      'P3_year_4of5_positive':bool(len(ey)==5 and int(ey.positive.sum())>=4),
      'P4_loyo_4of5_positive':bool(len(lo)==5 and int(lo.positive.sum())>=4),
    }
    primary_confirmed=all(primary_gates.values())

    # Cause A horizon
    hp={int(r.horizon_h):float(r.premium) for _,r in ht[ht.tf_group.eq('H1')].iterrows()}
    horizon_support=bool(np.isfinite(hp.get(10,np.nan)) and np.isfinite(hp.get(30,np.nan)) and np.isfinite(hp.get(120,np.nan)) and
                         (((hp[10]>=0 or hp[30]>=0) and hp[120]<0) or (hp[10]>hp[30]>hp[120] and hp[120]<0)))

    # Cause B risk scaling
    erq=rq[rq.eligible]; risk_support=bool(len(erq)==4 and int(erq.h1_nonnegative.sum())>=3)

    # Cause C staleness
    def row_age(k):
        q=ag[ag.age_bucket.eq(k)]
        return q.iloc[0] if len(q) else None
    young=row_age('LT2'); stale=row_age('GE2')
    age_support=False
    if young is not None and stale is not None:
        enough=min(int(young.aligned_n),int(young.opposed_n),int(stale.aligned_n),int(stale.opposed_n))>=100
        age_support=bool(enough and np.isfinite(young.premium) and np.isfinite(stale.premium) and young.premium>=0 and stale.premium<0)

    # Cause D composition
    em=mt[mt.eligible]; mech_frac=float(em.h1_nonnegative.mean()) if len(em) else np.nan
    mech_med=float(em.h1_premium.median()) if len(em) else np.nan
    composition_support=bool(len(em)>0 and mech_frac>=.70 and mech_med>0 and primary['h1']['premium']<0)

    causes={'HORIZON_MISMATCH':horizon_support,'RISK_SCALING':risk_support,'CONTEXT_STALENESS':age_support,'MECHANIC_COMPOSITION':composition_support}
    active=[k for k,v in causes.items() if v]
    if not primary_confirmed: verdict='H1_ASYMMETRY_NOT_CONFIRMED'
    elif len(active)>1: verdict='MULTIFACTOR_H1_ASYMMETRY'
    elif len(active)==1: verdict='H1_ASYMMETRY_EXPLAINED_BY_'+active[0]
    else: verdict='STRUCTURAL_H1_ASYMMETRY_UNEXPLAINED'

    summary={'lab':LAB,'status':'REUSED_HISTORY_PREREGISTERED_STRUCTURAL_DIAGNOSTIC','verdict':verdict,
      'n':int(len(z)),'high_threshold':THRESH,'primary':primary,'bootstrap':boot,'primary_gates':primary_gates,
      'primary_confirmed':primary_confirmed,'positive_years':int(ey.positive.sum()),'eligible_years':int(len(ey)),
      'loyo_positive':int(lo.positive.sum()),'loyo_runs':int(len(lo)),
      'causes':causes,'active_causes':active,
      'horizon_h1_premiums':hp,'risk_quartiles_edges':rq_edges,'risk_eligible':int(len(erq),'__dummy') if False else int(len(erq)),
      'risk_h1_nonnegative':int(erq.h1_nonnegative.sum()) if len(erq) else 0,
      'atr_ratio_edges':ar_edges,
      'mechanics_eligible':int(len(em)),'mechanics_h1_nonnegative_fraction':mech_frac,'mechanics_h1_median_premium':mech_med,
      'xau_meta':meta,'promotion_authorized':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',
      '> Reused-history structural diagnostic. No TF deletion, live filter, or sizing change is authorized.','',
      '## Primary asymmetry','',
      f"- M5+M15 HIGH premium: **{primary['small']['premium']:+.5f}R** (A={primary['small']['aligned_n']}, O={primary['small']['opposed_n']})",
      f"- H1 HIGH premium: **{primary['h1']['premium']:+.5f}R** (A={primary['h1']['aligned_n']}, O={primary['h1']['opposed_n']})",
      f"- Asymmetry: **{primary['asymmetry']:+.5f}R**",
      f"- Weekly bootstrap 95% CI: **[{boot['ci_lo']:+.5f}, {boot['ci_hi']:+.5f}]**, P>0={boot['p_positive']:.3f}",
      f"- Years positive: {int(ey.positive.sum())}/{len(ey)}; LOYO positive: {int(lo.positive.sum())}/{len(lo)}",'',
      '## Cause audit','']
    for k,v in causes.items(): lines.append(f"- {'SUPPORTED' if v else 'NOT SUPPORTED'} — `{k}`")
    lines += ['', '### Common-clock H1 premiums']
    for h in [10,30,120]: lines.append(f'- {h}h: {hp.get(h,np.nan):+.5f}R')
    lines += ['',f'- Risk quartiles with non-negative H1 premium: {int(erq.h1_nonnegative.sum()) if len(erq) else 0}/{len(erq)} eligible',
              f'- Mechanics non-negative H1 premium: {int(em.h1_nonnegative.sum()) if len(em) else 0}/{len(em)} eligible; median={mech_med:+.5f}',
              '', 'See CSV outputs for year, horizon, risk, ATR-ratio, Context-age, direction, and mechanic decomposition.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print((out/'REPORT.md').read_text()); print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
