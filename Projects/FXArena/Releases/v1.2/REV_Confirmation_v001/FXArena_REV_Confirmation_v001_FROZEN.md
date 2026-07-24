# REV_Confirmation v001 — FROZEN execution note

Source specification: `FXArena_REV_Confirmation_TZ_v001_2026-07-24.md`, frozen before execution.

Production funnel used in this run:
- `ACCEPTANCE_CONFIRMED`, observable after M5 close.
- `max_penetration_seen@D3 <= 1.0 ATR`, reconstructed only from M1 bars `[episode_start, D3)`.
- REV direction is opposite level/attack side.
- Entry is the first M1 open after acceptance becomes observable.
- D3 invalidation: `level + attack_side * (d3_peak + 0.05 ATR)`; risk floor `0.75 ATR`.
- TP 2R; SL 1R; TIME240 = -1R; same-M1 tie = SL.
- Actual minute spread via bid/ask; commission 6 points RT.
- One signal per D3: smallest causal D3 penetration, then smallest episode_id.
- One executed episode per level per 7 days; no simultaneous REV positions.
- Threshold 0.75 is diagnostic only.
- RC1 FAIL stops RC2-RC6 and declares F11.
