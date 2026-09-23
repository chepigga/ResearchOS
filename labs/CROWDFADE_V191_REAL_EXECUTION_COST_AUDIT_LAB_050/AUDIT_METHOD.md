# LAB050 — V191 REAL EXECUTION COST AUDIT

Status: OBSERVATIONAL AUDIT — TWO BROKER REPORTS

## Scope

User supplied two MT5 Trade History reports:

1. GetLeveraged Ltd.
   - account report: 227622
   - current V191 marker: comments starting `CF191`

2. IC Markets / Raw Trading Ltd
   - account report: 53049472
   - current V191 marker: comments starting `CF191`

The audit intentionally excludes:
- `CF200...` trades;
- older generic `CrowdFade` trades from the primary V191 sample;
- non-bot / unmarked trades.

## Important source limitation

Current V191 entries in both reports are market orders.

The MT5 history report contains:
- order open timestamp;
- fill timestamp;
- fill price;
- initial SL;
- final position SL;
- commission;
- swap;
- realized PnL;
- stop-trigger comments.

It does NOT contain the contemporaneous bid/ask snapshot or a requested market price for market entries.

Therefore the reports do not permit exact reconstruction of:
- entry spread;
- entry slippage versus requested quote;
- spread paid on non-stop market exits.

LAB050 therefore reports an **observed execution-cost floor**, not a complete all-in spread/slippage estimate.

## Observable cost components

### Explicit cost
Per closed trade:
`explicit_cost_usd = -(commission + swap)`

Positive means a cost.

### Stop-fill slippage
Only for exits explicitly marked `[sl ...]`.

For long positions:
`adverse_stop_slippage = final_SL - exit_fill`

For short positions:
`adverse_stop_slippage = exit_fill - final_SL`

Positive = adverse execution.
Negative = favorable execution.

Stop slippage bps:
`stop_slip_bps = adverse_price / final_SL * 10000`

### Initial-R conversion
Initial risk is measured from entry fill to the initial SL stored on the entry order.

`initial_risk_usd = abs(entry_fill - initial_SL) * volume`

`observed_cost_R = (explicit_cost_usd + stop_slip_usd) / initial_risk_usd`

Non-stop trades have zero observed stop slippage; their unobserved spread/market-exit cost is not assumed to be zero — it is simply absent from the report.

## LAB049-equivalent flat bps

For direct comparison with LAB049's flat cost stress, define the flat-bps value that would create the same aggregate observed R drag over the sample:

`equiv_flat_bps = 10000 * SUM(observed_cost_R) / SUM(entry_price / initial_risk_price)`

This is an apples-to-apples **lower-bound equivalent** to LAB049's cost parameter.

## Latency

Market order report latency:
`fill_latency_sec = filled_time - order_open_time`

MT5 report resolution is one second, so values of 0s mean "less than one displayed second", not literal zero network latency.

## Cross-broker matched-fill diagnostic

Exact matches require:
- identical CF191 comment;
- identical symbol.

Only exact matches are used.
Because quote feeds differ and there is no independent mid-price reference, cross-broker fill-price differences are a relative execution diagnostic, not absolute slippage.

## Interpretation against LAB049

LAB049 approximate historical cost-only break-even:
- control 2.5/0.5: ~1.48 bps
- balanced 3.5/0.5: ~1.75 bps
- aggressive 5.0/0.5: ~1.85 bps

The observed LAB050 floor must be below the relevant break-even with enough margin left for:
- unobserved entry spread;
- unobserved market-exit spread/slippage;
- any fees not represented in the history report.

No strategy retuning is allowed from LAB050.
