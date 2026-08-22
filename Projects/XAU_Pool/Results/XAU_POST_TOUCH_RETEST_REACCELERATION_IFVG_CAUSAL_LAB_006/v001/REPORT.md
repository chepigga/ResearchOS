# XAU_POST_TOUCH_RETEST_REACCELERATION_IFVG_CAUSAL_LAB_006 — v001 REPORT

**Verdict:** `HEALTH_FILTER_IMPROVES_BUT_NOT_PROFITABLE`  
**Holdout opened:** `false`

## Audit

- canonical SHA: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- pre-holdout rows: 1,080,929
- LAB005 parent candidate rows: 53,707
- causal confirmed iFVG events: 188,859

## Primary Confirmation — BOTH / T+3 / 1.5R / serial

- N: **2,098**
- trades/week: **26.94**
- EV: **-0.1954R**
- PF: **0.712**
- TP rate: **32.13%**
- gross EV: **-0.1566R**
- max DD: **414.84R**
- worst day: **-11.46R**
- BUY EV: **-0.2183R**
- SELL EV: **-0.1704R**
- BACK EV: **-0.1941R**
- THROUGH EV: **-0.1968R**
- +$0.10 stress EV: **-0.2729R**

Weekly CI: **[-0.2572, -0.1487]R**.

## Health selection

Confirmation: parent retests **14,577**, BOTH pass **4,356 (29.88%)**; correctness pass **84.57%** vs fail **66.13%**, uplift **+18.44 pp**.

Discovery: parent retests **16,642**, BOTH pass **4,952 (29.76%)**; correctness pass **83.28%** vs fail **65.61%**, uplift **+17.67 pp**.

The week-cluster bootstrap confirms that the selection uplift is real:
- Confirmation CI for correctness uplift: **[+14.55, +19.74] pp**
- Discovery CI: **[+16.55, +19.41] pp**

## Ablation — independent Confirmation 1.5R

- PRIMARY_BOTH: N 4,356; EV **-0.1831R**; PF **0.729**; correctness **84.57%**
- REACCEL_ONLY: N 8,514; EV **-0.1654R**; PF **0.752**; correctness **84.59%**
- IFVG_ONLY: N 6,570; EV **-0.1894R**; PF **0.720**; correctness **76.35%**

The aligned iFVG condition does not add measurable value over re-acceleration alone in this causal formulation.

## Frozen gates

- G0_DATA_EXECUTION: PASS
- G1_PRIMARY_POWER: PASS
- G2_CONFIRMATION_EV: FAIL
- G3_WEEK_CLUSTER_CI: FAIL
- G4_SPLIT_TRANSFER: FAIL
- G5_2R_SURVIVAL: FAIL
- G6_DIRECTION_BREADTH: FAIL
- G7_BRANCH_BREADTH: FAIL
- G8_PROP_DD_PROXY: FAIL
- G9_COST_STRESS: FAIL
- G10_HEALTH_SELECTION: PASS
- G11_IFVG_INCREMENTAL: FAIL

## Timing counterfactual — diagnostic only, NOT tradable

The strongest finding is that selection and entry timing separate sharply. On Confirmation PRIMARY_BOTH signals:

- future-health-selected LAB005 retest entry EV (non-causal diagnostic): **+0.1893R**
- actual LAB006 post-reacceleration entry EV: **-0.1831R** independent / **-0.1954R** serial
- median entry deterioration versus LAB005 retest entry: **0.205 ATR**, about **0.41R** with the frozen 0.50 ATR stop
- paired weekly LAB006 minus LAB005 retest: **-0.368R**, 95% CI **[-0.412, -0.327]**

This does NOT authorize entering earlier using future information. It shows that future re-acceleration is a strong *label* for retest quality, but a poor *entry trigger* because the confirmation consumes the remaining reward.

Among selected Confirmation signals, if the frozen LAB002 directional path is correct, the old retest entry has about **+0.326R** EV; if wrong, about **-0.562R**. After waiting for re-acceleration those become roughly **-0.078R** and **-0.759R** respectively. The waiting step destroys the economics even for many correctly selected paths.

## iFVG incremental verdict

The aligned iFVG condition does not add measurable value over re-acceleration alone:

- Confirmation correctness: PRIMARY_BOTH **84.57%** vs REACCEL_ONLY **84.59%**
- Confirmation independent EV: PRIMARY_BOTH **-0.183R** vs REACCEL_ONLY **-0.165R**
- IFVG_ONLY correctness: **76.35%**, EV **-0.189R**

So `G11_IFVG_INCREMENTAL` fails. The podcast-style iFVG remains plausible as an *entry model at the retest itself*, but waiting for a later confirmed iFVG/re-acceleration does not help.

## Yearly transfer

Primary serial 1.5R EV:
- 2022: **-0.142R**
- 2023: **-0.249R**
- 2024: **-0.185R**
- 2025 H1: **-0.220R**

No year is positive.

## Interpretation

LAB006 found a strong causal health label but not a tradable delayed trigger.

> Future re-acceleration can identify which retests were healthy, but by the time that fact is confirmed the favorable entry location is gone.

The next problem is therefore not “wait for more confirmation.” It is to predict the future-health state using only information already available at the LAB005 retest close, then preserve the next-M1-open retest entry.

## Next required LAB

`XAU_RETEST_BAR_EARLY_HEALTH_PROXY_AND_IFVG_ENTRY_LAB_007`

Freeze the LAB005 retest-entry timing and ask whether information already known **on the retest confirmation bar** can predict the future-health label without waiting for it. Candidate causal features must be frozen before replay: retest-bar body/close location, rejection wick geometry, one-minute displacement, and only iFVG evidence already confirmed by the retest close. Entry remains next-M1-open, preserving the favorable LAB005 location. No future re-acceleration field may be used as an entry feature.

No holdout opening or live/EA allocation is authorized.
