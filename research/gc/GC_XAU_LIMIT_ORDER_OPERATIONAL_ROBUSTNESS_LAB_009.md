# GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009

**Status: POST_DISCOVERY_OPERATIONAL_ROBUSTNESS_NOT_OOS**

Primary operational mode: **ONE_ACTIVE_SETUP**. Primary cost stress: **+0.05R adverse cost per filled trade** on top of already embedded FTMO spread.

| Candidate | Cohort | Accept | Fills | EV/orig | EV/fill | PF | MaxDD R | +weeks | LATE EV | DD @0.5% | Worst day @0.5% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D1.00_E3M | COMMON_CLOCK | 86.5% | 90 | +0.075 | +0.205 | 1.33 | 8.40 | 4/6 | +0.053 | 4.20% | -2.10% |
| D1.00_E3M | AMP_ALL | 86.4% | 105 | +0.079 | +0.209 | 1.34 | 8.40 | 5/7 | +0.068 | 4.20% | -2.10% |
| D1.00_E5M | COMMON_CLOCK | 82.4% | 107 | +0.057 | +0.131 | 1.21 | 12.24 | 4/6 | -0.014 | 6.12% | -2.10% |
| D1.00_E5M | AMP_ALL | 82.4% | 126 | +0.057 | +0.127 | 1.20 | 12.24 | 5/7 | +0.007 | 6.12% | -2.10% |
| D0.75_E3M | COMMON_CLOCK | 86.5% | 107 | +0.045 | +0.103 | 1.15 | 9.86 | 3/6 | +0.011 | 4.93% | -2.10% |
| D0.75_E3M | AMP_ALL | 86.7% | 125 | +0.058 | +0.129 | 1.19 | 10.02 | 5/7 | -0.008 | 5.01% | -2.10% |
| D0.75_E5M | COMMON_CLOCK | 82.9% | 123 | +0.035 | +0.069 | 1.10 | 11.61 | 3/6 | -0.031 | 5.80% | -2.10% |
| D0.75_E5M | AMP_ALL | 83.2% | 144 | +0.046 | +0.089 | 1.13 | 13.21 | 4/7 | -0.038 | 6.61% | -2.10% |

## Cost stress — COMMON_CLOCK / ONE_ACTIVE_SETUP

| Candidate | 0R | 0.025R | 0.05R | 0.10R |
|---|---:|---:|---:|---:|
| D1.00_E3M | +0.094 | +0.084 | +0.075 | +0.057 |
| D1.00_E5M | +0.079 | +0.068 | +0.057 | +0.035 |
| D0.75_E3M | +0.067 | +0.056 | +0.045 | +0.023 |
| D0.75_E5M | +0.060 | +0.047 | +0.035 | +0.010 |

## Robustness gate

- **D1.00_E3M PASS** — COMMON EV +0.075R/original signal, PF 1.33, DD@0.5% 4.20%.
- **D0.75_E3M PASS** — COMMON EV +0.045R/original signal, PF 1.15, DD@0.5% 4.93%.

Descriptive operational leader: **D1.00_E3M**.

## Governance

This remains post-discovery. A passing operational candidate can be frozen for forward/OOS shadow testing, but LAB009 itself cannot certify production profitability.
