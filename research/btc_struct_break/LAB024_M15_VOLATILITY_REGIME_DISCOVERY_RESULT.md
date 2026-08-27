# LAB024 — M15_VOLATILITY_REGIME_DISCOVERY result

Date: 2026-08-27
Prereg: 6a3445e25a8bf028ea81b05da045229a765ff181
Verdict: NO_VOLATILITY_REGIME_PASSES_FULL_DISCOVERY_GATE

## Result
No volatility state passed every preregistered discovery gate across DEV 2019–2022 and VAL 2023–2025.

Strongest same-sign states:
- BREAK_RETEST + RV1H Q1 (<20th trailing percentile): DEV N80 EV +0.156R; VAL N95 EV +0.145R PF1.33; 2/3 positive VAL years; 1.5x cost EV +0.115R; low overlap with old-pivot core. Fails yearly concentration gate.
- COMPRESSION SELL + RV1H Q1: DEV N78 EV +0.013R; VAL N65 EV +0.157R PF1.37; fails yearly stability/concentration.
- BREAK_RETEST + RV1H Q4 (60–80th percentile): DEV N175 EV +0.069R; VAL N130 EV +0.103R PF1.21; fails concentration.

Interpretation: volatility is useful descriptive context but does not independently produce a robust new M15 regime under the frozen screen. Do not tune the volatility thresholds. Next high-information source should be causal volume-profile / value-area structure built from lower-timeframe volume, not M15 volume smeared across the candle.
