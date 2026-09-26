from pathlib import Path
import json, importlib.util
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
LB=2016
REASON={1:'INITIAL_STOP',2:'PROFIT_STOP',4:'TIME_EXIT'}

def metrics(a): return lab43.metrics(np.asarray(a,float))

def bucket(x):
    if not np.isfinite(x):return 'NA'
    if x<0.2:return 'P0_20'
    if x<0.4:return 'P20_40'
    if x<0.6:return 'P40_60'
    if x<0.8:return 'P60_80'
    return 'P80_100'

def build(label,p):
    df=lab54.extract_cf191g_events(p)
    exp=EXPECT[label]
    if len(df)!=exp['N'] or abs(float(df.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'parity {label}: {len(df)} {df.R.sum()}')
    df=lab54.add_targets(df,p)

    dt5,H5,L5,C5,Z5,A5=p[5],p[6],p[7],p[8],p[9],p[10]
    vm=A5/C5
    pct=np.full(len(vm),np.nan)
    for k in range(LB,len(vm)):
        hist=vm[k-LB:k]
        if np.all(np.isfinite(hist)) and np.isfinite(vm[k]):
            pct[k]=float(np.mean(hist<=vm[k]))

    vp=[];vr=[];er=[]
    for _,r in df.iterrows():
        k=int(r.entry_k)
        vp.append(float(pct[k]) if k<len(pct) else np.nan)
        vr.append(float(vm[k]) if k<len(vm) else np.nan)
        rr,ex,reason=lab53.manage_cf191g(dt5,H5,L5,C5,k,int(r.side),float(C5[k]),float(A5[k]))
        er.append(REASON.get(int(reason),str(reason)))
    df['vol_metric_atr_pct']=vr
    df['vol_percentile_7d']=vp
    df['vol_bucket']=[bucket(x) for x in vp]
    df['control_exit_reason']=er
    df['period']=label
    return df

def desc(g,period,b):
    m=metrics(g.R.to_numpy(float))
    return {
      'period':period,'bucket':b,'N':len(g),
      'EV_R':m.get('EV',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),
      'WR':m.get('WR',np.nan),'MaxDD_R':m.get('MaxDD_R',np.nan),
      'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
      'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
      'initial_stop_share':float((g.control_exit_reason=='INITIAL_STOP').mean()) if len(g) else np.nan,
      'right_tail_ge_1p5R':float((g.R>=1.5).mean()) if len(g) else np.nan,
      'mean_vol_percentile':float(g.vol_percentile_7d.mean()) if len(g) else np.nan,
    }

def main():
    ft,fz=lab43.load_flow();hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    dh=build('historical',hist);df=build('forward_2026',fwd)
    events=pd.concat([dh,df],ignore_index=True);events.to_csv(OUT/'volatility_events.csv',index=False)
    rows=[]
    for period,d in [('historical',dh),('forward_2026',df)]:
        for b in ['P0_20','P20_40','P40_60','P60_80','P80_100','NA']:
            rows.append(desc(d[d.vol_bucket==b],period,b))
    sm=pd.DataFrame(rows);sm.to_csv(OUT/'volatility_regime_map.csv',index=False)

    checks={}
    for period in ['historical','forward_2026']:
        mid=sm[(sm.period==period)&(sm.bucket=='P40_60')].iloc[0]
        hi=sm[(sm.period==period)&(sm.bucket=='P80_100')].iloc[0]
        checks[period]={
          'mid_N':int(mid.N),'high_N':int(hi.N),
          'high_EV_lt_mid':bool(hi.EV_R<mid.EV_R),
          'high_PF_lt_mid':bool(hi.PF<mid.PF),
          'high_MAE60_gt_mid':bool(hi.mean_mae60>mid.mean_mae60),
          'high_initial_stop_share_gt_mid':bool(hi.initial_stop_share>mid.initial_stop_share),
        }
    penalty=all(checks[p]['high_EV_lt_mid'] and checks[p]['high_PF_lt_mid'] and
                (checks[p]['high_MAE60_gt_mid'] or checks[p]['high_initial_stop_share_gt_mid']) for p in checks)
    result={'lab':'LAB064_CAUSAL_VOLATILITY_REGIME','checks':checks,
            'simple_high_vol_penalty_repeats_both_periods':bool(penalty),
            'limitations':['Diagnostic only; no vol filter/risk change.',
                           '7d causal percentile excludes first 2016 M5 bars in each prepared evaluation series.',
                           'BTCUSDT only; 2026 Mar-Aug reused shadow/stress.']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB064 — CAUSAL ENTRY VOLATILITY REGIME MAP','',
      'One-axis diagnostic: ATR14/price percentile over prior 7d completed M5.','',
      '## Regime map','',sm.to_markdown(index=False),'',
      '## Checks','',json.dumps(checks,indent=2),'',
      f'Simple high-vol penalty repeats both periods: **{penalty}**'
    ]))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
