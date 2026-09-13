#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

LAB='UNIVERSAL_CONTEXT_FROZEN_HEADS_UNSEEN_MARKET_REPLICATION_LAB_005'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB004_PATH=ROOT/'labs'/'UNIVERSAL_CONTEXT_DIRECTIONAL_ASYMMETRY_AND_SEPARATE_BULL_BEAR_HEADS_LAB_004'/'run_lab.py'
SEED=2026091305
BOOT_N=5000
START='2024-09-15T00:00:00Z'
END='2026-09-01T00:00:00Z'
MARKETS={
    'USDJPY':'USDJPY=X',
    'GBPUSD':'GBPUSD=X',
    'AUDUSD':'AUDUSD=X',
    'USDCAD':'CAD=X',
}


def load_lab004():
    spec=importlib.util.spec_from_file_location('lab004',LAB004_PATH)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def epoch(s: str) -> int:
    return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp())


def fetch_yahoo_h1(name: str, ticker: str) -> tuple[pd.DataFrame, dict]:
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
    params={
        'period1':epoch(START),
        'period2':epoch(END),
        'interval':'1h',
        'events':'history',
        'includeAdjustedClose':'false',
    }
    sess=requests.Session()
    sess.headers.update({'User-Agent':'Mozilla/5.0 ResearchOS-LAB005/1.0'})
    r=sess.get(url,params=params,timeout=60)
    raw=r.content
    sha=hashlib.sha256(raw).hexdigest()
    if r.status_code!=200:
        raise RuntimeError(f'{name}: Yahoo HTTP {r.status_code}: {r.text[:500]}')
    obj=r.json()
    err=((obj.get('chart') or {}).get('error'))
    if err:
        raise RuntimeError(f'{name}: Yahoo error: {err}')
    res=((obj.get('chart') or {}).get('result') or [])
    if not res:
        raise RuntimeError(f'{name}: no Yahoo result')
    x=res[0]
    ts=x.get('timestamp') or []
    quote=(((x.get('indicators') or {}).get('quote') or [{}])[0])
    if not ts:
        raise RuntimeError(f'{name}: no timestamps')
    d=pd.DataFrame({
        'time':pd.to_datetime(ts,unit='s',utc=True).tz_convert(None),
        'open':quote.get('open'),
        'high':quote.get('high'),
        'low':quote.get('low'),
        'close':quote.get('close'),
    })
    for c in ['open','high','low','close']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna().drop_duplicates('time').sort_values('time').reset_index(drop=True)
    meta={
        'market':name,'ticker':ticker,'source_url':r.url,'sha256_raw_json':sha,
        'rows_h1':len(d),'first_h1':str(d.time.min()),'last_h1':str(d.time.max()),
        'requested_start':START,'requested_end':END,
    }
    return d,meta


def to_h4(h1: pd.DataFrame) -> pd.DataFrame:
    return (h1.set_index('time').sort_index()
            .resample('4h',origin='epoch',label='left',closed='left')
            .agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'))
            .dropna())


def week_key(df: pd.DataFrame) -> pd.Series:
    return df.market.astype(str)+'|'+pd.to_datetime(df.available_time).dt.to_period('W-SUN').astype(str)


def boot_mean(q: pd.DataFrame, metric: str, seed: int) -> dict:
    q=q[['market','available_time',metric]].copy()
    q[metric]=pd.to_numeric(q[metric],errors='coerce')
    q=q.dropna(subset=[metric])
    obs=float(q[metric].mean()) if len(q) else np.nan
    if q.empty:
        return {'observed':obs,'ci_lo':np.nan,'ci_hi':np.nan,'n':0,'clusters':0}
    q['cluster']=week_key(q)
    st=q.groupby('cluster')[metric].agg(['count','sum']).to_numpy(float)
    rng=np.random.default_rng(seed); draws=[]; m=len(st)
    for _ in range(BOOT_N):
        x=st[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0:
            draws.append(x[1]/x[0])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)),'ci_hi':float(np.quantile(dr,.975)),
            'n':len(q),'clusters':m}


def market_metric(df: pd.DataFrame, metric: str, accuracy=False) -> pd.DataFrame:
    rows=[]
    for m,g in df.groupby('market'):
        v=pd.to_numeric(g[metric],errors='coerce').dropna()
        row={'market':m,'n':len(v)}
        row['accuracy' if accuracy else 'mean']=float(v.mean()) if len(v) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def coverage(all_df: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for m,z in all_df.groupby('market'):
        ex=z[z.regime.eq('EXPANSION')]
        cp=z[z.regime.eq('COMPRESSION')]
        rows.append({
            'market':m,
            'exp_n':len(ex),
            'exp_bull_n':int(ex.exp_bull_signal.sum()),
            'exp_bull_cov':float(ex.exp_bull_signal.mean()) if len(ex) else np.nan,
            'comp_n':len(cp),
            'comp_bear_n':int(cp.comp_bear_signal.sum()),
            'comp_bear_cov':float(cp.comp_bear_signal.mean()) if len(cp) else np.nan,
            'comp_conflict':float(cp.comp_conflict.mean()) if len(cp) else np.nan,
        })
    return pd.DataFrame(rows)


def secondary_table(all_df: pd.DataFrame) -> pd.DataFrame:
    specs=[
        ('EXPANSION_BULL','exp_bull_signal','bull_signed8',False),
        ('EXPANSION_BEAR','exp_bear_signal','bear_signed8',False),
        ('RETRACEMENT_BULL','ret_bull_signal','bull_signed24',False),
        ('RETRACEMENT_BEAR','ret_bear_signal','bear_signed24',False),
        ('COMPRESSION_BULL','comp_bull_signal','comp_bull_correct',True),
        ('COMPRESSION_BEAR','comp_bear_signal','comp_bear_correct',True),
    ]
    rows=[]
    for head,flag,metric,is_acc in specs:
        q=all_df[all_df[flag]].copy()
        if head.startswith('COMPRESSION_'):
            q=q[q.fp_resolved]
        for m,g in q.groupby('market'):
            v=pd.to_numeric(g[metric],errors='coerce').dropna()
            rows.append({'head':head,'market':m,'n':len(v),
                         'metric':'accuracy' if is_acc else 'mean_signed_atr',
                         'value':float(v.mean()) if len(v) else np.nan})
    return pd.DataFrame(rows)


def evaluate(markets: dict[str,pd.DataFrame], audits: list[dict], out: Path, lab4):
    lab2=lab4.load_lab002(); base=lab2.load_base()
    frames=[]; meta=[]
    for market,h4 in markets.items():
        z=lab2.add_forward(lab2.add_engine(h4,base))
        z=lab4.add_outcomes(lab4.add_heads(z))
        z['market']=market
        ready=z[z.regime.isin(['EXPANSION','RETRACEMENT','COMPRESSION','TRANSITION'])].copy()
        frames.append(ready)
        meta.append({'market':market,'h4_rows':len(h4),'ready_bars':len(ready),
                     'first_h4':str(h4.index.min()),'last_h4':str(h4.index.max())})
    all_df=pd.concat(frames).sort_values(['market','available_time'])
    meta_df=pd.DataFrame(meta)

    if any(meta_df.ready_bars<500):
        verdict='DATA_BLOCKED'
        summary={'lab':LAB,'verdict':verdict,'reason':'<500 ready H4 bars in required market'}
        out.mkdir(parents=True,exist_ok=True)
        meta_df.to_csv(out/'market_meta.csv',index=False)
        (out/'data_audit.json').write_text(json.dumps(audits,indent=2))
        (out/'summary.json').write_text(json.dumps(summary,indent=2))
        (out/'REPORT.md').write_text(f'# {LAB}\n**Verdict: {verdict}**\n')
        print(json.dumps(summary,indent=2)); return

    # Primary A: frozen Expansion BULL.
    eb=all_df[all_df.exp_bull_signal].copy()
    eb_rows=market_metric(eb,'bull_signed8',False)
    p_eb=boot_mean(eb,'bull_signed8',SEED+1)
    eligible_eb=eb_rows[eb_rows.n>=50]
    h1=bool(len(eligible_eb)>=3 and int((eligible_eb['mean']>0).sum())>=3 and
            not (eligible_eb['mean']<-.05).any() and p_eb['n']>=250 and
            np.isfinite(p_eb['ci_lo']) and p_eb['ci_lo']>0)

    # Primary B: frozen Compression BEAR.
    cb=all_df[all_df.comp_bear_signal & all_df.fp_resolved].copy()
    cb_rows=market_metric(cb,'comp_bear_correct',True)
    p_cb=boot_mean(cb,'comp_bear_correct',SEED+2)
    eligible_cb=cb_rows[cb_rows.n>=10]
    cb_underpowered=bool(len(eligible_cb)<3 or p_cb['n']<60)
    if cb_underpowered:
        h2=False; h2_status='UNDERPOWERED'
    else:
        h2=bool(int((eligible_cb.accuracy>.5).sum())>=3 and not (eligible_cb.accuracy<.45).any() and
                np.isfinite(p_cb['ci_lo']) and p_cb['ci_lo']>.5)
        h2_status='PASS' if h2 else 'FAIL'

    cov=coverage(all_df)
    h3=bool(((cov.exp_bull_cov>=.05)&(cov.exp_bull_cov<=.70)&
             (cov.comp_bear_cov>=.005)&(cov.comp_bear_cov<=.15)).all())

    if h1 and h2 and h3:
        verdict='FROZEN_HEADS_UNSEEN_REPLICATION_SUPPORTED'
    elif h1 and h3 and cb_underpowered:
        verdict='EXPANSION_BULL_REPLICATED_COMPRESSION_BEAR_UNDERPOWERED'
    elif h1 and h3 and (not cb_underpowered) and (not h2):
        verdict='EXPANSION_BULL_REPLICATED_COMPRESSION_BEAR_FAILED'
    else:
        verdict='UNSEEN_REPLICATION_NOT_SUPPORTED'

    # Secondary frozen heads.
    secondary=secondary_table(all_df)

    # Expansion BULL yearly stability.
    y=eb.copy(); y['year']=pd.to_datetime(y.available_time).dt.year
    yearly=[]
    for (m,yr),g in y.groupby(['market','year']):
        v=g.bull_signed8.dropna(); yearly.append({'market':m,'year':int(yr),'n':len(v),'mean':float(v.mean()) if len(v) else np.nan})
    yearly_df=pd.DataFrame(yearly)

    summary={
        'lab':LAB,'verdict':verdict,
        'h1_expansion_bull_replication':h1,
        'h2_compression_bear_status':h2_status,
        'h2_compression_bear_pass':h2,
        'h3_coverage_sanity':h3,
        'pool_expansion_bull':p_eb,
        'pool_compression_bear_accuracy':p_cb,
        'unseen_markets':list(MARKETS.keys()),
        'data_window':[START,END],
    }

    out.mkdir(parents=True,exist_ok=True)
    meta_df.to_csv(out/'market_meta.csv',index=False)
    eb_rows.to_csv(out/'expansion_bull_by_market.csv',index=False)
    cb_rows.to_csv(out/'compression_bear_by_market.csv',index=False)
    cov.to_csv(out/'coverage.csv',index=False)
    secondary.to_csv(out/'secondary_frozen_heads.csv',index=False)
    yearly_df.to_csv(out/'expansion_bull_yearly.csv',index=False)
    (out/'data_audit.json').write_text(json.dumps(audits,indent=2))
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    lines=[
        f'# {LAB}',f'**Verdict: {verdict}**','',
        '## Primary gates',
        f'- H1 frozen EXPANSION_BULL unseen replication: **{"PASS" if h1 else "FAIL"}** — pooled {p_eb["observed"]:+.4f} ATR, CI [{p_eb["ci_lo"]:+.4f}, {p_eb["ci_hi"]:+.4f}], N={p_eb["n"]}.',
        f'- H2 frozen COMPRESSION_BEAR unseen replication: **{h2_status}** — pooled accuracy {100*p_cb["observed"]:.2f}%, CI [{100*p_cb["ci_lo"]:.2f}%, {100*p_cb["ci_hi"]:.2f}%], N={p_cb["n"]}.',
        f'- H3 coverage sanity: **{"PASS" if h3 else "FAIL"}**.','',
        '## Market data','',meta_df.to_markdown(index=False),'',
        '## EXPANSION_BULL — unseen markets','',eb_rows.to_markdown(index=False,floatfmt='.4f'),'',
        '## COMPRESSION_BEAR — unseen markets','',cb_rows.to_markdown(index=False,floatfmt='.4f'),'',
        '## Coverage','',cov.to_markdown(index=False,floatfmt='.4f'),'',
        '## Secondary frozen LAB004 heads','',secondary.to_markdown(index=False,floatfmt='.4f'),'',
        '## EXPANSION_BULL yearly diagnostic','',yearly_df.to_markdown(index=False,floatfmt='.4f'),'',
        '## Boundary',
        'No unseen outcome was used to change a score, threshold, market, horizon, geometry definition, or verdict rule. This is market-OOS semantic replication only; it does not establish executable P/L or FTMO execution economics.'
    ]
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2,default=str))


def main():
    lab4=load_lab004(); markets={}; audits=[]
    for name,ticker in MARKETS.items():
        h1,meta=fetch_yahoo_h1(name,ticker); audits.append(meta); markets[name]=to_h4(h1)
    evaluate(markets,audits,HERE/'output',lab4)


if __name__=='__main__':
    main()
