#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_CAUSAL_CONTEXT_ROUTER_ABLATION_LAB_001'
SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
BOOT_N=2500
SEED=2026090901


def sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def find_col(df,names):
    lut={c.lower():c for c in df.columns}
    for n in names:
        if n.lower() in lut:return lut[n.lower()]
    return None


def load_m1(path:Path):
    df=pd.read_csv(path)
    aliases={
      'time':['time','timestamp','datetime','date_time','<date>'],
      'open':['open','bid_open','<open>'],'high':['high','bid_high','<high>'],
      'low':['low','bid_low','<low>'],'close':['close','bid_close','<close>'],
      'volume':['tick_volume','tickvolume','tick_vol','ticks','volume','<tickvol>']}
    out=pd.DataFrame()
    for dst,names in aliases.items():
        c=find_col(df,names)
        if c is not None:out[dst]=df[c]
    miss=[c for c in ['time','open','high','low','close'] if c not in out]
    if miss:raise ValueError(f'Missing native columns {miss}; got={list(df.columns)}')
    out['time']=pd.to_datetime(out.time,errors='coerce')
    for c in out.columns:
        if c!='time':out[c]=pd.to_numeric(out[c],errors='coerce')
    if 'volume' not in out:out['volume']=1.0
    out=out.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time',keep='last')
    return out.reset_index(drop=True)


def wilder(s,n):return s.ewm(alpha=1.0/n,adjust=False,min_periods=n).mean()


def h4_frame(m1):
    x=m1.set_index('time').sort_index()
    return x.resample('4h',origin='epoch',label='left',closed='left').agg(
      open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum')).dropna().copy()


def indicators(d):
    d=d.copy();pc=d.close.shift(1)
    tr=pd.concat([(d.high-d.low).abs(),(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1)
    d['atr14']=wilder(tr,14);d['atr_med50']=d.atr14.rolling(50,min_periods=25).median();d['atr_ratio']=d.atr14/d.atr_med50
    for n in [20,50,200]:d[f'ema{n}']=d.close.ewm(span=n,adjust=False,min_periods=n).mean()
    d['slope50_atr']=(d.ema50-d.ema50.shift(3))/d.atr14.replace(0,np.nan)
    delta=d.close.diff();gain=delta.clip(lower=0);loss=(-delta).clip(lower=0)
    rs=wilder(gain,14)/wilder(loss,14).replace(0,np.nan);d['rsi14']=100-100/(1+rs)
    up=d.high.diff();dn=-d.low.diff()
    pdm=pd.Series(np.where((up>dn)&(up>0),up,0.0),index=d.index);mdm=pd.Series(np.where((dn>up)&(dn>0),dn,0.0),index=d.index)
    pdi=100*wilder(pdm,14)/d.atr14.replace(0,np.nan);mdi=100*wilder(mdm,14)/d.atr14.replace(0,np.nan)
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan);d['adx14']=wilder(dx,14)
    d['prior_hi20']=d.high.rolling(20,min_periods=20).max().shift(1);d['prior_lo20']=d.low.rolling(20,min_periods=20).min().shift(1)
    d['breakout']=(d.close>d.prior_hi20)|(d.close<d.prior_lo20)
    d['sweep']=((d.high>d.prior_hi20)&(d.close<d.prior_hi20))|((d.low<d.prior_lo20)&(d.close>d.prior_lo20))
    r24=d.high.rolling(24,min_periods=24).max()-d.low.rolling(24,min_periods=24).min()
    d['range24_ratio']=r24/r24.rolling(100,min_periods=50).median().replace(0,np.nan)
    em=pd.concat([d.ema20,d.ema50,d.ema200],axis=1)
    d['ema_spread_atr']=(em.max(axis=1)-em.min(axis=1))/d.atr14.replace(0,np.nan)
    d['dist20_atr']=(d.close-d.ema20).abs()/d.atr14.replace(0,np.nan);d['dist50_atr']=(d.close-d.ema50).abs()/d.atr14.replace(0,np.nan)
    d['relvol20']=d.volume/d.volume.rolling(20,min_periods=10).median().replace(0,np.nan)
    cr=(d.high-d.low).replace(0,np.nan);upper=d.high-pd.concat([d.open,d.close],axis=1).max(axis=1);lower=pd.concat([d.open,d.close],axis=1).min(axis=1)-d.low
    d['rejection_wick']=pd.concat([upper,lower],axis=1).max(axis=1)/cr
    d['cross_ema20']=((d.close-d.ema20)*(d.close.shift(1)-d.ema20.shift(1))<0)
    d['stack_up']=(d.ema20>d.ema50)&(d.ema50>d.ema200)&(d.slope50_atr>0)
    d['stack_dn']=(d.ema20<d.ema50)&(d.ema50<d.ema200)&(d.slope50_atr<0)
    d['stack']=d.stack_up|d.stack_dn
    d['bias']=np.select([d.stack_up,d.stack_dn],['BULL','BEAR'],default='NEUTRAL')
    return d


def add_router(h4):
    d=indicators(h4);s=pd.DataFrame(index=d.index)
    exp=25*d['stack'].astype(float)+20*d.breakout.astype(float)+10*(d.atr_ratio>1.05)+10*(d.atr_ratio>1.20)+15*(d.adx14>=20)+10*(d.relvol20>=1.05)+10*(d.dist20_atr>=0.50)
    mind=pd.concat([d.dist20_atr,d.dist50_atr],axis=1).min(axis=1)
    pb=30*d['stack'].astype(float)+25*(mind<=0.65)+15*((mind>0.65)&(mind<=1.0))+15*((d.rsi14>=35)&(d.rsi14<=65))+15*(d.adx14>=18)+15*((~d.breakout)&(d.atr_ratio<=1.40))
    prev=d.rsi14.shift(1);turn=((prev<35)&(d.rsi14>prev))|((prev>65)&(d.rsi14<prev))
    rev=30*d.sweep.astype(float)+25*turn.astype(float)+15*d.cross_ema20.astype(float)+15*(d.adx14<d.adx14.shift(1))+15*(d.rejection_wick>=0.45)
    rng=25*(d.adx14<20)+25*(d.range24_ratio<0.85)+20*(d.ema_spread_atr<1.0)+15*(d.atr_ratio<0.95)+15*(~d['stack'])
    s['EXPANSION']=exp.astype(float).clip(0,100);s['PULLBACK']=pb.astype(float).clip(0,100);s['REVERSAL']=rev.astype(float).clip(0,100);s['RANGE']=rng.astype(float).clip(0,100)
    ready=d[['ema200','atr_ratio','rsi14','adx14','range24_ratio','relvol20']].notna().all(axis=1)
    s=s.where(ready,np.nan);sm=s.rolling(3,min_periods=3).mean()
    states=[];confs=[];cur=None;held=0
    for idx,row in sm.iterrows():
        if row.isna().all():states.append(None);confs.append(np.nan);continue
        scores=row.to_dict()
        if cur is None:cur=max(scores,key=scores.get);held=1
        else:
            ar=d.loc[idx,'atr_ratio'];ar=1.0 if pd.isna(ar) else ar
            if ar<0.80:minhold,gap=4,12
            elif ar>1.35:minhold,gap=2,5
            else:minhold,gap=3,8
            adj=scores.copy();adj[cur]=adj[cur]+5
            ch=max(adj,key=adj.get)
            if ch!=cur and held>=minhold and adj[ch]>adj[cur]+gap:cur=ch;held=1
            else:held+=1
        vals=sorted(scores.values(),reverse=True);states.append(cur);confs.append((vals[0]-vals[1])/100 if len(vals)>1 else np.nan)
    d['regime']=states;d['regime_confidence']=confs
    for c in s.columns:d[f'score_{c.lower()}']=s[c]
    d['available_time']=d.index+pd.Timedelta(hours=4)
    return d


def event_available(p):
    mins=p.tf.map({'M5':5,'M15':15,'H1':60})
    if mins.isna().any():raise ValueError(f'Unknown TFs: {sorted(p.loc[mins.isna(),"tf"].unique())}')
    return p.time+pd.to_timedelta(mins,unit='m')


def metric(q,n0):
    e=q.excess.to_numpy(float);r=q.R.to_numpy(float)
    return {'n':int(len(q)),'retention':float(len(q)/n0) if n0 else np.nan,
      'mean_excess':float(np.mean(e)) if len(e) else np.nan,'median_excess':float(np.median(e)) if len(e) else np.nan,
      'p_excess_pos':float(np.mean(e>0)) if len(e) else np.nan,'mean_R':float(np.mean(r)) if len(r) else np.nan,'p_R_pos':float(np.mean(r>0)) if len(r) else np.nan}


def cluster_boot(q):
    if q.empty:return {'ci_lo':np.nan,'ci_hi':np.nan,'weeks':0}
    z=q.copy();z['week']=z.available_event_time.dt.to_period('W').astype(str)
    groups=[g.excess.to_numpy(float) for _,g in z.groupby('week',sort=True)]
    rng=np.random.default_rng(SEED);vals=[];m=len(groups)
    for _ in range(BOOT_N):
        ix=rng.integers(0,m,m);arr=np.concatenate([groups[i] for i in ix]);vals.append(float(np.mean(arr)))
    return {'ci_lo':float(np.quantile(vals,.025)),'ci_hi':float(np.quantile(vals,.975)),'weeks':m,'draws':BOOT_N}


def transfer_table(df,variants):
    rows=[]
    dims=[('year',['year']),('tf',['tf']),('dir',['dir']),('year_dir',['year','dir'])]
    for v,mask in variants.items():
        q=df[mask]
        for label,cols in dims:
            for key,g in q.groupby(cols,dropna=False):
                key=(key,) if not isinstance(key,tuple) else key
                rec={'variant':v,'dimension':label,'n':len(g),'mean_excess':g.excess.mean(),'mean_R':g.R.mean(),'p_excess_pos':(g.excess>0).mean()}
                for c,k in zip(cols,key):rec[c]=k
                rows.append(rec)
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--m1',required=True);ap.add_argument('--pool',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    m1p=Path(a.m1);poolp=Path(a.pool);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    actual=sha256(m1p)
    if actual!=SHA:raise RuntimeError(f'Canonical SHA mismatch: {actual}')
    m1=load_m1(m1p);ctx=add_router(h4_frame(m1))
    p=pd.read_parquet(poolp);p['time']=pd.to_datetime(p.time,errors='coerce')
    p['R']=pd.to_numeric(p.R,errors='coerce');p['excess']=pd.to_numeric(p.excess,errors='coerce')
    p=p.dropna(subset=['time','tf','dir','R','excess']).sort_values('time').copy();p['available_event_time']=event_available(p);p['year']=p.available_event_time.dt.year
    c=ctx[['available_time','regime','regime_confidence','bias','atr_ratio','adx14','rsi14','score_expansion','score_pullback','score_reversal','score_range']].dropna(subset=['regime']).sort_values('available_time').reset_index()
    j=pd.merge_asof(p.sort_values('available_event_time'),c,left_on='available_event_time',right_on='available_time',direction='backward',allow_exact_matches=True)
    missing=int(j.regime.isna().sum());j=j.dropna(subset=['regime']).copy();n0=len(j)
    primary=j.regime.isin(['PULLBACK','EXPANSION']);strict=primary&(((j.dir>0)&j.bias.eq('BULL'))|((j.dir<0)&j.bias.eq('BEAR')));negative=j.regime.isin(['REVERSAL','RANGE'])
    variants={'BASELINE':pd.Series(True,index=j.index),'PRIMARY_PULLBACK_EXPANSION':primary,'STRICT_DIRECTION_MATCH':strict,'NEG_CONTROL_REVERSAL_RANGE':negative}
    mets={k:metric(j[m],n0) for k,m in variants.items()};boots={k:cluster_boot(j[m]) for k,m in variants.items()}
    reg=[]
    for name,g in j.groupby('regime'):
        x=metric(g,n0);x['regime']=name;reg.append(x)
    pd.DataFrame(reg).to_csv(out/'regime_metrics.csv',index=False)
    tr=transfer_table(j,variants);tr.to_csv(out/'transfer.csv',index=False)
    # compact context counts only; do not persist 266k-row joined stream
    pd.DataFrame([{'regime':r,'bias':b,'n':len(g),'mean_excess':g.excess.mean(),'mean_R':g.R.mean()} for (r,b),g in j.groupby(['regime','bias'])]).to_csv(out/'regime_bias_matrix.csv',index=False)
    b=mets['BASELINE'];pr=mets['PRIMARY_PULLBACK_EXPANSION'];ng=mets['NEG_CONTROL_REVERSAL_RANGE'];bp=boots['PRIMARY_PULLBACK_EXPANSION']
    yr=tr[(tr.variant=='PRIMARY_PULLBACK_EXPANSION')&(tr.dimension=='year')]
    positive_years=int(((yr['n']>=100)&(yr.mean_excess>0)).sum())
    gates={'retention_ge_35pct':pr['retention']>=.35,'mean_excess_gt_baseline':pr['mean_excess']>b['mean_excess'],'mean_excess_gt_negative_control':pr['mean_excess']>ng['mean_excess'],'p_excess_pos_gt_baseline':pr['p_excess_pos']>b['p_excess_pos'],'raw_mean_R_gt_baseline':pr['mean_R']>b['mean_R'],'cluster_ci_low_gt_zero':bp['ci_lo']>0,'positive_excess_in_ge3_years_n100':positive_years>=3}
    verdict='PROMISING_EVENT_ENRICHMENT' if all(gates.values()) else ('MIXED_EVENT_ENRICHMENT' if gates['mean_excess_gt_baseline'] and gates['mean_excess_gt_negative_control'] else 'REJECT_HARD_CONTEXT_GATE')
    summary={'lab':LAB,'verdict':verdict,'status':'REUSED_HISTORY_EVENT_ABLATION_ONLY','native_sha256':actual,'m1_rows':len(m1),'m1_start':str(m1.time.min()),'m1_end':str(m1.time.max()),'pool_rows_finite':len(p),'context_missing_warmup_events':missing,'context_eligible_n':n0,'metrics':mets,'bootstrap':boots,'gates':gates,'positive_primary_years_n100':positive_years}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','', '> Reused-history event enrichment only. Candidate events overlap by design; CumR/PF/DD are not portfolio metrics here. Router weights were copied unchanged from the BTC preregistration.','',f'- Native SHA256: `{actual}`',f'- Native M1 rows: **{len(m1):,}** | {m1.time.min()} → {m1.time.max()}',f'- Finite pool events: **{len(p):,}** | context eligible: **{n0:,}** | warmup excluded: **{missing:,}**','', '## Main ablation','','| Variant | N | Retain | Mean excess | Median excess | P(excess>0) | Mean R | P(R>0) | 95% cluster CI excess |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for k in variants:
        m=mets[k];bo=boots[k];lines.append(f"| {k} | {m['n']:,} | {m['retention']:.1%} | {m['mean_excess']:+.4f}R | {m['median_excess']:+.4f}R | {m['p_excess_pos']:.1%} | {m['mean_R']:+.4f}R | {m['p_R_pos']:.1%} | [{bo['ci_lo']:+.4f}, {bo['ci_hi']:+.4f}] |")
    lines+=['','## Gates']+[f"- {'PASS' if v else 'FAIL'} — `{k}`" for k,v in gates.items()]
    lines+=['',f'- Positive PRIMARY years with >=100 events: **{positive_years}**','', '## Interpretation','PRIMARY is the only preregistered hard-gate test. STRICT_DIRECTION_MATCH is secondary diagnostic only. Passing event enrichment still requires a separately frozen executable-trade OOS test before any EA or risk allocation change.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__':main()
