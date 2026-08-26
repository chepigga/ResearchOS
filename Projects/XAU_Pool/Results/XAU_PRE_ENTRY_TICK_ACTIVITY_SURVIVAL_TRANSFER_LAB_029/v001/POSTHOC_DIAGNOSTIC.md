# LAB029 POSTHOC DIAGNOSTIC

Frozen verdict unchanged: `TICK_ACTIVITY_SIGNAL_TRANSFERABLE_NOT_ECONOMIC`.

## What transferred
- Full Confirmation survival base: 16.23%.
- PRICE+TICK_ACTIVITY AUC: 0.6402 vs PRICE_ONLY 0.6395 (tiny incremental delta +0.0006 in this narrow replay).
- Frozen Discovery threshold coverage: 30.29%.
- Selected survival precision: 23.42% (1.44x base).
- Survivor retention: 43.72%; failure rejection: 72.31%.
- 2024: AUC 0.6668, precision lift 1.59x.
- 2025H1: AUC 0.5802, precision lift 1.18x; much weaker but still above base precision.
- SELL breadth is stronger than BUY: SELL precision 25.42% vs 14.39% base; BUY 22.01% vs 18.14% base.

## Score shape
Confirmation score deciles strongly rank first-5m survival:
- bottom decile survival: 2.54%
- top decile survival: 27.12%
This is a >10x ratio and confirms genuine ranking of the probation target.

## Why economics fail
The target is misaligned with terminal trade economics.
- selected starter-control EV: -0.0529R
- rejected starter-control EV: -0.0387R
- selected frozen full baseline EV: -0.2116R
- rejected frozen full baseline EV: -0.1550R
- selected baseline TP rate: 31.0%
- rejected baseline TP rate: 34.3%

Thus higher probability of surviving the first five minutes does NOT imply higher probability of eventual TP or higher terminal expectancy. Tick activity helps identify short-horizon path resilience, not monetizable winner quality.

## Lineage caveat
LAB029's narrow replay produced 26 PRICE / 40 PRICE+ACTIVITY features, whereas the persisted LAB028 report lists 34 / 48. Therefore the strong +0.0156 AUC activity increment reported in LAB028 did not replicate as a standalone increment here (+0.0006). LAB029 itself remains internally preregistered and causal, but should not be described as an exact feature-parity replication of LAB028.

## Research implication
Do not optimize another threshold on the same survive5 target. The target itself is the bottleneck. A next screen should target preservation of the known positive winner lineage (early TP1.5 + double-no-return confirmed winner) or use external information with closer economic meaning, e.g. real COMEX GC volume/order flow, while keeping the decision clock pre-entry.
