# FT_REJECTED_001 — Partial Pipeline Diagnostic

**Date:** 2026-07-25  
**Status:** BLOCKED / PARTIAL DIAGNOSTIC ONLY  
**Frozen primary verdict:** NOT OPENED

## 1. Data/provenance audit

- `AK47_ea_dryrun_signals.csv` SHA256: `a62a93a471cff3ce000bb237556125a9f54101c0b0ee33c5b0bca4605b0db7f2`
- `AK47_ea_debug_log.csv` SHA256: `f259dc513f4af46bdbff5d40b45101cd574e1587d2500e8beb50c736fe14a82e`
- M5 SHA256: `1ba5f86a8d9f191e97e357875d6496e454630d95b5bf86e3052c2327b4a83f73`
- M5 actual coverage: `2025-02-13 14:15:00 .. 2026-07-23 23:45:00`
- M5 rows: `100971`
- Replayable candidates in available M5 window: `545`
- Missing candidate timestamps inside that window: `0`
- Excluded `DAILY_STOP`: `3`

The required 2023–2026 formal test cannot be executed because the available M5 file begins on 2025-02-13. Therefore `CONFIRMS-REGIME` versus `GATE-ARTIFACT` remains unresolved.

## 2. Engine validation against tester lifecycle

- ACCEPT oracle candidates in available window: `78`
- Matched to executed lifecycle rows: `65`
- Correlation between hypothetical `R_raw` and tester `result_R`: `0.9539`
- Mean absolute difference: `0.4415R`
- Median absolute difference: `0.2970R`

This validates the replay mechanics for a diagnostic run. Simulated rejected trades use the frozen `−0.05R` cost convention rather than tester fills.

## 3. ACCEPT vs REJECT — available 2025-02..2026-07 window

| Population | Module | N | WR | EV_net | Sum R | PF |
|---|---|---:|---:|---:|---:|---:|
| ACCEPT | ALL | 78 | 51.28% | +1.8183R | +141.827R | 4.814 |
| ACCEPT | LONBUY | 17 | 47.06% | +0.8163R | +13.877R | 3.062 |
| ACCEPT | NYBUY | 61 | 52.46% | +2.0975R | +127.950R | 5.202 |
| REJECT | ALL | 467 | 24.84% | +0.1606R | +75.022R | 1.209 |
| REJECT | LONBUY | 121 | 38.02% | +0.1514R | +18.322R | 1.268 |
| REJECT | NYBUY | 346 | 20.23% | +0.1639R | +56.700R | 1.196 |

## 4. Reject reasons — available window

| Reason | N | WR | EV_net | Sum R | PF |
|---|---:|---:|---:|---:|---:|
| SLATR_OUT_OF_RANGE | 4 | 75.00% | +3.4500R | +13.800R | 14.143 |
| ACCEPT | 78 | 51.28% | +1.8183R | +141.827R | 4.814 |
| SWEEP_TOO_SHALLOW | 15 | 26.67% | +0.5500R | +8.250R | 1.714 |
| SCORE_BLOCK | 190 | 24.21% | +0.2808R | +53.350R | 1.354 |
| FAR_FROM_SWING_HIGH | 136 | 25.74% | +0.1633R | +22.203R | 1.223 |
| LON_H1_NOT_BULL | 14 | 42.86% | -0.0807R | -1.130R | 0.850 |
| SL_TOO_TIGHT_USD | 101 | 18.81% | -0.1801R | -18.188R | 0.784 |
| LON_RECLAIM_CP | 6 | 50.00% | -0.3688R | -2.213R | 0.148 |
| LON_SWEEP_DEPTH | 1 | 0.00% | -1.0500R | -1.050R | 0.000 |

## 5. Year split — partial only

| Population | Year | N | EV_net | Sum R | PF |
|---|---:|---:|---:|---:|---:|
| ACCEPT | 2025 | 49 | +1.7470R | +85.603R | 4.638 |
| ACCEPT | 2026 | 29 | +1.9387R | +56.223R | 5.119 |
| REJECT | 2025 | 352 | +0.1523R | +53.614R | 1.199 |
| REJECT | 2026 | 115 | +0.1862R | +21.408R | 1.242 |

## 6. SCORE_BLOCK qScore buckets — partial only

| qScore bucket | N | WR | EV_net | Sum R | PF |
|---|---:|---:|---:|---:|---:|
| <=69 | 15 | 13.33% | -0.5675R | -8.512R | 0.376 |
| 70-79 | 23 | 34.78% | +1.0370R | +23.850R | 2.514 |
| 80-92 | 75 | 22.67% | +0.1294R | +9.702R | 1.161 |
| 93-99 | 71 | 23.94% | +0.3184R | +22.610R | 1.399 |
| >=100 | 6 | 33.33% | +0.9500R | +5.700R | 2.357 |

## 7. SL_TOO_TIGHT_USD by year — partial only

| Year | N | WR | EV_net | Sum R | PF |
|---|---:|---:|---:|---:|---:|
| 2025 | 95 | 17.89% | -0.2549R | -24.217R | 0.698 |
| 2026 | 6 | 33.33% | +1.0049R | +6.030R | 2.558 |

## 8. Partial findings — not frozen conclusions

- REJECT aggregate: `N=467`, EV `+0.1606R`, PF `1.21`.
- ACCEPT aggregate: `N=78`, EV `+1.8183R`, PF `4.81`.
- The gates strongly improve average EV in this late regime, even though the rejected population remains mildly positive.
- `SL_TOO_TIGHT_USD` is negative in the available aggregate (`EV −0.1801R`, N=101), so this filter behaves as intended on the partial window.
- Partial `GATE_LOOSEN_CANDIDATE` flags appear for `SCORE_BLOCK` and `FAR_FROM_SWING_HIGH`, but they are non-actionable because 2023–2024 is missing.

## 9. Frozen status

- Primary verdict: **BLOCKED_PARTIAL_DATA**.
- No gate is changed.
- No risk is increased.
- No 2025–2026 finding is promoted to OOS evidence.
- Formal execution resumes only after receiving `XAUUSD_M5_20220601_20260723_TESTER_FULL.csv` from the Strategy Tester streaming exporter.
