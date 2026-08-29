#!/usr/bin/env python3
"""XAU_PRICE_TIME_ALOGICAL_POST_TRAP_PAYOFF_MAP_LAB_008

Question
--------
LAB006/007 showed that immediate inverse 2R reversals are structurally weak.
This lab asks a narrower question: after a causal crowd-trap transition, is
there a SHORT executable inverse response, and what is its natural size/time?

Signal lineage is frozen from LAB007 V2. No new setup thresholds are fitted.
We map forward executable Bid/Ask paths at 3/5/10/15/20/30/60 minutes, then
screen only small targets 0.10..0.40 ATR with RR >= 1.5.

Causality
---------
- crowd obviousness uses t0-1 or earlier;
- transition is known only after its completed wait window;
- DIRECT/RETEST entry minute is inherited exactly from LAB007 V2;
- all forward path measurements begin at the actual later entry minute.

Execution
---------
BUY enters first_ask, exits/scores on Bid; SELL enters first_bid, exits/scores
on Ask. Thus spread is embedded in MFE/MAE/terminal returns. Commission is
added explicitly at the same 0.0007% USD-notional per side used by LAB001.

Chronology
----------
2023-2024 discovery -> 2025 validation -> 2026 untouched final OOS.
Selection uses 240-minute de-clustered samples per cell. Ambiguous M1 cases
where both target and stop are touched inside a horizon are treated as LOSSES
in the lower-bound trading screen. This is intentionally conservative.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from xau_price_time_alogical_path_transition_lab007_v2 import (
    add_obviousness,
    build_transitions,
    cooldown,
)

COMMISSION_RATE_SIDE = 0.000007
HORIZONS = (3, 5, 10, 15, 20, 30, 60)
TARGET_ATRS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.40)
RRS = (1.5, 2.0)
SELECTION_HORIZONS = (3, 5, 10, 15, 20, 30)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--bars', type=Path, required=True)
    p.add_argument('--labels', type=Path, required=True)
    p.add_argument('--outdir', type=Path, required=True)
    return p.parse_args()


def load_full(bp: Path, lp: Path) -> pd.DataFrame:
    b = pd.read_parquet(bp)
    l = pd.read_parquet(lp)
    bc = [
        'minute','timestamp_from_time_msc','first_bid','first_ask',
        'bid_high','bid_low','bid_close','ask_high','ask_low','ask_close',
        'mid_open','mid_high','mid_low','mid_close'
    ]
    lc = ['minute','atr14_causal','BUY_S1.25_R2_H240','SELL_S1.25_R2_H240']
    mb = [c for c in bc if c not in b.columns]
    ml = [c for c in lc if c not in l.columns]
    if mb or ml:
        raise RuntimeError(f'schema mismatch bars={mb} labels={ml}')
    x = b[bc].merge(l[lc], on='minute', how='inner', validate='one_to_one')
    x = x.sort_values('minute').reset_index(drop=True)
    x['year'] = pd.to_datetime(x['timestamp_from_time_msc'], errors='coerce').dt.year.astype('Int64')
    return x


def forward_roll(a: np.ndarray, w: int, kind: str) -> np.ndarray:
    s = pd.Series(np.asarray(a)[::-1])
    z = (s.rolling(w, min_periods=w).max() if kind == 'max' else s.rolling(w, min_periods=w).min())
    return z.to_numpy()[::-1]


def endpoint(a: np.ndarray, w: int) -> np.ndarray:
    out = np.full(len(a), np.nan, dtype=float)
    if w <= len(a):
        out[:len(a)-w+1] = np.asarray(a, float)[w-1:]
    return out


def pf(r: np.ndarray):
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    if not len(r):
        return None
    gp = float(r[r > 0].sum())
    gl = float(-r[r < 0].sum())
    return gp / gl if gl > 0 else None


def rstats(r: np.ndarray) -> dict:
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    if not len(r):
        return {'n':0,'mean_R':None,'pf':None,'win_rate':None,'sum_R':0.0,'max_dd_R':None}
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return {
        'n': int(len(r)),
        'mean_R': float(np.mean(r)),
        'pf': pf(r),
        'win_rate': float(np.mean(r > 0)),
        'sum_R': float(np.sum(r)),
        'max_dd_R': float(np.max(dd)) if len(dd) else 0.0,
    }


def independent_events(t: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for _, g in t.groupby('cell_id', sort=False, observed=True):
        parts.append(cooldown(g, minutes=240))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def path_arrays(x: pd.DataFrame, t: pd.DataFrame, horizon: int):
    idx = t['entry_idx'].to_numpy(np.int64)
    side_buy = t['inverse_side'].eq('BUY').to_numpy()
    atr = t['atr0'].to_numpy(float)

    f_bid_hi = forward_roll(x['bid_high'].to_numpy(float), horizon, 'max')[idx]
    f_bid_lo = forward_roll(x['bid_low'].to_numpy(float), horizon, 'min')[idx]
    f_ask_hi = forward_roll(x['ask_high'].to_numpy(float), horizon, 'max')[idx]
    f_ask_lo = forward_roll(x['ask_low'].to_numpy(float), horizon, 'min')[idx]
    e_bid = x['first_bid'].to_numpy(float)[idx]
    e_ask = x['first_ask'].to_numpy(float)[idx]
    end_bid = endpoint(x['bid_close'].to_numpy(float), horizon)[idx]
    end_ask = endpoint(x['ask_close'].to_numpy(float), horizon)[idx]

    entry = np.where(side_buy, e_ask, e_bid)
    mfe_px = np.where(side_buy, f_bid_hi - e_ask, e_bid - f_ask_lo)
    mae_px = np.where(side_buy, e_ask - f_bid_lo, f_ask_hi - e_bid)
    terminal_px = np.where(side_buy, end_bid - e_ask, e_bid - end_ask)

    mfe = np.divide(mfe_px, atr, out=np.full(len(t), np.nan), where=atr > 0)
    mae = np.divide(mae_px, atr, out=np.full(len(t), np.nan), where=atr > 0)
    terminal = np.divide(terminal_px, atr, out=np.full(len(t), np.nan), where=atr > 0)
    mfe = np.maximum(mfe, 0.0)
    mae = np.maximum(mae, 0.0)
    commission_atr = np.divide(2.0 * COMMISSION_RATE_SIDE * entry, atr, out=np.full(len(t), np.nan), where=atr > 0)
    terminal_net = terminal - commission_atr
    return mfe, mae, terminal_net, commission_atr


def describe_group(mfe, mae, terminal_net, commission_atr):
    ok = np.isfinite(mfe) & np.isfinite(mae) & np.isfinite(terminal_net) & np.isfinite(commission_atr)
    mfe, mae, terminal_net, commission_atr = mfe[ok], mae[ok], terminal_net[ok], commission_atr[ok]
    n = len(mfe)
    if not n:
        return {'n':0}
    out = {
        'n': n,
        'mfe_mean_atr': float(np.mean(mfe)),
        'mfe_median_atr': float(np.median(mfe)),
        'mfe_p75_atr': float(np.quantile(mfe, .75)),
        'mae_mean_atr': float(np.mean(mae)),
        'mae_median_atr': float(np.median(mae)),
        'mae_p75_atr': float(np.quantile(mae, .75)),
        'terminal_mean_atr_net': float(np.mean(terminal_net)),
        'terminal_median_atr_net': float(np.median(terminal_net)),
        'commission_mean_atr': float(np.mean(commission_atr)),
    }
    for q in TARGET_ATRS:
        out[f'p_mfe_ge_{q:.2f}'] = float(np.mean(mfe >= q))
        out[f'p_mfe_ge_{q:.2f}_mae_lt_{q/1.5:.3f}'] = float(np.mean((mfe >= q) & (mae < q/1.5)))
    return out


def build_descriptive_map(x: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for h in HORIZONS:
        mfe, mae, terminal, comm = path_arrays(x, t, h)
        for (cid, yr), ix in t.groupby(['cell_id','entry_year'], sort=True, observed=True).groups.items():
            ii = np.asarray(list(ix), dtype=np.int64)
            base = t.iloc[ii[0]]
            rows.append({
                'cell_id': cid, 'year': int(yr), 'horizon_min': h,
                'crowd_dir': int(base.crowd_dir), 'score_bucket': str(base.score_bucket),
                'wait_min': int(base.wait_min), 'transition': str(base.transition),
                'entry_mode': str(base.entry_mode),
                **describe_group(mfe[ii], mae[ii], terminal[ii], comm[ii])
            })
        print(f'[MAP] horizon={h} done', flush=True)
    return pd.DataFrame(rows)


def lower_bound_r(mfe, mae, terminal_net_atr, commission_atr, target_atr, rr):
    stop_atr = target_atr / rr
    hit_t = mfe >= target_atr
    hit_s = mae >= stop_atr
    amb = hit_t & hit_s
    win = hit_t & ~hit_s
    loss = hit_s  # includes ambiguous by design
    neither = ~hit_t & ~hit_s
    comm_r = commission_atr / stop_atr
    r = np.full(len(mfe), np.nan)
    r[win] = rr - comm_r[win]
    r[loss] = -1.0 - comm_r[loss]
    r[neither] = terminal_net_atr[neither] / stop_atr
    return r, win, loss, amb, neither


def surface_period(x: pd.DataFrame, t: pd.DataFrame, years: set[int]) -> pd.DataFrame:
    d = t[t.entry_year.isin(years)].copy().reset_index(drop=True)
    if d.empty:
        return pd.DataFrame()
    rows = []
    groups = {cid: np.asarray(ix, dtype=np.int64) for cid, ix in d.groupby('cell_id', sort=True, observed=True).groups.items()}
    for h in SELECTION_HORIZONS:
        mfe, mae, terminal, comm = path_arrays(x, d, h)
        for cid, ii in groups.items():
            base = d.iloc[ii[0]]
            valid = np.isfinite(mfe[ii]) & np.isfinite(mae[ii]) & np.isfinite(terminal[ii]) & np.isfinite(comm[ii])
            jj = ii[valid]
            if not len(jj):
                continue
            for target in TARGET_ATRS:
                for rr in RRS:
                    r, win, loss, amb, neither = lower_bound_r(mfe[jj], mae[jj], terminal[jj], comm[jj], target, rr)
                    st = rstats(r)
                    rows.append({
                        'config_id': f'{cid}|H{h}|T{target:.2f}|RR{rr:.1f}',
                        'cell_id': cid, 'horizon_min': h, 'target_atr': target, 'rr': rr,
                        'stop_atr': target/rr,
                        'crowd_dir': int(base.crowd_dir), 'score_bucket': str(base.score_bucket),
                        'wait_min': int(base.wait_min), 'transition': str(base.transition),
                        'entry_mode': str(base.entry_mode),
                        **st,
                        'clean_win_rate': float(np.mean(win)),
                        'loss_or_amb_rate': float(np.mean(loss)),
                        'ambiguous_rate': float(np.mean(amb)),
                        'neither_rate': float(np.mean(neither)),
                        'mfe_median_atr': float(np.median(mfe[jj])),
                        'mae_median_atr': float(np.median(mae[jj])),
                    })
        print(f'[SURFACE] years={sorted(years)} horizon={h} done', flush=True)
    return pd.DataFrame(rows)


def add_plateau(train: pd.DataFrame) -> pd.DataFrame:
    z = train.copy()
    good = (z['n'] >= 80) & (z['mean_R'] > 0) & (z['pf'] > 1.0) & (z['ambiguous_rate'] <= .20)
    good_ids = set(z.loc[good, 'config_id'])
    horizons = list(SELECTION_HORIZONS)
    targets = list(TARGET_ATRS)
    plateau = []
    for _, r in z.iterrows():
        neigh = 0
        hi = horizons.index(int(r.horizon_min))
        ti = targets.index(float(r.target_atr))
        for dh, dt in ((-1,0),(1,0),(0,-1),(0,1)):
            nh, nt = hi+dh, ti+dt
            if 0 <= nh < len(horizons) and 0 <= nt < len(targets):
                nid = f"{r.cell_id}|H{horizons[nh]}|T{targets[nt]:.2f}|RR{float(r.rr):.1f}"
                if nid in good_ids:
                    neigh += 1
        plateau.append(neigh)
    z['positive_neighbor_count'] = plateau
    return z


def choose_locked(train, val, final):
    train = add_plateau(train)
    t = train.add_prefix('train_').rename(columns={'train_config_id':'config_id'})
    v = val.add_prefix('val_').rename(columns={'val_config_id':'config_id'})
    f = final.add_prefix('final_').rename(columns={'final_config_id':'config_id'})
    m = t.merge(v, on='config_id', how='outer').merge(f, on='config_id', how='outer')
    m['discovery_pass'] = (
        (m.train_n >= 80) & (m.train_mean_R >= .05) & (m.train_pf >= 1.08) &
        (m.train_ambiguous_rate <= .20) & (m.train_positive_neighbor_count >= 1)
    )
    m['validation_pass'] = (
        (m.val_n >= 30) & (m.val_mean_R > 0) & (m.val_pf > 1.0) &
        (m.val_ambiguous_rate <= .25)
    )
    m['locked_before_2026'] = m.discovery_pass & m.validation_pass
    m['final_2026_pass'] = (m.final_n >= 20) & (m.final_mean_R > 0) & (m.final_pf > 1.0)
    return m


def portfolio_from_locked(x: pd.DataFrame, t: pd.DataFrame, locked: pd.DataFrame) -> pd.DataFrame:
    configs = locked.loc[locked.locked_before_2026].copy()
    if configs.empty:
        return pd.DataFrame()
    rank = configs.set_index('config_id')['train_mean_R'].to_dict()
    parts = []
    cache = {}
    for _, c in configs.iterrows():
        h = int(c.train_horizon_min); target = float(c.train_target_atr); rr = float(c.train_rr); cid = str(c.train_cell_id)
        g = t[t.cell_id.eq(cid)].copy().reset_index(drop=True)
        if g.empty:
            continue
        key = (cid, h)
        if key not in cache:
            cache[key] = path_arrays(x, g, h)
        mfe, mae, terminal, comm = cache[key]
        r, win, loss, amb, neither = lower_bound_r(mfe, mae, terminal, comm, target, rr)
        g['r_lb'] = r
        g['config_id'] = c.config_id
        g['train_rank'] = rank.get(c.config_id, -999.0)
        g['target_atr'] = target; g['rr'] = rr; g['horizon_min'] = h
        parts.append(g[np.isfinite(g.r_lb)])
    if not parts:
        return pd.DataFrame()
    d = pd.concat(parts, ignore_index=True)
    d = d.sort_values(['event_idx','train_rank'], ascending=[True,False]).drop_duplicates('event_idx')
    return cooldown(d.sort_values('entry_minute'), minutes=240)


def yearly_portfolio(p: pd.DataFrame) -> pd.DataFrame:
    if p.empty:
        return pd.DataFrame(columns=['year','n','mean_R','pf','win_rate','sum_R','max_dd_R'])
    rows = []
    for y, g in p.groupby('entry_year', sort=True):
        rows.append({'year':int(y), **rstats(g.sort_values('entry_minute')['r_lb'].to_numpy(float))})
    return pd.DataFrame(rows)


def main():
    a = parse_args(); a.outdir.mkdir(parents=True, exist_ok=True)
    x = add_obviousness(load_full(a.bars, a.labels))
    t_raw = build_transitions(x)
    if t_raw.empty:
        raise RuntimeError('LAB007 lineage generated no transitions')
    t = independent_events(t_raw)
    print(f'input_rows={len(x)} raw_transitions={len(t_raw)} independent_rows={len(t)} cells={t.cell_id.nunique()}', flush=True)

    desc = build_descriptive_map(x, t)
    desc.to_csv(a.outdir/'response_map_by_cell_year.csv', index=False)

    tr = surface_period(x, t, {2023, 2024})
    va = surface_period(x, t, {2025})
    fi = surface_period(x, t, {2026})
    tr.to_csv(a.outdir/'surface_train_2023_2024.csv', index=False)
    va.to_csv(a.outdir/'surface_validation_2025.csv', index=False)
    fi.to_csv(a.outdir/'surface_final_2026.csv', index=False)

    locked = choose_locked(tr, va, fi)
    locked = locked.sort_values(['locked_before_2026','train_mean_R','val_mean_R'], ascending=[False,False,False], na_position='last')
    locked.to_csv(a.outdir/'candidate_transfer.csv', index=False)

    p = portfolio_from_locked(x, t, locked)
    if not p.empty:
        p.to_csv(a.outdir/'locked_portfolio_trades.csv', index=False)
    yp = yearly_portfolio(p)
    yp.to_csv(a.outdir/'locked_portfolio_yearly.csv', index=False)

    locked_n = int(locked.locked_before_2026.sum()) if len(locked) else 0
    positive_2026 = int((locked.locked_before_2026 & locked.final_2026_pass).sum()) if len(locked) else 0
    p26 = p[p.entry_year.eq(2026)] if not p.empty else pd.DataFrame()
    s26 = rstats(p26.r_lb.to_numpy(float)) if not p26.empty else rstats(np.array([]))

    # Descriptive best short response in untouched 2026 is diagnostic only, not selectable.
    best_2026_desc = None
    d26 = desc[desc.year.eq(2026)].copy()
    if len(d26):
        d26 = d26.sort_values(['terminal_mean_atr_net','n'], ascending=[False,False])
        best_2026_desc = d26.iloc[0][['cell_id','horizon_min','n','mfe_median_atr','mae_median_atr','terminal_mean_atr_net']].to_dict()

    verdict = 'FAIL_NO_SHORT_RESPONSE_TRANSFER'
    if locked_n > 0:
        verdict = 'PASS' if (s26['n'] >= 20 and s26['mean_R'] is not None and s26['mean_R'] > 0 and s26['pf'] is not None and s26['pf'] > 1.05) else 'FAIL_OOS'

    out = {
        'lab':'XAU_PRICE_TIME_ALOGICAL_POST_TRAP_PAYOFF_MAP_LAB_008',
        'lineage':'LAB007 V2 frozen transition definitions',
        'input_rows':int(len(x)),
        'raw_transition_rows':int(len(t_raw)),
        'independent_transition_rows':int(len(t)),
        'matrix_cells':int(t.cell_id.nunique()),
        'horizons_min':list(HORIZONS),
        'target_atrs':list(TARGET_ATRS),
        'rrs':list(RRS),
        'locked_configs_before_2026':locked_n,
        'locked_configs_positive_in_2026':positive_2026,
        'final_2026_locked_portfolio_lower_bound':s26,
        'best_2026_descriptive_cell_diagnostic_only':best_2026_desc,
        'ambiguity_policy':'If target and stop both occur inside horizon, lower-bound screen counts LOSS.',
        'verdict':verdict,
    }
    (a.outdir/'verdict.json').write_text(json.dumps(out, indent=2, default=lambda z: float(z) if isinstance(z, np.floating) else int(z) if isinstance(z, np.integer) else str(z)))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == '__main__':
    main()
