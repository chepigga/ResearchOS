#!/usr/bin/env python3
"""XAU_PRICE_TIME_DOUBLE_TRAP_SECOND_STAGE_RESPONSE_LAB_010

Purpose
-------
Test the second-stage inverse hypothesis exposed by LAB009:
1) an obvious price-time crowd state transitions into a trap;
2) an early inverse trader enters and is stopped on exact Bid/Ask ticks (LAB009);
3) price extends through that early-contrarian stop;
4) the adverse extreme stops progressing for a short causal hold window;
5) price reclaims part of the extension;
6) only then enter the same inverse direction and test a short exact-tick response.

This is not an optimization of LAB009's entry. LAB009 exact SL events are frozen lineage.
The stage-2 structural matrix is frozen before any 2026 payoff inspection.

Chronology / anti-leakage
-------------------------
- Stage-1 universe: frozen LAB009 exact-tick artifact from run 33245644124.
- Only LAB009 rows with tick_outcome == SL are eligible.
- Structural gates are price+time only and use completed M1 bars after the exact SL tick.
- Gate availability is screened ONLY by sample counts in 2023-24 and 2025, never by payoff.
- Exact payoff selection: 2023-24 discovery -> 2025 validation -> 2026 final untouched OOS.
- A parameter-neighborhood support rule is required before locking a config.
- Portfolio is globally de-clustered by 240 minutes.

Execution
---------
BUY stage-2: enter Ask; TP/SL resolved on Bid.
SELL stage-2: enter Bid; TP/SL resolved on Ask.
Spread is therefore naturally included. Commission is 0.0007% USD notional per side,
matching the frozen XAU lineage. No slippage is added here; any surviving config must
later pass slippage/cost stress before EA admission.
"""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

COMMISSION_RATE_SIDE = 0.000007
RAW_TICK_ROWS_EXPECTED = 158_961_208
COOLDOWN_MIN = 240
SIG_NEW_EXTREME_ATR = 0.03
MAX_STAGE2_WAIT_MIN = 30

EXTRA_SWEEP_ATR = (0.00, 0.10, 0.20)
HOLD_MIN = (3, 5, 10)
RECLAIM_ATR = (0.10, 0.20, 0.30)
TARGET_ATR = (0.20, 0.30, 0.40)
RR_VALUES = (1.5, 2.0)
HORIZONS_MIN = (10, 20, 30)

DISCOVERY_MIN_N = 100
VALIDATION_MIN_N = 40
FINAL_MIN_N = 20
DISCOVERY_MIN_EV = 0.03
DISCOVERY_MIN_PF = 1.08
NEIGHBOR_SUPPORT_MIN = 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--bars', type=Path, required=True)
    p.add_argument('--labels', type=Path, required=True)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--lab009-events', type=Path, required=True)
    p.add_argument('--raw-zip', type=Path, required=True)
    p.add_argument('--outdir', type=Path, required=True)
    return p.parse_args()


def pf(r):
    a = np.asarray(r, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return None
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return gp / gl if gl > 0 else None


def stats(r):
    a = np.asarray(r, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return {'n': 0, 'mean_R': None, 'pf': None, 'win_rate': None,
                'sum_R': 0.0, 'max_dd_R': None}
    eq = np.cumsum(a)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return {
        'n': int(len(a)),
        'mean_R': float(np.mean(a)),
        'pf': pf(a),
        'win_rate': float(np.mean(a > 0)),
        'sum_R': float(np.sum(a)),
        'max_dd_R': float(np.max(dd)) if len(dd) else 0.0,
    }


def cooldown(df, minutes=COOLDOWN_MIN, time_col='entry_minute_stage2'):
    if df.empty:
        return df.copy()
    z = df.sort_values(time_col)
    keep = []
    last = -10**18
    for ix, m in zip(z.index, z[time_col].to_numpy(np.int64)):
        if int(m) - last >= minutes:
            keep.append(ix)
            last = int(m)
    return z.loc[keep].copy()


def load_bars_and_atr(bp: Path, lp: Path):
    b = pd.read_parquet(bp)
    l = pd.read_parquet(lp)
    bcols = ['minute', 'timestamp_from_time_msc', 'first_time_msc', 'first_bid', 'first_ask',
             'mid_open', 'mid_high', 'mid_low', 'mid_close']
    lcols = ['minute', 'atr14_causal']
    mb = [c for c in bcols if c not in b.columns]
    ml = [c for c in lcols if c not in l.columns]
    if mb or ml:
        raise RuntimeError(f'schema mismatch bars={mb} labels={ml}')
    x = b[bcols].merge(l[lcols], on='minute', how='inner', validate='one_to_one')
    x = x.sort_values('minute').reset_index(drop=True)
    x['year'] = pd.to_datetime(x['timestamp_from_time_msc'], errors='coerce').dt.year.astype('Int64')
    return x


def frozen_stage1_sl_events(path: Path):
    e = pd.read_parquet(path)
    req = ['event_idx', 'entry_idx', 'entry_minute', 'entry_year', 'inverse_side',
           'score_bucket', 'wait_min', 'transition', 'entry_mode', 'cell_id',
           'atr_entry', 'sl_price', 'tick_outcome', 'hit_time_msc']
    miss = [c for c in req if c not in e.columns]
    if miss:
        raise RuntimeError(f'LAB009 artifact schema missing {miss}')
    e = e[(e.tick_outcome == 'SL') & (e.hit_time_msc >= 0) & (e.entry_mode == 'DIRECT')].copy()
    key = ['event_idx', 'entry_idx', 'inverse_side', 'hit_time_msc']
    e = e.sort_values(['event_idx', 'entry_idx', 'hit_time_msc']).drop_duplicates(key).reset_index(drop=True)
    e['stage1_uid'] = np.arange(len(e), dtype=np.int64)
    return e


def gate_id(extra, hold, reclaim):
    return f'XS{extra:.2f}|H{int(hold)}|RC{reclaim:.2f}'


def find_stage2_signals(x: pd.DataFrame, stage1: pd.DataFrame):
    mins = x.minute.to_numpy(np.int64)
    hi = x.mid_high.to_numpy(float)
    lo = x.mid_low.to_numpy(float)
    close = x.mid_close.to_numpy(float)
    first_t = x.first_time_msc.to_numpy(np.int64)
    first_bid = x.first_bid.to_numpy(float)
    first_ask = x.first_ask.to_numpy(float)
    atr_bar = x.atr14_causal.to_numpy(float)
    years = x.year.to_numpy()

    rows = []
    total = len(stage1)
    for kk, r in enumerate(stage1.itertuples(index=False), 1):
        side = str(r.inverse_side)
        atr = float(r.atr_entry)
        slp = float(r.sl_price)
        if not np.isfinite(atr) or atr <= 0 or not np.isfinite(slp):
            continue
        hit_min = int(r.hit_time_msc // 60000 * 60000)
        j0 = int(np.searchsorted(mins, hit_min, side='right'))
        if j0 >= len(x) - 1:
            continue
        jmax = min(len(x) - 2, j0 + MAX_STAGE2_WAIT_MIN - 1)

        for extra in EXTRA_SWEEP_ATR:
            extra_thr = extra * atr
            worst = slp
            threshold_seen = (extra <= 0.0)
            last_sig_extreme = j0 - 1

            for j in range(j0, jmax + 1):
                if side == 'BUY':
                    pext = lo[j]
                    if not threshold_seen and np.isfinite(pext) and pext <= slp - extra_thr:
                        threshold_seen = True
                        worst = min(worst, pext)
                        last_sig_extreme = j
                    elif threshold_seen and np.isfinite(pext) and pext < worst - SIG_NEW_EXTREME_ATR * atr:
                        worst = pext
                        last_sig_extreme = j
                    elif threshold_seen and np.isfinite(pext):
                        worst = min(worst, pext)
                    reclaim_dist = close[j] - worst if threshold_seen and np.isfinite(close[j]) else np.nan
                else:
                    pext = hi[j]
                    if not threshold_seen and np.isfinite(pext) and pext >= slp + extra_thr:
                        threshold_seen = True
                        worst = max(worst, pext)
                        last_sig_extreme = j
                    elif threshold_seen and np.isfinite(pext) and pext > worst + SIG_NEW_EXTREME_ATR * atr:
                        worst = pext
                        last_sig_extreme = j
                    elif threshold_seen and np.isfinite(pext):
                        worst = max(worst, pext)
                    reclaim_dist = worst - close[j] if threshold_seen and np.isfinite(close[j]) else np.nan

                if not threshold_seen:
                    continue

                quiet_bars = j - last_sig_extreme
                for hold in HOLD_MIN:
                    if quiet_bars < hold:
                        continue
                    for reclaim in RECLAIM_ATR:
                        if not np.isfinite(reclaim_dist) or reclaim_dist < reclaim * atr:
                            continue
                        eidx = j + 1
                        if eidx >= len(x):
                            continue
                        gid = gate_id(extra, hold, reclaim)
                        rows.append({
                            'stage1_uid': int(r.stage1_uid),
                            'event_idx': int(r.event_idx),
                            'source_cell_id': str(r.cell_id),
                            'score_bucket': str(r.score_bucket),
                            'wait_min': int(r.wait_min),
                            'transition': str(r.transition),
                            'stage1_entry_mode': str(r.entry_mode),
                            'inverse_side': side,
                            'stage1_hit_time_msc': int(r.hit_time_msc),
                            'stage1_sl_price': slp,
                            'atr_stage1': atr,
                            'gate_id': gid,
                            'extra_sweep_atr': float(extra),
                            'hold_min': int(hold),
                            'reclaim_atr': float(reclaim),
                            'worst_price': float(worst),
                            'reclaim_dist_atr': float(reclaim_dist / atr),
                            'qualify_bar_idx': int(j),
                            'entry_idx_stage2': int(eidx),
                            'entry_minute_stage2': int(mins[eidx]),
                            'entry_time_msc_stage2': int(first_t[eidx]),
                            'entry_bid_stage2': float(first_bid[eidx]),
                            'entry_ask_stage2': float(first_ask[eidx]),
                            'atr_stage2': float(atr_bar[eidx]) if np.isfinite(atr_bar[eidx]) else atr,
                            'entry_year_stage2': int(years[eidx]),
                        })
        if kk % 10000 == 0:
            print(f'[STAGE2] {kk}/{total} stage1 events scanned rows={len(rows)}', flush=True)

    if not rows:
        return pd.DataFrame()
    s = pd.DataFrame(rows)
    s = s.sort_values(['stage1_uid', 'gate_id', 'entry_minute_stage2'])
    s = s.drop_duplicates(['stage1_uid', 'gate_id'], keep='first').reset_index(drop=True)
    return s


def structural_gate_screen(signals: pd.DataFrame):
    rows = []
    for gid, g in signals.groupby('gate_id', sort=True):
        trn = int(g.entry_year_stage2.isin([2023, 2024]).sum())
        val = int(g.entry_year_stage2.eq(2025).sum())
        fin = int(g.entry_year_stage2.eq(2026).sum())
        f = g.iloc[0]
        rows.append({
            'gate_id': gid,
            'extra_sweep_atr': float(f.extra_sweep_atr),
            'hold_min': int(f.hold_min),
            'reclaim_atr': float(f.reclaim_atr),
            'train_n_structural': trn,
            'val_n_structural': val,
            'final_n_structural': fin,
            'eligible_pre2026': bool(trn >= DISCOVERY_MIN_N and val >= VALIDATION_MIN_N),
        })
    return pd.DataFrame(rows).sort_values(['eligible_pre2026', 'train_n_structural', 'val_n_structural'], ascending=[False, False, False])


def payoff_id(target, rr, horizon):
    return f'T{target:.2f}|RR{rr:.1f}|H{int(horizon)}'


def build_unique_signals(signals: pd.DataFrame, gate_screen: pd.DataFrame):
    gates = set(gate_screen.loc[gate_screen.eligible_pre2026, 'gate_id'].astype(str))
    m = signals[signals.gate_id.isin(gates)].copy()
    if m.empty:
        return pd.DataFrame(), pd.DataFrame()
    sig_cols = ['stage1_uid', 'entry_idx_stage2', 'inverse_side', 'entry_minute_stage2',
                'entry_time_msc_stage2', 'entry_bid_stage2', 'entry_ask_stage2',
                'atr_stage2', 'entry_year_stage2']
    u = m[sig_cols].drop_duplicates(['stage1_uid', 'entry_idx_stage2', 'inverse_side']).reset_index(drop=True)
    u['signal_uid'] = np.arange(len(u), dtype=np.int64)
    membership = m.merge(u[['stage1_uid', 'entry_idx_stage2', 'inverse_side', 'signal_uid']],
                         on=['stage1_uid', 'entry_idx_stage2', 'inverse_side'], how='inner', validate='many_to_one')
    return u, membership


def attach_file_ranges(audit_path: Path):
    a = json.loads(audit_path.read_text())
    fs = []
    for f in a.get('files', []):
        if f.get('valid_rows', 0) > 0 and f.get('first_time_msc') is not None and f.get('last_time_msc') is not None:
            fs.append((f['member'], int(f['first_time_msc']), int(f['last_time_msc'])))
    fs.sort(key=lambda z: z[1])
    if not fs:
        raise RuntimeError('audit has no valid raw file ranges')
    return fs


def expand_payoff_events(unique_signals: pd.DataFrame):
    parts = []
    for target in TARGET_ATR:
        for rr in RR_VALUES:
            stop = target / rr
            for horizon in HORIZONS_MIN:
                d = unique_signals.copy()
                d['target_atr'] = float(target)
                d['rr'] = float(rr)
                d['stop_atr'] = float(stop)
                d['horizon_min'] = int(horizon)
                d['payoff_id'] = payoff_id(target, rr, horizon)
                side_buy = d.inverse_side.eq('BUY').to_numpy()
                atr = d.atr_stage2.to_numpy(float)
                entry = np.where(side_buy, d.entry_ask_stage2.to_numpy(float), d.entry_bid_stage2.to_numpy(float))
                d['entry_exec_price'] = entry
                d['tp_price'] = np.where(side_buy, entry + target * atr, entry - target * atr)
                d['sl_price'] = np.where(side_buy, entry - stop * atr, entry + stop * atr)
                d['commission_R'] = np.divide(2.0 * COMMISSION_RATE_SIDE * entry, stop * atr,
                                              out=np.full(len(d), np.nan), where=np.isfinite(atr) & (atr > 0))
                d['end_time_msc'] = d.entry_minute_stage2.to_numpy(np.int64) + int(horizon) * 60_000 - 1
                parts.append(d)
    e = pd.concat(parts, ignore_index=True)
    e['payoff_event_uid'] = np.arange(len(e), dtype=np.int64)
    return e.sort_values('entry_time_msc_stage2').reset_index(drop=True)


def replay_exact(raw_zip: Path, files, events: pd.DataFrame):
    n = len(events)
    outcome = np.full(n, 'UNRESOLVED', object)
    rval = np.full(n, np.nan, float)
    hit_time = np.full(n, -1, np.int64)
    terminal_px = np.full(n, np.nan, float)

    start = events.entry_time_msc_stage2.to_numpy(np.int64)
    end = events.end_time_msc.to_numpy(np.int64)
    side_buy = events.inverse_side.eq('BUY').to_numpy()
    tp = events.tp_price.to_numpy(float)
    sl = events.sl_price.to_numpy(float)
    rr = events.rr.to_numpy(float)
    comm = events.commission_R.to_numpy(float)
    entry = events.entry_exec_price.to_numpy(float)
    atr = events.atr_stage2.to_numpy(float)
    stop_atr = events.stop_atr.to_numpy(float)

    with zipfile.ZipFile(raw_zip, 'r') as z:
        names = set(z.namelist())
        order = np.argsort(start)
        start_sorted = start[order]
        for k, (member, ft, lt) in enumerate(files, 1):
            if member not in names:
                continue
            hi_pos = int(np.searchsorted(start_sorted, lt, side='right'))
            if hi_pos <= 0:
                continue
            cand = order[:hi_pos]
            cand = cand[(end[cand] >= ft) & (outcome[cand] == 'UNRESOLVED')]
            if not len(cand):
                continue
            with z.open(member) as fh:
                df = pd.read_csv(fh, usecols=['time_msc', 'bid', 'ask'])
            if df.empty:
                continue
            tt = df.time_msc.to_numpy(np.int64)
            bid = df.bid.to_numpy(float)
            ask = df.ask.to_numpy(float)
            for ei in cand:
                lo_i = int(np.searchsorted(tt, start[ei], side='left'))
                hi_i = int(np.searchsorted(tt, end[ei], side='right'))
                if hi_i <= lo_i:
                    continue
                px = bid[lo_i:hi_i] if side_buy[ei] else ask[lo_i:hi_i]
                terminal_px[ei] = float(px[-1])
                if side_buy[ei]:
                    hit = np.flatnonzero((px >= tp[ei]) | (px <= sl[ei]))
                else:
                    hit = np.flatnonzero((px <= tp[ei]) | (px >= sl[ei]))
                if len(hit):
                    j = lo_i + int(hit[0])
                    p = float(bid[j] if side_buy[ei] else ask[j])
                    hit_time[ei] = int(tt[j])
                    is_tp = (p >= tp[ei]) if side_buy[ei] else (p <= tp[ei])
                    if is_tp:
                        outcome[ei] = 'TP'
                        rval[ei] = rr[ei] - comm[ei]
                    else:
                        outcome[ei] = 'SL'
                        rval[ei] = -1.0 - comm[ei]
            if k % 100 == 0:
                print(f'[RAW] {k}/{len(files)} resolved={(outcome != "UNRESOLVED").sum()}/{n}', flush=True)

    for ei in np.flatnonzero(outcome == 'UNRESOLVED'):
        if np.isfinite(terminal_px[ei]):
            pnl = (terminal_px[ei] - entry[ei]) if side_buy[ei] else (entry[ei] - terminal_px[ei])
            rval[ei] = pnl / (stop_atr[ei] * atr[ei]) - comm[ei]
            outcome[ei] = 'TIME'
        else:
            outcome[ei] = 'NO_TICKS'

    out = events.copy()
    out['tick_outcome'] = outcome
    out['R_exact'] = rval
    out['hit_time_msc'] = hit_time
    out['terminal_exec_price'] = terminal_px
    out['minutes_to_hit'] = np.where(hit_time >= 0, (hit_time - start) / 60000.0, np.nan)
    return out


def aggregate_configs(exact: pd.DataFrame, membership: pd.DataFrame):
    cols = ['signal_uid', 'gate_id', 'extra_sweep_atr', 'hold_min', 'reclaim_atr',
            'score_bucket', 'wait_min', 'transition', 'stage1_uid', 'entry_minute_stage2',
            'entry_year_stage2']
    m = membership[cols].drop_duplicates(['signal_uid', 'gate_id'])
    z = exact.merge(m, on=['signal_uid', 'stage1_uid', 'entry_minute_stage2', 'entry_year_stage2'],
                    how='inner', validate='many_to_many')
    z = z[np.isfinite(z.R_exact)].copy()

    rows = []
    period_defs = [('train', {2023, 2024}), ('val', {2025}), ('final', {2026})]
    base_keys = ['gate_id', 'payoff_id', 'target_atr', 'rr', 'stop_atr', 'horizon_min']
    for keys, g0 in z.groupby(base_keys, sort=True):
        row = dict(zip(base_keys, keys))
        for name, yrs in period_defs:
            g = g0[g0.entry_year_stage2.isin(yrs)].sort_values('entry_minute_stage2')
            g = g.drop_duplicates(['signal_uid', 'payoff_id'])
            s = stats(g.R_exact.to_numpy(float))
            row.update({f'{name}_{k}': v for k, v in s.items()})
            row[f'{name}_tp_rate'] = float((g.tick_outcome == 'TP').mean()) if len(g) else None
            row[f'{name}_sl_rate'] = float((g.tick_outcome == 'SL').mean()) if len(g) else None
            row[f'{name}_median_minutes_to_hit'] = float(g.minutes_to_hit.dropna().median()) if g.minutes_to_hit.notna().any() else None
        rows.append(row)
    return pd.DataFrame(rows), z


def add_neighbor_support(c: pd.DataFrame):
    if c.empty:
        return c
    e_vals = list(EXTRA_SWEEP_ATR)
    h_vals = list(HOLD_MIN)
    r_vals = list(RECLAIM_ATR)
    t_vals = list(TARGET_ATR)
    rr_vals = list(RR_VALUES)
    hz_vals = list(HORIZONS_MIN)

    def idx(vals, v):
        return min(range(len(vals)), key=lambda i: abs(float(vals[i]) - float(v)))

    coords = {}
    positive = {}
    for i, row in c.iterrows():
        co = (idx(e_vals, row.extra_sweep_atr), idx(h_vals, row.hold_min), idx(r_vals, row.reclaim_atr),
              idx(t_vals, row.target_atr), idx(rr_vals, row.rr), idx(hz_vals, row.horizon_min))
        coords[i] = co
        positive[i] = bool(row.train_n >= DISCOVERY_MIN_N and row.val_n >= VALIDATION_MIN_N and
                           row.train_mean_R is not None and row.train_mean_R > 0 and
                           row.val_mean_R is not None and row.val_mean_R > 0 and
                           row.train_pf is not None and row.train_pf > 1.0 and
                           row.val_pf is not None and row.val_pf > 1.0)

    lookup = {co: i for i, co in coords.items()}
    support = []
    for i, co in coords.items():
        n = 0
        for dim in range(6):
            for delta in (-1, 1):
                q = list(co)
                q[dim] += delta
                j = lookup.get(tuple(q))
                if j is not None and positive.get(j, False):
                    n += 1
        support.append(n)
    c = c.copy()
    c['neighbor_positive_support'] = support
    return c


def build_transfer(configs: pd.DataFrame, gate_screen: pd.DataFrame):
    if configs.empty:
        return configs
    gs = gate_screen[['gate_id', 'train_n_structural', 'val_n_structural', 'final_n_structural', 'eligible_pre2026']]
    c = configs.merge(gs, on='gate_id', how='left', validate='many_to_one')
    c = add_neighbor_support(c)
    c['discovery_pass'] = (
        (c.train_n >= DISCOVERY_MIN_N) &
        (c.train_mean_R >= DISCOVERY_MIN_EV) &
        (c.train_pf >= DISCOVERY_MIN_PF)
    )
    c['validation_pass'] = (
        (c.val_n >= VALIDATION_MIN_N) &
        (c.val_mean_R > 0) &
        (c.val_pf > 1.0)
    )
    c['plateau_pass'] = c.neighbor_positive_support >= NEIGHBOR_SUPPORT_MIN
    c['locked_before_2026'] = c.eligible_pre2026 & c.discovery_pass & c.validation_pass & c.plateau_pass
    c['final_2026_pass'] = (
        (c.final_n >= FINAL_MIN_N) &
        (c.final_mean_R > 0) &
        (c.final_pf > 1.0)
    )
    return c.sort_values(['locked_before_2026', 'train_mean_R', 'val_mean_R', 'neighbor_positive_support'],
                         ascending=[False, False, False, False], na_position='last')


def build_locked_portfolio(exact: pd.DataFrame, membership: pd.DataFrame, transfer: pd.DataFrame):
    locked = transfer[transfer.locked_before_2026].copy()
    if locked.empty:
        return pd.DataFrame()
    rank = locked.set_index(['gate_id', 'payoff_id']).train_mean_R.to_dict()
    mem = membership[['signal_uid', 'gate_id', 'stage1_uid', 'entry_minute_stage2', 'entry_year_stage2']].drop_duplicates(['signal_uid', 'gate_id'])
    z = exact.merge(mem, on=['signal_uid', 'stage1_uid', 'entry_minute_stage2', 'entry_year_stage2'], how='inner')
    z['key'] = list(zip(z.gate_id.astype(str), z.payoff_id.astype(str)))
    z = z[z.key.isin(set(rank)) & np.isfinite(z.R_exact)].copy()
    if z.empty:
        return z
    z['train_rank'] = z.key.map(rank)
    z = z.sort_values(['entry_minute_stage2', 'train_rank'], ascending=[True, False])
    z = z.drop_duplicates(['signal_uid'])
    z = cooldown(z, COOLDOWN_MIN, 'entry_minute_stage2')
    return z


def yearly(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame(columns=['year', 'n', 'mean_R', 'pf', 'win_rate', 'sum_R', 'max_dd_R'])
    rows = []
    for y, g in df.groupby('entry_year_stage2', sort=True):
        rows.append({'year': int(y), **stats(g.sort_values('entry_minute_stage2').R_exact.to_numpy(float))})
    return pd.DataFrame(rows)


def source_context_diagnostics(z: pd.DataFrame, transfer: pd.DataFrame):
    locked = set(zip(transfer.loc[transfer.locked_before_2026, 'gate_id'].astype(str),
                     transfer.loc[transfer.locked_before_2026, 'payoff_id'].astype(str)))
    if not locked:
        return pd.DataFrame()
    d = z.copy()
    d['key'] = list(zip(d.gate_id.astype(str), d.payoff_id.astype(str)))
    d = d[d.key.isin(locked) & np.isfinite(d.R_exact)]
    rows = []
    for (sb, trn, yr), g in d.groupby(['score_bucket', 'transition', 'entry_year_stage2'], sort=True):
        g = g.drop_duplicates(['signal_uid', 'payoff_id'])
        rows.append({'score_bucket': sb, 'transition': trn, 'year': int(yr), **stats(g.R_exact.to_numpy(float))})
    return pd.DataFrame(rows)


def main():
    a = parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    x = load_bars_and_atr(a.bars, a.labels)
    stage1 = frozen_stage1_sl_events(a.lab009_events)
    print(f'stage1 exact SL events={len(stage1)}', flush=True)

    signals = find_stage2_signals(x, stage1)
    if signals.empty:
        raise RuntimeError('No causal second-stage signals generated')
    signals.to_parquet(a.outdir / 'stage2_structural_signals.parquet', index=False)
    print(f'stage2 structural rows={len(signals)} unique stage1={signals.stage1_uid.nunique()}', flush=True)

    gate_screen = structural_gate_screen(signals)
    gate_screen.to_csv(a.outdir / 'structural_gate_screen.csv', index=False)
    eligible = int(gate_screen.eligible_pre2026.sum())
    print(f'eligible structural gates pre2026={eligible}/{len(gate_screen)}', flush=True)
    if eligible == 0:
        out = {
            'lab': 'XAU_PRICE_TIME_DOUBLE_TRAP_SECOND_STAGE_RESPONSE_LAB_010',
            'verdict': 'FAIL_NO_STRUCTURAL_SAMPLE',
            'stage1_exact_sl_events': int(len(stage1)),
            'stage2_structural_rows': int(len(signals)),
            'eligible_structural_gates_pre2026': 0,
        }
        (a.outdir / 'verdict.json').write_text(json.dumps(out, indent=2))
        print(json.dumps(out, indent=2), flush=True)
        return

    unique_signals, membership = build_unique_signals(signals, gate_screen)
    membership.to_parquet(a.outdir / 'stage2_gate_membership.parquet', index=False)
    print(f'unique stage2 physical signals={len(unique_signals)}', flush=True)

    payoff_events = expand_payoff_events(unique_signals)
    print(f'exact payoff event rows={len(payoff_events)}', flush=True)
    files = attach_file_ranges(a.audit)
    exact = replay_exact(a.raw_zip, files, payoff_events)
    exact.to_parquet(a.outdir / 'stage2_exact_payoff_events.parquet', index=False)

    configs, joined = aggregate_configs(exact, membership)
    transfer = build_transfer(configs, gate_screen)
    transfer.to_csv(a.outdir / 'candidate_transfer_exact.csv', index=False)

    portfolio = build_locked_portfolio(exact, membership, transfer)
    if not portfolio.empty:
        portfolio.to_csv(a.outdir / 'locked_portfolio_exact_trades.csv', index=False)
    yp = yearly(portfolio)
    yp.to_csv(a.outdir / 'locked_portfolio_yearly.csv', index=False)
    source_context_diagnostics(joined, transfer).to_csv(a.outdir / 'locked_source_context_yearly.csv', index=False)

    locked = int(transfer.locked_before_2026.sum()) if len(transfer) else 0
    positive_2026 = int((transfer.locked_before_2026 & transfer.final_2026_pass).sum()) if len(transfer) else 0
    p26 = portfolio[portfolio.entry_year_stage2.eq(2026)] if not portfolio.empty else pd.DataFrame()
    s26 = stats(p26.R_exact.to_numpy(float)) if not p26.empty else stats([])

    if locked == 0:
        verdict = 'FAIL_NO_PRE2026_TRANSFER'
    elif s26['n'] >= FINAL_MIN_N and s26['mean_R'] is not None and s26['mean_R'] > 0 and s26['pf'] is not None and s26['pf'] > 1.05:
        verdict = 'PASS'
    elif s26['n'] >= 10 and s26['mean_R'] is not None and s26['mean_R'] > 0:
        verdict = 'WEAK_PASS'
    else:
        verdict = 'FAIL_OOS'

    best = None
    if len(transfer):
        b = transfer.iloc[0]
        best = {k: (None if pd.isna(b[k]) else b[k].item() if hasattr(b[k], 'item') else b[k])
                for k in ['gate_id', 'payoff_id', 'extra_sweep_atr', 'hold_min', 'reclaim_atr',
                          'target_atr', 'rr', 'horizon_min', 'train_n', 'train_mean_R', 'train_pf',
                          'val_n', 'val_mean_R', 'val_pf', 'neighbor_positive_support',
                          'locked_before_2026', 'final_n', 'final_mean_R', 'final_pf'] if k in b.index}

    out = {
        'lab': 'XAU_PRICE_TIME_DOUBLE_TRAP_SECOND_STAGE_RESPONSE_LAB_010',
        'lineage': 'LAB009 exact stage1 SL -> post-SL extra sweep -> no-new-extreme hold -> reclaim -> next-M1 exact entry',
        'raw_tick_rows_expected': RAW_TICK_ROWS_EXPECTED,
        'stage1_exact_sl_events': int(len(stage1)),
        'stage2_structural_rows': int(len(signals)),
        'unique_stage2_physical_signals': int(len(unique_signals)),
        'structural_gates_total': int(len(gate_screen)),
        'eligible_structural_gates_pre2026': eligible,
        'payoff_configs_per_signal': int(len(TARGET_ATR) * len(RR_VALUES) * len(HORIZONS_MIN)),
        'locked_configs_before_2026': locked,
        'locked_configs_positive_2026': positive_2026,
        'final_2026_locked_portfolio': s26,
        'best_exact_config': best,
        'structural_grid': {
            'extra_sweep_atr': list(EXTRA_SWEEP_ATR),
            'hold_min': list(HOLD_MIN),
            'reclaim_atr': list(RECLAIM_ATR),
            'significant_new_extreme_atr': SIG_NEW_EXTREME_ATR,
            'max_stage2_wait_min': MAX_STAGE2_WAIT_MIN,
        },
        'payoff_grid': {
            'target_atr': list(TARGET_ATR),
            'rr': list(RR_VALUES),
            'horizons_min': list(HORIZONS_MIN),
        },
        'selection': {
            'discovery_years': [2023, 2024],
            'validation_years': [2025],
            'final_oos_year': 2026,
            'discovery_min_n': DISCOVERY_MIN_N,
            'validation_min_n': VALIDATION_MIN_N,
            'discovery_min_ev_R': DISCOVERY_MIN_EV,
            'discovery_min_pf': DISCOVERY_MIN_PF,
            'neighbor_positive_support_min': NEIGHBOR_SUPPORT_MIN,
        },
        'verdict': verdict,
    }
    (a.outdir / 'verdict.json').write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == '__main__':
    main()
