# LAB028 Post-hoc diagnostic

Frozen verdict remains `NO_PRE_ENTRY_SURVIVAL_SIGNAL` under the preregistered FULL-vs-PRICE_ONLY primary comparison.

## What actually happened
- PRICE_ONLY AUC 0.6280, fixed-threshold precision 21.44%, coverage 32.50%.
- PLUS_ACTIVITY AUC 0.6437, precision 24.10%, coverage 30.67%.
- PLUS_EFFORT AUC 0.6341: handcrafted effort/result ratios gave back part of the activity gain.
- PLUS_SPREAD/FULL AUC 0.6247: spread interactions further degraded ranking.
- real_volume is zero on all 1,080,929 pre-holdout canonical rows, so no exchange-volume conclusion is possible from this dataset.

## Interpretation
Tick activity contains incremental pre-entry information about first-5m survival, but the broad engineered feature stack dilutes it. The operational signal is still too weak for the starter economics: the preregistered FULL router selected starter-control EV -0.0460R versus -0.0406R rejected.

The promising activity-only result is a post-hoc lineage clue, not an authorized rescue. A clean next experiment should freeze PRICE_ONLY + TICK_ACTIVITY only, test temporal transfer/year stability and build an operational router without effort/spread features or Confirmation threshold tuning.
