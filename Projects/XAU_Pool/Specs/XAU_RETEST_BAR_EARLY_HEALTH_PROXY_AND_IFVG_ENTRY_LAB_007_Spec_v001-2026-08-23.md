# XAU_RETEST_BAR_EARLY_HEALTH_PROXY_AND_IFVG_ENTRY_LAB_007 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-23  
**Parents:** LAB002 → LAB003 → LAB004 → LAB005 → LAB006

## Question

LAB006 showed that future post-retest re-acceleration is a strong label for retest quality, but waiting for that confirmation destroys entry economics. LAB007 asks whether that future-health state can be predicted **at the LAB005 retest-confirmation close**, using only information already causal at that close, while preserving the LAB005 next-M1-open entry.

Primary lifecycle:

`T+3 directional state → LAB005 role-flip retest close → early-health score from completed retest bar → if selected, next-M1-open entry → frozen 1.5R/2R economics`

No future re-acceleration or future iFVG field may be used as an entry feature.

## Canonical data / embargo

- canonical input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- causal parent touch universe: frozen LAB002 `events.csv.gz`
- Discovery: retest decision time `< 2024-01-01`
- Confirmation: `2024-01-01 <= retest decision time < 2025-07-01`
- sealed holdout: `>= 2025-07-01`

No post-holdout event or price bar may be read for the reported verdict.

## Frozen parent lifecycle

Reconstruct LAB005 exactly:

- primary clock T+3;
- directional state threshold `|s3| >= 0.10 ATR_touch`;
- BACK direction = arrival side; THROUGH direction = opposite arrival side;
- same decision minute dedupe: strongest `abs(s3)` per direction, tie `MID > HIGH > LOW`; simultaneous LONG+SHORT conflict is skipped;
- retest window T+4 through T+18 inclusive (15 minutes);
- touched dynamic VWAP level zone ± `0.05 ATR_touch`;
- retest confirmation close at least `+0.03 ATR_touch` on intended side;
- first qualifying retest only;
- causal entry = next contiguous M1 open after retest-confirmation close: BUY AskOpen, SELL BidOpen.

Only filled LAB005 retests are eligible for model training/evaluation.

## Frozen future-health label — training target only

The target is LAB006 `PRIMARY_BOTH`, reconstructed causally but used **only as a supervised historical label**:

1. within the next 5 completed M1 bars after retest confirmation, a REACCEL bar exists with:
   - progress from retest close >= `+0.10 ATR` in trade direction;
   - directional real body >= `+0.05 ATR`;
   - close held >= `+0.05 ATR` on intended side of contemporaneous touched level;
2. a direction-aligned confirmed iFVG exists in the local frozen LAB006 window by that REACCEL close.

This future label is forbidden as a live feature. It exists only to train on Discovery and score Confirmation OOS.

## Features available at retest close

All continuous price features are normalized by frozen `ATR_touch`. No future bar is used.

Primary feature set:

1. `close_hold_atr` = `d*(Close[j]-Level[j])/ATR`.
2. `body_dir_atr` = `d*(Close[j]-Open[j])/ATR`.
3. `rejection_wick_atr` = lower wick for BUY / upper wick for SELL, normalized by ATR.
4. `adverse_wick_atr` = opposite wick, normalized by ATR.
5. `directional_clv` = direction-adjusted close-location value in bar range, in `[-1,+1]`.
6. `range_atr` = `(High[j]-Low[j])/ATR`.
7. `penetration_atr` = maximum retest-bar excursion through the contemporaneous touched level against intended direction.
8. `progress_1m_atr` = `d*(Close[j]-Close[j-1])/ATR`.
9. `progress_3m_atr` = `d*(Close[j]-Close[j-3])/ATR`, only from completed past bars.
10. `wait_from_decision_min` = minutes from T+3 decision to retest confirmation.
11. `existing_aligned_ifvg` = 1 only if a direction-aligned confirmed iFVG is already known by retest close inside `max(decision_i, j-5) ... j`.

No session, year, future path label, post-retest bar, news, trend, COT, RSI, ADX, volume regime, or manually selected level subset is included.

## Model — frozen before replay

Primary model is deliberately simple and fixed:

- `sklearn LogisticRegression`
- L2 penalty, `C=1.0`
- solver `lbfgs`
- max_iter `2000`
- no class weighting
- continuous features median-imputed using **Discovery medians only**
- continuous features standardized using **Discovery mean/std only**
- binary `existing_aligned_ifvg` is included without manual interaction terms
- model is fit only on Discovery filled retests
- Confirmation labels are never used for fitting, threshold selection, calibration, or feature choice.

### Frozen primary selection threshold

After fitting on Discovery, compute Discovery predicted health probabilities and freeze the numeric cutoff at the **70th percentile** (top 30% Discovery score).

Rationale is fixed ex ante: LAB006 `PRIMARY_BOTH` health prevalence was about 30%, so LAB007 asks whether retest-close information can causally recover a comparable-sized subset. The cutoff is **not** optimized on Discovery P&L, accuracy, PF, or Confirmation outcomes.

Apply this single frozen numeric cutoff unchanged to Confirmation.

Secondary diagnostics only:
- all-score deciles;
- fixed probability thresholds 0.50 / 0.60 / 0.70;
- model ablation excluding `existing_aligned_ifvg`.

These diagnostics cannot change the primary verdict.

## Economics — unchanged from LAB005

Selected signals enter at the already-frozen LAB005 next-M1-open retest entry.

- `1R = 0.50 * ATR_touch`
- hard stop = 1R from actual entry
- primary TP = 1.5R
- secondary TP = 2.0R
- max hold = 60 minutes from actual entry
- BUY exits use future Bid OHLC
- SELL exits use future Ask OHLC
- same-M1 TP+SL = conservative LOSS
- no hit = executable quote at horizon clipped to `[-1,targetR]`
- spread embedded in Bid/Ask
- commission proxy `$5 RT/lot = $0.05` XAU price equivalent
- stress: +$0.05 and +$0.10 price-equivalent RT

## Primary serial lifecycle

Deployability view = one lifecycle at a time, preserving LAB005 timing:

1. chronological deduped T+3 parent signals;
2. when flat, accept next signal and enter PENDING_RETEST;
3. while pending, ignore other signals;
4. if no retest within 15m, become flat at expiry;
5. if retest occurs, compute early-health score at retest close;
6. if score below frozen cutoff, reject and become flat after retest close;
7. if selected, enter next contiguous M1 open and hold until TP/SL/time exit;
8. ignore all other signals while position active;
9. no hedging, pyramiding, averaging, martingale.

Independent selected-signal economics are diagnostic only.

## Diagnostics

Report Discovery and Confirmation:

- health-label prevalence;
- ROC AUC and Brier score;
- selected fraction;
- future-health precision selected vs rejected;
- LAB002 directional correctness selected vs rejected;
- model coefficient table;
- existing-iFVG model ablation AUC and selection/economics;
- selected independent and serial 1.5R/2R EV, PF, TP rate, total R;
- BUY/SELL and BACK/THROUGH EV;
- yearly transfer;
- max DD, worst day, consecutive losses;
- cost stress;
- serial frequency;
- paired same-signal selected-retset EV versus unfiltered LAB005 retest baseline where appropriate.

## Frozen bootstrap

Calendar-week cluster bootstrap:
- 4000 resamples
- seed `20260823`

Primary intervals:
- Confirmation serial selected mean R;
- Confirmation selected-vs-rejected future-health precision gap;
- Confirmation selected-vs-rejected directional-correctness gap.

## Frozen gates

Primary = Confirmation / top-30%-Discovery-score cutoff / LAB005 next-open retest entry / 1.5R / serial / BASE.

- `G0_DATA_CAUSALITY`: canonical SHA valid, Bid/Ask execution fields present, all feature timestamps <= retest close, holdout false.
- `G1_MODEL_DISCRIMINATION`: Confirmation ROC AUC > 0.55 and selected future-health precision exceeds rejected precision by >= +5 pp.
- `G2_PRIMARY_POWER`: Confirmation serial selected trades >= 300 and >= 10 trades/week.
- `G3_CONFIRMATION_EV`: Confirmation serial EV > 0 and PF > 1.0.
- `G4_WEEK_CLUSTER_CI`: lower 95% weekly cluster CI of Confirmation serial mean R > 0.
- `G5_SPLIT_TRANSFER`: Discovery and Confirmation serial selected EV both > 0.
- `G6_2R_SURVIVAL`: Confirmation selected 2R serial EV >= 0.
- `G7_DIRECTION_BREADTH`: Confirmation BUY EV > 0 and SELL EV > 0.
- `G8_BRANCH_BREADTH`: Confirmation BACK EV > 0 and THROUGH EV > 0.
- `G9_PROP_DD_PROXY`: Confirmation max DD <= 20R and worst calendar day > -16R.
- `G10_COST_STRESS`: Confirmation 1.5R EV remains > 0 under additional $0.10 price-equivalent stress.
- `G11_EARLY_SELECTION_UPLIFT`: selected directional correctness exceeds rejected correctness by >= +5 pp in both Discovery and Confirmation.

## Verdicts

- `GO_TO_REPLICATION`: all G0..G11 pass.
- `EARLY_HEALTH_EDGE_NARROW`: G1/G3/G4/G5/G11 pass but one power/breadth/stress/DD gate fails.
- `EARLY_HEALTH_PREDICTIVE_NOT_PROFITABLE`: G1 and G11 pass but G3 fails.
- `NO_EARLY_HEALTH_PROXY`: G1 or G11 fails.
- `INVALID_CAUSALITY_DATA`: G0 fails.

No automatic holdout opening, EA creation, or live allocation.

## Anti-overfit

LAB007 does not change after outcomes:
- T+3 ±0.10 state rule;
- 15m LAB005 retest lifecycle;
- retest zone/close rule;
- future-health label definition;
- feature list or feature signs;
- logistic family / C / solver;
- top-30% Discovery-score selection rule;
- stop/targets/hold/costs;
- MID/HIGH/LOW, BUY/SELL, BACK/THROUGH subsets;
- session/news/volatility filters.

If LAB007 fails, later work must change one explicit causal dimension in a new preregistered LAB.
