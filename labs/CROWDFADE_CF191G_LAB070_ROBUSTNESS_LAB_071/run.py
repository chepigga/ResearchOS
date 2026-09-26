from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_CF191G_HIGH_VOL_FAILED_EARLY_PARTIAL_LAB_070'/'output'/'partial_events.csv'

p43=ROOT.parent/'CROWDFADE_V191D_TO_V191F_ABLATION_LAB_043'/'run.py'
sp=importlib.util.spec_from_file_location('lab43',p43)
lab43=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab43)

SEED=69071
BOOT=5000
BLOCK=50
COST_STRESS=[0.0,0.5,1.0,2.0]

def metrics(a): return lab43.metrics(np.asarray(a,float))

@njit(cache=True)
def boot_pair(control,modified,starts,block_len):
    B=starts.shape[0]; nb=starts.shape[1]; n=len(control)
    ds=np.zeros(B); ddd=np.zeros(B); drdd=np.zeros(B)
    for b in range(B):
        sc=0.;sm=0.;eqc=0.;eqm=0.;pkc=0.;pkm=0.;ddc=0.;ddm=0.;cnt=0
        for z in range(nb):
            st=starts[b,z]
            for j in range(block_len):
                if cnt>=n: break
                idx=(st+j)%n
                xc=control[idx];xm=modified[idx]
                sc+=xc;sm+=xm
                eqc+=xc;eqm+=xm
                if eqc>pkc:pkc=eqc
                if eqm>pkm:pkm=eqm
                d1=pkc-eqc;d2=pkm-eqm
                if d1>ddc:ddc=d1
                if d2>ddm:ddm=d2
                cnt+=1
            if cnt>=n: break
        rc=sc/ddc if ddc>0 else 99.
        rm=sm/ddm if ddm>0 else 99.
        ds[b]=sm-sc
        ddd[b]=ddm-ddc
        drdd[b]=rm-rc
    return ds,ddd,drdd

def quantiles(x):
    return {
      'median':float(np.median(x)),
      'p10':float(np.quantile(x,0.10)),
      'p90':float(np.quantile(x,0.90)),
    }

def period_map(d,period):
    t=pd.to_datetime(d.signal_ts,unit='s',utc=True)
    keys=t.dt.year.astype(str) if period=='historical' else t.dt.strftime('%Y-%m')
    rows=[]
    for key in sorted(keys.unique()):
        g=d[keys==key]
        c=metrics(g.R.to_numpy(float));m=metrics(g.modified_R.to_numpy(float))
        rows.append({
          'period':period,'subperiod':str(key),'N':len(g),'actions':int(g.acted.sum()),
          'control_SumR':c['SumR'],'modified_SumR':m['SumR'],'delta_SumR':m['SumR']-c['SumR'],
          'control_MaxDD':c['MaxDD_R'],'modified_MaxDD':m['MaxDD_R'],
          'control_R_DD':c['R_DD'],'modified_R_DD':m['R_DD'],'delta_R_DD':m['R_DD']-c['R_DD'],
          'control_PF':c['PF'],'modified_PF':m['PF']
        })
    return rows

def main():
    df=pd.read_csv(SRC)
    df['acted']=df.acted.astype(bool)
    all_cost=[]; boot_rows=[]; stability=[]; checks={}

    for period in ['historical','forward_2026']:
        d=df[df.period==period].sort_values('signal_ts').reset_index(drop=True)
        c=d.R.to_numpy(float); base=d.modified_R.to_numpy(float)
        cm=metrics(c)

        for bps in COST_STRESS:
            extra=np.zeros(len(d),float)
            mask=d.acted.to_numpy(bool)
            extra[mask]=0.5*(bps/10000.0)*d.loc[mask,'entry_price'].to_numpy(float)/(1.5*d.loc[mask,'entry_atr'].to_numpy(float))
            rr=base-extra
            m=metrics(rr)
            all_cost.append({
              'period':period,'extra_bps_on_reduced_half':bps,'actions':int(mask.sum()),
              **m,
              'delta_SumR_vs_control':m['SumR']-cm['SumR'],
              'delta_MaxDD_vs_control':m['MaxDD_R']-cm['MaxDD_R'],
              'delta_R_DD_vs_control':m['R_DD']-cm['R_DD'],
              'sumR_ratio_vs_control':m['SumR']/cm['SumR'] if cm['SumR']!=0 else np.nan
            })

        rng=np.random.default_rng(SEED + (0 if period=='historical' else 1))
        nb=int(np.ceil(len(d)/BLOCK))
        starts=rng.integers(0,len(d),size=(BOOT,nb),dtype=np.int64)
        ds,ddd,drdd=boot_pair(c,base,starts,BLOCK)
        br={
          'period':period,'replicates':BOOT,'block_len':BLOCK,
          'sumR_delta':quantiles(ds),
          'maxDD_delta':quantiles(ddd),
          'R_DD_delta':quantiles(drdd),
          'prob_R_DD_delta_gt_0':float(np.mean(drdd>0)),
          'prob_SumR_delta_gt_0':float(np.mean(ds>0)),
          'prob_MaxDD_delta_lt_0':float(np.mean(ddd<0))
        }
        boot_rows.append(br)

        c1=[x for x in all_cost if x['period']==period and x['extra_bps_on_reduced_half']==1.0][0]
        checks[period]={
          'cost_1bps_R_DD_not_worse':bool(c1['delta_R_DD_vs_control']>=0),
          'cost_1bps_SumR_ge_98pct':bool(c1['sumR_ratio_vs_control']>=0.98),
          'bootstrap_median_R_DD_delta_gt_0':bool(br['R_DD_delta']['median']>0),
          'bootstrap_prob_R_DD_gt_0_ge_0p60':bool(br['prob_R_DD_delta_gt_0']>=0.60)
        }
        stability += period_map(d,period)

    costdf=pd.DataFrame(all_cost);costdf.to_csv(OUT/'cost_stress.csv',index=False)
    stab=pd.DataFrame(stability);stab.to_csv(OUT/'stability_map.csv',index=False)
    (OUT/'bootstrap.json').write_text(json.dumps(boot_rows,indent=2))
    promotion=all(all(v.values()) for v in checks.values())

    result={
      'lab':'LAB071_LAB070_FIXED_RULE_ROBUSTNESS',
      'checks':checks,
      'DEMO_CANDIDATE':bool(promotion),
      'bootstrap':boot_rows,
      'limitations':[
        'Rule parameters are frozen from LAB070; no retuning.',
        'Block bootstrap resamples paired 50-trade chronological blocks with wrap-around.',
        'Extra cost stress is applied only to the 50% reduction leg.',
        '2026 Mar-Aug is reused shadow/stress, not pristine OOS.',
        'BTCUSDT only; broker-specific spread/slippage still requires demo validation.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB071 — LAB070 FIXED-RULE ROBUSTNESS','',
      '## Cost stress','',costdf.to_markdown(index=False),'',
      '## Bootstrap','',json.dumps(boot_rows,indent=2),'',
      '## Stability map','',stab.to_markdown(index=False),'',
      '## Checks','',json.dumps(checks,indent=2),'',
      f'DEMO candidate: **{promotion}**','',
      '## Limitations']+[f'- {x}' for x in result['limitations']]
    ))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
