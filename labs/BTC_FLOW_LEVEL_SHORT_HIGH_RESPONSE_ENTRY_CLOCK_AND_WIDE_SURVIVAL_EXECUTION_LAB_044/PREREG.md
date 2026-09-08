# BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ENTRY_CLOCK_AND_WIDE_SURVIVAL_EXECUTION_LAB_044

## Purpose
Translate the frozen LAB043 SHORT HIGH_RESPONSE research edge into a bounded, prop-aware execution screen without adding any new signal feature or tuning entry/stop/target thresholds.

## Frozen lineage
- Source router: `BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043/output/short_response_router_stream.csv`.
- Formal universe: exact `side=-1`, `response_router=HIGH_RESPONSE`, `signal_time < 2026-08-01`; expected N=475.
- Join by `flow_id` to `BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035/output/activation_stream.csv` for frozen `level`, `atr14`, `touch_time`, `class_time`, `class_price`, and original +12h horizon.
- Require exact timestamp/state parity after join. August 2026 is audit-only.
- Price path is Binance USD-M BTCUSDT M15, identical price lineage used to construct LAB035 levels/touches/acceptance.

## Entry clocks (fixed, no search)
1. `TOUCH`: executable SHORT sell-stop at the frozen 12h prior-low level when the frozen touch occurs. Entry price = frozen `level`; entry time = frozen `touch_time`. Every HIGH_RESPONSE event is eligible.
2. `ACCEPT`: only frozen `state=ACCEPT` events. Enter SHORT at the close that first accepted below the frozen level. Entry price = frozen `class_price`; entry time = frozen `class_time`. REJECT events are explicit no-trades and contribute 0 to EV per original HIGH_RESPONSE signal.

No later re-entry, no limit improvement, no partial fills, no pyramiding.

## Fixed survival grid
Frozen stop distances from entry using frozen LAB035 ATR14:
- 1.5 ATR
- 2.0 ATR
- 2.5 ATR
- 3.0 ATR

Target for every bounded policy is exactly `1.5R`, satisfying TP >= 1.5x stop. Original signal horizon remains `signal_time + 12h`; if neither SL nor TP is hit, exit at the M15 close at that original horizon.

Primary execution configuration is **ACCEPT + 2.5 ATR stop + 1.5R TP**. This is preregistered before results as the confirmation-first / wider-survival candidate. `TOUCH + 2.5 ATR` is the primary entry-clock comparator. Other stop widths are survival diagnostics, not optimized alternatives.

## M15 path ordering guardrail
- ACCEPT entry occurs at the `class_time` close; its OHLC bar cannot stop/target the trade because those extremes occurred before entry. First executable barrier bar is the next M15 bar.
- TOUCH entry occurs intrabar at the frozen level. If the touch bar reaches TP, the price necessarily crossed the SHORT entry first, so TP is executable unless the same bar also reaches SL. If the touch bar reaches SL, order within the bar is unknown; count SL first (worst-case conservative). Any later M15 bar that touches both SL and TP is also counted SL-first.
- This conservative ambiguity policy is frozen and must not be changed after results.

## Costs
Primary round-turn friction = **5 bps of entry notional** converted to R using the actual ATR stop distance. Report 0 bps and 10 bps sensitivity without changing trade paths. These are research cost screens, not a claim of exact current FTMO BTC CFD transaction costs.

## Metrics
For every entry clock x stop width:
- eligible/traded count and fill share;
- TP / SL / time-exit shares;
- gross and 5bps net expectancy in R;
- net PF and cumulative R;
- max realized drawdown in R;
- DD-equivalent at fixed 0.25% risk/trade;
- EV per original 475 HIGH_RESPONSE signals (no-trade=0);
- winner-kill rate: among positive no-stop time-exit outcomes, fraction whose path touches the stop before the original +12h horizon;
- median MAE/MFE in ATR;
- max concurrent open trades and gross stop-risk at 0.25% per trade.

Transfer for the two preregistered 2.5 ATR policies (`ACCEPT`, `TOUCH`): 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul, pooled recent 2025H2+2026, and 2022 stress. Report August only as reused audit.

## Primary gates
1. exact frozen HIGH_RESPONSE pre-Aug N = 475;
2. LAB035 join/timestamp/state parity = 100%;
3. M15 horizon/path coverage >=99%;
4. TOUCH trades >=450;
5. ACCEPT trades >=300;
6. winner-kill rate decreases monotonically from 1.5 to 3.0 ATR for ACCEPT;
7. winner-kill rate decreases monotonically from 1.5 to 3.0 ATR for TOUCH;
8. primary ACCEPT-2.5 net EV > 0R;
9. primary ACCEPT-2.5 PF >=1.10;
10. primary ACCEPT-2.5 EV per original signal >= +0.05R;
11. primary ACCEPT-2.5 max DD equivalent at 0.25% risk <=4.0%;
12. primary ACCEPT-2.5 max concurrent gross risk at 0.25% <=2.0%;
13. primary ACCEPT-2.5 10bps EV >0R;
14. primary ACCEPT-2.5 2025H2 EV per original signal >0;
15. primary ACCEPT-2.5 2026 EV per original signal >0;
16. primary ACCEPT-2.5 pooled recent EV per original signal >0 with >=50 original signals;
17. primary ACCEPT-2.5 2022 stress EV per original signal >0;
18. TOUCH-2.5 net EV >0R;
19. TOUCH-2.5 PF >=1.10;
20. TOUCH-2.5 pooled recent EV per original signal >0;
21. ACCEPT-2.5 EV per original signal is not worse than TOUCH-2.5 by more than 0.15R;
22. August is not used for selection or thresholds.

## Verdict
- PASS only if >=18/22 and critical gates 1,2,3,8,9,10,11,13,14,15,16 pass.
- WATCH if >=12/22, or if TOUCH execution survives but confirmation-first ACCEPT execution materially degrades the edge.
- otherwise FAIL.

## Guardrail
This remains reused historical execution research, not fresh OOS and not a live EA. No live allocation is authorized from this LAB alone.
