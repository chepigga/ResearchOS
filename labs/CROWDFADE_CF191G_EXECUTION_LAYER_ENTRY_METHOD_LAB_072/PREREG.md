# LAB072 — CF191g EXECUTION LAYER ENTRY METHOD

## Question
With CrowdFade CF191g direction/signal frozen, which execution method produces the strongest transferable result:
1. immediate market at signal;
2. canonical market after confirmation;
3. passive retracement/limit after confirmation with TTL 5m / 10m / 15m?

No signal retuning.

## Frozen signal universe
Use the exact canonical CF191g event extractor already parity-checked in LAB054/LAB068:
- Z threshold 1.00
- canonical confirmation logic unchanged
- signal ATR snapshot unchanged
- same historical 2021-2025 and reused 2026 Mar-Aug shadow/stress sets
- BTCUSDT only.

The canonical event list is frozen before alternative execution is evaluated. Alternative entries do not create/delete future signal events in this diagnostic LAB.

## Entry methods
For every frozen canonical event:

### MARKET_SIGNAL
Enter immediately after the frozen signal M5 bar closes, using the next 1m open.

### CONFIRM_MARKET
Current production concept: enter immediately after the frozen canonical confirmation M5 bar closes, using the next 1m open.

### RETRACE_LIMIT_5 / 10 / 15
After the same frozen canonical confirmation, place one passive limit at the midpoint of the realized signal-close -> confirmation-close displacement:
  limit = (signal_close + confirmation_close) / 2

This is a fixed 50% retracement of the already-observed confirmation move; it is not threshold-mined.
TTL is exactly 5 / 10 / 15 minutes after confirmation. If not touched, skip the trade.

## Standardized outcome geometry
Execution quality comparator only:
- SL distance = 1.50 × frozen signal ATR
- TP distance = 3.00 × frozen signal ATR = 2.0R
- TP is therefore >= user minimum 1.5R
- max hold = 6h
- if SL and TP are both touched inside the same 1m bar, assume SL first (conservative).

This fixed-geometry comparator does NOT replace CF191g positive-skew management. If an entry method survives, it must later be replayed statefully with canonical management.

## Costs
Evaluate three cost models:
- GROSS: no broker friction, for mechanism diagnosis only.
- IC: spread = median BTC spread from BFP004 parity window 24-26 Sep 2026 = 0.597376 bps; commission = 0; adverse stop slippage = median BTC stop slippage from LAB050 IC sample = 0.684253 bps.
- GETLEVERAGED: spread = 2.643809 bps; commission = 0; adverse stop slippage = 0.291636 bps.

Spread is applied as bid/ask around the reference mid at entry and exit. Commission is zero because LAB050 observed zero explicit commission in both BTC samples. Stop slippage applies only to stop exits.

## Primary metrics
For each dataset × cost model × method:
- N signals
- N fills / fill rate
- WR
- EV_R
- PF
- SumR
- MaxDD_R
- R/DD
- TP rate
- SL rate
- time-exit rate
- entry improvement vs CONFIRM_MARKET in ATR
- missed-trade opportunity cost for limit variants.

## Robust promotion criterion
A method is a transfer candidate only if, versus CONFIRM_MARKET under BOTH IC and GetLeveraged cost models:
1. EV_R is not lower in historical 2021-25 and 2026 shadow/stress;
2. R/DD is not lower in both periods;
3. PF is not lower in both periods;
4. for limit methods, fill rate >= 50% in both periods;
5. no single historical year has SumR deterioration > 20% versus CONFIRM_MARKET.

No method is promoted from the 24-26 Sep broker parity window alone.

## Broker transfer shadow
Separately audit recent real BTC CF191g signal timestamps from Sep 25 on the BFP004 IC/GetLeveraged minute feeds. This is a small-N transfer sanity check only and cannot override long-history failure.

## Stop rules
- No threshold tuning after result.
- Do not try 40/60/70% retracement in this LAB.
- Do not change confirmation threshold/TTL.
- Do not change SL/TP geometry.
- If all candidates fail, keep CONFIRM_MARKET and move to broker-normalized spread/SL execution as a separate LAB.
