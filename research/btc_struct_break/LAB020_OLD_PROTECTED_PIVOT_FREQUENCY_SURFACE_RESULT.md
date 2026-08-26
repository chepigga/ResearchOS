# LAB020 — OLD_PROTECTED_PIVOT_FREQUENCY_SURFACE result

Date: 2026-08-26
Prereg: a5c3cad6f62949568eb5171f6af00427858f28f9
Verdict: NO_NEIGHBORING_PLATEAU__CORE_CONTEXT_IS_STRUCTURALLY_NARROW

## Main result
The low frequency is not caused by a shortage of M15 events. It is caused by the rarity of the old-protected-pivot structural state.

### BREAK_RETEST VAL
- all canonical trades: 698
- unviolated pivot: 658
- age>=22: 74
- riskATR>3.72: 67
- frozen core intersection: 34
- core EV +0.293R, PF 1.80

Broadening to age>=16/riskATR>3.72:
- N53, EV +0.151R, PF 1.34
- but the 19 newly added trades have EV -0.102R.

Broadening to age>=22/riskATR>3.0:
- N45, EV +0.176R, PF 1.42
- the 11 newly added trades have EV -0.187R.

Therefore no neighboring plateau exists; the old core carries the broader rules.

### COMPRESSION_RELEASE SELL VAL
- raw releases: 2,154
- retest <=8 bars: 1,808
- correct latest pivot stop: 1,789
- age>=22: 187
- unviolated: 179
- age>=22 + unviolated + riskATR>3.72 independent candidates: 112
- historical pooled-family final SELL trades: 60
- core EV +0.109R, PF 1.24

Broadening to age>=16/riskATR>3.72:
- N99, EV -0.030R, PF 0.94
- 45 extra trades EV -0.038R
- 6 core trades displaced; those displaced trades average +1.307R.

Broadening to age>=22/riskATR>3.0:
- N73, EV +0.032R, PF 1.07
- 14 extra trades EV -0.374R.

No compression neighboring plateau.

## Important execution-state discovery
The positive historical COMPRESSION SELL seed was generated inside the pooled BUY+SELL compression family state.

If implemented naively as SELL-only:
- frequency rises from N60 to N83 in VAL
- EV collapses from +0.109R to -0.027R.

The extra SELL trades admitted without opposite-side blockers:
- N25
- EV -0.396R
- PF 0.31.

Therefore the pooled family / virtual opposite-side blocker is part of the causal engine state and must be preserved in any EA parity implementation.

## Disjoint watch cell
One preregistered surface cell is interesting but is NOT a plateau or promoted rule:

COMPRESSION SELL, pivot age 16–21, riskATR 2.5–3.0:
- DEV N42, EV +0.380R, PF 1.91
- VAL N26, EV +0.328R, PF 2.20
- 2023 positive, 2024 negative, 2025 positive
- 1.5x cost VAL EV +0.298R
- bootstrap CI crosses zero and no multiple-comparison support.

Status: DISJOINT_ISLAND_WATCH_NOT_PLATEAU.

## Portfolio implication
Current frozen two-engine portfolio:
- 29 trades/year
- EV +0.214R
- PF 1.53
- MaxDD 4.30R.

Loosen BREAK only to age>=16/riskATR>3.72:
- 34.3 trades/year
- EV +0.151R
- PF 1.35
- MaxDD 8.60R.

Loosen both engines to age>=16/riskATR>3.72:
- 45 trades/year
- EV +0.094R
- PF 1.20
- MaxDD 8.25R.

Conclusion: frequency must come from independent structural context/event families, not weakening the frozen old-pivot core.