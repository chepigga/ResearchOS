# BTC_FLOW_LEVEL_CVD_PRESSURE_X_PRICE_RESPONSE_CAUSAL_ROLLING_INTERACTION_REPLICATION_LAB_039

## Purpose
Formal causal replication of the diagnostic LAB038 interaction `HIGH NET TAKER PRESSURE × HIGH PRICE RESPONSE` using only strictly-prior rolling thresholds.

## Frozen lineage
- Source: `BTC_FLOW_LEVEL_PRETOUCH_NET_TAKER_DELTA_PRICE_RESPONSE_AND_CVD_ABSORPTION_LAB_038/output/cvd_absorption_stream.csv`.
- FLOW direction, level, touch, HIGH_VOLUME flag, ACCEPT/REJECT state, `fut_netdelta_norm_60`, `fut_disp_atr_60`, and frozen post-classification residual are unchanged.
- Selection/inference uses `signal_time < 2026-08-01`; August 2026 is audit only.

## Causal thresholds
For every frozen HIGH_VOLUME event at time `t`:
- reference cohort = resolved HIGH_VOLUME events with timestamps in `[t-90d, t)` only;
- require at least 20 prior resolved events;
- pressure threshold = median prior `fut_netdelta_norm_60`;
- response threshold = median prior `fut_disp_atr_60`;
- if history <20 or either threshold unavailable, label `UNRESOLVED`.

No global threshold, future data, optimization, or fallback threshold is allowed.

## Frozen interaction cells
- `EFFICIENT_IGNITION`: pressure > rolling pressure median AND response > rolling response median.
- `ABSORPTION`: pressure > rolling pressure median AND response <= rolling response median.
- `THIN_LIQUIDITY`: pressure <= median AND response > median.
- `WEAK`: pressure <= median AND response <= median.

## Primary tests
1. On resolved pre-Aug HIGH_VOLUME events, compare `EFFICIENT_IGNITION` vs `ABSORPTION`:
   - ACCEPT rate;
   - frozen LAB035 post-classification residual ATR;
   - hit rate.
2. 7-day cluster bootstrap, 5000 draws, fixed seed 20260908, for:
   - ACCEPT-rate difference;
   - residual difference.
3. Transfer slices: 2021–2024, 2025H1, 2025H2, 2026 Jan-Jul, pooled recent, LONG, SHORT, fixed 2022 SHORT, August audit.
4. Report frequency: resolved interaction events/month and efficient-ignition events/month.

## Gates
1. frozen HIGH_VOLUME pre-Aug >=500;
2. resolved rolling thresholds >=80% of pre-Aug HIGH_VOLUME;
3. EFFICIENT_IGNITION N>=120;
4. ABSORPTION N>=80;
5. efficient ACCEPT rate > absorption;
6. ACCEPT-rate gap >=+0.03;
7. ACCEPT-rate bootstrap CI lower >0;
8. efficient residual > absorption;
9. residual gap >=+0.50 ATR;
10. residual bootstrap CI lower >0;
11. efficient residual positive;
12. efficient residual hit >=0.50;
13. 2022 SHORT efficient residual positive with N>=15;
14. pooled recent efficient residual positive with N>=30;
15. 2025H2 efficient residual positive;
16. 2026 efficient residual positive;
17. LONG efficient residual positive;
18. SHORT efficient residual positive;
19. efficient frequency >=1.0/month;
20. August not used for selection.

Verdict:
- PASS if >=16/20 and gates 5,8,10,14,15,16 pass.
- WATCH if >=11/20 or residual mechanism remains economically positive but statistical/transfer proof incomplete.
- otherwise FAIL.

## Guardrail
This is a replication/mechanism LAB, not an executable strategy. No entry, stop, target, or sizing optimization. Live allocation = 0.
