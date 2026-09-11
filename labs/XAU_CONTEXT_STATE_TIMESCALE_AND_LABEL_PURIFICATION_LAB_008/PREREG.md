# XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008 — PREREG

## Objective
Diagnose **when** each frozen H4 Context label is informative on XAUUSD and whether its semantics become cleaner when the current label is the actual score winner rather than a hysteresis-inherited state. This is not a trading-edge test and does not use TP/SL, EV, PF, sizing, or trade selection.

This lab follows LAB007, which found insufficient 24h semantic separation and a very rare `REVERSAL` state. LAB008 is a preregistered reused-history refinement; it may suggest a better interpretation or future redesign, but it cannot validate a redesigned indicator on fresh data.

## Frozen data and router
- Canonical XAUUSD M1 release asset: `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- Required SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Router logic, scores, smoothing, hysteresis, weights and four labels are frozen from `CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001` with only the already-audited technical parity hotfixes used in LAB007.
- States: `EXPANSION`, `PULLBACK`, `REVERSAL`, `RANGE`.
- A state is usable only at H4 close (`available_time = H4 open + 4h`).

## Primary sampling unit
Primary sample = first causally available H4 bar of each contiguous state episode, exactly as in LAB007.

Secondary diagnostics:
1. every eligible H4 state bar;
2. episode-age buckets: `ONSET=1`, `EARLY=2–3`, `MATURE>=4` H4 bars since state onset.

No secondary sample may override the primary timescale verdict.

## Frozen horizons
Evaluate all outcomes at **4h, 8h, 12h, 24h, 48h** after state availability. No post-result horizon insertion or deletion is allowed.

## Frozen forward metrics
At each observation, reference price and ATR14(H4) are known at state availability. Forward windows begin only after availability.

For every horizon H compute:
- `range_atr_H = (future max high - future min low) / ATR14`;
- `abs_close_atr_H = abs(close_H - ref) / ATR14`;
- `contained_1atr_H`: neither +1 ATR nor -1 ATR touched;
- `two_sided_1atr_H`: both +1 ATR and -1 ATR touched;
- `momentum_flip_H`: H close return opposite already-known pre-state 12h momentum;
- `bias_follow_H`: H close return in already-known frozen Context bias direction;
- `bias_signed_close_atr_H = bias_dir * (close_H-ref)/ATR14`.

## State-semantic contrasts by horizon
The following four contrasts are frozen before outcomes:

### EXPANSION
Primary semantic contrast: `mean(range_atr_H | EXPANSION) - mean(range_atr_H | RANGE)`.
Expected sign: positive.
Secondary: absolute terminal displacement difference, expected positive.

### RANGE
Primary semantic contrast: `P(contained_1atr_H | RANGE) - P(contained_1atr_H | EXPANSION)`.
Expected sign: positive.
Secondary: two-sided 1 ATR probability should not exceed Expansion; descriptive only.

### REVERSAL
Primary semantic contrast: `P(momentum_flip_H | REVERSAL) - P(momentum_flip_H | EXPANSION)`.
Expected sign: positive.
Because LAB007 found very few Reversal episodes, N is always shown and no low-N result may be called validated.

### PULLBACK
Primary semantic contrast: `P(bias_follow_H | PULLBACK) - 0.50` among non-neutral Context-bias observations.
Expected sign: positive.
Secondary: mean `bias_signed_close_atr_H`, expected positive.
We do not reuse RANGE as the Pullback comparator because LAB007 showed RANGE usually has neutral bias and therefore an unusably tiny denominator.

## Natural-timescale rule
For each state, weekly-cluster bootstrap the primary semantic contrast at all five frozen horizons using 5,000 draws and seed `2026091108`.

Define:
- `confirmed_horizon` = the **earliest** frozen horizon whose observed contrast is positive and whose 95% weekly-cluster bootstrap lower bound is > 0;
- `peak_observed_horizon` = horizon with the largest observed primary contrast, descriptive only;
- if no horizon is confirmed, `confirmed_horizon = NONE`.

This rule is diagnostic. It does not authorize changing the indicator timeframe or trading horizon.

## Label-purity audit
The router already emits the four raw state scores. For each H4 bar compute the raw score winner and top-vs-second score gap.

Frozen, outcome-independent purity classes:
- `STRONG_PURE`: current hysteresis label equals raw score winner AND raw winner gap >= 10 score points;
- `WEAK_PURE`: current label equals raw score winner AND raw winner gap < 10;
- `INHERITED_CONFLICT`: current hysteresis label is not the current raw score winner.

The 10-point strong-purity boundary is fixed from the router's existing switching-gap scale (5–12 points), not from outcomes.

For each state and horizon report the state-appropriate primary semantic metric by purity class. The preregistered purification contrast is:
`STRONG_PURE - NOT_STRONG`, oriented so positive always means cleaner label semantics:
- Expansion: `range_atr` higher is cleaner;
- Range: `contained_1atr` higher is cleaner;
- Reversal: `momentum_flip` higher is cleaner;
- Pullback: `bias_follow` higher is cleaner.

A state has `PURITY_SUPPORTED` only if:
1. STRONG_PURE and NOT_STRONG each have >=20 valid primary observations at the tested horizon;
2. expected-sign observed contrast is positive at >=3 of 5 frozen horizons;
3. at least one of those positive horizons has weekly-bootstrap 95% CI lower bound > 0.
Otherwise it is `PURITY_NOT_CONFIRMED`; if sample counts are insufficient, `PURITY_UNDERPOWERED`.

## Episode-age audit
Using all eligible H4 state bars, report each state metric by `ONSET`, `EARLY`, `MATURE`. This answers whether a label becomes semantically cleaner only after persistence. It is descriptive only and cannot change the verdict in this lab.

## Time transfer
For each state-semantic primary contrast and each horizon, report effect sign separately for 2023, 2024, 2025 and 2026 YTD. 2022 is shown but excluded from transfer because it is partial and contains warm-up.

For a confirmed horizon to be called `TIME_TRANSFERRED`, expected-sign contrast must also be positive in >=3/4 eligible full-year slices. Otherwise it is `TIME_UNSTABLE`.

## Overall interpretation verdict
This lab is about interpretability, not alpha.

- `CONTEXT_LABELS_HAVE_USABLE_TIMESCALES` if at least 3 of 4 states have a confirmed horizon, and at least 2 of those are TIME_TRANSFERRED.
- `CONTEXT_LABELS_PARTIALLY_TIMESCALE_SPECIFIC` if 1–2 states have a confirmed horizon, or >=3 confirm but fewer than 2 time-transfer.
- `CONTEXT_LABELS_REQUIRE_REDESIGN` if no state has a confirmed horizon.

Purity findings are reported separately and never rescue a failed timescale verdict.

## Anti-overfit rules
- No router threshold, weight, score, smoothing or hysteresis change in LAB008.
- No state renaming after outcomes inside this lab.
- No outcome-driven purity threshold search.
- No choosing a different primary metric after results.
- No treating peak-observed horizon as confirmed unless its CI rule passes.
- Any proposed redesign from LAB008 must be frozen in a later lab and tested separately.