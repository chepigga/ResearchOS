#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = 'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAB8_PATH = ROOT / 'labs' / 'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008' / 'run_lab.py'
XAU_SHA = 'db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
HORIZONS = [4, 8, 12, 24, 48]
YEARS = [2023, 2024, 2025, 2026]
BOOT_N = 5000
SEED = 2026091109


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_lab8():
    spec = importlib.util.spec_from_file_location('xau_context_lab8', LAB8_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def add_roles(allbars: pd.DataFrame) -> pd.DataFrame:
    z = allbars.copy()
    cond = [
        z.regime.eq('REVERSAL') & z.episode_age.eq(1),
        z.regime.eq('REVERSAL') & z.episode_age.ge(2),
        z.regime.eq('RANGE') & z.episode_age.le(2),
        z.regime.eq('RANGE') & z.episode_age.ge(3),
        z.regime.eq('PULLBACK') & z.episode_age.le(3),
        z.regime.eq('PULLBACK') & z.episode_age.ge(4),
        z.regime.eq('EXPANSION') & z.episode_age.le(3),
        z.regime.eq('EXPANSION') & z.episode_age.ge(4),
    ]
    roles = [
        'REVERSAL_EVENT', 'REVERSAL_AFTERGLOW',
        'RANGE_SHORT', 'RANGE_STALE',
        'PULLBACK_FORMING', 'PULLBACK_MATURE',
        'EXPANSION_FORMING', 'EXPANSION_MATURE',
    ]
    z['display_role'] = np.select(cond, roles, default='UNMAPPED')
    if (z.display_role == 'UNMAPPED').any():
        bad = z.loc[z.display_role.eq('UNMAPPED'), ['regime', 'episode_age']].head().to_dict('records')
        raise RuntimeError(f'Unmapped display roles: {bad}')
    return z


def week_col(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).dt.to_period('W-SUN').astype(str)


def bootstrap_pair_roles(df: pd.DataFrame, metric: str, role_a: str, role_b: str, seed: int) -> dict:
    z = df[df.display_role.isin([role_a, role_b])][['available_time', 'display_role', metric]].copy()
    z[metric] = pd.to_numeric(z[metric], errors='coerce')
    z = z.dropna(subset=['available_time', metric])
    va = z.loc[z.display_role.eq(role_a), metric]
    vb = z.loc[z.display_role.eq(role_b), metric]
    observed = float(va.mean() - vb.mean()) if len(va) and len(vb) else np.nan
    eligible = bool(len(va) >= 20 and len(vb) >= 20)
    if z.empty:
        return dict(observed=observed, ci_lo=np.nan, ci_hi=np.nan, p_positive=np.nan,
                    n_a=int(len(va)), n_b=int(len(vb)), weeks=0, eligible=eligible)
    z['week'] = week_col(z.available_time)
    weeks = sorted(z.week.unique())
    stats = []
    for w in weeks:
        g = z[z.week.eq(w)]
        a = g.loc[g.display_role.eq(role_a), metric].to_numpy(float)
        b = g.loc[g.display_role.eq(role_b), metric].to_numpy(float)
        stats.append([len(a), np.nansum(a), len(b), np.nansum(b)])
    arr = np.asarray(stats, float)
    rng = np.random.default_rng(seed)
    draws = np.full(BOOT_N, np.nan)
    m = len(arr)
    for k in range(BOOT_N):
        s = arr[rng.integers(0, m, size=m)].sum(axis=0)
        if s[0] > 0 and s[2] > 0:
            draws[k] = s[1] / s[0] - s[3] / s[2]
    draws = draws[np.isfinite(draws)]
    return dict(
        observed=observed,
        ci_lo=float(np.quantile(draws, .025)) if len(draws) else np.nan,
        ci_hi=float(np.quantile(draws, .975)) if len(draws) else np.nan,
        p_positive=float(np.mean(draws > 0)) if len(draws) else np.nan,
        n_a=int(len(va)), n_b=int(len(vb)), weeks=int(m), eligible=eligible
    )


def bootstrap_one_role(df: pd.DataFrame, metric: str, role: str, null: float, seed: int) -> dict:
    z = df[df.display_role.eq(role)][['available_time', metric]].copy()
    z[metric] = pd.to_numeric(z[metric], errors='coerce')
    z = z.dropna(subset=['available_time', metric])
    v = z[metric]
    observed = float(v.mean() - null) if len(v) else np.nan
    eligible = bool(len(v) >= 50)
    if z.empty:
        return dict(observed=observed, ci_lo=np.nan, ci_hi=np.nan, p_positive=np.nan,
                    n_a=0, n_b=0, weeks=0, eligible=eligible)
    z['week'] = week_col(z.available_time)
    stats = z.groupby('week')[metric].agg(['count', 'sum']).to_numpy(float)
    rng = np.random.default_rng(seed)
    draws = np.full(BOOT_N, np.nan)
    m = len(stats)
    for k in range(BOOT_N):
        s = stats[rng.integers(0, m, size=m)].sum(axis=0)
        if s[0] > 0:
            draws[k] = s[1] / s[0] - null
    draws = draws[np.isfinite(draws)]
    return dict(
        observed=observed,
        ci_lo=float(np.quantile(draws, .025)) if len(draws) else np.nan,
        ci_hi=float(np.quantile(draws, .975)) if len(draws) else np.nan,
        p_positive=float(np.mean(draws > 0)) if len(draws) else np.nan,
        n_a=int(len(v)), n_b=0, weeks=int(m), eligible=eligible
    )


def primary_specs():
    return [
        dict(name='H1_REVERSAL_ONSET_EVENT', kind='PAIR', metric='momentum_flip_24h',
             a='REVERSAL_EVENT', b='REVERSAL_AFTERGLOW', horizon=24),
        dict(name='H2_RANGE_SHORT_CONTAINMENT', kind='PAIR', metric='contained_1atr_8h',
             a='RANGE_SHORT', b='RANGE_STALE', horizon=8),
        dict(name='H3_PULLBACK_MATURITY_CONTINUATION', kind='PAIR', metric='bias_follow_24h',
             a='PULLBACK_MATURE', b='PULLBACK_FORMING', horizon=24),
        dict(name='H4_EXPANSION_MATURITY_MOVEMENT', kind='PAIR', metric='range_atr_24h',
             a='EXPANSION_MATURE', b='EXPANSION_FORMING', horizon=24),
        dict(name='H5_PULLBACK_MATURE_ABSOLUTE_BIAS', kind='ONE', metric='bias_follow_24h',
             a='PULLBACK_MATURE', b='0.50', horizon=24, null=0.50),
        dict(name='H6_MATURE_EXPANSION_VS_SHORT_RANGE', kind='PAIR', metric='range_atr_24h',
             a='EXPANSION_MATURE', b='RANGE_SHORT', horizon=24),
    ]


def evaluate_primary(z: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, s in enumerate(primary_specs()):
        if s['kind'] == 'PAIR':
            r = bootstrap_pair_roles(z, s['metric'], s['a'], s['b'], SEED + i)
        else:
            r = bootstrap_one_role(z, s['metric'], s['a'], s['null'], SEED + i)
        pass_gate = bool(r['eligible'] and np.isfinite(r['observed']) and r['observed'] > 0 and
                         np.isfinite(r['ci_lo']) and r['ci_lo'] > 0)
        status = 'PASS' if pass_gate else ('FAIL' if r['eligible'] else 'UNDERPOWERED')
        rows.append({**s, **r, 'pass_gate': pass_gate, 'status': status})
    return pd.DataFrame(rows)


def secondary_specs_for_horizon(h: int):
    return [
        dict(name='REVERSAL_EVENT_VS_AFTERGLOW', kind='PAIR', metric=f'momentum_flip_{h}h', a='REVERSAL_EVENT', b='REVERSAL_AFTERGLOW'),
        dict(name='REVERSAL_EVENT_VS_EXPANSION_FORMING', kind='PAIR', metric=f'momentum_flip_{h}h', a='REVERSAL_EVENT', b='EXPANSION_FORMING'),
        dict(name='RANGE_SHORT_VS_STALE', kind='PAIR', metric=f'contained_1atr_{h}h', a='RANGE_SHORT', b='RANGE_STALE'),
        dict(name='RANGE_SHORT_VS_EXPANSION_FORMING', kind='PAIR', metric=f'contained_1atr_{h}h', a='RANGE_SHORT', b='EXPANSION_FORMING'),
        dict(name='PULLBACK_MATURE_VS_FORMING', kind='PAIR', metric=f'bias_follow_{h}h', a='PULLBACK_MATURE', b='PULLBACK_FORMING'),
        dict(name='PULLBACK_MATURE_VS_050', kind='ONE', metric=f'bias_follow_{h}h', a='PULLBACK_MATURE', b='0.50', null=0.50),
        dict(name='EXPANSION_MATURE_VS_FORMING', kind='PAIR', metric=f'range_atr_{h}h', a='EXPANSION_MATURE', b='EXPANSION_FORMING'),
        dict(name='EXPANSION_MATURE_VS_RANGE_SHORT', kind='PAIR', metric=f'range_atr_{h}h', a='EXPANSION_MATURE', b='RANGE_SHORT'),
    ]


def timeshape(z: pd.DataFrame) -> pd.DataFrame:
    rows = []
    k = 100
    for h in HORIZONS:
        for s in secondary_specs_for_horizon(h):
            if s['kind'] == 'PAIR':
                r = bootstrap_pair_roles(z, s['metric'], s['a'], s['b'], SEED + k)
            else:
                r = bootstrap_one_role(z, s['metric'], s['a'], s['null'], SEED + k)
            rows.append({'horizon_h': h, **s, **r})
            k += 1
    return pd.DataFrame(rows)


def year_effects(z: pd.DataFrame) -> pd.DataFrame:
    d = z.copy()
    d['year'] = pd.to_datetime(d.available_time).dt.year
    rows = []
    for s in primary_specs():
        for year in YEARS:
            g = d[d.year.eq(year)]
            if s['kind'] == 'PAIR':
                va = pd.to_numeric(g.loc[g.display_role.eq(s['a']), s['metric']], errors='coerce').dropna()
                vb = pd.to_numeric(g.loc[g.display_role.eq(s['b']), s['metric']], errors='coerce').dropna()
                effect = float(va.mean() - vb.mean()) if len(va) and len(vb) else np.nan
                eligible_year = bool(len(va) >= 5 and len(vb) >= 5 and np.isfinite(effect))
                n_b = len(vb)
            else:
                va = pd.to_numeric(g.loc[g.display_role.eq(s['a']), s['metric']], errors='coerce').dropna()
                effect = float(va.mean() - s['null']) if len(va) else np.nan
                eligible_year = bool(len(va) >= 10 and np.isfinite(effect))
                n_b = 0
            rows.append(dict(
                hypothesis=s['name'], year=year, metric=s['metric'], role_a=s['a'], role_b=s['b'],
                n_a=int(len(va)), n_b=int(n_b), effect=effect, eligible_year=eligible_year,
                positive=bool(eligible_year and effect > 0)
            ))
    return pd.DataFrame(rows)


def role_counts(z: pd.DataFrame) -> pd.DataFrame:
    x = z.groupby('display_role').agg(
        bars=('display_role', 'size'),
        episodes=('episode_id', 'nunique'),
        median_episode_age=('episode_age', 'median'),
        mean_episode_age=('episode_age', 'mean'),
    ).reset_index()
    x['share'] = x.bars / x.bars.sum()
    return x.sort_values('bars', ascending=False)


def role_raw_metrics(z: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for role in sorted(z.display_role.unique()):
        g = z[z.display_role.eq(role)]
        for h in HORIZONS:
            rec = {'display_role': role, 'horizon_h': h, 'n_rows': int(len(g))}
            for base in ['range_atr', 'abs_close_atr', 'contained_1atr', 'two_sided_1atr', 'momentum_flip', 'bias_follow', 'bias_signed_close_atr']:
                c = f'{base}_{h}h'
                v = pd.to_numeric(g[c], errors='coerce').dropna()
                rec[f'{base}_n'] = int(len(v))
                rec[f'{base}_mean'] = float(v.mean()) if len(v) else np.nan
                rec[f'{base}_median'] = float(v.median()) if len(v) else np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xau-m1', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    p = Path(args.xau_m1)
    actual = sha256(p)
    if actual != XAU_SHA:
        raise RuntimeError(f'Canonical XAU SHA mismatch: {actual}')

    lab8 = load_lab8()
    m1 = lab8.read_xau_native(p)
    h4 = lab8.to_h4(m1)
    router = lab8.load_router_module()
    ctx = router.add_router(h4)
    ctx = lab8.add_forward_metrics(ctx)
    ctx = ctx.dropna(subset=['available_time', 'atr14']).copy()
    allbars, onset = lab8.make_episodes(ctx)

    if len(allbars) != 6216 or len(onset) != 610:
        raise RuntimeError(f'LAB008 parity failed: allbars={len(allbars)} onset={len(onset)} expected 6216/610')

    z = add_roles(allbars)
    primary = evaluate_primary(z)
    shape = timeshape(z)
    yearly = year_effects(z)
    counts = role_counts(z)
    raw = role_raw_metrics(z)

    primary.to_csv(out / 'primary_role_hypotheses.csv', index=False)
    shape.to_csv(out / 'secondary_role_timeshape.csv', index=False)
    yearly.to_csv(out / 'year_transfer.csv', index=False)
    counts.to_csv(out / 'role_counts.csv', index=False)
    raw.to_csv(out / 'role_horizon_metrics.csv', index=False)

    transfer_rows = []
    transferable_names = {x['name'] for x in primary_specs()[1:]}
    for name in sorted(transferable_names):
        g = yearly[yearly.hypothesis.eq(name)]
        eligible = int(g.eligible_year.sum())
        positive = int(g.loc[g.eligible_year, 'positive'].sum())
        passed = bool(eligible == 4 and positive >= 3)
        transfer_rows.append({'hypothesis': name, 'eligible_years': eligible, 'positive_years': positive, 'transfer_pass': passed})
    transfer = pd.DataFrame(transfer_rows)
    transfer.to_csv(out / 'transfer_summary.csv', index=False)

    eligible_n = int(primary.eligible.sum())
    pass_n = int(primary.pass_gate.sum())
    pass_frac = float(pass_n / eligible_n) if eligible_n else np.nan
    transfer_pass_n = int(transfer.transfer_pass.sum())

    if eligible_n < 3:
        verdict = 'TEMPORAL_ROLE_REDESIGN_UNDERPOWERED'
    elif pass_n <= 1:
        verdict = 'TEMPORAL_ROLE_REDESIGN_NOT_SUPPORTED'
    elif eligible_n >= 4 and pass_frac >= .75 and transfer_pass_n >= 2:
        verdict = 'TEMPORAL_ROLE_REDESIGN_SUPPORTED_DISCOVERY_ONLY'
    else:
        verdict = 'PARTIAL_TEMPORAL_ROLE_SUPPORT'

    summary = {
        'lab': LAB,
        'status': 'REUSED_HISTORY_PREREGISTERED_TEMPORAL_ROLE_DIAGNOSTIC',
        'verdict': verdict,
        'xau_sha256': actual,
        'm1_rows': int(len(m1)),
        'h4_rows': int(len(h4)),
        'valid_context_bars': int(len(allbars)),
        'episode_onsets': int(len(onset)),
        'eligible_primary_hypotheses': eligible_n,
        'passed_primary_hypotheses': pass_n,
        'eligible_pass_fraction': pass_frac,
        'transfer_passes': transfer_pass_n,
        'promotion_authorized': False,
        'trading_edge_tested': False,
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, default=str))

    lines = [
        f'# {LAB}', '', f'**Verdict: {verdict}**', '',
        '> Human-readable Context display-layer diagnostic only. No trading edge or execution claim.', '',
        f'- Canonical XAU SHA: `{actual}`',
        f'- Valid Context H4 bars: **{len(allbars):,}**',
        f'- Frozen state episodes: **{len(onset):,}**',
        f'- Eligible primary hypotheses: **{eligible_n}/6**',
        f'- Primary bootstrap passes: **{pass_n}/{eligible_n if eligible_n else 0} eligible**',
        f'- 3/4-year transfer passes (H2-H6): **{transfer_pass_n}/5**', '',
        '## Frozen redesigned display roles', '',
        '| Role | Bars | Episodes | Share |', '|---|---:|---:|---:|'
    ]
    for r in counts.itertuples():
        lines.append(f'| {r.display_role} | {r.bars:,} | {r.episodes:,} | {r.share:.1%} |')

    lines += ['', '## Primary preregistered hypotheses', '',
              '| Hypothesis | Metric | Role A | Role B/null | Effect | 95% CI | N A | N B | Status |',
              '|---|---|---|---|---:|---:|---:|---:|---|']
    for r in primary.itertuples():
        lines.append(f'| {r.name} | {r.metric} | {r.a} | {r.b} | {r.observed:+.4f} | [{r.ci_lo:+.4f}, {r.ci_hi:+.4f}] | {r.n_a} | {r.n_b} | {r.status} |')

    lines += ['', '## Year transfer', '',
              '| Hypothesis | Positive / eligible years | Transfer |', '|---|---:|---|']
    for r in transfer.itertuples():
        lines.append(f"| {r.hypothesis} | {r.positive_years}/{r.eligible_years} | {'PASS' if r.transfer_pass else 'FAIL/UNDERPOWERED'} |")

    lines += ['', '## Interpretation rules', '',
              '- A pass validates the temporal **display role**, not a trading setup.',
              '- `REVERSAL_EVENT` is intentionally tested only at episode onset; later reversal bars are retained as `REVERSAL_AFTERGLOW`.',
              '- `RANGE_SHORT` is age 1–2 only; later range bars remain visible as `RANGE_STALE` for diagnostics.',
              '- `PULLBACK_MATURE` / `EXPANSION_MATURE` begin at age 4 H4 bars; no age-boundary search is allowed.',
              '- Secondary 4/8/12/24/48h shape tables cannot override the preregistered primary horizons.',
              '- Reused history: even a full pass remains discovery-only until fresh post-freeze replication.']
    (out / 'REPORT.md').write_text('\n'.join(lines))
    print((out / 'REPORT.md').read_text())


if __name__ == '__main__':
    main()
