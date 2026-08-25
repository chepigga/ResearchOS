# LAB024 post-hoc diagnostic — does not change frozen verdict

Frozen verdict remains `NO_SHALLOW_ADVERSE_EXCURSION_KILL_EDGE`.

## Why the primary protective kill failed
The preregistered primary kill used executable exit quote-space:
- BUY trigger on BidLow <= entry - 0.10 ATR;
- SELL trigger on AskHigh >= entry + 0.10 ATR.

Because the frozen early entry itself is BUY at AskOpen / SELL at BidOpen, spread is already embedded between entry and executable exit quote. As a result, the 0.10 ATR protective threshold was effectively a very tight stop including spread.

Observed Confirmation:
- trigger rate 75.19%;
- every trigger occurred on the entry M1 bar (`T0`);
- primary manager TP rate collapsed to ~0.33% in serial trading.

Thus LAB024 did not faithfully isolate the LAB023 *price-path* event; it tested an executable tight protective stop whose distance included spread.

## Quote-space parity with LAB023
A post-hoc diagnostic reconstructed the exact LAB023 event definition, without applying a management rescue:
- BUY event: AskLow <= frozen Ask-entry - 0.10 ATR within the first 5 active M1 bars;
- SELL event: BidHigh >= frozen Bid-entry + 0.10 ATR within the first 5 active M1 bars.

Confirmation reproduces LAB023 exactly:
- SAME-SIDE EARLY5 event: N=1839 (78.12%), frozen baseline EV -0.382746R, TP 24.90%; mean first-event delay 0.64 min;
- NO event: N=515 (21.88%), frozen baseline EV +0.579994R, TP 63.30%.

Therefore the strong causal information from LAB023 is real and reproducible. The failed LAB024 primary result is specifically about using a 0.10 ATR *executable opposite-quote protective stop*, not about invalidating the same-side early price-excursion signal.

## Correct next causal execution question
A future LAB must keep the LAB023 same-side event definition but separate **signal measurement** from **exit execution**:
1. observe same-side excursion during the first 5 M1 bars;
2. do not pretend the opposite-side executable quote equals the signal threshold;
3. with M1 bid/ask OHLC, use a conservative causal execution such as next-M1-open after the completed trigger bar, with original TP/SL barrier precedence;
4. compare saved losers versus destroyed winners and opportunity cost without threshold rescue.

This should be a new preregistered LAB, not a repair of LAB024.
