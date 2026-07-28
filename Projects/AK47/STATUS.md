# AK47 Status

**Updated:** 2026-07-29

## Canonical environment

- Symbol: XAUUSD
- Target: FTMO-style 100K prop account
- Risk intent: 0.25–0.50% per trade
- Test mode: MT5 real ticks where final replication is required
- Research mode: Python replay on canonical M1 Bid/Ask and lifecycle exports

## Established findings

- Original MorrisCandle/BeltHold line showed aggregate promise but strong regime dependence.
- M3 adaptive giveback materially changes the complete trade path and cannot be treated as a minor exit overlay.
- Immediate post-M3 re-entry is caused by `no position -> OCO allowed`; the EA lacks a causal market-state permission layer.
- Fixed cooldown, directional lock, structural reset and fresh-H1-bar rearm are NO-GO.
- Simple directional post-close proxies are NO-GO.
- The 2026 auction-rhythm profile passed internal statistics but failed sealed 2022–2025 replay.

## Latest sealed result

Frozen rule:

`0.50 < pre30_alternation <= 4/7`

2022–2025 replay:

- WATCH N=28
- EV=-0.175R
- PF=0.69
- permutation p=0.649
- verdict: NO-GO

## Active research direction

1. Causal M3 exit analysis on identical entry sequences.
2. Full-entry-universe taxonomy instead of post-M3-only filtering.
3. RS001 per-direction lookback calibration.
4. XAU regime-break explanation across 2022–2026.

## Current production status

No new post-M3 filter is approved for EA integration. Existing positive exploratory profiles remain research-only until independent OOS replication.
