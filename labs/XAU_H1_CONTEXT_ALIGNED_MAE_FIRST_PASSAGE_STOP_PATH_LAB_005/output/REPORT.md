# XAU_H1_CONTEXT_ALIGNED_MAE_FIRST_PASSAGE_STOP_PATH_LAB_005

**Verdict: H1_STOP_PATH_MISMATCH_NOT_SUPPORTED**

> Reused-history causal path diagnostic. No stop change, filter, sizing, or production promotion is authorized.

## Frozen H1 HIGH subset

- ALIGNED: 1195
- OPPOSED: 966
- Frozen realized excess premium A-O: **-0.11386R**
- 120h terminal directional premium A-O: **+0.73318R**

## Primary STOP-FIRST -> late +1R recovery

- ALIGNED rate: **22.5105%**
- OPPOSED rate: **27.4327%**
- Delta recovery: **-4.9223%**
- Weekly bootstrap 95% CI: **[-10.1373%, +0.7692%]**, P>0=0.047
- Years positive: 1/4; LOYO positive: 0/4

## Recovery conditional on current stop-first

- ALIGNED stop-first rate: 43.264%; recover-to-zero given stop: 69.826%; recover-to-+1R given stop: 52.031%
- OPPOSED stop-first rate: 52.070%; recover-to-zero given stop: 72.366%; recover-to-+1R given stop: 52.684%

## Gates
- FAIL — `S1_delta_recovery_gt_zero`
- FAIL — `S2_boot_ci_lo_gt_zero`
- PASS — `S3_terminal_120h_premium_gt_zero`
- PASS — `S4_realized_frozen_premium_lt_zero`
- FAIL — `S5_year_3of4_positive`
- FAIL — `S6_loyo_3of4_positive`

See CSV outputs for MAE/MFE, symmetric first-passage, year/LOYO transfer, recovery timing, and fixed 1:1.5 stop-width ablations.