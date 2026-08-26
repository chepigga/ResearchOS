# LAB030 POSTHOC DIAGNOSTIC — frozen verdict unchanged

## What was proven mechanically
Confirmation target parity exactly reproduces the positive lineage emphasized after LAB027:
- EARLY_TP15 = 77
- DOUBLE_NO_RETURN_CONFIRMED = 118
- total positive lineage = 195 / 2354 = 8.28%
Thus the failure is not caused by target drift.

## What pre-entry information can and cannot do
PRICE_ONLY AUC = 0.6175. PRICE+TICK_ACTIVITY AUC = 0.6091, so broker tick activity does not add rank information for the positive winner lineage and slightly hurts it.
The operational activity router selects 21.03% of Confirmation with 12.32% positive-lineage precision versus 8.28% base (1.49x), but retains only 31.28% of positives.

Subtype retention is asymmetric:
- DOUBLE_NO_RETURN_CONFIRMED: 47 / 118 retained = 39.83%
- EARLY_TP15: 14 / 77 retained = 18.18%
The pre-entry state is materially worse at finding the very strong early-TP lineage.

## Temporal instability
2024: AUC 0.6415, precision lift 1.67x.
2025H1: AUC 0.5314, precision lift 1.13x.
So the pre-entry mapping is not temporally transferable into 2025H1.

## Economics
Selected full baseline EV = -0.1858R vs rejected -0.1685R.
Selected 0.25x starter-control EV = -0.0464R vs rejected -0.0421R.
Therefore score enrichment for the lineage label does not translate into economic enrichment.

## Interpretation
The positive lineage is highly distinguishable after entry (via no-return / path behavior), but only weakly distinguishable before entry from local XAU price + broker tick activity. This supports the hypothesis that the missing information is exogenous/order-flow/liquidity information rather than another transformation of the same pre-entry price path.

The next research direction should not tune another local threshold. The cleanest extension is external causally aligned market information such as COMEX GC futures volume / trade flow / volume-at-price / aggressor imbalance available before the XAU CFD starter clock, with a strict venue-time alignment audit first.
