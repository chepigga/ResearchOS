# FXArena Session & Time-of-Day Lab v001

## Verdict

**NO SESSION EDGE WORTH FILTERING — F9. Stage 2 was not executed.**

- Control: P0 N=3535, total +1848.874811R, gross MaxDD 14.415969R — PASS.
- P4b: total +2256.511804R, gross MaxDD 12.436807R.
- No session passed the pre-registered T1, T2 and T3 transition barrier.
- ContPrimary, selection, risk layer and P4b exits were untouched.

## Stage 1 — overall session diagnostics

| Session | Share | P0 EV | P4b EV | P4b total | P4b gross DD standalone | Recorded cost | TP | SL | TO | BE | Median hold | TB flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1_ASIA | 33.52% | +0.5109R | +0.6117R | +724.92R | 9.926R | 0.0883R | 22.78% | 13.16% | 29.87% | 34.18% | 68m | 35.27% |
| S2_LONDON | 34.68% | +0.6446R | +0.7802R | +956.48R | 5.387R | 0.0698R | 26.43% | 14.76% | 32.79% | 26.02% | 69m | 41.35% |
| S3_NY_OVERLAP | 25.21% | +0.4143R | +0.5278R | +470.31R | 11.000R | 0.0525R | 22.56% | 18.41% | 27.72% | 31.31% | 60m | 32.55% |
| S4_LATE_NY | 6.59% | +0.3606R | +0.4498R | +104.80R | 7.024R | 0.0562R | 7.30% | 16.74% | 43.78% | 32.19% | 81m | 25.32% |

### P4b by year

| Session | Year | N | EV | Total | Cost | TP | SL | TO | BE | Hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1_ASIA | 2023 | 308 | +0.3386R | +104.29R | 0.0937R | 15.26% | 16.88% | 29.87% | 37.99% | 66m |
| S1_ASIA | 2024 | 202 | +0.4567R | +92.26R | 0.0965R | 14.85% | 13.86% | 35.64% | 35.64% | 79m |
| S1_ASIA | 2025 | 431 | +0.8445R | +363.99R | 0.0838R | 29.93% | 9.98% | 27.15% | 32.95% | 66m |
| S1_ASIA | 2026 | 244 | +0.6737R | +164.38R | 0.0828R | 26.23% | 13.52% | 29.92% | 30.33% | 68m |
| S2_LONDON | 2023 | 308 | +0.4261R | +131.24R | 0.0610R | 18.51% | 18.51% | 27.27% | 35.71% | 62m |
| S2_LONDON | 2024 | 444 | +0.9500R | +421.81R | 0.0803R | 29.50% | 12.84% | 34.01% | 23.65% | 86m |
| S2_LONDON | 2025 | 308 | +0.8646R | +266.30R | 0.0649R | 31.17% | 12.66% | 35.71% | 20.45% | 71m |
| S2_LONDON | 2026 | 166 | +0.8261R | +137.13R | 0.0674R | 24.10% | 16.87% | 34.34% | 24.70% | 69m |
| S3_NY_OVERLAP | 2023 | 225 | +0.4510R | +101.48R | 0.0442R | 20.00% | 17.78% | 26.67% | 35.56% | 60m |
| S3_NY_OVERLAP | 2024 | 254 | +0.6295R | +159.89R | 0.0606R | 26.38% | 16.54% | 33.46% | 23.62% | 60m |
| S3_NY_OVERLAP | 2025 | 269 | +0.4265R | +114.74R | 0.0492R | 21.93% | 25.65% | 21.93% | 30.48% | 60m |
| S3_NY_OVERLAP | 2026 | 143 | +0.6587R | +94.20R | 0.0571R | 20.98% | 9.09% | 30.07% | 39.86% | 75m |
| S4_LATE_NY | 2023 | 71 | +0.4750R | +33.72R | 0.0558R | 16.90% | 8.45% | 40.85% | 33.80% | 81m |
| S4_LATE_NY | 2024 | 45 | +0.1613R | +7.26R | 0.0790R | 8.89% | 24.44% | 44.44% | 22.22% | 60m |
| S4_LATE_NY | 2025 | 47 | -0.0083R | -0.39R | 0.0310R | 0.00% | 27.66% | 38.30% | 34.04% | 60m |
| S4_LATE_NY | 2026 | 70 | +0.9173R | +64.21R | 0.0589R | 1.43% | 12.86% | 50.00% | 35.71% | 119m |

## Top-5 gross drawdown attribution

| Policy | Session | Trade share | Top-5 negative-loss share |
|---|---|---:|---:|
| P0 | S1_ASIA | 33.52% | 23.98% |
| P0 | S2_LONDON | 34.68% | 30.12% |
| P0 | S3_NY_OVERLAP | 25.21% | 40.96% |
| P0 | S4_LATE_NY | 6.59% | 4.94% |
| P4b | S1_ASIA | 33.52% | 24.12% |
| P4b | S2_LONDON | 34.68% | 28.44% |
| P4b | S3_NY_OVERLAP | 25.21% | 42.48% |
| P4b | S4_LATE_NY | 6.59% | 4.96% |

The closest block was **S3 NY_OVERLAP** under P4b: 42.48% of negative gross loss inside the top-5 drawdown episodes, but its trade share was **25.205%**, above the frozen `<=25%` limit. Its annual overrepresentation sign was also not stable: negative in 2023, positive in 2024–2025, negative in 2026.

## October 2023 canonical DD cluster

- P0 max-DD start-to-trough: 2023-10-12 14:51:00 to 2023-10-23 09:51:00.
- Trades: 17; non-TB: 14; TB: 3.
- P0 gross by non-TB: -11.415969R; TB: -3.000000R.

## T1–T3 transition barrier

| Session | T1 EV | T1 DD | T2 EV 4/4 | T2 DD 4/4 | Cost ratio | TO ratio | SL ratio | Transition |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1_ASIA | False | False | False | False | 1.248x | 0.956x | 0.862x | **False** |
| S2_LONDON | False | False | False | False | 0.987x | 1.049x | 0.966x | **False** |
| S3_NY_OVERLAP | False | False | False | False | 0.741x | 0.887x | 1.205x | **False** |
| S4_LATE_NY | False | False | False | False | 0.794x | 1.400x | 1.096x | **False** |

### Mechanical observations

- S1 Asia has the highest recorded `gross-net` drag: 1.248x the P4b average, but its EV is positive in all four years and it is not a DD-concentration block.
- S3 NY overlap has lower recorded drag, but a 1.205x SL share and dominates the 2025 DD cluster. The effect is not stable across years and narrowly misses the frozen trade-share condition.
- S4 Late NY has TO share 1.400x average, below the example 1.5x mechanical marker, and only 2025 is negative.

> Data limitation: `recorded_cost_r = gross - net`. The fixtures do not expose spread and commission as separate fields. This limitation is non-binding because no block passed T1/T2.

## Stage 2

**Not executed.** No candidate block passed all T1–T3, therefore no veto, permutation or paired bootstrap result is admissible.

Reserved but unused sampler parameters: block=20, bootstrap=5000, seed=2026072402; permutation=200, seed=2026072401. The sampler code is preserved in `run_session_timing_v001.py`.

## Diagnostic-only hourly output

The hourly table and 95% confidence intervals are included only as descriptive material. No hour-level decision or filter was made.

## Governance result

- Register as **F9: session edge worth filtering not found**.
- Session boundaries are closed for this research branch; new boundaries require a new frozen specification.
- Keep all four sessions. Do not add a time veto to v1.30 from this lab.
