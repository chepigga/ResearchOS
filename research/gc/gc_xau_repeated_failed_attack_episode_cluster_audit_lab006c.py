#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
SRC=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005_EVENTS.csv'
OUT_JSON=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_EPISODE_CLUSTER_AUDIT_LAB006C.json'
OUT_MD=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_EPISODE_CLUSTER_AUDIT_LAB006C.md'
GAPS=(120,300,600)

def cluster_ids(df,gap_s,same_direction):
    x=df.sort_values('gc_t0_ms').copy().reset_index(drop=True)
    ids=[];cid=-1;last_t=None;last_d=None
    for r in x.itertuples(index=False):
        t=int(r.gc_t0_ms);d=int(r.direction)
        new = last_t is None or (t-last_t)>gap_s*1000 or (same_direction and d!=last_d)
        if new: cid+=1
        ids.append(cid);last_t=t;last_d=d
    x['cluster_id']=ids
    return x

def summarize_clusters(x):
    g=x.groupby('cluster_id',sort=True)
    rows=[]
    for cid,z in g:
        t=z.gc_t0_ms.to_numpy(np.int64)
        rows.append({
          'cluster_id':int(cid),'n_signals':int(len(z)),
          'span_s':float((t.max()-t.min())/1000),
          'has2':bool(z.hit2.any()),'has3':bool(z.hit3.any()),
          'n2':int(z.hit2.sum()),'n3':int(z.hit3.sum()),
          'first_day':pd.to_datetime(int(t.min()),unit='ms',utc=True).date().isoformat()
        })
    c=pd.DataFrame(rows)
    n=len(c)
    days=max(1,c.first_day.nunique()) if n else 1
    win2=c[c.has2];win3=c[c.has3]
    return {
      'signals':int(len(x)),'clusters':int(n),'days':int(days),
      'clusters_per_day':float(n/days) if days else None,
      'median_signals_per_cluster':float(c.n_signals.median()) if n else None,
      'mean_signals_per_cluster':float(c.n_signals.mean()) if n else None,
      'p90_signals_per_cluster':float(c.n_signals.quantile(.90)) if n else None,
      'median_cluster_span_s':float(c.span_s.median()) if n else None,
      'singleton_share':float((c.n_signals==1).mean()) if n else None,
      'cluster_plus2_share':float(c.has2.mean()) if n else None,
      'cluster_plus3_share':float(c.has3.mean()) if n else None,
      'median_plus2_signals_in_winning_cluster':float(win2.n2.median()) if len(win2) else None,
      'median_plus3_signals_in_winning_cluster':float(win3.n3.median()) if len(win3) else None,
    }

def main():
    d=pd.read_csv(SRC)
    d=d[d.variant=='MARKET_NOW'].drop_duplicates('gc_t0_ms').copy()
    out={}
    for subset in ('ALL','QUIET'):
        base=d if subset=='ALL' else d[d.quiet_start==True]
        out[subset]={}
        for mode,samedir in (('TIME_ONLY',False),('SAME_DIRECTION',True)):
            out[subset][mode]={}
            for gap in GAPS:
                x=cluster_ids(base,gap,samedir)
                out[subset][mode][str(gap)]=summarize_clusters(x)
    OUT_JSON.write_text(json.dumps({'lab':'GC_XAU_REPEATED_FAILED_ATTACK_EPISODE_CLUSTER_AUDIT_LAB006C','results':out},indent=2),encoding='utf-8')

    def f(x,d=1):
        return 'NA' if x is None else f'{x:.{d}f}'
    lines=['# GC_XAU_REPEATED_FAILED_ATTACK_EPISODE_CLUSTER_AUDIT_LAB006C','',
           'Descriptive clustering of frozen LAB005 causal signals.','',
           '| Subset | Mode | Gap | Signals | Clusters | Cl/day | Med sig/cluster | P90 sig/cluster | Singleton | +2 clusters | +3 clusters |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for subset in ('ALL','QUIET'):
        for mode in ('TIME_ONLY','SAME_DIRECTION'):
            for gap in GAPS:
                x=out[subset][mode][str(gap)]
                lines.append(f"| {subset} | {mode} | {gap//60}m | {x['signals']} | {x['clusters']} | {f(x['clusters_per_day'])} | {f(x['median_signals_per_cluster'])} | {f(x['p90_signals_per_cluster'])} | {f(x['singleton_share']*100)}% | {f(x['cluster_plus2_share']*100)}% | {f(x['cluster_plus3_share']*100)}% |")
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
