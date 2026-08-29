# XAU_PRICE_TIME_ALOGICAL_POST_TRAP_PAYOFF_MAP_LAB_008

Frozen research question: after LAB007 crowd-trap transitions, is there a short executable inverse response even though a full 2R reversal fails?

- lineage: LAB007 V2 transition definitions unchanged
- horizons: 3, 5, 10, 15, 20, 30, 60 minutes
- targets: 0.10, 0.15, 0.20, 0.25, 0.30, 0.40 ATR
- RR screen: 1.5 and 2.0 only
- execution: BUY Ask->Bid, SELL Bid->Ask; commission explicit
- ambiguity: target+stop in same M1 horizon is LOSS in lower-bound screen
- de-cluster: 240 minutes per LAB007 cell
- chronology: 2023-24 discovery, 2025 validation, 2026 untouched final OOS
- anti-curve-fit: discovery config must have at least one positive neighboring horizon/target configuration
