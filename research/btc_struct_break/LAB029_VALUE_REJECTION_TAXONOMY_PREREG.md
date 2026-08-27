# LAB029 — BTC_VALUE_REJECTION_TAXONOMY_DISCOVERY

Date: 2026-08-27

## Objective
Decompose POC-opposed BREAK_RETEST into three causal rejection types without threshold tuning.

## Frozen population
Canonical BREAK_RETEST trades with LAB025 M1 volume-profile features.
POC_OPPOSED remains the parent context.

## Frozen rejection types
1. CLOSE_BACK_INSIDE_VALUE
   - within prior 12 completed M15 bars before fill, price was outside current VA in the opposed direction at least once;
   - then a later completed M15 close returned back inside current value (BUY: close > VAL, SELL: close < VAH).

2. FAILED_RETEST_OF_VA_BOUNDARY
   - after CLOSE_BACK_INSIDE_VALUE, at least one later completed M15 bar retests the same VA boundary within 0.25 ATR;
   - that bar closes on the trade-aligned side of the boundary (BUY above VAL, SELL below VAH).

3. POC_SNAPBACK
   - POC migration is OPPOSED at fill;
   - short-horizon 6h POC versus 12h-lagged 24h POC has moved at least 0.25 ATR back toward trade direction.
   - computed causally from M1 profiles ending strictly before fill.

## Controls
A: POC_OPPOSED
B: CLOSE_BACK_INSIDE_VALUE
C: FAILED_RETEST_OF_VA_BOUNDARY
D: POC_SNAPBACK
E: UNION(B,C,D) diagnostic only

## Primary discovery gates for each B/C/D
2024 discovery and 2025 replication:
- DISC2024 EV > 0
- REPL2025 EV >= +0.10R
- REPL2025 PF >= 1.30
- REPL2025 N >= 15
- 1.5x cost EV > 0
- 2025 half-year stability: both non-negative OR weaker half >= -0.05R
- overlap current core <= 20%

## Portfolio diagnostic gate
- trade count +10% or more
- portfolio EV >= +0.18R
- PF >= 1.40
- MaxDD <= 1.35x current core
- 1.5x cost portfolio EV > 0

No side selection, no threshold changes, no post-hoc combinations promoted in this LAB.
