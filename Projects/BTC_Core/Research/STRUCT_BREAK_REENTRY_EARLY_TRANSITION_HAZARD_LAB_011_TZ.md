# STRUCT_BREAK_REENTRY_EARLY_TRANSITION_HAZARD_LAB_011 — preregistration

**Date:** 2026-08-25
**Branch:** `lab/btc-struct-break-regime-004`

## Question
Can the transition from `LOW -> recovery/scratch -> renewed impulse` be detected early enough to support a fresh 1.5R trade, before the 30-minute HIGH confirmation used in LAB009B/LAB010 consumes too much excursion?

## Frozen upstream population
- Canonical STRUCT_BREAK v002.
- LOW30 = frozen LAB008 classifier.
- Re-arm only after LAB009A recovery/scratch.
- DEV = 2019-09..2022-12.
- VAL = 2023-01..2025-12.
- 2026 excluded.

## Event clock and causality
- Primary data: BTCUSDT M5.
- Scratch bar itself is excluded because part of its OHLC may precede the scratch fill.
- Observation begins with the next fully closed M5 bar.
- Candidate decision clock: every 5 minutes from 15 through 60 minutes of post-scratch observation.
- Entry occurs at the next M5 open after a qualifying transition score. One re-entry maximum.

## Frozen feature family
No new indicators. Only response variables already validated in LAB008, measured on rolling 5m and 15m windows relative to the original broken/entry level and original risk scale:
1. `NET_R` — directional net progress.
2. `MAE_R` — adverse excursion.
3. `CLOSEBACK_FRAC` — fraction of closes back through the old broken level.
4. `DIR_CLOSE_FRAC` — fraction of directional candle closes aligned with the trade side.

The primary model is a standardized logistic regression (`C=0.3`) trained only on DEV candidate snapshots to predict whether a fresh trade from the next M5 open reaches +1.5R before -1R within 24h. Each setup receives equal total training weight across its candidate snapshots.

## Trigger
- Threshold = DEV 67th percentile of model score (top third), frozen before VAL.
- Trigger = first score crossing at/above threshold from the 15m observation point through 60m.
- If no crossing by 60m: no re-entry.

## Fresh trade geometry
Primary geometry only:
- stop = 1.0 × ATR14(M5) from fresh entry;
- TP = 1.5 × stop distance;
- cost = 0.06R;
- no BE/trailing in primary test.

This uses the simplest preregistered fresh-risk branch from LAB010 and isolates timing from stop-geometry mining.

## Primary outputs
- DEV/VAL N, EV, PF, TP rate, 95% bootstrap CI.
- P(TP before SL) vs cost-adjusted fair breakeven (~42.4%).
- VAL yearly EV 2023/2024/2025.
- Full adaptive portfolio EV and max DD versus canonical.
- Re-entry timing versus the old LAB009B 30m-HIGH trigger where both exist.

## Replication
Exact M1 replay for 2024-2025 using the same M5-derived trigger times and entry/stop/TP levels. No M1-based retuning.

## Promotion gate
Primary policy passes only if all are true:
1. VAL N >= 40.
2. VAL EV >= +0.10R per fresh re-entry.
3. VAL bootstrap CI lower bound > 0.
4. At least 2/3 VAL years positive.
5. VAL TP-before-SL probability > fair cost-adjusted breakeven.
6. Full adaptive portfolio improves VAL EV.
7. Adaptive max DD does not exceed canonical by >10%.

## Guardrails
- No VAL threshold tuning.
- No alternative feature mining after outcomes.
- No 2026 in verdict.
- Secondary diagnostics cannot promote the rule.
