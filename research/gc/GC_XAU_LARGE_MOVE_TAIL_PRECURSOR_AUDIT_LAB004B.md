# GC_XAU_LARGE_MOVE_TAIL_PRECURSOR_AUDIT_LAB004B

Tail event audit: +/-2 ATR and +/-3 ATR first passage within 5m.

| Threshold | Period | N | Quiet | delta_flip ALL enrich | repeated ALL enrich | repeated QUIET enrich |
|---:|---|---:|---:|---:|---:|---:|
| 2.0 ATR | TRAIN | 2470 | 771 | 1.03x | 1.21x | 1.85x |
| 2.0 ATR | VALID | 2330 | 685 | 1.01x | 1.09x | 1.41x |
| 2.0 ATR | POST_CHECK | 1349 | 366 | 0.97x | 1.09x | 2.38x |
| 3.0 ATR | TRAIN | 1272 | 327 | 0.86x | 1.16x | 1.49x |
| 3.0 ATR | VALID | 1170 | 353 | 0.71x | 1.05x | 1.51x |
| 3.0 ATR | POST_CHECK | 674 | 184 | 0.88x | 1.25x | 1.46x |

No threshold winner selected. No execution optimization.
