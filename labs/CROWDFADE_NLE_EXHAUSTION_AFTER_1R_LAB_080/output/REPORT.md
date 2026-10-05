# LAB080 — NLE EXHAUSTION STATE AFTER +1R

{
  "lab": "LAB080_NLE_EXHAUSTION_AFTER_1R",
  "preregistered_states": {
    "EXH_CORE": "at least 2 of {post1R OI15 >= TRAIN Q75, post1R Price15 >= TRAIN Q75, post1R Taker5 >= TRAIN Q75}",
    "EXH_REGIME": "EXH_CORE and (entry ATR > TRAIN Q25 or entry eff30 < TRAIN median)",
    "EXH_STRICT": "EXH_CORE and entry ATR > TRAIN Q25 and entry eff30 < TRAIN median"
  },
  "train_thresholds": {
    "oi15_q75": 0.004194424464552204,
    "px15_q75": 0.0074990324458864,
    "taker5_q75": 0.3173923186811107,
    "atr_q25": 0.0021350508646708973,
    "eff30_med": 0.3781869987336376
  },
  "management_grid": "If exhaustion state is active at +1R, tighten floor to +0.5R/+0.75R/+1.0R; otherwise preserve current runner. Candidate selection uses historical only.",
  "historical_selected_candidate": "EXH_STRICT_LOCK_1R",
  "historical_base_EV": 0.1994489331435472,
  "historical_selected_EV": 0.20158939816449625,
  "forward_2026_base_EV": -0.13284788956561888,
  "forward_2026_selected_EV": -0.1057248520832334,
  "forward_2026_selected_PF": 0.8401365839775811,
  "forward_2026_selected_MaxDD_R": 13.296876314901493,
  "note": "Diagnostic management LAB only; no production change unless TRAIN-selected rule transfers to 2026 without DD deterioration."
}

## State quality

| period       | state      |   N_reached1R |   N_exhaustion |   exhaustion_rate |   current_EV_exhaustion |   giveback_exhaustion |   current_EV_normal |   giveback_normal |
|:-------------|:-----------|--------------:|---------------:|------------------:|------------------------:|----------------------:|--------------------:|------------------:|
| forward_2026 | EXH_CORE   |            51 |              5 |         0.0980392 |               -0.383268 |              0.8      |            0.293085 |          0.565217 |
| forward_2026 | EXH_REGIME |            51 |              5 |         0.0980392 |               -0.383268 |              0.8      |            0.293085 |          0.565217 |
| forward_2026 | EXH_STRICT |            51 |              1 |         0.0196078 |               -1.0071   |              1        |            0.251454 |          0.58     |
| historical   | EXH_CORE   |           654 |            114 |         0.174312  |                1.06114  |              0.350877 |            0.673884 |          0.481481 |
| historical   | EXH_REGIME |           654 |            106 |         0.16208   |                1.06513  |              0.349057 |            0.678766 |          0.479927 |
| historical   | EXH_STRICT |           654 |             39 |         0.059633  |                0.840589 |              0.461538 |            0.735096 |          0.458537 |

## Sequential equity metrics

| period       | strategy              |   N |       EV_R |       WR |       PF |      SumR |   MaxDD_R |
|:-------------|:----------------------|----:|-----------:|---------:|---------:|----------:|----------:|
| historical   | CURRENT               | 972 |  0.199449  | 0.403292 | 1.34783  | 193.864   |   18.4549 |
| forward_2026 | CURRENT               |  74 | -0.132848  | 0.324324 | 0.803175 |  -9.83074 |   13.2969 |
| historical   | EXH_CORE_LOCK_0.5R    | 972 |  0.191801  | 0.427984 | 1.34808  | 186.431   |   19.4467 |
| forward_2026 | EXH_CORE_LOCK_0.5R    |  74 | -0.09352   | 0.351351 | 0.855622 |  -6.92048 |   13.2969 |
| historical   | EXH_CORE_LOCK_0.75R   | 972 |  0.191823  | 0.427984 | 1.34812  | 186.452   |   19.1967 |
| forward_2026 | EXH_CORE_LOCK_0.75R   |  74 | -0.0800065 | 0.351351 | 0.876485 |  -5.92048 |   13.2969 |
| historical   | EXH_CORE_LOCK_1R      | 972 |  0.193872  | 0.427984 | 1.35184  | 188.444   |   18.9467 |
| forward_2026 | EXH_CORE_LOCK_1R      |  74 | -0.0664929 | 0.351351 | 0.897347 |  -4.92048 |   13.2969 |
| historical   | EXH_REGIME_LOCK_0.5R  | 972 |  0.191221  | 0.426955 | 1.34635  | 185.867   |   19.4467 |
| forward_2026 | EXH_REGIME_LOCK_0.5R  |  74 | -0.09352   | 0.351351 | 0.855622 |  -6.92048 |   13.2969 |
| historical   | EXH_REGIME_LOCK_0.75R | 972 |  0.196116  | 0.426955 | 1.35522  | 190.625   |   19.1967 |
| forward_2026 | EXH_REGIME_LOCK_0.75R |  74 | -0.0800065 | 0.351351 | 0.876485 |  -5.92048 |   13.2969 |
| historical   | EXH_REGIME_LOCK_1R    | 972 |  0.198092  | 0.426955 | 1.3588   | 192.546   |   18.9467 |
| forward_2026 | EXH_REGIME_LOCK_1R    |  74 | -0.0664929 | 0.351351 | 0.897347 |  -4.92048 |   13.2969 |
| historical   | EXH_STRICT_LOCK_0.5R  | 972 |  0.198238  | 0.412551 | 1.3508   | 192.687   |   18.4549 |
| forward_2026 | EXH_STRICT_LOCK_0.5R  |  74 | -0.112482  | 0.337838 | 0.82992  |  -8.32364 |   13.2969 |
| historical   | EXH_STRICT_LOCK_0.75R | 972 |  0.19968   | 0.412551 | 1.35336  | 194.089   |   18.4549 |
| forward_2026 | EXH_STRICT_LOCK_0.75R |  74 | -0.109103  | 0.337838 | 0.835028 |  -8.07364 |   13.2969 |
| historical   | EXH_STRICT_LOCK_1R    | 972 |  0.201589  | 0.412551 | 1.35674  | 195.945   |   18.4549 |
| forward_2026 | EXH_STRICT_LOCK_1R    |  74 | -0.105725  | 0.337838 | 0.840137 |  -7.82364 |   13.2969 |