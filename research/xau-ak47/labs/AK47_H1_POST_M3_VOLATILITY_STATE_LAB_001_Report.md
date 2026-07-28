# AK47 H1 Post-M3 Volatility State Lab 001

## Scope
- Phase A exploratory state profiling; no trading rule is authorised.
- Uses only completed H1 information available before the next entry.
- Source lifecycle: real M3 exit → next entry → next trade exit.
- H1 features reconstructed from the supplied XAUUSD M5 feed.

## Integrity
- Episodes: 119
- Episodes with complete H1 features: 116
- Mean next-trade result: -0.0162R
- Total next-trade result: -1.88R
- Win rate: 40.5%

## Main descriptive findings
- Highest ATR acceleration quartile: N=29, EV +0.478R.
- Moderate episode width, 1.04–1.38 ATR: N=29, EV +0.467R.
- Medium body ratio, 0.32–0.55: N=29, EV +0.451R.
- Giveback fraction 0.342–0.400: N=29, EV -0.497R.
- Near-flat ATR acceleration, 0.928–1.031: N=29, EV -0.395R.
- Low overlap quartile, 0.206–0.318: N=29, EV -0.353R.
- Very wide episode, 1.38–3.55 ATR: N=29, EV -0.330R.

## State profiling
A four-cluster exploratory model found only four TREND_EXPANSION observations. Same-direction entries in that tiny group were positive, but N=3 is not actionable. The large balanced/chop group was approximately flat-to-negative and unstable by month.

## Monthly stability
The same observable states changed sign across months. January was strongly positive, March strongly negative, and later months mixed. Therefore no simple bar-state gate is authorised.

## Verdict
- No stable profitable post-M3 profile has yet been established.
- Volatility acceleration and moderate episode width are promising explanatory variables, not trading rules.
- Matched non-M3 controls are required before attributing weakness to the M3 exit itself.
- Any candidate must be frozen and tested on an independent period/feed.
