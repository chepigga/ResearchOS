import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

import btc_low_activity_flow_alignment_flip_lab008 as lab8
import btc_low_activity_flow_2021_failure_regime_causal_map_lab010 as lab10
import btc_low_activity_flow_2021_matched_microstructure_failure_map_lab011 as lab11
import btc_unsupported_breakout_flow_sponsorship_common_support_lab012 as lab12

LAB = 'BTC_BUY_P12_FLOW_SPONSORSHIP_BROAD_SHELL_REPLICATION_LAB_014'
INDEPENDENT_YEARS = [2020, 2022, 2023, 2024, 2025]
DISCOVERY_YEAR = 2021
FORWARD_YEAR = 2026
Q_LOW = 1.0 / 3.0
MIN_VETO_YEAR = 4
MIN_KEEP_YEAR = 8
MIN_VETO_POOLED = 20

SHELLS = [
    'ALL_BUY_BOS',
    'LOW_ACTIVITY_BUY_BOS',
    'LOW_ACTIVITY_PLUS_FLOW_ALIGN_BUY_BOS',
]

OUT = Path('lab014')
OUT.mkdir(parents=True, exist_ok=True)


def num(s):
    return pd.to_numeric(s, errors='coerce').astype(float)


def build_broad_base():
    # Exact causal lineage used by LAB012/LAB013, but do NOT apply their narrow shell yet.
    m, sig, e = lab8.build_all_events()
    discovery = e[(e.signal_time >= lab8.DISCOVERY_START) & (e.signal_time <= lab8.DISCOVERY_END)].copy()
    frozen_state_thr = lab8.freeze_thresholds(discovery)
    x = lab8.apply_frozen_state(e, frozen_state_thr)
    x = lab10.add_slow_regime_features(m, x)
    x = lab11.add_micro(m, x)
    x = x[x.year.between(2020, 2026)].copy().reset_index(drop=True)
    return m, e, x, frozen_state_thr


def shell_mask(df, shell):
    buy = df.direction.astype(int) == 1
    if shell == 'ALL_BUY_BOS':
        return buy
    if shell == 'LOW_ACTIVITY_BUY_BOS':
        return buy & (df.low_activity_score >= 2)
    if shell == 'LOW_ACTIVITY_PLUS_FLOW_ALIGN_BUY_BOS':
        return buy & (df.low_activity_score >= 2) & (df.flow_align_12 == 1)
    raise KeyError(shell)


def narrow_buy(df):
    return df[shell_mask(df, 'LOW_ACTIVITY_PLUS_FLOW_ALIGN_BUY_BOS')].copy()


def freeze_p12_from_original_shell(train):
    # Critical design choice: threshold is estimated ONLY from the original LAB013 BUY shell,
    # then applied unchanged to all broader shells. This isolates context interaction and avoids
    # silently redefining "low P12" in each shell.
    s = num(narrow_buy(train).flow_persistence_12).dropna()
    return float(s.quantile(Q_LOW)) if len(s) else np.nan


def apply_p12(df, cutoff):
    z = df.copy()
    p12 = num(z.flow_persistence_12)
    z['p12_cutoff'] = cutoff
    z['veto_P12_LOW'] = ((p12 <= cutoff) if np.isfinite(cutoff) else False).astype(int)
    return z


def summarize(df, shell, year, fold_type, support_mode):
    if support_mode == 'COMMON_SUPPORT':
        s = df[df.common_support == 1].copy()
    else:
        s = df.copy()
    veto = s[s.veto_P12_LOW == 1]
    keep = s[s.veto_P12_LOW == 0]

    def rate(x, c):
        return float(x[c].mean()) if len(x) else np.nan

    bl = rate(s, 'is_large'); bf = rate(s, 'is_fail')
    vl = rate(veto, 'is_large'); vf = rate(veto, 'is_fail')
    kl = rate(keep, 'is_large'); kf = rate(keep, 'is_fail')
    lgap = 100 * (vl - kl) if np.isfinite(vl) and np.isfinite(kl) else np.nan
    fgap = 100 * (vf - kf) if np.isfinite(vf) and np.isfinite(kf) else np.nan
    valid = len(veto) >= MIN_VETO_YEAR and len(keep) >= MIN_KEEP_YEAR
    passed = bool(valid and np.isfinite(lgap) and np.isfinite(fgap) and lgap <= -7 and fgap >= 5)
    large_total = int(s.is_large.sum()) if len(s) else 0
    return {
        'shell': shell,
        'support_mode': support_mode,
        'year': int(year),
        'fold_type': fold_type,
        'test_n': int(len(df)),
        'supported_n': int(len(s)),
        'support_coverage': float(len(s) / len(df)) if len(df) else np.nan,
        'p12_cutoff': float(df.p12_cutoff.iloc[0]) if len(df) else np.nan,
        'baseline_large_rate': bl,
        'baseline_fail_rate': bf,
        'veto_n': int(len(veto)),
        'veto_share': float(len(veto) / len(s)) if len(s) else np.nan,
        'veto_large_rate': vl,
        'keep_n': int(len(keep)),
        'keep_large_rate': kl,
        'veto_minus_keep_large_pp': lgap,
        'veto_fail_rate': vf,
        'keep_fail_rate': kf,
        'veto_minus_keep_fail_pp': fgap,
        'large_retention': float(keep.is_large.sum() / large_total) if large_total else np.nan,
        'frequency_retention': float(len(keep) / len(s)) if len(s) else np.nan,
        'valid_year': bool(valid),
        'pass_year': bool(passed),
    }


def pooled_metrics(oof, shell, support_mode):
    q = oof[(oof.shell == shell) & (oof.support_mode == support_mode)].copy()
    veto = q[q.veto_P12_LOW == 1]
    keep = q[q.veto_P12_LOW == 0]

    def rate(x, c):
        return float(x[c].mean()) if len(x) else np.nan

    vl = rate(veto, 'is_large'); kl = rate(keep, 'is_large')
    vf = rate(veto, 'is_fail'); kf = rate(keep, 'is_fail')
    try:
        odds_l, p_l = fisher_exact(
            [[int(veto.is_large.sum()), int(len(veto) - veto.is_large.sum())],
             [int(keep.is_large.sum()), int(len(keep) - keep.is_large.sum())]],
            alternative='less') if len(veto) and len(keep) else (np.nan, np.nan)
    except Exception:
        odds_l, p_l = np.nan, np.nan
    try:
        odds_f, p_f = fisher_exact(
            [[int(veto.is_fail.sum()), int(len(veto) - veto.is_fail.sum())],
             [int(keep.is_fail.sum()), int(len(keep) - keep.is_fail.sum())]],
            alternative='greater') if len(veto) and len(keep) else (np.nan, np.nan)
    except Exception:
        odds_f, p_f = np.nan, np.nan

    large_total = int(q.is_large.sum()) if len(q) else 0
    return {
        'shell': shell,
        'support_mode': support_mode,
        'supported_n': int(len(q)),
        'veto_n': int(len(veto)),
        'keep_n': int(len(keep)),
        'veto_large_rate': vl,
        'keep_large_rate': kl,
        'veto_minus_keep_large_pp': 100 * (vl - kl) if np.isfinite(vl) and np.isfinite(kl) else np.nan,
        'veto_fail_rate': vf,
        'keep_fail_rate': kf,
        'veto_minus_keep_fail_pp': 100 * (vf - kf) if np.isfinite(vf) and np.isfinite(kf) else np.nan,
        'large_retention': float(keep.is_large.sum() / large_total) if large_total else np.nan,
        'frequency_retention': float(len(keep) / len(q)) if len(q) else np.nan,
        'fisher_large_less_p': float(p_l) if np.isfinite(p_l) else np.nan,
        'fisher_fail_greater_p': float(p_f) if np.isfinite(p_f) else np.nan,
        'fisher_large_odds': float(odds_l) if np.isfinite(odds_l) else np.nan,
        'fisher_fail_odds': float(odds_f) if np.isfinite(odds_f) else np.nan,
    }


def make_eval_frame(train, test, shell, cutoff):
    tr = train[shell_mask(train, shell)].copy().reset_index(drop=True)
    te = test[shell_mask(test, shell)].copy().reset_index(drop=True)
    raw = apply_p12(te, cutoff)
    raw['common_support'] = 1
    raw['support_reason'] = 'RAW_UNGATED'

    if len(tr) and len(te):
        sup = lab12.common_support(tr, te)
        sup = apply_p12(sup, cutoff)
    else:
        sup = apply_p12(te, cutoff)
        sup['common_support'] = 0
        sup['support_reason'] = 'EMPTY_TRAIN_OR_TEST'
    return raw, sup


def append_oof(rows, frame, shell, support_mode, eval_year, fold_type):
    z = frame.copy()
    if support_mode == 'COMMON_SUPPORT':
        z = z[z.common_support == 1].copy()
    z['shell'] = shell
    z['support_mode'] = support_mode
    z['eval_year'] = int(eval_year)
    z['eval_fold_type'] = fold_type
    rows.append(z)


def add_stability(pooled_df, yearly_df):
    rows = []
    for _, p in pooled_df.iterrows():
        y = yearly_df[
            (yearly_df.shell == p.shell)
            & (yearly_df.support_mode == p.support_mode)
            & (yearly_df.fold_type == 'INDEPENDENT_LOYO')
        ]
        valid = y[y.valid_year == True]
        d = p.to_dict()
        d['valid_years'] = int(len(valid))
        d['passing_years'] = int(valid.pass_year.sum())
        d['negative_large_gap_years'] = int((valid.veto_minus_keep_large_pp < 0).sum())
        d['positive_fail_gap_years'] = int((valid.veto_minus_keep_fail_pp > 0).sum())
        pooled_pass = bool(
            d['veto_n'] >= MIN_VETO_POOLED
            and np.isfinite(d['veto_minus_keep_large_pp'])
            and np.isfinite(d['veto_minus_keep_fail_pp'])
            and d['veto_minus_keep_large_pp'] <= -7
            and d['veto_minus_keep_fail_pp'] >= 5
        )
        d['pooled_pass'] = pooled_pass
        d['robust_3of5'] = bool(pooled_pass and d['valid_years'] >= 3 and d['passing_years'] >= 3)
        d['robust_4of5'] = bool(pooled_pass and d['valid_years'] >= 4 and d['passing_years'] >= 4)
        rows.append(d)
    return pd.DataFrame(rows)


def choose_verdict(stability):
    s = stability[stability.support_mode == 'COMMON_SUPPORT'].set_index('shell')
    a = s.loc['ALL_BUY_BOS']
    b = s.loc['LOW_ACTIVITY_BUY_BOS']
    c = s.loc['LOW_ACTIVITY_PLUS_FLOW_ALIGN_BUY_BOS']
    if bool(a.robust_3of5):
        return 'P12_GENERALIZES_TO_ALL_BUY_BOS'
    if bool(b.robust_3of5) and not bool(a.robust_3of5):
        return 'P12_REQUIRES_LOW_ACTIVITY_CONTEXT'
    if bool(c.robust_3of5) and not bool(b.robust_3of5):
        return 'P12_REQUIRES_LOW_ACTIVITY_PLUS_FLOW_ALIGNMENT_INTERACTION'
    if bool(a.pooled_pass) or bool(b.pooled_pass) or bool(c.pooled_pass):
        return 'P12_EFFECT_PRESENT_BUT_YEARLY_ROBUSTNESS_INSUFFICIENT'
    return 'P12_BROAD_SHELL_REPLICATION_FAILS'


def main():
    print('=' * 110)
    print(LAB)
    _, all_events, base, state_thr = build_broad_base()
    print(f'ALL_EVENTS {len(all_events)} BROAD_BASE {len(base)}')
    print('QUESTION: where does frozen BUY P12_LOW actually work: all BUY BOS, LOW_ACTIVITY, or only LOW_ACTIVITY+FLOW_ALIGN?')
    print('CAUSALITY: all micro/persistence windows end at i-1; BOS candle/post-BOS excluded from predictor.')
    print('THRESHOLD: each LOYO fold estimates P12 Q33 ONLY in original LAB013 BUY shell, then applies the same cutoff to all three shells.')
    print('2021 excluded from independent threshold/support training; 2026 pseudo-forward.')

    # Lineage parity diagnostics against LAB013 shell.
    narrow_all = narrow_buy(base)
    print(f'LAB013_NARROW_BUY_ALL_2020_2026 {len(narrow_all)}')
    for y in range(2020, 2027):
        q = narrow_all[narrow_all.year == y]
        if len(q):
            print(f'  NARROW BUY {y}: n={len(q)} LARGE={int(q.is_large.sum())} ({q.is_large.mean():.4f}) FAIL={int(q.is_fail.sum())} ({q.is_fail.mean():.4f})')

    yearly_rows = []
    oof_rows = []
    threshold_rows = []

    # Strict independent LOYO.
    for test_year in INDEPENDENT_YEARS:
        train = base[base.year.isin([y for y in INDEPENDENT_YEARS if y != test_year])].copy()
        test = base[base.year == test_year].copy()
        cutoff = freeze_p12_from_original_shell(train)
        threshold_rows.append({
            'year': test_year,
            'fold_type': 'INDEPENDENT_LOYO',
            'threshold_source': 'ORIGINAL_LAB013_NARROW_BUY_SHELL',
            'q': Q_LOW,
            'p12_cutoff': cutoff,
            'train_n_narrow_buy': int(len(narrow_buy(train))),
        })
        for shell in SHELLS:
            raw, sup = make_eval_frame(train, test, shell, cutoff)
            yearly_rows.append(summarize(raw, shell, test_year, 'INDEPENDENT_LOYO', 'RAW'))
            yearly_rows.append(summarize(sup, shell, test_year, 'INDEPENDENT_LOYO', 'COMMON_SUPPORT'))
            append_oof(oof_rows, raw, shell, 'RAW', test_year, 'INDEPENDENT_LOYO')
            append_oof(oof_rows, sup, shell, 'COMMON_SUPPORT', test_year, 'INDEPENDENT_LOYO')

    yearly_df = pd.DataFrame(yearly_rows)
    oof_df = pd.concat(oof_rows, ignore_index=True) if oof_rows else pd.DataFrame()
    pooled = []
    for shell in SHELLS:
        for mode in ('RAW', 'COMMON_SUPPORT'):
            pooled.append(pooled_metrics(oof_df, shell, mode))
    pooled_df = pd.DataFrame(pooled)
    stability_df = add_stability(pooled_df, yearly_df)

    # 2021 discovery diagnostic + 2026 pseudo-forward; independent years only train thresholds/support.
    diag_rows = []
    train_ind = base[base.year.isin(INDEPENDENT_YEARS)].copy()
    cutoff_ind = freeze_p12_from_original_shell(train_ind)
    for year, fold_type in [
        (DISCOVERY_YEAR, 'DISCOVERY_2021_DIAGNOSTIC'),
        (FORWARD_YEAR, 'PSEUDO_FORWARD_2026'),
    ]:
        test = base[base.year == year].copy()
        for shell in SHELLS:
            raw, sup = make_eval_frame(train_ind, test, shell, cutoff_ind)
            diag_rows.append(summarize(raw, shell, year, fold_type, 'RAW'))
            diag_rows.append(summarize(sup, shell, year, fold_type, 'COMMON_SUPPORT'))
    diag_df = pd.DataFrame(diag_rows)

    verdict_class = choose_verdict(stability_df)

    # Explicit interaction deltas: how much effect strengthens as shell narrows.
    cs = stability_df[stability_df.support_mode == 'COMMON_SUPPORT'].set_index('shell')
    interaction = {
        'large_gap_all_buy_pp': float(cs.loc['ALL_BUY_BOS', 'veto_minus_keep_large_pp']),
        'large_gap_low_activity_pp': float(cs.loc['LOW_ACTIVITY_BUY_BOS', 'veto_minus_keep_large_pp']),
        'large_gap_low_activity_align_pp': float(cs.loc['LOW_ACTIVITY_PLUS_FLOW_ALIGN_BUY_BOS', 'veto_minus_keep_large_pp']),
        'fail_gap_all_buy_pp': float(cs.loc['ALL_BUY_BOS', 'veto_minus_keep_fail_pp']),
        'fail_gap_low_activity_pp': float(cs.loc['LOW_ACTIVITY_BUY_BOS', 'veto_minus_keep_fail_pp']),
        'fail_gap_low_activity_align_pp': float(cs.loc['LOW_ACTIVITY_PLUS_FLOW_ALIGN_BUY_BOS', 'veto_minus_keep_fail_pp']),
    }

    verdict = {
        'lab': LAB,
        'question': 'Does frozen BUY P12 sponsorship replicate in ALL BUY BOS, LOW_ACTIVITY BUY BOS, or only LOW_ACTIVITY+FLOW_ALIGN BUY BOS?',
        'target': 'clean MFE >= 2.5R within 32 M15 bars before structural SL',
        'predictor': 'flow_persistence_12 only',
        'causality': 'all persistence inputs end at i-1; BOS candle/post-BOS excluded',
        'shells': SHELLS,
        'threshold_policy': 'LOYO P12 Q33 estimated only from original LAB013 narrow BUY shell; exact same cutoff applied to all shells; no threshold search',
        'support_policy': 'report RAW and LAB012 slow-state COMMON_SUPPORT separately',
        'independent_years': INDEPENDENT_YEARS,
        'discovery_year_excluded_from_training': DISCOVERY_YEAR,
        'pseudo_forward_year': FORWARD_YEAR,
        'pooled_common_support': stability_df[stability_df.support_mode == 'COMMON_SUPPORT'].to_dict('records'),
        'pooled_raw': stability_df[stability_df.support_mode == 'RAW'].to_dict('records'),
        'interaction': interaction,
        'verdict_class': verdict_class,
        'warning': 'Replication/interaction study only. Historical years have prior inspection; true production admission still requires untouched forward and execution-cost validation.',
    }

    print('\nPOOLED / STABILITY')
    cols = [
        'shell','support_mode','supported_n','veto_n','keep_n',
        'veto_large_rate','keep_large_rate','veto_minus_keep_large_pp',
        'veto_fail_rate','keep_fail_rate','veto_minus_keep_fail_pp',
        'large_retention','frequency_retention','fisher_large_less_p','fisher_fail_greater_p',
        'valid_years','passing_years','negative_large_gap_years','positive_fail_gap_years','pooled_pass','robust_3of5'
    ]
    print(stability_df[cols].to_string(index=False))
    print('\nYEARLY INDEPENDENT — COMMON SUPPORT')
    print(yearly_df[yearly_df.support_mode == 'COMMON_SUPPORT'].to_string(index=False))
    print('\n2021 / 2026 DIAGNOSTICS — COMMON SUPPORT')
    print(diag_df[diag_df.support_mode == 'COMMON_SUPPORT'].to_string(index=False))
    print('\nVERDICT')
    print(json.dumps(verdict, indent=2))

    yearly_df.to_csv(OUT / 'lab014_yearly_independent.csv', index=False)
    stability_df.to_csv(OUT / 'lab014_pooled_stability.csv', index=False)
    diag_df.to_csv(OUT / 'lab014_2021_2026_diagnostics.csv', index=False)
    pd.DataFrame(threshold_rows).to_csv(OUT / 'lab014_frozen_p12_thresholds.csv', index=False)
    oof_df.to_csv(OUT / 'lab014_oof_events.csv', index=False)
    with open(OUT / 'lab014_verdict.json', 'w', encoding='utf-8') as f:
        json.dump(verdict, f, indent=2)


if __name__ == '__main__':
    main()
