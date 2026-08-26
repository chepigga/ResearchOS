import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

import btc_buy_p12_flow_sponsorship_broad_shell_replication_lab014 as lab14

LAB = 'BTC_NATIVE_FLOW_REGIME_ROUTER_TO_POSITIVE_CONTINUATION_LAB_015'
OUT = Path('lab015')
OUT.mkdir(parents=True, exist_ok=True)

INDEPENDENT_YEARS = [2020, 2022, 2023, 2024, 2025]
DISCOVERY_DIAGNOSTIC_YEAR = 2021
FORWARD_YEAR = 2026
Q_SKIP = 1.0 / 3.0
Q_ALLOW = 2.0 / 3.0

# Frozen architecture. No feature search / threshold search in this LAB.
PRICE_REGIME = [
    'break_distance_atr', 'stop_atr', 'atr_regime_ratio',
    'rv_7d_daily_pct', 'rv_prev23d_daily_pct', 'rv_7d_vs_prev23d',
    'range_7d_vs_prev23d', 'trend_eff_7d', 'trend_eff_30d',
    'trend_signed_7d_atr', 'trend_signed_30d_atr',
    'directional_position_30d', 'direction_bar_share_7d', 'direction_bar_share_30d',
]

NATIVE_FLOW = [
    'low_activity_score', 'flow_align_12',
    'trades_7d_vs_prev23d', 'volume_7d_vs_prev23d', 'avg_trade_7d_vs_prev23d',
    'flow_delta_7d', 'flow_delta_prev23d', 'flow_shift_7d_minus_prev23d',
    'flow_delta_micro_12', 'flow_persistence_12', 'flow_flip_rate_12', 'flow_churn_12',
    'price_response_per_flow_12', 'aligned_flow_no_result_share_12',
    'failed_push_share_12', 'future_wick_ratio_12',
    'response_shift_3v12', 'no_result_shift_3v12', 'persistence_shift_3v12',
]

# Small preregistered interaction surface: regime x sponsorship quality.
REGIME_AXES = [
    'rv_7d_vs_prev23d', 'trend_eff_7d', 'trend_signed_7d_atr',
    'directional_position_30d', 'range_7d_vs_prev23d',
]
FLOW_AXES = [
    'flow_persistence_12', 'flow_delta_micro_12', 'flow_churn_12',
    'price_response_per_flow_12', 'aligned_flow_no_result_share_12',
]

MODELS = ['PRICE_REGIME_ONLY', 'PRICE_REGIME_PLUS_NATIVE_FLOW']
UNIVERSES = ['ALL_BUY_BOS', 'LOW_ACTIVITY_BUY_BOS']


def safe_auc(y, p):
    y = np.asarray(y, int)
    p = np.asarray(p, float)
    return float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else np.nan


def safe_ap(y, p):
    y = np.asarray(y, int)
    p = np.asarray(p, float)
    return float(average_precision_score(y, p)) if y.sum() > 0 else np.nan


def clean_buy(base):
    x = base[base.direction.astype(int) == 1].copy().reset_index(drop=True)
    x = x[x.year.between(2020, 2026)].copy().reset_index(drop=True)
    return x


def universe_mask(df, universe):
    if universe == 'ALL_BUY_BOS':
        return np.ones(len(df), dtype=bool)
    if universe == 'LOW_ACTIVITY_BUY_BOS':
        return pd.to_numeric(df.low_activity_score, errors='coerce').fillna(-999).to_numpy(float) >= 2
    raise KeyError(universe)


def fit_transform(train, test, model_name):
    base_cols = [c for c in PRICE_REGIME if c in train.columns and c in test.columns]
    flow_cols = [c for c in NATIVE_FLOW if c in train.columns and c in test.columns]
    cols = base_cols if model_name == 'PRICE_REGIME_ONLY' else base_cols + flow_cols
    cols = list(dict.fromkeys(cols))

    tr = train[cols].apply(pd.to_numeric, errors='coerce').astype(float)
    te = test[cols].apply(pd.to_numeric, errors='coerce').astype(float)

    med = tr.median(axis=0)
    tr = tr.fillna(med).fillna(0.0)
    te = te.fillna(med).fillna(0.0)
    mu = tr.mean(axis=0)
    sd = tr.std(axis=0, ddof=0).replace(0.0, 1.0).fillna(1.0)
    ztr = (tr - mu) / sd
    zte = (te - mu) / sd

    names = list(cols)
    Xtr = ztr.to_numpy(float)
    Xte = zte.to_numpy(float)

    if model_name == 'PRICE_REGIME_PLUS_NATIVE_FLOW':
        inter_tr = []
        inter_te = []
        inter_names = []
        for a in REGIME_AXES:
            if a not in ztr.columns:
                continue
            for b in FLOW_AXES:
                if b not in ztr.columns:
                    continue
                inter_tr.append((ztr[a] * ztr[b]).to_numpy(float))
                inter_te.append((zte[a] * zte[b]).to_numpy(float))
                inter_names.append(f'{a}__X__{b}')
        if inter_tr:
            Xtr = np.column_stack([Xtr] + inter_tr)
            Xte = np.column_stack([Xte] + inter_te)
            names += inter_names
    return Xtr, Xte, names


def fit_model(train, test, model_name):
    Xtr, Xte, names = fit_transform(train, test, model_name)
    ytr = train.is_large.astype(int).to_numpy()
    if len(np.unique(ytr)) < 2:
        return np.full(len(train), ytr.mean() if len(ytr) else 0.0), np.full(len(test), ytr.mean() if len(ytr) else 0.0), names, None
    model = LogisticRegression(
        C=0.35,
        penalty='l2',
        class_weight='balanced',
        solver='liblinear',
        max_iter=5000,
        random_state=20260826,
    )
    model.fit(Xtr, ytr)
    return model.predict_proba(Xtr)[:, 1], model.predict_proba(Xte)[:, 1], names, model


def route(scores, lo, hi):
    s = np.asarray(scores, float)
    return np.where(s >= hi, 'ALLOW', np.where(s <= lo, 'SKIP', 'REDUCE'))


def summarize_router(frame, year, fold_type, model_name, universe, lo, hi):
    q = frame[universe_mask(frame, universe)].copy()
    if not len(q):
        return []
    rows = []
    baseline_large = float(q.is_large.mean())
    baseline_fail = float(q.is_fail.mean())
    for tier in ['ALLOW', 'REDUCE', 'SKIP']:
        g = q[q.route == tier]
        rows.append({
            'year': int(year), 'fold_type': fold_type, 'model': model_name, 'universe': universe,
            'tier': tier, 'n': int(len(g)), 'share': float(len(g) / len(q)),
            'large_rate': float(g.is_large.mean()) if len(g) else np.nan,
            'fail_rate': float(g.is_fail.mean()) if len(g) else np.nan,
            'baseline_large_rate': baseline_large, 'baseline_fail_rate': baseline_fail,
            'large_uplift_pp': 100 * (float(g.is_large.mean()) - baseline_large) if len(g) else np.nan,
            'fail_delta_pp': 100 * (float(g.is_fail.mean()) - baseline_fail) if len(g) else np.nan,
            'score_lo': float(lo), 'score_hi': float(hi),
        })
    return rows


def evaluate_fold(train, test, year, fold_type):
    metric_rows, tier_rows, event_rows, coef_rows = [], [], [], []
    for model_name in MODELS:
        tr_score, te_score, names, model = fit_model(train, test, model_name)
        lo = float(np.quantile(tr_score, Q_SKIP))
        hi = float(np.quantile(tr_score, Q_ALLOW))
        te = test.copy()
        te['score'] = te_score
        te['route'] = route(te_score, lo, hi)
        te['model'] = model_name
        te['eval_year'] = int(year)
        te['fold_type'] = fold_type
        event_rows.append(te)

        for universe in UNIVERSES:
            q = te[universe_mask(te, universe)].copy()
            metric_rows.append({
                'year': int(year), 'fold_type': fold_type, 'model': model_name, 'universe': universe,
                'n': int(len(q)), 'large_n': int(q.is_large.sum()) if len(q) else 0,
                'large_rate': float(q.is_large.mean()) if len(q) else np.nan,
                'fail_rate': float(q.is_fail.mean()) if len(q) else np.nan,
                'auc': safe_auc(q.is_large, q.score) if len(q) else np.nan,
                'ap': safe_ap(q.is_large, q.score) if len(q) else np.nan,
                'score_lo': lo, 'score_hi': hi,
            })
            tier_rows.extend(summarize_router(te, year, fold_type, model_name, universe, lo, hi))

        if model is not None:
            for n, c in zip(names, model.coef_[0]):
                coef_rows.append({'year': int(year), 'fold_type': fold_type, 'model': model_name, 'feature': n, 'coef': float(c), 'abs_coef': float(abs(c))})
    return metric_rows, tier_rows, event_rows, coef_rows


def pooled_summary(events):
    rows = []
    for model_name in MODELS:
        m = events[(events.model == model_name) & (events.fold_type == 'INDEPENDENT_LOYO')].copy()
        for universe in UNIVERSES:
            q = m[universe_mask(m, universe)].copy()
            baseline_large = float(q.is_large.mean()) if len(q) else np.nan
            baseline_fail = float(q.is_fail.mean()) if len(q) else np.nan
            row = {
                'model': model_name, 'universe': universe, 'n': int(len(q)),
                'auc': safe_auc(q.is_large, q.score) if len(q) else np.nan,
                'ap': safe_ap(q.is_large, q.score) if len(q) else np.nan,
                'baseline_large_rate': baseline_large, 'baseline_fail_rate': baseline_fail,
            }
            for tier in ['ALLOW', 'REDUCE', 'SKIP']:
                g = q[q.route == tier]
                row[f'{tier.lower()}_n'] = int(len(g))
                row[f'{tier.lower()}_share'] = float(len(g) / len(q)) if len(q) else np.nan
                row[f'{tier.lower()}_large_rate'] = float(g.is_large.mean()) if len(g) else np.nan
                row[f'{tier.lower()}_fail_rate'] = float(g.is_fail.mean()) if len(g) else np.nan
            if row['allow_n'] and row['skip_n']:
                row['allow_minus_skip_large_pp'] = 100 * (row['allow_large_rate'] - row['skip_large_rate'])
                row['skip_minus_allow_fail_pp'] = 100 * (row['skip_fail_rate'] - row['allow_fail_rate'])
                row['allow_large_uplift_pp'] = 100 * (row['allow_large_rate'] - baseline_large)
            else:
                row['allow_minus_skip_large_pp'] = np.nan
                row['skip_minus_allow_fail_pp'] = np.nan
                row['allow_large_uplift_pp'] = np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def yearly_stability(tiers):
    rows = []
    t = tiers[tiers.fold_type == 'INDEPENDENT_LOYO'].copy()
    for model_name in MODELS:
        for universe in UNIVERSES:
            q = t[(t.model == model_name) & (t.universe == universe)]
            years = []
            for y in INDEPENDENT_YEARS:
                z = q[q.year == y].set_index('tier')
                if not {'ALLOW', 'SKIP'}.issubset(set(z.index)):
                    continue
                a, s = z.loc['ALLOW'], z.loc['SKIP']
                if int(a['n']) < 5 or int(s['n']) < 5:
                    continue
                years.append({
                    'year': y,
                    'large_order_ok': bool(a.large_rate > s.large_rate),
                    'fail_order_ok': bool(s.fail_rate > a.fail_rate),
                    'allow_uplift_ok': bool(a.large_uplift_pp > 0),
                    'allow_large_rate': float(a.large_rate), 'skip_large_rate': float(s.large_rate),
                    'allow_fail_rate': float(a.fail_rate), 'skip_fail_rate': float(s.fail_rate),
                })
            rows.append({
                'model': model_name, 'universe': universe, 'valid_years': len(years),
                'large_order_years': int(sum(v['large_order_ok'] for v in years)),
                'fail_order_years': int(sum(v['fail_order_ok'] for v in years)),
                'allow_uplift_years': int(sum(v['allow_uplift_ok'] for v in years)),
            })
    return pd.DataFrame(rows)


def choose_verdict(pooled, stability, metrics, tiers):
    p = pooled.set_index(['model', 'universe'])
    s = stability.set_index(['model', 'universe'])
    b = p.loc[('PRICE_REGIME_ONLY', 'ALL_BUY_BOS')]
    f = p.loc[('PRICE_REGIME_PLUS_NATIVE_FLOW', 'ALL_BUY_BOS')]
    sl = s.loc[('PRICE_REGIME_PLUS_NATIVE_FLOW', 'ALL_BUY_BOS')]

    auc_lift = float(f.auc - b.auc)
    router_ok = bool(
        np.isfinite(f.allow_large_uplift_pp) and f.allow_large_uplift_pp >= 5.0
        and np.isfinite(f.allow_minus_skip_large_pp) and f.allow_minus_skip_large_pp >= 8.0
        and np.isfinite(f.skip_minus_allow_fail_pp) and f.skip_minus_allow_fail_pp >= 5.0
        and int(sl.valid_years) >= 4
        and int(sl.large_order_years) >= 4
    )
    incremental_ok = bool(np.isfinite(auc_lift) and auc_lift >= 0.02)

    # Pseudo-forward directional check, not used to tune anything.
    ft = tiers[(tiers.fold_type == 'PSEUDO_FORWARD_2026') & (tiers.model == 'PRICE_REGIME_PLUS_NATIVE_FLOW') & (tiers.universe == 'ALL_BUY_BOS')]
    forward_ok = False
    if len(ft):
        z = ft.set_index('tier')
        if {'ALLOW', 'SKIP'}.issubset(set(z.index)) and int(z.loc['ALLOW', 'n']) >= 5 and int(z.loc['SKIP', 'n']) >= 5:
            forward_ok = bool(z.loc['ALLOW', 'large_rate'] > z.loc['SKIP', 'large_rate'])

    if router_ok and incremental_ok and forward_ok:
        verdict = 'NATIVE_FLOW_REGIME_ROUTER_REPLICATES_WITH_INCREMENTAL_EDGE'
    elif router_ok and incremental_ok:
        verdict = 'NATIVE_FLOW_REGIME_ROUTER_REPLICATES_BUT_2026_FORWARD_WEAK'
    elif router_ok:
        verdict = 'REGIME_ROUTER_WORKS_BUT_NATIVE_FLOW_INCREMENTALITY_IS_WEAK'
    elif incremental_ok:
        verdict = 'NATIVE_FLOW_ADDS_RANK_INFORMATION_BUT_ROUTER_IS_NOT_STABLE'
    else:
        verdict = 'NO_ROBUST_NATIVE_FLOW_REGIME_ROUTER_EDGE'
    return verdict, auc_lift, forward_ok


def main():
    print('=' * 110)
    print(LAB)
    _, all_events, base, _ = lab14.build_broad_base()
    buy = clean_buy(base)
    print('TARGET: is_large = clean MFE >=2.5R within 32 M15 bars before structural SL (frozen lineage).')
    print('CAUSALITY: every regime/flow input ends at i-1; BOS candle and post-BOS data excluded from predictors.')
    print('PRIMARY: ALL BUY BOS. Router = ALLOW top train-score tercile / REDUCE middle / SKIP bottom.')
    print('NO SEARCH: fixed L2 logistic, fixed C=0.35, fixed feature families, fixed interaction surface, fixed terciles.')
    print(f'BUY_EVENTS={len(buy)} ALL_EVENTS={len(all_events)}')

    metric_rows, tier_rows, event_rows, coef_rows = [], [], [], []
    for test_year in INDEPENDENT_YEARS:
        train = buy[buy.year.isin([y for y in INDEPENDENT_YEARS if y != test_year])].copy()
        test = buy[buy.year == test_year].copy()
        a, b, c, d = evaluate_fold(train, test, test_year, 'INDEPENDENT_LOYO')
        metric_rows += a; tier_rows += b; event_rows += c; coef_rows += d

    train_ind = buy[buy.year.isin(INDEPENDENT_YEARS)].copy()
    for year, fold_type in [(DISCOVERY_DIAGNOSTIC_YEAR, 'DISCOVERY_2021_DIAGNOSTIC'), (FORWARD_YEAR, 'PSEUDO_FORWARD_2026')]:
        test = buy[buy.year == year].copy()
        a, b, c, d = evaluate_fold(train_ind, test, year, fold_type)
        metric_rows += a; tier_rows += b; event_rows += c; coef_rows += d

    metrics = pd.DataFrame(metric_rows)
    tiers = pd.DataFrame(tier_rows)
    events = pd.concat(event_rows, ignore_index=True)
    coefs = pd.DataFrame(coef_rows)
    pooled = pooled_summary(events)
    stability = yearly_stability(tiers)
    verdict_class, auc_lift, forward_ok = choose_verdict(pooled, stability, metrics, tiers)

    primary = pooled[(pooled.model == 'PRICE_REGIME_PLUS_NATIVE_FLOW') & (pooled.universe == 'ALL_BUY_BOS')].iloc[0].to_dict()
    baseline = pooled[(pooled.model == 'PRICE_REGIME_ONLY') & (pooled.universe == 'ALL_BUY_BOS')].iloc[0].to_dict()
    forward = tiers[(tiers.fold_type == 'PSEUDO_FORWARD_2026') & (tiers.model == 'PRICE_REGIME_PLUS_NATIVE_FLOW') & (tiers.universe == 'ALL_BUY_BOS')].to_dict(orient='records')
    discovery = tiers[(tiers.fold_type == 'DISCOVERY_2021_DIAGNOSTIC') & (tiers.model == 'PRICE_REGIME_PLUS_NATIVE_FLOW') & (tiers.universe == 'ALL_BUY_BOS')].to_dict(orient='records')

    verdict = {
        'lab': LAB,
        'target': 'clean MFE >=2.5R within 32 M15 bars before structural SL',
        'primary_universe': 'ALL_BUY_BOS',
        'router': 'ALLOW top train-score tercile / REDUCE middle / SKIP bottom',
        'models': MODELS,
        'causality': 'all predictors end at i-1; BOS candle/post-BOS excluded',
        'independent_years': INDEPENDENT_YEARS,
        'discovery_diagnostic_year': DISCOVERY_DIAGNOSTIC_YEAR,
        'pseudo_forward_year': FORWARD_YEAR,
        'no_search_policy': 'fixed L2 logistic C=0.35; frozen feature families/interactions/terciles; no threshold or hyperparameter rescue',
        'price_regime_only_pooled': baseline,
        'native_flow_router_pooled': primary,
        'native_flow_auc_lift_vs_price_regime': auc_lift,
        'yearly_stability': stability.to_dict(orient='records'),
        'discovery_2021_router': discovery,
        'pseudo_forward_2026_router': forward,
        'pseudo_forward_direction_ok': bool(forward_ok),
        'verdict_class': verdict_class,
        'warning': 'Research routing study only; no execution-cost or prop-EA admission claim.',
    }

    metrics.to_csv(OUT / 'lab015_fold_metrics.csv', index=False)
    tiers.to_csv(OUT / 'lab015_router_tiers.csv', index=False)
    events.to_csv(OUT / 'lab015_oof_events.csv', index=False)
    pooled.to_csv(OUT / 'lab015_pooled_summary.csv', index=False)
    stability.to_csv(OUT / 'lab015_yearly_stability.csv', index=False)
    coefs.to_csv(OUT / 'lab015_model_coefficients.csv', index=False)
    with open(OUT / 'lab015_verdict.json', 'w', encoding='utf-8') as f:
        json.dump(verdict, f, indent=2, default=float)

    print('\nPOOLED')
    print(pooled.to_string(index=False))
    print('\nSTABILITY')
    print(stability.to_string(index=False))
    print('\n2021 / 2026 ROUTER')
    print(tiers[(tiers.fold_type != 'INDEPENDENT_LOYO') & (tiers.model == 'PRICE_REGIME_PLUS_NATIVE_FLOW')].to_string(index=False))
    print('\nVERDICT', verdict_class)


if __name__ == '__main__':
    main()
