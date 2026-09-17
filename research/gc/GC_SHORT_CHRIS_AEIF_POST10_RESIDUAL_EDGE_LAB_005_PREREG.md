# GC SHORT CHRIS/AEIF POST10 RESIDUAL EDGE LAB005 — PREREG

Scope: frozen LAB003 Chris/AEIF SHORT event set only. No signal retuning. No XAU execution tuning.

## Question

Does the causal state observed at +10m after entry contain predictive information for **additional** bearish movement after the checkpoint, rather than merely describing price movement already realized by +10m?

## Frozen checkpoints / targets

Checkpoint: +10m from LAB003 entry.
Residual SHORT returns measured from the checkpoint close to:
- +15m (`resid_10_15_atr`)
- +20m (`resid_10_20_atr`)
- +30m (`resid_10_30_atr`)

All returns normalized by the frozen seed ATR14 used in LAB003.

## Frozen causal feature family at +10m

Use only the already identified LAB004 cp10 family:
- `cp10_ret`
- `cp10_cum_body`
- `cp10_bear_frac`
- `cp10_closepos`
- `cp10_mfe`
- `cp10_mae`
- `cp10_dist_seed_close`
- `cp10_dist_seed_high`

No new feature search and no threshold sweep.

## Analysis

For each feature and each residual target:
1. compute orientation-free AUC for positive residual return (`residual > 0`), with orientation chosen only by sign on Rithmic TRAIN;
2. evaluate the same orientation on Rithmic VALID, Rithmic FULL, AMP VALID, AMP FULL;
3. report Spearman correlation between feature and continuous residual return using that fixed orientation;
4. do not create a trading overlay in this lab.

## Evidence gate

A residual path feature family is considered historically promising only if at least one preregistered cp10 feature satisfies all of:
- Rithmic VALID AUC >= 0.65 on at least one residual horizon;
- AMP VALID AUC >= 0.65 on the same residual horizon;
- Rithmic FULL AUC >= 0.60;
- AMP FULL AUC >= 0.60;
- fixed TRAIN orientation is directionally consistent in both VALID feeds;
- minimum target-class count >= 3 winners and >= 3 losers in Rithmic VALID and AMP VALID.

If the gate passes, result is **not** a tradable rule. The next step must be a separately preregistered walk-forward decision-gate lab.

If it fails, the apparent LAB004 cp10 strength is treated as mostly path-description rather than forward residual predictiveness.
