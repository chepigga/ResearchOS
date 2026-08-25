# LAB018 event-family operationalization addendum

Date: 2026-08-25
Status: FROZEN BEFORE ANY LAB018 RESULT CALCULATION

This file removes implementation ambiguity from the original preregistration.

## Shared pivots and ATR
- M15 pivot-3/pivot-5 use centered 3-3 and 5-5 extrema; a pivot is available only after its right-side confirmation bars have closed.
- ATR14 is Wilder-style true-range rolling mean approximation used consistently on M15; only completed/current entry bar information is used.
- Retest begins on the bar after the release bar and is valid for 8 M15 bars.
- If both SL and TP are touched in one bar after entry, adverse ordering is used.

## B COMPRESSION_RELEASE exact implementation
For release bar i:
- compression window = bars i-6 ... i-1;
- compression range = max(high)-min(low) over those 6 bars;
- baseline = median of all rolling 6-bar ranges fully contained in bars i-48 ... i-1;
- compression iff range <= 0.70*baseline;
- BUY release iff close[i] > compression high; SELL iff close[i] < compression low;
- release body/full-range >= 0.50;
- retest level = compression high for BUY, compression low for SELL.

## C FAILED_RESPONSE_RELEASE exact implementation
Search the most recent confirmed pivot-3 response origin within the previous 12 bars.
BUY:
- origin = confirmed pivot-3 HIGH k;
- bars k+1..k+3 contain at least 2 bearish closes and close[k+3] < close[k];
- protection reference = most recent confirmed pivot-3 LOW strictly before k;
- the three response closes never close below that protection reference;
- release bar i closes above high[k];
- retest level = high[k].
SELL is symmetric using pivot-3 LOW origin, at least 2 bullish closes, prior pivot-3 HIGH protection, no response close above protection, release close below low[k].

## D TWO_LEG_CORRECTION_RELEASE exact implementation
Use confirmed pivot-3s only and search the latest alternating correction sequence whose C pivot is confirmed before release.
BUY:
- A = pivot-3 LOW, B = subsequent pivot-3 HIGH, C = subsequent pivot-3 LOW;
- A,B,C all lie within the 32 bars preceding release;
- C >= A (second correction does not make a lower correction low);
- B > the last confirmed pivot-3 HIGH preceding A (directional bounce/impulse condition);
- release close > high[B];
- retest level = high[B].
SELL symmetric: A=HIGH, B=LOW, C=HIGH; C <= A; B < prior pivot-3 LOW before A; release close < low[B]; retest at low[B].

## Event de-duplication
- For each family and direction, after one release is detected, do not create another event until its 8-bar retest window expires or an entry occurs.
- After an entry, one active position per family only; later signals during that position are ignored.

## Common protected-pivot filter at actual fill
At the actual retest fill bar:
- stop anchor is the latest confirmed opposite-side pivot-5 available before that fill;
- pivot age >=22 bars;
- pivot level not violated after its confirmation and before fill;
- riskATR = abs(entry level - stop pivot)/ATR14(fill) > 3.72;
- stop must lie on the correct side of entry.
