# LAB014 — MONO_CONTINUATION_CAUSAL_EDGE

Date: 2026-09-23
Status: NO_PRODUCTION_CANDIDATE / WATCHLIST_ONLY

Historical source:
- GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005_EVENTS.csv
- 15,206 unique MARKET_NOW base signals
- 5,341 anchored episodes
- 1,973 ultimate MONO episodes

## Causal prefix clocks — exact LAB005 FTMO XAU tick outcomes

| Clock | TRAIN N | TRAIN Hold300 EV | VALID N | VALID Hold300 EV | POST N | POST Hold300 EV | FULL EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| MONO1 | 1752 | -0.292 ATR | 2279 | -0.171 | 1310 | -0.250 | -0.230 |
| MONO2 | 809 | -0.305 | 1125 | -0.171 | 664 | -0.168 | -0.212 |
| MONO3 | 327 | -0.422 | 408 | -0.151 | 232 | -0.076 | -0.225 |
| MONO4 | 87 | -0.221 | 74 | -0.154 | 63 | -0.219 | -0.198 |
| MONO5 | 9 | +0.828 | 4 | +0.397 | 5 | +1.293 | +0.861 |

MONO1–4 fail. MONO5 is interesting but N=18 total and is not actionable.

## Episode-finalization clock

Clock is causal: wait until anchor + 300s, confirm all episode signals are same-direction, then measure continuation.

External XAUUSD 1-minute bars:
- 1,919 MONO episodes with complete follow-up

| Period | N | +5m EV / PF | +15m EV / PF | +30m EV / PF |
|---|---:|---:|---:|---:|
| TRAIN | 610 | -0.015 / 0.98 | -0.019 / 0.98 | +0.153 / 1.09 |
| VALID | 842 | -0.003 / 1.00 | -0.032 / 0.97 | +0.058 / 1.04 |
| POST_CHECK | 467 | +0.089 / 1.15 | +0.235 / 1.22 | +0.330 / 1.23 |
| FULL | 1919 | +0.016 / 1.02 | +0.037 / 1.03 | +0.155 / 1.10 |

Generic MONO continuation is too weak.

## N=3 watchlist

Exactly 3 signals in a completed MONO episode is the only signal-count family with positive gross +30m continuation in TRAIN / VALID / POST.

Approximate gross:
- TRAIN +0.297 ATR
- VALID +0.148 ATR
- POST +0.268 ATR

But cost sensitivity kills robustness.

### Cost sensitivity — N=3, 30m

Commission: 0.0007% notional per side.

| Assumed spread | TRAIN EV/PF | VALID EV/PF | POST EV/PF | FULL EV/PF |
|---|---:|---:|---:|---:|
| 0.0 + commission | +0.260 / 1.18 | +0.095 / 1.06 | +0.232 / 1.16 | +0.178 / 1.12 |
| 0.2 + commission | +0.139 / 1.10 | -0.009 / 0.99 | +0.114 / 1.08 | +0.065 / 1.04 |
| 0.4 + commission | +0.018 / 1.01 | -0.113 / 0.93 | -0.004 / 1.00 | -0.047 / 0.97 |
| 0.6 + commission | -0.103 / 0.93 | -0.217 / 0.87 | -0.123 / 0.92 | -0.160 / 0.90 |

## Verdict

LAB014 FAILS as a production strategy.

- Do not add generic MONO continuation to executor.
- Do not weaken frozen Q65 because of LAB013.
- MONO5 remains watchlist only due tiny N.
- N=3 / 30m is cost-sensitive and not robust enough.
- LAB013's 23.09 result was real but regime-specific.

Next:
1. LAB015 MONO long-history replication (2025-01-01 → 2026-09-15)
2. LAB016 volume / spacing mechanism from raw AMP ticks
3. LAB017 exact FTMO execution only if longer-history gate survives
4. Shadow-only MONO live logger; no MONO orders.
