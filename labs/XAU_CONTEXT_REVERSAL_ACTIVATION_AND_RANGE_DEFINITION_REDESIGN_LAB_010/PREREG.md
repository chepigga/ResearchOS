# XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010 — PREREG

## Objective
Diagnose and redesign two weak parts of the frozen H4 XAU Context display layer:

1. why the frozen `REVERSAL` state almost disappears in 2025–2026, while its rare onset events show promising 8–24h momentum-flip semantics;
2. whether `RANGE` can be replaced by a causal structural definition that actually describes near-term containment/compression.

This is **indicator-state / human-decision-support research**, not a trading-alpha lab. No entries, TP/SL, EV, PF, sizing or prop-risk changes are tested.

## Frozen source and parity
- Base lineage: completed LAB009 output branch.
- Canonical XAUUSD M1 asset: release `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- Required SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Frozen H4 Context router, weights, smoothing, hysteresis and bias logic remain unchanged.
- Previously audited runtime/parity fixes are allowed only to make the frozen code execute.
- Required parity: **6,216 valid Context H4 bars and 610 frozen regime episodes**.

All definitions below are frozen **before LAB010 outcomes are computed**.

---

# Part A — REVERSAL activation audit

## Frozen reversal components
All are available at the H4 close that creates the observation:

- `SWEEP`: frozen 20-bar liquidity sweep/reclaim flag.
- `RSI_TURN`: prior RSI14 <35 and current RSI rises, OR prior RSI14 >65 and current RSI falls.
- `EMA20_CROSS`: frozen close cross of EMA20.
- `ADX_FALLING`: ADX14 < previous H4 ADX14.
- `REJECTION`: frozen rejection-wick ratio >=0.45.

The frozen unsmoothed reversal score is unchanged:
`30*SWEEP + 25*RSI_TURN + 15*EMA20_CROSS + 15*ADX_FALLING + 15*REJECTION`.

## Activation candidates
Each candidate is converted into **causal activation events**: only the first H4 bar of each contiguous True block is retained. No future information, cooldown search or post-result dedup rule is allowed.

### R0_FROZEN_REVERSAL_ONSET — diagnostic baseline
First H4 bar of each frozen `REVERSAL` regime episode. Not eligible to win redesign because LAB009 already established it is too sparse.

### R1_LOCATION_TRANSITION
`(SWEEP OR REJECTION) AND (RSI_TURN OR EMA20_CROSS OR ADX_FALLING)`.

Rationale: at least one price-location/rejection clue plus at least one transition clue.

### R2_TWO_OF_FIVE
At least **2 of the 5** frozen reversal components are True on the H4 bar.

Rationale: broad component vote without score-weight tuning.

### R3_RAW_REVERSAL_WINNER
The frozen **unsmoothed** `score_reversal` is the strict/equal maximum among the four frozen unsmoothed state scores on that H4 bar.

Rationale: test whether hysteresis / 3-bar smoothing / state competition is the bottleneck rather than reversal evidence itself.

No numerical thresholds are optimized in LAB010.

## Reversal activation diagnosis
For each calendar year 2023, 2024, 2025, 2026 YTD report:
- component True rate for all 5 frozen components;
- pairwise component co-occurrence;
- raw reversal-score mean, median, P75, P90;
- fraction of bars where raw reversal score ranks #1 or top-2;
- activation-event counts for R0–R3.

Primary diagnostic question: did the scarcity in 2025–26 come from missing reversal evidence, or from frozen state competition/hysteresis?

## Reversal semantic test
Primary horizon: **24h**.

Metric: `momentum_flip_24h`, exactly as LAB008/009: future 24h close direction opposite the already-known pre-event 12h momentum direction; zero/invalid pre-momentum excluded.

For each R1–R3 candidate compare activation events against **all other eligible H4 bars that are not candidate activations** using weekly-cluster bootstrap.

Candidate eligibility:
- >=20 valid activation events overall;
- >=5 valid events in both 2025 and 2026 YTD.

Candidate semantic pass:
- observed 24h momentum-flip premium >0;
- weekly-cluster bootstrap 95% CI lower bound >0;
- positive premium in >=3/4 years 2023–2026 when each year has >=5 candidate events.

Secondary descriptive horizons: 8h and 12h. They cannot override the 24h primary test.

A candidate that recovers event count but has no semantic separation is **not** a valid redesign.

---

# Part B — RANGE definition redesign

## Frozen range components
All already exist in the frozen router:

- `LOW_ADX`: ADX14 <20.
- `COMPRESSED_24`: range24_ratio <0.85.
- `EMA_COIL`: ema_spread_atr <1.0.
- `LOW_ATR`: atr_ratio <0.95.
- `NO_STACK`: frozen EMA stack is False.

## Range candidates
These definitions are frozen before outcomes:

### G0_FROZEN_RANGE — diagnostic baseline
Frozen regime == `RANGE`. Not eligible to win redesign.

### G1_VOL_COMPRESSION
`COMPRESSED_24 AND LOW_ATR`.

### G2_STRUCTURAL_COIL
`COMPRESSED_24 AND EMA_COIL AND LOW_ADX`.

### G3_MAJORITY_3OF5
At least **3 of the 5** frozen range components are True.

### G4_STRICT_COIL
`LOW_ADX AND COMPRESSED_24 AND EMA_COIL AND LOW_ATR`.

No threshold search is allowed.

## Range semantic tests
Primary horizon: **8h**.

Primary metric: `contained_1atr_8h` from LAB008/009: neither +1 ATR nor -1 ATR is touched in the next 8h.

For each G1–G4 compare candidate bars against all other eligible noncandidate H4 bars with weekly-cluster bootstrap.

Candidate eligibility:
- >=100 valid candidate bars overall;
- prevalence between 2% and 35% of valid Context bars (to avoid an unusably rare or nearly-always-on label).

Candidate primary pass:
- containment premium >0;
- weekly-cluster bootstrap 95% CI lower bound >0;
- positive containment premium in >=3/4 years 2023–2026.

### Negative-control movement test
At **24h**, candidate mean `range_atr_24h` must be lower than `EXPANSION_MATURE` from frozen LAB009 temporal roles.

For a full range-semantic pass, the difference:
`mean(range_atr_24h | EXPANSION_MATURE) - mean(range_atr_24h | candidate) > 0`
must also have weekly-cluster bootstrap 95% CI lower bound >0.

Secondary descriptive horizons: 4h and 12h containment.

---

# Inference
- Weekly cluster bootstrap: **5,000 draws**.
- Fixed seed: `2026091110` + deterministic offsets.
- Calendar weeks are resampled jointly for pairwise comparisons.
- Year transfer uses 2023, 2024, 2025, 2026 YTD.
- Reused history: all positive findings remain **DISCOVERY_ONLY**.

# Predeclared candidate selection
No post-result threshold tuning.

## Reversal winner
Among eligible R1–R3 candidates, rank by:
1. 24h semantic bootstrap pass (required to be a winner);
2. 3/4-year positive transfer;
3. larger 24h momentum-flip premium;
4. if tied, simpler preregistered order R1 → R2 → R3.

If none passes bootstrap, there is **no reversal redesign winner**.

## Range winner
Among eligible G1–G4 candidates, rank by:
1. 8h containment bootstrap pass (required);
2. 24h movement negative-control bootstrap pass;
3. 3/4-year positive transfer;
4. larger 8h containment premium;
5. if tied, simpler preregistered order G1 → G2 → G3 → G4.

If none passes the 8h bootstrap, there is **no range redesign winner**.

# Verdict
- `REVERSAL_AND_RANGE_REDESIGN_SUPPORTED_DISCOVERY_ONLY` if both a reversal winner and a range winner exist and both pass their year-transfer requirement; range winner must also pass 24h movement negative control.
- `PARTIAL_REVERSAL_RANGE_REDESIGN_SUPPORT` if exactly one side has a qualifying winner, or both have winners but one misses transfer/negative-control.
- `REVERSAL_RANGE_REDESIGN_NOT_SUPPORTED` if neither side has a semantic bootstrap winner.
- `REVERSAL_RANGE_REDESIGN_UNDERPOWERED` only if all R1–R3 and all G1–G4 candidates fail minimum-N eligibility.

# Anti-overfit / production restrictions
- No modifications to frozen Context weights, score thresholds, smoothing, hysteresis or labels inside this lab.
- No post-result age search, horizon search, component-threshold search or candidate invention.
- The winning candidate, if any, is a display-layer **discovery**, not a production rule.
- No automated entry, position sizing or prop-challenge risk changes are authorized by LAB010.