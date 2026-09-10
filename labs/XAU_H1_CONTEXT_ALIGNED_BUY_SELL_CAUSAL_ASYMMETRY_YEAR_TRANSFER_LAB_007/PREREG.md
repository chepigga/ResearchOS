# XAU_H1_CONTEXT_ALIGNED_BUY_SELL_CAUSAL_ASYMMETRY_YEAR_TRANSFER_LAB_007 — PREREG

Status: preregistered before LAB007 outcome computation.

## Frozen lineage
- Source: LAB006 frozen H1 HIGH+ALIGNED executable construction.
- XAU context universe parity: 263,405.
- Frozen H1 HIGH+ALIGNED candidate rows expected: 1,195.
- Context threshold: `context_score > 0.55`.
- Timeframe: H1 only.
- Entry clock: same causal availability clock as LAB006.
- Entry price / ATR: same H1 signal close and ATR14 as LAB006.
- Stop: 1.5 ATR.
- Target: 2.25 ATR = 1.5R gross.
- Maximum hold: 120h.
- Same-bar SL/TP ambiguity: STOP first, unchanged.
- Primary synthetic all-in round-turn cost: 2 bps.
- Stress costs: 1, 3, 5 bps.
- Risk proxy for DD: 0.25% per trade.
- No threshold, RR, stop, cost or regime optimization is allowed in LAB007.

## Why LAB007 exists
LAB006 post-hoc direction decomposition showed BUY much stronger than SELL. LAB007 tests whether that asymmetry is stable and executable rather than accepting a post-hoc BUY-only deletion.

## Two ledgers — both fixed before outcomes
### A. Attribution ledger
Use the exact LAB006 combined single-position ledger. Compare BUY vs SELL contributions without changing trade availability.

### B. Counterfactual direction ledgers
Starting from the same deduplicated frozen H1 HIGH+ALIGNED event ledger used by LAB006:
- BUY-only: retain only dir=+1 signals, then independently apply the same one-open-position-at-a-time rule.
- SELL-only: retain only dir=-1 signals, then independently apply the same one-open-position-at-a-time rule.
This intentionally allows a BUY signal that LAB006 skipped only because a SELL was open to become executable in the BUY-only branch, and vice versa.

## Primary estimands
1. Attribution asymmetry at 2 bps: `EV_BUY - EV_SELL` on the frozen LAB006 combined ledger.
2. Counterfactual asymmetry at 2 bps: `EV_BUY_ONLY - EV_SELL_ONLY`.
3. BUY-only standalone executable quality at 2 bps.

## Time transfer
Years: 2023, 2024, 2025, 2026. No year selection.
For BUY-only and SELL-only report N, EV, PF, CumR, DD, recovery factor, win rate, TP/SL/TIME rates.
Leave-one-year-out for BUY-only and SELL-only.

## Bootstrap
5,000 weekly-cluster resamples with frozen seed `2026091007`.
Report:
- attribution BUY-minus-SELL EV difference CI;
- counterfactual BUY-only-minus-SELL-only EV difference CI;
- BUY-only standalone EV CI.
No iid trade bootstrap is primary.

## Cost stress
Recompute BUY-only and SELL-only at 1/2/3/5 bps using the same gross exits. No cost-dependent signal selection.

## Concentration diagnostics (secondary, not promotion gates)
For BUY-only 2 bps report:
- monthly EV/PF/N;
- fraction of total positive PnL contributed by best calendar year;
- fraction of total positive PnL contributed by best calendar month;
- top-10 trading weeks share of positive PnL.
These are diagnostics only; no post-hoc episode filter is allowed.

## Preregistered gates
Direction asymmetry:
- A1: attribution `EV_BUY - EV_SELL > 0`.
- A2: weekly-cluster 95% CI lower bound for attribution difference > 0.
- A3: counterfactual `EV_BUY_ONLY - EV_SELL_ONLY > 0`.
- A4: weekly-cluster 95% CI lower bound for counterfactual difference > 0.

BUY-only executable quality:
- B1: 2 bps BUY-only EV > 0.
- B2: 2 bps BUY-only PF >= 1.20.
- B3: weekly-cluster 95% CI lower bound for BUY-only EV > 0.
- B4: all 4 years have N>=20, EV>0 and PF>1.0.
- B5: BUY-only leave-one-year-out EV >0 in 4/4 runs.
- B6: 5 bps BUY-only EV >0 and PF>1.05.
- B7: BUY-only max closed-trade DD at 0.25% risk <=4.0%.
- B8: BUY-only recovery factor >=2.0.
- B9: BUY-only N>=100.

## Verdict logic
- `BUY_ONLY_EXECUTABLE_TRANSFER_SUPPORTED_DISCOVERY_ONLY` only if A1-A4 and B1-B9 all pass.
- `BUY_SELL_ASYMMETRY_SUPPORTED_BUY_NOT_TRANSFER_READY` if A1-A4 pass but any B gate fails.
- `BUY_SELL_ASYMMETRY_MIXED` if point estimates A1/A3 pass but either bootstrap asymmetry gate fails.
- `BUY_SELL_ASYMMETRY_NOT_SUPPORTED` otherwise.

## Interpretation boundary
This is reused-history research. Even a full pass does not authorize production deployment, because the BUY-only hypothesis was motivated by LAB006 results. Fresh/OOS replication is required before EA promotion.
