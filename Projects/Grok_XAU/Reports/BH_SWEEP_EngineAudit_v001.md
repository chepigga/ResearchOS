# BH_SWEEP Engine Audit v001

**Date:** 2026-07-24  
**Source:** `AK47_FT_EA_156.mq5` / compiled companion `AK47_FT_EA_156.ex5`  
**Status:** ENGINE SOURCE IDENTIFIED / ORACLE PARITY NOT YET PROVEN

## Identification

The user confirmed that the relevant XAU bot is `AK47_FT_EA_156`, not `Grok_Core_XAU`.

The source contains an independent `BH_SWEEP` module introduced in v1.55. Its comments explicitly identify the research lineage as:

- MorrisCandle V2 (2026-07-05);
- EMA20 reversal sensitivity;
- in-sample control `N=88`, `BUY=52`, `SELL=36`;
- in-sample expectancy `EV=+0.276R`.

## Frozen signal rules found in source

The BH module matches the preregistered strategy definition at the signal level:

- M15 fractal depth 5;
- swing maximum age 96 M15 bars;
- swing consumed by first break;
- sweep event requires break and reclaim-close on the same bar;
- BeltHold search window `<=3` bars;
- body ratio `>=0.60`;
- opposite shadow ratio `<=0.05`;
- signal close must remain beyond the swept level;
- BUY requires close below EMA20; SELL requires close above EMA20;
- SL uses the extremum from sweep bar through signal bar plus/minus `0.25*ATR14(M15)`;
- TP `2R`;
- time stop 96 M15 bars.

## Important distinction: oracle signal engine vs integrated EA execution

`ProcessBeltHold()` contains the frozen mechanical signal reconstruction, but the integrated EA adds execution and portfolio gates that are not part of TZ-BH-OOS-001v2 and must not contaminate Step 0 or Step 1:

- daily equity stop;
- maximum trades per day;
- per-module daily loss-streak cooldown;
- one open BH position at a time;
- portfolio concurrency/floating-loss gates;
- minimum live SL distance of USD 3;
- spread, STOPLEVEL, FREEZELEVEL and margin gates;
- real Ask/Bid and live slippage handling.

The source itself documents two known deviations from the original oracle: the USD 3 SL floor and one-open-BH-position restriction. Therefore an ordinary Strategy Tester run of the full EA is not accepted as the frozen oracle result.

## Required validation implementation

Use the BH signal logic as the recovered engine source, but run it in an isolated oracle harness with all integrated-EA gates removed. Apply the preregistered `-0.05R/trade` cost only after gross trade simulation.

Step 0 remains mandatory because ATR/EMA implementation, entry-bar convention, simultaneous TP/SL tie-breaking and time-stop pricing must reproduce `N=88 / B52 / S36 / EV=+0.276R` within the registered drift limits.

## Provenance

- `AK47_FT_EA_156.mq5` SHA256: `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65`
- `AK47_FT_EA_156.ex5` SHA256: `40201896ac194c3194bf9a86a64e7dad4b7d8abc284a0ae4192e6491c4b390a2`
- source size: 126,758 bytes
- source lines: 2,938
- declared EA version: 1.56

## Current blockers

1. Same-feed XAUUSD M15 export through 2026-07-23.
2. Exact original in-sample start/end boundary or original trade fixture for deterministic Step 0 comparison.
3. Confirmation of oracle intrabar collision convention if both SL and TP are touched in one M15 bar.

No OOS verdict is claimed by this audit.
