# AK47 H1 M3 — Episode Boundary Backlog

**Date:** 2026-07-28

## Confirmed issue

After `M3_GIVEBACK_EXIT`, the EA often triggers a new OCO before a genuinely independent H1 setup has formed.

Episode Boundary Lab integrity:

- 119 M3 episodes;
- 119 next entries;
- 119 next-trade outcomes;
- 828 H1-state observations;
- 91 continuation-close events;
- 77 full-continuation events;
- 26 failure-boundary events.

Critical descriptive split:

| Group | N | Avg P/L | Total P/L | Win Rate |
|---|---:|---:|---:|---:|
| Entry before any new H1 close | 81 | -$32.25 | -$2,612.28 | 35.8% |
| Entry after at least one H1 close | 38 | +$20.45 | +$776.97 | 52.6% |

Important correction: this split was association, not causal proof that waiting creates edge.

## Rejected hypotheses

### One-hour episode lock

**NO-GO** — changed OCO path and did not restore expectancy.

### Directional episode lock

**NO-GO** — both same- and opposite-direction re-entry could be negative.

### Structural reset

**NO-GO** — opposite structural close could fail to occur for weeks or months; trade count collapsed.

### Failure boundary

Only three observations before the next entry; average result approximately -$153.78.

**REJECTED / insufficient and negative.**

### Continuation close

- N=14;
- average approximately -$174.28;
- total approximately -$2,439.90.

**NO-GO.**

### Full continuation

Overall:

- N=23;
- average approximately +$58.07.

Split:

- same direction: N=16, average approximately -$31.04;
- opposite direction: N=7, average approximately +$261.74.

Same-direction continuation is rejected. Opposite direction remains research-only because N=7 and may be outlier-driven.

## Fresh-bar re-arm experiment

Rule:

1. cancel pending after M3 exit;
2. consume current H1 bar;
3. wait for one complete fresh H1 bar;
4. create OCO from that bar.

Technical state machine passed, but performance failed:

- 326 trades;
- Net -$964.84;
- PF 0.983;
- Expected Payoff -$2.96;
- Max Equity DD 7.21%;
- Win Rate 45.71%.

Baseline M3:

- 364 trades;
- Net +$4,664.50;
- PF 1.091;
- Max Equity DD 6.54%.

**Final verdict: NO-GO.**

## Main lesson

The problem cannot be solved by elapsed time, a fixed number of bars, direction locks, or a simple structural boundary.

The naturally delayed-entry group represented a different market regime. It was not evidence that the delay itself caused better performance.

## Closed branch

Do not continue optimising:

- cooldown duration;
- number of bars to wait;
- same/opposite direction locks;
- simple continuation/failure boundary.

## Next use of this research

Episode-boundary results should feed a broader volatility/auction-state lab. Future work must determine whether the market is expansion-ready, balanced, compressed, exhausted, or unstable before testing direction.
