# CrowdFade broker normalization — 2026-09-26

Target brokers: IC and GetLeveraged. Signal logic is not intentionally retuned.

## CF191g v197
Base: `CrowdFadeMulti_CF191g_EPISODE_GUARD_v195.mq5`
Output: `CrowdFadeMulti_CF191g_BROKER_NORMALIZED_v197.mq5`

Changes:
- normalized execution gate after canonical confirmation: current spread / actual 1R;
- optional commission and deviation contribution to cost/R;
- WAIT for broker-cost normalization up to 3 completed canonical M5 confirmation opportunities instead of immediate skip/retrace;
- confirmation remains active while execution cost is unacceptable;
- execution audit events: `EXEC_COST_WAIT`, `EXEC_COST_EXPIRE`, `EXEC_COST_OK`;
- default candidate cap `InpMaxSpreadRiskR=0.10` (DEMO candidate; LAB075 still required for promotion).

Frozen: CrowdFade signal, canonical confirmation geometry, stop geometry, positive-skew management, episode guard.

## CF191s v197
Base: `CrowdFadeMulti_CF191s_REGIME_GUARD_v196.mq5`
Output: `CrowdFadeMulti_CF191s_BROKER_NORMALIZED_v197.mq5`

Changes:
- retains v196 crowd-side / |Z| / response regime consistency;
- adds price-exhaustion veto `InpConfirmMaxFavorableATR=1.25` to reject stale entries after the move is already extended;
- normalized spread/actual-1R + commission gate;
- valid confirmation waits up to 15 minutes for cost normalization rather than being destroyed immediately;
- audit events: `STRICT_CONFIRM_CANCEL_EXHAUSTED`, `STRICT_EXEC_COST_WAIT`, `STRICT_EXEC_COST_EXPIRE`, `STRICT_EXEC_COST_OK`;
- default candidate cost cap `0.10R` (DEMO candidate; requires forward validation).

## CF200 v205
Base: `CrowdFadeMulti_CF200_WINNER_PRESERVATION_v204.mq5`
Output: `CrowdFadeMulti_CF200_BROKER_NORMALIZED_v205.mq5`

Changes:
- passive LIMIT architecture retained;
- adds actual-1R normalized execution-cost gate at pending placement;
- default `InpMaxSpreadRiskR=0.067`, chosen to preserve the existing 0.30 ATR / 4.50 ATR stop geometry rather than invent a new optimized threshold;
- adds volatility-regime sanity veto `InpMaxATRExpansionAtPlacement=1.75` before pending placement;
- audit events: `CONFIRM_CANCEL_ATR_EXPANSION`, `LIMIT_COST_SKIP`, `LIMIT_COST_OK`;
- existing broker lot/notional/margin normalization retained.

## Validation status
These are DEMO/forward candidates, not production-promoted builds. Compile in current MT5/MetaEditor before attachment. Run IC and GetLeveraged in parallel with identical signal settings. Primary comparison: signal/confirmation parity, cost-gate decisions, fill rate, EV/PF/DD, and right-tail preservation.
