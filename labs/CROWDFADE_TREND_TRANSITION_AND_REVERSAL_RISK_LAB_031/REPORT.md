# CROWDFADE_TREND_TRANSITION_AND_REVERSAL_RISK_LAB_031

## Question

Does a causal H1/H4 transition state identify reversal risk for the current CrowdFade v200 live-candidate after lowering the signal threshold to Z=2.05?

Specifically, is the state

`H1 opposite H4 + CrowdFade trade follows H4`

a stale-H4 risk state that should be de-risked?

## Frozen candidate

- Z = **2.05**
- M15 completed-close confirmation = **0.25 ATR**
- confirmation TTL = **60m**
- passive retrace = **0.60 ATR**
- limit TTL = **20m**
- SL = **4.5 ATR**
- TP = **10 ATR**
- max hold = **24h**
- max 3 trades/day
- inherited 1 ATR anti-repeat
- cost proxy = **0.5 bps**

No signal, entry or exit parameter was optimized inside this LAB.

## Trend definition

Completed bars only.

H1 / H4 state:
- UP: close > EMA50 and EMA50 > EMA50[-4]
- DOWN: close < EMA50 and EMA50 < EMA50[-4]
- otherwise NEUTRAL

Buckets:

- **ALIGNED_WITH**: H1=H4 non-neutral; trade follows both.
- **ALIGNED_COUNTER**: H1=H4 non-neutral; trade opposes both.
- **CONFLICT_FOLLOW_H1**: H1 and H4 opposite; trade follows H1.
- **CONFLICT_FOLLOW_H4**: H1 and H4 opposite; trade follows H4 and opposes H1.
- **MIXED_NEUTRAL**: all remaining states.
- **CONFLICT_ONSET**: conflict and prior completed H1 was not already in the current H1 state.

## Raw state diagnostics — 2021–2025

| State | N | EV | PF | SumR |
|---|---:|---:|---:|---:|
| ALIGNED_WITH | 618 | **+0.1117R** | **1.229** | +69.01R |
| ALIGNED_COUNTER | 457 | **+0.0118R** | **1.024** | +5.38R |
| CONFLICT_FOLLOW_H1 | 210 | +0.0399R | 1.079 | +8.38R |
| CONFLICT_FOLLOW_H4 | 65 | **+0.1389R** | **1.279** | +9.03R |
| MIXED_NEUTRAL | 292 | +0.1048R | 1.217 | +30.60R |

Historical result:

**CONFLICT_FOLLOW_H4 is not a toxic state.**

It is actually one of the stronger small buckets.

The clearly weak historical state is **ALIGNED_COUNTER**, not stale-H4 conflict.

## Raw state diagnostics — 2026 Mar–Aug shadow

| State | N | EV | PF | SumR |
|---|---:|---:|---:|---:|
| ALIGNED_WITH | 69 | **-0.0131R** | **0.973** | -0.90R |
| ALIGNED_COUNTER | 38 | +0.1166R | 1.236 | +4.43R |
| CONFLICT_FOLLOW_H1 | 26 | **+0.3483R** | **1.716** | +9.06R |
| CONFLICT_FOLLOW_H4 | 4 | **+0.6048R** | **2.203** | +2.42R |
| MIXED_NEUTRAL | 39 | +0.0541R | 1.109 | +2.11R |

2026 sample for CONFLICT_FOLLOW_H4 is only N=4, so it cannot support aggressive conclusions. But it definitely does **not** support de-risking.

### Transition onset

Historical:
- N=71
- EV **+0.1232R**
- PF **1.285**

2026:
- N=10
- EV **+0.8528R**
- PF **3.776**

Therefore the causal transition-onset state is not behaving as a reversal-danger bucket. It is behaving as an opportunity bucket in the available samples.

Do **not** boost it from this result; the 2026 sample is small.

## Risk-overlay test

Starting point was the current inherited LAB026 map:

- HIGH 1.50x
- NORMAL 1.00x
- LOW 0.75x

Then only the transition overlay changed.

### Historical

| Mode | SumR | PF | MaxDD | R/DD | +years |
|---|---:|---:|---:|---:|---:|
| LAB026 BASE | **+148.95R** | 1.167 | 23.31R | **6.391** | 5/5 |
| stale-H4 0.75x | +146.70R | 1.166 | 23.05R | 6.363 | 5/5 |
| stale-H4 0.50x | +144.44R | 1.164 | 22.80R | 6.334 | 5/5 |
| stale-H4 veto | +139.93R | 1.162 | 22.30R | 6.274 | 5/5 |
| all-conflict 0.75x | +144.60R | 1.168 | 23.86R | 6.059 | 5/5 |

Every stale-H4 de-risk variant loses return and R/DD versus leaving the state alone.

### 2026 Mar–Aug

| Mode | SumR | PF | MaxDD | R/DD | +months |
|---|---:|---:|---:|---:|---:|
| LAB026 BASE | **+15.57R** | **1.162** | 10.78R | **1.444** | 4/6 |
| stale-H4 0.75x | +14.96R | 1.156 | 10.78R | 1.388 | 4/6 |
| stale-H4 0.50x | +14.36R | 1.151 | 10.78R | 1.331 | 4/6 |
| stale-H4 veto | +13.15R | 1.139 | 10.78R | 1.219 | 3/6 |
| all-conflict 0.75x | +12.70R | 1.137 | 10.42R | 1.218 | 4/6 |

Again, transition de-risking is harmful.

## Important new finding: LAB026 sizing no longer transports cleanly to Z=2.05

At flat 1x risk, the current Z=2.05 sequence is:

### Historical flat risk
- N = 1642
- SumR = **+122.40R**
- EV = +0.0745R
- PF = 1.151
- MaxDD = **19.83R**
- R/DD = **6.174**
- 5/5 years positive

### 2026 flat risk
- N = 176
- SumR = **+17.12R**
- EV = +0.0972R
- PF = **1.198**
- MaxDD = **8.34R**
- R/DD = **2.051**

Applying the inherited LAB026 HIGH1.5/NORMAL1/LOW0.75 map:

### Historical
- SumR rises to +148.95R
- but DD rises to 23.31R
- R/DD improves only slightly: 6.174 -> 6.391

### 2026
- SumR **falls**: 17.12R -> 15.57R
- PF **falls**: 1.198 -> 1.162
- DD **rises**: 8.34R -> 10.78R
- R/DD **falls sharply**: 2.051 -> 1.444

This matters because LAB026 was validated on Z=2.50. Lowering Z to 2.05 changes the trade population enough that the old quality multipliers are no longer transport-safe.

## Verdict

### Hypothesis: stale H4 during H1/H4 conflict is dangerous

**FAIL.**

There is no evidence to de-risk or veto `CONFLICT_FOLLOW_H4`.

Both historical and 2026 direction of effect is opposite to the hypothesis.

### Transition state

**Useful diagnostic, but not a risk veto.**

Conflict onset is positive in both samples and especially strong in 2026, though sample size is too small for risk boosting.

### Current v200 risk map

**LAB026 must be revalidated after the Z change to 2.05.**

For the current Z2.05 candidate, flat risk is materially cleaner than inherited LAB026 sizing in 2026.

## Recommended next step

Run a dedicated **CROWDFADE_Z205_QUALITY_RISK_RECALIBRATION_LAB_032**.

Freeze:
- Z=2.05
- entry/exit unchanged
- no new signal filters

Test only conservative sizing:
- flat 1/1/1
- old 1.5/1/0.75 control
- 1.25/1/0.75
- 1.25/1/1
- 1/1/0.75

Selection priority:
1. 5/5 positive years
2. 2026 stability
3. MaxDD
4. R/DD
5. monthly consistency
6. no frequency change

Do not optimize EMA periods or transition thresholds.

## Limitations

- BTCUSDT lineage only.
- Historical = 2021–2025 discovery/research.
- 2026 Mar–Aug is reused forward-shadow/stress, not pristine OOS.
- September 18 live trades are not in the released flow archive, so they are not included in the research sample.
- Risk outputs are normalized R sequences, not broker-specific daily-DD/margin simulations.
