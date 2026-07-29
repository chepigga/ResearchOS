# Grok XAU

ResearchOS project for XAUUSD research, oracle validation, execution modelling and later EA deployment.

## Current research line

`BH_SWEEP` — BeltHold confirmation after a consumed M15 swing sweep/reclaim, filtered by EMA20 reversal context.

## Current canonical state

- Laboratory: `BH_OOS_001`
- Specification: `TZ-BH-OOS-001v2`
- Status: `PREREGISTERED / BLOCKED_DATA_AND_ENGINE`
- No OOS verdict exists yet.
- `InpBH_Enable` must remain `false` until the preregistered OOS gate is completed.

## Source of truth

1. `STATUS.md`
2. `Specs/TZ-BH-OOS-001v2.md`
3. `BACKLOG.md`
4. `RESEARCH_REGISTER.md`

## Data rule

The 2026-05-01..2026-07-23 OOS segment must use the same broker feed as the in-sample research. A cross-feed validation is a different experiment and cannot substitute for this laboratory.
