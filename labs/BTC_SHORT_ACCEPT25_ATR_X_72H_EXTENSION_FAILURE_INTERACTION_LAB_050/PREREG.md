# BTC_SHORT_ACCEPT25_ATR_X_72H_EXTENSION_FAILURE_INTERACTION_LAB_050

## Frozen parent
- Exact frozen ACCEPT2.5 execution lineage: 327 pre-Aug trades from LAB044/045/048/049.
- Signal family unchanged: SHORT HIGH_RESPONSE -> ACCEPT -> SL 2.5 ATR -> TP 1.5R -> original max 12h, net payoff at 5bps.
- Causal regime clock unchanged: `regime_time = entry_time - 15m`.
- Source variables already persisted in LAB045: `atr_rank_90d`, `downside_extension_72h_atr`, `net_r_5bps`, `period`.
- No August data used for selection. Live allocation = 0.

## Question
Does the positive ATR context fail when the SHORT is already too extended downward over the prior 72h?

## Primary causal interaction hypothesis
Fit one frozen linear interaction specification on the 327 trades:

`net_r_5bps = b0 + b1*ATR + b2*EXT72 + b3*(ATR*EXT72) + period fixed effects`

where:
- `ATR = atr_rank_90d` in [0,1].
- `EXT72 = downside_extension_72h_atr`, already causal at `regime_time`.
- `b3 < 0` is the preregistered sign: greater prior downside extension should reduce the benefit of high ATR.

Primary proof uses 7-day cluster bootstrap, 5000 draws. No threshold search.

## Secondary frozen diagnostics
1. Within frozen LAB049 ATR bands, estimate Spearman and linear slope of `EXT72 -> netR`:
   - LOW_BAND: ATR <0.4
   - MID_SPIKE: 0.4-0.6
   - DEAD_MID: 0.6-0.8
   - TOP_BAND: >=0.8
2. In TOP_BAND specifically, test whether extension slope is negative and whether 2025_H1 has higher mean extension than profitable TOP_BAND periods.
3. Period map for 2021, 2022, 2023, 2024, 2025_H1, 2025_H2, 2026_JAN_JUL.
4. Leave-one-period-out interaction coefficient using the exact same specification; no refitting of thresholds because there are none.

## Gates
Critical gates:
1. exact frozen N=327.
2. ATR coverage >=99%.
3. EXT72 coverage >=99%.
4. primary interaction coefficient b3 < 0.
5. primary 7d cluster bootstrap 95% CI upper < 0.
6. interaction sign negative in >=5/7 leave-one-period-out samples.
7. TOP_BAND EXT72->netR slope <0.
8. TOP_BAND EXT72 Spearman rho <0.
9. 2025_H1 TOP_BAND mean EXT72 > pooled profitable TOP_BAND periods mean EXT72.
10. 2025_H2 and 2026 TOP_BAND remain positive as guardrails.

Supporting gates:
11. period-fixed main ATR coefficient remains positive after interaction.
12. period-fixed EXT72 main coefficient is non-positive.
13. 2022 interaction-adjusted pattern not worse than parent descriptively.
14. no new cutoff/router searched.
15. August not used for selection.

## Verdict
- PASS: all critical gates and >=13/15 total.
- WATCH: interaction sign negative and >=11/15 total, but bootstrap/transfer proof incomplete.
- FAIL: interaction sign non-negative, or fewer than 11/15 gates.

Reused historical lineage; not fresh OOS.