# GC SHORT SELL-PRESSURE ACCEPTANCE CONTINUATION LAB002

**Status:** `HISTORICAL_SHORT_ACCEPTANCE_REJECT_NOT_OOS`

Mechanism: `EXTREME SELL -> BREAK/CLOSE BELOW PRIOR20 LOW -> NEXT M1 ACCEPTS BELOW -> SHORT`.
Historical bounded discovery only; not independent OOS. No XAU execution tuning here.

## Key periods

| Feed | Period | N15 | EV15 ATR | N30 | EV30 ATR |
|---|---:|---:|---:|---:|---:|
| RITHMIC | TRAIN | 41 | +0.12153 | 40 | +1.02877 |
| RITHMIC | VALID | 24 | -0.07237 | 24 | -0.39045 |
| RITHMIC | LATE_CHECK | 15 | -0.49227 | 15 | -0.25147 |
| RITHMIC | POST_CHECK | 0 | NA | 0 | NA |
| RITHMIC | FULL | 80 | -0.05173 | 79 | +0.35453 |
| AMP | TRAIN | 29 | +0.08967 | 29 | +0.56192 |
| AMP | VALID | 26 | -0.27457 | 26 | -0.65874 |
| AMP | LATE_CHECK | 13 | -0.27880 | 13 | -0.35436 |
| AMP | POST_CHECK | 7 | +2.13600 | 7 | +2.36957 |
| AMP | FULL | 75 | +0.09052 | 75 | +0.14865 |

## Frozen gates

- PASS — `rithmic_full_n15_ge25`
- PASS — `rithmic_train_n15_ge12`
- PASS — `rithmic_valid_n15_ge8`
- PASS — `rithmic_train_ev15_pos`
- PASS — `rithmic_train_ev30_pos`
- FAIL — `rithmic_valid_ev15_pos`
- FAIL — `rithmic_valid_ev30_pos`
- FAIL — `rithmic_full_ev15_pos`
- PASS — `rithmic_full_ev30_pos`
- FAIL — `rithmic_late_conditional_positive`
- FAIL — `amp_valid_ev15_pos`
- FAIL — `amp_valid_ev30_pos`

## Decision

Reject this exact acceptance definition. Do not tune its thresholds post hoc; preregister a different bearish mechanism if SHORT research continues.
