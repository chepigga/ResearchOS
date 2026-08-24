# LAB022 post-hoc diagnostic — does not change frozen verdict

Frozen verdict remains `CALIBRATION_FIXES_PROBABILITIES_NOT_ECONOMICS`.

## What calibration fixed
Discovery-only temporal temperature scaling learned T=2.2518 for 1.5R.
On untouched Confirmation:
- logloss improved 0.9066 -> 0.8397 (-7.38%)
- multiclass Brier improved 0.5311 -> 0.5108 (-3.82%)
- macro AUC remained effectively unchanged (~0.758)
- raw payoff manager serial EV -0.1702R -> calibrated -0.1537R

Thus LAB021's diagnosis of overconfidence was real and transferable.

## Why economics remain negative
Calibration reduced model exits from ~86% to ~61% and improved management relative to the raw manager, but the calibrated manager still cannot overcome the frozen early-entry baseline EV of -0.1806R.

Among the 1,405 independent Confirmation trades where calibrated management exits:
- predicted remaining HOLD value at the decision averaged -0.0945R
- realized remaining gross value from decision-state to frozen terminal averaged only -0.0224R
So the calibrated decision boundary is no longer wildly wrong: these are close-to-indifferent remaining-value states on average.

However, the baseline entry itself is the larger problem:
- trades selected for MODEL_EXIT had frozen baseline net EV +0.3148R and TP rate 51.9%
- trades left to HOLD had frozen baseline net EV -0.8930R and TP rate 5.8%

This is not evidence that the manager should simply reverse its decisions. MODEL_EXIT trades are generally already in favorable current states where little incremental value remains; HOLD trades are often already deeply adverse, where exiting immediately locks in a large loss and continued optionality can still be better than EXIT NOW even if final trade-level EV remains negative.

## Outcome-conditioned exit balance
At calibrated model exits:
- eventual SL: N=611; exit improves trade by about +1.262R vs frozen terminal
- eventual TP: N=729; exit costs about -1.022R vs frozen terminal
- TIME: N=63; effect about +0.041R
The large loser-savings and winner-destruction nearly offset; net management lift is small.

## Interpretation
Temporal calibration solved the stated probability-calibration problem but exposed a more fundamental constraint:
**the negative expectancy is already embedded in the entry/universe before management can act.**

A management overlay can reduce tail loss / occupancy and modestly improve EV, but it is unlikely to manufacture +0.18R of edge needed to turn this frozen digestion next-open entry positive.

If research continues, the next high-value test should return to **entry price / fill frontier inside the accepted-side digestion**, not add another management classifier. A shallow pre-placed internal limit with fixed causal expiry is a cleaner hypothesis than further HOLD/EXIT modeling.
