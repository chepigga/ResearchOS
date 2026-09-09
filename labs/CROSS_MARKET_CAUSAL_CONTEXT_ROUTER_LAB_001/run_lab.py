#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

LAB = 'CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001'
HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'
OUT.mkdir(parents=True, exist_ok=True)
LABS = HERE.parent
SRC53 = LABS / 'BTC_SHORT_ACCEPT25_PERSISTENT_FAILURE_EXIT_VS_SEVERE_ADVERSE1R_EXECUTION_LAB_053' / 'output' / 'execution_stream.csv'
PRE = pd.Timestamp('2026-08-01', tz='UTC')
SEED = 20260909 + 1001
BOOT_N = 3000
PERIODS = ['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']


def pf(v):
    v = np.asarray(v, float)
    gp = v[v > 0].sum(); gl = -v[v < 0].sum()
    return float(gp / gl) if gl > 0 else (float('inf') if gp > 0 else np.nan)


def maxdd(v):
    v = np.asarray(v, float)
    if len(v) == 0: return np.nan
    eq = np.r_[0.0, np.cumsum(v)]
    return float(np.max(np.maximum.accumulate(eq) - eq))


def max_loss_streak(v):
    best = cur = 0
    for x in np.asarray(v, float):
        if x < 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return int(best)


def period_of(t):
    if t.year in [2021, 2022, 2023, 2024]: return str(t.year)
    if t.year == 2025: return '2025_H1' if t < pd.Timestamp('2025-07-01', tz='UTC') else '2025_H2'
    if t.year == 2026 and t < PRE: return '2026_JAN_JUL'
    return 'OTHER'


def wilder(s, n):
    return s.ewm(alpha=1.0/n, adjust=False, min_periods=n).mean()


def indicators(df):
    d = df.copy()
    pc = d.close.shift(1)
    tr = pd.concat([(d.high-d.low).abs(), (d.high-pc).abs(), (d.low-pc).abs()], axis=1).max(axis=1)
    d['atr14'] = wilder(tr, 14)
    d['atr_med50'] = d.atr14.rolling(50, min_periods=25).median()
    d['atr_ratio'] = d.atr14 / d.atr_med50
    for n in [20, 50, 200]:
        d[f'ema{n}'] = d.close.ewm(span=n, adjust=False, min_periods=n).mean()
    d['slope50_atr'] = (d.ema50 - d.ema50.shift(3)) / d.atr14.replace(0, np.nan)

    delta = d.close.diff()
    gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    rs = wilder(gain, 14) / wilder(loss, 14).replace(0, np.nan)
    d['rsi14'] = 100 - 100/(1+rs)

    up = d.high.diff(); dn = -d.low.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=d.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=d.index)
    plus_di = 100 * wilder(plus_dm,14) / d.atr14.replace(0,np.nan)
    minus_di = 100 * wilder(minus_dm,14) / d.atr14.replace(0,np.nan)
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di).replace(0,np.nan)
    d['adx14'] = wilder(dx, 14)

    d['prior_hi20'] = d.high.rolling(20, min_periods=20).max().shift(1)
    d['prior_lo20'] = d.low.rolling(20, min_periods=20).min().shift(1)
    d['breakout'] = (d.close > d.prior_hi20) | (d.close < d.prior_lo20)
    d['sweep'] = ((d.high > d.prior_hi20) & (d.close < d.prior_hi20)) | ((d.low < d.prior_lo20) & (d.close > d.prior_lo20))

    r24 = d.high.rolling(24, min_periods=24).max() - d.low.rolling(24, min_periods=24).min()
    d['range24_ratio'] = r24 / r24.rolling(100, min_periods=50).median().replace(0,np.nan)
    spread = pd.concat([d.ema20,d.ema50,d.ema200],axis=1).max(axis=1) - pd.concat([d.ema20,d.ema50,d.ema200],axis=1).min(axis=1)
    d['ema_spread_atr'] = spread / d.atr14.replace(0,np.nan)
    d['dist20_atr'] = (d.close-d.ema20).abs()/d.atr14.replace(0,np.nan)
    d['dist50_atr'] = (d.close-d.ema50).abs()/d.atr14.replace(0,np.nan)
    d['relvol20'] = d.volume / d.volume.rolling(20, min_periods=10).median().replace(0,np.nan)

    candle_range = (d.high-d.low).replace(0,np.nan)
    upper = d.high - pd.concat([d.open,d.close],axis=1).max(axis=1)
    lower = pd.concat([d.open,d.close],axis=1).min(axis=1) - d.low
    d['rejection_wick'] = pd.concat([upper,lower],axis=1).max(axis=1) / candle_range
    d['cross_ema20'] = ((d.close-d.ema20) * (d.close.shift(1)-d.ema20.shift(1)) < 0)

    d['stack_up'] = (d.ema20>d.ema50)&(d.ema50>d.ema200)&(d.slope50_atr>0)
    d['stack_dn'] = (d.ema20<d.ema50)&(d.ema50<d.ema200)&(d.slope50_atr<0)
    d['stack'] = d.stack_up | d.stack_dn
    d['bias'] = np.select([d.stack_up,d.stack_dn], ['BULL','BEAR'], default='NEUTRAL')
    return d


def add_router(df):
    d = indicators(df)
    s = pd.DataFrame(index=d.index)

    # EXPANSION: fixed preregistered point system.
    exp = pd.Series(0.0,index=d.index)
    exp += 25*d.stack.astype(float)
    exp += 20*d.breakout.astype(float)
    exp += 10*(d.atr_ratio>1.05).astype(float) + 10*(d.atr_ratio>1.20).astype(float)
    exp += 15*(d.adx14>=20).astype(float)
    exp += 10*(d.relvol20>=1.05).astype(float)
    exp += 10*(d.dist20_atr>=0.50).astype(float)
    s['EXPANSION'] = exp.clip(0,100)

    pb = pd.Series(0.0,index=d.index)
    pb += 30*d.stack.astype(float)
    mindist = pd.concat([d.dist20_atr,d.dist50_atr],axis=1).min(axis=1)
    pb += 25*(mindist<=0.65).astype(float) + 15*((mindist>0.65)&(mindist<=1.0)).astype(float)
    pb += 15*((d.rsi14>=35)&(d.rsi14<=65)).astype(float)
    pb += 15*(d.adx14>=18).astype(float)
    pb += 15*((~d.breakout)&(d.atr_ratio<=1.40)).astype(float)
    s['PULLBACK'] = pb.clip(0,100)

    rev = pd.Series(0.0,index=d.index)
    prev_rsi = d.rsi14.shift(1)
    rsi_turn = ((prev_rsi<35)&(d.rsi14>prev_rsi)) | ((prev_rsi>65)&(d.rsi14<prev_rsi))
    rev += 30*d.sweep.astype(float)
    rev += 25*rsi_turn.astype(float)
    rev += 15*d.cross_ema20.astype(float)
    rev += 15*(d.adx14<d.adx14.shift(1)).astype(float)
    rev += 15*(d.rejection_wick>=0.45).astype(float)
    s['REVERSAL'] = rev.clip(0,100)

    rng = pd.Series(0.0,index=d.index)
    rng += 25*(d.adx14<20).astype(float)
    rng += 25*(d.range24_ratio<0.85).astype(float)
    rng += 20*(d.ema_spread_atr<1.0).astype(float)
    rng += 15*(d.atr_ratio<0.95).astype(float)
    rng += 15*(~d.stack).astype(float)
    s['RANGE'] = rng.clip(0,100)

    sm = s.rolling(3,min_periods=3).mean()
    states=[]; confs=[]; cur=None; held=0
    for i,(idx,row) in enumerate(sm.iterrows()):
        if row.isna().all():
            states.append(None); confs.append(np.nan); continue
        scores=row.fillna(-1e9).to_dict()
        if cur is None:
            cur=max(scores,key=scores.get); held=1
        else:
            atrr=d.loc[idx,'atr_ratio']
            if pd.isna(atrr): atrr=1.0
            if atrr<0.80: min_hold,gap=4,12
            elif atrr>1.35: min_hold,gap=2,5
            else: min_hold,gap=3,8
            adjusted=scores.copy(); adjusted[cur]=adjusted.get(cur,-1e9)+5
            challenger=max(adjusted,key=adjusted.get)
            if challenger!=cur and held>=min_hold and adjusted[challenger] > adjusted[cur]+gap:
                cur=challenger; held=1
            else:
                held+=1
        vals=sorted([v for v in scores.values() if np.isfinite(v)],reverse=True)
        conf=(vals[0]-vals[1])/100.0 if len(vals)>=2 else np.nan
        states.append(cur); confs.append(conf)
    d['regime']=states; d['regime_confidence']=confs
    for c in s.columns: d[f'score_{c.lower()}']=s[c]
    # Bar open timestamp is the index; context becomes available only at H4 close.
    d['available_time']=d.index + pd.Timedelta(hours=4)
    return d


def fetch_binance_futures_h1(start='2020-01', end='2026-07'):
    months=pd.period_range(start,end,freq='M')
    frames=[]; missing=[]
    sess=requests.Session(); sess.headers.update({'User-Agent':'ResearchOS-context-router/1.0'})
    cols=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_base','taker_quote','ignore']
    for p in months:
        ym=str(p)
        url=f'https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{ym}.zip'
        try:
            r=sess.get(url,timeout=30)
            if r.status_code!=200:
                missing.append({'month':ym,'status':r.status_code}); continue
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                name=z.namelist()[0]
                raw=pd.read_csv(z.open(name),header=None,names=cols)
                frames.append(raw)
        except Exception as e:
            missing.append({'month':ym,'status':str(e)})
    if not frames:
        raise RuntimeError(f'No Binance archive data downloaded; missing={missing[:5]}')
    x=pd.concat(frames,ignore_index=True)
    ot=pd.to_numeric(x.open_time,errors='coerce')
    # Binance archives may use ms or us timestamps depending on vintage.
    unit='us' if float(ot.dropna().median())>1e14 else 'ms'
    x['time']=pd.to_datetime(ot,unit=unit,utc=True,errors='coerce')
    for c in ['open','high','low','close','volume']:
        x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x[['time','open','high','low','close','volume']].dropna().drop_duplicates('time').sort_values('time')
    meta={'source':'Binance USD-M futures public monthly archive','symbol':'BTCUSDT','interval':'1h','rows':len(x),'first':str(x.time.min()),'last':str(x.time.max()),'missing_months':missing}
    return x,meta


def to_h4(h1):
    x=h1.set_index('time').sort_index()
    h4=x.resample('4h',origin='epoch',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum')).dropna()
    return h4


def load_frozen_trades():
    e=pd.read_csv(SRC53)
    for c in ['signal_time','entry_time','exit_time']:
        e[c]=pd.to_datetime(e[c],utc=True,errors='coerce')
    for c in ['net_r_5bps','net_r_10bps','net_r_0bps']:
        e[c]=pd.to_numeric(e[c],errors='coerce')
    e=e[(e.policy=='PERSISTENT_EXIT')&(e.signal_time<PRE)].copy().sort_values('entry_time')
    e=e.drop_duplicates('flow_id',keep='first')
    e['period']=e.signal_time.map(period_of)
    return e


def attach_context(trades,ctx):
    cols=['available_time','regime','regime_confidence','bias','atr_ratio','adx14','rsi14','ema20','ema50','ema200','score_expansion','score_pullback','score_reversal','score_range']
    c=ctx[cols].dropna(subset=['available_time','regime']).sort_values('available_time').reset_index(drop=False).rename(columns={'time':'h4_open'})
    t=trades.sort_values('entry_time').copy()
    out=pd.merge_asof(t,c,left_on='entry_time',right_on='available_time',direction='backward',allow_exact_matches=True)
    return out


def metrics(q, baseline_n):
    q=q.sort_values('entry_time')
    v=q.net_r_5bps.to_numpy(float)
    dd=maxdd(v) if len(v) else np.nan
    cum=float(np.nansum(v)) if len(v) else 0.0
    p=pf(v) if len(v) else np.nan
    rec=float(cum/dd) if len(v) and dd and np.isfinite(dd) and dd>0 else np.nan
    return dict(trades=int(len(q)),retention=float(len(q)/baseline_n) if baseline_n else np.nan,ev=float(np.nanmean(v)) if len(v) else np.nan,pf=p,cumr=cum,cumr_per_baseline_trade=float(cum/baseline_n) if baseline_n else np.nan,maxdd_r=dd,dd_pct_025=float(dd*0.25) if np.isfinite(dd) else np.nan,dd_pct_050=float(dd*0.50) if np.isfinite(dd) else np.nan,win_rate=float(np.mean(v>0)) if len(v) else np.nan,loss_streak=max_loss_streak(v),recovery_factor=rec)


def cluster_bootstrap(q):
    q=q.sort_values('entry_time').copy()
    if len(q)==0: return {}
    epoch=pd.Timestamp('1970-01-01',tz='UTC')
    q['cluster']=(((q.entry_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    groups=[g.net_r_5bps.to_numpy(float) for _,g in q.groupby('cluster',sort=True)]
    rng=np.random.default_rng(SEED); evs=[]; dds=[]; totals=[]
    m=len(groups)
    for _ in range(BOOT_N):
        idx=rng.integers(0,m,size=m); path=np.concatenate([groups[i] for i in idx])
        evs.append(float(path.mean())); dds.append(maxdd(path)); totals.append(float(path.sum()))
    return dict(clusters=m,draws=BOOT_N,ev_ci_lo=float(np.quantile(evs,.025)),ev_ci_hi=float(np.quantile(evs,.975)),dd_p50=float(np.quantile(dds,.50)),dd_p95=float(np.quantile(dds,.95)),total_ci_lo=float(np.quantile(totals,.025)),total_ci_hi=float(np.quantile(totals,.975)))


def scan_xau_native_data():
    root=HERE.parents[1]
    candidates=[]
    for pat in ['*XAU*.csv','*xau*.csv','*XAU*.parquet','*xau*.parquet']:
        for p in root.rglob(pat):
            if '/output/' in str(p).replace('\\','/'): continue
            candidates.append(str(p.relative_to(root)))
    # Existing XAU research lineage explicitly expects this file.
    expected=root/'xau_historical_bars_cleaned.csv'
    status={'expected_path':str(expected.relative_to(root)),'found_expected':expected.exists(),'other_candidates':sorted(set(candidates))[:50]}
    if not expected.exists(): status['status']='BLOCKED_NATIVE_XAU_DATA_NOT_IN_REPO'
    else: status['status']='NATIVE_XAU_DATA_FOUND_NOT_EXECUTED_IN_THIS_BTC_FROZEN_LINEAGE'
    return status


def main():
    trades=load_frozen_trades()
    if len(trades)!=327:
        raise RuntimeError(f'Frozen parity failed: expected 327 PERSISTENT_EXIT trades, got {len(trades)}')

    h1,source_meta=fetch_binance_futures_h1()
    h4=to_h4(h1)
    ctx=add_router(h4)
    joined=attach_context(trades,ctx)
    if joined.regime.isna().any():
        raise RuntimeError(f'Missing context for {int(joined.regime.isna().sum())} frozen trades')

    variants={
      'BASELINE': pd.Series(True,index=joined.index),
      'PRIMARY_PULLBACK_EXPANSION': joined.regime.isin(['PULLBACK','EXPANSION']),
      'STRICT_PRIMARY_PLUS_BEAR': joined.regime.isin(['PULLBACK','EXPANSION']) & joined.bias.eq('BEAR'),
      'NEG_CONTROL_REVERSAL_RANGE': joined.regime.isin(['REVERSAL','RANGE']),
    }
    met={name:metrics(joined[mask],len(joined)) for name,mask in variants.items()}

    rows=[]
    for name,mask in variants.items():
        q=joined[mask]
        for p in PERIODS:
            z=q[q.period==p]
            r=metrics(z,int((joined.period==p).sum()))
            r.update(variant=name,period=p,baseline_period_n=int((joined.period==p).sum()))
            rows.append(r)
    transfer=pd.DataFrame(rows)
    transfer.to_csv(OUT/'btc_period_transfer.csv',index=False)

    joined['is_primary']=variants['PRIMARY_PULLBACK_EXPANSION']
    joined['is_strict']=variants['STRICT_PRIMARY_PLUS_BEAR']
    joined.to_csv(OUT/'btc_frozen_trades_with_context.csv',index=False)

    regime_rows=[]
    for reg,g in joined.groupby('regime'):
        r=metrics(g,len(joined)); r.update(regime=reg)
        regime_rows.append(r)
    pd.DataFrame(regime_rows).sort_values('regime').to_csv(OUT/'btc_regime_metrics.csv',index=False)

    cross=joined.groupby(['regime','bias']).agg(trades=('flow_id','size'),ev=('net_r_5bps','mean'),cumr=('net_r_5bps','sum'),win_rate=('net_r_5bps',lambda s:float((s>0).mean()))).reset_index()
    cross.to_csv(OUT/'btc_regime_bias_matrix.csv',index=False)

    boots={name:cluster_bootstrap(joined[mask]) for name,mask in variants.items()}
    (OUT/'btc_cluster_bootstrap.json').write_text(json.dumps(boots,indent=2))

    b=met['BASELINE']; p=met['PRIMARY_PULLBACK_EXPANSION']; n=met['NEG_CONTROL_REVERSAL_RANGE']
    gates={
      'primary_retention_ge_35pct':p['retention']>=0.35,
      'primary_ev_gt_baseline':p['ev']>b['ev'],
      'primary_pf_gt_baseline':p['pf']>b['pf'],
      'primary_recovery_gt_baseline':p['recovery_factor']>b['recovery_factor'],
      'primary_dd_lt_baseline':p['maxdd_r']<b['maxdd_r'],
      'primary_ev_gt_negative_control':p['ev']>n['ev'],
    }
    if all(gates.values()): verdict='PROMISING_DISCOVERY_FREEZE_ROUTER_FOR_FRESH_OOS'
    elif gates['primary_ev_gt_baseline'] and gates['primary_ev_gt_negative_control']:
        verdict='MIXED_DISCOVERY_EDGE_BUT_PROP_UTILITY_NOT_CLEAN'
    else:
        verdict='REJECT_CONTEXT_OVERLAY_ON_FROZEN_BTC_SHORT_V1'

    xau=scan_xau_native_data()
    summary={'lab':LAB,'verdict':verdict,'contamination_status':'REUSED_HISTORY_DISCOVERY_ONLY','source':source_meta,'baseline_n':len(joined),'metrics':met,'gates':gates,'xau':xau}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    (OUT/'xau_status.json').write_text(json.dumps(xau,indent=2))

    def fnum(x,fmt='.3f'):
        return 'nan' if x is None or not np.isfinite(x) else format(x,fmt)
    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',
           '> Reused-history discovery/ablation only. Frozen BTC SHORT v1 alpha thresholds were not changed. Router was preregistered before execution.','',
           '## Data / clock',
           f"- Frozen BTC PERSISTENT_EXIT trades: **{len(joined)}** (parity exact).",
           f"- Context source: **{source_meta['source']}**, {source_meta['first']} → {source_meta['last']}.",
           '- Router timeframe: **H4**, using only the last fully closed H4 bar (`available_time = H4 open + 4h`).','',
           '## Main ablation','',
           '| Variant | N | Retain | EV | PF | CumR | DD R | DD @0.25% | Recovery | WR | Loss streak |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name in variants:
        m=met[name]
        lines.append(f"| {name} | {m['trades']} | {m['retention']:.1%} | {m['ev']:+.3f}R | {m['pf']:.3f} | {m['cumr']:+.2f}R | {m['maxdd_r']:.2f}R | {m['dd_pct_025']:.2f}% | {m['recovery_factor']:.2f} | {m['win_rate']:.1%} | {m['loss_streak']} |")
    lines += ['','## Gates']
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['','## Regime decomposition','', '| Regime | N | EV | PF | CumR | DD R |', '|---|---:|---:|---:|---:|---:|']
    for _,r in pd.DataFrame(regime_rows).sort_values('regime').iterrows():
        lines.append(f"| {r.regime} | {int(r.trades)} | {r.ev:+.3f}R | {r.pf:.3f} | {r.cumr:+.2f}R | {r.maxdd_r:.2f}R |")
    lines += ['','## Transfer by period','', '| Variant | Period | N | EV | PF | CumR | DD R |', '|---|---|---:|---:|---:|---:|---:|']
    for _,r in transfer.iterrows():
        lines.append(f"| {r.variant} | {r.period} | {int(r.trades)} | {r.ev:+.3f}R | {r.pf:.3f} | {r.cumr:+.2f}R | {r.maxdd_r:.2f}R |")
    lines += ['','## XAU status',f"- **{xau['status']}**",'- No GC/Yahoo surrogate was substituted.','',
              '## Decision','If PRIMARY passes all preregistered gates, freeze the router specification and test it only on fresh/native broker data. If it fails, do not tune weights on this same history; inspect decomposition only to form a new separately preregistered hypothesis.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__':
    main()
