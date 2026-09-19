#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
SRC=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005_EVENTS.csv'
OUT_JSON=ROOT/'GC_XAU_TRAPPED_CROWD_EPISODE_STATE_AND_FINAL_DIRECTION_LAB007.json'
OUT_MD=ROOT/'GC_XAU_TRAPPED_CROWD_EPISODE_STATE_AND_FINAL_DIRECTION_LAB007.md'
OUT_EVENTS=ROOT/'GC_XAU_TRAPPED_CROWD_EPISODE_STATE_AND_FINAL_DIRECTION_LAB007_EVENTS.csv'

GAP_MS=300000
RULES=('R1_DOMINANCE_3','R2_DOMINANCE_5','R3_RUN3','R4_FINAL_FLIP_TO_DOMINANT','R5_QUIET_DOMINANCE_3')

def pf(v):
    x=np.asarray(v,float)
    p=x[x>0].sum();n=-x[x<0].sum()
    if n==0:return float('inf') if p>0 else None
    return float(p/n)

def stat(v):
    x=np.asarray([a for a in v if np.isfinite(a)],float)
    return {'n':int(len(x)),'ev':float(x.mean()) if len(x) else None,'median':float(np.median(x)) if len(x) else None,'wr':float((x>0).mean()*100) if len(x) else None,'pf':pf(x) if len(x) else None}

def build_unique():
    d=pd.read_csv(SRC)
    d=d[d.variant=='MARKET_NOW'].drop_duplicates('gc_t0_ms').sort_values('gc_t0_ms').reset_index(drop=True)
    return d

def assign_episodes(d):
    ep=[];cid=-1;last=None
    for t in d.gc_t0_ms.astype(np.int64):
        if last is None or int(t)-int(last)>GAP_MS: cid+=1
        ep.append(cid);last=int(t)
    x=d.copy();x['episode_id']=ep
    return x

def enrich_state(x):
    rows=[]
    for eid,z in x.groupby('episode_id',sort=True):
        z=z.sort_values('gc_t0_ms').reset_index(drop=True)
        long_n=short_n=flips=0;run=0;prev_dir=None
        dets=[]
        for i,r in z.iterrows():
            d=int(r.direction)
            if d>0:long_n+=1
            else:short_n+=1
            if prev_dir is None or d!=prev_dir:
                if prev_dir is not None:flips+=1
                run=1
            else:
                run+=1
            total=long_n+short_n
            bal=abs(long_n-short_n)/total
            dom=1 if long_n>short_n else (-1 if short_n>long_n else 0)
            det=float(r.impact_deterioration) if pd.notna(r.impact_deterioration) else np.nan
            if np.isfinite(det):dets.append(det)
            rows.append({
              **r.to_dict(),
              'signal_index_in_episode':i+1,
              'elapsed_s':(int(r.gc_t0_ms)-int(z.gc_t0_ms.iloc[0]))/1000.0,
              'cum_long':long_n,'cum_short':short_n,'directional_balance':bal,
              'dominant_direction':dom,'run_length_same_direction':run,
              'direction_flips_so_far':flips,
              'current_equals_dominant':bool(dom!=0 and d==dom),
              'previous_direction':prev_dir if prev_dir is not None else 0,
              'cum_mean_impact_deterioration':float(np.mean(dets)) if dets else np.nan
            })
            prev_dir=d
    return pd.DataFrame(rows)

def rule_hit(r,rule):
    total=int(r.signal_index_in_episode)
    bal=float(r.directional_balance)
    cur=int(r.direction);dom=int(r.dominant_direction)
    if rule=='R1_DOMINANCE_3':
        return total>=3 and bal>=.67 and dom!=0 and cur==dom
    if rule=='R2_DOMINANCE_5':
        return total>=5 and bal>=.60 and dom!=0 and cur==dom
    if rule=='R3_RUN3':
        return int(r.run_length_same_direction)>=3
    if rule=='R4_FINAL_FLIP_TO_DOMINANT':
        return total>=4 and int(r.direction_flips_so_far)>=1 and dom!=0 and cur==dom and int(r.previous_direction)==-dom
    if rule=='R5_QUIET_DOMINANCE_3':
        return total>=3 and bal>=.67 and dom!=0 and cur==dom and bool(r.quiet_start)
    return False

def emit_setups(s):
    rows=[]
    for eid,z in s.groupby('episode_id',sort=True):
        z=z.sort_values('gc_t0_ms')
        for rule in RULES:
            picked=None
            for r in z.itertuples(index=False):
                if rule_hit(r,rule):
                    picked=r;break
            if picked is None:continue
            rows.append({
              'episode_id':int(eid),'rule':rule,'gc_t0_ms':int(picked.gc_t0_ms),
              'event_utc':picked.event_utc,'period':picked.period,
              'direction':int(picked.direction),'quiet_start':bool(picked.quiet_start),
              'signal_index_in_episode':int(picked.signal_index_in_episode),
              'elapsed_s':float(picked.elapsed_s),'directional_balance':float(picked.directional_balance),
              'run_length_same_direction':int(picked.run_length_same_direction),
              'direction_flips_so_far':int(picked.direction_flips_so_far),
              'hit2':bool(picked.hit2),'hit3':bool(picked.hit3),
              'fixed5m_ev_atr':float(picked.hold300_atr) if pd.notna(picked.hold300_atr) else np.nan,
              'mfe5_atr':float(picked.mfe5_atr) if pd.notna(picked.mfe5_atr) else np.nan,
              'mae5_atr':float(picked.mae5_atr) if pd.notna(picked.mae5_atr) else np.nan,
              'hit1':bool(pd.notna(picked['fp_pos_1.00_ms']) if isinstance(picked,pd.Series) else pd.notna(getattr(picked,'_asdict')().get('fp_pos_1.00_ms',np.nan)))
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
              'hit2_rate':float(z.hit2.mean()) if len(z) else None,
              'hit3_rate':float(z.hit3.mean()) if len(z) else None,
              'fixed5m':stat(z.fixed5m_ev_atr.to_numpy(float)) if len(z) else stat([]),
              'mfe5':stat(z.mfe5_atr.to_numpy(float)) if len(z) else stat([]),
              'mae5':stat(z.mae5_atr.to_numpy(float)) if len(z) else stat([]),
              'median_emit_index':float(z.signal_index_in_episode.median()) if len(z) else None,
              'median_elapsed_s':float(z.elapsed_s.median()) if len(z) else None,
            }
    return out

def gate(x):
    tr=x['TRAIN'];va=x['VALID']
    c={
      'train_n_ge100':tr['n']>=100,'valid_n_ge100':va['n']>=100,
      'train_hit2_ge25':tr['hit2_rate'] is not None and tr['hit2_rate']>=.25,
      'valid_hit2_ge25':va['hit2_rate'] is not None and va['hit2_rate']>=.25,
      'train_hit3_ge09':tr['hit3_rate'] is not None and tr['hit3_rate']>=.09,
      'valid_hit3_ge09':va['hit3_rate'] is not None and va['hit3_rate']>=.09,
      'train_ev_pos':tr['fixed5m']['ev'] is not None and tr['fixed5m']['ev']>0,
      'valid_ev_pos':va['fixed5m']['ev'] is not None and va['fixed5m']['ev']>0,
    }
    c['pass']=all(c.values());return c

def main():
    d=build_unique()
    x=assign_episodes(d)
    s=enrich_state(x)
    setups=emit_setups(s)
    setups.to_csv(OUT_EVENTS,index=False)
    res=summarize(setups)
    gates={r:gate(res[r]) for r in RULES}
    survivors=[r for r in RULES if gates[r]['pass']]

    episodes=x.groupby('episode_id').agg(start_ms=('gc_t0_ms','min'),end_ms=('gc_t0_ms','max'),signals=('gc_t0_ms','size')).reset_index()
    episode_summary={'episodes':int(len(episodes)),'median_signals':float(episodes.signals.median()),'mean_signals':float(episodes.signals.mean()),'median_span_s':float(((episodes.end_ms-episodes.start_ms)/1000).median())}

    out={'lab':'GC_XAU_TRAPPED_CROWD_EPISODE_STATE_AND_FINAL_DIRECTION_LAB007','status':'EPISODE_STATE_DISCOVERY_NOT_OOS','episode_summary':episode_summary,'results':res,'gates':gates,'survivors':survivors}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(x,d=3):
        return 'NA' if x is None else f'{x:.{d}f}'
    lines=['# GC_XAU_TRAPPED_CROWD_EPISODE_STATE_AND_FINAL_DIRECTION_LAB007','',
           'Status: EPISODE_STATE_DISCOVERY_NOT_OOS','',
           f"Episodes: {episode_summary['episodes']}; median signals/episode {episode_summary['median_signals']:.1f}; median span {episode_summary['median_span_s']:.1f}s",'',
           '| Rule | Period | N | +2ATR | +3ATR | Fixed5m EV ATR | PF | Med emit idx | Med elapsed | Gate |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for rule in RULES:
        for p in ('TRAIN','VALID','POST_CHECK'):
            z=res[rule][p]
            lines.append(f"| {rule} | {p} | {z['n']} | {f(None if z['hit2_rate'] is None else z['hit2_rate']*100,1)}% | {f(None if z['hit3_rate'] is None else z['hit3_rate']*100,1)}% | {f(z['fixed5m']['ev'])} | {f(z['fixed5m']['pf'])} | {f(z['median_emit_index'],1)} | {f(z['median_elapsed_s'],1)}s | {'PASS' if gates[rule]['pass'] else 'FAIL'} |")
    lines+=['',f"Survivors: {survivors if survivors else 'NONE'}",'','No limit/SL/TP optimization was performed.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
