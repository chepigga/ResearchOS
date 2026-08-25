# STRUCT_BREAK_PERSISTENT_FLOW_VS_EXHAUSTION_LAB_007 — Report

Date: 2026-08-25
Status: REJECTED PRIMARY HYPOTHESIS
Preregistration commit: 1d265399246e39bb03077cbfe8fc30bc3cf74934

## Universe
Canonical STRUCT_BREAK v002.
DEV 2019-2022: N=767.
VAL 2023-2025: N=698.
2026 kept as shadow only.
All features sampled through the fully closed M15 bar before entry.

## Data
Exact Binance BTCUSDT M15 clock with OHLC plus volume, trades, taker_ratio and avg_trade.

## Targets
Primary: REACHED_1R = be==1.
Secondary: FULL_TP_2.3R = R>2.0.

## Fixed models — primary target
PRICE: DEV AUC 0.570, VAL AUC 0.554, VAL top EV +0.003R.
FLOW: DEV AUC 0.592, VAL AUC 0.500, VAL top EV -0.038R.
EXTREME: DEV AUC 0.559, VAL AUC 0.499, VAL top EV -0.014R.
PRICE+FLOW: DEV AUC 0.612, VAL AUC 0.536, VAL top EV +0.064R.
COMBINED: DEV AUC 0.619, VAL AUC 0.539, VAL top EV +0.066R.

GO gate was VAL AUC >=0.58 plus top-third EV >=+0.10R. No model passes.

## Secondary full TP target
Best preregistered VAL AUC was EXTREME at 0.542 with top EV +0.120R; CI crosses zero and classifier gate fails. FLOW VAL AUC was 0.491.

## Weak transferable clues
P_ER_4H oriented VAL AUC about 0.563.
P_RET_4H oriented VAL AUC about 0.559.
These are not sufficient economic selectors: preregistered PRICE top-third EV is about +0.003R.

## Post-hoc diagnostics
BUY PRICE model: VAL AUC about 0.602, top EV about +0.147R; SELL does not transfer. Requires independent replication.

Inside frozen riskATR>3.72 tail (DEV N=65 / VAL N=67), FLOW model for full TP produced VAL AUC about 0.586 and top EV about +0.326R, but this is a small post-hoc subgroup. Individual hints point toward LOWER long-horizon absolute imbalance/activity. None of 22 tail-flow features survives BH multiple-testing correction (best q about 0.458).

2026 shadow: FLOW full-TP AUC about 0.616 but REACHED_1R AUC about 0.495; not used for verdict.

## Formal verdict
PERSISTENT_M15_FLOW_SELECTOR_REJECTED.

M15 aggregated price/flow state immediately before retest entry is too coarse to identify the missing selector. This does not reject event-local microstructure. Static geometry (LAB006) and aggregated M15 flow (LAB007) both fail, pushing the missing information toward the event clock:
pre-break state -> break impulse -> aggressive-flow transition -> acceptance/exhaustion -> first retest.

## Next experiment
STRUCT_BREAK_EVENT_CLOCK_RAW_FLOW_TRANSITION_LAB_008.
Test pre-break vs break vs post-break flow transitions aligned to the structural-break timestamp using event-local Binance aggTrades/1m flow, before the retest entry is known.
