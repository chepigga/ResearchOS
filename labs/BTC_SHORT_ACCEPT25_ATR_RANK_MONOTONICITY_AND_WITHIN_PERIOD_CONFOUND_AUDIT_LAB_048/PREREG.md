# BTC_SHORT_ACCEPT25_ATR_RANK_MONOTONICITY_AND_WITHIN_PERIOD_CONFOUND_AUDIT_LAB_048

## Frozen lineage
- Parent scientific execution: LAB044 `SHORT HIGH_RESPONSE -> ACCEPT -> SL 2.5 ATR -> TP 1.5R -> original max 12h`, 5bps research friction.
- Exact pre-Aug ACCEPT2.5 trade universe: 327 trades; original HIGH_RESPONSE SHORT signals: 475.
- ATR regime feature is frozen LAB045 `atr_rank_90d`, measured at `entry_time - 15m`, strictly causal.
- No alternative ATR window, threshold, stop, target, entry, time-exit, feature, weighting, or regime label may be searched in LAB048.
- August remains audit-only and is not used for selection.

## Question
LAB045 found a positive trade-level Spearman relation between `atr_rank_90d` and frozen `net_r_5bps` (rho ~ +0.232), while LAB047 showed the preregistered 0.50 split did not separate strongly. LAB048 asks whether the ATR relation is genuinely monotonic and survives removal of period/year confounding, or whether it is mostly a mixture effect.

## Primary tests
### H1 — absolute-rank monotonicity
Because `atr_rank_90d` is already a causal percentile in [0,1], use fixed absolute bins, not sample qcut:
- Quintiles: [0,.2), [.2,.4), [.4,.6), [.6,.8), [.8,1].
- Deciles: [0,.1), ... [.9,1].

Primary monotonicity evidence:
1. global Spearman `atr_rank_90d -> net_r_5bps` positive;
2. fixed quintile Q5-Q1 mean-EV gap positive;
3. 7-day cluster bootstrap 95% CI for Q5-Q1 gap lower bound > 0;
4. Spearman of fixed quintile midpoint vs quintile mean EV >= +0.70;
5. decile D10-D1 mean-EV gap positive and decile midpoint-vs-mean-EV Spearman >= +0.50.

No bin boundary may be changed after seeing outcomes.

### H2 — within-period confound audit
Frozen periods: 2021, 2022, 2023, 2024, 2025_H1, 2025_H2, 2026_JAN_JUL.
- Fit fixed-effects OLS: `net_r_5bps ~ atr_rank_90d + period dummies`.
- Primary coefficient is ATR-rank beta (R per full 0->1 rank move).
- 7-day cluster bootstrap (5000 draws, seed 20260908) resamples time clusters and refits the fixed-effects model.
- Strong within-period evidence requires beta > 0 and bootstrap 95% CI lower bound > 0.
- Secondary: compute Spearman ATR-rank -> netR separately inside each frozen period with N>=20; report sign count, 2025_H2 and 2026 specifically.

## Economic diagnostics
- For each fixed quintile/decile report N, trade EV, PF, CumR.
- Report LOW half (<0.50), HIGH half (>=0.50) only as parity with LAB047; no promotion or retuning.
- Report period-level mean ATR-rank and execution EV, but period-level correlation is descriptive only.

## Gates
1. exact frozen ACCEPT2.5 N=327
2. ATR-rank coverage >=99%
3. fixed absolute quintile and decile construction only
4. global ATR-rank rho positive
5. global rho p <= .05
6. Q5-Q1 EV gap > 0
7. Q5-Q1 7d bootstrap lower > 0
8. quintile midpoint-vs-EV rho >= .70
9. D10-D1 EV gap > 0
10. decile midpoint-vs-EV rho >= .50
11. fixed-effects ATR beta > 0
12. fixed-effects ATR beta bootstrap lower > 0
13. at least 5/7 period Spearman signs positive (eligible N>=20)
14. 2025_H2 within-period rho >= 0
15. 2026_JAN_JUL within-period rho >= 0
16. LAB047 0.50 split parity reproduced
17. August not used for selection

## Verdict logic
- `PASS_ATR_RANK_MONOTONIC_WITHIN_PERIOD_EFFECT` only if gates 1-12 all pass and at least 4/5 of gates 13-17 pass.
- `WATCH_ATR_RANK_NONLINEAR_OR_PARTIAL_WITHIN_PERIOD` if global association/upper-bin economics remain positive but either monotonicity or fixed-effects bootstrap proof is incomplete.
- `FAIL_ATR_RANK_ASSOCIATION_EXPLAINED_BY_CONFOUND_OR_NONMONOTONICITY` if fixed-effects beta is non-positive or the fixed-bin structure shows no coherent positive gradient.

## Guardrail
This LAB is an audit only. It cannot create a live ATR veto or new router. Any usable nonlinear ATR state discovered here requires a separately preregistered replication LAB. Live allocation = 0.
