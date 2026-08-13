# SELL_CORE_013 — B3 × exact-parity LH+BOS incremental edge

## Verdict

**013A parity: PASS. 013B intersection: NOT PASS as a stable SELL core.**

## 013A parity

Frozen ResearchOS M1 ends 2026-08-10 05:59 UTC and is ~52–53h shorter than the user's source implied by 22,474 hourly clocks. On the common frozen sample:

- clocks: 22,421
- LH: 11,566
- LH+BOS: **1,609** (exact user count)
- gross directional WR: **49.534%**
- gross EV: **+0.094974%**
- net EV after 0.096% cost: **-0.001026%**
- net PF: **0.9992**

Thus the user's H1/LR2/LH/BOS implementation is reproduced correctly. The remaining LH/clock count difference is attributable to the shorter frozen data tail.

## 013B overlap

On the user's hourly grid, canonical H4 B3 aligned = H4 ST DOWN + age 27..50:

- total clocks: 22,421
- LH+BOS: 1,609
- B3 aligned clocks: 3,092
- intersection: **257**
- P(LH+BOS | B3) = 8.31%
- P(LH+BOS | not B3) = 6.99%
- phi = **0.0176**

Therefore B3 and LH+BOS are almost orthogonal descriptors; the intersection is not merely the same state measured twice.

## Aggregate intersection

### User-native exit

B3 + LH+BOS, 48h:

- N=257, 29 H4 episodes
- net price EV **+0.1738%**
- PF **1.11**
- net WR **52.53%**

B3 without LH+BOS:

- EV -0.1450%
- PF 0.91

Raw uplift = **+0.3188 percentage points**, but episode bootstrap CI `[-0.830, +1.658]`, P(uplift>0)=63.2%.

### Canonical ResearchOS exit

B3 + LH+BOS, 48h:

- price EV **+0.3003%**, PF 1.33
- EV **+0.4944R**, PF_R **1.70**

B3 without LH+BOS:

- price EV +0.2259%
- EV +0.2997R

Incremental uplift inside B3:

- +0.0745 percentage points, CI `[-0.812, +1.161]`, P>0=49.9%
- +0.1947R, CI `[-0.714, +1.329]`, P>0=58.1%

Thus the aggregate intersection is positive, but the incremental gain over B3 itself is not statistically demonstrated.

## Year transfer — intersection

### Native 48h

- 2024: N48, **-1.340%**, PF 0.29
- 2025: N132, **-0.675%**, PF 0.61
- 2026: N77, **+2.573%**, PF 3.35

### Canonical 48h

- 2024: **-0.742R**, price -1.106%
- 2025: **-0.205R**, price -0.285%
- 2026: **+2.463R**, price +2.181%

Inside-B3 comparison also shows the same migration: LH+BOS hurts B3 materially in 2024, is slightly worse in 2025, and strongly improves B3 in 2026.

Therefore the attractive aggregate is dominated by the 2026 regime and is not a 2024–2026 transferable selector.

## Phase robustness

The user's grid is anchored at minute :20. Frozen sensitivity used :20 / :40 / :00.

Intersection is stable across phase:

- Native price EV: +0.174%, +0.174%, +0.245%
- Canonical 48h EV: +0.494R, +0.479R, +0.520R
- Canonical 72h EV: +0.773R, +0.759R, +0.783R

So the result is not a :20 grid artifact. The failure is transfer/regime stability, not phase timing.

## Frozen conclusion

1. Exact LH+BOS detector parity is established.
2. B3 and LH+BOS are nearly orthogonal.
3. Their intersection is positive in aggregate and phase-robust.
4. **It is not a valid universal SELL core because 2024 and 2025 remain negative and the apparent edge comes from 2026.**
5. Do not rescue this result post hoc with topology/funding/FVG/v283.
6. The useful next research question is why structural SELL selection turns on so strongly in 2026 and whether that regime change can be identified causally before entry.

013A run: `31702684638`, artifact `9181888862`, SHA256 `71bf632d1611e7f50197586807d0e7626f8c11562dc8dfc70ca34f468a832a90`.

013B run: `31702973260`, artifact `9182027499`, SHA256 `71fdd3d96296faecd239a6119a85c343d6f659c4a085b71ef88b24fc0c279b28`.
