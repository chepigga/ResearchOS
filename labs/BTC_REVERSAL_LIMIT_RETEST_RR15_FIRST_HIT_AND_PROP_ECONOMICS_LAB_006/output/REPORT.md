# BTC_REVERSAL_LIMIT_RETEST_RR15_FIRST_HIT_AND_PROP_ECONOMICS_LAB_006

**Verdict:** **PASS_PROP_ECONOMICS_SCREEN**

Role: frozen LAB005 limit-entry first-hit / prop-economics screen; not a live strategy.

## Frozen setup
- Selector/entry: exact LAB005 REV selector + `LIMIT_R0.50_T60`.
- 1R = 1.00 × parent event M15 range from filled limit.
- Primary TP = 1.5R; secondary audit = 2.0R.
- Ambiguous same M15 SL+TP = SL-first.
- Primary cost stress = 5 bps round trip; 0/2/10 bps are sensitivity.
- Frozen router q80: **0.324358**.

## Primary RR1.5 / 5bps

| Split | N | TP | SL | TIME | Net EV R | PF | Cum R | Max DD R | Max consec L | MFE R | MAE R | 0.5% eq return | 0.5% max DD | Max overlap | Risk load |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BRIDGE_2025 | 18 | 55.6% | 44.4% | 0.0% | +0.276 | 1.556 | +4.96 | 4.06 | 3 | 1.53 | 0.78 | +2.47% | 2.02% | 1 | 0.50% |
| DEV_2021_2024 | 77 | 41.6% | 54.5% | 3.9% | +0.029 | 1.050 | +2.21 | 12.52 | 5 | 1.30 | 1.07 | +0.97% | 6.14% | 2 | 1.00% |
| OOS_2026 | 14 | 64.3% | 35.7% | 0.0% | +0.528 | 2.362 | +7.39 | 2.28 | 2 | 1.44 | 0.95 | +3.73% | 1.14% | 1 | 0.50% |

## Cost sensitivity — RR1.5

| Split | Cost | Net EV R | PF | Cum R |
|---|---:|---:|---:|---:|
| BRIDGE_2025 | 0 bps | +0.389 | 1.875 | +7.00 |
| BRIDGE_2025 | 2 bps | +0.344 | 1.739 | +6.18 |
| BRIDGE_2025 | 5 bps | +0.276 | 1.556 | +4.96 |
| BRIDGE_2025 | 10 bps | +0.162 | 1.296 | +2.92 |
| DEV_2021_2024 | 0 bps | +0.091 | 1.167 | +7.03 |
| DEV_2021_2024 | 2 bps | +0.066 | 1.119 | +5.10 |
| DEV_2021_2024 | 5 bps | +0.029 | 1.050 | +2.21 |
| DEV_2021_2024 | 10 bps | -0.034 | 0.945 | -2.60 |
| OOS_2026 | 0 bps | +0.607 | 2.700 | +8.50 |
| OOS_2026 | 2 bps | +0.575 | 2.558 | +8.06 |
| OOS_2026 | 5 bps | +0.528 | 2.362 | +7.39 |
| OOS_2026 | 10 bps | +0.449 | 2.074 | +6.28 |

## RR2.0 audit at 5bps

| Split | N | TP | SL | TIME | Net EV R | PF | Cum R |
|---|---:|---:|---:|---:|---:|---:|---:|
| BRIDGE_2025 | 18 | 50.0% | 44.4% | 5.6% | +0.423 | 1.816 | +7.61 |
| DEV_2021_2024 | 77 | 35.1% | 61.0% | 3.9% | +0.042 | 1.064 | +3.21 |
| OOS_2026 | 14 | 57.1% | 42.9% | 0.0% | +0.635 | 2.358 | +8.89 |

## Gates
- PASS — `bridge_filled_ge_15`
- PASS — `oos_filled_ge_10`
- PASS — `bridge_net_ev_positive`
- PASS — `oos_net_ev_positive`
- PASS — `bridge_pf_gt_1`
- PASS — `oos_pf_gt_1`
- PASS — `oos_max_consecutive_losses_le_8`
- PASS — `oos_equity_maxdd_050_lt_5pct`
- PASS — `oos_overlap_risk_050_lt_4pct`

**Score 9/9 -> PASS_PROP_ECONOMICS_SCREEN**

## Caveats

- 5 bps is a frozen stress assumption, not a claim about the exact current FTMO BTC CFD all-in cost.
- Closed-equity DD understates a prop firm's floating intraday DD. Max concurrent initial risk is reported separately.
- Sample sizes remain small, especially 2026; this LAB screens monetization geometry, not final production readiness.
- No 2026 tuning of selector, limit distance, TTL, SL distance, RR, or cost gate is authorized after this run.
