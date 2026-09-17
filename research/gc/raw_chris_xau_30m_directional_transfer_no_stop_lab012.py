#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('research/gc')
EVENTS = ROOT / 'GC_SHORT_CHRIS_AEIF_BUY_FAILURE_LAB_003_EVENTS.csv'
HELPER = ROOT / 'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON = ROOT / 'RAW_CHRIS_XAU_30M_DIRECTIONAL_TRANSFER_NO_STOP_LAB012.json'
OUT_MD = ROOT / 'RAW_CHRIS_XAU_30M_DIRECTIONAL_TRANSFER_NO_STOP_LAB012.md'
OUT_EVENTS = ROOT / 'RAW_CHRIS_XAU_30M_DIRECTIONAL_TRANSFER_NO_STOP_LAB012_EVENTS.csv'

FEED = 'AMP_CQG_RAW_EXCLUSIVE'
CLOCK_OFFSET_MIN = 180
HOLD_MIN = 30
STALE_MS = 5000
BOOT_N = 20000
SEED = 20260917


def load_helper():
    spec = importlib.util.spec_from_file_location('lt', HELPER)
    m = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    return m


def first_idx(times, target_ms):
    i = int(np.searchsorted(times, target_ms, side='left'))
    if i >= len(times):
        return None, None
    lag = int(times[i] - target_ms)
    if lag < 0 or lag > STALE_MS:
        return None, lag
    return i, lag


def bootstrap(vals):
    vals = np.asarray(vals, float)
    if len(vals) < 2:
        return {'p_ev_gt0': None, 'ci95': [None, None]}
    rng = np.random.default_rng(SEED)
    means = np.empty(BOOT_N)
    for i in range(BOOT_N):
        means[i] = rng.choice(vals, size=len(vals), replace=True).mean()
    return {
        'p_ev_gt0': float((means > 0).mean()),
        'ci95': [float(np.quantile(means, .025)), float(np.quantile(means, .975))],
    }


def stats(df):
    z = df[df.executable].copy().sort_values('gc_entry_time')
    va = z.ret_30m_atr.dropna().to_numpy(float)
    vb = z.ret_30m_bps.dropna().to_numpy(float)
    out = {
        'signals': int(len(df)),
        'executable': int(len(z)),
        'ev_atr': float(va.mean()) if len(va) else None,
        'median_atr': float(np.median(va)) if len(va) else None,
        'wr_atr': float((va > 0).mean()) if len(va) else None,
        'sum_atr': float(va.sum()) if len(va) else None,
        'ev_bps': float(vb.mean()) if len(vb) else None,
        'median_bps': float(np.median(vb)) if len(vb) else None,
        'bootstrap_atr': bootstrap(va),
        'monthly': {},
    }
    if len(z):
        z['month'] = pd.to_datetime(z.gc_entry_time, utc=True).dt.strftime('%Y-%m')
        for month, g in z.groupby('month'):
            v = g.ret_30m_atr.dropna().to_numpy(float)
            out['monthly'][month] = {
                'n': int(len(v)),
                'ev_atr': float(v.mean()) if len(v) else None,
                'sum_atr': float(v.sum()) if len(v) else None,
                'wr': float((v > 0).mean()) if len(v) else None,
            }
    return out


def main():
    if not EVENTS.exists():
        raise SystemExit(f'Missing {EVENTS}')

    ev = pd.read_csv(EVENTS)
    ev = ev[ev.feed.eq(FEED)].copy()
    ev['entry_time'] = pd.to_datetime(ev.entry_time, utc=True)
    ev = ev.sort_values('entry_time').reset_index(drop=True)

    lt = load_helper()
    times, bids, asks, file_stats = lt.read_xau_ticks()
    xau_m1 = lt.build_xau_m1(times, bids, asks)
    atr_map = lt.xau_atr_lookup(xau_m1)

    rows = []
    for r in ev.itertuples(index=False):
        utc_ms = int(pd.Timestamp(r.entry_time).value // 1_000_000)
        entry_target = utc_ms + CLOCK_OFFSET_MIN * 60000
        exit_target = entry_target + HOLD_MIN * 60000
        i, ilag = first_idx(times, entry_target)
        j, xlag = first_idx(times, exit_target)
        row = {
            'seed_time': pd.Timestamp(r.seed_time).isoformat(),
            'gc_entry_time': pd.Timestamp(r.entry_time).isoformat(),
            'broker_entry_target_msc': entry_target,
            'broker_exit_target_msc': exit_target,
            'entry_lag_ms': ilag,
            'exit_lag_ms': xlag,
            'executable': False,
            'reject_reason': '',
        }
        if i is None:
            row['reject_reason'] = 'NO_ENTRY_TICK_WITHIN_5S'
            rows.append(row); continue
        if j is None or j < i:
            row['reject_reason'] = 'NO_EXIT_TICK_WITHIN_5S'
            rows.append(row); continue
        entry_bid = float(bids[i]); entry_ask = float(asks[i]); exit_ask = float(asks[j])
        if not (np.isfinite(entry_bid) and np.isfinite(entry_ask) and np.isfinite(exit_ask) and entry_bid > 0 and entry_ask >= entry_bid and exit_ask > 0):
            row['reject_reason'] = 'INVALID_QUOTE'
            rows.append(row); continue
        atr = float(atr_map.get(entry_target - 60000, np.nan))
        if not np.isfinite(atr) or atr <= 0:
            row['reject_reason'] = 'NO_XAU_ATR'
            rows.append(row); continue
        diff = entry_bid - exit_ask
        row.update({
            'executable': True,
            'entry_tick_msc': int(times[i]),
            'exit_tick_msc': int(times[j]),
            'entry_bid': entry_bid,
            'entry_ask': entry_ask,
            'entry_spread': entry_ask-entry_bid,
            'exit_ask': exit_ask,
            'xau_atr14_m1': atr,
            'ret_30m_price': diff,
            'ret_30m_atr': float(diff/atr),
            'ret_30m_bps': float(diff/entry_bid*10000.0),
        })
        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(OUT_EVENTS, index=False)
    s = stats(out)
    aug = s['monthly'].get('2026-08', {}).get('ev_atr')
    sep = s['monthly'].get('2026-09', {}).get('ev_atr')
    gates = {
        'signals_ge20': s['signals'] >= 20,
        'executable_ge20': s['executable'] >= 20,
        'gross_ev_atr_pos': s['ev_atr'] is not None and s['ev_atr'] > 0,
        'gross_ev_bps_pos': s['ev_bps'] is not None and s['ev_bps'] > 0,
        'wr_ge50pct': s['wr_atr'] is not None and s['wr_atr'] >= .50,
        'aug_ev_nonneg': aug is not None and aug >= 0,
        'sep_ev_nonneg': sep is not None and sep >= 0,
        'bootstrap_p_ge080': s['bootstrap_atr']['p_ev_gt0'] is not None and s['bootstrap_atr']['p_ev_gt0'] >= .80,
    }
    gates['pass'] = all(gates.values())
    status = 'HISTORICAL_RAW_CHRIS_XAU_30M_DIRECTIONAL_TRANSFER_PASS_SMALL_SAMPLE_NOT_OOS' if gates['pass'] else 'HISTORICAL_RAW_CHRIS_XAU_30M_DIRECTIONAL_TRANSFER_FAIL_SMALL_SAMPLE_NOT_OOS'
    result = {
        'status': status,
        'frozen': {
            'feed': FEED,
            'clock_offset_min': CLOCK_OFFSET_MIN,
            'entry': 'SHORT at executable XAU Bid',
            'exit': 'cover at executable XAU Ask exactly 30m later',
            'sl': None, 'tp': None, 'limit': None, 'filters': None,
            'spread': 'embedded',
        },
        'xau_file_stats': file_stats,
        'summary': s,
        'gates': gates,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding='utf-8')

    def pct(x): return 'NA' if x is None else f'{100*x:.1f}%'
    def num(x): return 'NA' if x is None else f'{x:+.4f}'
    lines = [
        '# RAW CHRIS XAU 30M DIRECTIONAL TRANSFER NO STOP — LAB012','',
        f'**Status:** `{status}`','',
        'Frozen Chris SHORT transferred to executable FTMO-Demo XAUUSD with no SL/TP/limit/new filter. Entry = Bid; exit exactly +30m = Ask; spread embedded.','',
        '## Aggregate','',
        f'- Signals: **{s["signals"]}**',
        f'- Executable: **{s["executable"]}**',
        f'- EV: **{num(s["ev_atr"])} XAU ATR** / **{num(s["ev_bps"])} bps**',
        f'- Median: **{num(s["median_atr"])} ATR**',
        f'- WR: **{pct(s["wr_atr"])}**',
        f'- Sum: **{num(s["sum_atr"])} ATR**',
        f'- Bootstrap P(EV>0): **{pct(s["bootstrap_atr"]["p_ev_gt0"])}**; 95% CI **[{num(s["bootstrap_atr"]["ci95"][0])}, {num(s["bootstrap_atr"]["ci95"][1])}] ATR**','',
        '## Monthly',''
    ]
    for m,g in s['monthly'].items():
        lines.append(f'- {m}: N={g["n"]}, EV={num(g["ev_atr"])} ATR, Sum={num(g["sum_atr"])} ATR, WR={pct(g["wr"])}')
    lines += ['', '## Frozen gates','']
    for k,v in gates.items():
        if k != 'pass': lines.append(f'- {"PASS" if v else "FAIL"} — `{k}`')
    lines += ['', '## Decision','']
    if gates['pass']:
        lines.append('Raw Chris 30m direction transfers positively to executable XAU on this overlap. LAB011 therefore failed primarily because the frozen SL/TP execution geometry destroyed the delayed move. This remains a small historical sample, not independent OOS.')
    else:
        lines.append('Raw Chris 30m direction does not pass the preregistered executable-XAU transfer gates on this overlap. Do not rescue by tuning hold time, session, entry delay, spread filter, stop, target, or selector on this same sample.')
    OUT_MD.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(status)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
