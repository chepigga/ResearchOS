# CONTEXT_INDICATOR_PUBLIC_SPEC_COMPONENT_PARITY_AND_STATE_TRANSITION_AUDIT_LAB_009 — PREREG

Purpose: audit the reconstructed Context indicator itself, not trading edge. No PnL/PF/EV promotion criteria.

Frozen implementation under audit: `labs/CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001/run_lab.py` plus continuous score from LAB002. No router weights/thresholds may be changed in LAB009.

Primary dataset: BTCUSDT public H1 archive 2020-01 through 2026-07, resampled to H4 exactly as frozen router. XAU is not required for component activation because LAB008 already established exact upstream XAU reconstruction parity; LAB009 is architecture/state-machine audit.

Public-spec checklist frozen before results:
1 EMA20/50/200 structure; 2 EMA slope; 3 ATR14 relative volatility; 4 higher-timeframe/D1 bias; 5 daily inside-bar; 6 24-bar compression/range; 7 swing pivots; 8 BOS; 9 liquidity sweep/failed sweep; 10 RSI14 rhythm EMA9-vs-WMA45; 11 ADX14 level; 12 ADX decay; 13 relative volume vs 20-bar baseline; 14 session contribution; 15 Expansion score; 16 Pullback score; 17 Reversal score; 18 Range score; 19 3-bar score smoothing; 20 current-mode inertia bonus; 21 minimum hold; 22 switch gap; 23 low-vol wider gap; 24 high-vol shorter hold; 25 exact public TF mapping M1→M15, M5→H1, M15→H4, H1→D1; 26 closed-HTF availability clock; 27 Current Context output; 28 Next Context / runner-up anticipation; 29 direction compatibility layer.

For every item record: IMPLEMENTED_EXACT / IMPLEMENTED_PROXY / NOT_IMPLEMENTED; causal audit; activation count/rate where applicable; expected-direction sanity; observable effect on score/state where applicable.

Causality gate: perturb bars strictly after cutoff and verify all indicator/router outputs at/before cutoff remain byte/equality-equivalent (NaN-aware). PASS requires zero changed pre-cutoff rows.

Score activation gate: each of four regime scores must activate (>0) and each regime must occur at least once after warm-up.

State-machine gates: every observed transition must obey frozen minimum-hold and challenger-gap rules reconstructed from the score stream; low-vol (`atr_ratio<0.80`) must use hold=4/gap=12; high-vol (`atr_ratio>1.35`) hold=2/gap=5; otherwise hold=3/gap=8. Inertia bonus is +5 to current state before challenge.

Closed-clock gate: H4 row open at t must have `available_time=t+4h`; no attached state may be available earlier.

Next-context test: define runner-up strictly as second-highest 3-bar-smoothed raw score, excluding current regime. Report whether runner-up equals the next realized regime on the bar immediately before an actual transition, and compare to unconditional next-state baseline. This is descriptive architecture validation only; no threshold tuning.

A component is `PASS_PUBLIC_PARITY` only if exact public behavior is implemented and relevant dynamic gates pass. A proxy is explicitly `PROXY`, never promoted to exact. Missing public items remain FAIL/GAP even if the overall router works.

Overall verdict:
- `FULL_PUBLIC_SPEC_PARITY` only if all 29 are exact/pass.
- `FUNCTIONAL_PROXY_WITH_PUBLIC_SPEC_GAPS` if core 4-state causal machine passes but at least one public component is proxy/missing.
- `STATE_MACHINE_AUDIT_FAILED` if causality, closed clock, score activation, or transition-rule gates fail.

No trading-system conclusion is authorized by this lab.