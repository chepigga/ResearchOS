# U02C4 — SAME_STATE_INCREMENTAL_VALUE / RANDOM-TIME NULL

## Status
PASS as historical timing-null diagnostic on the default-v283 stateless shadow. Not exact MT5 lifecycle parity.

## Design
For each episode-first v283 opportunity in four preregistered cells, sample 200 random M5 timestamps from the exact same continuous side-specific H4 market-clock state episode.

Focus:
- BUY TIER_A
- BUY OTHER_B3
- BUY TIER_B
- SELL SELL_B3

Primary inference is paired at the v283-event level:
`delta = v283 stop-or-time outcome - mean(random same-episode outcome)`.

Exit geometry: no TP; SL=1.5×completed H1 ATR14; otherwise 24/48/72h time exit; cost proxy $27.5/BTC.
Bootstrap: 20,000 event-level resamples. Seed 28304.

## 24h result

| Side | State | N | v283 EV | Same-state random EV | Delta | 95% CI | P(delta>0) | Interpretation |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BUY | TIER_A | 26 | +0.937R | +0.731R | +0.206R | [-0.612,+0.979] | 70.3% | state carries most of edge; no proven timing increment |
| BUY | OTHER_B3 | 177 | +0.203R | +0.038R | +0.165R | [-0.042,+0.381] | 93.9% | suggestive timing alpha, not yet 95% closure |
| BUY | TIER_B | 47 | -0.368R | -0.299R | -0.069R | [-0.412,+0.313] | 34.4% | timing not the main problem; v283-occurrence episodes are themselves bad |
| SELL | SELL_B3 | 121 | -0.232R | -0.060R | -0.172R | [-0.384,+0.049] | 6.2% | first v283 timing likely harms; nearly one-sided negative evidence |

In price-percent space, SELL B3 24h delta is -0.210%, bootstrap P(delta>0)=3.17%, with CI [-0.431%, +0.012%].

## 48h result
- TIER_A: v283 +0.737R vs random +0.688R; delta +0.049R; no increment.
- BUY OTHER_B3: v283 +0.337R vs random +0.093R; delta +0.245R; P(delta>0)=94.95%; still narrowly below conventional 95% closure.
- TIER_B: v283 -0.255R vs random -0.350R; both bad; timing does not rescue state.
- SELL B3: v283 -0.004R vs random +0.046R; no timing value.

## Year behavior
### BUY OTHER_B3 timing delta, 24h
- 2024: -0.111R
- 2025: +0.135R
- 2026: +0.567R

This suggests a strengthening/migration of B3 BUY execution value; do not convert this post-hoc observation into a historical threshold without a separately preregistered recent-regime test.

### TIER_A timing delta, 24h
- 2024: +1.498R (N=4)
- 2025: -0.095R (N=18)
- 2026: +0.268R (N=4)

Tier A remains a strong state, but v283 is not proven to be the source of its edge.

### SELL B3 timing delta, 24h
- 2024: -0.557R
- 2025: -0.157R
- 2026: +0.412R

Clear regime migration: historical first-v283 timing is bad, recent 2026 is positive on small N=13.

## Architecture consequence
1. TIER_A BUY: do not require v283 for the primary Tier-A entry. The state itself is already strong. v283 may remain a telemetry/re-entry candidate, not a mandatory confirmation.
2. BUY B3: v283 is the best candidate for a genuine timing/execution layer. Evidence is strong but just below formal closure; next test should be OOS/recent-regime validation rather than threshold tuning.
3. TIER_B BUY: do not interpret the negative v283 result as pure timing harm. Random moments inside the same v283-occurrence Tier-B episodes are also negative. v283 occurrence appears to identify a bad Tier-B subpopulation; this can be tested as a veto/state-subset marker.
4. SELL B3: first v283 confirmation is not a valid historical timing solution. Test causal persistence / delayed confirmation separately.

## Next LAB
U02C5 should split into two preregistered questions:
A) BUY B3 timing validation: does v283 beat same-state random in a held-out/recent-regime test without changing thresholds?
B) SELL B3 persistence ablation: fixed causal ordinals (#1/#2/#3/#4/#6) vs matched same-state random null, to test whether delayed/persistent v283 state improves timing without survivor-bias claims.
