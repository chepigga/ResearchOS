# LAB182 — ZigZag threshold × wave parity × entry timing
BTC M5 589793 bars, 2021–2026-08-10. First pass, no PnL.

Using frozen LAB181 context-aligned RR>=1.5 ZigZag setups, post-hoc match confirmations by time/side to LAB169 **2754** hindsight waves; wave labels never enter signal.

|Struct/Signal/Exec|k 0.5|k 1.5|k 3.0|
|--|--:|--:|--:|
|M30/M15/M5|206|34|7|
|H1/M15/M5|658|57|31|
|H4/H1/M15|158|28|22|

H1/M15/M5 at k0.5: 5602 RR>=1.5 candidates, 794 aligned events in 658 unique waves (23.89%), median earliest signal 42.07% of wave elapsed time, 232/658 in first quarter, 373/658 first half. k1.5 only 57 waves (2.07%), conditional earliest median 16.67% wave elapsed. These are geometric routes not outcomes.

Normalization to **last closed H1 ATR**: k0.5 M15 nominal threshold median 0.232 H1 ATR, k1.5=>0.681, k3=>1.298. Actual move at confirmation medians 0.452 /0.859 /1.492 H1 ATR. H1 k3 actual median 3.387 H1 ATR. Equal k across TF not equal physical amplitude. Median post-hoc equivalence is not rerunning identical common H1 absolute-distance thresholds.

Caveats: independently labeled 2754 LAB169 waves not canonical LAB161 2680; superficial ~31 H1 k3 confirmations/month vs ~40 waves/month does not establish identical swings. No price amplitude capture analysis yet, no unique route identity dedup, real fill/cost/TP before SL audit. Existing LAB181 pivots have possible same-bar extreme confirmation ambiguity. Results do not justify EA promotion.

Next LAB183: same H1 ATR absolute-price ZigZag thresholds across TF, canonical wave parity, remaining amplitude at confirmation, conservative entry timing, dedup by origin-destination zones. Full reproducible local report and scripts: LAB182_REPORT.md, lab182_audit.py, lab182_normalize.py, LAB182_WAVE_PARITY.csv, LAB182_WAVE_MATCHED_SIGNALS.csv, LAB182_EQUIVALENT_H1_ATR.csv.