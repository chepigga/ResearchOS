# RAW_CHRIS_GC_NATIVE_EXECUTION_COST_ROBUSTNESS_LAB013

**Status:** `GC_NATIVE_EDGE_SURVIVES_LOW_FRICTION_BUT_SL1_TP2_NOT_COST_ROBUST_AT_2PLUS_TICKS`

## Purpose

Test whether the frozen RAW Chris/AEIF SHORT mechanism is genuinely GC-native after the failed GC→XAU transfer. No signal retuning.

## Frozen inputs

- 234 RAW Chris events from LAB010.
- Native instrument: COMEX GC futures.
- Actual directional GC Last-tick first-passage.
- SHORT; SL 1.0 seed ATR; TP 2.0 seed ATR; max hold 30m.
- No selector/session/score/entry-delay changes.
- GC tick = 0.10 price points = $10/contract.
- Historical Bid/Ask is unavailable in the compact feed, so friction is modeled as total round-turn tick cost stress.

## SL1 / TP2 / 30m

| Total RT friction | EV | PF | SumR | MaxDD | P(EV>0) |
|---:|---:|---:|---:|---:|---:|
| 0.0 tick | +0.178R | 1.297 | +41.57R | 10.34R | 97.1% |
| 0.5 tick | +0.135R | 1.217 | +31.58R | 11.28R | 92.6% |
| 1.0 tick | +0.092R | 1.143 | +21.59R | 12.23R | 83.9% |
| 2.0 ticks | +0.0069R | 1.010 | +1.61R | 14.13R | 52.7% |
| 3.0 ticks | -0.078R | 0.894 | -18.37R | 19.48R | 20.0% |
| 4.0 ticks | -0.164R | 0.791 | -38.35R | 38.84R | 4.1% |

Gross WR 40.2%; max negative streak 8.

### Year stability

Gross: 2025 +0.222R; 2026 +0.124R.

At 1 tick RT: 2025 +0.111R; 2026 +0.069R.

At 2 ticks RT: 2025 +0.0002R; 2026 +0.0149R.

## Break-even friction

Mean one-tick cost on this ATR distribution is ~0.0854R.

Implied break-even total round-turn friction for SL1/TP2 is **~2.08 GC ticks**, about **$20.81/contract RT**. This is the strategy friction budget, not an estimate of AMP's actual fee.

## Window robustness

Positive EV in 5/9 quality windows, gross and under 1-2 tick stress. Therefore the fixed SL1/TP2 wrapper is not uniformly regime-independent.

## Raw 30m directional edge

The no-stop 30m path is materially thicker than SL1/TP2 on the LAB010 ledger:

- gross ~+0.47 ATR
- 1 tick RT ~+0.38 ATR
- 2 ticks ~+0.30 ATR
- 3 ticks ~+0.21 ATR
- 4 ticks ~+0.13 ATR

Implied break-even friction is ~5.5 ticks RT.

## Decision

1. Evidence supports Chris as substantially **GC-native**, not a universal XAU directional signal.
2. Raw GC delayed-resolution survives low/moderate cost stress.
3. SL1/TP2 is cost-fragile and effectively exhausted around 2 ticks RT.
4. Do not declare SL1/TP2 production-ready.
5. Next research should preserve delayed winners via causal dynamic-failure/wider-path execution rather than tightening the stop.
6. Before live GC execution, insert exact AMP all-in commission/routing fees and measured live slippage.

**Research conclusion:** `CHRIS_IS_LIKELY_GC_NATIVE; RAW_EDGE_SURVIVES; SL1_TP2_IS_COST_FRAGILE`.
