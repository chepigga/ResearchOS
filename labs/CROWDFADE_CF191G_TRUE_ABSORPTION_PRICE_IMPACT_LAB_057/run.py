from pathlib import Path
import json, zipfile, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p54=ROOT.parent/'CROWDFADE_CF191G_CAUSAL_REGIME_IMPULSE_MODEL_LAB_054'/'run.py'
sp=importlib.util.spec_from_file_location('lab54',p54)
lab54=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab54)
lab53=lab54.lab53; lab43=lab54.lab43
lab54.DATA=DATA; lab53.DATA=DATA; lab43.DATA=DATA

EXPECT={
    'historical': {'N':5297,'SumR':700.3704107793633},
    'forward_2026': {'N':544,'SumR':35.49784078156513},
}

AGGR_PCTL=0.90
LOW_IMPACT=0.15
TRAIL_BLOCKS=288

def metrics_r(a):
    return lab43.metrics(np.asarray(a,float))

def load_m5_micro():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,4,7,10])
        ot=(pd.to_numeric(q.iloc[:,0],errors='coerce')//1000).astype('Int64')
        close=pd.to_numeric(q.iloc[:,1],errors='coerce')
        quote=pd.to_numeric(q.iloc[:,2],errors='coerce')
        tbq=pd.to_numeric(q.iloc[:,3],errors='coerce')
        x=pd.DataFrame({'open_ts':ot,'close':close,'quote_volume':quote,'taker_buy_quote':tbq}).dropna()
        rows.append(x)
    m1=pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)
    m1['block_end']=((m1.open_ts.astype(np.int64)//300)+1)*300
    g=m1.groupby('block_end',sort=True)
    m5=g.agg(
        close=('close','last'),
        quote_volume=('quote_volume','sum'),
        taker_buy_quote=('taker_buy_quote','sum'),
        bars=('open_ts','count')
    ).reset_index().rename(columns={'block_end':'ts'})
    m5=m5[m5.bars==5].copy().reset_index(drop=True)
    m5['taker_sell_quote']=m5.quote_volume-m5.taker_buy_quote
    m5['delta_notional']=m5.taker_buy_quote-m5.taker_sell_quote
    m5['aggression_mag']=m5.delta_notional.abs()
    m5['median_prev_24h']=m5.aggression_mag.shift(1).rolling(TRAIL_BLOCKS,min_periods=TRAIL_BLOCKS).median()
    return m5

def load_oi():
    return lab54.load_flow_meta()[['ts','oi']].copy()

def asof_idx(ts,q):
    return np.searchsorted(ts,q,'right')-1

def aggr_bucket(p):
    if not np.isfinite(p): return 'NA'
    if p<0.20:return 'P0_20'
    if p<0.40:return 'P20_40'
    if p<0.60:return 'P40_60'
    if p<0.90:return 'P60_90'
    return 'P90_100'

def impact_bucket(x):
    if not np.isfinite(x): return 'NA'
    if x<0.05:return 'I0_05'
    if x<0.15:return 'I05_15'
    if x<0.30:return 'I15_30'
    if x<0.60:return 'I30_60'
    return 'I60_PLUS'

def add_features(df,p,m5,oi):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    ek=df.entry_k.to_numpy(np.int64)
    et=df.entry_ts.to_numpy(np.int64)
    side=df.side.to_numpy(np.int8)
    atr=A5[ek]

    mt=m5.ts.to_numpy(np.int64)
    close=m5.close.to_numpy(float)
    dq=m5.delta_notional.to_numpy(float)
    amag=m5.aggression_mag.to_numpy(float)
    med=m5.median_prev_24h.to_numpy(float)

    cur=asof_idx(mt,et)
    prev=cur-1

    n=len(df)
    delta=np.full(n,np.nan);mag=np.full(n,np.nan);median=np.full(n,np.nan)
    to_med=np.full(n,np.nan);pct=np.full(n,np.nan)
    rawret=np.full(n,np.nan);absimp=np.full(n,np.nan);cfimp=np.full(n,np.nan)
    signed_aggr=np.full(n,np.nan)

    for i,(j,j0,sd,a) in enumerate(zip(cur,prev,side,atr)):
        if j<0 or j0<0 or mt[j]!=et[i] or not np.isfinite(a) or a<=0: continue
        delta[i]=dq[j];mag[i]=amag[j];median[i]=med[j]
        if np.isfinite(med[j]) and med[j]>0:
            to_med[i]=amag[j]/med[j]
        if j>=TRAIL_BLOCKS:
            hist=amag[j-TRAIL_BLOCKS:j]
            hist=hist[np.isfinite(hist)]
            if len(hist)==TRAIL_BLOCKS:
                pct[i]=float(np.mean(hist<=amag[j]))
        r=close[j]-close[j0]
        rawret[i]=r
        absimp[i]=abs(r)/a
        cfimp[i]=sd*r/a
        signed_aggr[i]=sd*dq[j]

    df['delta_notional_5m']=delta
    df['aggression_mag_5m']=mag
    df['rolling_median_aggression_24h']=median
    df['aggression_to_median']=to_med
    df['aggression_percentile']=pct
    df['raw_price_change_5m']=rawret
    df['impact_atr_abs']=absimp
    df['impact_cf_dir']=cfimp
    df['signed_aggression']=signed_aggr
    df['aggression_sign']=np.where(signed_aggr>0,'WITH',np.where(signed_aggr<0,'AGAINST','ZERO'))
    df['aggr_bucket']=[aggr_bucket(x) for x in pct]
    df['impact_bucket']=[impact_bucket(x) for x in absimp]
    df['adverse_absorp']=(df.aggression_percentile>=AGGR_PCTL)&(df.impact_atr_abs<LOW_IMPACT)&(df.signed_aggression>0)
    df['supportive_absorp']=(df.aggression_percentile>=AGGR_PCTL)&(df.impact_atr_abs<LOW_IMPACT)&(df.signed_aggression<0)

    oit=oi.ts.to_numpy(np.int64);oiv=oi.oi.to_numpy(float)
    now=asof_idx(oit,et)
    for mins in [5,15,30]:
        pr=asof_idx(oit,et-mins*60)
        out=np.full(n,np.nan)
        g=(now>=0)&(pr>=0)&(oiv[pr]>0)
        out[g]=oiv[now[g]]/oiv[pr[g]]-1.0
        df[f'oi_ch{mins}']=out
    return df

def build(label,p,m5,oi):
    df=lab54.extract_cf191g_events(p)
    rr,st,side,sk=lab53.sim_cf191g(*p,False)
    if len(df)!=len(rr) or not np.allclose(df.R.to_numpy(float),rr,atol=1e-12,rtol=0):
        raise RuntimeError(f'event parity fail {label}')
    exp=EXPECT[label]
    if len(df)!=exp['N'] or abs(float(df.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'control parity fail {label}: N={len(df)} SumR={df.R.sum()}')
    df=lab54.add_targets(df,p)
    df=add_features(df,p,m5,oi)
    df['period']=label
    df['entry_time']=pd.to_datetime(df.entry_ts,unit='s',utc=True).astype(str)
    return df

def describe(g,period,label):
    m=metrics_r(g.R.to_numpy(float))
    return {
      'period':period,'bucket':label,'N':len(g),
      'EV_R':m.get('EV',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),
      'WR':m.get('WR',np.nan),'MaxDD_R':m.get('MaxDD_R',np.nan),
      'mean_mfe15':float(g.mfe_15m.mean()) if len(g) else np.nan,
      'mean_mae15':float(g.mae_15m.mean()) if len(g) else np.nan,
      'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
      'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
      'mean_ret60':float(g.ret_60m.mean()) if len(g) else np.nan,
      'impulse60_rate':float(g.impulse60.mean()) if len(g) else np.nan,
      'mean_aggression_percentile':float(g.aggression_percentile.mean()) if len(g) else np.nan,
      'mean_aggression_to_median':float(g.aggression_to_median.mean()) if len(g) else np.nan,
      'mean_impact_abs':float(g.impact_atr_abs.mean()) if len(g) else np.nan,
      'mean_impact_cf_dir':float(g.impact_cf_dir.mean()) if len(g) else np.nan,
      'mean_oi_ch5':float(g.oi_ch5.mean()) if len(g) else np.nan,
      'mean_oi_ch15':float(g.oi_ch15.mean()) if len(g) else np.nan,
      'mean_oi_ch30':float(g.oi_ch30.mean()) if len(g) else np.nan,
    }

def map_period(df,period):
    valid=df[df.aggression_percentile.notna()&df.impact_atr_abs.notna()].copy()
    rows=[]
    for sign in ['WITH','AGAINST']:
        s=valid[valid.aggression_sign==sign]
        for ab in ['P0_20','P20_40','P40_60','P60_90','P90_100']:
            for ib in ['I0_05','I05_15','I15_30','I30_60','I60_PLUS']:
                g=s[(s.aggr_bucket==ab)&(s.impact_bucket==ib)]
                if len(g):
                    d=describe(g,period,f'{sign}_{ab}_{ib}')
                    d.update({'aggression_sign':sign,'aggr_bucket':ab,'impact_bucket':ib})
                    rows.append(d)
    return pd.DataFrame(rows)

def main():
    m5=load_m5_micro(); oi=load_oi()
    ft,fz=lab43.load_flow()
    hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))

    dh=build('historical',hist,m5,oi)
    df=build('forward_2026',fwd,m5,oi)
    events=pd.concat([dh,df],ignore_index=True)
    events.to_csv(OUT/'cf191g_true_absorption_events.csv',index=False)

    maps=pd.concat([map_period(dh,'historical'),map_period(df,'forward_2026')],ignore_index=True)
    maps.to_csv(OUT/'true_absorption_map.csv',index=False)

    controls=[];flags=[]
    for period,d in [('historical',dh),('forward_2026',df)]:
        c=describe(d,period,'CONTROL');controls.append(c)
        for name,mask in [('ADVERSE_ABSORPTION',d.adverse_absorp),('SUPPORTIVE_ABSORPTION',d.supportive_absorp)]:
            x=describe(d[mask],period,name)
            x['delta_EV_vs_control']=x['EV_R']-c['EV_R']
            x['delta_PF_vs_control']=x['PF']-c['PF'] if np.isfinite(x['PF']) else np.nan
            x['delta_MFE60_vs_control']=x['mean_mfe60']-c['mean_mfe60']
            x['delta_MAE60_vs_control']=x['mean_mae60']-c['mean_mae60']
            flags.append(x)

    controldf=pd.DataFrame(controls); flagdf=pd.DataFrame(flags)
    controldf.to_csv(OUT/'control_geometry.csv',index=False)
    flagdf.to_csv(OUT/'shadow_flag_results.csv',index=False)

    def get(period,bucket):
        return flagdf[(flagdf.period==period)&(flagdf.bucket==bucket)].iloc[0]
    def ctl(period):
        return controldf[controldf.period==period].iloc[0]

    checks={}
    for period in ['historical','forward_2026']:
        a=get(period,'ADVERSE_ABSORPTION');s=get(period,'SUPPORTIVE_ABSORPTION');c=ctl(period)
        checks[period]={
          'adverse_N':int(a.N),'supportive_N':int(s.N),
          'adverse_EV_below_control':bool(a.EV_R<c.EV_R) if np.isfinite(a.EV_R) else False,
          'adverse_PF_below_control':bool(a.PF<c.PF) if np.isfinite(a.PF) else False,
          'adverse_MFE_lower':bool(a.mean_mfe60<c.mean_mfe60) if np.isfinite(a.mean_mfe60) else False,
          'adverse_MAE_higher':bool(a.mean_mae60>c.mean_mae60) if np.isfinite(a.mean_mae60) else False,
          'supportive_EV_gt_adverse':bool(s.EV_R>a.EV_R) if np.isfinite(s.EV_R) and np.isfinite(a.EV_R) else False,
          'supportive_MFE_gt_adverse':bool(s.mean_mfe60>a.mean_mfe60) if np.isfinite(s.mean_mfe60) and np.isfinite(a.mean_mfe60) else False,
          'supportive_MAE_lt_adverse':bool(s.mean_mae60<a.mean_mae60) if np.isfinite(s.mean_mae60) and np.isfinite(a.mean_mae60) else False,
        }

    mech=(
      checks['historical']['adverse_EV_below_control'] and checks['forward_2026']['adverse_EV_below_control']
      and checks['historical']['adverse_PF_below_control'] and checks['forward_2026']['adverse_PF_below_control']
      and checks['historical']['supportive_EV_gt_adverse'] and checks['forward_2026']['supportive_EV_gt_adverse']
    )

    result={
      'lab':'CROWDFADE_CF191G_TRUE_ABSORPTION_PRICE_IMPACT_LAB_057',
      'thresholds':{'aggression_percentile':AGGR_PCTL,'impact_atr_abs_lt':LOW_IMPACT,'trailing_blocks':TRAIL_BLOCKS},
      'parity':{
        'historical':{'N':len(dh),'SumR':float(dh.R.sum())},
        'forward_2026':{'N':len(df),'SumR':float(df.R.sum())}},
      'checks':checks,
      'mechanism_supported_on_primary_EV_PF_signs':bool(mech),
      'limitations':[
        'Diagnostic only; no stateful skip was tested.',
        'High aggression is absolute quote-notional taker delta relative to prior 24h, not delta ratio.',
        'Passive liquidity is inferred from failed price impact; full order book resting liquidity is not observed.',
        'BTCUSDT only; ETH/SOL transfer not established.',
        '2026 Mar-Aug is reused shadow/stress, not pristine OOS.',
        'Sample size of >=90th percentile + <0.15 ATR flags may be small.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    lines=['# LAB057 — TRUE ABSORPTION: AGGRESSION MAGNITUDE × PRICE IMPACT','',
      'Diagnostic only. No CF191g trading rule was changed.','',
      '## Control parity','',
      f"- 2021–2025: N={len(dh)}, SumR={dh.R.sum():+.6f}",
      f"- 2026 Mar–Aug: N={len(df)}, SumR={df.R.sum():+.6f}",'',
      '## Frozen detector','',
      f"- High aggression: current |quote-notional taker delta| >= causal prior-24h {int(AGGR_PCTL*100)}th percentile.",
      f"- Low impact: |5m price change| / ATR < {LOW_IMPACT:.2f}.",
      '- Adverse: aggression sign WITH CF191g side.',
      '- Supportive: aggression sign AGAINST CF191g side.','',
      '## Control geometry','',controldf.to_markdown(index=False),'',
      '## Shadow flags','',flagdf.to_markdown(index=False),'',
      '## Primary diagnostic checks','',
      json.dumps(checks,indent=2),'',
      f"Mechanism supported on primary EV/PF signs in both periods: **{mech}**",'',
      '## Fixed causal map','',maps.to_markdown(index=False),'',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
