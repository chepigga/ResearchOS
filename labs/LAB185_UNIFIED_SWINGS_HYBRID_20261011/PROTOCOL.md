# LAB185 — UNIFIED SWING × HYBRID SIGNAL × WAVE PARITY
Status: PRE-REGISTERED SPEC, NOT RESULTS. 2026-10-11.

## Causal pivot definition
H4/H1/M15 swing high/low: strict high exceeds highs of 2 closed bars to left and 2 closed bars to right; strict low below lows. Confirm at CLOSE of second right bar, not at pivot. No swing valid before confirmation. Swing amplitude >=1.0 * ATR14 of same timeframe from previous confirmed opposite swing; ATR sampled from CLOSED bars at confirmation, without future reads; freeze prev opposite swing before candidate. Tie handling: reject ties to avoid ambiguous order. A superseded unconfirmed pivot cannot emit signals. Maintain time fields pivot_time and confirm_time.

## Hypothesized hybrid sequence
H4 last confirmed BOS of frozen confirmed swing in trade direction as ALIGNED context. ALSO independently retain H4_TRANSITION (no aligned BOS yet), to preserve early reversals, but segregate outcome.
H1 liquidity sweep of already-confirmed swing followed by M5/H1 close reclaim depending configured signal rule, timestamped only at completion. Sell sweeps high, buy sweeps low.
M15 either newly confirmed 2L2R swing or causal ZigZag reversing >=1.0 * most recently CLOSED ATR(H1), direction matches H1 reclaim; record separate modalities and overlap.
M5 entry next bar open after retest of reclaim level or closed-bar micro BOS (compare separate execution modes; do not allow entry at signal bar low/high); structural SL beyond known sweep wick plus buffer (freeze 0.1 ATR(H1) for research); target first *ahead of entry* unconsumed confirmed H1 liquidity proxy, RR >=1.5. Same friction/fill model for all methods. For research, NO production code until broker rules confirmed.

## Shared fair comparison
Same candidate timestamp and level inventory for ZigZag and Market Structure; same H4/H1 logic, H1 target, structural SL, M5 fill timing, RR, episode collapse by origin-zone/destination-zone pair, no orphan future pivot target. Compare (i) Market Structure swing confirm/BOS/CHOCH, (ii) causal ZigZag, (iii) hybrid. Preregister no optimization.

## Reference wave definitions
Canonical LAB161 2680 baseline immutable. LAB169 independent 2754 remains secondary parity reference. NEW independent 2.5 ATR(H1) confirmed-swing waves are third *diagnostic* universe, never used to filter live signals. Wave overlap >=70% simultaneously time and price, specify overlap over reference interval in each dimension and one-to-one assignment to prevent double counting. Only retrospective audit uses oracle endpoints; no future lookahead into detector.

## Outcomes requested
Number of raw signals, independent liquidity routes/month BUY/SELL, coverage of each frozen wave universe, earliest confirmation and M5 filled entry delays, remaining *price* amplitude at confirmation (posthoc diagnostic), RR>=1.5; next first-TP versus SL conservative replay as separate downstream phase. Price-only baseline; Crowd/OI/volume profile withheld.
