# SELL_CORE_003 — B3 × HTF_FLIP_COUNT_7D

## Verdict

**REJECT `flip_cnt_7d` as an independent SELL selector under the canonical H4 market clock.**

Feature used in this lab:
- canonical H4 Supertrend ATR10×3, U05 BAR_OPEN lag1;
- `flip_cnt_7d` = count of causal H4 ST direction changes over the previous 42 completed H4 observations (7 days);
- exact older implementation was not present in the repository, so this literal definition was frozen before outcomes.

Primary universe:
- SELL B3, ST age 27–50;
- every H4 boundary in state;
- next M1 open entry;
- SL = 1.5×completed H1 ATR14;
- no TP;
- 48h primary / 72h sensitivity;
- $27.5/BTC cost proxy.

## Raw descriptive quintiles

48h rank quintiles:
- Q1: +0.186R, PF 1.26
- Q2: -0.012R, PF 0.98
- Q3: +0.101R, PF 1.12
- Q4: -0.294R, PF 0.65
- Q5: +0.654R, PF 1.90

72h:
- Q1: +0.275R
- Q2: -0.109R
- Q3: -0.047R
- Q4: -0.260R
- Q5: +0.510R

The raw Q5 looks strong but its mean ST age is ~32.5 versus ~45.8 in Q1. Because B3 itself is defined by ST age, this is a major structural confound.

Discrete counts make the same point:
- flip=0: 48h +0.111R; 72h +0.135R
- flip=1: 48h +0.172R; 72h +0.092R
- flip=2: 48h -0.250R; 72h -0.367R

There is no monotonic raw advantage with more flips.

## Primary exact-age + year controlled test

Coefficient = incremental outcome per one extra flip after demeaning within exact ST age and calendar year; uncertainty from 20,000 cluster-bootstrap resamples of continuous ST episodes.

SELL B3 age 27–50:
- 48h beta_R = **-0.532R**, CI [-1.394, +0.402], P(beta>0)=11.9%
- 48h beta_price = -0.286 pp, P>0=28.5%
- 72h beta_R = **-0.499R**, CI [-1.421, +0.638], P(beta>0)=16.7%
- 72h beta_price = -0.250 pp, P>0=33.1%

Generic B3 age 28–58 sensitivity:
- 48h beta_R = **-0.636R**, CI [-1.457, +0.278], P(beta>0)=8.0%
- 48h beta_price = -0.445 pp, P>0=19.1%
- 72h beta_R = **-0.547R**, CI [-1.436, +0.523], P(beta>0)=13.6%
- 72h beta_price = -0.389 pp, P>0=25.1%

Thus the apparent high-flip Q5 advantage does not survive control for B3 phase age and year. `flip_cnt_7d` is mostly acting as a proxy for where we are inside B3, not as independent SELL information.

## Important secondary clue

H4 relation remains directionally useful in the same primary sample:
- SELL-aligned B3: 48h EV +0.296R, PF 1.39; 72h +0.242R, PF 1.31
- SELL-opposite B3: 48h EV -0.064R, PF 0.92; 72h -0.116R, PF 0.86

This is descriptive in SELL_CORE_003 and should not be promoted without a dedicated age/year-controlled relation test.

## Research decision

- Do not use `flip_cnt_7d` as a hard SELL gate.
- Do not interpret the raw Q5 as a standalone rotational-regime edge.
- Preserve the H4 SELL-aligned B3 clue for the next dedicated SELL lab.
