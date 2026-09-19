# GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C

Status: THRESHOLD_STABILITY_INTERSECTION_NOT_OOS

## TRAIN-frozen thresholds

| Q | 5s impulse | 30s volume | 30s aligned volume |
|---:|---:|---:|---:|
| Q60 | 0.0000 | 43.60 | 17.20 |
| Q65 | 0.0521 | 56.00 | 20.60 |
| Q70 | 0.0979 | 63.00 | 22.80 |
| Q75 | 0.1306 | 73.00 | 29.00 |
| Q80 | 0.1707 | 80.80 | 36.00 |

## Threshold surface

| Family | Q | Period | N | Retain | +2ATR | +3ATR | EV ATR | PF |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| IMPULSE | Q60 | TRAIN | 32 | 60.4% | 18.8% | 9.4% | 0.330 | 1.520 |
| IMPULSE | Q60 | VALID | 33 | 44.6% | 33.3% | 12.1% | 0.369 | 1.653 |
| IMPULSE | Q60 | POST_CHECK | 21 | 46.7% | 33.3% | 19.0% | 0.321 | 1.552 |
| IMPULSE | Q65 | TRAIN | 16 | 30.2% | 37.5% | 18.8% | 1.384 | 4.549 |
| IMPULSE | Q65 | VALID | 21 | 28.4% | 38.1% | 9.5% | 0.563 | 2.313 |
| IMPULSE | Q65 | POST_CHECK | 11 | 24.4% | 36.4% | 36.4% | 0.702 | 2.539 |
| IMPULSE | Q70 | TRAIN | 14 | 26.4% | 28.6% | 7.1% | 0.237 | 1.531 |
| IMPULSE | Q70 | VALID | 18 | 24.3% | 38.9% | 11.1% | 0.549 | 2.103 |
| IMPULSE | Q70 | POST_CHECK | 6 | 13.3% | 50.0% | 50.0% | 0.844 | 2.996 |
| IMPULSE | Q75 | TRAIN | 12 | 22.6% | 33.3% | 8.3% | 0.524 | 2.924 |
| IMPULSE | Q75 | VALID | 17 | 23.0% | 41.2% | 11.8% | 0.577 | 2.095 |
| IMPULSE | Q75 | POST_CHECK | 5 | 11.1% | 40.0% | 40.0% | 0.720 | 2.420 |
| IMPULSE | Q80 | TRAIN | 10 | 18.9% | 40.0% | 10.0% | 0.564 | 2.728 |
| IMPULSE | Q80 | VALID | 16 | 21.6% | 37.5% | 12.5% | 0.490 | 1.875 |
| IMPULSE | Q80 | POST_CHECK | 2 | 4.4% | 50.0% | 50.0% | 0.993 | 9.774 |
| VOLUME | Q60 | TRAIN | 21 | 38.9% | 33.3% | 14.3% | 1.374 | 6.403 |
| VOLUME | Q60 | VALID | 35 | 47.3% | 28.6% | 5.7% | 0.188 | 1.322 |
| VOLUME | Q60 | POST_CHECK | 23 | 51.1% | 26.1% | 26.1% | 0.346 | 1.667 |
| VOLUME | Q65 | TRAIN | 19 | 35.2% | 36.8% | 15.8% | 1.585 | 10.432 |
| VOLUME | Q65 | VALID | 31 | 41.9% | 32.3% | 6.5% | 0.270 | 1.482 |
| VOLUME | Q65 | POST_CHECK | 20 | 44.4% | 30.0% | 30.0% | 0.526 | 2.124 |
| VOLUME | Q70 | TRAIN | 16 | 29.6% | 31.2% | 12.5% | 1.693 | 16.387 |
| VOLUME | Q70 | VALID | 26 | 35.1% | 34.6% | 7.7% | 0.228 | 1.368 |
| VOLUME | Q70 | POST_CHECK | 14 | 31.1% | 21.4% | 21.4% | 0.478 | 2.201 |
| VOLUME | Q75 | TRAIN | 14 | 25.9% | 35.7% | 14.3% | 2.012 | 42.367 |
| VOLUME | Q75 | VALID | 23 | 31.1% | 39.1% | 8.7% | 0.312 | 1.493 |
| VOLUME | Q75 | POST_CHECK | 12 | 26.7% | 25.0% | 25.0% | 0.642 | 2.923 |
| VOLUME | Q80 | TRAIN | 11 | 20.4% | 45.5% | 18.2% | 2.409 | 39.913 |
| VOLUME | Q80 | VALID | 23 | 31.1% | 39.1% | 8.7% | 0.312 | 1.493 |
| VOLUME | Q80 | POST_CHECK | 9 | 20.0% | 11.1% | 11.1% | 0.367 | 2.260 |
| ALIGNED_VOLUME | Q60 | TRAIN | 21 | 38.9% | 33.3% | 14.3% | 1.177 | 4.243 |
| ALIGNED_VOLUME | Q60 | VALID | 39 | 52.7% | 35.9% | 5.1% | 0.265 | 1.451 |
| ALIGNED_VOLUME | Q60 | POST_CHECK | 25 | 55.6% | 24.0% | 24.0% | 0.294 | 1.545 |
| ALIGNED_VOLUME | Q65 | TRAIN | 19 | 35.2% | 36.8% | 15.8% | 1.422 | 6.078 |
| ALIGNED_VOLUME | Q65 | VALID | 38 | 51.4% | 36.8% | 5.3% | 0.285 | 1.481 |
| ALIGNED_VOLUME | Q65 | POST_CHECK | 23 | 51.1% | 26.1% | 26.1% | 0.322 | 1.592 |
| ALIGNED_VOLUME | Q70 | TRAIN | 16 | 29.6% | 37.5% | 18.8% | 1.941 | 25.095 |
| ALIGNED_VOLUME | Q70 | VALID | 35 | 47.3% | 37.1% | 5.7% | 0.392 | 1.789 |
| ALIGNED_VOLUME | Q70 | POST_CHECK | 21 | 46.7% | 28.6% | 28.6% | 0.527 | 2.254 |
| ALIGNED_VOLUME | Q75 | TRAIN | 14 | 25.9% | 42.9% | 21.4% | 2.176 | 31.977 |
| ALIGNED_VOLUME | Q75 | VALID | 30 | 40.5% | 33.3% | 6.7% | 0.292 | 1.515 |
| ALIGNED_VOLUME | Q75 | POST_CHECK | 16 | 35.6% | 31.2% | 31.2% | 0.803 | 4.168 |
| ALIGNED_VOLUME | Q80 | TRAIN | 12 | 22.2% | 41.7% | 25.0% | 2.541 | 134.056 |
| ALIGNED_VOLUME | Q80 | VALID | 26 | 35.1% | 34.6% | 7.7% | 0.280 | 1.472 |
| ALIGNED_VOLUME | Q80 | POST_CHECK | 12 | 26.7% | 16.7% | 16.7% | 0.212 | 1.658 |
| IMPULSE_AND_VOLUME | Q60 | TRAIN | 12 | 22.6% | 33.3% | 16.7% | 2.423 | 223.288 |
| IMPULSE_AND_VOLUME | Q60 | VALID | 18 | 24.3% | 33.3% | 11.1% | 0.805 | 3.469 |
| IMPULSE_AND_VOLUME | Q60 | POST_CHECK | 10 | 22.2% | 30.0% | 30.0% | 0.689 | 2.718 |
| IMPULSE_AND_VOLUME | Q65 | TRAIN | 8 | 15.1% | 50.0% | 25.0% | 3.376 | NA |
| IMPULSE_AND_VOLUME | Q65 | VALID | 13 | 17.6% | 38.5% | 7.7% | 0.928 | 4.091 |
| IMPULSE_AND_VOLUME | Q65 | POST_CHECK | 8 | 17.8% | 37.5% | 37.5% | 0.745 | 2.487 |
| IMPULSE_AND_VOLUME | Q70 | TRAIN | 6 | 11.3% | 33.3% | 0.0% | 0.972 | NA |
| IMPULSE_AND_VOLUME | Q70 | VALID | 9 | 12.2% | 44.4% | 11.1% | 0.974 | 3.564 |
| IMPULSE_AND_VOLUME | Q70 | POST_CHECK | 4 | 8.9% | 50.0% | 50.0% | 1.287 | 4.279 |
| IMPULSE_AND_VOLUME | Q75 | TRAIN | 6 | 11.3% | 33.3% | 0.0% | 0.972 | NA |
| IMPULSE_AND_VOLUME | Q75 | VALID | 8 | 10.8% | 50.0% | 12.5% | 0.938 | 3.195 |
| IMPULSE_AND_VOLUME | Q75 | POST_CHECK | 2 | 4.4% | 50.0% | 50.0% | 3.109 | NA |
| IMPULSE_AND_VOLUME | Q80 | TRAIN | 5 | 9.4% | 40.0% | 0.0% | 1.003 | NA |
| IMPULSE_AND_VOLUME | Q80 | VALID | 7 | 9.5% | 42.9% | 14.3% | 0.709 | 2.452 |
| IMPULSE_AND_VOLUME | Q80 | POST_CHECK | 0 | 0.0% | NA% | NA% | NA | NA |
| IMPULSE_AND_ALIGNED_VOLUME | Q60 | TRAIN | 12 | 22.6% | 33.3% | 16.7% | 2.078 | 11.341 |
| IMPULSE_AND_ALIGNED_VOLUME | Q60 | VALID | 22 | 29.7% | 36.4% | 9.1% | 0.539 | 2.082 |
| IMPULSE_AND_ALIGNED_VOLUME | Q60 | POST_CHECK | 12 | 26.7% | 25.0% | 25.0% | 0.337 | 1.591 |
| IMPULSE_AND_ALIGNED_VOLUME | Q65 | TRAIN | 8 | 15.1% | 50.0% | 25.0% | 3.385 | NA |
| IMPULSE_AND_ALIGNED_VOLUME | Q65 | VALID | 15 | 20.3% | 40.0% | 6.7% | 0.721 | 2.994 |
| IMPULSE_AND_ALIGNED_VOLUME | Q65 | POST_CHECK | 8 | 17.8% | 37.5% | 37.5% | 0.745 | 2.487 |
| IMPULSE_AND_ALIGNED_VOLUME | Q70 | TRAIN | 7 | 13.2% | 42.9% | 14.3% | 1.331 | NA |
| IMPULSE_AND_ALIGNED_VOLUME | Q70 | VALID | 11 | 14.9% | 45.5% | 9.1% | 1.037 | 4.336 |
| IMPULSE_AND_ALIGNED_VOLUME | Q70 | POST_CHECK | 4 | 8.9% | 50.0% | 50.0% | 1.287 | 4.279 |
| IMPULSE_AND_ALIGNED_VOLUME | Q75 | TRAIN | 6 | 11.3% | 50.0% | 16.7% | 1.405 | NA |
| IMPULSE_AND_ALIGNED_VOLUME | Q75 | VALID | 10 | 13.5% | 50.0% | 10.0% | 1.015 | 3.967 |
| IMPULSE_AND_ALIGNED_VOLUME | Q75 | POST_CHECK | 2 | 4.4% | 50.0% | 50.0% | 3.109 | NA |
| IMPULSE_AND_ALIGNED_VOLUME | Q80 | TRAIN | 5 | 9.4% | 40.0% | 20.0% | 1.540 | NA |
| IMPULSE_AND_ALIGNED_VOLUME | Q80 | VALID | 8 | 10.8% | 50.0% | 12.5% | 0.882 | 3.065 |
| IMPULSE_AND_ALIGNED_VOLUME | Q80 | POST_CHECK | 0 | 0.0% | NA% | NA% | NA | NA |

## Plateau diagnostics

- IMPULSE: positive=[[60, 80]]; robust=[[60, 80]]
- VOLUME: positive=[[60, 80]]; robust=[[65, 80]]
- ALIGNED_VOLUME: positive=[[60, 80]]; robust=[[60, 80]]
- IMPULSE_AND_VOLUME: positive=[[60, 80]]; robust=[[60, 80]]
- IMPULSE_AND_ALIGNED_VOLUME: positive=[[60, 80]]; robust=[[60, 80]]

Intersections with VALID N<12 are descriptive only. No production winner selected.
