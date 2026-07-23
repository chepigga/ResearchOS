# FXArena Entry Lab v001 — Market / Limit / Hybrid Tournament

## Verdict

**F10 — `market @ D3+60s` remains optimal. Entry layer is closed.**

No E1–E6 arm passed EL1–EL5. The result uses EV per all 3535 signals; missed entries remain 0R rows. Stop-order arms were not tested.

## Gate 0 — exact P4b replay

- Ordered signals: **3535 / 3535**, exact episode order.
- Entry max difference: `0`; risk max difference: `0`.
- Exit-time differences: **0**.
- Total net: **+2256.511802R** versus frozen +2256.511804R; difference -0.00000192R.
- Gross MaxDD: **12.436807R** versus frozen 12.436807R.

## Tournament table — denominator is always 3535 signals

| Arm | Total | Δ vs E0 | EV/signal | Fill | Missed | Missed TB | Gross DD | Neg. months | Price improvement | Entry-cost saving | EL1 | EL2 | EL3 | EL4 | EL5 | PASS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0 | +2256.51R | +0.00R | +0.6383R | 100.00% | 0 | 0.00% | 12.437R | 0 | +0.00R | +0.00R | — | — | — | — | — | — |
| E1 | +323.52R | -1932.99R | +0.0915R | 34.23% | 2325 | 64.05% | 20.584R | 10 | -339.14R | +94.65R | False | False | False | False | False | False |
| E2 | +307.43R | -1949.08R | +0.0870R | 31.63% | 2417 | 66.95% | 20.991R | 11 | -296.55R | +94.65R | False | False | False | False | False | False |
| E3 | +1847.72R | -408.79R | +0.5227R | 93.49% | 230 | 3.92% | 16.699R | 0 | -638.27R | -19.44R | False | False | True | False | True | False |
| E4 | +1551.17R | -705.35R | +0.4388R | 100.00% | 0 | 0.00% | 17.131R | 2 | -596.92R | +23.88R | False | False | False | False | True | False |
| E5 | +1829.93R | -426.58R | +0.5177R | 100.00% | 0 | 0.00% | 15.940R | 0 | -317.49R | -5.11R | False | False | True | False | True | False |
| E6 | +1648.59R | -607.92R | +0.4664R | 100.00% | 0 | 0.00% | 17.000R | 1 | -448.29R | +10.57R | False | False | False | False | True | False |

## EL4 paired moving-block bootstrap

Block 20, 5000 iterations, shared indices, seed `2026072404`.

| Arm | P(total > E0) | P(DD > E0+0.5R) |
|---|---:|---:|
| E1 | 0.00% | 87.08% |
| E2 | 0.00% | 88.00% |
| E3 | 0.00% | 65.50% |
| E4 | 0.00% | 82.50% |
| E5 | 0.00% | 64.02% |
| E6 | 0.00% | 88.12% |

## TB versus non-TB

E0 TB contributes **+1599.24R (70.9%)** from 1274 signals, EV +1.255R. Non-TB contributes +657.28R, EV +0.291R.

| Arm | Branch | Signals | Fill | Total | EV/signal | Missed | Missed E0 value |
|---|---|---:|---:|---:|---:|---:|---:|
| E0 | nonTB | 2261 | 100.00% | +657.28R | +0.2907R | 0 | +0.00R |
| E0 | TB | 1274 | 100.00% | +1599.24R | +1.2553R | 0 | +0.00R |
| E1 | nonTB | 2261 | 33.26% | -0.25R | -0.0001R | 1509 | +476.14R |
| E1 | TB | 1274 | 35.95% | +323.77R | +0.2541R | 816 | +955.80R |
| E2 | nonTB | 2261 | 30.83% | -16.81R | -0.0074R | 1564 | +505.74R |
| E2 | TB | 1274 | 33.05% | +324.24R | +0.2545R | 853 | +998.52R |
| E3 | nonTB | 2261 | 92.04% | +432.66R | +0.1914R | 180 | -51.62R |
| E3 | TB | 1274 | 96.08% | +1415.05R | +1.1107R | 50 | +17.87R |
| E4 | nonTB | 2261 | 100.00% | +357.19R | +0.1580R | 0 | +0.00R |
| E4 | TB | 1274 | 100.00% | +1193.98R | +0.9372R | 0 | +0.00R |
| E5 | nonTB | 2261 | 100.00% | +458.48R | +0.2028R | 0 | +0.00R |
| E5 | TB | 1274 | 100.00% | +1371.45R | +1.0765R | 0 | +0.00R |
| E6 | nonTB | 2261 | 100.00% | +387.45R | +0.1714R | 0 | +0.00R |
| E6 | TB | 1274 | 100.00% | +1261.14R | +0.9899R | 0 | +0.00R |

## Missed-signal and mechanics findings

- **E1:** fills 34.23%, misses 2325 signals and **64.05% of TB**; missed E0 value is +1431.94R. EL5 disqualifies it.
- **E2:** fills 31.63%, misses 2417 signals and **66.95% of TB**; missed E0 value is +1504.26R. EL5 disqualifies it.
- **E3:** fills 93.49% and misses only 3.92% of TB. The missed set was net negative at E0 prices (-33.75R), but confirmation delay degraded entry price by -638.27R and total by -408.79R.
- **E4:** saves +23.88R of entry cost, but limit/fallback timing degrades effective entry price by -596.92R and total by -705.35R.
- **E5:** is the best participation-preserving hybrid after E3, but still loses -426.58R and raises gross DD to 15.940R.
- **E6:** the causal D3 flag fires on 46.76% of signals; routing does not rescue the hybrid and loses -607.92R.

### Level-price geometry diagnostic

- The episode level is directionally better than E0 market price for **77.11%** of signals.
- Yet E1 fills only **14.82%** of that genuinely cheaper subset within five minutes.
- In the remaining 22.89%, the literal level order is not a cheaper pullback price and fills almost immediately; this creates adverse realized entry selection.

## Replay law

- E0 is the exact frozen P4b baseline, without adding a new slippage penalty.
- New market legs use raw M1 spread of their entry minute, preserving genuine zero-spread rows, plus 1 point adverse slippage.
- Passive limit fills require at least 1 point penetration; exact touch is not a fill; fill price is the order price.
- Stop distance is fixed at `max(30pt, 1.5 × max(0.75, penetration_ATR) × ATR_touch)`.
- P4b exits are rebuilt from actual candidate entry: TB → TP3; non-TB → TP2 with BE@60; timeout 120; stop-first M1 ordering; commission 6 points.
- E5 full-position replay begins when the second half fills or falls back on the sixth minute.
- E6 uses only completed D3-available M5 features: `EFFICIENCY_5 OR BB_EXPANSION OR RANGE_EXPANSION_15`.

## Governance

- No parameter, TTL, offset, split, stop, selector, risk or exit tuning.
- `EV per fill` is not used for gates or verdict.
- Since E0 wins, no tick-validation candidate is promoted and no v1.30 entry composition is created.
- **F10 closes the Entry layer:** further market/limit/confirmation variants require genuinely new information and a new frozen hypothesis, not another timing grid.
