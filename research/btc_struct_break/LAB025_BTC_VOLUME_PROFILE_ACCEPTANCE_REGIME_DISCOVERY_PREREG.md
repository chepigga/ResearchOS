# LAB025 — BTC_VOLUME_PROFILE_ACCEPTANCE_REGIME_DISCOVERY

Date: 2026-08-27
Status: PREREGISTERED BEFORE CALCULATION

## Objective
Search for causal M1-derived volume-profile regimes that create additional positive M15 trade populations for canonical BREAK_RETEST and canonical LAB023 COMPRESSION SELL.

## Volume-profile construction
For each M15 trade fill timestamp, use Binance BTCUSDT M1 bars strictly before the fill.
- Primary profile window: prior 24h = 1440 M1 bars.
- Secondary comparison profile for POC migration: prior 24h ending 6h earlier.
- 48 equal-width price bins between min(low) and max(high) of the profile window.
- Each M1 bar contributes its full volume to the bin containing HLC3=(high+low+close)/3.
- POC = highest-volume bin center.
- Value Area = contiguous bins grown from POC toward the larger adjacent bin until cumulative volume >=70%; boundaries are VAL/VAH.
- HVN/LVN status of entry bin uses volume-density percentile across the 48 bins: LVN <=30th percentile, HVN >=70th percentile, MID otherwise.

## Frozen causal regime states
A) ENTRY_LOCATION: ABOVE_VAH / INSIDE_VALUE / BELOW_VAL.
B) ACCEPTED_OUTSIDE_VALUE: last 4 completed M15 closes before fill are all above VAH or all below VAL; direction-aligned / direction-opposed / NONE.
C) POC_MIGRATION: current POC minus lagged-6h profile POC, normalized by M15 ATR14 at fill; ALIGNED if >=+0.5 ATR for BUY or <=-0.5 ATR for SELL, OPPOSED symmetric, FLAT otherwise.
D) ENTRY_NODE: LVN / MID / HVN.
E) VALUE_SHIFT: current POC is directionally displaced >=1.0 ATR from lagged-6h POC; TRUE/FALSE.
F) OUTSIDE_VALUE_PLUS_LVN: direction-aligned outside-value location AND entry bin LVN.
G) ACCEPTANCE_PLUS_POC_MIGRATION: direction-aligned accepted outside value AND aligned POC migration.

## Populations
1. canonical BREAK_RETEST all trades from frozen run_v002.
2. canonical LAB023 COMPRESSION SELL accepted pooled-queue trades.
Existing old-pivot core is used only for overlap diagnostics, not selection.

## Splits
DEV: <=2022
VAL: 2023–2025
2026: shadow only, excluded from promotion verdict.

## Base trade economics
Use frozen trade R from each canonical population. Base cost is already included in R. Stress adds incremental cost to 1.5x base.

## Discovery gates for a regime seed
All must pass:
1. DEV EV > 0
2. VAL EV >= +0.08R
3. VAL PF >= 1.15
4. VAL N >= 25
5. >=2/3 positive VAL years
6. VAL EV >0 at 1.5x costs
7. largest VAL year <=70% of positive net result
8. overlap with current two-engine core <=50% within +/-8 M15 bars

This is a multiple-regime discovery screen. Any passing state is a replication seed only, not confirmed production edge. No threshold optimization after results.