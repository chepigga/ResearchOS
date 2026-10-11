# LAB195 BREAKOUT × STOP × COST forensic audit

2026-10-11. Frozen LAB194 4411 trades and full BTC M5 source.

**Total:** TP 1355 (30.7%), SL 2789 (63.2%), timeout 267; gross EV +0.0053R, hypothetical all-in 10bps EV -0.1981R. Median cost debit 0.1476R. 968/2789 stopped trades (34.7%) subsequently reached their ORIGINAL TP by 24h since entry. This is POST-TRADE oracle path info and does not prove a wider stop makes money.

**Critical skew:** 4351 Acceptance events vs 60 Rejection. Current result cannot validate reversal engine.

Stop-distance bins in ATR(M5): <1 ATR 55, 73.2% stop-then-TP, -0.634R net; 1–2 ATR 456 59.8%, -0.193R; 2–4 ATR 1660 40.7%, -0.198R; >4 ATR 2240 23.4%, -0.188R.

Session mean 10bps EV: Asia UTC0–6 -0.172R (1150), Europe7–12 -0.225R (1042), US13–20 -0.202R (1677), Late21–23 -0.190R (542). Hypothesis that Asia is main loss driver is unsupported.

Low volatility quartile -0.350R, other vol quartiles -0.136 to -0.157R. Median cost in low-vol quartile 0.307R versus high-vol 0.068R. Breakout candle body fraction quartiles -0.205,-0.255,-0.163,-0.169R; signed displacement quartiles -0.208,-0.185,-0.181,-0.218R; no monotonic breakout-quality edge. Volume multiplier quartiles -0.249,-0.240,-0.186,-0.117R (even highest loses).

**Interpretation:** gross edge virtually zero, costs wipe out profits, early stop-outs common, and signal taxonomy strongly favors ACCEPT. Not proof that altered SL is better. Next LAB196 should perform causal paired execution experiment on identical source breakout episodes with alternative SL/confirmed entry, full RR requalification, true available pivot TP, and cost sensitivity. Broker fees/stop levels still require explicit account specifications.

Local source and outputs: /mnt/data/lab195_audit.py, LAB195_TRADE_DIAGNOSTICS.csv, LAB195_BREAKDOWN.csv, LAB195_REPORT.md.
