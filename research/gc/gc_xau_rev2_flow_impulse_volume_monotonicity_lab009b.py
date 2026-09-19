#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
SRC=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009_EVENTS.csv'
OUT_JSON=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_MONOTONICITY_LAB009B.json'
OUT_MD=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_MONOTONICITY_LAB009B.md'
OUT_CSV=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_MONOTONICITY_LAB009B_BINS.csv'

FEATURES=[
 (5,'post_signed_impulse_atr'),
 (30,'volume_acceleration'),
 (30,'post_volume'),
 (30,'post_aligned_volume'),
 (0,'attack2_volume'),
]

def fmt(v,d=3):
    if v is None or (isinstance(v,float) and not np.isfinite(v)): return 'NA'
    return f'{v:.{d}f}'

def bin_label(x,q33,q67):
    if pd.isna(x): return None
    if x<=q33:return 'LOW'
    if x<q67:return 'MID'
    return 'HIGH'

def stats(z):
    n=len(z)
    return {
      'n':int(n),
      'hit2':float(z.hit2.mean()) if n else None,
      'hit3':float(z.hit3.mean()) if n else None,
      'ev':float(z.fixed5m_atr.mean()) if n else None
    }

def main():
    d=pd.read_csv(SRC)
    results=[]
    summary={}
    strong=[]
    for w,feat in FEATURES:
        sub=d[(d.window_s==w) & d[feat].notna()].copy()
        tr=sub[sub.period=='TRAIN']
        q33=float(tr[feat].quantile(1/3))
        q67=float(tr[feat].quantile(2/3))
        sub['bin']=sub[feat].apply(lambda x:bin_label(x,q33,q67))
        summary[f'{w}s:{feat}']={'q33':q33,'q67':q67,'periods':{}}
        for p in ('TRAIN','VALID','POST_CHECK'):
            zp=sub[sub.period==p]
            summary[f'{w}s:{feat}']['periods'][p]={}
            for b in ('LOW','MID','HIGH'):
                s=stats(zp[zp['bin']==b])
                summary[f'{w}s:{feat}']['periods'][p][b]=s
                results.append({'window_s':w,'feature':feat,'period':p,'bin':b,'q33':q33,'q67':q67,**s})
        t=summary[f'{w}s:{feat}']['periods']['TRAIN']
        v=summary[f'{w}s:{feat}']['periods']['VALID']
        train_mono=(t['HIGH']['hit2'] is not None and t['MID']['hit2'] is not None and t['LOW']['hit2'] is not None and
                    t['HIGH']['hit2']>t['MID']['hit2']>t['LOW']['hit2'] and
                    t['HIGH']['ev']>t['MID']['ev']>t['LOW']['ev'])
        valid_sep=(v['HIGH']['hit2'] is not None and v['LOW']['hit2'] is not None and
                   v['HIGH']['hit2']>v['LOW']['hit2'] and v['HIGH']['ev']>v['LOW']['ev'])
        gate=(train_mono and valid_sep and t['HIGH']['n']>=15 and v['HIGH']['n']>=15 and
              t['HIGH']['ev'] is not None and v['HIGH']['ev'] is not None and
              t['HIGH']['ev']>0 and v['HIGH']['ev']>0)
        summary[f'{w}s:{feat}']['train_monotonic']=train_mono
        summary[f'{w}s:{feat}']['valid_high_gt_low']=valid_sep
        summary[f'{w}s:{feat}']['strong_candidate']=gate
        if gate: strong.append({'window_s':w,'feature':feat,'q33':q33,'q67':q67})

    pd.DataFrame(results).to_csv(OUT_CSV,index=False)
    out={'lab':'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_MONOTONICITY_LAB009B',
         'status':'MONOTONICITY_AUDIT_NOT_OOS',
         'features':summary,'strong_candidates':strong}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    lines=['# GC_XAU_REV2_FLOW_IMPULSE_VOLUME_MONOTONICITY_LAB009B','',
           'Status: MONOTONICITY_AUDIT_NOT_OOS','',
           '| Clock | Feature | Period | LOW N/+2/EV | MID N/+2/EV | HIGH N/+2/EV | Train monotonic | Valid H>L | Strong |',
           '|---:|---|---|---|---|---|---|---|---|']
    for w,feat in FEATURES:
        key=f'{w}s:{feat}'
        info=summary[key]
        for p in ('TRAIN','VALID','POST_CHECK'):
            z=info['periods'][p]
            def cell(b):
                s=z[b]
                return f"{s['n']}/{fmt(None if s['hit2'] is None else s['hit2']*100,1)}%/{fmt(s['ev'])}"
            lines.append(f"| {w}s | {feat} | {p} | {cell('LOW')} | {cell('MID')} | {cell('HIGH')} | {info['train_monotonic']} | {info['valid_high_gt_low']} | {info['strong_candidate']} |")
    lines+=['',f"Strong candidates: {strong if strong else 'NONE'}",'',
            'Thresholds are TRAIN-only terciles and remain frozen in VALID/POST. No combinations or execution optimization.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
