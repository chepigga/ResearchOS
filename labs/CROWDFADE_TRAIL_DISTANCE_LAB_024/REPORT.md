# CROWDFADE_TRAIL_DISTANCE_LAB_024

## Question

What happens if CrowdFade keeps the frozen 4.5 ATR hard stop but activates continuous trailing after +1R MFE with trail distances:

- 0.5R
- 1.0R
- 2.5R

No signal, entry, TP, hold, BE, weekday/hour, or risk-multiplier changes.

## Causal mechanics

- hard SL = 4.5 ATR = 1R
- TP = 10 ATR
- trailing activates after +1R MFE
- trailing stop updates continuously at available path resolution
- historical: completed 1m bars, effective next bar
- 2026: completed 1-second OHLC, effective next second
- early exits change future reachable signals, so each mode is a full sequential rerun

## Historical 2021–2025

| Mode | N | WR | EV | PF | SumR | MaxDD | R/DD | +years |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| No trail | 1227 | 43.85% | **+0.1064R** | **1.210** | **+130.60R** | **13.50R** | **9.675** | 5/5 |
| Trail 0.5R | 1348 | 52.67% | +0.0451R | 1.105 | +60.75R | 15.00R | 4.050 | 5/5 |
| Trail 1.0R | 1298 | 52.23% | +0.0588R | 1.136 | +76.31R | 14.61R | 5.223 | 5/5 |
| Trail 2.5R | 1228 | 43.24% | +0.1027R | 1.204 | +126.15R | 14.44R | 8.738 | 5/5 |

Historical verdict:

- 0.5R trail: strong FAIL.
- 1.0R trail: strong FAIL.
- 2.5R trail: much less destructive, but still inferior to no trail:
  - EV 0.1027 vs 0.1064
  - PF 1.204 vs 1.210
  - SumR 126.15 vs 130.60
  - DD 14.44 vs 13.50
  - R/DD 8.74 vs 9.68

Exit mix:

- No trail: SL 587, TP 253, TIME 387
- 0.5R: SL 545, TRAIL 575, TP 43, TIME 185
- 1.0R: SL 531, TRAIL 363, TP 168, TIME 236
- 2.5R: SL 502, TRAIL 95, TP 251, TIME 380

0.5R and 1R materially truncate TP/right-tail behavior.

## 2026 seconds forward-shadow

| Mode | N | WR | EV | PF | SumR | MaxDD | R/DD | +months |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| No trail | 136 | 47.06% | +0.2111R | 1.467 | +28.71R | 6.49R | 4.424 | 6/6 |
| Trail 0.5R | 150 | 53.33% | +0.0835R | 1.210 | +12.52R | 7.18R | 1.743 | 5/6 |
| Trail 1.0R | 141 | 53.19% | +0.1324R | 1.332 | +18.67R | 7.60R | 2.456 | 5/6 |
| Trail 2.5R | 136 | 47.06% | **+0.2191R** | **1.494** | **+29.80R** | **6.39R** | **4.665** | **6/6** |

2026 2.5R trail versus no trail:

- same N = 136
- same WR = 47.06%
- EV +3.8%
- PF improves 1.467 → 1.494
- SumR +1.09R
- DD improves 6.49R → 6.39R
- R/DD improves 4.424 → 4.665
- all 6 months remain positive

Only 10 exits are changed to trailing in 2026.

## Interpretation

The result supports the existing right-tail thesis.

### 0.5R distance

At +1R activation, the stop is placed around +0.5R from entry.

This aggressively locks small winners and destroys large-winner capture.

Historical WR rises, but EV, PF, SumR and R/DD collapse.

### 1.0R distance

At +1R activation, the stop is approximately at entry / breakeven distance before costs.

This is effectively a dynamic early-profit protection regime and remains strongly harmful.

### 2.5R distance

At +1R activation, a 2.5R trailing distance initially does not tighten beyond the original -1R hard stop.

It only becomes protective after MFE expands further:

- around +1.5R MFE it begins to improve the hard stop,
- around +2.5R MFE it reaches approximately entry,
- around +3.5R MFE it locks about +1R.

Therefore it preserves most of the right tail.

This explains why:
- historical performance is close to baseline,
- 2026 can improve slightly.

## Verdict

Production core remains:

**TRAILING = OFF**

Strong rejection:

- 0.5R trailing
- 1.0R trailing

New watch candidate:

**2.5R trailing distance, activated at +1R MFE**

Why watch-only:

- 2026 improves across EV/PF/DD/R-DD and keeps 6/6 positive months;
- historical 5-year performance is still slightly worse than no trail;
- 2026 is reused forward-shadow, not pristine OOS;
- 1-second OHLC is not true tick sequence.

Next clean validation if pursued:

- baseline vs fixed 2.5R trail only;
- leave-one-year-out;
- contribution / changed-exit analysis;
- fresh untouched forward;
- true broker/tick execution if available.

Full equity sequences:

- `output/equity_sequence_2021_2025.csv`
- `output/equity_sequence_2026.csv`
