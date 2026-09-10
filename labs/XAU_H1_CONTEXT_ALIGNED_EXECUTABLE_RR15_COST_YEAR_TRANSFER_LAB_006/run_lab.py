#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = 'XAU_H1_CONTEXT_ALIGNED_EXECUTABLE_RR15_COST_YEAR_TRANSFER_LAB_006'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAB002_PATH = ROOT / 'labs' / 'CROSS_MARKET_CAUSAL_CONTEXT_CONTINUOUS_SCORE_INTERACTION_LAB_002' / 'run_lab.py'
THRESH = 0.55
STOP_ATR = 1.5
TP_ATR = 2.25
MAX_HOURS = 120
COST_BPS = [1.0, 2.0, 3.0, 5.0]
PRIMARY_BPS = 2.0
YEARS = ['2023','2024','2025','2026']
BOOT_N = 5000
SEED = 2026091006
RISK_PCT = 0.25
EXPECTED_ALIGNED = 1195


def load_lab002():
    spec = importlib.util.spec_from_file_location('lab002_lab006', LAB002_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def h1_signal_features(m1: pd.DataFrame) -> pd.DataFrame:
    g = m1.set_index('time').resample('1h', origin='epoch', label='left', closed='left').agg(
        open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last')
    ).dropna().reset_index()
    pc = g.close.shift(1)
    tr = pd.concat([g.high-g.low, (g.high-pc).abs(), (g.low-pc).abs()], axis=1).max(axis=1)
    g['signal_atr'] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    g['signal_close'] = g.close
    return g[['time','signal_close','signal_atr']].rename(columns={'time':'signal_time'})


def prepare_aligned(x: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    sig_col = 'time' if 'time' in x.columns else ('time_x' if 'time_x' in x.columns else None)
    if sig_col is None:
        raise KeyError(f'No signal-time column: {list(x.columns)}')
    z = x.rename(columns={sig_col:'signal_time'}).copy()
    z['signal_time'] = pd.to_datetime(z.signal_time, errors='coerce')
    z['available_event_time'] = pd.to_datetime(z.available_event_time, errors='coerce')
    z = z.merge(h1_signal_features(m1), on='signal_time', how='left', validate='many_to_one')
    z['is_high'] = pd.to_numeric(z.context_score, errors='coerce') > THRESH
    z = z[z.tf.eq('H1') & z.is_high & z.bias_compat_label.eq('ALIGNED')].copy()
    for c in ['signal_atr','signal_close','dir']:
        z[c] = pd.to_numeric(z[c], errors='coerce')
    z = z.dropna(subset=['available_event_time','signal_atr','signal_close','dir'])
    z = z[(z.signal_atr > 0) & z.dir.isin([-1,1])].copy()
    z['year'] = z.available_event_time.dt.year.astype(str)
    if len(z) != EXPECTED_ALIGNED:
        raise RuntimeError(f'Frozen H1 HIGH ALIGNED parity failed: {len(z)} != {EXPECTED_ALIGNED}')
    return z.sort_values(['available_event_time','dir']).reset_index(drop=True)


def dedup_signals(z: pd.DataFrame) -> pd.DataFrame:
    # Frozen executable duplicate policy: one order per available event time + direction.
    d = z.sort_values(['available_event_time','dir']).drop_duplicates(['available_event_time','dir'], keep='first').copy()
    return d.reset_index(drop=True)


def first_idx(mask: np.ndarray):
    q = np.flatnonzero(mask)
    return int(q[0]) if len(q) else None


def simulate_one(row, T, H, L, C):
    start = np.datetime64(pd.Timestamp(row.available_event_time).to_datetime64())
    end = start + np.timedelta64(MAX_HOURS, 'h')
    i0 = int(np.searchsorted(T, start, side='left'))
    i1 = int(np.searchsorted(T, end, side='right'))
    if i0 >= len(T) or i1 <= i0:
        return None
    t = T[i0:i1]; hi = H[i0:i1]; lo = L[i0:i1]; cl = C[i0:i1]
    entry = float(row.signal_close); atr = float(row.signal_atr); d = int(row.dir)
    stop_dist = STOP_ATR * atr; tp_dist = TP_ATR * atr
    if not np.isfinite(entry) or not np.isfinite(stop_dist) or stop_dist <= 0:
        return None
    if d == 1:
        stop_hit = lo <= entry - stop_dist
        tp_hit = hi >= entry + tp_dist
    else:
        stop_hit = hi >= entry + stop_dist
        tp_hit = lo <= entry - tp_dist
    isx = first_idx(stop_hit); itp = first_idx(tp_hit)
    samebar = isx is not None and itp is not None and isx == itp
    if isx is not None and (itp is None or isx <= itp):
        state = 'SL'; gross_r = -1.0; ix = isx
    elif itp is not None:
        state = 'TP'; gross_r = 1.5; ix = itp
    else:
        state = 'TIME'; ix = len(cl)-1
        gross_r = float(d * (cl[ix] - entry) / stop_dist)
    exit_time = pd.Timestamp(t[ix])
    hold_h = float((t[ix] - start) / np.timedelta64(1,'h'))
    rec = {
        'entry_time': pd.Timestamp(start), 'exit_time': exit_time, 'hold_hours': hold_h,
        'state': state, 'gross_r': gross_r, 'samebar': bool(samebar),
        'entry_price': entry, 'signal_atr': atr, 'stop_distance': stop_dist,
        'dir': d, 'year': str(pd.Timestamp(start).year),
    }
    for bps in COST_BPS:
        cost_r = entry * (bps / 10000.0) / stop_dist
        rec[f'cost_r_{bps:g}bps'] = float(cost_r)
        rec[f'net_r_{bps:g}bps'] = float(gross_r - cost_r)
    return rec


def simulate_event_ledger(d: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    T = m1.time.to_numpy(dtype='datetime64[ns]')
    H = m1.high.to_numpy(float); L = m1.low.to_numpy(float); C = m1.close.to_numpy(float)
    rows = []
    for _, r in d.iterrows():
        q = simulate_one(r, T, H, L, C)
        if q is not None:
            rows.append(q)
    return pd.DataFrame(rows).sort_values('entry_time').reset_index(drop=True)


def single_position_ledger(events: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    keep = []
    active_until = None
    skipped = 0
    for i, r in events.sort_values('entry_time').iterrows():
        et = pd.Timestamp(r.entry_time)
        if active_until is None or et >= active_until:
            keep.append(i)
            active_until = pd.Timestamp(r.exit_time)
        else:
            skipped += 1
    return events.loc[keep].sort_values('entry_time').reset_index(drop=True), skipped


def pf(v: pd.Series) -> float:
    x = pd.to_numeric(v, errors='coerce').dropna().to_numpy(float)
    gp = x[x > 0].sum(); gl = -x[x < 0].sum()
    if gl == 0:
        return float('inf') if gp > 0 else np.nan
    return float(gp / gl)


def max_dd(v: pd.Series) -> float:
    x = pd.to_numeric(v, errors='coerce').fillna(0).to_numpy(float)
    if len(x) == 0:
        return np.nan
    eq = np.cumsum(x); eq0 = np.r_[0.0, eq]
    peaks = np.maximum.accumulate(eq0)
    return float(np.max(peaks - eq0))


def metrics(ledger: pd.DataFrame, bps: float) -> dict:
    col = f'net_r_{bps:g}bps'
    v = pd.to_numeric(ledger[col], errors='coerce').dropna()
    n = len(v); cum = float(v.sum()) if n else np.nan; dd = max_dd(v)
    states = ledger.loc[v.index, 'state'] if n else pd.Series(dtype=str)
    rec = {
        'bps': bps, 'n': int(n), 'ev_r': float(v.mean()) if n else np.nan,
        'pf': pf(v), 'win_rate': float((v > 0).mean()) if n else np.nan,
        'cum_r': cum, 'max_dd_r': dd,
        'recovery_factor': float(cum/dd) if n and np.isfinite(dd) and dd > 0 else np.nan,
        'tp_rate': float((states == 'TP').mean()) if n else np.nan,
        'sl_rate': float((states == 'SL').mean()) if n else np.nan,
        'time_rate': float((states == 'TIME').mean()) if n else np.nan,
        'cum_return_proxy_pct_at_025': float(cum * RISK_PCT) if n else np.nan,
        'max_dd_proxy_pct_at_025': float(dd * RISK_PCT) if n and np.isfinite(dd) else np.nan,
        'median_hold_hours': float(pd.to_numeric(ledger.loc[v.index,'hold_hours'], errors='coerce').median()) if n else np.nan,
    }
    return rec


def yearly_table(ledger: pd.DataFrame, bps: float) -> pd.DataFrame:
    rows = []
    for y in YEARS:
        g = ledger[ledger.year.astype(str).eq(y)].copy()
        m = metrics(g, bps)
        rows.append({'year': y, **m, 'eligible': bool(m['n'] >= 20),
                     'positive': bool(m['n'] >= 20 and np.isfinite(m['ev_r']) and m['ev_r'] > 0 and np.isfinite(m['pf']) and m['pf'] > 1.0)})
    return pd.DataFrame(rows)


def direction_table(ledger: pd.DataFrame, bps: float) -> pd.DataFrame:
    rows=[]
    for d, name in [(1,'BUY'),(-1,'SELL')]:
        g=ledger[ledger.dir.eq(d)].copy(); rows.append({'direction':name, **metrics(g,bps)})
    return pd.DataFrame(rows)


def loyo_table(ledger: pd.DataFrame, bps: float) -> pd.DataFrame:
    rows=[]
    for y in YEARS:
        g=ledger[~ledger.year.astype(str).eq(y)].copy(); m=metrics(g,bps)
        rows.append({'left_out':y, **m, 'positive':bool(np.isfinite(m['ev_r']) and m['ev_r']>0)})
    return pd.DataFrame(rows)


def weekly_bootstrap_ev(ledger: pd.DataFrame, bps: float) -> dict:
    col=f'net_r_{bps:g}bps'
    z=ledger[['entry_time',col]].copy(); z[col]=pd.to_numeric(z[col],errors='coerce'); z=z.dropna()
    tt=pd.to_datetime(z.entry_time,errors='coerce',utc=True); z=z.loc[tt.notna()].copy(); tt=tt.loc[tt.notna()]
    z['_week']=tt.dt.to_period('W-SUN').astype(str).values
    stats=[]
    for _,g in z.groupby('_week',sort=True):
        x=g[col].to_numpy(float); stats.append([len(x),float(x.sum())])
    a=np.asarray(stats,float); rng=np.random.default_rng(SEED); vals=np.full(BOOT_N,np.nan)
    for k in range(BOOT_N):
        s=a[rng.integers(0,len(a),size=len(a))].sum(axis=0)
        if s[0]>0: vals[k]=s[1]/s[0]
    vals=vals[np.isfinite(vals)]
    return {'weeks':int(len(a)),'draws':BOOT_N,'ci_lo':float(np.quantile(vals,.025)),
            'ci_hi':float(np.quantile(vals,.975)),'p_positive':float(np.mean(vals>0))}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--xau-pool',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    lab002=load_lab002(); router=lab002.load_router_module()
    x,meta=lab002.build_xau_join(Path(a.xau_m1),Path(a.xau_pool),router)
    if len(x)!=263405: raise RuntimeError(f'Frozen XAU context parity failed: {len(x)} != 263405')
    m1=lab002.read_xau_native(Path(a.xau_m1))
    aligned=prepare_aligned(x,m1)
    dedup=dedup_signals(aligned)
    events=simulate_event_ledger(dedup,m1)
    primary, skipped=single_position_ledger(events)

    cost_rows=[metrics(primary,b) for b in COST_BPS]
    cost=pd.DataFrame(cost_rows); cost.to_csv(out/'cost_sensitivity.csv',index=False)
    yr=yearly_table(primary,PRIMARY_BPS); yr.to_csv(out/'year_transfer_2bps.csv',index=False)
    dr=direction_table(primary,PRIMARY_BPS); dr.to_csv(out/'direction_2bps.csv',index=False)
    lo=loyo_table(primary,PRIMARY_BPS); lo.to_csv(out/'leave_one_year_out_2bps.csv',index=False)
    boot=weekly_bootstrap_ev(primary,PRIMARY_BPS)
    events.to_csv(out/'event_dedup_ledger.csv',index=False)
    primary.to_csv(out/'primary_single_position_ledger.csv',index=False)

    m2=cost[cost.bps.eq(PRIMARY_BPS)].iloc[0].to_dict()
    m5=cost[cost.bps.eq(5.0)].iloc[0].to_dict()
    gates={
      'G1_2bps_ev_gt_zero':bool(m2['ev_r']>0),
      'G2_2bps_pf_ge_1_20':bool(m2['pf']>=1.20),
      'G3_bootstrap_ci_lo_gt_zero':bool(boot['ci_lo']>0),
      'G4_all_4_years_positive_pf_gt1_n20':bool(len(yr)==4 and yr.eligible.all() and yr.positive.all()),
      'G5_loyo_4of4_ev_positive':bool(len(lo)==4 and lo.positive.all()),
      'G6_5bps_ev_gt_zero_pf_gt_1_05':bool(m5['ev_r']>0 and m5['pf']>1.05),
      'G7_dd_at_025_le_4pct':bool(m2['max_dd_proxy_pct_at_025']<=4.0),
      'G8_recovery_factor_ge_2':bool(np.isfinite(m2['recovery_factor']) and m2['recovery_factor']>=2.0),
      'G9_n_ge_100':bool(m2['n']>=100),
    }
    if all(gates.values()): verdict='EXECUTABLE_RR15_TRANSFER_SUPPORTED_DISCOVERY_ONLY'
    elif m2['ev_r']>0 and m2['pf']>1.0: verdict='POSITIVE_BUT_TRANSFER_NOT_CONFIRMED'
    else: verdict='EXECUTABLE_RR15_NOT_SUPPORTED'

    summary={
      'lab':LAB,'status':'REUSED_HISTORY_PREREGISTERED_EXECUTION_DIAGNOSTIC','verdict':verdict,
      'selector':'H1 AND context_score>0.55 AND ALIGNED','sl_atr':STOP_ATR,'tp_atr':TP_ATR,'gross_rr':1.5,'max_hours':MAX_HOURS,
      'cost_model':{'ftmo_metals_commission_rt_bps':0.14,'synthetic_all_in_rt_bps':COST_BPS,'primary_bps':PRIMARY_BPS},
      'xau_meta':meta,'frozen_aligned_rows':int(len(aligned)),'event_dedup_n':int(len(events)),
      'duplicate_rows_removed':int(len(aligned)-len(dedup)),'primary_n':int(len(primary)),'overlap_signals_skipped':int(skipped),
      'primary_2bps':m2,'stress_5bps':m5,'bootstrap_2bps':boot,'gates':gates,
      'promotion_authorized':False,
    }
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',
      '> Reused-history execution diagnostic. Synthetic all-in bps costs on bid-only M1 are not true MT5 bid/ask replication. No production promotion is authorized.','',
      '## Frozen executable universe','',
      f'- Frozen H1 HIGH ALIGNED rows: **{len(aligned)}**',
      f'- Unique executable event signals: **{len(events)}**',
      f'- Primary single-position trades: **{len(primary)}**',
      f'- Duplicate rows removed: **{len(aligned)-len(dedup)}**',
      f'- Overlap signals skipped: **{skipped}**','',
      '## Primary 2 bps all-in RT','',
      f"- EV: **{m2['ev_r']:+.5f}R**",f"- PF: **{m2['pf']:.3f}**",f"- Win rate: **{100*m2['win_rate']:.2f}%**",
      f"- CumR: **{m2['cum_r']:+.2f}R**",f"- Max closed-trade DD: **{m2['max_dd_r']:.2f}R** = **{m2['max_dd_proxy_pct_at_025']:.2f}% @0.25% risk**",
      f"- Recovery factor: **{m2['recovery_factor']:.2f}**",f"- Median hold: **{m2['median_hold_hours']:.1f}h**",'',
      '## Weekly cluster bootstrap','',f"- 95% CI EV: **[{boot['ci_lo']:+.5f}, {boot['ci_hi']:+.5f}]R**; P(EV>0)={boot['p_positive']:.3f}",'',
      '## Cost stress','']
    for _,r in cost.iterrows(): lines.append(f"- {r.bps:g} bps: N={int(r.n)}, EV **{r.ev_r:+.5f}R**, PF **{r.pf:.3f}**, CumR {r.cum_r:+.2f}R, DD {r.max_dd_r:.2f}R")
    lines += ['', '## Year transfer (2 bps)','']
    for _,r in yr.iterrows(): lines.append(f"- {r.year}: N={int(r.n)}, EV **{r.ev_r:+.5f}R**, PF **{r.pf:.3f}**, CumR {r.cum_r:+.2f}R, DD {r.max_dd_r:.2f}R")
    lines += ['', '## Gates','']
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print((out/'REPORT.md').read_text())
    print(json.dumps(summary,indent=2,default=str))


if __name__=='__main__':
    main()
