# GC SHORT CHRIS/AEIF HORIZON DECAY LAB003H

**Status:** `HISTORICAL_HORIZON_DECAY_AUDIT_NOT_OOS`

Frozen LAB003 event set; signal definition unchanged.

## EV by feed / period / horizon

| Feed | Period | 1m | 3m | 5m | 10m | 15m | 30m |
|---|---|---:|---:|---:|---:|---:|---:|
| RITHMIC | TRAIN | -0.01647 | +0.31892 | +0.08611 | +0.96632 | +0.35474 | -1.07977 |
| RITHMIC | VALID | -0.01676 | -0.13550 | -0.11713 | -0.45686 | +0.29900 | +0.59787 |
| RITHMIC | LATE_CHECK | -0.20278 | -0.69776 | -0.60267 | +0.10942 | +0.05502 | +0.28086 |
| RITHMIC | POST_CHECK | NA | NA | NA | NA | NA | NA |
| RITHMIC | FULL | -0.04201 | -0.02627 | -0.10019 | +0.20257 | +0.28854 | -0.13166 |
| AMP | TRAIN | +0.06641 | +0.81621 | +0.61997 | +1.17962 | +0.30520 | -0.53081 |
| AMP | VALID | -0.02918 | -0.13286 | -0.14057 | -0.48641 | +0.27664 | +0.58404 |
| AMP | LATE_CHECK | +0.05149 | +0.21889 | +0.34332 | +0.59765 | -0.32284 | +1.42154 |
| AMP | POST_CHECK | +0.33968 | -0.13354 | -0.72889 | -0.19182 | -0.43126 | -0.94357 |
| AMP | FULL | +0.05790 | +0.17581 | +0.06525 | +0.17516 | +0.08749 | +0.23961 |

## FULL best horizon (descriptive only)

- Rithmic: 15m, EV +0.28854 ATR
- AMP: 30m, EV +0.23961 ATR

## Interpretation

No strict cross-feed 5m dominance over both 15m and 30m on VALID and FULL. Treat horizon shape as mixed; inspect the full curve rather than selecting a best horizon post hoc.

This audit cannot promote LAB003 by itself and does not authorize threshold or execution retuning.
