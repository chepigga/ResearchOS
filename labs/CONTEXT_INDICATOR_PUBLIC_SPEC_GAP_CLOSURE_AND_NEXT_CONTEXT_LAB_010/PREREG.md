# CONTEXT_INDICATOR_PUBLIC_SPEC_GAP_CLOSURE_AND_NEXT_CONTEXT_LAB_010 — PREREG

Purpose: close the known public-spec gaps of the reconstructed Context indicator and audit the indicator itself. No trading edge/PnL optimization is allowed.

Parent audit: LAB009 identified 29 public components: 8 exact, 14 proxy, 7 missing. LAB010 may add missing public components and replace proxies only where the public description is operationally specific. Unknown proprietary weights/thresholds remain PROXY and may not be called exact.

Frozen public-spec interpretation before results:
1. EMA20/50/200 structure: exact.
2. EMA slope: proxy because public source does not disclose slope lookback/normalization.
3. ATR14 relative volatility: use ATR14 / rolling 50-bar arithmetic mean ATR14. This closes the 'vs average' wording; lookback remains proxy if undisclosed.
4. D1 HTF bias: add causal D1 bias from last closed D1 bar using EMA20/50/200 stack plus EMA50 slope sign. Because proprietary D1 rule is undisclosed, status=PROXY rather than EXACT.
5. Daily inside-bar: exact definition on completed D1 bars: high < previous high and low > previous low; attached only after D1 close.
6. 24-bar compression/range: exact existing range24 construct.
7. Swing pivots: add causal confirmed 2-left/2-right pivots; status=PROXY because pivot depth is undisclosed.
8. BOS: replace rolling-20 breakout proxy with close beyond latest causally confirmed swing high/low; status=PROXY because pivot depth is proxy.
9. Liquidity sweep/failed sweep: replace rolling-20 sweep with wick through latest causally confirmed swing level and close back inside; status=PROXY because swing definition is proxy.
10. RSI14 rhythm EMA9 vs WMA45: exact literal implementation on RSI14.
11. ADX14 level: exact.
12. ADX decay: exact.
13. Relative volume vs 20-bar average: replace median denominator with arithmetic rolling mean20; exact literal implementation.
14. Session contribution: add UTC session labels Asia 00-07, London 07-13, Overlap 13-16, NewYork 16-21, Off 21-24 and a small fixed score contribution. Status=PROXY because source does not disclose session boundaries/weights.
15-18. Four regime scores remain PROXY because proprietary weights are unknown; LAB010 only swaps in the closer public components above, with no outcome fitting.
19. 3-bar smoothing exact.
20-24. Inertia/min-hold/gaps remain PROXY because proprietary constants are unknown; keep frozen LAB001 constants (+5 inertia; low-vol hold4/gap12; normal hold3/gap8; high-vol hold2/gap5).
25. Public TF map M1→M15, M5→H1, M15→H4, H1→D1: implement exact routing function and unit-test all four mappings.
26. Closed-HTF clock: exact; all HTF-derived features attach only after source bar close.
27. Current Context output: exact.
28. Next Context: explicit output = highest 3-bar-smoothed raw score excluding Current Context; also output next_context_confidence=(runner_up_score-current_score? no) = runner-up score gap vs third-best normalized by 100. The regime label itself is primary.
29. Direction compatibility: exact layer retained.

No public-spec item may be promoted from PROXY to EXACT unless its operational definition above is literal and unambiguous from public wording.

Primary dataset: BTCUSDT public H1 2020-01 through 2026-07, with D1 built causally from H1 and H4 execution context. This provides enough history to exercise D1, H4, sessions, swings and all four states. XAU portability is not required for this architecture closure lab; prior XAU parity remains separate evidence.

Primary gates:
- G1 causality perturbation: changing future bars after cutoff changes zero outputs at/before cutoff.
- G2 D1 clock: no D1-derived value attached before completed D1 close.
- G3 swing clock: pivot at bar i with right=2 cannot be available before i+2 source bars close.
- G4 TF mapping unit test 4/4 exact.
- G5 all 29 checklist items are either EXACT or PROXY; NOT_IMPLEMENTED count must be 0.
- G6 all four regime scores and all four Current Context states activate.
- G7 independent state-machine reconstruction mismatch=0.
- G8 Next Context exists on >=95% of warm rows and pre-transition runner-up match rate exceeds conditional old-state baseline.
- G9 Reversal activation is reported but NOT optimized. No minimum frequency gate; frequency change vs LAB009 is descriptive only.

Overall verdict:
- `PUBLIC_SPEC_COMPONENT_CLOSURE_COMPLETE_WITH_PROPRIETARY_PROXIES` if G1-G8 pass and missing=0.
- `GAP_CLOSURE_INCOMPLETE` if any public component remains missing.
- `STATE_MACHINE_OR_CAUSALITY_FAILED` if G1/G2/G3/G4/G6/G7/G8 fail.

No claim of proprietary ZynAlgo code/weight parity is authorized. No trading-system conclusion is authorized.