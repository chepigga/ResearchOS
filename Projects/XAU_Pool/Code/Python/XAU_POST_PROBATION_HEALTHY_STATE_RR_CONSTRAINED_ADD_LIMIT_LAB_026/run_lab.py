#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_POST_PROBATION_HEALTHY_STATE_RR_CONSTRAINED_ADD_LIMIT_LAB_026'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
LAB025_EVENTS_SHA='c74d2426019874b431e45e7560d32855300645c5246162a8217cc8f540ac4fea'
LAB025_RUNNER_SHA='18275ae3e4638b9d3714c96cc2f311b89df7daf500c44fbb3870c152f5b88619'
HOLDOUT=pd.Timestamp('2025-07-01')
RISK_ATR=0.50; COMMISSION_PRICE=0.05; HOLD_MIN=60; BOOT_N=4000; SEED=20260825
STARTER=0.25; ADD_RISK=0.75; PROBATION=5; PRIMARY_RR=1.5; PRIMARY_EXPIRY=5

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load_module(path:Path,name='lab025'):
    sp=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def load_prices(path:Path):
    cols=['time','open','high','low','close','ask_open','ask_high','ask_low','ask_close']
    df=pd.read_csv(path,sep=';',usecols=cols)
    df['time']=pd.to_datetime(df.time,format='%Y.%m.%d %H:%M')
    return df

def rr_limit(sl,tp,d,rr):
    ysl=d*sl; ytp=d*tp; ylim=(ytp+rr*ysl)/(1.0+rr); return d*ylim

def simulate_rr_add(events,df,rr=1.5,expiry=5,target=1.5,prefix='rr26'):
    y=events.copy()
    times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    bo=df.open.to_numpy(float); bh=df.high.to_numpy(float); bl=df.low.to_numpy(float); bc=df.close.to_numpy(float)
    ao=df.ask_open.to_numpy(float); ah=df.ask_high.to_numpy(float); al=df.ask_low.to_numpy(float); ac=df.ask_close.to_numpy(float)
    rows=[]; violations=0
    for r in y.itertuples(index=False):
        ei=int(r.baseline_entry_i); d=int(r.dir); a=float(r.atr0); e=float(r.baseline_entry); orig=RISK_ATR*a
        sl=e-d*orig; tp=e+d*target*orig; end_t=times[ei]+HOLD_MIN
        if not bool(r.primary_promoted):
            gross=float(r.primary_gross_R); net=float(r.primary_net_R); stress=float(r.primary_stress10_R)
            outcome=str(r.primary_outcome); ex=pd.Timestamp(r.primary_exit_time) if pd.notna(r.primary_exit_time) else pd.NaT
            rows.append((gross,net,stress,outcome,ex,False,False,np.nan,np.nan,np.nan,0,STARTER,False))
            continue
        pi=ei+PROBATION
        if pi>=len(df) or times[pi]!=times[ei]+PROBATION:
            violations+=1
            rows.append((np.nan,np.nan,np.nan,'CLOCK_FAIL',pd.NaT,False,False,np.nan,np.nan,np.nan,0,STARTER,False)); continue
        limit=rr_limit(sl,tp,d,rr)
        place_quote=ao[pi] if d>0 else bo[pi]
        def realized_rr(px):
            risk=d*(px-sl); rew=d*(tp-px); return rew/risk if risk>0 else np.nan
        filled=False; fill_i=-1; fill_px=np.nan; fill_latency=np.nan
        starter_open=True; add_open=False; starter_gross=0.0; add_gross=0.0; outcome_parts=[]; last=pi
        for k in range(expiry):
            j=pi+k
            if j>=len(df) or times[j]!=times[pi]+k or times[j]>end_t:
                break
            last=j
            starter_sl=(bl[j]<=sl) if d>0 else (ah[j]>=sl)
            starter_tp=(bh[j]>=tp) if d>0 else (al[j]<=tp)
            if starter_sl:
                starter_gross=-STARTER; starter_open=False; outcome_parts.append('STARTER_SL'); break
            if starter_tp:
                starter_gross=STARTER*target; starter_open=False; outcome_parts.append('STARTER_TP'); break
            if not filled:
                if k==0 and ((d>0 and place_quote<=limit) or (d<0 and place_quote>=limit)):
                    px=place_quote
                    if np.isfinite(realized_rr(px)) and realized_rr(px)>=rr-1e-12:
                        filled=True; fill_i=j; fill_px=float(px); fill_latency=0
                else:
                    touched=(al[j]<=limit) if d>0 else (bh[j]>=limit)
                    if touched:
                        filled=True; fill_i=j; fill_px=float(limit); fill_latency=k
                if filled:
                    add_open=True
                    add_sl=(bl[j]<=sl) if d>0 else (ah[j]>=sl)
                    if add_sl:
                        add_gross=-ADD_RISK; add_open=False; outcome_parts.append('ADD_SL_FILLBAR')
                        starter_gross=-STARTER; starter_open=False; outcome_parts.append('STARTER_SL'); break
        start_after=max(pi+expiry, (fill_i+1 if filled else pi+expiry))
        if starter_open or add_open:
            for j in range(start_after,len(df)):
                if times[j]>end_t: break
                last=j
                slhit=(bl[j]<=sl) if d>0 else (ah[j]>=sl)
                tphit=(bh[j]>=tp) if d>0 else (al[j]<=tp)
                if slhit:
                    if starter_open: starter_gross=-STARTER; starter_open=False; outcome_parts.append('STARTER_SL')
                    if add_open: add_gross=-ADD_RISK; add_open=False; outcome_parts.append('ADD_SL')
                    break
                if tphit:
                    if starter_open: starter_gross=STARTER*target; starter_open=False; outcome_parts.append('STARTER_TP')
                    if add_open:
                        addrisk=d*(fill_px-sl)
                        factor=ADD_RISK*orig/addrisk
                        add_gross=factor*d*(tp-fill_px)/orig; add_open=False; outcome_parts.append('ADD_TP')
                    break
        exitp=bc[last] if d>0 else ac[last]
        if starter_open:
            starter_gross=STARTER*d*(exitp-e)/orig; starter_open=False; outcome_parts.append('STARTER_TIME')
        add_factor=0.0
        if filled:
            addrisk=d*(fill_px-sl)
            add_factor=ADD_RISK*orig/addrisk if addrisk>0 else 0.0
            if add_open:
                add_gross=add_factor*d*(exitp-fill_px)/orig; add_open=False; outcome_parts.append('ADD_TIME')
        gross=float(starter_gross+add_gross)
        lot_factor=STARTER+add_factor
        comm=COMMISSION_PRICE/orig*lot_factor
        net=float(gross-comm); stress=float(net-0.10/orig*lot_factor)
        ex=df.at[last,'time']
        rrr=realized_rr(fill_px) if filled else np.nan
        risk_used=1.0 if filled else STARTER
        rows.append((gross,net,stress,'+'.join(outcome_parts) if outcome_parts else 'TIME',ex,True,filled,float(limit),float(fill_px) if filled else np.nan,float(rrr) if filled else np.nan,int(fill_latency) if filled else -1,float(risk_used),not filled))
    cols=['gross_R','net_R','stress10_R','outcome','exit_time','healthy','add_filled','add_limit','add_entry','add_rr','fill_latency','risk_budget_used','add_expired']
    for k,c in enumerate(cols): y[f'{prefix}_{c}']=[r[k] for r in rows]
    y[f'{prefix}_promoted']=y[f'{prefix}_add_filled'].astype(bool)
    return y,violations

def bootstrap_pair(df,col_a,col_b,lab025,seed):
    z=lab025.dedupe(df,lab025).copy(); z['diff']=z[col_a]-z[col_b]; z['week']=pd.to_datetime(z.baseline_entry_time).dt.to_period('W-MON').astype(str)
    w=z.groupby('week')['diff'].mean().dropna().to_numpy(float)
    if len(w)<8:return {'n_weeks':len(w),'mean':float(w.mean()) if len(w) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(w,size=len(w),replace=True).mean() for _ in range(BOOT_N)])
    return {'n_weeks':int(len(w)),'mean':float(w.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--lab025-events',type=Path,required=True); ap.add_argument('--lab025-runner',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args()
    out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    if sha256(a.input)!=CANONICAL_SHA: raise RuntimeError('canonical SHA mismatch')
    if sha256(a.lab025_events)!=LAB025_EVENTS_SHA: raise RuntimeError('LAB025 events SHA mismatch')
    if sha256(a.lab025_runner)!=LAB025_RUNNER_SHA: raise RuntimeError('LAB025 runner SHA mismatch')
    lab025=load_module(a.lab025_runner); ev=pd.read_csv(a.lab025_events,compression='gzip',parse_dates=['break_time','baseline_entry_time','primary_exit_time','lifecycle_end_time'])
    df=load_prices(a.input)
    z15,v15=simulate_rr_add(ev,df,PRIMARY_RR,PRIMARY_EXPIRY,1.5,'rr26')
    z20,v20=simulate_rr_add(ev,df,PRIMARY_RR,PRIMARY_EXPIRY,2.0,'rr26_2r')
    for c in [c for c in z20.columns if c.startswith('rr26_2r_')]: z15[c]=z20[c]
    conf=z15[z15.split=='CONFIRMATION'].copy(); disc=z15[z15.split=='DISCOVERY'].copy()
    cs=lab025.build_serial(conf,'rr26',lab025); ds=lab025.build_serial(disc,'rr26',lab025); c2=lab025.build_serial(conf,'rr26_2r',lab025)
    cm=lab025.stats(cs,'rr26'); dm=lab025.stats(ds,'rr26'); c2m=lab025.stats(c2,'rr26_2r')
    mks=lab025.build_serial(conf,'primary',lab025); mkm=lab025.stats(mks,'primary')
    for q in (conf,disc):
        q['full_net_R']=q.baseline_net_R_1p5; q['full_gross_R']=q.baseline_gross_R_1p5; q['full_stress10_R']=q.baseline_stress10_R_1p5; q['full_outcome']=q.baseline_outcome_1p5; q['full_exit_time']=q.baseline_exit_time_1p5; q['full_risk_budget_used']=1.0; q['full_promoted']=False
    fs=lab025.build_serial(conf,'full',lab025); fm=lab025.stats(fs,'full')
    weekly=lab025.bootstrap_week_ev(cs,'rr26',SEED)
    pair_full=bootstrap_pair(conf,'rr26_net_R','baseline_net_R_1p5',lab025,SEED+1)
    pair_mkt=bootstrap_pair(conf,'rr26_net_R','primary_net_R',lab025,SEED+2)
    dq=lab025.dedupe(conf,lab025).copy(); healthy=dq[dq.primary_promoted.astype(bool)].copy(); filled=healthy[healthy.rr26_add_filled.astype(bool)].copy(); unfilled=healthy[~healthy.rr26_add_filled.astype(bool)].copy()
    cohort=[]
    for name,g in [('HEALTHY_ALL',healthy),('ADD_FILLED',filled),('ADD_UNFILLED',unfilled)]:
        cohort.append({'cohort':name,'n':len(g),'baseline_ev':float(g.baseline_net_R_1p5.mean()) if len(g) else np.nan,'lab025_market_promote_ev':float(g.primary_net_R.mean()) if len(g) else np.nan,'lab026_ev':float(g.rr26_net_R.mean()) if len(g) else np.nan,'tp_rate':float(g.rr26_outcome.str.contains('TP').mean()) if len(g) else np.nan,'mean_add_rr':float(g.rr26_add_rr.mean()) if len(g) else np.nan,'median_add_rr':float(g.rr26_add_rr.median()) if len(g) else np.nan,'median_fill_latency':float(g.rr26_fill_latency.replace(-1,np.nan).median()) if len(g) else np.nan})
    cohort=pd.DataFrame(cohort); cohort.to_csv(out/'healthy_add_cohort.csv',index=False)
    if len(filled):
        starter_cf=STARTER*filled.baseline_net_R_1p5; inc=filled.rr26_net_R-starter_cf
        filled_add={'n':len(filled),'combined_ev':float(filled.rr26_net_R.mean()),'starter_cf_ev':float(starter_cf.mean()),'incremental_add_ev':float(inc.mean()),'mean_rr':float(filled.rr26_add_rr.mean()),'median_rr':float(filled.rr26_add_rr.median()),'rr_ge_1p5':float((filled.rr26_add_rr>=1.5-1e-9).mean())}
    else: filled_add={'n':0}
    sens=[]
    for rr in (1.25,1.5,2.0):
        for ex in (3,5,10):
            if rr==PRIMARY_RR and ex==PRIMARY_EXPIRY: zz=z15; vv=v15; pref='rr26'
            else: pref=f's_rr{str(rr).replace(".","p")}_e{ex}'; zz,vv=simulate_rr_add(ev,df,rr,ex,1.5,pref)
            cc=zz[zz.split=='CONFIRMATION'].copy(); ss=lab025.build_serial(cc,pref,lab025); sm=lab025.stats(ss,pref); dd=lab025.dedupe(cc,lab025); hh=dd[dd.primary_promoted.astype(bool)]; fr=float(hh[f'{pref}_add_filled'].mean()) if len(hh) else np.nan
            sens.append({'min_rr':rr,'expiry_min':ex,'fill_rate_healthy':fr,'violations':vv,**sm})
    pd.DataFrame(sens).to_csv(out/'sensitivity.csv',index=False)
    health_select=bool(len(healthy)>0 and float(healthy.baseline_net_R_1p5.mean())>0 and float(healthy.baseline_net_R_1p5.mean())>float(dq[~dq.primary_promoted.astype(bool)].baseline_net_R_1p5.mean()))
    filled_ok=bool(filled_add.get('incremental_add_ev',-9)>0 and filled_add.get('combined_ev',-9)>0)
    gates={'G0_DATA_CAUSALITY':bool(v15==0 and v20==0),'G1_POWER':bool(cm.get('n',0)>=300 and cm.get('trades_per_week',0)>=3),'G2_POSITIVE_ECONOMICS':bool(cm.get('ev',-9)>0 and cm.get('pf',0)>1),'G3_WEEKLY_ROBUSTNESS':bool(weekly['ci95'][0] is not None and weekly['ci95'][0]>0),'G4_RISK_EFFICIENCY':bool(cm.get('risk_efficiency',-9)>0),'G5_HEALTHY_SELECTIVITY':health_select,'G6_FILLED_ADD_ECONOMICS':filled_ok,'G7_BEATS_LAB025_MARKET_PROMOTION':bool(pair_mkt['ci95'][0] is not None and pair_mkt['ci95'][0]>0),'G8_DISCOVERY_TRANSFER':bool(dm.get('ev',-9)>0 and cm.get('ev',-9)>0),'G9_DIRECTION_BREADTH':bool(cm.get('buy_ev',-9)>0 and cm.get('sell_ev',-9)>0),'G10_2R_SURVIVAL':bool(c2m.get('ev',-9)>0),'G11_COST_STRESS':bool(cm.get('stress10_ev',-9)>0),'G12_PROP_DD_PROXY':bool(cm.get('worst_day_R',-99)>-4 and cm.get('max_dd_R',999)<fm.get('max_dd_R',999))}
    if all(gates.values()): status='RR_CONSTRAINED_ADD_LIMIT_EDGE'
    elif gates['G5_HEALTHY_SELECTIVITY'] and gates['G7_BEATS_LAB025_MARKET_PROMOTION']: status='RR_LIMIT_IMPROVES_EXECUTION_BUT_NOT_POSITIVE'
    elif gates['G5_HEALTHY_SELECTIVITY']: status='HEALTH_SIGNAL_PERSISTS_RR_LIMIT_NOT_ENOUGH'
    else: status='NO_RR_CONSTRAINED_ADD_LIMIT_EDGE'
    verdict={'status':status,'gates':gates,'primary_confirmation':cm,'primary_discovery':dm,'confirmation_2R':c2m,'lab025_market_promotion':mkm,'full_immediate':fm,'weekly_ev':weekly,'paired_vs_full':pair_full,'paired_vs_lab025_market':pair_mkt,'filled_add':filled_add,'holdout_opened':False,'causality_violations':int(v15+v20)}
    pd.DataFrame([{'strategy':'LAB026_RR15_ADD_LIMIT','split':'CONFIRMATION',**cm},{'strategy':'LAB026_RR15_ADD_LIMIT','split':'DISCOVERY',**dm},{'strategy':'LAB026_RR15_ADD_LIMIT_2R','split':'CONFIRMATION',**c2m},{'strategy':'LAB025_MARKET_PROMOTE','split':'CONFIRMATION',**mkm},{'strategy':'FULL_IMMEDIATE','split':'CONFIRMATION',**fm}]).to_csv(out/'summary.csv',index=False)
    z15.to_csv(out/'events.csv.gz',index=False,compression='gzip')
    report=f'''# {LAB} — {VERSION} REPORT\n\n**Verdict:** `{status}`  \n**Holdout opened:** `false`\n\n## Primary Confirmation — 25% starter + healthy probation + RR>=1.5 add-limit\n- N **{cm.get('n')}**, trades/week **{cm.get('trades_per_week'):.2f}**\n- EV **{cm.get('ev'):+.4f}R**, PF **{cm.get('pf'):.3f}**, TP **{cm.get('tp_rate'):.2%}**\n- add fill/promotion rate **{cm.get('promotion_rate'):.2%}**, mean risk budget **{cm.get('mean_risk_budget_used'):.3f}R**\n- risk-efficiency **{cm.get('risk_efficiency'):+.4f}**\n- BUY **{cm.get('buy_ev'):+.4f}R**, SELL **{cm.get('sell_ev'):+.4f}R**\n- stress10 **{cm.get('stress10_ev'):+.4f}R**\n- max DD **{cm.get('max_dd_R'):.2f}R**, worst day **{cm.get('worst_day_R'):.2f}R**\n- weekly EV CI **{weekly['ci95']}**\n\n## Comparison\n- FULL_IMMEDIATE EV **{fm.get('ev'):+.4f}R**, PF **{fm.get('pf'):.3f}**\n- LAB025 market-promotion EV **{mkm.get('ev'):+.4f}R**, PF **{mkm.get('pf'):.3f}**\n- LAB026 minus FULL paired weekly **{pair_full['mean']:+.4f}R**, CI **{pair_full['ci95']}**\n- LAB026 minus LAB025 market-promotion paired weekly **{pair_mkt['mean']:+.4f}R**, CI **{pair_mkt['ci95']}**\n\n## Healthy add cohort\n{cohort.to_string(index=False)}\n\n## Filled add economics\n{json.dumps(filled_add,indent=2)}\n\n## Transfer / 2R\n- Discovery EV **{dm.get('ev'):+.4f}R**\n- Confirmation 2R EV **{c2m.get('ev'):+.4f}R**, PF **{c2m.get('pf'):.3f}**\n\n## Frozen gates\n''' + '\n'.join([f'- {k}: **{"PASS" if v else "FAIL"}**' for k,v in gates.items()]) + '\n\nNo sensitivity rescue, no holdout opening, no EA/live authorization.\n'
    (out/'REPORT.md').write_text(report); (out/'verdict.json').write_text(json.dumps(verdict,indent=2,default=str)); (out/'audit.json').write_text(json.dumps({'canonical_sha':sha256(a.input),'lab025_events_sha':sha256(a.lab025_events),'lab025_runner_sha':sha256(a.lab025_runner),'raw_rows':len(df),'events':len(ev),'holdout_opened':False,'causality_violations':int(v15+v20)},indent=2))
    print(json.dumps(verdict,indent=2,default=str))
if __name__=='__main__': main()
