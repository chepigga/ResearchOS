# BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044

**Verdict: PASS_SHORT_HIGH_RESPONSE_BOUNDED_EXECUTION_BRIDGE — 20/22**

## Frozen execution lineage
- exact HIGH_RESPONSE SHORT pre-Aug: **475**; August audit: **1**
- LAB035 timestamp/state parity: **100.0%**
- M15 path coverage TOUCH/ACCEPT-eligible: **100.0% / 100.0%**

## Policy grid (TP=1.5R, cost=5bps RT)

| Clock | SL ATR | Trades | TP | SL | Time | EV R | PF | EV/original | CumR | MaxDD R | DD@0.25% | Winner killed | MAE ATR | MFE ATR | Max conc | Risk conc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TOUCH | 1.5 | 475 | 0.337 | 0.634 | 0.029 | -0.230 | 0.676 | -0.230 | -109.2 | 114.29 | 28.57% | 0.502 | 2.59 | 3.37 | 1 | 0.25% |
| TOUCH | 2.0 | 475 | 0.371 | 0.554 | 0.076 | -0.074 | 0.879 | -0.074 | -35.3 | 60.54 | 15.14% | 0.355 | 2.59 | 3.37 | 1 | 0.25% |
| TOUCH | 2.5 | 475 | 0.356 | 0.469 | 0.175 | +0.012 | 1.023 | +0.012 | +5.8 | 29.09 | 7.27% | 0.247 | 2.59 | 3.37 | 1 | 0.25% |
| TOUCH | 3.0 | 475 | 0.331 | 0.396 | 0.274 | +0.072 | 1.152 | +0.072 | +34.0 | 17.83 | 4.46% | 0.175 | 2.59 | 3.37 | 1 | 0.25% |
| ACCEPT | 1.5 | 327 | 0.401 | 0.557 | 0.043 | -0.056 | 0.910 | -0.039 | -18.4 | 24.79 | 6.20% | 0.395 | 2.23 | 3.15 | 1 | 0.25% |
| ACCEPT | 2.0 | 327 | 0.416 | 0.465 | 0.119 | +0.095 | 1.180 | +0.065 | +31.0 | 12.15 | 3.04% | 0.246 | 2.23 | 3.15 | 1 | 0.25% |
| ACCEPT | 2.5 | 327 | 0.367 | 0.419 | 0.214 | +0.086 | 1.176 | +0.059 | +28.2 | 11.44 | 2.86% | 0.162 | 2.23 | 3.15 | 1 | 0.25% |
| ACCEPT | 3.0 | 327 | 0.330 | 0.361 | 0.309 | +0.100 | 1.225 | +0.069 | +32.8 | 9.71 | 2.43% | 0.108 | 2.23 | 3.15 | 1 | 0.25% |

## Cost sensitivity for preregistered 2.5 ATR policies

- ACCEPT 2.5: EV 0/5/10bps = **+0.148 / +0.086 / +0.024 R**
- TOUCH 2.5: EV 0/5/10bps = **+0.074 / +0.012 / -0.050 R**

## 2.5 ATR transfer (EV per original HIGH_RESPONSE signal)

| Clock | Slice | Original N | Trades | EV/original | Trade EV | PF | CumR |
|---|---|---:|---:|---:|---:|---:|---:|
| TOUCH | 2021 | 82 | 82 | +0.233 | +0.233 | 1.535 | +19.11 |
| TOUCH | 2022 | 79 | 79 | -0.149 | -0.149 | 0.753 | -11.75 |
| TOUCH | 2023 | 83 | 83 | -0.024 | -0.024 | 0.958 | -1.95 |
| TOUCH | 2024 | 94 | 94 | +0.033 | +0.033 | 1.063 | +3.12 |
| TOUCH | 2025_H1 | 46 | 46 | -0.215 | -0.215 | 0.636 | -9.89 |
| TOUCH | 2025_H2 | 44 | 44 | -0.067 | -0.067 | 0.883 | -2.96 |
| TOUCH | 2026_JAN_JUL | 47 | 47 | +0.214 | +0.214 | 1.427 | +10.08 |
| TOUCH | POOLED_RECENT | 91 | 91 | +0.078 | +0.078 | 1.145 | +7.12 |
| TOUCH | AUG_REUSED | 1 | 1 | -1.126 | -1.126 | 0.000 | -1.13 |
| ACCEPT | 2021 | 82 | 62 | +0.180 | +0.238 | 1.556 | +14.75 |
| ACCEPT | 2022 | 79 | 49 | -0.025 | -0.040 | 0.930 | -1.96 |
| ACCEPT | 2023 | 83 | 52 | -0.004 | -0.006 | 0.988 | -0.31 |
| ACCEPT | 2024 | 94 | 64 | +0.057 | +0.084 | 1.177 | +5.39 |
| ACCEPT | 2025_H1 | 46 | 32 | -0.080 | -0.114 | 0.795 | -3.66 |
| ACCEPT | 2025_H2 | 44 | 33 | +0.088 | +0.117 | 1.248 | +3.86 |
| ACCEPT | 2026_JAN_JUL | 47 | 35 | +0.216 | +0.290 | 1.631 | +10.16 |
| ACCEPT | POOLED_RECENT | 91 | 68 | +0.154 | +0.206 | 1.443 | +14.02 |
| ACCEPT | AUG_REUSED | 1 | 0 | +0.000 | +nan | nan | +0.00 |

## Gates
- PASS — `exact_high_response_preaug_n_475`
- PASS — `lab035_join_timestamp_state_parity_100pct`
- PASS — `m15_path_coverage_ge_99pct`
- PASS — `touch_trades_ge_450`
- PASS — `accept_trades_ge_300`
- PASS — `accept_winner_kill_monotonic_1_5_to_3`
- PASS — `touch_winner_kill_monotonic_1_5_to_3`
- PASS — `primary_accept_2_5_net_ev_positive`
- PASS — `primary_accept_2_5_pf_ge_1_10`
- PASS — `primary_accept_2_5_ev_per_original_ge_0_05`
- PASS — `primary_accept_2_5_dd_025_le_4pct`
- PASS — `primary_accept_2_5_concurrent_risk_le_2pct`
- PASS — `primary_accept_2_5_10bps_ev_positive`
- PASS — `primary_accept_2_5_2025h2_ev_per_original_positive`
- PASS — `primary_accept_2_5_2026_ev_per_original_positive`
- PASS — `primary_accept_2_5_pooled_recent_positive_n50`
- FAIL — `primary_accept_2_5_2022_stress_positive`
- PASS — `touch_2_5_net_ev_positive`
- FAIL — `touch_2_5_pf_ge_1_10`
- PASS — `touch_2_5_pooled_recent_ev_per_original_positive`
- PASS — `accept_ev_per_original_not_worse_touch_by_0_15`
- PASS — `august_not_used_for_selection`

## Guardrail
Frozen LAB043 SHORT HIGH_RESPONSE universe; same Binance USD-M M15 price lineage as LAB035. No signal/threshold/entry-price improvement after results. TOUCH same-bar ambiguity is SL-first; ACCEPT begins barrier checking on the next M15 bar. 5bps is a research friction assumption with 0/10bps sensitivity, not a claim of exact current FTMO BTC CFD costs. Reused historical execution research, not fresh OOS. Live allocation = **0**.
