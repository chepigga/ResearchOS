# XAU LAB022 IMPLEMENTATION MANIFEST v001
Date: 2026-08-24
Status: PRE-OUTCOME CODE FREEZE

- Spec SHA-256: c7b5552bbfd6c68484ff6d62ee91a9244df35f7a4f231393b04164dc2b54a32e
- Runner SHA-256: 8f87e91b4efce196296f4f51727212c434c3324cdc7338a1284215242f577d9b
- DF cache SHA-256: ec05163508f6f69c9688e5e50e1f418f6ca64aba42f17cf8d6504775df147ef8
- Setups cache SHA-256: 83526be03cb66ff596c3949138e7e8935cd12b9f8783a41adaf5f2c04d4ccfda
- Parent LAB012 runner SHA-256: 09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a
- LAB020 runner SHA-256: 8e0cd8dc09d5a9d48fab7b951091e836e8d4f276943cd1663192314f8f0ae78d
- LAB021 final runner SHA-256: 3e38dd164f61e36e5e5b30a39b303e50fe585e150f15a804e034a01a79a733f3

Implementation details frozen before outcomes:
- Base model/features/labels/snapshot clock imported from frozen LAB021/LAB020 lineage.
- Temporal calibration folds:
  - train < 2023-01-01, predict 2023H1;
  - train < 2023-07-01, predict 2023H2.
- Primary calibrator: one scalar multiclass temperature T per target, bounded [0.50, 5.00], minimizing temporal-OOT Discovery multiclass logloss.
- Final base model refit on all Discovery after T freeze.
- Calibration does not change rank ordering within a target.
- TIME payoff remains Discovery-only.
- Decision remains EV_REMAINING <= 0 -> exit next contiguous M1 open.
- No Confirmation tuning, no threshold margin, no holdout opening.
