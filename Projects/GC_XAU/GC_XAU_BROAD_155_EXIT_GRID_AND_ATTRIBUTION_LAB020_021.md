# GC-XAU LAB020/021 — BROAD 155 EXIT GRID + SIGNAL ATTRIBUTION — CORRECTED FINAL

Date: 2026-09-25
Scope: the same 155 CLOSED Broad XAU trades from FTMO report `ReportHistory-1514715065_ftmo(1).xlsx`.

## Correction note
The first draft attempted to use a delayed external GCZ6 M1 snapshot for the whole day. That feed only covered through ~09:09 UTC and therefore could not cover the full 155-signal FTMO interval. Those incomplete proxy results are rejected.

The corrected analysis uses the report's own XAUUSD deal-price execution tape:
- 313 valid XAU deal observations on 2026-09-25
- exact trade entry prices and original SL/risk distance
- future observed deal prices for path reconstruction
- timeout endpoint accepted only when the last observed price is <=120 seconds stale
- original full round-turn commission translated to R and subtracted
- no extra synthetic spread/slippage added

Validation against actual 5-minute trade outcomes:
- all 155 current 5m trades represented
- tape proxy vs actual 5m gross-R correlation ≈ 0.987
- mean absolute error ≈ 0.019R
This is sufficiently close for descriptive hold/TP comparison, but it is still a sparse execution-tape proxy, not a tick-exact backtest.

## Current 155-trade actual ranking
| Method | N | Actual net EV | PF | WR |
|---|---:|---:|---:|---:|
| DOM | 41 | +0.1333R | 1.537 | 63.4% |
| BASE | 54 | +0.0019R | 1.007 | 55.6% |
| MIX | 49 | -0.2091R | 0.492 | 40.8% |
| REV | 11 | -0.4752R | 0.045 | 18.2% |

Leg ranking:
- DOM_CONT: +0.2076R, PF 1.767
- DOM2: +0.0904R, PF 1.385
- BASE1: +0.0019R, PF 1.007
- MIX2: -0.2038R, PF 0.459
- MIXED: -0.2147R, PF 0.521
- REV2: -0.2557R, PF 0.078, N=3
- REV1: -0.5575R, PF 0.039

## Directional precision over the first 5 minutes
Using the report execution tape, last observed direction at +5m:
- DOM: 68.4% correct; mean favorable excursion +0.516R vs adverse 0.359R
- BASE: 55.6% correct; favorable +0.357R vs adverse 0.338R
- MIX: 40.8% correct; favorable +0.311R vs adverse 0.549R
- REV: 27.3% correct; favorable +0.091R vs adverse 0.515R

Leg detail:
- DOM_CONT: ~69.2% correct at +5m; favorable +0.664R vs adverse 0.350R
- DOM2: 68.0%; favorable +0.431R vs adverse 0.363R
- BASE1: 55.6%; favorable +0.357R vs adverse 0.338R
- MIX2: 36.0%; favorable +0.280R vs adverse 0.528R
- MIXED: 45.8%; favorable +0.343R vs adverse 0.571R
- REV1: 25.0%; favorable +0.110R vs adverse 0.583R
- REV2: 33.3%, N=3

Verdict: DOM_CONT is the most directionally precise signal in this forward sample.

## Side asymmetry
| Method | BUY EV | SELL EV |
|---|---:|---:|
| BASE | +0.0033R | +0.0003R |
| DOM | **+0.2144R** | +0.0188R |
| MIX | **-0.2699R** | -0.1281R |
| REV | **-0.5924R** | -0.4082R |

DOM BUY is the strongest side. REV BUY is the weakest.
Do not create a global BUY-only rule from this one day; the asymmetry is method-specific.

## Exit grid — production-relevant cells with TP >= 1.5R
Original stop remains 1R. Only max hold and TP are changed.

### BASE1
- 5m / TP1.5: EV +0.0066R, PF 1.024
- **10m / TP1.5: EV +0.1692R, PF 1.566, N=52, TP hit 9.6%**
- 10m / TP2: EV +0.1479R, PF 1.495
- 15m / TP1.5: EV +0.1069R, PF 1.284
- 30m becomes negative

Interpretation: BASE is primarily an EXIT-TIMING problem. Five minutes is too short; ~10m is materially better in this sample.

### DOM2
- 5m / TP1.5: EV +0.1018R, PF 1.449
- **10m / TP1.5: EV +0.1184R, PF 1.358**
- 15m / TP1.5: +0.0506R
- 30m negative

Interpretation: DOM2 remains good at 5–10m; extending too far degrades it.

### DOM_CONT
- **5m / TP1.5: EV +0.2124R, PF 1.798**
- 10m / TP1.5: +0.0959R
- 15m / TP1.5: -0.0848R
- 30m / TP2: +0.0739R

Interpretation: current ~5m exit is already very effective for DOM_CONT. Longer hold does NOT improve the >=1.5R production geometry.

### MIX2
- 5m / TP1.5: -0.1998R
- 10m / TP1.5: -0.2417R
- 15m / TP2: -0.1612R
- best late rescue: 30m / TP2 ≈ -0.0485R, still negative

Interpretation: MIX2 is mainly an ENTRY/STATE problem, not a 5m-exit problem.

### MIXED
All tested production-relevant cells remain negative.
Best tested >=1.5R cell is still materially negative.

Interpretation: MIXED is an ENTRY/STATE problem.

### REV1
- 5m / TP2: -0.3939R
- 10m / TP2: -0.1194R
- 30m / TP2: -0.0971R

Longer hold reduces the damage but does not create a positive strategy.

### REV2
30m / TP2 = +0.0897R, but N=3 only.
No inference or promotion is allowed from this sample.

## TP reach / profit precision
Diagnostic TP0.5 within 5m (below the user's production R:R rule, used only to measure immediate directional precision):
- DOM: TP0.5 hit 48.8%, EV +0.0408R after commission
- BASE: hit 27.8%, EV -0.0549R
- MIX: hit 32.7%, EV -0.2240R
- REV: hit 0%, EV -0.3562R

Important: MIX can make a short favorable excursion, but adverse excursion is much larger and the strategy remains negative. Therefore “touches some profit” is not equivalent to a precise signal.

## What drives profit in this 155-signal day?
Local price context was measured from the same XAU execution tape before entry.

### BASE — short impulse matters
3m signal-aligned price impulse:
- aligned N=11: EV +0.1335R, PF 1.898
- counter/no alignment N=40: EV -0.0203R, PF 0.934

5m signal-aligned impulse:
- aligned N=15: **EV +0.1655R, PF 1.765**
- counter N=37: **EV -0.0397R, PF 0.863**

60m alignment:
- aligned N=17: +0.1511R, PF 1.931
- counter N=25: -0.1361R, PF 0.664

Interpretation: BASE needs price confirmation. A raw first signal is weak; when XAU is already moving with it, BASE becomes substantially better.

### DOM — slow trend matters more than immediate impulse
3m:
- aligned +0.1094R
- counter +0.1496R

5m:
- aligned +0.0937R
- counter +0.1429R

Both are profitable, so DOM does not require a short-term impulse confirmation.

30m directional alignment:
- aligned N=11: **+0.2604R, PF 1.912**
- counter N=26: +0.0957R, PF 1.403

Interpretation: DOM already contains persistence/order-flow information. A broader trend aligned with DOM strengthens it; forcing a 3–5m impulse filter could delete good trades.

### MIX
MIX loses in both short-impulse states.
30m alignment reduces damage:
- aligned -0.1145R
- counter -0.3983R
but still does not produce positive edge.

Interpretation: trend helps classify MIX quality, but does not rescue raw MIX on this day.

### REV
Very weak and small N.
5m:
- aligned N=6: -0.7135R, 0% WR
- counter N=4: -0.1468R

Interpretation: REV is too early / lacks reversal confirmation in this sample. It needs a separate post-signal confirmation study, not simply a longer timeout.

## Combined conclusion
1. Most accurate current signal: DOM_CONT, then DOM2.
2. BASE is usable only conditionally; its strongest clue is short impulse confirmation and a ~10m hold rather than 5m.
3. DOM profit is linked more to persistence + broader ~30m trend alignment than to a 3–5m price impulse.
4. MIX/MIXED are primarily bad-entry/state problems on 25-Sep.
5. REV is primarily a reversal-timing/confirmation problem.
6. Long-history LAB019 remains important: leg performance is regime dependent. This one forward day does NOT justify permanently deleting MIX/REV or universally preferring DOM.

No Broad Demo or Q65 production rule is changed by this descriptive study.
