# BTC_PRE_BOS_AGGRESSIVE_FLOW_X_LARGE_BREAKOUT_LAB_007

## Status

PASS as a research signal: Binance aggressive-flow variables add incremental held-out 2026 information beyond the price-only precursor set. The original simple hypothesis `high counter-side aggression + low price progress = absorption` is NOT supported.

## Data and parity

Native Binance BTCUSDT M15 replication using frozen release data through 2026-08-09. LAB005/006 event logic was ported from the MQL5 research script; all precursor features stop before the BOS candle.

- Native Binance signals: 3232
- Executable labeled events: 1661
- LARGE >= 2.5R before structural SL within 32 M15 bars: 257 (15.47%)
- EXTREME >= 4R: 119
- FAIL: 759
- MT5 reference: 1601 executable / 234 LARGE = 14.62%

Year LARGE rates on Binance-native replication:

- 2023: 16.79%
- 2024: 17.08%
- 2025: 12.32%
- 2026 through Aug 9: 16.24%

Direction:

- SELL: 142/825 = 17.21%
- BUY: 115/836 = 13.76%

The native Binance event count is not expected to equal MT5 exactly because pivots/BOS are reconstructed on Binance BTCUSDT rather than event-level joined to MT5 BTCUSD. The close LARGE-rate parity (15.47% vs 14.62%) is encouraging but is not exact execution parity.

## Main held-out 2026 result

Train = 2023-2025. Test = 2026.

| Model | AUC | Average Precision | Brier | Top 20% LARGE rate |
|---|---:|---:|---:|---:|
| Price only | 0.5264 | 0.2011 | 0.1383 | 14.55% (n=55) |
| Price + Binance aggressive flow | 0.6037 | 0.2592 | 0.1348 | 25.45% (n=55) |

Increment from flow:

- AUC: +0.0773
- Average Precision: +0.0581
- Brier improvement: +0.0035
- Top-20% selection: 14.55% -> 25.45%
- 2026 unconditional LARGE baseline: 16.24%

This is meaningful incremental rankability, but not yet a frozen trading selector.

## Original participant hypothesis falsification

The preregistered intuitive rules did not work:

| Rule | Train LARGE | Train neutral lift | 2026 LARGE | 2026 neutral lift |
|---|---:|---:|---:|---:|
| High counter aggression + low counter progress | 14.09% | -1.58pp | 11.27% | -5.20pp |
| Same + short-term flow flip | 15.43% | -0.32pp | 12.82% | -3.37pp |
| High counter-side share only | 15.20% | -0.29pp | 11.83% | -4.54pp |
| Flow flip only | 15.50% | -0.06pp | 18.66% | +2.57pp |

Therefore `counter-side aggressive volume is high but price refuses to move` is not the invariant in this dataset.

## What did transfer

The strongest recurring signal is almost the opposite: LARGE breakouts tend to come out of BELOW-NORMAL Binance activity immediately before BOS.

Large-vs-nonlarge standardized effects include:

- trades_z_3: -0.191 SD
- trades_z_6: -0.182 SD
- trades_z_12: -0.183 SD
- counter_volume_z_12: -0.159 SD
- total_volume_z_12: -0.155 SD
- total_volume_z_3: -0.152 SD
- counter_volume_z_3: -0.150 SD

At the same time, 12-bar directional aggressive-flow balance is mildly more aligned with the future BOS direction:

- future_share_12: +0.174 SD
- flow_delta_12: +0.174 SD
- counter_share_12: -0.174 SD

So the emerging state is better described as:

`participation/activity contracts -> counter-side pressure is not dominant -> mild directional taker imbalance appears -> BOS -> large expansion`

rather than:

`huge counter-side aggression is absorbed -> BOS`.

## Frozen train quantile diagnostics on 2026

Thresholds were derived from 2023-2025 and then applied to 2026. Examples:

- counter_volume_z_3 lowest quintile: train 20.14% LARGE / +4.51pp neutral lift; 2026 26.19% / +10.46pp (n=42)
- total_volume_z_6 lowest quintile: train 20.14% / +4.36pp; 2026 26.19% / +10.36pp (n=42)
- trades_z_12 lowest quintile: train 21.22% / +4.99pp; 2026 25.00% / +8.97pp (n=40)
- trades_z_6 lowest quintile: train 19.78% / +4.00pp; 2026 23.91% / +7.98pp (n=46)
- total_volume_z_12 lowest quintile: train 21.22% / +5.30pp; 2026 23.68% / +7.77pp (n=38)

Caution: these bins are diagnostic. Ranking the displayed bins by their 2026 lift is post-test inspection and must not be treated as a newly frozen OOS selector.

## Verdict

**Research verdict: PASS / promising, not production-ready.**

Binance taker-flow contains incremental information about which BOS events become LARGE. The strongest transferable footprint is not classical absorption via high opposing aggression; it is low pre-BOS participation/activity plus a mild flow alignment/transition.

Next required experiment should freeze a compact `LOW_ACTIVITY + FLOW_ALIGNMENT/FLIP` selector using only pre-2026 training logic, run year/side ablations, and then obtain an untouched extension (preferably Binance data after 2026-08-09 or another venue) before claiming a deployable edge.
