# LAB167 — LIQUIDITY-TO-LIQUIDITY TRADEABILITY ATLAS
Date: 2026-10-10
Status: PREREGISTERED / NOT EXECUTED
Parent: lab/lab166-success-failure-execution-20261010

## Objective
Start from full retrospective BTCUSDT >=3 ATR price-wave census (2680 waves, ~40/month), NOT from Crowd/OI setup candidates. Quantify how many movements provide at least one CAUSALLY tradable liquidity-to-liquidity trade with target distance / structural risk >= 1.5, then count realized fill, TP-first, SL-first, unfilled, timeout, duplicate paths, and monthly frequency.

## Strict separation
A. Retrospective ceiling: only the eventual wave is known post hoc. Count plausible start/end structural liquidity anchors for explanatory anatomy. Do NOT call this a feasible trade.
B. Causal executable opportunity: every anchor, direction, entry and stop can be derived from closed history strictly before submission; never use wave endpoint, hindsight swing or completed future session profile.
Report A and B separately. Never use prospective-wave truth to choose live entry side.

## Data
Use LAB161 canonical M5 OHLCV and 2680 LAB161 wave labels. Last available bar 2026-08-10 21:20 UTC. Confirm wave IDs, timestamp coverage, causal H1 ATR SMA14 (lineage), and missing/gapped forward paths. Liquidation/order-book liquidity is not in dataset; use explicit PRICE-LIQUIDITY PROXIES, not claim real order liquidity.
No crowd, OI or profile-shape gate in primary experiment. Profile POC/VAH/VAL may be targets only when computed from previously closed M5 bars; label as candle-volume proxy.

## Liquidity proxies, preregister
1. Previous confirmed H1 swing high/low: 2 closed bars on either side, known only after confirmation.
2. Previous completed UTC day high/low (PDH/PDL).
3. Last 24h prior closed M5 high/low.
4. Causal anchored range high/low / POC only from detected range known before candidate bar.
Deduplicate targets within 0.1 x closed H1 ATR; choose FIRST valid opposing liquidity obstacle along proposed trade path, not furthest after the fact. Exclude targets already touched before entry. Require >0 target distance.

## Three nonoverlapping regimes
CONT: confirmed H1 trend with price-side direction and pullback reclaim; reversal and range cannot claim same signal.
REV: sweep of a prior liquidity level plus close back through it, and invalidation past sweep extreme.
RANGE: known balanced range, failed excursion/acceptance or return to range with first opposing structural node as target.
Regime labels must be determined only at signal timestamp. Compare against alternate neutral baseline to expose sensitivity; do not classify regime using future wave peak.

## Entries
E0 next M5 open after causal trigger.
E1 next completed M5 confirmation + next open.
E2 passive retest of frozen level within 60min (no market fallback).
Record candidate/fill/TTL; no same-bar fill-to-TP assumption; SL-first on OHLC ambiguity; gap handling; overlap max two positions and one new entry per same route until invalidation.
No optimizations of trigger thresholds based on CHECK.

## Stop and TP
Structural SL beyond swing/sweep/range edge with 0.1 H1 ATR buffer.
TP at nearest causal opposing liquidity node (not fixed ATR profit goal).
Reject RR <1.5 or nonpositive; show 1.5, 2 and 3 threshold categories. SL always smaller than TP. Full TP no partials in primary experiment.
24h hard maximum hold; report open positions at 24h and never count them as TP.
Costs: report 0bps, 5bps, 7.5bps and 10bps roundtrip sensitivities explicitly as hypothetical; mark execution transfer to broker as unverified. Bid/ask tick-based broker validation required before deployment.

## Splits and audit
Development 2021-2023; validation 2024; check 2025-2026-08-10 with no threshold retune. These dates are already reused, NOT pristine OOS.
Per year and month: waves, candidate routes, RR>=1.5 routes, filled routes, distinct covered waves, entry count, win%, EV R, PF, max drawdown (including floating), trade duration and missed opportunity taxonomy. Cluster uncertainty by weekly blocks.
No unobserved bar can become success; maintain no future leakage fixtures; same-bar SL/TP ambiguity conservative.
Compare continuation/reversal/range both on same eligible M5 history and without double counting wave coverage.

## Status / unblock
GitHub connector can read text files but cannot deliver GitHub release binary BTC btc_5m.zip to current computation container; local network DNS blocked. Existing LAB164 185 CHECK stage signals and 145 geometry-valid RR>=1.5 stage cases DO NOT answer 2680-wave population question. No new LAB167 numerical result has been produced. Need machine with release archive and dependencies to execute scripts, or attach raw file to conversation.
Production EA untouched.
