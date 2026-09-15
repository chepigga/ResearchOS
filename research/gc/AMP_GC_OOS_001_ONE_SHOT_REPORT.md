# AMP_GC_OOS_001 — ONE-SHOT UNTOUCHED REPLICATION

## Verdict: **FEED_SIGNAL_DIVERGENCE**

No parameter sweep, threshold change, session filter, or AMP-performance-based selection was performed.

- AMP M5 bars: **7,699**
- evaluation starts after frozen 240-bar warmup: **2026-08-07T15:25:00+00:00**
- AMP CORE: **90 = 38 LONG / 52 SHORT**
- 30m cooldown baseline branch kept: **79**
- AMP confirmations: **55 = 28 LONG / 27 SHORT**

## Same-date Rithmic source-parity window

Window: `2026-08-07T15:25:00+00:00` → `2026-09-11T11:45:00+00:00`
- CORE: AMP **82**, Rithmic **88**, matched **75**, AMP-only **7**, Rithmic-only **13**, Jaccard **0.7895**
- Confirmation: AMP **52**, Rithmic **52**, matched **46**, AMP-only **6**, Rithmic-only **6**, Jaccard **0.7931**

## Historical XAU timestamp mapping (coverage-limited)

XAU history: `2026-08-03 01:05:00` → `2026-09-08 20:03:00` file clock (UTC+2 mapping).
- AMP confirmations whose scheduled XAU time is inside available history: **42**
- exact-timestamp eligible transfers: **41 = 19 LONG / 22 SHORT**
- missing exact XAU timestamp inside available history: **1**

## Frozen bridge implementation

AMP mixed BUY+SELL prints are excluded from directional aggressor volume to preserve mutually-exclusive Rithmic aggressor semantics. This choice was preregistered before the run.

The 30-minute cooldown and confirmation-transfer path are reported as separate historical branches: confirmation is generated from frozen CORE directly, matching the historical 105→61 lineage; cooldown remains the frozen 105→92 baseline diagnostic branch.

No later XAU confirmations are treated as failures merely because the release XAU file ends on September 8.
