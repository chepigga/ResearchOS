# LAB021 post-hoc diagnostic — does not change frozen verdict

Frozen verdict remains `NO_OUTCOME_X_PAYOFF_MANAGEMENT_EDGE`.

## Strong ranking, weak value calibration

The FULL outcome model has useful OOS ranking information (macro OVR AUC 0.7581; TP 0.7236; SL 0.7223; TIME 0.8283), but probability magnitudes are too extreme for an expected-value decision rule.

Confirmation calibration examples:
- FULL TP Q1: mean pTP ~0.069 vs actual TP ~0.162.
- FULL TP Q5: mean pTP ~0.800 vs actual TP ~0.680.
- FULL SL Q1: mean pSL ~0.128 vs actual SL ~0.208.
- FULL SL Q5: mean pSL ~0.901 vs actual SL ~0.748.

Thus low probabilities are too low and high probabilities too high. FULL is also slightly worse than MINIMAL in log-loss/Brier despite higher macro AUC.

## Decision-boundary failure

The primary rule exits when predicted remaining HOLD EV <= 0. It triggers on ~85.4% of independent Confirmation trades, with median managed duration 1 minute.

Among 2,010 model-exit trades:
- mean predicted remaining EV at the exit decision is strongly negative (~-0.23R);
- actual mean remaining HOLD value from that state is approximately +0.01R overall.

By terminal baseline class among model exits:
- eventual SL: N 1,320; actual remaining HOLD value ~-0.738R;
- eventual TP: N 625; actual remaining HOLD value ~+1.554R;
- eventual TIME: N 65; actual remaining HOLD value ~+0.333R.

This reproduces the asymmetry seen in LAB020: the model can identify many bad states, but the selected exit boundary still contains enough future winners with large upside that saved losses are offset.

## Outcome-conditioned economics

Across all independent Confirmation trades:
- eventual SL: management improves baseline by about +0.647R/trade;
- eventual TP: management reduces baseline by about -1.236R/trade;
- eventual TIME: management reduces baseline by about -0.328R/trade.

Hence the issue is not absence of state information. The issue is using uncalibrated class probabilities directly as money probabilities at a tail-sensitive decision boundary.

## Interpretation

LAB021 validates the decomposition idea partially: terminal outcome ranking is much stronger than direct residual-R prediction from LAB020. But expected-value management requires calibrated probabilities, especially around the EXIT/HOLD boundary. A rational next study is temporal Discovery-only probability calibration while keeping the frozen outcome-model features, payoff equation, entry, SL/TP and Confirmation untouched. This is a new hypothesis and is not authorized by LAB021.
