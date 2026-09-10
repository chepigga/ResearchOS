# XAU_H1_CONTEXT_ALIGNED_EXECUTABLE_RR15_COST_YEAR_TRANSFER_LAB_006

Status: PREREGISTERED BEFORE OUTCOME.

## Frozen lineage
- Canonical native XAU M1 SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Reuse LAB002 causal H4 Context score without changing its weights or timing.
- Frozen selector: `tf=H1`, `context_score > 0.55`, `bias_compat_label=ALIGNED`.
- Expected pre-execution parity from LAB005: 1,195 ALIGNED candidate rows before duplicate/exposure handling.
- Entry information clock: signal H1 close, available only after the H1 signal bar closes.

## Frozen execution rule
- Entry: signal H1 close.
- Stop: `1.5 * ATR14(H1)` from entry.
- Target: `2.25 * ATR14(H1)` from entry.
- Gross geometric R:R = 1:1.5.
- Maximum holding period: 120h.
- Same M1 bar touching both SL and TP: count SL first (conservative).
- No BE, trailing, partial, re-entry logic, news filter, session filter, or threshold tuning.

## Executability / duplicate policy
Two ledgers are computed, but only one is primary.
1. EVENT_DEDUP: collapse identical `available_event_time + dir` rows to one signal; this removes multiple mechanic labels describing the same executable entry.
2. PRIMARY_SINGLE_POSITION: sort EVENT_DEDUP chronologically and allow only one open trade at a time. Any signal arriving before the previous trade exits is skipped. This is the preregistered primary ledger.

No result-dependent choice between the two ledgers is allowed.

## Costs
Current FTMO published Metals CFD commission is 0.0007% of volume per side, i.e. 0.0014% round-turn = 0.14 bps of notional. Public stable XAU spread/slippage is not available, therefore this lab uses a synthetic all-in round-turn cost grid rather than claiming exact broker replication.

Frozen all-in cost scenarios, applied to every closed trade as `cost_R = entry_price * bps / 10000 / stop_distance`:
- 1 bps RT
- **2 bps RT PRIMARY**
- 3 bps RT
- 5 bps RT stress

The 2 bps primary cost includes commission + synthetic spread/slippage allowance. No cost scenario may be selected after seeing results.

## Outcomes
For every cost scenario report:
- N, win rate, TP/SL/TIME rates
- mean net R (EV)
- profit factor from net R
- cumulative net R
- max closed-trade drawdown in R
- recovery factor
- fixed-risk translation at 0.25% per trade: cumulative return proxy and max closed-trade DD proxy

Primary 2 bps additionally reports:
- calendar-year transfer for 2023, 2024, 2025, 2026
- BUY/SELL split
- weekly-cluster bootstrap, 5,000 draws, seed 2026091006
- leave-one-year-out stability
- trade frequency / median holding time

## Primary gates
LAB006 is `EXECUTABLE_RR15_TRANSFER_SUPPORTED_DISCOVERY_ONLY` only if ALL are true on PRIMARY_SINGLE_POSITION:
1. 2 bps overall EV > 0.
2. 2 bps overall PF >= 1.20.
3. Weekly-cluster bootstrap 95% CI lower bound for 2 bps EV > 0.
4. All four eligible years 2023-2026 have EV > 0 and PF > 1.0, with >=20 trades/year.
5. All four leave-one-year-out EV values > 0.
6. 5 bps stress EV > 0 and PF > 1.05.
7. Closed-trade max DD at fixed 0.25% risk <= 4.0%.
8. Recovery factor at 2 bps >= 2.0.
9. PRIMARY_SINGLE_POSITION has >=100 trades total.

If gates fail but overall EV/PF are positive, verdict is `POSITIVE_BUT_TRANSFER_NOT_CONFIRMED`.
If 2 bps EV <=0 or PF <=1, verdict is `EXECUTABLE_RR15_NOT_SUPPORTED`.

## Interpretation restrictions
- Reused-history diagnostic; no production promotion from this lab alone.
- Synthetic bid-only M1 + all-in bps cost is not a true MT5 bid/ask tick replication.
- No margin/daily floating-DD proof is claimed here.
- No stop, target, Context threshold, cost, timeframe, direction, or concurrency rule may be changed after results are visible.