#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
SRC=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009_EVENTS.csv'
OUT_JSON=ROOT/'GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C.json'
OUT_MD=ROOT/'GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C.md'
OUT_CSV=ROOT/'GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C_GRID.csv'

QS=[0.60,0.65,0.70,0.75,0.80]

def pf(vals):
    x=np.asarray([v for v in vals if np.isfinite(v)],float)
    if not len(x): return None
    p=x[x>0].sum(); n=-x[x<0].sum()
    if n==0:return float('inf') if p>0 else None
    return float(p/n)

def stats(z,base_n):
    n=len(z)
    vals=z.fixed5m_atr.to_numpy(float) if n else np.array([])
    return {
      'n':int(n),
      'retention':float(n/base_n) if base_n else None,
      'hit2':float(z.hit2.mean()) if n else None,
      'hit3':float(z.hit3.mean()) if n else None,
      'ev':float(np.nanmean(vals)) if n else None,
      'pf':pf(vals)
    }

def fmt(v,d=3):
    if v is None or (isinstance(v,float) and not np.isfinite(v)): return 'NA'
    return f'{v:.{d}f}'

def main():
    d=pd.read_csv(SRC)

    d5=d[d.window_s==5].copy()
    d30=d[d.window_s==30].copy()

    keep5=['gc_t0_ms','period','post_signed_impulse_atr','hit2','hit3','fixed5m_atr']
    keep30=['gc_t0_ms','period','post_volume','post_aligned_volume','hit2','hit3','fixed5m_atr']
    a=d5[keep5].rename(columns={'hit2':'hit2_5','hit3':'hit3_5','fixed5m_atr':'fixed5m_atr_5'})
    b=d30[keep30].rename(columns={'hit2':'hit2_30','hit3':'hit3_30','fixed5m_atr':'fixed5m_atr_30'})
    m=a.merge(b,on=['gc_t0_ms','period'],how='inner')

    thresholds={}
    tr5=d5[d5.period=='TRAIN']
    tr30=d30[d30.period=='TRAIN']
    for q in QS:
        key=f'Q{int(q*100)}'
        thresholds[key]={
          'impulse':float(tr5.post_signed_impulse_atr.quantile(q)),
          'volume':float(tr30.post_volume.quantile(q)),
          'aligned_volume':float(tr30.post_aligned_volume.quantile(q))
        }

    base={}
    for clock,dd in [('5s',d5),('30s',d30)]:
        base[clock]={}
        for p in ('TRAIN','VALID','POST_CHECK'):
            z=dd[dd.period==p]
            base[clock][p]=stats(z,len(z))

    rows=[]
    families=['IMPULSE','VOLUME','ALIGNED_VOLUME','IMPULSE_AND_VOLUME','IMPULSE_AND_ALIGNED_VOLUME']
    for q in QS:
        qk=f'Q{int(q*100)}';th=thresholds[qk]
        for fam in families:
            for p in ('TRAIN','VALID','POST_CHECK'):
                if fam=='IMPULSE':
                    z0=d5[d5.period==p].copy(); base_n=len(z0)
                    z=z0[z0.post_signed_impulse_atr>=th['impulse']].copy()
                    z=z.rename(columns={'fixed5m_atr':'fixed5m_atr'})
                    clock='5s'
                elif fam=='VOLUME':
                    z0=d30[d30.period==p].copy(); base_n=len(z0)
                    z=z0[z0.post_volume>=th['volume']].copy(); clock='30s'
                elif fam=='ALIGNED_VOLUME':
                    z0=d30[d30.period==p].copy(); base_n=len(z0)
                    z=z0[z0.post_aligned_volume>=th['aligned_volume']].copy(); clock='30s'
                else:
                    z0=m[m.period==p].copy(); base_n=len(z0)
                    if fam=='IMPULSE_AND_VOLUME':
                        z=z0[(z0.post_signed_impulse_atr>=th['impulse']) & (z0.post_volume>=th['volume'])].copy()
                    else:
                        z=z0[(z0.post_signed_impulse_atr>=th['impulse']) & (z0.post_aligned_volume>=th['aligned_volume'])].copy()
                    z=z.rename(columns={'hit2_30':'hit2','hit3_30':'hit3','fixed5m_atr_30':'fixed5m_atr'})
                    clock='30s'
                s=stats(z,base_n)
                rows.append({'family':fam,'q':int(q*100),'clock':clock,'period':p,**s})

    g=pd.DataFrame(rows)
    g.to_csv(OUT_CSV,index=False)

    stability={}
    for fam in families:
        stability[fam]={'positive_plateaus':[],'robust_plateaus':[]}
        qvals=[int(q*100) for q in QS]
        good=[];rob=[]
        for q in qvals:
            tr=g[(g.family==fam)&(g.q==q)&(g.period=='TRAIN')].iloc[0]
            va=g[(g.family==fam)&(g.q==q)&(g.period=='VALID')].iloc[0]
            clock=tr.clock
            btr=base[clock]['TRAIN']['hit2']; bva=base[clock]['VALID']['hit2']
            good.append(bool(tr.ev>0 and va.ev>0))
            rob.append(bool(tr.ev>0 and va.ev>0 and tr.hit2>btr and va.hit2>bva))
        for arr,name in [(good,'positive_plateaus'),(rob,'robust_plateaus')]:
            start=None
            for i,v in enumerate(arr+[False]):
                if v and start is None:start=i
                if (not v) and start is not None:
                    if i-start>=3:
                        stability[fam][name].append([qvals[start],qvals[i-1]])
                    start=None

    intersections=[]
    for fam in ('IMPULSE_AND_VOLUME','IMPULSE_AND_ALIGNED_VOLUME'):
        for q in [int(x*100) for x in QS]:
            tr=g[(g.family==fam)&(g.q==q)&(g.period=='TRAIN')].iloc[0]
            va=g[(g.family==fam)&(g.q==q)&(g.period=='VALID')].iloc[0]
            po=g[(g.family==fam)&(g.q==q)&(g.period=='POST_CHECK')].iloc[0]
            intersections.append({
              'family':fam,'q':q,
              'train_n':int(tr.n),'valid_n':int(va.n),'post_n':int(po.n),
              'train_hit2':float(tr.hit2) if pd.notna(tr.hit2) else None,
              'valid_hit2':float(va.hit2) if pd.notna(va.hit2) else None,
              'post_hit2':float(po.hit2) if pd.notna(po.hit2) else None,
              'train_ev':float(tr.ev) if pd.notna(tr.ev) else None,
              'valid_ev':float(va.ev) if pd.notna(va.ev) else None,
              'post_ev':float(po.ev) if pd.notna(po.ev) else None,
              'train_pf':float(tr.pf) if pd.notna(tr.pf) else None,
              'valid_pf':float(va.pf) if pd.notna(va.pf) else None,
              'post_pf':float(po.pf) if pd.notna(po.pf) else None,
              'valid_n_ge12':bool(va.n>=12)
            })

    out={'lab':'GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C',
         'status':'THRESHOLD_STABILITY_INTERSECTION_NOT_OOS',
         'thresholds':thresholds,'base':base,'stability':stability,'intersections':intersections}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    lines=['# GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C','',
           'Status: THRESHOLD_STABILITY_INTERSECTION_NOT_OOS','',
           '## TRAIN-frozen thresholds','',
           '| Q | 5s impulse | 30s volume | 30s aligned volume |',
           '|---:|---:|---:|---:|']
    for q in [int(x*100) for x in QS]:
        th=thresholds[f'Q{q}']
        lines.append(f"| Q{q} | {fmt(th['impulse'],4)} | {fmt(th['volume'],2)} | {fmt(th['aligned_volume'],2)} |")
    lines+=['','## Threshold surface','',
            '| Family | Q | Period | N | Retain | +2ATR | +3ATR | EV ATR | PF |',
            '|---|---:|---|---:|---:|---:|---:|---:|---:|']
    for fam in families:
        for q in [int(x*100) for x in QS]:
            for p in ('TRAIN','VALID','POST_CHECK'):
                r=g[(g.family==fam)&(g.q==q)&(g.period==p)].iloc[0]
                lines.append(f"| {fam} | Q{q} | {p} | {int(r.n)} | {fmt(r.retention*100,1)}% | {fmt(r.hit2*100 if pd.notna(r.hit2) else None,1)}% | {fmt(r.hit3*100 if pd.notna(r.hit3) else None,1)}% | {fmt(r.ev)} | {fmt(r.pf)} |")
    lines+=['','## Plateau diagnostics','']
    for fam in families:
        lines.append(f"- {fam}: positive={stability[fam]['positive_plateaus'] or 'NONE'}; robust={stability[fam]['robust_plateaus'] or 'NONE'}")
    lines+=['','Intersections with VALID N<12 are descriptive only. No production winner selected.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
