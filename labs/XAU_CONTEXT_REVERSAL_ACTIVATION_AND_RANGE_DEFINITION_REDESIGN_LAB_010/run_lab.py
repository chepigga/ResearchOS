#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = 'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAB8_PATH = ROOT / 'labs' / 'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008' / 'run_lab.py'
LAB9_PATH = ROOT / 'labs' / 'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009' / 'run_lab.py'
XAU_SHA = 'db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
YEARS = [2023, 2024, 2025, 2026]
BOOT_N = 5000
SEED = 2026091110


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def week_col(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).dt.to_period('W-SUN').astype(str)


def add_components_and_candidates(z: pd.DataFrame) -> pd.DataFrame:
    d = z.copy().sort_index()

    prev_rsi = d['rsi14'].shift(1)
    prev_ok = pd.Series(d.index, index=d.index).shift(1).eq(pd.Series(d.index, index=d.index) - pd.Timedelta(hours=4))
    d['SWEEP'] = d['sweep'].fillna(False).astype(bool)
    d['RSI_TURN'] = ((((prev_rsi < 35) & (d['rsi14'] > prev_rsi)) |
                      ((prev_rsi > 65) & (d['rsi14'] < prev_rsi))) & prev_ok).fillna(False)
    d['EMA20_CROSS'] = d['cross_ema20'].fillna(False).astype(bool)
    d['ADX_FALLING'] = ((d['adx14'] < d['adx14'].shift(1)) & prev_ok).fillna(False)
    d['REJECTION'] = d['rejection_wick'].ge(0.45).fillna(False)

    comp_cols = ['SWEEP', 'RSI_TURN', 'EMA20_CROSS', 'ADX_FALLING', 'REJECTION']
    d['REV_COMPONENT_COUNT'] = d[comp_cols].astype(int).sum(axis=1)

    score_cols = ['score_expansion', 'score_pullback', 'score_reversal', 'score_range']
    score = d[score_cols].apply(pd.to_numeric, errors='coerce')
    d['RAW_REV_WINNER'] = score['score_reversal'].ge(score.max(axis=1)).fillna(False)
    # rank 1 = highest, method=min preserves ties as top rank.
    d['RAW_REV_RANK'] = score.rank(axis=1, ascending=False, method='min')['score_reversal']

    d['R0_FROZEN_REVERSAL_ONSET_BOOL'] = d['regime'].eq('REVERSAL') & d['episode_age'].eq(1)
    d['R1_LOCATION_TRANSITION_BOOL'] = ((d['SWEEP'] | d['REJECTION']) &
                                         (d['RSI_TURN'] | d['EMA20_CROSS'] | d['ADX_FALLING']))
    d['R2_TWO_OF_FIVE_BOOL'] = d['REV_COMPONENT_COUNT'].ge(2)
    d['R3_RAW_REVERSAL_WINNER_BOOL'] = d['RAW_REV_WINNER']

    d['LOW_ADX'] = d['adx14'].lt(20).fillna(False)
    d['COMPRESSED_24'] = d['range24_ratio'].lt(0.85).fillna(False)
    d['EMA_COIL'] = d['ema_spread_atr'].lt(1.0).fillna(False)
    d['LOW_ATR'] = d['atr_ratio'].lt(0.95).fillna(False)
    d['NO_STACK'] = (~d['stack'].fillna(False)).astype(bool)
    rcols = ['LOW_ADX', 'COMPRESSED_24', 'EMA_COIL', 'LOW_ATR', 'NO_STACK']
    d['RANGE_COMPONENT_COUNT'] = d[rcols].astype(int).sum(axis=1)

    d['G0_FROZEN_RANGE'] = d['regime'].eq('RANGE')
    d['G1_VOL_COMPRESSION'] = d['COMPRESSED_24'] & d['LOW_ATR']
    d['G2_STRUCTURAL_COIL'] = d['COMPRESSED_24'] & d['EMA_COIL'] & d['LOW_ADX']
    d['G3_MAJORITY_3OF5'] = d['RANGE_COMPONENT_COUNT'].ge(3)
    d['G4_STRICT_COIL'] = d['LOW_ADX'] & d['COMPRESSED_24'] & d['EMA_COIL'] & d['LOW_ATR']

    # Convert reversal booleans to first-bar activation events in contiguous True blocks.
    idx = pd.Series(d.index, index=d.index)
    contiguous_prev = idx.shift(1).eq(idx - pd.Timedelta(hours=4))
    for base in ['R0_FROZEN_REVERSAL_ONSET', 'R1_LOCATION_TRANSITION', 'R2_TWO_OF_FIVE', 'R3_RAW_REVERSAL_WINNER']:
        b = d[f'{base}_BOOL'].fillna(False).astype(bool)
        prev_true = b.shift(1).fillna(False) & contiguous_prev
        d[base] = b & (~prev_true)

    return d


def cluster_bootstrap_masks(df: pd.DataFrame, metric: str, mask_a: pd.Series, mask_b: pd.Series,
                            seed: int, difference: str = 'A_MINUS_B') -> dict:
    x = df[['available_time', metric]].copy()
    x[metric] = pd.to_numeric(x[metric], errors='coerce')
    x['A'] = mask_a.reindex(x.index).fillna(False).astype(bool)
    x['B'] = mask_b.reindex(x.index).fillna(False).astype(bool)
    x = x.dropna(subset=['available_time', metric])
    va = x.loc[x.A, metric].to_numpy(float)
    vb = x.loc[x.B, metric].to_numpy(float)
    if difference == 'A_MINUS_B':
        obs = float(np.mean(va) - np.mean(vb)) if len(va) and len(vb) else np.nan
    else:
        obs = float(np.mean(vb) - np.mean(va)) if len(va) and len(vb) else np.nan
    if x.empty:
        return dict(observed=obs, ci_lo=np.nan, ci_hi=np.nan, p_positive=np.nan,
                    n_a=int(len(va)), n_b=int(len(vb)), weeks=0)

    x['week'] = week_col(x['available_time'])
    weeks = sorted(x['week'].unique())
    stats = []
    for w in weeks:
        g = x[x.week.eq(w)]
        a = g.loc[g.A, metric].to_numpy(float)
        b = g.loc[g.B, metric].to_numpy(float)
        stats.append([len(a), np.nansum(a), len(b), np.nansum(b)])
    arr = np.asarray(stats, float)
    rng = np.random.default_rng(seed)
    draws = np.full(BOOT_N, np.nan)
    m = len(arr)
    for k in range(BOOT_N):
        s = arr[rng.integers(0, m, size=m)].sum(axis=0)
        if s[0] > 0 and s[2] > 0:
            delta = s[1] / s[0] - s[3] / s[2]
            draws[k] = delta if difference == 'A_MINUS_B' else -delta
    draws = draws[np.isfinite(draws)]
    return dict(
        observed=obs,
        ci_lo=float(np.quantile(draws, .025)) if len(draws) else np.nan,
        ci_hi=float(np.quantile(draws, .975)) if len(draws) else np.nan,
        p_positive=float(np.mean(draws > 0)) if len(draws) else np.nan,
        n_a=int(len(va)), n_b=int(len(vb)), weeks=int(m)
    )


def reversal_component_audit(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    x = d.copy()
    x['year'] = pd.to_datetime(x['available_time']).dt.year
    comps = ['SWEEP', 'RSI_TURN', 'EMA20_CROSS', 'ADX_FALLING', 'REJECTION']
    cand = ['R0_FROZEN_REVERSAL_ONSET', 'R1_LOCATION_TRANSITION', 'R2_TWO_OF_FIVE', 'R3_RAW_REVERSAL_WINNER']

    annual = []
    for y in YEARS:
        g = x[x.year.eq(y)]
        rev = pd.to_numeric(g['score_reversal'], errors='coerce').dropna()
        rec = {
            'year': y, 'bars': int(len(g)),
            'raw_rev_score_mean': float(rev.mean()) if len(rev) else np.nan,
            'raw_rev_score_median': float(rev.median()) if len(rev) else np.nan,
            'raw_rev_score_p75': float(rev.quantile(.75)) if len(rev) else np.nan,
            'raw_rev_score_p90': float(rev.quantile(.90)) if len(rev) else np.nan,
            'raw_rev_rank1_rate': float(g['RAW_REV_RANK'].eq(1).mean()),
            'raw_rev_top2_rate': float(g['RAW_REV_RANK'].le(2).mean()),
        }
        for c in comps:
            rec[f'{c.lower()}_rate'] = float(g[c].mean()) if len(g) else np.nan
        for c in cand:
            rec[f'{c.lower()}_events'] = int(g[c].sum())
        annual.append(rec)

    co = []
    for y in YEARS:
        g = x[x.year.eq(y)]
        for i, a in enumerate(comps):
            for b in comps[i + 1:]:
                co.append({'year': y, 'component_a': a, 'component_b': b,
                           'cooccur_rate': float((g[a] & g[b]).mean()) if len(g) else np.nan,
                           'cooccur_bars': int((g[a] & g[b]).sum())})

    periods = []
    for label, years in [('EARLY_2023_2024', [2023, 2024]), ('LATE_2025_2026', [2025, 2026])]:
        g = x[x.year.isin(years)]
        rec = {'period': label, 'bars': int(len(g))}
        for c in comps:
            rec[f'{c.lower()}_rate'] = float(g[c].mean()) if len(g) else np.nan
        rec['raw_rev_rank1_rate'] = float(g['RAW_REV_RANK'].eq(1).mean())
        rec['raw_rev_top2_rate'] = float(g['RAW_REV_RANK'].le(2).mean())
        rec['raw_rev_score_mean'] = float(pd.to_numeric(g['score_reversal'], errors='coerce').mean())
        for c in cand:
            rec[f'{c.lower()}_events'] = int(g[c].sum())
        periods.append(rec)
    return pd.DataFrame(annual), pd.DataFrame(co), pd.DataFrame(periods)


def reversal_semantics(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    years = []
    candidates = ['R1_LOCATION_TRANSITION', 'R2_TWO_OF_FIVE', 'R3_RAW_REVERSAL_WINNER']
    horizons = [8, 12, 24]
    for ci, c in enumerate(candidates):
        for hi, h in enumerate(horizons):
            metric = f'momentum_flip_{h}h'
            valid = pd.to_numeric(d[metric], errors='coerce').notna()
            ma = d[c] & valid
            mb = (~d[c]) & valid
            r = cluster_bootstrap_masks(d, metric, ma, mb, SEED + 100 + ci * 10 + hi)
            r.update(candidate=c, horizon_h=h, metric=metric)
            rows.append(r)
        for y in YEARS:
            g = d[pd.to_datetime(d.available_time).dt.year.eq(y)]
            metric = 'momentum_flip_24h'
            va = pd.to_numeric(g.loc[g[c], metric], errors='coerce').dropna()
            vb = pd.to_numeric(g.loc[~g[c], metric], errors='coerce').dropna()
            effect = float(va.mean() - vb.mean()) if len(va) and len(vb) else np.nan
            years.append({'candidate': c, 'year': y, 'metric': metric,
                          'n_candidate': int(len(va)), 'n_other': int(len(vb)),
                          'effect': effect, 'year_eligible': bool(len(va) >= 5 and np.isfinite(effect)),
                          'positive': bool(len(va) >= 5 and np.isfinite(effect) and effect > 0)})
    sem = pd.DataFrame(rows)
    yr = pd.DataFrame(years)

    summary = []
    for order, c in enumerate(candidates, start=1):
        p = sem[(sem.candidate.eq(c)) & (sem.horizon_h.eq(24))].iloc[0]
        yc = yr[yr.candidate.eq(c)]
        all_years_eligible = bool(len(yc) == 4 and yc.year_eligible.all())
        positive_years = int(yc.loc[yc.year_eligible, 'positive'].sum())
        n2025 = int(yc.loc[yc.year.eq(2025), 'n_candidate'].iloc[0])
        n2026 = int(yc.loc[yc.year.eq(2026), 'n_candidate'].iloc[0])
        eligible = bool(p.n_a >= 20 and n2025 >= 5 and n2026 >= 5)
        boot_pass = bool(eligible and p.observed > 0 and np.isfinite(p.ci_lo) and p.ci_lo > 0)
        transfer = bool(all_years_eligible and positive_years >= 3)
        summary.append({'candidate': c, 'order': order, 'eligible': eligible,
                        'n_24h': int(p.n_a), 'n_2025': n2025, 'n_2026': n2026,
                        'effect_24h': float(p.observed), 'ci_lo_24h': float(p.ci_lo), 'ci_hi_24h': float(p.ci_hi),
                        'bootstrap_pass': boot_pass, 'positive_years': positive_years,
                        'all_years_eligible': all_years_eligible, 'transfer_pass': transfer})
    return sem, yr, pd.DataFrame(summary)


def range_semantics(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidates = ['G1_VOL_COMPRESSION', 'G2_STRUCTURAL_COIL', 'G3_MAJORITY_3OF5', 'G4_STRICT_COIL']
    shape_rows = []
    year_rows = []
    summary = []
    years_s = pd.to_datetime(d.available_time).dt.year
    expansion_mature = d['display_role'].eq('EXPANSION_MATURE')

    for ci, c in enumerate(candidates):
        prevalence = float(d[c].mean())
        for hi, h in enumerate([4, 8, 12]):
            metric = f'contained_1atr_{h}h'
            valid = pd.to_numeric(d[metric], errors='coerce').notna()
            ma = d[c] & valid
            mb = (~d[c]) & valid
            r = cluster_bootstrap_masks(d, metric, ma, mb, SEED + 300 + ci * 10 + hi)
            r.update(candidate=c, horizon_h=h, metric=metric, prevalence=prevalence)
            shape_rows.append(r)

        # 24h movement negative control: Expansion Mature minus candidate.
        metric = 'range_atr_24h'
        valid = pd.to_numeric(d[metric], errors='coerce').notna()
        ma = expansion_mature & valid
        mb = d[c] & valid
        move = cluster_bootstrap_masks(d, metric, ma, mb, SEED + 350 + ci, difference='A_MINUS_B')

        for y in YEARS:
            g = d[years_s.eq(y)]
            v1 = pd.to_numeric(g.loc[g[c], 'contained_1atr_8h'], errors='coerce').dropna()
            v0 = pd.to_numeric(g.loc[~g[c], 'contained_1atr_8h'], errors='coerce').dropna()
            effect = float(v1.mean() - v0.mean()) if len(v1) and len(v0) else np.nan
            year_rows.append({'candidate': c, 'year': y, 'metric': 'contained_1atr_8h',
                              'n_candidate': int(len(v1)), 'n_other': int(len(v0)),
                              'effect': effect, 'positive': bool(np.isfinite(effect) and effect > 0)})

        p8 = next(r for r in shape_rows if r['candidate'] == c and r['horizon_h'] == 8)
        yc = [x for x in year_rows if x['candidate'] == c]
        positive_years = sum(1 for x in yc if x['positive'])
        eligible = bool(p8['n_a'] >= 100 and 0.02 <= prevalence <= 0.35)
        boot_pass = bool(eligible and p8['observed'] > 0 and np.isfinite(p8['ci_lo']) and p8['ci_lo'] > 0)
        movement_pass = bool(move['observed'] > 0 and np.isfinite(move['ci_lo']) and move['ci_lo'] > 0)
        transfer = bool(positive_years >= 3)
        summary.append({'candidate': c, 'order': ci + 1, 'eligible': eligible,
                        'prevalence': prevalence, 'n_8h': int(p8['n_a']),
                        'containment_effect_8h': float(p8['observed']),
                        'containment_ci_lo_8h': float(p8['ci_lo']), 'containment_ci_hi_8h': float(p8['ci_hi']),
                        'bootstrap_pass': boot_pass,
                        'movement_effect_expansion_minus_candidate_24h': float(move['observed']),
                        'movement_ci_lo_24h': float(move['ci_lo']), 'movement_ci_hi_24h': float(move['ci_hi']),
                        'movement_pass': movement_pass,
                        'positive_years': int(positive_years), 'transfer_pass': transfer,
                        'movement_n_expansion': int(move['n_a']), 'movement_n_candidate': int(move['n_b'])})

    return pd.DataFrame(shape_rows), pd.DataFrame(year_rows), pd.DataFrame(summary)


def choose_reversal(summary: pd.DataFrame):
    q = summary[summary.bootstrap_pass].copy()
    if q.empty:
        return None
    q = q.sort_values(['transfer_pass', 'effect_24h', 'order'], ascending=[False, False, True])
    return q.iloc[0].to_dict()


def choose_range(summary: pd.DataFrame):
    q = summary[summary.bootstrap_pass].copy()
    if q.empty:
        return None
    q = q.sort_values(['movement_pass', 'transfer_pass', 'containment_effect_8h', 'order'],
                      ascending=[False, False, False, True])
    return q.iloc[0].to_dict()


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

    lab8 = load_module(LAB8_PATH, 'xau_context_lab8_for_lab10')
    lab9 = load_module(LAB9_PATH, 'xau_context_lab9_for_lab10')
    m1 = lab8.read_xau_native(p)
    h4 = lab8.to_h4(m1)
    router = lab8.load_router_module()
    ctx = router.add_router(h4)
    ctx = lab8.add_forward_metrics(ctx)
    ctx = ctx.dropna(subset=['available_time', 'atr14']).copy()
    allbars, onset, episodes = lab8.make_episodes(ctx)
    if len(allbars) != 6216 or len(onset) != 610:
        raise RuntimeError(f'LAB009 parity failed: bars={len(allbars)}, episodes={len(onset)} expected 6216/610')

    allbars = lab9.add_roles(allbars)
    d = add_components_and_candidates(allbars)

    annual, cooccur, periods = reversal_component_audit(d)
    rev_shape, rev_year, rev_summary = reversal_semantics(d)
    rng_shape, rng_year, rng_summary = range_semantics(d)
    rev_winner = choose_reversal(rev_summary)
    rng_winner = choose_range(rng_summary)

    rev_qual = bool(rev_winner is not None and rev_winner['transfer_pass'])
    rng_qual = bool(rng_winner is not None and rng_winner['transfer_pass'] and rng_winner['movement_pass'])
    if rev_qual and rng_qual:
        verdict = 'REVERSAL_AND_RANGE_REDESIGN_SUPPORTED_DISCOVERY_ONLY'
    elif rev_winner is not None or rng_winner is not None:
        verdict = 'PARTIAL_REVERSAL_RANGE_REDESIGN_SUPPORT'
    else:
        any_rev_eligible = bool(rev_summary.eligible.any())
        any_rng_eligible = bool(rng_summary.eligible.any())
        verdict = 'REVERSAL_RANGE_REDESIGN_NOT_SUPPORTED' if (any_rev_eligible or any_rng_eligible) else 'REVERSAL_RANGE_REDESIGN_UNDERPOWERED'

    annual.to_csv(out / 'reversal_component_annual.csv', index=False)
    cooccur.to_csv(out / 'reversal_component_cooccurrence.csv', index=False)
    periods.to_csv(out / 'reversal_early_vs_late_diagnostic.csv', index=False)
    rev_shape.to_csv(out / 'reversal_candidate_timeshape.csv', index=False)
    rev_year.to_csv(out / 'reversal_candidate_year_transfer.csv', index=False)
    rev_summary.to_csv(out / 'reversal_candidate_summary.csv', index=False)
    rng_shape.to_csv(out / 'range_candidate_timeshape.csv', index=False)
    rng_year.to_csv(out / 'range_candidate_year_transfer.csv', index=False)
    rng_summary.to_csv(out / 'range_candidate_summary.csv', index=False)

    summary = {
        'lab': LAB,
        'status': 'REUSED_HISTORY_PREREGISTERED_INDICATOR_REDESIGN_DISCOVERY',
        'verdict': verdict,
        'xau_sha256': actual,
        'm1_rows': int(len(m1)),
        'h4_rows': int(len(h4)),
        'valid_context_bars': int(len(allbars)),
        'episode_onsets': int(len(onset)),
        'reversal_winner': None if rev_winner is None else rev_winner['candidate'],
        'reversal_winner_transfer': bool(rev_winner['transfer_pass']) if rev_winner is not None else False,
        'range_winner': None if rng_winner is None else rng_winner['candidate'],
        'range_winner_transfer': bool(rng_winner['transfer_pass']) if rng_winner is not None else False,
        'range_winner_movement_control': bool(rng_winner['movement_pass']) if rng_winner is not None else False,
        'promotion_authorized': False,
        'trading_edge_tested': False,
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, default=str))

    lines = [
        f'# {LAB}', '', f'**Verdict: {verdict}**', '',
        '> Indicator-state / human-decision-support redesign only. No trading edge or execution claim.', '',
        f'- Canonical XAU SHA: `{actual}`',
        f'- Valid Context H4 bars: **{len(allbars):,}**',
        f'- Frozen episodes: **{len(onset):,}**',
        f"- Reversal winner: **{summary['reversal_winner'] or 'NONE'}**",
        f"- Range winner: **{summary['range_winner'] or 'NONE'}**", '',
        '## Reversal candidate summary', '',
        '| Candidate | Eligible | N24 | N2025 | N2026 | 24h flip premium | 95% CI | Bootstrap | Years + | Transfer |',
        '|---|---|---:|---:|---:|---:|---:|---|---:|---|'
    ]
    for r in rev_summary.itertuples():
        lines.append(f'| {r.candidate} | {"YES" if r.eligible else "NO"} | {r.n_24h} | {r.n_2025} | {r.n_2026} | {r.effect_24h:+.4f} | [{r.ci_lo_24h:+.4f}, {r.ci_hi_24h:+.4f}] | {"PASS" if r.bootstrap_pass else "FAIL"} | {r.positive_years}/4 | {"PASS" if r.transfer_pass else "FAIL"} |')

    lines += ['', '## Range candidate summary', '',
              '| Candidate | Eligible | Prevalence | N8 | 8h containment premium | 95% CI | Bootstrap | Expansion-candidate 24h range | Movement CI | Years + |',
              '|---|---|---:|---:|---:|---:|---|---:|---:|---:|']
    for r in rng_summary.itertuples():
        lines.append(f'| {r.candidate} | {"YES" if r.eligible else "NO"} | {r.prevalence:.1%} | {r.n_8h} | {r.containment_effect_8h:+.4f} | [{r.containment_ci_lo_8h:+.4f}, {r.containment_ci_hi_8h:+.4f}] | {"PASS" if r.bootstrap_pass else "FAIL"} | {r.movement_effect_expansion_minus_candidate_24h:+.4f} | [{r.movement_ci_lo_24h:+.4f}, {r.movement_ci_hi_24h:+.4f}] | {r.positive_years}/4 |')

    lines += ['', '## Reversal scarcity diagnostic — annual', '',
              '| Year | Sweep | RSI turn | EMA20 cross | ADX falling | Rejection | Raw rev #1 | Raw rev top2 | Frozen events | R1 | R2 | R3 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in annual.itertuples():
        lines.append(f'| {r.year} | {r.sweep_rate:.1%} | {r.rsi_turn_rate:.1%} | {r.ema20_cross_rate:.1%} | {r.adx_falling_rate:.1%} | {r.rejection_rate:.1%} | {r.raw_rev_rank1_rate:.1%} | {r.raw_rev_top2_rate:.1%} | {r.r0_frozen_reversal_onset_events} | {r.r1_location_transition_events} | {r.r2_two_of_five_events} | {r.r3_raw_reversal_winner_events} |')

    lines += ['', '## Interpretation constraints', '',
              '- R1–R3 and G1–G4 were frozen in PREREG before outcomes; no thresholds were optimized after seeing results.',
              '- Reversal candidates are activation-event onsets, not repeated bars.',
              '- Range candidates are persistent bar-level conditions because a human display must remain on while compression persists.',
              '- A candidate that increases frequency without semantic separation is rejected.',
              '- Reused history: any winner is discovery-only and requires fresh post-freeze replication before changing the production indicator.']
    (out / 'REPORT.md').write_text('\n'.join(lines))
    print((out / 'REPORT.md').read_text())


if __name__ == '__main__':
    main()
