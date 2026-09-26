from pathlib import Path
import json, zipfile, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Reuse exact CF191g causal event extractor and outcome geometry from LAB054.
p54=ROOT.parent/'CROWDFADE_CF191G_CAUSAL_REGIME_IMPULSE_MODEL_LAB_054'/'run.py'
sp=importlib.util.spec_from_file_location('lab54',p54)
lab54=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab54)
lab53=lab54.lab53; lab43=lab54.lab43
lab54.DATA=DATA; lab53.DATA=DATA; lab43.DATA=DATA

EXPECT={
    'historical': {'N':5297,'SumR':700.3704107793633},
    'forward_2026': {'N':544,'SumR':35.49784078156513},
}

WINDOWS=[5,15,30]

def metrics_r(a):
    return lab43.metrics(np.asarray(a,float))

def load_micro():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,4,5,9])
        ts=(pd.to_numeric(q.iloc[:,0],errors='coerce')//1000).astype('Int64')
        close=pd.to_numeric(q.iloc[:,1],errors='coerce')
        vol=pd.to_numeric(q.iloc[:,2],errors='coerce')
        taker=pd.to_numeric(q.iloc[:,3],errors='coerce')
        x=pd.DataFrame({'ts_start':ts,'close':close,'volume':vol,'taker_buy':taker}).dropna()
        x['ts']=x.ts_start.astype(np.int64)+60  # minute becomes causal after it closes
        rows.append(x[['ts','close','volume','taker_buy']])
    m=pd.concat(rows,ignore_index=True).sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
    m['taker_sell']=m.volume-m.taker_buy
    m['delta']=m.taker_buy-m.taker_sell
    return m

def load_oi():
    return lab54.load_flow_meta()[['ts','oi']].copy()

def asof_idx(ts,q):
    return np.searchsorted(ts,q,'right')-1

def add_absorption_features(df,p,micro,oi):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    ek=df.entry_k.to_numpy(np.int64)
    et=df.entry_ts.to_numpy(np.int64)
    sd=df.side.to_numpy(np.int8)
    atr=A5[ek]
    mt=micro.ts.to_numpy(np.int64)
    mc=micro.close.to_numpy(float)
    mv=micro.volume.to_numpy(float)
    mb=micro.taker_buy.to_numpy(float)
    md=micro.delta.to_numpy(float)
    oi_ts=oi.ts.to_numpy(np.int64); oi_v=oi.oi.to_numpy(float)

    for w in WINDOWS:
        flow_ratio=np.full(len(df),np.nan)
        signed_flow=np.full(len(df),np.nan)
        price_resp=np.full(len(df),np.nan)
        abs_resp=np.full(len(df),np.nan)
        impact=np.full(len(df),np.nan)
        total_vol=np.full(len(df),np.nan)
        buy_vol=np.full(len(df),np.nan)
        sell_vol=np.full(len(df),np.nan)
        raw_delta=np.full(len(df),np.nan)

        for i,(t0,side,a) in enumerate(zip(et,sd,atr)):
            if not np.isfinite(a) or a<=0: continue
            e=asof_idx(mt,t0)
            s=asof_idx(mt,t0-w*60)
            if e<0 or s<0 or e<=s: continue
            # (s, e] are completed minutes ending no later than entry.
            sl=slice(s+1,e+1)
            vv=mv[sl]; bb=mb[sl]; dd=md[sl]
            if len(vv)==0: continue
            v=float(np.nansum(vv)); b=float(np.nansum(bb)); d=float(np.nansum(dd))
            if not np.isfinite(v) or v<=0: continue
            sell=v-b
            ratio=d/v
            p0=mc[s]
            p1=mc[e]
            if not np.isfinite(p0) or not np.isfinite(p1): continue
            pr=float(side*(p1-p0)/a)
            sf=float(side*ratio)
            flow_ratio[i]=ratio; signed_flow[i]=sf; price_resp[i]=pr
            abs_resp[i]=abs(pr); impact[i]=pr/(abs(ratio)+1e-6)
            total_vol[i]=v; buy_vol[i]=b; sell_vol[i]=sell; raw_delta[i]=d

        df[f'taker_delta_ratio_{w}m']=flow_ratio
        df[f'signed_flow_{w}m']=signed_flow
        df[f'price_response_atr_{w}m']=price_resp
        df[f'abs_price_response_atr_{w}m']=abs_resp
        df[f'flow_to_price_impact_{w}m']=impact
        df[f'total_volume_{w}m']=total_vol
        df[f'taker_buy_volume_{w}m']=buy_vol
        df[f'taker_sell_volume_{w}m']=sell_vol
        df[f'taker_delta_{w}m']=raw_delta

    for w in [15,30]:
        now=asof_idx(oi_ts,et)
        prev=asof_idx(oi_ts,et-w*60)
        out=np.full(len(df),np.nan)
        g=(now>=0)&(prev>=0)&(oi_v[prev]>0)
        out[g]=oi_v[now[g]]/oi_v[prev[g]]-1.0
        df[f'oi_ch{w}']=out

    return df

def build(label,p,micro,oi):
    # Reuse LAB054 event extraction + outcome calculation, but not its ML.
    df=lab54.extract_cf191g_events(p)
    rr,st,side,sk=lab53.sim_cf191g(*p,False)
    if len(df)!=len(rr) or not np.allclose(df.R.to_numpy(float),rr,atol=1e-12,rtol=0):
        raise RuntimeError(f'event parity fail {label}')
    exp=EXPECT[label]
    if len(df)!=exp['N'] or abs(float(df.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'control parity fail {label}: N={len(df)} SumR={df.R.sum()}')
    df=lab54.add_targets(df,p)
    df=add_absorption_features(df,p,micro,oi)
    df['period']=label
    df['entry_time']=pd.to_datetime(df.entry_ts,unit='s',utc=True).astype(str)
    return df

def q5(series):
    valid=series.notna()
    out=pd.Series(pd.NA,index=series.index,dtype='object')
    if valid.sum()<5:return out
    ranks=series[valid].rank(method='first')
    out.loc[valid]=pd.qcut(ranks,5,labels=['Q1','Q2','Q3','Q4','Q5']).astype(str)
    return out

def describe(g,period,window,label,flowq='',priceq=''):
    m=metrics_r(g.R.to_numpy(float))
    return {
      'period':period,'window_min':window,'bucket':label,
      'flow_q':flowq,'price_q':priceq,'N':len(g),
      'EV_R':m.get('EV',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),
      'MaxDD_R':m.get('MaxDD_R',np.nan),
      'WR':m.get('WR',np.nan),
      'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
      'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
      'mean_ret60':float(g.ret_60m.mean()) if len(g) else np.nan,
      'impulse60_rate':float(g.impulse60.mean()) if len(g) else np.nan,
      'mean_oi_ch15':float(g.oi_ch15.mean()) if len(g) else np.nan,
      'mean_oi_ch30':float(g.oi_ch30.mean()) if len(g) else np.nan,
      'mean_signed_flow':float(g[f'signed_flow_{window}m'].mean()) if len(g) else np.nan,
      'mean_price_response_atr':float(g[f'price_response_atr_{window}m'].mean()) if len(g) else np.nan,
    }

def maps_for_period(df,period):
    map_rows=[];corner_rows=[];summary=[]
    control=metrics_r(df.R.to_numpy(float))
    for w in WINDOWS:
        fcol=f'signed_flow_{w}m'; pcol=f'price_response_atr_{w}m'
        x=df[df[fcol].notna()&df[pcol].notna()].copy()
        x['flow_q']=q5(x[fcol]);x['price_q']=q5(x[pcol])
        x=x[x.flow_q.notna()&x.price_q.notna()].copy()

        for fq in ['Q1','Q2','Q3','Q4','Q5']:
            for pq in ['Q1','Q2','Q3','Q4','Q5']:
                g=x[(x.flow_q==fq)&(x.price_q==pq)]
                if len(g):
                    map_rows.append(describe(g,period,w,'CELL',fq,pq))

        buckets={
          'ADVERSE_ABSORPTION_QCORNER': x[(x.flow_q=='Q5')&x.price_q.isin(['Q1','Q2'])],
          'SUPPORTIVE_ABSORPTION_QCORNER': x[(x.flow_q=='Q1')&x.price_q.isin(['Q4','Q5'])],
          'FLOW_WITH_PRICE_WITH': x[(x.flow_q=='Q5')&x.price_q.isin(['Q4','Q5'])],
          'FLOW_AGAINST_PRICE_AGAINST': x[(x.flow_q=='Q1')&x.price_q.isin(['Q1','Q2'])],
        }
        cdesc={}
        for name,g in buckets.items():
            d=describe(g,period,w,name)
            d['delta_EV_vs_control']=d['EV_R']-control.get('EV',np.nan)
            d['delta_PF_vs_control']=d['PF']-control.get('PF',np.nan) if np.isfinite(d['PF']) else np.nan
            corner_rows.append(d); cdesc[name]=d

        adv=cdesc['ADVERSE_ABSORPTION_QCORNER']
        sup=cdesc['SUPPORTIVE_ABSORPTION_QCORNER']
        separation=(sup['EV_R']-adv['EV_R']) if np.isfinite(sup['EV_R']) and np.isfinite(adv['EV_R']) else np.nan
        geom=((adv['mean_mae60']-adv['mean_mfe60']) if np.isfinite(adv['mean_mae60']) else np.nan)
        summary.append({
          'period':period,'window_min':w,'control_N':len(df),'mapped_N':len(x),
          'control_EV':control.get('EV',np.nan),'control_PF':control.get('PF',np.nan),
          'adverse_N':adv['N'],'adverse_EV':adv['EV_R'],'adverse_PF':adv['PF'],
          'adverse_mfe60':adv['mean_mfe60'],'adverse_mae60':adv['mean_mae60'],
          'supportive_N':sup['N'],'supportive_EV':sup['EV_R'],'supportive_PF':sup['PF'],
          'supportive_mfe60':sup['mean_mfe60'],'supportive_mae60':sup['mean_mae60'],
          'supportive_minus_adverse_EV':separation,
          'adverse_MAE_minus_MFE':geom
        })
    return pd.DataFrame(map_rows),pd.DataFrame(corner_rows),pd.DataFrame(summary)

def main():
    micro=load_micro();oi=load_oi()
    ft,fz=lab43.load_flow()
    hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))

    dh=build('historical',hist,micro,oi)
    df=build('forward_2026',fwd,micro,oi)
    events=pd.concat([dh,df],ignore_index=True)
    events.to_csv(OUT/'cf191g_absorption_events.csv',index=False)

    maps=[];corners=[];summaries=[]
    for period,d in [('historical',dh),('forward_2026',df)]:
        a,b,c=maps_for_period(d,period);maps.append(a);corners.append(b);summaries.append(c)
    mapdf=pd.concat(maps,ignore_index=True)
    cornerdf=pd.concat(corners,ignore_index=True)
    sumdf=pd.concat(summaries,ignore_index=True)

    mapdf.to_csv(OUT/'absorption_5x5_map.csv',index=False)
    cornerdf.to_csv(OUT/'absorption_corner_buckets.csv',index=False)
    sumdf.to_csv(OUT/'absorption_window_summary.csv',index=False)

    # Descriptive stability call, not a production PASS.
    stability=[]
    for w in WINDOWS:
        h=sumdf[(sumdf.period=='historical')&(sumdf.window_min==w)].iloc[0]
        f=sumdf[(sumdf.period=='forward_2026')&(sumdf.window_min==w)].iloc[0]
        adverse_below_control=bool(h.adverse_EV<h.control_EV and f.adverse_EV<f.control_EV)
        supportive_above_control=bool(h.supportive_EV>h.control_EV and f.supportive_EV>f.control_EV)
        supportive_gt_adverse=bool(h.supportive_EV>h.adverse_EV and f.supportive_EV>f.adverse_EV)
        stability.append({
          'window_min':w,
          'adverse_EV_below_control_both':adverse_below_control,
          'supportive_EV_above_control_both':supportive_above_control,
          'supportive_EV_gt_adverse_both':supportive_gt_adverse,
          'descriptive_absorption_pattern':bool(adverse_below_control and supportive_gt_adverse),
          'historical_separation_EV':float(h.supportive_minus_adverse_EV),
          'forward_2026_separation_EV':float(f.supportive_minus_adverse_EV)
        })
    stab=pd.DataFrame(stability)
    stab.to_csv(OUT/'absorption_stability.csv',index=False)

    result={
      'lab':'CROWDFADE_CF191G_CAUSAL_ABSORPTION_MAP_LAB_056',
      'parity':{
        'historical':{'N':len(dh),'SumR':float(dh.R.sum())},
        'forward_2026':{'N':len(df),'SumR':float(df.R.sum())}},
      'window_summary':sumdf.to_dict('records'),
      'stability':stability,
      'limitations':[
        'Diagnostic quintiles use each evaluation period distribution; they are descriptive and not deployable thresholds.',
        'BTCUSDT only; ETH/SOL transfer not established.',
        '2026 Mar-Aug is reused shadow/stress, not pristine OOS.',
        'Binance taker-buy volume is aggressive-flow proxy; passive liquidity is inferred through failed price impact, not observed order-by-order.',
        'OI archive is contextual only and not part of absorption bucket definitions.',
        'No hard gate or risk multiplier is promoted from LAB056.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    lines=['# LAB056 — CF191G CAUSAL ABSORPTION MAP','',
      'Diagnostic only. CF191g signal and trading state machine unchanged.','',
      '## Control parity','',
      f"- 2021–2025: N={len(dh)}, SumR={dh.R.sum():+.6f}",
      f"- 2026 Mar–Aug: N={len(df)}, SumR={df.R.sum():+.6f}",'',
      '## Window summary','',sumdf.to_markdown(index=False),'',
      '## Corner buckets','',cornerdf.to_markdown(index=False),'',
      '## Stability','',stab.to_markdown(index=False),'',
      '## Interpretation rule','',
      '- Adverse absorption corner = signed aggressive flow Q5 but signed price response Q1/Q2.',
      '- Supportive absorption corner = signed aggressive flow Q1 but signed price response Q4/Q5.',
      '- Quintile cutoffs are descriptive only and cannot become production thresholds from this LAB.','',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
