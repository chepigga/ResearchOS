# BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043

## Purpose
Formal SHORT-only replication of the directional response router suggested by LAB041–042, with no new features, thresholds, or execution tuning.

## Frozen lineage
- Source: `BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041/output/all_touch_elasticity_stream.csv`.
- Use only rows with frozen `book_state` resolved and `side == -1`.
- `HIGH_RESPONSE = DRIVEN_MOVE + THIN_BOOK`.
- `LOW_RESPONSE = ABSORPTION + WEAK`.
- No pressure split is used in the primary decision.
- Primary selection/inference period: `signal_time < 2026-08-01`.
- August 2026 remains audit-only.

## Primary hypothesis
Among frozen SHORT touches, HIGH_RESPONSE has higher post-classification residual ATR than LOW_RESPONSE.

Primary tests:
1. Mean residual gap `HIGH_RESPONSE - LOW_RESPONSE`.
2. 7-day cluster bootstrap, 5000 draws, seed 20260908.
3. ACCEPT-rate difference as mechanism diagnostic only; profitability proof does not require ACCEPT-rate separation.
4. Frequency per month.

## Transfer / robustness
Report HIGH_RESPONSE and LOW_RESPONSE separately for:
- 2021
- 2022
- 2023
- 2024
- 2025H1
- 2025H2
- 2026 Jan-Jul
- pooled recent 2025H2 + 2026 Jan-Jul
- August 2026 audit only.

Also report the HIGH_RESPONSE minus LOW_RESPONSE residual gap by the same slices. No slice-specific thresholds.

## Mechanism decomposition (secondary, frozen)
Inside SHORT HIGH_RESPONSE, report frozen components `DRIVEN_MOVE` and `THIN_BOOK` separately. Inside LOW_RESPONSE, report `ABSORPTION` and `WEAK`. This is descriptive only and cannot redefine the router.

## Gates
1. frozen SHORT resolved pre-Aug >= 900;
2. HIGH_RESPONSE N >= 450;
3. LOW_RESPONSE N >= 450;
4. HIGH_RESPONSE residual > 0;
5. LOW_RESPONSE residual <= 0;
6. residual gap >= +0.50 ATR;
7. 7d cluster bootstrap residual-gap lower 95% CI > 0;
8. HIGH_RESPONSE hit rate >= 0.50;
9. HIGH_RESPONSE frequency >= 6/month;
10. 2021 HIGH_RESPONSE positive;
11. 2022 HIGH_RESPONSE positive;
12. 2023 HIGH_RESPONSE positive;
13. 2024 HIGH_RESPONSE positive;
14. 2025H1 HIGH_RESPONSE positive;
15. 2025H2 HIGH_RESPONSE positive;
16. 2026 HIGH_RESPONSE positive;
17. pooled recent HIGH_RESPONSE positive with N >= 60;
18. pooled recent LOW_RESPONSE <= 0 with N >= 60;
19. pooled recent gap >= +0.50 ATR;
20. 2022 stress HIGH_RESPONSE positive with N >= 50;
21. frozen THIN_BOOK SHORT positive;
22. frozen DRIVEN_MOVE SHORT positive;
23. frozen ABSORPTION SHORT <= 0;
24. frozen WEAK SHORT <= 0;
25. August not used for selection.

## Verdict
- PASS only if >=21/25 and critical gates 4,5,6,7,15,16,17,18,19 pass.
- WATCH if >=14/25 or HIGH_RESPONSE is economically positive but proof/transfer incomplete.
- otherwise FAIL.

## Guardrails
This is reused historical lineage, not fresh OOS. No entry, SL, TP, horizon, pressure threshold, response threshold, or execution optimization. Live allocation = 0.
