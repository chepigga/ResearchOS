from pathlib import Path
import json, importlib.util, zipfile
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Reuse LAB044 exact frozen minimal-repair replay.
p44=Path(__file__).resolve().parents[1]/'CROWDFADE_V191_MINIMAL_ADVERSE_REPAIR_LAB_044'/'run.py'
spec=importlib.util.spec_from_file_location('lab044',p44)
lab44=importlib.util.module_from_spec(spec); spec.loader.exec_module(lab44)
lab44.DATA=DATA
lab44.lab43.DATA=DATA

def tf_states(ts,C,sec):
    b=(ts//sec)*sec
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]
    en=np.r_[st[1:],len(ts)]
    close=C[en-1]; bt=b[st]
    ema=pd.Series(close).ewm(span=50,adjust=False).mean().to_numpy()
    lag4=pd.Series(ema).shift(4).to_numpy()
    state=np.where((close>ema)&(ema>lag4),1,np.where((close<ema)&(ema<lag4),-1,0)).astype(np.int64)
    return (bt+sec).astype(np.int64),state

def enrich_base(raw,ft,fz,start,end,label):
    p=lab44.lab43.prep(raw,ft,fz,start,end)
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p

    # Exact frozen LAB044 candidate: v191d + freshness45 + adverse0.75 + ExitZ retained.
    trades=lab44.make_df(lab44.sim(*p,lab44.FRESH45_ADV)).copy()
    if len(trades)==0:
        return trades,p

    # Signal-index mapping.
    idx=np.searchsorted(dt5,trades.signal_ts.to_numpy(np.int64))
    idx=np.clip(idx,0,len(dt5)-1)
    exact=dt5[idx]==trades.signal_ts.to_numpy(np.int64)
    if not np.all(exact):
        raise RuntimeError('Signal timestamp mapping failed')

    trades['signal_z']=Z5[idx]
    trades['signal_abs_z']=np.abs(trades.signal_z)
    trades['signal_atr']=A5[idx]
    trades['signal_px']=C5[idx]
    trades['atr_pct']=trades.signal_atr/trades.signal_px

    # H1/H4 causal completed states at signal.
    h1t,h1s=tf_states(ts,C,3600)
    h4t,h4s=tf_states(ts,C,14400)
    h1i=np.searchsorted(h1t,trades.signal_ts.to_numpy(np.int64),'right')-1
    h4i=np.searchsorted(h4t,trades.signal_ts.to_numpy(np.int64),'right')-1
    h1=np.where(h1i>=0,h1s[np.maximum(h1i,0)],0)
    h4=np.where(h4i>=0,h4s[np.maximum(h4i,0)],0)
    trades['h1_state']=h1; trades['h4_state']=h4
    rel=[]
    for s,a,b in zip(trades.side.to_numpy(int),h1,h4):
        if a!=0 and b!=0 and a==b:
            rel.append('ALIGNED_WITH' if s==a else 'ALIGNED_COUNTER')
        else:
            rel.append('MIXED')
    trades['trend_relation']=rel

    # Causal rolling volatility regime using prior 30d of signal-clock ATR%.
    # Quantile thresholds are lagged one M5 decision so current observation does not define its own bucket.
    atrpct=A5/C5
    s=pd.Series(atrpct)
    q33=s.shift(1).rolling(8640,min_periods=2880).quantile(0.33).to_numpy()
    q67=s.shift(1).rolling(8640,min_periods=2880).quantile(0.67).to_numpy()
    vr=[]
    for j in idx:
        if j<0 or j>=len(q33) or not np.isfinite(q33[j]) or not np.isfinite(q67[j]):
            vr.append('UNKNOWN')
        elif atrpct[j]<=q33[j]:
            vr.append('LOW_VOL')
        elif atrpct[j]>=q67[j]:
            vr.append('HIGH_VOL')
        else:
            vr.append('MID_VOL')
    trades['vol_regime']=vr

    # Prior same-side crowd extreme, using only prior completed M5 signal states.
    last_pos=-10**18; last_neg=-10**18
    prev_gap=np.full(len(dt5),np.nan)
    for j,(t,z) in enumerate(zip(dt5,Z5)):
        if z>=1.0:
            if last_pos>-10**17: prev_gap[j]=(t-last_pos)/60.0
            last_pos=t
        elif z<=-1.0:
            if last_neg>-10**17: prev_gap[j]=(t-last_neg)/60.0
            last_neg=t
    trades['mins_since_prior_same_extreme']=prev_gap[idx]
    trades['episode_role']=np.where(
        trades.mins_since_prior_same_extreme.isna() | (trades.mins_since_prior_same_extreme>180),
        'FIRST_OR_RESET','REPEAT_WITHIN_3H')

    # Pre-registered diagnostic buckets. Not optimization thresholds.
    trades['z_bucket']=pd.cut(trades.signal_abs_z,
        bins=[1.0,1.25,1.50,2.0,2.50,np.inf],right=False,
        labels=['1.00-1.25','1.25-1.50','1.50-2.00','2.00-2.50','2.50+'])
    trades['confirm_speed']=pd.cut(trades.confirm_age_min,
        bins=[-np.inf,5,15,30,45.000001],right=True,
        labels=['<=5m','5-15m','15-30m','30-45m'])
    trades['adverse_bucket']=pd.cut(trades.max_adverse_atr,
        bins=[-np.inf,0.15,0.30,0.50,0.750001],right=True,
        labels=['<=0.15','0.15-0.30','0.30-0.50','0.50-0.75'])
    trades['response_bucket']=pd.cut(trades.response_ratio,
        bins=[-np.inf,0.75,1.0,2.0,np.inf],right=False,
        labels=['<0.75','0.75-1.00','1.00-2.00','2.00+'])
    trades['prior_extreme_gap']=pd.cut(trades.mins_since_prior_same_extreme,
        bins=[-np.inf,30,90,180,np.inf],right=True,
        labels=['<=30m','30-90m','90-180m','>180m'])
    trades['z_persistence']=np.abs(trades.confirm_z)/(trades.signal_abs_z+1e-12)
    trades['z_persistence_bucket']=pd.cut(trades.z_persistence,
        bins=[-np.inf,0.50,0.75,1.0,1.50,np.inf],right=False,
        labels=['<0.50','0.50-0.75','0.75-1.00','1.00-1.50','1.50+'])

    trades.to_csv(OUT/f'{label}_enriched_trades.csv',index=False)
    return trades,p

def metric(g):
    return lab44.lab43.metrics(g.R.to_numpy(float))

def one_dim(df,col):
    rows=[]
    for k,g in df.groupby(col,observed=True,dropna=False):
        m=metric(g)
        rows.append({'bucket':str(k),**m})
    return rows

def two_dim(df,a,b):
    rows=[]
    for (x,y),g in df.groupby([a,b],observed=True,dropna=False):
        m=metric(g)
        rows.append({a:str(x),b:str(y),**m})
    return rows

def yearly_consistency(df,col):
    q=df.copy()
    q['year']=pd.to_datetime(q.signal_ts,unit='s',utc=True).dt.year
    rows=[]
    for k,g in q.groupby(col,observed=True,dropna=False):
        yr={str(y):metric(h) for y,h in g.groupby('year')}
        pos=sum(1 for v in yr.values() if v.get('SumR',0)>0)
        rows.append({'bucket':str(k),'positive_years':pos,'years_total':len(yr),'years':yr})
    return rows

def monthly_consistency(df,col):
    q=df.copy()
    q['month']=pd.to_datetime(q.signal_ts,unit='s',utc=True).dt.strftime('%Y-%m')
    rows=[]
    for k,g in q.groupby(col,observed=True,dropna=False):
        mo={str(y):metric(h) for y,h in g.groupby('month')}
        pos=sum(1 for v in mo.values() if v.get('SumR',0)>0)
        rows.append({'bucket':str(k),'positive_months':pos,'months_total':len(mo),'months':mo})
    return rows

def cross_sample_table(h,f,col):
    hd={x['bucket']:x for x in one_dim(h,col)}
    fd={x['bucket']:x for x in one_dim(f,col)}
    keys=sorted(set(hd)|set(fd))
    out=[]
    for k in keys:
        a=hd.get(k,{});b=fd.get(k,{})
        out.append({
          'dimension':col,'bucket':k,
          'hist_N':a.get('N',0),'hist_EV':a.get('EV',np.nan),'hist_PF':a.get('PF',np.nan),'hist_SumR':a.get('SumR',np.nan),
          'fwd_N':b.get('N',0),'fwd_EV':b.get('EV',np.nan),'fwd_PF':b.get('PF',np.nan),'fwd_SumR':b.get('SumR',np.nan),
          'cross_sample_positive_EV':bool(a.get('EV',-1)>0 and b.get('EV',-1)>0)})
    return out

def main():
    ft,fz=lab44.lab43.load_flow()
    hist=lab44.lab43.load_hist()
    sec=lab44.lab43.load_sec()

    h,_=enrich_base(hist,ft,fz,
        int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),'historical')
    f,_=enrich_base(sec,ft,fz,
        int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),'forward')

    dims=['z_bucket','side','confirm_speed','adverse_bucket','response_bucket',
          'trend_relation','vol_regime','episode_role','prior_extreme_gap','z_persistence_bucket']

    result={
      'lab':'CROWDFADE_V191_POSITIVE_SUBPOPULATION_ATTRIBUTION_LAB_045',
      'base_shell':'v191d + freshness45 + max adverse0.75 + ExitZ retained; SL/BE/trail/H6 unchanged',
      'purpose':'Diagnostic attribution only. No new gate is promoted and no thresholds are optimized.',
      'historical_all':metric(h),
      'forward_all':metric(f),
      'dimensions':{},
      'cross_sample':[],
      'interactions':{},
      'limitations':[
        'BTCUSDT only; ETH/SOL transfer not established.',
        '2021-2025 uses 1m OHLC; 2026 Mar-Aug uses second OHLC.',
        '2026 is reused forward-shadow/stress, not pristine OOS.',
        'Bucket boundaries were preregistered for diagnosis and were not tuned inside LAB045.',
        'Multiple diagnostic slices create multiple-comparison risk; a positive bucket is hypothesis-generating only.',
        'Volatility regime uses lagged 30-day rolling ATR% terciles, causal at the signal timestamp.',
        'Trend relation uses completed H1/H4 EMA50 plus 4-bar EMA slope states.',
        'First/repeat uses time since prior same-side |Z|>=1 completed M5 state; reset threshold is 3h.',
        'v191 MT5 is tick/timer-driven; replay is the same common research approximation used by LAB043/044.'
      ]}

    for d in dims:
        result['dimensions'][d]={
          'historical':one_dim(h,d),
          'forward':one_dim(f,d),
          'historical_consistency':yearly_consistency(h,d),
          'forward_consistency':monthly_consistency(f,d)}
        result['cross_sample'] += cross_sample_table(h,f,d)

    # Pre-registered interactions; diagnostic only.
    interactions=[
      ('z_bucket','episode_role'),
      ('trend_relation','episode_role'),
      ('confirm_speed','adverse_bucket'),
      ('response_bucket','trend_relation')]
    for a,b in interactions:
        result['interactions'][f'{a}__x__{b}']={
          'historical':two_dim(h,a,b),
          'forward':two_dim(f,a,b)}

    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    pd.DataFrame(result['cross_sample']).to_csv(OUT/'cross_sample_buckets.csv',index=False)
    for d in dims:
        pd.DataFrame(result['dimensions'][d]['historical']).to_csv(OUT/f'historical_{d}.csv',index=False)
        pd.DataFrame(result['dimensions'][d]['forward']).to_csv(OUT/f'forward_{d}.csv',index=False)

    # Human-readable report with only direct diagnostics, no optimized gate claim.
    lines=['# LAB045 — POSITIVE SUBPOPULATION ATTRIBUTION','',
      'Base shell: **v191d + freshness45 + adverse<=0.75 ATR + ExitZ retained**.',
      '',
      'This LAB is diagnostic only. No new filter/risk rule is promoted from bucket results.',
      '',
      '## Baseline',
      f"- Historical: {lab44.fmt(result['historical_all'])}",
      f"- 2026 shadow: {lab44.fmt(result['forward_all'])}",
      '',
      '## One-dimensional attribution']
    for d in dims:
        lines += ['',f'### {d}','','Historical:']
        for x in result['dimensions'][d]['historical']:
            lines.append(f"- {x['bucket']}: {lab44.fmt(x)}")
        lines += ['','2026 shadow:']
        for x in result['dimensions'][d]['forward']:
            lines.append(f"- {x['bucket']}: {lab44.fmt(x)}")

    lines += ['','## Cross-sample positive-EV buckets']
    positive=[x for x in result['cross_sample'] if x['cross_sample_positive_EV']]
    if positive:
        for x in positive:
            lines.append(f"- {x['dimension']}={x['bucket']}: hist N{x['hist_N']} EV {x['hist_EV']:+.4f} PF {x['hist_PF']:.3f}; 2026 N{x['fwd_N']} EV {x['fwd_EV']:+.4f} PF {x['fwd_PF']:.3f}")
    else:
        lines.append('- None.')

    lines += ['','## Pre-registered interactions']
    for k,v in result['interactions'].items():
        lines += ['',f'### {k}','','Historical:']
        for x in v['historical']: lines.append('- '+json.dumps(x))
        lines += ['','2026:']
        for x in v['forward']: lines.append('- '+json.dumps(x))

    lines += ['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
