#!/usr/bin/env python3
"""Audit-fixed runner for BTC_PAXG_CROSS_ASSET_DIVERGENCE_AND_RESPONSE_LAB_001.

The frozen research design and data are unchanged. This wrapper corrects one
reporting bug in v1: scalar model gates must explicitly select PRIMARY=4h
rather than taking the first horizon row from the metrics table.
"""
from __future__ import annotations
import numpy as np
import run_lab as lab


def verdict_fixed(e, mm, s):
    def g(sp, mo, c):
        q = mm[(mm.split == sp) & (mm.model == mo) & (mm.horizon == lab.PRIMARY)]
        if len(q) != 1:
            raise RuntimeError(f"Expected one primary metric row: {sp=} {mo=} {lab.PRIMARY=}; got {len(q)}")
        return float(q.iloc[0][c])

    a25 = g('BRIDGE_2025', 'BTC_PLUS_PAXG', 'auc') - g('BRIDGE_2025', 'BTC_ONLY', 'auc')
    a26 = g('OOS_2026', 'BTC_PLUS_PAXG', 'auc') - g('OOS_2026', 'BTC_ONLY', 'auc')
    bd = g('OOS_2026', 'BTC_ONLY', 'brier') - g('OOS_2026', 'BTC_PLUS_PAXG', 'brier')

    o = s[s.split == 'OOS_2026']
    top = o[o.aug_top20]
    base = o[f'cont_win_{lab.PRIMARY}'].mean()
    tw = top[f'cont_win_{lab.PRIMARY}'].mean()
    tm, tl, th = lab.ci(top[f'cont_{lab.PRIMARY}'])

    def bm(sp, state):
        q = e[(e.split == sp) & (e.paxg_state == state)]
        return len(q), q[f'cont_{lab.PRIMARY}'].mean()

    n25, i25 = bm('BRIDGE_2025', 'INVERSE')
    n26, i26 = bm('OOS_2026', 'INVERSE')
    all25 = e[e.split == 'BRIDGE_2025'][f'cont_{lab.PRIMARY}'].mean()
    all26 = e[e.split == 'OOS_2026'][f'cont_{lab.PRIMARY}'].mean()
    mech = np.isfinite(i25) and np.isfinite(i26) and (i25 - all25) * (i26 - all26) > 0

    gates = {
        'oos_events_ge_100': len(o) >= 100,
        'paxg_auc_delta_2026_ge_0.02': a26 >= .02,
        'paxg_auc_delta_bridge_positive': a25 > 0,
        'oos_brier_improves': bd > 0,
        'oos_top20_lift_ge_0.05': (tw - base) >= .05 and len(top) >= 20,
        'oos_top20_mean_positive': tm > 0,
        'mechanism_transfer_same_sign': bool(mech),
    }
    n = sum(gates.values())
    v = ('PASS_INCREMENTAL_CONTEXT' if n == len(gates)
         else ('WATCH_WEAK_INCREMENTAL_CONTEXT' if n >= 4 and gates['oos_events_ge_100']
               else 'FAIL_NO_ROBUST_INCREMENTAL_CONTEXT'))
    return dict(
        verdict=v,
        gates_passed=n,
        gates_total=len(gates),
        gates=gates,
        auc_delta_2025=a25,
        auc_delta_2026=a26,
        brier_improvement_2026=bd,
        oos_base_cont_win_rate=base,
        oos_top20_cont_win_rate=tw,
        oos_top20_lift=tw-base,
        oos_top20_n=len(top),
        oos_top20_mean_cont_return=tm,
        oos_top20_mean_ci=[tl, th],
        inverse_bridge_n=n25,
        inverse_oos_n=n26,
        inverse_bridge_mean=i25,
        inverse_oos_mean=i26,
        audit_fix='v2_primary_horizon_explicit',
    )


lab.verdict = verdict_fixed

if __name__ == '__main__':
    lab.main()
