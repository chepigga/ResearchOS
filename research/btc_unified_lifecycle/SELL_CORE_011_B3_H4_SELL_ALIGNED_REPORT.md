# SELL_CORE_011 — B3 × H4_SELL_ALIGNED STATE VALIDATION

## Verdict

**NOT PASS / do not freeze as SELL core.**

The previously observed aggregate clue is real and reproducible, but it is not stable enough across years or H4-age phase to promote as a standalone SELL state.

## Frozen state

- Canonical H4 Supertrend ATR10×3, U05 BAR_OPEN lag1.
- SELL-aligned = H4 ST DOWN.
- Frozen SELL B3 = H4 ST age 27..50 inclusive.
- No funding, FVG, CHoCH, v283, flow or other gates.
- FIRST = first eligible B3 clock per continuous bearish ST episode.
- PERIODIC_4H = every eligible B3 H4 clock.
- Phase robustness = 0h primary, +2h sensitivity.
- SL = 1.5× completed H1 ATR14; no TP; 48h primary / 72h sensitivity; $27.5/BTC cost proxy.
- Cluster inference by continuous H4 ST episode.
- Max concurrent initial risk diagnostic per episode = 0.5%.

## Primary 48h results

### FIRST at B3 onset (age 27)

- N = 45, 45 episodes.
- EV = **+0.681R**.
- PF = **1.82**.
- Price EV = **+0.622%**.
- Cluster bootstrap 95% CI R = `[-0.343, +1.909]`, P(EV>0)=88.5%.
- Price-space CI = `[-0.437%, +1.901%]`, P>0=85.1%.

Strong point estimate, but uncertainty is too wide for PASS.

Yearly FIRST:

- 2024: N19, EV **-0.067R**, PF0.93, price -0.025%.
- 2025: N16, EV **+0.523R**, PF1.68, price +0.526%.
- 2026: N10, EV **+2.352R**, PF4.22, price +2.005%.

Thus FIRST is 2/3 positive and heavily strengthened in 2026.

### PERIODIC_4H

- N = **778**, 46 episodes.
- EV = **+0.296R**.
- PF = **1.392**.
- Price EV = **+0.233%**.
- Cluster-bootstrap 95% CI R = `[-0.179, +0.823]`, P(EV>0)=87.7%.
- Price CI = `[-0.278%, +0.807%]`, P>0=79.0%.

This exactly reproduces the earlier SELL_CORE_003 B3/H4-SELL-aligned clue (`N=778`, EV≈+0.296R, PF≈1.39), confirming that the clue was not created by flip-count conditioning.

Yearly PERIODIC_4H:

- 2024: N286, EV **+0.101R**, PF1.13, but price EV **-0.192%**.
- 2025: N311, EV **-0.139R**, PF0.83, price **-0.067%**.
- 2026: N181, EV **+1.352R**, PF3.16, price **+1.423%**.

So the aggregate edge is not transferable: 2025 is negative, and 2024 disagrees between R and price space. 2026 dominates the aggregate improvement.

## Phase robustness

The state is robust to a +2h phase shift:

- FIRST 48h: +0.681R at 0h vs **+0.816R** at +2h; paired delta +0.135R, CI crosses zero.
- PERIODIC 48h: +0.296R vs **+0.309R**; delta +0.013R, essentially invariant.
- PERIODIC 72h: +0.242R vs +0.256R.

Therefore the failure is **not exact clock-timestamp fragility**.

## Episode-risk bootstrap

Using the preregistered 0.5% max-concurrent episode risk budget:

- FIRST 48h: mean episode return +0.340%, CI `[-0.171%, +0.954%]`, P>0=88.5%.
- PERIODIC_4H 48h: +0.209%, CI `[-0.122%, +0.586%]`, P>0=88.0%.
- PERIODIC_4H 72h: +0.114%, CI `[-0.131%, +0.414%]`, P>0=78.4%.

No episode-level 95% PASS.

## H4-age topology diagnostic

The preregistered bar-for-bar age table shows B3 age 27..50 is not homogeneous.

Early B3 is mostly positive:

- age27 +0.681R
- 28 +0.637R
- 29 +0.947R
- 30 +0.769R
- 31 +0.289R
- 32 +0.875R
- 33 +0.630R
- 34 +0.292R
- 35 +0.155R

Middle B3 deteriorates:

- 36 -0.442R
- 37 -0.005R
- 38 -0.247R
- 39 -0.634R
- 40 +0.028R
- 41 -0.224R
- 42 +0.022R
- 43 -0.254R
- 44 -0.242R

Late B3 improves again:

- 45 +0.435R
- 46 +0.510R
- 47 +0.273R
- 48 +0.972R
- 49 +0.303R
- 50 +0.943R

This U-shaped profile is a **diagnostic clue only**. No age subrange is promoted because it was observed after outcomes.

## Frozen interpretation

1. `B3 × H4 SELL-aligned` is a genuine recurring market phenomenon, not a calculation artifact.
2. It is **not stable enough to become the SELL backbone**: cluster uncertainty crosses zero and yearly transfer fails.
3. Exact H4 timing is not the problem; +2h phase shift leaves results almost unchanged.
4. The B3 bucket appears to mix multiple lifecycle phases. The next research question should concern **bearish H4 age/phase topology and transfer**, not another stacked filter.
5. Do not rescue this result post hoc by selecting ages 27–35 or 45–50 from this table.

Workflow run: `31698900232`  
Artifact: `9180423389`  
Artifact SHA256: `870220435920c84f1f75fbd553eafbabf4f2d2e10088cd4c3c9c89210d62b170`
