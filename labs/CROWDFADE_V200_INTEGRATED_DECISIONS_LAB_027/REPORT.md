# CROWDFADE_V200_INTEGRATED_DECISIONS_LAB_027

## Purpose

Test all major v200 strategy decisions as an integrated causal system instead of combining conclusions from separate LABs.

Frozen entry core:

- ZLong = 2.50
- ZShort = 2.50
- M15 confirmation = 0.25 ATR
- confirmation TTL = 60m
- passive retrace = 0.60 ATR
- limit TTL = 20m
- hard SL = 4.5 ATR
- max hold = 24h
- anti-repeat = 1 ATR
- max 3 trades/day

Decision matrix:

1. fixed TP 10 ATR vs NO fixed TP
2. trail OFF vs 2.5R trail armed at +1R
3. flat risk vs LAB026 tiers:
   - HIGH 1.50x
   - NORMAL 1.00x
   - LOW 0.75x

The full v200 configuration tested here is:

> NO fixed TP + 2.5R trail + LAB026 risk tiers

---

# Historical 2021–2025

| Mode | N | SumR | EV | PF | MaxDD | R/DD | +years |
|---|---:|---:|---:|---:|---:|---:|---:|
| TP10 flat | 1227 | +130.60R | +0.1064 | 1.210 | 13.50R | 9.675 | 5/5 |
| **TP10 + LAB026** | 1227 | **+167.62R** | **+0.1366** | **1.254** | **13.39R** | **12.523** | **5/5** |
| TP10 + trail2.5 flat | 1228 | +126.15R | +0.1027 | 1.204 | 14.44R | 8.738 | 5/5 |
| TP10 + trail2.5 + LAB026 | 1228 | +164.29R | +0.1338 | 1.250 | 15.11R | 10.873 | 5/5 |
| NoTP / no trail flat | 1150 | +147.39R | +0.1282 | 1.246 | 20.88R | 7.060 | 5/5 |
| NoTP / no trail + LAB026 | 1150 | +179.16R | +0.1558 | 1.282 | 20.28R | 8.833 | 5/5 |
| NoTP + trail2.5 flat | 1163 | +150.86R | +0.1297 | 1.258 | 16.85R | 8.955 | 5/5 |
| **V200 FULL** | 1163 | **+183.24R** | **+0.1576** | 1.296 | **19.33R** | **9.479** | 5/5 |

Historical interpretation:

- Removing fixed TP raises absolute SumR in-sample because some large winners survive.
- But it materially increases DD and reduces sequence efficiency.
- LAB026 improves every comparable exit regime.
- Best historical R/DD is **TP10 + LAB026**, not v200 full.
- 2.5R trailing with fixed TP does not improve historical robustness.

V200 full annual:
- 2021 +57.79R
- 2022 +45.81R
- 2023 +39.60R
- 2024 +19.21R
- 2025 +20.83R

The system remains profitable every year, but 2024/2025 are much weaker in efficiency.

Exit mix v200 full:
- SL 526
- TRAIL 121
- TIME 516
- TP 0

The high number of TIME exits is a major behavioral change.

---

# 2026 second-level forward-shadow / stress

| Mode | N | SumR | EV | PF | MaxDD | R/DD | +months |
|---|---:|---:|---:|---:|---:|---:|---:|
| TP10 flat | 136 | +28.71R | +0.2111 | 1.467 | 6.49R | 4.424 | **6/6** |
| **TP10 + LAB026** | 136 | **+35.85R** | **+0.2636** | 1.566 | 6.75R | **5.313** | 5/6 |
| TP10 + trail2.5 flat | 136 | +29.80R | +0.2191 | 1.494 | **6.39R** | 4.665 | **6/6** |
| **TP10 + trail2.5 + LAB026** | 136 | **+37.07R** | **+0.2726** | **1.597** | **6.68R** | **5.552** | 5/6 |
| NoTP / no trail flat | 126 | +16.10R | +0.1278 | 1.267 | 10.38R | 1.551 | 4/6 |
| NoTP / no trail + LAB026 | 126 | +15.39R | +0.1222 | 1.244 | 12.25R | 1.256 | 4/6 |
| NoTP + trail2.5 flat | 127 | +13.56R | +0.1068 | 1.236 | 10.30R | 1.316 | 5/6 |
| **V200 FULL** | 127 | **+15.16R** | **+0.1193** | **1.254** | **11.82R** | **1.282** | **4/6** |

## Critical result

Current v200 full is much worse than the fixed-TP alternatives in 2026.

Versus TP10 + LAB026:

- trades: 136 -> 127
- SumR: +35.85 -> **+15.16R**
- EV: +0.2636 -> **+0.1193R**
- PF: 1.566 -> **1.254**
- DD: 6.75 -> **11.82R**
- R/DD: 5.313 -> **1.282**
- positive months: 5/6 -> **4/6**

Current v200 full monthly:

- Mar +7.11R
- Apr +2.02R
- May +5.44R
- Jun +4.62R
- Jul **-2.27R**
- Aug **-1.78R**

Exit mix:
- SL 51
- TRAIL 15
- TIME 61
- TP 0

## Why removing TP fails

The effect is not only that winners can give profit back.

Longer-lived positions change the causal system:

- positions occupy the single BTC slot longer;
- later signals become unreachable;
- trade count falls;
- more exits occur at 24h instead of at the profitable fixed target;
- the 2.5R trail is deliberately wide and therefore protects only very large MFE;
- many trades that would have exited at +2.22R remain exposed.

2026 demonstrates that this occupancy/right-tail trade-off is unfavorable.

---

# Decision audit

## PASS — symmetric Z 2.50 / 2.50

Retained from LAB016.

## PASS — M15 confirmation 0.25 ATR / TTL 60m

Frozen core. No evidence in LAB027 to change it.

## PASS — passive retrace 0.60 ATR / TTL 20m

Frozen core.

## PASS — hard SL 4.5 ATR

Still the robustness anchor.

## PASS — LAB026 quality sizing

The quality-aware sizing remains useful.

With fixed TP it improves historical R/DD from 9.675 to 12.523 and 2026 R/DD from 4.424 to 5.313.

## FAIL — removing fixed TP

This is the largest failed v200 decision.

No-TP variants have worse 2026 SumR, DD and R/DD, and fewer reachable trades.

## MIXED / WATCH — 2.5R trailing

With fixed TP:
- historical slightly worse;
- 2026 slightly better.

Therefore 2.5R trail is not independently robust enough to replace fixed TP.

It may remain a watch option if fixed TP is retained.

## PASS — BE OFF

No new reason to enable BE.

## PASS — partial OFF

No evidence to enable partial exits.

## PASS — signal reversal exit OFF

No new evidence here to re-enable it.

## PASS — max hold 24h only as fallback

24h is acceptable with fixed TP because most large winners can exit earlier at target.

Without fixed TP it becomes too dominant: 516 historical and 61/127 2026 v200 trades exit by TIME.

---

# Source-code audit of CrowdFadeMulti_v200.mq5

Static checks passed:

- balanced braces/parentheses/brackets;
- Z 2.50 / 2.50 present;
- SL 4.5 ATR present;
- confirm 0.25 ATR and 4 M15 bars present;
- retrace 0.60 ATR present;
- max 3/day present;
- BE/partial/chase disabled by default;
- LAB026 1.50 / 1.00 / 0.75 active;
- no TP is actually sent in pending orders;
- trail is expressed in initial-R units;
- risk registration begins on actual fill.

Unit check of wide trail:

- MFE 1.0R -> hard stop remains -1R
- MFE 1.5R -> stop ~-1R
- MFE 2.0R -> stop ~-0.5R
- MFE 2.5R -> stop ~0R
- MFE 3.5R -> stop ~+1R
- MFE 5.0R -> stop ~+2.5R

So the 2.5R trail implementation is mechanically correct.

## Parity warning found

The current v200 code calls the ATR pause gate twice inside TryEnter:

1. when the original extreme signal arms confirmation;
2. again after confirmation before sending the passive limit.

The research sequence applies the inherited anti-repeat gate at the original signal state.

This second live check can reject a signal after it already passed the research gate if price moves back toward the previous entry during confirmation.

Status:
- **parity discrepancy identified**
- not yet promoted as a fix until quantified

## Execution-only items not reproducible from Binance OHLC

These require demo-forward logs:

- actual broker spread gate behavior;
- ORDER_TIME_SPECIFIED support / expiration behavior;
- passive queue/fill probability;
- partial fills;
- slippage;
- exact commission;
- 1-second timer peak capture vs exchange tick peak.

The MQL5 API signatures used for BuyLimit and PositionModify are valid, and the code checks trade retcodes after requests.

---

# Recommended configuration after LAB027

Best robust candidate from the tested matrix:

> **fixed TP 10 ATR + LAB026 risk tiers + trailing OFF**

Configuration:

- SL 4.5 ATR
- TP 10 ATR = about +2.22R
- max hold 24h fallback
- HIGH 1.50x
- NORMAL 1.00x
- LOW 0.75x
- BE OFF
- partial OFF
- signal exit OFF

Alternative watch configuration:

> fixed TP 10 ATR + LAB026 + 2.5R trailing

It is stronger in 2026 but weaker historically, therefore not the robustness winner.

Current no-fixed-TP v200 should **not** be treated as validated for demo deployment.
