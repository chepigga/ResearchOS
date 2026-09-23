# LAB050 — LIVE SIGNAL ACTUAL VS LAB ENTRY/EXIT COUNTERFACTUAL

Status: **DONE — SAME LIVE SIGNAL SET, BROKER ACTUAL VS FROZEN LAB MANAGEMENT**

Successful counterfactual workflow:
`35834250647`

Counterfactual output:
- `counterfactual_output/signal_counterfactual.csv`
- `counterfactual_output/summary.json`

## Experiment definition

Keep the live `CF191` signal IDs fixed.

For each unique signal+symbol pair, independently replay:
- confirmation move 0.30 ATR;
- freshness <=45m;
- max pre-confirm adverse <=0.75 ATR;
- v191d confirmation-Z consistency;
- SL1.5 ATR;
- BE0.5 / lock0.15;
- ExitZ0.75;
- H6;
- flat research cost 0.5bps.

Compare trail arms:
- control 2.5/0.5;
- balanced 3.5/0.5;
- aggressive 5.0/0.5.

Primary broker comparison uses frozen balanced `3.5/0.5`.

Important:
this is an **independent per-signal counterfactual**, not a stateful portfolio replay.
LAB046 toxic-state gating / occupancy is intentionally not re-applied because the question is:
"same live signal, what would happen with LAB entry/exit?"

Reference execution data for replay:
Binance futures 1m klines + ratio metrics.
Actual fills:
broker CFD MT5 reports.

Therefore R is the primary comparison unit.
Hypothetical USD figures are normalized estimates using each actual broker trade's initial risk USD, not broker-tick-exact reconstructed PnL.

## Unique live signal universe

75 unique CF191 signal+symbol pairs.

LAB confirmation layer:
- ENTER 69
- SKIP 6
  - SKIP_CONFIRM_Z 3
  - SKIP_NO_CONFIRM 2
  - SKIP_ADVERSE 1

Independent replay:
- 2.5/0.5: **+10.324R**, EV +0.150R
- 3.5/0.5: **+14.680R**, EV +0.213R
- 5.0/0.5: **+18.267R**, EV +0.265R

The small fresh sample therefore preserves the LAB048 ordering:
5.0 > 3.5 > 2.5 on headline SumR.
This is observational confirmation only, not a new promotion test.

## GetLeveraged

Live signals:
- 58
- 56 closed
- 2 still open
- 5 signals would be skipped by the LAB entry shell

Same **closed** signal rows:

Actual broker:
- SumR **-1.960R**
- realized net PnL **+$417.35**

LAB balanced 3.5 counterfactual:
- SumR **+13.697R**
- normalized estimated PnL at the same initial-risk dollars: **+$2,914.29**

Delta:
- **+15.656R**
- normalized PnL delta **+$2,496.94**

Entry timing:
- actual median signal->entry: **5.0 min**
- LAB median: **3.0 min**
- actual entry is median **2.0 min later**

Hold:
- actual median: **33.1 min**
- LAB median: **31.0 min**

Exit structure:
Actual:
- PROTECTED_STOP 33
- SL 13
- EXIT_Z_INFERRED 10
- OPEN 2

LAB 3.5:
- PROTECTED_STOP 41
- SL 6
- EXIT_Z 5
- TIME 1
- SKIP 5

Largest lost opportunities versus LAB include:
- `CF191B1789977900 SOL`: actual +0.075R vs LAB +2.939R
- `CF191B1789941900 BTC`: actual +0.103R vs LAB +2.066R
- `CF191B1789925700 ETH`: actual -1.199R vs LAB +0.094R
- `CF191B1789772100 SOL`: actual -1.027R vs LAB +0.094R
- `CF191S1789833600 SOL`: actual -1.017R vs LAB +0.091R
- `CF191S1790067600 BTC`: actual -1.007R vs LAB +0.089R

Interpretation:
GetLeveraged execution cost is relatively clean from the prior audit, yet actual outcome is far below the LAB counterfactual.
Therefore execution cost alone does not explain the divergence.
Entry timing / management parity is a major issue.

## IC Markets

Live signals:
- 20
- 19 closed
- 1 open
- 1 signal would be skipped by the LAB entry shell

Same **closed** signal rows:

Actual broker:
- SumR **-10.451R**
- realized PnL **-$943.10**

LAB balanced 3.5 counterfactual:
- SumR **-0.123R**
- normalized estimated PnL at same initial-risk dollars: **+$92.13**

Delta:
- **+10.328R**
- normalized PnL delta **+$1,035.23**

Entry timing:
- actual median signal->entry: **~5.0 min**
- LAB median: **2.0 min**
- actual entry is median **3.0 min later**

Hold:
- actual median: **45.8 min**
- LAB median: **33.0 min**

Exit structure:
Actual:
- SL 11
- PROTECTED_STOP 5
- EXIT_Z_INFERRED 3
- OPEN 1

LAB 3.5:
- PROTECTED_STOP 13
- SL 4
- EXIT_Z 2
- SKIP 1

Largest divergences:
- `CF191B1790013600 BTC`: actual +0.111R vs LAB +1.829R
- `CF191S1790076300 BTC`: actual -1.085R vs LAB +0.091R
- `CF191B1790040000 SOL`: actual -1.029R vs LAB +0.094R
- `CF191S1790054100 ETH`: actual -1.010R vs LAB +0.091R
- `CF191S1790028300 SOL`: actual -1.007R vs LAB +0.094R
- `CF191S1790061300 ETH`: actual -1.010R vs LAB +0.089R
- `CF191B1790091600 ETH`: actual -1.003R vs LAB +0.093R
- `CF191S1790093100 SOL`: actual -1.001R vs LAB +0.094R

IC also has the worse execution-cost tail from the first LAB050 audit, so its divergence combines:
1. live-vs-LAB timing/management mismatch;
2. heavier broker slippage tail.

## Six live trades that LAB entry rules would skip

Actual combined result:
**-2.618R**

- GetLeveraged `CF191S1789788600 BTC`: SKIP_NO_CONFIRM; actual +0.096R
- GetLeveraged `CF191S1789814100 BTC`: SKIP_ADVERSE; actual -0.265R
- GetLeveraged `CF191B1789832400 BTC`: SKIP_CONFIRM_Z; actual -0.779R
- GetLeveraged `CF191B1789842900 BTC`: SKIP_NO_CONFIRM; actual -1.315R
- GetLeveraged `CF191B1789874100 SOL`: SKIP_CONFIRM_Z; actual -0.135R
- IC `CF191B1790021700 ETH`: SKIP_CONFIRM_Z; actual -0.220R

Thus restoring LAB confirmation parity alone would have removed five losing trades and one small winner in this sample.

## Core conclusion

The main V191 live problem is now more specific than "broker cost".

**The live EA is not reproducing the entry/management geometry that produced the LAB edge.**

Observed differences:
- live generally enters at ~5 minutes after signal;
- LAB confirmation enters at ~2–3 minutes median on these same signals;
- live generates materially more full SL exits;
- LAB converts many of those same signals to protected small wins;
- LAB confirmation shell would also reject six live trades with net actual result -2.62R.

GetLeveraged shows this even though its measured execution cost is comparatively low.
Therefore broker slippage is not sufficient to explain the GetLeveraged underperformance.

IC has BOTH:
- parity mismatch;
- worse execution/slippage tail.

## Next engineering target

Before more parameter research:
**V191 LIVE/LAB EXECUTION PARITY**

Audit / fix the EA so that for a recorded signal ID it reproduces:
- exact confirmation clock and price rule;
- <=45m freshness;
- max adverse <=0.75 ATR;
- confirmation-Z consistency;
- entry timing;
- frozen SL1.5;
- BE0.5/0.15;
- ExitZ0.75;
- trail3.5/0.5 candidate;
- H6.

Then run the same signal-by-signal parity table again.

Do not retune signal thresholds until live and replay agree mechanically.
