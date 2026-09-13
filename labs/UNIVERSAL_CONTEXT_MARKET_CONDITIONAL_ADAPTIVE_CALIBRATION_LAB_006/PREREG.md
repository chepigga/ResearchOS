# UNIVERSAL_CONTEXT_MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_LAB_006 — PREREG

Status: **FROZEN BEFORE LAB006 OUTCOMES**

## Question
Can the frozen Universal Context geometry + frozen LAB004 raw side-specific scores become portable across markets when the **decision threshold and confidence are calibrated causally from the trailing history of the current symbol itself**, instead of using one fixed threshold for every asset?

This LAB is motivated by LAB005 failure of fixed universal heads. It is therefore a **causal adaptive-calibration design test on reused markets**, not fresh unseen-market proof. Any accepted adaptive rule must later be replicated on new symbols or later data without retuning.

## Frozen market universe
Seven markets already present in the Universal Context lineage:
- XAUUSD
- BTCUSDT
- EURUSD
- USDJPY
- GBPUSD
- AUDUSD
- USDCAD

No market may be dropped because of results.

## Frozen data sources
- XAUUSD — canonical `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`, SHA256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- BTCUSDT — Binance USD-M futures monthly 1h archive `2021-01` through `2026-07`, resampled H4.
- EURUSD — `v1.0/EURUSD_M1_202301020005_202607172354.csv`, SHA256 `09b872ae42af24ca67c525754da3266e21d96833fc9d66fe8bbdb1dac39836f5`, resampled H4.
- USDJPY / GBPUSD / AUDUSD / USDCAD — exact LAB005 Yahoo source and fixed raw window `[2024-09-15, 2026-09-01)`, hard-clamped before H4 resampling.

Closed H4 bars only.

## Frozen evaluation window
Primary evaluation only on:
`2025-06-01T00:00:00` <= available_time <= `2026-07-17T23:59:59`

Earlier history may be used only for causal calibration. No future observation may enter a current prediction.

## Frozen engine lineage
- Geometry: import LAB002 `add_engine()` unchanged.
- Forward outcomes: LAB002 `add_forward()` unchanged.
- Raw BULL/BEAR score formulas and first-passage outcome logic: import LAB004 `add_heads()` / `add_outcomes()` unchanged.
- LAB004 **fixed signal thresholds are not used as decisions in LAB006**. The raw score formulas remain frozen; only the decision layer becomes causal/adaptive.

States / head families:
- EXPANSION: BULL score, BEAR score; outcome horizon 8h signed ATR.
- RETRACEMENT: BULL score, BEAR score; outcome horizon 24h signed ATR.
- COMPRESSION: BULL score, BEAR score; outcome = first unique ±1 ATR passage within 24h.

## Causal adaptive calibration
All parameters below are universal and identical for every market/head.

### 1. Causal score rank
For each market + head separately, among bars eligible for that head's geometry state:
- rank lookback = previous **252 eligible state observations**;
- minimum history = **100 eligible observations**;
- current score rank = fraction of those prior scores <= current raw score;
- current bar is never included in its own rank.

Rank bins:
- `LOW`: rank < 0.50
- `MID`: 0.50 <= rank < 0.75
- `HIGH`: 0.75 <= rank < 0.90
- `EXTREME`: rank >= 0.90

Only HIGH or EXTREME may become active predictions.

### 2. Causal calibration sample
For a current head observation, inspect at most the previous **504 eligible state observations**.
Use only rows that:
- occurred before the current observation;
- already have a known/mature outcome by current `available_time`;
- had a valid causal score-rank at their own decision time;
- belong to the **same rank bin** as the current observation.

Outcome maturity lag:
- EXPANSION: prior observation available_time + 8h <= current available_time.
- RETRACEMENT: +24h <= current available_time.
- COMPRESSION: +24h <= current available_time.

Minimum calibration sample: **N=30 resolved/mature observations** in the same bin.

### 3. Bayesian probability shrinkage
Binary success:
- EXPANSION / RETRACEMENT: signed ATR outcome > 0.
- COMPRESSION: predicted side equals unique resolved first-passage side.

Use fixed Beta prior `Beta(12,12)`.
`p_hat = (wins + 12) / (n + 24)`.

### 4. Signed-edge shrinkage for return heads
For EXPANSION and RETRACEMENT only:
- calculate historical mean signed ATR in same calibration sample;
- shrink toward zero with pseudo-count 24:
`edge_hat = mean_signed_ATR * n/(n+24)`.

### 5. Active side rule
A side is ACTIVE only if:
- current rank >= 0.75;
- calibration N >=30;
- `p_hat >= 0.55`;
- EXPANSION / RETRACEMENT additionally require `edge_hat >= +0.02 ATR`.

COMPRESSION requires only `p_hat >=0.55` after rank/N gates.

### 6. BULL vs BEAR arbitration
Within the current geometry state:
- if exactly one side ACTIVE: choose that side;
- if both sides ACTIVE: choose the side with higher `p_hat` only if absolute probability gap >= **0.03**;
- otherwise ABSTAIN / WAIT.

Reported `confidence` is the chosen side's causal `p_hat`; it is **not** yet trade-profit probability because no entry/SL/TP economics are defined.

## Rank-only baseline for adaptation-benefit audit
For each state, define a frozen non-calibrated baseline:
- side eligible if rank >=0.75;
- if only one side eligible, choose it;
- if both eligible, choose the side with the higher rank; ties = abstain.

No `p_hat` or `edge_hat` gate is used in this baseline.

## Statistics
- deterministic 5,000-draw cluster bootstrap by `market × calendar-week`;
- seed `2026091306`;
- primary evaluation only inside frozen evaluation window.

## Primary hypotheses

### H1 — adaptive EXPANSION portability
For selected adaptive EXPANSION signals:
- at least 5 of 7 markets have N>=20 and positive mean signed 8h ATR;
- no market with N>=20 has mean < -0.05 ATR;
- pooled N>=200;
- pooled bootstrap 95% CI lower bound >0.

### H2 — adaptive RETRACEMENT portability
For selected adaptive RETRACEMENT signals:
- at least 5 of 7 markets have N>=50 and positive mean signed 24h ATR;
- no market with N>=50 has mean < -0.05 ATR;
- pooled N>=400;
- pooled bootstrap 95% CI lower bound >0.

### H3 — adaptive COMPRESSION direction
For adaptive COMPRESSION signals with unique resolved ±1 ATR first passage:
- at least 5 of 7 markets have N>=15;
- accuracy >50% in at least 5 eligible markets;
- no eligible market accuracy <45%;
- pooled N>=150;
- pooled bootstrap 95% CI lower bound >50%.

If pooled N<150 or fewer than 5 markets have N>=15, H3 status=`UNDERPOWERED` rather than performance FAIL.

### H4 — confidence calibration quality
Across all adaptive selected signals with binary outcomes:
- pooled Brier score < **0.245**;
- Expected Calibration Error using fixed bins [0.55,0.60), [0.60,0.70), [0.70,1.00] <= **0.10**;
- each confidence bin used in the metric must contain >=30 observations; bins with <30 are reported but excluded from ECE weighting.

### H5 — coverage / abstention sanity
Inside evaluation window:
- EXPANSION selected coverage 2%–45% in at least 6/7 markets;
- RETRACEMENT selected coverage 5%–50% in at least 6/7 markets;
- COMPRESSION selected coverage 1%–30% in at least 6/7 markets;
- BULL/BEAR arbitration conflict-abstain rate <=15% within each state for every market.

### H6 — adaptive calibration adds value vs rank-only baseline
For each state family compare adaptive selected outcomes with frozen rank-only baseline on the same evaluation window:
- adaptive mean signed ATR / accuracy must exceed rank-only baseline in at least 2 of 3 state families;
- at least one state-family adaptive-minus-baseline cluster-bootstrap 95% CI lower bound >0.

## Frozen verdicts
- `MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_SUPPORTED`: H1,H2,H4,H5,H6 PASS and H3 PASS or UNDERPOWERED.
- `MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_PARTIAL_SUPPORT`: H4,H5,H6 PASS and at least one of H1/H2 PASS, with no adequately powered state family showing strongly negative pooled performance.
- `MARKET_CONDITIONAL_ADAPTIVE_CALIBRATION_NOT_SUPPORTED`: otherwise.
- `DATA_BLOCKED`: any required market has <500 ready H4 bars or required source unavailable.

## Secondary diagnostics — cannot rescue primary verdict
- market-by-market BULL/BEAR selection mix;
- selected confidence distribution;
- yearly performance;
- HIGH vs EXTREME rank-bin performance;
- raw score-rank monotonicity;
- per-market adaptive vs fixed LAB004 head comparison.

## Interpretation boundary
This LAB tests whether **causal self-calibration** can convert a universal context/state engine into a portable decision layer. It does not establish exact entries, SL/TP, profit probability, spread/commission/slippage economics, FTMO parity, or production readiness.

## Anti-curve-fit boundary
After this prereg commit no market, evaluation window, rank lookback, calibration lookback, prior, probability threshold, edge threshold, arbitration margin, coverage band, or pass/fail gate may change inside LAB006. Only technical runtime/parser fixes that preserve formulas are allowed and must be disclosed.