# GC_M1_AEIF_HISTORICAL_EDGE_REPLICATION_001

Exact LAB001-style M1 mechanism replication on raw GC feeds already in the GC release. No XAU, no execution model, no threshold sweep.

## Original ATAS/dxFeed reference

- LAB001 reference: A N=356, B N=77, D N=46 on 2026-09-06 22:00 through 2026-09-11 12:46.
- Reference B EV: 5m +0.407 ATR; 15m +0.561 ATR.
- Reference D EV: 5m +0.399 ATR; 15m +0.646 ATR.

## Rithmic raw

Coverage: `2026-08-03T00:00:00+00:00` → `2026-09-11T20:59:00+00:00`; M1 bars **41102**.

### Full historical coverage

| Stage | N | 1m | 3m | 5m | 15m |
|---|---:|---:|---:|---:|---:|
| A | 2494 | +0.018 | +0.017 | +0.017 | +0.060 |
| B | 438 | +0.017 | +0.038 | +0.054 | +0.152 |
| D | 238 | +0.259 | +0.618 | +0.534 | +0.795 |

### Exact ATAS/LAB001 clock overlap

| Stage | N | 1m | 3m | 5m | 15m |
|---|---:|---:|---:|---:|---:|
| A | 374 | -0.010 | +0.049 | +0.128 | +0.252 |
| B | 54 | -0.044 | -0.040 | +0.158 | +0.266 |
| D | 31 | +0.172 | +0.443 | +0.509 | +1.036 |

Overlap counts: A **375**, B **54**, D **31**.

## AMP/CQG raw

Coverage: `2026-08-06T18:24:00+00:00` → `2026-09-15T18:23:00+00:00`; M1 bars **38464**.

### Full historical coverage

| Stage | N | 1m | 3m | 5m | 15m |
|---|---:|---:|---:|---:|---:|
| A | 2373 | +0.007 | +0.009 | +0.018 | +0.080 |
| B | 441 | -0.000 | +0.028 | +0.022 | +0.094 |
| D | 243 | +0.226 | +0.565 | +0.529 | +0.682 |

### Exact ATAS/LAB001 clock overlap

| Stage | N | 1m | 3m | 5m | 15m |
|---|---:|---:|---:|---:|---:|
| A | 378 | -0.021 | +0.010 | +0.114 | +0.163 |
| B | 55 | -0.030 | +0.093 | +0.373 | +0.346 |
| D | 34 | +0.179 | +0.560 | +0.888 | +1.317 |

Overlap counts: A **379**, B **55**, D **34**.

## Interpretation rule

This LAB does not select a winner across feeds or variants. The question is whether the original M1 effort/result mechanism remains directionally positive on longer raw histories and on the exact LAB001 clock overlap. If full-history B/D loses sign while only the short overlap is positive, the edge is regime/sample-specific. If B/D remains positive across both raw feeds, it is materially stronger evidence for a transportable M1 GC edge.
