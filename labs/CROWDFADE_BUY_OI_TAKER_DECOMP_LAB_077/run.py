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

FLAT_PRIMARY=0.0002  # 0.02%
FLAT_SENS=[0.0,0.0001,0.0002,0.0005]

def metrics(a):
    return lab43.metrics(np.asarray(a,float))

def load_flow_raw():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:
            r=pd.read_csv(f,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r['t']=pd.to_datetime(r.create_time,utc=True,errors='coerce')
    r['oi']=pd.to_numeric(r.sum_open_interest,errors='coerce')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['t','oi','ratio']).sort_values('t').drop_duplicates('t')
    r=r[r.oi>0].copy()
    r['ts']=r.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    return r[['ts','oi','ratio']].reset_index(drop=True)

def load_micro():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,5,9])
        ts=(pd.to_numeric(q.iloc[:,0],errors='coerce')//1000).astype('Int64')
        vol=pd.to_numeric(q.iloc[:,1],errors='coerce')
        taker=pd.to_numeric(q.iloc[:,2],errors='coerce')
        x=pd.DataFrame({'ts_start':ts,'volume':vol,'taker_buy':taker}).dropna()
        x['ts']=x.ts_start.astype(np.int64)+60
        rows.append(x[['ts','volume','taker_buy']])
    m=pd.concat(rows,ignore_index=True).sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
    m['delta']=2.0*m.taker_buy-m.volume
    for w in [5,15]:
        sv=m.volume.rolling(w,min_periods=w).sum()
        sd=m.delta.rolling(w,min_periods=w).sum()
        m[f'taker_delta{w}']=sd/sv.replace(0,np.nan)
    return m[['ts','taker_delta5','taker_delta15']]

def asof_idx(src,query):
    return np.searchsorted(src,query,'right')-1

def add_flow_5_15(df,flow,micro):
    et=df.entry_ts.to_numpy(np.int64)
    ft=flow.ts.to_numpy(np.int64); oi=flow.oi.to_numpy(float)
    fi=asof_idx(ft,et)
    for w in [5,15]:
        fp=asof_idx(ft,et-w*60)
        out=np.full(len(df),np.nan)
        g=(fi>=0)&(fp>=0)&(oi[fp]>0)
        out[g]=oi[fi[g]]/oi[fp[g]]-1.0
        df[f'oi_ch{w}']=out
    mt=micro.ts.to_numpy(np.int64); mi=asof_idx(mt,et)
    for w in [5,15]:
        a=micro[f'taker_delta{w}'].to_numpy(float)
        out=np.full(len(df),np.nan); g=mi>=0; out[g]=a[mi[g]]
        df[f'taker_delta{w}']=out
    return df

def add_exit_timing(df,p):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    profit_exit=np.full(len(df),np.nan)
    arm3=np.full(len(df),np.nan)
    arm35=np.full(len(df),np.nan)
    reasons=[]
    for i,r in df.iterrows():
        k=int(r.entry_k); sd=int(r.side); ep=float(C5[k]); a=float(A5[k])
        rr,ex,reason=lab53.manage_cf191g(dt5,H5,L5,C5,k,sd,ep,a)
        reasons.append(int(reason))
        if int(reason)==2:
            profit_exit[i]=(dt5[ex]-dt5[k])/60.0
        end=min(len(dt5)-1,np.searchsorted(dt5,dt5[k]+lab53.HOLD_S,'left'))
        t3=t35=np.nan
        for q in range(k+1,end+1):
            mfe=((H5[q]-ep)/a) if sd>0 else ((ep-L5[q])/a)
            if np.isnan(t3) and mfe>=lab53.G_BE_ARM: t3=(dt5[q]-dt5[k])/60.0
            if np.isnan(t35) and mfe>=lab53.G_TRAIL_ARM: t35=(dt5[q]-dt5[k])/60.0
            if not np.isnan(t3) and not np.isnan(t35): break
        arm3[i]=t3; arm35[i]=t35
    df['exit_reason']=reasons
    df['time_to_profit_exit_min']=profit_exit
    df['time_to_3atr_min']=arm3
    df['time_to_3p5atr_min']=arm35
    return df

def oi_state(x,band):
    if not np.isfinite(x): return 'NA'
    if x < -band: return 'OI_DOWN'
    if x > band: return 'OI_UP'
    return 'OI_FLAT'

def summarize(df,w,band):
    d=df.copy()
    d['oi_state']=d[f'oi_ch{w}'].map(lambda x:oi_state(x,band))
    d['taker_state']=np.where(d[f'taker_delta{w}']>0,'TAKER_STRONG','TAKER_WEAK')
    rows=[]
    for (os,ts),g in d.groupby(['oi_state','taker_state'],dropna=False):
        if os=='NA': continue
        m=metrics(g.R.to_numpy(float))
        pe=g[g.exit_reason==2]
        rows.append({
          'window_min':w,'flat_band_pct':band*100,'oi_state':os,'taker_state':ts,'N':len(g),
          'EV_R':m.get('EV',np.nan),'WR':m.get('WR',np.nan),'PF':m.get('PF',np.nan),
          'SumR':m.get('SumR',np.nan),'MaxDD_R':m.get('MaxDD_R',np.nan),
          'MFE_15m_mean':float(g.mfe_15m.mean()),'MAE_15m_mean':float(g.mae_15m.mean()),
          'MFE_60m_mean':float(g.mfe_60m.mean()),'MAE_60m_mean':float(g.mae_60m.mean()),
          'profit_exit_rate':float((g.exit_reason==2).mean()),
          'time_to_profit_exit_median':float(pe.time_to_profit_exit_min.median()) if len(pe) else np.nan,
          'time_to_profit_exit_mean':float(pe.time_to_profit_exit_min.mean()) if len(pe) else np.nan,
          'time_to_3atr_median':float(g.time_to_3atr_min.median(skipna=True)),
          'time_to_3p5atr_median':float(g.time_to_3p5atr_min.median(skipna=True)),
          'oi_change_mean_pct':float(g[f'oi_ch{w}'].mean()*100),
          'taker_delta_mean':float(g[f'taker_delta{w}'].mean())
        })
    return pd.DataFrame(rows)

def build():
    flow=load_flow_raw(); micro=load_micro()
    ft,fz=lab43.load_flow()
    hist_raw=lab43.load_hist(); sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    parts=[]
    for label,p in [('historical',hist),('forward_2026',fwd)]:
        d=lab54.build_dataset(label,p,lab54.load_flow_meta(),lab54.load_1m_microstructure())
        d=d[d.side==1].copy().reset_index(drop=True)
        d=add_flow_5_15(d,flow,micro)
        d=add_exit_timing(d,p)
        d['period']=label
        parts.append(d)
    return pd.concat(parts,ignore_index=True)

def main():
    d=build()
    d.to_csv(OUT/'buy_events_enriched.csv',index=False)

    primary=pd.concat([summarize(d,5,FLAT_PRIMARY),summarize(d,15,FLAT_PRIMARY)],ignore_index=True)
    primary.to_csv(OUT/'primary_5m_15m.csv',index=False)

    sens=[]
    for band in FLAT_SENS:
        for w in [5,15]:
            x=summarize(d,w,band)
            x['band_label']=f'{band*100:.3f}%'
            sens.append(x)
    sensitivity=pd.concat(sens,ignore_index=True)
    sensitivity.to_csv(OUT/'flat_band_sensitivity.csv',index=False)

    period_rows=[]
    for period,g in d.groupby('period'):
        for w in [5,15]:
            x=summarize(g,w,FLAT_PRIMARY);x['period']=period;period_rows.append(x)
    period=pd.concat(period_rows,ignore_index=True)
    period.to_csv(OUT/'period_split.csv',index=False)

    base=metrics(d.R.to_numpy(float))
    result={
      'lab':'CROWDFADE_BUY_OI_TAKER_DECOMP_LAB_077',
      'scope':'CF191g BUY only; signal and management frozen',
      'N_BUY':int(len(d)),
      'baseline':base,
      'primary_definitions':{
        'oi_down':f'dOI < -{FLAT_PRIMARY*100:.3f}%',
        'oi_flat':f'|dOI| <= {FLAT_PRIMARY*100:.3f}%',
        'oi_up':f'dOI > +{FLAT_PRIMARY*100:.3f}%',
        'taker_strong':'net taker delta > 0 (aggressive buy volume > aggressive sell volume)',
        'taker_weak':'net taker delta <= 0',
        'windows':'trailing 5m and 15m ending at entry'
      },
      'note_time_to_tp':'CF191g has no fixed TP. Report uses actual PROFIT_STOP exit time (reason=2), plus first passage to +3.0 ATR and +3.5 ATR management arms.',
      'limitations':['Diagnostic/post-hoc decomposition; no production gate promoted.',
                     'Historical 2021-2025 uses 1m Binance klines; 2026 Mar-Aug is reused shadow/stress.',
                     'OI source cadence follows frozen flow archive; 5m/15m changes use as-of values.',
                     'Primary flat band is fixed at 0.02%; robustness table includes 0/0.01/0.02/0.05%.']
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))
    lines=['# LAB077 — CrowdFade BUY: OI × taker decomposition','',
      f"BUY N = **{len(d)}**",'',
      'Primary definitions: OI_DOWN < -0.02%, OI_FLAT within ±0.02%, OI_UP > +0.02%; taker STRONG iff net taker delta > 0.','',
      'CF191g has no fixed TP; time-to-TP below is actual PROFIT_STOP exit timing, with +3.0/+3.5 ATR first-passage diagnostics.','',
      '## Primary 5m / 15m','',primary.to_markdown(index=False),'',
      '## Historical vs 2026 split','',period.to_markdown(index=False),'',
      '## Flat-band sensitivity','',sensitivity.to_markdown(index=False),'',
      '## Notes']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
