#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = 'CROSS_MARKET_CAUSAL_CONTEXT_DIRECTION_COMPATIBILITY_INTERACTION_LAB_003'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAB002_PATH = ROOT / 'labs' / 'CROSS_MARKET_CAUSAL_CONTEXT_CONTINUOUS_SCORE_INTERACTION_LAB_002' / 'run_lab.py'
BOOT_N = 5000
SEED = 2026090903
BTC_THRESHOLD = 0.525
XAU_THRESHOLD = 0.55
BTC_PERIODS = ['2021','2022','2023','2024','2025_H1','2025_H2','2026_JAN_JUL']
XAU_PERIODS = ['2022','2023','2024','2025','2026']


def load_lab002():
    spec = importlib.util.spec_from_file_location('lab002', LAB002_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def finite_mean(s: pd.Series) -> float:
    v = pd.to_numeric(s, errors='coerce').dropna()
    return float(v.mean()) if len(v) else np.nan


def cell_mean(d: pd.DataFrame, outcome: str, high: bool, compat: str):
    g = d[(d['is_high'] == high) & d['bias_compat_label'].eq(compat)]
    v = pd.to_numeric(g[outcome], errors='coerce').dropna()
    return int(len(v)), (float(v.mean()) if len(v) else np.nan)


def primary_stats(d: pd.DataFrame, outcome: str, raw_col: str | None = None):
    z = d.dropna(subset=['context_score', outcome]).copy()
    cells = {}
    for high, hname in [(True,'HIGH'), (False,'NON_HIGH')]:
        for comp in ['ALIGNED','OPPOSED','NEUTRAL']:
            n, m = cell_mean(z, outcome, high, comp)
            cells[f'{hname}_{comp}'] = {'n': n, 'mean': m}
            if raw_col and raw_col in z.columns:
                g = z[(z['is_high'] == high) & z['bias_compat_label'].eq(comp)]
                cells[f'{hname}_{comp}']['mean_raw_R'] = finite_mean(g[raw_col])
    ha = cells['HIGH_ALIGNED']['mean']; ho = cells['HIGH_OPPOSED']['mean']
    na = cells['NON_HIGH_ALIGNED']['mean']; no = cells['NON_HIGH_OPPOSED']['mean']
    hp = ha - ho if np.isfinite(ha) and np.isfinite(ho) else np.nan
    nprem = na - no if np.isfinite(na) and np.isfinite(no) else np.nan
    interaction = hp - nprem if np.isfinite(hp) and np.isfinite(nprem) else np.nan
    return {
        'cells': cells,
        'high_premium': float(hp) if np.isfinite(hp) else np.nan,
        'nonhigh_premium': float(nprem) if np.isfinite(nprem) else np.nan,
        'interaction': float(interaction) if np.isfinite(interaction) else np.nan,
    }


def weekly_bootstrap(d: pd.DataFrame, time_col: str, outcome: str):
    z = d.dropna(subset=[time_col, outcome, 'context_score']).copy()
    z = z[z.bias_compat_label.isin(['ALIGNED','OPPOSED'])].copy()
    t = pd.to_datetime(z[time_col], errors='coerce', utc=True)
    z = z.loc[t.notna()].copy(); t = t.loc[t.notna()]
    z['_week'] = t.dt.to_period('W-SUN').astype(str).values
    z['_y'] = pd.to_numeric(z[outcome], errors='coerce')
    z = z.dropna(subset=['_y'])

    # HA, HO, NA, NO -> count/sum per week.
    rows = []
    for _, g in z.groupby('_week', sort=True):
        rec = []
        for high, comp in [(True,'ALIGNED'),(True,'OPPOSED'),(False,'ALIGNED'),(False,'OPPOSED')]:
            v = g.loc[(g.is_high == high) & g.bias_compat_label.eq(comp), '_y'].to_numpy(float)
            rec.extend([len(v), float(v.sum())])
        rows.append(rec)
    a = np.asarray(rows, float)
    m = len(a); rng = np.random.default_rng(SEED)
    hp = np.full(BOOT_N, np.nan); inter = np.full(BOOT_N, np.nan)
    for k in range(BOOT_N):
        ix = rng.integers(0, m, size=m)
        s = a[ix].sum(axis=0)
        means = []
        for j in range(0, 8, 2):
            n, sm = s[j], s[j+1]
            means.append(sm/n if n > 0 else np.nan)
        ha, ho, na, no = means
        if np.isfinite(ha) and np.isfinite(ho): hp[k] = ha - ho
        if np.all(np.isfinite(means)): inter[k] = (ha-ho) - (na-no)
    hp = hp[np.isfinite(hp)]; inter = inter[np.isfinite(inter)]
    return {
        'weeks': int(m), 'draws': BOOT_N,
        'high_premium_ci_lo': float(np.quantile(hp,.025)) if len(hp) else np.nan,
        'high_premium_ci_hi': float(np.quantile(hp,.975)) if len(hp) else np.nan,
        'high_premium_p_positive': float(np.mean(hp > 0)) if len(hp) else np.nan,
        'interaction_ci_lo': float(np.quantile(inter,.025)) if len(inter) else np.nan,
        'interaction_ci_hi': float(np.quantile(inter,.975)) if len(inter) else np.nan,
        'interaction_p_positive': float(np.mean(inter > 0)) if len(inter) else np.nan,
    }


def high_premium_for(g: pd.DataFrame, outcome: str):
    hi = g[g.is_high]
    a = pd.to_numeric(hi.loc[hi.bias_compat_label.eq('ALIGNED'), outcome], errors='coerce').dropna()
    o = pd.to_numeric(hi.loc[hi.bias_compat_label.eq('OPPOSED'), outcome], errors='coerce').dropna()
    return {
        'aligned_n': int(len(a)), 'opposed_n': int(len(o)),
        'aligned_mean': float(a.mean()) if len(a) else np.nan,
        'opposed_mean': float(o.mean()) if len(o) else np.nan,
        'high_premium': float(a.mean()-o.mean()) if len(a) and len(o) else np.nan,
    }


def time_transfer(d: pd.DataFrame, period_col: str, periods: list[str], outcome: str, min_n: int):
    rows = []
    for p in periods:
        g = d[d[period_col].astype(str).eq(str(p))]
        x = high_premium_for(g, outcome)
        eligible = x['aligned_n'] >= min_n and x['opposed_n'] >= min_n
        rows.append({'period': str(p), 'n': int(len(g)), **x,
                     'eligible': bool(eligible),
                     'positive': bool(eligible and np.isfinite(x['high_premium']) and x['high_premium'] > 0)})
    return pd.DataFrame(rows)


def leave_one_period_out(d: pd.DataFrame, period_col: str, eligible_periods: list[str], outcome: str):
    rows = []
    for p in eligible_periods:
        g = d[~d[period_col].astype(str).eq(str(p))]
        s = primary_stats(g, outcome)
        ok = bool(np.isfinite(s['high_premium']) and s['high_premium'] > 0 and
                  np.isfinite(s['interaction']) and s['interaction'] > 0)
        rows.append({'left_out': str(p), 'n': int(len(g)),
                     'high_premium': s['high_premium'], 'interaction': s['interaction'], 'both_positive': ok})
    return pd.DataFrame(rows)


def categorical_transfer(d: pd.DataFrame, group_col: str, outcome: str, min_n: int):
    rows = []
    for key, g in d.groupby(group_col, dropna=False, sort=True):
        x = high_premium_for(g, outcome)
        eligible = x['aligned_n'] >= min_n and x['opposed_n'] >= min_n
        rows.append({group_col: key, 'n': int(len(g)), **x,
                     'eligible': bool(eligible),
                     'positive': bool(eligible and np.isfinite(x['high_premium']) and x['high_premium'] > 0)})
    return pd.DataFrame(rows)


def mechanic_transfer(d: pd.DataFrame, outcome: str, min_n: int):
    flags = sorted(c for c in d.columns if c.startswith('f_'))
    rows = []
    for c in flags:
        g = d[pd.to_numeric(d[c], errors='coerce').fillna(0).astype(float) > 0]
        x = high_premium_for(g, outcome)
        eligible = x['aligned_n'] >= min_n and x['opposed_n'] >= min_n
        rows.append({'mechanic': c, 'n': int(len(g)), **x,
                     'eligible': bool(eligible),
                     'positive': bool(eligible and np.isfinite(x['high_premium']) and x['high_premium'] > 0)})
    return pd.DataFrame(rows)


def high_compat_table(d: pd.DataFrame, outcome: str, raw_col: str | None = None):
    rows = []
    for high, hname in [(False,'NON_HIGH'),(True,'HIGH')]:
        for comp in ['ALIGNED','NEUTRAL','OPPOSED']:
            g = d[(d.is_high == high) & d.bias_compat_label.eq(comp)]
            v = pd.to_numeric(g[outcome], errors='coerce').dropna()
            r = {'context_band': hname, 'compat': comp, 'n': int(len(v)),
                 'mean_outcome': float(v.mean()) if len(v) else np.nan,
                 'p_positive': float((v > 0).mean()) if len(v) else np.nan}
            if raw_col and raw_col in g.columns:
                r['mean_raw_R'] = finite_mean(g[raw_col])
            rows.append(r)
    return pd.DataFrame(rows)


def evaluate_market(name: str, d: pd.DataFrame, time_col: str, outcome: str,
                    period_col: str, periods: list[str], threshold: float, min_period_n: int,
                    out: Path, raw_col: str | None = None):
    z = d.dropna(subset=['context_score', outcome]).copy()
    z['is_high'] = z.context_score > threshold
    stats = primary_stats(z, outcome, raw_col)
    boot = weekly_bootstrap(z, time_col, outcome)
    tr = time_transfer(z, period_col, periods, outcome, min_period_n)
    tr.to_csv(out / f'{name.lower()}_time_transfer.csv', index=False)
    eligible_periods = tr.loc[tr.eligible, 'period'].astype(str).tolist()
    lopo = leave_one_period_out(z, period_col, eligible_periods, outcome)
    lopo.to_csv(out / f'{name.lower()}_leave_one_period_out.csv', index=False)
    high_compat_table(z, outcome, raw_col).to_csv(out / f'{name.lower()}_context_x_compat.csv', index=False)

    eligible_n = int(tr.eligible.sum())
    positive_n = int(tr.positive.sum())
    positive_fraction = float(positive_n / eligible_n) if eligible_n else np.nan
    lopo_fraction = float(lopo.both_positive.mean()) if len(lopo) else np.nan

    gates = {
        'G1_high_premium_gt_zero': bool(np.isfinite(stats['high_premium']) and stats['high_premium'] > 0),
        'G2_boot_high_premium_ci_lo_gt_zero': bool(np.isfinite(boot.get('high_premium_ci_lo',np.nan)) and boot['high_premium_ci_lo'] > 0),
        'G3_interaction_gt_zero': bool(np.isfinite(stats['interaction']) and stats['interaction'] > 0),
        'G4_boot_interaction_ci_lo_gt_zero': bool(np.isfinite(boot.get('interaction_ci_lo',np.nan)) and boot['interaction_ci_lo'] > 0),
        'G5_time_transfer_75pct_min4': bool(eligible_n >= 4 and np.isfinite(positive_fraction) and positive_fraction >= .75),
        'G6_lopo_80pct_both_positive': bool(len(lopo) >= 4 and np.isfinite(lopo_fraction) and lopo_fraction >= .80),
    }
    extra = {}
    if name == 'XAU':
        tf = categorical_transfer(z, 'tf', outcome, 200); tf.to_csv(out/'xau_tf_transfer.csv', index=False)
        dr = categorical_transfer(z, 'dir', outcome, 200); dr.to_csv(out/'xau_direction_transfer.csv', index=False)
        mech = mechanic_transfer(z, outcome, 200); mech.to_csv(out/'xau_mechanic_transfer.csv', index=False)

        tf_e = tf[tf.eligible]; dr_e = dr[dr.eligible]; me = mech[mech.eligible]
        tf_pos = int(tf_e.positive.sum()); dr_pos = int(dr_e.positive.sum()); me_pos = int(me.positive.sum())
        me_frac = float(me_pos/len(me)) if len(me) else np.nan
        me_median = float(me.high_premium.median()) if len(me) else np.nan
        g7 = bool(len(tf_e) >= 3 and tf_pos >= 2)
        # Require both directions when both are eligible; if only one is eligible, gate fails prereg.
        g8 = bool(len(dr_e) == 2 and dr_pos == 2)
        g9 = bool(len(me) > 0 and np.isfinite(me_frac) and me_frac >= .70 and np.isfinite(me_median) and me_median > 0)
        gates.update({'G7_xau_tf_2of3_positive': g7,
                      'G8_xau_buy_sell_both_positive': g8,
                      'G9_xau_mechanics_70pct_median_positive': g9})
        extra = {
            'tf_eligible': int(len(tf_e)), 'tf_positive': tf_pos,
            'direction_eligible': int(len(dr_e)), 'direction_positive': dr_pos,
            'mechanics_total': int(len(mech)), 'mechanics_eligible': int(len(me)),
            'mechanics_positive': me_pos, 'mechanics_positive_fraction': me_frac,
            'mechanics_median_high_premium': me_median,
        }

    core_keys = [k for k in gates if k.startswith('G1_') or k.startswith('G2_') or k.startswith('G3_') or k.startswith('G4_') or k.startswith('G5_') or k.startswith('G6_')]
    core_pass = all(gates[k] for k in core_keys)
    all_pass = all(gates.values())
    if all_pass:
        verdict = 'DIRECTION_CONTEXT_INTERACTION_SUPPORTED_DISCOVERY_ONLY'
    elif gates['G1_high_premium_gt_zero'] and gates['G3_interaction_gt_zero']:
        verdict = 'MIXED_DIRECTION_CONTEXT_INTERACTION'
    else:
        verdict = 'DIRECTION_CONTEXT_INTERACTION_NOT_SUPPORTED'

    return z, {
        'market': name, 'n': int(len(z)), 'outcome': outcome, 'high_threshold': threshold,
        **stats, 'bootstrap': boot,
        'eligible_time_periods': eligible_n, 'positive_time_periods': positive_n,
        'positive_time_fraction': positive_fraction,
        'lopo_runs': int(len(lopo)), 'lopo_both_positive_fraction': lopo_fraction,
        'core_pass': bool(core_pass), 'gates': gates, 'extra_transfer': extra, 'verdict': verdict,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xau-m1', required=True)
    ap.add_argument('--xau-pool', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    lab002 = load_lab002()
    router = lab002.load_router_module()

    btc = pd.read_csv(lab002.BTC_INPUT)
    if len(btc) != 327:
        raise RuntimeError(f'BTC frozen parity failed: {len(btc)} != 327')
    btc['entry_time'] = pd.to_datetime(btc.entry_time, utc=True, errors='coerce')
    btc['net_r_5bps'] = pd.to_numeric(btc.net_r_5bps, errors='coerce')
    btc = lab002.add_continuous_fields(btc, pd.Series(-1, index=btc.index))
    _, btc_summary = evaluate_market('BTC', btc, 'entry_time', 'net_r_5bps', 'period', BTC_PERIODS,
                                     BTC_THRESHOLD, 5, out)

    xau, xau_meta = lab002.build_xau_join(Path(a.xau_m1), Path(a.xau_pool), router)
    if len(xau) != 263405:
        raise RuntimeError(f'XAU frozen causal parity failed: {len(xau)} != 263405')
    _, xau_summary = evaluate_market('XAU', xau, 'available_event_time', 'excess', 'year', XAU_PERIODS,
                                     XAU_THRESHOLD, 200, out, raw_col='R')

    supported = [btc_summary['verdict'] == 'DIRECTION_CONTEXT_INTERACTION_SUPPORTED_DISCOVERY_ONLY',
                 xau_summary['verdict'] == 'DIRECTION_CONTEXT_INTERACTION_SUPPORTED_DISCOVERY_ONLY']
    if all(supported):
        verdict = 'CROSS_MARKET_DIRECTION_CONTEXT_INTERACTION_SUPPORTED_DISCOVERY_ONLY'
    elif (btc_summary['verdict'] == 'DIRECTION_CONTEXT_INTERACTION_NOT_SUPPORTED' and
          xau_summary['verdict'] == 'DIRECTION_CONTEXT_INTERACTION_NOT_SUPPORTED'):
        verdict = 'REJECT_CROSS_MARKET_DIRECTION_CONTEXT_INTERACTION'
    else:
        verdict = 'MIXED_CROSS_MARKET_DIRECTION_CONTEXT_INTERACTION'

    summary = {
        'lab': LAB,
        'status': 'REUSED_HISTORY_PREREGISTERED_INTERACTION_AUDIT',
        'verdict': verdict,
        'frozen_score': '(EXPANSION+PULLBACK-REVERSAL-RANGE)/200',
        'primary_interaction': '(HIGH_ALIGNED-HIGH_OPPOSED)-(NONHIGH_ALIGNED-NONHIGH_OPPOSED)',
        'btc': btc_summary, 'xau': xau_summary, 'xau_meta': xau_meta,
        'promotion_authorized': False,
    }
    (out/'summary.json').write_text(json.dumps(summary, indent=2, default=str))

    lines = [f'# {LAB}', '', f'**Verdict: {verdict}**', '',
             '> Preregistered reused-history interaction audit. No live sizing promotion is authorized.', '',
             '## Frozen test', '',
             '- `C = (Expansion + Pullback - Reversal - Range) / 200`',
             f'- BTC HIGH: `C > {BTC_THRESHOLD}`; XAU HIGH: `C > {XAU_THRESHOLD}`',
             '- Primary: `(HIGH A-O) - (NON_HIGH A-O)`', '',
             '| Market | N | HIGH A | HIGH O | HIGH premium | NONHIGH premium | Interaction | HP 95% CI | Interaction 95% CI | Time + | LOPO + | Verdict |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for s in [btc_summary, xau_summary]:
        c=s['cells']; b=s['bootstrap']
        lines.append(
            f"| {s['market']} | {s['n']:,} | {c['HIGH_ALIGNED']['mean']:+.4f} (n={c['HIGH_ALIGNED']['n']}) | "
            f"{c['HIGH_OPPOSED']['mean']:+.4f} (n={c['HIGH_OPPOSED']['n']}) | {s['high_premium']:+.4f} | "
            f"{s['nonhigh_premium']:+.4f} | {s['interaction']:+.4f} | "
            f"[{b.get('high_premium_ci_lo',np.nan):+.4f}, {b.get('high_premium_ci_hi',np.nan):+.4f}] | "
            f"[{b.get('interaction_ci_lo',np.nan):+.4f}, {b.get('interaction_ci_hi',np.nan):+.4f}] | "
            f"{s['positive_time_periods']}/{s['eligible_time_periods']} | {s['lopo_both_positive_fraction']:.0%} | {s['verdict']} |")
    lines += ['', '## Gates', '']
    for s in [btc_summary, xau_summary]:
        lines.append(f"### {s['market']}")
        for k,v in s['gates'].items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
        if s['market']=='XAU':
            e=s['extra_transfer']
            lines += [f"- TF positive: {e['tf_positive']}/{e['tf_eligible']}",
                      f"- Directions positive: {e['direction_positive']}/{e['direction_eligible']}",
                      f"- Mechanics positive: {e['mechanics_positive']}/{e['mechanics_eligible']} ({e['mechanics_positive_fraction']:.1%} if eligible)",
                      f"- Median mechanic HIGH premium: {e['mechanics_median_high_premium']:+.5f}"]
        lines.append('')
    lines += ['## Interpretation', '',
              '- A positive HIGH premium alone is insufficient: the difference-in-differences interaction must also survive weekly cluster bootstrap.',
              '- XAU must additionally transfer across TF, BUY/SELL, and the frozen mechanic family rather than being carried by one subgroup.',
              '- This is reused history. Even a full pass is discovery-grade and requires fresh sequential/OOS replication before risk modulation.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print((out/'REPORT.md').read_text())
    print((out/'summary.json').read_text())


if __name__ == '__main__':
    main()
