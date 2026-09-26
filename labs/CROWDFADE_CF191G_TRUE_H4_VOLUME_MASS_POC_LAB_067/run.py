from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_CF191G_TRUE_H4_POC_REJECTION_LAB_066'/'output'

def classify(row):
    side=int(row.event_side)
    rejected=float(row.lower_third_share if side>0 else row.upper_third_share)
    opposite=float(row.upper_third_share if side>0 else row.lower_third_share)
    mass='MASS_ALIGNED' if rejected>opposite else ('MASS_OPPOSITE' if rejected<opposite else 'MASS_BALANCED')
    poc=row.profile_class
    if poc=='POC_ALIGNED' and mass=='MASS_ALIGNED':
        combo='PROFILE_CONFIRMED'
    elif poc=='POC_OPPOSITE' and mass=='MASS_OPPOSITE':
        combo='PROFILE_CONTRADICTED'
    elif (poc=='POC_ALIGNED') ^ (mass=='MASS_ALIGNED'):
        combo='PROFILE_PARTIAL'
    else:
        combo='PROFILE_OTHER'
    return rejected,opposite,mass,combo

def ev_summary(ev):
    rows=[]
    for period in ['historical','forward_2026']:
        d=ev[ev.period==period]
        for state in ['PROFILE_CONFIRMED','PROFILE_PARTIAL','PROFILE_CONTRADICTED','PROFILE_OTHER']:
            g=d[d.profile_combo==state]
            rows.append({
              'period':period,'profile_state':state,'N':len(g),
              'mean_ret_1h':float(g.ret_1h.mean()) if len(g) else np.nan,
              'mean_ret_4h':float(g.ret_4h.mean()) if len(g) else np.nan,
              'median_ret_4h':float(g.ret_4h.median()) if len(g) else np.nan,
              'mean_ret_8h':float(g.ret_8h.mean()) if len(g) else np.nan,
              'mean_ret_12h':float(g.ret_12h.mean()) if len(g) else np.nan,
              'mean_mfe_4h':float(g.mfe_4h.mean()) if len(g) else np.nan,
              'mean_mae_4h':float(g.mae_4h.mean()) if len(g) else np.nan,
              'mean_rejected_side_share':float(g.rejected_side_share.mean()) if len(g) else np.nan,
              'mean_opposite_side_share':float(g.opposite_side_share.mean()) if len(g) else np.nan,
            })
    return pd.DataFrame(rows)

def cf_summary(over):
    rows=[]
    for period in ['historical','forward_2026']:
        d=over[over.period==period]
        for rel in ['SUPPORTIVE','ADVERSE']:
            for st in ['PROFILE_CONFIRMED','PROFILE_PARTIAL','PROFILE_CONTRADICTED','PROFILE_OTHER']:
                g=d[(d.relation==rel)&(d.profile_combo==st)]
                r=g.R.to_numpy(float)
                if len(r):
                    wins=r[r>0].sum();loss=-r[r<0].sum()
                    pf=float(wins/loss) if loss>0 else np.inf
                    ev=float(r.mean());sumr=float(r.sum())
                else:
                    pf=ev=sumr=np.nan
                rows.append({
                  'period':period,'relation':rel,'profile_state':st,'N':len(g),
                  'EV_R':ev,'PF':pf,'SumR':sumr,
                  'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
                  'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
                })
    return pd.DataFrame(rows)

def main():
    ev=pd.read_csv(SRC/'true_poc_h4_events.csv')
    if len(ev[ev.period=='historical'])!=221 or len(ev[ev.period=='forward_2026'])!=21:
        raise RuntimeError('LAB066 event parity failed')
    vals=ev.apply(classify,axis=1,result_type='expand')
    vals.columns=['rejected_side_share','opposite_side_share','mass_state','profile_combo']
    ev=pd.concat([ev,vals],axis=1)
    ev.to_csv(OUT/'volume_mass_profile_events.csv',index=False)
    esm=ev_summary(ev);esm.to_csv(OUT/'event_outcomes.csv',index=False)

    checks={}
    for period in ['historical','forward_2026']:
        c=esm[(esm.period==period)&(esm.profile_state=='PROFILE_CONFIRMED')].iloc[0]
        x=esm[(esm.period==period)&(esm.profile_state=='PROFILE_CONTRADICTED')].iloc[0]
        checks[period]={
          'confirmed_N':int(c.N),'contradicted_N':int(x.N),
          'confirmed_mean_ret4_gt_contradicted':bool(c.mean_ret_4h>x.mean_ret_4h) if np.isfinite(c.mean_ret_4h) and np.isfinite(x.mean_ret_4h) else False,
          'confirmed_median_ret4_gt_contradicted':bool(c.median_ret_4h>x.median_ret_4h) if np.isfinite(c.median_ret_4h) and np.isfinite(x.median_ret_4h) else False,
          'confirmed_mfe4_gt_contradicted':bool(c.mean_mfe_4h>x.mean_mfe_4h) if np.isfinite(c.mean_mfe_4h) and np.isfinite(x.mean_mfe_4h) else False,
          'confirmed_mae4_lt_contradicted':bool(c.mean_mae_4h<x.mean_mae_4h) if np.isfinite(c.mean_mae_4h) and np.isfinite(x.mean_mae_4h) else False,
          'sample_ok':bool(c.N >= (20 if period=='historical' else 5) and x.N >= (20 if period=='historical' else 5))
        }
    primary=all(all(v for k,v in checks[p].items() if not k.endswith('_N')) for p in checks)

    over=pd.read_csv(SRC/'cf191g_true_poc_overlap_events.csv')
    mapcols=ev[['end_ts','profile_combo','mass_state','rejected_side_share','opposite_side_share']]
    over=over.merge(mapcols,left_on='h4_event_end_ts',right_on='end_ts',how='left')
    over.to_csv(OUT/'cf191g_overlap_events.csv',index=False)
    csm=cf_summary(over);csm.to_csv(OUT/'cf191g_overlap_summary.csv',index=False)

    result={
      'lab':'LAB067_TRUE_H4_VOLUME_MASS_POC',
      'checks':checks,
      'primary_pattern_repeats_and_sample_ok':bool(primary),
      'cf191g_overlap_N':int(len(over)),
      'limitations':[
        'Uses frozen LAB066 true aggTrade profiles; no thresholds retuned.',
        'Mass alignment is only rejected-side-third share versus opposite-side-third share.',
        'Diagnostic only; no trading action.',
        '2026 Mar-Aug is reused shadow/stress.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB067 — TRUE H4 VOLUME-MASS LOCATION + POC REJECTION','',
      '## Event outcomes','',esm.to_markdown(index=False),'',
      '## Primary checks','',json.dumps(checks,indent=2),'',
      f'Primary pattern repeats with adequate sample: **{primary}**','',
      '## CF191g overlap','',csm.to_markdown(index=False)
    ]))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
