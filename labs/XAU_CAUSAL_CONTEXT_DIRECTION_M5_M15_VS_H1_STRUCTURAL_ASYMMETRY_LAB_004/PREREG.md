# XAU_CAUSAL_CONTEXT_DIRECTION_M5_M15_VS_H1_STRUCTURAL_ASYMMETRY_LAB_004 — PREREG

Status: preregistered before LAB004 outcome inspection.

## Frozen universe
- Native XAU M1 SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Reuse LAB002/LAB003 causal Context join and availability boundary.
- Expected Context-eligible events: `263405`.
- Context score unchanged: `C=(Expansion+Pullback-Reversal-Range)/200`.
- HIGH unchanged: `C>0.55`.
- Direction compatibility unchanged: ALIGNED / OPPOSED from event direction vs frozen H4 bias.
- Primary economic outcome remains drift-adjusted `excess`; raw `R` is secondary.
- No event, mechanic, year, direction, TF, or threshold may be removed after seeing LAB004 outcomes.

## Question
LAB003 found HIGH-direction premium positive on M5/M15 but negative on H1. Determine whether this is explained by horizon, volatility/risk scaling, Context staleness, or mechanic composition, versus a genuine structural H1 asymmetry.

## Primary estimator
Within HIGH Context:
`ASYM = premium(M5+M15) - premium(H1)`, where `premium = mean(ALIGNED excess)-mean(OPPOSED excess)`.

Primary gates:
1. `ASYM > 0`.
2. Weekly-cluster bootstrap 95% CI lower bound for ASYM > 0, 5000 draws, seed `2026090904`.
3. ASYM positive in >=4/5 calendar years when both groups have >=100 ALIGNED and >=100 OPPOSED events.
4. Leave-one-year-out ASYM positive in >=4/5 runs.

## Frozen decomposition tests
### A. Horizon mismatch
Use bid-close structural forward return normalized by signal risk `1.5*ATR14(TF)` from the causal signal-bar close. Compute for ALL TF at the same fixed horizons: `10h`, `30h`, `120h`.
- Support horizon mismatch only if H1 HIGH premium is non-negative at 10h or 30h and negative at 120h, or shows a strictly worsening sign transition toward 120h.
- Otherwise horizon mismatch is not sufficient.

### B. ATR / risk scaling
Derive `risk_pct=1.5*ATR14(TF)/signal_close` without using outcomes. Create pooled quartiles from HIGH ALIGNED/OPPOSED events using feature-only qcut edges.
- Compare H1 premium vs M5+M15 premium inside every eligible common risk quartile (>=100 A and O per group).
- If aggregate H1 negativity disappears in >=3/4 eligible matched risk quartiles, support risk-scaling explanation.

Also report existing causal `atr_ratio` quartiles within H1 as a volatility-state diagnostic; no thresholds are fitted.

### C. Context staleness
`context_age_hours = available_event_time - H4_context_available_time`.
Frozen buckets: `[0,1)`, `[1,2)`, `[2,3)`, `[3,4.01]` hours.
- Support staleness only if H1 premium is non-negative in age <2h aggregate and negative in age >=2h aggregate, with both aggregates >=100 A and O.

### D. Mechanic composition / Simpson audit
For every frozen `f_*` mechanic, compare HIGH premium separately on H1 and on M5+M15.
Eligibility: >=100 ALIGNED and >=100 OPPOSED in both TF groups.
- Support composition explanation only if >=70% of eligible mechanics have non-negative H1 premium and median H1 premium >0 while aggregate H1 premium is negative.
- Otherwise H1 weakness exists within mechanics and is not a simple composition artifact.

### E. Direction and year structure
Report H1 HIGH premium separately for BUY/SELL and 2022/2023/2024/2025/2026. No subgroup is promoted or deleted.

## Verdict taxonomy
- `H1_ASYMMETRY_NOT_CONFIRMED`: primary asymmetry bootstrap fails.
- `H1_ASYMMETRY_EXPLAINED_BY_<CAUSE>`: primary asymmetry confirmed and one prereg cause gate passes.
- `MULTIFACTOR_H1_ASYMMETRY`: primary confirmed and >1 cause gate passes.
- `STRUCTURAL_H1_ASYMMETRY_UNEXPLAINED`: primary confirmed, none of A-D explains it.

Reused-history diagnostic only. No live filter, EA change, TF deletion, or risk modulation is authorized by LAB004.