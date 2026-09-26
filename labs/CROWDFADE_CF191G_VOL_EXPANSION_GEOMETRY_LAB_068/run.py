from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_CF191G_CAUSAL_VOLATILITY_REGIME_LAB_064'/'output'/'volatility_events.csv'

def metrics_r(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'EV':np.nan,'PF':np.nan,'SumR':np.nan,'WR':np.nan}
    win=a[a>0].sum();loss=-a[a<0].sum()
    return {'EV':float(a.mean()),'PF':float(win/loss) if loss>0 else np.inf,
            'SumR':float(a.sum()),'WR':float((a>0).mean())}

def period(ts):
    t=pd.to_datetime(int(ts),unit='s',utc=True)
    if pd.Timestamp('2021-01-01',tz='UTC')<=t<pd.Timestamp('2024-01-01',tz='UTC'):return '2021_2023'
    if pd.Timestamp('2024-01-01',tz='UTC')<=t<pd.Timestamp('2026-01-01',tz='UTC'):return '2024_2025'
    if pd.Timestamp('2026-03-01',tz='UTC')<=t<pd.Timestamp('2026-09-01',tz='UTC'):return '2026'
    return 'OTHER'

def desc(g,p,b):
    m=metrics_r(g.R.to_numpy(float))
    return {
      'period':p,'vol_bucket':b,'N':len(g),
      'EV_R':m['EV'],'PF':m['PF'],'SumR':m['SumR'],'WR':m['WR'],
      'FAST_0P5_rate':float((g.mfe_15m>=0.5).mean()) if len(g) else np.nan,
      'EXPAND_1R_60_rate':float((g.mfe_60m>=1.0).mean()) if len(g) else np.nan,
      'LATE_EXPAND_rate':float(((g.mfe_15m<0.5)&(g.mfe_60m>=1.0)).mean()) if len(g) else np.nan,
      'FAILED_EXPAND_rate':float((g.mfe_60m<1.0).mean()) if len(g) else np.nan,
      'impulse60_rate':float(g.impulse60.mean()) if len(g) else np.nan,
      'RIGHT_TAIL_ge1p5R_rate':float((g.R>=1.5).mean()) if len(g) else np.nan,
      'mean_mfe15':float(g.mfe_15m.mean()) if len(g) else np.nan,
      'mean_mfe30':float(g.mfe_30m.mean()) if len(g) else np.nan,
      'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
      'mean_mfe120':float(g.mfe_120m.mean()) if len(g) else np.nan,
      'mean_mae15':float(g.mae_15m.mean()) if len(g) else np.nan,
      'mean_mae30':float(g.mae_30m.mean()) if len(g) else np.nan,
      'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
      'mean_mae120':float(g.mae_120m.mean()) if len(g) else np.nan,
    }

def main():
    d=pd.read_csv(SRC)
    d['subperiod']=[period(x) for x in d.entry_ts]
    rows=[]
    for p in ['2021_2023','2024_2025','2026']:
        x=d[d.subperiod==p]
        for b in ['P40_60','P80_100']:
            rows.append(desc(x[x.vol_bucket==b],p,b))
    sm=pd.DataFrame(rows); sm.to_csv(OUT/'vol_expansion_map.csv',index=False)

    checks={}
    for p in ['2021_2023','2024_2025','2026']:
        mid=sm[(sm.period==p)&(sm.vol_bucket=='P40_60')].iloc[0]
        hi=sm[(sm.period==p)&(sm.vol_bucket=='P80_100')].iloc[0]
        checks[p]={
          'mid_N':int(mid.N),'high_N':int(hi.N),
          'high_fast0p5_lt_mid':bool(hi.FAST_0P5_rate<mid.FAST_0P5_rate),
          'high_expand1R60_lt_mid':bool(hi.EXPAND_1R_60_rate<mid.EXPAND_1R_60_rate),
          'high_failed_expand_gt_mid':bool(hi.FAILED_EXPAND_rate>mid.FAILED_EXPAND_rate),
          'high_right_tail_lt_mid':bool(hi.RIGHT_TAIL_ge1p5R_rate<mid.RIGHT_TAIL_ge1p5R_rate),
          'high_mfe60_lt_mid':bool(hi.mean_mfe60<mid.mean_mfe60),
          'high_mae60_gt_mid':bool(hi.mean_mae60>mid.mean_mae60),
          'delta_EV_R':float(hi.EV_R-mid.EV_R),
          'delta_MFE60':float(hi.mean_mfe60-mid.mean_mfe60),
          'delta_MAE60':float(hi.mean_mae60-mid.mean_mae60),
        }

    c=checks['2026']
    lost_expansion=(c['high_expand1R60_lt_mid'] and c['high_failed_expand_gt_mid'] and
                    c['high_right_tail_lt_mid'] and c['high_mfe60_lt_mid'] and
                    not c['high_mae60_gt_mid'])
    result={'lab':'LAB068_VOL_EXPANSION_GEOMETRY','checks':checks,
            'classification_2026':'LOST_DIRECTIONAL_EXPANSION_UNDER_HIGH_ATR' if lost_expansion else 'NOT_CLEAN_EXPANSION_ONLY',
            'note':'Diagnostic only; no action promoted.'}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB068 — VOLATILITY × POST-ENTRY EXPANSION GEOMETRY','',
      'Frozen LAB064 volatility buckets; no new threshold.','',
      '## Map','',sm.to_markdown(index=False),'',
      '## Checks','',json.dumps(checks,indent=2),'',
      f"2026 classification: **{result['classification_2026']}**"
    ]))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
