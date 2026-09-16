# GC_XAU_LONG_DEMO_READINESS_FREEZE_001

Frozen before the final LONG readiness sequence.

## Scope

GC futures / AMP order-flow sensor -> FTMO-Demo XAUUSD LONG execution only.
No SHORT work. No signal rediscovery.

## Frozen incumbent

- Signal: `BUYER_BREAKOUT_LONG_001`
- Signal clock: completed GC M1 bar only
- GC conditions remain frozen from LAB003/004 lineage
- XAU execution: D1.00 buy limit
- Order start: next XAU M1 after completed GC signal information
- Expiry: E3 = order_start + 3 minutes
- SL: 1.5 ATR14(XAU M1)
- TP: 3R = 4.5 ATR
- Hard timeout: original signal clock + 30 minutes
- one-active semantics: corrected LAB013H/014H semantics
- quoted spread embedded through Ask entry / Bid exit path
- stress cost reference: +0.05R/fill
- research risk for demo: 0.25% equity/trade

## Optional execution overlay

LAB017 may test one preregistered causal prefill acceleration gate. It may replace the bare incumbent only if it passes every LAB017 gate. If LAB017 fails, it is discarded and the frozen D1/E3 incumbent remains the candidate.

## Demo-readiness gates

A system is `READY_FOR_FTMO_DEMO_SHADOW` only if ALL applicable gates pass:

1. `historical_replay_exact`: corrected D1/E3 replay reproduces frozen event semantics.
2. `historical_ev_positive`: AMP_ALL corrected EV/signal > 0.
3. `loo_week_min_positive`: leave-one-week-out minimum EV/signal > 0.
4. `bootstrap_p_positive_ge95`: block/dependency bootstrap P(EV>0) >= 0.95.
5. `risk_p95_dd_025_le4pct`: p95 drawdown at 0.25% risk <= 4.0%.
6. `stress_cost_010_positive`: full historical EV/signal remains > 0 after total +0.10R/fill cost stress (i.e. additional +0.05R beyond the current +0.05R reference).
7. `stress_cost_015_nonnegative`: full historical EV/signal remains >= 0 after total +0.15R/fill cost stress.
8. `late_half_positive`: late-half EV/signal > 0 under the chosen demo candidate.
9. `execution_no_lookahead`: every order/cancel decision uses information available strictly before the action timestamp.
10. `implementation_spec_frozen`: a machine-readable demo execution specification is emitted with all clocks, prices, cancellation, SL/TP/timeout and one-active rules.

## Interpretation

- Passing these gates authorizes transfer to **FTMO Demo / shadow execution only** at 0.25% risk.
- It does NOT authorize live/funded deployment.
- Demo phase is the independent forward/OOS implementation and slippage validation.
- No post-hoc threshold/depth/model search is allowed inside the readiness sequence.
