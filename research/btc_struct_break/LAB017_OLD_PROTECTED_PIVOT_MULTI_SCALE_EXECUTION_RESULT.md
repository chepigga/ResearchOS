# OLD_PROTECTED_PIVOT_MULTI_SCALE_EXECUTION_LAB_017

**Date:** 2026-08-25  
**Status:** COMPLETED  
**Preregistration commit:** `5e763fb03d19fa9ee7237f7ff6ed09eb53151d11`  
**Formal verdict:** `M15_EXECUTION_SCALE_IS_PART_OF_SIGNAL__M5_EXPANSION_REJECTED`

## Main result

| Branch | DEV N | DEV EV | VAL N | VAL EV | VAL PF | VAL MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| A: M15→M15 control | 37 | +0.494R | 34 | +0.293R | 1.80 | 4.36R |
| B: M15 pivot → M5 execution | 307 | +0.037R | 361 | -0.006R | 0.99 | 28.95R |
| C: M5 pivot age>=66 | 0 | — | 0 | — | — | — |
| C2: M5 pivot age>=22 | 534 | -0.095R | 518 | -0.047R | 0.91 | 34.67R |

Primary Branch B increased VAL frequency from 11.3/year to 120.3/year (10.6x), but expectancy collapsed from +0.293R to -0.006R and PF from 1.80 to 0.99.

## VAL yearly — M15 control
- 2023: N=10, EV +0.330R
- 2024: N=7, EV +0.169R
- 2025: N=17, EV +0.322R

At 1.5x modeled cost, control remains EV +0.263R, PF 1.68.

## VAL yearly — M15 context + M5 execution
- 2023: N=114, EV -0.097R
- 2024: N=117, EV -0.127R
- 2025: N=130, EV +0.182R

Only 1/3 VAL years positive. At 1.5x cost EV = -0.036R.

BUY diagnostic: N=195, EV +0.025R, PF 1.04.  
SELL diagnostic: N=166, EV -0.043R, PF 0.92.

## Fully M5
Scale-preserving age>=66 M5 bars produced zero qualifying entries. Secondary age>=22 M5 bars produced many trades but was negative in all 3 VAL years; pooled VAL EV -0.047R, PF 0.91.

## Interpretation
The original 71-trade lineage is not merely under-sampled because M15 execution is coarse. M5 creates many micro-breaks inside the same broad old-pivot context, but these are mostly noise.

The positive setup appears to require both:
1. old protected pivot / large structural distance;
2. a meaningful M15-level break/retest event.

The M15 break is therefore part of the signal, not just execution timing.

## Decision
Keep the frozen M15 lineage:
- riskATR >3.72
- protected pivot age >=22 M15 bars
- canonical M15 structural break/retest

Reject broad M15-context→M5 expansion and fully M5 reinterpretations.

If more frequency is needed, prefer horizontal expansion (other independent markets / venues / structural event families) rather than weakening the M15 event.