#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
SRC=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005_EVENTS.csv'
OUT_JSON=ROOT/'GC_XAU_ANCHORED_5MIN_EPISODE_AND_RESOLUTION_STATE_LAB007B.json'
OUT_MD=ROOT/'GC_XAU_ANCHORED_5MIN_EPISODE_AND_RESOLUTION_STATE_LAB007B.md'
OUT_EVENTS=ROOT/'GC_XAU_ANCHORED_5MIN_EPISODE_AND_RESOLUTION_STATE_LAB007B_EVENTS.csv'

ANCHOR_MS=300000
RULES=(
 'R1_EARLY_DOMINANCE_3',
 'R2_EARLY_QUIET_DOMINANCE_3',
 'R3_RUN3_BEFORE240',
 'R4_DOMINANCE_THEN_OPPOSITE_FLIP',
 'R5_DOMINANCE_REASSERT_AFTER_FLIP'
)

def pf(v):
    x=np.asarray(v,float)
    p=x[x>0].sum(); n=-x[x<0].sum()
    if n==0:return float('inf') if p>0 else None
    return float(p/n)

def stat(v):
    x=np.asarray([a for a in v if np.isfinite(a)],float)
    return {
      'n':int(len(x)),
      'ev':float(x.mean()) if len(x) else None,
      'median':float(np.median(x)) if len(x) else None,
      'wr':float((x>0).mean()*100) if len(x) else None,
      'pf':pf(x) if len(x) else None
    }

def load_unique():
    d=pd.read_csv(SRC)
    d=d[d.variant=='MARKET_NOW'].drop_duplicates('gc_t0_ms').sort_values('gc_t0_ms').reset_index(drop=True)
    return d

def assign_anchored(d):
    rows=[]; eid=0; i=0; n=len(d)
    while i<n:
        anchor=int(d.loc[i,'gc_t0_ms'])
        end=anchor+ANCHOR_MS
        j=i
        while j<n and int(d.loc[j,'gc_t0_ms'])<=end:
            r=d.loc[j].to_dict(); r['episode_id']=eid; r['anchor_ms']=anchor; rows.append(r); j+=1
        eid+=1; i=j
    return pd.DataFrame(rows)

def enrich_state(x):
    rows=[]
    for eid,z in x.groupby('episode_id',sort=True):
        z=z.sort_values('gc_t0_ms').reset_index(drop=True)
        long_n=short_n=flips=0; run=0; prev=None; dets=[]
        for idx,r in z.iterrows():
            cur=int(r.direction)
            prev_long=long_n; prev_short=short_n
            dom_before=1 if prev_long>prev_short else (-1 if prev_short>prev_long else 0)
            if cur>0: long_n+=1
            else: short_n+=1
            if prev is None or cur!=prev:
                if prev is not None: flips+=1
                run=1
            else:
                run+=1
            total=long_n+short_n
            bal=abs(long_n-short_n)/total
            dom=1 if long_n>short_n else (-1 if short_n>long_n else 0)
            det=float(r.impact_deterioration) if pd.notna(r.impact_deterioration) else np.nan
            if np.isfinite(det): dets.append(det)
            rows.append({
              **r.to_dict(),
              'signal_index':idx+1,
              'elapsed_s':(int(r.gc_t0_ms)-int(r.anchor_ms))/1000.0,
              'cum_long':long_n,'cum_short':short_n,
              'directional_balance':bal,
              'dominant_direction':dom,
              'dominant_before_current':dom_before,
              'run_length_same_direction':run,
              'direction_flips_so_far':flips,
              'previous_direction':0 if prev is None else prev,
              'current_equals_dominant':bool(dom!=0 and cur==dom),
              'cum_mean_impact_deterioration':float(np.mean(dets)) if dets else np.nan
            })
            prev=cur
    return pd.DataFrame(rows)

def rule_prediction(r,rule):
    total=int(r.signal_index); elapsed=float(r.elapsed_s); cur=int(r.direction)
    dom=int(r.dominant_direction); dom_before=int(r.dominant_before_current)
    prev=int(r.previous_direction); bal=float(r.directional_balance); flips=int(r.direction_flips_so_far)

    if rule=='R1_EARLY_DOMINANCE_3':
        if total>=3 and elapsed<=180 and bal>=.67 and dom!=0 and cur==dom:
            return cur
    elif rule=='R2_EARLY_QUIET_DOMINANCE_3':
        if total>=3 and elapsed<=180 and bal>=.67 and dom!=0 and cur==dom and bool(r.quiet_start):
            return cur
    elif rule=='R3_RUN3_BEFORE240':
        if int(r.run_length_same_direction)>=3 and elapsed<=240:
            return cur
    elif rule=='R4_DOMINANCE_THEN_OPPOSITE_FLIP':
        if total>=4 and dom_before!=0 and prev==dom_before and cur==-dom_before:
            return cur
    elif rule=='R5_DOMINANCE_REASSERT_AFTER_FLIP':
        if total>=4 and flips>=1 and dom!=0 and cur==dom and prev==-dom and elapsed<=300:
            return cur
    return None

def emit_setups(s):
    rows=[]
    for eid,z in s.groupby('episode_id',sort=True):
        z=z.sort_values('gc_t0_ms')
        for rule in RULES:
            pick=None; pred=None
            for r in z.itertuples(index=False):
                p=rule_prediction(r,rule)
                if p is not None:
                    pick=r; pred=int(p); break
            if pick is None: continue

            base_dir=int(pick.direction)
            same = pred==base_dir
            hit2=bool(pick.hit2) if same else bool(np.isfinite(getattr(pick,'fp_neg_2.00_ms',np.nan)))
            hit3=bool(pick.hit3) if same else bool(np.isfinite(getattr(pick,'fp_neg_3.00_ms',np.nan)))
            hit1=bool(np.isfinite(getattr(pick,'fp_pos_1.00_ms',np.nan))) if same else bool(np.isfinite(getattr(pick,'fp_neg_1.00_ms',np.nan)))

            hold=float(pick.hold300_atr) if pd.notna(pick.hold300_atr) else np.nan
            mfe=float(pick.mfe5_atr) if pd.notna(pick.mfe5_atr) else np.nan
            mae=float(pick.mae5_atr) if pd.notna(pick.mae5_atr) else np.nan
            if not same:
                hold=-hold
                mfe,mae = -mae,-mfe

            rows.append({
              'episode_id':int(eid),'rule':rule,
              'gc_t0_ms':int(pick.gc_t0_ms),'event_utc':pick.event_utc,'period':pick.period,
              'prediction':pred,'source_signal_direction':base_dir,
              'quiet_start':bool(pick.quiet_start),
              'signal_index':int(pick.signal_index),'elapsed_s':float(pick.elapsed_s),
              'directional_balance':float(pick.directional_balance),
              'run_length_same_direction':int(pick.run_length_same_direction),
              'direction_flips_so_far':int(pick.direction_flips_so_far),
              'hit1':hit1,'hit2':hit2,'hit3':hit3,
              'fixed5m_ev_atr':hold,'mfe5_atr':mfe,'mae5_atr':mae
            })
    return pd.DataFrame(rows)

def summarize(setups):
    out={}
    for rule in RULES:
        out[rule]={}
        for p in ('TRAIN','VALID','POST_CHECK','FULL'):
            z=setups[setups.rule==rule] if p=='FULL' else setups[(setups.rule==rule)&(setups.period==p)]
            out[rule][p]={
              'n':int(len(z)),
              'hit1_rate':float(z.hit1.mean()) if len(z) else None,
              'hit2_rate':float(z.hit2.mean()) if len(z) else None,
              'hit3_rate':float(z.hit3.mean()) if len(z) else None,
              'fixed5m':stat(z.fixed5m_ev_atr.to_numpy(float)) if len(z) else stat([]),
              'mfe5':stat(z.mfe5_atr.to_numpy(float)) if len(z) else stat([]),
              'mae5':stat(z.mae5_atr.to_numpy(float)) if len(z) else stat([]),
              'median_emit_index':float(z.signal_index.median()) if len(z) else None,
              'median_elapsed_s':float(z.elapsed_s.median()) if len(z) else None
            }
    return out

def gate(x):
    tr=x['TRAIN']; va=x['VALID']
    c={
      'train_n_ge100':tr['n']>=100,
      'valid_n_ge100':va['n']>=100,
      'train_hit2_ge25':tr['hit2_rate'] is not None and tr['hit2_rate']>=.25,
      'valid_hit2_ge25':va['hit2_rate'] is not None and va['hit2_rate']>=.25,
      'train_hit3_ge09':tr['hit3_rate'] is not None and tr['hit3_rate']>=.09,
      'valid_hit3_ge09':va['hit3_rate'] is not None and va['hit3_rate']>=.09,
      'train_ev_pos':tr['fixed5m']['ev'] is not None and tr['fixed5m']['ev']>0,
      'valid_ev_pos':va['fixed5m']['ev'] is not None and va['fixed5m']['ev']>0,
      'valid_pf_ge110':va['fixed5m']['pf'] is not None and va['fixed5m']['pf']>=1.10
    }
    c['pass']=all(c.values())
    return c

def main():
    d=load_unique()
    x=assign_anchored(d)
    s=enrich_state(x)
    setups=emit_setups(s)
    setups.to_csv(OUT_EVENTS,index=False)
    res=summarize(setups)
    gates={r:gate(res[r]) for r in RULES}
    survivors=[r for r in RULES if gates[r]['pass']]

    eps=x.groupby('episode_id').agg(start_ms=('gc_t0_ms','min'),end_ms=('gc_t0_ms','max'),signals=('gc_t0_ms','size')).reset_index()
    ep_summary={
      'episodes':int(len(eps)),
      'median_signals':float(eps.signals.median()),
      'mean_signals':float(eps.signals.mean()),
      'p90_signals':float(eps.signals.quantile(.9)),
      'median_span_s':float(((eps.end_ms-eps.start_ms)/1000).median()),
      'max_span_s':float(((eps.end_ms-eps.start_ms)/1000).max())
    }

    out={'lab':'GC_XAU_ANCHORED_5MIN_EPISODE_AND_RESOLUTION_STATE_LAB007B','status':'ANCHORED_EPISODE_DISCOVERY_NOT_OOS','episode_summary':ep_summary,'results':res,'gates':gates,'survivors':survivors}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(v,d=3):
        return 'NA' if v is None else f'{v:.{d}f}'
    lines=['# GC_XAU_ANCHORED_5MIN_EPISODE_AND_RESOLUTION_STATE_LAB007B','',
           'Status: ANCHORED_EPISODE_DISCOVERY_NOT_OOS','',
           f"Episodes: {ep_summary['episodes']}; median signals/episode {ep_summary['median_signals']:.1f}; median span {ep_summary['median_span_s']:.1f}s; max span {ep_summary['max_span_s']:.1f}s",'',
           '| Rule | Period | N | +1ATR | +2ATR | +3ATR | Fixed5m EV | PF | Med emit idx | Med elapsed | Gate |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for rule in RULES:
        for p in ('TRAIN','VALID','POST_CHECK'):
            z=res[rule][p]
            lines.append(f"| {rule} | {p} | {z['n']} | {f(None if z['hit1_rate'] is None else z['hit1_rate']*100,1)}% | {f(None if z['hit2_rate'] is None else z['hit2_rate']*100,1)}% | {f(None if z['hit3_rate'] is None else z['hit3_rate']*100,1)}% | {f(z['fixed5m']['ev'])} | {f(z['fixed5m']['pf'])} | {f(z['median_emit_index'],1)} | {f(z['median_elapsed_s'],1)}s | {'PASS' if gates[rule]['pass'] else 'FAIL'} |")
    lines+=['',f"Survivors: {survivors if survivors else 'NONE'}",'','No limit/SL/TP optimization was performed.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
