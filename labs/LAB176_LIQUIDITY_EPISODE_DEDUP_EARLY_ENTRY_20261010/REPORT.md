# LAB176 — LIQUIDITY EPISODE DEDUP × EARLY ENTRY
Date 2026-10-10. Research, not executed trades. Frozen LAB175 7311 candidates and LAB169 2754 hindsight waves.

Time-only prospective dedup by engine+side: 3h 4841 (71.2/mo), 6h 3630 (53.4/mo), 12h 2534 (37.3/mo), 24h 1676 (24.6/mo); none 7311 (107.5/mo). Preferred diagnostic 6h, NOT optimized: CONT 3519 (BUY 1794 SELL 1725), REV 111 (BUY49 SELL62); RR>=2 2014, RR>=3 570.

6h selected 446 matching same-side candidate routes in 420 unique retrospective LAB169 waves out of 2754. First matching selected entry per wave: 239/420 in first 25% of elapsed wave time, 286/420 in first 50%, median 14.3%. Hindsight waves only used AFTER detection for audit, not for selecting entries. Duration fraction is not price capture or realized profit.

Important limitations: fixed hours not actual same-liquidity episode (not grouped by target level); opposite-side and cross-engine overlaps possible; 53.4/mo is NOT proven independent opportunities or profitable fills. Wave definition LAB169 2754 differs from LAB161 2680; no parity. No fees/PNL evaluation by design.

Reproduce using source LAB175_SEQUENTIAL_ROUTES.csv, LAB169_waves.csv and lab176_run.py. Local outputs LAB176_ALL_CANDIDATES_EPISODES.csv LAB176_EPISODES_6H.csv LAB176_FIRST_ENTRY_PER_WAVE.csv LAB176_MONTHLY.csv LAB176_SENSITIVITY.csv LAB176_REPORT.md.
