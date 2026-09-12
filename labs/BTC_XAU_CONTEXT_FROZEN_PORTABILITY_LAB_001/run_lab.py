#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

LAB='BTC_XAU_CONTEXT_FROZEN_PORTABILITY_LAB_001'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
LAB13_PATH=ROOT/'labs'/'XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013'/'run_lab.py'
LAB16_PATH=ROOT/'labs'/'XAU_CONTEXT_SETUP_CONFIRMATION_OB_IMBALANCE_LIQUIDITY_PRICE_ACTION_LAB_016'/'run_lab.py'
BTC15_SHA='19acf95a3bb7a868fa1e6c8da8dbc73d4a2f7004b771e394bbee8e6c5b6e58b9'
BOOT_N=5000
SEED=2026091201
COMPONENTS=['OB_CONFIRM','IMBALANCE_CONFIRM','LIQUIDITY_CONFIRM','PRICE_ACTION_CONFIRM']


def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None; spec.loader.exec_module(mod); return mod


def read_btc15_zip(path:Path)->pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        files=[x for x in z.namelist() if x.lower().endswith(('.csv','.txt')) and not x.endswith('/')]
        if not files: raise RuntimeError('No CSV/TXT in btc_15m.zip')
        name=max(files,key=lambda x:z.getinfo(x).file_size)
        with z.open(name) as f:
            raw=pd.read_csv(f,low_memory=False)
        # If archive is headerless Binance kline format, pandas treated first data row as header.
        low=[str(c).strip().lower() for c in raw.columns]
        named=any(x in low for x in ['open','high','low','close','timestamp','time','open_time','datetime','date'])
        if not named:
            with z.open(name) as f:
                raw=pd.read_csv(f,header=None,low_memory=False)
            if raw.shape[1] < 6: raise RuntimeError(f'Unsupported BTC M15 columns={raw.shape[1]}')
            raw=raw.iloc[:,:12]
            cols=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_base','taker_quote','ignore'][:raw.shape[1]]
            raw.columns=cols
    lut={str(c).strip().lower():c for c in raw.columns}
    out=pd.DataFrame()
    def pick(dst,names):
        for n in names:
            if n in lut: out[dst]=raw[lut[n]]; return
    pick('time',['time','timestamp','datetime','date','open_time','opentime'])
    pick('open',['open','o']); pick('high',['high','h']); pick('low',['low','l']); pick('close',['close','c'])
    pick('volume',['volume','vol','tick_volume','base_volume'])
    miss=[c for c in ['time','open','high','low','close'] if c not in out]
    if miss: raise RuntimeError(f'Missing BTC columns {miss}; got={list(raw.columns)}')
    t=out.time
    if pd.api.types.is_numeric_dtype(t):
        v=pd.to_numeric(t,errors='coerce'); med=float(v.dropna().median())
        unit='us' if med>1e14 else ('ms' if med>1e11 else 's')
        out['time']=pd.to_datetime(v,unit=unit,utc=True,errors='coerce').dt.tz_convert(None)
    else:
        out['time']=pd.to_datetime(t,utc=True,errors='coerce').dt.tz_convert(None)
    for c in ['open','high','low','close']:
        out[c]=pd.to_numeric(out[c],errors='coerce')
    out['volume']=pd.to_numeric(out['volume'],errors='coerce') if 'volume' in out else 1.0
    out['volume']=out['volume'].fillna(0.0)
    out=out.dropna(subset=['time','open','high','low','close']).drop_duplicates('time').sort_values('time').reset_index(drop=True)
    return out


def to_h4(m15:pd.DataFrame)->pd.DataFrame:
    return (m15.set_index('time').resample('4h',origin='epoch',label='left',closed='left')
            .agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum')).dropna())


def add_m15_atr(m15:pd.DataFrame)->pd.DataFrame:
    z=m15.set_index('time').copy().sort_index()
    tr=pd.concat([(z.high-z.low),(z.high-z.close.shift()).abs(),(z.low-z.close.shift()).abs()],axis=1).max(axis=1)
    z['atr14_m15']=tr.rolling(14,min_periods=14).mean()
    return z


def exact_first_passage_m15(m15:pd.DataFrame,d:pd.DataFrame,pop:pd.Series)->pd.DataFrame:
    mt=m15.index.to_numpy(dtype='datetime64[ns]'); mh=m15.high.to_numpy(float); ml=m15.low.to_numpy(float)
    rows=[]
    for idx,r in d.loc[pop].iterrows():
        t0=np.datetime64(pd.Timestamp(r.available_time).to_datetime64(),'ns'); t1=t0+np.timedelta64(8,'h')
        a=int(np.searchsorted(mt,t0,'left')); b=int(np.searchsorted(mt,t1,'left'))
        up=float(r.close+r.atr14); dn=float(r.close-r.atr14); label='NO_BREAKOUT'; direction=0; touch=pd.NaT
        for j in range(a,b):
            hu=mh[j]>=up; hd=ml[j]<=dn
            if hu and hd: label='AMBIGUOUS'; direction=0; touch=pd.Timestamp(mt[j]); break
            if hu: label='BULL_FIRST'; direction=1; touch=pd.Timestamp(mt[j]); break
            if hd: label='BEAR_FIRST'; direction=-1; touch=pd.Timestamp(mt[j]); break
        rows.append({'h4_index':idx,'resolution':label,'target_dir':direction,'touch_time':touch})
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
    z=q[['available_time','D14_CONCORDANCE','correct']].dropna().copy(); bull=z[z.D14_CONCORDANCE.eq(1)]; bear=z[z.D14_CONCORDANCE.eq(-1)]
    obs=float(bull.correct.mean()-bear.correct.mean()) if len(bull) and len(bear) else np.nan
    if not len(bull) or not len(bear): return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n_bull':len(bull),'n_bear':len(bear)}
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


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--btc15-zip',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); p=Path(a.btc15_zip); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    if sha256(p)!=BTC15_SHA: raise RuntimeError(f'btc_15m.zip SHA mismatch: {sha256(p)}')
    lab8=load_module(LAB8_PATH,'btc_lab8'); lab9=load_module(LAB9_PATH,'btc_lab9'); lab10=load_module(LAB10_PATH,'btc_lab10')
    lab13=load_module(LAB13_PATH,'btc_lab13'); lab16=load_module(LAB16_PATH,'btc_lab16')
    m15raw=read_btc15_zip(p); m15=add_m15_atr(m15raw); h4=to_h4(m15raw); router=lab8.load_router_module()
    ctx=router.add_router(h4); ctx=lab8.add_forward_metrics(ctx); ctx=ctx.dropna(subset=['available_time','atr14']).copy()
    allbars,onset=lab8.make_episodes(ctx); d=lab9.add_roles(allbars); d=lab10.add_components_and_candidates(d); d=lab13.add_prediction_candidates(d)
    d['D14_CONCORDANCE']=np.where((d.D1_HTF_BIAS==d.D2_TREND_PRESSURE)&d.D1_HTF_BIAS.ne(0),d.D1_HTF_BIAS,0).astype(int)
    pop=d.regime.eq('PULLBACK')&d.G1_VOL_COMPRESSION.fillna(False)&d.D14_CONCORDANCE.ne(0)
    d=lab16.add_confirmation(d,m15,pop); fp=exact_first_passage_m15(m15,d,pop); d=d.join(fp,how='left')
    q=d.loc[pop].copy(); q['HIGH75']=q.SETUP_CONFIRMATION_PCT.ge(75); q['D14_signed24']=q.D14_CONCORDANCE*pd.to_numeric(q.close_ret_atr_24h,errors='coerce')
    resolved=q[q.target_dir.isin([-1,1])].copy(); resolved['correct']=(resolved.D14_CONCORDANCE==resolved.target_dir).astype(float)
    high=resolved[resolved.HIGH75].copy(); hall=boot_mean(high,'correct',SEED+1)
    h1=bool(hall['n']>=60 and hall['observed']>0.55 and np.isfinite(hall['ci_lo']) and hall['ci_lo']>0.50)
    side=[]; sideboot={}
    for i,(sgn,name) in enumerate([(1,'BULL'),(-1,'BEAR')]):
        g=high[high.D14_CONCORDANCE.eq(sgn)].copy(); b=boot_mean(g,'correct',SEED+10+i); sideboot[name]=b
        follow=q[q.HIGH75&q.D14_CONCORDANCE.eq(sgn)].D14_signed24.dropna()
        side.append({'side':name,'n_resolved':b['n'],'accuracy':b['observed'],'ci_lo':b['ci_lo'],'ci_hi':b['ci_hi'],'n_follow24':len(follow),'mean_signed24_atr':float(follow.mean()) if len(follow) else np.nan})
    sides=pd.DataFrame(side); bull=sideboot['BULL']; bear=sideboot['BEAR']
    h2=bool(bull['n']>=30 and bull['observed']>0.60 and np.isfinite(bull['ci_lo']) and bull['ci_lo']>0.50)
    h3=bool(bear['n']>=25 and bear['observed']>0.55 and np.isfinite(bear['ci_lo']) and bear['ci_lo']>0.50)
    asym=boot_side_diff(high,SEED+20); h4=bool(asym['n_bull']>=25 and asym['n_bear']>=25 and asym['observed']>0 and np.isfinite(asym['ci_lo']) and asym['ci_lo']>0)

    buckets=[]
    for pct in [0,25,50,75,100]:
        g=q[q.SETUP_CONFIRMATION_PCT.eq(pct)]; r=g[g.target_dir.isin([-1,1])].copy(); follow=pd.to_numeric(g.D14_signed24,errors='coerce').dropna()
        buckets.append({'score_pct':pct,'n_all':len(g),'n_resolved':len(r),'accuracy':float((r.D14_CONCORDANCE==r.target_dir).mean()) if len(r) else np.nan,'mean_signed24_atr':float(follow.mean()) if len(follow) else np.nan})
    bucket=pd.DataFrame(buckets)

    comp=[]
    for sgn,name in [(1,'BULL'),(-1,'BEAR')]:
        sr=resolved[resolved.D14_CONCORDANCE.eq(sgn)]
        for c in COMPONENTS:
            a1=sr[sr[c]]; a0=sr[~sr[c]]
            comp.append({'side':name,'component':c,'n_present':len(a1),'n_absent':len(a0),'accuracy_present':float(a1.correct.mean()) if len(a1) else np.nan,'accuracy_absent':float(a0.correct.mean()) if len(a0) else np.nan,'premium':float(a1.correct.mean()-a0.correct.mean()) if len(a1) and len(a0) else np.nan})
    comp=pd.DataFrame(comp)

    years=[]
    for y in sorted(pd.to_datetime(resolved.available_time).dt.year.unique()):
        g=resolved[(pd.to_datetime(resolved.available_time).dt.year==y)&resolved.HIGH75]
        years.append({'year':int(y),'n':len(g),'accuracy':float(g.correct.mean()) if len(g) else np.nan})
    years=pd.DataFrame(years)

    catastrophic=any((sides.n_resolved>=25)&(sides.accuracy<0.45))
    if h1 and (h2 or h3) and not catastrophic: verdict='BTC_PORTABILITY_CONFIRMED'
    elif (h1 or h2 or h3) and not catastrophic: verdict='BTC_PARTIAL_PORTABILITY'
    else: verdict='BTC_PORTABILITY_NOT_SUPPORTED'
    summary={'lab':LAB,'verdict':verdict,'data_sha':sha256(p),'m15_rows':len(m15),'data_start':str(m15.index.min()),'data_end':str(m15.index.max()),'h4_valid_bars':len(allbars),'episodes':len(onset),'population':len(q),'resolved_n':len(resolved),'high75_n':len(high),'h1_high75_all_pass':h1,'high75_accuracy':hall['observed'],'high75_ci_lo':hall['ci_lo'],'high75_ci_hi':hall['ci_hi'],'h2_bull_pass':h2,'bull_high75_accuracy':bull['observed'],'bull_high75_ci_lo':bull['ci_lo'],'bull_high75_n':bull['n'],'h3_bear_pass':h3,'bear_high75_accuracy':bear['observed'],'bear_high75_ci_lo':bear['ci_lo'],'bear_high75_n':bear['n'],'h4_asymmetry_pass':h4,'asymmetry_effect':asym['observed'],'asymmetry_ci_lo':asym['ci_lo'],'asymmetry_ci_hi':asym['ci_hi']}
    pd.DataFrame([summary]).to_csv(out/'summary.csv',index=False); (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    sides.to_csv(out/'side_metrics.csv',index=False); bucket.to_csv(out/'buckets.csv',index=False); comp.to_csv(out/'component_by_side.csv',index=False); years.to_csv(out/'annual_high75.csv',index=False)
    report=[f'# {LAB}',f'**Verdict: {verdict}**','',f'- Data: {summary["data_start"]} → {summary["data_end"]}; M15 rows **{len(m15):,}**.',f'- Frozen BTC population: **{len(q)}**; resolved: **{len(resolved)}**; HIGH75 resolved: **{len(high)}**.','',f'- H1 HIGH75 all: **{hall["observed"]:.3f}**, CI **[{hall["ci_lo"]:.3f}, {hall["ci_hi"]:.3f}]**, N={hall["n"]} — {"PASS" if h1 else "FAIL"}.',f'- H2 BULL HIGH75: **{bull["observed"]:.3f}**, CI **[{bull["ci_lo"]:.3f}, {bull["ci_hi"]:.3f}]**, N={bull["n"]} — {"PASS" if h2 else "FAIL"}.',f'- H3 BEAR HIGH75: **{bear["observed"]:.3f}**, CI **[{bear["ci_lo"]:.3f}, {bear["ci_hi"]:.3f}]**, N={bear["n"]} — {"PASS" if h3 else "FAIL"}.',f'- H4 BULL-BEAR asymmetry: **{asym["observed"]:+.3f}**, CI **[{asym["ci_lo"]:+.3f}, {asym["ci_hi"]:+.3f}]** — {"PASS" if h4 else "FAIL"}.','','## Score buckets',bucket.to_markdown(index=False),'','## Direction',sides.to_markdown(index=False),'','## Components by side',comp.to_markdown(index=False),'','## Annual HIGH75',years.to_markdown(index=False),'','## Boundary','This is a no-retune Binance BTCUSDT portability test. It does not establish FTMO BTCUSD execution parity or profit probability.']
    (out/'REPORT.md').write_text('\n'.join(report))
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
