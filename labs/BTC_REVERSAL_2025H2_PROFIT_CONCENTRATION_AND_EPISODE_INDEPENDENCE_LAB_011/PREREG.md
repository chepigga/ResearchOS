# BTC_REVERSAL_2025H2_PROFIT_CONCENTRATION_AND_EPISODE_INDEPENDENCE_LAB_011 — preregistration

## Question
Is the frozen reversal branch's strong 2025 H2 profit broad across months, directions and independent market episodes, or concentrated in a few trades/clusters? Does 2026 show a similar breadth pattern?

## Frozen base
Inherited exactly from LAB006–010:
- frozen LAB003 BTC-only REV selector and q80 threshold;
- only `selected_rev` opportunities;
- entry `LIMIT_R0.50_T60`, no market fallback;
- SL = 1.0 × event M15 range;
- TP = 1.5R;
- same-bar TP+SL = SL-first;
- 5 bps round-trip cost stress;
- no new gate, no resizing, no direction change.
- `NO_FILL = 0R` at opportunity level.

## Primary windows
- Discovery target: **2025 H2 = 2025-07-01 through 2025-12-31**.
- Transfer audit: **2026 Jan–Jul**.
August 2026 has zero frozen REV opportunities and is not used to rescue any conclusion.

## Episode definition
Primary independent episode rule is frozen before results:
- sort frozen `selected_rev` opportunities by event time;
- a new episode starts only when the gap from the previous frozen REV opportunity is **> 7 calendar days**;
- all opportunities inside the episode remain together, including NO_FILL signals.
This is a clustering diagnostic, not a trading rule.

Audit-only episode gaps: 3d and 14d. They cannot rescue the primary 7d verdict.

## Concentration metrics
For 2025 H2 and 2026 Jan–Jul report:
1. monthly signals/fills/cumR/EV/PF;
2. impulse-direction split (`+1` bullish impulse -> reversal SELL; `-1` bearish impulse -> reversal BUY);
3. primary 7d episodes: signals, fills, cumR, EV;
4. top-1 and top-3 winning-trade share of gross positive R;
5. top episode share of gross positive R;
6. leave-one-month-out (LOMO) total R;
7. leave-one-episode-out (LOEO) total R;
8. deterministic 5,000-draw episode-cluster bootstrap of mean R per opportunity.

## Primary 2025 H2 breadth gates
1. frozen 2025 H2 cumulative R > 0;
2. at least 4 of 6 calendar months have positive opportunity-level cumulative R;
3. every leave-one-month-out cumulative R remains > 0;
4. at least 4 primary 7d episodes exist;
5. at least 3 primary episodes are positive;
6. every leave-one-episode-out cumulative R remains > 0;
7. top-1 winning trade contributes <= 35% of gross positive R;
8. top-3 winning trades contribute <= 70% of gross positive R;
9. top episode contributes <= 50% of gross positive R;
10. episode-cluster bootstrap 95% lower bound of mean R/opportunity > 0.

## 2026 transfer gates
11. 2026 Jan–Jul cumulative R > 0;
12. 2026 has at least 3 positive primary episodes and top episode <= 60% of gross positive R.

## Verdict
- `PASS_BROAD_EPISODE_INDEPENDENT_EDGE`: >=10/12 gates pass and gates 1, 4, 6, 10, 11 pass.
- `WATCH_POSITIVE_BUT_CONCENTRATED`: cumulative R is positive in both windows but breadth/cluster gates fail.
- `FAIL_PROFIT_CONCENTRATED_OR_UNSTABLE`: otherwise.

## Scientific status
2025 H2 and 2026 have already been observed in earlier LABs, so this is a structural diagnosis, not a fresh holdout. No result from this LAB authorizes live allocation by itself.
