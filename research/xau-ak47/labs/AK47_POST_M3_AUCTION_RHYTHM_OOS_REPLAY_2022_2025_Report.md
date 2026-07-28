# AK47_POST_M3_AUCTION_RHYTHM_OOS_REPLAY_2022_2025

**Frozen rule:** `0.50 < pre30_alternation <= 4/7`  
**Replay period:** 2022-06-01 to 2025-12-31  
**Status:** sealed historical OOS replay  
**Verdict:** **NO-GO**

## Parity basis
The same Python engine produced 365 trades and 118 M3 exits on 2026 versus the MT5 canonical 364 trades and 119 M3 exits. The one-event discrepancy is accepted as minute-bar execution approximation.

## OOS result
- Total replay trades: **316**
- M3 exits: **95**
- Post-M3 next entries: **94**
- WATCH matches: **28**
- WATCH EV: **-0.175R**
- WATCH PF: **0.69**
- WATCH WR: **42.9%**
- WATCH Sum: **-4.91R**
- OTHER EV: **-0.057R**
- Delta EV: **-0.118R**

## Statistical validation
- One-sided permutation p-value: **0.64932**
- Bootstrap 95% delta CI: **[-0.629, +0.413]R**

## Year splits
- 2022: no WATCH matches in the available June-December segment.
- 2023 WATCH: N=1, EV=+0.592R.
- 2024 WATCH: N=9, EV=-0.070R.
- 2025 WATCH: N=18, EV=-0.270R.

## Interpretation
The auction-rhythm WATCH profile did not survive independent historical replay. The positive 2026 result is regime-specific or sample-specific and must not be promoted into the EA. The threshold is closed as NO-GO unless a new structural hypothesis explains the 2026-only behaviour.
