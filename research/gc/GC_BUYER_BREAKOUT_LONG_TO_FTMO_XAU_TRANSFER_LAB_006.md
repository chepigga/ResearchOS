# GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006

**Verdict: TRANSFER_FAIL**

Clock calibration: `FTMO clock = UTC +3.0h`; M1 return correlation = **0.9869** on N=38000 common M1 returns.

Primary horizon was frozen at **15 minutes** before this run. Entry is XAU Ask; exit is XAU Bid; quoted spread is therefore included.

| Feed | Candidate N | XAU EV 15m (bps) | EV 15m (ATR) | WR | Positive days | Price-no-OF EV (bps) | Incremental (bps) | Day CI95 (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RITHMIC | 301 | +0.162 | +0.086 | 49.5% | 18/34 | -0.467 | +0.629 | [-1.835,+2.042] |
| AMP | 280 | +0.299 | +0.139 | 48.2% | 16/33 | -1.122 | +1.422 | [-1.878,+2.321] |

Exact common-clock candidate subset: **N=246**, XAU 15m EV **+0.660 bps**, WR **48.8%**.

## Horizon profile — candidate only

| Feed | 1m | 3m | 5m | 10m | 15m | 30m | 60m |
|---|---:|---:|---:|---:|---:|---:|---:|
| RITHMIC | -1.271 | -0.893 | -0.629 | -0.043 | +0.162 | -0.546 | +1.356 |
| AMP | -1.151 | -1.030 | -0.649 | +0.356 | +0.299 | -0.824 | -0.515 |

## Gate

- PASS — `rithmic_n_ge100`
- PASS — `amp_n_ge100`
- PASS — `rithmic_ev15_bps_pos`
- PASS — `amp_ev15_bps_pos`
- PASS — `rithmic_ev15_atr_pos`
- PASS — `amp_ev15_atr_pos`
- PASS — `rithmic_incremental_vs_price_no_of_pos`
- PASS — `amp_incremental_vs_price_no_of_pos`
- PASS — `common_clock_ev15_pos`
- PASS — `rithmic_positive_days_ge50pct`
- FAIL — `amp_positive_days_ge50pct`

## Governance

No GC threshold, session filter, stop, take-profit, time-stop, retest entry or XAU outcome filter was optimized in this LAB. Commission and discretionary slippage are not applied; quoted FTMO spread is already included through Ask-entry/Bid-exit. If this transfer passes, execution geometry belongs in a separate LAB007.
