# SELL_CORE_010 — AUTONOMOUS_FUNDING_Q4_STATE

## Verdict

**REJECT as a standalone periodic SELL state.**

The old `funding Q4: SELL +1.17%, 8/8` finding was a funding-context result inside a large oracle/signal population; it was not an autonomous strategy that sells every funding observation while Q4 is active. SELL_CORE_010 tested that missing autonomous hypothesis directly.

## Frozen data

- Binance BTCUSDT perpetual funding: 7,576 observations, 2019-09-10 08:00 UTC through 2026-08-09 08:00 UTC.
- Binance BTCUSDT H1 futures/flow bars: 60,646 bars, 2019-09-08 17:00 UTC through 2026-08-09 14:00 UTC.
- Funding asset SHA256: `df4dc9d6c0c28069e1f1a20c4d1f0ffb3d7195869aae151263ec8fff10052ef8`.
- H1 flow asset SHA256: `e9501054d851fd6dfc605f97671c59f15afa9b259620191756c45af62031417e`.

## Funding state

- `funding_3d` = trailing mean of 9 x 8h funding observations.
- Primary `STRICT2000_INCLUSIVE`: current `funding_3d` percentile against the previous 2,000 valid `funding_3d` observations, inclusive ECDF; Q4 >= 0.75. This is exact SELL_CORE_001 percentile parity.
- `EXPANDING90_INCLUSIVE`: newly preregistered causal sensitivity using previous `min(2000, available)` observations with at least 90 prior observations, solely to inspect early 2019-2020 history.
- `STRICT2000_MIDRANK`: tie sensitivity.

Because the strict method needs 2,000 prior observations, its usable state starts in 2021. In 2022 the causal percentile never reached Q4 (`max=0.647`), so there are zero Funding-Q4 entries that year. The expanding method also has zero Q4 observations in 2022 for the same reason.

## Autonomous strategy

- SELL every 8h funding timestamp while Funding-Q4 state is active.
- Phase 0h primary; +4h phase sensitivity.
- Entry next H1 open strictly after decision time.
- SL = 1.5 x completed H1 Wilder ATR14.
- No TP.
- 48h primary; 72h sensitivity.
- Frozen ResearchOS cost proxy = $27.5/BTC round-turn.
- Funding episode max-concurrent initial-risk budget diagnostic = 0.50%; 8h cadence / 48h hold implies 0.08333% initial risk per entry for a six-slot maximum overlap.

## Primary strict2000 result

Funding-Q4, phase 0:

- N = 1,035 trades, 33 Q4 episodes, ~4.04 trades/week.
- EV48 = **-0.2261R**.
- PF48 = **0.724**.
- price EV48 = **-0.3322%**.
- SL rate48 = 76.4%.
- EV72 = **-0.2215R**.
- PF72 = **0.745**.
- price EV72 = **-0.3617%**.

For comparison, Q1-Q3 periodic SELL was much closer to flat: EV48 -0.0314R, PF0.961, price EV48 -0.0573%.

### Strict yearly Funding-Q4, 48h

| Year | N | Episodes | EV48 R | PF48 | Price EV48 |
|---:|---:|---:|---:|---:|---:|
| 2021 | 67 | 5 | -0.345 | 0.542 | -0.402% |
| 2022 | 0 | 0 | no Q4 state | — | — |
| 2023 | 362 | 12 | -0.094 | 0.889 | -0.323% |
| 2024 | 526 | 9 | -0.283 | 0.652 | -0.349% |
| 2025 | 53 | 4 | -0.548 | 0.336 | -0.505% |
| 2026 | 27 | 4 | +0.033 | 1.046 | +0.374% |

Only 1/5 years containing Q4 entries is positive in R and price space.

## Expanding90 full-history sensitivity

Funding-Q4, phase 0:

- N = 1,813, 59 Q4 episodes, ~5.11 trades/week.
- EV48 = **-0.0985R**.
- PF48 = **0.879**.
- price EV48 = **-0.2269%**.
- EV72 = **-0.1273R**.
- PF72 = **0.854**.
- price EV72 = **-0.3066%**.

Yearly 48h:

- 2019: +0.599R, PF1.70, N105.
- 2020: -0.043R, PF0.95, N374.
- 2021: -0.040R, PF0.95, N366.
- 2022: no Q4 state (causal percentile max 0.647).
- 2023: -0.094R, PF0.89, N362.
- 2024: -0.283R, PF0.65, N526.
- 2025: -0.548R, PF0.34, N53.
- 2026: +0.033R, PF1.05, N27.

Only 2/7 calendar years containing Q4 entries are positive. Thus the old 8/8 context result does not transfer to the autonomous periodic strategy.

## Phase robustness

Funding-Q4 48h:

- Strict phase0: -0.226R.
- Strict +4h: -0.156R.
- paired delta +0.070R, but both phases remain negative.
- Expanding phase0: -0.0985R.
- Expanding +4h: -0.0937R.

The state is phase-stable in the wrong direction; phase shift does not rescue it.

## Episode bootstrap

With the 0.50% max-concurrent episode risk diagnostic:

- Strict Funding-Q4 phase0: mean episode return **-0.591%**, 95% CI `[-1.449%, +0.323%]`, P(>0)=9.7%.
- Strict Funding-Q4 +4h: -0.407%, CI `[-1.177%, +0.494%]`, P(>0)=16.2%.
- Expanding Funding-Q4 phase0: -0.252%, CI `[-0.887%, +0.380%]`, P(>0)=21.4%.

No episode-level PASS.

## RV168 control

No exact legacy RV168 formula was recoverable from frozen findings, so this lab preregistered a diagnostic-only standard measure:

`RV168 = sqrt(sum(last 168 completed H1 close-to-close log-return^2))`.

Funding percentile is not strongly correlated with this volatility measure:

- Strict corr(percentile, log RV168) = -0.096.
- Expanding corr = +0.004.

Episode-cluster bootstrap regression `R48 ~ FundingQ4 + z(log RV168) + year fixed effects`:

- Strict Q4 beta = **-0.0435R**, CI `[-0.404, +0.463]`, P(beta>0)=41.3%.
- Expanding Q4 beta = +0.166R, CI `[-0.070, +0.529]`, P(beta>0)=90.9% — suggestive but not a 95% PASS and cannot rescue the negative standalone strategy.

## Important diagnostic clue: Funding-Q4 x low RV168

This was preregistered as a diagnostic decomposition, not a tradable threshold and not an independent OOS test.

Inside the **lowest RV168 quintile**:

- Strict Funding-Q4: N136, EV48 **+0.463R**, PF1.56, price EV +0.209%.
- Expanding Funding-Q4: N200, EV48 **+0.807R**, PF2.03, price EV +0.565%.

But Funding-Q4 becomes negative in RV quintiles Q3-Q5, including strongly negative results in the upper RV buckets. This suggests that the broad historical funding effect may depend on volatility/regime context rather than representing a universal standalone short state. This is a clue only; `Funding Q4 AND low RV` is **not promoted** from this lab.

## Frozen conclusion

1. **Autonomous Funding-Q4 periodic SELL is rejected.**
2. The old `+1.17%, 8/8` result remains valid only for its original broad oracle/context question; it cannot be cited as evidence for blind 8h shorting.
3. The failure is not explained by simple RV168 correlation; Funding-Q4 is nearly orthogonal to RV168 overall.
4. A preregistered diagnostic revealed a strong low-RV interaction, but it requires a separate validation lab before any use as a rule.
5. Do not combine Funding-Q4 with FVG/B3/CHoCH/v283 post hoc to rescue this lab.

Workflow run: `31696511696`  
Artifact: `9179578156`  
Artifact SHA256: `7898d9817a69c39a16bd54d1eb6c025ea31ea292f5731c6c61d6e651f7cf23a2`
