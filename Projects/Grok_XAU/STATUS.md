# Grok XAU Status

**Updated:** 2026-07-24  
**Project status:** ACTIVE / VALIDATED  
**Validated laboratory:** BH_OOS_002 v2  
**Formal verdict:** PASS — DEMO ONLY

## Canonical module

The relevant source is `AK47_FT_EA_156.mq5`, which contains `BH_SWEEP v1.55`
inside EA v1.56. `Grok_Core_XAU.mq5` is unrelated and must not be used for this
research line.

Frozen configuration:

- XAUUSD M15;
- fractal depth 5;
- swing age 96 bars;
- BeltHold window 0..3;
- body >= 0.60 range;
- opposite shadow <= 0.05 range;
- EMA20 reversal context;
- next-M15-open entry;
- SL extremum[sweep..signal] +/- 0.25 ATR14;
- TP 2R;
- 96 actual M15-bar time stop;
- conservative same-bar SL priority;
- OOS cost correction -0.05R/trade.

## Step 0 reproduction control

**PASS**

- Target: N=88, BUY=52, SELL=36, EV=+0.276R.
- Reproduced: N=88, BUY=52, SELL=36, legacy EV=+0.275780R.
- Entry-time and direction matches: 88/88.
- Exit-reason mismatches: 0.
- Canonical parent: `BeltHold_trades_regen_wide-2026-07-05.csv` plus EMA20 reversal context.
- The `tight` file is EMA10 sensitivity N=56, not the canonical basket.
- Fixed -0.05R cost produces +0.258370R, drift -0.017630R, inside the registered 0.02R tolerance and explained by the cost convention.

## Frozen OOS result

Window: `2026-05-01..2026-07-23`

- N: `14`
- BUY / SELL: `8 / 6`
- TP / SL / TIMESTOP: `6 / 8 / 0`
- WR: `42.86%`
- EV raw: `+0.285714R`
- EV net: `+0.235714R`
- Sum net: `+3.300R`
- PF net: `1.393`
- Max DD: `3.300R`
- Unresolved: `0`

Monthly:

- May: N=5, EV net +0.150R, sum +0.750R
- June: N=4, EV net +0.450R, sum +1.800R
- July: N=5, EV net +0.150R, sum +0.750R

Direction:

- BUY: N=8, EV net +0.450R, sum +3.600R
- SELL: N=6, EV net -0.050R, sum -0.300R

SELL remains enabled in the frozen configuration. Removing or tuning it after
inspection is prohibited.

## Deployment state

- `InpBH_Enable=true`: permitted on **demo only**.
- `InpBH_RiskPct=0.30`: keep frozen; do not increase.
- Live: **PROHIBITED** pending one complete forward month and review.
- Preserve all integrated prop-firm portfolio and execution safety gates.

## Next action

Run one controlled demo forward month with lifecycle logging for signal, fill,
spread, slippage, SL/TP and time-stop. Compare forward signals to the frozen
oracle and reopen research if there is material signal or execution drift.

## Primary records

- [Specification](Specs/TZ-BH-OOS-002.md)
- [Report](Reports/BH_OOS_002_v002_Report.md)
- [Decision](Decisions/ADR-BH-OOS-002-PASS.md)
- [Results](Results/BH_OOS_002/v002/README.md)
- [Oracle](Code/Python/BH_OOS_Oracle_v002.py)

## Security finding

The unrelated legacy `Grok_Core_XAU.mq5` contained a plaintext xAI API key.
The key still must be revoked/rotated. `AK47_FT_EA_156.mq5` did not contain an
embedded API credential in the source scan.
