# GC SHORT FAILED-RECLAIM DISCOVERY LAB001

**Status:** `HISTORICAL_SHORT_MECHANISM_REJECT_NOT_OOS`

Primary mechanism: `SELLER BREAKDOWN -> RECOVERY ATTEMPT -> FAILED RECLAIM -> SHORT`.
This is historical bounded discovery only; not independent OOS.

## Primary key periods

| Feed | Period | N15 | EV15 ATR | N30 | EV30 ATR |
|---|---:|---:|---:|---:|---:|
| RITHMIC | TRAIN | 27 | -0.91272 | 27 | -0.62619 |
| RITHMIC | VALID | 18 | +0.34830 | 18 | +0.74799 |
| RITHMIC | LATE_CHECK | 4 | +2.18959 | 4 | +1.53341 |
| RITHMIC | FULL | 49 | -0.19624 | 49 | +0.05490 |
| AMP | VALID | 16 | +0.81779 | 16 | +1.56736 |
| AMP | LATE_CHECK | 6 | +2.53193 | 5 | +2.11164 |
| AMP | POST_CHECK | 1 | -0.79715 | 1 | +3.63701 |
| AMP | FULL | 42 | -0.03797 | 41 | +0.50549 |

## Frozen gates

- PASS — `rithmic_full_n_ge30`
- PASS — `rithmic_valid_n_ge8`
- PASS — `rithmic_valid_15m_ev_pos`
- PASS — `rithmic_valid_30m_ev_pos`
- PASS — `rithmic_late_n_ge3_and_15m_ev_pos`
- PASS — `rithmic_late_30m_ev_pos`
- PASS — `amp_valid_15m_ev_pos`
- PASS — `amp_valid_30m_ev_pos`
- FAIL — `rithmic_full_15m_ev_pos`
- PASS — `rithmic_full_30m_ev_pos`

## Decision

Reject this exact failed-reclaim definition. Do not tune its thresholds post hoc. If SHORT research continues, preregister a different bearish mechanism.
