# LAB_LSR_SNAP_001 — L/S peak snap

Data: 2022-01-19 → 2026-10-19, bars=499,089. OOS from 2025-01-01.

Params: Z_WIN=288, Z_PEAK=1.5, PEAK_LOOK=12, SNAP_K=3, SNAP_MIN=0.5, COOLDOWN=48, DELAY=1, ATR_N=48, SL_ATR=1.0, FT_HORIZON=48, MFE_HORIZON=48, MAX_HOLD=288, COST_BPS=4.0, LEVEL_LOOK=288, FEAT_LOOK=12, OOS_FROM=2025-01-01

Events: 1673 (long-skew 852, short-skew 821); with level break: 530

Base rate (random bar, long, ±1 ATR first touch): 49.1% n=4996


## H1 — Direction after snap (first touch ±1 ATR / ±2 ATR, horizon 48 bars)

| Variant | Split | Win ±1ATR | Win ±2ATR | MFE mean (ATR) | MAE mean (ATR) |
|---|---|---|---|---|---|
| PRICE | IS |  45.4% [42.6–48.3] n=1151 |  47.9% [45.0–50.8] n=1119 | 4.50 | 4.44 |
| PRICE + level | IS |  44.2% [39.1–49.5] n=346 |  51.0% [45.7–56.3] n=339 | 5.09 | 4.25 |
| PRICE | OOS |  45.8% [41.6–50.1] n=522 |  51.1% [46.8–55.4] n=511 | 5.48 | 4.39 |
| PRICE + level | OOS |  38.6% [31.9–45.8] n=184 |  44.6% [37.6–51.8] n=184 | 5.77 | 4.68 |
| PRICE | ALL |  45.5% [43.2–47.9] n=1673 |  48.9% [46.5–51.3] n=1630 | 4.81 | 4.42 |
| PRICE + level | ALL |  42.3% [38.1–46.5] n=530 |  48.8% [44.5–53.0] n=523 | 5.32 | 4.40 |
| FADE | IS |  48.3% [45.4–51.2] n=1151 |  48.7% [45.8–51.6] n=1119 | 4.53 | 4.41 |
| FADE + level | IS |  43.6% [38.5–48.9] n=346 |  49.3% [44.0–54.6] n=339 | 4.65 | 4.69 |
| FADE | OOS |  44.3% [40.0–48.5] n=522 |  46.8% [42.5–51.1] n=511 | 5.08 | 4.79 |
| FADE + level | OOS |  39.1% [32.4–46.3] n=184 |  42.4% [35.5–49.6] n=184 | 5.68 | 4.77 |
| FADE | ALL |  47.0% [44.7–49.4] n=1673 |  48.1% [45.7–50.5] n=1630 | 4.70 | 4.53 |
| FADE + level | ALL |  42.1% [37.9–46.3] n=530 |  46.8% [42.6–51.1] n=523 | 5.01 | 4.72 |

Win ±1ATR: 50% = coin. Win ±2ATR is symmetric too (target 2ATR vs stop 2ATR).

## H2 — Magnitude: peak |z| and snap speed vs MFE (Spearman)

- PRICE: ρ(|peak|, MFE) = -0.031; ρ(|snap|, MFE) = +0.068
- FADE: ρ(|peak|, MFE) = -0.028; ρ(|snap|, MFE) = +0.005

| |peak| tercile | n | MFE price | MFE fade |
|---|---|---|---|
| low | 558 | 5.14 | 4.76 |
| mid | 557 | 4.88 | 4.94 |
| high | 558 | 4.40 | 4.40 |

## H3 — Exit models (R after 4.0 bps cost, stop 1.0 ATR, max hold 288 bars)

| Variant | Exit | IS mean R [95% CI] | OOS mean R [95% CI] | win% ALL |
|---|---|---|---|---|
| PRICE | R2 | -0.275 [-0.352…-0.195] | -0.267 [-0.398…-0.139] | 32.6% |
| PRICE | Z0 | -0.149 [-0.363…+0.095] | -0.076 [-0.433…+0.320] | 16.6% |
| PRICE | OPP | -0.149 [-0.412…+0.124] | -0.059 [-0.441…+0.343] | 10.9% |
| PRICE | SLOPE | -0.167 [-0.368…+0.066] | -0.004 [-0.390…+0.511] | 17.8% |
| PRICE | COMBO | -0.137 [-0.356…+0.117] | -0.050 [-0.409…+0.344] | 16.1% |
| FADE | R2 | -0.233 [-0.310…-0.150] | -0.357 [-0.479…-0.235] | 32.8% |
| FADE | Z0 | +0.044 [-0.203…+0.321] | -0.020 [-0.496…+0.538] | 15.5% |
| FADE | OPP | +0.007 [-0.267…+0.336] | +0.011 [-0.473…+0.602] | 10.2% |
| FADE | SLOPE | -0.192 [-0.339…-0.035] | -0.179 [-0.436…+0.085] | 19.5% |
| FADE | COMBO | +0.015 [-0.229…+0.292] | -0.010 [-0.479…+0.552] | 15.2% |

## H4 — Path: P(price up first, ±1 ATR) by flow feature at the snap

Long-skew = crowd long and unwinding. Base rate above.

| Skew | Feature | TRUE | FALSE |
|---|---|---|---|
| long | basis<0 (perp discount) |  49.1% [45.5–52.7] n=737 |  47.8% [38.9–56.9] n=115 |
| long | spot CVD 1h > 0 |  48.9% [44.1–53.7] n=411 |  49.0% [44.3–53.6] n=441 |
| long | taker 1h > 1 (buyers) |  48.1% [43.0–53.2] n=364 |  49.6% [45.2–54.0] n=488 |
| long | OI 1h falling |  50.2% [45.9–54.5] n=512 |  47.1% [41.8–52.4] n=340 |
| long | top positions 1h falling |  51.1% [45.6–56.7] n=307 |  47.7% [43.5–51.9] n=545 |
| short | basis<0 (perp discount) |  46.4% [42.8–50.0] n=722 |  45.5% [36.0–55.2] n=99 |
| short | spot CVD 1h > 0 |  41.0% [36.1–46.0] n=376 |  50.8% [46.2–55.4] n=445 |
| short | taker 1h > 1 (buyers) |  44.8% [39.4–50.2] n=324 |  47.3% [42.9–51.7] n=497 |
| short | OI 1h falling |  45.8% [41.5–50.3] n=493 |  47.0% [41.6–52.4] n=328 |
| short | top positions 1h falling |  54.9% [49.2–60.5] n=293 |  41.5% [37.4–45.7] n=528 |

Signal = the TRUE/FALSE intervals don't overlap and both differ from the base rate.

## H5 — Lead/lag: corr(Δz[t], return[t+lag]), 5m, metric delay 1 bar(s)

| lag | corr |
|---|---|
| -6 | -0.0617 |
| -5 | -0.0664 |
| -4 | -0.0725 |
| -3 | -0.0938 |
| -2 | -0.0736 |
| -1 | +0.1687 |
| +0 | +0.0764 |
| +1 | -0.0285 |
| +2 | -0.0063 |
| +3 | -0.0039 |
| +4 | -0.0050 |
| +5 | -0.0071 |
| +6 | -0.0027 |

Negative lags = price before Δz (L/S reacts to price). Positive lags = Δz predicts price.

## Reading guide

- Edge only if OOS confirms IS and the CI excludes 0 (R) or 50% (win rate).
- Prop rule: a variant is worth an EA only with OOS mean R > 0 after costs AND enough events.