# SELL_CORE_001 — FUNDING Q4 × MARKET-CLOCK DECOMPOSITION

## Verdict

**FAIL as a standalone SELL market-clock gate.**

Frozen recent window: BTC 2024-01-01 through 2026-08-08, Binance perpetual funding context computed on the full unfiltered history before market-clock conditioning.

Funding construction:
- trailing 3-day mean (9 x 8h observations);
- causal percentile versus previous 2,000 funding observations;
- primary Q4 = inclusive ECDF >= 0.75;
- midrank ECDF fixed sensitivity;
- no FVG conditioning, no outcome-driven tuning.

Common SELL replay:
- funding timestamp (00/08/16 UTC) as H4-aligned signal clock;
- next M1 open;
- SL = 1.5 x completed H1 ATR14;
- no TP;
- 48h time exit;
- $27.5/BTC cost proxy.

Primary unit = first Q4/non-Q4 observation inside each continuous canonical H4 market-clock episode. CI by cluster bootstrap on market-clock episodes.

## Primary inclusive-ECDF results

| Cell | Q4 N | Q4 EV_R | Q4 PF | Q4 EV_pct | non-Q4 EV_R | Delta Q4 - nonQ4 | P(Delta>0) |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | 84 | -0.176 | 0.778 | -0.335% | -0.049 | -0.126R | 31.2% |
| B1 | 29 | +0.107 | 1.140 | -0.045% | -0.309 | +0.416R | 76.1% |
| B2 | 27 | -0.201 | 0.757 | -0.498% | +0.152 | -0.353R | 24.0% |
| **B3** | **19** | **-0.463** | **0.442** | **-0.574%** | **+0.343** | **-0.807R** | **2.5%** |
| B4 | 9 | -0.407 | 0.417 | -0.276% | -0.780 | +0.373R | 85.9% |
| SELL_B3 age 27-50 | 19 | -0.463 | 0.442 | -0.574% | +0.343 | -0.807R | 2.6% |

B3 Delta R cluster-bootstrap CI: approximately **[-1.643, -0.00006]** for generic B3. Price-space delta is -0.867 percentage points with P(delta>0) about 3.4%.

Midrank sensitivity remains negative:
- ALL Q4 EV -0.470R, delta -0.507R;
- B2 Q4 EV -0.768R, delta -1.026R;
- B3 Q4 EV -0.258R, delta -0.562R;
- B4 Q4 EV -0.326R, delta +0.287R but Q4 itself remains negative.

## Year stability

Q4 is not stable as a profitable SELL context in any bucket:
- ALL: positive 1/3 years;
- B1: 1/3;
- B2: 0/3;
- B3: 1/3;
- B4: no usable 2026 Q4 sample.

B3 Q4 by year:
- 2024 N13: -0.774R, -0.986%;
- 2025 N3: -1.028R, -1.489%;
- 2026 N3: +1.449R, +2.129%.

This is a regime migration, not a stable Q4 SELL rule.

## Important secondary clue

Inside B3, the **SELL-aligned** non-Q4 subgroup is strong in aggregate (N35, EV +1.141R, PF 2.65, +1.003% price), while B3 aligned Q4 is negative (N11, EV -0.604R, PF 0.305). However the non-Q4 aligned subgroup is not stable 3/3 (2024 slightly negative; strength is concentrated in 2025-26), so it is a clue, not a frozen rule.

## Interpretation

The old broad funding Q4 result (+1.17% SELL, 8/8 in the earlier oracle/context study) asked a different question: funding as a slow contextual variable on a broad signal population / excess-over-drift framework. SELL_CORE_001 tests whether Q4 can itself define a causal SELL entry/state when mapped to the canonical H4 market clock and replayed with the common SL/no-TP/48h outcome.

It cannot. In particular, imposing Q4 on B3 destroys the positive non-Q4 B3 subset. Therefore funding should remain a slow contextual feature/diagnostic, not be promoted to a hard SELL gate in the current BTC core.
