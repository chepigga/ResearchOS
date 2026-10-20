# CROWDFADE_ENGINE_A_ABLATION_LAB_004 — does the crowd condition add to Engine A?

Frozen thresholds (TRAIN): EXT80 = 1.53 H1 ATR, OI70 = +0.867%. Cost 2.81 bps. Execution = LAB122 (SWING3 → next M5 open, SL 1 H1 ATR, TP 3R, 48h, one position). TRAIN < 2025-01-01 ≤ OOS. Data 2021-01-01 → 2026-08-10.

| variant | split | N | EV R [95% CI] | PF | win% |
|---|---|---|---|---|---|
| FULL (Engine A) | ALL | 143 | +0.350 [+0.058…+0.659] | 1.53 | 35.7 |
| FULL (Engine A) | TRAIN | 124 | +0.348 [+0.024…+0.686] | 1.52 | 35.5 |
| FULL (Engine A) | OOS | 19 | +0.361 [-0.391…+1.205] | 1.60 | 36.8 |
| CTX_ONSET (no crowd) | ALL | 868 | -0.050 [-0.162…+0.066] | 0.93 | 25.7 |
| CTX_ONSET (no crowd) | TRAIN | 607 | -0.092 [-0.221…+0.048] | 0.88 | 24.5 |
| CTX_ONSET (no crowd) | OOS | 261 | +0.048 [-0.157…+0.258] | 1.06 | 28.4 |
| CTX_ONSET, crowd z≥1 with trend | ALL | 151 | +0.254 [-0.039…+0.555] | 1.37 | 32.5 |
| CTX_ONSET, crowd z≥1 with trend | TRAIN | 124 | +0.174 [-0.142…+0.501] | 1.24 | 30.6 |
| CTX_ONSET, crowd z≥1 with trend | OOS | 27 | +0.620 [-0.088…+1.360] | 2.06 | 40.7 |
| CTX_ONSET, crowd z 0..1 | ALL | 142 | -0.004 [-0.267…+0.280] | 1.00 | 26.8 |
| CTX_ONSET, crowd z 0..1 | TRAIN | 117 | +0.055 [-0.259…+0.383] | 1.08 | 28.2 |
| CTX_ONSET, crowd z 0..1 | OOS | 25 | -0.278 [-0.844…+0.317] | 0.66 | 20.0 |
| CTX_ONSET, crowd against trend (z<0) | ALL | 683 | -0.084 [-0.210…+0.046] | 0.89 | 25.0 |
| CTX_ONSET, crowd against trend (z<0) | TRAIN | 460 | -0.140 [-0.290…+0.012] | 0.82 | 23.5 |
| CTX_ONSET, crowd against trend (z<0) | OOS | 223 | +0.032 [-0.195…+0.262] | 1.04 | 28.3 |
| Z_AGAINST (crowd on our side) | ALL | 309 | -0.173 [-0.352…+0.006] | 0.78 | 22.3 |
| Z_AGAINST (crowd on our side) | TRAIN | 237 | -0.190 [-0.385…+0.021] | 0.76 | 21.5 |
| Z_AGAINST (crowd on our side) | OOS | 72 | -0.119 [-0.475…+0.274] | 0.85 | 25.0 |
| FULL_NO_OI | ALL | 359 | +0.067 [-0.104…+0.255] | 1.09 | 28.7 |
| FULL_NO_OI | TRAIN | 286 | +0.052 [-0.149…+0.253] | 1.07 | 28.3 |
| FULL_NO_OI | OOS | 73 | +0.127 [-0.272…+0.559] | 1.18 | 30.1 |
| FULL_NO_EXT | ALL | 588 | +0.061 [-0.076…+0.202] | 1.08 | 28.2 |
| FULL_NO_EXT | TRAIN | 490 | +0.074 [-0.078…+0.225] | 1.10 | 28.4 |
| FULL_NO_EXT | OOS | 98 | -0.007 [-0.337…+0.332] | 0.99 | 27.6 |
| CTX_EVERY_6h (no crowd, sampled) | ALL | 280 | -0.312 [-0.485…-0.136] | 0.62 | 19.3 |
| CTX_EVERY_6h (no crowd, sampled) | TRAIN | 198 | -0.357 [-0.551…-0.151] | 0.58 | 18.2 |
| CTX_EVERY_6h (no crowd, sampled) | OOS | 82 | -0.204 [-0.528…+0.158] | 0.75 | 22.0 |

Engine A trade days also present in CTX_ONSET: 113 of 115.

**Reading:** if CTX_ONSET (no crowd) ≈ FULL, the crowd condition adds little beyond the price/OI context. If FULL > CTX_ONSET and the crowd-split rows rank z≥1 > 0..1 > z<0, the crowd extreme carries real information.