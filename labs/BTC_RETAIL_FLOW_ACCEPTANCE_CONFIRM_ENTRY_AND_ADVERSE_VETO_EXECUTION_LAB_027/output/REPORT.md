# BTC_RETAIL_FLOW_ACCEPTANCE_CONFIRM_ENTRY_AND_ADVERSE_VETO_EXECUTION_LAB_027

**Verdict: WATCH_ACCEPTANCE_DRIFT_SURVIVES_BUT_BOUNDED_EXECUTION_WEAK — 10/14 scored gates**

## Frozen parity
- lineage rows: **3209**, pre-Aug **3196**
- timestamp parity: **100.00%**
- acceptance-threshold parity max abs error: **0.00000000**
- entry-bar ambiguous ACCEPT events: **0**

## Pre-Aug policy economics

| Policy | Signals | Trades | Util | EV/trade | Policy EV/signal | Cum ATR | PF | DD ATR | Stop | Hold h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ACCEPT_BOUNDED | 3196 | 1496 | 0.468 | 0.196 | 0.092 | 293.697 | 1.172 | 67.496 | 0.680 | 4.500 |
| ACCEPT_NOSTOP | 3196 | 1496 | 0.468 | 0.379 | 0.178 | 567.625 | 1.222 | 139.590 | — | 4.500 |
| IMMEDIATE_BOUNDED | 3196 | 3196 | 1.000 | 0.099 | 0.099 | 316.512 | 1.085 | 167.961 | 0.693 | — |
| IMMEDIATE_NOSTOP | 3196 | 3196 | 1.000 | 0.193 | 0.193 | 616.268 | 1.102 | 231.431 | — | — |

## Primary bounded ACCEPT by window

| Window | Signals | Trades | Util | EV/trade | Policy EV/signal | Cum ATR | PF | DD | Stop | L/S |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 631 | 322 | 0.510 | 0.316 | 0.161 | 101.700 | 1.299 | 40.919 | 0.652 | 162/160 |
| 2022 | 529 | 268 | 0.507 | 0.377 | 0.191 | 101.029 | 1.345 | 50.385 | 0.660 | 136/132 |
| 2023 | 572 | 265 | 0.463 | 0.244 | 0.113 | 64.552 | 1.206 | 40.278 | 0.683 | 133/132 |
| 2024 | 583 | 253 | 0.434 | 0.128 | 0.056 | 32.467 | 1.113 | 33.490 | 0.676 | 122/131 |
| 2025_H1 | 256 | 128 | 0.500 | 0.312 | 0.156 | 39.933 | 1.271 | 37.187 | 0.688 | 68/60 |
| 2025_H2 | 309 | 132 | 0.427 | -0.199 | -0.085 | -26.231 | 0.848 | 62.931 | 0.765 | 57/75 |
| 2026_JAN_JUL | 316 | 128 | 0.405 | -0.154 | -0.063 | -19.754 | 0.873 | 39.351 | 0.703 | 58/70 |
| AUG2026_REUSED_AUDIT | 13 | 5 | 0.385 | -1.409 | -0.542 | -7.043 | 0.052 | 7.043 | 0.800 | 5/0 |
| ALL_PRE_AUG | 3196 | 1496 | 0.468 | 0.196 | 0.092 | 293.697 | 1.172 | 67.496 | 0.680 | 736/760 |
| POOLED_RECENT | 625 | 260 | 0.416 | -0.177 | -0.074 | -45.985 | 0.860 | 67.496 | 0.735 | 115/145 |

## Primary bounded ACCEPT pre-Aug by side

| Side | Signals | Trades | EV/trade | Policy EV/signal | Cum ATR | PF | DD | Stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | 1563 | 736 | 0.371 | 0.175 | 272.901 | 1.324 | 46.670 | 0.682 |
| SHORT | 1633 | 760 | 0.027 | 0.013 | 20.796 | 1.024 | 126.422 | 0.679 |

## 7d cluster bootstrap
- clusters: **1**, draws: **5000**
- ACCEPT bounded policy EV/signal minus immediate bounded: **-0.007 ATR**, 95% CI **[-0.007, -0.007]**

## Gates
- PASS — `exact_lab026_lineage_and_parity`
- PASS — `accept_executable_count_ge_1000`
- PASS — `signal_utilization_ge_35pct`
- PASS — `bounded_accept_ev_trade_positive`
- FAIL — `bounded_accept_pf_gt_1_20`
- PASS — `bounded_accept_policy_ev_signal_positive`
- FAIL — `bounded_accept_policy_ev_gt_immediate`
- PASS — `bounded_accept_dd_le_immediate`
- PASS — `nostop_accept_ev_trade_positive`
- PASS — `stress_2022_short_n80_and_cum_positive`
- FAIL — `pooled_recent_cum_positive`
- PASS — `long_bounded_accept_ev_positive`
- PASS — `short_bounded_accept_ev_positive`
- FAIL — `bootstrap_accept_minus_immediate_ci_lower_gt_zero`

## August 2026 reused audit
Reported separately; scientific verdict cannot be rescued or failed by August. Trades=5, Cum=-7.043 ATR, EV/trade=-1.409.

## Guardrail
Primary is bounded: ACCEPT_FIRST only, market entry at frozen +0.5 ATR threshold, emergency SL 1.5 ATR from entry, no TP, original signal +12h time exit, 5 bps RT cost. ADVERSE_FIRST/AMBIGUOUS/NONE = veto. No threshold/stop/horizon optimization. This remains reused research lineage; no full floating-equity FTMO daily-DD simulation. Live allocation = **0**.
