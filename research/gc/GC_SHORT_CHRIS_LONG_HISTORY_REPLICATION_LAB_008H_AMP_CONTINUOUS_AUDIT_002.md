# GC SHORT CHRIS LONG-HISTORY REPLICATION LAB008H — AMP @GCE CONTINUOUS AUDIT 002

**Status:** `LONG_HISTORY_REPLICATION_FAIL_POST10_Q50_NOT_OOS`

This is a companion historical replication using AMP/CQG `@GCE` continuous-symbol history. Frozen Chris/AEIF signal logic and frozen LAB006 POST10/Q50 decision gate were not retuned. This does **not** replace the original preregistered causal front-contract stitching specification.

## Raw source audit

Input compact archive: `@GCE_LAB008H_COMPACT.zip`

- Original raw CSV size before compaction: 17.30 GB
- Input CSV files: 568
- Total raw rows: 174,022,818
- Exclusive directional rows retained: 27,025,331
- BUY-only: 13,456,208
- SELL-only: 13,569,123
- DUAL excluded: 148,947
- NEITHER excluded: 146,848,540
- Invalid excluded: 0
- First directional timestamp: 2025-01-01 23:00 UTC
- Last directional timestamp: 2026-09-15 23:55 UTC
- Reconstructed directional M1 bars: 330,116

The continuous symbol has strongly intermittent historical aggressor-flag coverage. Directional-tag-rich windows alternate with long sparse windows around contract cycles. Therefore a quality-controlled companion audit was run only on directional-rich windows and rolling state was reset between windows.

## Objective data-quality segmentation

Primary audit threshold: weekday exclusive-directional rows >= 20,000/day. This is a feed-quality threshold, not a strategy threshold. It identifies the clearly bimodal active-contract windows in `@GCE`.

Nine directional-rich windows were found:

1. 2025-01-02 → 2025-01-29
2. 2025-02-26 → 2025-03-27
3. 2025-04-28 → 2025-05-28
4. 2025-06-26 → 2025-07-29
5. 2025-10-29 → 2025-11-25
6. 2026-01-02 → 2026-01-28
7. 2026-02-25 → 2026-03-26
8. 2026-04-28 → 2026-05-27
9. 2026-06-25 → 2026-07-28

Total directional-rich calendar coverage: ~272 days (~8.9 months), despite a 20.5-month calendar span.

Robustness checks at 10k and 30k weekday directional-row thresholds produced the same core conclusion.

## Frozen logic used

Chris/AEIF SHORT seed unchanged:

- extreme BUY aggression (`delta_frac >= prior240 Q90`, `buy_vol >= prior240 Q75`)
- upper-auction location (`buy_loc >= prior240 Q75 buy_loc`)
- weak result (`BUY impact <= prior BUY-A impact Q20`)
- first bearish confirmation within next 2 contiguous M1 bars
- entry at next contiguous M1 open

POST10 decision gate unchanged:

- checkpoint = entry +10m
- feature = `cp10_dist_seed_high`
- minimum 8 prior eligible events
- threshold = expanding median Q50 of prior eligible feature values
- selected if current feature >= prior Q50
- primary target = residual +10→+20 / seed ATR
- secondary target = residual +10→+30 / seed ATR

Rolling GC feature state was reset between data-quality windows; 240 completed M1 bars were required before the frozen 240-bar quantiles become available naturally.

## Primary 20k quality-audit result

- Frozen Chris events: 234
- Complete POST10 primary events: 224
- OOF after 8-event warmup: 216
- Selected: 114
- Rejected: 102

Primary residual +10→+20 ATR:

- all OOF EV: **+0.1836 ATR**, WR **53.24%**
- selected EV: **+0.1150 ATR**, WR **50.88%**
- rejected EV: **+0.2603 ATR**, WR **55.88%**
- selected uplift vs all OOF: **-0.0686 ATR**

Secondary residual +10→+30 ATR among selected:

- N = 111
- EV: **+0.4037 ATR**
- WR: **51.35%**

Selected primary by year:

- 2025: N=61, EV **-0.1330 ATR**
- 2026: N=53, EV **+0.4003 ATR**

## Robustness to feed-quality threshold

### 10k/day

- selected N=115
- selected primary EV +0.1228 ATR
- selected WR 51.30%
- rejected EV +0.2526 ATR
- 2025 selected EV -0.1330 ATR

### 20k/day

- selected N=114
- selected primary EV +0.1150 ATR
- selected WR 50.88%
- rejected EV +0.2603 ATR
- 2025 selected EV -0.1330 ATR

### 30k/day

- selected N=113
- selected primary EV +0.0952 ATR
- selected WR 50.44%
- rejected EV +0.2603 ATR
- 2025 selected EV -0.1330 ATR

Conclusion is stable across reasonable data-quality thresholds: the frozen POST10/Q50 selector does not reproduce its earlier 40-day uplift.

## LAB008H prereg gate mapping

Against the original Stage-B gates, this companion source gives:

1. usable stitched coverage >=24 months — **FAIL** (calendar span ~20.5 months; quality-rich coverage ~8.9 months)
2. frozen Chris events >=75 — **PASS** (234)
3. OOF POST10 >=50 — **PASS** (216)
4. selected >=25 — **PASS** (114)
5. selected primary EV >0 — **PASS** (+0.1150 ATR)
6. selected primary EV > all-OOF by >=+0.10 ATR — **FAIL** (-0.0686 ATR uplift)
7. selected primary EV > rejected — **FAIL** (+0.1150 vs +0.2603)
8. selected WR >=55% — **FAIL** (50.88%)
9. selected secondary EV >=0 — **PASS** (+0.4037 ATR)
10. at least 3 calendar years with >=5 selected and positive primary EV — **FAIL** (only 2025/2026; 2025 negative)
11. no calendar year >50% selected events — **FAIL** (2025 61/114 >50%)

## Decision

The long-history evidence does **not** validate the LAB006 POST10/Q50 selector. The very strong 40-day result does not generalize on the longer AMP `@GCE` historical sample.

The underlying Chris event family is not completely dead: all-OOF primary residual remains modestly positive (+0.184 ATR), and selected secondary +10→+30 residual is positive. But the frozen Q50 selector specifically fails because it is worse than both the all-OOF baseline and the rejected set, has ~51% WR, and is negative in 2025.

Do not promote `Chris/AEIF SHORT + POST10 Q50` to production EA logic from this evidence. If continued, next research should treat the frozen Q50 selector as rejected and separately investigate whether the raw Chris event family has a simpler, more stable delayed-resolution edge without using the failed gate. Any such work must be a new LAB and not a rescue mutation of LAB008H.
