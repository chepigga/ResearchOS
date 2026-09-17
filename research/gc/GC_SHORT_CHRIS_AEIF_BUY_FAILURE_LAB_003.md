# GC SHORT CHRIS/AEIF BUY FAILURE LAB003

**Status:** `HISTORICAL_CHRIS_AEIF_SHORT_REJECT_NOT_OOS`

Mechanism: `EXTREME BUY -> UPPER LOCATION -> WEAK UPWARD RESULT -> BEARISH CONFIRMATION <=2 M1 -> SHORT`.
Historical bounded discovery only; not independent OOS. No XAU execution tuning here.

## Key periods

| Feed | Period | N15 | EV15 ATR | N30 | EV30 ATR |
|---|---:|---:|---:|---:|---:|
| RITHMIC | TRAIN | 9 | +0.35474 | 9 | -1.07977 |
| RITHMIC | VALID | 10 | +0.29900 | 10 | +0.59787 |
| RITHMIC | LATE_CHECK | 3 | +0.05502 | 3 | +0.28086 |
| RITHMIC | POST_CHECK | 0 | NA | 0 | NA |
| RITHMIC | FULL | 22 | +0.28854 | 22 | -0.13166 |
| AMP | TRAIN | 6 | +0.30520 | 6 | -0.53081 |
| AMP | VALID | 10 | +0.27664 | 10 | +0.58404 |
| AMP | LATE_CHECK | 4 | -0.32284 | 4 | +1.42154 |
| AMP | POST_CHECK | 3 | -0.43126 | 3 | -0.94357 |
| AMP | FULL | 23 | +0.08749 | 23 | +0.23961 |

## Frozen gates

- FAIL — `rithmic_full_n15_ge25`
- FAIL — `rithmic_train_n15_ge10`
- PASS — `rithmic_valid_n15_ge8`
- PASS — `rithmic_train_ev15_pos`
- PASS — `rithmic_valid_ev15_pos`
- PASS — `rithmic_valid_ev30_pos`
- PASS — `rithmic_full_ev15_pos`
- FAIL — `rithmic_full_ev30_pos`
- PASS — `rithmic_late_conditional_positive`
- PASS — `amp_valid_ev15_pos`
- PASS — `amp_valid_ev30_pos`

## Decision

Reject this exact definition. Do not tune its thresholds post hoc; any continuation requires a separately preregistered mechanism.
