# XAU_POST_TOUCH_SEQUENCE_EXECUTION_ECONOMICS_LAB_004 — v001 REPORT

**Verdict:** `NO_EXECUTABLE_EDGE`  
**Holdout opened:** `false`

## Canonical audit

- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- raw M1 rows: 1,454,538
- pre-holdout rows: 1,080,929
- canonical VWAP touch universe inherited from frozen LAB002 events
- combined candidate rows: 418,333
- directional signal rows: 316,694
- Bid/Ask simulated target rows: 633,388
- sealed holdout `>=2025-07-01`: untouched

## Primary result — T+3 / 1.5R / VWAP_VOLUME / serial portfolio

Confirmation:

- trades: **14,806**
- frequency: **189.9/week**
- EV: **-0.1802R/trade**
- PF: **0.731**
- net-positive rate: **34.72%**
- TP1.5R rate: **32.86%**
- total: **-2,668.5R**
- max DD: **2,672.4R**
- worst calendar day: **-44.07R**
- max consecutive losses: **16**
- BUY EV: **-0.1722R**
- SELL EV: **-0.1886R**
- +$0.10 round-trip price stress EV: **-0.2564R**

Discovery also fails: N **16,580**, EV **-0.1943R**, PF **0.715**.

Weekly cluster bootstrap in Confirmation: 79 weeks, mean **-0.1727R**, 95% CI **[-0.1959R, -0.1500R]**.

## Execution frontier

| Clock | Target | N | EV R | PF | TP rate |
|---|---:|---:|---:|---:|---:|
| T+1 | 1.5R | 13,848 | -0.1941 | 0.713 | 32.39% |
| T+3 | 1.5R | 14,806 | -0.1802 | 0.731 | 32.86% |
| T+5 | 1.5R | 14,829 | -0.1700 | 0.745 | 33.14% |
| T+3 | 2.0R | 13,884 | -0.1778 | 0.752 | 25.97% |

All frozen market-entry clocks fail.

## Yearly transfer

T+3 / 1.5R serial VWAP EV:
- 2022: **-0.2117R**
- 2023: **-0.1841R**
- 2024: **-0.1821R**
- 2025 H1: **-0.1762R**

No year is positive.

## Anchored-mean control

Confirmation T+3 / 1.5R serial anchored mean: N **13,825**, EV **-0.1798R**, PF **0.731**. This is nearly identical to VWAP and matches LAB003's generic-sequence conclusion.

## Why 79% state prediction did not become profitable

LAB003 predicted which **0.50 ATR barrier measured from the touched level** would be reached later. LAB004 waits until the causal decision clock and then asks price to travel another **0.75 ATR from the actual entry** before losing **0.50 ATR from entry**.

At Confirmation T+3 the median absolute signed displacement is already about **0.325 ATR** from the level. A material part of the response is therefore already consumed before entry.

The failure is not mainly transaction cost:
- gross EV before commission: **-0.1421R**
- mean commission cost: about **0.0381R**
- net EV: **-0.1802R**

Primary serial outcomes:
- SL: **63.94%**
- TP: **32.86%**
- time exit: **3.03%**
- same-bar conservative loss: **0.18%**
- median holding time: **7 minutes**

Both branches fail independently:
- BACK EV: **-0.1963R**
- THROUGH EV: **-0.1618R**

## Frozen gates

- G0_DATA_EXECUTION: PASS
- G1_CONFIRMATION_EV: **FAIL**
- G2_WEEK_CLUSTER_CI: **FAIL**
- G3_SPLIT_TRANSFER: **FAIL**
- G4_2R_SURVIVAL: **FAIL**
- G5_T1_EXECUTABLE: **FAIL**
- G6_DIRECTION_BREADTH: **FAIL**
- G7_PROP_DD_PROXY: **FAIL**
- G8_COST_STRESS: **FAIL**

## Interpretation

LAB002/003 discovered a real causal state variable, not a directly tradable market-entry rule.

> **Do not chase the confirmed response at market. The confirmation consumes too much of the available move.**

This is closer to the podcast's actual execution: directional confirmation is followed by a retrace / gap interaction / role-flip retest rather than an immediate market chase.

## Next required LAB

`XAU_POST_TOUCH_SEQUENCE_RETEST_ENTRY_CAUSAL_LAB_005`

Freeze the LAB002/003 directional state, do not enter at market, wait for the first causal retest toward the touched dynamic level / role-flip zone inside a frozen short window, then evaluate Bid/Ask execution with hard SL and minimum 1:1.5 R:R. Measure fill rate, missed winners, adverse selection, EV and serial prop-safe frequency.

No holdout opening and no live/EA allocation are authorized by LAB004.
