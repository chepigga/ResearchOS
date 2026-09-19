# GC_XAU_BIG_MOVE_DISCRIMINATOR_INSIDE_REPEATED_FAILED_ATTACK_LAB006

Status: CAUSAL_DISCRIMINATOR_DISCOVERY_NOT_OOS

## Base causal hit rates

| Subset | Period | N | +2 ATR <=5m | +3 ATR <=5m |
|---|---|---:|---:|---:|
| ALL | TRAIN | 5004 | 19.6% | 7.8% |
| ALL | VALID | 6422 | 19.9% | 7.4% |
| ALL | POST_CHECK | 3745 | 19.7% | 7.4% |
| QUIET | TRAIN | 2723 | 18.8% | 6.8% |
| QUIET | VALID | 3468 | 19.6% | 6.9% |
| QUIET | POST_CHECK | 2053 | 19.4% | 7.4% |

## Frozen TRAIN-tail feature tests

| Feature | Tail | Threshold | Train N | T +2 lift | T +3 lift | Valid N | V +2 lift | V +3 lift | Post +2 lift | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| prior30_abs_move_atr | Q5 | 0.1862 | 545 | 1.11x | 1.13x | 768 | 1.18x | 1.19x | 0.91x | FAIL |
| prior30_signed_pred_move_atr | Q1 | -0.1463 | 545 | 1.09x | 1.02x | 668 | 1.16x | 1.19x | 1.01x | FAIL |
| attack2_impact | Q5 | 0.1448 | 545 | 1.19x | 1.42x | 678 | 1.10x | 1.09x | 1.03x | FAIL |
| efficiency2 | Q5 | 0.5716 | 545 | 1.17x | 1.21x | 767 | 1.10x | 1.07x | 0.89x | FAIL |
| prior60_signed_pred_move_atr | Q1 | -0.7844 | 545 | 1.01x | 0.91x | 674 | 1.08x | 1.29x | 1.03x | FAIL |
| attack1_delta_frac | Q1 | -0.4069 | 545 | 1.19x | 1.21x | 599 | 1.06x | 1.28x | 1.04x | FAIL |
| prior60_range_atr | Q5 | 1.2043 | 545 | 1.06x | 1.05x | 672 | 1.06x | 1.31x | 1.08x | FAIL |
| abs_delta_frac_1 | Q5 | 0.5714 | 552 | 1.03x | 0.93x | 522 | 1.05x | 1.30x | 1.01x | FAIL |
| attack2_delta_frac | Q1 | -0.3333 | 560 | 1.07x | 0.91x | 596 | 1.04x | 1.24x | 1.01x | FAIL |
| abs_delta_frac_2 | Q5 | 0.4783 | 547 | 0.97x | 0.86x | 520 | 1.03x | 0.92x | 1.16x | FAIL |
| efficiency_deterioration | Q1 | 0.3163 | 545 | 1.11x | 1.05x | 652 | 1.02x | 1.06x | 0.97x | FAIL |
| gc_pred_60_atr | Q1 | -0.7566 | 545 | 0.94x | 0.86x | 692 | 1.02x | 1.17x | 1.05x | FAIL |
| gc_minus_xau_signed_context | Q5 | 0.1356 | 545 | 1.07x | 1.05x | 600 | 1.00x | 1.20x | 1.10x | FAIL |
| impact_deterioration | Q1 | 0.1424 | 545 | 1.05x | 1.07x | 664 | 0.99x | 0.96x | 0.98x | FAIL |
| attack2_volume | Q5 | 61.0000 | 550 | 1.09x | 1.06x | 979 | 0.97x | 0.87x | 0.89x | FAIL |
| persistence_abs_delta | Q5 | 0.3333 | 683 | 1.08x | 1.11x | 639 | 0.97x | 1.11x | 1.12x | FAIL |
| efficiency1 | Q1 | 0.4394 | 545 | 1.01x | 0.94x | 618 | 0.97x | 1.01x | 0.98x | FAIL |
| attack1_impact | Q5 | 0.7078 | 545 | 1.01x | 0.94x | 657 | 0.94x | 1.14x | 1.08x | FAIL |
| attack1_volume | Q5 | 72.0000 | 553 | 1.05x | 1.14x | 938 | 0.91x | 0.86x | 0.93x | FAIL |
| volume_ratio_2_to_1 | Q1 | 0.4118 | 546 | 1.05x | 1.21x | 606 | 0.85x | 1.00x | 1.02x | FAIL |

Survivors: NONE

No execution optimization was performed. Thresholds are TRAIN-only quintile edges, frozen before VALID/POST evaluation.
