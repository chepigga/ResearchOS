# XAU_ACCEPTED_SIDE_SHALLOW_LIMIT_ENTRY_PRICE_FRONTIER_LAB_023 — Spec v001

Date: 2026-08-24
Status: PREREGISTERED / PRE-HOLDOUT

## Question
Does replacing the frozen early digestion market entry with a pre-placed shallow internal limit improve executable economics without requiring a return to the old broken level?

## Frozen lineage
- Canonical XAU M1 bid/ask data SHA-256: db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b
- Strong-bias / digestion universe: exact LAB012/LAB019 cached parent events.
- Discovery: break_time < 2024-01-01.
- Confirmation: 2024-01-01 <= break_time < 2025-07-01.
- Holdout >= 2025-07-01 remains sealed.
- Only strong_accept + valid frozen digestion + baseline entry events are eligible.

## Baseline
Frozen LAB012 early digestion entry:
- enter at next M1 open after digestion-close;
- BUY at AskOpen, SELL at BidOpen;
- baseline risk distance = 0.50 ATR_touch;
- baseline TP1.5 distance = 0.75 ATR_touch;
- baseline TP2.0 distance = 1.00 ATR_touch;
- commission proxy = $0.05 XAU price-equivalent round turn;
- conservative same-bar TP+SL = LOSS;
- max holding horizon = 60 minutes.

## Primary shallow-limit execution
At digestion close, submit one limit order for the next bar onward.

Primary depth:
- 0.10 ATR_touch better than frozen baseline market entry price.
- BUY limit = baseline_entry - 0.10 ATR_touch.
- SELL limit = baseline_entry + 0.10 ATR_touch.

Expiry:
- active for 5 contiguous completed M1 bars beginning with baseline_entry_i;
- if not touched within those 5 bars, CANCEL / SKIP;
- first touch only; no chasing and no second order.

Fill convention:
- BUY limit fills if AskLow <= limit price; fill at limit price.
- SELL limit fills if BidHigh >= limit price; fill at limit price.
- if the first active bar opens through the limit at a better executable price, fill at the better opening quote (BUY min(AskOpen, limit), SELL max(BidOpen, limit)).
- no intrabar knowledge beyond bid/ask OHLC.

## Frozen absolute stop and target
This LAB isolates entry price.
For a filled limit trade, KEEP the exact absolute baseline market-entry stop and target:
- BUY SL = baseline_entry - 0.50 ATR; SELL SL = baseline_entry + 0.50 ATR.
- BUY TP1.5 = baseline_entry + 0.75 ATR; SELL TP1.5 = baseline_entry - 0.75 ATR.
- TP2.0 similarly +/-1.00 ATR from baseline entry.

Therefore a 0.10 ATR better fill changes actual risk/reward. Primary 1.5 target becomes approximately 0.85 ATR reward versus 0.40 ATR risk before costs (~2.125:1), if filled exactly at the limit.

R normalization for reporting:
- 1R = actual absolute distance from LIMIT FILL to the frozen baseline SL.
- target R = actual distance from LIMIT FILL to frozen baseline TP divided by actual risk.
- max 60m from fill.

## Secondary frontier diagnostics — NOT winner selection
Depths: 0.05, 0.15, 0.20 ATR, each with same 5m expiry.
Expiry sensitivity for primary 0.10 depth: 3m and 10m.
These do not change the primary verdict and cannot be selected post-hoc.

## Comparisons
1. Same eligible universe baseline market-entry serial economics.
2. Primary limit filled-trades independent economics.
3. Primary limit serial portfolio economics.
4. Opportunity-adjusted R per original eligible event, where unfilled limit = 0R, to prevent fill-rate cherry-picking.
5. Filled-vs-unfilled adverse-selection diagnostic.
6. BUY/SELL and digestion-state breadth.

## Primary gates
G0 causality/data/hash PASS.
G1 fill rate >= 20% and primary serial N >= 400 and >= 4 trades/week.
G2 primary serial EV > 0 and PF > 1.
G3 weekly-cluster mean EV lower 95% CI > 0.
G4 opportunity-adjusted mean R per original eligible event > 0 with week CI > 0.
G5 Discovery independent EV > 0 and Confirmation independent EV > 0.
G6 BUY EV > 0 and SELL EV > 0.
G7 2R sensitivity EV >= 0.
G8 +$0.10 stress EV > 0.
G9 primary limit beats frozen baseline on paired opportunity-adjusted weekly delta with lower 95% CI > 0.
G10 no evidence that fill requires old-level degradation/retest beyond frozen digestion definition.

## Verdict labels
- SHALLOW_LIMIT_ENTRY_EDGE
- SHALLOW_LIMIT_IMPROVES_PRICE_NOT_POSITIVE
- SHALLOW_LIMIT_POSITIVE_BUT_NOT_ROBUST
- NO_SHALLOW_LIMIT_ENTRY_EDGE
- INVALID_DATA_CAUSALITY

No threshold/depth/expiry rescue is allowed after Confirmation results. Holdout remains sealed unless a future integrated system passes preregistered gates.
