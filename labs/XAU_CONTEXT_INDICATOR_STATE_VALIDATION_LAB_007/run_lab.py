#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = 'XAU_CONTEXT_INDICATOR_STATE_VALIDATION_LAB_007'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ROUTER_PATH = ROOT / 'labs' / 'CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001' / 'run_lab.py'
XAU_SHA = 'db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
STATES = ['EXPANSION', 'PULLBACK', 'REVERSAL', 'RANGE']
HORIZONS = {4: 1, 12: 3, 24: 6, 48: 12}
BOOT_N = 5000
SEED = 2026091107


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_router_module():
    spec = importlib.util.spec_from_file_location('lab001_router_state_validation', ROUTER_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def read_xau_native(path: Path) -> pd.DataFrame:
    first = path.open('r', encoding='utf-8', errors='ignore').readline()
    sep = ';' if first.count(';') > first.count(',') else ','
    raw = pd.read_csv(path, sep=sep)
    lut = {c.lower(): c for c in raw.columns}
    aliases = {
        'time': ['time', 'timestamp', 'datetime', 'date_time', '<date>'],
        'open': ['open', 'bid_open', '<open>'],
        'high': ['high', 'bid_high', '<high>'],
        'low': ['low', 'bid_low', '<low>'],
        'close': ['close', 'bid_close', '<close>'],
        'volume': ['tick_volume', 'tickvolume', 'tick_vol', 'ticks', 'volume', '<tickvol>'],
    }
    out = pd.DataFrame()
    for dst, names in aliases.items():
        for name in names:
            if name.lower() in lut:
                out[dst] = raw[lut[name.lower()]]
                break
    miss = [c for c in ['time', 'open', 'high', 'low', 'close'] if c not in out.columns]
    if miss:
        raise ValueError(f'Missing XAU columns {miss}; got={list(raw.columns)}')
    out['time'] = pd.to_datetime(out['time'], errors='coerce')
    for c in [x for x in out.columns if x != 'time']:
        out[c] = pd.to_numeric(out[c], errors='coerce')
    if 'volume' not in out.columns:
        out['volume'] = 1.0
    return out.dropna(subset=['time', 'open', 'high', 'low', 'close']).drop_duplicates('time').sort_values('time').reset_index(drop=True)


def to_h4(m1: pd.DataFrame) -> pd.DataFrame:
    return (m1.set_index('time').resample('4h', origin='epoch', label='left', closed='left')
            .agg(open=('open', 'first'), high=('high', 'max'), low=('low', 'min'), close=('close', 'last'), volume=('volume', 'sum'))
            .dropna())


def add_forward_metrics(ctx: pd.DataFrame) -> pd.DataFrame:
    d = ctx.copy().sort_index()
    idx = pd.Series(d.index, index=d.index)
    prev3_ok = idx.shift(3).eq(idx - pd.Timedelta(hours=12))
    pre = np.sign(d['close'] - d['close'].shift(3)).astype(float)
    d['pre_mom_dir'] = pre.where(prev3_ok)
    d['bias_dir'] = d['bias'].map({'BULL': 1.0, 'BEAR': -1.0, 'NEUTRAL': 0.0}).fillna(0.0)

    for hours, n in HORIZONS.items():
        contiguous = pd.Series(True, index=d.index)
        future_highs, future_lows = [], []
        for i in range(1, n + 1):
            contiguous &= idx.shift(-i).eq(idx + pd.Timedelta(hours=4 * i))
            future_highs.append(d['high'].shift(-i))
            future_lows.append(d['low'].shift(-i))
        fhi = pd.concat(future_highs, axis=1).max(axis=1).where(contiguous)
        flo = pd.concat(future_lows, axis=1).min(axis=1).where(contiguous)
        fclose = d['close'].shift(-n).where(contiguous)
        atr = d['atr14'].replace(0, np.nan)
        ret_atr = (fclose - d['close']) / atr
        d[f'close_ret_atr_{hours}h'] = ret_atr
        d[f'abs_close_atr_{hours}h'] = ret_atr.abs()
        d[f'range_atr_{hours}h'] = ((fhi - flo) / atr).where(contiguous)
        d[f'up_exc_atr_{hours}h'] = ((fhi - d['close']) / atr).where(contiguous)
        d[f'down_exc_atr_{hours}h'] = ((d['close'] - flo) / atr).where(contiguous)
        hit_up = (fhi >= d['close'] + atr).where(contiguous)
        hit_dn = (flo <= d['close'] - atr).where(contiguous)
        d[f'contained_1atr_{hours}h'] = (~(hit_up | hit_dn)).astype(float).where(contiguous)
        d[f'two_sided_1atr_{hours}h'] = (hit_up & hit_dn).astype(float).where(contiguous)
        mom_valid = d['pre_mom_dir'].notna() & d['pre_mom_dir'].ne(0) & ret_atr.notna()
        d[f'momentum_flip_{hours}h'] = (ret_atr * d['pre_mom_dir'] < 0).astype(float).where(mom_valid)
        bias_valid = d['bias_dir'].ne(0) & ret_atr.notna()
        d[f'bias_follow_{hours}h'] = (ret_atr * d['bias_dir'] > 0).astype(float).where(bias_valid)
        d[f'bias_signed_close_atr_{hours}h'] = (ret_atr * d['bias_dir']).where(bias_valid)
    return d


def make_episodes(d: pd.DataFrame):
    z = d[d['regime'].isin(STATES)].copy().sort_index()
    idx = pd.Series(z.index, index=z.index)
    new_ep = z['regime'].ne(z['regime'].shift(1)) | idx.diff().gt(pd.Timedelta(hours=4))
    z['episode_id'] = new_ep.cumsum().astype(int)
    onset = z.groupby('episode_id', sort=True).head(1).copy()
    rows = []
    for eid, g in z.groupby('episode_id', sort=True):
        rows.append({
            'episode_id': int(eid), 'state': str(g['regime'].iloc[0]),
            'start_h4_open': str(g.index.min()), 'available_start': str(g['available_time'].iloc[0]),
            'bars': int(len(g)), 'market_hours': int(len(g) * 4),
            'mean_confidence': float(pd.to_numeric(g['regime_confidence'], errors='coerce').mean())
        })
    return z, onset, pd.DataFrame(rows)


def state_horizon_summary(df: pd.DataFrame, sample: str) -> pd.DataFrame:
    rows = []
    for h in HORIZONS:
        for state in STATES:
            g = df[df['regime'].eq(state)]
            rec = {'sample': sample, 'horizon_h': h, 'state': state, 'n_rows': int(len(g))}
            for base in ['range_atr', 'abs_close_atr', 'up_exc_atr', 'down_exc_atr', 'contained_1atr', 'two_sided_1atr', 'momentum_flip', 'bias_follow', 'bias_signed_close_atr']:
                c = f'{base}_{h}h'
                v = pd.to_numeric(g[c], errors='coerce').dropna()
                rec[f'{base}_n'] = int(len(v))
                rec[f'{base}_mean'] = float(v.mean()) if len(v) else np.nan
                rec[f'{base}_median'] = float(v.median()) if len(v) else np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


def cluster_bootstrap_diff(df: pd.DataFrame, metric: str, state_a: str, state_b: str, seed: int) -> dict:
    z = df[df['regime'].isin([state_a, state_b])][['available_time', 'regime', metric]].copy()
    z[metric] = pd.to_numeric(z[metric], errors='coerce')
    z = z.dropna(subset=['available_time', metric])
    if z.empty:
        return {'observed': np.nan, 'ci_lo': np.nan, 'ci_hi': np.nan, 'p_positive': np.nan, 'weeks': 0, 'n_a': 0, 'n_b': 0}
    z['week'] = pd.to_datetime(z['available_time']).dt.to_period('W-SUN').astype(str)
    va = z.loc[z['regime'].eq(state_a), metric]
    vb = z.loc[z['regime'].eq(state_b), metric]
    observed = float(va.mean() - vb.mean()) if len(va) and len(vb) else np.nan
    weeks = sorted(z['week'].unique())
    arr = []
    for w in weeks:
        gw = z[z['week'].eq(w)]
        a = gw.loc[gw['regime'].eq(state_a), metric].to_numpy(float)
        b = gw.loc[gw['regime'].eq(state_b), metric].to_numpy(float)
        arr.append([len(a), np.nansum(a), len(b), np.nansum(b)])
    a = np.asarray(arr, float)
    rng = np.random.default_rng(seed)
    draws = np.full(BOOT_N, np.nan)
    m = len(a)
    for k in range(BOOT_N):
        s = a[rng.integers(0, m, size=m)].sum(axis=0)
        if s[0] > 0 and s[2] > 0:
            draws[k] = s[1] / s[0] - s[3] / s[2]
    draws = draws[np.isfinite(draws)]
    return {
        'observed': observed,
        'ci_lo': float(np.quantile(draws, .025)) if len(draws) else np.nan,
        'ci_hi': float(np.quantile(draws, .975)) if len(draws) else np.nan,
        'p_positive': float(np.mean(draws > 0)) if len(draws) else np.nan,
        'weeks': int(m), 'draws': int(len(draws)), 'n_a': int(len(va)), 'n_b': int(len(vb))
    }


def year_effects(df: pd.DataFrame, specs: list[dict]) -> pd.DataFrame:
    rows = []
    d = df.copy()
    d['year'] = pd.to_datetime(d['available_time']).dt.year
    for spec in specs:
        for year in [2022, 2023, 2024, 2025, 2026]:
            g = d[d['year'].eq(year)]
            va = pd.to_numeric(g.loc[g['regime'].eq(spec['a']), spec['metric']], errors='coerce').dropna()
            vb = pd.to_numeric(g.loc[g['regime'].eq(spec['b']), spec['metric']], errors='coerce').dropna()
            effect = float(va.mean() - vb.mean()) if len(va) and len(vb) else np.nan
            rows.append({'hypothesis': spec['name'], 'year': year, 'state_a': spec['a'], 'state_b': spec['b'],
                         'metric': spec['metric'], 'n_a': int(len(va)), 'n_b': int(len(vb)),
                         'effect': effect, 'expected_positive': True,
                         'positive': bool(np.isfinite(effect) and effect > 0)})
    return pd.DataFrame(rows)


def transition_tables(allbars: pd.DataFrame):
    z = allbars.copy().sort_index()
    idx = pd.Series(z.index, index=z.index)
    nxt = z['regime'].shift(-1)
    contiguous = idx.shift(-1).eq(idx + pd.Timedelta(hours=4))
    t = pd.DataFrame({'from_state': z['regime'], 'to_state': nxt}).loc[contiguous]
    t = t[t['from_state'].isin(STATES) & t['to_state'].isin(STATES)]
    counts = pd.crosstab(t['from_state'], t['to_state']).reindex(index=STATES, columns=STATES, fill_value=0)
    probs = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0)
    return counts, probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xau-m1', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    p = Path(a.xau_m1)
    actual = sha256(p)
    if actual != XAU_SHA:
        raise RuntimeError(f'Canonical XAU SHA mismatch: {actual}')

    m1 = read_xau_native(p)
    h4 = to_h4(m1)
    router = load_router_module()
    ctx = router.add_router(h4)
    ctx = add_forward_metrics(ctx)
    ctx = ctx.dropna(subset=['available_time', 'atr14']).copy()

    allbars, onset, episodes = make_episodes(ctx)
    if not set(STATES).issubset(set(allbars['regime'].dropna().unique())):
        raise RuntimeError(f'Missing states: {set(STATES) - set(allbars.regime.dropna().unique())}')

    primary_summary = state_horizon_summary(onset, 'EPISODE_ONSET')
    secondary_summary = state_horizon_summary(allbars, 'ALL_H4_BARS')
    primary_summary.to_csv(out / 'primary_state_horizon_summary.csv', index=False)
    secondary_summary.to_csv(out / 'secondary_allbars_state_horizon_summary.csv', index=False)
    episodes.to_csv(out / 'episodes.csv', index=False)

    occ = allbars.groupby('regime').agg(bars=('regime', 'size'), confidence_mean=('regime_confidence', 'mean'), confidence_median=('regime_confidence', 'median')).reindex(STATES)
    occ['share'] = occ['bars'] / occ['bars'].sum()
    epstat = episodes.groupby('state').agg(episodes=('episode_id', 'size'), median_bars=('bars', 'median'), mean_bars=('bars', 'mean'), max_bars=('bars', 'max')).reindex(STATES)
    occ = occ.join(epstat)
    occ.to_csv(out / 'occupancy_episode_stats.csv')

    counts, probs = transition_tables(allbars)
    counts.to_csv(out / 'transition_counts.csv')
    probs.to_csv(out / 'transition_probabilities.csv')

    specs = [
        {'name': 'H1_EXPANSION_RANGE_MOVEMENT', 'metric': 'range_atr_24h', 'a': 'EXPANSION', 'b': 'RANGE'},
        {'name': 'H2_EXPANSION_RANGE_DISPLACEMENT', 'metric': 'abs_close_atr_24h', 'a': 'EXPANSION', 'b': 'RANGE'},
        {'name': 'H3_RANGE_CONTAINMENT', 'metric': 'contained_1atr_24h', 'a': 'RANGE', 'b': 'EXPANSION'},
        {'name': 'H4_REVERSAL_MOMENTUM_FLIP', 'metric': 'momentum_flip_24h', 'a': 'REVERSAL', 'b': 'EXPANSION'},
        {'name': 'H5_PULLBACK_BIAS_RESUME', 'metric': 'bias_follow_24h', 'a': 'PULLBACK', 'b': 'RANGE'},
    ]

    hyp_rows = []
    for i, spec in enumerate(specs):
        b = cluster_bootstrap_diff(onset, spec['metric'], spec['a'], spec['b'], SEED + i)
        gate = bool(np.isfinite(b['observed']) and b['observed'] > 0 and np.isfinite(b['ci_lo']) and b['ci_lo'] > 0)
        hyp_rows.append({**spec, **b, 'gate_pass': gate})
    hyps = pd.DataFrame(hyp_rows)
    hyps.to_csv(out / 'primary_hypotheses.csv', index=False)

    years = year_effects(onset, specs)
    years.to_csv(out / 'year_transfer.csv', index=False)
    transfer_rows = []
    for spec in specs:
        g = years[(years['hypothesis'].eq(spec['name'])) & years['year'].isin([2023, 2024, 2025, 2026])]
        eligible = g['effect'].notna()
        n_eligible = int(eligible.sum())
        positive = int(g.loc[eligible, 'positive'].sum())
        stable = bool(n_eligible == 4 and positive >= 3)
        transfer_rows.append({'hypothesis': spec['name'], 'eligible_years': n_eligible, 'positive_years': positive, 'stable_3_of_4': stable})
    transfer = pd.DataFrame(transfer_rows)
    transfer.to_csv(out / 'transfer_summary.csv', index=False)

    semantic_passes = int(hyps['gate_pass'].sum())
    stable_hypotheses = int(transfer['stable_3_of_4'].sum())
    transfer_gate = stable_hypotheses >= 3
    if semantic_passes >= 4 and transfer_gate:
        verdict = 'CONTEXT_STATE_SEMANTICS_SUPPORTED_DISCOVERY_ONLY'
    elif semantic_passes <= 1:
        verdict = 'CONTEXT_STATE_SEMANTICS_NOT_SUPPORTED'
    else:
        verdict = 'PARTIAL_CONTEXT_STATE_SEPARATION'

    summary = {
        'lab': LAB,
        'status': 'REUSED_HISTORY_CAUSAL_STATE_VALIDATION_ONLY',
        'verdict': verdict,
        'canonical_sha256': actual,
        'm1_rows': int(len(m1)), 'h4_rows': int(len(h4)),
        'context_valid_bars': int(len(allbars)), 'episode_onsets': int(len(onset)),
        'context_start': str(allbars.index.min()), 'context_end': str(allbars.index.max()),
        'semantic_passes': semantic_passes,
        'stable_transfer_hypotheses': stable_hypotheses,
        'transfer_gate': bool(transfer_gate),
        'promotion_authorized': False,
        'primary_hypotheses': hyp_rows,
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, default=str))

    s24 = primary_summary[primary_summary['horizon_h'].eq(24)].set_index('state')
    lines = [f'# {LAB}', '', f'**Verdict: {verdict}**', '',
             '> This lab validates state semantics, not trading edge. No TP/SL, no PF/EV gate, no live-risk authorization.', '',
             f'- Canonical XAU SHA: `{actual}`', f'- Valid H4 Context bars: **{len(allbars):,}**', f'- Primary state episodes: **{len(onset):,}**', '',
             '## Primary 24h state map — episode onsets', '',
             '| State | Episodes | Range / ATR | |Close| / ATR | Contained ±1ATR | Momentum flip | Bias follow | Median episode H4 bars |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for state in STATES:
        r = s24.loc[state]
        med_ep = occ.loc[state, 'median_bars']
        lines.append(f"| {state} | {int(r['n_rows'])} | {r['range_atr_mean']:.3f} | {r['abs_close_atr_mean']:.3f} | {r['contained_1atr_mean']:.1%} | {r['momentum_flip_mean']:.1%} | {r['bias_follow_mean']:.1%} | {med_ep:.1f} |")
    lines += ['', '## Preregistered semantic gates', '',
             '| Hypothesis | Effect | 95% weekly-cluster CI | P(effect>0) | Gate | Year sign transfer |',
             '|---|---:|---:|---:|---|---|']
    tmap = transfer.set_index('hypothesis')
    for _, r in hyps.iterrows():
        tr = tmap.loc[r['name']]
        lines.append(f"| {r['name']} | {r['observed']:+.4f} | [{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}] | {r['p_positive']:.3f} | {'PASS' if r['gate_pass'] else 'FAIL'} | {int(tr['positive_years'])}/{int(tr['eligible_years'])} |")
    lines += ['', f'**Semantic gates:** {semantic_passes}/5  ', f'**Stable 3-of-4-year hypotheses:** {stable_hypotheses}/5  ', f'**Transfer gate:** {"PASS" if transfer_gate else "FAIL"}', '',
              '## Interpretation rules', '',
              '- `EXPANSION` is useful if it identifies more future movement/displacement than `RANGE`; it does not need to make money by itself.',
              '- `RANGE` is useful if it genuinely contains price more often.',
              '- `REVERSAL` is useful if it increases the probability that already-known pre-state momentum flips.',
              '- `PULLBACK` is useful if it more often resumes the already-known structural bias than `RANGE`.',
              '- 4h/12h/48h and all-H4-bar tables are diagnostics only; the preregistered verdict is driven by 24h episode onsets.']
    (out / 'REPORT.md').write_text('\n'.join(lines))
    print((out / 'REPORT.md').read_text())


if __name__ == '__main__':
    main()
