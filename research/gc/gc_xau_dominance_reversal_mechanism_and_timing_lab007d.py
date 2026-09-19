#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
SRC=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005_EVENTS.csv'
OUT_JSON=ROOT/'GC_XAU_DOMINANCE_REVERSAL_MECHANISM_AND_TIMING_LAB007D.json'
OUT_MD=ROOT/'GC_XAU_DOMINANCE_REVERSAL_MECHANISM_AND_TIMING_LAB007D.md'
OUT_EVENTS=ROOT/'GC_XAU_DOMINANCE_REVERSAL_MECHANISM_AND_TIMING_LAB007D_EVENTS.csv'
ANCHOR_MS=300000

def pf(v):
    x=np.asarray([a for a in v if np.isfinite(a)],float)
    if not len(x): return None
    p=x[x>0].sum();n=-x[x<0].sum()
    if n==0:return float('inf') if p>0 else None
    return float(p/n)

def stat(v):
    x=np.asarray([a for a in v if np.isfinite(a)],float)
    return {'n':int(len(x)),'ev':float(x.mean()) if len(x) else None,'median':float(np.median(x)) if len(x) else None,'wr':float((x>0).mean()*100) if len(x) else None,'pf':pf(x)}

def load_unique():
    d=pd.read_csv(SRC)
    return d[d.variant=='MARKET_NOW'].drop_duplicates('gc_t0_ms').sort_values('gc_t0_ms').reset_index(drop=True)

def assign_anchored(d):
    rows=[];eid=0;i=0;n=len(d)
    while i<n:
        anchor=int(d.loc[i,'gc_t0_ms']);end=anchor+ANCHOR_MS;j=i
        while j<n and int(d.loc[j,'gc_t0_ms'])<=end:
            r=d.loc[j].to_dict();r['episode_id']=eid;r['anchor_ms']=anchor;rows.append(r);j+=1
        eid+=1;i=j
    return pd.DataFrame(rows)

def is_dom_reversal(z):
    dirs=z.direction.astype(int).tolist()
    return len(dirs)>=4 and dirs[0]==dirs[1] and dirs[-1]==dirs[-2] and dirs[-1]==-dirs[0]

def parse_fp(r,col):
    v=r.get(col,np.nan)
    return float(v) if pd.notna(v) else np.nan

def build_episode_rows(x):
    rows=[]
    for eid,z in x.groupby('episode_id',sort=True):
        z=z.sort_values('gc_t0_ms').reset_index(drop=True)
        if not is_dom_reversal(z):continue
        dom=int(z.loc[0,'direction']);rev=-dom
        rev_idx=[i for i,d in enumerate(z.direction.astype(int)) if i>=2 and d==rev]
        if not rev_idx:continue
        r1i=rev_idx[0]
        r2i=rev_idx[1] if len(rev_idx)>=2 else None
        last_dom_idx=max(i for i in range(r1i) if int(z.loc[i,'direction'])==dom)
        for label,idx in [('REV1',r1i),('REV2',r2i)]:
            if idx is None:continue
            r=z.loc[idx]
            prevdom=z.loc[last_dom_idx]
            same=True  # prediction equals source signal direction for reversal clocks
            rec={
              'episode_id':int(eid),'clock':label,'period':r.period,'gc_t0_ms':int(r.gc_t0_ms),
              'dominance_dir':dom,'reversal_dir':rev,'signal_index':int(idx+1),
              'elapsed_from_anchor_s':float((int(r.gc_t0_ms)-int(z.anchor_ms.iloc[0]))/1000),
              'elapsed_from_last_dom_s':float((int(r.gc_t0_ms)-int(prevdom.gc_t0_ms))/1000),
              'quiet_start':bool(r.quiet_start),
              'impact_deterioration':float(r.impact_deterioration),
              'attack1_impact':float(r.attack1_impact),'attack2_impact':float(r.attack2_impact),
              'dominance_count_before':int(sum(int(z.loc[k,'direction'])==dom for k in range(idx))),
              'reversal_count_so_far':int(sum(int(z.loc[k,'direction'])==rev for k in range(idx+1))),
              'delta_impact_change_vs_last_dom':float(r.impact_deterioration-prevdom.impact_deterioration),
              'hit2':bool(r.hit2),'hit3':bool(r.hit3),
              'fixed5m_ev_atr':float(r.hold300_atr) if pd.notna(r.hold300_atr) else np.nan,
              'mfe5_atr':float(r.mfe5_atr) if pd.notna(r.mfe5_atr) else np.nan,
              'mae5_atr':float(r.mae5_atr) if pd.notna(r.mae5_atr) else np.nan,
            }
            for th in ('0.25','0.50','1.00','2.00','3.00'):
                rec[f'fp_pos_{th}_ms']=parse_fp(r,f'fp_pos_{th}_ms')
            for th in ('0.25','0.50','1.00'):
                rec[f'fp_neg_{th}_ms']=parse_fp(r,f'fp_neg_{th}_ms')
            rows.append(rec)
    return pd.DataFrame(rows)

def summarize(ev):
    out={}
    for clock in ('REV1','REV2'):
        out[clock]={}
        for p in ('TRAIN','VALID','POST_CHECK','FULL'):
            z=ev[ev.clock==clock] if p=='FULL' else ev[(ev.clock==clock)&(ev.period==p)]
            plus2=z[z.hit2==True]
            t50=plus2['fp_pos_0.50_ms'].dropna().to_numpy(float)/1000 if len(plus2) else np.array([])
            out[clock][p]={
              'n':int(len(z)),
              'hit2_rate':float(z.hit2.mean()) if len(z) else None,
              'hit3_rate':float(z.hit3.mean()) if len(z) else None,
              'fixed5m':stat(z.fixed5m_ev_atr.to_numpy(float)) if len(z) else stat([]),
              'mfe5':stat(z.mfe5_atr.to_numpy(float)) if len(z) else stat([]),
              'mae5':stat(z.mae5_atr.to_numpy(float)) if len(z) else stat([]),
              'median_t50_plus2_s':float(np.median(t50)) if len(t50) else None,
              'median_elapsed_anchor_s':float(z.elapsed_from_anchor_s.median()) if len(z) else None,
              'quiet_share':float(z.quiet_start.mean()) if len(z) else None
            }
    return out

def limit_stats(ev,depth):
    # approximate from LAB005 market-row path: use MAE/MFE to assess fill potential only; no executable re-sim possible from ledger.
    # To keep LAB007D honest, report unavailable rather than fabricate.
    return None

def gate(s):
    out={}
    for clock in ('REV1','REV2'):
        tr=s[clock]['TRAIN'];va=s[clock]['VALID']
        c={
          'train_n_ge40':tr['n']>=40,'valid_n_ge40':va['n']>=40,
          'train_ev_pos':tr['fixed5m']['ev'] is not None and tr['fixed5m']['ev']>0,
          'valid_ev_nonneg':va['fixed5m']['ev'] is not None and va['fixed5m']['ev']>=0,
          'train_hit2_ge20':tr['hit2_rate'] is not None and tr['hit2_rate']>=.20,
          'valid_hit2_ge20':va['hit2_rate'] is not None and va['hit2_rate']>=.20,
          'valid_t50_ge15':va['median_t50_plus2_s'] is not None and va['median_t50_plus2_s']>=15,
        }
        c['pass']=all(c.values());out[clock]=c
    return out

def main():
    d=load_unique();x=assign_anchored(d);ev=build_episode_rows(x)
    ev.to_csv(OUT_EVENTS,index=False)
    s=summarize(ev);g=gate(s)
    survivors=[k for k,v in g.items() if v['pass']]

    mech={}
    for clock in ('REV1','REV2'):
        mech[clock]={}
        for p in ('TRAIN','VALID','POST_CHECK'):
            z=ev[(ev.clock==clock)&(ev.period==p)]
            mech[clock][p]={
              'n':int(len(z)),
              'quiet_share':float(z.quiet_start.mean()) if len(z) else None,
              'median_elapsed_from_last_dom_s':float(z.elapsed_from_last_dom_s.median()) if len(z) else None,
              'median_impact_deterioration':float(z.impact_deterioration.median()) if len(z) else None,
              'median_change_vs_last_dom':float(z.delta_impact_change_vs_last_dom.median()) if len(z) else None,
              'median_dom_count_before':float(z.dominance_count_before.median()) if len(z) else None,
              'median_rev_count':float(z.reversal_count_so_far.median()) if len(z) else None,
            }

    out={'lab':'GC_XAU_DOMINANCE_REVERSAL_MECHANISM_AND_TIMING_LAB007D','status':'MECHANISM_TIMING_AUDIT_NOT_OOS','summary':s,'mechanism':mech,'gates':g,'survivors':survivors,'limit_benchmarks':'NOT_COMPUTED_FROM_LEDGER_ONLY'}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(v,d=3):
        return 'NA' if v is None else f'{v:.{d}f}'
    lines=['# GC_XAU_DOMINANCE_REVERSAL_MECHANISM_AND_TIMING_LAB007D','',
           'Status: MECHANISM_TIMING_AUDIT_NOT_OOS','',
           '| Clock | Period | N | +2ATR | +3ATR | Fixed5m EV | PF | Med t+0.5 on +2 winners | Quiet | Med from last dominance | Gate |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for clock in ('REV1','REV2'):
        for p in ('TRAIN','VALID','POST_CHECK'):
            z=s[clock][p];m=mech[clock][p]
            lines.append(f"| {clock} | {p} | {z['n']} | {f(None if z['hit2_rate'] is None else z['hit2_rate']*100,1)}% | {f(None if z['hit3_rate'] is None else z['hit3_rate']*100,1)}% | {f(z['fixed5m']['ev'])} | {f(z['fixed5m']['pf'])} | {f(z['median_t50_plus2_s'],1)}s | {f(None if m['quiet_share'] is None else m['quiet_share']*100,1)}% | {f(m['median_elapsed_from_last_dom_s'],1)}s | {'PASS' if g[clock]['pass'] else 'FAIL'} |")
    lines+=['','## Mechanism medians','',
            '| Clock | Period | Impact deterioration | Change vs last dominance | Dom signals before | Rev signals so far |',
            '|---|---|---:|---:|---:|---:|']
    for clock in ('REV1','REV2'):
        for p in ('TRAIN','VALID','POST_CHECK'):
            m=mech[clock][p]
            lines.append(f"| {clock} | {p} | {f(m['median_impact_deterioration'])} | {f(m['median_change_vs_last_dom'])} | {f(m['median_dom_count_before'],1)} | {f(m['median_rev_count'],1)} |")
    lines+=['',f"Timing survivors: {survivors if survivors else 'NONE'}",'',
            'LIMIT_REV2 benchmarks were intentionally not approximated from the LAB005 ledger because exact post-REV2 executable tick path is required. No SL/TP optimization performed.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
