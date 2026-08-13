# U02C6 — B3 V283 OCCURRENCE SELECTION ABLATION

**Status:** STRONG CANDIDATE PASS, with an important architectural restriction.

## Corrected causal design

The first comparator using episodes that never received v283 in their future lifetime was rejected because it future-conditioned the control group.

The accepted comparator is a causal risk set at the same B3 age/delay: same year, state still active, no v283 occurrence known yet, allowed to receive v283 later. Controls are matched on comparison-time RV168_control and ATR%.

Treated entry is the first fixed H4 clock strictly after first v283 BUY occurrence; it is not the exact v283 timestamp. Exit: SL=1.5×completed H1 ATR14, no TP, 48h time exit, $27.5/BTC cost proxy.

## Primary result

| Estimator | N | Treated EV | Control EV | Delta | 95% CI | P(delta>0) |
|---|---:|---:|---:|---:|---:|---:|
| K1 nearest | 48 | +0.918R | -0.227R | **+1.145R** | **[+0.028,+2.333]** | **97.79%** |
| K5 mean | 48 | +0.918R | -0.046R | **+0.964R** | [-0.017,+2.093] | **97.25%** |

Volatility matching balance is good: K1 SMD log RV168=-0.061, log ATR%=-0.132; K5 pool -0.018 and -0.162.

Yearly excess is positive 3/3:
- 2024: K1 +0.940R; K5 +0.948R
- 2025: K1 +1.173R; K5 +0.895R
- 2026: K1 +1.428R; K5 +1.088R

## Important restriction

Occurrence does **not** make the whole remainder of B3 periodically tradable:
- 4h after activation: EV -0.112R, PF 0.85
- 8h: EV -0.103R, PF 0.87
- 12h: approximately flat, PF ~1.00

So the candidate rule is:

`B3 BUY -> wait for first v283 BUY occurrence -> one BUY at next fixed H4 clock -> SL 1.5×H1 ATR -> no TP -> 48h time exit`

Not:

`B3 + occurrence -> trade every 4h/8h for the rest of the episode`.

## Verdict

- Exact v283 M5 timestamp remains rejected as proven fine timing alpha.
- v283 occurrence is a **strong candidate B3 activation selector**.
- It survives same-age risk-set control, year control and RV168/ATR% matching.
- K1 CI excludes zero; K5 is borderline by 0.017R, therefore classify **STRONG CANDIDATE PASS**, not frozen production truth.

## Current core candidates

- Tier A BUY: state-only, periodic 4h practical prop candidate.
- B3 BUY: occurrence activation -> one next-H4 BUY.
- Tier B BUY: not accepted yet.
- SELL: no validated core branch yet.

Next: assemble the minimal BTC core and unified portfolio replay before ETH transfer.
