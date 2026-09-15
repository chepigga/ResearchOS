# GC_M1_ORDERFLOW_EDGE_DISCOVERY_003

Bounded historical discovery; **not OOS certification**. All entries are exact next M1 open.

Passing candidates: **NONE**
Winner: **NONE**

| Candidate | Gate | R Train 15m | R Valid 15m | AMP Valid 15m | Late 15m R/AMP | Post 15m AMP |
|---|---|---:|---:|---:|---:|---:|
| A_REV | FAIL | -0.042 | +0.070 | +0.129 | +0.237/+0.143 | -0.362 |
| FAIL_Q20_REV | FAIL | +0.096 | +0.188 | +0.157 | +0.271/+0.341 | -0.357 |
| OPPOSITE_BODY_REV | FAIL | +0.099 | +0.035 | -0.017 | -0.557/-0.339 | -0.503 |
| REJECTION_REV | FAIL | -0.156 | -0.116 | -0.184 | -0.242/-0.244 | -0.453 |
| SWEEP_REJECT_REV | FAIL | -1.115 | +0.430 | +0.580 | -0.931/-0.320 | -0.190 |
| LOC_OPPOSITE_BODY_REV | FAIL | -0.482 | +0.643 | +0.486 | -0.346/-0.257 | -0.797 |
| LOC_FAIL_Q20_REV | FAIL | -0.262 | +0.251 | +0.247 | -0.411/+0.120 | -0.855 |
| A_CONT | FAIL | +0.042 | -0.070 | -0.129 | -0.237/-0.143 | +0.362 |
| IMPACT_Q80_CONT | FAIL | +0.232 | +0.145 | +0.115 | +0.113/+0.032 | +1.022 |
| BREAKOUT_CONT | FAIL | +0.149 | +0.083 | +0.175 | +0.164/+0.194 | +0.965 |
| RANGE_IMPACT_CONT | FAIL | +0.134 | -0.117 | -0.120 | -0.251/-0.174 | +0.587 |

## Governance

Rithmic and AMP are two representations of largely the same GC market, so cross-feed agreement is a parity/robustness check, not independent market OOS. LATE_CHECK and POST_CHECK were not used to select the winner. Any historical winner still requires a future untouched sample before promotion.
