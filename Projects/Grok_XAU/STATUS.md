# Grok XAU Status

**Updated:** 2026-07-24  
**Project status:** ACTIVE / REANIMATED  
**Active laboratory:** BH_OOS_001 v2  
**Laboratory status:** PREREGISTERED / BLOCKED_DATA_AND_ENGINE

## Frozen hypothesis

BH_SWEEP may retain non-negative net expectancy on unseen XAUUSD M15 data from 2026-05-01 through 2026-07-23 when evaluated by the exact same frozen MorrisCandle V2 oracle used for the in-sample result.

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

1. Frozen MorrisCandle V2 oracle source/config package is not available in the active runtime or File Library.
2. Original in-sample data window/fixture required for the N=88 control is not available in the active runtime.
3. Fresh same-feed XAUUSD M15 export covering 2024-12-01..2026-07-23 is not available.
4. The supplied `Grok_Core_XAU.mq5` is not the BH_SWEEP oracle. It is an AI-driven EA with BOS context and ATR×2 stops.

## Security finding

The supplied legacy EA contained a plaintext xAI API key. The key must be revoked/rotated. Only a redacted archival copy may enter the repository.

## Deployment state

- Demo: BH disabled pending PASS.
- Live: prohibited.
- Canonical EA switch: `InpBH_Enable=false`.

## Next executable action

Run `XAUUSD_M15_Exporter_v001.mq5` inside the same MT5 broker terminal used for the in-sample work, then upload the resulting CSV together with the exact frozen oracle package and original control fixture.
