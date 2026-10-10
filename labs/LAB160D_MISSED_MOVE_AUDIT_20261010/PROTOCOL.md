# LAB160d — MISSED PRICE MOVE AUDIT
Frozen before audit results, 2026-10-10. Parent LAB160c b6dfec23d683404acce7e17340701b871c860bd6.

Scope: BTC2021–2024; OLD_PROFILE stress7.5bps, risk0.25%, identical LAB155 execution. No new strategy or optimization, no changes to live bot.

Two denominators, never pooled:
1. Reproduce LAB160b fixed nonoverlap UTC6/24/48h windows, dominant excursion>=3 H1ATR and terminal retains>=50%. Include already-open same-side positions; raw entry coverage must match61/877,67/539,70/345. Clock windows are not unique economic moves.
2. Retrospective directional-change close-price legs. Track alternating close extrema; confirm a turn after opposite movement>=1 ATR (ATR known at the current extreme); label legs whose pivot-to-pivot amplitude>=3 ATR measured with start-pivot closed H1 ATR. No overlapping interiors. A fixed2ATR reversal sensitivity is reported separately. Last unconfirmed leg excluded. Pivots are hindsight labels, not executable entry prices.

Gate journal: recover A freshZ1 crossings with trend/extension/OI/phase/SWING3; B3 depth0.5 attack, Z strengthening/OI, terminal-two-step and reclaim; R48 breakout/4-of6 acceptance/2h cooldown/margin/no-retest/OI; EARLY activeZ rescue and episode-age. Verify passed candidate multisets against original506raw records where applicable. Exact old lineage availability/missing-row assumptions retained; this is not a new live data-latency audit.

Movement audit:
- same-direction positions opened before start are included if still active;
- raw signal before peak is not automatically an executed/capturing position;
- infer late confirmation from candidate start before peak and entry after peak, not from any unrelated future signal;
- profile-rejected, portfolio-rejected, passed-before-peak but already-exited, absent raw signal kept distinct;
- partial TP, exits and carried-position mark-to-market accounted with actual replay prices.

Exclusive operational coverage categories: held through peak, overlap but exited before peak, timely eligible raw but portfolio rejected, timely raw profile rejected, late confirmed setup, no timely executable raw signal. Supplementary gate flags may overlap; no single failed gate is called the sole cause when several are false. For gate diagnosis search candidate anchors during the move and up to12h before start (covers confirmation searches), with assessment timestamp<=peak cutoff. Delayed candidates assessed after peak are not available before peak.

Price capture descriptors: best single same-direction trade gross price-point contribution DURING movement divided by movement amplitude; can be negative or>100 in OHLC timing edge cases, never called account return. Whole-account directional net R contribution = sum of mark-to-market changes of same-side trades over the interval, with entry cost charged only if entry falls within interval. No oracle entry P/L or recoverable-profit claim. Report overlap without positive contribution separately. Equity contribution can include open P/L at peak.

Synthetic tests for carried/partial positions and pivot nonoverlap; raw gates and full portfolio replay parity; row-level CSV evidence and mechanically selected examples. Report sensitivity to movement definition and scope. No summing cross-horizon counts; no pristine OOS claim.
