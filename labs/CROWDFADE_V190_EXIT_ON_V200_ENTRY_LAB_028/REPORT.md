# CROWDFADE_V190_EXIT_ON_V200_ENTRY_LAB_028

## Purpose

Apply the **literal v1.90 exit engine** to the frozen v200 entry and LAB026 risk sizing.

Frozen v200 entry/risk:

- Z = 2.50 / 2.50
- M15 confirmation = 0.25 ATR
- confirmation TTL = 60m
- passive retrace = 0.60 ATR
- limit TTL = 20m
- hard SL = 4.5 ATR
- max 3/day
- anti-repeat = 1 ATR
- LAB026 risk = HIGH 1.50x / NORMAL 1.00x / LOW 0.75x

Literal v190 exit engine from source code:

- BE trigger = +0.50 ATR
- BE lock = +0.15 ATR
- trail arm = +2.50 ATR MFE
- trail distance = 0.50 ATR from peak
- signal exit = opposite |Z| >= 1.00
- time exit = 6h
- no fixed TP

Important: v190 itself uses hard SL = 1.00 ATR. This LAB intentionally keeps v200 hard SL = 4.5 ATR and transfers only the exit engine exactly as requested.

---

# Historical 2021–2025

## Exact v190 exit + LAB026

- N = 1689
- WR = **81.23%**
- EV = **+0.00484R**
- SumR = **+8.17R**
- PF = **1.039**
- MaxDD = 13.80R
- R/DD = **0.592**
- positive years = **3/5**

Annual:

- 2021 +8.20R
- 2022 +2.82R
- 2023 **-3.47R**
- 2024 **-2.93R**
- 2025 +3.56R

Exit mix:

- hard SL = 136
- BE/trail stop = **1314**
- signal exit = 187
- time = 52

The engine produces a very high win rate by cutting trades very early, but almost all expectancy disappears.

## Without signal exit

- N = 1685
- WR = 82.85%
- EV = **-0.00188R**
- SumR = **-3.17R**
- PF = 0.986
- 2/5 positive years

Signal exit is therefore not the main problem. It actually helps somewhat.

## 24h hold with signal exit

- N = 1685
- WR = 82.26%
- EV = +0.00720R
- SumR = +12.13R
- PF = 1.058
- 4/5 positive years

Longer hold helps slightly but does not restore the edge.

---

# 2026 second-level forward-shadow

## Exact v190 exit + LAB026

- N = 187
- WR = **81.82%**
- EV = **-0.0111R**
- SumR = **-2.08R**
- PF = **0.892**
- MaxDD = 3.83R
- positive months = **3/6**

Monthly:

- Mar -1.09R
- Apr -2.02R
- May +0.59R
- Jun +0.70R
- Jul -0.40R
- Aug +0.15R

Exit mix:

- hard SL = 8
- BE/trail stop = **145**
- signal exit = 25
- time = 9

This confirms the historical result: literal v190 exits over-tighten the v200 system.

## No signal exit

- EV = -0.00216R
- SumR = -0.40R
- PF = 0.979
- 4/6 positive months

## 24h hold + signal exit

- EV = -0.00706R
- SumR = -1.32R
- PF = 0.929
- 3/6 positive months

Neither ablation repairs the system.

---

# Why the literal transfer fails

v190 hard SL:

> 1.00 ATR = 1R

Therefore its exit geometry is approximately:

- BE trigger = +0.50R
- BE lock = +0.15R
- trail arm = +2.50R
- trail distance = 0.50R

v200 hard SL:

> 4.50 ATR = 1R

If the v190 ATR numbers are copied literally:

- BE trigger 0.50 ATR = **+0.111R**
- BE lock 0.15 ATR = **+0.033R**
- trail arm 2.50 ATR = **+0.556R**
- trail distance 0.50 ATR = **0.111R**

So the exit engine becomes radically tighter relative to risk.

This explains:

- extremely high WR;
- very high BE/trail stop count;
- collapsed EV;
- loss of right tail.

The problem is therefore **unit mismatch / geometry mismatch**, not evidence that v190-style dynamic exits are inherently bad.

---

# Correct next interpretation

If the goal is to preserve the **behavioral geometry** of v190 on the wider v200 stop, the v190 exits should be translated in R, not copied in ATR.

Geometry-equivalent v200 values would be approximately:

- BE trigger = +0.50R = **+2.25 ATR**
- BE lock = +0.15R = **+0.675 ATR**
- trail arm = +2.50R = **+11.25 ATR**
- trail distance = +0.50R = **2.25 ATR**
- signal exit = opposite |Z| >= 1.00
- time exit = 6h

That is a different experiment and was **not** tested in LAB028.

---

# Verdict

**Literal v190 exit-engine on v200 = FAIL.**

Do not deploy these literal ATR parameters on v200.

The next meaningful test, if desired, is:

> v190 geometry preserved in R on v200 entry + LAB026

rather than literal ATR transfer.
