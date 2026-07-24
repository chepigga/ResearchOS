# Grok XAU Status

**Updated:** 2026-07-24  
**Project status:** ACTIVE / REANIMATED  
**Active laboratory:** BH_OOS_001 v2  
**Laboratory status:** PREREGISTERED / ENGINE_IDENTIFIED / BLOCKED_DATA_AND_PARITY

## Frozen hypothesis

BH_SWEEP may retain non-negative net expectancy on unseen XAUUSD M15 data from 2026-05-01 through 2026-07-23 when evaluated by the exact same frozen MorrisCandle V2 oracle used for the in-sample result.

## Correct engine source

The user confirmed that the relevant bot is `AK47_FT_EA_156`, not `Grok_Core_XAU`.

`AK47_FT_EA_156.mq5` contains the independent BH_SWEEP v1.55 module and explicitly records the MorrisCandle V2 + EMA20 lineage and the control target `N=88 (B52/S36), EV=+0.276R`.

The BH signal code matches the preregistered strategy definition. However, the full EA also adds live/portfolio gates that are not part of the frozen oracle. Therefore the full EA Strategy Tester result is not accepted as Step 0 without an isolated oracle-parity harness.

See: `Reports/BH_SWEEP_EngineAudit_v001.md`.

## In-sample control target

- Expected trades: `N=88`
- Direction split: `BUY=52`, `SELL=36`
- Expected EV: `+0.276R`
- Allowed reproduction drift: `|ΔN| <= 2` and `|ΔEV| <= 0.02R`
- Larger drift: `CONTROL_FAIL`; OOS must not run before root-cause localisation.

## OOS gate

- PASS: `N >= 8` and `EV_net >= 0`
- FAIL: `N >= 8` and `EV_net < 0`
- INCONCLUSIVE: `N < 8`
- Near-miss handling is forbidden except under a separate NM1-NM4 decision.

## Current blockers

1. Fresh same-feed XAUUSD M15 export covering 2024-12-01..2026-07-23 is not available.
2. Exact original in-sample boundary or original N=88 trade fixture is not available for deterministic parity comparison.
3. Oracle execution conventions still require parity confirmation: EMA/ATR implementation, market-entry price convention, same-bar TP/SL collision rule, and time-stop price.
4. `AK47_FT_EA_156` integrated execution contains non-oracle gates: daily stop, max trades/day, loss-streak cooldown, one-open-BH restriction, portfolio gates, USD 3 SL floor, spread/STOPLEVEL/FREEZELEVEL/margin gates.

## Legacy clarification

`Grok_Core_XAU.mq5` remains classified as an unrelated legacy AI-driven EA and is not the source of BH_SWEEP.

## Security finding

The unrelated legacy `Grok_Core_XAU.mq5` contained a plaintext xAI API key. The key must be revoked/rotated. `AK47_FT_EA_156.mq5` did not show an embedded API credential in the source scan.

## Deployment state

- Demo: BH disabled pending PASS.
- Live: prohibited.
- Canonical EA switch: `InpBH_Enable=false`.

## Next executable action

Run `XAUUSD_M15_Exporter_v001.mq5` inside the same MT5 broker terminal used for the in-sample work and upload the resulting CSV. Then build the isolated parity harness from the recovered BH module and execute Step 0 before opening the OOS window.
