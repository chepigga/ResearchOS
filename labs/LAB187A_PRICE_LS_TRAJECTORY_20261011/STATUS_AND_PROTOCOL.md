# LAB187A — PRICE STRUCTURE × L/S TRAJECTORY
2026-10-11 — PARTIAL EXECUTION / SOURCE BLOCKER

## Frozen price-only population
5089 first chronological H1 Sweep/Reclaim setups from LAB186. 942 TP first (18.51% of all), 3800 SL first, 347 timeout, M5 OHLC simulation, not broker execution and not fees-adjusted. All signal parameters frozen. Annual direction table is generated in LAB187A_PRICE_ONLY_BASELINE.csv.

## Critical L/S source blocker
BTC M5 and LAB185/186 files are available in local research environment, but historical Binance account long/short ratio time series with **observed publication/availability timestamps** is absent from current local material; GitHub repo code searches did not locate a usable series. No Crowd/OI/Volume Profile value is fabricated. There is currently **no valid Price+L/S estimated effect**.

## Preregistered joining protocol
Source must supply UTC event_time, available_time, ratio, source, metric_type; metric_type should explicitly distinguish global account ratio from top-trader account/position ratios. Each decision checkpoint: H1 reclaim close; M15 confirmation close; M5 next-open. Join only last observation with available_time <= decision_time and freshness <=12h; retain missing as missing (no future fill). Ratio must be positive. Check exchange sampling cadence and actual publication timing; do not infer available_time == event_time without proof.

## Planned incremental feature set (no tuning on CHECK)
L/S ratio level, trailing causal z-score over 6h/24h (minimum completed sample requirements), 1h and 6h change, slope and acceleration; price-alignment/conflict/neutral buckets must be computed for prior known publication snapshots. Avoid global hindsight normalization, correct for historical changes in sampling, and preserve missing-value coverage. Matched comparison on IDENTICAL baseline rows: price only vs Price + L/S only; additionally L/S-only event grid on the same times. Stratify continuation/reversal/range and H4 alignment, periods 2021–23 fit, 2024 validate, 2025–2026 CHECK reused previously (not pristine OOS). No MAE oracle selection.

## Files
Local executable join script: /mnt/data/lab187a_price_ls_audit.py; price control table: /mnt/data/LAB187A_PRICE_ONLY_BASELINE.csv. Running script without an L/S source creates only honest baseline; with validated L/S CSV it produces as-of joined LAB187A_CAUSAL_LS_JOIN.csv.

## Stop criteria
Without verified historical L/S source and publication timestamps, no claim about differential TP-first, EV or statistical signal confidence is permitted. No EA deployment. Broker/prop specs required for production code.
