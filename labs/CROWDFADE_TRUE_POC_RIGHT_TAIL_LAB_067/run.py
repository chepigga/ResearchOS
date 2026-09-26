from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_CF191G_TRUE_H4_POC_REJECTION_LAB_066'/'output'/'true_poc_h4_events.csv'

def split(ts):
    t=pd.to_datetime(int(ts),unit='s',utc=True)
    if pd.Timestamp('2021-01-01',tz='UTC')<=t<pd.Timestamp('2024-01-01',tz='UTC'):return '2021_2023'
    if pd.Timestamp('2024-01-01',tz='UTC')<=t<pd.Timestamp('2026-01-01',tz='UTC'):return '2024_2025'
    if pd.Timestamp('2026-03-01',tz='UTC')<=t<pd.Timestamp('2026-09-01',tz='UTC'):return '2026'
    return 'OTHER'

def q(s,p):
    return float(s.quantile(p)) if len(s) else np.nan

def desc(g,period,cls):
    return {
      'period':period,'profile_class':cls,'N':len(g),
      'mean_ret4':float(g.ret_4h.mean()) if len(g) else np.nan,
      'q25_ret4':q(g.ret_4h,.25),'median_ret4':q(g.ret_4h,.5),
      'q75_ret4':q(g.ret_4h,.75),'q90_ret4':q(g.ret_4h,.90),
      'positive_ret4_share':float((g.ret_4h>0).mean()) if len(g) else np.nan,
      'q75_mfe4':q(g.mfe_4h,.75),'q90_mfe4':q(g.mfe_4h,.90),
      'median_mae4':q(g.mae_4h,.5),'q75_mae4':q(g.mae_4h,.75),
    }

def main():
    d=pd.read_csv(SRC)
    d['subperiod']=[split(x) for x in d.end_ts]
    rows=[]
    for p in ['2021_2023','2024_2025','2026']:
        x=d[d.subperiod==p]
        for cls in ['POC_ALIGNED','POC_MIDDLE','POC_OPPOSITE']:
            rows.append(desc(x[x.profile_class==cls],p,cls))
    sm=pd.DataFrame(rows)
    sm.to_csv(OUT/'right_tail_map.csv',index=False)

    checks={}
    for p in ['2021_2023','2024_2025','2026']:
        a=sm[(sm.period==p)&(sm.profile_class=='POC_ALIGNED')].iloc[0]
        o=sm[(sm.period==p)&(sm.profile_class=='POC_OPPOSITE')].iloc[0]
        checks[p]={
          'aligned_N':int(a.N),'opposite_N':int(o.N),
          'aligned_q90_ret4_gt_opposite':bool(a.q90_ret4>o.q90_ret4) if np.isfinite(a.q90_ret4) and np.isfinite(o.q90_ret4) else False,
          'aligned_q90_mfe4_gt_opposite':bool(a.q90_mfe4>o.q90_mfe4) if np.isfinite(a.q90_mfe4) and np.isfinite(o.q90_mfe4) else False,
          'aligned_median_ret4_gt_opposite':bool(a.median_ret4>o.median_ret4) if np.isfinite(a.median_ret4) and np.isfinite(o.median_ret4) else False,
        }
    repeat=all(checks[p]['aligned_q90_ret4_gt_opposite'] and checks[p]['aligned_q90_mfe4_gt_opposite'] for p in checks)
    result={'lab':'LAB067_TRUE_POC_RIGHT_TAIL','checks':checks,
            'right_tail_advantage_repeats_all_splits':bool(repeat),
            'decision':'SHADOW_ONLY' if repeat else 'CLOSE_FOOTPRINT_POC_BRANCH',
            'note':'Same LAB066 sample; robustness diagnostic, not independent OOS.'}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB067 — TRUE POC RIGHT-TAIL DISTRIBUTION CHECK','',
      'Same LAB066 event sample; no new thresholds.','',
      '## Distribution map','',sm.to_markdown(index=False),'',
      '## Checks','',json.dumps(checks,indent=2),'',
      f"Right-tail advantage repeats all splits: **{repeat}**",'',
      f"Decision: **{result['decision']}**"
    ]))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
