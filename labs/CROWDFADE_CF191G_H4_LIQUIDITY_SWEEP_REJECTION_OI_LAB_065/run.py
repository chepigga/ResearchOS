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
 'historical':{'N':5297,'SumR':700.3704107793633},
 'forward_2026':{'N':544,'SumR':35.49784078156513},
}
VOL_LB=180
PRIOR_H4=6
REASON={1:'INITIAL_STOP',2:'PROFIT_STOP',4:'TIME_EXIT'}

def metrics(a): return lab43.metrics(np.asarray(a,float))

def load_h4():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,1,2,3,4,7])
        ot=(pd.to_numeric(q.iloc[:,0],errors='coerce')//1000).astype('Int64')
        op=pd.to_numeric(q.iloc[:,1],errors='coerce')
        hi=pd.to_numeric(q.iloc[:,2],errors='coerce')
        lo=pd.to_numeric(q.iloc[:,3],errors='coerce')
        cl=pd.to_numeric(q.iloc[:,4],errors='coerce')
        qv=pd.to_numeric(q.iloc[:,5],errors='coerce')
        x=pd.DataFrame({'open_ts':ot,'open':op,'high':hi,'low':lo,'close':cl,'quote_volume':qv}).dropna()
        rows.append(x)
    m=pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)
    m['bucket']=(m.open_ts.astype(np.int64)//14400)*14400
    g=m.groupby('bucket',sort=True)
    h4=g.agg(
      open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),
      quote_volume=('quote_volume','sum'),bars=('open_ts','count')
    ).reset_index().rename(columns={'bucket':'open_ts'})
    h4=h4[h4.bars==240].copy().reset_index(drop=True)
    h4['end_ts']=h4.open_ts.astype(np.int64)+14400

    qv=h4.quote_volume.to_numpy(float)
    vp=np.full(len(h4),np.nan)
    for i in range(VOL_LB,len(h4)):
        hist=qv[i-VOL_LB:i]
        if np.all(np.isfinite(hist)) and np.isfinite(qv[i]):
            vp[i]=float(np.mean(hist<=qv[i]))
    h4['volume_percentile']=vp
    h4['high_volume']=h4.volume_percentile>=0.80

    H=h4.high.to_numpy(float);L=h4.low.to_numpy(float);C=h4.close.to_numpy(float)
    longrej=np.zeros(len(h4),bool); shortrej=np.zeros(len(h4),bool)
    close_loc=np.full(len(h4),np.nan)
    for i in range(PRIOR_H4,len(h4)):
        rng=H[i]-L[i]
        if rng<=0: continue
        loc=(C[i]-L[i])/rng
        close_loc[i]=loc
        longrej[i]=(L[i] < np.min(L[i-PRIOR_H4:i])) and (loc>=2/3)
        shortrej[i]=(H[i] > np.max(H[i-PRIOR_H4:i])) and (loc<=1/3)
    h4['close_loc']=close_loc
    h4['long_rejection']=longrej
    h4['short_rejection']=shortrej
    return h4

def add_oi(h4):
    flow=lab54.load_flow_meta()
    ft=flow.ts.to_numpy(np.int64);oi=flow.oi.to_numpy(float)
    st=h4.open_ts.to_numpy(np.int64);et=h4.end_ts.to_numpy(np.int64)
    i0=np.searchsorted(ft,st,'right')-1
    i1=np.searchsorted(ft,et,'right')-1
    ch=np.full(len(h4),np.nan)
    good=(i0>=0)&(i1>=0)&(oi[i0]>0)
    ch[good]=oi[i1[good]]/oi[i0[good]]-1.0
    h4['oi_change_h4']=ch
    h4['oi_flush']=ch<0
    h4['event_side']=np.where(h4.high_volume & h4.oi_flush & h4.long_rejection,1,
                      np.where(h4.high_volume & h4.oi_flush & h4.short_rejection,-1,0))
    return h4

def build(label,p,h4):
    df=lab54.extract_cf191g_events(p)
    exp=EXPECT[label]
    if len(df)!=exp['N'] or abs(float(df.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'parity {label}: {len(df)} {df.R.sum()}')
    df=lab54.add_targets(df,p)
    dt5,H5,L5,C5,Z5,A5=p[5],p[6],p[7],p[8],p[9],p[10]

    end=h4.end_ts.to_numpy(np.int64)
    et=df.entry_ts.to_numpy(np.int64)
    j=np.searchsorted(end,et,'right')-1
    cols=['open_ts','end_ts','volume_percentile','high_volume','close_loc','long_rejection','short_rejection','oi_change_h4','oi_flush','event_side']
    for c in cols:
        arr=h4[c].to_numpy()
        out=np.full(len(df),np.nan if arr.dtype.kind in 'fc' else -999, dtype=float if arr.dtype.kind in 'fc' else object)
        good=j>=0
        if arr.dtype.kind in 'fc':
            out=np.full(len(df),np.nan,float);out[good]=arr[j[good]]
        else:
            out=np.empty(len(df),object);out[:]=None;out[good]=arr[j[good]]
        df[f'h4_{c}']=out

    rel=[]
    for sd,es in zip(df.side.to_numpy(np.int8),df.h4_event_side):
        if es is None: rel.append('NA')
        else:
            e=int(es)
            if e==0: rel.append('NONE')
            elif e==sd: rel.append('SUPPORTIVE')
            elif e==-sd: rel.append('ADVERSE')
            else: rel.append('NONE')
    df['h4_rejection_state']=rel

    er=[]
    for _,r in df.iterrows():
        k=int(r.entry_k)
        rr,ex,reason=lab53.manage_cf191g(dt5,H5,L5,C5,k,int(r.side),float(C5[k]),float(A5[k]))
        er.append(REASON.get(int(reason),str(reason)))
    df['control_exit_reason']=er
    df['period']=label
    return df

def desc(g,period,state):
    m=metrics(g.R.to_numpy(float))
    return {
      'period':period,'state':state,'N':len(g),
      'EV_R':m.get('EV',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),
      'WR':m.get('WR',np.nan),'MaxDD_R':m.get('MaxDD_R',np.nan),
      'mean_mfe15':float(g.mfe_15m.mean()) if len(g) else np.nan,
      'mean_mae15':float(g.mae_15m.mean()) if len(g) else np.nan,
      'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
      'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
      'initial_stop_share':float((g.control_exit_reason=='INITIAL_STOP').mean()) if len(g) else np.nan,
      'right_tail_ge_1p5R':float((g.R>=1.5).mean()) if len(g) else np.nan,
    }

def main():
    h4=add_oi(load_h4())
    ft,fz=lab43.load_flow();hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    dh=build('historical',hist,h4);df=build('forward_2026',fwd,h4)
    events=pd.concat([dh,df],ignore_index=True);events.to_csv(OUT/'h4_rejection_events.csv',index=False)

    rows=[]
    for period,d in [('historical',dh),('forward_2026',df)]:
        for s in ['SUPPORTIVE','ADVERSE','NONE','NA']:
            rows.append(desc(d[d.h4_rejection_state==s],period,s))
    sm=pd.DataFrame(rows);sm.to_csv(OUT/'h4_rejection_map.csv',index=False)

    # Unique H4 component attrition by evaluation interval
    attrs=[]
    for period,start,end in [
      ('historical',pd.Timestamp('2021-01-01',tz='UTC').timestamp(),pd.Timestamp('2026-01-01',tz='UTC').timestamp()),
      ('forward_2026',pd.Timestamp('2026-03-01',tz='UTC').timestamp(),pd.Timestamp('2026-09-01',tz='UTC').timestamp())]:
        x=h4[(h4.end_ts>=start)&(h4.end_ts<end)]
        sweep=(x.long_rejection|x.short_rejection)
        attrs.append({
          'period':period,'h4_bars':len(x),
          'high_volume_bars':int(x.high_volume.sum()),
          'sweep_rejection_bars':int(sweep.sum()),
          'oi_down_bars':int(x.oi_flush.sum()),
          'full_composite_bars':int((x.event_side!=0).sum())
        })
    attr=pd.DataFrame(attrs);attr.to_csv(OUT/'component_attrition.csv',index=False)

    checks={}
    for period in ['historical','forward_2026']:
        sup=sm[(sm.period==period)&(sm.state=='SUPPORTIVE')].iloc[0]
        adv=sm[(sm.period==period)&(sm.state=='ADVERSE')].iloc[0]
        none=sm[(sm.period==period)&(sm.state=='NONE')].iloc[0]
        checks[period]={
          'supportive_N':int(sup.N),'adverse_N':int(adv.N),'none_N':int(none.N),
          'supportive_EV_gt_none':bool(sup.EV_R>none.EV_R) if np.isfinite(sup.EV_R) and np.isfinite(none.EV_R) else False,
          'supportive_PF_gt_none':bool(sup.PF>none.PF) if np.isfinite(sup.PF) and np.isfinite(none.PF) else False,
          'supportive_MFE60_gt_none':bool(sup.mean_mfe60>none.mean_mfe60) if np.isfinite(sup.mean_mfe60) else False,
          'supportive_initial_stop_lt_none':bool(sup.initial_stop_share<none.initial_stop_share) if np.isfinite(sup.initial_stop_share) else False,
          'adverse_EV_lt_supportive':bool(adv.EV_R<sup.EV_R) if np.isfinite(adv.EV_R) and np.isfinite(sup.EV_R) else False,
        }
    repeated=all(checks[p]['supportive_EV_gt_none'] and checks[p]['supportive_PF_gt_none'] for p in checks)

    result={'lab':'LAB065_H4_LIQUIDITY_SWEEP_REJECTION_OI',
      'checks':checks,'supportive_edge_repeats_both_periods':bool(repeated),
      'limitations':[
       'No footprint POC/volume-at-price; OHLC rejection + H4 quote volume is only a proxy.',
       'Only the latest completed H4 candle is mapped to each CF191g fill.',
       'OI flush uses sign only; no magnitude threshold.',
       'Diagnostic only; no entry/exit/risk action tested.',
       'BTCUSDT only; 2026 Mar-Aug reused shadow/stress.'
      ]}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB065 — H4 LIQUIDITY-SWEEP / REJECTION + OI-FLUSH MAP','',
      'Footprint-free proxy inspired by the reviewed video. Diagnostic only.','',
      '## Component attrition','',attr.to_markdown(index=False),'',
      '## CF191g outcome map','',sm.to_markdown(index=False),'',
      '## Checks','',json.dumps(checks,indent=2),'',
      f'Supportive EV/PF edge repeats both periods: **{repeated}**','',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    ))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
