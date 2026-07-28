# AK47_POST_M3_MICROSTRUCTURE_PROFILE_LAB_001

**Date:** 2026-07-29  
**Status:** Phase A complete — one WATCH profile, no production gate  
**Episodes:** 116/116 with native M1 Bid/Ask coverage  
**Exact CopyTicks joins:** 9 only

## Research question
Why does the EA often re-enter incorrectly after `M3_GIVEBACK_EXIT`, and can a profitable pre-entry microstructure profile be identified without repeated MT5 runs?

## Data and causal boundary
The canonical full source is a native **M1 Bid/Ask bar stream**, not raw tick-by-tick history. It contains minute OHLC, Ask OHLC, spread min/max/mean/close and tick volume.

Features allowed for profiling were calculated strictly before the entry minute:

- direction-adjusted movement over 5/10/30 minutes;
- path efficiency;
- price range;
- direction alternation;
- spread level and spread shock;
- volume shock;
- existing H1 regime features from Phase A.

Entry-minute and post-entry fields were used only as labels/diagnostics. They are not valid gate inputs.

## Baseline post-M3 population
- N: **116**
- EV: **-0.016R**
- Sum: **-1.88R**
- WR: **40.5%**

## Unsupervised state result
Silhouette selected two pre-entry geometry clusters.

| micro_state | N | EV_R | Sum_R | WR |
|---:|---:|---:|---:|---:|
| 0 | 23 | +0.162 | +3.734 | 34.8% |
| 1 | 93 | -0.060 | -5.615 | 41.9% |

The apparently positive cluster is **not valid**: all 23 observations occur in January–April and the state disappears entirely in May–July. It is a time/regime marker, not a reusable gate.

## Main explanatory finding
The most interesting non-linear feature is **30-minute direction alternation**.

Exploratory WATCH profile:

```text
0.50 < pre30_alternation <= 0.5714286
```

Interpretation: over the preceding 30 one-minute closes, direction changes are neither rare nor excessive. The approach is an organised two-sided auction rather than a one-way climax or chaotic chop.

| Split | Group | N | EV_R | Sum_R | WR |
|---|---|---:|---:|---:|---:|
| Discovery Jan-Apr | WATCH | 22 | +0.452 | +9.942 | 54.5% |
| Discovery Jan-Apr | Other | 59 | -0.232 | -13.714 | 32.2% |
| Temporal check May-Jul | WATCH | 14 | +0.651 | +9.118 | 64.3% |
| Temporal check May-Jul | Other | 21 | -0.344 | -7.228 | 33.3% |
| Full | WATCH | 36 | +0.529 | +19.060 | 58.3% |
| Full | Other | 80 | -0.262 | -20.941 | 32.5% |

Full-sample profile-minus-other EV delta: **+0.791R**. Bootstrap 95% delta CI: **[+0.237, +1.349]R**.

Direction split is symmetric in this sample:

- BUY: N=18, EV about +0.610R;
- SELL: N=18, EV about +0.449R.

## Why this is not yet GO
The threshold emerged during exploratory inspection of several features and buckets. The May–July check is encouraging, but it is not a sealed untouched OOS dataset because feature families were investigated in the same research session.

Monthly performance is uneven: February, March and May remain negative. Therefore the profile is a **candidate explanatory mechanism**, not a final trading rule.

## Tick-level audit limitation
Only 9 post-M3 entries exactly matched the separate CopyTicks run. This is insufficient to test millisecond ordering or 1–30 second acceptance reliably. No tick-level conclusion is claimed.

## Current explanation of bot behaviour
The incorrect re-entry is not explained by elapsed time after M3. It is more consistent with the shape of the approach to the next breakout:

- too directional can represent climax/exhaustion;
- too alternating can represent chaotic balance;
- a moderate alternation band may represent an orderly auction capable of producing accepted expansion.

## Verdict
- Universal post-M3 cooldown: **NO-GO**.
- Unsupervised micro-cluster gate: **NO-GO**.
- Moderate 30-minute alternation profile: **WATCH**.
- Production implementation: **NOT ALLOWED YET**.

## Required next test
Create frozen lab `AK47_POST_M3_AUCTION_RHYTHM_VALIDATION_LAB_001` with the only frozen rule:

```text
0.50 < pre30_alternation <= 4/7
```

Test on an untouched segment or a different canonical EA run using exact Python replay, permutation/max-stat control, monthly/yearly and BUY/SELL stability, matched non-M3 comparison, and only then one MT5 confirmation run.