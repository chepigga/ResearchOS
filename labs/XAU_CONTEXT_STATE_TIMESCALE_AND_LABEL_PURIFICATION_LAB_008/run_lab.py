#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = 'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ROUTER_PATH = ROOT / 'labs' / 'CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001' / 'run_lab.py'
XAU_SHA = 'db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
STATES = ['EXPANSION', 'PULLBACK', 'REVERSAL', 'RANGE']
HORIZONS = {4: 1, 8: 2, 12: 3, 24: 6, 48: 12}
BOOT_N = 5000
SEED = 2026091108
YEARS = [2023, 2024, 2025, 2026]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_router_module():
    spec = importlib.util.spec_from_file_location('lab001_router_timescale', ROUTER_PATH)
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
    miss = [c for c in ['time', 'open', 'high', 'low', 'close'] if c not in out]
    if miss:
        raise ValueError(f'Missing XAU columns {miss}; got={list(raw.columns)}')
    out['time'] = pd.to_datetime(out['time'], errors='coerce')
    for c in [x for x in out.columns if x != 'time']:
        out[c] = pd.to_numeric(out[c], errors='coerce')
    if 'volume' not in out:
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
    d['pre_mom_dir'] = np.sign(d['close'] - d['close'].shift(3)).astype(float).where(prev3_ok)
    d['bias_dir'] = d['bias'].map({'BULL': 1.0, 'BEAR': -1.0, 'NEUTRAL': 0.0}).fillna(0.0)

    score_cols = [f'score_{s.lower()}' for s in STATES]
    score_arr = d[score_cols].apply(pd.to_numeric, errors='coerce')
    d['raw_winner'] = score_arr.idxmax(axis=1).str.replace('score_', '', regex=False).str.upper()
    sorted_vals = np.sort(score_arr.to_numpy(float), axis=1)
    d['raw_score_gap'] = sorted_vals[:, -1] - sorted_vals[:, -2]
    winner_match = d['regime'].eq(d['raw_winner'])
    d['purity_class'] = np.select(
        [winner_match & d['raw_score_gap'].ge(10.0), winner_match],
        ['STRONG_PURE', 'WEAK_PURE'],
        default='INHERITED_CONFLICT'
    )

    for hours, n in HORIZONS.items():
        contiguous = pd.Series(True, index=d.index)
        highs, lows = [], []
        for i in range(1, n + 1):
            contiguous &= idx.shift(-i).eq(idx + pd.Timedelta(hours=4 * i))
            highs.append(d['high'].shift(-i))
            lows.append(d['low'].shift(-i))
        fhi = pd.concat(highs, axis=1).max(axis=1).where(contiguous)
        flo = pd.concat(lows, axis=1).min(axis=1).where(contiguous)
        fclose = d['close'].shift(-n).where(contiguous)
        atr = d['atr14'].replace(0, np.nan)
        ret = (fclose - d['close']) / atr
        d[f'close_ret_atr_{hours}h'] = ret
        d[f'abs_close_atr_{hours}h'] = ret.abs()
        d[f'range_atr_{hours}h'] = ((fhi - flo) / atr).where(contiguous)
        hit_up = (fhi >= d['close'] + atr).where(contiguous)
        hit_dn = (flo <= d['close'] - atr).where(contiguous)
        d[f'contained_1atr_{hours}h'] = (~(hit_up | hit_dn)).astype(float).where(contiguous)
        d[f'two_sided_1atr_{hours}h'] = (hit_up & hit_dn).astype(float).where(contiguous)
        mom_valid = d['pre_mom_dir'].notna() & d['pre_mom_dir'].ne(0) & ret.notna()
        d[f'momentum_flip_{hours}h'] = (ret * d['pre_mom_dir'] < 0).astype(float).where(mom_valid)
        bias_valid = d['bias_dir'].ne(0) & ret.notna()
        d[f'bias_follow_{hours}h'] = (ret * d['bias_dir'] > 0).astype(float).where(bias_valid)
        d[f'bias_signed_close_atr_{hours}h'] = (ret * d['bias_dir']).where(bias_valid)
    return d


def make_episodes(d: pd.DataFrame):
    z = d[d['regime'].isin(STATES)].copy().sort_index()
    idx = pd.Series(z.index, index=z.index)
    new_ep = z['regime'].ne(z['regime'].shift(1)) | idx.diff().gt(pd.Timedelta(hours=4))
    z['episode_id'] = new_ep.cumsum().astype(int)
    z['episode_age'] = z.groupby('episode_id').cumcount() + 1
    z['age_bucket'] = np.select(
        [z['episode_age'].eq(1), z['episode_age'].between(2, 3)],
        ['ONSET', 'EARLY'], default='MATURE'
    )
    onset = z[z['episode_age'].eq(1)].copy()
    return z, onset


def week_col(t: pd.Series) -> pd.Series:
    return pd.to_datetime(t).dt.to_period('W-SUN').astype(str)


def bootstrap_pair(df: pd.DataFrame, metric: str, a: str, b: str, seed: int) -> dict:
    z = df[df['regime'].isin([a, b])][['available_time', 'regime', metric]].copy()
    z[metric] = pd.to_numeric(z[metric], errors='coerce')
    z = z.dropna(subset=['available_time', metric])
    va = z.loc[z['regime'].eq(a), metric]
    vb = z.loc[z['regime'].eq(b), metric]
    observed = float(va.mean() - vb.mean()) if len(va) and len(vb) else np.nan
    if z.empty:
        return {'observed': observed, 'ci_lo': np.nan, 'ci_hi': np.nan, 'p_positive': np.nan, 'n_a': len(va), 'n_b': len(vb), 'weeks': 0}
    z['week'] = week_col(z['available_time'])
    weeks = sorted(z['week'].unique())
    stats = []
    for w in weeks:
        g = z[z['week'].eq(w)]
        xa = g.loc[g['regime'].eq(a), metric].to_numpy(float)
        xb = g.loc[g['regime'].eq(b), metric].to_numpy(float)
        stats.append([len(xa), np.nansum(xa), len(xb), np.nansum(xb)])
    arr = np.asarray(stats, float)
    rng = np.random.default_rng(seed)
    draws = np.full(BOOT_N, np.nan)
    m = len(arr)
    for k in range(BOOT_N):
        s = arr[rng.integers(0, m, size=m)].sum(axis=0)
        if s[0] > 0 and s[2] > 0:
            draws[k] = s[1] / s[0] - s[3] / s[2]
    draws = draws[np.isfinite(draws)]
    return {
        'observed': observed,
        'ci_lo': float(np.quantile(draws, .025)) if len(draws) else np.nan,
        'ci_hi': float(np.quantile(draws, .975)) if len(draws) else np.nan,
        'p_positive': float(np.mean(draws > 0)) if len(draws) else np.nan,
        'n_a': int(len(va)), 'n_b': int(len(vb)), 'weeks': int(m)
    }


def bootstrap_one_sample(df: pd.DataFrame, metric: str, state: str, null: float, seed: int) -> dict:
    z = df[df['regime'].eq(state)][['available_time', metric]].copy()
    z[metric] = pd.to_numeric(z[metric], errors='coerce')
    z = z.dropna(subset=['available_time', metric])
    v = z[metric]
    observed = float(v.mean() - null) if len(v) else np.nan
    if z.empty:
        return {'observed': observed, 'ci_lo': np.nan, 'ci_hi': np.nan, 'p_positive': np.nan, 'n_a': 0, 'n_b': 0, 'weeks': 0}
    z['week'] = week_col(z['available_time'])
    stats = z.groupby('week')[metric].agg(['count', 'sum']).reset_index(drop=True).to_numpy(float)
    rng = np.random.default_rng(seed)
    draws = np.full(BOOT_N, np.nan)
    m = len(stats)
    for k in range(BOOT_N):
        s = stats[rng.integers(0, m, size=m)].sum(axis=0)
        if s[0] > 0:
            draws[k] = s[1] / s[0] - null
    draws = draws[np.isfinite(draws)]
    return {
        'observed': observed,
        'ci_lo': float(np.quantile(draws, .025)) if len(draws) else np.nan,
        'ci_hi': float(np.quantile(draws, .975)) if len(draws) else np.nan,
        'p_positive': float(np.mean(draws > 0)) if len(draws) else np.nan,
        'n_a': int(len(v)), 'n_b': 0, 'weeks': int(m)
    }


def semantic_spec(state: str, h: int):
    if state == 'EXPANSION':
        return f'range_atr_{h}h', 'RANGE', 'PAIR'
    if state == 'RANGE':
        return f'contained_1atr_{h}h', 'EXPANSION', 'PAIR'
    if state == 'REVERSAL':
        return f'momentum_flip_{h}h', 'EXPANSION', 'PAIR'
    if state == 'PULLBACK':
        return f'bias_follow_{h}h', '0.50', 'ONE'
    raise KeyError(state)


def state_timescale(onset: pd.DataFrame):
    rows = []
    for si, state in enumerate(STATES):
        for hi, h in enumerate(HORIZONS):
            metric, comparator, kind = semantic_spec(state, h)
            if kind == 'PAIR':
                b = bootstrap_pair(onset, metric, state, comparator, SEED + si * 100 + hi)
            else:
                b = bootstrap_one_sample(onset, metric, state, 0.50, SEED + si * 100 + hi)
            rows.append({
                'state': state, 'horizon_h': h, 'metric': metric, 'comparator': comparator,
                **b, 'confirmed': bool(np.isfinite(b['observed']) and b['observed'] > 0 and np.isfinite(b['ci_lo']) and b['ci_lo'] > 0)
            })
    return pd.DataFrame(rows)


def raw_metric_summary(onset: pd.DataFrame):
    rows = []
    metrics = ['range_atr', 'abs_close_atr', 'contained_1atr', 'two_sided_1atr', 'momentum_flip', 'bias_follow', 'bias_signed_close_atr']
    for state in STATES:
        g = onset[onset['regime'].eq(state)]
        for h in HORIZONS:
            rec = {'state': state, 'horizon_h': h, 'episodes': int(len(g))}
            for base in metrics:
                c = f'{base}_{h}h'
                v = pd.to_numeric(g[c], errors='coerce').dropna()
                rec[f'{base}_n'] = int(len(v))
                rec[f'{base}_mean'] = float(v.mean()) if len(v) else np.nan
                rec[f'{base}_median'] = float(v.median()) if len(v) else np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


def year_transfer(onset: pd.DataFrame):
    d = onset.copy()
    d['year'] = pd.to_datetime(d['available_time']).dt.year
    rows = []
    for state in STATES:
        for h in HORIZONS:
            metric, comparator, kind = semantic_spec(state, h)
            for year in [2022, *YEARS]:
                g = d[d['year'].eq(year)]
                a = pd.to_numeric(g.loc[g['regime'].eq(state), metric], errors='coerce').dropna()
                if kind == 'PAIR':
                    b = pd.to_numeric(g.loc[g['regime'].eq(comparator), metric], errors='coerce').dropna()
                    effect = float(a.mean() - b.mean()) if len(a) and len(b) else np.nan
                    nb = int(len(b))
                else:
                    effect = float(a.mean() - .50) if len(a) else np.nan
                    nb = 0
                rows.append({
                    'state': state, 'horizon_h': h, 'year': year, 'metric': metric,
                    'comparator': comparator, 'n_a': int(len(a)), 'n_b': nb,
                    'effect': effect, 'positive': bool(np.isfinite(effect) and effect > 0)
                })
    return pd.DataFrame(rows)


def purity_bootstrap(onset: pd.DataFrame):
    rows = []
    for si, state in enumerate(STATES):
        for hi, h in enumerate(HORIZONS):
            metric, _, _ = semantic_spec(state, h)
            g = onset[onset['regime'].eq(state)][['available_time', 'purity_class', metric]].copy()
            g['group'] = np.where(g['purity_class'].eq('STRONG_PURE'), 'STRONG', 'NOT_STRONG')
            g[metric] = pd.to_numeric(g[metric], errors='coerce')
            g = g.dropna(subset=[metric, 'available_time'])
            va = g.loc[g['group'].eq('STRONG'), metric]
            vb = g.loc[g['group'].eq('NOT_STRONG'), metric]
            observed = float(va.mean() - vb.mean()) if len(va) and len(vb) else np.nan
            if len(g):
                g['week'] = week_col(g['available_time'])
                weeks = sorted(g['week'].unique())
                stats = []
                for w in weeks:
                    gw = g[g['week'].eq(w)]
                    xa = gw.loc[gw['group'].eq('STRONG'), metric].to_numpy(float)
                    xb = gw.loc[gw['group'].eq('NOT_STRONG'), metric].to_numpy(float)
                    stats.append([len(xa), np.nansum(xa), len(xb), np.nansum(xb)])
                arr = np.asarray(stats, float)
                rng = np.random.default_rng(SEED + 1000 + si * 100 + hi)
                draws = np.full(BOOT_N, np.nan)
                m = len(arr)
                for k in range(BOOT_N):
                    s = arr[rng.integers(0, m, size=m)].sum(axis=0)
                    if s[0] > 0 and s[2] > 0:
                        draws[k] = s[1] / s[0] - s[3] / s[2]
                draws = draws[np.isfinite(draws)]
            else:
                draws = np.array([], float); m = 0
            rows.append({
                'state': state, 'horizon_h': h, 'metric': metric,
                'strong_n': int(len(va)), 'not_strong_n': int(len(vb)),
                'strong_mean': float(va.mean()) if len(va) else np.nan,
                'not_strong_mean': float(vb.mean()) if len(vb) else np.nan,
                'effect': observed,
                'ci_lo': float(np.quantile(draws, .025)) if len(draws) else np.nan,
                'ci_hi': float(np.quantile(draws, .975)) if len(draws) else np.nan,
                'p_positive': float(np.mean(draws > 0)) if len(draws) else np.nan,
                'n_eligible': bool(len(va) >= 20 and len(vb) >= 20),
                'positive': bool(np.isfinite(observed) and observed > 0),
                'confirmed_positive': bool(np.isfinite(observed) and observed > 0 and len(va) >= 20 and len(vb) >= 20 and len(draws) and np.quantile(draws, .025) > 0)
            })
    return pd.DataFrame(rows)


def age_audit(allbars: pd.DataFrame):
    rows = []
    for state in STATES:
        for h in HORIZONS:
            metric, _, _ = semantic_spec(state, h)
            for age in ['ONSET', 'EARLY', 'MATURE']:
                v = pd.to_numeric(allbars.loc[(allbars['regime'].eq(state)) & (allbars['age_bucket'].eq(age)), metric], errors='coerce').dropna()
                rows.append({'state': state, 'horizon_h': h, 'metric': metric, 'age_bucket': age,
                             'n': int(len(v)), 'mean': float(v.mean()) if len(v) else np.nan,
                             'median': float(v.median()) if len(v) else np.nan})
    return pd.DataFrame(rows)


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
    allbars, onset = make_episodes(ctx)

    if len(allbars) != 6216 or len(onset) != 610:
        raise RuntimeError(f'LAB007 parity failed: allbars={len(allbars)} onset={len(onset)} expected 6216/610')

    timescale = state_timescale(onset)
    raw = raw_metric_summary(onset)
    yearly = year_transfer(onset)
    purity = purity_bootstrap(onset)
    age = age_audit(allbars)

    timescale.to_csv(out / 'state_timescale_contrasts.csv', index=False)
    raw.to_csv(out / 'state_horizon_metrics.csv', index=False)
    yearly.to_csv(out / 'year_transfer.csv', index=False)
    purity.to_csv(out / 'purity_contrasts.csv', index=False)
    age.to_csv(out / 'episode_age_semantics.csv', index=False)

    purity_dist = (onset.groupby(['regime', 'purity_class']).size().rename('episodes').reset_index())
    purity_dist['share_within_state'] = purity_dist['episodes'] / purity_dist.groupby('regime')['episodes'].transform('sum')
    purity_dist.to_csv(out / 'purity_distribution.csv', index=False)

    state_rows = []
    confirmed_count = 0; transferred_count = 0
    for state in STATES:
        g = timescale[timescale['state'].eq(state)].sort_values('horizon_h')
        confirmed = g[g['confirmed']]
        confirmed_h = int(confirmed.iloc[0]['horizon_h']) if len(confirmed) else None
        peak_row = g.loc[g['observed'].idxmax()] if g['observed'].notna().any() else None
        peak_h = int(peak_row['horizon_h']) if peak_row is not None else None
        peak_effect = float(peak_row['observed']) if peak_row is not None else np.nan
        if confirmed_h is not None:
            confirmed_count += 1
            yg = yearly[(yearly['state'].eq(state)) & (yearly['horizon_h'].eq(confirmed_h)) & (yearly['year'].isin(YEARS))]
            eligible_years = int(yg['effect'].notna().sum())
            positive_years = int(yg.loc[yg['effect'].notna(), 'positive'].sum())
            time_transferred = bool(eligible_years == 4 and positive_years >= 3)
        else:
            eligible_years = 0; positive_years = 0; time_transferred = False
        if time_transferred:
            transferred_count += 1

        pg = purity[purity['state'].eq(state)].copy()
        eligible_h = int(pg['n_eligible'].sum())
        positive_h = int((pg['n_eligible'] & pg['positive']).sum())
        ci_h = int((pg['n_eligible'] & pg['confirmed_positive']).sum())
        if eligible_h < 3:
            purity_verdict = 'PURITY_UNDERPOWERED'
        elif positive_h >= 3 and ci_h >= 1:
            purity_verdict = 'PURITY_SUPPORTED'
        else:
            purity_verdict = 'PURITY_NOT_CONFIRMED'

        state_rows.append({
            'state': state, 'confirmed_horizon_h': confirmed_h, 'peak_observed_horizon_h': peak_h,
            'peak_observed_effect': peak_effect, 'eligible_years_at_confirmed': eligible_years,
            'positive_years_at_confirmed': positive_years, 'time_transfer': 'TIME_TRANSFERRED' if time_transferred else 'TIME_UNSTABLE',
            'purity_eligible_horizons': eligible_h, 'purity_positive_horizons': positive_h,
            'purity_ci_confirmed_horizons': ci_h, 'purity_verdict': purity_verdict
        })
    state_summary = pd.DataFrame(state_rows)
    state_summary.to_csv(out / 'state_timescale_summary.csv', index=False)

    if confirmed_count >= 3 and transferred_count >= 2:
        verdict = 'CONTEXT_LABELS_HAVE_USABLE_TIMESCALES'
    elif confirmed_count >= 1:
        verdict = 'CONTEXT_LABELS_PARTIALLY_TIMESCALE_SPECIFIC'
    else:
        verdict = 'CONTEXT_LABELS_REQUIRE_REDESIGN'

    summary = {
        'lab': LAB,
        'status': 'REUSED_HISTORY_PREREGISTERED_STATE_DIAGNOSTIC',
        'verdict': verdict,
        'xau_sha256': actual,
        'm1_rows': int(len(m1)),
        'h4_rows': int(len(h4)),
        'valid_context_bars': int(len(allbars)),
        'episode_onsets': int(len(onset)),
        'confirmed_states': int(confirmed_count),
        'time_transferred_states': int(transferred_count),
        'state_summary': state_rows,
        'promotion_authorized': False,
        'trading_edge_tested': False
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, default=str))

    lines = [
        f'# {LAB}', '', f'**Verdict: {verdict}**', '',
        '> State-meaning diagnostic only. No trading edge, TP/SL, PF/EV or live-risk claim.', '',
        f'- Canonical XAU SHA: `{actual}`',
        f'- Valid Context H4 bars: **{len(allbars):,}**',
        f'- Primary episode onsets: **{len(onset):,}**', '',
        '## Natural timescale by label', '',
        '| State | Confirmed horizon | Peak observed horizon | Peak effect | Year transfer | Purity |',
        '|---|---:|---:|---:|---|---|'
    ]
    for r in state_rows:
        ch = f"{r['confirmed_horizon_h']}h" if r['confirmed_horizon_h'] is not None else 'NONE'
        ph = f"{r['peak_observed_horizon_h']}h" if r['peak_observed_horizon_h'] is not None else 'NONE'
        lines.append(f"| {r['state']} | {ch} | {ph} | {r['peak_observed_effect']:+.4f} | {r['time_transfer']} ({r['positive_years_at_confirmed']}/{r['eligible_years_at_confirmed']}) | {r['purity_verdict']} |")

    lines += ['', '## Horizon contrasts', '',
              '| State | H | Effect | 95% CI | P(>0) | N state | N comparator | Confirmed |',
              '|---|---:|---:|---:|---:|---:|---:|---|']
    for _, r in timescale.iterrows():
        lines.append(f"| {r['state']} | {int(r['horizon_h'])}h | {r['observed']:+.4f} | [{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}] | {r['p_positive']:.3f} | {int(r['n_a'])} | {int(r['n_b'])} | {'YES' if r['confirmed'] else 'NO'} |")

    lines += ['', '## Purity distribution — episode onsets', '']
    for state in STATES:
        g = purity_dist[purity_dist['regime'].eq(state)]
        parts = [f"{x.purity_class}={int(x.episodes)} ({x.share_within_state:.1%})" for x in g.itertuples()]
        lines.append(f"- **{state}:** " + '; '.join(parts))

    lines += ['', '## Interpretation', '',
              '- `confirmed_horizon` is the earliest preregistered horizon with positive semantic effect and weekly-bootstrap 95% CI entirely above zero.',
              '- `peak_observed_horizon` is descriptive only and must not be treated as confirmed when its CI fails.',
              '- `STRONG_PURE` means the hysteresis label is also the current raw score winner with >=10 score-point lead.',
              '- If purity helps, the next lab may preregister a redesigned display layer; this lab itself does not change the router.',
              '- Reused history: no live/production promotion is authorized.']
    (out / 'REPORT.md').write_text('\n'.join(lines))
    print((out / 'REPORT.md').read_text())


if __name__ == '__main__':
    main()
