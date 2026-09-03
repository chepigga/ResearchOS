# BTC_REVERSAL_EDGE_ON_OFF_REGIME_AND_ROUTER_ABSTENTION_LAB_008 — preregistration

## Question
Can a causal event-time regime gate identify when the already-frozen BTC reversal branch should trade versus abstain, improving stability without changing the underlying selector, entry, stop, target, TTL, or cost assumptions?

## Frozen base strategy
Inherited exactly from LAB006/LAB007:
- parent impulse = completed BTC 60m |return| >= prior 30d 97.5th percentile, 4h cooldown;
- frozen LAB003 BTC-only CONT/REV router and DEV q80 threshold;
- only `selected_rev` signals are eligible;
- entry = `LIMIT_R0.50_T60`, no market fallback;
- SL = 1.0 × parent event M15 range;
- TP = 1.5R primary;
- same-bar SL+TP = SL-first;
- cost stress = 5 bps round trip.

No parameter above may change after results are observed.

## Causal regime clock
The ON/OFF gate is evaluated at the completed parent impulse close, before any post-impulse fill information exists. No year label, future return, fill status, MFE/MAE, or future path feature may enter the gate.

## Primary feature set
All features are available at impulse close:
- `router_margin = p_rev - p_cont`
- `router_conf`
- impulse-direction-signed prior 24h return
- impulse-direction-signed prior 7d return
- impulse-direction-signed prior 30d return
- 24h trend efficiency
- 7d trend efficiency
- 7d directional extreme position relative to prior 7d high/low
- 4h/24h realized-volatility ratio
- impulse strength = |60m return| / causal impulse threshold
- existing event `btc_range_z`
- existing event `btc_vol_z`

Primary model: fixed Ridge regression (`alpha=5.0`) with median imputation + standardization.

Target per eligible `selected_rev` signal:
- if the frozen limit never fills within TTL: `signal_net_R = 0`;
- if filled: frozen RR1.5 first-hit net R after 5 bps cost.
This prevents a gate from receiving artificial credit merely because some signals do not fill.

## Walk-forward protocol
Expanding yearly walk-forward. For each test bucket, fit using only strictly earlier completed signal outcomes:
- test 2022: train 2021
- test 2023: train 2021–2022
- test 2024: train 2021–2023
- test 2025: train 2021–2024
- test 2026 Jan–Jul: train 2021–2025
- August 2026: reused audit only; it is no longer fresh after LAB007.

The ON threshold is the median fitted score on that test year's training sample. Thus the intended train coverage is ~50%; no test-year threshold tuning is allowed.

## Important causality boundary, frozen before execution
The new ON/OFF gate itself is strictly event-time causal and its yearly fit uses only prior completed signal outcomes. However, the inherited LAB003 selector was originally trained on the full DEV 2021–2024 block. Therefore retrospective 2022–2024 results are **conditional mechanism diagnostics under that frozen DEV selector**, not a full deployment-causal simulation of the entire pipeline. Forward years 2025 and 2026 are the stronger transfer evidence because the inherited selector was frozen before them. Any PASS in this LAB remains a research PASS and cannot be promoted to production without a later strict end-to-end causal selector replication.

## Primary comparison
For each walk-forward year compare:
- BASE: trade every frozen `selected_rev` signal;
- GATED: trade only when predicted regime score >= frozen train median; abstained signals contribute 0R.

Report signal count, gate coverage, filled count, cumulative R, EV per opportunity, EV per traded signal, PF, max DD R, and max consecutive losses.

## Audit families
For diagnosis only; they cannot rescue a failed primary combined gate:
- ROUTER_ONLY
- TREND_ONLY
- VOL_ONLY
- IMPULSE_ONLY

## Promotion gates
Primary combined gate only:
1. pooled 2022–2026 gated cumulative R > pooled BASE cumulative R;
2. pooled gated max DD R < pooled BASE max DD R;
3. 2022 cumulative-R delta > 0;
4. 2024 cumulative-R delta > 0;
5. gated 2025 cumulative R > 0;
6. gated 2026 Jan–Jul cumulative R > 0;
7. gated positive years >= 4 of 5 for 2022, 2023, 2024, 2025, 2026 Jan–Jul;
8. pooled gate coverage between 25% and 75%;
9. 2025+2026 pooled gated cumulative R > 0;
10. 2025+2026 pooled gated max DD <= BASE max DD.

`PASS_CAUSAL_ON_OFF_ABSTENTION_ROUTER` requires >=8/10 with gates 1, 3, 4, 5, 6 all passing. Otherwise WATCH/FAIL according to preregistered score logic.

## Scientific status
Years 2022/2024 motivated this LAB and therefore are mechanism-discovery data, not pristine holdout. 2025/2026 and August have also been seen in prior LABs. A PASS here is a causal walk-forward **gate** research pass, not production authorization. No live allocation is authorized by this LAB alone.
