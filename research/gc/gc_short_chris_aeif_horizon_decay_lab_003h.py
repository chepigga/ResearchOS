#!/usr/bin/env python3
"""LAB003H — horizon-decay audit for frozen Chris/AEIF SHORT events."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path('research/gc')
BASE = ROOT / 'gc_m1_orderflow_edge_discovery_003.py'
EVENTS = ROOT / 'GC_SHORT_CHRIS_AEIF_BUY_FAILURE_LAB_003_EVENTS.csv'
OUT_JSON = ROOT / 'GC_SHORT_CHRIS_AEIF_HORIZON_DECAY_LAB_003H.json'
OUT_MD = ROOT / 'GC_SHORT_CHRIS_AEIF_HORIZON_DECAY_LAB_003H.md'
OUT_CSV = ROOT / 'GC_SHORT_CHRIS_AEIF_HORIZON_DECAY_LAB_003H_EVENTS.csv'

TRAIN_END = pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END = pd.Timestamp('2026-09-06T22:00:00Z')
LATE_END = pd.Timestamp('2026-09-11T12:46:00Z')
HORIZONS = (1,3,5,10,15,30)


def load_base():
    spec = importlib.util.spec_from_file_location('edge003_h003h', BASE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def period(df, name):
    t = pd.to_datetime(df.seed_time, utc=True)
    if name == 'TRAIN': return df[t < TRAIN_END]
    if name == 'VALID': return df[(t >= TRAIN_END) & (t < VALID_END)]
    if name == 'LATE_CHECK': return df[(t >= VALID_END) & (t <= LATE_END)]
    if name == 'POST_CHECK': return df[t > LATE_END]
    if name == 'FULL': return df
    raise ValueError(name)


def metric(df, h):
    col=f'fwd_{h}m_atr'
    v=df[col].dropna().to_numpy(float)
    if not len(v):
        return {'n':0,'ev':None,'median':None,'wr':None,'sum':None}
    return {'n':int(len(v)),'ev':float(v.mean()),'median':float(np.median(v)),
            'wr':float((v>0).mean()*100),'sum':float(v.sum())}


def summarize(df):
    return {p:{str(h):metric(period(df,p),h) for h in HORIZONS}
            for p in ('TRAIN','VALID','LATE_CHECK','POST_CHECK','FULL')}


def fmt(x): return 'NA' if x is None else f'{x:+.5f}'


def enrich(events, bars):
    b=bars.copy()
    b['time']=pd.to_datetime(b.time, utc=True)
    idx={t:i for i,t in enumerate(b.time)}
    rows=[]
    for r in events.itertuples(index=False):
        et=pd.Timestamp(r.entry_time)
        if et.tzinfo is None: et=et.tz_localize('UTC')
        else: et=et.tz_convert('UTC')
        i=idx.get(et)
        if i is None: continue
        row=r._asdict()
        ep=float(r.entry); atr=float(r.seed_atr14)
        for h in HORIZONS:
            j=i+h-1
            if j < len(b) and b.iloc[j].time == et + pd.Timedelta(minutes=h-1):
                row[f'fwd_{h}m_atr']=(ep-float(b.iloc[j].close))/atr
            else:
                row[f'fwd_{h}m_atr']=np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    m=load_base()
    e=pd.read_csv(EVENTS, low_memory=False)
    for c in ('seed_time','confirm_time','entry_time'):
        e[c]=pd.to_datetime(e[c], utc=True)
    work=ROOT/'_chris003h_work'; work.mkdir(parents=True, exist_ok=True)
    rz=work/'rithmic.zip'; az=work/'amp.zip'
    if not rz.exists(): m.download(m.RITH_URL, rz)
    if not az.exists(): m.download(m.AMP_URL, az)
    if m.sha(rz)!=m.RITH_SHA or m.sha(az)!=m.AMP_SHA: raise SystemExit('source SHA mismatch')
    rb=m.load_rithmic(rz); ab=m.load_amp(az)
    re=enrich(e[e.feed.eq('RITHMIC_RAW')].copy(), rb)
    ae=enrich(e[e.feed.eq('AMP_CQG_RAW_EXCLUSIVE')].copy(), ab)
    all_e=pd.concat([re,ae],ignore_index=True)
    all_e.to_csv(OUT_CSV,index=False)
    rs, aas = summarize(re), summarize(ae)

    def best_full(s):
        vals=[(h,s['FULL'][str(h)]['ev']) for h in HORIZONS if s['FULL'][str(h)]['ev'] is not None]
        return max(vals,key=lambda z:z[1]) if vals else (None,None)
    rb_h, rb_ev=best_full(rs); am_h, am_ev=best_full(aas)

    fast_rule=lambda s: all(s['VALID'][str(h)]['ev'] is not None for h in (5,15,30)) and s['VALID']['5']['ev']>s['VALID']['15']['ev'] and s['VALID']['5']['ev']>s['VALID']['30']['ev'] and s['FULL']['5']['ev']>s['FULL']['15']['ev'] and s['FULL']['5']['ev']>s['FULL']['30']['ev']
    fast_consistent=fast_rule(rs) and fast_rule(aas)

    result={'status':'HISTORICAL_HORIZON_DECAY_AUDIT_NOT_OOS','horizons':list(HORIZONS),
            'rithmic':rs,'amp':aas,
            'best_full_horizon':{'rithmic':{'h':rb_h,'ev':rb_ev},'amp':{'h':am_h,'ev':am_ev}},
            'fast_5m_dominance_valid_and_full_both_feeds':bool(fast_consistent)}
    OUT_JSON.write_text(json.dumps(result,indent=2),encoding='utf-8')

    lines=['# GC SHORT CHRIS/AEIF HORIZON DECAY LAB003H','',
           '**Status:** `HISTORICAL_HORIZON_DECAY_AUDIT_NOT_OOS`','',
           'Frozen LAB003 event set; signal definition unchanged.','',
           '## EV by feed / period / horizon','',
           '| Feed | Period | 1m | 3m | 5m | 10m | 15m | 30m |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    for feed,s in (('RITHMIC',rs),('AMP',aas)):
        for p in ('TRAIN','VALID','LATE_CHECK','POST_CHECK','FULL'):
            vals=' | '.join(fmt(s[p][str(h)]['ev']) for h in HORIZONS)
            lines.append(f'| {feed} | {p} | {vals} |')
    lines += ['', '## FULL best horizon (descriptive only)','',
              f'- Rithmic: {rb_h}m, EV {fmt(rb_ev)} ATR',
              f'- AMP: {am_h}m, EV {fmt(am_ev)} ATR', '',
              '## Interpretation','']
    if fast_consistent:
        lines.append('5m dominates 15m and 30m on VALID and FULL on both feeds: evidence supports a fast rejection edge.')
    else:
        lines.append('No strict cross-feed 5m dominance over both 15m and 30m on VALID and FULL. Treat horizon shape as mixed; inspect the full curve rather than selecting a best horizon post hoc.')
    lines += ['', 'This audit cannot promote LAB003 by itself and does not authorize threshold or execution retuning.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result['best_full_horizon'],indent=2))
    print('fast_5m_dominance=',fast_consistent)

if __name__=='__main__': main()
