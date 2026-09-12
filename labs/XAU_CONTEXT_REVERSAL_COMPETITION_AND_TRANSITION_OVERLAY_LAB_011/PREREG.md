# XAU_CONTEXT_REVERSAL_COMPETITION_AND_TRANSITION_OVERLAY_LAB_011 — PREREG

## Objective
Test the architectural hypothesis suggested by LAB009–010: the Context indicator should keep a persistent main state while `REVERSAL` and `COMPRESSION` operate as independent causal transition overlays rather than competing persistent regimes.

This is a human-decision-support / indicator-semantics lab. It does **not** test trading edge, entries, TP/SL, EV, PF, position sizing, commissions, or prop-firm risk.

## Frozen source and parity
- Base lineage: completed LAB010 branch.
- Canonical XAUUSD M1 asset: release `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- Required SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Frozen H4 Context router, scores, 3-bar smoothing, hysteresis, bias and availability-time logic are unchanged.
- Previously audited runtime/parity fixes are permitted only to execute the frozen code.
- Required parity: **6,216 valid Context H4 bars and 610 frozen state episodes**.

All overlay definitions, horizons, controls and verdict gates below are frozen **before LAB011 outcomes are computed**.

---

# Part A — REVERSAL competition / overlay test

## Frozen reversal overlay
Use exactly LAB010 `R3_RAW_REVERSAL_WINNER`:
- frozen unsmoothed `score_reversal` is equal to the maximum of the four frozen unsmoothed state scores on that H4 bar;
- only the first H4 bar of each contiguous True block is an activation event.

No score threshold or cooldown search is allowed.

## Competition classification
For every R3 activation event compute the frozen 3-bar-smoothed scores that feed the router.

Each event is classified causally into exactly one bucket:
1. `ADMITTED_REVERSAL`: frozen router regime on the event bar is `REVERSAL`.
2. `SMOOTHING_SUPPRESSED`: router regime is not `REVERSAL` and the 3-bar-smoothed reversal score is not the smoothed winner.
3. `HYSTERESIS_SUPPRESSED`: router regime is not `REVERSAL` but the 3-bar-smoothed reversal score is the smoothed winner.

This classification is diagnostic only and cannot be modified after outcomes.

## Persistent main-state underlay
For overlay tests the main state is the frozen router regime when it is one of:
- `PULLBACK`
- `EXPANSION`
- `RANGE`

A suppressed R3 event necessarily retains one of these main states. `ADMITTED_REVERSAL` events are reported separately and are not part of the primary incremental-overlay test.

## Primary reversal hypothesis R-H1
Among **suppressed** R3 activation events (`SMOOTHING_SUPPRESSED` + `HYSTERESIS_SUPPRESSED`), test whether the overlay adds information beyond the persistent main state.

Primary horizon: **24h**.
Primary metric: `momentum_flip_24h`, exactly as LAB008–010: future 24h close direction opposite the already-known pre-event 12h momentum direction; zero/invalid pre-momentum excluded.

Control: non-R3 H4 bars with the **same frozen main state** (`PULLBACK`, `EXPANSION`, or `RANGE`).

The primary effect is a state-stratified premium:
- calculate event minus control flip-rate within each main state;
- aggregate state premiums weighted by suppressed-event count in that state.

Weekly cluster bootstrap resamples calendar weeks jointly and recomputes the state-stratified effect.

Eligibility:
- >=50 valid suppressed R3 events overall;
- >=10 valid events in both 2025 and 2026 YTD;
- at least 2 main-state strata each with >=10 suppressed events.

Pass:
- observed stratified 24h flip premium >0;
- bootstrap 95% CI lower bound >0;
- positive annual premium in >=3/4 years 2023–2026 when each year has >=10 valid suppressed events.

## Secondary reversal diagnostics
These cannot override R-H1:
- 8h and 12h stratified flip premiums;
- separate `SMOOTHING_SUPPRESSED` and `HYSTERESIS_SUPPRESSED` 24h premiums;
- event counts by frozen main state and calendar year;
- fraction of R3 events admitted vs suppressed;
- raw reversal-score lead over current frozen-state raw score;
- smoothed reversal-score lead over current frozen-state smoothed score.

## R-H2 — overlay usefulness across main states
At 24h, report the sign of the event-minus-control momentum-flip premium separately for `PULLBACK`, `EXPANSION`, and `RANGE`.

R-H2 passes only if:
- at least 2 eligible strata have >=20 valid suppressed events;
- at least 2 eligible strata have positive premium;
- no eligible stratum has premium <= -5 percentage points.

R-H2 is a robustness gate, not a substitute for R-H1 bootstrap significance.

---

# Part B — COMPRESSION as breakout-risk overlay

## Frozen compression overlay
Use exactly LAB010 `G1_VOL_COMPRESSION`:
`COMPRESSED_24 AND LOW_ATR`, where:
- `COMPRESSED_24`: frozen `range24_ratio < 0.85`;
- `LOW_ATR`: frozen `atr_ratio < 0.95`.

Unlike the reversal overlay, compression is a persistent condition and remains ON while the condition remains true.

## Main-state scope
Primary compression tests use only bars whose frozen main state is:
- `PULLBACK`, or
- `EXPANSION`.

`RANGE` is excluded from the primary test because LAB007–010 did not validate `RANGE` as a stable semantic state. It remains descriptive only.

## C-H1 — incremental 8h breakout risk
Primary horizon: **8h**.
Metric: `breakout_1atr_8h = 1 - contained_1atr_8h`; i.e. either +1 ATR or -1 ATR is touched within the next 8h.

Control: non-G1 bars with the **same frozen main state** (`PULLBACK` or `EXPANSION`).

Primary effect: main-state-stratified breakout-rate premium, weighted by G1 candidate count within each state.

Eligibility:
- >=200 valid G1 bars in PULLBACK+EXPANSION combined;
- >=50 G1 bars in each of the two main states;
- >=50 valid G1 bars in each of 2025 and 2026 YTD.

Pass:
- observed stratified breakout premium >0;
- weekly-cluster bootstrap 95% CI lower bound >0;
- positive annual premium in >=3/4 years 2023–2026.

## C-H2 — movement follow-through
At **24h**, compare `range_atr_24h` for G1 vs non-G1 within the same main state using the same stratified weekly bootstrap.

C-H2 passes if:
- observed 24h range premium >0;
- 95% CI lower bound >0;
- positive sign in >=3/4 years.

This tests whether compression is merely an 8h touch-probability effect or a broader expansion-risk condition.

## Secondary compression diagnostics
Cannot override primary gates:
- 4h / 12h breakout-risk premiums;
- PULLBACK-only and EXPANSION-only premiums;
- time-to-first ±1ATR touch distribution;
- future 12h transition rate into frozen `EXPANSION` state, descriptive only;
- G1 prevalence by year and main state.

---

# Inference
- Weekly cluster bootstrap: **5,000 draws**.
- Fixed seed: `2026091211` plus deterministic offsets.
- Calendar weeks are resampled jointly for event/candidate and controls.
- Primary comparisons are state-stratified so an overlay must add information **beyond the persistent main state** rather than merely rediscovering it.
- Year transfer: 2023, 2024, 2025, 2026 YTD.
- Reused history: all findings remain **DISCOVERY_ONLY**.

# Verdict
- `TRANSITION_OVERLAY_ARCHITECTURE_SUPPORTED_DISCOVERY_ONLY` if R-H1, R-H2, C-H1 and C-H2 all pass.
- `PARTIAL_TRANSITION_OVERLAY_SUPPORT` if either:
  - reversal side passes both R-H1 and R-H2 but compression side is incomplete, or
  - compression side passes both C-H1 and C-H2 but reversal side is incomplete, or
  - at least 2 of the 4 gates pass with one from each side.
- `TRANSITION_OVERLAY_ARCHITECTURE_NOT_SUPPORTED` if <=1 of the 4 gates pass.
- `TRANSITION_OVERLAY_ARCHITECTURE_UNDERPOWERED` if R-H1 is underpowered and C-H1 is underpowered.

# Anti-overfit restrictions
- No changes to frozen router weights, scores, hysteresis or state thresholds.
- No new reversal candidate search; only frozen R3 is tested.
- No new compression candidate search; only frozen G1 is tested.
- No post-result horizon selection, main-state subset search, age search, score-gap filter, cooldown or dedup change.
- Secondary diagnostics cannot override failed primary gates.
- This lab can support a **display architecture** only; it cannot authorize automated entries or risk changes.