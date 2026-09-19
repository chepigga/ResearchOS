#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
SRC=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005_EVENTS.csv'
OUT_JSON=ROOT/'GC_XAU_ANCHORED_EPISODE_STRUCTURAL_CLASSES_LAB007C.json'
OUT_MD=ROOT/'GC_XAU_ANCHORED_EPISODE_STRUCTURAL_CLASSES_LAB007C.md'
OUT_EVENTS=ROOT/'GC_XAU_ANCHORED_EPISODE_STRUCTURAL_CLASSES_LAB007C_EVENTS.csv'

ANCHOR_MS=300000
CLASSES=('SPARSE','ONE_SIDED_BUILDUP','DOMINANCE_REVERSAL','ALTERNATING_CONFLICT','REASSERTION','MIXED_TRANSITION')

def pf(v):
    x=np.asarray([a for a in v if np.isfinite(a)],float)
    if not len(x): return None
    p=x[x>0].sum(); n=-x[x<0].sum()
    if n==0:return float('inf') if p>0 else None
    return float(p/n)

def load_unique():
    d=pd.read_csv(SRC)
    d=d[d.variant=='MARKET_NOW'].drop_duplicates('gc_t0_ms').sort_values('gc_t0_ms').reset_index(drop=True)
    return d

def assign_anchored(d):
    rows=[];eid=0;i=0;n=len(d)
    while i<n:
        anchor=int(d.loc[i,'gc_t0_ms']); end=anchor+ANCHOR_MS
        j=i
        while j<n and int(d.loc[j,'gc_t0_ms'])<=end:
            r=d.loc[j].to_dict(); r['episode_id']=eid; r['anchor_ms']=anchor; rows.append(r); j+=1
        eid+=1;i=j
    return pd.DataFrame(rows)

def run_stats(dirs):
    if not dirs:return 0,0
    flips=sum(int(dirs[i]!=dirs[i-1]) for i in range(1,len(dirs)))
    longest=1;cur=1
    for i in range(1,len(dirs)):
        if dirs[i]==dirs[i-1]:
            cur+=1;longest=max(longest,cur)
        else:cur=1
    final_run=1
    for i in range(len(dirs)-2,-1,-1):
        if dirs[i]==dirs[-1]:final_run+=1
        else:break
    return flips,longest,final_run

def dominant(dirs):
    s=sum(dirs)
    return 1 if s>0 else (-1 if s<0 else 0)

def classify(n,balance,flips,dirs,final_run,dom):
    if n<=2:return 'SPARSE'
    if n>=3 and balance>=.67 and flips<=1:return 'ONE_SIDED_BUILDUP'
    if n>=4 and dirs[0]==dirs[1] and dirs[-1]==dirs[-2] and dirs[-1]==-dirs[0]:
        return 'DOMINANCE_REVERSAL'
    if n>=4 and flips>=2 and balance<=.33:return 'ALTERNATING_CONFLICT'
    if n>=4 and flips>=1 and final_run>=2 and dom!=0 and dirs[-1]==dom:
        return 'REASSERTION'
    return 'MIXED_TRANSITION'

def build_episodes(x):
    rows=[]
    for eid,z in x.groupby('episode_id',sort=True):
        z=z.sort_values('gc_t0_ms').reset_index(drop=True)
        dirs=[int(v) for v in z.direction.tolist()]
        n=len(dirs); longs=sum(d>0 for d in dirs); shorts=n-longs
        bal=abs(longs-shorts)/n
        flips,longest,final_run=run_stats(dirs)
        dom=dominant(dirs)
        half=max(1,n//2)
        first_dom=dominant(dirs[:half]); second_dom=dominant(dirs[half:])
        det=pd.to_numeric(z.impact_deterioration,errors='coerce')
        first_det=float(det.iloc[:half].mean()) if len(det.iloc[:half].dropna()) else np.nan
        second_det=float(det.iloc[half:].mean()) if len(det.iloc[half:].dropna()) else np.nan
        quiet_share=float(z.quiet_start.astype(bool).mean())
        cls=classify(n,bal,flips,dirs,final_run,dom)

        last=z.iloc[-1]
        pred=None
        if cls in ('ONE_SIDED_BUILDUP','DOMINANCE_REVERSAL','REASSERTION'):
            pred=int(dirs[-1])

        pos2=bool(pd.notna(last.get('fp_pos_2.00_ms',np.nan)))
        neg2=bool(pd.notna(last.get('fp_neg_2.00_ms',np.nan)))
        pos3=bool(pd.notna(last.get('fp_pos_3.00_ms',np.nan)))
        neg3=bool(pd.notna(last.get('fp_neg_3.00_ms',np.nan)))
        any2=pos2 or neg2
        any3=pos3 or neg3

        dir2=dir3=np.nan; hold=np.nan
        if pred is not None:
            same=pred==int(last.direction)
            dir2=pos2 if same else neg2
            dir3=pos3 if same else neg3
            hold=float(last.hold300_atr) if pd.notna(last.hold300_atr) else np.nan
            if not same and np.isfinite(hold):hold=-hold

        rows.append({
          'episode_id':int(eid),'class':cls,
          'anchor_ms':int(z.anchor_ms.iloc[0]),'end_ms':int(last.gc_t0_ms),
          'period':last.period,'n_signals':n,'long_count':longs,'short_count':shorts,
          'directional_balance':bal,'flips':flips,'longest_run':longest,'final_run':final_run,
          'first_direction':dirs[0],'last_direction':dirs[-1],'dominant_direction':dom,
          'first_half_dominant':first_dom,'second_half_dominant':second_dom,
          'mean_impact_deterioration':float(det.mean()) if len(det.dropna()) else np.nan,
          'first_half_impact_deterioration':first_det,'second_half_impact_deterioration':second_det,
          'quiet_share':quiet_share,'predicted_direction':pred if pred is not None else 0,
          'any2':bool(any2),'any3':bool(any3),
          'dir2':dir2,'dir3':dir3,'fixed5m_ev_atr':hold
        })
    return pd.DataFrame(rows)

def summarize(ep):
    out={}
    for cls in CLASSES:
        out[cls]={}
        for p in ('TRAIN','VALID','POST_CHECK','FULL'):
            z=ep[ep['class']==cls] if p=='FULL' else ep[(ep['class']==cls)&(ep.period==p)]
            pred=z[z.predicted_direction!=0]
            vals=pred.fixed5m_ev_atr.dropna().to_numpy(float)
            out[cls][p]={
              'n':int(len(z)),
              'share':None,
              'any2_rate':float(z.any2.mean()) if len(z) else None,
              'any3_rate':float(z.any3.mean()) if len(z) else None,
              'dir_n':int(len(pred)),
              'dir2_rate':float(pred.dir2.astype(float).mean()) if len(pred) else None,
              'dir3_rate':float(pred.dir3.astype(float).mean()) if len(pred) else None,
              'fixed5m_ev':float(vals.mean()) if len(vals) else None,
              'fixed5m_pf':pf(vals)
            }
        for p in ('TRAIN','VALID','POST_CHECK','FULL'):
            denom=len(ep) if p=='FULL' else len(ep[ep.period==p])
            out[cls][p]['share']=float(out[cls][p]['n']/denom) if denom else None
    return out

def main():
    d=load_unique();x=assign_anchored(d);ep=build_episodes(x)
    ep.to_csv(OUT_EVENTS,index=False)
    res=summarize(ep)

    interesting=[]
    for cls in CLASSES:
        tr=res[cls]['TRAIN'];va=res[cls]['VALID']
        expansion_ok=(tr['any2_rate'] is not None and va['any2_rate'] is not None and tr['any2_rate']>=.30 and va['any2_rate']>=.30)
        directional_ok=(tr['dir_n']>=100 and va['dir_n']>=100 and tr['dir2_rate'] is not None and va['dir2_rate'] is not None and tr['dir2_rate']>=.25 and va['dir2_rate']>=.25 and tr['fixed5m_ev'] is not None and va['fixed5m_ev'] is not None and tr['fixed5m_ev']>0 and va['fixed5m_ev']>0)
        if expansion_ok or directional_ok:
            interesting.append({'class':cls,'expansion_candidate':expansion_ok,'directional_candidate':directional_ok})

    out={'lab':'GC_XAU_ANCHORED_EPISODE_STRUCTURAL_CLASSES_LAB007C','status':'STRUCTURAL_TAXONOMY_NOT_OOS','results':res,'interesting_classes':interesting}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(v,d=1):
        return 'NA' if v is None else f'{v:.{d}f}'
    lines=['# GC_XAU_ANCHORED_EPISODE_STRUCTURAL_CLASSES_LAB007C','',
           'Status: STRUCTURAL_TAXONOMY_NOT_OOS','',
           '| Class | Period | N | Share | Any +2ATR | Any +3ATR | Dir N | Dir +2ATR | Dir +3ATR | Fixed5m EV | PF |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cls in CLASSES:
        for p in ('TRAIN','VALID','POST_CHECK'):
            z=res[cls][p]
            lines.append(f"| {cls} | {p} | {z['n']} | {f(None if z['share'] is None else z['share']*100)}% | {f(None if z['any2_rate'] is None else z['any2_rate']*100)}% | {f(None if z['any3_rate'] is None else z['any3_rate']*100)}% | {z['dir_n']} | {f(None if z['dir2_rate'] is None else z['dir2_rate']*100)}% | {f(None if z['dir3_rate'] is None else z['dir3_rate']*100)}% | {f(z['fixed5m_ev'],3)} | {f(z['fixed5m_pf'],3)} |")
    lines+=['',f"Interesting classes: {interesting if interesting else 'NONE'}",'','Classes use GC episode structure only; no XAU outcome enters taxonomy. No execution optimization.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
