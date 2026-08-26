import json
from pathlib import Path
import numpy as np
import pandas as pd

import btc_low_activity_flow_alignment_flip_lab008 as lab8
import btc_low_activity_flow_2021_failure_regime_causal_map_lab010 as lab10
import btc_low_activity_flow_2021_matched_microstructure_failure_map_lab011 as lab11

LAB = 'BTC_UNSUPPORTED_BREAKOUT_FLOW_SPONSORSHIP_COMMON_SUPPORT_LAB_012'
FULL_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
REPLICATION_YEARS = [2020, 2022, 2023, 2024, 2025]
DISCOVERY_YEAR = 2021
FORWARD_YEAR = 2026

# Frozen concept from LAB011. Threshold values are estimated ONLY from each training fold.
RESP_Q = 2.0 / 3.0
FLOW_Q = 1.0 / 3.0
PERSIST_Q = 1.0 / 3.0
SHIFT_Q = 1.0 / 3.0

# Common-support gate on slow / structural state variables.
SUPPORT_FEATURES = list(lab11.MATCH)
SUPPORT_Q_LO = 0.01
SUPPORT_Q_HI = 0.99
SUPPORT_K = 5
SUPPORT_MAX_RMS_DISTANCE = 1.25

# Same-year matched diagnostic: compare vetoed events with nearest kept events
# after the slow/common-support gate. This is NOT used to define the rule.
MATCH_K = 3
MATCH_MAX_RMS_DISTANCE = 1.50


def _safe_num(s):
    return pd.to_numeric(s, errors='coerce').astype(float)


def build_base():
    m, sig, e = lab8.build_all_events()
    discovery = e[(e.signal_time >= lab8.DISCOVERY_START) & (e.signal_time <= lab8.DISCOVERY_END)].copy()
    thr = lab8.freeze_thresholds(discovery)
    x = lab8.apply_frozen_state(e, thr)
    x = lab10.add_slow_regime_features(m, x)
    base = x[(x.low_activity_score >= 2) & (x.flow_align_12 == 1)].copy().reset_index(drop=True)
    base = lab11.add_micro(m, base)
    return m, e, base


def freeze_rule(train):
    abs_flow = _safe_num(train['flow_delta_micro_6']).abs().dropna()
    response = _safe_num(train['price_response_per_flow_6']).dropna()
    persistence = _safe_num(train['flow_persistence_12']).dropna()
    shift = _safe_num(train['persistence_shift_3v12']).dropna()
    return {
        'response_hi': float(response.quantile(RESP_Q)),
        'abs_flow_lo': float(abs_flow.quantile(FLOW_Q)),
        'persistence_lo': float(persistence.quantile(PERSIST_Q)),
        'persistence_shift_lo': float(shift.quantile(SHIFT_Q)),
    }


def apply_rule(df, rule):
    z = df.copy()
    response = _safe_num(z['price_response_per_flow_6'])
    abs_flow = _safe_num(z['flow_delta_micro_6']).abs()
    persistence = _safe_num(z['flow_persistence_12'])
    shift = _safe_num(z['persistence_shift_3v12'])

    z['unsupported_high_response'] = (response >= rule['response_hi']).astype(int)
    z['unsupported_low_abs_flow'] = (abs_flow <= rule['abs_flow_lo']).astype(int)
    z['unsupported_low_persistence'] = (persistence <= rule['persistence_lo']).astype(int)
    z['unsupported_falling_persistence'] = (shift <= rule['persistence_shift_lo']).astype(int)
    z['unsupported_score'] = (
        z['unsupported_high_response']
        + z['unsupported_low_abs_flow']
        + z['unsupported_low_persistence']
        + z['unsupported_falling_persistence']
    )
    # Prespecified main veto: thin/unsupported price response AND weak absolute flow
    # AND weak or falling persistence.
    z['unsupported_veto'] = (
        (z['unsupported_high_response'] == 1)
        & (z['unsupported_low_abs_flow'] == 1)
        & ((z['unsupported_low_persistence'] == 1) | (z['unsupported_falling_persistence'] == 1))
    ).astype(int)
    # Diagnostic only; never used for the main verdict.
    z['unsupported_score2plus'] = (z['unsupported_score'] >= 2).astype(int)
    z['unsupported_score3plus'] = (z['unsupported_score'] >= 3).astype(int)
    return z


def _scale_frame(train, features):
    med = {}
    sd = {}
    lo = {}
    hi = {}
    for f in features:
        s = _safe_num(train[f])
        med[f] = float(s.median())
        v = float(s.std(ddof=0))
        sd[f] = v if np.isfinite(v) and v > 1e-12 else 1.0
        lo[f] = float(s.quantile(SUPPORT_Q_LO))
        hi[f] = float(s.quantile(SUPPORT_Q_HI))
    return med, sd, lo, hi


def _vec(row, features, med, sd):
    vals = []
    for f in features:
        v = float(row[f]) if pd.notna(row[f]) else med[f]
        vals.append((v - med[f]) / sd[f])
    return np.asarray(vals, float)


def common_support(train, test):
    med, sd, lo, hi = _scale_frame(train, SUPPORT_FEATURES)
    tr = train.reset_index(drop=True)
    tv = np.vstack([_vec(r, SUPPORT_FEATURES, med, sd) for _, r in tr.iterrows()])
    out = []
    for _, r in test.reset_index(drop=True).iterrows():
        exact = (
            (tr.direction.to_numpy(int) == int(r.direction))
            & (tr.low_activity_score.to_numpy(int) == int(r.low_activity_score))
        )
        pos = np.where(exact)[0]
        if len(pos) < SUPPORT_K:
            out.append((0, np.nan, len(pos), 'INSUFFICIENT_STRATUM'))
            continue

        in_box = True
        for f in SUPPORT_FEATURES:
            v = float(r[f]) if pd.notna(r[f]) else np.nan
            if (not np.isfinite(v)) or v < lo[f] or v > hi[f]:
                in_box = False
                break
        if not in_box:
            out.append((0, np.nan, len(pos), 'OUTSIDE_1_99_BOX'))
            continue

        rv = _vec(r, SUPPORT_FEATURES, med, sd)
        dist = np.sqrt(np.mean((tv[pos] - rv) ** 2, axis=1))
        kth = float(np.partition(dist, SUPPORT_K - 1)[SUPPORT_K - 1])
        ok = int(kth <= SUPPORT_MAX_RMS_DISTANCE)
        out.append((ok, kth, len(pos), 'SUPPORTED' if ok else 'DISTANCE_FAIL'))

    z = test.reset_index(drop=True).copy()
    z['common_support'] = [x[0] for x in out]
    z['support_kth_distance'] = [x[1] for x in out]
    z['support_stratum_n_train'] = [x[2] for x in out]
    z['support_reason'] = [x[3] for x in out]
    return z


def summarize_group(df, label):
    n = len(df)
    if n == 0:
        return {
            'group': label, 'n': 0, 'large_n': 0, 'large_rate': np.nan,
            'fail_n': 0, 'fail_rate': np.nan,
        }
    return {
        'group': label,
        'n': int(n),
        'large_n': int(df.is_large.sum()),
        'large_rate': float(df.is_large.mean()),
        'fail_n': int(df.is_fail.sum()),
        'fail_rate': float(df.is_fail.mean()),
    }


def fold_metrics(test_rule, year, fold_type):
    supported = test_rule[test_rule.common_support == 1].copy()
    veto = supported[supported.unsupported_veto == 1]
    keep = supported[supported.unsupported_veto == 0]
    score2 = supported[supported.unsupported_score2plus == 1]
    score3 = supported[supported.unsupported_score3plus == 1]

    b = summarize_group(supported, 'supported_baseline')
    v = summarize_group(veto, 'main_veto')
    k = summarize_group(keep, 'kept')
    s2 = summarize_group(score2, 'score2plus')
    s3 = summarize_group(score3, 'score3plus')

    supported_large = int(supported.is_large.sum())
    retained_large = int(keep.is_large.sum())
    return {
        'year': int(year),
        'fold_type': fold_type,
        'test_n': int(len(test_rule)),
        'supported_n': int(len(supported)),
        'support_coverage': float(len(supported) / len(test_rule)) if len(test_rule) else np.nan,
        'baseline_large_rate': b['large_rate'],
        'baseline_fail_rate': b['fail_rate'],
        'veto_n': v['n'],
        'veto_share': float(v['n'] / len(supported)) if len(supported) else np.nan,
        'veto_large_rate': v['large_rate'],
        'veto_fail_rate': v['fail_rate'],
        'keep_n': k['n'],
        'keep_large_rate': k['large_rate'],
        'keep_fail_rate': k['fail_rate'],
        'veto_minus_keep_large_pp': 100.0 * (v['large_rate'] - k['large_rate']) if np.isfinite(v['large_rate']) and np.isfinite(k['large_rate']) else np.nan,
        'veto_minus_keep_fail_pp': 100.0 * (v['fail_rate'] - k['fail_rate']) if np.isfinite(v['fail_rate']) and np.isfinite(k['fail_rate']) else np.nan,
        'keep_minus_baseline_large_pp': 100.0 * (k['large_rate'] - b['large_rate']) if np.isfinite(k['large_rate']) and np.isfinite(b['large_rate']) else np.nan,
        'keep_minus_baseline_fail_pp': 100.0 * (k['fail_rate'] - b['fail_rate']) if np.isfinite(k['fail_rate']) and np.isfinite(b['fail_rate']) else np.nan,
        'large_retention': float(retained_large / supported_large) if supported_large else np.nan,
        'frequency_retention': float(len(keep) / len(supported)) if len(supported) else np.nan,
        'score2plus_n': s2['n'],
        'score2plus_large_rate': s2['large_rate'],
        'score2plus_fail_rate': s2['fail_rate'],
        'score3plus_n': s3['n'],
        'score3plus_large_rate': s3['large_rate'],
        'score3plus_fail_rate': s3['fail_rate'],
    }


def within_year_veto_match(test_rule):
    s = test_rule[test_rule.common_support == 1].copy().reset_index(drop=True)
    veto = s[s.unsupported_veto == 1].copy()
    keep = s[s.unsupported_veto == 0].copy()
    if len(veto) == 0 or len(keep) < MATCH_K:
        return pd.DataFrame(), {
            'veto_units': int(len(veto)), 'pairs': 0, 'matched_controls': 0,
            'matched_control_large_rate': np.nan, 'matched_control_fail_rate': np.nan,
            'veto_large_rate': float(veto.is_large.mean()) if len(veto) else np.nan,
            'veto_fail_rate': float(veto.is_fail.mean()) if len(veto) else np.nan,
        }

    med, sd, _, _ = _scale_frame(keep, SUPPORT_FEATURES)
    kv = np.vstack([_vec(r, SUPPORT_FEATURES, med, sd) for _, r in keep.iterrows()])
    rows = []
    for vi, r in veto.iterrows():
        exact = (
            (keep.direction.to_numpy(int) == int(r.direction))
            & (keep.low_activity_score.to_numpy(int) == int(r.low_activity_score))
        )
        pos = np.where(exact)[0]
        if len(pos) < MATCH_K:
            continue
        rv = _vec(r, SUPPORT_FEATURES, med, sd)
        d = np.sqrt(np.mean((kv[pos] - rv) ** 2, axis=1))
        take = np.argsort(d)[:MATCH_K]
        if float(d[take[-1]]) > MATCH_MAX_RMS_DISTANCE:
            continue
        for rank, q in enumerate(take, 1):
            ki = int(keep.index[pos[q]])
            rows.append({
                'veto_index': int(vi), 'keep_index': ki, 'rank': rank,
                'distance': float(d[q]),
                'veto_large': int(r.is_large), 'veto_fail': int(r.is_fail),
                'control_large': int(keep.loc[ki, 'is_large']),
                'control_fail': int(keep.loc[ki, 'is_fail']),
            })
    mt = pd.DataFrame(rows)
    if len(mt) == 0:
        return mt, {
            'veto_units': int(len(veto)), 'pairs': 0, 'matched_controls': 0,
            'matched_control_large_rate': np.nan, 'matched_control_fail_rate': np.nan,
            'veto_large_rate': float(veto.is_large.mean()), 'veto_fail_rate': float(veto.is_fail.mean()),
        }

    unit = mt.groupby('veto_index').agg(
        veto_large=('veto_large', 'first'),
        veto_fail=('veto_fail', 'first'),
        control_large=('control_large', 'mean'),
        control_fail=('control_fail', 'mean'),
        mean_distance=('distance', 'mean'),
    ).reset_index()
    diag = {
        'veto_units': int(len(veto)),
        'matched_veto_units': int(len(unit)),
        'pairs': int(len(mt)),
        'matched_controls': int(mt.keep_index.nunique()),
        'veto_large_rate': float(unit.veto_large.mean()),
        'matched_control_large_rate': float(unit.control_large.mean()),
        'veto_minus_matched_large_pp': 100.0 * float(unit.veto_large.mean() - unit.control_large.mean()),
        'veto_fail_rate': float(unit.veto_fail.mean()),
        'matched_control_fail_rate': float(unit.control_fail.mean()),
        'veto_minus_matched_fail_pp': 100.0 * float(unit.veto_fail.mean() - unit.control_fail.mean()),
        'mean_distance': float(unit.mean_distance.mean()),
    }
    return mt, diag


def pooled_metrics(parts, label):
    if not parts:
        return {'label': label, 'n': 0}
    x = pd.concat(parts, ignore_index=True)
    s = x[x.common_support == 1]
    v = s[s.unsupported_veto == 1]
    k = s[s.unsupported_veto == 0]
    out = {
        'label': label,
        'n': int(len(x)),
        'supported_n': int(len(s)),
        'support_coverage': float(len(s) / len(x)) if len(x) else np.nan,
        'baseline_large_rate': float(s.is_large.mean()) if len(s) else np.nan,
        'baseline_fail_rate': float(s.is_fail.mean()) if len(s) else np.nan,
        'veto_n': int(len(v)),
        'veto_large_rate': float(v.is_large.mean()) if len(v) else np.nan,
        'veto_fail_rate': float(v.is_fail.mean()) if len(v) else np.nan,
        'keep_n': int(len(k)),
        'keep_large_rate': float(k.is_large.mean()) if len(k) else np.nan,
        'keep_fail_rate': float(k.is_fail.mean()) if len(k) else np.nan,
        'veto_minus_keep_large_pp': 100.0 * float(v.is_large.mean() - k.is_large.mean()) if len(v) and len(k) else np.nan,
        'veto_minus_keep_fail_pp': 100.0 * float(v.is_fail.mean() - k.is_fail.mean()) if len(v) and len(k) else np.nan,
        'large_retention': float(k.is_large.sum() / s.is_large.sum()) if len(s) and s.is_large.sum() else np.nan,
        'frequency_retention': float(len(k) / len(s)) if len(s) else np.nan,
    }
    return out


def fold_pass(row):
    if row['supported_n'] < 10 or row['veto_n'] < 3 or row['keep_n'] < 5:
        return False
    a = row['veto_minus_keep_large_pp']
    b = row['veto_minus_keep_fail_pp']
    return bool(np.isfinite(a) and np.isfinite(b) and a <= -5.0 and b >= 5.0)


def main():
    _, e, base = build_base()
    outdir = Path('lab012')
    outdir.mkdir(exist_ok=True)

    fold_rows = []
    threshold_rows = []
    oof_parts = []
    match_rows = []
    match_diags = []

    for year in FULL_YEARS:
        train = base[base.year.isin([y for y in FULL_YEARS if y != year])].copy().reset_index(drop=True)
        test = base[base.year == year].copy().reset_index(drop=True)
        rule = freeze_rule(train)
        z = apply_rule(test, rule)
        z = common_support(train, z)
        z['fold_year'] = year
        z['fold_type'] = 'DISCOVERY_YEAR_DIAGNOSTIC' if year == DISCOVERY_YEAR else 'INDEPENDENT_YEAR_REPLICATION'
        oof_parts.append(z)

        fm = fold_metrics(z, year, z.fold_type.iloc[0] if len(z) else ('DISCOVERY_YEAR_DIAGNOSTIC' if year == DISCOVERY_YEAR else 'INDEPENDENT_YEAR_REPLICATION'))
        fold_rows.append(fm)
        threshold_rows.append({'year': year, 'fold_type': fm['fold_type'], **rule})

        mt, md = within_year_veto_match(z)
        if len(mt):
            mt['year'] = year
            match_rows.append(mt)
        md['year'] = year
        md['fold_type'] = fm['fold_type']
        match_diags.append(md)

    folds = pd.DataFrame(fold_rows)
    folds['pass'] = folds.apply(fold_pass, axis=1)
    thresholds = pd.DataFrame(threshold_rows)
    oof = pd.concat(oof_parts, ignore_index=True)
    matches = pd.concat(match_rows, ignore_index=True) if match_rows else pd.DataFrame()
    match_diag = pd.DataFrame(match_diags)

    independent_parts = [x for x in oof_parts if len(x) and int(x.year.iloc[0]) in REPLICATION_YEARS]
    discovery_parts = [x for x in oof_parts if len(x) and int(x.year.iloc[0]) == DISCOVERY_YEAR]
    pooled_ind = pooled_metrics(independent_parts, 'POOLED_INDEPENDENT_REPLICATION_2020_2022_2025')
    pooled_2021 = pooled_metrics(discovery_parts, 'DISCOVERY_2021_DIAGNOSTIC')

    # Forward/pseudo-OOS 2026: freeze once on 2020-2025, no 2026 information in thresholds.
    train_fwd = base[base.year.isin(FULL_YEARS)].copy().reset_index(drop=True)
    test_fwd = base[base.year == FORWARD_YEAR].copy().reset_index(drop=True)
    fwd_rule = freeze_rule(train_fwd)
    fwd = apply_rule(test_fwd, fwd_rule)
    fwd = common_support(train_fwd, fwd)
    fwd['fold_year'] = FORWARD_YEAR
    fwd['fold_type'] = 'PSEUDO_FORWARD_2026'
    fwd_metrics = fold_metrics(fwd, FORWARD_YEAR, 'PSEUDO_FORWARD_2026')
    fwd_match, fwd_match_diag = within_year_veto_match(fwd)
    fwd_match_diag['year'] = FORWARD_YEAR
    fwd_match_diag['fold_type'] = 'PSEUDO_FORWARD_2026'

    valid_ind = folds[(folds.fold_type == 'INDEPENDENT_YEAR_REPLICATION') & (folds.supported_n >= 10) & (folds.veto_n >= 3) & (folds.keep_n >= 5)]
    pass_n = int(valid_ind['pass'].sum()) if len(valid_ind) else 0
    valid_n = int(len(valid_ind))

    p_large = pooled_ind.get('veto_minus_keep_large_pp', np.nan)
    p_fail = pooled_ind.get('veto_minus_keep_fail_pp', np.nan)
    p_ret = pooled_ind.get('large_retention', np.nan)
    p_freq = pooled_ind.get('frequency_retention', np.nan)

    strong = (
        valid_n >= 3 and pass_n >= max(3, int(np.ceil(0.60 * valid_n)))
        and np.isfinite(p_large) and p_large <= -8.0
        and np.isfinite(p_fail) and p_fail >= 8.0
        and np.isfinite(p_ret) and p_ret >= 0.70
    )
    partial = (
        valid_n >= 2
        and np.isfinite(p_large) and p_large <= -5.0
        and np.isfinite(p_fail) and p_fail >= 3.0
    )
    if strong:
        verdict_class = 'UNSUPPORTED_BREAKOUT_VETO_REPLICATES_ON_COMMON_SUPPORT'
    elif partial:
        verdict_class = 'UNSUPPORTED_BREAKOUT_VETO_PARTIALLY_REPLICATES_NEEDS_MORE_OOS'
    else:
        verdict_class = 'UNSUPPORTED_BREAKOUT_VETO_DOES_NOT_REPLICATE_RELIABLY'

    verdict = {
        'lab': LAB,
        'question': 'Does the LAB011 unsupported-breakout / weak-flow-sponsorship mechanism replicate out of year after strict slow-regime common-support gating?',
        'base_selector': 'LOW_ACTIVITY_SCORE>=2 AND FLOW_DELTA_12>0',
        'target': 'clean MFE >= 2.5R within 32 M15 bars before structural SL',
        'causality': 'all sponsorship features end at i-1; BOS candle and post-BOS bars excluded',
        'frozen_main_veto': 'price_response_per_flow_6 >= train Q67 AND abs(flow_delta_micro_6) <= train Q33 AND (flow_persistence_12 <= train Q33 OR persistence_shift_3v12 <= train Q33)',
        'threshold_policy': 'quantile levels fixed before LAB012; numerical cutoffs estimated from training years only',
        'common_support': {
            'features': SUPPORT_FEATURES,
            'exact_strata': 'direction + low_activity_score',
            'train_quantile_box': [SUPPORT_Q_LO, SUPPORT_Q_HI],
            'k': SUPPORT_K,
            'max_rms_standardized_distance': SUPPORT_MAX_RMS_DISTANCE,
        },
        'independent_replication_years': REPLICATION_YEARS,
        'discovery_year_diagnostic_only': DISCOVERY_YEAR,
        'pooled_independent_replication': pooled_ind,
        'discovery_2021_diagnostic': pooled_2021,
        'valid_independent_years': valid_n,
        'passing_independent_years': pass_n,
        'forward_2026': fwd_metrics,
        'forward_2026_rule': fwd_rule,
        'forward_2026_match_diagnostic': fwd_match_diag,
        'verdict_class': verdict_class,
        'warning': 'Research classification only. No production router/EA admission until independent execution/cost replication and untouched forward validation.',
    }

    print('=' * 100)
    print(LAB)
    print('EVENTS', len(e), 'BASE LOW2_X_ALIGN', len(base))
    print('IMPORTANT: all sponsorship features end at i-1; BOS/post-BOS excluded.')
    print('\nFROZEN RULE:')
    print(verdict['frozen_main_veto'])
    print('\nLOYO YEARLY RESULTS')
    print(folds.to_string(index=False))
    print('\nTHRESHOLDS BY TRAINING FOLD')
    print(thresholds.to_string(index=False))
    print('\nSAME-YEAR VETO MATCH DIAGNOSTICS')
    print(match_diag.to_string(index=False))
    print('\nPOOLED INDEPENDENT REPLICATION')
    print(json.dumps(pooled_ind, indent=2))
    print('\n2021 DISCOVERY-YEAR DIAGNOSTIC')
    print(json.dumps(pooled_2021, indent=2))
    print('\nPSEUDO-FORWARD 2026')
    print(json.dumps(fwd_metrics, indent=2))
    print('\nVERDICT')
    print(json.dumps(verdict, indent=2))

    base.to_csv(outdir / f'{LAB}_BASE_EVENTS.csv', index=False)
    oof.to_csv(outdir / f'{LAB}_LOYO_OOF_EVENTS.csv', index=False)
    folds.to_csv(outdir / f'{LAB}_YEARLY_FOLDS.csv', index=False)
    thresholds.to_csv(outdir / f'{LAB}_FROZEN_THRESHOLDS_BY_FOLD.csv', index=False)
    match_diag.to_csv(outdir / f'{LAB}_MATCH_DIAGNOSTICS.csv', index=False)
    if len(matches):
        matches.to_csv(outdir / f'{LAB}_WITHIN_YEAR_MATCHES.csv', index=False)
    fwd.to_csv(outdir / f'{LAB}_FORWARD_2026_EVENTS.csv', index=False)
    if len(fwd_match):
        fwd_match.to_csv(outdir / f'{LAB}_FORWARD_2026_MATCHES.csv', index=False)
    (outdir / 'verdict.json').write_text(json.dumps(verdict, indent=2), encoding='utf-8')

    report = [
        f'# {LAB}', '',
        'Strict out-of-year common-support replication of the LAB011 unsupported-breakout / weak-flow-sponsorship hypothesis.', '',
        'Main veto was frozen conceptually before this run; only fold-specific numerical quantiles are learned from training years.', '',
        '## Yearly LOYO results', '', folds.to_markdown(index=False), '',
        '## Same-year slow-state matched diagnostic', '', match_diag.to_markdown(index=False), '',
        '## Pooled independent replication', '', f'```json\n{json.dumps(pooled_ind, indent=2)}\n```', '',
        '## 2021 diagnostic', '', f'```json\n{json.dumps(pooled_2021, indent=2)}\n```', '',
        '## Pseudo-forward 2026', '', f'```json\n{json.dumps(fwd_metrics, indent=2)}\n```', '',
        '## Verdict', '', f'```json\n{json.dumps(verdict, indent=2)}\n```',
    ]
    (outdir / f'{LAB}_REPORT.md').write_text('\n'.join(report), encoding='utf-8')


if __name__ == '__main__':
    main()
