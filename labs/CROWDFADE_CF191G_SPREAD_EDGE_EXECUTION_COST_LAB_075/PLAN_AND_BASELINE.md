# LAB075 — SPREAD × EDGE / EXECUTION COST

Status: STARTED
Parent: LAB074 `CROWDFADE_CF191G_MARKET_VS_CONFIRM_POSITIVE_SKEW_LAB_074`
Parent commit: `fc393029d3fa0d7dc842501db129c0ea0d7c30ed`
Canonical trade population: LAB074 `output/trades.csv`

## Frozen components

Do NOT retune signal logic, confirmation logic, or positive-skew management in this lab.
The purpose is execution-cost robustness only.

## LAB074 baseline

### Historical

| cost model | mode | N | EV_R | PF | SumR | MaxDD_R |
|---|---|---:|---:|---:|---:|---:|
| GROSS | MARKET_RAW | 5405 | +0.139469 | 1.24489 | +753.832 | 26.808 |
| GROSS | CONFIRM_CANONICAL | 5297 | +0.144791 | 1.25045 | +766.959 | 31.123 |
| IC | MARKET_RAW | 5405 | +0.110208 | 1.18815 | +595.675 | 32.092 |
| IC | CONFIRM_CANONICAL | 5299 | +0.107665 | 1.18073 | +570.517 | 36.176 |
| GETLEVERAGED | MARKET_RAW | 5405 | +0.039417 | 1.06489 | +213.051 | 79.735 |
| GETLEVERAGED | CONFIRM_CANONICAL | 5297 | +0.062911 | 1.10333 | +333.239 | 56.261 |

### Forward 2026

| cost model | mode | N | EV_R | PF | SumR | MaxDD_R |
|---|---|---:|---:|---:|---:|---:|
| GROSS | MARKET_RAW | 552 | -0.022748 | 0.96433 | -12.557 | 49.811 |
| GROSS | CONFIRM_CANONICAL | 544 | +0.081590 | 1.13413 | +44.385 | 25.723 |
| IC | MARKET_RAW | 552 | -0.053066 | 0.91931 | -29.293 | 64.110 |
| IC | CONFIRM_CANONICAL | 544 | +0.058043 | 1.09268 | +31.575 | 28.869 |
| GETLEVERAGED | MARKET_RAW | 552 | -0.063668 | 0.90278 | -35.145 | 64.260 |
| GETLEVERAGED | CONFIRM_CANONICAL | 544 | -0.006775 | 0.98959 | -3.686 | 46.275 |

## Immediate inference to test

LAB074 indicates that confirmation is not simply an entry-quality improvement in-sample: under historical IC it is approximately flat/slightly worse than MARKET_RAW in EV. Its important effect appears in forward 2026, where it changes IC from negative to positive EV and materially reduces drawdown. Under GETLEVERAGED it improves forward EV substantially but does not quite clear break-even.

This makes execution cost / spread a plausible boundary variable rather than a secondary nuisance variable.

## LAB075 questions

1. What is the break-even all-in execution cost for `CONFIRM_CANONICAL` and `MARKET_RAW`?
2. Does confirmation have a higher cost tolerance in forward 2026?
3. At what spread/cost bucket does EV cross zero for each mode?
4. Is the cost sensitivity stable by historical year and 2026 month?
5. Does high spread merely subtract approximately constant R, or is it associated with structurally worse trade paths / stops?
6. Can a causal max-spread gate improve forward EV and DD without destroying trade count?

## Required outputs

- cost bucket × mode: N, WR, EV_R, PF, SumR, MaxDD_R
- historical years and forward-2026 months separately
- break-even cost estimate in R/trade
- sensitivity curve for incremental execution cost
- causal spread-gate sweep only after the descriptive cost analysis
- retained-trade percentage for every proposed gate
- promotion decision must require forward robustness, not historical optimization

## Guardrails

- TP remains >= 1.5R.
- No signal retuning.
- No management retuning.
- No choosing a threshold solely on aggregate historical optimum.
- Any spread threshold proposed for production must survive forward 2026 and broker-cost comparison.

## Current status

LAB075 scaffold committed. Next computation should consume the canonical LAB074 trade population and recover the per-trade execution-cost/spread fields used by LAB074. If those fields are not present in `trades.csv`, recover the exact LAB074 cost-model implementation before running a spread-gate sweep; do not invent a spread proxy.
