#!/usr/bin/env python3
from __future__ import annotations

import argparse, io, importlib.util, json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import requests

LAB='BTC_XAU_CONTEXT_FROZEN_PORTABILITY_LONG_HISTORY_LAB_002'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
LAB13_PATH=ROOT/'labs'/'XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013'/'run_lab.py'
LAB16_PATH=ROOT/'labs'/'XAU_CONTEXT_SETUP_CONFIRMATION_OB_IMBALANCE_LIQUIDITY_PRICE_ACTION_LAB_016'/'run_lab.py'
START='2021-01'; END='2026-07'
BOOT_N=5000; SEED=2026091202
COMPONENTS=['OB_CONFIRM','IMBALANCE_CONFIRM','LIQUIDITY_CONFIRM','PRICE_ACTION_CONFIRM']


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None; spec.loader.exec_module(mod); return mod


def fetch_binance_m15()->tuple[pd.DataFrame,list]:
    sess=requests.Session(); sess.headers.update({'User-Agent':'ResearchOS-BTC-context-portability/1.0'})
    frames=[]; missing=[]
    cols=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_base','taker_quote','ignore']
    for p in pd.period_range(START,END,freq='M'):
        ym=str(p)
        url=f'https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-{ym}.zip'
        try:
            r=sess.get(url,timeout=45)
            if r.status_code!=200:
                missing.append({'month':ym,'status':r.status_code}); continue
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                name=z.namelist()[0]
                raw=pd.read_csv(z.open(name),header=None,names=cols,dtype=str)
            ot=pd.to_numeric(raw.open_time,errors='coerce')
            raw=raw[ot.notna()].copy(); ot=ot[ot.notna()]
            if raw.empty:
                missing.append({'month':ym,'status':'empty'}); continue
            med=float(ot.median()); unit='us' if med>1e14 else ('ms' if med>1e11 else 's')
            raw['time']=pd.to_datetime(ot,unit=unit,utc=True,errors='coerce').dt.tz_convert(None)
            for c in ['open','high','low','close','volume']:
                raw[c]=pd.to_numeric(raw[c],errors='coerce')
            frames.append(raw[['time','open','high','low','close','volume']].dropna())
        except Exception as e:
            missing.append({'month':ym,'status':type(e).__name__+':'+str(e)[:120]})
    if not frames: raise RuntimeError(f'No Binance M15 downloaded; missing={missing[:5]}')
    x=pd.concat(frames,ignore_index=True).drop_duplicates('time').sort_values('time').reset_index(drop=True)
    return x,missing


def add_m15_atr(x:pd.DataFrame)->pd.DataFrame:
    z=x.set_index('time').sort_index().copy()
    tr=pd.concat([(z.high-z.low),(z.high-z.close.shift()).abs(),(z.low-z.close.shift()).abs()],axis=1).max(axis=1)
    z['atr14_m15']=tr.rolling(14,min_periods=14).mean()
    return z


def to_h4(x:pd.DataFrame)->pd.DataFrame:
    return (x.set_index('time').sort_index().resample('4h',origin='epoch',label='left',closed='left')
            .agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum')).dropna())


def exact_first_passage_m15(m15:pd.DataFrame,d:pd.DataFrame,pop:pd.Series)->pd.DataFrame:
    mt=m15.index.to_numpy(dtype='datetime64[ns]'); mh=m15.high.to_numpy(float); ml=m15.low.to_numpy(float)
    rows=[]
    for idx,r in d.loc[pop].iterrows():
        t0=np.datetime64(pd.Timestamp(r.available_time).to_datetime64(),'ns'); t1=t0+np.timedelta64(8,'h')
        a=int(np.searchsorted(mt,t0,'left')); b=int(np.searchsorted(mt,t1,'left'))
        up=float(r.close+r.atr14); dn=float(r.close-r.atr14)
        label='NO_BREAKOUT'; direction=0; touch=pd.NaT
        for j in range(a,min(b,len(mt))):
            hu=mh[j]>=up; hd=ml[j]<=dn
            if hu and hd: label='AMBIGUOUS'; touch=pd.Timestamp(mt[j]); break
            if hu: label='BULL_FIRST'; direction=1; touch=pd.Timestamp(mt[j]); break
            if hd: label='BEAR_FIRST'; direction=-1; touch=pd.Timestamp(mt[j]); break
        rows.append({'h4_index':idx,'resolution':label,'target_dir':direction,'touch_time':touch})
    if not rows:
        return pd.DataFrame(columns=['resolution','target_dir','touch_time'],index=pd.Index([],name='h4_index'))
    return pd.DataFrame(rows).set_index('h4_index')


def week_col(s): return pd.to_datetime(s).dt.to_period('W-SUN').astype(str)


def boot_mean(q:pd.DataFrame,metric:str,seed:int)->dict:
    z=q[['available_time',metric]].copy(); z[metric]=pd.to_numeric(z[metric],errors='coerce'); z=z.dropna()
    obs=float(z[metric].mean()) if len(z) else np.nan
    if z.empty:return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n':0,'weeks':0}
    z['week']=week_col(z.available_time); arr=z.groupby('week')[metric].agg(['count','sum']).to_numpy(float)
    rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if s[0]>0: draws.append(s[1]/s[0])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)),'ci_hi':float(np.quantile(dr,.975)),'n':int(len(z)),'weeks':int(m)}


def boot_side_diff(q:pd.DataFrame,seed:int)->dict:
    z=q[['available_time','D14_CONCORDANCE','correct']].dropna().copy()
    bull=z[z.D14_CONCORDANCE.eq(1)]; bear=z[z.D14_CONCORDANCE.eq(-1)]
    obs=float(bull.correct.mean()-bear.correct.mean()) if len(bull) and len(bear) else np.nan
    if not len(bull) or not len(bear):return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n_bull':len(bull),'n_bear':len(bear)}
    z['week']=week_col(z.available_time); stats=[]
    for _,g in z.groupby('week'):
        b=g[g.D14_CONCORDANCE.eq(1)].correct.to_numpy(float); s=g[g.D14_CONCORDANCE.eq(-1)].correct.to_numpy(float)
        stats.append([len(b),np.nansum(b),len(s),np.nansum(s)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        x=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0 and x[2]>0: draws.append(x[1]/x[0]-x[3]/x[2])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)) if len(dr) else np.nan,'ci_hi':float(np.quantile(dr,.975)) if len(dr) else np.nan,'n_bull':int(len(bull)),'n_bear':int(len(bear))}


def exact_composition(row)->str:
    vals=[bool(row[c]) for c in COMPONENTS]
    n=sum(vals)
    if n==4:return 'ALL4'
    if n!=3:return f'{n}OF4'
    return 'NO_'+COMPONENTS[vals.index(False)].replace('_CONFIRM','').replace('PRICE_ACTION','PRICE_ACTION')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    lab8=load_module(LAB8_PATH,'btc2_lab8'); lab9=load_module(LAB9_PATH,'btc2_lab9'); lab10=load_module(LAB10_PATH,'btc2_lab10'); lab13=load_module(LAB13_PATH,'btc2_lab13'); lab16=load_module(LAB16_PATH,'btc2_lab16')
    m15raw,missing=fetch_binance_m15(); expected=len(pd.period_range(START,END,freq='M'))
    m15=add_m15_atr(m15raw); h4=to_h4(m15raw); router=lab8.load_router_module()
    ctx=router.add_router(h4); ctx=lab8.add_forward_metrics(ctx); ctx=ctx.dropna(subset=['available_time','atr14']).copy(); allbars,onset=lab8.make_episodes(ctx)
    d=lab9.add_roles(allbars); d=lab10.add_components_and_candidates(d); d=lab13.add_prediction_candidates(d)
    d['D14_CONCORDANCE']=np.where((d.D1_HTF_BIAS==d.D2_TREND_PRESSURE)&d.D1_HTF_BIAS.ne(0),d.D1_HTF_BIAS,0).astype(int)
    pull=d.regime.eq('PULLBACK'); g1=d.G1_VOL_COMPRESSION.fillna(False); d14=d.D14_CONCORDANCE.ne(0); pop=pull&g1&d14
    gates={'h4_ready':int(len(d)),'episodes':int(len(onset)),'pullback':int(pull.sum()),'g1':int(g1.sum()),'d14':int(d14.sum()),'pullback_g1':int((pull&g1).sum()),'pullback_d14':int((pull&d14).sum()),'g1_d14':int((g1&d14).sum()),'population':int(pop.sum())}
    d=lab16.add_confirmation(d,m15,pop); fp=exact_first_passage_m15(m15,d,pop); d=d.join(fp,how='left')
    q=d.loc[pop].copy(); q['HIGH75']=q.SETUP_CONFIRMATION_PCT.ge(75); q['D14_signed24']=q.D14_CONCORDANCE*pd.to_numeric(q.close_ret_atr_24h,errors='coerce')
    resolved=q[q.target_dir.isin([-1,1])].copy(); resolved['correct']=(resolved.D14_CONCORDANCE==resolved.target_dir).astype(float); high=resolved[resolved.HIGH75].copy()
    hall=boot_mean(high,'correct',SEED+1); h1=bool(hall['n']>=60 and hall['observed']>0.55 and np.isfinite(hall['ci_lo']) and hall['ci_lo']>0.50)
    side_rows=[]; sb={}
    for i,(sgn,name) in enumerate([(1,'BULL'),(-1,'BEAR')]):
        r=high[high.D14_CONCORDANCE.eq(sgn)].copy(); b=boot_mean(r,'correct',SEED+10+i); sb[name]=b
        f=q[q.HIGH75&q.D14_CONCORDANCE.eq(sgn)].D14_signed24.dropna()
        side_rows.append({'side':name,'n_resolved':b['n'],'accuracy':b['observed'],'ci_lo':b['ci_lo'],'ci_hi':b['ci_hi'],'n_follow24':len(f),'mean_signed24_atr':float(f.mean()) if len(f) else np.nan})
    sides=pd.DataFrame(side_rows); bull=sb['BULL']; bear=sb['BEAR']
    h2=bool(bull['n']>=30 and bull['observed']>0.60 and np.isfinite(bull['ci_lo']) and bull['ci_lo']>0.50)
    h3=bool(bear['n']>=25 and bear['observed']>0.55 and np.isfinite(bear['ci_lo']) and bear['ci_lo']>0.50)
    asym=boot_side_diff(high,SEED+20); h4=bool(asym['n_bull']>=25 and asym['n_bear']>=25 and asym['observed']>0 and np.isfinite(asym['ci_lo']) and asym['ci_lo']>0)

    buckets=[]
    for pct in [0,25,50,75,100]:
        g=q[q.SETUP_CONFIRMATION_PCT.eq(pct)]; r=g[g.target_dir.isin([-1,1])]; f=pd.to_numeric(g.D14_signed24,errors='coerce').dropna()
        buckets.append({'score_pct':pct,'n_all':len(g),'n_resolved':len(r),'accuracy':float((r.D14_CONCORDANCE==r.target_dir).mean()) if len(r) else np.nan,'mean_signed24_atr':float(f.mean()) if len(f) else np.nan})
    buckets=pd.DataFrame(buckets)

    comp=[]
    for sgn,name in [(1,'BULL'),(-1,'BEAR')]:
        sr=resolved[resolved.D14_CONCORDANCE.eq(sgn)]
        for c in COMPONENTS:
            a1=sr[sr[c]]; a0=sr[~sr[c]]
            comp.append({'side':name,'component':c,'n_present':len(a1),'n_absent':len(a0),'accuracy_present':float(a1.correct.mean()) if len(a1) else np.nan,'accuracy_absent':float(a0.correct.mean()) if len(a0) else np.nan,'premium':float(a1.correct.mean()-a0.correct.mean()) if len(a1) and len(a0) else np.nan})
    comp=pd.DataFrame(comp)

    comps=[]
    if len(high):
        hh=high.copy(); hh['composition']=hh.apply(exact_composition,axis=1)
        for side in ['ALL','BULL','BEAR']:
            z=hh if side=='ALL' else hh[hh.D14_CONCORDANCE.eq(1 if side=='BULL' else -1)]
            for k,g in z.groupby('composition'):
                comps.append({'side':side,'composition':k,'n_resolved':len(g),'accuracy':float(g.correct.mean())})
    comps=pd.DataFrame(comps,columns=['side','composition','n_resolved','accuracy'])

    annual=[]
    years=pd.to_datetime(resolved.available_time).dt.year if len(resolved) else pd.Series([],dtype=int)
    for y in range(2021,2027):
        g=resolved[(years==y)&resolved.HIGH75] if len(resolved) else resolved
        annual.append({'year':y,'n_high75':len(g),'accuracy':float(g.correct.mean()) if len(g) else np.nan,'bull_n':int((g.D14_CONCORDANCE==1).sum()) if len(g) else 0,'bear_n':int((g.D14_CONCORDANCE==-1).sum()) if len(g) else 0})
    annual=pd.DataFrame(annual)

    data_incomplete=(len(missing)>2)
    underpowered=(hall['n']<60 and bull['n']<30 and bear['n']<25)
    catastrophic=bool(((sides.n_resolved>=25)&(sides.accuracy<0.45)).any()) if len(sides) else False
    if data_incomplete: verdict='DATA_INCOMPLETE'
    elif underpowered: verdict='BTC_PORTABILITY_UNDERPOWERED'
    elif h1 and (h2 or h3) and not catastrophic: verdict='BTC_PORTABILITY_CONFIRMED'
    elif (h1 or h2 or h3) and not catastrophic: verdict='BTC_PARTIAL_PORTABILITY'
    else: verdict='BTC_PORTABILITY_NOT_SUPPORTED'

    summary={'lab':LAB,'verdict':verdict,'fixed_start':START,'fixed_end':END,'expected_months':expected,'missing_months':missing,'m15_rows':len(m15),'data_start':str(m15.index.min()),'data_end':str(m15.index.max()),**gates,'resolved_n':len(resolved),'high75_n':len(high),'h1_pass':h1,'high75_accuracy':hall['observed'],'high75_ci_lo':hall['ci_lo'],'high75_ci_hi':hall['ci_hi'],'h2_bull_pass':h2,'bull_high75_n':bull['n'],'bull_high75_accuracy':bull['observed'],'bull_high75_ci_lo':bull['ci_lo'],'h3_bear_pass':h3,'bear_high75_n':bear['n'],'bear_high75_accuracy':bear['observed'],'bear_high75_ci_lo':bear['ci_lo'],'h4_asymmetry_pass':h4,'asymmetry_effect':asym['observed'],'asymmetry_ci_lo':asym['ci_lo'],'asymmetry_ci_hi':asym['ci_hi']}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str)); pd.DataFrame([summary]).to_csv(out/'summary.csv',index=False)
    buckets.to_csv(out/'buckets.csv',index=False); sides.to_csv(out/'side_metrics.csv',index=False); comp.to_csv(out/'component_by_side.csv',index=False); comps.to_csv(out/'compositions.csv',index=False); annual.to_csv(out/'annual_high75.csv',index=False); pd.DataFrame([gates]).to_csv(out/'gate_counts.csv',index=False); pd.DataFrame(missing).to_csv(out/'missing_months.csv',index=False)

    report=[f'# {LAB}',f'**Verdict: {verdict}**','',f'- Fixed Binance USD-M BTCUSDT M15 history: **{summary["data_start"]} → {summary["data_end"]}**; rows **{len(m15):,}**; missing months **{len(missing)}**.',f'- H4 ready bars: **{gates["h4_ready"]:,}**; episodes **{gates["episodes"]:,}**; frozen population **{gates["population"]:,}**; resolved **{len(resolved):,}**; HIGH75 resolved **{len(high):,}**.','',f'- H1 HIGH75 overall: **{hall["observed"]:.3f}**, 95% CI **[{hall["ci_lo"]:.3f}, {hall["ci_hi"]:.3f}]**, N={hall["n"]} — {"PASS" if h1 else "FAIL"}.',f'- H2 BULL HIGH75: **{bull["observed"]:.3f}**, CI **[{bull["ci_lo"]:.3f}, {bull["ci_hi"]:.3f}]**, N={bull["n"]} — {"PASS" if h2 else "FAIL"}.',f'- H3 BEAR HIGH75: **{bear["observed"]:.3f}**, CI **[{bear["ci_lo"]:.3f}, {bear["ci_hi"]:.3f}]**, N={bear["n"]} — {"PASS" if h3 else "FAIL"}.',f'- H4 BULL-BEAR gap: **{asym["observed"]:+.3f}**, CI **[{asym["ci_lo"]:+.3f}, {asym["ci_hi"]:+.3f}]** — {"PASS" if h4 else "FAIL"}.','','## Frozen gate counts',pd.DataFrame([gates]).to_markdown(index=False),'','## Evidence buckets',buckets.to_markdown(index=False),'','## Side metrics',sides.to_markdown(index=False),'','## Component value by side',comp.to_markdown(index=False),'','## HIGH75 exact compositions',comps.to_markdown(index=False) if len(comps) else 'No HIGH75 compositions.','','## Calendar-year HIGH75',annual.to_markdown(index=False),'','## Missing months',pd.DataFrame(missing).to_markdown(index=False) if missing else 'None.','','## Boundary','No retuning. This is direction/confirmation portability only, not P(profitable trade), RR economics, fees, funding, slippage, or FTMO BTCUSD parity.']
    (out/'REPORT.md').write_text('\n'.join(report)); print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
