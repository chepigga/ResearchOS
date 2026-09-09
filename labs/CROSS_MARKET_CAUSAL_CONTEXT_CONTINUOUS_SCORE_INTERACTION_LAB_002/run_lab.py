#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = 'CROSS_MARKET_CAUSAL_CONTEXT_CONTINUOUS_SCORE_INTERACTION_LAB_002'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BTC_INPUT = ROOT / 'labs' / 'CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001' / 'output' / 'btc_frozen_trades_with_context.csv'
ROUTER_PATH = ROOT / 'labs' / 'CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001' / 'run_lab.py'
XAU_SHA = 'db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
BOOT_N = 3000
SEED = 2026090902
BTC_PERIODS = ['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_router_module():
    spec = importlib.util.spec_from_file_location('lab001_router', ROUTER_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def add_continuous_fields(df: pd.DataFrame, direction: pd.Series) -> pd.DataFrame:
    z = df.copy()
    req = ['score_expansion','score_pullback','score_reversal','score_range','bias']
    miss = [c for c in req if c not in z.columns]
    if miss:
        raise ValueError(f'Missing Context columns: {miss}')
    for c in req[:-1]:
        z[c] = pd.to_numeric(z[c], errors='coerce')
    z['context_score'] = (
        z.score_expansion + z.score_pullback - z.score_reversal - z.score_range
    ) / 200.0
    d = pd.to_numeric(direction, errors='coerce')
    aligned = ((d > 0) & z.bias.eq('BULL')) | ((d < 0) & z.bias.eq('BEAR'))
    opposed = ((d > 0) & z.bias.eq('BEAR')) | ((d < 0) & z.bias.eq('BULL'))
    z['bias_compat'] = np.select([aligned, opposed], [1, -1], default=0).astype(int)
    z['bias_compat_label'] = z.bias_compat.map({1:'ALIGNED',0:'NEUTRAL',-1:'OPPOSED'})
    return z


def quantile_bins(s: pd.Series, q: int):
    valid = s.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=s.index), []
    try:
        codes, edges = pd.qcut(valid, q=q, labels=False, retbins=True, duplicates='drop')
    except ValueError:
        codes, edges = pd.cut(valid, bins=q, labels=False, retbins=True, duplicates='drop')
    out = pd.Series(np.nan, index=s.index, dtype=float)
    out.loc[valid.index] = codes.astype(float) + 1.0
    return out, [float(x) for x in np.asarray(edges)]


def slope_xy(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x = x[m]; y = y[m]
    if len(x) < 2 or np.nanvar(x) <= 0:
        return np.nan
    return float(np.cov(x, y, ddof=0)[0,1] / np.var(x))


def pf(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    gp = v[v > 0].sum(); gl = -v[v < 0].sum()
    return float(gp / gl) if gl > 0 else (float('inf') if gp > 0 else np.nan)


def bin_table(df, bin_col, outcome, raw_col=None):
    rows = []
    for b, g in df.dropna(subset=[bin_col, outcome]).groupby(bin_col, sort=True):
        v = pd.to_numeric(g[outcome], errors='coerce').dropna()
        r = {
            'bin': int(b), 'n': int(len(v)), 'score_min': float(g.context_score.min()),
            'score_max': float(g.context_score.max()), 'score_mean': float(g.context_score.mean()),
            'mean_outcome': float(v.mean()), 'median_outcome': float(v.median()),
            'p_positive': float((v > 0).mean()), 'pf': pf(v)
        }
        if raw_col and raw_col in g.columns:
            rr = pd.to_numeric(g[raw_col], errors='coerce').dropna()
            r['mean_raw_R'] = float(rr.mean()) if len(rr) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def ordered_stats(table: pd.DataFrame):
    if table.empty or len(table) < 2:
        return {'bins': int(len(table)), 'adjacent_monotone_fraction': np.nan, 'bin_mean_corr': np.nan}
    t = table.sort_values('bin')
    means = t.mean_outcome.to_numpy(float); bins = t.bin.to_numpy(float)
    dif = np.diff(means)
    corr = float(np.corrcoef(bins, means)[0,1]) if np.std(means) > 0 else np.nan
    return {
        'bins': int(len(t)),
        'adjacent_monotone_fraction': float(np.mean(dif >= 0)),
        'bin_mean_corr': corr,
        'bottom_mean': float(means[0]),
        'top_mean': float(means[-1]),
        'top_bottom_lift': float(means[-1] - means[0])
    }


def cluster_bootstrap(df, time_col, outcome, qcol='q5'):
    z = df.dropna(subset=[time_col, outcome, 'context_score', qcol]).copy()
    if z.empty:
        return {}
    t = pd.to_datetime(z[time_col], errors='coerce', utc=True)
    z = z.loc[t.notna()].copy(); t = t.loc[t.notna()]
    z['_week'] = t.dt.to_period('W-SUN').astype(str).values
    bins = sorted(int(x) for x in z[qcol].dropna().unique())
    if len(bins) < 2:
        return {}
    lo, hi = min(bins), max(bins)
    groups = [g for _, g in z.groupby('_week', sort=True)]
    rng = np.random.default_rng(SEED)
    lifts, slopes = [], []
    m = len(groups)
    for _ in range(BOOT_N):
        ix = rng.integers(0, m, size=m)
        s = pd.concat([groups[i] for i in ix], ignore_index=True)
        bot = pd.to_numeric(s.loc[s[qcol] == lo, outcome], errors='coerce').dropna()
        top = pd.to_numeric(s.loc[s[qcol] == hi, outcome], errors='coerce').dropna()
        if len(bot) and len(top):
            lifts.append(float(top.mean() - bot.mean()))
        slopes.append(slope_xy(s.context_score, pd.to_numeric(s[outcome], errors='coerce')))
    lifts = np.asarray(lifts, float); slopes = np.asarray(slopes, float); slopes = slopes[np.isfinite(slopes)]
    return {
        'weeks': int(m), 'draws': BOOT_N,
        'lift_ci_lo': float(np.quantile(lifts,.025)) if len(lifts) else np.nan,
        'lift_ci_hi': float(np.quantile(lifts,.975)) if len(lifts) else np.nan,
        'lift_p_positive': float(np.mean(lifts > 0)) if len(lifts) else np.nan,
        'slope_ci_lo': float(np.quantile(slopes,.025)) if len(slopes) else np.nan,
        'slope_ci_hi': float(np.quantile(slopes,.975)) if len(slopes) else np.nan,
        'slope_p_positive': float(np.mean(slopes > 0)) if len(slopes) else np.nan,
    }


def transfer(df, period_col, periods, outcome, min_extreme_n):
    rows = []
    for p in periods:
        g = df[df[period_col].astype(str) == str(p)].dropna(subset=['q5', outcome, 'context_score']).copy()
        if g.empty:
            rows.append({'period': str(p), 'n': 0, 'bottom_n': 0, 'top_n': 0, 'lift': np.nan, 'slope': np.nan, 'eligible': False, 'positive': False})
            continue
        lo = int(g.q5.min()); hi = int(g.q5.max())
        bot = pd.to_numeric(g.loc[g.q5 == lo, outcome], errors='coerce').dropna()
        top = pd.to_numeric(g.loc[g.q5 == hi, outcome], errors='coerce').dropna()
        lift = float(top.mean() - bot.mean()) if len(bot) and len(top) else np.nan
        sl = slope_xy(g.context_score, pd.to_numeric(g[outcome], errors='coerce'))
        eligible = len(bot) >= min_extreme_n and len(top) >= min_extreme_n
        rows.append({'period': str(p), 'n': int(len(g)), 'bottom_n': int(len(bot)), 'top_n': int(len(top)), 'lift': lift, 'slope': sl, 'eligible': bool(eligible), 'positive': bool(eligible and np.isfinite(lift) and lift > 0)})
    return pd.DataFrame(rows)


def interaction_matrix(df, outcome, raw_col=None):
    rows = []
    for (q, comp), g in df.dropna(subset=['q5', outcome]).groupby(['q5','bias_compat_label'], sort=True):
        v = pd.to_numeric(g[outcome], errors='coerce').dropna()
        rec = {'q5': int(q), 'compat': comp, 'n': int(len(v)), 'mean_outcome': float(v.mean()) if len(v) else np.nan, 'p_positive': float((v > 0).mean()) if len(v) else np.nan}
        if raw_col and raw_col in g.columns:
            rr = pd.to_numeric(g[raw_col], errors='coerce').dropna(); rec['mean_raw_R'] = float(rr.mean()) if len(rr) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def evaluate_market(name, df, time_col, outcome, period_col, periods, min_extreme_n, outdir, raw_col=None):
    d = df.dropna(subset=['context_score', outcome]).copy()
    d['q5'], q5_edges = quantile_bins(d.context_score, 5)
    d['q10'], q10_edges = quantile_bins(d.context_score, 10)
    q5 = bin_table(d, 'q5', outcome, raw_col); q10 = bin_table(d, 'q10', outcome, raw_col)
    q5.to_csv(outdir / f'{name.lower()}_quintiles.csv', index=False)
    q10.to_csv(outdir / f'{name.lower()}_deciles.csv', index=False)
    inter = interaction_matrix(d, outcome, raw_col); inter.to_csv(outdir / f'{name.lower()}_q5_bias_interaction.csv', index=False)
    tr = transfer(d, period_col, periods, outcome, min_extreme_n); tr.to_csv(outdir / f'{name.lower()}_transfer.csv', index=False)
    ord5 = ordered_stats(q5); ord10 = ordered_stats(q10)
    sl = slope_xy(d.context_score, pd.to_numeric(d[outcome], errors='coerce'))
    boot = cluster_bootstrap(d, time_col, outcome, 'q5')
    positive_periods = int(tr.positive.sum())
    eligible_periods = int(tr.eligible.sum())
    needed = 5 if name == 'BTC' else 4
    gates = {
        'top_gt_bottom': bool(np.isfinite(ord5.get('top_bottom_lift',np.nan)) and ord5['top_bottom_lift'] > 0),
        'bootstrap_lift_ci_low_gt_zero': bool(np.isfinite(boot.get('lift_ci_lo',np.nan)) and boot['lift_ci_lo'] > 0),
        'continuous_slope_gt_zero': bool(np.isfinite(sl) and sl > 0),
        'bootstrap_slope_ci_low_gt_zero': bool(np.isfinite(boot.get('slope_ci_lo',np.nan)) and boot['slope_ci_lo'] > 0),
        'q5_adjacent_monotone_ge_075': bool(np.isfinite(ord5.get('adjacent_monotone_fraction',np.nan)) and ord5['adjacent_monotone_fraction'] >= .75),
        'time_transfer_positive_required': bool(positive_periods >= needed),
    }
    verdict = 'CONTINUOUS_CONTEXT_SUPPORTED' if all(gates.values()) else ('MIXED_CONTINUOUS_CONTEXT_EVIDENCE' if gates['top_gt_bottom'] and gates['continuous_slope_gt_zero'] else 'CONTINUOUS_CONTEXT_NOT_SUPPORTED')
    return d, {
        'market': name, 'n': int(len(d)), 'outcome': outcome,
        'score_formula': '(EXPANSION+PULLBACK-REVERSAL-RANGE)/200',
        'q5_edges': q5_edges, 'q10_edges': q10_edges,
        'q5_ordered': ord5, 'q10_ordered': ord10,
        'continuous_slope': sl, 'bootstrap': boot,
        'eligible_transfer_periods': eligible_periods, 'positive_transfer_periods': positive_periods,
        'required_positive_periods': needed, 'gates': gates, 'verdict': verdict,
    }


def read_xau_native(path: Path):
    first = path.open('r', encoding='utf-8', errors='ignore').readline()
    sep = ';' if first.count(';') > first.count(',') else ','
    df = pd.read_csv(path, sep=sep)
    lut = {c.lower(): c for c in df.columns}
    aliases = {
        'time':['time','timestamp','datetime','date_time','<date>'],
        'open':['open','bid_open','<open>'], 'high':['high','bid_high','<high>'],
        'low':['low','bid_low','<low>'], 'close':['close','bid_close','<close>'],
        'volume':['tick_volume','tickvolume','tick_vol','ticks','volume','<tickvol>']
    }
    out = pd.DataFrame()
    for dst, names in aliases.items():
        for n in names:
            if n.lower() in lut:
                out[dst] = df[lut[n.lower()]]; break
    miss = [c for c in ['time','open','high','low','close'] if c not in out]
    if miss: raise ValueError(f'Missing XAU native columns: {miss}; got={list(df.columns)}')
    out.time = pd.to_datetime(out.time, errors='coerce')
    for c in out.columns:
        if c != 'time': out[c] = pd.to_numeric(out[c], errors='coerce')
    if 'volume' not in out: out['volume'] = 1.0
    return out.dropna(subset=['time','open','high','low','close']).drop_duplicates('time').sort_values('time').reset_index(drop=True)


def event_available(p):
    mins = p.tf.map({'M5':5,'M15':15,'H1':60})
    if mins.isna().any(): raise ValueError(f'Unknown XAU TFs: {sorted(p.loc[mins.isna(),"tf"].unique())}')
    return p.time + pd.to_timedelta(mins, unit='m')


def build_xau_join(m1_path: Path, pool_path: Path, router):
    actual = sha256(m1_path)
    if actual != XAU_SHA:
        raise RuntimeError(f'Canonical XAU SHA mismatch: {actual}')
    m1 = read_xau_native(m1_path)
    h4 = m1.set_index('time').resample('4h', origin='epoch', label='left', closed='left').agg(
        open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last'), volume=('volume','sum')).dropna()
    ctx = router.add_router(h4)
    pool = pd.read_parquet(pool_path)
    pool['time'] = pd.to_datetime(pool.time, errors='coerce')
    pool['R'] = pd.to_numeric(pool.R, errors='coerce'); pool['excess'] = pd.to_numeric(pool.excess, errors='coerce')
    pool['dir'] = pd.to_numeric(pool.dir, errors='coerce')
    pool = pool.dropna(subset=['time','tf','dir','R','excess']).sort_values('time').copy()
    pool['available_event_time'] = event_available(pool)
    pool['year'] = pool.available_event_time.dt.year.astype(str)
    cols = ['available_time','bias','score_expansion','score_pullback','score_reversal','score_range']
    c = ctx[cols].dropna(subset=['available_time']).sort_values('available_time').reset_index(drop=False)
    j = pd.merge_asof(pool.sort_values('available_event_time'), c, left_on='available_event_time', right_on='available_time', direction='backward', allow_exact_matches=True)
    j = j.dropna(subset=['score_expansion','score_pullback','score_reversal','score_range']).copy()
    j = add_continuous_fields(j, j.dir)
    return j, {'sha256': actual, 'm1_rows': int(len(m1)), 'm1_start': str(m1.time.min()), 'm1_end': str(m1.time.max()), 'pool_finite': int(len(pool)), 'context_eligible': int(len(j))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xau-m1', required=True); ap.add_argument('--xau-pool', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    router = load_router_module()

    btc = pd.read_csv(BTC_INPUT)
    if len(btc) != 327: raise RuntimeError(f'BTC frozen parity failed: {len(btc)} != 327')
    btc['entry_time'] = pd.to_datetime(btc.entry_time, utc=True, errors='coerce')
    btc['net_r_5bps'] = pd.to_numeric(btc.net_r_5bps, errors='coerce')
    btc = add_continuous_fields(btc, pd.Series(-1, index=btc.index))
    btc_eval, btc_summary = evaluate_market('BTC', btc, 'entry_time', 'net_r_5bps', 'period', BTC_PERIODS, 5, out)

    xau, xau_meta = build_xau_join(Path(a.xau_m1), Path(a.xau_pool), router)
    xau_eval, xau_summary = evaluate_market('XAU', xau, 'available_event_time', 'excess', 'year', ['2022','2023','2024','2025','2026'], 100, out, raw_col='R')

    cross_supported = btc_summary['verdict'] == 'CONTINUOUS_CONTEXT_SUPPORTED' and xau_summary['verdict'] == 'CONTINUOUS_CONTEXT_SUPPORTED'
    if cross_supported:
        verdict = 'CROSS_MARKET_CONTINUOUS_CONTEXT_SUPPORTED_DISCOVERY_ONLY'
    elif btc_summary['verdict'] == 'CONTINUOUS_CONTEXT_NOT_SUPPORTED' and xau_summary['verdict'] == 'CONTINUOUS_CONTEXT_NOT_SUPPORTED':
        verdict = 'REJECT_GENERAL_CONTINUOUS_CONTEXT_OVERLAY'
    else:
        verdict = 'MIXED_CROSS_MARKET_CONTINUOUS_CONTEXT'
    summary = {
        'lab': LAB, 'status': 'REUSED_HISTORY_DISCOVERY_INTERACTION_ONLY', 'verdict': verdict,
        'preregistered_score': '(EXPANSION+PULLBACK-REVERSAL-RANGE)/200',
        'btc': btc_summary, 'xau': xau_summary, 'xau_meta': xau_meta,
        'promotion_authorized': False
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, default=str))

    lines = [f'# {LAB}', '', f'**Verdict: {verdict}**', '',
        '> Reused-history discovery only. No thresholds, router weights, alpha rules, or risk sizing were fit in this lab.', '',
        '## Frozen continuous score', '', '`C = (Expansion + Pullback - Reversal - Range) / 200`', '',
        '| Market | N | Q1 mean | Q5 mean | Lift | Slope | Lift 95% CI | Slope 95% CI | Q5 monotone | Positive transfer | Verdict |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for s in [btc_summary, xau_summary]:
        q = s['q5_ordered']; b = s['bootstrap']
        lines.append(f"| {s['market']} | {s['n']:,} | {q.get('bottom_mean',np.nan):+.4f} | {q.get('top_mean',np.nan):+.4f} | {q.get('top_bottom_lift',np.nan):+.4f} | {s['continuous_slope']:+.4f} | [{b.get('lift_ci_lo',np.nan):+.4f}, {b.get('lift_ci_hi',np.nan):+.4f}] | [{b.get('slope_ci_lo',np.nan):+.4f}, {b.get('slope_ci_hi',np.nan):+.4f}] | {q.get('adjacent_monotone_fraction',np.nan):.0%} | {s['positive_transfer_periods']}/{s['required_positive_periods']} required | {s['verdict']} |")
    lines += ['', '## Frozen gates', '']
    for s in [btc_summary, xau_summary]:
        lines.append(f"### {s['market']}")
        for k, v in s['gates'].items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
        lines.append('')
    lines += ['## Interpretation', '',
        '- A pass only supports graded Context information on reused history; it does not authorize live risk modulation.',
        '- Bias compatibility is reported separately in the Q5 × bias matrices and never folded into C.',
        '- XAU primary outcome is drift-adjusted excess; raw R is secondary.',
        '- If only one market passes, Context is market/alpha-specific rather than a general router.']
    (out / 'REPORT.md').write_text('\n'.join(lines))
    print((out / 'REPORT.md').read_text())


if __name__ == '__main__':
    main()
