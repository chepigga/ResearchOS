# GC_SHORT_CHRIS_LONG_HISTORY_REPLICATION_LAB_008H — 40D SUFFICIENCY AUDIT

**Scope:** frozen LAB008H lineage evaluated on the already-certified ~40-day explicit-aggressor datasets only. This does not satisfy the preregistered long-history coverage requirement and does not alter the preregistration.

## Sources

- Rithmic `GC_RITHMIC_40D_003_GCZ6.zip`: ~2026-08-03 -> 2026-09-11, explicit aggressor BUY/SELL.
- AMP/CQG `AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip`: ~2026-08-06 -> 2026-09-15, explicit `is_buy` / `is_sell` flags.

## Frozen Chris event count

From LAB003, unchanged definition:

- Rithmic FULL Chris events: **22**.
- AMP FULL Chris events: **23**.

## Frozen POST10 Q50 walk-forward result

From LAB006, unchanged gate: `cp10_dist_seed_high >= expanding prior-event Q50`, after 8 prior eligible events.

### Primary residual +10m -> +20m

- Rithmic: OOF N=14, selected N=7, selected EV **+2.02996 ATR**, rejected EV **-0.42238 ATR**, uplift **+1.22617 ATR**, selected WR **85.7%**.
- AMP: OOF N=15, selected N=8, selected EV **+2.24587 ATR**, rejected EV **-0.15949 ATR**, uplift **+1.12250 ATR**, selected WR **87.5%**.

### Secondary residual +10m -> +30m

- Rithmic selected EV **+2.70232 ATR**, selected WR **85.7%**.
- AMP selected EV **+2.39923 ATR**, selected WR **75.0%**.

## LAB008H long-history prereg gates on current data

The 40-day sample cannot pass the frozen long-history gates by construction:

- usable stitched coverage >=24 months: **FAIL** (~40 days only)
- frozen Chris events >=75: **FAIL** (22 / 23 per feed)
- OOF POST10 events >=50: **FAIL** (14 / 15)
- selected events >=25: **FAIL** (7 / 8)
- multi-year stability gates: **NOT TESTABLE**

Economic-direction diagnostics are positive on the available sample, but they cannot substitute for the preregistered sample-size and multi-year gates.

## Decision

**Status:** `40D_EDGE_POSITIVE_BUT_LONG_HISTORY_SAMPLE_INSUFFICIENT`.

Do not retune. Collect a longer AMP/CQG GC tick history with the same native MT5 `MqlTick.flags` semantics (`TICK_FLAG_BUY` / `TICK_FLAG_SELL`) and rerun the frozen LAB008H unchanged.
