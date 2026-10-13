# LAB253 Standalone rough replay (not MT5 parity)

Research runner created but NOT YET EXECUTED OR VALIDATED because local Python runtime is unavailable.
Clone ResearchOS and ensure frozen LAB150 input datasets, BTC M5 ZIP/CSV and user trendlines.py are accessible.

Commands from repository root:

    pip install pandas numpy
    python labs/LAB253_TRENDLINE_PORTFOLIO_20261013/export_raw_signals.py
    python labs/LAB253_TRENDLINE_PORTFOLIO_20261013/run_lab253.py --price 'btc_5m(1).zip' --raw-signals lab253_raw_signals.csv --trendlines trendlines.py --server-offset 0 --cost-bps 7.5 --out lab253_results

Outputs: summary.csv, trades.csv, equity_VARIANT.csv, cl_breaks.csv, correction_states.csv, metadata.json.

Baseline must reproduce LAB151 reference prior to trusting any comparison: stress 7.5bps, N341, EV+0.571R, PF1.91, MTM-DD4.52%.
Variants BASE, TL_FILTER, TL_TRAIL, TL_ADD, COMBINED. Trailing variant removes fixed TP3R to test >3R capture; keeps SL tightening only.

Limitations: synthetic-only validation of user trendlines.py; fixed server UTC offset no DST support; shared EMA-retest cooldown missing; ATR parity not independently verified; stop-first M5 OHLC; MTM DD close-to-close proxy; no real fill or prop reset; API latency uncertain.
Production v157 untouched.