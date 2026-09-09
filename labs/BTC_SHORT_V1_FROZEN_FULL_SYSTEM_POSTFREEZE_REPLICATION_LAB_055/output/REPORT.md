# BTC_SHORT_V1_FROZEN_FULL_SYSTEM_POSTFREEZE_REPLICATION_LAB_055

**Verdict: WATCH_POSTFREEZE_INSUFFICIENT_FRESH_TRADES — 12/13 gates**

## Frozen system
`FLOW SHORT → HIGH_RESPONSE → ACCEPT → SL 2.5 ATR → TP 1.5R → signal+12h → PERSISTENT_FAILURE EXIT NOW`

## Raw/parity
- metrics tail: **2026-09-08 23:45:00+00:00**; futures tail: **2026-09-08 23:45:00+00:00**
- August FLOW parity: generated **13**, frozen **13**, exact union-match **100.0%**
- August router overlap SHORT N=**1**, state/router exact match **100.0%**

## Full-system results

| Slice | FLOW SHORT | Touch | HIGH_RESPONSE | Trades | Persistent exits | EV5 | PF | CumR | MaxDD R | DD@0.25% | EV10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HELDOUT_AUG | 16 | 7 | 5 | 2 | 0 | +1.242 | inf | +2.485 | 0.00 | 0.00% | +0.985 |
| FRESH_SEP | 7 | 6 | 3 | 2 | 1 | +0.516 | 3.706 | +1.031 | 0.38 | 0.10% | +0.435 |
| POSTFREEZE_COMBINED | 23 | 13 | 8 | 4 | 1 | +0.879 | 10.224 | +3.516 | 0.38 | 0.10% | +0.710 |

## Fresh September note
- Completed-horizon fresh trades: **2**.
- If N<5, the preregistered verdict is WATCH regardless of point estimate; this prevents overclaiming from a tiny post-freeze sample.

## Gates
- PASS — `metrics_tail_reaches_sep8`
- PASS — `futures_tail_reaches_sep8`
- PASS — `aug_flow_parity_ge95pct`
- PASS — `aug_router_parity_100pct_when_overlap`
- PASS — `fresh_sep_has_flow_short`
- PASS — `fresh_sep_has_high_response_short`
- FAIL — `fresh_sep_trades_ge5`
- PASS — `fresh_sep_ev_positive_if_n5`
- PASS — `fresh_sep_pf_ge1_10_if_n5`
- PASS — `fresh_sep_10bps_positive_if_n5`
- PASS — `fresh_sep_dd_le4pct`
- PASS — `combined_ev_nonnegative`
- PASS — `no_tuning`

## Guardrail
No threshold or management rule was changed. August is held-out/reused audit, not newly collected OOS. September is sequential fresh relative to LAB043–054 freeze, subject to raw-data/parity gates. No further tuning from these outcomes. Live allocation = **0**.
