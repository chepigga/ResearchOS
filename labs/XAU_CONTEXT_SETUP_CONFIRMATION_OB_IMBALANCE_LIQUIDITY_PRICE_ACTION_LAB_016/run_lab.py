#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_SETUP_CONFIRMATION_OB_IMBALANCE_LIQUIDITY_PRICE_ACTION_LAB_016'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
LAB13_PATH=ROOT/'labs'/'XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013'/'run_lab.py'
XAU_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
YEARS=[2023,2024,2025,2026]
BOOT_N=5000
SEED=2026091216
COMPONENTS=['OB_CONFIRM','IMBALANCE_CONFIRM','LIQUIDITY_CONFIRM','PRICE_ACTION_CONFIRM']


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(mod); return mod


def week_col(s:pd.Series)->pd.Series:
    return pd.to_datetime(s).dt.to_period('W-SUN').astype(str)


def to_m15(m1:pd.DataFrame)->pd.DataFrame:
    z=(m1.set_index('time').resample('15min',origin='epoch',label='left',closed='left')
       .agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum')).dropna())
    tr=pd.concat([(z.high-z.low),(z.high-z.close.shift()).abs(),(z.low-z.close.shift()).abs()],axis=1).max(axis=1)
    z['atr14_m15']=tr.rolling(14,min_periods=14).mean()
    return z


def prior_slice(m15:pd.DataFrame,t:pd.Timestamp,hours:int)->pd.DataFrame:
    # only M15 bars fully closed by available_time; a bar labeled t-15m is the latest eligible bar
    return m15[(m15.index>=t-pd.Timedelta(hours=hours)) & (m15.index < t)].copy()


def order_block_confirm(m15:pd.DataFrame,t:pd.Timestamp,direction:int)->bool:
    w=prior_slice(m15,t,12)
    if len(w)<20: return False
    idx=list(w.index)
    for p in range(len(w)-4,-1,-1):
        c=w.iloc[p]
        if direction==1 and not (c.close<c.open): continue
        if direction==-1 and not (c.close>c.open): continue
        if p<4: continue
        prior4=w.iloc[p-4:p]
        for k in range(p+1,min(p+4,len(w))):
            disp=w.iloc[k]; atr=disp.atr14_m15
            if not np.isfinite(atr) or atr<=0: continue
            body=abs(disp.close-disp.open)
            if direction==1:
                good=body>=atr and disp.close>c.high and disp.close>prior4.high.max()
            else:
                good=body>=atr and disp.close<c.low and disp.close<prior4.low.min()
            if not good: continue
            post=w.iloc[k+1:]
            if post.empty: continue
            if direction==1:
                invalid=(post.close<c.low).any()
                touch=((post.low<=c.high)&(post.high>=c.low))
                if invalid or not touch.any(): continue
                first_touch_pos=np.flatnonzero(touch.to_numpy())[0]
                aft=post.iloc[first_touch_pos:]
                if (aft.close>((c.high+c.low)/2)).any(): return True
            else:
                invalid=(post.close>c.high).any()
                touch=((post.high>=c.low)&(post.low<=c.high))
                if invalid or not touch.any(): continue
                first_touch_pos=np.flatnonzero(touch.to_numpy())[0]
                aft=post.iloc[first_touch_pos:]
                if (aft.close<((c.high+c.low)/2)).any(): return True
    return False


def imbalance_confirm(m15:pd.DataFrame,t:pd.Timestamp,direction:int)->bool:
    w=prior_slice(m15,t,6)
    if len(w)<3: return False
    for i in range(len(w)-1,1,-1):
        a=w.iloc[i-2]; c=w.iloc[i]
        later=w.iloc[i+1:]
        if direction==1 and c.low>a.high:
            if later.empty or not (later.low<=a.high).any(): return True
        if direction==-1 and c.high<a.low:
            if later.empty or not (later.high>=a.low).any(): return True
    return False


def liquidity_confirm(m15:pd.DataFrame,t:pd.Timestamp,direction:int)->bool:
    # need 5h reference + 4h event window => pull 9h
    w=prior_slice(m15,t,9)
    if len(w)<24: return False
    event_start=t-pd.Timedelta(hours=4)
    for i in range(20,len(w)):
        ts=w.index[i]
        if ts<event_start: continue
        e=w.iloc[i]; p=w.iloc[i-20:i]
        if direction==1:
            ref=float(p.low.min())
            if e.low<ref and e.close>ref: return True
        else:
            ref=float(p.high.max())
            if e.high>ref and e.close<ref: return True
    return False


def price_action_confirm(m15:pd.DataFrame,t:pd.Timestamp,direction:int)->bool:
    # Pull 4h so preceding 8 bars exist for structure checks; event itself limited to last 2h.
    w=prior_slice(m15,t,4)
    if len(w)<10: return False
    event_start=t-pd.Timedelta(hours=2)
    for i in range(1,len(w)):
        if w.index[i]<event_start: continue
        e=w.iloc[i]; prev=w.iloc[i-1]
        rng=e.high-e.low
        if rng<=0: continue
        if direction==1:
            engulf=(e.close>e.open and prev.close<prev.open and e.open<=prev.close and e.close>=prev.open)
            lower_wick=min(e.open,e.close)-e.low
            reject=(lower_wick/rng>=0.45 and (e.high-e.close)/rng<=0.35)
            struct=False
            if i>=8: struct=e.close>w.iloc[i-8:i].high.max()
        else:
            engulf=(e.close<e.open and prev.close>prev.open and e.open>=prev.close and e.close<=prev.open)
            upper_wick=e.high-max(e.open,e.close)
            reject=(upper_wick/rng>=0.45 and (e.close-e.low)/rng<=0.35)
            struct=False
            if i>=8: struct=e.close<w.iloc[i-8:i].low.min()
        if engulf or reject or struct: return True
    return False


def add_confirmation(d:pd.DataFrame,m15:pd.DataFrame,pop:pd.Series)->pd.DataFrame:
    z=d.copy()
    for c in COMPONENTS: z[c]=False
    for idx,r in z.loc[pop].iterrows():
        t=pd.Timestamp(r.available_time); direction=int(r.D14_CONCORDANCE)
        z.at[idx,'OB_CONFIRM']=order_block_confirm(m15,t,direction)
        z.at[idx,'IMBALANCE_CONFIRM']=imbalance_confirm(m15,t,direction)
        z.at[idx,'LIQUIDITY_CONFIRM']=liquidity_confirm(m15,t,direction)
        z.at[idx,'PRICE_ACTION_CONFIRM']=price_action_confirm(m15,t,direction)
    z['SETUP_CONFIRMATION_PCT']=25*z[COMPONENTS].astype(int).sum(axis=1)
    return z


def cluster_boot_group_diff(q:pd.DataFrame,metric:str,group_col:str,high_val:bool,seed:int)->dict:
    z=q[['available_time',metric,group_col]].copy().dropna(subset=['available_time',metric,group_col])
    a=z[z[group_col].eq(high_val)]; b=z[z[group_col].ne(high_val)]
    obs=float(a[metric].mean()-b[metric].mean()) if len(a) and len(b) else np.nan
    if z.empty: return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n_hi':0,'n_lo':0,'weeks':0}
    z['week']=week_col(z.available_time); weeks=sorted(z.week.unique()); stats=[]
    for w in weeks:
        g=z[z.week.eq(w)]; aa=g[g[group_col].eq(high_val)][metric].to_numpy(float); bb=g[g[group_col].ne(high_val)][metric].to_numpy(float)
        stats.append([len(aa),np.nansum(aa),len(bb),np.nansum(bb)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[0]>0 and s[2]>0: draws.append(s[1]/s[0]-s[3]/s[2])
    draws=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(draws,.025)) if len(draws) else np.nan,'ci_hi':float(np.quantile(draws,.975)) if len(draws) else np.nan,'n_hi':int(len(a)),'n_lo':int(len(b)),'weeks':int(m)}


def cluster_boot_mean(q:pd.DataFrame,metric:str,seed:int)->dict:
    z=q[['available_time',metric]].copy(); z[metric]=pd.to_numeric(z[metric],errors='coerce'); z=z.dropna()
    obs=float(z[metric].mean()) if len(z) else np.nan
    if z.empty:return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n':0,'weeks':0}
    z['week']=week_col(z.available_time); arr=z.groupby('week')[metric].agg(['count','sum']).to_numpy(float)
    rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[0]>0: draws.append(s[1]/s[0])
    draws=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(draws,.025)),'ci_hi':float(np.quantile(draws,.975)),'n':int(len(z)),'weeks':int(m)}


def annual_group_premium(q:pd.DataFrame,metric:str,group_col:str)->pd.DataFrame:
    y=pd.to_datetime(q.available_time).dt.year; rows=[]
    for year in YEARS:
        g=q[y.eq(year)].dropna(subset=[metric,group_col]); a=g[g[group_col]]; b=g[~g[group_col]]
        eff=float(a[metric].mean()-b[metric].mean()) if len(a) and len(b) else np.nan
        elig=bool(len(a)>=20 and len(b)>=20 and np.isfinite(eff))
        rows.append({'year':year,'n_hi':len(a),'n_lo':len(b),'effect':eff,'eligible':elig,'positive':bool(elig and eff>0)})
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1)
    if sha256(p)!=XAU_SHA: raise RuntimeError('Canonical XAU SHA mismatch')
    lab8=load_module(LAB8_PATH,'lab8_016'); lab9=load_module(LAB9_PATH,'lab9_016'); lab10=load_module(LAB10_PATH,'lab10_016'); lab13=load_module(LAB13_PATH,'lab13_016')
    m1=lab8.read_xau_native(p); m15=to_m15(m1); h4=lab8.to_h4(m1); router=lab8.load_router_module()
    ctx=router.add_router(h4); ctx=lab8.add_forward_metrics(ctx); ctx=ctx.dropna(subset=['available_time','atr14']).copy(); allbars,onset=lab8.make_episodes(ctx)
    if len(allbars)!=6216 or len(onset)!=610: raise RuntimeError(f'Parity failed bars={len(allbars)} episodes={len(onset)}')
    d=lab9.add_roles(allbars); d=lab10.add_components_and_candidates(d); d=lab13.add_prediction_candidates(d)
    d['D14_CONCORDANCE']=np.where((d.D1_HTF_BIAS==d.D2_TREND_PRESSURE)&d.D1_HTF_BIAS.ne(0),d.D1_HTF_BIAS,0).astype(int)
    pop=d.regime.eq('PULLBACK')&d.G1_VOL_COMPRESSION.fillna(False)&d.D14_CONCORDANCE.ne(0)
    d=add_confirmation(d,m15,pop)
    fp=lab13.exact_first_passage(m1,d,pop); d=d.join(fp,how='left')
    q=d.loc[pop].copy(); q['D14_signed24']=q.D14_CONCORDANCE*pd.to_numeric(q.close_ret_atr_24h,errors='coerce')
    q['HIGH50']=q.SETUP_CONFIRMATION_PCT.ge(50); q['HIGH75']=q.SETUP_CONFIRMATION_PCT.ge(75)
    resolved=q[q.target_dir.isin([-1,1])].copy(); resolved['correct']=(resolved.D14_CONCORDANCE==resolved.target_dir).astype(float)

    h1raw=cluster_boot_group_diff(resolved,'correct','HIGH50',True,SEED+1); h1yrs=annual_group_premium(resolved,'correct','HIGH50')
    h1_transfer=bool(int(h1yrs.eligible.sum())>=3 and int(h1yrs.positive.sum())>=3)
    h1=bool(h1raw['n_hi']>=100 and h1raw['n_lo']>=100 and h1raw['observed']>0 and np.isfinite(h1raw['ci_lo']) and h1raw['ci_lo']>0 and h1_transfer)

    follow=q.dropna(subset=['D14_signed24']).copy(); h2raw=cluster_boot_group_diff(follow,'D14_signed24','HIGH50',True,SEED+2); h2yrs=annual_group_premium(follow,'D14_signed24','HIGH50')
    h2_transfer=bool(int(h2yrs.eligible.sum())>=3 and int(h2yrs.positive.sum())>=3)
    h2=bool(h2raw['n_hi']>=150 and h2raw['n_lo']>=150 and h2raw['observed']>0 and np.isfinite(h2raw['ci_lo']) and h2raw['ci_lo']>0 and h2_transfer)

    hi75=resolved[resolved.HIGH75].copy(); h3raw=cluster_boot_mean(hi75,'correct',SEED+3)
    h3=bool(len(hi75)>=60 and h3raw['observed']>0.55 and np.isfinite(h3raw['ci_lo']) and h3raw['ci_lo']>0.50)

    buckets=[]
    for score in [0,25,50,75,100]:
        g=q[q.SETUP_CONFIRMATION_PCT.eq(score)]; r=g[g.target_dir.isin([-1,1])].copy()
        acc=float((r.D14_CONCORDANCE==r.target_dir).mean()) if len(r) else np.nan
        signed=pd.to_numeric(g.D14_signed24,errors='coerce').dropna()
        buckets.append({'score_pct':score,'n_all':len(g),'n_resolved':len(r),'accuracy':acc,'mean_signed24_atr':float(signed.mean()) if len(signed) else np.nan})
    bucket=pd.DataFrame(buckets); elig=bucket[bucket.n_resolved>=30].sort_values('score_pct'); h4=bool(len(elig)>=2 and np.all(np.diff(elig.accuracy.to_numpy(float))>=-1e-12))

    components=[]; component_year=[]
    for c in COMPONENTS:
        for present in [True,False]:
            g=q[q[c].eq(present)]; r=g[g.target_dir.isin([-1,1])]
            components.append({'component':c,'present':present,'n_all':len(g),'prevalence':float(len(g)/len(q)) if len(q) else np.nan,'n_resolved':len(r),'accuracy':float((r.D14_CONCORDANCE==r.target_dir).mean()) if len(r) else np.nan,'mean_signed24_atr':float(pd.to_numeric(g.D14_signed24,errors='coerce').mean()) if len(g) else np.nan})
        for year in YEARS:
            gy=q[pd.to_datetime(q.available_time).dt.year.eq(year)]
            a=gy[gy[c]]; b=gy[~gy[c]]; ar=a[a.target_dir.isin([-1,1])]; br=b[b.target_dir.isin([-1,1])]
            component_year.append({'component':c,'year':year,'n_present':len(a),'n_absent':len(b),'accuracy_present':float((ar.D14_CONCORDANCE==ar.target_dir).mean()) if len(ar) else np.nan,'accuracy_absent':float((br.D14_CONCORDANCE==br.target_dir).mean()) if len(br) else np.nan})
    comp=pd.DataFrame(components); compyr=pd.DataFrame(component_year)

    sides=[]
    g50=resolved[resolved.HIGH50]
    for sign,name in [(1,'BULL'),(-1,'BEAR')]:
        s=g50[g50.D14_CONCORDANCE.eq(sign)]
        sides.append({'side':name,'n':len(s),'accuracy':float((s.D14_CONCORDANCE==s.target_dir).mean()) if len(s) else np.nan,'mean_score_pct':float(s.SETUP_CONFIRMATION_PCT.mean()) if len(s) else np.nan})
    side=pd.DataFrame(sides)

    powered_h1=(h1raw['n_hi']>=100 and h1raw['n_lo']>=100); powered_h3=len(hi75)>=60
    passed=sum([h1,h2,h3])
    if h1 and h2 and h3: verdict='SETUP_CONFIRMATION_SUPPORTED_DISCOVERY_ONLY'
    elif h1 and h3 and not h2: verdict='SETUP_CONFIRMATION_DIRECTION_ONLY'
    elif passed in [1,2]: verdict='SETUP_CONFIRMATION_PARTIAL'
    elif not powered_h1 or not powered_h3: verdict='SETUP_CONFIRMATION_UNDERPOWERED'
    else: verdict='SETUP_CONFIRMATION_NOT_SUPPORTED'

    bucket.to_csv(out/'score_buckets.csv',index=False); comp.to_csv(out/'component_diagnostics.csv',index=False); compyr.to_csv(out/'component_year_diagnostics.csv',index=False); side.to_csv(out/'side_symmetry.csv',index=False); h1yrs.to_csv(out/'h1_year_transfer.csv',index=False); h2yrs.to_csv(out/'h2_year_transfer.csv',index=False)
    q[['available_time','close','atr14','bias','D14_CONCORDANCE','SETUP_CONFIRMATION_PCT']+COMPONENTS+['resolution','target_dir','D14_signed24']].to_csv(out/'confirmation_events.csv',index=False)
    summary={'lab':LAB,'verdict':verdict,'population':int(len(q)),'resolved_n':int(len(resolved)),'score_mean':float(q.SETUP_CONFIRMATION_PCT.mean()),'score_median':float(q.SETUP_CONFIRMATION_PCT.median()),'h1':h1raw|{'transfer':h1_transfer,'pass':h1},'h2':h2raw|{'transfer':h2_transfer,'pass':h2},'h3':h3raw|{'n_high75':int(len(hi75)),'pass':h3},'h4_monotonic':h4}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    report=[f'# {LAB}','',f'**Verdict: {verdict}**','',f'- Population PULLBACK+G1+D14: **{len(q):,}**',f'- Exact resolved ±1 ATR: **{len(resolved):,}**',f'- Mean confirmation: **{summary["score_mean"]:.1f}%**; median **{summary["score_median"]:.0f}%**','', '## Primary gates','', '| Gate | Effect | 95% CI | N | Pass |','|---|---:|---:|---:|---|',f'| H1 >=50 vs <50 direction accuracy premium | {h1raw["observed"]:+.3f} | [{h1raw["ci_lo"]:+.3f}, {h1raw["ci_hi"]:+.3f}] | {h1raw["n_hi"]}/{h1raw["n_lo"]} | {"PASS" if h1 else "FAIL"} |',f'| H2 >=50 vs <50 signed24 premium | {h2raw["observed"]:+.3f} ATR | [{h2raw["ci_lo"]:+.3f}, {h2raw["ci_hi"]:+.3f}] | {h2raw["n_hi"]}/{h2raw["n_lo"]} | {"PASS" if h2 else "FAIL"} |',f'| H3 >=75 absolute accuracy | {h3raw["observed"]:.3f} | [{h3raw["ci_lo"]:+.3f}, {h3raw["ci_hi"]:+.3f}] | {len(hi75)} | {"PASS" if h3 else "FAIL"} |',f'| H4 bucket monotonicity | — | — | eligible buckets={len(elig)} | {"PASS" if h4 else "FAIL"} |','', '## Score buckets','',bucket.to_markdown(index=False),'','## Component diagnostics','',comp.to_markdown(index=False),'','## Side symmetry at >=50%','',side.to_markdown(index=False),'','## Constraints','','- Equal 25% weights were frozen before outcomes.','- This percentage is setup evidence coverage, NOT probability of profit.','- Reused history => any positive result remains DISCOVERY_ONLY.','- No automated entry/risk claim.']
    (out/'REPORT.md').write_text('\n'.join(report))
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
