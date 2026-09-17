# RAW CHRIS XAU 30M DIRECTIONAL TRANSFER NO STOP — LAB012

**Status:** `HISTORICAL_RAW_CHRIS_XAU_30M_DIRECTIONAL_TRANSFER_FAIL_SMALL_SAMPLE_NOT_OOS`

Frozen Chris SHORT transferred to executable FTMO-Demo XAUUSD with no SL/TP/limit/new filter. Entry = Bid; exit exactly +30m = Ask; spread embedded.

## Aggregate

- Signals: **23**
- Executable: **23**
- EV: **-0.1670 XAU ATR** / **-2.5244 bps**
- Median: **-0.4912 ATR**
- WR: **43.5%**
- Sum: **-3.8399 ATR**
- Bootstrap P(EV>0): **40.9%**; 95% CI **[-1.7665, +1.4491] ATR**

## Monthly

- 2026-08: N=12, EV=-1.3147 ATR, Sum=-15.7768 ATR, WR=33.3%
- 2026-09: N=11, EV=+1.0852 ATR, Sum=+11.9369 ATR, WR=54.5%

## Frozen gates

- PASS — `signals_ge20`
- PASS — `executable_ge20`
- FAIL — `gross_ev_atr_pos`
- FAIL — `gross_ev_bps_pos`
- FAIL — `wr_ge50pct`
- FAIL — `aug_ev_nonneg`
- PASS — `sep_ev_nonneg`
- FAIL — `bootstrap_p_ge080`

## Decision

Raw Chris 30m direction does not pass the preregistered executable-XAU transfer gates on this overlap. Do not rescue by tuning hold time, session, entry delay, spread filter, stop, target, or selector on this same sample.
