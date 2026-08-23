# XAU_POST_BREAK_ORDERED_STATE_PATH_AND_BIAS_LAB_009 — v001 REPORT

**Verdict:** `ORDERED_STORYLINE_ADDS_BIAS_INFORMATION`  
**Holdout opened:** `false`

## Primary T+15 bias result

- Confirmation N: **12,027**
- acceptance base rate: **47.10%**
- SNAPSHOT_STATE AUC: **0.8083**
- BAG_OF_STATES AUC: **0.8114**
- ORDERED_PATH AUC: **0.8250**
- ordered − snapshot: **+0.0167**; weekly CI **[+0.0133, +0.0202]**
- ordered − bag: **+0.0136**; weekly CI **[+0.0106, +0.0164]**
- snapshot / bag / ordered Brier: **0.1690 / 0.1753 / 0.1670**
- calibration Q5 − Q1 actual acceptance: **+72.61%**

## T+30 survival

- ORDERED_PATH AUC: **0.8709**

## Breadth

- BUY: N 5,920, ordered AUC **0.8220**
- SELL: N 6,107, ordered AUC **0.8278**
- HIGH: N 4,085, ordered AUC **0.8277**
- LOW: N 3,357, ordered AUC **0.8311**
- MID: N 4,585, ordered AUC **0.8169**
- 2024: N 8,285, ordered AUC **0.8183**
- 2025: N 3,742, ordered AUC **0.8398**

## Most frequent ordered paths in Confirmation

- `RECLAIM>RECLAIM>RECLAIM`: Discovery N 2,706, rate 10.6%; Confirmation N 2,384, rate 11.5%
- `EXPAND>HOLD>HOLD`: Discovery N 849, rate 73.9%; Confirmation N 724, rate 70.2%
- `EXPAND>EXPAND>HOLD`: Discovery N 637, rate 82.3%; Confirmation N 614, rate 78.0%
- `EXPAND>HOLD>EXPAND`: Discovery N 573, rate 85.5%; Confirmation N 550, rate 85.5%
- `HOLD>RECLAIM>RECLAIM`: Discovery N 543, rate 16.8%; Confirmation N 479, rate 18.6%
- `HOLD>EXPAND>HOLD`: Discovery N 552, rate 75.0%; Confirmation N 451, rate 76.7%
- `HOLD>HOLD>HOLD`: Discovery N 472, rate 65.7%; Confirmation N 398, rate 71.9%
- `EXPAND>EXPAND>EXPAND`: Discovery N 335, rate 92.5%; Confirmation N 363, rate 91.7%
- `TEST>RECLAIM>RECLAIM`: Discovery N 372, rate 17.5%; Confirmation N 326, rate 18.1%
- `HOLD>HOLD>EXPAND`: Discovery N 335, rate 80.0%; Confirmation N 322, rate 84.2%

## Frozen gates

- G0_DATA_CAUSALITY: PASS
- G1_POWER: PASS
- G2_BIAS_AUC: PASS
- G3_ORDER_BEATS_SNAPSHOT: PASS
- G4_ORDER_BEATS_BAG: PASS
- G5_BRIER_INCREMENTAL: PASS
- G6_CALIBRATION: PASS
- G7_DIRECTION_MIRROR: PASS
- G8_LEVEL_BREADTH: PASS
- G9_YEAR_TRANSFER: PASS
- G10_T30_SURVIVAL: PASS

## Why order matters — matched bags, different sequence

- `EXPAND → RECLAIM → RECLAIM`: Discovery 16.4%, Confirmation 13.4% acceptance; reordered `RECLAIM → RECLAIM → EXPAND`: Discovery 61.8%, Confirmation 65.4%.
- `HOLD → EXPAND → RECLAIM`: Discovery 30.8%, Confirmation 25.4%; reordered `RECLAIM → EXPAND → HOLD`: Discovery 57.5%, Confirmation 69.6%.
- `EXPAND → HOLD → HOLD`: Discovery 73.9%, Confirmation 70.2%; reordered `HOLD → HOLD → EXPAND`: Discovery 80.0%, Confirmation 84.2%.
- `EXPAND → EXPAND → HOLD`: Discovery 82.3%, Confirmation 78.0%; reordered `HOLD → EXPAND → EXPAND`: Discovery 84.4%, Confirmation 87.4%.

This is exactly the information lost by count-based or single-state summaries.

## Probability interpretation

Confirmation calibration is strong: ordered-path score quintiles move from 11.5% actual acceptance in Q1 to 84.1% in Q5. This is a bias probability, not an entry signal.

## Backoff coverage

At T+15 Confirmation, 81.89% of events use an exact 3-state path learned in Discovery, 15.95% use frozen last-two-state backoff, and only 2.16% fall back to the final snapshot state.

## Generic-level control

The same mechanism is not VWAP-specific. Anchored-mean control T+15 ORDERED AUC is 0.8268 versus VWAP 0.8250; T+30 is 0.8628 versus VWAP 0.8709. The edge is therefore best interpreted as a generic post-break acceptance storyline, with VWAP acting as one objective level generator rather than the causal source of the information.

## Interpretation

The chronological storyline adds transferable OOS bias information beyond both the current state and the unordered set of states.

No entry/economics or holdout opening is authorized.