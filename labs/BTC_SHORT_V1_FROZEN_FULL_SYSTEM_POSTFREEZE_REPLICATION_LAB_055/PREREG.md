# BTC_SHORT_V1_FROZEN_FULL_SYSTEM_POSTFREEZE_REPLICATION_LAB_055

## Purpose
End-to-end replication of the already frozen SHORT v1 system. No signal, threshold, entry, stop, target, horizon, failure-management, cost, or sizing parameter may be changed from LAB043–054.

## Frozen system
1. Binance USD-M BTCUSDT retail `count_long_short_ratio`, M15 last observation.
2. `delta_ls_12 = ratio_t - ratio_{t-12}`.
3. Strictly-prior rolling 90 calendar day q20/q80, minimum 1000 prior M15 observations.
4. Contrarian FLOW: `delta>=q80 => SHORT`; flow-only signals are 12h non-overlapping exactly as LAB022.
5. Activation level: prior 12h futures extreme, 48 closed M15 bars. SHORT level = prior12_low.
6. TOUCH if price low reaches level within signal+12h.
7. ACCEPT if one of the first 4 M15 closes from TOUCH is `close<=level`; entry at the first ACCEPT close.
8. Causal response router exactly equivalent to frozen LAB041/043 SHORT collapse: HIGH_RESPONSE iff the event's directional futures 60m response is above the strictly-prior 90d median response among valid all-touch events; pressure magnitude does not affect HIGH-vs-LOW collapse. Minimum 40 prior valid events.
9. Trade only `SHORT + HIGH_RESPONSE + ACCEPT`.
10. Frozen execution: SL = 2.5 ATR14(signal); TP = 1.5R; horizon = signal_time+12h; ACCEPT entry-bar is not eligible for intrabar SL/TP; later ambiguous M15 SL/TP bars are SL-first.
11. Frozen management from LAB052/053/054: ADVERSE_FIRST is -0.5R first-passage within first 120m after entry. Do not exit on ADVERSE_FIRST. If before recovery (`M15 close<=entry`) there are 2 consecutive closed M15 bars `close>level`, exit immediately at the second close (`PERSISTENT_FAILURE = EXIT NOW`). No WAIT/reacceptance refinement.
12. Costs: 5 bps primary, 10 bps stress. Risk reporting at 0.25% per trade.

## Post-freeze windows
- HELDOUT_AUG: 2026-08-01 through 2026-08-31. August was present as audit-only in prior files and explicitly excluded from selection. It is a held-out/reused audit, not newly collected OOS.
- FRESH_SEP: 2026-09-01 onward using only completed public Binance daily archives available at run time, requiring the full signal+12h horizon to be present. September was not part of LAB043–054 selection.

## Data/parity requirements
- Rebuild retail FLOW from raw Binance daily metrics and validate August generated flow signal_time+side against frozen LAB022 flow-only stream.
- Validate August frozen HIGH_RESPONSE classification against persisted LAB041/043 state wherever event IDs/timestamps match.
- September classification must use only event/state history strictly before each September event; historical LAB041 valid all-touch rows may seed the 90d event distribution through 2026-08-31.
- No September outcome may influence thresholds or classification.

## Primary outputs
For HELDOUT_AUG, FRESH_SEP, and POSTFREEZE_COMBINED report:
- FLOW SHORT signals
- touched events
- HIGH_RESPONSE SHORT signals
- ACCEPT/trades
- PERSISTENT early exits
- EV/trade at 5bps and 10bps
- PF
- CumR
- MaxDD R and DD at 0.25%
- EV per original HIGH_RESPONSE signal
- exit distribution (TP/SL/TIME/PERSISTENT)

## Verdict
- PASS_FROZEN_SHORT_V1_POSTFREEZE: September has >=5 trades, 5bps EV>0, PF>=1.10, 10bps EV>0, DD@0.25%<=4%, and POSTFREEZE_COMBINED EV>=0.
- FAIL_FROZEN_SHORT_V1_POSTFREEZE: September has >=5 trades and 5bps EV<=0 or PF<1.0, or DD@0.25%>4%.
- WATCH_POSTFREEZE_INSUFFICIENT_FRESH_TRADES: September has <5 completed trades, regardless of point estimate.

## Guardrail
This LAB is validation only. No further sequence/refinement/tuning is permitted from the September outcomes. Reused August must never be represented as fresh OOS. Live allocation remains 0 until broker-native parity is separately established.