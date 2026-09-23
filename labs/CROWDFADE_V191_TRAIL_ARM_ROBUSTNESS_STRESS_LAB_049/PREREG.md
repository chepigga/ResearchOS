# LAB049 — V191_TRAIL_ARM_ROBUSTNESS_STRESS

Status: PRE-REGISTERED BEFORE EXECUTION

## Frozen strategy family

Exactly three trail configurations from LAB048:

1. CONTROL_A2P5_G0P5
   - trail arm = 2.5 ATR
   - trail gap = 0.5 ATR

2. BALANCED_A3P5_G0P5
   - trail arm = 3.5 ATR
   - trail gap = 0.5 ATR

3. AGGRESSIVE_A5P0_G0P5
   - trail arm = 5.0 ATR
   - trail gap = 0.5 ATR

No additional arm/gap values are allowed in LAB049.

Everything else is frozen:
- BTCUSDT
- v191 contrarian crowd signal |Z| >= 1.00
- confirmation move = 0.30 ATR against crowd
- confirmation freshness <=45m
- v191d confirmation-side consistency
- cancel if max pre-confirm adverse >0.75 ATR
- skip RAPID_REPEAT<=30m
- skip causal HIGH_VOL
- pause =1 ATR
- max trades/day =3
- SL1.5 ATR
- fixed TP OFF
- BE arm0.5 / lock0.15 ATR
- ExitZ0.75
- max hold6h

## Causal execution stress scenarios

The grid is fixed before execution.

S0_BASE:
- cost = 0.5 bps
- entry delay = 0 sec

S1_COST_1BPS:
- cost = 1.0 bps
- entry delay = 0 sec

S2_COST_2BPS:
- cost = 2.0 bps
- entry delay = 0 sec

S3_DELAY_60S:
- cost = 0.5 bps
- entry delay = 60 sec

S4_DELAY_180S:
- cost = 0.5 bps
- entry delay = 180 sec

S5_ADVERSE_COMBINED:
- cost = 2.0 bps
- entry delay = 180 sec

No other cost or delay values may be added after results are observed.

## Entry-delay mechanics

Signal detection and confirmation are frozen and occur at the original confirmation timestamp.

For delayed scenarios only:
- execution occurs at the first raw execution-frame bar with timestamp >= original confirmation timestamp + delay;
- entry price is that bar's close;
- the same frozen ATR from the original signal is used for SL/BE/trailing distances;
- SL/BE/trail/ExitZ/H6 timing starts from the delayed execution timestamp;
- H6 is measured from delayed entry;
- no signal re-validation or new threshold check is introduced during the delay;
- if no execution bar exists before sample end, the trade is skipped.

Delayed execution therefore changes occupancy and downstream reachability and MUST be replayed statefully.

## Cost mechanics

The existing research cost term is preserved exactly, but COST_BPS is replaced by the scenario value:
R_net = price_move_R - (cost_bps / 10000) * entry / initial_risk_price

No new commission model is introduced.

## Samples

Historical:
- 2021-01-01 through 2025-12-31
- BTCUSDT 1m OHLC frame

Forward shadow/stress:
- 2026-03-01 through 2026-08-31
- BTCUSDT second OHLC frame

2026 remains reused shadow/stress, not pristine OOS.

## Immutable reference

V192_CANONICAL_CONTROL is replayed unchanged only under S0_BASE as a quality reference.
LAB049 is not a V192 retuning exercise.

## Required metrics for every arm x causal stress

- N
- WR
- EV
- PF
- SumR
- MaxDD_R
- R/DD
- max consecutive losses
- median and p90 hold
- exit reasons
- annual 2021-2025 metrics
- monthly 2026 metrics
- full chronological ledger
- stateful reachability delta vs same-stress CONTROL_A2P5_G0P5

## Right-tail clipping diagnostics

These are diagnostics only and do NOT alter occupancy or exits.

For every arm under:
- S0_BASE
- S5_ADVERSE_COMBINED

report:
- original SumR
- SumR with positive trade R capped at +5R
- SumR with positive trade R capped at +3R
- EV/PF under +5R cap
- EV/PF under +3R cap
- positive historical years / forward months under each cap
- top1/top5 gross-positive concentration
- SumR excluding top1 and top5 winners

The clipping operation is:
R_clipped = min(R, cap_R) for R>0; losses unchanged.

## Pre-registered verdicts

### STRESS_SURVIVOR

A configuration is STRESS_SURVIVOR only if:
1. EV>0 and PF>1 in BOTH historical and 2026 for ALL six causal stress scenarios;
2. under S5_ADVERSE_COMBINED:
   - >=3/5 historical years positive;
   - >=3/6 forward months positive;
3. trade count under S5 remains >=90% of that configuration's S0 trade count in BOTH samples;
4. MaxDD under S5 is <=2.0x that configuration's S0 MaxDD in BOTH samples.

### TAIL_ROBUST

TAIL_ROBUST requires STRESS_SURVIVOR plus:
- under S0, +3R clipping leaves aggregate SumR>0 in both samples;
- under S5, +3R clipping leaves aggregate SumR>0 in both samples;
- under S5, SumR excluding top5 winners remains >0 in both samples.

### STRESS_DOMINANT_VS_CONTROL

A candidate (3.5 or 5.0) is STRESS_DOMINANT_VS_CONTROL only if it is TAIL_ROBUST and:
- under S5 it has higher SumR than CONTROL in BOTH historical and forward;
- under S5 it has higher R/DD than CONTROL in BOTH historical and forward.

No candidate may be selected by headline EV alone.

## Interpretation guardrail

LAB049 is a robustness screen, not another parameter search.

If BALANCED 3.5/0.5 and/or AGGRESSIVE 5.0/0.5 satisfy TAIL_ROBUST and STRESS_DOMINANT_VS_CONTROL, the next step is side-by-side demo/shadow validation with the frozen configuration(s), not interpolation to new arm values.

If a candidate fails, do not retune inside LAB049.
