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
MINUTE_LOOKBACK=1440
SEQ_LOOKBACK=288
EPS=1e-6

def metrics_r(a):
    return lab43.metrics(np.asarray(a,float))

def load_m1():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,1,4,7,10])
        ot=(pd.to_numeric(q.iloc[:,0],errors='coerce')//1000).astype('Int64')
        op=pd.to_numeric(q.iloc[:,1],errors='coerce')
        cl=pd.to_numeric(q.iloc[:,2],errors='coerce')
        quote=pd.to_numeric(q.iloc[:,3],errors='coerce')
        tbq=pd.to_numeric(q.iloc[:,4],errors='coerce')
        x=pd.DataFrame({'open_ts':ot,'open':op,'close':cl,'quote_volume':quote,'taker_buy_quote':tbq}).dropna()
        x['end_ts']=x.open_ts.astype(np.int64)+60
        rows.append(x)
    m=pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)
    m['taker_sell_quote']=m.quote_volume-m.taker_buy_quote
    m['delta_notional']=m.taker_buy_quote-m.taker_sell_quote
    m['aggression_mag']=m.delta_notional.abs()
    m['typical_1m_aggression']=m.aggression_mag.shift(1).rolling(MINUTE_LOOKBACK,min_periods=MINUTE_LOOKBACK).median()
    m['aggression_intensity']=m.aggression_mag/m.typical_1m_aggression.replace(0,np.nan)
    return m

def build_sequence_table(p,m1):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    ends=m1.end_ts.to_numpy(np.int64)
    opens=m1.open.to_numpy(float); closes=m1.close.to_numpy(float)
    deltas=m1.delta_notional.to_numpy(float); intens=m1.aggression_intensity.to_numpy(float)

    rows=[]
    for k,t in enumerate(dt5):
        j=np.searchsorted(ends,int(t),'left')
        if j>=len(ends) or ends[j]!=int(t) or j<4: continue
        idx=np.arange(j-4,j+1)
        expected=np.arange(int(t)-240,int(t)+1,60)
        if not np.array_equal(ends[idx],expected): continue
        a=float(A5[k])
        if not np.isfinite(a) or a<=0: continue
        ii=intens[idx]
        dd=deltas[idx]
        if not np.all(np.isfinite(ii)) or not np.all(np.isfinite(dd)): continue
        raw_imp=(closes[idx]-opens[idx])/a
        eff=raw_imp/(ii+EPS)
        x=np.arange(1,6,dtype=float)
        eff_slope=float(np.polyfit(x,eff,1)[0])
        imp_slope=float(np.polyfit(x,raw_imp,1)[0])
        first2=float(np.mean(eff[:2])); last2=float(np.mean(eff[-2:]))
        drop=float(first2-last2)
        rows.append({
          'ts':int(t),'k':int(k),'atr':a,
          'mean_aggression_intensity':float(np.mean(ii)),
          'base_efficiency_slope':eff_slope,
          'base_impact_slope':imp_slope,
          'base_first2_efficiency':first2,
          'base_last2_efficiency':last2,
          'base_efficiency_drop':drop,
          'd1':float(dd[0]),'d2':float(dd[1]),'d3':float(dd[2]),'d4':float(dd[3]),'d5':float(dd[4]),
          'i1':float(ii[0]),'i2':float(ii[1]),'i3':float(ii[2]),'i4':float(ii[3]),'i5':float(ii[4]),
          'p1':float(raw_imp[0]),'p2':float(raw_imp[1]),'p3':float(raw_imp[2]),'p4':float(raw_imp[3]),'p5':float(raw_imp[4]),
        })
    s=pd.DataFrame(rows).sort_values('ts').reset_index(drop=True)
    ap=np.full(len(s),np.nan);dp_buy=np.full(len(s),np.nan);dp_sell=np.full(len(s),np.nan)
    ag=s.mean_aggression_intensity.to_numpy(float);dr=s.base_efficiency_drop.to_numpy(float)
    for j in range(SEQ_LOOKBACK,len(s)):
        prev_ag=ag[j-SEQ_LOOKBACK:j];prev_dr=dr[j-SEQ_LOOKBACK:j]
        if np.all(np.isfinite(prev_ag)) and np.isfinite(ag[j]):
            ap[j]=float(np.mean(prev_ag<=ag[j]))
        if np.all(np.isfinite(prev_dr)) and np.isfinite(dr[j]):
            dp_buy[j]=float(np.mean(prev_dr<=dr[j]))
            dp_sell[j]=float(np.mean((-prev_dr)<=(-dr[j])))
    s['sequence_aggression_percentile']=ap
    s['drop_percentile_buy']=dp_buy
    s['drop_percentile_sell']=dp_sell
    return s

def p_bucket(x):
    if not np.isfinite(x): return 'NA'
    if x<0.20:return 'P0_20'
    if x<0.40:return 'P20_40'
    if x<0.60:return 'P40_60'
    if x<0.80:return 'P60_80'
    return 'P80_100'

def d_bucket(x):
    if not np.isfinite(x): return 'NA'
    if x<0.20:return 'D0_20'
    if x<0.40:return 'D20_40'
    if x<0.60:return 'D40_60'
    if x<0.80:return 'D60_80'
    return 'D80_100'

def attach_sequence(df,seq):
    mp={int(t):i for i,t in enumerate(seq.ts.to_numpy(np.int64))}
    out={
      'with_fraction':[],'against_fraction':[],'mean_aggression_intensity':[],
      'efficiency_slope':[],'impact_slope':[],'first2_efficiency':[],
      'last2_efficiency':[],'efficiency_drop':[],'sequence_aggression_percentile':[],
      'efficiency_drop_percentile':[],'persistence_class':[]
    }
    minute_cols={f'{kind}{i}':[] for kind in ['signed_delta_','aggr_intensity_','impact_','efficiency_'] for i in range(1,6)}
    for _,r in df.iterrows():
        j=mp.get(int(r.entry_ts),None)
        if j is None:
            vals={k:np.nan for k in out if k!='persistence_class'}
            for k,v in vals.items():out[k].append(v)
            out['persistence_class'].append('NA')
            for k in minute_cols:minute_cols[k].append(np.nan)
            continue
        q=seq.iloc[j];side=int(r.side)
        dd=np.array([q.d1,q.d2,q.d3,q.d4,q.d5],float)
        ii=np.array([q.i1,q.i2,q.i3,q.i4,q.i5],float)
        raw=np.array([q.p1,q.p2,q.p3,q.p4,q.p5],float)
        sdelta=side*dd
        impact=side*raw
        eff=impact/(ii+EPS)
        wf=float(np.mean(sdelta>0));af=float(np.mean(sdelta<0))
        cls='WITH_PERSISTENT' if wf>=0.80 else ('AGAINST_PERSISTENT' if af>=0.80 else 'MIXED')
        out['with_fraction'].append(wf);out['against_fraction'].append(af)
        out['mean_aggression_intensity'].append(float(q.mean_aggression_intensity))
        out['efficiency_slope'].append(float(side*q.base_efficiency_slope))
        out['impact_slope'].append(float(side*q.base_impact_slope))
        out['first2_efficiency'].append(float(side*q.base_first2_efficiency))
        out['last2_efficiency'].append(float(side*q.base_last2_efficiency))
        out['efficiency_drop'].append(float(side*q.base_efficiency_drop))
        out['sequence_aggression_percentile'].append(float(q.sequence_aggression_percentile))
        dp=q.drop_percentile_buy if side>0 else q.drop_percentile_sell
        out['efficiency_drop_percentile'].append(float(dp))
        out['persistence_class'].append(cls)
        for n in range(5):
            minute_cols[f'signed_delta_{n+1}'].append(float(sdelta[n]))
            minute_cols[f'aggr_intensity_{n+1}'].append(float(ii[n]))
            minute_cols[f'impact_{n+1}'].append(float(impact[n]))
            minute_cols[f'efficiency_{n+1}'].append(float(eff[n]))
    for k,v in out.items():df[k]=v
    for k,v in minute_cols.items():df[k]=v
    df['aggr_bucket']=[p_bucket(x) for x in df.sequence_aggression_percentile]
    df['drop_bucket']=[d_bucket(x) for x in df.efficiency_drop_percentile]
    df['adverse_decay_corner']=(df.persistence_class=='WITH_PERSISTENT')&(df.sequence_aggression_percentile>=0.80)&(df.efficiency_drop_percentile>=0.80)
    df['supportive_decay_corner']=(df.persistence_class=='AGAINST_PERSISTENT')&(df.sequence_aggression_percentile>=0.80)&(df.efficiency_drop_percentile>=0.80)
    return df

def build(label,p,m1):
    df=lab54.extract_cf191g_events(p)
    rr,st,side,sk=lab53.sim_cf191g(*p,False)
    if len(df)!=len(rr) or not np.allclose(df.R.to_numpy(float),rr,atol=1e-12,rtol=0):
        raise RuntimeError(f'event parity fail {label}')
    exp=EXPECT[label]
    if len(df)!=exp['N'] or abs(float(df.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'control parity fail {label}')
    df=lab54.add_targets(df,p)
    seq=build_sequence_table(p,m1)
    df=attach_sequence(df,seq)
    df['period']=label
    df['entry_time']=pd.to_datetime(df.entry_ts,unit='s',utc=True).astype(str)
    return df,seq

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
      'mean_with_fraction':float(g.with_fraction.mean()) if len(g) else np.nan,
      'mean_against_fraction':float(g.against_fraction.mean()) if len(g) else np.nan,
      'mean_sequence_aggression_percentile':float(g.sequence_aggression_percentile.mean()) if len(g) else np.nan,
      'mean_efficiency_drop_percentile':float(g.efficiency_drop_percentile.mean()) if len(g) else np.nan,
      'mean_efficiency_drop':float(g.efficiency_drop.mean()) if len(g) else np.nan,
      'mean_efficiency_slope':float(g.efficiency_slope.mean()) if len(g) else np.nan,
    }

def map_period(df,period):
    valid=df[df.sequence_aggression_percentile.notna()&df.efficiency_drop_percentile.notna()].copy()
    rows=[]
    for cls in ['WITH_PERSISTENT','AGAINST_PERSISTENT','MIXED']:
        s=valid[valid.persistence_class==cls]
        for ab in ['P0_20','P20_40','P40_60','P60_80','P80_100']:
            for db in ['D0_20','D20_40','D40_60','D60_80','D80_100']:
                g=s[(s.aggr_bucket==ab)&(s.drop_bucket==db)]
                if len(g):
                    d=describe(g,period,f'{cls}_{ab}_{db}')
                    d.update({'persistence_class':cls,'aggr_bucket':ab,'drop_bucket':db})
                    rows.append(d)
    return pd.DataFrame(rows)

def main():
    m1=load_m1()
    ft,fz=lab43.load_flow()
    hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))

    dh,sh=build('historical',hist,m1)
    df,sf=build('forward_2026',fwd,m1)
    events=pd.concat([dh,df],ignore_index=True)
    events.to_csv(OUT/'cf191g_sequential_absorption_events.csv',index=False)

    maps=pd.concat([map_period(dh,'historical'),map_period(df,'forward_2026')],ignore_index=True)
    maps.to_csv(OUT/'sequential_absorption_map.csv',index=False)

    controls=[];flags=[]
    for period,d in [('historical',dh),('forward_2026',df)]:
        c=describe(d,period,'CONTROL');controls.append(c)
        for name,mask in [('ADVERSE_DECAY_CORNER',d.adverse_decay_corner),('SUPPORTIVE_DECAY_CORNER',d.supportive_decay_corner)]:
            x=describe(d[mask],period,name)
            x['delta_EV_vs_control']=x['EV_R']-c['EV_R']
            x['delta_PF_vs_control']=x['PF']-c['PF'] if np.isfinite(x['PF']) else np.nan
            x['delta_MFE60_vs_control']=x['mean_mfe60']-c['mean_mfe60']
            x['delta_MAE60_vs_control']=x['mean_mae60']-c['mean_mae60']
            flags.append(x)

    controldf=pd.DataFrame(controls);flagdf=pd.DataFrame(flags)
    controldf.to_csv(OUT/'control_geometry.csv',index=False)
    flagdf.to_csv(OUT/'decay_corner_results.csv',index=False)

    checks={}
    for period in ['historical','forward_2026']:
        c=controldf[controldf.period==period].iloc[0]
        a=flagdf[(flagdf.period==period)&(flagdf.bucket=='ADVERSE_DECAY_CORNER')].iloc[0]
        s=flagdf[(flagdf.period==period)&(flagdf.bucket=='SUPPORTIVE_DECAY_CORNER')].iloc[0]
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

    result={
      'lab':'CROWDFADE_CF191G_SEQUENTIAL_ABSORPTION_DECAY_LAB_058',
      'parity':{
        'historical':{'N':len(dh),'SumR':float(dh.R.sum())},
        'forward_2026':{'N':len(df),'SumR':float(df.R.sum())}},
      'checks':checks,
      'limitations':[
        'Diagnostic only; no stateful veto tested.',
        'Sequence uses Binance 1m taker quote-notional proxy, not full order-book resting liquidity.',
        'Aggression magnitude is normalized by prior 1440 completed 1m bars.',
        'Sequence percentiles use prior 288 completed 5m sequences only.',
        'BTCUSDT only; ETH/SOL transfer not established.',
        '2026 Mar-Aug is reused shadow/stress, not pristine OOS.',
        'Persistent 4-of-5 + double-tail corner may still be sample-limited.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    lines=['# LAB058 — SEQUENTIAL ABSORPTION / MARGINAL PRICE-IMPACT DECAY','',
      'Diagnostic only. CF191g state machine unchanged.','',
      '## Control parity','',
      f"- 2021–2025: N={len(dh)}, SumR={dh.R.sum():+.6f}",
      f"- 2026 Mar–Aug: N={len(df)}, SumR={df.R.sum():+.6f}",'',
      '## Control geometry','',controldf.to_markdown(index=False),'',
      '## Decay corners','',flagdf.to_markdown(index=False),'',
      '## Primary checks','',json.dumps(checks,indent=2),'',
      '## Fixed causal map','',maps.to_markdown(index=False),'',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
