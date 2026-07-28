# AK47 Falsification Log

This file prevents rejected hypotheses from being rediscovered and retuned on the same data.

## Post-M3 cooldown family

### Fixed cooldown

Verdict: NO-GO. Time elapsed did not identify a new market state and changed the entire future OCO path.

### Directional lock

Verdict: NO-GO. Same-direction and opposite-direction re-entries could both be negative.

### Structural reset

Verdict: NO-GO. Opposite EpisodeHigh/EpisodeLow close caused excessive blocking and trade-count collapse.

### Fresh H1 bar rearm

Verdict: NO-GO.

Result:

- Trades 326
- Net Profit -$964.84
- PF 0.983
- Expected Payoff -$2.96
- Max Equity DD 7.21%

Baseline M3:

- Trades 364
- Net Profit +$4,664.50
- PF 1.091
- Max Equity DD 6.54%

## Directional regime proxy family

### D1 EMA bias at exit

Verdict: NO-GO. The real-time proxy reversed the sign of the hindsight association.

### Pre-exit five-bar momentum

Verdict: NO-GO on the full dataset. Aggregate effect was approximately zero and unstable by year.

## Auction-rhythm family

Frozen rule:

`0.50 < pre30_alternation <= 4/7`

2026 internal validation:

- N=36
- EV=+0.529R
- PF=2.42

Sealed 2022–2025 replay:

- N=28
- EV=-0.175R
- PF=0.69
- permutation p=0.649

Verdict: NO-GO. Do not optimise neighbouring thresholds on the same history.

## Governance rule

A failed OOS hypothesis may only be reopened after a qualitatively new mechanism, new independent data, and a new preregistration.
