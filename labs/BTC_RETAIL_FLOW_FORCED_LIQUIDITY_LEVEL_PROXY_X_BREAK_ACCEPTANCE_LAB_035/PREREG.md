# BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035

## Question
Does frozen retail-flow direction become materially more profitable when price activates an economically plausible forced-liquidity proxy level and is accepted beyond that level?

## Frozen directional lineage
- Exact non-overlapping flow stream from LAB022 (`flow_only_nonoverlap.csv`).
- Direction is frozen and never changed by price:
  - retail long crowding extreme => SHORT (`side=-1`)
  - retail long contraction extreme => LONG (`side=+1`).
- Primary horizon remains original signal +12h.
- No new ratio cutoff, no new flow threshold, no stop/TP search.

## Forced-liquidity level proxy
True future liquidation prices are not observable historically for 2025-2026. Therefore the primary causal proxy is frozen BEFORE the run:
- SHORT flow: lowest futures M15 low of the previous 12h (48 completed bars), excluding the signal bar.
- LONG flow: highest futures M15 high of the previous 12h, excluding the signal bar.
Rationale: this is the nearest 12h directional extreme beyond which clustered stops / leveraged forced exits are economically plausible. It is a proxy, not claimed to be the actual liquidation price.

## OI backing
At signal time calculate futures `sum_open_interest` change over the previous 3h.
- `OI_BACKED = oi_logchg_3h > 0`
This is fixed and used only as an interaction label; no OI magnitude cutoff search.

## Distance
Signal-time distance to the frozen level in ATR14(M15):
- `<=0.5 ATR`
- `0.5-1 ATR`
- `1-2 ATR`
- `>2 ATR`
No bin may be promoted as a live cutoff from this reused sample.

## Activation and acceptance
Within original signal +12h:
1. `TOUCH` = first M15 bar whose high/low crosses the frozen level in the flow direction.
2. Starting with the TOUCH bar, inspect that bar plus the next 3 completed M15 bars (maximum 1h).
3. `ACCEPT` = first completed M15 close beyond the frozen level in the flow direction.
4. `REJECT` = TOUCH occurred but none of those 4 closes is beyond the level.
5. If +12h arrives before classification, state=`UNRESOLVED`.

Primary anti-tautology outcome:
- ACCEPT residual = signed move from the acceptance close to original signal +12h, normalized by ATR14 known at signal.
- REJECT residual = signed move from the fourth response close (classification time) to original signal +12h.
The level-break movement used to define ACCEPT is therefore excluded from the residual.

Also report frozen full signal->12h ATR return by state for economic context.

## OI flush audit
Diagnostic only, not a causal entry rule:
- OI change from the bar before TOUCH to 1h after classification.
- `OI_FLUSH = post-classification OI < pre-touch OI`.
This tests whether accepted breaks are accompanied by position destruction, but it cannot rescue the primary hypothesis.

## Historical direct-liquidation audit
Binance USD-M `liquidationSnapshot` historically existed but was discontinued/removed after 2024-03-31. The runner will attempt direct files for a deterministic sample of pre-2024 events. If files are available, report liquidation count/notional in a fixed window around TOUCH/ACCEPT and whether liquidation side matches expected forced side. This audit is informative only and is NOT a PASS gate because public archive availability is incomplete/non-stationary.

## Windows
- 2021
- 2022 bearish stress
- 2023
- 2024 through available sample
- 2025 H1
- 2025 H2
- 2026 Jan-Jul
- Aug 2026 reused audit only
- pooled pre-Aug
- pooled recent 2025H2 + 2026 Jan-Jul

## Primary gates
1. frozen flow lineage N>=3200.
2. futures M15 coverage >=99% of pre-Aug signals.
3. OI metrics coverage >=90% of pre-Aug signals.
4. TOUCH N>=500 pre-Aug.
5. ACCEPT N>=200 pre-Aug.
6. ACCEPT residual mean > 0.
7. ACCEPT residual mean exceeds REJECT residual mean by >=0.20 ATR.
8. 7-day cluster bootstrap 95% CI lower bound for ACCEPT-minus-REJECT residual > 0.
9. ACCEPT full 12h mean exceeds all-flow baseline by >=0.15 ATR.
10. OI_BACKED ACCEPT full 12h mean exceeds non-OI-backed ACCEPT by >=0.15 ATR.
11. 2022 SHORT ACCEPT residual N>=30 and mean >0.
12. pooled recent ACCEPT residual N>=50 and mean >0.
13. TOUCH rate is higher in <=0.5 ATR distance bin than >2 ATR bin (sanity/geometry gate).

PASS: >=10/13 and critical gates 1,2,5,6,8,12.
WATCH: acceptance is directionally useful but bootstrap or recent transfer is incomplete.
FAIL: no robust acceptance separation or accepted residual <=0.

## Guardrails
- No support/resistance optimization.
- No alternative lookback after results; 12h level is frozen.
- No alternative acceptance bar-count after results; 4 M15 bars is frozen.
- No stop/TP or entry optimization in this LAB.
- Historical liquidation snapshots are validation only, never used to choose levels.
- August 2026 remains reused audit only.
- Live allocation remains 0.