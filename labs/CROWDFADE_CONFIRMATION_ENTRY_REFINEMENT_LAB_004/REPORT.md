# CROWDFADE_CONFIRMATION_ENTRY_REFINEMENT_LAB_004 — RESULT

## Status
**FAIL under the explicitly tested ATR-pause semantics.**

No fresh OOS was consumed. Data are the already-used BTCUSDT 1-second + flow history, Mar-Aug 2026.

Frozen test defaults:
- ZThreshold 2.50
- ConfirmATR 0.50
- StopATR 1.50
- ExitZ 0.75
- PauseMode ATR
- PauseATR 1.00
- MaxTradesPerDay 3
- TTL 3h; Hold 6h
- BE 0.50 -> +0.15 ATR
- Trail arm 2.50 / distance 0.50 ATR

Important implementation note: because live `InpPauseMode=ATR` semantics were not available in the research source, this LAB explicitly interpreted it as: after a closed trade, next entry is permitted only after absolute price displacement from the prior entry is >= 1.0 frozen ATR. Daily cap counts executed entries by UTC day. This result must not be treated as exact EA parity until that semantic is confirmed.

## Timing ablation

| Mode | N | WR | EV | PF | SumR | MaxDD | Stop rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| A0 immediate confirm touch | 455 | 65.49% | **-0.0965R** | 0.708 | -43.92R | 48.29R | 86.15% |
| A1 confirm M5 close | 390 | 63.59% | **-0.1067R** | 0.694 | -41.62R | 45.29R | 85.90% |
| A2 next M5 close | 367 | 68.66% | **-0.0624R** | 0.791 | -22.91R | 25.80R | 86.38% |

A2 materially reduced loss and DD versus A0, but did **not** reduce stop rate and remained negative. Only Mar, Jun, Jul were positive (3/6 months), so it fails the preregistered timing gate.

A0 diagnostics: 941 signals blocked by max-3/day and 744 blocked by the tested ATR-pause rule. This means the new defaults substantially change event selection versus LAB002 and make exact pause parity critical.

## Anti-impulse

No timing candidate passed, so the preregistered selector retained A0 for veto testing.

Best observed veto among inspected grid was approximately:
- 4 completed M5 bars / 1.25 ATR
- N = 435
- WR = 64.83%
- EV = **-0.0774R**

This is an improvement of about +0.0191R/trade over A0 but remains negative and is just below the predeclared +0.02R EV improvement threshold. It therefore does not rescue the system.

## Decision

1. Do not promote M5-close delay or anti-impulse into live CrowdFade from this LAB.
2. Do not proceed to exit tuning on top of this exact research state until `InpPauseMode=ATR` is matched to the actual EA semantics.
3. Once pause parity is confirmed, rerun the same frozen LAB004 without changing Z/Confirm/Stop/ExitZ/trade cap.
4. If parity replay remains negative, the updated defaults themselves need a baseline audit before further entry optimization.

Live allocation remains 0%. No live CrowdFade code changed.
