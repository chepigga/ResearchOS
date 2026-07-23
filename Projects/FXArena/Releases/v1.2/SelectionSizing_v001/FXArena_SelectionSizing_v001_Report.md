# FXArena Selection & Sizing Lab v001

## Verdict

**A_VERDICT_VALID__B_STOP_CONTROL_MISMATCH**

P0 exits and ContPrimary were not modified. Gate metric is gross MaxDD. Bootstrap is paired moving-block, block 20, 5000 iterations, shared indices; absolute formulation is rejected.

## Control

- N: 3535
- Total net: +1848.874807R
- Gross MaxDD: 14.415969R
- p parity max abs diff: 1.11e-16
- **PASS: True**

## Part A — sizing tiers

- Total weighted: +1924.73R
- EV weighted: +0.544478R
- Gross MaxDD weighted: 15.185R
- Realized mean weight: 0.997199
- EV monotonic by p tercile: **True**

| Tier | N | Mean p | Flat EV | Weighted total |
|---|---:|---:|---:|---:|
| LOW | 1226 | 0.591150 | +0.433691R | +372.19R |
| MID | 1116 | 0.633068 | +0.477252R | +532.61R |
| HIGH | 1193 | 0.743755 | +0.657633R | +1019.92R |

Gates: `{"SA1_total": true, "SA2_gross_DD": false, "SA3_calendar": true, "SA4_permutation": true, "SA5_paired_bootstrap": false}`

SA4 real advantage +75.86R; null p95 +1887.45R; p=0.004975.

SA5 P(total candidate > baseline)=99.5800%; P(DD candidate > baseline+0.5)=56.1800%.

**Part A verdict: FAIL**

## Part B — threshold curve

| Top | N | Total | EV | Gross DD | Negative months | Day-cap rejected/raw |
|---:|---:|---:|---:|---:|---:|---:|
| 3% | 3059 | +1684.85R | +0.5508R | 13.165R | 0 | 39.43% |
| 4% | 3515 | +1889.61R | +0.5376R | 14.416R | 0 | 45.00% |
| 5% | 3795 | +1911.84R | +0.5038R | 14.700R | 0 | 49.92% |
| 6% | 3951 | +1765.83R | +0.4469R | 15.124R | 1 | 52.19% |

### Frozen 4% control

- Trailing q0.96 N: 3515
- PINNED N: 3535
- Ordered IDs equal: False
- Intersection: 2893
- Trailing total: +1889.61R
- PINNED total: +1848.87R
- **Control verdict: STOP**

Source audit: original monthly-top-4% gives N=3535, ordered parity=True.

**Part B verdict: STOP — control mismatch**

## Composition

Not run: both A and B had to pass.

## Governance

No weights or threshold cells were tuned. Part B curves are diagnostic only and cannot be promoted. Sampler source, seeds, trades, bootstrap CSVs, plots and SHA256 manifest are preserved in the complete workflow artifact.
