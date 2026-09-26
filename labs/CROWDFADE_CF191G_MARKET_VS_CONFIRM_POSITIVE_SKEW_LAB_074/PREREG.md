# LAB074 — CF191g MARKET vs CONFIRM with CANONICAL POSITIVE-SKEW MANAGEMENT

## Purpose
LAB073 correctly removed the lookahead in MARKET vs CONFIRM, but used a standardized 2R TP comparator.
Production CF191g does NOT use a fixed 2R TP; its edge is positive-skew management.
LAB074 therefore repeats the same two independent causal entry state machines with the frozen CF191g management.

No entry or management threshold is tuned.

## Entry state machines
Exactly as preregistered in LAB073:

### MARKET_RAW
- fresh eligible |Z| >= 1.00 while flat
- max 3 trades/day
- 1.0 ATR pause-distance rule
- enter immediately at the completed M5 signal close
- no future confirmation information.

### CONFIRM_CANONICAL
Frozen CF191g confirmation:
- favorable move >= 0.30 signal ATR
- <=45m
- pre-confirm adverse <=0.75 ATR
- crowd sign remains on original side
- |Z| at confirmation >=0.75
- response ratio >=0.50
- then market entry at the completed confirmation M5 close.

Each mode runs its OWN occupancy and future reachability.

## Frozen canonical management
- initial SL = 1.50 ATR
- max hold = 6h
- no fixed TP
- BE arm = +3.00 ATR MFE
- BE lock = +2.25 ATR
- trail arm = +3.50 ATR MFE
- trail gap = 0.50 ATR from peak
- ExitZ OFF
- management evaluated on completed canonical M5 path, matching CF191g research lineage.

## Broker execution models
Use the same frozen BFP004/LAB050 models:
- GROSS: spread 0, stop slippage 0
- IC: median BTC spread 0.597376 bps, commission 0, median stop slippage 0.684253 bps
- GetLeveraged: median BTC spread 2.643809 bps, commission 0, median stop slippage 0.291636 bps

Spread is embedded as bid/ask around mid. Stop slippage is adverse on stop fills only.

## Periods
- 2021-01-01 through 2025-12-31 historical.
- 2026-03-01 through 2026-08-31 reused forward/shadow stress (NOT pristine OOS).

BTC only.

## Primary metrics
N, WR, EV_R, PF, SumR, MaxDD_R, R/DD, max loss streak, exit reason mix, yearly/monthly stability.

## Promotion criterion for MARKET_RAW
Versus CONFIRM_CANONICAL under BOTH IC and GetLeveraged:
1. EV_R >= confirmation in historical AND 2026.
2. PF >= confirmation in historical AND 2026.
3. R/DD >= confirmation in historical AND 2026.
4. MaxDD <= 1.25x confirmation in both periods.
5. all five historical years positive.
6. forward 2026 SumR > 0.
7. N >= 200 in forward.

If MARKET_RAW fails, keep canonical confirmation in production.
No threshold tuning after result.
