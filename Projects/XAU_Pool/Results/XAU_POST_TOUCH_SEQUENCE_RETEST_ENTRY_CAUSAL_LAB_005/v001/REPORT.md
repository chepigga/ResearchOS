# XAU_POST_TOUCH_SEQUENCE_RETEST_ENTRY_CAUSAL_LAB_005 — v001 REPORT

**Verdict:** `RETEST_IMPROVES_BUT_NOT_PROFITABLE`  
**Holdout opened:** `false`

## Canonical audit

- canonical SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- pre-holdout M1 rows: **1,080,929**
- inherited frozen LAB002 touch events: **71,561**
- Bid/Ask + AskOpen execution fields: present
- LAB002 event index/time lineage: valid
- sealed holdout `>=2025-07-01`: untouched

## Frozen primary lifecycle

`VWAP touch -> T+3 BACK/THROUGH signal -> no market chase -> wait <=15m for first role-flip retest -> retest bar closes >=0.03 ATR back on intended side -> enter next M1 open`

Execution was kept identical to LAB004 after entry:
- 1R = `0.50 * ATR_touch`
- TP = **1.5R** primary / **2.0R** secondary
- max hold = 60m
- spread embedded with canonical Bid/Ask
- commission proxy = $5 RT/lot = $0.05 price-equivalent
- one pending/active lifecycle at a time

## Primary result — Confirmation / T+3 / 1.5R / serial

- accepted lifecycles: **11,178**
- filled trades: **6,477**
- serial fill rate: **57.94%**
- frequency: **83.0 trades/week**
- median wait to retest confirmation: **4m**
- median wait to actual next-open entry: **5m**
- median entry improvement vs T+3 market chase: **+0.123 ATR**
- mean entry improvement: **+0.153 ATR**

Economics:
- EV: **-0.1708R/trade**
- PF: **0.743**
- gross EV before commission: **-0.1323R**
- TP1.5R rate: **32.98%**
- positive-rate: **35.14%**
- total: **-1,106.1R**
- max DD: **1,114.5R**
- worst calendar day: **-18.09R**
- max consecutive losses: **18**
- BUY EV: **-0.1805R**
- SELL EV: **-0.1604R**
- BACK EV: **-0.1886R**
- THROUGH EV: **-0.1491R**
- +$0.10 stress EV: **-0.2476R**

Weekly-cluster EV bootstrap:
- 78 weeks
- mean weekly-cluster EV: **-0.1629R**
- 95% CI: **[-0.1930R, -0.1331R]**

This is a clear economic failure, not a power issue.

## Discovery transfer

Discovery also fails:
- N: **7,300**
- EV: **-0.1867R**
- PF: **0.724**
- BUY EV: **-0.1784R**
- SELL EV: **-0.1951R**

Thus the sign is stable but negative in both pre-registered splits.

## 2R and T+1 frontier

No frozen alternative rescues the lifecycle:

- T+3 / 2R Confirmation: **-0.1601R**, PF **0.774**
- T+1 / 1.5R Confirmation: **-0.1797R**, PF **0.731**
- T+1 / 2R Confirmation: **-0.1666R**, PF **0.766**

Waiting for a retest is better than market chasing, but not enough to produce positive economics.

## Retest DOES improve entry quality

This is the strongest positive result in LAB005.

On the same serial filled Confirmation signals, paired retest entry versus the frozen T+3 market entry:

- mean weekly paired uplift: **+0.340R**
- 95% CI: **[+0.314R, +0.366R]**

`G10_RETEST_UPLIFT` therefore **passes strongly**.

For the actual primary serial trades:
- matched T+3 market-entry EV on these same filled signals: approximately **-0.508R**
- retest-entry EV: **-0.171R**
- raw paired improvement: approximately **+0.337R/trade**

So the retest is not useless. It rescues roughly one-third of an R relative to chasing the exact same adverse-selected signals.

## Why the retest still fails: adverse selection

The key mechanism is a trade-off between **entry price** and **signal quality**.

Confirmation all eligible T+3 signals:
- retest fill rate: **57.74%**
- filled signals' frozen LAB002 path-correctness: **71.64%**
- unfilled signals' path-correctness: **87.23%**
- adverse-selection gap: **-15.59 percentage points**

Discovery is almost identical:
- filled correctness: **70.87%**
- unfilled correctness: **87.17%**
- gap: **-16.30 pp**

The pattern also transfers across branches and direction:
- BACK filled 71.2% vs unfilled 88.1%
- THROUGH filled 72.2% vs unfilled 85.9%
- SELL filled 71.1% vs unfilled 86.6%
- BUY filled 72.2% vs unfilled 87.9%

Interpretation:

> **The strongest impulses often never retest. The trades that do return to the level are disproportionately the weaker / failing impulses.**

Thus waiting for the retest gives a better price but selects a lower-quality subset.

## A useful diagnostic, not a tradable filter

Using the future LAB002 label only for explanation (not for entry):
- filled signals that were eventually path-correct had EV about **+0.116R**
- filled signals that were path-wrong had EV about **-0.868R**

This cannot be used directly because `signal_correct` is only known later. It shows the next research problem precisely: identify **causally at the retest** which pullbacks are healthy and which are failed original impulses.

## Frozen gates

- G0_DATA_EXECUTION: PASS
- G1_FILL_POWER: PASS
- G2_CONFIRMATION_EV: **FAIL**
- G3_WEEK_CLUSTER_CI: **FAIL**
- G4_SPLIT_TRANSFER: **FAIL**
- G5_2R_SURVIVAL: **FAIL**
- G6_DIRECTION_BREADTH: **FAIL**
- G7_BRANCH_BREADTH: **FAIL**
- G8_PROP_DD_PROXY: **FAIL**
- G9_COST_STRESS: **FAIL**
- G10_RETEST_UPLIFT: **PASS**

## Interpretation

LAB005 rejects the simple execution thesis:

> confirmation -> any first level retest -> small close back on signal side -> entry

The retest itself is not sufficient confirmation. It improves location but creates adverse selection.

This is also where the podcast's **iFVG / renewed displacement** component becomes economically meaningful: the author does not merely buy/sell because price returned to the level; he waits for the retest to **respect a gap / invert / close back with renewed directional evidence**.

## Next required LAB

`XAU_POST_TOUCH_RETEST_REACCELERATION_IFVG_CAUSAL_LAB_006`

Freeze LAB005 signal and retest universe, then ask one narrow question:

**Can causal renewed displacement / iFVG formed at or immediately after the retest distinguish healthy pullbacks from the adverse-selected failed impulses?**

Do not change the 15m retest window, level zone, 0.50 ATR risk, 1.5R/2R target or costs. Add only the post-retest re-acceleration/iFVG confirmation dimension, and report both coverage loss and incremental EV.

No holdout opening and no EA/live allocation are authorized by LAB005.
