# LAB020 post-hoc diagnostic — does not change frozen verdict

Frozen verdict remains `NO_LIVE_STATE_MANAGEMENT_EDGE`.

## 1. Predictive information exists, but expected-R transfer fails

On Confirmation snapshots:
- MINIMAL (`current_R + time + dir + p_accept + level`) AUC for `hold_advantage_R > 0`: **0.6064**.
- FULL live state AUC: **0.5938**.
- FULL minus MINIMAL: **-0.0126 AUC**.

Thus adding MFE/MAE, tempo, acceptance and event flags does not improve transferable ranking. Position geometry is the dominant source of information.

However, even the better MINIMAL ranking does not create management edge. Post-hoc MINIMAL management is also negative (serial EV about **-0.177R**) and has negative paired lift.

## 2. Sign calibration is the central failure

The regression is asked to predict *expected R gained by holding versus exiting at the current mark*. On Confirmation, the sign of the prediction is badly transferred:

FULL model, first live decision per trade:
- predicted EXIT: actual mean hold advantage **+0.013R**;
- predicted HOLD: actual mean hold advantage **-0.014R**.

Across all snapshots:
- FULL predicted EXIT: actual mean hold advantage **+0.034R**;
- FULL predicted HOLD: actual mean hold advantage **-0.008R**.

The model can rank the *probability* that hold advantage is positive, but it does not preserve the *magnitude-weighted expected value* needed for a management decision.

## 3. Why current adverse R is deceptive

Fixed current-R bins show that deeply adverse but still-alive positions often retain slightly positive mean hold advantage:
- current R in (-1.0,-0.75]: actual hold advantage **+0.039R** while model mean prediction is **-0.085R**;
- (-0.75,-0.50]: **+0.033R** vs prediction **-0.148R**;
- (-0.50,-0.25]: **+0.076R** vs prediction **-0.169R**.

This is economically intuitive: once a trade is already near SL but has not hit it, the incremental downside left to the original SL is small while the remaining upside to TP can still be large. A frequency classifier can therefore prefer EXIT even when the payoff-weighted HOLD option remains valuable.

## 4. Saved losers vs destroyed winners

Confirmation independent trades by frozen baseline outcome:
- eventual SL: manager improves average R by about **+0.649R**, but exits **87.7%** of them;
- eventual TP: manager destroys about **-1.230R** per trade and exits **76.9%** of them;
- eventual TIME exits: delta about **-0.330R**.

The saved losers are not enough to offset the value destroyed in winners.

## 5. Feature-group diagnostic

On the fixed Confirmation sample, grouped permutation importance is dominated by POSITION geometry. Acceptance adds only a small amount, while event flags and frozen context do not improve the full model OOS.

## Interpretation

LAB020 does not show that live state is useless. It shows that a single direct regression of `final_R - current_R` is not a robust management decision engine across time. The next rational management formulation should separate:
1. probability of TP / SL / time outcome from the current live state;
2. the payoff remaining to each outcome from the current R;
3. then compute decision-theoretic HOLD EV explicitly.

That decomposition would preserve the asymmetry that direct regression appears to lose. It would be a new preregistered LAB, not a rescue of LAB020.
